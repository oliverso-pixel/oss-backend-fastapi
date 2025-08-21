# app/models/audit.py
from sqlalchemy import Column, BigInteger, String, DateTime, JSON, Text
from app.models.base import BaseModel

class AuditLog(BaseModel):
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), index=True)
    resource_id = Column(BigInteger)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)