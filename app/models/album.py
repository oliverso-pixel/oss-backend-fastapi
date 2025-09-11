# app/models/album.py
from sqlalchemy import Column, BigInteger, String, Text, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.models.post import Visibility

class Album(BaseModel):
    __tablename__ = "albums"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pet_id = Column(BigInteger, ForeignKey("pets.id", ondelete="SET NULL"))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    cover_media_id = Column(BigInteger, ForeignKey("media.id", ondelete="SET NULL"))
    visibility = Column(Enum(Visibility), default=Visibility.PRIVATE)
    is_deleted = Column(Boolean, default=False)
    
    # 關聯
    owner = relationship("User", back_populates="albums")
    pet = relationship("Pet", back_populates="albums")
    media = relationship("AlbumMedia", back_populates="album")

