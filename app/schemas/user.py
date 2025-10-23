# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, field_validator, validator
from typing import Optional, List
from datetime import date, datetime
from app.schemas.base import BaseSchema
from app.schemas.mixins import URLFieldMixin
from app.models.user import PrivacyLevel
from app.core.config import settings
import re

class UserBase(BaseSchema, URLFieldMixin):
    """用戶基礎 Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None
    background_image_url: Optional[str] = None

    class Config:
        from_attributes = True

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
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserUpdate(BaseSchema, URLFieldMixin):
    """更新用戶 Schema"""
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None
    background_image_url: Optional[str] = None
    birth_date: Optional[date] = None
    privacy_level: Optional[PrivacyLevel] = None
    show_email: Optional[bool] = None
    show_phone: Optional[bool] = None
    show_online_status: Optional[bool] = None
    show_last_seen: Optional[bool] = None

    class Config:
        from_attributes = True

class UserProfileStats(BaseSchema):
    """用戶個人資料頁面的統計數據"""
    total_posts: int
    total_following: int
    total_followers: int

class UserProfileBase(BaseSchema, URLFieldMixin):
    """所有個人資料視圖的基礎"""
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    background_image_url: Optional[str]
    bio: Optional[str]
    privacy_level: PrivacyLevel
    linked_roles: List[str]

    class Config:
        from_attributes = True

class UserPrivateProfile(UserProfileBase, UserProfileStats):
    """非好友看到的私密用戶資料"""
    pass

class UserPublicProfile(UserProfileBase, UserProfileStats):
    """公開用戶或好友看到的私密用戶資料"""
    created_at: datetime
    birth_date: Optional[date]

class UserFriendViewProfile(UserPublicProfile):
    """好友看到的私密用戶資料，包含共同好友"""
    mutual_friends: int

class UserFullResponse(UserPublicProfile):
    """完整資訊響應 - 自己或管理員可見"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]
    # privacy_level: str
    show_email: bool
    show_phone: bool
    show_online_status: bool
    show_last_seen: bool
    # roles: List[str] = []
    
    class Config:
        from_attributes = True

UserResponse = UserFullResponse

class PrivacySettings(BaseSchema):
    """隱私設置 Schema"""
    privacy_level: PrivacyLevel
    show_email: bool
    show_phone: bool
    show_online_status: bool
    show_last_seen: bool

class UserWithRoles(UserResponse):
    """包含角色的用戶 Schema"""
    roles: List[str] = []

