# app/models/media.py
from sqlalchemy import Column, BigInteger, String, Integer, Boolean, ForeignKey, Enum as SQLAlchemyEnum, DateTime, func, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.core.database import Base
import enum

class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"

class Media(Base):
    __tablename__ = "media"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    media_type = Column(
        SQLAlchemyEnum(MediaType, values_callable=lambda x: [e.value for e in x]), 
        nullable=False
    )
    width = Column(Integer)
    height = Column(Integer)
    duration = Column(Integer)
    thumbnail_path = Column(String(500))
    is_processed = Column(Boolean, default=False)
    extra_data = Column(JSON)  # 儲存額外資訊（如不同尺寸的路徑）
    hash = Column(String(64), index=True)  # 檔案 hash，用於去重
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    folder_type = Column(String(50))  # avatar, post, chat, etc.
    related_id = Column(BigInteger)   # 關聯的物件 ID
    is_public = Column(Boolean, default=True)  # 是否公開訪問
    deleted_at = Column(DateTime)  # 軟刪除

# 關聯表
class PostMedia(Base):
    __tablename__ = "post_media"
    
    post_id = Column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    media_id = Column(BigInteger, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    display_order = Column(Integer, default=0)
    
    post = relationship("Post", back_populates="media")
    media = relationship("Media")

class AlbumMedia(Base):
    __tablename__ = "album_media"
    
    album_id = Column(BigInteger, ForeignKey("albums.id", ondelete="CASCADE"), primary_key=True)
    media_id = Column(BigInteger, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    display_order = Column(Integer, default=0)
    
    album = relationship("Album", back_populates="media")
    media = relationship("Media")

