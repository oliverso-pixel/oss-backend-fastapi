# app/core/redis.py
import redis
from redis import Redis
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis 連接管理器"""
    _instance: Optional[Redis] = None
    
    @classmethod
    def get_redis(cls) -> Redis:
        """獲取 Redis 連接實例"""
        if cls._instance is None:
            try:
                # 簡化連接選項，避免 socket 選項問題
                cls._instance = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # 測試連接
                cls._instance.ping()
                logger.info("Redis connection established")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                # 創建一個 Mock Redis 客戶端作為後備方案
                logger.warning("Using in-memory fallback instead of Redis")
                from app.core.redis_fallback import FallbackRedis
                cls._instance = FallbackRedis()
        
        return cls._instance
    
    @classmethod
    def close(cls):
        """關閉 Redis 連接"""
        if cls._instance:
            try:
                cls._instance.close()
                logger.info("Redis connection closed")
            except:
                pass
            finally:
                cls._instance = None

# 延遲初始化，避免在導入時就連接
redis_client = None

def get_redis() -> Redis:
    """FastAPI 依賴注入函數"""
    global redis_client
    if redis_client is None:
        redis_client = RedisManager.get_redis()
    return redis_client

