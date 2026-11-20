import sqlite3
import sys

DB = 'data/app.db'
mode = sys.argv[1] if len(sys.argv) > 1 else 'data'

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


def show(title, sql):
    print(f'--- {title}')
    rows = conn.execute(sql).fetchall()
    if not rows:
        print('(empty)')
    for row in rows:
        print(dict(row))


if mode == 'schema':
    tables = [
        r['name']
        for r in conn.execute(
            'SELECT name FROM sqlite_master '
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    for table in tables:
        # имена таблиц взяты из sqlite_master, а не от пользователя (PRAGMA не принимает параметры)
        cols = [
            f'{r["name"]} {r["type"]}'
            for r in conn.execute(f'PRAGMA table_info({table})')
        ]
        print(f'{table}: ' + ', '.join(cols))
else:
    show(
        'schema_migrations',
        'SELECT version, name FROM schema_migrations ORDER BY version',
    )
    show(
        'users',
        'SELECT id, name, email, age, substr(password_hash, 1, 20) AS password_hash, '
        'last_login_at FROM users',
    )
    show(
        'sessions',
        'SELECT substr(id, 1, 16) AS id_hash, user_id, expires_at - created_at AS ttl_seconds '
        'FROM sessions',
    )
    show('profiles', 'SELECT * FROM profiles')
