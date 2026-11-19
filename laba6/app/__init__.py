from uuid import uuid4

from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException

from app.config import Settings
from app.db import Database
from app.errors import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.handlers.auth_handler import create_auth_blueprint
from app.handlers.user_handler import create_user_blueprint
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService


def create_app(settings=None):
    settings = settings or Settings.from_env()
    app = Flask(__name__)

    app.config['SECRET_KEY'] = settings.secret_key
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False

    app.permanent_session_lifetime = 3600

    db = Database(settings.db_path)
    db.migrate('migrations')

    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    user_service = UserService(
        user_repo,
        blocked_domains=settings.blocked_email_domains,
    )

    app.register_blueprint(create_auth_blueprint(auth_service))
    app.register_blueprint(create_user_blueprint(user_service))

    @app.before_request
    def assign_request_id():
        g.request_id = str(uuid4())

    def error_response(error, message, code, status, details=None):
        response = jsonify(
            {
                'error': message,
                'message': message,
                'code': code,
                'details': details or {},
                'request_id': getattr(g, 'request_id', str(uuid4())),
            }
        )
        response.status_code = status
        response.headers['X-Request-ID'] = response.get_json()['request_id']
        return response

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return error_response(
            error, str(error), error.code, 400, error.details
        )

    @app.errorhandler(ConflictError)
    def handle_conflict_error(error):
        return error_response(
            error,
            str(error),
            error.code or 'CONFLICT',
            409,
            error.details,
        )

    @app.errorhandler(BusinessRuleError)
    def handle_business_rule_error(error):
        return error_response(
            error,
            str(error),
            'BUSINESS_RULE_VIOLATION',
            409,
            error.details,
        )

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error):
        return error_response(
            error, str(error), 'NOT_FOUND', 404, error.details
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if error.code == 404:
            code = 'NOT_FOUND'
        elif error.code == 405:
            code = 'METHOD_NOT_ALLOWED'
        else:
            code = 'HTTP_ERROR'

        return error_response(
            error,
            error.description,
            code,
            error.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception('Unexpected application error')
        return error_response(
            error,
            'An unexpected error occurred',
            'INTERNAL_ERROR',
            500,
        )

    if settings.enable_debug_routes:

        @app.get('/debug/crash')
        def debug_crash():
            raise RuntimeError('Intentional debug crash')

    @app.get('/health')
    def health():
        return jsonify(
            {
                'status': 'ok',
                'message': 'Application is running',
            }
        ), 200

    return app
