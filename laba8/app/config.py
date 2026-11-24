import os
from dataclasses import dataclass


def _split(value):
    return tuple(item.strip() for item in value.split(',') if item.strip())


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    db_path: str
    migrations_dir: str
    log_level: str
    log_file: str
    blocked_email_domains: frozenset
    session_ttl_seconds: int
    cookie_secure: bool
    cookie_samesite: str
    allowed_origins: tuple
    instance_name: str
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
                d.lower() for d in _split(domains)
            ),
            session_ttl_seconds=int(os.getenv('SESSION_TTL_SECONDS', '3600')),
            cookie_secure=os.getenv('COOKIE_SECURE', '1') == '1',
            cookie_samesite=os.getenv('COOKIE_SAMESITE', 'Strict'),
            allowed_origins=_split(os.getenv('ALLOWED_ORIGINS', '')),
            instance_name=os.getenv('INSTANCE_NAME', 'app'),
            enable_debug_routes=os.getenv('ENABLE_DEBUG_ROUTES', '0') == '1',
        )
