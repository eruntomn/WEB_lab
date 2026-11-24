from datetime import UTC, datetime

from app.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models import User
from app.security import hash_password


class UserService:
    """Регистрация, чтение и удаление пользователей (бизнес-правила)."""

    def __init__(self, user_repo, email_service, blocked_domains, log):
        self.user_repo = user_repo
        self.email_service = email_service
        self.blocked_domains = blocked_domains
        self.log = log

    def create_user(self, name, email, age, password):
        self._check_email_rules(email)
        user = User(
            name=name,
            email=email,
            age=age,
            password_hash=hash_password(password),
            created_at=datetime.now(UTC).isoformat(timespec='seconds'),
        )
        user = self.user_repo.save(user)
        self.log.info('User registered: id=%s', user.id)
        self.email_service.send_welcome(user)
        return user

    def get_user(self, user_id):
        user = self.user_repo.find_by_id(user_id)
        if user is None:
            raise NotFoundError(f'User {user_id} not found', {'id': user_id})
        return user

    def list_users(self):
        return self.user_repo.find_all()

    def delete_user(self, user_id):
        self.get_user(user_id)
        self.user_repo.delete(
            user_id
        )  # сессии и профиль удалит БД (ON DELETE CASCADE)
        self.log.info('User deleted: id=%s', user_id)

    def _check_email_rules(self, email):
        domain = email.split('@')[1]
        if domain in self.blocked_domains:
            raise BusinessRuleError(
                'Registration with disposable email domains is not allowed',
                {'field': 'email', 'domain': domain},
            )
        if self.user_repo.email_exists(email):
            raise ConflictError(
                'Email already exists',
                {'field': 'email', 'value': email},
                code='EMAIL_ALREADY_EXISTS',
            )
