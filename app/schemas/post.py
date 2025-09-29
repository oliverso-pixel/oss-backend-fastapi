# app/schemas/post.py
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.user import UserPublicProfile
from app.schemas.pet import PetResponse
from app.models.post import Visibility
from app.models.social import PostTag # 導入 PostTag

class PostBase(BaseSchema):
    """貼文基礎 Schema"""
    content: Optional[str] = Field(None, max_length=5000)
    visibility: Visibility = Visibility.PUBLIC
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    pet_id: Optional[int] = None
    
    @field_validator('content')
    def content_or_media_required(cls, v, values):
        # 至少需要內容或媒體（這個驗證會在 PostCreate 中進行）
        return v

class PostCreate(PostBase):
    """創建貼文 Schema"""
    tags: Optional[List[str]] = Field(None, max_items=10)
    media_ids: Optional[List[int]] = Field(None, max_items=10)
    
    @field_validator('media_ids')
    def validate_content_or_media(cls, v, values):
        if 'content' in values.data and not v and not values.data.get('content'):
            raise ValueError('Post must have either content or media')
        return v

class PostUpdate(BaseSchema):
    """更新貼文 Schema"""
    content: Optional[str] = Field(None, max_length=5000)
    visibility: Optional[Visibility] = None
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    tags: Optional[List[str]] = Field(None, max_items=10)
    media_ids: Optional[List[int]] = Field(None, max_items=10)

class MediaResponse(BaseSchema):
    """媒體響應 Schema"""
    id: int
    file_path: str
    thumbnail_path: Optional[str]
    media_type: str
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int]
    display_order: int

class TagResponse(TimestampSchema):
    """標籤響應 Schema"""
    id: int
    name: str
    usage_count: int

class CommentResponse(TimestampSchema):
    """評論響應 Schema"""
    id: int
    user: UserPublicProfile
    content: str
    parent_id: Optional[int]
    is_deleted: bool
    replies: Optional[List['CommentResponse']] = []

class PostResponse(PostBase, TimestampSchema):
    """貼文響應 Schema"""
    id: int
    user_id: int
    author: UserPublicProfile
    pet: Optional[PetResponse]
    view_count: int
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
    media: List[MediaResponse] = []
    tags: List[TagResponse] = []
    
    @computed_field
    @property
    def processed_tags(self) -> List[TagResponse]:
        if hasattr(self, 'tags') and all(isinstance(pt, PostTag) for pt in self.tags):
             return [TagResponse.model_validate(pt.tag) for pt in self.tags]
        return self.tags

    class Config:
        from_attributes = True

class PostDetailResponse(PostResponse):
    """貼文詳細響應（包含評論）"""
    comments: List[CommentResponse] = []
    user_can_edit: bool = False
    user_can_delete: bool = False

class PostStatistics(BaseSchema):
    """貼文統計"""
    view_count: int
    like_count: int
    comment_count: int
    share_count: int

class PostListResponse(BaseSchema):
    """貼文列表響應"""
    posts: List[PostResponse]
    total: int
    has_more: bool

# 更新 forward references
CommentResponse.model_rebuild()

