import sqlite3


def make_db():
    conn = sqlite3.connect(':memory:')
    conn.execute(
        'CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)'
    )
    conn.executemany(
        'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
        [
            ('admin', 'S3cret!', 'admin'),
            ('anna', 'anna-pass', 'user'),
            ('boris', 'boris-pass', 'user'),
        ],
    )
    return conn


def login_vulnerable(conn, username, password):
    query = f"SELECT username, role FROM users WHERE username = '{username}' AND password = '{password}'"
    print('   SQL:', query)
    return conn.execute(query).fetchone()


def login_safe(conn, username, password):
    return conn.execute(
        'SELECT username, role FROM users WHERE username = ? AND password = ?',
        (username, password),
    ).fetchone()


def search_vulnerable(conn, text):
    query = f"SELECT username, role FROM users WHERE username LIKE '%{text}%'"
    print('   SQL:', query)
    return conn.execute(query).fetchall()


def search_safe(conn, text):
    return conn.execute(
        'SELECT username, role FROM users WHERE username LIKE ?',
        (f'%{text}%',),
    ).fetchall()


def main():
    conn = make_db()
    print('=== VULNERABLE code (string formatting) ===')
    print('1) normal login anna / anna-pass')
    print('   result:', login_vulnerable(conn, 'anna', 'anna-pass'))
    print(
        "2) attack: username = admin' --   (the password check is commented out)"
    )
    print('   result:', login_vulnerable(conn, "admin' --", 'wrong'))
    print("3) attack: username = ' OR '1'='1' --")
    print('   result:', login_vulnerable(conn, "' OR '1'='1' --", 'wrong'))
    print('4) attack on search: UNION SELECT leaks all passwords')
    print(
        '   result:',
        search_vulnerable(
            conn, "zzz' UNION SELECT username, password FROM users --"
        ),
    )

    print('\n=== SAFE code (parameterized queries: ?) ===')
    print(
        "2) admin' --                 ->",
        login_safe(conn, "admin' --", 'wrong'),
    )
    print(
        "3) ' OR '1'='1' --           ->",
        login_safe(conn, "' OR '1'='1' --", 'wrong'),
    )
    print(
        '4) UNION SELECT in search    ->',
        search_safe(
            conn, "zzz' UNION SELECT username, password FROM users --"
        ),
    )
    print('   the input is treated as plain text, not as SQL')


if __name__ == '__main__':
    main()
