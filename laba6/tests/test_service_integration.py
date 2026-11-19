from unittest.mock import Mock

import pytest

from app.db import Database
from app.errors import ConflictError
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

pytestmark = pytest.mark.integration


@pytest.fixture
def parts(tmp_path):
    repo = UserRepository(Database(str(tmp_path / 'test.db')))
    email_service = Mock()
    service = UserService(
        repo, email_service, frozenset({'tempmail.com'}), Mock()
    )
    return service, repo, email_service


def test_create_user_is_saved_in_database(parts):
    service, repo, email_service = parts

    user = service.create_user('John', 'john@example.com', 25, 'Passw0rd123')

    assert user.id is not None
    saved = repo.find_by_id(user.id)
    assert saved.name == 'John'
    assert saved.password_hash != 'Passw0rd123'
    email_service.send_welcome.assert_called_once()


def test_duplicate_email_is_rejected_by_real_database_check(parts):
    service, repo, email_service = parts
    service.create_user('John', 'john@example.com', 25, 'Passw0rd123')

    with pytest.raises(ConflictError):
        service.create_user('Other', 'john@example.com', 30, 'Passw0rd123')

    assert repo.count() == 1
    assert email_service.send_welcome.call_count == 1


def test_update_user_changes_are_visible_in_database(parts):
    service, repo, _ = parts
    user = service.create_user('John', 'john@example.com', 25, 'Passw0rd123')

    service.update_user(user.id, 'Johnny', 'johnny@example.com', 26)

    saved = repo.find_by_id(user.id)
    assert (saved.name, saved.email, saved.age) == (
        'Johnny',
        'johnny@example.com',
        26,
    )
