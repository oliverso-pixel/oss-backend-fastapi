# app/models/social.py
from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, ForeignKey, Enum, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.core.database import Base
import enum

class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"

class Friendship(BaseModel):
    """好友關係表"""
    __tablename__ = "friendships"
    
    # 使用複合主鍵
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    friend_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING)
    accepted_at = Column(DateTime)
    
    # 關聯
    user = relationship("User", foreign_keys=[user_id], backref="friendships_initiated")
    friend = relationship("User", foreign_keys=[friend_id], backref="friendships_received")
    
    # 確保不能加自己為好友
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
    )

class Follow(BaseModel):
    """關注關係表"""
    __tablename__ = "follows"
    
    # 使用複合主鍵
    follower_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    # 關聯
    follower = relationship("User", foreign_keys=[follower_id], backref="following")
    following = relationship("User", foreign_keys=[following_id], backref="followers")

class Like(BaseModel):
    __tablename__ = "likes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    
    post = relationship("Post", back_populates="likes")

class Comment(BaseModel):
    """評論表"""
    __tablename__ = "comments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("comments.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    # 關聯
    user = relationship("User", backref="comments")
    post = relationship("Post", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="replies")

class Tag(BaseModel):
    """標籤表"""
    __tablename__ = "tags"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    usage_count = Column(BigInteger, default=0)
    
    # 關聯
    posts = relationship("PostTag", back_populates="tag")

class PostTag(Base):
    """貼文標籤關聯表"""
    __tablename__ = "post_tags"
    
    post_id = Column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    
    # 關聯
    post = relationship("Post", back_populates="tags")
    tag = relationship("Tag", back_populates="posts")

class ChatRoom(BaseModel):
    """聊天室表"""
    __tablename__ = "chat_rooms"
    
    id = Column(BigInteger, primary_key=True, index=True)
    type = Column(Enum('private', 'group'), default='private')
    name = Column(String(100))
    
    # 關聯
    members = relationship("ChatRoomMember", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")

class ChatRoomMember(Base):
    """聊天室成員表"""
    __tablename__ = "chat_room_members"
    
    room_id = Column(BigInteger, ForeignKey("chat_rooms.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(Enum('member', 'admin'), default='member')
    joined_at = Column(DateTime, server_default=func.now())
    last_read_at = Column(DateTime)
    
    # 關聯
    room = relationship("ChatRoom", back_populates="members")
    user = relationship("User", backref="chat_memberships")

class ChatMessage(BaseModel):
    """聊天訊息表"""
    __tablename__ = "chat_messages"
    
    id = Column(BigInteger, primary_key=True, index=True)
    room_id = Column(BigInteger, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    media_id = Column(BigInteger, ForeignKey("media.id", ondelete="SET NULL"))
    is_deleted = Column(Boolean, default=False)
    
    # 關聯
    room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", backref="sent_messages")
    media = relationship("Media")

class Notification(BaseModel):
    """通知表"""
    __tablename__ = "notifications"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(200))
    content = Column(Text)
    data = Column(Text)  # JSON 格式的額外數據
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    # 關聯
    user = relationship("User", backref="notifications")