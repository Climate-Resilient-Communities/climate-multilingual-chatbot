"""
Azure-specific configuration settings for the Climate Multilingual Chatbot
"""

import os
from typing import Dict, Any, Optional
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_running_in_azure() -> bool:
    """Check if the application is running in Azure environment"""
    return bool(os.getenv("WEBSITE_SITE_NAME"))

def get_azure_settings() -> Dict[str, Any]:
    """
    Get Azure-specific settings for the application.
    This function checks for Azure environment variables and returns appropriate configurations.
    
    Returns:
        Dictionary containing Azure-specific settings
    """
    return {
        "WEBSITE_SITE_NAME": os.getenv("WEBSITE_SITE_NAME", ""),
        "WEBSITE_HOSTNAME": os.getenv("WEBSITE_HOSTNAME", ""),
        "WEBSITE_INSTANCE_ID": os.getenv("WEBSITE_INSTANCE_ID", ""),
        "WEBSITE_RESOURCE_GROUP": os.getenv("WEBSITE_RESOURCE_GROUP", ""),
        "WEBSITES_PORT": os.getenv("WEBSITES_PORT", "8000"),
        "APPINSIGHTS_INSTRUMENTATIONKEY": os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "")
    }

def configure_for_azure() -> None:
    """
    Configure the application for Azure environment.
    This function should be called early in the application startup.
    """
    try:
        # Set up Application Insights if available
        if os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY"):
            try:
                logger.addHandler(
                    AzureLogHandler(
                        connection_string=f"InstrumentationKey={os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')}"
                    )
                )
                logger.info(f"Application Insights telemetry enabled. Application started in Azure environment: {os.getenv('WEBSITE_SITE_NAME')}")
            except ImportError:
                logger.warning("Application Insights SDK not installed. Install opencensus-ext-azure for telemetry support.")
        
        # Configure AWS credentials for Bedrock access in Azure
        if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
            logger.info("AWS credentials detected for Bedrock access")
        else:
            logger.warning("AWS credentials not found - Bedrock access may be unavailable")
        
        # Set Azure-specific environment variables
        os.environ['HF_HOME'] = "/tmp/huggingface"
        os.environ['TRANSFORMERS_CACHE'] = "/tmp/huggingface/transformers"
        os.environ['TORCH_HOME'] = "/tmp/torch"
        os.environ['XDG_CACHE_HOME'] = "/tmp/cache"
        
        # Create necessary directories
        os.makedirs("/tmp/huggingface/transformers", exist_ok=True)
        os.makedirs("/tmp/torch", exist_ok=True)
        os.makedirs("/tmp/cache", exist_ok=True)
        
        logger.info("Azure environment configuration completed")
        
    except Exception as e:
        logger.error(f"Error configuring Azure environment: {str(e)}")
        raise