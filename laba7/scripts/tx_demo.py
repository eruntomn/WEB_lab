import sys
import threading
import time

import psycopg2
import psycopg2.errors

from app.config import Settings

DSN = Settings.from_env().database_url


def reset_accounts():
    conn = psycopg2.connect(DSN)
    with conn, conn.cursor() as cur:
        cur.execute(
            'UPDATE accounts SET balance = CASE id WHEN 1 THEN 1000 WHEN 2 THEN 500 ELSE 0 END, '
            'version = 0'
        )
    conn.close()


def show(title):
    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute('SELECT owner, balance FROM accounts ORDER BY id')
        rows = cur.fetchall()
    conn.close()
    total = sum(balance for _, balance in rows)
    line = ', '.join(f'{owner}={balance}' for owner, balance in rows)
    print(f'  {title}: {line} | total = {total}')


def atomicity():
    print('=== 1. Transfer WITHOUT a transaction (autocommit) ===')
    reset_accounts()
    show('before')
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute('UPDATE accounts SET balance = balance - 100 WHERE id = 1')
        print('  debited 100 from Alice (id=1)')
        cur.execute(
            'UPDATE accounts SET balance = balance + 100 WHERE id = 999'
        )
        print(f'  credit to account 999: rows affected = {cur.rowcount}')
    conn.close()
    show('after ')
    print('  -> 100 disappeared!\n')

    print('=== 2. The same transfer INSIDE a transaction ===')
    reset_accounts()
    show('before')
    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE accounts SET balance = balance - 100 WHERE id = 1'
            )
            print('  debited 100 from Alice (id=1)')
            cur.execute(
                'UPDATE accounts SET balance = balance + 100 WHERE id = 999'
            )
            if cur.rowcount == 0:
                raise RuntimeError('account 999 does not exist')
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f'  ERROR: {exc} -> ROLLBACK')
    finally:
        conn.close()
    show('after ')
    print('  -> money is intact')


def savepoint():
    conn = psycopg2.connect(DSN)
    with conn.cursor() as cur:
        cur.execute('TRUNCATE transfers RESTART IDENTITY')
        cur.execute(
            'INSERT INTO transfers (from_account, to_account, amount) VALUES (1, 2, 10)'
        )
        print('1) inserted transfer 1 -> 2 (10)')
        cur.execute('SAVEPOINT sp1')
        try:
            cur.execute(
                'INSERT INTO transfers (from_account, to_account, amount) VALUES (1, 2, -5)'
            )
        except psycopg2.errors.CheckViolation as exc:
            print(
                f'2) invalid transfer (-5) failed: {exc.diag.constraint_name}'
            )
            cur.execute('ROLLBACK TO SAVEPOINT sp1')
            print(
                '   ROLLBACK TO SAVEPOINT sp1: the transaction is still alive'
            )
        cur.execute(
            'INSERT INTO transfers (from_account, to_account, amount) VALUES (2, 3, 20)'
        )
        print('3) inserted transfer 2 -> 3 (20)')
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(
            'SELECT id, from_account, to_account, amount FROM transfers ORDER BY id'
        )
        print('Committed rows in transfers:')
        for row in cur.fetchall():
            print('  ', row)
    conn.close()


def read_balance(cur):
    cur.execute('SELECT balance FROM accounts WHERE id = 1')
    return cur.fetchone()[0]


def isolation():
    for level in ('READ COMMITTED', 'REPEATABLE READ'):
        reset_accounts()
        reader = psycopg2.connect(DSN)
        reader.set_session(isolation_level=level)
        writer = psycopg2.connect(DSN)
        with reader.cursor() as r, writer.cursor() as w:
            first = read_balance(r)
            w.execute(
                'UPDATE accounts SET balance = balance + 100 WHERE id = 1'
            )
            writer.commit()
            second = read_balance(r)
        reader.commit()
        reader.close()
        writer.close()
        verdict = (
            'value changed inside one transaction'
            if first != second
            else 'same snapshot'
        )
        print(
            f'{level:<16} first read = {first}, second read = {second}  ({verdict})'
        )


def lock_in_order(name, first, second, results):
    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT id FROM accounts WHERE id = %s FOR UPDATE', (first,)
            )
            print(f'  [{name}] locked account {first}')
            time.sleep(0.5)
            print(f'  [{name}] waiting for account {second} ...')
            cur.execute(
                'SELECT id FROM accounts WHERE id = %s FOR UPDATE', (second,)
            )
            print(f'  [{name}] locked account {second}')
        conn.commit()
        results[name] = 'committed'
    except psycopg2.errors.DeadlockDetected:
        conn.rollback()
        print(f'  [{name}] DEADLOCK detected -> transaction aborted, ROLLBACK')
        results[name] = 'aborted by deadlock detector'
    finally:
        conn.close()


def run_pair(order1, order2):
    results = {}
    threads = [
        threading.Thread(target=lock_in_order, args=('T1', *order1, results)),
        threading.Thread(target=lock_in_order, args=('T2', *order2, results)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print('  result:', results)


def deadlock():
    print('=== 1. Opposite lock order (T1: 1 -> 2, T2: 2 -> 1) ===')
    run_pair((1, 2), (2, 1))
    print('\n=== 2. Same lock order for everyone (lowest id first) ===')
    run_pair((1, 2), (1, 2))


if __name__ == '__main__':
    actions = {
        'atomicity': atomicity,
        'savepoint': savepoint,
        'isolation': isolation,
        'deadlock': deadlock,
    }
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode not in actions:
        print(
            'Usage: python -m scripts.tx_demo [atomicity|savepoint|isolation|deadlock]'
        )
        sys.exit(2)
    actions[mode]()
