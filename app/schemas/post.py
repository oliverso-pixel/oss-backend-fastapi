# app/schemas/post.py
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List, Union
from datetime import datetime
from app.schemas.base import BaseSchema, TimestampSchema
from app.schemas.user import UserPublicProfile
from app.schemas.pet import PetResponse
from app.schemas.mixins import URLFieldMixin
from app.models.post import Visibility
from app.models.social import PostTag
from app.schemas.user import UserPublicProfile, UserPrivateProfile, UserFriendViewProfile, UserFullResponse
from app.schemas.comment import CommentWithRepliesResponse

class PostBase(BaseSchema):
    content: Optional[str] = None
    visibility: Visibility = Visibility.PUBLIC
    tags: Optional[List[str]] = []
    pet_id: Optional[int] = None
    location: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    comments_enabled: bool = True

class PostCreate(PostBase):
    media_ids: Optional[List[int]] = []

class PostUpdate(BaseSchema):
    content: Optional[str] = None
    visibility: Optional[Visibility] = None
    tags: Optional[List[str]] = None
    location: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    media_ids: Optional[List[int]] = None

class MediaResponse(BaseSchema, URLFieldMixin):
    """媒體響應 Schema"""
    id: int
    file_path: str
    thumbnail_path: Optional[str]
    media_type: str
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int]
    display_order: int

    class Config:
        from_attributes = True

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

AuthorProfile = Union[UserPublicProfile, UserPrivateProfile, UserFriendViewProfile, UserFullResponse]

class PostResponse(PostBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    # 作者欄位現在可以是任何一種 AuthorProfile
    author: AuthorProfile
    media: Optional[List[MediaResponse]] = []
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
    view_count: int = 0
    
    class Config:
        from_attributes = True

class PostDetailResponse(PostResponse):
    """貼文詳細響應（包含評論）"""
    user_can_edit: bool = False
    user_can_delete: bool = False
    comments_enabled: bool = True
    # comments: List[CommentResponse] = []
    comments: List[CommentWithRepliesResponse] = []

    class Config:
        from_attributes = True

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

