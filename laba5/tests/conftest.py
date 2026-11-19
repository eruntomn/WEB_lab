import logging

import pytest

from app import create_app
from app.config import Settings

VALID_USER = {
    'name': 'Anna',
    'email': 'anna@example.com',
    'age': 25,
    'password': 'Passw0rd123',
}


@pytest.fixture
def make_app(tmp_path):
    """Фабрика приложения с временной базой данных и временным логом."""

    def _make(**overrides):
        values = {
            'host': '127.0.0.1',
            'port': 5000,
            'db_path': str(tmp_path / 'test.db'),
            'log_level': 'WARNING',
            'log_file': str(tmp_path / 'logs' / 'test.log'),
            'blocked_email_domains': frozenset(
                {'tempmail.com', 'mailinator.com'}
            ),
            'enable_debug_routes': False,
        }
        values.update(overrides)
        return create_app(Settings(**values))

    yield _make
    for handler in logging.getLogger('api').handlers:
        handler.close()  # освобождаем лог-файл (важно для Windows)


@pytest.fixture
def client(make_app):
    return make_app().test_client()


@pytest.fixture
def debug_client(make_app):
    return make_app(enable_debug_routes=True).test_client()


@pytest.fixture
def valid_user():
    return dict(VALID_USER)


@pytest.fixture
def create_user(client):
    """Создаёт пользователя через API; поля можно переопределить."""

    def _create(**overrides):
        return client.post('/users', json={**VALID_USER, **overrides})

    return _create
