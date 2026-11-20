from functools import wraps

from flask import Blueprint, g, jsonify, make_response, request

from app.handlers.utils import get_json_body
from app.validators import validate_login_payload, validate_user_payload

COOKIE_NAME = 'session_id'


def create_login_required(auth_service):
    def login_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            g.current_user = auth_service.authenticate(
                request.cookies.get(COOKIE_NAME)
            )
            return view(*args, **kwargs)

        return wrapper

    return login_required


def create_auth_blueprint(
    auth_service, user_service, settings, login_required
):
    bp = Blueprint('auth', __name__)

    @bp.post('/auth/register')
    def register():
        data = validate_user_payload(get_json_body(), with_password=True)
        user = user_service.create_user(**data)
        response = jsonify(user.to_public_dict())
        response.status_code = 201
        response.headers['Location'] = f'/users/{user.id}/profile'
        return response

    @bp.post('/auth/login')
    def login():
        data = validate_login_payload(get_json_body())
        user, token = auth_service.login(data['email'], data['password'])
        response = jsonify(user.to_public_dict())
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=settings.session_ttl_seconds,
            httponly=True,
            secure=settings.cookie_secure,
            samesite='Lax',
            path='/',
        )
        return response

    @bp.post('/auth/logout')
    def logout():
        auth_service.logout(request.cookies.get(COOKIE_NAME))
        response = make_response('', 204)
        response.delete_cookie(COOKIE_NAME, path='/')
        return response

    @bp.get('/me')
    @login_required
    def me():
        return jsonify(g.current_user.to_public_dict())

    @bp.delete('/me')
    @login_required
    def delete_me():
        user_service.delete_user(g.current_user.id)
        response = make_response('', 204)
        response.delete_cookie(COOKIE_NAME, path='/')
        return response

    return bp
