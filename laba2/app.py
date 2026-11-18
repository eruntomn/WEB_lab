import math
import re
from datetime import UTC, datetime

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.json.sort_keys = False  # поля в JSON идут в том порядке, как в коде

users = {}  # id -> пользователь
next_id = 1

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def error(status, message):
    """Единый формат ошибок."""
    return jsonify({'error': {'status': status, 'message': message}}), status


def validate_user(data):
    """Проверка тела запроса. Возвращает (данные, список ошибок)."""
    if not isinstance(data, dict):
        return None, ['body must be a JSON object']
    errors = []
    name = data.get('name')
    email = data.get('email')
    age = data.get('age')

    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 50:
        errors.append('name: required string, 2-50 characters')
    if not isinstance(email, str) or not EMAIL_RE.match(email.strip()):
        errors.append('email: required, must be a valid email address')
    if age is not None and (
        isinstance(age, bool)
        or not isinstance(age, int)
        or not 0 <= age <= 150
    ):
        errors.append('age: must be an integer between 0 and 150')

    if errors:
        return None, errors
    return {
        'name': name.strip(),
        'email': email.strip().lower(),
        'age': age,
    }, []


def email_taken(email, exclude_id=None):
    return any(
        u['email'] == email and u['id'] != exclude_id for u in users.values()
    )


@app.get('/')
def index():
    return jsonify(
        {'service': 'Users API', 'docs': '/docs', 'openapi': '/openapi.yaml'}
    )


# ---------- GET /users ----------
@app.get('/users')
def list_users():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        age_gt = request.args.get('age_gt')
        age_gt = int(age_gt) if age_gt is not None else None
    except ValueError:
        return error(400, 'page, limit and age_gt must be integers')
    if page < 1 or not 1 <= limit <= 100:
        return error(400, 'page must be >= 1, limit must be between 1 and 100')

    items = sorted(users.values(), key=lambda u: u['id'])
    if age_gt is not None:
        items = [
            u for u in items if u['age'] is not None and u['age'] > age_gt
        ]
    search = request.args.get('search')
    if search:
        items = [u for u in items if search.lower() in u['name'].lower()]

    total = len(items)
    start = (page - 1) * limit
    return jsonify(
        {
            'items': items[start : start + limit],
            'total': total,
            'page': page,
            'page_size': limit,
            'pages': max(1, math.ceil(total / limit)),
        }
    )


# ---------- POST /users ----------
@app.post('/users')
def create_user():
    global next_id
    data = request.get_json(silent=True)
    if data is None:
        return error(
            400, 'body must be valid JSON with Content-Type: application/json'
        )
    clean, errors = validate_user(data)
    if errors:
        return error(400, '; '.join(errors))
    if email_taken(clean['email']):
        return error(409, 'user with this email already exists')

    user = {
        'id': next_id,
        **clean,
        'created_at': datetime.now(UTC).isoformat(timespec='seconds'),
    }
    users[next_id] = user
    next_id += 1

    response = jsonify(user)
    response.status_code = 201
    response.headers['Location'] = f'/users/{user["id"]}'
    return response


# ---------- GET /users/{id} ----------
@app.get('/users/<int:user_id>')
def get_user(user_id):
    user = users.get(user_id)
    if user is None:
        return error(404, f'user {user_id} not found')
    return jsonify(user)


# ---------- PUT /users/{id} ----------
@app.put('/users/<int:user_id>')
def update_user(user_id):
    user = users.get(user_id)
    if user is None:
        return error(404, f'user {user_id} not found')
    data = request.get_json(silent=True)
    if data is None:
        return error(
            400, 'body must be valid JSON with Content-Type: application/json'
        )
    clean, errors = validate_user(data)
    if errors:
        return error(400, '; '.join(errors))
    if email_taken(clean['email'], exclude_id=user_id):
        return error(409, 'user with this email already exists')

    user.update(clean)  # id и created_at не меняются
    return jsonify(user)


# ---------- DELETE /users/{id} ----------
@app.delete('/users/<int:user_id>')
def delete_user(user_id):
    if user_id not in users:
        return error(404, f'user {user_id} not found')
    del users[user_id]
    return '', 204


# ---------- документация ----------
@app.get('/openapi.yaml')
def openapi_spec():
    return send_file('openapi.yaml', mimetype='application/yaml')


SWAGGER_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Users API docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
  <script>SwaggerUIBundle({ url: "/openapi.yaml", dom_id: "#swagger-ui" });</script>
</body>
</html>"""


@app.get('/docs')
def docs():
    return SWAGGER_HTML


# ---------- ошибки в JSON ----------
@app.errorhandler(404)
def handle_404(_):
    return error(404, 'resource not found')


@app.errorhandler(405)
def handle_405(_):
    return error(405, 'method not allowed')


@app.errorhandler(500)
def handle_500(_):
    return error(500, 'internal server error')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
