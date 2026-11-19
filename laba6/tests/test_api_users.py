import pytest

pytestmark = pytest.mark.integration


def test_create_user_returns_201_with_location(client, create_user):
    response = create_user()

    assert response.status_code == 201
    assert response.headers['Location'] == '/users/1'
    body = response.get_json()
    assert (body['id'], body['name'], body['email'], body['age']) == (
        1,
        'Anna',
        'anna@example.com',
        25,
    )
    assert 'created_at' in body


def test_get_user_returns_200(client, create_user):
    create_user()

    response = client.get('/users/1')

    assert response.status_code == 200
    assert response.get_json()['name'] == 'Anna'


def test_list_users_returns_page_structure(client, create_user):
    create_user(email='a@example.com')
    create_user(email='b@example.com')

    response = client.get('/users')
    body = response.get_json()

    assert response.status_code == 200
    assert (body['total'], body['page'], body['page_size'], body['pages']) == (
        2,
        1,
        10,
        1,
    )
    assert [u['email'] for u in body['items']] == [
        'a@example.com',
        'b@example.com',
    ]


def test_update_user_returns_200_and_saves_changes(client, create_user):
    create_user()

    response = client.put(
        '/users/1',
        json={
            'name': 'Anna Smith',
            'email': 'anna.smith@example.com',
            'age': 26,
        },
    )

    assert response.status_code == 200
    assert response.get_json()['name'] == 'Anna Smith'
    assert client.get('/users/1').get_json()['age'] == 26


def test_delete_user_returns_204_and_user_is_gone(client, create_user):
    create_user()

    response = client.delete('/users/1')

    assert response.status_code == 204
    assert response.data == b''
    assert client.get('/users/1').status_code == 404


def test_pagination_splits_items_between_pages(client, create_user):
    for i in range(3):
        create_user(email=f'user{i}@example.com')

    body = client.get('/users?page=2&limit=2').get_json()

    assert len(body['items']) == 1
    assert (body['total'], body['pages']) == (3, 2)


def test_email_is_saved_in_lowercase(create_user):
    response = create_user(email='Anna@Example.COM')

    assert response.get_json()['email'] == 'anna@example.com'


@pytest.mark.parametrize('age', [18, 120])
def test_age_boundaries_are_accepted(create_user, age):
    assert create_user(age=age).status_code == 201


@pytest.mark.parametrize('age', [17, 121, 0])
def test_age_outside_range_returns_400(create_user, age):
    response = create_user(age=age)

    assert response.status_code == 400
    assert (
        response.get_json()['details']['age'] == 'Must be between 18 and 120'
    )


@pytest.mark.parametrize(
    'name, status', [('Jo', 201), ('J' * 50, 201), ('J', 400), ('J' * 51, 400)]
)
def test_name_length_boundaries(create_user, name, status):
    assert create_user(name=name).status_code == status


@pytest.mark.parametrize('limit', [1, 100])
def test_list_accepts_boundary_limits(client, limit):
    assert client.get(f'/users?limit={limit}').status_code == 200


@pytest.mark.parametrize('limit', [0, 101])
def test_list_rejects_limits_outside_range(client, limit):
    response = client.get(f'/users?limit={limit}')

    assert response.status_code == 400
    assert 'limit' in response.get_json()['details']


def test_list_of_empty_database(client):
    body = client.get('/users').get_json()

    assert (body['items'], body['total'], body['pages']) == ([], 0, 1)


def test_update_with_same_age_is_allowed(client, create_user):
    create_user(age=25)

    response = client.put(
        '/users/1',
        json={'name': 'Anna', 'email': 'anna@example.com', 'age': 25},
    )

    assert response.status_code == 200


@pytest.mark.regression
def test_regression_password_is_never_returned(client, create_user):
    created = create_user()
    for response in (created, client.get('/users/1'), client.get('/users')):
        assert 'password' not in response.get_data(as_text=True)
