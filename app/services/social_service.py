# app/services/social_service.py
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc, func
from app.models.social import Friendship, FriendshipStatus, Follow, Notification
from app.models.user import User, PrivacyLevel
from app.models.post import Post
from app.services.notification_service import NotificationService
from app.schemas.social import FriendshipStatistics, SocialFeed, SocialActivity

class SocialService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    # ========== 好友功能 ==========
    
    def send_friend_request(self, user_id: int, friend_id: int, message: str = None) -> bool:
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
            status=FriendshipStatus.PENDING,
            message=message
        )
        self.db.add(friendship)
        
        # 發送通知給對方
        requester = self.db.query(User).filter(User.id == user_id).first()
        self.notification_service.create_notification(
            user_id=friend_id,
            type="friend_request",
            title="新的好友請求",
            content=f"{requester.display_name or requester.username} 想要加您為好友",
            data={"requester_id": user_id, "message": message}
        )
        
        self.db.commit()
        return True
    
    def get_received_friend_requests(self, user_id: int, status: str = None, 
                                   skip: int = 0, limit: int = 20) -> Tuple[List[Friendship], int]:
        """獲取收到的好友請求"""
        query = self.db.query(Friendship).options(
            joinedload(Friendship.user)
        ).filter(
            Friendship.friend_id == user_id
        )
        
        if status:
            query = query.filter(Friendship.status == FriendshipStatus(status))
        else:
            query = query.filter(Friendship.status == FriendshipStatus.PENDING)
        
        total = query.count()
        requests = query.order_by(desc(Friendship.created_at)).offset(skip).limit(limit).all()
        
        return requests, total
    
    def get_sent_friend_requests(self, user_id: int, status: str = None,
                               skip: int = 0, limit: int = 20) -> Tuple[List[Friendship], int]:
        """獲取發送的好友請求"""
        query = self.db.query(Friendship).options(
            joinedload(Friendship.friend)
        ).filter(
            Friendship.user_id == user_id
        )
        
        if status:
            query = query.filter(Friendship.status == FriendshipStatus(status))
        
        total = query.count()
        requests = query.order_by(desc(Friendship.created_at)).offset(skip).limit(limit).all()
        
        return requests, total
    
    def accept_friend_request(self, request_id: int, user_id: int) -> bool:
        """接受好友請求"""
        # 查找待處理的請求
        friendship = self.db.query(Friendship).filter(
            Friendship.id == request_id,
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
            friend_id=friendship.user_id,
            status=FriendshipStatus.ACCEPTED,
            accepted_at=datetime.utcnow()
        )
        self.db.add(reverse_friendship)
        
        # 發送通知
        accepter = self.db.query(User).filter(User.id == user_id).first()
        self.notification_service.create_notification(
            user_id=friendship.user_id,
            type="friend_accepted",
            title="好友請求已接受",
            content=f"{accepter.display_name or accepter.username} 已接受您的好友請求",
            data={"accepter_id": user_id}
        )
        
        self.db.commit()
        return True
    
    def reject_friend_request(self, request_id: int, user_id: int, reason: str = None) -> bool:
        """拒絕好友請求"""
        friendship = self.db.query(Friendship).filter(
            Friendship.id == request_id,
            Friendship.friend_id == user_id,
            Friendship.status == FriendshipStatus.PENDING
        ).first()
        
        if not friendship:
            return False
        
        # 更新狀態為拒絕
        friendship.status = FriendshipStatus.REJECTED
        friendship.rejected_at = datetime.utcnow()
        friendship.rejection_reason = reason
        
        self.db.commit()
        return True
    
    def remove_friend(self, user_id: int, friend_id: int) -> bool:
        """移除好友"""
        # 刪除雙向關係
        deleted = self.db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
            ),
            Friendship.status == FriendshipStatus.ACCEPTED
        ).delete()
        
        self.db.commit()
        return deleted > 0
    
    def block_user(self, user_id: int, blocked_id: int, reason: str = None) -> bool:
        """封鎖用戶"""
        # 移除現有關係
        self.remove_friend(user_id, blocked_id)
        
        # 取消關注關係
        self.db.query(Follow).filter(
            or_(
                and_(Follow.follower_id == user_id, Follow.following_id == blocked_id),
                and_(Follow.follower_id == blocked_id, Follow.following_id == user_id)
            )
        ).delete()
        
        # 創建封鎖關係
        block = Friendship(
            user_id=user_id,
            friend_id=blocked_id,
            status=FriendshipStatus.BLOCKED,
            reason=reason
        )
        self.db.add(block)
        self.db.commit()
        return True
    
    def unblock_user(self, user_id: int, blocked_id: int) -> bool:
        """解除封鎖"""
        deleted = self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.friend_id == blocked_id,
            Friendship.status == FriendshipStatus.BLOCKED
        ).delete()
        
        self.db.commit()
        return deleted > 0
    
    def get_friends(self, user_id: int, search: str = None, online_only: bool = False,
                   skip: int = 0, limit: int = 20) -> Tuple[List[User], int]:
        """獲取好友列表"""
        query = self.db.query(User).join(
            Friendship,
            and_(
                Friendship.friend_id == User.id,
                Friendship.user_id == user_id,
                Friendship.status == FriendshipStatus.ACCEPTED
            )
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_term),
                    User.display_name.ilike(search_term)
                )
            )
        
        if online_only:
            # 假設5分鐘內有活動為在線
            online_threshold = datetime.utcnow() - timedelta(minutes=5)
            query = query.filter(User.last_login_at >= online_threshold)
        
        total = query.count()
        friends = query.order_by(User.display_name).offset(skip).limit(limit).all()
        
        return friends, total
    
    def get_blocked_users(self, user_id: int, skip: int = 0, 
                         limit: int = 20) -> Tuple[List[Tuple[User, Friendship]], int]:
        """獲取封鎖列表"""
        query = self.db.query(User, Friendship).join(
            Friendship,
            and_(
                Friendship.friend_id == User.id,
                Friendship.user_id == user_id,
                Friendship.status == FriendshipStatus.BLOCKED
            )
        )
        
        total = query.count()
        blocked = query.order_by(desc(Friendship.created_at)).offset(skip).limit(limit).all()
        
        return blocked, total
    
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
            Friendship.user_id == user_id,
            Friendship.friend_id == target_id,
            Friendship.status == FriendshipStatus.BLOCKED
        ).first() is not None
    
    def has_pending_friend_request(self, user_id: int, target_id: int) -> bool:
        """檢查是否有待處理的好友請求"""
        return self.db.query(Friendship).filter(
            or_(
                and_(
                    Friendship.user_id == user_id,
                    Friendship.friend_id == target_id
                ),
                and_(
                    Friendship.user_id == target_id,
                    Friendship.friend_id == user_id
                )
            ),
            Friendship.status == FriendshipStatus.PENDING
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
        follower = self.db.query(User).filter(User.id == follower_id).first()
        self.notification_service.create_notification(
            user_id=following_id,
            type="new_follower",
            title="新的關注者",
            content=f"{follower.display_name or follower.username} 開始關注您",
            data={"follower_id": follower_id}
        )
        
        self.db.commit()
        return True
    
    def unfollow_user(self, follower_id: int, following_id: int) -> bool:
        """取消關注"""
        deleted = self.db.query(Follow).filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id
        ).delete()
        
        self.db.commit()
        return deleted > 0
    
    def get_followers(self, user_id: int, search: str = None,
                     skip: int = 0, limit: int = 20) -> Tuple[List[Follow], int]:
        """獲取關注者列表"""
        query = self.db.query(Follow).options(
            joinedload(Follow.follower)
        ).filter(
            Follow.following_id == user_id
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.join(User, User.id == Follow.follower_id).filter(
                or_(
                    User.username.ilike(search_term),
                    User.display_name.ilike(search_term)
                )
            )
        
        total = query.count()
        followers = query.order_by(desc(Follow.created_at)).offset(skip).limit(limit).all()
        
        return followers, total
    
    def get_following(self, user_id: int, search: str = None,
                     skip: int = 0, limit: int = 20) -> Tuple[List[Follow], int]:
        """獲取關注列表"""
        query = self.db.query(Follow).options(
            joinedload(Follow.following)
        ).filter(
            Follow.follower_id == user_id
        )
        
        if search:
            search_term = f"%{search}%"
            query = query.join(User, User.id == Follow.following_id).filter(
                or_(
                    User.username.ilike(search_term),
                    User.display_name.ilike(search_term)
                )
            )
        
        total = query.count()
        following = query.order_by(desc(Follow.created_at)).offset(skip).limit(limit).all()
        
        return following, total
    
    def is_following(self, follower_id: int, following_id: int) -> bool:
        """檢查是否關注"""
        return self.db.query(Follow).filter(
            Follow.follower_id == follower_id,
            Follow.following_id == following_id
        ).first() is not None
    
    # ========== 統計功能 ==========
    
    def get_social_statistics(self, user_id: int) -> FriendshipStatistics:
        """獲取社交統計數據"""
        # 好友統計
        total_friends = self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.status == FriendshipStatus.ACCEPTED
        ).count()
        
        pending_sent = self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.status == FriendshipStatus.PENDING
        ).count()
        
        pending_received = self.db.query(Friendship).filter(
            Friendship.friend_id == user_id,
            Friendship.status == FriendshipStatus.PENDING
        ).count()
        
        # 關注統計
        total_followers = self.db.query(Follow).filter(
            Follow.following_id == user_id
        ).count()
        
        total_following = self.db.query(Follow).filter(
            Follow.follower_id == user_id
        ).count()
        
        # 封鎖統計
        blocked_users = self.db.query(Friendship).filter(
            Friendship.user_id == user_id,
            Friendship.status == FriendshipStatus.BLOCKED
        ).count()
        
        # 共同好友數（與所有好友的平均共同好友數）
        mutual_friends = self._calculate_average_mutual_friends(user_id)
        
        return FriendshipStatistics(
            total_friends=total_friends,
            pending_requests_sent=pending_sent,
            pending_requests_received=pending_received,
            total_followers=total_followers,
            total_following=total_following,
            blocked_users=blocked_users,
            mutual_friends=mutual_friends
        )
    
    def get_friend_suggestions(self, user_id: int, limit: int = 10) -> List[Tuple[User, int]]:
        """獲取好友推薦（基於共同好友）"""
        # 獲取用戶的好友列表
        friend_ids = self.db.query(Friendship.friend_id).filter(
            Friendship.user_id == user_id,
            Friendship.status == FriendshipStatus.ACCEPTED
        ).subquery()
        
        # 查找好友的好友（二度關係）
        suggestions = self.db.query(
            User,
            func.count(Friendship.user_id).label('mutual_count')
        ).join(
            Friendship,
            and_(
                Friendship.friend_id == User.id,
                Friendship.status == FriendshipStatus.ACCEPTED
            )
        ).filter(
            Friendship.user_id.in_(friend_ids),
            User.id != user_id,
            ~User.id.in_(friend_ids),  # 排除已經是好友的
            User.is_active == True,
            User.privacy_level == PrivacyLevel.PUBLIC  # 只推薦公開用戶
        ).group_by(User.id).order_by(
            desc('mutual_count')
        ).limit(limit).all()
        
        # 排除已封鎖的用戶
        blocked_ids = self.db.query(Friendship.friend_id).filter(
            or_(
                and_(
                    Friendship.user_id == user_id,
                    Friendship.status == FriendshipStatus.BLOCKED
                ),
                and_(
                    Friendship.friend_id == user_id,
                    Friendship.status == FriendshipStatus.BLOCKED
                )
            )
        ).subquery()
        
        # 過濾結果
        filtered_suggestions = [
            (user, count) for user, count in suggestions
            if user.id not in blocked_ids
        ]
        
        return filtered_suggestions
    
    def get_social_feed(self, user_id: int, include_friends: bool = True,
                       include_following: bool = True, skip: int = 0, 
                       limit: int = 20) -> SocialFeed:
        """獲取社交動態"""
        # 獲取相關用戶ID
        user_ids = [user_id]
        
        if include_friends:
            friend_ids = self.db.query(Friendship.friend_id).filter(
                Friendship.user_id == user_id,
                Friendship.status == FriendshipStatus.ACCEPTED
            ).all()
            user_ids.extend([fid[0] for fid in friend_ids])
        
        if include_following:
            following_ids = self.db.query(Follow.following_id).filter(
                Follow.follower_id == user_id
            ).all()
            user_ids.extend([fid[0] for fid in following_ids])
        
        # 獲取最新貼文
        posts = self.db.query(Post).filter(
            Post.user_id.in_(user_ids),
            Post.is_deleted == False,
            Post.visibility == 'public'  # 只顯示公開貼文
        ).order_by(
            desc(Post.created_at)
        ).offset(skip).limit(limit).all()
        
        # 轉換為活動格式
        activities = []
        for post in posts:
            activities.append(SocialActivity(
                type="new_post",
                user_id=post.user_id,
                content=post.content[:100] if post.content else None,
                created_at=post.created_at
            ))
        
        total = len(activities)
        has_more = total == limit
        
        return SocialFeed(
            activities=activities,
            total=total,
            has_more=has_more
        )
    
    def _calculate_average_mutual_friends(self, user_id: int) -> int:
        """計算平均共同好友數"""
        # 這是一個簡化的實現
        return 0