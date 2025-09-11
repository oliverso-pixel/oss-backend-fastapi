# app/models/pet_transfer.py
from sqlalchemy import Column, BigInteger, String, Text, DECIMAL, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class TransferStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class TransferType(str, enum.Enum):
    GIFT = "gift"
    SALE = "sale"
    ADOPTION = "adoption"
    OTHER = "other"

class PetTransferHistory(BaseModel):
    """寵物轉移歷史記錄表"""
    __tablename__ = "pet_transfer_history"
    
    id = Column(BigInteger, primary_key=True, index=True)
    pet_id = Column(BigInteger, ForeignKey("pets.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transfer_reason = Column(Text)
    transfer_type = Column(
        SQLEnum(TransferType, values_callable=lambda x: [e.value for e in x]),
        default=TransferType.OTHER,
        nullable=False
    )
    transfer_fee = Column(DECIMAL(10, 2))
    notes = Column(Text)
    status = Column(
        SQLEnum(TransferStatus, values_callable=lambda x: [e.value for e in x]),
        default=TransferStatus.PENDING,
        nullable=False,
        index=True
    )
    requested_at = Column(DateTime, nullable=False)
    responded_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # 關聯
    pet = relationship("Pet", backref="transfer_history")
    from_user = relationship("User", foreign_keys=[from_user_id], backref="sent_transfers")
    to_user = relationship("User", foreign_keys=[to_user_id], backref="received_transfers")

