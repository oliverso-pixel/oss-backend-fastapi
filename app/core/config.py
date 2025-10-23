# app/core/config.py
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Pet Social Platform"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # 資料庫設定
    DATABASE_URL: str = Field(
        default="mysql+pymysql://root:password@localhost:3306/oss?charset=utf8mb4",
        env="DATABASE_URL"
    )

    # Redis 設定
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL"
    )

    # JWT 設定
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, env="REFRESH_TOKEN_EXPIRE_MINUTES")  # 7 天

    # 檔案上傳設定
    STATIC_DIR: str = Field(default="static", env="STATIC_DIR")
    UPLOAD_DIR: str = Field(default="/mnt/www/html/oss", env="UPLOAD_DIR")
    BASE_UPLOAD_PATH: str = Field(default="/mnt/www/html/oss", env="BASE_UPLOAD_PATH")
    
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo"]

    # URL 設定
    # BASE_URL: str = Field(default="http://192.168.50.103", env="BASE_URL")
    BASE_URL: str = Field(default="http://124.244.244.26:10380", env="BASE_URL")
    CDN_URL: Optional[str] = Field(default=None, env="CDN_URL")

    # 用戶儲存空間限制 (MB)
    USER_STORAGE_LIMIT_MB: float = Field(default=1024.0, env="USER_STORAGE_LIMIT_MB")  # 1GB

    @property
    def upload_path(self) -> Path:
        """獲取上傳路徑並確保存在"""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    # 檔案上傳限制
    MAX_FILE_SIZES: Dict[str, int] = {
        "avatar": 50 * 1024 * 1024,        # 50MB
        "background": 10 * 1024 * 1024,   # 10MB
        "post_image": 20 * 1024 * 1024,   # 20MB
        "post_video": 100 * 1024 * 1024,  # 100MB
        "chat_file": 50 * 1024 * 1024,    # 50MB
        "document": 10 * 1024 * 1024,     # 10MB
        "product_image": 10 * 1024 * 1024, # 10MB
    }
    
    # 允許的檔案類型
    ALLOWED_FILE_TYPES: Dict[str, List[str]] = {
        "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "video": ["video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo"],
        "document": ["application/pdf", "application/msword", 
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        "audio": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/webm"],
    }
    
    # 圖片處理設定
    IMAGE_SIZES: Dict[str, Dict[str, tuple]] = {
        "avatar": {
            "original": (800, 800),
            "medium": (400, 400),
            "small": (200, 200),
            "thumbnail": (100, 100)
        },
        "background": {
            "original": (1920, 1080),
            "medium": (1280, 720),
            "small": (640, 360)
        },
        "post": {
            "original": (2048, 2048),
            "medium": (1024, 1024),
            "small": (512, 512),
            "thumbnail": (200, 200)
        },
        "product": {
            "original": (1200, 1200),
            "medium": (600, 600),
            "small": (300, 300),
            "thumbnail": (150, 150)
        }
    }
    
    # 檔案保留政策
    FILE_RETENTION_DAYS: Dict[str, int] = {
        "temp": 1,           # 臨時檔案保留1天
        "chat": 365,         # 聊天檔案保留1年
        "deleted": 30,       # 已刪除檔案保留30天
    }

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://124.244.244.26:16231"],
        env="BACKEND_CORS_ORIGINS"
    )

    class Config:
        env_file = ".env"
        from_attributes = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

