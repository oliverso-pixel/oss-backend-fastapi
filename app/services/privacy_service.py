# app/services/privacy_service.py
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session, joinedload
from app.models.user import User, PrivacyLevel
from app.models.pet import Pet
from app.models.social import Friendship, FriendshipStatus
# from app.schemas.user import UserPublicResponse, UserPrivateProfileResponse, UserFullResponse, UserFriendViewResponse
from app.schemas.user import UserPublicProfile, UserPrivateProfile, UserFullResponse, UserFriendViewProfile
from app.schemas.pet import PetPublicResponse, PetPrivateResponse
from app.services.social_service import SocialService
from datetime import datetime, timedelta

class PrivacyService:
    def __init__(self, db: Session):
        self.db = db
        self.social_service = SocialService(db)
    
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
    
    def is_vet(self, user: User) -> bool:
        """檢查用戶是否為獸醫"""
        if isinstance(user, User):
            # 檢查角色
            has_role = any(role.role.name == 'veterinarian' for role in user.roles)
            if has_role:
                return True
            # 也可以檢查 veterinarians 表中是否有記錄
            # from app.models.medical import Veterinarian
            # vet_record = self.db.query(Veterinarian).filter(Veterinarian.user_id == user.id).first()
            # return vet_record is not None
        elif isinstance(user, dict):
            roles = user.get('roles', [])
            return 'veterinarian' in roles
        return False
    
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

    # def get_user_visible_data(
    #     self, 
    #     viewer: Optional[User], 
    #     target_user: User
    # ) -> Union[UserPublicResponse, UserPrivateProfileResponse, UserFullResponse]:
    #     """根據新的隱私規則獲取可見的用戶資料"""
    #     viewer_id = viewer.id if viewer else None

    #     # 規則 1: 如果是自己或管理員，返回完整資料
    #     if viewer and (viewer_id == target_user.id or self.is_admin(viewer)):
    #         return self._get_full_user_data(target_user)
        
    #     # 規則 2: 如果目標用戶是公開的
    #     if target_user.privacy_level == PrivacyLevel.PUBLIC:
    #         return UserPublicResponse.model_validate(target_user)
        
    #     # 規則 3: 如果目標用戶是私密的
    #     if target_user.privacy_level == PrivacyLevel.PRIVATE:
    #         # 檢查查看者是否為好友
    #         is_friend = self.is_friend(viewer.id, target_user.id) if viewer else False
    #         if is_friend:
    #             # 好友可以看到公開資訊
    #             return UserFriendViewResponse.model_validate(target_user)
    #         else:
    #             # 非好友只能看到統計數據
    #             stats = self.social_service.get_user_social_stats(target_user.id)
    #             private_data = {
    #                 "id": target_user.id,
    #                 "username": target_user.username,
    #                 "display_name": target_user.display_name,
    #                 "avatar_url": target_user.avatar_url,
    #                 **stats
    #             }
    #             return UserPrivateProfileResponse(**private_data)
        
    #     # 預設情況，對於未知的 privacy_level，回傳最少資訊
    #     stats = self.social_service.get_user_social_stats(target_user.id)
    #     private_data = {
    #         "id": target_user.id,
    #         "username": target_user.username,
    #         "display_name": target_user.display_name,
    #         "avatar_url": target_user.avatar_url,
    #         **stats
    #     }
    #     return UserPrivateProfileResponse(**private_data)

    def get_user_visible_data(
        self, 
        viewer: Optional[User], 
        target_user: User
    ) -> Union[UserPublicProfile, UserPrivateProfile, UserFullResponse, UserFriendViewProfile]:
        """根據新的隱私規則獲取可見的用戶資料"""
        viewer_id = viewer.id if viewer else None

        # 規則 1: 如果是自己或管理員，返回完整資料
        if viewer and (viewer_id == target_user.id or self.is_admin(viewer)):
            full_data = UserFullResponse.model_validate(target_user).model_dump()
            stats = self.social_service.get_user_social_stats(target_user.id)
            full_data.update(stats)
            full_data['linked_roles'] = [role.role.name for role in target_user.roles if role.role]
            return UserFullResponse.model_validate(full_data)
        
        # 準備基礎資料
        stats = self.social_service.get_user_social_stats(target_user.id)
        linked_roles = [role.role.name for role in target_user.roles if role.role]
        base_data = {
            **target_user.__dict__,
            **stats,
            "linked_roles": linked_roles
        }

        # 規則 2: 如果目標用戶是公開的
        if target_user.privacy_level == PrivacyLevel.PUBLIC:
            return UserPublicProfile.model_validate(base_data)
        
        # 規則 3: 如果目標用戶是私密的
        if target_user.privacy_level == PrivacyLevel.PRIVATE:
            is_friend = self.social_service.is_friend(viewer.id, target_user.id) if viewer else False
            if is_friend:
                # 好友可以看到公開資訊 + 共同好友
                mutual_friends = self.social_service.get_mutual_friends_count(viewer.id, target_user.id)
                friend_data = {**base_data, "mutual_friends": mutual_friends}
                return UserFriendViewProfile.model_validate(friend_data)
            else:
                # 非好友只能看到私密資訊
                return UserPrivateProfile.model_validate(base_data)
        
        # 預設回退
        return UserPrivateProfile.model_validate(base_data)
    
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
            "background_image_url":user.background_image_url,
            "birth_date":user.birth_date,
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

        return UserFullResponse.model_validate(data)
        
        # return data
    
    def _is_user_online(self, user: User) -> bool:
        """判斷用戶是否在線（最近5分鐘有活動）"""
        if not user.last_login_at:
            return False
        
        now = datetime.utcnow()
        return (now - user.last_login_at) < timedelta(minutes=5)

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

    # def get_pet_data_for_viewer(
    #     self,
    #     viewer: Optional[User],
    #     pet: Pet
    # ) -> Union[PetPublicResponse, PetPrivateResponse, None]:
    #     """根據查看者的權限，返回適當的寵物資料模型，用於列表和搜尋結果。"""
    #     if not pet or not pet.owner:
    #         return None

    #     # 如果查看者被飼主封鎖，則完全看不到該寵物
    #     if viewer and self.social_service.is_blocked(pet.user_id, viewer.id):
    #         return None

    #     # 飼主或管理員總能看到完整資料
    #     if viewer and (viewer.id == pet.user_id or self.is_admin(viewer)):
    #         response = PetPublicResponse.model_validate(pet)
    #         response.owner_username = pet.owner.username
    #         return response

    #     # 如果寵物是公開的，返回完整公開資料
    #     if pet.privacy_level == PrivacyLevel.PUBLIC:
    #         response = PetPublicResponse.model_validate(pet)
    #         response.owner_username = pet.owner.username
    #         return response
        
    #     # 如果寵物是私密的，返回部分資料
    #     if pet.privacy_level == PrivacyLevel.PRIVATE:
    #         response = PetPrivateResponse.model_validate(pet)
    #         response.owner_username = pet.owner.username
    #         return response

    #     return None

    def get_pet_data_for_viewer(
        self,
        viewer: Optional[User],
        pet: Pet
    ) -> Union[PetPublicResponse, PetPrivateResponse, None]:
        """根據查看者的權限，返回適當的寵物資料模型"""
        if not pet or not pet.owner: return None
        if viewer and self.social_service.is_blocked(pet.user_id, viewer.id): return None
        if viewer and (viewer.id == pet.user_id or self.is_admin(viewer)):
            return PetPublicResponse.model_validate(pet)
        if pet.privacy_level == PrivacyLevel.PUBLIC:
            return PetPublicResponse.model_validate(pet)
        if pet.privacy_level == PrivacyLevel.PRIVATE:
            return PetPrivateResponse.model_validate(pet)
        return None

