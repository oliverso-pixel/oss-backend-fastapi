# app/schemas/mixins.py
from pydantic import model_validator
from typing import Optional, Any, Dict
from app.core.config import settings

class URLFieldMixin:
    """處理 URL 欄位的 Mixin"""
    
    @model_validator(mode='after')
    def build_urls(self) -> 'URLFieldMixin':
        """將所有 URL 相關欄位的相對路徑轉換為完整 URL"""
        url_fields = ['avatar_url', 'background_image_url', 'file_path', 'thumbnail_path']
        
        for field in url_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if value and isinstance(value, str):
                    # 如果已經是完整 URL，跳過
                    if not value.startswith(('http://', 'https://')):
                        # 清理路徑
                        clean_path = value.strip('/')
                        if clean_path.startswith('static/'):
                            clean_path = clean_path[7:]
                        
                        base_url = settings.BASE_URL.rstrip('/')
                        setattr(self, field, f"{base_url}/static/{clean_path}")
        
        return self
    
