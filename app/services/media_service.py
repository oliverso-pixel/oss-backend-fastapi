# app/services/media_service.py
import os
import uuid
import hashlib
import shutil
import aiofiles
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from pathlib import Path
from PIL import Image
import cv2
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.models.media import Media, MediaType
from app.core.config import settings

class MediaService:
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.static_dir = Path(settings.STATIC_DIR)
        # self.base_path = Path(settings.BASE_UPLOAD_PATH)
        self.base_path = self.upload_dir
        self._ensure_directories()

    def _ensure_directories(self):
        """確保所有必要的目錄存在"""
        directories = [
            "avatars", "backgrounds", "posts/images", "posts/videos",
            "pets/avatars", "shop/products", "shop/merchants/logos",
            "shop/merchants/banners", "chat", "medical", "temp"
        ]
        for dir_path in directories:
            full_path = self.base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

    def get_file_url(self, file_path: str, size: Optional[str] = None) -> str:
        """獲取檔案 URL"""
        if not file_path:
            return None
        
        # 如果已經是完整 URL（外部連結），直接返回
        if file_path.startswith(('http://', 'https://')):
            return file_path
        
        # 清理路徑
        clean_path = self._clean_path(file_path)
        
        # 如果有 CDN，使用 CDN URL
        # base_url = settings.CDN_URL or settings.BASE_URL
        
        if size and size != 'original':
            clean_path = self._get_sized_path(clean_path, size)
        
        # 組合完整 URL
        base_url = settings.BASE_URL.rstrip('/')
        return f"{base_url}/static/{clean_path}"
    
    def get_relative_path(self, full_path: str) -> str:
        """從完整路徑提取相對路徑"""
        if isinstance(full_path, Path):
            full_path = str(full_path)
            
        # 移除 BASE_URL
        if full_path.startswith(settings.BASE_URL):
            full_path = full_path[len(settings.BASE_URL):].lstrip('/')
            
        # 移除 /static/ 前綴
        if full_path.startswith('/static/'):
            return full_path[8:]
        elif full_path.startswith('static/'):
            return full_path[7:]
            
        # 如果是絕對路徑，轉換為相對於 static 目錄的路徑
        try:
            path = Path(full_path)
            if path.is_absolute():
                relative = path.relative_to(self.static_dir)
                # return str(relative)
                return str(relative).replace('\\', '/')  # 確保使用正斜線
        except:
            pass
            
        return full_path
    
    def _clean_path(self, path: str) -> str:
        """清理路徑，移除不必要的前綴"""
        clean_path = path.strip('/')
        
        # 移除 static/ 前綴
        if clean_path.startswith('static/'):
            clean_path = clean_path[7:]
        
        # 移除 uploads/ 前綴（如果路徑以 uploads 開頭）
        if clean_path.startswith('uploads/'):
            clean_path = clean_path[8:]
            
        return clean_path
    
    def _get_sized_path(self, path: str, size: str) -> str:
        """獲取指定尺寸的檔案路徑"""
        path_parts = Path(path).parts
        if len(path_parts) >= 2:
            # 插入尺寸目錄
            # 例如: avatars/1/file.jpg -> avatars/1/medium/file.jpg
            new_parts = list(path_parts[:-1]) + [size] + [path_parts[-1]]
            return str(Path(*new_parts)).replace('\\', '/')
        return path
    
    async def upload_file(
        self, 
        file: UploadFile, 
        user_id: int,
        file_type: str,
        subfolder: Optional[str] = None,
        related_id: Optional[int] = None,
        generate_sizes: bool = True,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Media:
        """通用檔案上傳方法"""
        # 驗證檔案
        self._validate_file(file, file_type)
        
        # 生成檔案路徑
        file_info = self._generate_file_path(file, file_type, user_id, subfolder, related_id)
        
        # 保存原始檔案
        content = await file.read()
        await self._save_file(file_info['full_path'], content)
        
        # 處理檔案（縮圖、壓縮等）
        processed_info = await self._process_file(
            file_info['full_path'], 
            file_type, 
            generate_sizes,
            processing_options  # 傳遞處理選項
        )
        
        # 創建資料庫記錄
        media = self._create_media_record(
            user_id=user_id,
            file_info=file_info,
            file_size=len(content),
            mime_type=file.content_type,
            processed_info=processed_info
        )
        
        return media
    
    def _create_media_record(
        self,
        user_id: int,
        file_info: Dict[str, str],
        file_size: int,
        mime_type: str,
        processed_info: Dict[str, any]
    ) -> Media:
        """創建媒體記錄"""
        try:
            # 判斷媒體類型
            if mime_type.startswith("video/"):
                media_type = MediaType.VIDEO
            elif mime_type.startswith("image/"):
                media_type = MediaType.IMAGE
            elif mime_type.startswith("audio/"):
                media_type = MediaType.AUDIO
            else:
                media_type = MediaType.DOCUMENT

            # 確保路徑是相對路徑
            relative_path = self.get_relative_path(file_info['relative_path'])
            thumbnail_path = None
            if processed_info.get("thumbnail"):
                thumbnail_path = self.get_relative_path(processed_info["thumbnail"])
            
            # 處理 sizes 中的路徑
            if processed_info.get("sizes"):
                for size_name, size_path in processed_info["sizes"].items():
                    processed_info["sizes"][size_name] = self.get_relative_path(size_path)
            
            media = Media(
                user_id=user_id,
                file_path=relative_path,
                file_name=file_info['filename'],
                file_size=file_size,
                mime_type=mime_type,
                media_type=media_type,
                width=processed_info.get("width"),
                height=processed_info.get("height"),
                duration=processed_info.get("duration"),
                thumbnail_path=thumbnail_path,
                is_processed=True,
                extra_data=processed_info,  # 保存所有處理資訊
                folder_type=file_info.get('folder_type', 'general')
            )
            
            self.db.add(media)
            self.db.commit()
            self.db.refresh(media)
            
            return media
            
        except Exception as e:
            self.db.rollback()
            print(f"Error creating media record: {str(e)}")
            raise

    async def _process_image(
        self, 
        image_path: Path, 
        file_type: str,
        generate_sizes: bool,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, any]:
        """處理圖片檔案"""
        info = {"sizes": {}}
        
        with Image.open(image_path) as img:
            info["width"] = img.width
            info["height"] = img.height
            info["format"] = img.format
            
            # 處理裁切（如果提供了裁切資訊）
            if processing_options and processing_options.get("crop"):
                crop_data = processing_options["crop"]
                img = self._crop_image(img, crop_data)
                # 保存裁切後的圖片
                img.save(image_path, quality=95)
                info["width"] = img.width
                info["height"] = img.height
            
            # 使用提供的尺寸或默認尺寸
            if processing_options and "sizes" in processing_options:
                sizes_config = processing_options["sizes"]
            elif generate_sizes and file_type in settings.IMAGE_SIZES:
                sizes_config = settings.IMAGE_SIZES[file_type]
            else:
                sizes_config = None
            
            if sizes_config:
                base_dir = image_path.parent
                base_name = image_path.stem
                
                for size_name, dimensions in sizes_config.items():
                    if size_name == "original":
                        # 優化原圖
                        self._optimize_image(img, image_path, dimensions)
                        relative_path = str(image_path.relative_to(self.static_dir)).replace('\\', '/')
                        info["sizes"]["original"] = relative_path
                    else:
                        # 生成不同尺寸
                        size_dir = base_dir / size_name
                        size_dir.mkdir(exist_ok=True)
                        size_path = size_dir / f"{base_name}_{size_name}{image_path.suffix}"
                        
                        resized = self._resize_image(img, dimensions)
                        resized.save(size_path, quality=85, optimize=True)
                        
                        relative_path = str(size_path.relative_to(self.static_dir)).replace('\\', '/')
                        info["sizes"][size_name] = relative_path
        
        return info
    
    def get_media_url(self, file_path: str) -> str:
        """獲取媒體檔案的完整 URL"""
        if file_path:
            return f"/static/{file_path}"
        return None
    
    def _validate_file(self, file: UploadFile, file_type: str):
        """驗證檔案類型和大小"""
        # 檢查檔案類型
        allowed_types = []
        if file_type in ["avatar", "pet_avatar", "background", "post_image", "product_image"]:
            allowed_types = settings.ALLOWED_FILE_TYPES["image"]
        elif file_type in ["post_video", "chat_video"]:
            allowed_types = settings.ALLOWED_FILE_TYPES["video"]
        elif file_type == "document":
            allowed_types = settings.ALLOWED_FILE_TYPES["document"]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not allowed"
            )
        
        # 檢查檔案大小
        max_size = settings.MAX_FILE_SIZES.get(file_type, 10 * 1024 * 1024)
        if file.size and file.size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
            )
    
    def _generate_file_path(
        self, 
        file: UploadFile, 
        file_type: str,
        user_id: int,
        subfolder: Optional[str] = None,
        related_id: Optional[int] = None
    ) -> Dict[str, str]:
        """生成檔案路徑"""
        # 生成唯一檔名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_str = uuid.uuid4().hex[:8]
        file_ext = Path(file.filename).suffix.lower()
        
        # 根據檔案類型決定路徑
        if file_type == "avatar":
            relative_dir = f"avatars/{user_id}"
            filename = f"avatar_{timestamp}_{random_str}{file_ext}"
        
        elif file_type == "background":
            relative_dir = f"backgrounds/{user_id}"
            filename = f"bg_{timestamp}_{random_str}{file_ext}"
        
        elif file_type == "post_image":
            date_path = datetime.now().strftime("%Y/%m/%d")
            relative_dir = f"posts/{date_path}/images"
            filename = f"{related_id}_{timestamp}_{random_str}{file_ext}"
        
        elif file_type == "pet_avatar":
            relative_dir = f"pets/avatars/{related_id}"
            filename = f"pet_{timestamp}_{random_str}{file_ext}"
        
        elif file_type == "product_image":
            merchant_id = subfolder
            relative_dir = f"shop/products/{merchant_id}/{related_id}/main"
            filename = f"product_{timestamp}_{random_str}{file_ext}"
        
        elif file_type == "chat_file":
            file_category = self._get_file_category(file.content_type)
            month_path = datetime.now().strftime("%Y/%m")
            relative_dir = f"chat/{month_path}/{file_category}/{related_id}"
            filename = f"chat_{timestamp}_{random_str}{file_ext}"
        
        else:
            relative_dir = f"temp/{user_id}"
            filename = f"temp_{timestamp}_{random_str}{file_ext}"
        
        # 完整路徑
        full_dir = self.base_path / relative_dir
        full_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "relative_dir": relative_dir,
            "filename": filename,
            "relative_path": f"{relative_dir}/{filename}",
            "full_path": full_dir / filename
        }
    
    async def _save_file(self, path: Path, content: bytes):
        """保存檔案"""
        async with aiofiles.open(path, 'wb') as f:
            await f.write(content)
    
    async def _process_file(
        self, 
        file_path: Path, 
        file_type: str,
        generate_sizes: bool,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, any]:
        """處理檔案（生成縮圖、獲取資訊等）"""
        processed_info = {}
        
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            # 處理圖片
            processed_info = await self._process_image(
                file_path, 
                file_type, 
                generate_sizes,
                processing_options
            )
        
        elif file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mpeg']:
            # 處理影片
            processed_info = await self._process_video(file_path)
        
        return processed_info
    
    def _resize_image(self, img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
        """調整圖片大小"""
        # 保持比例縮放
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img
    
    def _optimize_image(self, img: Image.Image, path: Path, max_size: Tuple[int, int]):
        """優化圖片"""
        # 轉換格式
        if img.mode in ('RGBA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                rgb_img.paste(img, mask=img.split()[-1])
            else:
                rgb_img.paste(img)
            img = rgb_img
        
        # 調整大小
        if img.width > max_size[0] or img.height > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 保存優化後的圖片
        img.save(path, 'JPEG', quality=85, optimize=True)
    
    async def _process_video(self, video_path: Path) -> Dict[str, any]:
        """處理影片檔案"""
        info = {}
        
        # 使用 OpenCV 獲取影片資訊
        cap = cv2.VideoCapture(str(video_path))
        
        if cap.isOpened():
            info["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            info["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            info["fps"] = cap.get(cv2.CAP_PROP_FPS)
            info["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            info["duration"] = info["frame_count"] / info["fps"] if info["fps"] > 0 else 0
            
            # 生成縮圖
            thumbnail_path = await self._generate_video_thumbnail(cap, video_path)
            if thumbnail_path:
                info["thumbnail"] = str(thumbnail_path.relative_to(self.base_path))
            
            cap.release()
        
        return info
    
    def _crop_image(self, img: Image.Image, crop_data: Dict[str, int]) -> Image.Image:
        """裁切圖片"""
        x = crop_data.get("x", 0)
        y = crop_data.get("y", 0)
        width = crop_data.get("width", img.width)
        height = crop_data.get("height", img.height)
        
        # 確保裁切範圍在圖片內
        x = max(0, min(x, img.width))
        y = max(0, min(y, img.height))
        width = min(width, img.width - x)
        height = min(height, img.height - y)
        
        return img.crop((x, y, x + width, y + height))
    
    async def _generate_video_thumbnail(self, cap, video_path: Path) -> Optional[Path]:
        """生成影片縮圖"""
        # 跳到影片的 10% 位置
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 10)
        
        ret, frame = cap.read()
        if ret:
            thumb_dir = video_path.parent / "thumbnails"
            thumb_dir.mkdir(exist_ok=True)
            thumb_path = thumb_dir / f"{video_path.stem}_thumb.jpg"
            
            cv2.imwrite(str(thumb_path), frame)
            return thumb_path
        
        return None
    
    def _get_file_category(self, mime_type: str) -> str:
        """根據 MIME 類型判斷檔案分類"""
        if mime_type.startswith("image/"):
            return "images"
        elif mime_type.startswith("video/"):
            return "videos"
        elif mime_type.startswith("audio/"):
            return "voice"
        else:
            return "documents"
    
    async def cleanup_temp_files(self):
        """清理臨時檔案"""
        temp_dir = self.base_path / "temp"
        cutoff_time = datetime.now() - timedelta(days=settings.FILE_RETENTION_DAYS["temp"])
        
        for user_dir in temp_dir.iterdir():
            if user_dir.is_dir():
                for file_path in user_dir.rglob("*"):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            file_path.unlink()
    
    async def move_to_permanent(self, temp_path: str, permanent_type: str, **kwargs) -> Media:
        """將臨時檔案移動到永久儲存"""
        temp_full_path = self.base_path / temp_path
        if not temp_full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Temporary file not found"
            )
        
        # 讀取臨時檔案
        with open(temp_full_path, 'rb') as f:
            content = f.read()
        
        # 創建 UploadFile 物件
        file = UploadFile(
            filename=temp_full_path.name,
            file=None
        )
        file.file = content
        file.content_type = self._guess_content_type(temp_full_path)
        
        # 上傳到永久位置
        media = await self.upload_file(
            file=file,
            file_type=permanent_type,
            **kwargs
        )
        
        # 刪除臨時檔案
        temp_full_path.unlink()
        
        return media
    
    def _guess_content_type(self, file_path: Path) -> str:
        """猜測檔案的 MIME 類型"""
        import mimetypes
        content_type, _ = mimetypes.guess_type(str(file_path))
        return content_type or "application/octet-stream"
    
    async def delete_media(self, media_id: int, user_id: int) -> bool:
        """刪除媒體檔案"""
        media = self.db.query(Media).filter(
            Media.id == media_id,
            Media.user_id == user_id
        ).first()
        
        if not media:
            return False
        
        # 刪除實體檔案
        if media.file_path:
            file_path = self.upload_dir / media.file_path
            if file_path.exists():
                file_path.unlink()
        
        # 刪除縮略圖
        if media.thumbnail_path:
            thumb_path = self.upload_dir / media.thumbnail_path
            if thumb_path.exists():
                thumb_path.unlink()
        
        # 刪除資料庫記錄
        self.db.delete(media)
        self.db.commit()
        
        return True

    