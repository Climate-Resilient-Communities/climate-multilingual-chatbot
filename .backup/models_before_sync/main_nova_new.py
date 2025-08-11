import os
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
import ray
from langsmith import traceable
from src.utils.env_loader import load_environment
from src.models.climate_pipeline import ClimateQueryPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultilingualClimateChatbot:
    """Legacy wrapper for backwards compatibility - now uses ClimateQueryPipeline."""
    
    def __init__(self, index_name: str, use_ray: bool = False):
        load_environment()
        self.use_ray = use_ray
        if self.use_ray:
            if not ray.is_initialized():
                ray.init()
        
        # Initialize the new pipeline
        self.pipeline = ClimateQueryPipeline(index_name=index_name)
        logger.info("✓ MultilingualClimateChatbot initialized with new pipeline")
        # One-time prewarm to reduce first-query latency
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.info("Scheduling pipeline.prewarm() in running loop (legacy wrapper)")
                loop.create_task(self.pipeline.prewarm())
            else:
                logger.info("Running pipeline.prewarm() before serving (legacy wrapper)")
                loop.run_until_complete(self.pipeline.prewarm())
        except Exception as e:
            logger.warning(f"Prewarm skipped (legacy wrapper): {e}")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            await self.pipeline.cleanup()
            
            # Shutdown Ray if initialized
            if ray.is_initialized():
                try:
                    ray.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down Ray: {str(e)}")
            
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")

    async def _process_query_internal(
        self,
        query: str,
        language_name: str,
        run_manager=None
    ) -> Dict[str, Any]:
        """Legacy method - now delegates to the new pipeline."""
        logger.info("Delegating to ClimateQueryPipeline...")
        return await self.pipeline.process_query(
            query=query,
            language_name=language_name,
            run_manager=run_manager
        )

    # Legacy helper methods that might be called from other parts of the codebase
    def get_language_code(self, language_name: str) -> str:
        """Convert language name to code - delegate to pipeline."""
        return self.pipeline.get_language_code(language_name)

    def _init_cohere(self):
        """Legacy method - now handled by pipeline."""
        return self.pipeline.cohere_client

    def _initialize_redis(self):
        """Legacy method - now handled by pipeline.""" 
        return self.pipeline.redis_client

    # Backwards compatibility properties
    @property
    def nova_model(self):
        """Access to Nova model for backwards compatibility."""
        return self.pipeline.nova_model

    @property
    def cohere_model(self):
        """Access to Cohere model for backwards compatibility."""
        return self.pipeline.cohere_model

    @property
    def router(self):
        """Access to router for backwards compatibility."""
        return self.pipeline.router

    @property
    def redis_client(self):
        """Access to Redis client for backwards compatibility."""
        return self.pipeline.redis_client

    @property
    def COHERE_API_KEY(self):
        """Access to Cohere API key for backwards compatibility."""
        return self.pipeline.COHERE_API_KEY

    @property
    def cohere_client(self):
        """Access to Cohere client for backwards compatibility."""
        return self.pipeline.cohere_client
