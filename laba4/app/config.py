import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    db_path: str
    log_level: str
    log_file: str
    blocked_email_domains: frozenset
    enable_debug_routes: bool

    @classmethod
    def from_env(cls):
        domains = os.getenv(
            'BLOCKED_EMAIL_DOMAINS', 'tempmail.com,mailinator.com'
        )
        return cls(
            host=os.getenv('APP_HOST', '0.0.0.0'),
            port=int(os.getenv('APP_PORT', '5000')),
            db_path=os.getenv('DB_PATH', 'data/app.db'),
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            log_file=os.getenv('LOG_FILE', 'logs/app.log'),
            blocked_email_domains=frozenset(
                d.strip().lower() for d in domains.split(',') if d.strip()
            ),
            enable_debug_routes=os.getenv('ENABLE_DEBUG_ROUTES', '0') == '1',
        )
