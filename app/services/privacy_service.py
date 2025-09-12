# app/services/privacy_service.py
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session
from app.models.user import User, PrivacyLevel
from app.models.pet import Pet
from app.models.social import Friendship, FriendshipStatus
from app.schemas.user import UserPublicResponse, UserPrivateProfileResponse, UserFullResponse
from app.services.social_service import SocialService
from datetime import datetime, timedelta

class PrivacyService:
    def __init__(self, db: Session):
        self.db = db
        self.social_service = SocialService(db)
    
    def is_friend(self, user_id: int, target_user_id: int) -> bool:
        """檢查是否為好友關係"""
        if user_id == target_user_id:
            return True
        
        friendship = self.db.query(Friendship).filter(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == target_user_id)) |
            ((Friendship.user_id == target_user_id) & (Friendship.friend_id == user_id)),
            Friendship.status == 'accepted'
        ).first()
        
        return friendship is not None
    
    def is_admin(self, user: User) -> bool:
        """檢查是否為管理員"""
        # 處理 User 對象
        if isinstance(user, User):
            return any(role.role.name in ['admin', 'super_admin'] for role in user.roles)
        # 處理字典
        elif isinstance(user, dict):
            roles = user.get('roles', [])
            return any(role in ['admin', 'super_admin'] for role in roles)
        return False
    
    # def get_user_visible_data(
    #     self, 
    #     viewer: Optional[Union[User, dict]], 
    #     target_user: User
    # ) -> Dict[str, Any]:
    #     """根據隱私設置獲取可見的用戶資料"""
    #     # 獲取 viewer 的 ID
    #     viewer_id = None
    #     if viewer:
    #         if isinstance(viewer, User):
    #             viewer_id = viewer.id
    #         elif isinstance(viewer, dict):
    #             viewer_id = viewer.get('id')
        
    #     # 如果是自己，返回所有資料
    #     if viewer_id and viewer_id == target_user.id:
    #         return self._get_full_user_data(target_user)
        
    #     # 如果查看者是管理員，返回所有資料
    #     if viewer and self.is_admin(viewer):
    #         return self._get_full_user_data(target_user)
        
    #     # 根據目標用戶的隱私設置返回資料
    #     if target_user.privacy_level == PrivacyLevel.PUBLIC:
    #         return self._get_public_user_data(target_user, viewer)
    #     elif target_user.privacy_level == PrivacyLevel.FRIENDS_ONLY:
    #         if viewer_id and self.is_friend(viewer_id, target_user.id):
    #             return self._get_limited_user_data(target_user)
    #         else:
    #             return self._get_minimal_user_data(target_user)
    #     else:  # PRIVATE
    #         return self._get_minimal_user_data(target_user)

    def get_user_visible_data(
        self, 
        viewer: Optional[User], 
        target_user: User
    ) -> Union[UserPublicResponse, UserPrivateProfileResponse, UserFullResponse]:
        """根據新的隱私規則獲取可見的用戶資料"""
        viewer_id = viewer.id if viewer else None

        # 規則 1: 如果是自己或管理員，返回完整資料
        if viewer and (viewer_id == target_user.id or self.is_admin(viewer)):
            return self._get_full_user_data(target_user)
        
        # 規則 2: 根據目標用戶的隱私設定返回資料
        if target_user.privacy_level == PrivacyLevel.PUBLIC:
            # 返回公開資料
            return UserPublicResponse.model_validate(target_user)
        else: # PRIVACY_LEVEL == PRIVATE
            # 獲取統計數據
            stats = self.social_service.get_user_social_stats(target_user.id)
            private_data = {
                "id": target_user.id,
                "username": target_user.username,
                "display_name": target_user.display_name,
                "avatar_url": target_user.avatar_url,
                **stats # 將統計數據合併
            }
            return UserPrivateProfileResponse(**private_data)
    
    def _get_minimal_user_data(self, user: User) -> Dict[str, Any]:
        """獲取最少的用戶資料（隱私模式）"""
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "is_verified": user.is_verified,
            "created_at": user.created_at
        }
    
    def _get_public_user_data(self, user: User, viewer: Optional[Union[User, dict]] = None) -> Dict[str, Any]:
        """獲取公開的用戶資料"""
        data = self._get_minimal_user_data(user)
        data["bio"] = user.bio
        
        # 根據設置顯示在線狀態
        if user.show_online_status and viewer:
            data["is_online"] = self._is_user_online(user)
        
        # 根據設置顯示最後上線時間
        if user.show_last_seen and viewer:
            data["last_seen"] = user.last_login_at
        
        # 根據設置顯示聯絡資訊
        if user.show_email:
            data["email"] = user.email
        
        if user.show_phone:
            data["phone"] = user.phone
        
        return data
    
    def _get_limited_user_data(self, user: User) -> Dict[str, Any]:
        """獲取有限的用戶資料（好友可見）"""
        data = self._get_minimal_user_data(user)
        data["bio"] = user.bio
        
        if user.show_online_status:
            data["is_online"] = self._is_user_online(user)
        
        if user.show_last_seen:
            data["last_seen"] = user.last_login_at
        
        # 好友可以看到更多資訊
        if user.show_email:
            data["email"] = user.email
        
        if user.show_phone:
            data["phone"] = user.phone
        
        return data
    
    def _get_full_user_data(self, user: User) -> Dict[str, Any]:
        """獲取完整的用戶資料（自己或管理員）"""
        # 確保正確加載關聯數據
        if hasattr(user, 'roles') and user.roles:
            # 從 UserRole 對象中提取角色名稱
            role_names = []
            for user_role in user.roles:
                if hasattr(user_role, 'role') and user_role.role:
                    role_names.append(user_role.role.name)
        else:
            role_names = []
            
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "bio": user.bio,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "two_factor_enabled": user.two_factor_enabled,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "privacy_level": user.privacy_level.value if user.privacy_level else "public",
            "show_email": user.show_email,
            "show_phone": user.show_phone,
            "show_online_status": user.show_online_status,
            "show_last_seen": user.show_last_seen,
            "roles": role_names
        }
        
        if user.show_online_status:
            data["is_online"] = self._is_user_online(user)
        
        return data
    
    def _is_user_online(self, user: User) -> bool:
        """判斷用戶是否在線（最近5分鐘有活動）"""
        if not user.last_login_at:
            return False
        
        now = datetime.utcnow()
        return (now - user.last_login_at) < timedelta(minutes=5)
    
    # def filter_users_by_privacy(
    #     self, 
    #     users: List[User], 
    #     viewer: Optional[Union[User, dict]]
    # ) -> List[Dict[str, Any]]:
    #     """根據隱私設置過濾多個用戶的資料"""
    #     result = []
    #     for user in users:
    #         visible_data = self.get_user_visible_data(viewer, user)
    #         result.append(visible_data)
    #     return result

    def filter_users_by_privacy(
        self, 
        users: List[User], 
        viewer: Optional[User]
    ) -> List[Dict[str, Any]]:
        """根據隱私設置過濾多個用戶的資料"""
        result = []
        for user in users:
            visible_data = self.get_user_visible_data(viewer, user)
            result.append(visible_data)
        return result
    
    def can_view_pet(self, viewer: Optional[User], pet: Pet) -> bool:
        """檢查用戶是否可以查看指定的寵物"""
        # 寵物不存在或未啟用
        if not pet or not pet.is_active:
            # 只有主人或管理員可以查看未啟用的寵物
            if viewer and (pet.user_id == viewer.id or self.is_admin(viewer)):
                return True
            return False

        # 寵物主人和管理員永遠可以查看
        if viewer and (pet.user_id == viewer.id or self.is_admin(viewer)):
            return True

        # 檢查寵物的隱私設定
        if pet.privacy_level == PrivacyLevel.PUBLIC:
            return True
        
        # 對於非公開的寵物，必須是登入用戶
        if not viewer:
            return False

        if pet.privacy_level == PrivacyLevel.FRIENDS_ONLY:
            return self.is_friend(viewer.id, pet.user_id)

        # 對於 PRIVATE 的寵物，或不滿足上述條件的情況，預設為不可見
        return False

