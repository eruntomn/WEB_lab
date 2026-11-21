import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    host: str
    port: int
    migrations_dir: str
    log_level: str
    query_warn_threshold: int

    @classmethod
    def from_env(cls):
        return cls(
            database_url=os.getenv(
                'DATABASE_URL',
                'postgresql://webprog:webprog123@localhost:5433/webprog',
            ),
            host=os.getenv('APP_HOST', '0.0.0.0'),
            port=int(os.getenv('APP_PORT', '5000')),
            migrations_dir=os.getenv('MIGRATIONS_DIR', 'migrations'),
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            query_warn_threshold=int(os.getenv('QUERY_WARN_THRESHOLD', '20')),
        )
