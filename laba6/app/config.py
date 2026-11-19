import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    host: str = '0.0.0.0'
    port: int = 5000
    db_path: str = 'data/app.db'
    secret_key: str = 'development-only-change-this-key'
    log_level: str = 'INFO'
    log_file: str = 'logs/app.log'
    blocked_email_domains: frozenset = field(
        default_factory=lambda: frozenset(
            {
                'tempmail.com',
                'mailinator.com',
            }
        )
    )
    enable_debug_routes: bool = False

    @classmethod
    def from_env(cls):
        blocked_domains = frozenset(
            domain.strip().lower()
            for domain in os.getenv(
                'BLOCKED_EMAIL_DOMAINS',
                'tempmail.com,mailinator.com',
            ).split(',')
            if domain.strip()
        )

        debug_value = os.getenv('ENABLE_DEBUG_ROUTES', '0').strip().lower()

        return cls(
            host=os.getenv('APP_HOST', '0.0.0.0'),
            port=int(os.getenv('APP_PORT', '5000')),
            db_path=os.getenv('DB_PATH', 'data/app.db'),
            secret_key=os.getenv(
                'SECRET_KEY',
                'development-only-change-this-key',
            ),
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            log_file=os.getenv('LOG_FILE', 'logs/app.log'),
            blocked_email_domains=blocked_domains,
            enable_debug_routes=debug_value in {'1', 'true', 'yes', 'on'},
        )
