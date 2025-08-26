# app/models/audit.py
from sqlalchemy import Column, BigInteger, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), index=True)
    resource_id = Column(BigInteger, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())