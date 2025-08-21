# app/models/post.py
from sqlalchemy import Column, BigInteger, String, Text, Boolean, ForeignKey, Enum, DECIMAL
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class Visibility(str, enum.Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class Post(BaseModel):
    __tablename__ = "posts"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pet_id = Column(BigInteger, ForeignKey("pets.id", ondelete="SET NULL"))
    content = Column(Text)
    visibility = Column(Enum(Visibility), default=Visibility.PUBLIC)
    location = Column(String(255))
    latitude = Column(DECIMAL(10, 8))
    longitude = Column(DECIMAL(11, 8))
    view_count = Column(BigInteger, default=0)
    is_deleted = Column(Boolean, default=False)
    
    # 關聯
    author = relationship("User", back_populates="posts")
    pet = relationship("Pet", back_populates="posts")
    media = relationship("PostMedia", back_populates="post")
    tags = relationship("PostTag", back_populates="post")
    likes = relationship("Like", back_populates="post")
    comments = relationship("Comment", back_populates="post")