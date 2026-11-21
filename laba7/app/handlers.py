import time
import uuid
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import HTTPException

from app.db import get_stats, reset_stats
from app.errors import AppError, ValidationError


def error_response(status, error, code, message, details=None):
    body = {
        'error': error,
        'message': message,
        'code': code,
        'details': details or {},
        'request_id': g.get('request_id'),
    }
    return jsonify(body), status


def register_common(app, log, settings):

    @app.before_request
    def start_request():
        g.request_id = uuid.uuid4().hex[:8]
        g.started = time.perf_counter()
        reset_stats()

    @app.after_request
    def finish_request(response):
        elapsed_ms = (time.perf_counter() - g.started) * 1000
        stats = get_stats()
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-DB-Queries'] = str(stats['queries'])
        response.headers['X-DB-Time-Ms'] = str(stats['time_ms'])
        log.info(
            '[%s] %s %s -> %s (%.1f ms, %s queries)',
            g.request_id,
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
            stats['queries'],
        )
        if stats['queries'] > settings.query_warn_threshold:
            log.warning(
                '[%s] Possible N+1 problem: %s SQL queries for one request %s %s',
                g.request_id,
                stats['queries'],
                request.method,
                request.path,
            )
        return response

    @app.errorhandler(AppError)
    def handle_app_error(exc):
        log.warning('%s: %s | details=%s', exc.code, exc.message, exc.details)
        return error_response(
            exc.status, exc.error, exc.code, exc.message, exc.details
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        code = exc.name.upper().replace(' ', '_')
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


def get_json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError(
            'Body must be a JSON object with Content-Type: application/json'
        )
    return data


def int_field(data, name, minimum):
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(
            'Request validation failed', {name: 'Must be an integer'}
        )
    if value < minimum:
        raise ValidationError(
            'Request validation failed', {name: f'Must be >= {minimum}'}
        )
    return value


def str_field(data, name, min_len, max_len):
    value = data.get(name)
    if not isinstance(value, str):
        raise ValidationError(
            'Request validation failed', {name: 'Must be a string'}
        )
    value = value.strip()
    if not min_len <= len(value) <= max_len:
        raise ValidationError(
            'Request validation failed',
            {
                name: f'Length must be between {min_len} and {max_len} characters'
            },
        )
    return value


def amount_field(data):
    value = data.get('amount')
    message = (
        'Must be a positive number up to 1000000 with at most 2 decimal places'
    )
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValidationError('Request validation failed', {'amount': message})
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError('Request validation failed', {'amount': message})
    if (
        not amount.is_finite()
        or amount <= 0
        or amount > Decimal(1000000)
        or amount.as_tuple().exponent < -2
    ):
        raise ValidationError('Request validation failed', {'amount': message})
    return amount


def query_int(name, default, minimum, maximum):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError(
            'Invalid query parameters', {name: 'Must be an integer'}
        )
    if not minimum <= value <= maximum:
        raise ValidationError(
            'Invalid query parameters',
            {name: f'Must be between {minimum} and {maximum}'},
        )
    return value


def create_blueprint(transfer_service, registration_service, course_service):
    bp = Blueprint('api', __name__)

    @bp.get('/accounts')
    def accounts():
        return jsonify({'items': transfer_service.list_accounts()})

    @bp.post('/transfers')
    def create_transfer():
        data = get_json_object()
        result = transfer_service.transfer(
            int_field(data, 'from_account', 1),
            int_field(data, 'to_account', 1),
            amount_field(data),
        )
        return jsonify(result), 201

    @bp.get('/courses')
    def list_courses():
        mode = request.args.get('mode', 'joined')
        if mode not in ('naive', 'joined'):
            raise ValidationError(
                'Invalid query parameters',
                {'mode': 'Must be one of: naive, joined'},
            )
        limit = query_int('limit', 20, 1, 200)
        items = course_service.list_with_students(limit, mode)
        stats = get_stats()
        return jsonify(
            {
                'mode': mode,
                'limit': limit,
                'db_queries': stats['queries'],
                'db_time_ms': stats['time_ms'],
                'items': items,
            }
        )

    @bp.get('/courses/<int:course_id>')
    def get_course(course_id):
        return jsonify(course_service.get_course(course_id))

    @bp.put('/courses/<int:course_id>')
    def update_course(course_id):
        data = get_json_object()
        course = course_service.update_course(
            course_id,
            str_field(data, 'title', 1, 100),
            int_field(data, 'version', 0),
        )
        return jsonify(course)

    @bp.post('/courses/<int:course_id>/register')
    def register(course_id):
        strategy = request.args.get('strategy', 'atomic')
        data = get_json_object()
        result = registration_service.register(
            strategy, course_id, int_field(data, 'user_id', 1)
        )
        return jsonify({**result, 'strategy': strategy}), 201

    return bp
