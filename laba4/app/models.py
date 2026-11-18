from dataclasses import dataclass


@dataclass
class User:
    name: str
    email: str
    age: int
    password_hash: str
    created_at: str
    id: int | None = None

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            name=row['name'],
            email=row['email'],
            age=row['age'],
            password_hash=row['password_hash'],
            created_at=row['created_at'],
        )

    def to_public_dict(self):
        """Представление для клиента (без хэша пароля)."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'age': self.age,
            'created_at': self.created_at,
        }
