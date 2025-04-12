import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.main_nova import MultilingualClimateChatbot

@pytest.fixture
def mock_documents():
    return [
        {
            "title": "Climate Change Overview",
            "content": "Climate change refers to long-term shifts in global weather patterns and temperatures.",
            "url": "https://example.com/climate-change"
        }
    ]

@pytest.fixture
def mock_nova_chat():
    mock = Mock()
    mock.nova_chat.return_value = ("Response about climate change", ["citation1"])
    return mock

@pytest.fixture
def mock_router():
    mock = Mock()
    mock.route_query.return_value = {
        'should_proceed': True,
        'processed_query': 'processed query',
        'english_query': 'What is climate change?',
        'routing_info': {
            'needs_translation': False,
            'support_level': 'command_r_plus'
        }
    }
    return mock

@pytest.fixture
async def chatbot():
    with patch('src.main_nova.BedrockModel'), \
         patch('src.main_nova.Pinecone'), \
         patch('src.main_nova.BGEM3FlagModel'), \
         patch('src.main_nova.MultilingualRouter'), \
         patch('src.main_nova.ClimateCache'), \
         patch('src.main_nova.Client'):

        bot = MultilingualClimateChatbot('test-index')
        return bot

@pytest.mark.asyncio
async def test_process_query_success(chatbot, mock_documents):
    with patch('src.models.main_nova.get_documents', return_value=mock_documents), \
         patch('src.main_nova.check_hallucination', new=AsyncMock(return_value=0.95)), \
         patch.object(chatbot, 'process_input_guards', new=AsyncMock(return_value={'passed': True, 'topic_check': True})):
        
        result = await chatbot.process_query(
            query="What is climate change?",
            language_name="english"
        )
        
        assert result['success'] is True
        assert result.get('response') is not None
        assert result.get('citations') is not None
        assert result.get('faithfulness_score', 0.0) > 0.9
        assert 'processing_time' in result
        assert result.get('language_code') == 'en'

@pytest.mark.asyncio
async def test_process_query_with_translation(chatbot, mock_documents):
    with patch('src.models.main_nova.get_documents', return_value=mock_documents), \
         patch('src.main_nova.check_hallucination', new=AsyncMock(return_value=0.95)), \
         patch.object(chatbot, 'process_input_guards', new=AsyncMock(return_value={'passed': True, 'topic_check': True})):
        
        result = await chatbot.process_query(
            query="¿Qué es el cambio climático?",
            language_name="spanish"
        )
        
        assert result['success'] is True
        assert result.get('response') is not None
        assert result.get('citations') is not None
        assert result.get('faithfulness_score', 0.0) > 0.9
        assert 'processing_time' in result
        assert result.get('language_code') == 'es'

@pytest.mark.asyncio
async def test_process_query_unsupported_language(chatbot):
    result = await chatbot.process_query(
        query="unsupported query",
        language_name="unsupported"
    )
    
    assert result['success'] is False
    assert result['routing_info']['message'] == "Language not supported"
    assert result['routing_info']['needs_translation'] is False

@pytest.mark.asyncio
async def test_process_query_error_handling(chatbot):
    with patch.object(chatbot, 'process_input_guards', side_effect=Exception("Test error")):
        result = await chatbot.process_query(
            query="What is climate change?",
            language_name="english"
        )
        
        assert result['success'] is False
        assert "Test error" in result['message']
        assert result.get('response') is None