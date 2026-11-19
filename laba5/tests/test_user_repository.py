import sqlite3

import pytest

from app.db import Database
from app.models import User
from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.integration


def make_user(email='john@example.com', name='John', age=30):
    return User(
        name=name,
        email=email,
        age=age,
        password_hash='hash',
        created_at='2026-01-01T00:00:00+00:00',
    )


@pytest.fixture
def repo(tmp_path):
    return UserRepository(Database(str(tmp_path / 'test.db')))


def test_save_assigns_id_and_user_can_be_found(repo):
    saved = repo.save(make_user())

    assert saved.id is not None
    found = repo.find_by_id(saved.id)
    assert found.email == 'john@example.com'
    assert found.name == 'John'


def test_update_changes_are_persisted(repo):
    user = repo.save(make_user())
    user.name, user.age = 'Johnny', 31

    repo.update(user)

    saved = repo.find_by_id(user.id)
    assert (saved.name, saved.age) == ('Johnny', 31)


def test_delete_removes_user(repo):
    user = repo.save(make_user())

    assert repo.delete(user.id) is True
    assert repo.find_by_id(user.id) is None


def test_find_page_uses_limit_offset_and_id_order(repo):
    for i in range(5):
        repo.save(make_user(email=f'u{i}@example.com'))

    page = repo.find_page(limit=2, offset=2)

    assert [u.email for u in page] == ['u2@example.com', 'u3@example.com']
    assert repo.count() == 5


def test_data_persists_after_reopening_database(tmp_path):
    path = str(tmp_path / 'test.db')
    UserRepository(Database(path)).save(make_user())

    reopened = UserRepository(Database(path))

    assert reopened.count() == 1


def test_empty_table(repo):
    assert repo.count() == 0
    assert repo.find_page(limit=10, offset=0) == []


def test_email_exists_ignores_own_id(repo):
    user = repo.save(make_user())

    assert repo.email_exists('john@example.com') is True
    assert repo.email_exists('john@example.com', exclude_id=user.id) is False


def test_find_missing_user_returns_none(repo):
    assert repo.find_by_id(999) is None


def test_delete_missing_user_returns_false(repo):
    assert repo.delete(999) is False


def test_database_rejects_duplicate_email(repo):
    repo.save(make_user())

    with pytest.raises(sqlite3.IntegrityError):  # ограничение UNIQUE в таблице
        repo.save(make_user())


@pytest.mark.regression
def test_regression_values_are_not_interpreted_as_sql(repo):
    evil_name = "Robert'); DROP TABLE users;--"
    repo.save(make_user(name=evil_name))

    assert repo.count() == 1
    assert repo.find_by_id(1).name == evil_name
    assert repo.email_exists("' OR '1'='1") is False
