# app/api/va/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.security import oauth2_scheme, create_access_token, create_refresh_token, decode_token
from app.core.permissions import get_current_user
from app.schemas.auth import Token, LoginRequest, RefreshTokenRequest, ChangePasswordRequest, ResetPasswordRequest, ResetPasswordConfirm
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.privacy_service import PrivacyService
from app.models.user import User
from app.models.auth import TokenBlacklist, UserToken, TokenType

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

    privacy_service = PrivacyService(db)
    return privacy_service._get_full_user_data(user)

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
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
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
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if user_id:
            auth_service.logout(token, int(user_id))
            return {"message": "Successfully logged out"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
    except HTTPException as e:
        # 如果是 401 錯誤（token 無效或過期），直接傳遞
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            raise e
        # 其他 HTTP 異常也直接傳遞
        raise
    except Exception as e:
        print(f"Unexpected error during logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred during logout"
        )

@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),  # 使用 get_current_user
    db: Session = Depends(get_db)
) -> Any:
    """修改密碼"""
    auth_service = AuthService(db)
    auth_service.change_password(current_user, password_data.old_password, password_data.new_password)
    
    return {"message": "Password changed successfully. Please login again with your new password."}

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

@router.get("/token/status")
def check_token_status(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Any:
    """檢查 token 狀態（調試用）"""
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        user_id = payload.get("sub")
        iat = payload.get("iat")
        exp = payload.get("exp")
        
        # 檢查黑名單
        blacklisted = False
        if jti:
            bl_entry = db.query(TokenBlacklist).filter(
                TokenBlacklist.jti == jti
            ).first()
            blacklisted = bl_entry is not None
        
        # 檢查用戶狀態
        user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
        
        return {
            "token_valid": True,
            "jti": jti,
            "user_id": user_id,
            "issued_at": datetime.fromtimestamp(iat).isoformat() if iat else None,
            "expires_at": datetime.fromtimestamp(exp).isoformat() if exp else None,
            "blacklisted": blacklisted,
            "user_exists": user is not None,
            "user_active": user.is_active if user else None,
            "last_password_change": user.last_password_change.isoformat() if user and user.last_password_change else None,
            "token_issued_after_password_change": (
                datetime.fromtimestamp(iat) > user.last_password_change 
                if user and user.last_password_change and iat else None
            )
        }
    except Exception as e:
        return {
            "token_valid": False,
            "error": str(e)
        }
