# app/core/permissions.py
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import oauth2_scheme, decode_token
from app.models.user import User
from app.models.auth import UserRole, RolePermission, Permission, TokenBlacklist
from datetime import datetime, timedelta

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """獲取當前用戶（含 token 驗證）"""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        jti = payload.get("jti")
        iat = payload.get("iat")  # Token 發行時間
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 檢查黑名單 - 確保 JTI 存在
        if jti:
            blacklisted = db.query(TokenBlacklist).filter(
                TokenBlacklist.jti == jti
            ).first()
            if blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        # 獲取用戶
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 檢查 token 是否在密碼修改之前發行
        if user.last_password_change and iat:
            token_issued_at = datetime.fromtimestamp(iat)
            # 使用更精確的比較（考慮時區和微秒差異）
            if token_issued_at < user.last_password_change:
                print(f"Token issued before password change, rejecting")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired due to password change",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
        # 額外檢查：如果用戶有密碼修改記錄，檢查特定的黑名單
        if user.last_password_change:
            # 檢查是否有針對此用戶的密碼修改黑名單
            pwd_change_blacklist = db.query(TokenBlacklist).filter(
                TokenBlacklist.user_id == user.id,
                TokenBlacklist.reason == "Password changed",
                TokenBlacklist.blacklisted_at >= user.last_password_change - timedelta(seconds=1)
            ).first()
            
            if pwd_change_blacklist and iat:
                token_issued_at = datetime.fromtimestamp(iat)
                if token_issued_at < pwd_change_blacklist.blacklisted_at:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token expired due to password change",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

class PermissionChecker:
    """權限檢查裝飾器"""
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    def __call__(self, 
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> User:
        # 檢查權限
        user_permissions = self._get_user_permissions(current_user, db)
        
        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}"
                )
        
        return current_user
    
    def _get_user_permissions(self, user: User, db: Session) -> List[str]:
        """獲取用戶所有權限"""
        permissions = set()
        
        # 獲取角色權限
        user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
        for user_role in user_roles:
            role_permissions = db.query(RolePermission).filter(
                RolePermission.role_id == user_role.role_id
            ).all()
            for rp in role_permissions:
                permission = db.query(Permission).filter(
                    Permission.id == rp.permission_id
                ).first()
                if permission:
                    permissions.add(permission.name)
        
        return list(permissions)

# 便捷函數
def require_permission(permission: str):
    """單一權限要求"""
    return PermissionChecker([permission])

def require_any_permission(permissions: List[str]):
    """任一權限要求"""
    class AnyPermissionChecker(PermissionChecker):
        def __call__(self, token: str = Depends(oauth2_scheme), 
                     db: Session = Depends(get_db)) -> User:
            try:
                payload = decode_token(token)
                user_id = payload.get("sub")
                jti = payload.get("jti")
                
                if jti:
                    blacklisted = db.query(TokenBlacklist).filter(
                        TokenBlacklist.jti == jti,
                        TokenBlacklist.expires_at > datetime.utcnow()
                    ).first()
                    
                    if blacklisted:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Token has been revoked"
                        )
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            user_permissions = self._get_user_permissions(user, db)
            
            # 只要有任一權限即可
            if not any(perm in user_permissions for perm in self.required_permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied"
                )
            
            return user
    
    return AnyPermissionChecker(permissions)

# 預設權限裝飾器
is_authenticated = PermissionChecker([])
is_admin = PermissionChecker(["admin.access"])
is_merchant = PermissionChecker(["product.create"])