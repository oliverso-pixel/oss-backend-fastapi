# app/services/post_service.py
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
from fastapi import HTTPException, status
from app.models.post import Post, Visibility
from app.models.user import User
from app.models.pet import Pet
from app.models.media import Media, PostMedia
from app.models.social import Tag, PostTag, Like, Comment, Friendship, FriendshipStatus
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
            location=post_data.location,
            latitude=post_data.latitude,
            longitude=post_data.longitude
        )
        
        self.db.add(post)
        self.db.flush()
        
        # 處理標籤
        if post_data.tags:
            self._process_tags(post, post_data.tags)
        
        # 處理媒體檔案
        if post_data.media_ids:
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
        """獲取用戶的貼文列表"""
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.pet),
            joinedload(Post.media).joinedload(PostMedia.media),
            joinedload(Post.tags).joinedload(PostTag.tag)
        ).filter(
            Post.user_id == user_id,
            Post.is_deleted == False
        )
        
        # 根據查看者過濾可見性
        if not viewer or viewer.id != user_id:
            if viewer and self.social_service.is_friend(viewer.id, user_id):
                # 好友可以看到公開和好友貼文
                query = query.filter(Post.visibility.in_([Visibility.PUBLIC, Visibility.FRIENDS]))
            else:
                # 其他人只能看到公開貼文
                query = query.filter(Post.visibility == Visibility.PUBLIC)
        
        # 排序
        query = query.order_by(desc(Post.created_at))
        
        total = query.count()
        posts = query.offset(skip).limit(limit).all()
        
        return posts, total
    
    def get_feed(self, user_id: int, include_friends: bool = True,
                include_following: bool = True, skip: int = 0,
                limit: int = 20) -> Tuple[List[Post], int]:
        """獲取動態消息"""
        # 獲取要顯示貼文的用戶ID列表
        user_ids = [user_id]
        
        if include_friends:
            friends = self.db.query(Friendship.friend_id).filter(
                Friendship.user_id == user_id,
                Friendship.status == FriendshipStatus.ACCEPTED
            ).all()
            user_ids.extend([f[0] for f in friends])
        
        if include_following:
            from app.models.social import Follow
            following = self.db.query(Follow.following_id).filter(
                Follow.follower_id == user_id
            ).all()
            user_ids.extend([f[0] for f in following])
        
        # 去重
        user_ids = list(set(user_ids))
        
        # 查詢貼文
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.pet),
            joinedload(Post.media).joinedload(PostMedia.media),
            joinedload(Post.tags).joinedload(PostTag.tag),
            joinedload(Post.likes),
            joinedload(Post.comments)
        ).filter(
            Post.user_id.in_(user_ids),
            Post.is_deleted == False,
            or_(
                Post.visibility == Visibility.PUBLIC,
                and_(
                    Post.visibility == Visibility.FRIENDS,
                    Post.user_id.in_(
                        self.db.query(Friendship.friend_id).filter(
                            Friendship.user_id == user_id,
                            Friendship.status == FriendshipStatus.ACCEPTED
                        )
                    )
                ),
                Post.user_id == user_id  # 自己的所有貼文
            )
        )
        
        # 排除被封鎖用戶的貼文
        blocked_users = self.social_service.get_user_blocker_ids_subquery(user_id)
        query = query.filter(Post.user_id.notin_(blocked_users))
        
        # 排序
        query = query.order_by(desc(Post.created_at))
        
        total = query.count()
        posts = query.offset(skip).limit(limit).all()
        
        return posts, total
    
    def search_posts(self, query_str: str, tag: Optional[str] = None,
                    user_id: Optional[int] = None, pet_id: Optional[int] = None,
                    viewer: Optional[User] = None, skip: int = 0,
                    limit: int = 20) -> Tuple[List[Post], int]:
        """搜索貼文"""
        query = self.db.query(Post).options(
            joinedload(Post.author),
            joinedload(Post.pet),
            joinedload(Post.media).joinedload(PostMedia.media),
            joinedload(Post.tags).joinedload(PostTag.tag)
        ).filter(
            Post.is_deleted == False,
            Post.visibility == Visibility.PUBLIC  # 搜索只返回公開貼文
        )
        
        # 文字搜索
        if query_str:
            search_term = f"%{query_str}%"
            query = query.filter(
                or_(
                    Post.content.ilike(search_term),
                    Post.location.ilike(search_term)
                )
            )
        
        # 標籤過濾
        if tag:
            query = query.join(PostTag).join(Tag).filter(Tag.name == tag)
        
        # 用戶過濾
        if user_id:
            query = query.filter(Post.user_id == user_id)
        
        # 寵物過濾
        if pet_id:
            query = query.filter(Post.pet_id == pet_id)
        
        # 排除被封鎖用戶的貼文
        if viewer:
            blocked_users = self.social_service.get_user_blocker_ids_subquery(viewer.id)
            query = query.filter(Post.user_id.notin_(blocked_users))
        
        # 排序
        query = query.order_by(desc(Post.created_at))
        
        total = query.count()
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
    
    def add_comment(self, post_id: int, user_id: int, content: str,
                   parent_id: Optional[int] = None) -> Optional[Comment]:
        """新增評論"""
        # 檢查貼文是否存在
        post = self.get_post(post_id)
        if not post:
            return None
        
        # 檢查父評論是否存在
        if parent_id:
            parent_comment = self.db.query(Comment).filter(
                Comment.id == parent_id,
                Comment.post_id == post_id,
                Comment.is_deleted == False
            ).first()
            
            if not parent_comment:
                return None
        
        # 創建評論
        comment = Comment(
            post_id=post_id,
            user_id=user_id,
            parent_id=parent_id,
            content=content
        )
        
        self.db.add(comment)
        self.db.flush()
        
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
        
        self.db.commit()
        self.db.refresh(comment)
        
        return comment
    
    def delete_comment(self, comment_id: int, user_id: int) -> bool:
        """刪除評論（軟刪除）"""
        comment = self.db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.user_id == user_id,
            Comment.is_deleted == False
        ).first()
        
        if not comment:
            return False
        
        comment.is_deleted = True
        self.db.commit()
        
        return True
    
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
        """檢查是否可以查看貼文"""
        # 被刪除的貼文不可見
        if post.is_deleted:
            return False
        
        # 公開貼文所有人可見
        if post.visibility == Visibility.PUBLIC:
            return True
        
        # 私人貼文只有作者可見
        if post.visibility == Visibility.PRIVATE:
            return viewer and viewer.id == post.user_id
        
        # 好友貼文
        if post.visibility == Visibility.FRIENDS:
            if not viewer:
                return False
            if viewer.id == post.user_id:
                return True
            return self.social_service.is_friend(viewer.id, post.user_id)
        
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

