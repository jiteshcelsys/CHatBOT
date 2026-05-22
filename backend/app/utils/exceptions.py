"""
Typed HTTP exceptions that map to the ApiResponse.fail() envelope.
Raise these anywhere in route handlers or services; the exception
handler in main.py converts them to JSON automatically.
"""
from fastapi import HTTPException


class AppException(HTTPException):
    """Base class for all application-level HTTP errors."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found."):
        super().__init__(404, "NOT_FOUND", message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required."):
        super().__init__(401, "UNAUTHORIZED", message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(403, "FORBIDDEN", message)


class BadRequestException(AppException):
    def __init__(self, message: str = "Invalid request."):
        super().__init__(400, "BAD_REQUEST", message)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists."):
        super().__init__(409, "CONFLICT", message)
