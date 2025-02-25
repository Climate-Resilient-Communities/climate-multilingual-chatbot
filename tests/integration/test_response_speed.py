import pytest
from src.models.gen_response_nova import nova_chat
from src.utils.env_loader import load_environment
from src.models.nova_generation import NovaChat
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
    def nova_client(self):
        load_environment()
        return NovaChat()

    @pytest.mark.asyncio
    async def test_nova_response_speed(self, test_docs, nova_client):
        """Test Nova response generation speed"""
        query = "What is climate change and its main impacts?"
        
        start_time = time.time()
        response, citations = await nova_chat(query, test_docs, nova_client)
        
        processing_time = time.time() - start_time
        
        assert processing_time < 30, "Response generation took too long"
        assert isinstance(response, str)
        assert len(response) > 0
        assert isinstance(citations, list)

    @pytest.mark.asyncio
    async def test_cached_response_speed(self, test_docs, nova_client):
        """Test cached response retrieval speed"""
        query = "What is climate change and its main impacts?"
        
        # First call to cache the response
        await nova_chat(query, test_docs, nova_client)
        
        # Second call should be faster due to caching
        start_time = time.time()
        response, citations = await nova_chat(query, test_docs, nova_client)
        processing_time = time.time() - start_time
        
        assert processing_time < 1, "Cached response retrieval took too long"
        assert isinstance(response, str)
        assert len(response) > 0