from datetime import UTC, datetime

from werkzeug.security import generate_password_hash

from app.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models import User


class UserService:
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
            password_hash=generate_password_hash(
                password, method='pbkdf2:sha256'
            ),
            created_at=datetime.now(UTC).isoformat(timespec='seconds'),
        )
        user = self.user_repo.save(user)
        self.log.info('User created: id=%s', user.id)
        self.email_service.send_welcome(user)  # побочный эффект
        return user

    def get_user(self, user_id):
        user = self.user_repo.find_by_id(user_id)
        if user is None:
            raise NotFoundError(f'User {user_id} not found', {'id': user_id})
        return user

    def list_users(self, page, limit):
        total = self.user_repo.count()
        users = self.user_repo.find_page(limit, (page - 1) * limit)
        return users, total

    def update_user(self, user_id, name, email, age):
        user = self.get_user(user_id)
        self._check_email_rules(email, exclude_id=user_id)
        if age < user.age:
            raise BusinessRuleError(
                'Age cannot be decreased',
                {'field': 'age', 'current': user.age, 'new': age},
            )
        user.name, user.email, user.age = name, email, age
        self.user_repo.update(user)
        self.log.info('User updated: id=%s', user_id)
        return user

    def delete_user(self, user_id):
        self.get_user(user_id)  # 404, если не найден
        self.user_repo.delete(user_id)
        self.log.info('User deleted: id=%s', user_id)

    def _check_email_rules(self, email, exclude_id=None):
        domain = email.split('@')[1]
        if domain in self.blocked_domains:
            raise BusinessRuleError(
                'Registration with disposable email domains is not allowed',
                {'field': 'email', 'domain': domain},
            )
        if self.user_repo.email_exists(email, exclude_id):
            raise ConflictError(
                'Email already exists',
                {'field': 'email', 'value': email},
                code='EMAIL_ALREADY_EXISTS',
            )
