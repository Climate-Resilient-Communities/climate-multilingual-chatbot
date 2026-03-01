"""
Unit tests for MultilingualClimateChatbot in main_nova.py.

Tests the process_query method with proper mocking of the unified pipeline.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock


@pytest.fixture
def chatbot():
    """Create a chatbot with all heavy init bypassed."""
    # Patch _initialize_api_keys and _initialize_components to prevent any
    # real API calls or env-var lookups during __init__
    with patch('src.main_nova.MultilingualClimateChatbot._initialize_api_keys'), \
         patch('src.main_nova.MultilingualClimateChatbot._initialize_components'), \
         patch('src.main_nova.MultilingualClimateChatbot._initialize_langsmith'):
        from src.main_nova import MultilingualClimateChatbot
        bot = MultilingualClimateChatbot('test-index')

        # Manually set attributes that __init__ would have created
        bot.pipeline = AsyncMock()
        bot.router = AsyncMock()
        bot.nova_model = MagicMock()
        bot.redis_client = None
        bot.cohere_client = MagicMock()
        bot.COHERE_API_KEY = "test_key"
        bot.response_cache = {}
        bot.conversation_history = []
        bot.feedback_metrics = []
        bot.langsmith_client = MagicMock()
        return bot


@pytest.fixture
def mock_documents():
    return [
        {
            "title": "Climate Change Overview",
            "content": "Climate change refers to long-term shifts in global weather patterns.",
            "url": "https://example.com/climate-change"
        }
    ]


@pytest.mark.asyncio
async def test_process_query_success(chatbot, mock_documents):
    """Test successful query processing delegates to pipeline."""
    chatbot.pipeline.process_query = AsyncMock(return_value={
        "success": True,
        "response": "Climate change is caused by greenhouse gas emissions.",
        "citations": ["https://example.com/climate-change"],
        "faithfulness_score": 0.95,
        "language_code": "en",
        "processing_time": 0.5,
    })

    result = await chatbot.process_query(
        query="What is climate change?",
        language_name="english"
    )

    assert result['success'] is True
    assert result.get('response') is not None
    assert result.get('language_code') == 'en'
    chatbot.pipeline.process_query.assert_called_once()


@pytest.mark.asyncio
async def test_process_query_with_translation(chatbot):
    """Test query processing with non-English language."""
    chatbot.pipeline.process_query = AsyncMock(return_value={
        "success": True,
        "response": "El cambio climático se refiere a cambios a largo plazo.",
        "citations": ["https://example.com/climate-change"],
        "faithfulness_score": 0.95,
        "language_code": "es",
        "processing_time": 0.8,
    })

    result = await chatbot.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish"
    )

    assert result['success'] is True
    assert result.get('response') is not None
    assert result.get('language_code') == 'es'


@pytest.mark.asyncio
async def test_process_query_unsupported_language(chatbot):
    """Test that unsupported languages are handled gracefully."""
    chatbot.pipeline.process_query = AsyncMock(return_value={
        "success": False,
        "message": "Language routing error",
    })

    result = await chatbot.process_query(
        query="unsupported query",
        language_name="unsupported"
    )

    assert result['success'] is False


@pytest.mark.asyncio
async def test_process_query_error_handling(chatbot):
    """Test error handling when pipeline raises exception.

    When the pipeline fails, main_nova catches the exception and falls back
    to legacy processing. If legacy also fails (e.g. missing attributes),
    it returns success=False with an error message.
    """
    chatbot.pipeline.process_query = AsyncMock(side_effect=Exception("Test error"))

    result = await chatbot.process_query(
        query="What is climate change?",
        language_name="english"
    )

    # Should return error result, not raise
    assert result['success'] is False
    assert result.get('message') is not None
    assert len(result['message']) > 0
