CREATE TABLE profiles (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    bio        TEXT,
    city       TEXT,
    updated_at TEXT NOT NULL
);