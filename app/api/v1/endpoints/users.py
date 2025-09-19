# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any, Union
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.schemas.user import (
    UserResponse, UserUpdate, PrivacySettings,
    UserPublicProfile, UserPrivateProfile, UserFullResponse
)
from app.schemas.base import PaginationParams, PaginatedResponse
from app.services.user_service import UserService
from app.services.privacy_service import PrivacyService
from app.services.social_service import SocialService
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取當前用戶信息"""
    privacy_service = PrivacyService(db=None)
    return privacy_service._get_full_user_data(current_user)

@router.get("/", response_model=PaginatedResponse)
def get_users(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取用戶列表（根據隱私設置過濾）"""
    user_service = UserService(db)
    privacy_service = PrivacyService(db)

    users, total = user_service.get_users(
        skip=pagination.skip,
        limit=pagination.limit
    )

    # 根據隱私設置過濾用戶資料
    filtered_users = privacy_service.filter_users_by_privacy(users, current_user)
    
    return PaginatedResponse(
        items=filtered_users,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

# @router.get("/{user_id}")
# def get_user(
#     user_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ) -> Any:
#     """獲取特定用戶信息（根據隱私設置返回不同資料）"""
#     user_service = UserService(db)
#     privacy_service = PrivacyService(db)
    
#     user = user_service.get_user(user_id)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     # 根據隱私設置返回可見資料
#     visible_data = privacy_service.get_user_visible_data(current_user, user)
#     return visible_data

@router.get("/{user_id}", response_model=Union[UserPublicProfile, UserPrivateProfile])
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取特定用戶信息（已整合新的隱私與黑名單邏輯）"""
    # 檢查是否被目標用戶封鎖
    social_service = SocialService(db)
    if social_service.is_blocked(user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_service = UserService(db)
    target_user = user_service.get_user(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 根據隱私設置返回可見資料
    privacy_service = PrivacyService(db)
    visible_data = privacy_service.get_user_visible_data(current_user, target_user)
    return visible_data

@router.put("/{user_id}", response_model=UserFullResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """更新用戶信息"""
    # 只能更新自己的信息，除非是管理員
    privacy_service = PrivacyService(db)
    if current_user.id != user_id and not privacy_service.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user_service = UserService(db)
    user = user_service.update_user(user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return privacy_service._get_full_user_data(user)

@router.get("/{user_id}/privacy", response_model=PrivacySettings)
def get_user_privacy_settings(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取用戶隱私設置（僅自己或管理員可查看）"""
    privacy_service = PrivacyService(db)
    
    # 只能查看自己的隱私設置，除非是管理員
    if current_user.id != user_id and not privacy_service.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view privacy settings"
        )
    
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 處理可能的 None 值
    return PrivacySettings(
        privacy_level=user.privacy_level.value if user.privacy_level else PrivacyLevel.PUBLIC.value,
        show_email=user.show_email if user.show_email is not None else False,
        show_phone=user.show_phone if user.show_phone is not None else False,
        show_online_status=user.show_online_status if user.show_online_status is not None else True,
        show_last_seen=user.show_last_seen if user.show_last_seen is not None else True
    )

@router.put("/{user_id}/privacy", response_model=PrivacySettings)
def update_user_privacy_settings(
    user_id: int,
    privacy_settings: PrivacySettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """更新用戶隱私設置"""
    # 只能更新自己的隱私設置
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update privacy settings"
        )
    
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 更新隱私設置
    user.privacy_level = privacy_settings.privacy_level
    user.show_email = privacy_settings.show_email
    user.show_phone = privacy_settings.show_phone
    user.show_online_status = privacy_settings.show_online_status
    user.show_last_seen = privacy_settings.show_last_seen
    
    db.commit()
    db.refresh(user)
    
    return privacy_settings

# @router.get("/search/public", response_model=PaginatedResponse)
# def search_public_users(
#     q: str,
#     pagination: PaginationParams = Depends(),
#     db: Session = Depends(get_db)
# ) -> Any:
#     """搜索公開用戶（不需要登入）"""
#     user_service = UserService(db)
#     privacy_service = PrivacyService(db)
    
#     # 調用更新後的方法，獲取用戶列表和總數
#     users, total = user_service.search_public_users(q, pagination.skip, pagination.limit)
    
#     # 只返回公開資料
#     result_items = [
#         privacy_service._get_minimal_user_data(user) for user in users
#     ]
    
#     # 使用標準化的 PaginatedResponse 返回結果
#     return PaginatedResponse(
#         items=result_items,
#         total=total,  # <-- 使用從 service 層獲取的正確總數
#         page=pagination.page,
#         per_page=pagination.per_page,
#         pages=(total + pagination.per_page - 1) // pagination.per_page
#     )

@router.get("/search/public", response_model=PaginatedResponse)
def search_public_users(
    q: str,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # 搜索時也需要當前用戶來判斷顯示內容
) -> Any:
    """搜索公開用戶（不需要登入）"""
    user_service = UserService(db)
    privacy_service = PrivacyService(db)
    
    users, total = user_service.search_public_users(q, pagination.skip, pagination.limit)
    
    # 根據每個用戶的隱私設定決定顯示的內容
    result_items = privacy_service.filter_users_by_privacy(users, current_user)
    
    return PaginatedResponse(
        items=result_items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

