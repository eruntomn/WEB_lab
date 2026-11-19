import os
import sqlite3


class Database:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

        migrations_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'migrations',
        )
        self.migrate(migrations_dir)

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def execute(self, sql, params=()):
        with self._connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid, cursor.rowcount

    def query_one(self, sql, params=()):
        with self._connect() as conn:
            return conn.execute(sql, params).fetchone()

    def query_all(self, sql, params=()):
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()

    def migrate(self, directory):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            for filename in sorted(os.listdir(directory)):
                if not filename.endswith('.sql'):
                    continue

                exists = conn.execute(
                    'SELECT 1 FROM schema_migrations WHERE version = ?',
                    (filename,),
                ).fetchone()

                if exists:
                    continue

                path = os.path.join(directory, filename)

                with open(path, encoding='utf-8') as file:
                    script = file.read()

                conn.execute('BEGIN')
                try:
                    statement = ''
                    for line in script.splitlines():
                        statement += line + '\n'
                        if sqlite3.complete_statement(statement):
                            if statement.strip():
                                conn.execute(statement)
                            statement = ''

                    if statement.strip():
                        raise ValueError('Incomplete SQL migration')

                    conn.execute(
                        'INSERT INTO schema_migrations(version) VALUES (?)',
                        (filename,),
                    )
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
