from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class CustomException(HTTPException):
    """Base custom exception class"""
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class BadRequestException(CustomException):
    """400 Bad Request"""
    def __init__(self, detail: Any = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(CustomException):
    """401 Unauthorized"""
    def __init__(self, detail: Any = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(CustomException):
    """403 Forbidden"""
    def __init__(self, detail: Any = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundException(CustomException):
    """404 Not Found"""
    def __init__(self, detail: Any = "Not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class DuplicateValueException(CustomException):
    """409 Conflict - for duplicate values"""
    def __init__(self, detail: Any = "Duplicate value"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UnprocessableEntityException(CustomException):
    """422 Unprocessable Entity"""
    def __init__(self, detail: Any = "Unprocessable entity"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class RateLimitException(CustomException):
    """429 Too Many Requests"""
    def __init__(self, detail: Any = "Rate limit exceeded"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class InternalServerErrorException(CustomException):
    """500 Internal Server Error"""
    def __init__(self, detail: Any = "Internal server error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


