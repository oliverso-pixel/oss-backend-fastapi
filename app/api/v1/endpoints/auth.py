# app/api/va/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
from app.core.database import get_db
from app.core.security import oauth2_scheme, decode_token
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest, ChangePasswordRequest, ResetPasswordRequest, ResetPasswordConfirm
from app.schemas.user import UserCreate, UserResponse
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """註冊新用戶"""
    user_service = UserService(db)
    
    # 檢查用戶名和郵箱是否已存在
    if user_service.get_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if user_service.get_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # 創建用戶
    user = user_service.create_user(user_data)
    return user

@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """用戶登入"""
    auth_service = AuthService(db)
    
    # 驗證用戶
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 獲取設備信息
    device_info = {
        "ip": request.client.host,
        "user_agent": request.headers.get("user-agent"),
    }
    
    # 創建 tokens
    return auth_service.create_tokens(user, device_info)

@router.post("/refresh", response_model=Token)
def refresh_token(
    token_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """刷新訪問令牌"""
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(token_request.refresh_token)

@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Any:
    """用戶登出"""
    auth_service = AuthService(db)
    
    # 解碼 token 獲取用戶 ID
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    if user_id:
        auth_service.revoke_token(token, int(user_id))
    
    return {"message": "Successfully logged out"}

@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Any:
    """修改密碼"""
    # 獲取當前用戶
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    auth_service = AuthService(db)
    auth_service.change_password(user, password_data.old_password, password_data.new_password)
    
    return {"message": "Password changed successfully"}

@router.post("/reset-password")
def request_password_reset(
    reset_request: ResetPasswordRequest,
    db: Session = Depends(get_db)
) -> Any:
    """請求密碼重設"""
    auth_service = AuthService(db)
    token = auth_service.create_password_reset_token(reset_request.email)
    
    # 這裡應該發送郵件，包含重設連結
    # TODO: 實現郵件服務
    
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password/confirm")
def confirm_password_reset(
    reset_confirm: ResetPasswordConfirm,
    db: Session = Depends(get_db)
) -> Any:
    """確認密碼重設"""
    auth_service = AuthService(db)
    auth_service.reset_password(reset_confirm.token, reset_confirm.new_password)
    
    return {"message": "Password reset successfully"}
