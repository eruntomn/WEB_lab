from app.models import User


class UserRepository:
    """Доступ к таблице users: только SQL, все запросы параметризованные."""

    def __init__(self, db):
        self.db = db

    def save(self, user):
        user_id, _ = self.db.execute(
            'INSERT INTO users (name, email, age, password_hash, created_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (
                user.name,
                user.email,
                user.age,
                user.password_hash,
                user.created_at,
            ),
        )
        user.id = user_id
        return user

    def find_by_id(self, user_id):
        row = self.db.query_one('SELECT * FROM users WHERE id = ?', (user_id,))
        return User.from_row(row) if row else None

    def find_by_email(self, email):
        row = self.db.query_one(
            'SELECT * FROM users WHERE email = ?', (email,)
        )
        return User.from_row(row) if row else None

    def find_all(self, limit=100):
        rows = self.db.query_all(
            'SELECT * FROM users ORDER BY id LIMIT ?', (limit,)
        )
        return [User.from_row(row) for row in rows]

    def email_exists(self, email):
        row = self.db.query_one(
            'SELECT 1 FROM users WHERE email = ?', (email,)
        )
        return row is not None

    def touch_last_login(self, user_id, when):
        self.db.execute(
            'UPDATE users SET last_login_at = ? WHERE id = ?', (when, user_id)
        )

    def set_role(self, email, role):
        _, rowcount = self.db.execute(
            'UPDATE users SET role = ? WHERE email = ?', (role, email)
        )
        return rowcount > 0

    def delete(self, user_id):
        _, rowcount = self.db.execute(
            'DELETE FROM users WHERE id = ?', (user_id,)
        )
        return rowcount > 0
