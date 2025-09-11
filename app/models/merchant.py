# app/models/merchant.py
from sqlalchemy import Column, BigInteger, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON, DECIMAL
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class BusinessType(str, enum.Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"

class MerchantStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    REJECTED = "rejected"

class Merchant(BaseModel):
    __tablename__ = "merchants"
    
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    shop_name = Column(String(200), nullable=False)
    shop_slug = Column(String(100), unique=True, nullable=False)
    business_type = Column(Enum(BusinessType), nullable=False)
    business_registration_no = Column(String(100))
    tax_id = Column(String(50))
    description = Column(Text)
    logo_url = Column(String(500))
    banner_url = Column(String(500))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    business_hours = Column(JSON)
    address = Column(JSON)
    bank_account = Column(JSON)
    commission_rate = Column(DECIMAL(5, 2), default=10.00)
    status = Column(Enum(MerchantStatus), default=MerchantStatus.PENDING)
    verified_at = Column(DateTime)
    verified_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    rejection_reason = Column(Text)
    rating = Column(DECIMAL(3, 2), default=0.00)
    total_sales = Column(BigInteger, default=0)
    
    # 關聯
    user = relationship(
        "User", 
        foreign_keys=[user_id], 
        back_populates="merchant"
    )
    verifier = relationship(
        "User", 
        foreign_keys=[verified_by],
        back_populates="verified_merchants"
    )

