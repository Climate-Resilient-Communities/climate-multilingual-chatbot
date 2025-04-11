import redis
import json
import logging
import asyncio
import os
from typing import Any, Optional
from threading import Lock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisCache:
    _instance = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, host=None, port=None, db=0, expiration=3600, password=None, ssl=False):
        """Initialize Redis cache with configurable expiration time."""
        # Skip initialization if already initialized
        if hasattr(self, '_initialized'):
            return
            
        try:
            # Get configuration from environment variables or use provided values
            self.host = host or os.getenv('REDIS_HOST', 'localhost')
            self.port = port or int(os.getenv('REDIS_PORT', 6379))
            self.password = password or os.getenv('REDIS_PASSWORD')
            self.ssl = ssl or os.getenv('REDIS_SSL', '').lower() == 'true'
            
            logger.info(f"Initializing Redis connection to {self.host}:{self.port} (SSL: {self.ssl})")
            
            # Check if we're in an event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create new event loop if none exists
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Initialize Redis client with SSL if needed
            self.redis_client = redis.Redis(
                host=self.host, 
                port=self.port, 
                db=db,
                password=self.password,
                ssl=self.ssl,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis_client.ping()
            
            self.expiration = expiration
            self._closed = False
            self._async_lock = asyncio.Lock()
            self._initialized = True
            logger.info(f"✓ Redis cache initialized and connected successfully to {self.host}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {str(e)}")
            self.redis_client = None
            self._closed = True

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
        """Get value from cache with proper error handling."""
        if self._closed:
            logger.warning("Attempting to use closed Redis connection")
            return None
        try:
            loop = self._get_loop()
            async with self._async_lock:
                value = await loop.run_in_executor(
                    None, 
                    self.redis_client.get,
                    key
                )
                if value:
                    try:
                        decoded = json.loads(value)
                        logger.debug(f"Successfully retrieved and decoded cache for key: {key}")
                        return decoded
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding cached value: {str(e)}")
                        # Delete corrupt cache entry
                        await self.delete(key)
                        return None
                logger.debug(f"Cache miss for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    async def set(self, key: str, value: Any) -> bool:
        """Set value in cache with expiration."""
        if self._closed:
            logger.warning("Attempting to use closed Redis connection")
            return False
        try:
            loop = self._get_loop()
            async with self._async_lock:
                try:
                    # Ensure we only store strings, not bytes
                    serialized = json.dumps(value, ensure_ascii=False)
                    success = await loop.run_in_executor(
                        None,
                        lambda: self.redis_client.setex(key, self.expiration, serialized)
                    )
                    if success:
                        logger.debug(f"Successfully cached value for key: {key}")
                    return bool(success)
                except (TypeError, ValueError) as e:
                    logger.error(f"Failed to serialize cache value: {str(e)}")
                    return False
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if self._closed:
            return False
        try:
            loop = self._get_loop()
            async with self._async_lock:
                return bool(await loop.run_in_executor(None, self.redis_client.delete, key))
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    async def close(self):
        """Close Redis connection properly."""
        if self._closed:
            return
        try:
            async with self._async_lock:
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
                logger.debug("Redis connection closed during cleanup")
            except Exception:
                pass  # Suppress errors during garbage collection

# Add alias for compatibility
ClimateCache = RedisCache

