# app/models/auth.py
from sqlalchemy import Column, BigInteger, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.core.database import Base
import enum

class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class Role(BaseModel):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100))
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    
    # 關聯
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

class Permission(BaseModel):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # 關聯
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

class UserRole(Base):
    __tablename__ = "user_roles"
    
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at = Column(DateTime, server_default=func.now())  # 如果需要時間戳，使用不同的欄位名稱
    
    # 關聯 - 明確指定外鍵
    user = relationship(
        "User", 
        foreign_keys=[user_id], 
        back_populates="roles",
        overlaps="assigned_roles"
    )
    role = relationship("Role", back_populates="users")
    assigner = relationship(
        "User", 
        foreign_keys=[assigned_by], 
        back_populates="assigned_roles",
        overlaps="roles"
    )

class RolePermission(Base):
    __tablename__ = "role_permissions"
    
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    
    # 關聯
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

class UserToken(BaseModel):
    __tablename__ = "user_tokens"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_type = Column(Enum(TokenType), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    jti = Column(String(255), index=True)
    device_info = Column(JSON)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # 關聯
    user = relationship("User", back_populates="tokens")

class TokenBlacklist(BaseModel):
    """Token 黑名單表 - 用於追蹤已撤銷的 tokens"""
    __tablename__ = "token_blacklist"
    
    id = Column(BigInteger, primary_key=True, index=True)
    jti = Column(String(255), nullable=False, unique=True, index=True)  # JWT ID
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)  # Token 原本的過期時間
    reason = Column(String(255))  # 撤銷原因
    blacklisted_at = Column(DateTime, server_default=func.now())  # 加入黑名單的時間
    blacklisted_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))  # 誰執行的撤銷
    
    # 關聯
    user = relationship("User", foreign_keys=[user_id], backref="blacklisted_tokens")
    blacklisted_by_user = relationship("User", foreign_keys=[blacklisted_by])
    
    # 添加索引以提高查詢效能
    __table_args__ = (
        UniqueConstraint('jti', name='uq_token_blacklist_jti'),
    )

