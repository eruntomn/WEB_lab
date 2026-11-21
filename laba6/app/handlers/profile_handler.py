from flask import Blueprint, g, jsonify

from app.handlers.utils import get_json_body
from app.validators import validate_profile_payload


def profile_to_dict(user, profile):
    return {
        'user_id': user.id,
        'name': user.name,
        'bio': profile.bio if profile else None,
        'city': profile.city if profile else None,
        'updated_at': profile.updated_at if profile else None,
    }


def create_profile_blueprint(profile_service, login_required):
    bp = Blueprint('profiles', __name__)

    @bp.get('/users/<int:user_id>/profile')
    @login_required
    def get_profile(user_id):
        user, profile = profile_service.get_profile(user_id)
        return jsonify(profile_to_dict(user, profile))

    @bp.put('/users/<int:user_id>/profile')
    @login_required
    def put_profile(user_id):
        profile_service.ensure_owner(g.current_user.id, user_id)
        data = validate_profile_payload(get_json_body())
        user, profile = profile_service.save_profile(user_id, **data)
        return jsonify(profile_to_dict(user, profile))

    @bp.delete('/users/<int:user_id>/profile')
    @login_required
    def delete_profile(user_id):
        profile_service.ensure_owner(g.current_user.id, user_id)
        profile_service.delete_profile(user_id)
        return '', 204

    return bp
