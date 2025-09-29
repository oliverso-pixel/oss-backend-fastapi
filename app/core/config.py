# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os
from functools import lru_cache

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
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # JWT 設定
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, env="REFRESH_TOKEN_EXPIRE_MINUTES")  # 7 天

    # 檔案上傳設定
    UPLOAD_DIR: str = "/mnt/www/html/oss"
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo"]

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="BACKEND_CORS_ORIGINS"
    )

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = Settings()

