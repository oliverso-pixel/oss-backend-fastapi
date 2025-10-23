# app/core/exceptions.py
from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class TokenExpiredException(HTTPException):
    def __init__(self, headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers=headers or {"WWW-Authenticate": "Bearer"}
        )

class InvalidTokenException(HTTPException):
    def __init__(self, detail: str = "Invalid token", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers or {"WWW-Authenticate": "Bearer"}
        )

class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials", headers: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers or {"WWW-Authenticate": "Bearer"}
        )

