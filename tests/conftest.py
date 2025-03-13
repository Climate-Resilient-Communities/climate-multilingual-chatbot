import os
import sys
import pytest
from dotenv import load_dotenv

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the project root to the Python path
sys.path.insert(0, project_root)

def pytest_configure(config):
    """Set up test environment"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Ensure critical environment variables are available
    required_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'COHERE_API_KEY',
        'PINECONE_API_KEY',
        'TAVILY_API_KEY'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.fail(f"Missing required environment variables: {', '.join(missing)}")

@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Fixture to ensure environment is loaded for all tests"""
    load_dotenv()
    return True