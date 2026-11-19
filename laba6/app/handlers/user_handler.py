from functools import wraps
from math import ceil

from flask import Blueprint, jsonify, request, session, url_for

from app.errors import ValidationError
from app.validators import parse_pagination, validate_user_payload


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return function(*args, **kwargs)

    return wrapper


def create_user_blueprint(user_service):
    bp = Blueprint('users', __name__)

    @bp.post('/users')
    def create_user():
        if not request.is_json:
            raise ValidationError('Invalid JSON', code='INVALID_JSON')

        data = request.get_json(silent=True)
        if data is None:
            raise ValidationError('Invalid JSON', code='INVALID_JSON')

        payload = validate_user_payload(data, with_password=True)

        user = user_service.create_user(
            payload['name'],
            payload['email'],
            payload['age'],
            payload['password'],
        )

        response = jsonify(user.to_public_dict())
        response.status_code = 201
        response.headers['Location'] = url_for(
            'users.get_user', user_id=user.id
        )
        return response

    @bp.get('/users/<int:user_id>')
    def get_user(user_id):
        user = user_service.get_user(user_id)
        return jsonify(user.to_public_dict()), 200

    @bp.get('/users')
    def list_users():
        page, limit = parse_pagination(request.args)
        users, total = user_service.list_users(page, limit)

        return jsonify(
            {
                'items': [user.to_public_dict() for user in users],
                'total': total,
                'page': page,
                'page_size': limit,
                'pages': max(1, ceil(total / limit)),
            }
        ), 200

    @bp.put('/users/<int:user_id>')
    def update_user(user_id):
        if not request.is_json:
            raise ValidationError('Invalid JSON', code='INVALID_JSON')

        data = request.get_json(silent=True)
        if data is None:
            raise ValidationError('Invalid JSON', code='INVALID_JSON')

        payload = validate_user_payload(data)

        user = user_service.update_user(
            user_id,
            payload['name'],
            payload['email'],
            payload['age'],
        )
        return jsonify(user.to_public_dict()), 200

    @bp.delete('/users/<int:user_id>')
    def delete_user(user_id):
        user_service.delete_user(user_id)
        return '', 204

    @bp.get('/profile')
    @login_required
    def get_profile():
        user = user_service.get_profile(session['user_id'])
        return jsonify(user.to_public_dict()), 200

    @bp.patch('/profile')
    @login_required
    def update_profile():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValidationError('Invalid JSON')

        user = user_service.update_profile(session['user_id'], data)
        return jsonify(
            {
                'message': 'Profile updated',
                'user': user.to_public_dict(),
            }
        ), 200

    @bp.delete('/account')
    @login_required
    def delete_account():
        user_service.delete_account(session['user_id'])
        session.clear()
        return '', 204

    return bp
