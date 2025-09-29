# app/services/media_service.py
import os
import uuid
from datetime import datetime
from typing import Optional, List
from pathlib import Path
from PIL import Image
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models.media import Media, MediaType
from app.core.config import settings

class MediaService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(settings.UPLOAD_DIR)
    
    async def upload_image(self, file: UploadFile, user_id: int, 
                          folder: str = "images") -> Media:
        """上傳圖片"""
        # 生成唯一文件名
        ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        
        # 創建目錄結構
        date_path = datetime.now().strftime("%Y/%m/%d")
        relative_path = f"{folder}/{date_path}/{filename}"
        full_path = self.upload_dir / relative_path
        
        # 確保目錄存在
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存原始圖片
        content = await file.read()
        with open(full_path, "wb") as f:
            f.write(content)
        
        # 獲取圖片尺寸
        with Image.open(full_path) as img:
            width, height = img.size
            
            # 創建縮略圖
            thumbnail_path = self._create_thumbnail(img, full_path)
        
        # 創建媒體記錄
        media = Media(
            user_id=user_id,
            file_path=relative_path,
            file_name=file.filename,
            file_size=len(content),
            mime_type=file.content_type,
            media_type=MediaType.IMAGE,
            width=width,
            height=height,
            thumbnail_path=thumbnail_path,
            is_processed=True
        )
        
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)
        
        return media
    
    def _create_thumbnail(self, img: Image.Image, original_path: Path, 
                         size: tuple = (200, 200)) -> str:
        """創建縮略圖"""
        # 生成縮略圖路徑
        thumb_dir = original_path.parent / "thumbnails"
        thumb_dir.mkdir(exist_ok=True)
        
        thumb_filename = f"thumb_{original_path.name}"
        thumb_path = thumb_dir / thumb_filename
        
        # 創建縮略圖
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(thumb_path, quality=85)
        
        # 返回相對路徑
        return str(thumb_path.relative_to(self.upload_dir))

async def upload_post_media(self, files: List[UploadFile], user_id: int) -> List[Media]:
    """批量上傳貼文媒體"""
    media_list = []
    
    for file in files:
        if file.content_type.startswith("image/"):
            media = await self.upload_image(file, user_id, "posts")
        elif file.content_type.startswith("video/"):
            media = await self.upload_video(file, user_id, "posts")
        else:
            continue
        
        media_list.append(media)
    
    return media_list

async def upload_video(self, file: UploadFile, user_id: int, 
                      folder: str = "videos") -> Media:
    """上傳影片"""
    # 生成唯一文件名
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    
    # 創建目錄結構
    date_path = datetime.now().strftime("%Y/%m/%d")
    relative_path = f"{folder}/{date_path}/{filename}"
    full_path = self.upload_dir / relative_path
    
    # 確保目錄存在
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存原始影片
    content = await file.read()
    with open(full_path, "wb") as f:
        f.write(content)
    
    # TODO: 使用 ffmpeg 獲取影片資訊和生成縮圖
    # 這裡是簡化版本
    
    # 創建媒體記錄
    media = Media(
        user_id=user_id,
        file_path=relative_path,
        file_name=file.filename,
        file_size=len(content),
        mime_type=file.content_type,
        media_type=MediaType.VIDEO,
        is_processed=False  # 影片需要後續處理
    )
    
    self.db.add(media)
    self.db.commit()
    self.db.refresh(media)
    
    return media

def get_media_by_ids(self, media_ids: List[int], user_id: int) -> List[Media]:
    """根據ID列表獲取媒體檔案"""
    return self.db.query(Media).filter(
        Media.id.in_(media_ids),
        Media.user_id == user_id
    ).all()

