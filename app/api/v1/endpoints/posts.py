# app/api/v1/endpoints/posts.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User, PrivacyLevel
from app.models.post import Post, Visibility
from app.models.social import Comment, Like, Tag, PostTag
from app.models.media import Media
from app.services.post_service import PostService
from app.services.media_service import MediaService
from app.services.social_service import SocialService
from app.services.privacy_service import PrivacyService
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostDetailResponse,
    PostStatistics, TagResponse
)
from app.schemas.comment import (
    CommentCreate, CommentUpdate, CommentResponse, CommentSortOrder, CommentWithRepliesResponse, QuotedCommentInfo
)
from app.schemas.base import PaginationParams, PaginatedResponse

router = APIRouter()

def build_post_response(post, current_user: User, db: Session) -> PostResponse:
    """從資料庫物件建立 PostResponse"""
    social_service = SocialService(db)
    privacy_service = PrivacyService(db)
    
    # 處理 author
    author_data = privacy_service.get_user_visible_data(viewer=current_user, target_user=post.author)

    # 處理 tags - 只提取標籤名稱
    tags_data = [pt.tag.name for pt in post.tags]  # 改為只提取名稱
    
    # 處理 media
    media_data = []
    for pm in post.media:
        media_item = {
            "id": pm.media.id,
            "file_path": pm.media.file_path,
            "thumbnail_path": pm.media.thumbnail_path,
            "media_type": pm.media.media_type.value if hasattr(pm.media.media_type, 'value') else pm.media.media_type,
            "width": pm.media.width,
            "height": pm.media.height,
            "duration": pm.media.duration,
            "display_order": pm.display_order
        }
        media_data.append(media_item)

    # 計算統計數據
    like_count = len(post.likes) if post.likes else 0
    comment_count = len([c for c in post.comments if not c.is_deleted]) if post.comments else 0
    is_liked = any(like.user_id == current_user.id for like in post.likes) if post.likes else False

    response_data = {
        "id": post.id,
        "user_id": post.user_id,
        "content": post.content,
        "visibility": post.visibility.value if hasattr(post.visibility, 'value') else post.visibility,
        "tags": tags_data,  # 現在是字串列表
        "pet_id": post.pet_id,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "author": author_data.model_dump(),
        "media": media_data,
        "like_count": like_count,
        "comment_count": comment_count,
        "is_liked": is_liked,
        "view_count": post.view_count
    }
    
    return PostResponse.model_validate(response_data)

@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate, # PostCreate 應該包含 media_ids: List[int]
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """創建新貼文（媒體檔案需先通過 /api/v1/media/upload/post 上傳）"""
    post_service = PostService(db)
    privacy_service = PrivacyService(db)

    # 1. 在資料庫中創建貼文
    new_post = post_service.create_post(current_user.id, post_data)

    # 2. 決定要顯示哪一種作者個人資料
    # 因為是作者本人正在創建貼文，所以他看到的是自己的完整資料
    author_profile = privacy_service.get_user_visible_data(
        viewer=current_user,
        target_user=new_post.author
    )

    # 3. 手動組裝 API 回應的資料結構
    response_data = {
        "id": new_post.id,
        "user_id": new_post.user_id,
        "content": new_post.content,
        "visibility": new_post.visibility,
        "tags": [pt.tag.name for pt in new_post.tags],
        "pet_id": new_post.pet_id,
        "created_at": new_post.created_at,
        "updated_at": new_post.updated_at,
        "author": author_profile.model_dump() # 使用處理過的個人資料
    }

    # 4. 透過 PostResponse 模型驗證並回傳最終結果
    return PostResponse.model_validate(response_data)

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
    try:
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
        
        items = []
        for p in posts:
            try:
                item = build_post_response(p, current_user, db)
                items.append(item)
            except Exception as e:
                print(f"Error building post response for post {p.id}: {str(e)}")
                continue
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
            pages=(total + pagination.per_page - 1) // pagination.per_page
        )
    except Exception as e:
        print(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
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

@router.post("/{post_id}/comments/toggle", response_model=dict)
def toggle_post_comments(
    post_id: int,
    enabled: bool = Query(..., description="Enable or disable comments"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """開啟/關閉貼文評論功能"""
    post_service = PostService(db)
    success = post_service.toggle_comments(post_id, current_user.id, enabled)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to toggle comments for this post"
        )
    
    return {"message": f"Comments {'enabled' if enabled else 'disabled'} successfully"}

@router.get("/comments/search", response_model=PaginatedResponse)
def search_comments(
    q: Optional[str] = Query(None, description="Search query"),
    user_id: Optional[int] = Query(None, description="Filter by user"),
    post_id: Optional[int] = Query(None, description="Filter by post"),
    sort_by: CommentSortOrder = Query(CommentSortOrder.NEWEST),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """搜索評論"""
    post_service = PostService(db)
    comments, total = post_service.search_comments(
        query_str=q,
        user_id=user_id,
        post_id=post_id,
        sort_by=sort_by.value,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    items = [build_comment_response(c, current_user, db) for c in comments]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.post("/comments/{comment_id}/like", response_model=dict)
def like_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """按讚評論"""
    post_service = PostService(db)
    success = post_service.like_comment(comment_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment not found or already liked"
        )
    
    return {"message": "Comment liked successfully"}

@router.delete("/comments/{comment_id}/like", response_model=dict)
def unlike_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """取消按讚評論"""
    post_service = PostService(db)
    success = post_service.unlike_comment(comment_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found"
        )
    
    return {"message": "Comment unliked successfully"}

@router.delete("/comments/{comment_id}", response_model=dict)
def delete_comment(
    comment_id: int,
    reason: Optional[str] = Query(None, max_length=255, description="Deletion reason"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """刪除評論（軟刪除）"""
    post_service = PostService(db)
    success = post_service.delete_comment(comment_id, current_user.id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to delete it"
        )
    
    return {"message": "Comment deleted successfully"}

@router.get("/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: int,
    comment_sort: CommentSortOrder = Query(CommentSortOrder.NEWEST),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取貼文詳情"""
    post_service = PostService(db)
    privacy_service = PrivacyService(db)
    
    post = post_service.get_post(post_id, current_user)
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found or you don't have permission to view it"
        )
    
    # 構建基本響應
    post_data = build_post_response(post, current_user, db)
    
    # 將字典轉換為 PostDetailResponse
    response_data = post_data.model_dump() if hasattr(post_data, 'model_dump') else post_data
    
    # 添加詳細資訊
    response_data['user_can_edit'] = post.user_id == current_user.id
    response_data['user_can_delete'] = post.user_id == current_user.id or privacy_service.is_admin(current_user)
    response_data['comments_enabled'] = post.comments_enabled
    
    # 獲取排序後的評論
    comments = post_service.get_post_comments(post_id, comment_sort.value, current_user)
    
    # 構建評論樹狀結構
    comments_dict = {}
    root_comments = []
    
    for comment in comments:
        comment_response = build_comment_response(comment, current_user, db)
        # 確保有 replies 屬性
        if not hasattr(comment_response, 'replies'):
            comment_data = comment_response.model_dump() if hasattr(comment_response, 'model_dump') else comment_response
            comment_data['replies'] = []
            comment_response = CommentWithRepliesResponse(**comment_data)
        
        comments_dict[comment.id] = comment_response
        
        if comment.parent_id is None:
            root_comments.append(comment_response)
        else:
            parent = comments_dict.get(comment.parent_id)
            if parent and hasattr(parent, 'replies'):
                parent.replies.append(comment_response)
    
    response_data['comments'] = root_comments
    
    # 創建最終響應
    response = PostDetailResponse(**response_data)
    
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

def build_comment_response(comment: Comment, viewer: User, db: Session) -> CommentResponse:
    """從資料庫物件建立 CommentResponse"""
    privacy_service = PrivacyService(db)
    
    # 獲取評論者的可見資料
    user_data = privacy_service.get_user_visible_data(
        viewer=viewer,
        target_user=comment.user
    )
    
    # 處理引用的評論
    quoted_comment_data = None
    if comment.quoted_comment_id:
        quoted_user_data = privacy_service.get_user_visible_data(
            viewer=viewer,
            target_user=comment.quoted_comment.user
        )
        quoted_comment_data = QuotedCommentInfo(
            id=comment.quoted_comment.id,
            content=comment.quoted_comment.content if not comment.quoted_comment.is_deleted else "[已刪除]",
            user=quoted_user_data.model_dump(),
            is_deleted=comment.quoted_comment.is_deleted
        )
    
    # 檢查當前用戶是否已按讚
    is_liked = False
    if viewer:
        is_liked = any(like.user_id == viewer.id for like in comment.likes)
    
    # 處理已刪除的評論內容
    content = comment.content
    if comment.is_deleted:
        content = "[此評論已被刪除]"
        # 如果是管理員或刪除者，可以看到刪除原因
        if viewer and (privacy_service.is_admin(viewer) or comment.deleted_by == viewer.id):
            if comment.deletion_reason:
                content += f" (原因: {comment.deletion_reason})"
    
    response_data = {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "parent_id": comment.parent_id,
        "quoted_comment_id": comment.quoted_comment_id,
        "content": content,
        "like_count": comment.like_count,
        "reply_count": comment.reply_count,
        "last_reply_at": comment.last_reply_at,
        "is_deleted": comment.is_deleted,
        "deleted_by": comment.deleted_by,
        "deleted_at": comment.deleted_at,
        "deletion_reason": comment.deletion_reason if viewer and privacy_service.is_admin(viewer) else None,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "user": user_data.model_dump(),
        "quoted_comment": quoted_comment_data.model_dump() if quoted_comment_data else None,
        "is_liked": is_liked
    }
    
    return CommentResponse.model_validate(response_data)

@router.post("/{post_id}/comments", response_model=CommentResponse)
def add_comment(
    post_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """新增評論"""
    post_service = PostService(db)
    
    # 創建評論
    comment = post_service.add_comment(
        post_id=post_id,
        user_id=current_user.id,
        content=comment_data.content,
        parent_id=comment_data.parent_id
    )
    
    # 使用輔助函數建立響應
    return build_comment_response(comment, current_user, db)

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
    """獲取指定用戶的貼文（根據隱私設定返回）"""
    # 檢查目標用戶是否存在
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 檢查是否被封鎖
    social_service = SocialService(db)
    if social_service.is_blocked(user_id, current_user.id):
        # 被封鎖時返回空列表
        return PaginatedResponse(
            items=[],
            total=0,
            page=pagination.page,
            per_page=pagination.per_page,
            pages=0
        )
    
    post_service = PostService(db)
    posts, total = post_service.get_user_posts(
        user_id=user_id,
        viewer=current_user,
        skip=pagination.skip,
        limit=pagination.limit
    )
    
    # 如果是私密用戶且不是好友，返回空列表但保留統計數據
    if (target_user.privacy_level == PrivacyLevel.PRIVATE and 
        not social_service.is_friend(current_user.id, user_id) and
        current_user.id != user_id):
        # 可以在響應中包含一些統計信息
        return PaginatedResponse(
            items=[],
            total=0,  # 不顯示實際數量
            page=pagination.page,
            per_page=pagination.per_page,
            pages=0,
            # 可以添加額外的元數據
            meta={
                "privacy_restricted": True,
                "message": "This user's posts are only visible to friends"
            }
        )
    
    items = [build_post_response(p, current_user, db) for p in posts]
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=(total + pagination.per_page - 1) // pagination.per_page
    )

@router.get("/{post_id}/comments", response_model=List[CommentWithRepliesResponse])
def get_comments(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """獲取貼文的所有評論"""
    post_service = PostService(db)
    
    # 檢查貼文是否存在並且用戶有權限查看
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # 使用 _can_view_post 方法檢查權限
    if not post_service._can_view_post(post, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this post"
        )
    
    # 檢查評論是否開啟
    if not post.comments_enabled:
        return []  # 返回空列表而不是錯誤
    
    # 獲取評論
    comments = post_service.get_post_comments(post_id, viewer=current_user)
    
    # 構建評論樹狀結構
    comments_dict = {}
    root_comments = []
    
    for comment in comments:
        comment_response = build_comment_response(comment, current_user, db)
        
        # 轉換為字典以便修改
        if hasattr(comment_response, 'model_dump'):
            comment_data = comment_response.model_dump()
        else:
            comment_data = dict(comment_response)
        
        # 確保有 replies 欄位
        if 'replies' not in comment_data:
            comment_data['replies'] = []
        
        comment_with_replies = CommentWithRepliesResponse(**comment_data)
        comments_dict[comment.id] = comment_with_replies
        
        if comment.parent_id is None:
            root_comments.append(comment_with_replies)
    
    # 將回覆添加到父評論
    for comment in comments:
        if comment.parent_id and comment.parent_id in comments_dict:
            parent = comments_dict[comment.parent_id]
            child = comments_dict[comment.id]
            if child not in parent.replies:
                parent.replies.append(child)
    
    return root_comments

