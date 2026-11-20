from app.models import Session


class SessionRepository:
    def __init__(self, db):
        self.db = db

    def create(self, session):
        self.db.execute(
            'INSERT INTO sessions (id, user_id, created_at, expires_at) '
            'VALUES (?, ?, ?, ?)',
            (
                session.id,
                session.user_id,
                session.created_at,
                session.expires_at,
            ),
        )
        return session

    def find(self, session_id):
        row = self.db.query_one(
            'SELECT * FROM sessions WHERE id = ?', (session_id,)
        )
        return Session.from_row(row) if row else None

    def delete(self, session_id):
        self.db.execute('DELETE FROM sessions WHERE id = ?', (session_id,))

    def delete_expired(self, now):
        _, count = self.db.execute(
            'DELETE FROM sessions WHERE expires_at <= ?', (now,)
        )
        return count
