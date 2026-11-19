from flask import Flask

from app.config import Settings
from app.db import Database
from app.handlers.auth_handler import create_auth_blueprint
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


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

    app.register_blueprint(create_auth_blueprint(auth_service))

    return app
