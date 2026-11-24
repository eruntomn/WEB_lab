from dataclasses import dataclass


@dataclass
class User:
    name: str
    email: str
    age: int
    password_hash: str
    created_at: str
    id: int | None = None
    last_login_at: str | None = None
    role: str = 'user'

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            name=row['name'],
            email=row['email'],
            age=row['age'],
            password_hash=row['password_hash'],
            created_at=row['created_at'],
            last_login_at=row['last_login_at'],
            role=row['role'],
        )

    def to_public_dict(self):
        """Данные для клиента: без хэша пароля и других секретов."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'age': self.age,
            'role': self.role,
            'created_at': self.created_at,
            'last_login_at': self.last_login_at,
        }


@dataclass
class Session:
    id: str  # SHA-256 хэш токена, сам токен в базе не хранится
    user_id: int
    created_at: int
    expires_at: int
    csrf_token: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            created_at=row['created_at'],
            expires_at=row['expires_at'],
            csrf_token=row['csrf_token'],
        )


@dataclass
class Profile:
    user_id: int
    bio: str | None
    city: str | None
    updated_at: str

    @classmethod
    def from_row(cls, row):
        return cls(
            user_id=row['user_id'],
            bio=row['bio'],
            city=row['city'],
            updated_at=row['updated_at'],
        )
