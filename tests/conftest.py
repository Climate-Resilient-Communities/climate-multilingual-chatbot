import os
import sys
import warnings
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

    # Warn about missing environment variables instead of failing
    # Tests that need specific keys use @pytest.mark.skipif decorators
    required_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'COHERE_API_KEY',
        'PINECONE_API_KEY',
        'TAVILY_API_KEY'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        warnings.warn(
            f"Missing environment variables: {', '.join(missing)}. "
            f"Tests requiring these services will be skipped.",
            UserWarning
        )

@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Fixture to ensure environment is loaded for all tests"""
    load_dotenv()
    return True

@pytest.fixture(scope="session")
def chatbot():
    """Fixture to provide an instance of MultilingualClimateChatbot.

    This fixture creates a real chatbot instance that connects to live services.
    Tests using this fixture should be marked with appropriate skip decorators
    for missing API keys.
    """
    from src.main_nova import MultilingualClimateChatbot
    test_index_name = "climate-change-adaptation-index-10-24-prod"
    return MultilingualClimateChatbot(index_name=test_index_name)