import ray
import os
import logging
import json
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

def initialize_ray_for_azure():
    """Initialize Ray with optimized settings for Azure App Service with limited shared memory."""
    try:
        # Check if Ray is already initialized
        if ray.is_initialized():
            logger.info("Ray is already initialized, skipping initialization")
            return True

        logger.info("Initializing Ray with Azure-optimized settings")
        
        # Create a temporary directory for Ray's storage
        tmp_dir = tempfile.mkdtemp(prefix="ray_")
        logger.info(f"Created temporary directory for Ray: {tmp_dir}")
        
        # Configure Ray with minimal shared memory usage
        ray_config = {
            # Use minimal plasma store memory - just enough for small objects
            "object_store_memory": 50 * 1024 * 1024,  # 50 MB - below /dev/shm limits
            
            # Enable spilling objects to disk when shared memory is full
            "object_spilling_config": json.dumps({
                "type": "filesystem",
                "params": {"directory_path": tmp_dir}
            }),
            
            # Limit resources for a small environment
            "num_cpus": 1,  # Use only 1 CPU
            "dashboard_host": "127.0.0.1",  # Only local dashboard access
            "ignore_reinit_error": True,
            
            # Set storage path explicitly to temp directory
            "temp_dir": tmp_dir,
            
            # Avoid consuming too much memory
            "dashboard_port": 0,  # Disable dashboard to save memory
            "include_dashboard": False,
            
            # Set plasma store to small socket buffer
            "_system_config": {
                "object_spilling_threshold": 0.8,
                "max_io_workers": 1,
                "automatic_object_spilling_enabled": True,
                "object_store_full_delay_ms": 100
            }
        }
        
        # Initialize Ray with our configuration
        ray.init(**ray_config)
        
        logger.info("✅ Ray initialized successfully with Azure-optimized configuration")
        logger.info(f"Ray object store memory: {ray_config['object_store_memory'] / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Ray: {str(e)}")
        return False

def shutdown_ray():
    """Safely shutdown Ray if it's running."""
    try:
        if ray.is_initialized():
            ray.shutdown()
            logger.info("Ray shutdown successfully")
            return True
    except Exception as e:
        logger.error(f"Error shutting down Ray: {str(e)}")
    return False