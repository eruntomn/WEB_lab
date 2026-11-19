from datetime import UTC, datetime

from werkzeug.security import generate_password_hash

from app.errors import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models import User


class UserService:
    def __init__(
        self, user_repo, email_service=None, blocked_domains=None, log=None
    ):
        self.user_repo = user_repo
        self.email_service = email_service
        self.blocked_domains = blocked_domains or frozenset()
        self.log = log

    def create_user(self, name, email, age, password):
        name = name.strip()
        email = email.strip().lower()

        domain = email.rsplit('@', 1)[-1] if '@' in email else ''
        if domain in self.blocked_domains:
            raise BusinessRuleError(
                'Email domain is not allowed',
                {'domain': domain},
            )

        if self.user_repo.email_exists(email, None):
            raise ConflictError(
                'Email already exists',
                code='EMAIL_ALREADY_EXISTS',
            )

        user = User(
            name=name,
            email=email,
            age=age,
            password_hash=generate_password_hash(
                password,
                method='pbkdf2:sha256',
            ),
            created_at=datetime.now(UTC).isoformat(),
        )

        user = self.user_repo.save(user)

        if self.log:
            self.log.info('User created: id=%s', user.id)

        if self.email_service:
            self.email_service.send_welcome(user)

        return user

    def get_user(self, user_id):
        user = self.user_repo.find_by_id(user_id)
        if user is None:
            raise NotFoundError('User not found', {'id': user_id})
        return user

    def list_users(self, page=1, limit=10):
        offset = (page - 1) * limit
        total = self.user_repo.count()
        users = self.user_repo.find_page(limit, offset)
        return users, total

    def update_user(self, user_id, name, email, age):
        user = self.get_user(user_id)
        email = email.strip().lower()

        if age < user.age:
            raise BusinessRuleError(
                'Age cannot be decreased',
                {'field': 'age', 'current': user.age, 'new': age},
            )

        if self.user_repo.email_exists(email, user_id):
            raise ConflictError(
                'Email already exists',
                code='EMAIL_ALREADY_EXISTS',
            )

        user.name = name.strip()
        user.email = email
        user.age = age

        self.user_repo.update(user)
        return user

    def delete_user(self, user_id):
        self.get_user(user_id)
        return self.user_repo.delete(user_id)

    def get_profile(self, user_id):
        return self.get_user(user_id)

    def update_profile(self, user_id, data):
        user = self.get_profile(user_id)

        allowed = {'name', 'email', 'age', 'bio', 'avatar'}

        if not isinstance(data, dict) or not data:
            raise ValidationError('Invalid profile data')

        if set(data) - allowed:
            raise ValidationError('Unknown profile fields')

        if 'name' in data:
            if not isinstance(data['name'], str) or not data['name'].strip():
                raise ValidationError('Invalid name')
            user.name = data['name'].strip()

        if 'email' in data:
            if not isinstance(data['email'], str) or '@' not in data['email']:
                raise ValidationError('Invalid email')
            email = data['email'].strip().lower()

            if self.user_repo.email_exists(email, exclude_id=user_id):
                raise ConflictError('Email already exists')

            user.email = email

        if 'age' in data:
            if type(data['age']) is not int or not 18 <= data['age'] <= 120:
                raise ValidationError('Invalid age')
            user.age = data['age']

        for field in ('bio', 'avatar'):
            if field in data:
                if not isinstance(data[field], str):
                    raise ValidationError(f'Invalid {field}')
                setattr(user, field, data[field])

        return self.user_repo.update_profile(user)

    def delete_account(self, user_id):
        self.get_profile(user_id)
        return self.user_repo.delete(user_id)
