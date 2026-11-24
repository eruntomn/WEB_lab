import base64
import hashlib
import secrets

import bcrypt

ROLE_PERMISSIONS = {
    'user': {'profile.read', 'profile.write'},
    'admin': {'profile.read', 'profile.write', 'users.read', 'users.delete'},
}


def _prepare(password):
    """bcrypt принимает не более 72 байт, поэтому пароль сначала сворачиваем
    в 44 символа (SHA-256 + base64)."""
    return base64.b64encode(hashlib.sha256(password.encode('utf-8')).digest())


def hash_password(password, rounds=12):
    """bcrypt: случайная соль и намеренно медленное хэширование."""
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds)).decode(
        'ascii'
    )


def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(
            _prepare(password), password_hash.encode('ascii')
        )
    except ValueError:
        return False


def new_csrf_token():
    return secrets.token_hex(16)


def has_permission(role, permission):
    return permission in ROLE_PERMISSIONS.get(role, set())
