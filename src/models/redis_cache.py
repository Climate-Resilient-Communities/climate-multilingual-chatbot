import redis
import json
import logging
import asyncio
from typing import Any, Optional
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        self._closed = False
        self._lock = asyncio.Lock()

    def _get_loop(self):
        """Get or create an event loop."""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop
        except Exception as e:
            logger.error(f"Error getting event loop: {str(e)}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        if self._closed:
            logger.warning("Attempting to use closed Redis connection")
            return None
        try:
            loop = self._get_loop()
            async with self._lock:
                value = await loop.run_in_executor(
                    None, 
                    self.redis_client.get,
                    key
                )
                if value:
                    return json.loads(value)
                return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    async def set(self, key: str, value: Any, expiration: int = 3600) -> bool:
        if self._closed:
            logger.warning("Attempting to use closed Redis connection")
            return False
        try:
            loop = self._get_loop()
            async with self._lock:
                serialized = json.dumps(value)
                success = await loop.run_in_executor(
                    None,
                    lambda: self.redis_client.setex(key, expiration, serialized)
                )
                return bool(success)
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    async def close(self):
        """Asynchronously close the Redis connection."""
        if self._closed:
            return
        try:
            async with self._lock:
                if self.redis_client:
                    loop = self._get_loop()
                    await loop.run_in_executor(
                        None,
                        self.redis_client.close
                    )
                self._closed = True
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")

    def __del__(self):
        """Ensure resources are cleaned up."""
        if not self._closed and hasattr(self, 'redis_client'):
            try:
                self.redis_client.close()
            except Exception:
                pass

# Add alias for compatibility
ClimateCache = RedisCache

