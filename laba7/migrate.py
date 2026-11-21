import os
import re
import sys
import time

import psycopg2

from app.config import Settings

FILE_RE = re.compile(r'^(\d{3})_([a-z0-9_]+)\.(up|down)\.sql$')


def available(directory):
    found = {}
    for filename in sorted(os.listdir(directory)):
        match = FILE_RE.match(filename)
        if match:
            version, name, kind = match.groups()
            found.setdefault(version, {'name': name})[kind] = os.path.join(
                directory, filename
            )
    return found


def connect(dsn):
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(
            'CREATE TABLE IF NOT EXISTS schema_migrations ('
            'version TEXT PRIMARY KEY, name TEXT NOT NULL, '
            'applied_at TIMESTAMPTZ NOT NULL DEFAULT now())'
        )
    conn.commit()
    return conn


def applied_versions(conn):
    with conn.cursor() as cur:
        cur.execute('SELECT version FROM schema_migrations ORDER BY version')
        return [row[0] for row in cur.fetchall()]


def run_script(conn, path):
    with open(path, encoding='utf-8') as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)


def cmd_status(conn, directory):
    applied = set(applied_versions(conn))
    for version, item in available(directory).items():
        state = 'applied' if version in applied else 'pending'
        print(f'  {version}  {item["name"]:<30} {state}')


def cmd_up(conn, directory):
    applied = set(applied_versions(conn))
    done = 0
    for version, item in available(directory).items():
        if version in applied:
            continue
        started = time.perf_counter()
        try:
            run_script(conn, item['up'])
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO schema_migrations (version, name) VALUES (%s, %s)',
                    (version, item['name']),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        print(
            f'Applied migration {version}_{item["name"]} ({time.perf_counter() - started:.2f} s)'
        )
        done += 1
    if not done:
        print('Nothing to apply: schema is up to date')


def cmd_down(conn, directory):
    applied = applied_versions(conn)
    if not applied:
        print('Nothing to roll back')
        return
    version = applied[-1]
    item = available(directory).get(version)
    if item is None or 'down' not in item:
        raise RuntimeError(f'Missing .down.sql file for {version}')
    try:
        run_script(conn, item['down'])
        with conn.cursor() as cur:
            cur.execute(
                'DELETE FROM schema_migrations WHERE version = %s', (version,)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    print(f'Rolled back migration {version}_{item["name"]}')


def main():
    settings = Settings.from_env()
    command = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if command not in ('status', 'up', 'down'):
        print('Usage: python migrate.py [status|up|down]')
        sys.exit(2)
    try:
        conn = connect(settings.database_url)
    except psycopg2.OperationalError as exc:
        print(f'Cannot connect to the database: {exc}')
        print('Is the database running? Try: docker compose up -d --wait db')
        sys.exit(1)
    try:
        {'status': cmd_status, 'up': cmd_up, 'down': cmd_down}[command](
            conn, settings.migrations_dir
        )
    except Exception as exc:
        print(f'Migration error: {exc}')
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
