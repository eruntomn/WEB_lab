class AppError(Exception):
    """Базовая доменная ошибка. HTTP-статусов здесь нет: их назначает слой handlers."""

    code = 'INTERNAL_ERROR'

    def __init__(self, message, details=None, code=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code:
            self.code = code


class InvalidJsonError(AppError):
    code = 'INVALID_JSON'


class ValidationError(AppError):
    code = 'VALIDATION_ERROR'


class NotFoundError(AppError):
    code = 'NOT_FOUND'


class ConflictError(AppError):
    code = 'CONFLICT'


class BusinessRuleError(AppError):
    code = 'BUSINESS_RULE_VIOLATION'


class UnauthorizedError(AppError):
    code = 'UNAUTHORIZED'


class ForbiddenError(AppError):
    code = 'FORBIDDEN'
