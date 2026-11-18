import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    age           INTEGER NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);
"""


class Database:
    def __init__(self, path):
        self.path = path
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = self._connect()
        try:
            with conn:
                conn.executescript(SCHEMA)
        finally:
            conn.close()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, sql, params=()):

        conn = self._connect()
        try:
            with conn:
                cursor = conn.execute(sql, params)
                return cursor.lastrowid, cursor.rowcount
        finally:
            conn.close()

    def query_one(self, sql, params=()):
        conn = self._connect()
        try:
            return conn.execute(sql, params).fetchone()
        finally:
            conn.close()

    def query_all(self, sql, params=()):
        conn = self._connect()
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()
