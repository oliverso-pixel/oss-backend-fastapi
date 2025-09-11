# app/schemas/social.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.user import UserPublicResponse
from app.models.social import FriendshipStatus

class FriendshipBase(BaseSchema):
    """好友關係基礎 Schema"""
    user_id: int
    friend_id: int
    status: FriendshipStatus

class FriendshipResponse(FriendshipBase, TimestampSchema):
    """好友關係響應"""
    id: int
    accepted_at: Optional[datetime] = None
    user: Optional[UserPublicResponse] = None
    friend: Optional[UserPublicResponse] = None

class FriendRequestResponse(BaseSchema):
    """好友請求響應"""
    id: int
    user: Dict[str, Any]  # 發送者資訊
    status: str
    message: Optional[str] = None
    created_at: datetime
    responded_at: Optional[datetime] = None

class FriendshipAction(BaseSchema):
    """好友操作"""
    action: str = Field(..., pattern="^(accept|reject|remove|block)$")
    reason: Optional[str] = None

class FollowBase(BaseSchema):
    """關注基礎 Schema"""
    follower_id: int
    following_id: int

class FollowResponse(FollowBase, TimestampSchema):
    """關注響應"""
    follower: Optional[UserPublicResponse] = None
    following: Optional[UserPublicResponse] = None

class BlockedUserResponse(BaseSchema):
    """封鎖用戶響應"""
    id: int
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    blocked_at: datetime
    reason: Optional[str] = None

class FriendshipStatistics(BaseSchema):
    """社交統計"""
    total_friends: int
    pending_requests_sent: int
    pending_requests_received: int
    total_followers: int
    total_following: int
    blocked_users: int
    mutual_friends: int

class SocialActivity(BaseSchema):
    """社交活動"""
    type: str  # friend_added, started_following, new_post, etc.
    user_id: int
    target_user_id: Optional[int] = None
    content: Optional[str] = None
    created_at: datetime

class SocialFeed(BaseSchema):
    """社交動態"""
    activities: List[SocialActivity]
    total: int
    has_more: bool

