import os
import pytest
from src.models.gen_response_nova import generate_chat_response
from src.utils.env_loader import load_environment
from src.models.nova_flow import BedrockModel
import time
import asyncio

@pytest.mark.integration
class TestResponseSpeed:
    @pytest.fixture
    def test_docs(self):
        return [
            {
                'title': 'Climate Change Overview',
                'content': 'Climate change is a long-term shift in global weather patterns and temperatures.',
                'url': ['https://example.com/climate']
            },
            {
                'title': 'Impact Analysis',
                'content': 'Rising temperatures are causing more extreme weather events worldwide.',
                'url': ['https://example.com/impacts']
            }
        ]

    @pytest.fixture
    def nova_model(self):
        load_environment()
        return BedrockModel()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'),
        reason="Requires AWS Bedrock credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
    )
    async def test_nova_response_speed(self, test_docs, nova_model):
        """Test Nova response generation speed"""
        query = "What is climate change and its main impacts?"

        start_time = time.time()
        response, citations = await generate_chat_response(query, test_docs, nova_model)

        processing_time = time.time() - start_time

        assert processing_time < 30, "Response generation took too long"
        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(citations, list)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'),
        reason="Requires AWS Bedrock credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
    )
    async def test_cached_response_speed(self, test_docs, nova_model):
        """Test cached response retrieval speed"""
        query = "What is climate change and its main impacts?"

        # First call to cache the response
        await generate_chat_response(query, test_docs, nova_model)

        # Second call should be faster due to caching
        start_time = time.time()
        response, citations = await generate_chat_response(query, test_docs, nova_model)
        processing_time = time.time() - start_time

        assert processing_time < 5, "Cached response retrieval took too long"
        assert isinstance(response, str)
        assert len(response) > 0
