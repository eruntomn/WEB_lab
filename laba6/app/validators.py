import re

from app.errors import ValidationError


def validate_user_payload(data, with_password=False):
    if not isinstance(data, dict):
        raise ValidationError('Expected a JSON object')

    allowed = {'name', 'email', 'age'}
    if with_password:
        allowed.add('password')

    errors = {}

    for key in data:
        if key not in allowed:
            errors[key] = 'Unknown field'

    for key in allowed:
        if key not in data:
            errors[key] = 'Field is required'

    name = data.get('name')
    if 'name' in data:
        if name is None:
            errors['name'] = 'Must not be null'
        elif not isinstance(name, str):
            errors['name'] = 'Must be a string'
        elif not name.strip():
            errors['name'] = 'Must not be empty'
        elif not 2 <= len(name.strip()) <= 50:
            errors['name'] = 'Length must be between 2 and 50 characters'

    email = data.get('email')
    if 'email' in data:
        if email is None:
            errors['email'] = 'Must not be null'
        elif not isinstance(email, str):
            errors['email'] = 'Must be a string'
        elif not email:
            errors['email'] = 'Must not be empty'
        elif not 5 <= len(email) <= 254:
            errors['email'] = 'Length must be between 5 and 254 characters'
        elif not re.fullmatch(
            r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', email
        ):
            errors['email'] = 'Invalid email format'

    age = data.get('age')
    if 'age' in data:
        if age is None:
            errors['age'] = 'Must not be null'
        elif type(age) is not int:
            errors['age'] = 'Must be an integer'
        elif not 18 <= age <= 120:
            errors['age'] = 'Must be between 18 and 120'

    if with_password and 'password' in data:
        password = data['password']
        if password is None:
            errors['password'] = 'Must not be null'
        elif not isinstance(password, str):
            errors['password'] = 'Must be a string'
        elif not 8 <= len(password) <= 128:
            errors['password'] = 'Length must be between 8 and 128 characters'
        elif not (
            re.search(r'[A-Za-z]', password) and re.search(r'\d', password)
        ):
            errors['password'] = (
                'Must contain at least one letter and one digit'
            )

    if errors:
        raise ValidationError('Validation failed', errors)

    result = {
        'name': name.strip(),
        'email': email.lower().strip(),
        'age': age,
    }

    if with_password:
        result['password'] = data['password']

    return result


def parse_pagination(args):
    errors = {}

    try:
        page = int(args.get('page', 1))
        if page < 1:
            errors['page'] = 'Must be at least 1'
    except (TypeError, ValueError):
        page = 1
        errors['page'] = 'Must be an integer'

    try:
        limit = int(args.get('limit', 10))
        if not 1 <= limit <= 100:
            errors['limit'] = 'Must be between 1 and 100'
    except (TypeError, ValueError):
        limit = 10
        errors['limit'] = 'Must be an integer'

    if errors:
        raise ValidationError('Invalid pagination', errors)

    return page, limit
