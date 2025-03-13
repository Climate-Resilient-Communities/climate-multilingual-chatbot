"""
Azure-specific configuration settings for the Climate Multilingual Chatbot
"""

import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def is_running_in_azure() -> bool:
    """Check if the application is running in Azure environment"""
    azure_indicators = [
        'WEBSITE_SITE_NAME',
        'AZUREAPPSERVICE_CLIENTID_4CD08148C1844070A05DD21D5B8164BF',
        'AZUREAPPSERVICE_CLIENTID_E153C87972164A3DBFCF6F463223BFD9'
    ]
    return any(os.getenv(indicator) for indicator in azure_indicators)

def get_azure_settings() -> Dict[str, Any]:
    """
    Get Azure-specific settings for the application.
    This function checks for Azure environment variables and returns appropriate configurations.
    
    Returns:
        Dictionary containing Azure-specific settings
    """
    # Default settings
    settings = {
        "is_azure": is_running_in_azure(),
        "app_service_name": os.getenv('WEBSITE_SITE_NAME', None),
        "deployment_id": os.getenv('DEPLOYMENT_ID', 'production'),
        "logging": {
            "level": os.getenv('AZURE_LOG_LEVEL', 'INFO'),
            "application_insights": os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING') is not None,
        },
        "storage": {
            "account_name": os.getenv('AZURE_STORAGE_ACCOUNT', None),
            "connection_string": os.getenv('AZURE_STORAGE_CONNECTION_STRING', None),
        },
        "redis": {
            "enabled": os.getenv('AZURE_REDIS_HOST', os.getenv('REDIS_HOST')) is not None,
            "host": os.getenv('AZURE_REDIS_HOST', os.getenv('REDIS_HOST', 'localhost')),
            "port": int(os.getenv('AZURE_REDIS_PORT', os.getenv('REDIS_PORT', 6379))),
            "password": os.getenv('AZURE_REDIS_PASSWORD', os.getenv('REDIS_PASSWORD', None)),
            "ssl": os.getenv('AZURE_REDIS_SSL', 'False').lower() == 'true'
        },
        "api_keys": {
            "openai_available": os.getenv('OPENAI_API_KEY') is not None,
            "pinecone_available": os.getenv('PINECONE_API_KEY') is not None,
            "cohere_available": os.getenv('COHERE_API_KEY') is not None,
            "tavily_available": os.getenv('TAVILY_API_KEY') is not None,
            "hf_token_available": os.getenv('HF_API_TOKEN') is not None,
            "langsmith_available": os.getenv('LANGSMITH_API_KEY') is not None
        },
        "aws": {
            "credentials_available": os.getenv('AWS_ACCESS_KEY_ID') is not None and os.getenv('AWS_SECRET_ACCESS_KEY') is not None,
        }
    }
    
    # Add Azure App Service related identifiers
    settings["azure_app_service"] = {
        "client_ids": [
            os.getenv('AZUREAPPSERVICE_CLIENTID_4CD08148C1844070A05DD21D5B8164BF'),
            os.getenv('AZUREAPPSERVICE_CLIENTID_E153C87972164A3DBFCF6F463223BFD9')
        ],
        "subscription_ids": [
            os.getenv('AZUREAPPSERVICE_SUBSCRIPTIONID_49136745AFC1498AB33449C4D9D00708'),
            os.getenv('AZUREAPPSERVICE_SUBSCRIPTIONID_49D35EF09E3A43E7B83D857E5958E03F')
        ],
        "tenant_ids": [
            os.getenv('AZUREAPPSERVICE_TENANTID_44ACAC76814F4A0E9B71363D799E6C15'),
            os.getenv('AZUREAPPSERVICE_TENANTID_82DB361B2F1B4ABD97D52FE4FC3D7286')
        ],
        "publish_profile_available": os.getenv('AZURE_WEBAPP_PUBLISH_PROFILE') is not None
    }
    
    return settings

def configure_for_azure() -> None:
    """
    Configure the application for Azure environment.
    This function should be called early in the application startup.
    """
    if not is_running_in_azure():
        return
        
    # Log Azure detection
    logger.info("Azure environment detected. Configuring application for Azure...")
    
    # Check for required API keys
    required_keys = [
        'COHERE_API_KEY', 
        'PINECONE_API_KEY', 
        'TAVILY_API_KEY', 
        'HF_API_TOKEN'
    ]
    
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        logger.warning(f"Missing required API keys in Azure environment: {', '.join(missing_keys)}")
    else:
        logger.info("All required API keys are present in the Azure environment")
    
    # Redis configuration in Azure
    redis_host = os.getenv('AZURE_REDIS_HOST', os.getenv('REDIS_HOST'))
    if redis_host:
        logger.info(f"Redis configured at {redis_host}:{os.getenv('AZURE_REDIS_PORT', os.getenv('REDIS_PORT', 6379))}")
        
        # Enable SSL for Azure Redis Cache by default if not specified
        if 'azure.com' in str(redis_host).lower() and os.getenv('AZURE_REDIS_SSL') is None:
            os.environ['AZURE_REDIS_SSL'] = 'true'
            logger.info("SSL enabled for Azure Redis Cache connection")
    else:
        logger.warning("Redis host not configured in Azure environment")
    
    # Set up Application Insights if available
    app_insights_key = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
    if app_insights_key:
        try:
            # Import only when needed
            from opencensus.ext.azure.log_exporter import AzureLogHandler
            import logging
            
            # Configure the root logger with Azure Log Handler
            root_logger = logging.getLogger()
            root_logger.addHandler(AzureLogHandler(connection_string=app_insights_key))
            
            # Log startup event
            logger.info(f"Application Insights telemetry enabled. Application started in Azure environment: {os.getenv('WEBSITE_SITE_NAME')}")
        except ImportError:
            logger.warning("Application Insights SDK not installed. Install opencensus-ext-azure for telemetry support.")
    
    # Set Ray specific configurations for Azure
    os.environ['RAY_DISABLE_DOCKER_CPU_WARNING'] = '1'
    
    # Configure AWS credentials for Bedrock access in Azure
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        logger.info("AWS credentials detected for Bedrock access")
    else:
        logger.warning("AWS credentials not found - Bedrock access may be unavailable")