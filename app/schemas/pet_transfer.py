# app/schemas/pet_transfer.py
from pydantic import BaseModel, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
from enum import Enum
from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.user import UserPublicProfile
from app.schemas.pet import PetResponse

class TransferStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class TransferType(str, Enum):
    GIFT = "gift"
    SALE = "sale"
    ADOPTION = "adoption"
    OTHER = "other"

class PetTransferRequest(BaseSchema):
    """寵物轉移請求"""
    to_user_id: int = Field(..., description="接收者用戶ID")
    transfer_type: TransferType = Field(..., description="轉移類型")
    transfer_reason: Optional[str] = Field(None, max_length=500, description="轉移原因")
    transfer_fee: Optional[Decimal] = Field(None, ge=0, le=999999.99, description="轉移費用")
    notes: Optional[str] = Field(None, max_length=1000, description="備註")

class PetTransferUpdate(BaseSchema):
    """更新轉移請求"""
    status: TransferStatus
    notes: Optional[str] = None

class PetTransferResponse(TimestampSchema):  # 只繼承 TimestampSchema
    """寵物轉移響應"""
    id: int
    pet_id: int
    from_user_id: int
    to_user_id: int
    transfer_reason: Optional[str]
    transfer_type: TransferType
    transfer_fee: Optional[Decimal]
    notes: Optional[str]
    status: TransferStatus
    requested_at: datetime
    responded_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # 關聯資料
    pet: Optional[PetResponse] = None
    from_user: Optional[UserPublicProfile] = None
    to_user: Optional[UserPublicProfile] = None

    class Config:
        from_attributes = True

class PetTransferHistoryResponse(BaseSchema):  # 只繼承 BaseSchema
    """寵物轉移歷史記錄"""
    id: int
    pet_id: int
    from_user: UserPublicProfile
    to_user: UserPublicProfile
    transfer_type: TransferType
    transfer_reason: Optional[str]
    transfer_fee: Optional[Decimal]
    status: TransferStatus
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

