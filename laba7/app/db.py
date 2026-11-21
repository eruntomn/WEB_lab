import threading
import time
from contextlib import contextmanager

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

_local = threading.local()

ISOLATION_LEVELS = {'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE'}


def reset_stats():
    _local.queries = 0
    _local.time_ms = 0.0


def get_stats():
    return {
        'queries': getattr(_local, 'queries', 0),
        'time_ms': round(getattr(_local, 'time_ms', 0.0), 1),
    }


class CountingCursor(RealDictCursor):
    def execute(self, query, vars=None):
        started = time.perf_counter()
        try:
            return super().execute(query, vars)
        finally:
            _local.queries = getattr(_local, 'queries', 0) + 1
            _local.time_ms = (
                getattr(_local, 'time_ms', 0.0)
                + (time.perf_counter() - started) * 1000
            )


class Database:
    def __init__(self, dsn, minconn=1, maxconn=40):
        self.pool = ThreadedConnectionPool(
            minconn, maxconn, dsn, cursor_factory=CountingCursor
        )

    @contextmanager
    def transaction(self, isolation_level=None):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                if isolation_level:
                    if isolation_level not in ISOLATION_LEVELS:
                        raise ValueError(
                            f'Unknown isolation level: {isolation_level}'
                        )
                    cur.execute(
                        f'SET TRANSACTION ISOLATION LEVEL {isolation_level}'
                    )
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    def close(self):
        self.pool.closeall()
