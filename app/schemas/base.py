# app/schemas/base.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    """基礎 Schema"""
    model_config = ConfigDict(from_attributes=True)

class TimestampSchema(BaseSchema):
    """包含時間戳的 Schema"""
    created_at: datetime
    updated_at: datetime

class PaginationParams(BaseSchema):
    """分頁參數"""
    page: int = 1
    per_page: int = 20
    
    @property
    def skip(self):
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self):
        return self.per_page

class PaginatedResponse(BaseSchema):
    """分頁響應"""
    items: list
    total: int
    page: int
    per_page: int
    pages: int

