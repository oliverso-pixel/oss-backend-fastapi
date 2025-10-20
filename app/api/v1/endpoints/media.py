# app/api/v1/endpoints/media.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Any, Dict
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.pet import Pet
from app.models.post import Post
from app.models.media import Media, PostMedia, MediaType
from app.services.media_service import MediaService
from app.services.pet_service import PetService
from app.services.post_service import PostService
from app.services.privacy_service import PrivacyService
from app.schemas.media import (
    MediaType, MediaUploadResponse, MediaStatistics, MediaBatchUploadResponse, MediaDetailResponse, MediaUrlResponse, MediaResponse, PostMediaResponse
)
from app.schemas.user import UserFullResponse
from app.schemas.pet import PetResponse
from app.schemas.base import PaginatedResponse
from app.core.config import settings
import json
import logging

router = APIRouter()

# ========== 用戶相關上傳 ==========

@router.post("/upload/user/avatar", response_model=MediaUploadResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    crop_data: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上傳用戶頭像"""
    try:
        media_service = MediaService(db)
        
        # 解析裁切資料
        crop_info = None
        if crop_data:
            try:
                crop_info = json.loads(crop_data)
            except Exception as e:
                print(f"Failed to parse crop data: {e}")
        
        # 準備處理選項
        processing_options = {
            "sizes": settings.IMAGE_SIZES.get("avatar", {
                "original": (800, 800),
                "medium": (400, 400),
                "small": (200, 200),
                "thumbnail": (100, 100)
            })
        }
        
        if crop_info:
            processing_options["crop"] = crop_info
        
        # 上傳檔案
        media = await media_service.upload_file(
            file=file,
            user_id=current_user.id,
            file_type="avatar",
            processing_options=processing_options
        )
        
        if not media:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload avatar"
            )
        
        # 刪除舊頭像
        if current_user.avatar_url and current_user.avatar_url.startswith("/static/"):
            try:
                await _delete_old_media(current_user.avatar_url, current_user.id, db)
            except Exception as e:
                print(f"Failed to delete old avatar: {e}")
        
        # 更新用戶頭像
        current_user.avatar_url = media_service.get_file_url(media.file_path, "medium")
        db.commit()
        
        # 構建響應
        response = _build_media_response(media, media_service)
        
        # 確保返回響應
        if not response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to build response"
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_user_avatar: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload avatar: {str(e)}"
        )

@router.post("/upload/user/background", response_model=MediaUploadResponse)
async def upload_user_background(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上傳用戶背景圖片"""
    media_service = MediaService(db)
    
    media = await media_service.upload_file(
        file=file,
        user_id=current_user.id,
        file_type="background"
    )
    
    # 刪除舊背景
    if current_user.background_image_url and current_user.background_image_url.startswith("/static/"):
        await _delete_old_media(current_user.background_image_url, current_user.id, db)
    
    # 更新用戶背景
    current_user.background_image_url = media_service.get_file_url(media.file_path, "medium")
    db.commit()
    
    return _build_media_response(media, media_service)

# ========== 寵物相關上傳 ==========

@router.post("/upload/pet/{pet_id}/avatar", response_model=MediaUploadResponse)
async def upload_pet_avatar(
    pet_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上傳寵物頭像"""
    # 檢查寵物擁有權
    pet_service = PetService(db)
    pet = pet_service.get_pet(pet_id, current_user.id)
    if not pet or pet.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found or you don't have permission"
        )
    
    media_service = MediaService(db)
    
    # 上傳檔案
    media = await media_service.upload_file(
        file=file,
        user_id=current_user.id,
        file_type="pet_avatar",
        related_id=pet_id
    )
    
    # 刪除舊頭像
    if pet.avatar_url and pet.avatar_url.startswith("/static/"):
        await _delete_old_media(pet.avatar_url, current_user.id, db)
    
    # 更新寵物頭像
    pet.avatar_url = media_service.get_file_url(media.file_path, "medium")
    db.commit()
    
    return _build_media_response(media, media_service)

@router.get("/my-files", response_model=PaginatedResponse)
def get_my_files(
    media_type: Optional[MediaType] = None,
    folder_type: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search in filename"),
    sort_by: str = Query("created_at", pattern="^(created_at|file_size|file_name)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """獲取我的檔案列表（包含 URL）"""
    query = db.query(Media).filter(
        Media.user_id == current_user.id,
        Media.deleted_at.is_(None)
    )
    
    if media_type:
        query = query.filter(Media.media_type == media_type)
    
    if folder_type:
        query = query.filter(Media.folder_type == folder_type)
    
    if search:
        query = query.filter(Media.file_name.ilike(f"%{search}%"))
    
    # 排序
    if sort_by == "created_at":
        order_field = Media.created_at
    elif sort_by == "file_size":
        order_field = Media.file_size
    else:
        order_field = Media.file_name
    
    if order == "desc":
        query = query.order_by(order_field.desc())
    else:
        query = query.order_by(order_field.asc())
    
    total = query.count()
    files = query.offset((page - 1) * per_page).limit(per_page).all()
    
    media_service = MediaService(db)
    
    items = []
    for file in files:
        # 構建完整的媒體響應
        item = MediaResponse(
            id=file.id,
            user_id=file.user_id,
            file_name=file.file_name,
            file_size=file.file_size,
            mime_type=file.mime_type,
            media_type=file.media_type.value,
            width=file.width,
            height=file.height,
            duration=file.duration,
            is_processed=file.is_processed,
            folder_type=file.folder_type,
            created_at=file.created_at,
            updated_at=file.updated_at,
            url=media_service.get_file_url(file.file_path),
            thumbnail_url=media_service.get_file_url(file.thumbnail_path) if file.thumbnail_path else None
        )
        items.append(item)
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )

# ========== 貼文相關上傳 ==========

@router.post("/upload/post", response_model=MediaBatchUploadResponse)
async def upload_post_media(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上傳貼文媒體（支援多檔案）"""
    media_service = MediaService(db)
    success_uploads = []
    failed_uploads = []
    
    for idx, file in enumerate(files[:10]):  # 限制最多10個檔案
        try:
            file_type = "post_video" if file.content_type.startswith("video/") else "post_image"
            
            media = await media_service.upload_file(
                file=file,
                user_id=current_user.id,
                file_type=file_type
            )
            
            success_uploads.append(_build_media_response(media, media_service))
        except Exception as e:
            failed_uploads.append({
                "file_name": file.filename,
                "error": str(e)
            })
    
    return MediaBatchUploadResponse(
        success=success_uploads,
        failed=failed_uploads,
        total=len(files),
        success_count=len(success_uploads),
        failed_count=len(failed_uploads)
    )

# ========== 聊天相關上傳 ==========

@router.post("/upload/chat/{room_id}", response_model=MediaUploadResponse)
async def upload_chat_file(
    room_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上傳聊天檔案"""
    # TODO: 檢查用戶是否為聊天室成員
    
    media_service = MediaService(db)
    
    media = await media_service.upload_file(
        file=file,
        user_id=current_user.id,
        file_type="chat_file",
        related_id=room_id
    )
    
    return _build_media_response(media, media_service)

# ========== 獲取媒體資訊 ==========

@router.get("/{media_id}", response_model=MediaDetailResponse)
def get_media_detail(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """獲取媒體詳細資訊"""
    media = db.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # 檢查權限
    if media.user_id != current_user.id and not media.is_public:
        privacy_service = PrivacyService(db)
        if not privacy_service.is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this media"
            )
    
    media_service = MediaService(db)
    
    return MediaDetailResponse(
        id=media.id,
        user_id=media.user_id,
        file_path=media.file_path,
        file_name=media.file_name,
        file_size=media.file_size,
        mime_type=media.mime_type,
        media_type=media.media_type.value,
        width=media.width,
        height=media.height,
        duration=media.duration,
        thumbnail_path=media.thumbnail_path,
        is_processed=media.is_processed,
        folder_type=media.folder_type,
        related_id=media.related_id,
        is_public=media.is_public,
        extra_data=media.extra_data,
        hash=media.hash,
        deleted_at=media.deleted_at,
        created_at=media.created_at,
        updated_at=media.updated_at,
        url=media_service.get_file_url(media.file_path),
        thumbnail_url=media_service.get_file_url(media.thumbnail_path) if media.thumbnail_path else None
    )

@router.get("/{media_id}/urls", response_model=MediaUrlResponse)
def get_media_urls(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """獲取媒體的所有尺寸 URL"""
    media = db.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # 檢查權限
    if media.user_id != current_user.id and not media.is_public:
        privacy_service = PrivacyService(db)
        if not privacy_service.is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this media"
            )
    
    media_service = MediaService(db)
    
    # 獲取所有可用的尺寸
    urls = {
        "original": media_service.get_file_url(media.file_path)
    }
    
    # 如果是圖片且有不同尺寸
    if media.media_type == MediaType.IMAGE and media.extra_data and "sizes" in media.extra_data:
        sizes = media.extra_data.get("sizes", {})
        for size_name in ["large", "medium", "small", "thumbnail"]:
            if size_name in sizes:
                urls[size_name] = media_service.get_file_url(media.file_path, size_name)
    
    # 如果有縮圖
    if media.thumbnail_path:
        urls["thumbnail"] = media_service.get_file_url(media.thumbnail_path)
    
    return MediaUrlResponse(**urls)

@router.post("/batch/urls", response_model=List[MediaUrlResponse])
def get_batch_media_urls(
    media_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量獲取媒體 URL"""
    if len(media_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 media IDs allowed"
        )
    
    media_list = db.query(Media).filter(Media.id.in_(media_ids)).all()
    
    media_service = MediaService(db)
    privacy_service = PrivacyService(db)
    is_admin = privacy_service.is_admin(current_user)
    
    results = []
    for media in media_list:
        # 檢查權限
        if media.user_id != current_user.id and not media.is_public and not is_admin:
            continue
        
        urls = {
            "original": media_service.get_file_url(media.file_path)
        }
        
        if media.media_type == MediaType.IMAGE and media.extra_data and "sizes" in media.extra_data:
            sizes = media.extra_data.get("sizes", {})
            for size_name in ["large", "medium", "small", "thumbnail"]:
                if size_name in sizes:
                    urls[size_name] = media_service.get_file_url(media.file_path, size_name)
        
        if media.thumbnail_path:
            urls["thumbnail"] = media_service.get_file_url(media.thumbnail_path)
        
        results.append(MediaUrlResponse(**urls))
    
    return results

# ========== 特定資源的媒體獲取 ==========

@router.get("/user/{user_id}/avatar", response_model=MediaUrlResponse)
def get_user_avatar_urls(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """獲取用戶頭像的所有尺寸 URL"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.avatar_url:
        return MediaUrlResponse(original=None)
    
    # 如果是外部 URL，直接返回
    if not user.avatar_url.startswith("/static/"):
        return MediaUrlResponse(original=user.avatar_url)
    
    # 從 URL 提取檔案路徑
    file_path = user.avatar_url.replace("/static/", "")
    media = db.query(Media).filter(
        Media.file_path == file_path,
        Media.user_id == user_id
    ).first()
    
    if not media:
        return MediaUrlResponse(original=user.avatar_url)
    
    media_service = MediaService(db)
    
    urls = {
        "original": media_service.get_file_url(media.file_path)
    }
    
    # 獲取不同尺寸
    if media.extra_data and "sizes" in media.extra_data:
        for size in ["large", "medium", "small", "thumbnail"]:
            if size in media.extra_data["sizes"]:
                urls[size] = media_service.get_file_url(media.file_path, size)
    
    return MediaUrlResponse(**urls)

@router.get("/pet/{pet_id}/avatar", response_model=MediaUrlResponse)
def get_pet_avatar_urls(
    pet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """獲取寵物頭像的所有尺寸 URL"""
    pet = db.query(Pet).filter(Pet.id == pet_id).first()
    
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found"
        )
    
    if not pet.avatar_url:
        return MediaUrlResponse(original=None)
    
    # 如果是外部 URL，直接返回
    if not pet.avatar_url.startswith("/static/"):
        return MediaUrlResponse(original=pet.avatar_url)
    
    # 從 URL 提取檔案路徑
    file_path = pet.avatar_url.replace("/static/", "")
    media = db.query(Media).filter(
        Media.file_path == file_path,
        Media.folder_type == "pet_avatar",
        Media.related_id == pet_id
    ).first()
    
    if not media:
        return MediaUrlResponse(original=pet.avatar_url)
    
    media_service = MediaService(db)
    
    urls = {
        "original": media_service.get_file_url(media.file_path)
    }
    
    # 獲取不同尺寸
    if media.extra_data and "sizes" in media.extra_data:
        for size in ["large", "medium", "small", "thumbnail"]:
            if size in media.extra_data["sizes"]:
                urls[size] = media_service.get_file_url(media.file_path, size)
    
    return MediaUrlResponse(**urls)

@router.get("/post/{post_id}/media", response_model=List[PostMediaResponse])
def get_post_media(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """獲取貼文的所有媒體"""
    # 檢查貼文是否存在
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # 檢查權限（使用 PostService 的權限檢查）
    post_service = PostService(db)
    if not post_service.can_view(current_user, post):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this post"
        )
    
    # 獲取貼文媒體
    post_media = db.query(PostMedia).filter(
        PostMedia.post_id == post_id
    ).order_by(PostMedia.display_order).all()
    
    media_service = MediaService(db)
    
    results = []
    for pm in post_media:
        media = pm.media
        results.append(PostMediaResponse(
            id=media.id,
            url=media_service.get_file_url(media.file_path),
            thumbnail_url=media_service.get_file_url(media.thumbnail_path) if media.thumbnail_path else None,
            media_type=media.media_type.value,
            width=media.width,
            height=media.height,
            duration=media.duration,
            display_order=pm.display_order
        ))
    
    return results

# ========== 通用功能 ==========

@router.post("/upload/temp", response_model=MediaUploadResponse)
async def upload_temp_file(
    file: UploadFile = File(...),
    session_id: str = Query(..., description="Session ID for grouping temp files"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """上傳臨時檔案"""
    media_service = MediaService(db)
    
    media = await media_service.upload_file(
        file=file,
        user_id=current_user.id,
        file_type="temp",
        subfolder=session_id
    )
    
    return MediaUploadResponse(
        id=media.id,
        url=media_service.get_file_url(media.file_path),
        temp_path=media.file_path,
        expires_in=86400  # 24小時
    )

@router.delete("/{media_id}")
async def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """刪除媒體檔案"""
    media_service = MediaService(db)
    
    success = await media_service.delete_media(media_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found or you don't have permission to delete it"
        )
    
    return {"message": "Media deleted successfully"}

@router.get("/statistics", response_model=MediaStatistics)
async def get_media_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """獲取用戶媒體統計"""
    stats = db.query(
        func.count(Media.id).label("total_count"),
        func.sum(Media.file_size).label("total_size")
    ).filter(
        Media.user_id == current_user.id,
        Media.deleted_at.is_(None)
    ).first()
    
    by_type = db.query(
        Media.media_type,
        func.count(Media.id)
    ).filter(
        Media.user_id == current_user.id,
        Media.deleted_at.is_(None)
    ).group_by(Media.media_type).all()
    
    by_folder = db.query(
        Media.folder_type,
        func.count(Media.id)
    ).filter(
        Media.user_id == current_user.id,
        Media.deleted_at.is_(None)
    ).group_by(Media.folder_type).all()
    
    total_size = stats.total_size or 0
    storage_used_mb = total_size / (1024 * 1024)
    
    return MediaStatistics(
        total_count=stats.total_count or 0,
        total_size=total_size,
        by_type={t.value: c for t, c in by_type},
        by_folder={f: c for f, c in by_folder if f},
        storage_used_mb=round(storage_used_mb, 2),
        storage_limit_mb=settings.USER_STORAGE_LIMIT_MB,
        storage_percentage=round((storage_used_mb / settings.USER_STORAGE_LIMIT_MB) * 100, 2)
    )

# ========== 輔助函數 ==========

def _build_media_response(media: Media, media_service: MediaService) -> MediaUploadResponse:
    """構建媒體上傳響應"""
    if not media:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create media record"
        )
    
    # 確保 media_type 是字串
    media_type_value = media.media_type.value if hasattr(media.media_type, 'value') else str(media.media_type)
    
    # 基本響應數據
    response_data = {
        "id": media.id,
        "url": media_service.get_file_url(media.file_path),
        "media_type": media_type_value,
        "file_size": media.file_size,
        "width": media.width,
        "height": media.height,
        "duration": media.duration
    }
    
    # 添加縮圖 URL（如果存在）
    if media.media_type == MediaType.IMAGE:
        if media.thumbnail_path:
            response_data["thumbnail_url"] = media_service.get_file_url(media.thumbnail_path)
        else:
            response_data["thumbnail_url"] = media_service.get_file_url(media.file_path, "thumbnail")
    
    # 添加不同尺寸的 URL
    sizes = {}
    if media.extra_data and "sizes" in media.extra_data:
        for size_name in ["original", "medium", "small", "thumbnail"]:
            if size_name in media.extra_data["sizes"]:
                sizes[size_name] = media_service.get_file_url(media.file_path, size_name)
    
    if sizes:
        response_data["sizes"] = sizes
    
    return MediaUploadResponse(**response_data)

async def _delete_old_media(old_url: str, user_id: int, db: Session):
    """刪除舊媒體檔案"""
    if old_url and old_url.startswith("/static/"):
        media_service = MediaService(db)
        file_path = old_url.replace("/static/", "")
        old_media = db.query(Media).filter(
            Media.file_path == file_path,
            Media.user_id == user_id
        ).first()
        if old_media:
            await media_service.delete_media(old_media.id, user_id)

