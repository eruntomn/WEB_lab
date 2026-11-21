CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    name       TEXT        NOT NULL,
    email      TEXT        NOT NULL,
    status     TEXT        NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    id      SERIAL PRIMARY KEY,
    owner   TEXT          NOT NULL,
    balance NUMERIC(12,2) NOT NULL CHECK (balance >= 0),
    version INTEGER       NOT NULL DEFAULT 0
);

CREATE TABLE courses (
    id      SERIAL  PRIMARY KEY,
    title   TEXT    NOT NULL,
    seats   INTEGER NOT NULL CHECK (seats >= 0),
    version INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE registrations (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    course_id  INTEGER     NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, course_id)
);

CREATE TABLE transfers (
    id           SERIAL PRIMARY KEY,
    from_account INTEGER       NOT NULL REFERENCES accounts(id),
    to_account   INTEGER       NOT NULL REFERENCES accounts(id),
    amount       NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);