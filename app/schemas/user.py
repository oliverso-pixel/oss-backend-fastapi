# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.models.user import PrivacyLevel
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
    privacy_level: Optional[PrivacyLevel] = PrivacyLevel.PUBLIC
    
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
    privacy_level: Optional[PrivacyLevel] = None
    show_email: Optional[bool] = None
    show_phone: Optional[bool] = None
    show_online_status: Optional[bool] = None
    show_last_seen: Optional[bool] = None

class PrivacySettings(BaseSchema):
    """隱私設置 Schema"""
    privacy_level: PrivacyLevel
    show_email: bool
    show_phone: bool
    show_online_status: bool
    show_last_seen: bool

# 不同隱私級別的響應 Schema
class UserPublicResponse(BaseSchema):
    """公開資訊響應 - 最少資訊"""
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    created_at: datetime

class UserLimitedResponse(UserPublicResponse):
    """有限資訊響應 - 好友可見"""
    bio: Optional[str]
    last_seen: Optional[datetime] = None
    is_online: Optional[bool] = None
    
    class Config:
        from_attributes = True

class UserFullResponse(UserLimitedResponse):
    """完整資訊響應 - 自己或管理員可見"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]
    privacy_level: str
    show_email: bool
    show_phone: bool
    show_online_status: bool
    show_last_seen: bool
    roles: List[str] = []
    
    class Config:
        from_attributes = True

UserResponse = UserFullResponse

class UserWithRoles(UserResponse):
    """包含角色的用戶 Schema"""
    roles: List[str] = []

