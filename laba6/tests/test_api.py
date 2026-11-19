import pytest

from app import create_app
from app.config import Settings


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        host='127.0.0.1',
        port=5001,
        db_path=str(tmp_path / 'test.db'),
        secret_key='test-secret-key',
    )

    app = create_app(settings)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json['status'] == 'ok'


def test_register(client):
    response = client.post(
        '/auth/register',
        json={
            'name': 'Test User',
            'email': 'test@example.com',
            'age': 18,
            'password': 'TestPass123',
        },
    )

    assert response.status_code == 201
    assert response.json['message'] == 'Registration successful'


def test_login_and_profile(client):
    client.post(
        '/auth/register',
        json={
            'name': 'Test User',
            'email': 'test@example.com',
            'age': 18,
            'password': 'TestPass123',
        },
    )

    response = client.post(
        '/auth/login',
        json={'email': 'test@example.com', 'password': 'TestPass123'},
    )

    assert response.status_code == 200

    profile = client.get('/profile')

    assert profile.status_code == 200
    assert profile.json['email'] == 'test@example.com'


def test_profile_without_login(client):
    response = client.get('/profile')

    assert response.status_code == 401
