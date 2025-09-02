# app/services/user_service.py
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User, PrivacyLevel
from app.models.auth import UserRole, Role
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_create: UserCreate) -> User:
        """創建新用戶"""
        user = User(
            username=user_create.username,
            email=user_create.email,
            password_hash=get_password_hash(user_create.password),
            display_name=user_create.display_name,
            bio=user_create.bio if hasattr(user_create, 'bio') else None,
            phone=user_create.phone if hasattr(user_create, 'phone') else None,
            privacy_level=user_create.privacy_level if hasattr(user_create, 'privacy_level') else PrivacyLevel.PUBLIC,
            show_email=False,
            show_phone=False,
            show_online_status=True,
            show_last_seen=True,
            is_active=True,
            is_verified=False
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # 分配默認角色
        default_role = self.db.query(Role).filter_by(name="user").first()
        if default_role:
            user_role = UserRole(user_id=user.id, role_id=default_role.id)
            self.db.add(user_role)
            self.db.commit()

        self.db.refresh(user)
        
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """根據ID獲取用戶"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根據用戶名獲取用戶"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根據郵箱獲取用戶"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_users(self, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        """獲取用戶列表"""
        query = self.db.query(User)
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        return users, total
    
    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """更新用戶信息"""
        user = self.get_user(user_id)
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        
        # 如果更新密碼，需要哈希處理
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """刪除用戶"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        return True
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """驗證用戶"""
        user = self.get_by_username(username)
        if not user:
            user = self.get_by_email(username)
        
        if not user or not verify_password(password, user.password_hash):
            return None
        
        return user
    
    def is_active(self, user: User) -> bool:
        """檢查用戶是否活躍"""
        return user.is_active
    
    def is_superuser(self, user: User) -> bool:
        """檢查用戶是否為超級用戶"""
        return any(role.role.name == "admin" for role in user.roles)
    
    # def search_public_users(self, query: str, skip: int = 0, limit: int = 20) -> List[User]:
    def search_public_users(self, q: str, skip: int, limit: int) -> Tuple[List[User], int]:
        """搜索公開用戶"""
        # search = f"%{query}%"
        # return self.db.query(User).filter(
        #     or_(
        #         User.username.ilike(search),
        #         User.display_name.ilike(search)
        #     ),
        #     User.privacy_level == PrivacyLevel.PUBLIC,
        #     User.is_active == True
        # ).offset(skip).limit(limit).all()

        # 基礎查詢，只查找活躍且隱私設置為 PUBLIC 的用戶
        query = self.db.query(User).filter(
            User.is_active == True,
            User.privacy_level == PrivacyLevel.PUBLIC
        )

        # 應用搜索過濾條件
        query = query.filter(
            User.username.ilike(f"%{q}%")
        )

        # 首先計算總數（在應用分頁之前）
        total = query.count()

        # 然後應用分頁和排序
        users = query.order_by(User.username).offset(skip).limit(limit).all()

        return users, total