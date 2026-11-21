import time

import psycopg2.errors

from app.errors import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class TransferService:
    def __init__(self, db, log):
        self.db = db
        self.log = log

    def list_accounts(self):
        with self.db.transaction() as cur:
            cur.execute(
                'SELECT id, owner, balance, version FROM accounts ORDER BY id'
            )
            return cur.fetchall()

    def transfer(self, from_id, to_id, amount):
        if from_id == to_id:
            raise ValidationError(
                'Cannot transfer to the same account',
                {'to_account': 'Must differ from from_account'},
            )
        with self.db.transaction() as cur:
            cur.execute(
                'SELECT id, balance FROM accounts WHERE id = ANY(%s) ORDER BY id FOR UPDATE',
                ([from_id, to_id],),
            )
            accounts = {row['id']: row for row in cur.fetchall()}
            for account_id in (from_id, to_id):
                if account_id not in accounts:
                    raise NotFoundError(
                        f'Account {account_id} not found', {'id': account_id}
                    )
            if accounts[from_id]['balance'] < amount:
                raise BusinessRuleError(
                    'Insufficient funds',
                    {
                        'balance': str(accounts[from_id]['balance']),
                        'amount': str(amount),
                    },
                    code='INSUFFICIENT_FUNDS',
                )
            cur.execute(
                'UPDATE accounts SET balance = balance - %s, version = version + 1 WHERE id = %s',
                (amount, from_id),
            )
            cur.execute(
                'UPDATE accounts SET balance = balance + %s, version = version + 1 WHERE id = %s',
                (amount, to_id),
            )
            cur.execute(
                'INSERT INTO transfers (from_account, to_account, amount) '
                'VALUES (%s, %s, %s) RETURNING id, created_at',
                (from_id, to_id, amount),
            )
            row = cur.fetchone()
        self.log.info(
            'Transfer %s: %s -> %s, amount %s',
            row['id'],
            from_id,
            to_id,
            amount,
        )
        return {
            'id': row['id'],
            'from_account': from_id,
            'to_account': to_id,
            'amount': str(amount),
            'created_at': row['created_at'],
        }


class RegistrationService:
    STRATEGIES = ('naive', 'atomic', 'lock')

    def __init__(self, db, log):
        self.db = db
        self.log = log

    def register(self, strategy, course_id, user_id, delay=0.0):
        if strategy not in self.STRATEGIES:
            raise ValidationError(
                'Unknown strategy',
                {'strategy': f'Must be one of: {", ".join(self.STRATEGIES)}'},
            )
        method = getattr(self, f'_register_{strategy}')
        try:
            with self.db.transaction() as cur:
                method(cur, course_id, user_id, delay)
        except psycopg2.errors.UniqueViolation:
            raise ConflictError(
                'User is already registered on this course',
                {'user_id': user_id, 'course_id': course_id},
                code='ALREADY_REGISTERED',
            )
        except psycopg2.errors.ForeignKeyViolation:
            raise NotFoundError(
                'User or course not found',
                {'user_id': user_id, 'course_id': course_id},
            )
        self.log.info(
            'Registered user %s on course %s (%s)',
            user_id,
            course_id,
            strategy,
        )
        return {'user_id': user_id, 'course_id': course_id}

    @staticmethod
    def _insert_registration(cur, course_id, user_id):
        cur.execute(
            'INSERT INTO registrations (user_id, course_id) VALUES (%s, %s)',
            (user_id, course_id),
        )

    def _register_naive(self, cur, course_id, user_id, delay):
        cur.execute('SELECT seats FROM courses WHERE id = %s', (course_id,))
        course = cur.fetchone()
        if course is None:
            raise NotFoundError(
                f'Course {course_id} not found', {'id': course_id}
            )
        seats = course['seats']
        if seats <= 0:
            raise BusinessRuleError(
                'No seats available', {'course_id': course_id}, code='NO_SEATS'
            )
        time.sleep(delay)
        self._insert_registration(cur, course_id, user_id)
        cur.execute(
            'UPDATE courses SET seats = %s WHERE id = %s',
            (seats - 1, course_id),
        )

    def _register_atomic(self, cur, course_id, user_id, delay):
        cur.execute(
            'UPDATE courses SET seats = seats - 1 WHERE id = %s AND seats > 0',
            (course_id,),
        )
        if cur.rowcount == 0:
            cur.execute('SELECT 1 FROM courses WHERE id = %s', (course_id,))
            if cur.fetchone() is None:
                raise NotFoundError(
                    f'Course {course_id} not found', {'id': course_id}
                )
            raise BusinessRuleError(
                'No seats available', {'course_id': course_id}, code='NO_SEATS'
            )
        time.sleep(delay)
        self._insert_registration(cur, course_id, user_id)

    def _register_lock(self, cur, course_id, user_id, delay):
        cur.execute(
            'SELECT seats FROM courses WHERE id = %s FOR UPDATE', (course_id,)
        )
        course = cur.fetchone()
        if course is None:
            raise NotFoundError(
                f'Course {course_id} not found', {'id': course_id}
            )
        if course['seats'] <= 0:
            raise BusinessRuleError(
                'No seats available', {'course_id': course_id}, code='NO_SEATS'
            )
        time.sleep(delay)
        self._insert_registration(cur, course_id, user_id)
        cur.execute(
            'UPDATE courses SET seats = seats - 1 WHERE id = %s', (course_id,)
        )


class CourseService:
    def __init__(self, db, log):
        self.db = db
        self.log = log

    def get_course(self, course_id):
        with self.db.transaction() as cur:
            cur.execute(
                'SELECT c.id, c.title, c.seats, c.version, '
                '(SELECT count(*) FROM registrations r WHERE r.course_id = c.id) AS registered '
                'FROM courses c WHERE c.id = %s',
                (course_id,),
            )
            course = cur.fetchone()
        if course is None:
            raise NotFoundError(
                f'Course {course_id} not found', {'id': course_id}
            )
        return course

    def update_course(self, course_id, title, version):
        with self.db.transaction() as cur:
            cur.execute(
                'UPDATE courses SET title = %s, version = version + 1 '
                'WHERE id = %s AND version = %s RETURNING id, title, seats, version',
                (title, course_id, version),
            )
            course = cur.fetchone()
            if course is None:
                cur.execute(
                    'SELECT version FROM courses WHERE id = %s', (course_id,)
                )
                current = cur.fetchone()
                if current is None:
                    raise NotFoundError(
                        f'Course {course_id} not found', {'id': course_id}
                    )
                raise ConflictError(
                    'Course was changed by someone else, reload and retry',
                    {
                        'your_version': version,
                        'current_version': current['version'],
                    },
                    code='VERSION_CONFLICT',
                )
        return course

    def list_with_students(self, limit, mode):
        with self.db.transaction() as cur:
            if mode == 'naive':
                cur.execute(
                    'SELECT id, title, seats FROM courses ORDER BY id LIMIT %s',
                    (limit,),
                )
                courses = cur.fetchall()
                for course in courses:
                    cur.execute(
                        'SELECT u.id, u.name FROM registrations r '
                        'JOIN users u ON u.id = r.user_id '
                        'WHERE r.course_id = %s ORDER BY r.id DESC LIMIT 5',
                        (course['id'],),
                    )
                    course['students'] = cur.fetchall()
                return courses

            cur.execute(
                'SELECT c.id, c.title, c.seats, s.user_id, s.name '
                'FROM (SELECT id, title, seats FROM courses ORDER BY id LIMIT %s) c '
                'LEFT JOIN LATERAL ('
                '  SELECT r.id AS reg_id, u.id AS user_id, u.name '
                '  FROM registrations r JOIN users u ON u.id = r.user_id '
                '  WHERE r.course_id = c.id ORDER BY r.id DESC LIMIT 5'
                ') s ON TRUE '
                'ORDER BY c.id, s.reg_id DESC',
                (limit,),
            )
            courses = {}
            for row in cur.fetchall():
                course = courses.setdefault(
                    row['id'],
                    {
                        'id': row['id'],
                        'title': row['title'],
                        'seats': row['seats'],
                        'students': [],
                    },
                )
                if row['user_id'] is not None:
                    course['students'].append(
                        {'id': row['user_id'], 'name': row['name']}
                    )
            return list(courses.values())
