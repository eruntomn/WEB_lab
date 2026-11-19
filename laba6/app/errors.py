class ValidationError(Exception):
    def __init__(
        self,
        message='Validation error',
        details=None,
        code='VALIDATION_ERROR',
    ):
        super().__init__(message)
        self.details = details or {}
        self.code = code


class ConflictError(Exception):
    def __init__(self, message='Conflict', details=None, code=None):
        super().__init__(message)
        self.details = details or {}
        self.code = code


class NotFoundError(Exception):
    def __init__(self, message='Not found', details=None):
        super().__init__(message)
        self.details = details or {}


class BusinessRuleError(Exception):
    def __init__(self, message='Business rule violation', details=None):
        super().__init__(message)
        self.details = details or {}
