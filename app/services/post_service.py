# app/services/post_service.py
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func, asc
from fastapi import HTTPException, status
from app.models.post import Post, Visibility
from app.models.user import User, PrivacyLevel
from app.models.pet import Pet
from app.models.media import Media, PostMedia
from app.models.social import Tag, PostTag, Like, Comment, CommentLike, Friendship, FriendshipStatus
from app.schemas.post import PostCreate, PostUpdate, PostResponse, PostStatistics
from app.services.notification_service import NotificationService
from app.services.privacy_service import PrivacyService
from app.services.social_service import SocialService

class PostService:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
        self.privacy_service = PrivacyService(db)
        self.social_service = SocialService(db)

    def can_view(self, viewer: Optional[User], post: Post) -> bool:
        """檢查用戶是否可以查看貼文"""
        return self._can_view_post(post, viewer)
    
    def create_post(self, user_id: int, post_data: PostCreate) -> Post:
        """創建新貼文"""
        # 如果指定了寵物，檢查擁有權
        if post_data.pet_id:
            pet = self.db.query(Pet).filter(
                Pet.id == post_data.pet_id,
                Pet.user_id == user_id,
                Pet.is_active == True
            ).first()
            
            if not pet:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pet not found or you don't own this pet"
                )
        
        # 創建貼文
        post = Post(
            user_id=user_id,
            pet_id=post_data.pet_id,
            content=post_data.content,
            visibility=post_data.visibility,
            location=post_data.location if hasattr(post_data, 'location') else None,
            latitude=post_data.latitude if hasattr(post_data, 'latitude') else None,
            longitude=post_data.longitude if hasattr(post_data, 'longitude') else None,
            comments_enabled=post_data.comments_enabled
        )
        
        self.db.add(post)
        self.db.flush()
        
        # 處理標籤
        if post_data.tags:
            self._process_tags(post, post_data.tags)
        
        # 處理媒體檔案
        if hasattr(post_data, 'media_ids') and post_data.media_ids:
            self._attach_media(post, post_data.media_ids, user_id)
        
        self.db.commit()
        self.db.refresh(post)
        
        # 發送通知給關注者（如果是公開貼文）
        if post.visibility == Visibility.PUBLIC:
            self._notify_followers(post)
        
        return post
    
    def get_post(self, post_id: int, viewer: Optional[User] = None) -> Optional[Post]:
        """獲取貼文（考慮隱私設置）"""
        post = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.pet),
            joinedload(Post.media).joinedload(PostMedia.media),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.likes),
            joinedload(Post.comments).joinedload(Comment.user)
        ).filter(
            Post.id == post_id,
            Post.is_deleted == False
        ).first()
        
        if not post:
            return None
        
        # 檢查查看權限
        if not self._can_view_post(post, viewer):
            return None
        
        # 增加查看次數
        if viewer and viewer.id != post.user_id:
            post.view_count += 1
            self.db.commit()
        
        return post
    
    def update_post(self, post_id: int, user_id: int, post_update: PostUpdate) -> Optional[Post]:
        """更新貼文"""
        post = self.db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id,
            Post.is_deleted == False
        ).first()
        
        if not post:
            return None
        
        # 更新基本資訊
        update_data = post_update.model_dump(exclude_unset=True, exclude={'tags', 'media_ids'})
        for field, value in update_data.items():
            setattr(post, field, value)
        
        # 更新標籤
        if post_update.tags is not None:
            # 清除舊標籤
            self.db.query(PostTag).filter(PostTag.post_id == post_id).delete()
            # 添加新標籤
            if post_update.tags:
                self._process_tags(post, post_update.tags)
        
        # 更新媒體
        if post_update.media_ids is not None:
            # 清除舊媒體
            self.db.query(PostMedia).filter(PostMedia.post_id == post_id).delete()
            # 添加新媒體
            if post_update.media_ids:
                self._attach_media(post, post_update.media_ids, user_id)
        
        self.db.commit()
        self.db.refresh(post)
        
        return post
    
    def delete_post(self, post_id: int, user_id: int) -> bool:
        """刪除貼文（軟刪除）"""
        post = self.db.query(Post).filter(
            Post.id == post_id,
            Post.user_id == user_id,
            Post.is_deleted == False
        ).first()
        
        if not post:
            return False
        
        post.is_deleted = True
        self.db.commit()
        
        return True
    
    def get_user_posts(self, user_id: int, viewer: Optional[User] = None,
                  include_private: bool = False, skip: int = 0, 
                  limit: int = 20) -> Tuple[List[Post], int]:
        """獲取用戶的貼文列表（考慮隱私設定）"""
        # 獲取目標用戶
        target_user = self.db.query(User).filter(User.id == user_id).first()
        if not target_user:
            return [], 0
        
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.pet),
            joinedload(Post.media).joinedload(PostMedia.media),
            joinedload(Post.tags).joinedload(PostTag.tag)
        ).filter(
            Post.user_id == user_id,
            Post.is_deleted == False
        )
        
        # 根據查看者和目標用戶的隱私設定過濾
        if not viewer or viewer.id != user_id:
            # 不是本人查看
            if target_user.privacy_level == PrivacyLevel.PRIVATE:
                # 私密用戶：只有好友可以看到貼文
                if viewer and self.social_service.is_friend(viewer.id, user_id):
                    # 好友可以看到公開和好友貼文
                    query = query.filter(Post.visibility.in_([Visibility.PUBLIC, Visibility.FRIENDS]))
                else:
                    # 非好友看不到任何貼文
                    return [], 0
            else:
                # 公開用戶
                if viewer and self.social_service.is_friend(viewer.id, user_id):
                    # 好友可以看到公開和好友貼文
                    query = query.filter(Post.visibility.in_([Visibility.PUBLIC, Visibility.FRIENDS]))
                else:
                    # 其他人只能看到公開貼文
                    query = query.filter(Post.visibility == Visibility.PUBLIC)
        # 如果是本人，可以看到所有自己的貼文（包括私人）
        
        # 排序
        query = query.order_by(desc(Post.created_at))
        
        total = query.count()
        posts = query.offset(skip).limit(limit).all()
        
        return posts, total
    
    def get_feed(self, user_id: int, include_friends: bool = True,
            include_following: bool = True, skip: int = 0,
            limit: int = 20) -> Tuple[List[Post], int]:
        """獲取動態消息（考慮隱私設定）"""
        # 查詢貼文
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.pet),
            joinedload(Post.media).joinedload(PostMedia.media),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.likes),
            joinedload(Post.comments)
        ).filter(
            Post.is_deleted == False
        )
        
        # 構建可見性條件
        visibility_conditions = []
        
        # 1. 自己的所有貼文
        visibility_conditions.append(Post.user_id == user_id)
        
        # 2. 好友的貼文
        if include_friends:
            friend_ids = self.db.query(Friendship.friend_id).filter(
                Friendship.user_id == user_id,
                Friendship.status == FriendshipStatus.ACCEPTED
            ).subquery()
            
            # 好友的公開和好友貼文（不論好友的隱私設定）
            visibility_conditions.append(
                and_(
                    Post.user_id.in_(friend_ids),
                    Post.visibility.in_([Visibility.PUBLIC, Visibility.FRIENDS])
                )
            )
        
        # 3. 關注者的貼文
        if include_following:
            from app.models.social import Follow
            following_ids = self.db.query(Follow.following_id).filter(
                Follow.follower_id == user_id
            ).subquery()
            
            # 只能看到公開用戶的公開貼文（非好友情況）
            visibility_conditions.append(
                and_(
                    Post.user_id.in_(following_ids),
                    Post.author.has(privacy_level=PrivacyLevel.PUBLIC),
                    Post.visibility == Visibility.PUBLIC,
                    ~Post.user_id.in_(friend_ids) if include_friends else True
                )
            )
        
        # 應用可見性過濾
        query = query.filter(or_(*visibility_conditions))
        
        # 排除被封鎖用戶的貼文
        blocked_users = self.social_service.get_user_blocker_ids_subquery(user_id)
        query = query.filter(Post.user_id.notin_(blocked_users))
        
        # 排序
        query = query.order_by(desc(Post.created_at))
        
        total = query.count()
        posts = query.offset(skip).limit(limit).all()
        
        return posts, total
    
    def search_posts(self, query_str: str = None, tag: Optional[str] = None,
            user_id: Optional[int] = None, pet_id: Optional[int] = None,
            viewer: Optional[User] = None, skip: int = 0,
            limit: int = 20) -> Tuple[List[Post], int]:
        """搜索貼文（考慮用戶隱私設定）"""
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.pet),
            joinedload(Post.media).joinedload(PostMedia.media),
            joinedload(Post.tags).joinedload(PostTag.tag)
        ).filter(
            Post.is_deleted == False
        )
        
        # 文字搜索
        if query_str and query_str.strip():
            search_term = f"%{query_str.strip()}%"
            query = query.filter(
                or_(
                    Post.content.ilike(search_term),
                    Post.location.ilike(search_term) if Post.location else False
                )
            )
        
        # 標籤過濾
        if tag and tag.strip():
            tag_clean = tag.strip().lower()
            query = query.join(Post.tags).join(PostTag.tag).filter(
                Tag.name == tag_clean
            )
        
        # 用戶過濾
        if user_id:
            query = query.filter(Post.user_id == user_id)
        
        # 寵物過濾
        if pet_id:
            query = query.filter(Post.pet_id == pet_id)
        
        # 根據查看者過濾可見貼文
        if viewer:
            # 排除被封鎖用戶的貼文
            blocked_users = self.social_service.get_user_blocker_ids_subquery(viewer.id)
            query = query.filter(Post.user_id.notin_(blocked_users))
            
            # 構建可見性過濾條件
            visibility_conditions = []
            
            # 1. 自己的貼文
            visibility_conditions.append(Post.user_id == viewer.id)
            
            # 2. 公開用戶的公開貼文
            visibility_conditions.append(
                and_(
                    Post.author.has(privacy_level=PrivacyLevel.PUBLIC),
                    Post.visibility == Visibility.PUBLIC
                )
            )
            
            # 3. 好友的貼文（根據隱私設定）
            friend_ids = self.db.query(Friendship.friend_id).filter(
                Friendship.user_id == viewer.id,
                Friendship.status == FriendshipStatus.ACCEPTED
            ).subquery()
            
            # 公開用戶好友的公開和好友貼文
            visibility_conditions.append(
                and_(
                    Post.user_id.in_(friend_ids),
                    Post.author.has(privacy_level=PrivacyLevel.PUBLIC),
                    Post.visibility.in_([Visibility.PUBLIC, Visibility.FRIENDS])
                )
            )
            
            # 私密用戶好友的公開和好友貼文
            visibility_conditions.append(
                and_(
                    Post.user_id.in_(friend_ids),
                    Post.author.has(privacy_level=PrivacyLevel.PRIVATE),
                    Post.visibility.in_([Visibility.PUBLIC, Visibility.FRIENDS])
                )
            )
            
            # 應用過濾條件
            query = query.filter(or_(*visibility_conditions))
        else:
            # 未登入用戶只能看到公開用戶的公開貼文
            query = query.filter(
                Post.author.has(privacy_level=PrivacyLevel.PUBLIC),
                Post.visibility == Visibility.PUBLIC
            )
        
        # 排序
        query = query.order_by(desc(Post.created_at))
        
        # 先計算總數
        total = query.count()
        
        # 然後進行分頁
        posts = query.offset(skip).limit(limit).all()
        
        return posts, total
    
    def like_post(self, post_id: int, user_id: int) -> bool:
        """按讚貼文"""
        # 檢查貼文是否存在
        post = self.get_post(post_id)
        if not post:
            return False
        
        # 檢查是否已按讚
        existing_like = self.db.query(Like).filter(
            Like.post_id == post_id,
            Like.user_id == user_id
        ).first()
        
        if existing_like:
            return False
        
        # 創建按讚記錄
        like = Like(post_id=post_id, user_id=user_id)
        self.db.add(like)
        
        # 發送通知（如果不是自己的貼文）
        if post.user_id != user_id:
            liker = self.db.query(User).filter(User.id == user_id).first()
            self.notification_service.create_notification(
                user_id=post.user_id,
                type="post_liked",
                title="貼文被按讚",
                content=f"{liker.display_name or liker.username} 喜歡了你的貼文",
                data={"post_id": post_id, "liker_id": user_id}
            )
        
        self.db.commit()
        return True
    
    def unlike_post(self, post_id: int, user_id: int) -> bool:
        """取消按讚"""
        deleted = self.db.query(Like).filter(
            Like.post_id == post_id,
            Like.user_id == user_id
        ).delete()
        
        self.db.commit()
        return deleted > 0
    
    def toggle_comments(self, post_id: int, user_id: int, enabled: bool) -> bool:
        """開啟/關閉評論功能"""
        post = self.db.query(Post).filter(
            Post.id == post_id,
            Post.is_deleted == False
        ).first()
        
        if not post:
            return False
        
        # 只有貼文作者或管理員可以控制評論開關
        user = self.db.query(User).filter(User.id == user_id).first()
        if post.user_id != user_id and not self.privacy_service.is_admin(user):
            return False
        
        post.comments_enabled = enabled
        self.db.commit()
        
        return True

    def add_comment(self, post_id: int, user_id: int, content: str,
               parent_id: Optional[int] = None,
               quoted_comment_id: Optional[int] = None) -> Optional[Comment]:
        """新增評論（支援引用）"""
        # 檢查貼文是否存在
        post = self.get_post(post_id)
        if not post:
            return None
        
        # 檢查評論是否開啟
        if not post.comments_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Comments are disabled for this post"
            )
        
        # 檢查父評論是否存在
        parent_comment = None
        if parent_id:
            parent_comment = self.db.query(Comment).filter(
                Comment.id == parent_id,
                Comment.post_id == post_id,
                Comment.is_deleted == False
            ).first()
            
            if not parent_comment:
                return None
        
        # 檢查引用的評論是否存在
        quoted_comment = None
        if quoted_comment_id:
            quoted_comment = self.db.query(Comment).filter(
                Comment.id == quoted_comment_id,
                Comment.post_id == post_id
            ).first()
            
            if not quoted_comment:
                return None
        
        # 創建評論
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            parent_id=parent_id,
            quoted_comment_id=quoted_comment_id,
            content=content
        )
        
        self.db.add(comment)
        self.db.flush()
        
        # 手動更新父評論的統計數據
        if parent_comment:
            parent_comment.reply_count += 1
            parent_comment.last_reply_at = datetime.utcnow()
        
        # 發送通知
        if post.user_id != user_id:
            commenter = self.db.query(User).filter(User.id == user_id).first()
            self.notification_service.create_notification(
                user_id=post.user_id,
                type="post_commented",
                title="新的評論",
                content=f"{commenter.display_name or commenter.username} 評論了你的貼文",
                data={"post_id": post_id, "comment_id": comment.id, "commenter_id": user_id}
            )
        
        # 如果是回覆，通知被回覆的用戶
        if parent_id and parent_comment.user_id != user_id:
            self.notification_service.create_notification(
                user_id=parent_comment.user_id,
                type="comment_replied",
                title="評論被回覆",
                content=f"{commenter.display_name or commenter.username} 回覆了你的評論",
                data={"post_id": post_id, "comment_id": comment.id, "parent_id": parent_id}
            )
        
        # 如果引用了評論，通知被引用的用戶
        if quoted_comment_id and quoted_comment.user_id != user_id:
            self.notification_service.create_notification(
                user_id=quoted_comment.user_id,
                type="comment_quoted",
                title="評論被引用",
                content=f"{commenter.display_name or commenter.username} 引用了你的評論",
                data={"post_id": post_id, "comment_id": comment.id, "quoted_id": quoted_comment_id}
            )
        
        self.db.commit()
        self.db.refresh(comment)
        
        return comment
    
    def delete_comment(self, comment_id: int, user_id: int, reason: Optional[str] = None) -> bool:
        """刪除評論（軟刪除，保留刪除資訊）"""
        comment = self.db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.is_deleted == False
        ).first()
        
        if not comment:
            return False
        
        # 檢查權限：評論作者、貼文作者或管理員可以刪除
        user = self.db.query(User).filter(User.id == user_id).first()
        post = self.db.query(Post).filter(Post.id == comment.post_id).first()
        
        can_delete = (
            comment.user_id == user_id or
            post.user_id == user_id or
            self.privacy_service.is_admin(user)
        )
        
        if not can_delete:
            return False
        
        comment.is_deleted = True
        comment.deleted_by = user_id
        comment.deleted_at = datetime.utcnow()
        comment.deletion_reason = reason
        self.db.commit()
        
        return True
    
    def like_comment(self, comment_id: int, user_id: int) -> bool:
        """按讚評論"""
        # 檢查評論是否存在
        comment = self.db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.is_deleted == False
        ).first()
        
        if not comment:
            return False
        
        # 檢查是否已按讚
        existing_like = self.db.query(CommentLike).filter(
            CommentLike.comment_id == comment_id,
            CommentLike.user_id == user_id
        ).first()
        
        if existing_like:
            return False
        
        # 創建按讚記錄
        like = CommentLike(comment_id=comment_id, user_id=user_id)
        self.db.add(like)
        
        # 手動更新評論的按讚數
        comment.like_count += 1
        
        # 發送通知（如果不是自己的評論）
        if comment.user_id != user_id:
            liker = self.db.query(User).filter(User.id == user_id).first()
            self.notification_service.create_notification(
                user_id=comment.user_id,
                type="comment_liked",
                title="評論被按讚",
                content=f"{liker.display_name or liker.username} 喜歡了你的評論",
                data={"comment_id": comment_id, "liker_id": user_id}
            )
        
        self.db.commit()
        return True
    
    def unlike_comment(self, comment_id: int, user_id: int) -> bool:
        """取消按讚評論"""
        # 先獲取評論
        comment = self.db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            return False
        
        deleted = self.db.query(CommentLike).filter(
            CommentLike.comment_id == comment_id,
            CommentLike.user_id == user_id
        ).delete()
        
        if deleted > 0:
            # 手動更新評論的按讚數
            comment.like_count = max(0, comment.like_count - 1)
            self.db.commit()
            return True
        
        return False
    
    def search_comments(self, query_str: Optional[str] = None,
                       user_id: Optional[int] = None,
                       post_id: Optional[int] = None,
                       sort_by: str = "newest",
                       skip: int = 0,
                       limit: int = 20) -> Tuple[List[Comment], int]:
        """搜索評論"""
        query = self.db.query(Comment).filter(Comment.is_deleted == False)
        
        # 內容搜索
        if query_str:
            query = query.filter(Comment.content.ilike(f"%{query_str}%"))
        
        # 用戶過濾
        if user_id:
            query = query.filter(Comment.user_id == user_id)
        
        # 貼文過濾
        if post_id:
            query = query.filter(Comment.post_id == post_id)
        
        # 排序
        if sort_by == "newest":
            query = query.order_by(desc(Comment.created_at))
        elif sort_by == "oldest":
            query = query.order_by(asc(Comment.created_at))
        elif sort_by == "most_likes":
            query = query.order_by(desc(Comment.like_count))
        elif sort_by == "most_replies":
            query = query.order_by(desc(Comment.reply_count))
        elif sort_by == "recent_activity":
            query = query.order_by(desc(Comment.last_reply_at.nullslast()))
        
        total = query.count()
        comments = query.offset(skip).limit(limit).all()
        
        return comments, total
    
    def get_post_comments(self, post_id: int, sort_by: str = "newest",
                         viewer: Optional[User] = None) -> List[Comment]:
        """獲取貼文的所有評論（構建樹狀結構）"""
        query = self.db.query(Comment).options(
            joinedload(Comment.user),
            joinedload(Comment.quoted_comment).joinedload(Comment.user),
            joinedload(Comment.likes)
        ).filter(
            Comment.post_id == post_id
        )
        
        # 排序
        if sort_by == "newest":
            query = query.order_by(desc(Comment.created_at))
        elif sort_by == "oldest":
            query = query.order_by(asc(Comment.created_at))
        elif sort_by == "most_likes":
            query = query.order_by(desc(Comment.like_count))
        
        return query.all()
    
    def get_post_statistics(self, post_id: int) -> PostStatistics:
        """獲取貼文統計"""
        post = self.db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        like_count = self.db.query(func.count(Like.id)).filter(
            Like.post_id == post_id
        ).scalar()
        
        comment_count = self.db.query(func.count(Comment.id)).filter(
            Comment.post_id == post_id,
            Comment.is_deleted == False
        ).scalar()
        
        return PostStatistics(
            view_count=post.view_count,
            like_count=like_count,
            comment_count=comment_count,
            share_count=0  # 未實現分享功能
        )
    
    def get_trending_tags(self, days: int = 7, limit: int = 10) -> List[Tag]:
        """獲取熱門標籤"""
        # 簡單實現：返回使用次數最多的標籤
        tags = self.db.query(Tag).order_by(
            desc(Tag.usage_count)
        ).limit(limit).all()
        
        return tags
    
    def _can_view_post(self, post: Post, viewer: Optional[User]) -> bool:
        """檢查是否可以查看貼文（考慮用戶隱私設定）"""
        # 被刪除的貼文不可見
        if post.is_deleted:
            return False
        
        # 沒有查看者（未登入）
        if not viewer:
            # 只能看到隱私設定為 public 的用戶的公開貼文
            return (post.author.privacy_level == PrivacyLevel.PUBLIC and 
                   post.visibility == Visibility.PUBLIC)
        
        # 作者自己總是可以看到
        if viewer.id == post.user_id:
            return True
        
        # 管理員可以看到所有貼文
        if self.privacy_service.is_admin(viewer):
            return True
        
        # 檢查是否被封鎖
        if self.social_service.is_blocked(post.user_id, viewer.id):
            return False
        
        # 根據作者的隱私設定判斷
        author_privacy = post.author.privacy_level
        
        if author_privacy == PrivacyLevel.PUBLIC:
            # 公開用戶：根據貼文本身的可見性判斷
            if post.visibility == Visibility.PUBLIC:
                return True
            elif post.visibility == Visibility.FRIENDS:
                return self.social_service.is_friend(viewer.id, post.user_id)
            elif post.visibility == Visibility.PRIVATE:
                return False
        
        elif author_privacy == PrivacyLevel.PRIVATE:
            # 私密用戶：只有好友可以看到貼文
            is_friend = self.social_service.is_friend(viewer.id, post.user_id)
            
            if not is_friend:
                # 非好友不能看到任何貼文
                return False
            
            # 好友可以看到公開和好友貼文
            if post.visibility == Visibility.PUBLIC:
                return True
            elif post.visibility == Visibility.FRIENDS:
                return True
            elif post.visibility == Visibility.PRIVATE:
                return False
        
        return False
    
    def _process_tags(self, post: Post, tag_names: List[str]):
        """處理貼文標籤"""
        for tag_name in tag_names:
            # 清理標籤名稱
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue
            
            # 查找或創建標籤
            tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                tag = Tag(name=tag_name, usage_count=0)
                self.db.add(tag)
                self.db.flush()
            
            # 增加使用次數
            tag.usage_count += 1
            
            # 關聯到貼文
            post_tag = PostTag(post_id=post.id, tag_id=tag.id)
            self.db.add(post_tag)
    
    def _attach_media(self, post: Post, media_ids: List[int], user_id: int):
        """附加媒體檔案到貼文"""
        for order, media_id in enumerate(media_ids):
            # 確認媒體檔案存在且屬於用戶
            media = self.db.query(Media).filter(
                Media.id == media_id,
                Media.user_id == user_id
            ).first()
            
            if media:
                post_media = PostMedia(
                    post_id=post.id,
                    media_id=media_id,
                    display_order=order
                )
                self.db.add(post_media)
    
    def _notify_followers(self, post: Post):
        """通知關注者有新貼文"""
        from app.models.social import Follow
        
        # 獲取關注者
        followers = self.db.query(Follow.follower_id).filter(
            Follow.following_id == post.user_id
        ).all()
        
        author = post.author
        
        # 批量創建通知
        for follower_id in followers:
            self.notification_service.create_notification(
                user_id=follower_id[0],
                type="new_post",
                title="新貼文",
                content=f"{author.display_name or author.username} 發布了新貼文",
                data={"post_id": post.id, "author_id": post.user_id}
            )

