# app/models/social.py
from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, JSON, ForeignKey, Enum as SQLAlchemyEnum, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.core.database import Base
import enum

class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"

class ChatRoomType(str, enum.Enum):
    PRIVATE = 'private'
    GROUP = 'group'

class RoleType(str, enum.Enum):
    MEMBER = 'member'
    ADMIN = 'admin'

class Friendship(Base):
    """好友關係表"""
    __tablename__ = "friendships"
    
    id = Column(BigInteger, primary_key=True, index=True)  # 添加 ID 欄位
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLAlchemyEnum(FriendshipStatus, values_callable=lambda x: [e.value for e in x]), default=FriendshipStatus.PENDING, index=True)
    message = Column(Text)  # 好友請求訊息
    accepted_at = Column(DateTime)
    rejected_at = Column(DateTime)  # 拒絕時間
    rejection_reason = Column(Text)  # 拒絕原因
    reason = Column(Text)  # 封鎖原因（當 status = BLOCKED 時使用）
    created_at = Column(DateTime, nullable=False, server_default=func.now()) 
    
    # 關聯
    user = relationship("User", foreign_keys=[user_id], backref="friendships_initiated")
    friend = relationship("User", foreign_keys=[friend_id], backref="friendships_received")
    
    # 唯一約束
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
    )

class Follow(Base):
    """關注關係表"""
    __tablename__ = "follows"
    
    # 使用複合主鍵
    follower_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

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
    type = Column(SQLAlchemyEnum(ChatRoomType, values_callable=lambda x: [e.value for e in x]), default='private') 
    name = Column(String(100))
    
    # 關聯
    members = relationship("ChatRoomMember", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")

class ChatRoomMember(Base):
    """聊天室成員表"""
    __tablename__ = "chat_room_members"
    
    room_id = Column(BigInteger, ForeignKey("chat_rooms.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(SQLAlchemyEnum(RoleType, values_callable=lambda x: [e.value for e in x]), default='member') 
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
    data = Column(JSON)  # JSON 格式的額外數據
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    # 關聯
    user = relationship("User", backref="notifications")

