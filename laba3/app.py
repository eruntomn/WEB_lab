import logging
import math
import os
import time
import uuid
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, g, has_request_context, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from errors import (
    ApiError,
    BusinessRuleError,
    ConflictError,
    InvalidJsonError,
    NotFoundError,
)
from validators import parse_pagination, validate_user_payload

app = Flask(__name__)
app.json.sort_keys = False

users = {}  # id -> пользователь (хранилище в памяти)
next_id = 1

BLOCKED_EMAIL_DOMAINS = {'tempmail.com', 'mailinator.com'}


# ---------------------------------------------------------------- логирование
class RequestIdFilter(logging.Filter):
    """Добавляет в каждую строку лога идентификатор запроса."""

    def filter(self, record):
        record.request_id = (
            g.get('request_id', '-') if has_request_context() else '-'
        )
        return True


def setup_logging():
    level = os.getenv('LOG_LEVEL', 'INFO').upper()
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(request_id)s] %(message)s'
    )
    os.makedirs('logs', exist_ok=True)
    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(
            'logs/app.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8'
        ),
    ]
    logger = logging.getLogger('api')
    logger.handlers = []
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    logging.getLogger('werkzeug').setLevel(
        logging.WARNING
    )  # свои логи вместо стандартных
    return logger


log = setup_logging()


@app.before_request
def start_request():
    g.request_id = uuid.uuid4().hex[:8]
    g.started = time.perf_counter()


@app.after_request
def finish_request(response):
    elapsed_ms = (time.perf_counter() - g.started) * 1000
    response.headers['X-Request-ID'] = g.request_id
    log.info(
        '%s %s -> %s (%.1f ms)',
        request.method,
        request.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ------------------------------------------------------- обработка ошибок
def error_response(status, error, code, message, details=None):
    """Единый контракт ошибки (слайд 7 лекции 4)."""
    body = {
        'error': error,
        'message': message,
        'code': code,
        'details': details or {},
        'request_id': g.get('request_id'),
    }
    return jsonify(body), status


@app.errorhandler(ApiError)
def handle_api_error(exc):
    # Ожидаемые ошибки клиента (4xx): предупреждение без стека.
    log.warning('%s: %s | details=%s', exc.code, exc.message, exc.details)
    return error_response(
        exc.status, exc.error, exc.code, exc.message, exc.details
    )


@app.errorhandler(HTTPException)
def handle_http_exception(exc):
    # 404 неизвестного маршрута, 405 неверного метода и т.п.
    code = exc.name.upper().replace(' ', '_')
    log.warning('HTTP %s %s: %s', exc.code, exc.name, request.path)
    return error_response(exc.code, exc.name, code, exc.description)


@app.errorhandler(Exception)
def handle_unexpected(exc):
    # Неожиданные сбои (5xx): полный стек в лог, клиенту только общее сообщение.
    log.exception('Unhandled error on %s %s', request.method, request.path)
    return error_response(
        500,
        'Internal server error',
        'INTERNAL_ERROR',
        'Something went wrong. Please report the request_id.',
    )


# --------------------------------------------------------------- вспомогательное
def now_iso():
    return datetime.now(UTC).isoformat(timespec='seconds')


def public(user):
    """Пользователь без секретных полей."""
    return {k: v for k, v in user.items() if k != 'password_hash'}


def get_json_body():
    data = request.get_json(silent=True)
    if data is None:
        raise InvalidJsonError(
            'Body must be valid JSON and Content-Type must be application/json'
        )
    return data


def get_user_or_404(user_id):
    user = users.get(user_id)
    if user is None:
        raise NotFoundError(f'User {user_id} not found', {'id': user_id})
    return user


def check_business_rules(email, exclude_id=None):
    """Бизнес-правила (в отличие от проверки формата зависят от состояния системы)."""
    domain = email.split('@')[1]
    if domain in BLOCKED_EMAIL_DOMAINS:
        raise BusinessRuleError(
            'Registration with disposable email domains is not allowed',
            {'field': 'email', 'domain': domain},
        )
    for user in users.values():
        if user['email'] == email and user['id'] != exclude_id:
            raise ConflictError(
                'Email already exists',
                {'field': 'email', 'value': email},
                code='EMAIL_ALREADY_EXISTS',
            )


# --------------------------------------------------------------------- маршруты
@app.get('/users')
def list_users():
    page, limit = parse_pagination(request.args)
    items = sorted(users.values(), key=lambda u: u['id'])
    total = len(items)
    start = (page - 1) * limit
    return jsonify(
        {
            'items': [public(u) for u in items[start : start + limit]],
            'total': total,
            'page': page,
            'page_size': limit,
            'pages': max(1, math.ceil(total / limit)),
        }
    )


@app.post('/users')
def create_user():
    global next_id
    clean = validate_user_payload(
        get_json_body(), with_password=True
    )  # формат
    check_business_rules(clean['email'])  # бизнес-правила

    password = clean.pop('password')
    user = {
        'id': next_id,
        **clean,
        'password_hash': generate_password_hash(
            password, method='pbkdf2:sha256'
        ),
        'created_at': now_iso(),
    }
    users[next_id] = user
    next_id += 1
    log.info(
        'User created: id=%s', user['id']
    )  # пароль и email в лог не пишем

    response = jsonify(public(user))
    response.status_code = 201
    response.headers['Location'] = f'/users/{user["id"]}'
    return response


@app.get('/users/<int:user_id>')
def get_user(user_id):
    return jsonify(public(get_user_or_404(user_id)))


@app.put('/users/<int:user_id>')
def update_user(user_id):
    user = get_user_or_404(user_id)
    clean = validate_user_payload(get_json_body(), with_password=False)
    check_business_rules(clean['email'], exclude_id=user_id)
    if clean['age'] < user['age']:
        raise BusinessRuleError(
            'Age cannot be decreased',
            {'field': 'age', 'current': user['age'], 'new': clean['age']},
        )
    user.update(clean)
    log.info('User updated: id=%s', user_id)
    return jsonify(public(user))


@app.delete('/users/<int:user_id>')
def delete_user(user_id):
    get_user_or_404(user_id)
    del users[user_id]
    log.info('User deleted: id=%s', user_id)
    return '', 204


# Только для демонстрации обработки 5xx; включается переменной окружения.
if os.getenv('ENABLE_DEBUG_ROUTES') == '1':

    @app.get('/debug/crash')
    def debug_crash():
        raise RuntimeError('Intentional crash for error-handling demo')


if __name__ == '__main__':
    log.info('Starting API (log level %s)', logging.getLevelName(log.level))
    app.run(host='0.0.0.0', port=5000)
