# app/models/social.py
from sqlalchemy import Column, BigInteger, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.core.database import Base

class Like(BaseModel):
    __tablename__ = "likes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    
    post = relationship("Post", back_populates="likes")

class Comment(BaseModel):
    __tablename__ = "comments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("comments.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    post = relationship("Post", back_populates="comments")

class PostTag(Base):
    __tablename__ = "post_tags"
    
    post_id = Column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    
    post = relationship("Post", back_populates="tags")

class Tag(BaseModel):
    __tablename__ = "tags"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    usage_count = Column(BigInteger, default=0)