# app/api/v1/endpoints/social.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.social import FriendshipStatus
from app.services.social_service import SocialService
from app.services.privacy_service import PrivacyService
from app.schemas.social import (
    FriendshipResponse, FriendRequestResponse, FollowResponse,
    FriendshipAction, BlockedUserResponse, FriendshipStatistics,
    SocialFeed
)
from app.schemas.user import UserPublicResponse
from app.schemas.base import PaginationParams, PaginatedResponse

router = APIRouter()

# ========== 好友功能 ==========

@router.post("/friends/request/{user_id}", response_model=dict)
def send_friend_request(
    user_id: int,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """發送好友請求"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send friend request to yourself"
        )
    
    social_service = SocialService(db)
    
    # 檢查是否被封鎖
    if social_service.is_blocked(current_user.id, user_id) or social_service.is_blocked(user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot send friend request to this user"
        )
    
    success = social_service.send_friend_request(current_user.id, user_id, message)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Friend request already exists or users are already friends"
        )
    
    return {"message": "Friend request sent successfully"}

@router.get("/friends/requests", response_model=PaginatedResponse)
def get_friend_requests(
    type: str = Query("received", pattern="^(sent|received)$"),
    status: Optional[str] = Query(None, pattern="^(pending|accepted|rejected)$"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取好友請求列表"""
    social_service = SocialService(db)
    privacy_service = PrivacyService(db)
    
    if type == "received":
        requests, total = social_service.get_received_friend_requests(
            current_user.id, status, pagination.skip, pagination.limit
        )
    else:  # sent
        requests, total = social_service.get_sent_friend_requests(
            current_user.id, status, pagination.skip, pagination.limit
        )
    
    # 轉換為響應格式
    items = []
    for req in requests:
        user_data = privacy_service.get_user_visible_data(current_user, req.user)
        items.append(FriendRequestResponse(
            id=req.id,
            user=user_data,
            status=req.status.value,
            message=req.message,
            created_at=req.created_at,
            responded_at=req.accepted_at or req.rejected_at
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.post("/friends/requests/{request_id}/accept", response_model=dict)
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """接受好友請求"""
    social_service = SocialService(db)
    success = social_service.accept_friend_request(request_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found or already processed"
        )
    
    return {"message": "Friend request accepted"}

@router.post("/friends/requests/{request_id}/reject", response_model=dict)
def reject_friend_request(
    request_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """拒絕好友請求"""
    social_service = SocialService(db)
    success = social_service.reject_friend_request(request_id, current_user.id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found or already processed"
        )
    
    return {"message": "Friend request rejected"}

@router.get("/friends", response_model=PaginatedResponse)
def get_friends(
    search: Optional[str] = Query(None),
    online_only: bool = Query(False),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取好友列表"""
    social_service = SocialService(db)
    privacy_service = PrivacyService(db)
    
    friends, total = social_service.get_friends(
        current_user.id, search, online_only, pagination.skip, pagination.limit
    )
    
    # 轉換為響應格式，好友可以看到更多資訊
    items = []
    for friend in friends:
        user_data = privacy_service.get_user_visible_data(current_user, friend)
        items.append(user_data)
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.delete("/friends/{friend_id}", response_model=dict)
def remove_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """移除好友"""
    social_service = SocialService(db)
    success = social_service.remove_friend(current_user.id, friend_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend not found"
        )
    
    return {"message": "Friend removed successfully"}

# ========== 封鎖功能 ==========

@router.post("/block/{user_id}", response_model=dict)
def block_user(
    user_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """封鎖用戶"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself"
        )
    
    social_service = SocialService(db)
    success = social_service.block_user(current_user.id, user_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already blocked or error occurred"
        )
    
    return {"message": "User blocked successfully"}

@router.delete("/block/{user_id}", response_model=dict)
def unblock_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """解除封鎖"""
    social_service = SocialService(db)
    success = social_service.unblock_user(current_user.id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not in block list"
        )
    
    return {"message": "User unblocked successfully"}

@router.get("/blocked", response_model=PaginatedResponse)
def get_blocked_users(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取封鎖列表"""
    social_service = SocialService(db)
    blocked_users, total = social_service.get_blocked_users(
        current_user.id, pagination.skip, pagination.limit
    )
    
    # 封鎖的用戶只顯示最基本資訊
    items = []
    for user, block_info in blocked_users:
        items.append(BlockedUserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            blocked_at=block_info.created_at,
            reason=block_info.reason
        ))
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

# ========== 關注功能 ==========

@router.post("/follow/{user_id}", response_model=dict)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """關注用戶"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself"
        )
    
    social_service = SocialService(db)
    
    # 檢查是否被封鎖
    if social_service.is_blocked(current_user.id, user_id) or social_service.is_blocked(user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot follow this user"
        )
    
    success = social_service.follow_user(current_user.id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user"
        )
    
    return {"message": "Successfully followed user"}

@router.delete("/follow/{user_id}", response_model=dict)
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """取消關注"""
    social_service = SocialService(db)
    success = social_service.unfollow_user(current_user.id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not following this user"
        )
    
    return {"message": "Successfully unfollowed user"}

@router.get("/followers", response_model=PaginatedResponse)
def get_followers(
    search: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取關注者列表"""
    social_service = SocialService(db)
    privacy_service = PrivacyService(db)
    
    followers, total = social_service.get_followers(
        current_user.id, search, pagination.skip, pagination.limit
    )
    
    items = []
    for follower in followers:
        user_data = privacy_service.get_user_visible_data(current_user, follower.follower)
        # 添加關注時間
        user_data["followed_at"] = follower.created_at
        items.append(user_data)
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/following", response_model=PaginatedResponse)
def get_following(
    search: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取關注列表"""
    social_service = SocialService(db)
    privacy_service = PrivacyService(db)
    
    following, total = social_service.get_following(
        current_user.id, search, pagination.skip, pagination.limit
    )
    
    items = []
    for follow in following:
        user_data = privacy_service.get_user_visible_data(current_user, follow.following)
        # 添加關注時間
        user_data["followed_at"] = follow.created_at
        items.append(user_data)
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

# ========== 社交統計 ==========

@router.get("/statistics", response_model=FriendshipStatistics)
def get_social_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取社交統計數據"""
    social_service = SocialService(db)
    return social_service.get_social_statistics(current_user.id)

@router.get("/suggestions", response_model=PaginatedResponse)
def get_friend_suggestions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取好友推薦"""
    social_service = SocialService(db)
    privacy_service = PrivacyService(db)
    
    suggestions = social_service.get_friend_suggestions(current_user.id, limit)
    
    items = []
    for user, mutual_friends_count in suggestions:
        user_data = privacy_service.get_user_visible_data(current_user, user)
        user_data["mutual_friends_count"] = mutual_friends_count
        items.append(user_data)
    
    return PaginatedResponse(
        items=items,
        total=len(items),
        page=1,
        per_page=limit,
        pages=1
    )

# ========== 社交動態 ==========

@router.get("/feed", response_model=SocialFeed)
def get_social_feed(
    include_friends: bool = Query(True),
    include_following: bool = Query(True),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取社交動態（好友和關注者的最新動態）"""
    social_service = SocialService(db)
    return social_service.get_social_feed(
        current_user.id,
        include_friends,
        include_following,
        pagination.skip,
        pagination.limit
    )

# ========== 關係檢查 ==========

@router.get("/relationship/{user_id}", response_model=dict)
def check_relationship(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """檢查與指定用戶的關係狀態"""
    social_service = SocialService(db)
    
    return {
        "is_friend": social_service.is_friend(current_user.id, user_id),
        "is_following": social_service.is_following(current_user.id, user_id),
        "is_followed_by": social_service.is_following(user_id, current_user.id),
        "is_blocked": social_service.is_blocked(current_user.id, user_id),
        "is_blocked_by": social_service.is_blocked(user_id, current_user.id),
        "has_pending_request": social_service.has_pending_friend_request(current_user.id, user_id)
    }

