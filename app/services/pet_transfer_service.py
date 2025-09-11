# app/services/pet_transfer_service.py
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from app.models.pet import Pet
from app.models.user import User
from app.models.pet_transfer import PetTransferHistory, TransferStatus, TransferType
from app.services.notification_service import NotificationService
from app.services.privacy_service import PrivacyService

class PetTransferService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    def create_transfer_request(
        self,
        pet_id: int,
        from_user_id: int,
        to_user_id: int,
        transfer_type: TransferType,
        transfer_reason: Optional[str] = None,
        transfer_fee: Optional[float] = None,
        notes: Optional[str] = None
    ) -> PetTransferHistory:
        """創建寵物轉移請求"""
        # 檢查寵物是否存在且屬於發起者
        pet = self.db.query(Pet).filter(
            Pet.id == pet_id,
            Pet.user_id == from_user_id,
            Pet.is_active == True
        ).first()
        
        if not pet:
            raise ValueError("Pet not found or you don't own this pet")
        
        # 檢查接收者是否存在
        to_user = self.db.query(User).filter(
            User.id == to_user_id,
            User.is_active == True
        ).first()
        
        if not to_user:
            raise ValueError("Recipient user not found")
        
        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer pet to yourself")
        
        # 檢查是否有待處理的轉移請求
        existing_transfer = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.pet_id == pet_id,
            PetTransferHistory.status == TransferStatus.PENDING
        ).first()
        
        if existing_transfer:
            raise ValueError("This pet already has a pending transfer request")
        
        # 創建轉移請求
        transfer = PetTransferHistory(
            pet_id=pet_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            transfer_type=transfer_type,
            transfer_reason=transfer_reason,
            transfer_fee=transfer_fee,
            notes=notes,
            status=TransferStatus.PENDING,
            requested_at=datetime.utcnow()
        )
        
        self.db.add(transfer)
        self.db.flush()
        
        # 發送通知給接收者
        from_user = self.db.query(User).filter(User.id == from_user_id).first()
        self.notification_service.create_notification(
            user_id=to_user_id,
            type="pet_transfer_request",
            title="寵物轉移請求",
            content=f"{from_user.display_name or from_user.username} 想要將 {pet.name} 轉移給您",
            data={
                "transfer_id": transfer.id,
                "pet_id": pet_id,
                "from_user_id": from_user_id,
                "transfer_type": transfer_type.value
            }
        )
        
        self.db.commit()
        self.db.refresh(transfer)
        
        # 載入關聯資料
        transfer.pet = pet
        transfer.from_user = from_user
        transfer.to_user = to_user
        
        return transfer
    
    def accept_transfer(self, transfer_id: int, user_id: int) -> PetTransferHistory:
        """接受寵物轉移"""
        transfer = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.id == transfer_id,
            PetTransferHistory.to_user_id == user_id,
            PetTransferHistory.status == TransferStatus.PENDING
        ).first()
        
        if not transfer:
            raise ValueError("Transfer request not found or already processed")
        
        # 獲取寵物
        pet = self.db.query(Pet).filter(Pet.id == transfer.pet_id).first()
        if not pet:
            raise ValueError("Pet not found")
        
        # 執行轉移
        old_owner_id = pet.user_id
        pet.user_id = user_id
        
        # 更新轉移記錄
        transfer.status = TransferStatus.ACCEPTED
        transfer.responded_at = datetime.utcnow()
        transfer.completed_at = datetime.utcnow()
        
        # 發送通知給原擁有者
        self.notification_service.create_notification(
            user_id=old_owner_id,
            type="pet_transfer_accepted",
            title="寵物轉移已接受",
            content=f"您的寵物 {pet.name} 已成功轉移",
            data={
                "transfer_id": transfer_id,
                "pet_id": pet.id,
                "new_owner_id": user_id
            }
        )
        
        self.db.commit()
        self.db.refresh(transfer)
        
        # 載入關聯資料
        transfer.pet = pet
        transfer.from_user = self.db.query(User).filter(User.id == old_owner_id).first()
        transfer.to_user = self.db.query(User).filter(User.id == user_id).first()
        
        return transfer
    
    def reject_transfer(self, transfer_id: int, user_id: int, reason: Optional[str] = None) -> PetTransferHistory:
        """拒絕寵物轉移"""
        transfer = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.id == transfer_id,
            PetTransferHistory.to_user_id == user_id,
            PetTransferHistory.status == TransferStatus.PENDING
        ).first()
        
        if not transfer:
            raise ValueError("Transfer request not found or already processed")
        
        # 更新轉移記錄
        transfer.status = TransferStatus.REJECTED
        transfer.responded_at = datetime.utcnow()
        if reason:
            transfer.notes = f"{transfer.notes}\n拒絕原因: {reason}" if transfer.notes else f"拒絕原因: {reason}"
        
        # 獲取寵物資訊
        pet = self.db.query(Pet).filter(Pet.id == transfer.pet_id).first()
        
        # 發送通知給原擁有者
        self.notification_service.create_notification(
            user_id=transfer.from_user_id,
            type="pet_transfer_rejected",
            title="寵物轉移已拒絕",
            content=f"您的寵物 {pet.name if pet else ''} 轉移請求已被拒絕",
            data={
                "transfer_id": transfer_id,
                "pet_id": transfer.pet_id,
                "reason": reason
            }
        )
        
        self.db.commit()
        self.db.refresh(transfer)
        
        return transfer
    
    def cancel_transfer(self, transfer_id: int, user_id: int) -> PetTransferHistory:
        """取消寵物轉移請求"""
        transfer = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.id == transfer_id,
            PetTransferHistory.from_user_id == user_id,
            PetTransferHistory.status == TransferStatus.PENDING
        ).first()
        
        if not transfer:
            raise ValueError("Transfer request not found or cannot be cancelled")
        
        # 更新狀態
        transfer.status = TransferStatus.CANCELLED
        transfer.responded_at = datetime.utcnow()
        
        # 獲取寵物資訊
        pet = self.db.query(Pet).filter(Pet.id == transfer.pet_id).first()
        
        # 發送通知給接收者
        self.notification_service.create_notification(
            user_id=transfer.to_user_id,
            type="pet_transfer_cancelled",
            title="寵物轉移已取消",
            content=f"關於 {pet.name if pet else '寵物'} 的轉移請求已被取消",
            data={
                "transfer_id": transfer_id,
                "pet_id": transfer.pet_id
            }
        )
        
        self.db.commit()
        self.db.refresh(transfer)
        
        return transfer
    
    def get_received_transfers(
        self,
        user_id: int,
        status: Optional[TransferStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[PetTransferHistory], int]:
        """獲取收到的轉移請求"""
        query = self.db.query(PetTransferHistory).options(
            joinedload(PetTransferHistory.pet),
            joinedload(PetTransferHistory.from_user),
            joinedload(PetTransferHistory.to_user)
        ).filter(PetTransferHistory.to_user_id == user_id)
        
        if status:
            query = query.filter(PetTransferHistory.status == status)
        
        total = query.count()
        transfers = query.order_by(desc(PetTransferHistory.created_at)).offset(skip).limit(limit).all()
        
        return transfers, total
    
    def get_sent_transfers(
        self,
        user_id: int,
        status: Optional[TransferStatus] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[PetTransferHistory], int]:
        """獲取發送的轉移請求"""
        query = self.db.query(PetTransferHistory).options(
            joinedload(PetTransferHistory.pet),
            joinedload(PetTransferHistory.from_user),
            joinedload(PetTransferHistory.to_user)
        ).filter(PetTransferHistory.from_user_id == user_id)
        
        if status:
            query = query.filter(PetTransferHistory.status == status)
        
        total = query.count()
        transfers = query.order_by(desc(PetTransferHistory.created_at)).offset(skip).limit(limit).all()
        
        return transfers, total
    
    def get_pet_transfer_history(self, pet_id: int) -> List[PetTransferHistory]:
        """獲取寵物的完整轉移歷史"""
        history = self.db.query(PetTransferHistory).options(
            joinedload(PetTransferHistory.from_user),
            joinedload(PetTransferHistory.to_user)
        ).filter(
            PetTransferHistory.pet_id == pet_id,
            PetTransferHistory.status == TransferStatus.ACCEPTED
        ).order_by(desc(PetTransferHistory.completed_at)).all()
        
        return history
    
    def get_user_transfer_statistics(self, user_id: int) -> Dict[str, int]:
        """獲取用戶的轉移統計"""
        # 發送的轉移
        sent_total = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.from_user_id == user_id
        ).count()
        
        sent_accepted = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.from_user_id == user_id,
            PetTransferHistory.status == TransferStatus.ACCEPTED
        ).count()
        
        # 接收的轉移
        received_total = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.to_user_id == user_id
        ).count()
        
        received_accepted = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.to_user_id == user_id,
            PetTransferHistory.status == TransferStatus.ACCEPTED
        ).count()
        
        # 待處理
        pending_sent = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.from_user_id == user_id,
            PetTransferHistory.status == TransferStatus.PENDING
        ).count()
        
        pending_received = self.db.query(PetTransferHistory).filter(
            PetTransferHistory.to_user_id == user_id,
            PetTransferHistory.status == TransferStatus.PENDING
        ).count()
        
        return {
            "sent_total": sent_total,
            "sent_accepted": sent_accepted,
            "received_total": received_total,
            "received_accepted": received_accepted,
            "pending_sent": pending_sent,
            "pending_received": pending_received
        }
    
