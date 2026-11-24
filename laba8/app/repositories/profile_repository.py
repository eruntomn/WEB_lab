from app.models import Profile


class ProfileRepository:
    def __init__(self, db):
        self.db = db

    def get(self, user_id):
        row = self.db.query_one(
            'SELECT * FROM profiles WHERE user_id = ?', (user_id,)
        )
        return Profile.from_row(row) if row else None

    def upsert(self, profile):
        self.db.execute(
            'INSERT INTO profiles (user_id, bio, city, updated_at) '
            'VALUES (?, ?, ?, ?) '
            'ON CONFLICT(user_id) DO UPDATE SET '
            'bio = excluded.bio, city = excluded.city, updated_at = excluded.updated_at',
            (profile.user_id, profile.bio, profile.city, profile.updated_at),
        )
        return profile

    def delete(self, user_id):
        _, rowcount = self.db.execute(
            'DELETE FROM profiles WHERE user_id = ?', (user_id,)
        )
        return rowcount > 0
