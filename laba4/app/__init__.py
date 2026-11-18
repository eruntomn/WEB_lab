from flask import Flask

from app.config import Settings
from app.db import Database
from app.handlers.common import register_common
from app.handlers.user_handler import create_user_blueprint
from app.logging_config import setup_logging
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.services.user_service import UserService


def create_app(settings=None):
    settings = settings or Settings.from_env()
    log = setup_logging(settings.log_level, settings.log_file)

    db = Database(settings.db_path)
    user_repo = UserRepository(db)
    email_service = EmailService(log)
    user_service = UserService(
        user_repo, email_service, settings.blocked_email_domains, log
    )

    app = Flask(__name__)
    app.json.sort_keys = False
    register_common(app, log)
    app.register_blueprint(create_user_blueprint(user_service))

    if settings.enable_debug_routes:

        @app.get('/debug/crash')
        def debug_crash():
            raise RuntimeError('Intentional crash for error-handling demo')

    log.info(
        'App created: port=%s, db=%s, log level=%s',
        settings.port,
        settings.db_path,
        settings.log_level,
    )
    return app
