import psycopg2

from app.config import Settings

QUERIES = [
    (
        'Q1 users by email',
        "SELECT * FROM users WHERE email = 'user150000@example.com'",
    ),
    (
        'Q2 registrations of a course',
        'SELECT count(*) FROM registrations WHERE course_id = 7',
    ),
    (
        'Q3 users by LOWER(email)',
        "SELECT * FROM users WHERE LOWER(email) = 'user150000@example.com'",
    ),
    (
        'Q4 latest active users',
        "SELECT id, name FROM users WHERE status = 'active' ORDER BY created_at DESC LIMIT 20",
    ),
    (
        'Q5 last 5 students of a course',
        'SELECT r.id, u.name FROM registrations r JOIN users u ON u.id = r.user_id '
        'WHERE r.course_id = 7 ORDER BY r.id DESC LIMIT 5',
    ),
]


def explain(cur, sql):
    cur.execute('EXPLAIN (ANALYZE, FORMAT JSON) ' + sql)
    return cur.fetchone()[0][0]


def scan_nodes(plan):
    found = []
    if 'Scan' in plan['Node Type']:
        found.append(
            f'{plan["Node Type"]} on {plan.get("Index Name") or plan.get("Relation Name")}'
        )
    for child in plan.get('Plans', []):
        found.extend(scan_nodes(child))
    return found


def main():
    conn = psycopg2.connect(Settings.from_env().database_url)
    with conn.cursor() as cur:
        print(f'{"query":<34} {"time":>10}   plan')
        for label, sql in QUERIES:
            explain(cur, sql)  # прогрев кэша
            result = explain(cur, sql)
            plans = '; '.join(scan_nodes(result['Plan']))
            print(f'{label:<34} {result["Execution Time"]:>7.2f} ms   {plans}')
    conn.close()


if __name__ == '__main__':
    main()
