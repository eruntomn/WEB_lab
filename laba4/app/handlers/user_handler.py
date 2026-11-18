import math

from flask import Blueprint, jsonify, request

from app.errors import InvalidJsonError
from app.validators import parse_pagination, validate_user_payload


def get_json_body():
    data = request.get_json(silent=True)
    if data is None:
        raise InvalidJsonError(
            'Body must be valid JSON and Content-Type must be application/json'
        )
    return data


def create_user_blueprint(user_service):

    bp = Blueprint('users', __name__)

    @bp.get('/users')
    def list_users():
        page, limit = parse_pagination(request.args)
        users, total = user_service.list_users(page, limit)
        return jsonify(
            {
                'items': [u.to_public_dict() for u in users],
                'total': total,
                'page': page,
                'page_size': limit,
                'pages': max(1, math.ceil(total / limit)),
            }
        )

    @bp.post('/users')
    def create_user():
        data = validate_user_payload(get_json_body(), with_password=True)
        user = user_service.create_user(**data)
        response = jsonify(user.to_public_dict())
        response.status_code = 201
        response.headers['Location'] = f'/users/{user.id}'
        return response

    @bp.get('/users/<int:user_id>')
    def get_user(user_id):
        return jsonify(user_service.get_user(user_id).to_public_dict())

    @bp.put('/users/<int:user_id>')
    def update_user(user_id):
        data = validate_user_payload(get_json_body(), with_password=False)
        user = user_service.update_user(user_id, **data)
        return jsonify(user.to_public_dict())

    @bp.delete('/users/<int:user_id>')
    def delete_user(user_id):
        user_service.delete_user(user_id)
        return '', 204

    return bp
