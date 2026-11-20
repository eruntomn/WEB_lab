import time
import uuid

from flask import g, jsonify, request
from werkzeug.exceptions import HTTPException

from app.errors import (
    AppError,
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    InvalidJsonError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

# Соответствие доменных ошибок HTTP-статусам (HTTP-детали живут только в handlers)
HTTP_STATUS = {
    ValidationError: (400, 'Validation error'),
    InvalidJsonError: (400, 'Bad request'),
    UnauthorizedError: (401, 'Unauthorized'),
    ForbiddenError: (403, 'Forbidden'),
    NotFoundError: (404, 'Not found'),
    ConflictError: (409, 'Conflict'),
    BusinessRuleError: (409, 'Business rule violation'),
}


def error_response(status, error, code, message, details=None):
    body = {
        'error': error,
        'message': message,
        'code': code,
        'details': details or {},
        'request_id': g.get('request_id'),
    }
    return jsonify(body), status


def register_common(app, log):
    """Идентификатор запроса, логирование запросов и обработчики ошибок."""

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

    @app.errorhandler(AppError)
    def handle_app_error(exc):
        status, title = HTTP_STATUS.get(type(exc), (500, 'Internal error'))
        log.warning('%s: %s | details=%s', exc.code, exc.message, exc.details)
        return error_response(
            status, title, exc.code, exc.message, exc.details
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        code = exc.name.upper().replace(' ', '_')
        log.warning('HTTP %s %s: %s', exc.code, exc.name, request.path)
        return error_response(exc.code, exc.name, code, exc.description)

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        log.exception('Unhandled error on %s %s', request.method, request.path)
        return error_response(
            500,
            'Internal server error',
            'INTERNAL_ERROR',
            'Something went wrong. Please report the request_id.',
        )
