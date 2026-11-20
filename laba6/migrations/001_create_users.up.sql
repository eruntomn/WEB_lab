CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    age           INTEGER NOT NULL CHECK (age >= 18 AND age <= 120),
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);