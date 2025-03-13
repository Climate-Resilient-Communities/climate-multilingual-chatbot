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
async def test_aws_bedrock_connectivity():
    """Test AWS Bedrock API connectivity"""
    try:
        client = boto3.client(
            'bedrock',  # Changed from bedrock-runtime to bedrock
            region_name='us-east-1',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        # Simple test to verify connectivity
        response = client.get_foundation_model(
            modelIdentifier='anthropic.claude-v2'
        )
        assert response is not None
        print("✅ AWS Bedrock connection successful")
    except Exception as e:
        pytest.fail(f"AWS Bedrock connection failed: {str(e)}")

@pytest.mark.asyncio
async def test_cohere_connectivity():
    """Test Cohere API connectivity"""
    try:
        api_key = os.getenv('COHERE_API_KEY')
        if not api_key:
            raise ValueError("COHERE_API_KEY environment variable is not set")
        
        co = cohere.Client(api_key=api_key)
        # Simple test query
        response = co.chat(
            message="Hi",
            model="command"
        )
        assert response is not None
        print("✅ Cohere API connection successful")
    except Exception as e:
        pytest.fail(f"Cohere API connection failed: {str(e)}")

@pytest.mark.asyncio
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
            assert response.status_code in (200, 401)  # 401 means invalid key but API is reachable
            print("✅ Tavily API connection successful")
    except Exception as e:
        pytest.fail(f"Tavily API connection failed: {str(e)}")