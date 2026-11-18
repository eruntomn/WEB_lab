class ApiError(Exception):
    """Базовая ошибка API: знает свой HTTP-статус и код."""

    status = 500
    error = 'Internal error'
    code = 'INTERNAL_ERROR'

    def __init__(self, message, details=None, code=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code:
            self.code = code


class InvalidJsonError(ApiError):
    status = 400
    error = 'Bad request'
    code = 'INVALID_JSON'


class ValidationError(ApiError):
    status = 400
    error = 'Validation error'
    code = 'VALIDATION_ERROR'


class NotFoundError(ApiError):
    status = 404
    error = 'Not found'
    code = 'NOT_FOUND'


class ConflictError(ApiError):
    status = 409
    error = 'Conflict'
    code = 'CONFLICT'


class BusinessRuleError(ApiError):
    status = 409
    error = 'Business rule violation'
    code = 'BUSINESS_RULE_VIOLATION'
