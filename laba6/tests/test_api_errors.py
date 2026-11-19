import json

import pytest

pytestmark = pytest.mark.integration

ERROR_KEYS = {'error', 'message', 'code', 'details', 'request_id'}


def test_multiple_validation_errors_are_reported_together(client):
    payload = {
        'name': 'J',
        'email': 'invalid-email',
        'age': 15,
        'password': '123',
    }

    response = client.post('/users', json=payload)
    body = response.get_json()

    assert response.status_code == 400
    assert body['code'] == 'VALIDATION_ERROR'
    assert set(body['details']) == {'name', 'email', 'age', 'password'}


def test_missing_null_and_empty_fields_are_distinguished(client):
    response = client.post(
        '/users', json={'name': None, 'email': '', 'password': 'Passw0rd123'}
    )

    details = response.get_json()['details']
    assert details['name'] == 'Must not be null'
    assert details['email'] == 'Must not be empty'
    assert details['age'] == 'Field is required'


def test_invalid_json_returns_400(client):
    response = client.post(
        '/users', data='{bad json', content_type='application/json'
    )

    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_JSON'


def test_missing_content_type_returns_400(client, valid_user):
    response = client.post('/users', data=json.dumps(valid_user))

    assert response.status_code == 400
    assert response.get_json()['code'] == 'INVALID_JSON'


def test_json_array_instead_of_object_returns_400(client):
    response = client.post('/users', json=[1, 2, 3])

    assert response.status_code == 400
    assert response.get_json()['code'] == 'VALIDATION_ERROR'


def test_unknown_field_is_rejected(client, valid_user):
    response = client.post('/users', json={**valid_user, 'role': 'admin'})

    assert response.get_json()['details']['role'] == 'Unknown field'


def test_password_cannot_be_changed_via_put(client, create_user):
    create_user()

    response = client.put(
        '/users/1',
        json={
            'name': 'Anna',
            'email': 'anna@example.com',
            'age': 25,
            'password': 'NewPassw0rd1',
        },
    )

    assert response.status_code == 400
    assert response.get_json()['details']['password'] == 'Unknown field'


@pytest.mark.parametrize('query', ['page=0', 'page=abc', 'limit=abc'])
def test_invalid_query_parameters_return_400(client, query):
    assert client.get(f'/users?{query}').status_code == 400


def test_duplicate_email_returns_409(create_user):
    create_user()

    response = create_user(name='Other')

    assert response.status_code == 409
    assert response.get_json()['code'] == 'EMAIL_ALREADY_EXISTS'


@pytest.mark.regression
def test_regression_duplicate_email_check_ignores_case(create_user):
    create_user()

    assert create_user(email='ANNA@EXAMPLE.COM').status_code == 409


@pytest.mark.parametrize('domain', ['tempmail.com', 'mailinator.com'])
def test_disposable_domain_returns_409(create_user, domain):
    response = create_user(email=f'eva@{domain}')
    body = response.get_json()

    assert response.status_code == 409
    assert body['code'] == 'BUSINESS_RULE_VIOLATION'
    assert body['details']['domain'] == domain


def test_age_cannot_be_decreased(client, create_user):
    create_user(age=25)

    response = client.put(
        '/users/1',
        json={'name': 'Anna', 'email': 'anna@example.com', 'age': 20},
    )

    assert response.status_code == 409
    assert response.get_json()['details'] == {
        'field': 'age',
        'current': 25,
        'new': 20,
    }
    assert (
        client.get('/users/1').get_json()['age'] == 25
    )  # данные не изменились


def test_put_with_email_of_another_user_returns_409(client, create_user):
    create_user(email='a@example.com')
    create_user(email='b@example.com')

    response = client.put(
        '/users/2', json={'name': 'Boris', 'email': 'a@example.com', 'age': 25}
    )

    assert response.status_code == 409
    assert response.get_json()['code'] == 'EMAIL_ALREADY_EXISTS'


def test_put_keeping_own_email_is_allowed(client, create_user):
    create_user()

    response = client.put(
        '/users/1',
        json={'name': 'Anna Two', 'email': 'anna@example.com', 'age': 25},
    )

    assert response.status_code == 200


def test_get_unknown_user_returns_404(client):
    response = client.get('/users/999')
    body = response.get_json()

    assert response.status_code == 404
    assert body['code'] == 'NOT_FOUND'
    assert body['details'] == {'id': 999}


def test_update_unknown_user_returns_404(client):
    response = client.put(
        '/users/999',
        json={'name': 'Anna', 'email': 'anna@example.com', 'age': 25},
    )

    assert response.status_code == 404


def test_delete_unknown_user_returns_404(client):
    assert client.delete('/users/999').status_code == 404


def test_delete_twice_second_call_returns_404(client, create_user):
    create_user()

    assert client.delete('/users/1').status_code == 204
    assert client.delete('/users/1').status_code == 404


def test_unknown_route_returns_json_404(client):
    response = client.get('/nothing')

    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()['code'] == 'NOT_FOUND'


def test_unsupported_method_returns_405(client):
    response = client.patch('/users/1')

    assert response.status_code == 405
    assert response.get_json()['code'] == 'METHOD_NOT_ALLOWED'


def test_unexpected_error_returns_500_without_internal_details(debug_client):
    response = debug_client.get('/debug/crash')
    body = response.get_json()

    assert response.status_code == 500
    assert body['code'] == 'INTERNAL_ERROR'
    assert 'Intentional' not in response.get_data(as_text=True)
    assert 'RuntimeError' not in response.get_data(as_text=True)


def test_debug_route_is_disabled_by_default(client):
    assert client.get('/debug/crash').status_code == 404


def test_error_response_has_unified_structure(client):
    response = client.get('/users/999')
    body = response.get_json()

    assert set(body) == ERROR_KEYS
    assert body['request_id'] == response.headers['X-Request-ID']
