# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
import re

class UserBase(BaseSchema):
    """用戶基礎 Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    """創建用戶 Schema"""
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers and underscores')
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class UserUpdate(BaseSchema):
    """更新用戶 Schema"""
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None

class UserInDB(UserBase, TimestampSchema):
    """資料庫中的用戶 Schema"""
    id: int
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]

class UserResponse(UserInDB):
    """用戶響應 Schema"""
    pass

class UserWithRoles(UserResponse):
    """包含角色的用戶 Schema"""
    roles: List[str] = []