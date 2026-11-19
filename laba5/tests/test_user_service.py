from datetime import UTC, datetime
from unittest.mock import Mock, create_autospec, patch

import pytest

from app.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models import User
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.services.user_service import UserService

pytestmark = pytest.mark.unit

BLOCKED = frozenset({'tempmail.com', 'mailinator.com'})


def make_user(**overrides):
    data = {
        'id': 1,
        'name': 'Anna',
        'email': 'anna@example.com',
        'age': 25,
        'password_hash': 'hash',
        'created_at': '2026-01-01T00:00:00+00:00',
    }
    data.update(overrides)
    return User(**data)


def fake_save(user):
    user.id = 1
    return user


@pytest.fixture
def repo():
    mock = create_autospec(UserRepository, instance=True)
    mock.email_exists.return_value = False
    mock.save.side_effect = fake_save
    return mock


@pytest.fixture
def email_service():
    return create_autospec(EmailService, instance=True)


@pytest.fixture
def log():
    return Mock()


@pytest.fixture
def service(repo, email_service, log):
    return UserService(repo, email_service, BLOCKED, log)


def test_create_user_success(service, repo, email_service):
    # Act
    user = service.create_user('John', 'john@example.com', 25, 'Passw0rd123')

    # Assert
    assert user.id == 1
    assert user.name == 'John'
    assert user.email == 'john@example.com'
    repo.email_exists.assert_called_once_with('john@example.com', None)
    repo.save.assert_called_once()
    email_service.send_welcome.assert_called_once_with(user)


def test_create_user_hashes_password(service):
    user = service.create_user('John', 'john@example.com', 25, 'Passw0rd123')

    assert user.password_hash != 'Passw0rd123'
    assert user.password_hash.startswith('pbkdf2:sha256')


def test_create_user_logs_user_id(service, log):
    service.create_user('John', 'john@example.com', 25, 'Passw0rd123')

    log.info.assert_any_call('User created: id=%s', 1)


def test_create_user_sets_created_at_from_clock(service):
    with patch('app.services.user_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(
            2026, 1, 1, 12, 0, tzinfo=UTC
        )
        user = service.create_user(
            'John', 'john@example.com', 25, 'Passw0rd123'
        )

    assert user.created_at == '2026-01-01T12:00:00+00:00'


def test_get_user_returns_user_from_repository(service, repo):
    repo.find_by_id.return_value = make_user()

    user = service.get_user(1)

    assert user.name == 'Anna'
    repo.find_by_id.assert_called_once_with(1)


def test_list_users_calculates_offset_from_page(service, repo):
    repo.count.return_value = 25
    repo.find_page.return_value = []

    users, total = service.list_users(page=3, limit=10)

    assert total == 25
    assert users == []
    repo.find_page.assert_called_once_with(10, 20)


def test_update_user_success(service, repo):
    repo.find_by_id.return_value = make_user(age=25)

    user = service.update_user(1, 'Anna Smith', 'anna.smith@example.com', 26)

    assert (user.name, user.email, user.age) == (
        'Anna Smith',
        'anna.smith@example.com',
        26,
    )
    repo.email_exists.assert_called_once_with('anna.smith@example.com', 1)
    repo.update.assert_called_once_with(user)


def test_delete_user_calls_repository(service, repo):
    repo.find_by_id.return_value = make_user()

    service.delete_user(1)

    repo.delete.assert_called_once_with(1)


def test_update_user_same_age_is_allowed(service, repo):
    repo.find_by_id.return_value = make_user(age=25)

    user = service.update_user(1, 'Anna', 'anna@example.com', 25)

    assert user.age == 25


def test_update_user_age_one_less_is_rejected(service, repo):
    repo.find_by_id.return_value = make_user(age=25)
    with pytest.raises(BusinessRuleError):
        service.update_user(1, 'Anna', 'anna@example.com', 24)


def test_create_user_duplicate_email(service, repo, email_service):
    repo.email_exists.return_value = True

    with pytest.raises(ConflictError) as exc_info:
        service.create_user('John', 'john@example.com', 25, 'Passw0rd123')

    assert exc_info.value.code == 'EMAIL_ALREADY_EXISTS'
    repo.save.assert_not_called()
    email_service.send_welcome.assert_not_called()


@pytest.mark.parametrize('domain', ['tempmail.com', 'mailinator.com'])
def test_create_user_blocked_domain(service, repo, email_service, domain):
    with pytest.raises(BusinessRuleError) as exc_info:
        service.create_user('Eva', f'eva@{domain}', 30, 'Passw0rd123')

    assert exc_info.value.details['domain'] == domain
    repo.save.assert_not_called()
    email_service.send_welcome.assert_not_called()


def test_get_user_not_found(service, repo):
    repo.find_by_id.return_value = None

    with pytest.raises(NotFoundError) as exc_info:
        service.get_user(999)

    assert exc_info.value.details == {'id': 999}


def test_update_user_age_cannot_decrease(service, repo):
    repo.find_by_id.return_value = make_user(age=25)

    with pytest.raises(BusinessRuleError) as exc_info:
        service.update_user(1, 'Anna', 'anna@example.com', 20)

    assert exc_info.value.details == {'field': 'age', 'current': 25, 'new': 20}
    repo.update.assert_not_called()


def test_update_user_not_found(service, repo):
    repo.find_by_id.return_value = None

    with pytest.raises(NotFoundError):
        service.update_user(999, 'Anna', 'anna@example.com', 25)

    repo.update.assert_not_called()


def test_update_user_email_taken_by_another_user(service, repo):
    repo.find_by_id.return_value = make_user()
    repo.email_exists.return_value = True

    with pytest.raises(ConflictError):
        service.update_user(1, 'Anna', 'other@example.com', 25)

    repo.update.assert_not_called()


def test_delete_user_not_found(service, repo):
    repo.find_by_id.return_value = None

    with pytest.raises(NotFoundError):
        service.delete_user(999)

    repo.delete.assert_not_called()
