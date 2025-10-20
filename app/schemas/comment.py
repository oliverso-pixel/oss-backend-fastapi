# app/schemas/comment.py
from typing import Optional, List, Union, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.user import UserPublicProfile, UserPrivateProfile, UserFriendViewProfile, UserFullResponse

class CommentBase(BaseModel):
    """評論基礎模型"""
    content: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[int] = None
    quoted_comment_id: Optional[int] = None

class CommentCreate(CommentBase):
    """創建評論"""
    pass

class CommentUpdate(BaseModel):
    """更新評論"""
    content: str = Field(..., min_length=1, max_length=1000)

class QuotedCommentInfo(BaseModel):
    """被引用的評論資訊"""
    id: int
    content: str
    user: Union[UserPublicProfile, UserPrivateProfile, UserFriendViewProfile, UserFullResponse]
    is_deleted: bool
    
    class Config:
        from_attributes = True

class CommentUserInfo(BaseModel):
    """評論中的用戶簡要信息"""
    id: int
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class CommentResponse(CommentBase):
    """評論響應"""
    id: int
    post_id: int
    user_id: int
    is_deleted: bool = False
    deleted_by: Optional[int] = None
    deleted_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None
    like_count: int = 0
    reply_count: int = 0
    last_reply_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    user: Union[UserPublicProfile, UserPrivateProfile, UserFriendViewProfile, UserFullResponse]
    quoted_comment: Optional[QuotedCommentInfo] = None
    is_liked: bool = False  # 當前用戶是否已按讚
    
    class Config:
        from_attributes = True

class CommentWithRepliesResponse(CommentResponse):
    """包含回覆的評論響應"""
    # replies: List[CommentResponse] = []
    replies: List['CommentWithRepliesResponse'] = []

    class Config:
        from_attributes = True

CommentWithRepliesResponse.model_rebuild()

class CommentSearchQuery(BaseModel):
    """評論搜索參數"""
    content: Optional[str] = Field(None, description="搜索內容")
    user_id: Optional[int] = Field(None, description="按用戶ID過濾")
    post_id: Optional[int] = Field(None, description="按貼文ID過濾")

class CommentSortOrder(str, Enum):
    NEWEST = "newest"  # 最新
    OLDEST = "oldest"  # 最舊
    MOST_LIKES = "most_likes"  # 最多按讚
    MOST_REPLIES = "most_replies"  # 最多回覆
    RECENT_ACTIVITY = "recent_activity"  # 最新活動

class CommentDeleteRequest(BaseModel):
    """刪除評論請求"""
    reason: Optional[str] = Field(None, max_length=255, description="刪除原因")

