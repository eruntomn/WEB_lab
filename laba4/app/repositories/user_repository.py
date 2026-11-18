from app.models import User


class UserRepository:
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

    def find_page(self, limit, offset):
        rows = self.db.query_all(
            'SELECT * FROM users ORDER BY id LIMIT ? OFFSET ?', (limit, offset)
        )
        return [User.from_row(r) for r in rows]

    def count(self):
        return self.db.query_one('SELECT COUNT(*) AS c FROM users')['c']

    def email_exists(self, email, exclude_id=None):
        row = self.db.query_one(
            'SELECT 1 FROM users WHERE email = ? AND id != ?',
            (email, exclude_id if exclude_id is not None else 0),
        )
        return row is not None

    def update(self, user):
        self.db.execute(
            'UPDATE users SET name = ?, email = ?, age = ? WHERE id = ?',
            (user.name, user.email, user.age, user.id),
        )
        return user

    def delete(self, user_id):
        _, rowcount = self.db.execute(
            'DELETE FROM users WHERE id = ?', (user_id,)
        )
        return rowcount > 0
