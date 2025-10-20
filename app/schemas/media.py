# app/schemas/media.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from app.schemas.base import BaseSchema, TimestampSchema

class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"

class MediaBase(BaseSchema):
    """媒體基礎 Schema"""
    file_name: str
    file_size: int
    mime_type: str
    media_type: MediaType

class MediaCreate(MediaBase):
    """創建媒體 Schema"""
    folder_type: Optional[str] = None
    related_id: Optional[int] = None
    is_public: bool = True

class MediaUpdate(BaseSchema):
    """更新媒體 Schema"""
    file_name: Optional[str] = None
    is_public: Optional[bool] = None
    extra_data: Optional[Dict[str, Any]] = None

class MediaResponse(MediaBase, TimestampSchema):
    """媒體響應 Schema"""
    id: int
    user_id: int
    url: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    is_processed: bool
    folder_type: Optional[str] = None
    
    class Config:
        from_attributes = True

class MediaDetailResponse(MediaResponse):
    """媒體詳細響應 Schema"""
    file_path: str
    thumbnail_path: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    hash: Optional[str] = None
    related_id: Optional[int] = None
    is_public: bool
    deleted_at: Optional[datetime] = None

class MediaUploadResponse(BaseSchema):
    """媒體上傳響應 Schema"""
    id: int
    url: str
    thumbnail_url: Optional[str] = None
    media_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    sizes: Optional[Dict[str, str]] = Field(default_factory=dict, description="不同尺寸的URL")
    temp_path: Optional[str] = Field(None, description="臨時檔案路徑")
    expires_in: Optional[int] = Field(None, description="臨時檔案過期時間（秒）")
    
    class Config:
        from_attributes = True

class MediaBatchUploadResponse(BaseSchema):
    """批量上傳響應 Schema"""
    success: List[MediaUploadResponse]
    failed: List[Dict[str, str]] = Field(default_factory=list, description="失敗的檔案和原因")
    total: int
    success_count: int
    failed_count: int

class MediaUrlResponse(BaseSchema):
    """媒體 URL 響應"""
    original: str
    large: Optional[str] = None
    medium: Optional[str] = None
    small: Optional[str] = None
    thumbnail: Optional[str] = None

class MediaStatistics(BaseSchema):
    """媒體統計 Schema"""
    total_count: int
    total_size: int
    by_type: Dict[str, int]
    by_folder: Dict[str, int]
    storage_used_mb: float
    storage_limit_mb: Optional[float] = None
    storage_percentage: Optional[float] = None

class MediaSearchParams(BaseSchema):
    """媒體搜索參數"""
    media_type: Optional[MediaType] = None
    folder_type: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    min_size: Optional[int] = Field(None, ge=0)
    max_size: Optional[int] = Field(None, ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_public: Optional[bool] = None
    related_id: Optional[int] = None

class FileUploadConfig(BaseSchema):
    """檔案上傳配置"""
    allowed_types: List[str]
    max_file_size: int
    max_files: int = 10
    require_auth: bool = True
    auto_process: bool = True

class ImageProcessingOptions(BaseSchema):
    """圖片處理選項"""
    resize: bool = True
    max_width: Optional[int] = 2048
    max_height: Optional[int] = 2048
    quality: int = Field(85, ge=1, le=100)
    format: Optional[str] = None
    generate_thumbnail: bool = True
    thumbnail_size: tuple = (200, 200)
    generate_sizes: bool = True
    sizes: Optional[Dict[str, tuple]] = None

class VideoProcessingOptions(BaseSchema):
    """影片處理選項"""
    generate_thumbnail: bool = True
    thumbnail_at_percentage: int = Field(10, ge=0, le=100)
    max_duration: Optional[int] = None
    compress: bool = False
    target_bitrate: Optional[str] = None

class MediaFolder(BaseSchema):
    """媒體資料夾資訊"""
    name: str
    path: str
    file_count: int
    total_size: int
    created_at: datetime
    last_modified: datetime

# 用於不同功能的特定 Schema

class AvatarUploadRequest(BaseSchema):
    """頭像上傳請求"""
    crop_data: Optional[Dict[str, int]] = Field(None, description="裁切資訊 {x, y, width, height}")

class PostMediaResponse(BaseSchema):
    """貼文媒體響應"""
    id: int
    url: str
    thumbnail_url: Optional[str] = None
    media_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    display_order: int

class ChatFileUploadResponse(MediaUploadResponse):
    """聊天檔案上傳響應"""
    file_type: str  # image, video, document, audio
    preview_available: bool = False
    download_url: str

class ProductImageResponse(BaseSchema):
    """產品圖片響應"""
    id: int
    url: str
    thumbnail_url: str
    is_main: bool
    display_order: int
    alt_text: Optional[str] = None

class AlbumMediaResponse(BaseSchema):
    """相簿媒體響應"""
    id: int
    album_id: int
    media_id: int
    url: str
    thumbnail_url: Optional[str] = None
    media_type: str
    caption: Optional[str] = None
    display_order: int
    created_at: datetime

# 錯誤響應

class MediaError(BaseSchema):
    """媒體錯誤響應"""
    error_code: str
    message: str
    file_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class MediaQuota(BaseSchema):
    """用戶媒體配額"""
    user_id: int
    total_storage_mb: float
    used_storage_mb: float
    available_storage_mb: float
    file_count: int
    max_file_size_mb: float
    daily_upload_limit_mb: float
    daily_uploaded_mb: float

# 批量操作

class MediaBatchOperation(BaseSchema):
    """批量操作請求"""
    media_ids: List[int]
    operation: str  # delete, move, update_privacy, etc.
    params: Optional[Dict[str, Any]] = None

class MediaBatchOperationResult(BaseSchema):
    """批量操作結果"""
    success_count: int
    failed_count: int
    results: List[Dict[str, Any]]

# 媒體分享

class MediaShareRequest(BaseSchema):
    """媒體分享請求"""
    media_id: int
    share_type: str  # public_link, user, group
    target_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    password: Optional[str] = None

class MediaShareResponse(BaseSchema):
    """媒體分享響應"""
    share_id: str
    share_url: str
    expires_at: Optional[datetime] = None
    password_protected: bool = False

