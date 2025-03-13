"""
System initialization and coordination module
"""
import asyncio
import logging
from typing import Dict, Any, Optional
import redis
import pinecone
from src.utils.error_handler import handle_async_errors, ChatbotError
from src.data.config.config import REDIS_CONFIG, API_CONFIG
from src.utils.system_monitor import SystemMonitor
from src.utils.logging_config import setup_logging
from src.utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class SystemInitializer:
    def __init__(self):
        self.redis_client = None
        self.pinecone_client = None
        self.monitor = None
        self.metrics = MetricsCollector()
        
    @handle_async_errors
    async def init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_CONFIG["host"],
                port=REDIS_CONFIG["port"],
                db=REDIS_CONFIG["db"],
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            self.redis_client.ping()
            logger.info("✓ Redis connection established")
            return self.redis_client
        except Exception as e:
            logger.error(f"Redis initialization failed: {str(e)}")
            return None

    @handle_async_errors
    async def init_pinecone(self) -> Optional[pinecone.Pinecone]:
        """Initialize Pinecone connection"""
        try:
            self.pinecone_client = pinecone.Pinecone(
                api_key=os.getenv("PINECONE_API_KEY"),
                environment=API_CONFIG["pinecone"]["environment"]
            )
            self.pinecone_client.list_indexes()  # Test connection
            logger.info("✓ Pinecone connection established")
            return self.pinecone_client
        except Exception as e:
            logger.error(f"Pinecone initialization failed: {str(e)}")
            return None

    @handle_async_errors
    async def init_monitoring(self) -> bool:
        """Initialize system monitoring"""
        try:
            self.monitor = SystemMonitor()
            # Start monitoring in background
            asyncio.create_task(self.monitor.monitor_loop())
            logger.info("✓ System monitoring started")
            return True
        except Exception as e:
            logger.error(f"Monitoring initialization failed: {str(e)}")
            return False

    async def initialize_all(self) -> Dict[str, Any]:
        """Initialize all system components"""
        # Setup logging first
        setup_logging()
        logger.info("Starting system initialization...")

        # Initialize components in parallel
        results = await asyncio.gather(
            self.init_redis(),
            self.init_pinecone(),
            self.init_monitoring(),
            return_exceptions=True
        )

        status = {
            "redis": results[0] is not None,
            "pinecone": results[1] is not None,
            "monitoring": results[2] is True
        }

        if all(status.values()):
            logger.info("✓ All systems initialized successfully")
        else:
            failed_systems = [sys for sys, ok in status.items() if not ok]
            logger.error(f"System initialization partially failed. Failed systems: {failed_systems}")

        return {
            "success": all(status.values()),
            "status": status,
            "redis_client": self.redis_client,
            "pinecone_client": self.pinecone_client,
            "system_monitor": self.monitor
        }

    async def shutdown(self):
        """Gracefully shutdown all systems"""
        try:
            # Close Redis connection
            if self.redis_client:
                self.redis_client.close()
                logger.info("Redis connection closed")

            # Stop monitoring
            if self.monitor:
                # Assuming monitor has running tasks
                for task in asyncio.all_tasks():
                    if 'monitor_loop' in str(task):
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                logger.info("System monitoring stopped")

            logger.info("✓ All systems shutdown successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            raise

async def initialize_system() -> SystemInitializer:
    """Helper function to initialize the system"""
    initializer = SystemInitializer()
    await initializer.initialize_all()
    return initializer