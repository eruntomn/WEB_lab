import psycopg2

from app.config import Settings


def main():
    dsn = Settings.from_env().database_url
    conn = psycopg2.connect(dsn)
    with conn, conn.cursor() as cur:
        cur.execute(
            'TRUNCATE transfers, registrations, courses, users, accounts RESTART IDENTITY CASCADE'
        )
        cur.execute(
            "INSERT INTO accounts (owner, balance) VALUES ('Alice', 1000), ('Bob', 500), ('Carol', 0)"
        )
        cur.execute(
            'INSERT INTO courses (title, seats) '
            "SELECT 'Course ' || g, 30 FROM generate_series(1, 100) g"
        )
        cur.execute(
            'INSERT INTO users (name, email, status, created_at) '
            "SELECT 'User ' || g, 'user' || g || '@example.com', "
            "CASE WHEN g % 10 = 0 THEN 'inactive' ELSE 'active' END, "
            "now() - g * interval '1 second' "
            'FROM generate_series(1, 200000) g'
        )
        cur.execute(
            'INSERT INTO registrations (user_id, course_id) '
            'SELECT id, ((id - 1) % 100) + 1 FROM users'
        )
        cur.execute(
            'INSERT INTO registrations (user_id, course_id) '
            'SELECT id, ((id + 49) % 100) + 1 FROM users WHERE id % 2 = 0'
        )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute('ANALYZE')
        for table in ('users', 'courses', 'registrations', 'accounts'):
            cur.execute(f'SELECT count(*) FROM {table}')
            print(f'{table:<15} {cur.fetchone()[0]:>8} rows')
    conn.close()


if __name__ == '__main__':
    main()
