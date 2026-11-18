import re

from app.errors import ValidationError

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')

NAME_MIN, NAME_MAX = 2, 50
EMAIL_MIN, EMAIL_MAX = 5, 254
AGE_MIN, AGE_MAX = 18, 120
PASSWORD_MIN, PASSWORD_MAX = 8, 128


def _get_string(data, field, errors, min_len, max_len, strip=True):
    """Проверяет строковое поле. Отличает: нет поля / null / не строка / пустая строка."""
    if field not in data:
        errors[field] = 'Field is required'
        return None
    value = data[field]
    if value is None:
        errors[field] = 'Must not be null'
        return None
    if not isinstance(value, str):
        errors[field] = 'Must be a string'
        return None
    if strip:
        value = value.strip()
    if value == '':
        errors[field] = 'Must not be empty'
        return None
    if not min_len <= len(value) <= max_len:
        errors[field] = (
            f'Length must be between {min_len} and {max_len} characters'
        )
        return None
    return value


def validate_user_payload(data, with_password):
    """Проверка формата тела запроса. Возвращает очищенные данные или бросает ValidationError."""
    if not isinstance(data, dict):
        raise ValidationError('Request body must be a JSON object')

    errors = {}

    allowed = {'name', 'email', 'age'}
    if with_password:
        allowed.add('password')
    for field in data:
        if field not in allowed:
            errors[field] = 'Unknown field'

    name = _get_string(data, 'name', errors, NAME_MIN, NAME_MAX)

    email = _get_string(data, 'email', errors, EMAIL_MIN, EMAIL_MAX)
    if email is not None:
        email = email.lower()
        if not EMAIL_RE.match(email):
            errors['email'] = 'Invalid email format'

    age = None
    if 'age' not in data:
        errors['age'] = 'Field is required'
    elif data['age'] is None:
        errors['age'] = 'Must not be null'
    elif isinstance(data['age'], bool) or not isinstance(data['age'], int):
        errors['age'] = 'Must be an integer'
    elif not AGE_MIN <= data['age'] <= AGE_MAX:
        errors['age'] = f'Must be between {AGE_MIN} and {AGE_MAX}'
    else:
        age = data['age']

    password = None
    if with_password:
        password = _get_string(
            data, 'password', errors, PASSWORD_MIN, PASSWORD_MAX, strip=False
        )
        if password is not None and not (
            re.search(r'[A-Za-z]', password) and re.search(r'\d', password)
        ):
            errors['password'] = (
                'Must contain at least one letter and one digit'
            )

    if errors:
        raise ValidationError('Request validation failed', details=errors)

    clean = {'name': name, 'email': email, 'age': age}
    if with_password:
        clean['password'] = password
    return clean


def _parse_int(args, name, default, minimum, maximum, errors):
    raw = args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        errors[name] = 'Must be an integer'
        return default
    if not minimum <= value <= maximum:
        errors[name] = f'Must be between {minimum} and {maximum}'
        return default
    return value


def parse_pagination(args):
    """Параметры страницы списка: page >= 1, limit от 1 до 100."""
    errors = {}
    page = _parse_int(args, 'page', 1, 1, 100000, errors)
    limit = _parse_int(args, 'limit', 10, 1, 100, errors)
    if errors:
        raise ValidationError('Invalid query parameters', details=errors)
    return page, limit
