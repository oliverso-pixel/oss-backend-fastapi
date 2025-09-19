# app/models/user.py
from sqlalchemy import Column, BigInteger, String, Boolean, Date, DateTime, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class PrivacyLevel(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"

class User(BaseModel):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    background_image_url = Column(String(500))
    bio = Column(Text)
    birth_date = Column(Date)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(255))
    last_login_at = Column(DateTime)
    last_password_change = Column(DateTime)
    password_reset_token = Column(String(255))
    password_reset_expires = Column(DateTime)

    # 隱私設置
    privacy_level = Column(
        SQLAlchemyEnum(PrivacyLevel, values_callable=lambda x: [e.value for e in x]),
        default=PrivacyLevel.PUBLIC,
        nullable=False
    )
    show_email = Column(Boolean, default=False)
    show_phone = Column(Boolean, default=False)
    show_online_status = Column(Boolean, default=True)
    show_last_seen = Column(Boolean, default=True)
    # 關聯 - 明確指定外鍵和 primaryjoin
    pets = relationship("Pet", back_populates="owner", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    albums = relationship("Album", back_populates="owner", cascade="all, delete-orphan")
    roles = relationship(
        "UserRole", 
        primaryjoin="User.id==UserRole.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 作為分配者的角色關聯
    assigned_roles = relationship(
        "UserRole",
        primaryjoin="User.id==UserRole.assigned_by",
        back_populates="assigner"
    )
    
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")
    merchant = relationship(
        "Merchant", 
        primaryjoin="User.id==Merchant.user_id",
        back_populates="user", 
        uselist=False
    )
    # 作為驗證者的商戶
    verified_merchants = relationship(
        "Merchant",
        primaryjoin="User.id==Merchant.verified_by",
        back_populates="verifier"
    )

