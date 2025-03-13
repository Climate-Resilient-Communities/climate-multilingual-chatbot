import os
from dotenv import load_dotenv
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

__all__ = ['load_environment', 'validate_environment']

def load_environment():
    """
    Loads environment variables from the .env file.
    Call this function wherever you need to ensure environment variables are loaded.
    Returns True if environment was loaded successfully.
    """
    try:
        load_dotenv()
        return True
    except Exception as e:
        logger.error(f"Error loading environment: {e}")
        return False

def validate_environment(required_vars: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Validates that required environment variables are set.
    
    Args:
        required_vars: List of environment variable names to check for
        
    Returns:
        Dictionary with results of validation including missing variables
    """
    if required_vars is None:
        # Default required environment variables for the application
        required_vars = [
            'COHERE_API_KEY',
            'PINECONE_API_KEY', 
            'TAVILY_API_KEY',
            'HF_API_TOKEN',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY'
        ]
        
        # Optional but recommended variables
        recommended_vars = [
            'LANGSMITH_API_KEY',
            'LANGSMITH_PROJECT',
            'REDIS_HOST'
        ]
        
        # Log recommendations but don't make them required
        missing_recommended = [var for var in recommended_vars if os.getenv(var) is None]
        if missing_recommended:
            logger.warning(f"Missing recommended environment variables: {', '.join(missing_recommended)}")
    
    # Check Azure-specific variables if running in Azure
    if os.getenv('WEBSITE_SITE_NAME') or any(os.getenv(var) for var in [
        'AZUREAPPSERVICE_CLIENTID_4CD08148C1844070A05DD21D5B8164BF',
        'AZUREAPPSERVICE_CLIENTID_E153C87972164A3DBFCF6F463223BFD9'
    ]):
        # Azure is detected, no additional required variables since
        # we're using the existing ones from the .env file
        azure_vars = []
        required_vars.extend(azure_vars)
    
    # Check which variables are missing
    missing_vars = [var for var in required_vars if os.getenv(var) is None]
    
    return {
        "all_present": len(missing_vars) == 0,
        "missing_vars": missing_vars,
        "is_azure": os.getenv('WEBSITE_SITE_NAME') is not None or any(os.getenv(var) for var in [
            'AZUREAPPSERVICE_CLIENTID_4CD08148C1844070A05DD21D5B8164BF',
            'AZUREAPPSERVICE_CLIENTID_E153C87972164A3DBFCF6F463223BFD9'
        ])
    }