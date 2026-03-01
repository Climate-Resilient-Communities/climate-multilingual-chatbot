import os
import pytest
import boto3
import cohere
from pinecone import Pinecone
import httpx
from src.utils.env_loader import load_environment

# Load environment variables before tests
load_environment()

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'),
    reason="Requires AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
)
async def test_aws_bedrock_connectivity():
    """Test AWS Bedrock API connectivity"""
    try:
        client = boto3.client(
            'bedrock',
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        # Use list_foundation_models instead of get_foundation_model
        # to avoid dependency on specific model availability
        response = client.list_foundation_models()
        assert response is not None
        assert 'modelSummaries' in response
        print("AWS Bedrock connection successful")
    except Exception as e:
        pytest.fail(f"AWS Bedrock connection failed: {str(e)}")

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv('COHERE_API_KEY'), reason="Requires COHERE_API_KEY")
async def test_cohere_connectivity():
    """Test Cohere API connectivity"""
    try:
        api_key = os.getenv('COHERE_API_KEY')
        if not api_key:
            raise ValueError("COHERE_API_KEY environment variable is not set")

        co = cohere.ClientV2(api_key=api_key)
        # command/command-r/command-r-plus removed Sept 2025.
        # Use tiny-aya-global — the same model used in production pipeline.
        response = co.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="tiny-aya-global"
        )
        assert response is not None
        print("Cohere API connection successful")
    except Exception as e:
        pytest.fail(f"Cohere API connection failed: {str(e)}")

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv('PINECONE_API_KEY'), reason="Requires PINECONE_API_KEY")
async def test_pinecone_connectivity():
    """Test Pinecone API connectivity"""
    try:
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable is not set")
        
        pc = Pinecone(api_key=api_key)
        # List indexes to verify connectivity
        indexes = pc.list_indexes()
        assert indexes is not None
        print("✅ Pinecone API connection successful")
    except Exception as e:
        pytest.fail(f"Pinecone API connection failed: {str(e)}")

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv('TAVILY_API_KEY'), reason="Requires TAVILY_API_KEY")
async def test_tavily_connectivity():
    """Test Tavily API connectivity"""
    try:
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is not set")

        async with httpx.AsyncClient() as client:
            # Using POST request with proper JSON payload
            response = await client.post(
                'https://api.tavily.com/search',
                json={
                    'api_key': api_key,
                    'query': 'test query',
                    'search_depth': 'basic'
                }
            )
            # 200=success, 401=invalid key, 429=rate limit, 432=usage limit
            # Any of these means the API is reachable
            assert response.status_code in (200, 401, 429, 432), (
                f"Tavily API returned unexpected status {response.status_code}"
            )
            print("✅ Tavily API connection successful")
    except Exception as e:
        pytest.fail(f"Tavily API connection failed: {str(e)}")