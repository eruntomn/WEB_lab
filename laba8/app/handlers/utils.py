from flask import request

from app.errors import InvalidJsonError


def get_json_body():
    data = request.get_json(silent=True)
    if data is None:
        raise InvalidJsonError(
            'Body must be valid JSON and Content-Type must be application/json'
        )
    return data
