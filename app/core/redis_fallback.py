# app/core/redis_fallback.py
from typing import Dict, Set, Any, Optional, List
from datetime import datetime, timedelta
import json
import threading
import time

class FallbackRedis:
    """當 Redis 不可用時的記憶體後備方案"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._sets: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_expired(self):
        """清理過期的鍵"""
        while True:
            time.sleep(60)  # 每分鐘清理一次
            with self._lock:
                current_time = time.time()
                expired_keys = [k for k, exp in self._expiry.items() if exp < current_time]
                for key in expired_keys:
                    self._data.pop(key, None)
                    self._expiry.pop(key, None)
    
    def setex(self, key: str, seconds: int, value: Any) -> bool:
        """設置帶過期時間的鍵值"""
        with self._lock:
            self._data[key] = value
            self._expiry[key] = time.time() + seconds
            return True
    
    def get(self, key: str) -> Optional[str]:
        """獲取值"""
        with self._lock:
            if key in self._expiry:
                if self._expiry[key] < time.time():
                    self._data.pop(key, None)
                    self._expiry.pop(key, None)
                    return None
            return self._data.get(key)
    
    def exists(self, key: str) -> int:
        """檢查鍵是否存在"""
        with self._lock:
            if key in self._expiry and self._expiry[key] < time.time():
                self._data.pop(key, None)
                self._expiry.pop(key, None)
                return 0
            return 1 if key in self._data else 0
    
    def delete(self, *keys: str) -> int:
        """刪除鍵"""
        with self._lock:
            count = 0
            for key in keys:
                if key in self._data:
                    self._data.pop(key, None)
                    self._expiry.pop(key, None)
                    count += 1
            return count
    
    def sadd(self, key: str, *values: str) -> int:
        """添加到集合"""
        with self._lock:
            if key not in self._sets:
                self._sets[key] = set()
            initial_size = len(self._sets[key])
            self._sets[key].update(values)
            return len(self._sets[key]) - initial_size
    
    def srem(self, key: str, *values: str) -> int:
        """從集合移除"""
        with self._lock:
            if key not in self._sets:
                return 0
            initial_size = len(self._sets[key])
            self._sets[key].difference_update(values)
            return initial_size - len(self._sets[key])
    
    def smembers(self, key: str) -> Set[str]:
        """獲取集合所有成員"""
        with self._lock:
            return self._sets.get(key, set()).copy()
    
    def sismember(self, key: str, value: str) -> bool:
        """檢查是否為集合成員"""
        with self._lock:
            return value in self._sets.get(key, set())
    
    def scard(self, key: str) -> int:
        """獲取集合大小"""
        with self._lock:
            return len(self._sets.get(key, set()))
    
    def expire(self, key: str, seconds: int) -> bool:
        """設置過期時間"""
        with self._lock:
            if key in self._data:
                self._expiry[key] = time.time() + seconds
                return True
            return False
    
    def ttl(self, key: str) -> int:
        """獲取剩餘生存時間"""
        with self._lock:
            if key not in self._expiry:
                return -2  # 鍵不存在
            ttl = int(self._expiry[key] - time.time())
            return ttl if ttl > 0 else -2
    
    def ping(self) -> bool:
        """Ping 測試"""
        return True
    
    def info(self) -> Dict[str, Any]:
        """獲取信息"""
        with self._lock:
            return {
                "used_memory_human": f"{len(self._data)} keys",
                "connected_clients": 1,
                "type": "in-memory fallback"
            }
    
    def pipeline(self):
        """返回自身作為 pipeline"""
        return self
    
    def execute(self):
        """執行 pipeline（無操作）"""
        return []
    
    def close(self):
        """關閉連接（無操作）"""
        pass

    