# app/core/permissions.py
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import oauth2_scheme, decode_token
from app.models.user import User
from app.models.auth import UserRole, RolePermission, Permission

class PermissionChecker:
    """權限檢查裝飾器"""
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    def __call__(self, 
                 token: str = Depends(oauth2_scheme),
                 db: Session = Depends(get_db)) -> User:
        # 解碼 token
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # 獲取用戶
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # 檢查權限
        user_permissions = self._get_user_permissions(user, db)
        
        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}"
                )
        
        return user
    
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
            payload = decode_token(token)
            user_id = payload.get("sub")
            
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