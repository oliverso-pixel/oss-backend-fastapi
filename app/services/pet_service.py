# app/services/pet_service.py
from typing import List, Optional, Tuple, Dict
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from fastapi import HTTPException, status
from app.models.pet import Pet, Species, Gender
from app.models.user import User
from app.models.post import Post
from app.models.album import Album
from app.schemas.pet import PetCreate, PetUpdate, PetStatistics

class PetService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_pet(self, user_id: int, pet_data: PetCreate) -> Pet:
        """創建新寵物"""
        # 檢查用戶的寵物數量限制（可選）
        pet_count = self.db.query(Pet).filter(
            Pet.user_id == user_id,
            Pet.is_active == True
        ).count()
        
        if pet_count >= 10:  # 每個用戶最多 10 隻寵物
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have reached the maximum number of pets (10)"
            )
        
        # 創建寵物
        pet = Pet(
            user_id=user_id,
            **pet_data.model_dump()
        )
        
        self.db.add(pet)
        self.db.commit()
        self.db.refresh(pet)
        
        return pet
    
    def get_pet(self, pet_id: int, user_id: Optional[int] = None) -> Optional[Pet]:
        """獲取寵物資料"""
        query = self.db.query(Pet).filter(Pet.id == pet_id)
        
        # 如果指定了用戶，只返回該用戶的寵物
        if user_id:
            query = query.filter(Pet.user_id == user_id)
        
        pet = query.first()
        
        if pet and not pet.is_active and (not user_id or pet.user_id != user_id):
            return None  # 非擁有者無法查看已停用的寵物
        
        return pet
    
    def get_user_pets(self, user_id: int, include_inactive: bool = False, 
                     skip: int = 0, limit: int = 20) -> Tuple[List[Pet], int]:
        """獲取用戶的寵物列表"""
        query = self.db.query(Pet).filter(Pet.user_id == user_id)
        
        if not include_inactive:
            query = query.filter(Pet.is_active == True)
        
        # 按創建時間倒序排列
        query = query.order_by(Pet.created_at.desc())
        
        total = query.count()
        pets = query.offset(skip).limit(limit).all()
        
        return pets, total
    
    def update_pet(self, pet_id: int, user_id: int, pet_update: PetUpdate) -> Optional[Pet]:
        """更新寵物資料"""
        pet = self.get_pet(pet_id, user_id)
        
        if not pet:
            return None
        
        # 只有擁有者可以更新寵物資料
        if pet.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this pet"
            )
        
        update_data = pet_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(pet, field, value)
        
        self.db.commit()
        self.db.refresh(pet)
        
        return pet
    
    def delete_pet(self, pet_id: int, user_id: int) -> bool:
        """刪除寵物（軟刪除）"""
        pet = self.get_pet(pet_id, user_id)
        
        if not pet:
            return False
        
        if pet.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this pet"
            )
        
        # 軟刪除：設置為非活躍狀態
        pet.is_active = False
        
        # 同時將相關的貼文和相簿設為私有
        self.db.query(Post).filter(Post.pet_id == pet_id).update({
            "visibility": "private"
        })
        
        self.db.query(Album).filter(Album.pet_id == pet_id).update({
            "visibility": "private"
        })
        
        self.db.commit()
        
        return True
    
    def restore_pet(self, pet_id: int, user_id: int) -> Optional[Pet]:
        """恢復已刪除的寵物"""
        pet = self.db.query(Pet).filter(
            Pet.id == pet_id,
            Pet.user_id == user_id,
            Pet.is_active == False
        ).first()
        
        if not pet:
            return None
        
        pet.is_active = True
        self.db.commit()
        self.db.refresh(pet)
        
        return pet
    
    def get_pet_statistics(self, pet_id: int, user_id: int) -> PetStatistics:
        """獲取寵物統計資料"""
        pet = self.get_pet(pet_id, user_id)
        
        if not pet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pet not found"
            )
        
        # 計算年齡
        age_years = None
        if pet.birth_date:
            today = date.today()
            age_years = today.year - pet.birth_date.year - (
                (today.month, today.day) < (pet.birth_date.month, pet.birth_date.day)
            )
        
        # 統計貼文數
        total_posts = self.db.query(Post).filter(
            Post.pet_id == pet_id,
            Post.is_deleted == False
        ).count()
        
        # 統計相簿數
        total_albums = self.db.query(Album).filter(
            Album.pet_id == pet_id,
            Album.is_deleted == False
        ).count()
        
        # 最後活動時間
        last_post = self.db.query(Post).filter(
            Post.pet_id == pet_id,
            Post.is_deleted == False
        ).order_by(Post.created_at.desc()).first()
        
        last_activity = last_post.created_at if last_post else pet.created_at
        
        # 獲取用戶所有寵物的物種分布
        species_counts = self.db.query(
            Pet.species,
            func.count(Pet.id)
        ).filter(
            Pet.user_id == user_id,
            Pet.is_active == True
        ).group_by(Pet.species).all()
        
        species_distribution = {
            species.value: count for species, count in species_counts
        }
        
        return PetStatistics(
            total_pets=self.db.query(Pet).filter(
                Pet.user_id == user_id,
                Pet.is_active == True
            ).count(),
            active_pets=1 if pet.is_active else 0,
            species_distribution=species_distribution,
            avg_age_years=age_years,
            total_posts=total_posts,
            total_albums=total_albums,
            last_activity=last_activity
        )
    
    def search_pets(self, query: str, species: Optional[Species] = None,
               user_id: Optional[int] = None, skip: int = 0, 
               limit: int = 20) -> Tuple[List[Pet], int]:
        """搜索寵物"""
        search = f"%{query}%"
        q = self.db.query(Pet).options(joinedload(Pet.owner)).filter(
            Pet.is_active == True,
            Pet.name.ilike(search)
        )
        
        # 如果指定了物種
        if species:
            q = q.filter(Pet.species == species)
        
        # 如果指定了用戶
        if user_id:
            q = q.filter(Pet.user_id == user_id)
        
        # 先計算總數
        total = q.count()
        
        # 然後進行分頁
        pets = q.offset(skip).limit(limit).all()
        
        return pets, total
    
    def get_pet_by_name(self, user_id: int, pet_name: str) -> Optional[Pet]:
        """根據名字獲取用戶的寵物"""
        return self.db.query(Pet).filter(
            Pet.user_id == user_id,
            Pet.name == pet_name,
            Pet.is_active == True
        ).first()
    
    def update_pet_avatar(self, pet_id: int, user_id: int, avatar_url: str) -> Optional[Pet]:
        """更新寵物頭像"""
        pet = self.get_pet(pet_id, user_id)
        
        if not pet or pet.user_id != user_id:
            return None
        
        pet.avatar_url = avatar_url
        self.db.commit()
        self.db.refresh(pet)
        
        return pet
    
