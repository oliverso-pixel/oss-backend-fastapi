# app/api/v1/endpoints/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.post import Visibility
from app.services.post_service import PostService
from app.services.media_service import MediaService
from app.services.social_service import SocialService
from app.services.privacy_service import PrivacyService
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostDetailResponse,
    PostStatistics, CommentResponse, TagResponse
)
from app.schemas.base import PaginationParams, PaginatedResponse

router = APIRouter()

def build_post_response(post, current_user: User, db: Session) -> PostResponse:
    """從資料庫物件建立 PostResponse"""
    social_service = SocialService(db)
    privacy_service = PrivacyService(db)
    
    # 處理 author
    author_data = privacy_service.get_user_visible_data(viewer=current_user, target_user=post.author)

    # 處理 tags
    tags_data = [TagResponse.model_validate(pt.tag) for pt in post.tags]
    
    # 處理 media
    media_data = [
        {
            **pm.media.__dict__,
            "display_order": pm.display_order
        } for pm in post.media
    ]

    response_data = {
        **post.__dict__,
        "author": author_data,
        "tags": tags_data,
        "media": media_data,
        "like_count": len(post.likes),
        "comment_count": len([c for c in post.comments if not c.is_deleted]),
        "is_liked": any(like.user_id == current_user.id for like in post.likes)
    }
    
    return PostResponse.model_validate(response_data)


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """創建新貼文"""
    post_service = PostService(db)
    post = post_service.create_post(current_user.id, post_data)
    
    # 手動建立響應
    return build_post_response(post, current_user, db)

@router.get("/feed", response_model=PaginatedResponse)
def get_feed(
    include_friends: bool = Query(True, description="Include friends' posts"),
    include_following: bool = Query(True, description="Include following users' posts"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取動態消息"""
    post_service = PostService(db)
    posts, total = post_service.get_feed(
        user_id=current_user.id,
        include_friends=include_friends,
        include_following=include_following,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    items = [build_post_response(p, current_user, db) for p in posts]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/search", response_model=PaginatedResponse)
def search_posts(
    q: Optional[str] = Query(None, description="Search query"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    user_id: Optional[int] = Query(None, description="Filter by user"),
    pet_id: Optional[int] = Query(None, description="Filter by pet"),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """搜索貼文"""
    post_service = PostService(db)
    posts, total = post_service.search_posts(
        query_str=q,
        tag=tag,
        user_id=user_id,
        pet_id=pet_id,
        viewer=current_user,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    items = [build_post_response(p, current_user, db) for p in posts]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/trending/tags", response_model=List[TagResponse])
def get_trending_tags(
    days: int = Query(7, ge=1, le=30, description="Number of days to consider"),
    limit: int = Query(10, ge=1, le=50, description="Number of tags to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取熱門標籤"""
    post_service = PostService(db)
    tags = post_service.get_trending_tags(days=days, limit=limit)
    return [TagResponse.model_validate(tag) for tag in tags]

@router.get("/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取貼文詳情"""
    post_service = PostService(db)
    post = post_service.get_post(post_id, current_user)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or you don't have permission to view it"
        )
    
    # 構建詳細響應
    response = PostDetailResponse.model_validate(build_post_response(post, current_user, db))
    response.user_can_edit = post.user_id == current_user.id
    response.user_can_delete = post.user_id == current_user.id
    
    # 處理評論（構建樹狀結構）
    comments_dict = {}
    root_comments = []
    
    for comment in post.comments:
        if not comment.is_deleted or comment.user_id == current_user.id:
            comment_response = CommentResponse.model_validate(comment)
            comments_dict[comment.id] = comment_response
            
            if comment.parent_id is None:
                root_comments.append(comment_response)
            else:
                parent = comments_dict.get(comment.parent_id)
                if parent:
                    parent.replies.append(comment_response)
    
    response.comments = root_comments
    
    return response

@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """更新貼文"""
    post_service = PostService(db)
    post = post_service.update_post(post_id, current_user.id, post_update)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or you don't have permission to update it"
        )
    
    return build_post_response(post, current_user, db)

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """刪除貼文"""
    post_service = PostService(db)
    success = post_service.delete_post(post_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or you don't have permission to delete it"
        )

@router.get("/{post_id}/statistics", response_model=PostStatistics)
def get_post_statistics(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取貼文統計"""
    post_service = PostService(db)
    
    # 確認貼文存在且有權限查看
    post = post_service.get_post(post_id, current_user)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    return post_service.get_post_statistics(post_id)

# === 按讚功能 ===

@router.post("/{post_id}/like", response_model=dict)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """按讚貼文"""
    post_service = PostService(db)
    success = post_service.like_post(post_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post not found or already liked"
        )
    
    return {"message": "Post liked successfully"}

@router.delete("/{post_id}/like", response_model=dict)
def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """取消按讚"""
    post_service = PostService(db)
    success = post_service.unlike_post(post_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )
    
    return {"message": "Post unliked successfully"}

# === 評論功能 ===

@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: int,
    content: str = Query(..., min_length=1, max_length=1000),
    parent_id: Optional[int] = Query(None, description="Parent comment ID for replies"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """新增評論"""
    post_service = PostService(db)
    comment = post_service.add_comment(
        post_id=post_id,
        user_id=current_user.id,
        content=content,
        parent_id=parent_id
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post or parent comment not found"
        )
    
    return CommentResponse.model_validate(comment)

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """刪除評論"""
    post_service = PostService(db)
    success = post_service.delete_comment(comment_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to delete it"
        )

# === 用戶貼文 ===

@router.get("/users/{user_id}/posts", response_model=PaginatedResponse)
def get_user_posts(
    user_id: int,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取指定用戶的貼文"""
    post_service = PostService(db)
    posts, total = post_service.get_user_posts(
        user_id=user_id,
        viewer=current_user,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    items = [build_post_response(p, current_user, db) for p in posts]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

# === 媒體上傳（配合貼文使用）===

@router.post("/media/upload", response_model=dict)
async def upload_post_media(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """上傳貼文媒體檔案"""
    # 檢查文件類型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "video/mp4", "video/mpeg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
        )
    
    # 檢查文件大小
    max_size = 100 * 1024 * 1024  # 100MB
    if file.size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
        )
    
    media_service = MediaService(db)
    
    try:
        if file.content_type.startswith("image/"):
            media = await media_service.upload_image(
                file=file,
                user_id=current_user.id,
                folder="posts"
            )
        else:
            # TODO: 實現影片上傳
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Video upload not yet implemented"
            )
        
        return {
            "media_id": media.id,
            "file_path": media.file_path,
            "thumbnail_path": media.thumbnail_path,
            "media_type": media.media_type.value
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload media: {str(e)}"
        )

