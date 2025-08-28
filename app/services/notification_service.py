# app/services/notification_service.py
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.social import Notification
import json

class NotificationService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_notification(
        self, 
        user_id: int, 
        type: str, 
        title: str, 
        content: str,
        data: Dict[str, Any] = None
    ) -> Notification:
        """創建通知"""
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            content=content,
            data=json.dumps(data) if data else None
        )
        self.db.add(notification)
        self.db.commit()
        return notification
    
    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """標記為已讀"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def mark_all_as_read(self, user_id: int) -> int:
        """標記所有為已讀"""
        count = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            Notification.is_read: True,
            Notification.read_at: datetime.utcnow()
        })
        
        self.db.commit()
        return count
    
    def get_notifications(
        self, 
        user_id: int, 
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> List[Notification]:
        """獲取通知列表"""
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        return query.order_by(
            Notification.created_at.desc()
        ).limit(limit).offset(offset).all()
    
    def get_unread_count(self, user_id: int) -> int:
        """獲取未讀通知數量"""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
    
    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """刪除通知"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            self.db.delete(notification)
            self.db.commit()
            return True
        return False