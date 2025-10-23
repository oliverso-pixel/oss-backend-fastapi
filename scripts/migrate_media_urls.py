# scripts/migrate_media_urls.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.pet import Pet
from app.models.media import Media
from app.core.config import settings
from pathlib import Path

def extract_relative_path(url: str) -> str:
    """從完整 URL 提取相對路徑"""
    if not url:
        return url
        
    # 如果是外部 URL，保持不變
    if url.startswith(('http://', 'https://')) and not url.startswith(settings.BASE_URL):
        return url
        
    # 移除 BASE_URL
    if url.startswith(settings.BASE_URL):
        url = url[len(settings.BASE_URL):].lstrip('/')
        
    # 移除 /static/ 前綴
    if url.startswith('/static/'):
        return url[8:]
    elif url.startswith('static/'):
        return url[7:]
        
    return url

def migrate_urls():
    """遷移資料庫中的 URL 為相對路徑"""
    db = SessionLocal()
    
    try:
        print("Starting URL migration...")
        
        # 更新使用者頭像和封面圖片
        users = db.query(User).filter(
            (User.avatar_url.isnot(None)) | (User.background_image_url.isnot(None))
        ).all()
        
        print(f"Found {len(users)} users to update")
        
        for user in users:
            updated = False
            
            if user.avatar_url:
                new_path = extract_relative_path(user.avatar_url)
                if new_path != user.avatar_url:
                    print(f"Updating user {user.id} avatar: {user.avatar_url} -> {new_path}")
                    user.avatar_url = new_path
                    updated = True
                    
            if user.background_image_url:
                new_path = extract_relative_path(user.background_image_url)
                if new_path != user.background_image_url:
                    print(f"Updating user {user.id} cover: {user.background_image_url} -> {new_path}")
                    user.background_image_url = new_path
                    updated = True
            
            if updated:
                db.add(user)
        
        # 更新寵物頭像
        pets = db.query(Pet).filter(Pet.avatar_url.isnot(None)).all()
        
        print(f"Found {len(pets)} pets to update")
        
        for pet in pets:
            if pet.avatar_url:
                new_path = extract_relative_path(pet.avatar_url)
                if new_path != pet.avatar_url:
                    print(f"Updating pet {pet.id} avatar: {pet.avatar_url} -> {new_path}")
                    pet.avatar_url = new_path
                    db.add(pet)
        
        # 更新媒體檔案路徑
        media_items = db.query(Media).all()
        
        print(f"Found {len(media_items)} media items to update")
        
        for media in media_items:
            updated = False
            
            if media.file_path:
                new_path = extract_relative_path(media.file_path)
                if new_path != media.file_path:
                    print(f"Updating media {media.id} path: {media.file_path} -> {new_path}")
                    media.file_path = new_path
                    updated = True
                    
            if media.thumbnail_path:
                new_path = extract_relative_path(media.thumbnail_path)
                if new_path != media.thumbnail_path:
                    print(f"Updating media {media.id} thumbnail: {media.thumbnail_path} -> {new_path}")
                    media.thumbnail_path = new_path
                    updated = True
            
            # 更新 extra_data 中的 sizes
            if media.extra_data and "sizes" in media.extra_data:
                sizes_updated = False
                new_sizes = {}
                
                for size_name, size_path in media.extra_data["sizes"].items():
                    new_path = extract_relative_path(size_path)
                    new_sizes[size_name] = new_path
                    if new_path != size_path:
                        sizes_updated = True
                
                if sizes_updated:
                    media.extra_data["sizes"] = new_sizes
                    updated = True
                    print(f"Updated media {media.id} sizes")
            
            if updated:
                db.add(media)
        
        print("Committing changes...")
        db.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_migration():
    """驗證遷移結果"""
    db = SessionLocal()
    
    try:
        print("\nVerifying migration...")
        
        # 檢查是否還有完整 URL
        users_with_full_urls = db.query(User).filter(
            (User.avatar_url.like(f"{settings.BASE_URL}%")) |
            (User.avatar_url.like("http://%")) |
            (User.avatar_url.like("https://%")) |
            (User.background_image_url.like(f"{settings.BASE_URL}%")) |
            (User.background_image_url.like("http://%")) |
            (User.background_image_url.like("https://%"))
        ).count()
        
        print(f"Users with full URLs: {users_with_full_urls}")
        
        media_with_full_urls = db.query(Media).filter(
            (Media.file_path.like(f"{settings.BASE_URL}%")) |
            (Media.file_path.like("http://%")) |
            (Media.file_path.like("https://%")) |
            (Media.thumbnail_path.like(f"{settings.BASE_URL}%")) |
            (Media.thumbnail_path.like("http://%")) |
            (Media.thumbnail_path.like("https://%"))
        ).count()
        
        print(f"Media items with full URLs: {media_with_full_urls}")
        
        if users_with_full_urls == 0 and media_with_full_urls == 0:
            print("✅ Migration verified successfully!")
        else:
            print("⚠️ Some items still have full URLs")
            
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate media URLs to relative paths')
    parser.add_argument('--verify', action='store_true', help='Verify migration results')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_migration()
    else:
        migrate_urls()
        verify_migration()