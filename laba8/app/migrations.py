import os
import re
import sqlite3
from datetime import UTC, datetime

# Имя файла: 001_create_users.up.sql / 001_create_users.down.sql
FILE_RE = re.compile(r'^(\d{3})_([a-z0-9_]+)\.(up|down)\.sql$')


class MigrationError(Exception):
    pass


class Migrator:
    def __init__(self, db_path, directory):
        self.db_path = db_path
        self.directory = directory

    def _connect(self):
        folder = os.path.dirname(self.db_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute(
            'CREATE TABLE IF NOT EXISTS schema_migrations ('
            'version TEXT PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)'
        )
        conn.commit()
        return conn

    def available(self):
        found = {}
        for filename in sorted(os.listdir(self.directory)):
            match = FILE_RE.match(filename)
            if match:
                version, name, kind = match.groups()
                item = found.setdefault(version, {'name': name})
                item[kind] = os.path.join(self.directory, filename)
        return found

    @staticmethod
    def _applied_versions(conn):
        rows = conn.execute(
            'SELECT version FROM schema_migrations ORDER BY version'
        ).fetchall()
        return [row[0] for row in rows]

    def status(self):
        conn = self._connect()
        try:
            applied = set(self._applied_versions(conn))
        finally:
            conn.close()
        return [
            (version, item['name'], version in applied)
            for version, item in self.available().items()
        ]

    def up(self):
        conn = self._connect()
        done = []
        try:
            applied = set(self._applied_versions(conn))
            for version, item in self.available().items():
                if version in applied:
                    continue
                if 'up' not in item:
                    raise MigrationError(f'Missing .up.sql file for {version}')
                self._run_script(conn, item['up'])
                conn.execute(
                    'INSERT INTO schema_migrations (version, name, applied_at) '
                    'VALUES (?, ?, ?)',
                    (
                        version,
                        item['name'],
                        datetime.now(UTC).isoformat(timespec='seconds'),
                    ),
                )
                conn.commit()
                done.append(f'{version}_{item["name"]}')
        finally:
            conn.close()
        return done

    def down(self):
        conn = self._connect()
        try:
            applied = self._applied_versions(conn)
            if not applied:
                return None
            version = applied[-1]
            item = self.available().get(version)
            if item is None or 'down' not in item:
                raise MigrationError(f'Missing .down.sql file for {version}')
            self._run_script(conn, item['down'])
            conn.execute(
                'DELETE FROM schema_migrations WHERE version = ?', (version,)
            )
            conn.commit()
            return f'{version}_{item["name"]}'
        finally:
            conn.close()

    @staticmethod
    def _run_script(conn, path):
        with open(path, encoding='utf-8') as f:
            conn.executescript(f.read())
