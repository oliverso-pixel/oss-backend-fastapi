# app/schemas/token.py
from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: int  # user_id
    exp: Optional[int] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str