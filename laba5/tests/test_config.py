# tests/test_config.py
import pytest

from app.config import Settings

pytestmark = pytest.mark.unit

ENV_NAMES = [
    'APP_HOST',
    'APP_PORT',
    'DB_PATH',
    'LOG_LEVEL',
    'LOG_FILE',
    'BLOCKED_EMAIL_DOMAINS',
    'ENABLE_DEBUG_ROUTES',
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_settings_defaults():
    settings = Settings.from_env()

    assert settings.host == '0.0.0.0'
    assert settings.port == 5000
    assert settings.db_path == 'data/app.db'
    assert settings.log_level == 'INFO'
    assert settings.blocked_email_domains == frozenset(
        {'tempmail.com', 'mailinator.com'}
    )
    assert settings.enable_debug_routes is False


def test_settings_are_read_from_environment(monkeypatch):
    monkeypatch.setenv('APP_PORT', '8080')
    monkeypatch.setenv('LOG_LEVEL', 'debug')
    monkeypatch.setenv('BLOCKED_EMAIL_DOMAINS', ' A.com, b.org ,')
    monkeypatch.setenv('ENABLE_DEBUG_ROUTES', '1')

    settings = Settings.from_env()

    assert settings.port == 8080
    assert settings.log_level == 'DEBUG'
    assert settings.blocked_email_domains == frozenset({'a.com', 'b.org'})
    assert settings.enable_debug_routes is True


def test_invalid_port_fails_at_startup(monkeypatch):
    monkeypatch.setenv('APP_PORT', 'abc')

    with pytest.raises(ValueError):
        Settings.from_env()
