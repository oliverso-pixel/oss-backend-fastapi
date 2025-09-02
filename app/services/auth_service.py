# app/services/auth_service.py
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, hash_token, decode_token
from app.models.user import User
from app.models.auth import UserToken, TokenType, TokenBlacklist
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
        # 創建 tokens 時記錄 JTI
        access_jti = secrets.token_urlsafe(16)
        refresh_jti = secrets.token_urlsafe(16)
        
        access_token_data = {
            "sub": str(user.id),
            "jti": access_jti,
            "type": "access"
        }
        refresh_token_data = {
            "sub": str(user.id),
            "jti": refresh_jti,
            "type": "refresh"
        }

        access_token = create_access_token(data=access_token_data)
        refresh_token = create_refresh_token(data=refresh_token_data)
        
        # 儲存 refresh token 記錄
        refresh_token_record = UserToken(
            user_id=user.id,
            token_type=TokenType.REFRESH,
            token_hash=hash_token(refresh_token),
            jti=refresh_jti,  # 儲存 JTI
            device_info=device_info,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        )
        self.db.add(refresh_token_record)
        
        # 儲存 access token 記錄（包含 JTI）
        access_token_record = UserToken(
            user_id=user.id,
            token_type=TokenType.ACCESS,
            token_hash=hash_token(access_token),
            jti=access_jti,  # 儲存 JTI
            device_info=device_info,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        self.db.add(access_token_record)
        
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
        # 解碼 refresh token
        try:
            payload = decode_token(refresh_token)
            refresh_jti = payload.get("jti")
            user_id = payload.get("sub")
             
            # 檢查 refresh token 是否在黑名單中
            if refresh_jti and self._is_token_blacklisted(refresh_jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked"
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # 驗證 refresh token 記錄
        token_hash = hash_token(refresh_token)
        refresh_token_record = self.db.query(UserToken).filter(
            UserToken.token_hash == token_hash,
            UserToken.token_type == TokenType.REFRESH,
            UserToken.expires_at > datetime.utcnow(),
            UserToken.revoked_at.is_(None)
        ).first()
        
        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # 獲取用戶
        user = self.db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # 將所有舊的 access token 的 JTI 加入黑名單
        old_access_tokens = self.db.query(UserToken).filter(
            UserToken.user_id == user.id,
            UserToken.token_type == TokenType.ACCESS,
            UserToken.expires_at > datetime.utcnow(),
            UserToken.revoked_at.is_(None)
        ).all()
        
        for old_token in old_access_tokens:
            if old_token.jti:  # 如果有 JTI
                # 檢查是否已在黑名單中
                existing = self.db.query(TokenBlacklist).filter(
                    TokenBlacklist.jti == old_token.jti
                ).first()
                
                if not existing:
                    blacklist_entry = TokenBlacklist(
                        jti=old_token.jti,
                        user_id=user.id,
                        expires_at=old_token.expires_at,
                        reason="Token refreshed"
                    )
                    self.db.add(blacklist_entry)
            
            # 標記為已撤銷
            old_token.revoked_at = datetime.utcnow()
        
        # 撤銷當前的 refresh token
        refresh_token_record.revoked_at = datetime.utcnow()
        
        # 如果 refresh token 有 JTI，也加入黑名單
        if refresh_jti:
            refresh_blacklist = TokenBlacklist(
                jti=refresh_jti,
                user_id=user.id,
                expires_at=refresh_token_record.expires_at,
                reason="Refresh token used"
            )
            self.db.add(refresh_blacklist)
        
        # 創建新的 tokens
        new_access_jti = secrets.token_urlsafe(16)
        new_refresh_jti = secrets.token_urlsafe(16)
        
        access_token_data = {
            "sub": str(user.id),
            "jti": new_access_jti,
            "type": "access"
        }
        new_access_token = create_access_token(data=access_token_data)
        
        refresh_token_data = {
            "sub": str(user.id),
            "jti": new_refresh_jti,
            "type": "refresh"
        }
        new_refresh_token = create_refresh_token(data=refresh_token_data)
        
        # 儲存新的 token 記錄
        new_refresh_record = UserToken(
            user_id=user.id,
            token_type=TokenType.REFRESH,
            token_hash=hash_token(new_refresh_token),
            jti=new_refresh_jti,
            device_info=refresh_token_record.device_info,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        )
        self.db.add(new_refresh_record)
        
        new_access_record = UserToken(
            user_id=user.id,
            token_type=TokenType.ACCESS,
            token_hash=hash_token(new_access_token),
            jti=new_access_jti,
            device_info=refresh_token_record.device_info,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        self.db.add(new_access_record)
        
        # 提交所有更改
        self.db.commit()
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
    
    def logout(self, token: str, user_id: int):
        """登出 - 將 token 加入黑名單"""
        success = False

        try:
            # 解碼 token 以獲取 JTI 和過期時間
            payload = decode_token(token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            
            if jti and exp:
                # 將 token 加入黑名單
                existing = self.db.query(TokenBlacklist).filter(
                    TokenBlacklist.jti == jti
                ).first()
                
                if not existing:
                    # 將 token 加入黑名單
                    blacklist_entry = TokenBlacklist(
                        jti=jti,
                        user_id=user_id,
                        expires_at=datetime.fromtimestamp(exp),
                        reason="User logout"
                    )
                    self.db.add(blacklist_entry)
                    success = True
                else:
                    # Token 已經在黑名單中
                    print(f"Token {jti} already in blacklist")
                    success = True  # 仍然視為成功
                print(f"Token {jti} added to blacklist for user {user_id}")
        except HTTPException:
            # 如果是 HTTP 異常（如 token 過期），向上傳遞
            raise
        except Exception as e:
            print(f"Error adding token to blacklist: {str(e)}")
            # 繼續執行，不要因為黑名單失敗而阻止登出
        
        # 撤銷該用戶的所有 refresh tokens
        try:
            revoked_count = self.db.query(UserToken).filter(
                UserToken.user_id == user_id,
                UserToken.revoked_at.is_(None)
            ).update({"revoked_at": datetime.utcnow()})
            
            print(f"Revoked {revoked_count} refresh tokens for user {user_id}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error during logout: {str(e)}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete logout process"
            )
    
    def revoke_all_user_tokens(self, user_id: int, reason: str = "Password changed"):
        """撤銷用戶所有 tokens"""
        # 撤銷所有 refresh tokens
        self.db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.revoked_at.is_(None)
        ).update({"revoked_at": datetime.utcnow()})
        
        # 獲取用戶所有活躍的 token JTIs 並加入黑名單
        active_tokens = self.db.query(UserToken).filter(
            UserToken.user_id == user_id,
            UserToken.expires_at > datetime.utcnow()
        ).all()
        
        for token_record in active_tokens:
            # 如果我們儲存了 JTI，將它加入黑名單
            if token_record.token_type == TokenType.ACCESS:
                # token_hash 在這裡實際上是 JTI 的 hash
                # 為了簡化，我們可以創建一個虛擬的黑名單條目
                blacklist_entry = TokenBlacklist(
                    jti=f"revoked_{user_id}_{datetime.utcnow().timestamp()}",
                    user_id=user_id,
                    expires_at=token_record.expires_at,
                    reason=reason
                )
                self.db.add(blacklist_entry)
        
        self.db.commit()

    def change_password(self, user: User, old_password: str, new_password: str):
        """修改密碼"""
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )
        
        # 記錄密碼修改時間（重要：要在提交前設定）
        password_change_time = datetime.utcnow()
        
        # 更新密碼
        user.password_hash = get_password_hash(new_password)
        user.last_password_change = password_change_time
        
        # 立即提交密碼更改
        self.db.commit()
        
        # 將所有現有的 access tokens 加入黑名單
        # 獲取用戶所有未過期的 tokens
        active_tokens = self.db.query(UserToken).filter(
            UserToken.user_id == user.id,
            UserToken.expires_at > datetime.utcnow()
        ).all()
        
        # 為每個 token 創建黑名單條目
        for token_record in active_tokens:
            # 如果是 ACCESS token，使用其 hash 作為 JTI
            if token_record.token_type == TokenType.ACCESS:
                try:
                    # 創建一個唯一的 JTI
                    jti = f"pwd_change_{user.id}_{token_record.id}"
                    
                    # 檢查是否已存在
                    existing = self.db.query(TokenBlacklist).filter(
                        TokenBlacklist.jti == jti
                    ).first()
                    
                    if not existing:
                        blacklist_entry = TokenBlacklist(
                            jti=jti,
                            user_id=user.id,
                            expires_at=token_record.expires_at,
                            reason="Password changed"
                        )
                        self.db.add(blacklist_entry)
                except Exception as e:
                    print(f"Error blacklisting token {token_record.id}: {str(e)}")
        
        # 撤銷所有 refresh tokens
        self.db.query(UserToken).filter(
            UserToken.user_id == user.id,
            UserToken.revoked_at.is_(None)
        ).update({"revoked_at": password_change_time})
        
        # 提交所有更改
        self.db.commit()
        
        print(f"Password changed for user {user.id} at {password_change_time}")
    
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
        
        # 先提交密碼更改
        self.db.commit()
        
        # 然後撤銷所有 tokens
        self.revoke_all_user_tokens(user.id, reason="Password reset")

    def _is_token_blacklisted(self, jti: str) -> bool:
        """檢查 token 是否在黑名單中"""
        blacklisted = self.db.query(TokenBlacklist).filter(
            TokenBlacklist.jti == jti,
            TokenBlacklist.expires_at > datetime.utcnow()
        ).first()
        return blacklisted is not None
    
    def clean_expired_blacklist(self):
        """清理過期的黑名單記錄"""
        self.db.query(TokenBlacklist).filter(
            TokenBlacklist.expires_at < datetime.utcnow()
        ).delete()
        self.db.commit()