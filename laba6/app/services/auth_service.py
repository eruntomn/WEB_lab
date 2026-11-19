from datetime import UTC, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.errors import ConflictError, ValidationError
from app.models import User


class AuthService:
    def __init__(self, user_repo, log=None):
        self.user_repo = user_repo
        self.log = log

    def register(self, name, email, age, password):
        email = email.lower().strip()

        if self.user_repo.email_exists(email):
            raise ConflictError(
                'Email already exists',
                {'field': 'email'},
            )

        user = User(
            name=name,
            email=email,
            age=age,
            password_hash=generate_password_hash(password),
            created_at=datetime.now(UTC).isoformat(),
        )

        user = self.user_repo.save(user)

        if self.log:
            self.log.info('User registered: id=%s', user.id)

        return user

    def login(self, email, password):
        user = self.user_repo.find_by_email(email.lower().strip())

        if user is None or not check_password_hash(
            user.password_hash, password
        ):
            raise ValidationError('Invalid email or password')

        return user
