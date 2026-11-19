from flask import Blueprint, jsonify, request, session

from app.errors import ValidationError
from app.validators import validate_user_payload


def create_auth_blueprint(auth_service):

    bp = Blueprint('auth', __name__, url_prefix='/auth')

    @bp.post('/register')
    def register():
        data = request.get_json(silent=True)

        if data is None:
            raise ValidationError('JSON body is required')

        data = validate_user_payload(data, with_password=True)

        user = auth_service.register(**data)

        return jsonify(
            {
                'message': 'Registration successful',
                'user': user.to_public_dict(),
            }
        ), 201

    @bp.post('/login')
    def login():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            raise ValidationError('JSON body is required')

        email = data.get('email')
        password = data.get('password')

        if not isinstance(email, str) or not isinstance(password, str):
            raise ValidationError('Email and password are required')

        user = auth_service.login(email, password)

        session.clear()
        session['user_id'] = user.id
        session.permanent = True

        return jsonify(
            {
                'message': 'Login successful',
                'user': user.to_public_dict(),
            }
        )

    @bp.post('/logout')
    def logout():
        session.clear()

        return jsonify({'message': 'Logout successful'})

    @bp.get('/me')
    def me():
        user_id = session.get('user_id')

        if user_id is None:
            return jsonify({'error': 'Unauthorized'}), 401

        user = auth_service.user_repo.find_by_id(user_id)

        if user is None:
            session.clear()
            return jsonify({'error': 'Unauthorized'}), 401

        return jsonify(user.to_public_dict())

    return bp
