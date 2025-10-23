# app/services/token_blacklist_service.py
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
from redis import Redis
from app.core.redis import get_redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TokenBlacklistService:
    """Token 黑名單服務 - 支援 Redis 和後備方案"""
    
    # Redis key 前綴
    BLACKLIST_PREFIX = "token:blacklist:"
    USER_TOKENS_PREFIX = "user:tokens:"
    BLACKLIST_SET_KEY = "token:blacklist:all"
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = None
        self._is_redis_available = False
        self._initialize_redis(redis_client)
    
    def _initialize_redis(self, redis_client: Optional[Redis] = None):
        """初始化 Redis 連接"""
        try:
            self.redis = redis_client or get_redis()
            # 測試連接
            self.redis.ping()
            self._is_redis_available = True
            logger.info("TokenBlacklistService: Redis connection successful")
        except Exception as e:
            logger.warning(f"TokenBlacklistService: Redis not available, using fallback. Error: {str(e)}")
            self._is_redis_available = False
            # get_redis() 應該已經返回了 FallbackRedis
            if self.redis is None:
                from app.core.redis_fallback import FallbackRedis
                self.redis = FallbackRedis()
    
    def add_to_blacklist(
        self, 
        jti: str, 
        user_id: int, 
        expires_at: datetime,
        reason: str = "Unknown",
        blacklisted_by: Optional[int] = None
    ) -> bool:
        """將 token 加入黑名單"""
        try:
            # 計算 TTL
            ttl = int((expires_at - datetime.utcnow()).total_seconds())
            
            if ttl <= 0:
                logger.info(f"Token {jti} already expired, skipping blacklist")
                return True
            
            # 準備黑名單數據
            blacklist_data = {
                "jti": jti,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "reason": reason,
                "blacklisted_at": datetime.utcnow().isoformat(),
                "blacklisted_by": blacklisted_by
            }
            
            # 存儲數據
            key = f"{self.BLACKLIST_PREFIX}{jti}"
            success = self.redis.setex(key, ttl, json.dumps(blacklist_data))
            
            if success:
                # 添加到集合（僅在真實 Redis 時）
                if self._is_redis_available:
                    self.redis.sadd(self.BLACKLIST_SET_KEY, jti)
                    
                    # 添加到用戶 token 集合
                    user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
                    self.redis.sadd(user_tokens_key, jti)
                    self.redis.expire(user_tokens_key, 86400 * 7)  # 7 天
                
                logger.info(f"Token {jti} added to blacklist for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {str(e)}")
            # 在錯誤情況下，為了安全起見，我們假設操作成功
            # 這樣至少不會允許已撤銷的 token 繼續使用
            return True
    
    def is_blacklisted(self, jti: str) -> bool:
        """檢查 token 是否在黑名單中"""
        if not jti:
            return False
            
        try:
            return self.redis.exists(f"{self.BLACKLIST_PREFIX}{jti}") > 0
        except Exception as e:
            logger.error(f"Failed to check blacklist: {str(e)}")
            # 錯誤時採用保守策略
            return True
    
    def get_blacklist_info(self, jti: str) -> Optional[Dict[str, Any]]:
        """獲取黑名單詳細信息"""
        try:
            data = self.redis.get(f"{self.BLACKLIST_PREFIX}{jti}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get blacklist info: {str(e)}")
            return None
    
    def blacklist_user_tokens(
        self, 
        user_id: int, 
        reason: str = "User action",
        blacklisted_by: Optional[int] = None
    ) -> int:
        """將用戶的所有 token 加入黑名單"""
        count = 0
        
        try:
            # 如果使用後備方案，我們無法獲取用戶的所有 tokens
            if not self._is_redis_available:
                logger.warning("Cannot blacklist all user tokens with fallback Redis")
                return 0
            
            # 獲取用戶的所有 token
            user_tokens_key = f"{self.USER_TOKENS_PREFIX}{user_id}"
            tokens = self.redis.smembers(user_tokens_key)
            
            if not tokens:
                return 0
            
            for jti in tokens:
                # 檢查 token 是否還存在
                key = f"{self.BLACKLIST_PREFIX}{jti}"
                if self.redis.exists(key):
                    count += 1
            
            logger.info(f"Found {count} active tokens for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to blacklist user tokens: {str(e)}")
            return 0
    
    def get_blacklist_stats(self) -> Dict[str, Any]:
        """獲取黑名單統計信息"""
        try:
            stats = {
                "redis_available": self._is_redis_available,
                "backend_type": "Redis" if self._is_redis_available else "In-Memory Fallback"
            }
            
            if self._is_redis_available:
                info = self.redis.info()
                stats.update({
                    "total_blacklisted": self.redis.scard(self.BLACKLIST_SET_KEY),
                    "redis_memory_usage": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0)
                })
            else:
                stats.update({
                    "message": "Using in-memory fallback, statistics limited"
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get blacklist stats: {str(e)}")
            return {"error": str(e)}

# 創建全局實例（延遲初始化）
_token_blacklist_service = None

def get_token_blacklist_service() -> TokenBlacklistService:
    """獲取 Token 黑名單服務實例"""
    global _token_blacklist_service
    if _token_blacklist_service is None:
        _token_blacklist_service = TokenBlacklistService()
    return _token_blacklist_service

# 為了向後兼容
token_blacklist_service = get_token_blacklist_service()

