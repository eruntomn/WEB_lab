from datetime import UTC, datetime

from app.errors import ForbiddenError, NotFoundError
from app.models import Profile


class ProfileService:
    def __init__(self, user_repo, profile_repo, log):
        self.user_repo = user_repo
        self.profile_repo = profile_repo
        self.log = log

    def ensure_owner(self, current_user_id, user_id):
        if current_user_id != user_id:
            raise ForbiddenError(
                'You can modify only your own profile', {'user_id': user_id}
            )

    def get_profile(self, user_id):
        user = self.user_repo.find_by_id(user_id)
        if user is None:
            raise NotFoundError(f'User {user_id} not found', {'id': user_id})
        return user, self.profile_repo.get(user_id)

    def save_profile(self, user_id, bio, city):
        user = self.user_repo.find_by_id(user_id)
        profile = Profile(
            user_id=user_id,
            bio=bio,
            city=city,
            updated_at=datetime.now(UTC).isoformat(timespec='seconds'),
        )
        self.profile_repo.upsert(profile)
        self.log.info('Profile saved: user_id=%s', user_id)
        return user, profile

    def delete_profile(self, user_id):
        self.profile_repo.delete(user_id)
        self.log.info('Profile deleted: user_id=%s', user_id)
