from flask import Flask

from app.config import Settings
from app.db import Database
from app.handlers.auth_handler import (
    create_auth_blueprint,
    create_login_required,
)
from app.handlers.common import register_common
from app.handlers.profile_handler import create_profile_blueprint
from app.logging_config import setup_logging
from app.repositories.profile_repository import ProfileRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.profile_service import ProfileService
from app.services.user_service import UserService


def create_app(settings=None):
    settings = settings or Settings.from_env()
    log = setup_logging(settings.log_level, settings.log_file)

    # ---- Сборка зависимостей (Dependency Injection) ----
    db = Database(settings.db_path)
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)
    profile_repo = ProfileRepository(db)
    email_service = EmailService(log)
    user_service = UserService(
        user_repo, email_service, settings.blocked_email_domains, log
    )
    auth_service = AuthService(
        user_repo, session_repo, settings.session_ttl_seconds, log
    )
    profile_service = ProfileService(user_repo, profile_repo, log)
    login_required = create_login_required(auth_service)

    # ---- Flask-приложение ----
    app = Flask(__name__)
    app.json.sort_keys = False
    register_common(app, log)
    app.register_blueprint(
        create_auth_blueprint(
            auth_service, user_service, settings, login_required
        )
    )
    app.register_blueprint(
        create_profile_blueprint(profile_service, login_required)
    )

    if settings.enable_debug_routes:

        @app.get('/debug/crash')
        def debug_crash():
            raise RuntimeError('Intentional crash for error-handling demo')

    log.info(
        'App created: port=%s, db=%s, session ttl=%ss',
        settings.port,
        settings.db_path,
        settings.session_ttl_seconds,
    )
    return app
