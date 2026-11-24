import time

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Settings
from app.db import Database
from app.handlers.auth_handler import (
    create_auth_blueprint,
    create_auth_decorators,
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
    login_required, require_permission = create_auth_decorators(auth_service)

    # ---- Flask-приложение ----
    app = Flask(__name__)
    app.json.sort_keys = False
    # Приложение стоит за Nginx: берём реальный IP и схему из X-Forwarded-For / X-Forwarded-Proto
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    register_common(app, log)

    # CORS: разрешены только источники из ALLOWED_ORIGINS (по умолчанию никакие)
    if settings.allowed_origins:
        CORS(
            app,
            origins=list(settings.allowed_origins),
            methods=['GET', 'POST', 'PUT', 'DELETE'],
            allow_headers=['Content-Type', 'X-CSRF-Token'],
            max_age=600,
        )

    @app.after_request
    def add_instance_header(response):
        response.headers['X-Served-By'] = settings.instance_name
        return response

    app.register_blueprint(
        create_auth_blueprint(
            auth_service,
            user_service,
            settings,
            login_required,
            require_permission,
        )
    )
    app.register_blueprint(
        create_profile_blueprint(profile_service, login_required)
    )

    @app.get('/health')
    def health():
        return jsonify(
            {
                'status': 'ok',
                'instance': settings.instance_name,
                'client_ip': request.remote_addr,
                'x_forwarded_for': request.headers.get('X-Forwarded-For'),
                'x_forwarded_proto': request.headers.get('X-Forwarded-Proto'),
                'scheme': request.scheme,
                'host': request.host,
            }
        )

    if settings.enable_debug_routes:

        @app.get('/slow')
        def slow():
            seconds = min(
                max(request.args.get('seconds', default=5, type=int), 0), 120
            )
            time.sleep(seconds)
            return jsonify(
                {'slept': seconds, 'instance': settings.instance_name}
            )

    log.info(
        'App created: instance=%s, db=%s',
        settings.instance_name,
        settings.db_path,
    )
    return app
