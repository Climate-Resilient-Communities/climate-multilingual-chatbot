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
            
            # Test connection but don't block initialization
            try:
                self.redis_client.ping()
                logger.info(f"✓ Redis connection test successful to {self.host}")
            except Exception as ping_err:
                logger.warning(f"Redis ping failed but continuing: {str(ping_err)}")
            
            self.expiration = expiration
            self._closed = False
            self._initialized = True
            logger.info(f"✓ Redis cache initialized for {self.host}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {str(e)}")
            self.redis_client = None
            self._closed = True

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with proper error handling."""
        if self._closed or not self.redis_client:
            logger.warning("Attempting to use closed Redis connection")
            return None
        try:
            # Run Redis operation in thread to avoid blocking event loop
            value = await asyncio.to_thread(self.redis_client.get, key)
            if value:
                try:
                    decoded = json.loads(value)
                    logger.debug(f"Successfully retrieved and decoded cache for key: {key}")
                    return decoded
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding cached value: {str(e)}")
                    # Delete corrupt cache entry
                    await asyncio.to_thread(self.redis_client.delete, key)
                    return None
            logger.debug(f"Cache miss for key: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    async def set(self, key: str, value: Any) -> bool:
        """Set value in cache with expiration."""
        if self._closed or not self.redis_client:
            logger.warning("Attempting to use closed Redis connection")
            return False
        try:
            try:
                # Ensure we only store strings, not bytes
                serialized = json.dumps(value, ensure_ascii=False)
                success = await asyncio.to_thread(
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
        if self._closed or not self.redis_client:
            return False
        try:
            return bool(await asyncio.to_thread(self.redis_client.delete, key))
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    async def close(self):
        """Close Redis connection properly."""
        if self._closed or not self.redis_client:
            return
        try:
            if self.redis_client:
                await asyncio.to_thread(self.redis_client.close)
            self._closed = True
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")

    def __del__(self):
        """Ensure resources are cleaned up."""
        if not getattr(self, '_closed', True) and hasattr(self, 'redis_client'):
            try:
                self.redis_client.close()
                logger.debug("Redis connection closed during cleanup")
            except Exception:
                pass  # Suppress errors during garbage collection

# Add alias for compatibility
ClimateCache = RedisCache

