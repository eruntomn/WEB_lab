import secrets
from functools import wraps

from flask import Blueprint, g, jsonify, make_response, request

from app.errors import ForbiddenError
from app.handlers.utils import get_json_body
from app.security import has_permission
from app.validators import validate_login_payload, validate_user_payload

COOKIE_NAME = 'session_id'
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}


def create_auth_decorators(auth_service):
    def login_required(view):

        @wraps(view)
        def wrapper(*args, **kwargs):
            user, session = auth_service.authenticate(
                request.cookies.get(COOKIE_NAME)
            )
            g.current_user = user
            g.current_session = session
            if request.method not in SAFE_METHODS:
                sent = request.headers.get('X-CSRF-Token', '')
                if not secrets.compare_digest(
                    sent.encode('utf-8'), session.csrf_token.encode('utf-8')
                ):
                    raise ForbiddenError(
                        'CSRF token is missing or invalid', code='CSRF_FAILED'
                    )
            return view(*args, **kwargs)

        return wrapper

    def require_permission(permission):

        def decorator(view):
            @wraps(view)
            def wrapper(*args, **kwargs):
                if not has_permission(g.current_user.role, permission):
                    raise ForbiddenError(
                        'You do not have permission to perform this action',
                        {'required': permission},
                    )
                return view(*args, **kwargs)

            return login_required(wrapper)

        return decorator

    return login_required, require_permission


def create_auth_blueprint(
    auth_service, user_service, settings, login_required, require_permission
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
        user, token, csrf_token = auth_service.login(
            data['email'], data['password']
        )
        body = user.to_public_dict()
        body['csrf_token'] = csrf_token
        response = jsonify(body)
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=settings.session_ttl_seconds,
            httponly=True,
            secure=settings.cookie_secure,  # только по HTTPS
            samesite=settings.cookie_samesite,
            path='/',
        )
        return response

    @bp.post('/auth/logout')
    @login_required
    def logout():
        auth_service.logout(request.cookies.get(COOKIE_NAME))
        response = make_response('', 204)
        response.delete_cookie(COOKIE_NAME, path='/')
        return response

    @bp.get('/me')
    @login_required
    def me():
        body = g.current_user.to_public_dict()
        body['csrf_token'] = g.current_session.csrf_token
        return jsonify(body)

    @bp.delete('/me')
    @login_required
    def delete_me():
        user_service.delete_user(g.current_user.id)
        response = make_response('', 204)
        response.delete_cookie(COOKIE_NAME, path='/')
        return response

    @bp.get('/users')
    @require_permission('users.read')
    def list_users():
        users = user_service.list_users()
        return jsonify({'items': [u.to_public_dict() for u in users]})

    @bp.delete('/users/<int:user_id>')
    @require_permission('users.delete')
    def delete_user(user_id):
        user_service.delete_user(user_id)
        return '', 204

    return bp
