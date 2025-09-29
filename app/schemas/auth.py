# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.schemas.base import BaseSchema

class Token(BaseSchema):
    """Token Schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    """Token 數據 Schema"""
    username: Optional[str] = None
    user_id: Optional[int] = None

class LoginRequest(BaseSchema):
    """登入請求 Schema"""
    username: str
    password: str

class RefreshTokenRequest(BaseSchema):
    """刷新 Token 請求 Schema"""
    refresh_token: str

class ChangePasswordRequest(BaseSchema):
    """修改密碼請求 Schema"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

class ResetPasswordRequest(BaseSchema):
    """重設密碼請求 Schema"""
    email: EmailStr

class ResetPasswordConfirm(BaseSchema):
    """確認重設密碼 Schema"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

class TokenPayload(BaseModel):
    sub: int  # user_id
    exp: Optional[int] = None

