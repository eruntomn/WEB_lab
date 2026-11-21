import logging
import threading

from app.config import Settings
from app.db import Database
from app.errors import AppError
from app.services import RegistrationService

CAPACITY = 10
USERS = 30
DELAY = 0.05


def new_course(db, title):
    with db.transaction() as cur:
        cur.execute(
            'INSERT INTO courses (title, seats) VALUES (%s, %s) RETURNING id',
            (title, CAPACITY),
        )
        return cur.fetchone()['id']


def run_threads(service, strategy, course_id, user_ids):
    results = {'registered': 0, 'no_seats': 0, 'duplicate': 0, 'errors': 0}
    lock = threading.Lock()
    barrier = threading.Barrier(len(user_ids))

    def worker(user_id):
        barrier.wait()
        try:
            service.register(strategy, course_id, user_id, delay=DELAY)
            key = 'registered'
        except AppError as exc:
            key = {
                'NO_SEATS': 'no_seats',
                'ALREADY_REGISTERED': 'duplicate',
            }.get(exc.code, 'errors')
        except Exception:
            key = 'errors'
        with lock:
            results[key] += 1

    threads = [
        threading.Thread(target=worker, args=(uid,)) for uid in user_ids
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def state(db, course_id):
    with db.transaction() as cur:
        cur.execute('SELECT seats FROM courses WHERE id = %s', (course_id,))
        seats = cur.fetchone()['seats']
        cur.execute(
            'SELECT count(*) AS n FROM registrations WHERE course_id = %s',
            (course_id,),
        )
        count = cur.fetchone()['n']
    return seats, count


def main():
    logging.disable(logging.CRITICAL)
    db = Database(Settings.from_env().database_url)
    service = RegistrationService(db, logging.getLogger('api'))

    print(f'{USERS} users try to take {CAPACITY} seats at the same time\n')
    print(
        f'{"strategy":<9} {"registered":>10} {"rejected":>9} {"in DB":>6} {"seats left":>11}  verdict'
    )
    for strategy in ('naive', 'atomic', 'lock'):
        course_id = new_course(db, f'Race demo ({strategy})')
        results = run_threads(
            service, strategy, course_id, range(1, USERS + 1)
        )
        seats, count = state(db, course_id)
        verdict = (
            f'OVERSOLD ({count} > {CAPACITY})' if count > CAPACITY else 'OK'
        )
        print(
            f'{strategy:<9} {results["registered"]:>10} {results["no_seats"]:>9} {count:>6} {seats:>11}  {verdict}'
        )

    print(
        '\nThe same user registers 5 times at once (atomic strategy, UNIQUE constraint):'
    )
    course_id = new_course(db, 'Race demo (duplicates)')
    results = run_threads(service, 'atomic', course_id, [1] * 5)
    seats, count = state(db, course_id)
    print(
        f'  registered = {results["registered"]}, duplicates rejected = {results["duplicate"]}, '
        f'in DB = {count}, seats left = {seats} (seat of failed attempts was returned by ROLLBACK)'
    )
    db.close()


if __name__ == '__main__':
    main()
