# app/models/base.py
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from app.core.database import Base

class TimestampMixin:
    """時間戳 Mixin"""
    @declared_attr
    def created_at(cls):
        return Column(
            DateTime, 
            nullable=False, 
            server_default=func.now(),
            default=func.now()
        )
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime, 
            nullable=False, 
            server_default=func.now(),
            default=func.now(),
            onupdate=func.now()
        )

class BaseModel(Base, TimestampMixin):
    """基礎模型類"""
    __abstract__ = True

    __table_args__ = {'extend_existing': True}
    
    def to_dict(self):
        """轉換為字典"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
