class AppError(Exception):
    status = 500
    error = 'Internal error'
    code = 'INTERNAL_ERROR'

    def __init__(self, message, details=None, code=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code:
            self.code = code


class ValidationError(AppError):
    status = 400
    error = 'Validation error'
    code = 'VALIDATION_ERROR'


class NotFoundError(AppError):
    status = 404
    error = 'Not found'
    code = 'NOT_FOUND'


class ConflictError(AppError):
    status = 409
    error = 'Conflict'
    code = 'CONFLICT'


class BusinessRuleError(AppError):
    status = 409
    error = 'Business rule violation'
    code = 'BUSINESS_RULE_VIOLATION'
