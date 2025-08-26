# app/api/va/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.core.database import get_db
from app.core.permissions import get_current_user, is_authenticated
from app.core.security import oauth2_scheme, decode_token
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.base import PaginationParams, PaginatedResponse
from app.services.user_service import UserService
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def get_current_user(
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取當前用戶信息"""
    return current_user

# def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     db: Session = Depends(get_db)
# ) -> Any:
#     """獲取當前用戶信息"""
#     payload = decode_token(token)
#     if not payload:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     user_id = payload.get("sub")
#     if not user_id:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token payload",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     user = db.query(User).filter(User.id == int(user_id)).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     return user

@router.get("/", response_model=PaginatedResponse)
def get_users(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取用戶列表"""
    user_service = UserService(db)
    users, total = user_service.get_users(
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    return PaginatedResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取特定用戶信息"""
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """更新用戶信息"""
    # 只能更新自己的信息，除非是管理員
    if current_user.id != user_id:
        # TODO: 檢查是否為管理員
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
    return user

