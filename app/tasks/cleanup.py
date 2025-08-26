# app/tasks/cleanup.py
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.auth import TokenBlacklist, UserToken

def cleanup_expired_tokens():
    """清理過期的 tokens 和黑名單記錄"""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 清理過期的黑名單記錄
        deleted_blacklist = db.query(TokenBlacklist).filter(
            TokenBlacklist.expires_at < datetime.utcnow()
        ).delete()
        
        # 清理過期的 token 記錄
        deleted_tokens = db.query(UserToken).filter(
            UserToken.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        print(f"Cleaned up {deleted_blacklist} blacklist entries and {deleted_tokens} expired tokens")
        
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_expired_tokens()

# 可以使用 cron job 或 Celery 定期執行此任務