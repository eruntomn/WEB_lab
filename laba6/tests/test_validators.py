import pytest

from app.errors import ValidationError
from app.validators import parse_pagination, validate_user_payload

pytestmark = pytest.mark.unit

VALID = {
    'name': 'Anna',
    'email': 'anna@example.com',
    'age': 25,
    'password': 'Passw0rd123',
}


def errors_of(payload, with_password=True):
    """Вызывает валидатор, ожидая ошибку, и возвращает словарь details."""
    with pytest.raises(ValidationError) as exc_info:
        validate_user_payload(payload, with_password)
    return exc_info.value.details


# ------------------------------------------------ обычные сценарии
def test_valid_payload_returns_clean_data():
    clean = validate_user_payload(VALID, with_password=True)
    assert clean == VALID


def test_email_is_lowercased_and_name_is_stripped():
    payload = {**VALID, 'name': '  Anna  ', 'email': 'Anna@Example.COM'}
    clean = validate_user_payload(payload, with_password=True)
    assert clean['name'] == 'Anna'
    assert clean['email'] == 'anna@example.com'


def test_payload_without_password_is_valid_for_update():
    payload = {'name': 'Anna', 'email': 'anna@example.com', 'age': 25}
    clean = validate_user_payload(payload, with_password=False)
    assert 'password' not in clean


@pytest.mark.parametrize(
    'email', ['a@b.co', 'john.doe+tag@example.com', 'USER@EXAMPLE.COM']
)
def test_valid_emails_are_accepted(email):
    clean = validate_user_payload(
        {**VALID, 'email': email}, with_password=True
    )
    assert clean['email'] == email.lower()


# ------------------------------------------------ граничные сценарии
@pytest.mark.parametrize('age', [18, 120])
def test_age_boundaries_are_accepted(age):
    assert validate_user_payload({**VALID, 'age': age}, True)['age'] == age


@pytest.mark.parametrize('age', [17, 121, 0, -5])
def test_age_outside_range_is_rejected(age):
    assert (
        errors_of({**VALID, 'age': age})['age'] == 'Must be between 18 and 120'
    )


@pytest.mark.parametrize('name', ['Jo', 'J' * 50])
def test_name_length_boundaries_are_accepted(name):
    assert validate_user_payload({**VALID, 'name': name}, True)['name'] == name


@pytest.mark.parametrize('name', ['J', 'J' * 51])
def test_name_length_outside_range_is_rejected(name):
    expected = 'Length must be between 2 and 50 characters'
    assert errors_of({**VALID, 'name': name})['name'] == expected


@pytest.mark.parametrize(
    'password', ['Passw0rd', 'a1' + 'b' * 126]
)  # 8 и 128 символов
def test_password_length_boundaries_are_accepted(password):
    assert (
        validate_user_payload({**VALID, 'password': password}, True)[
            'password'
        ]
        == password
    )


@pytest.mark.parametrize(
    'password', ['short1', 'P' * 128 + '1']
)  # 6 и 129 символов
def test_password_length_outside_range_is_rejected(password):
    expected = 'Length must be between 8 and 128 characters'
    assert errors_of({**VALID, 'password': password})['password'] == expected


def test_pagination_defaults():
    assert parse_pagination({}) == (1, 10)


def test_pagination_valid_values():
    assert parse_pagination({'page': '2', 'limit': '50'}) == (2, 50)


@pytest.mark.parametrize('limit', ['1', '100'])
def test_pagination_limit_boundaries_are_accepted(limit):
    assert parse_pagination({'limit': limit})[1] == int(limit)


# ------------------------------------------------ ошибочные сценарии
@pytest.mark.parametrize(
    'age, message',
    [
        ('25', 'Must be an integer'),
        (25.5, 'Must be an integer'),
        (True, 'Must be an integer'),
        (None, 'Must not be null'),
    ],
)
def test_age_with_wrong_type_is_rejected(age, message):
    assert errors_of({**VALID, 'age': age})['age'] == message


@pytest.mark.parametrize('field', ['name', 'email', 'age', 'password'])
def test_missing_required_field_is_reported(field):
    payload = {k: v for k, v in VALID.items() if k != field}
    assert errors_of(payload)[field] == 'Field is required'


def test_null_empty_and_wrong_type_are_distinguished():
    assert errors_of({**VALID, 'name': None})['name'] == 'Must not be null'
    assert errors_of({**VALID, 'email': ''})['email'] == 'Must not be empty'
    assert errors_of({**VALID, 'name': '   '})['name'] == 'Must not be empty'
    assert errors_of({**VALID, 'name': 123})['name'] == 'Must be a string'


@pytest.mark.parametrize(
    'email',
    ['invalid-email', 'test@test', '@example.com', 'user name@example.com'],
)
def test_invalid_email_format_is_rejected(email):
    assert (
        errors_of({**VALID, 'email': email})['email'] == 'Invalid email format'
    )


def test_too_short_email_is_rejected_by_length():
    expected = 'Length must be between 5 and 254 characters'
    assert errors_of({**VALID, 'email': 'bad'})['email'] == expected


@pytest.mark.parametrize('password', ['password', '12345678'])
def test_password_without_letter_or_digit_is_rejected(password):
    expected = 'Must contain at least one letter and one digit'
    assert errors_of({**VALID, 'password': password})['password'] == expected


def test_unknown_field_is_rejected():
    assert errors_of({**VALID, 'role': 'admin'})['role'] == 'Unknown field'


def test_password_is_unknown_field_when_not_expected():
    payload = {
        'name': 'Anna',
        'email': 'anna@example.com',
        'age': 25,
        'password': 'Passw0rd123',
    }
    assert (
        errors_of(payload, with_password=False)['password'] == 'Unknown field'
    )


@pytest.mark.parametrize('payload', [[1, 2, 3], 'text', 42])
def test_non_object_body_is_rejected(payload):
    with pytest.raises(ValidationError, match='JSON object'):
        validate_user_payload(payload, with_password=True)


def test_all_errors_are_collected_at_once():
    payload = {
        'name': 'J',
        'email': 'invalid-email',
        'age': 15,
        'password': '123',
    }
    assert set(errors_of(payload)) == {'name', 'email', 'age', 'password'}


@pytest.mark.parametrize(
    'args, field',
    [
        ({'page': '0'}, 'page'),
        ({'page': 'abc'}, 'page'),
        ({'limit': '0'}, 'limit'),
        ({'limit': '101'}, 'limit'),
        ({'limit': '1.5'}, 'limit'),
    ],
)
def test_invalid_pagination_is_rejected(args, field):
    with pytest.raises(ValidationError) as exc_info:
        parse_pagination(args)
    assert field in exc_info.value.details


@pytest.mark.regression
def test_regression_zero_age_is_a_range_error_not_a_missing_field():
    """Баг: 0 принимался за «поле отсутствует». Ноль это обычное число вне диапазона."""
    assert (
        errors_of({**VALID, 'age': 0})['age'] == 'Must be between 18 and 120'
    )
