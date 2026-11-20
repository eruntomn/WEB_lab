import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Все настройки приложения. Берутся из переменных окружения."""

    host: str
    port: int
    db_path: str
    migrations_dir: str
    log_level: str
    log_file: str
    blocked_email_domains: frozenset
    session_ttl_seconds: int
    cookie_secure: bool
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
            migrations_dir=os.getenv('MIGRATIONS_DIR', 'migrations'),
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            log_file=os.getenv('LOG_FILE', 'logs/app.log'),
            blocked_email_domains=frozenset(
                d.strip().lower() for d in domains.split(',') if d.strip()
            ),
            session_ttl_seconds=int(os.getenv('SESSION_TTL_SECONDS', '3600')),
            cookie_secure=os.getenv('COOKIE_SECURE', '0') == '1',
            enable_debug_routes=os.getenv('ENABLE_DEBUG_ROUTES', '0') == '1',
        )
