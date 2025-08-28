# app/services/social_service.py
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.social import Friendship, FriendshipStatus, Follow, Notification
from app.models.user import User
from app.services.notification_service import NotificationService

class SocialService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    # ========== 好友功能 ==========
    
    def send_friend_request(self, user_id: int, friend_id: int) -> bool:
        """發送好友請求"""
        # 檢查是否已經是好友或有待處理的請求
        existing = self.db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
            )
        ).first()
        
        if existing:
            return False
        
        # 創建好友請求
        friendship = Friendship(
            user_id=user_id,
            friend_id=friend_id,
            status=FriendshipStatus.PENDING
        )
        self.db.add(friendship)
        
        # 發送通知給對方
        self.notification_service.create_notification(
            user_id=friend_id,
            type="friend_request",
            title="新的好友請求",
            content=f"用戶 {user_id} 想要加您為好友"
        )
        
        self.db.commit()
        return True
    
    def accept_friend_request(self, user_id: int, requester_id: int) -> bool:
        """接受好友請求"""
        # 查找待處理的請求
        friendship = self.db.query(Friendship).filter(
            Friendship.user_id == requester_id,
            Friendship.friend_id == user_id,
            Friendship.status == FriendshipStatus.PENDING
        ).first()
        
        if not friendship:
            return False
        
        # 更新狀態
        friendship.status = FriendshipStatus.ACCEPTED
        friendship.accepted_at = datetime.utcnow()
        
        # 創建雙向關係
        reverse_friendship = Friendship(
            user_id=user_id,
            friend_id=requester_id,
            status=FriendshipStatus.ACCEPTED,
            accepted_at=datetime.utcnow()
        )
        self.db.add(reverse_friendship)
        
        # 發送通知
        self.notification_service.create_notification(
            user_id=requester_id,
            type="friend_accepted",
            title="好友請求已接受",
            content=f"用戶 {user_id} 已接受您的好友請求"
        )
        
        self.db.commit()
        return True
    
    def reject_friend_request(self, user_id: int, requester_id: int) -> bool:
        """拒絕好友請求"""
        friendship = self.db.query(Friendship).filter(
            Friendship.user_id == requester_id,
            Friendship.friend_id == user_id,
            Friendship.status == FriendshipStatus.PENDING
        ).first()
        
        if not friendship:
            return False
        
        self.db.delete(friendship)
        self.db.commit()
        return True
    
    def remove_friend(self, user_id: int, friend_id: int) -> bool:
        """移除好友"""
        # 刪除雙向關係
        self.db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
            )
        ).delete()
        
        self.db.commit()
        return True
    
    def block_user(self, user_id: int, blocked_id: int) -> bool:
        """封鎖用戶"""
        # 移除現有關係
        self.remove_friend(user_id, blocked_id)
        
        # 創建封鎖關係
        block = Friendship(
            user_id=user_id,
            friend_id=blocked_id,
            status=FriendshipStatus.BLOCKED
        )
        self.db.add(block)
        self.db.commit()
        return True
    
    def unblock_user(self, user_id: int, blocked_id: int) -> bool:
        """解除封鎖"""
        self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.friend_id == blocked_id,
            Friendship.status == FriendshipStatus.BLOCKED
        ).delete()
        
        self.db.commit()
        return True
    
    def get_friends(self, user_id: int) -> List[User]:
        """獲取好友列表"""
        friendships = self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.status == FriendshipStatus.ACCEPTED
        ).all()
        
        friend_ids = [f.friend_id for f in friendships]
        return self.db.query(User).filter(User.id.in_(friend_ids)).all()
    
    def get_pending_friend_requests(self, user_id: int) -> List[Tuple[User, Friendship]]:
        """獲取待處理的好友請求"""
        requests = self.db.query(Friendship).filter(
            Friendship.friend_id == user_id,
            Friendship.status == FriendshipStatus.PENDING
        ).all()
        
        result = []
        for req in requests:
            user = self.db.query(User).filter(User.id == req.user_id).first()
            if user:
                result.append((user, req))
        
        return result
    
    def get_blocked_users(self, user_id: int) -> List[User]:
        """獲取封鎖列表"""
        blocks = self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.status == FriendshipStatus.BLOCKED
        ).all()
        
        blocked_ids = [b.friend_id for b in blocks]
        return self.db.query(User).filter(User.id.in_(blocked_ids)).all()
    
    def is_friend(self, user_id: int, target_id: int) -> bool:
        """檢查是否為好友"""
        return self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.friend_id == target_id,
            Friendship.status == FriendshipStatus.ACCEPTED
        ).first() is not None
    
    def is_blocked(self, user_id: int, target_id: int) -> bool:
        """檢查是否被封鎖"""
        return self.db.query(Friendship).filter(
            or_(
                and_(
                    Friendship.user_id == user_id,
                    Friendship.friend_id == target_id,
                    Friendship.status == FriendshipStatus.BLOCKED
                ),
                and_(
                    Friendship.user_id == target_id,
                    Friendship.friend_id == user_id,
                    Friendship.status == FriendshipStatus.BLOCKED
                )
            )
        ).first() is not None
    
    # ========== 關注功能 ==========
    
    def follow_user(self, follower_id: int, following_id: int) -> bool:
        """關注用戶"""
        # 檢查是否已經關注
        existing = self.db.query(Follow).filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id
        ).first()
        
        if existing:
            return False
        
        follow = Follow(
            follower_id=follower_id,
            following_id=following_id
        )
        self.db.add(follow)
        
        # 發送通知
        self.notification_service.create_notification(
            user_id=following_id,
            type="new_follower",
            title="新的關注者",
            content=f"用戶 {follower_id} 開始關注您"
        )
        
        self.db.commit()
        return True
    
    def unfollow_user(self, follower_id: int, following_id: int) -> bool:
        """取消關注"""
        self.db.query(Follow).filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id
        ).delete()
        
        self.db.commit()
        return True
    
    def get_followers(self, user_id: int) -> List[User]:
        """獲取關注者列表"""
        follows = self.db.query(Follow).filter(
            Follow.following_id == user_id
        ).all()
        
        follower_ids = [f.follower_id for f in follows]
        return self.db.query(User).filter(User.id.in_(follower_ids)).all()
    
    def get_following(self, user_id: int) -> List[User]:
        """獲取關注列表"""
        follows = self.db.query(Follow).filter(
            Follow.follower_id == user_id
        ).all()
        
        following_ids = [f.following_id for f in follows]
        return self.db.query(User).filter(User.id.in_(following_ids)).all()
    
    def is_following(self, follower_id: int, following_id: int) -> bool:
        """檢查是否關注"""
        return self.db.query(Follow).filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id
        ).first() is not None