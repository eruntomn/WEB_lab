import hashlib
import secrets
import time
from datetime import UTC, datetime

from app.errors import UnauthorizedError
from app.models import Session
from app.security import hash_password, new_csrf_token, verify_password

# Хэш-заглушка: пароль проверяется и для несуществующего email, чтобы по времени
# ответа нельзя было понять, есть ли такой пользователь
DUMMY_HASH = hash_password('dummy-password')


def hash_token(token):
    """В базе хранится только хэш токена: утечка БД не раскрывает действующие сессии."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class AuthService:
    """Вход, выход и проверка сессии."""

    def __init__(
        self,
        user_repo,
        session_repo,
        session_ttl_seconds,
        log,
        clock=time.time,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.session_ttl_seconds = session_ttl_seconds
        self.log = log
        self.clock = clock

    def login(self, email, password):
        user = self.user_repo.find_by_email(email)
        password_ok = verify_password(
            password, user.password_hash if user else DUMMY_HASH
        )
        if user is None or not password_ok:
            raise UnauthorizedError('Invalid email or password')

        now = int(self.clock())
        self.session_repo.delete_expired(now)
        token = secrets.token_urlsafe(32)
        csrf_token = new_csrf_token()
        self.session_repo.create(
            Session(
                id=hash_token(token),
                user_id=user.id,
                created_at=now,
                expires_at=now + self.session_ttl_seconds,
                csrf_token=csrf_token,
            )
        )
        user.last_login_at = datetime.fromtimestamp(now, UTC).isoformat(
            timespec='seconds'
        )
        self.user_repo.touch_last_login(user.id, user.last_login_at)
        self.log.info('Login success: user_id=%s', user.id)
        return user, token, csrf_token

    def logout(self, token):
        if token:
            self.session_repo.delete(hash_token(token))
            self.log.info('Logout')

    def authenticate(self, token):
        """По токену из cookie возвращает (пользователь, сессия) или бросает UnauthorizedError."""
        if not token:
            raise UnauthorizedError('Authentication required')
        session = self.session_repo.find(hash_token(token))
        if session is None:
            raise UnauthorizedError('Invalid session')
        if session.expires_at <= int(self.clock()):
            self.session_repo.delete(session.id)
            raise UnauthorizedError('Session expired')
        user = self.user_repo.find_by_id(session.user_id)
        if user is None:
            raise UnauthorizedError('Invalid session')
        return user, session
