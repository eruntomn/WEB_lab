import os
import sqlite3


class Database:
    """Обёртка над драйвером sqlite3. Только параметризованные запросы.
    Схему создают миграции (migrate.py), а не само приложение."""

    def __init__(self, path):
        self.path = path
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            'PRAGMA foreign_keys = ON'
        )  # без этого SQLite не проверяет внешние ключи и каскады
        return conn

    def execute(self, sql, params=()):
        """INSERT/UPDATE/DELETE. Возвращает (lastrowid, rowcount)."""
        conn = self._connect()
        try:
            with conn:  # commit при успехе, rollback при ошибке
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
