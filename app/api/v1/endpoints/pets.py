# app/api/v1/endpoints/pets.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Any, Dict
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User, PrivacyLevel
from app.models.social import Friendship, FriendshipStatus
from app.models.pet import Pet
from app.schemas.pet import Species, Gender
from app.services.pet_service import PetService
from app.services.media_service import MediaService
from app.services.privacy_service import PrivacyService
from app.schemas.pet import (
    PetCreate, PetUpdate, PetResponse, PetListResponse, PetStatistics
)
from app.schemas.base import PaginationParams, PaginatedResponse

router = APIRouter()

@router.post("", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def create_pet(
    pet_data: PetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """創建新寵物"""
    pet_service = PetService(db)
    pet = pet_service.create_pet(current_user.id, pet_data)
    
    # 返回完整的寵物資料
    response = PetResponse.model_validate(pet)
    response.owner_username = current_user.username
    
    return response

@router.get("/", response_model=PaginatedResponse)
def get_my_pets(
    include_inactive: bool = Query(False, description="Include inactive pets"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取我的寵物列表"""
    pet_service = PetService(db)
    pets, total = pet_service.get_user_pets(
        user_id=current_user.id,
        include_inactive=include_inactive,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    # 轉換為響應格式
    pet_responses = []
    for pet in pets:
        response = PetResponse.model_validate(pet)
        response.owner_username = current_user.username
        pet_responses.append(response)
    
    return PaginatedResponse(
        items=pet_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/species", response_model=List[Dict[str, str]])
def get_species_list() -> Any:
    """獲取支援的寵物種類列表"""
    return [
        {"value": species.value, "label": species.value.title()}
        for species in Species
    ]

@router.get("/search", response_model=PaginatedResponse)
def search_pets(
    q: Optional[str] = Query(None, description="Search query"),
    species: Optional[Species] = Query(None, description="Filter by species"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """搜索寵物"""
    pet_service = PetService(db)

    # 基礎查詢，只查找活躍的寵物
    query = db.query(Pet).options(joinedload(Pet.owner)).filter(Pet.is_active == True)

    # 應用隱私過濾
    # 1. public 的寵物
    # 2. friends 的寵物，且飼主是當前用戶的好友
    # 3. private 的寵物，但飼主是當前用戶自己
    friend_subquery = db.query(Friendship.friend_id).filter(
        Friendship.user_id == current_user.id,
        Friendship.status == FriendshipStatus.ACCEPTED
    ).subquery()
    
    query = query.filter(
        (Pet.privacy_level == PrivacyLevel.PUBLIC) |
        ((Pet.privacy_level == PrivacyLevel.FRIENDS_ONLY) & (Pet.user_id.in_(friend_subquery))) |
        (Pet.user_id == current_user.id)
    )

    # 應用搜索條件
    if q:
        query = query.filter(Pet.name.ilike(f"%{q}%"))
    if species:
        query = query.filter(Pet.species == species)
    if user_id:
        query = query.filter(Pet.user_id == user_id)

    total = query.count()
    pets = query.order_by(Pet.created_at.desc()).offset(pagination.skip).limit(pagination.limit).all()

    # if not q:
    #     # 獲取所有活躍的寵物
    #     query = db.query(Pet).options(joinedload(Pet.owner)).filter(
    #         Pet.is_active == True
    #     )
        
    #     if species:
    #         query = query.filter(Pet.species == species)
        
    #     if user_id:
    #         query = query.filter(Pet.user_id == user_id)
        
    #     total = query.count()
    #     pets = query.offset(pagination.skip).limit(pagination.limit).all()
    # else:
    #     # 使用搜索功能
    #     pets, total = pet_service.search_pets(
    #         query=q,
    #         species=species,
    #         user_id=user_id,
    #         skip=pagination.skip,
    #         limit=pagination.limit
    #     )
    
    # 轉換為響應格式
    pet_responses = []
    for pet in pets:
        response = PetResponse.model_validate(pet)
        response.owner_username = pet.owner.username if pet.owner else None
        pet_responses.append(response)
    
    return PaginatedResponse(
        items=pet_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/{pet_id}", response_model=PetResponse)
def get_pet(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取寵物詳情"""
    pet_service = PetService(db)
    privacy_service = PrivacyService(db)

    pet = pet_service.get_pet(pet_id)
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )
    
    # 使用 privacy_service 檢查權限
    if not privacy_service.can_view_pet(current_user, pet):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this pet's profile"
        )
    
    # # 如果寵物不是公開的，只有擁有者可以查看
    # if not pet.is_active and pet.user_id != current_user.id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You don't have permission to view this pet"
    #     )
    
    response = PetResponse.model_validate(pet)
    owner = db.query(User).filter(User.id == pet.user_id).first()
    response.owner_username = owner.username if owner else None
    
    return response

@router.put("/{pet_id}", response_model=PetResponse)
def update_pet(
    pet_id: int,
    pet_update: PetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """更新寵物資料"""
    pet_service = PetService(db)
    pet = pet_service.update_pet(pet_id, current_user.id, pet_update)
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to update it"
        )
    
    response = PetResponse.model_validate(pet)
    response.owner_username = current_user.username
    
    return response

@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """刪除寵物（軟刪除）"""
    pet_service = PetService(db)
    success = pet_service.delete_pet(pet_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission to delete it"
        )

@router.post("/{pet_id}/restore", response_model=PetResponse)
def restore_pet(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """恢復已刪除的寵物"""
    pet_service = PetService(db)
    pet = pet_service.restore_pet(pet_id, current_user.id)
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or cannot be restored"
        )
    
    response = PetResponse.model_validate(pet)
    response.owner_username = current_user.username
    
    return response

@router.get("/{pet_id}/statistics", response_model=PetStatistics)
def get_pet_statistics(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取寵物統計資料"""
    pet_service = PetService(db)
    
    try:
        stats = pet_service.get_pet_statistics(pet_id, current_user.id)
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pet statistics: {str(e)}"
        )

@router.post("/{pet_id}/avatar", response_model=PetResponse)
async def upload_pet_avatar(
    pet_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """上傳寵物頭像"""
    # 檢查文件類型
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed"
        )
    
    # 檢查文件大小（最大 5MB）
    if file.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum size is 5MB"
        )
    
    pet_service = PetService(db)
    media_service = MediaService(db)
    
    # 檢查寵物是否存在且屬於當前用戶
    pet = pet_service.get_pet(pet_id, current_user.id)
    if not pet or pet.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission"
        )
    
    try:
        # 上傳圖片
        media = await media_service.upload_image(
            file=file,
            user_id=current_user.id,
            folder=f"avatars/pets/{pet_id}"
        )
        
        # 更新寵物頭像
        pet = pet_service.update_pet_avatar(pet_id, current_user.id, media.file_path)
        
        response = PetResponse.model_validate(pet)
        response.owner_username = current_user.username
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=PaginatedResponse)
def get_user_pets(
    user_id: int,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取指定用戶的寵物列表（只顯示活躍的）"""
    pet_service = PetService(db)
    
    # 檢查用戶是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 只顯示活躍的寵物（除非是查看自己的）
    include_inactive = (user_id == current_user.id)
    
    pets, total = pet_service.get_user_pets(
        user_id=user_id,
        include_inactive=include_inactive,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    # 轉換為響應格式
    pet_responses = []
    for pet in pets:
        response = PetResponse.model_validate(pet)
        response.owner_username = user.username
        pet_responses.append(response)
    
    return PaginatedResponse(
        items=pet_responses,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

