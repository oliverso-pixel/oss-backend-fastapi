# app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, hash_token
from app.models.user import User
from app.models.auth import UserToken, TokenType
from app.schemas.auth import Token
import secrets

class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """驗證用戶"""
        user = self.db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
    
    def create_tokens(self, user: User, device_info: dict = None) -> Token:
        """創建訪問令牌和刷新令牌"""
        # 創建 tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # 儲存 refresh token
        token_record = UserToken(
            user_id=user.id,
            token_type=TokenType.REFRESH,
            token_hash=hash_token(refresh_token),
            device_info=device_info,
            expires_at=datetime.utcnow() + timedelta(minutes=10080)  # 7 days
        )
        self.db.add(token_record)
        
        # 更新最後登入時間
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    def refresh_access_token(self, refresh_token: str) -> Token:
        """刷新訪問令牌"""
        # 驗證 refresh token
        token_hash = hash_token(refresh_token)
        token_record = self.db.query(UserToken).filter(
            UserToken.token_hash == token_hash,
            UserToken.token_type == TokenType.REFRESH,
            UserToken.expires_at > datetime.utcnow(),
            UserToken.revoked_at.is_(None)
        ).first()
        
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # 獲取用戶
        user = token_record.user
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # 創建新的 access token
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # 更新 token 使用時間
        token_record.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    def revoke_token(self, token: str, user_id: int):
        """撤銷 token"""
        token_hash = hash_token(token)
        token_record = self.db.query(UserToken).filter(
            UserToken.token_hash == token_hash,
            UserToken.user_id == user_id
        ).first()
        
        if token_record:
            token_record.revoked_at = datetime.utcnow()
            self.db.commit()
    
    def revoke_all_user_tokens(self, user_id: int):
        """撤銷用戶所有 tokens"""
        self.db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.revoked_at.is_(None)
        ).update({"revoked_at": datetime.utcnow()})
        self.db.commit()
    
    def change_password(self, user: User, old_password: str, new_password: str):
        """修改密碼"""
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )
        
        user.password_hash = get_password_hash(new_password)
        user.last_password_change = datetime.utcnow()
        
        # 撤銷所有現有 tokens
        self.revoke_all_user_tokens(user.id)
        
        self.db.commit()
    
    def create_password_reset_token(self, email: str) -> str:
        """創建密碼重設令牌"""
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # 為了安全，即使用戶不存在也不要洩露信息
            return ""
        
        token = secrets.token_urlsafe(32)
        user.password_reset_token = hash_token(token)
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        self.db.commit()
        
        return token
    
    def reset_password(self, token: str, new_password: str):
        """重設密碼"""
        token_hash = hash_token(token)
        user = self.db.query(User).filter(
            User.password_reset_token == token_hash,
            User.password_reset_expires > datetime.utcnow()
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        user.password_hash = get_password_hash(new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.last_password_change = datetime.utcnow()
        
        # 撤銷所有現有 tokens
        self.revoke_all_user_tokens(user.id)
        
        self.db.commit()