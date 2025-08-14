import json
import hashlib
from typing import Optional, Any
import redis.asyncio as redis
from config import settings

class RedisCache:
    """Redis cache manager for API responses and model predictions."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connection_pool = None
    
    async def connect(self):
        """Establish Redis connection."""
        if not self.redis_client:
            try:
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                await self.redis_client.ping()
                print("✅ Redis connection established")
            except Exception as e:
                print(f"❌ Redis connection failed: {e}")
                self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _generate_key(self, prefix: str, data: str) -> str:
        """Generate a cache key from data."""
        hash_data = hashlib.md5(data.encode()).hexdigest()
        return f"{prefix}:{hash_data}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve data from cache."""
        if not self.redis_client:
            return None
        
        try:
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_hours: int) -> bool:
        """Store data in cache with TTL."""
        if not self.redis_client:
            return False
        
        try:
            ttl_seconds = ttl_hours * 3600
            await self.redis_client.setex(
                key, 
                ttl_seconds, 
                json.dumps(value, default=str)
            )
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete data from cache."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def get_model_prediction(self, text: str) -> Optional[dict]:
        """Get cached model prediction for text."""
        key = self._generate_key("model", text)
        return await self.get(key)
    
    async def set_model_prediction(self, text: str, prediction: dict) -> bool:
        """Cache model prediction for text."""
        key = self._generate_key("model", text)
        return await self.set(key, prediction, settings.CACHE_TTL_HOURS)
    
    async def get_api_response(self, endpoint: str, params: str) -> Optional[dict]:
        """Get cached API response."""
        key = self._generate_key(f"api:{endpoint}", params)
        return await self.get(key)
    
    async def set_api_response(self, endpoint: str, params: str, response: dict) -> bool:
        """Cache API response."""
        key = self._generate_key(f"api:{endpoint}", params)
        return await self.set(key, response, settings.API_CACHE_TTL_HOURS)
    
    async def clear_expired(self) -> int:
        """Clear expired keys (optional maintenance)."""
        if not self.redis_client:
            return 0
        
        try:
            # This is a simple approach - in production you might want more sophisticated cleanup
            return await self.redis_client.eval("""
                local keys = redis.call('keys', ARGV[1])
                local deleted = 0
                for i=1, #keys do
                    if redis.call('ttl', keys[i]) == -1 then
                        redis.call('del', keys[i])
                        deleted = deleted + 1
                    end
                end
                return deleted
            """, 0, "model:*")
        except Exception as e:
            print(f"Cache cleanup error: {e}")
            return 0

# Global cache instance
cache = RedisCache()
