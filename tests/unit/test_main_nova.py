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
async def mock_get_documents():
    return AsyncMock(return_value=[{
        "title": "Climate Change Overview",
        "content": "Climate change refers to long-term shifts in global weather patterns and temperatures.",
        "url": "https://example.com/climate-change",
        "metadata": {
            "text": "Climate change refers to long-term shifts in global weather patterns and temperatures.",
            "title": "Climate Change Overview",
            "url": "https://example.com/climate-change"
        },
        "score": 0.95
    }])

@pytest.fixture
def chatbot():
    with patch('src.main_nova.MultilingualClimateChatbot._initialize_api_keys'), \
         patch('src.main_nova.MultilingualClimateChatbot._initialize_models'), \
         patch('src.main_nova.MultilingualClimateChatbot._initialize_retrieval'), \
         patch('src.main_nova.MultilingualClimateChatbot._initialize_language_router'), \
         patch('src.main_nova.MultilingualClimateChatbot._initialize_nova_flow'), \
         patch('src.main_nova.MultilingualClimateChatbot._initialize_redis'), \
         patch('src.main_nova.ray.init'), \
         patch('src.main_nova.ray.get', return_value="yes"):
        
        import numpy as np
        bot = MultilingualClimateChatbot("test-index")
        
        # Add COHERE_API_KEY
        bot.COHERE_API_KEY = "test-key"
        
        # Initialize required attributes that would normally be set in _initialize methods
        bot.nova_model = Mock()
        bot.nova_model.query_normalizer = Mock(return_value="normalized query")
        bot.nova_model.nova_translation = Mock(return_value="translated text")
        
        # Mock the topic moderation pipeline
        bot.topic_moderation_pipe = Mock()
        bot.topic_moderation_pipe.return_value = [{'label': 'yes', 'score': 0.95}]
        
        # Set up nova_chat with proper return values
        nova_chat_mock = Mock()
        nova_chat_mock.nova_chat = Mock(return_value=("Response about climate change", ["citation1"]))
        bot.nova_chat = nova_chat_mock
        
        # Set up router with proper return values
        router_mock = Mock()
        router_mock.route_query = Mock(return_value={
            'should_proceed': True,
            'processed_query': 'processed query',
            'english_query': 'What is climate change?',
            'routing_info': {
                'needs_translation': False,
                'support_level': 'command_r_plus',
                'message': ''
            }
        })
        bot.router = router_mock
        
        # Set up index mock with proper response structure
        bot.index = Mock()
        bot.index.query = Mock(return_value={
            "matches": [
                {
                    "id": "1",
                    "score": 0.95,
                    "metadata": {
                        "text": "Sample climate change content",
                        "title": "Climate Change Overview",
                        "url": "https://example.com/climate-change"
                    }
                }
            ]
        })
        
        # Set up embed model with numpy array response
        bot.embed_model = Mock()
        bot.embed_model.encode = Mock(return_value=np.array([[0.1, 0.2, 0.3]], dtype=np.float32))
        
        bot.cohere_client = Mock()
        bot.cohere_client.rerank = Mock(return_value={
            "results": [
                {
                    "document": {
                        "text": "mocked text"
                    },
                    "relevance_score": 0.95
                }
            ]
        })

        return bot

@pytest.mark.asyncio
async def test_process_query_success(chatbot, mock_get_documents):
    # Mock the necessary components
    with patch('src.main_nova.get_documents', mock_get_documents), \
         patch('src.main_nova.check_hallucination', new=AsyncMock(return_value=0.95)), \
         patch.object(chatbot, 'process_input_guards', new=AsyncMock(return_value={'passed': True, 'topic_check': True})):
        
        # Test the process_query method
        result = await chatbot.process_query(
            query="What is climate change?",
            language_name="english"
        )
        
        # Verify the result
        assert result['success'] is True
        assert 'Response about climate change' in result['response']
        assert result['citations'] == ['citation1']
        assert result['faithfulness_score'] == 0.95
        assert 'processing_time' in result
        assert result['language_code'] == 'en'

@pytest.mark.asyncio
async def test_process_query_with_translation(chatbot, mock_get_documents):
    # Update router mock for translation case
    chatbot.router.route_query.return_value = {
        'should_proceed': True,
        'processed_query': 'processed query',
        'english_query': 'What is climate change?',
        'routing_info': {
            'needs_translation': True,
            'support_level': 'command_r_plus',
            'message': ''
        }
    }
    
    with patch('src.main_nova.get_documents', mock_get_documents), \
         patch('src.main_nova.check_hallucination', new=AsyncMock(return_value=0.85)), \
         patch.object(chatbot, 'process_input_guards', new=AsyncMock(return_value={'passed': True, 'topic_check': True})):
        
        result = await chatbot.process_query(
            query="¿Qué es el cambio climático?",
            language_name="spanish"
        )
        
        assert result['success'] is True
        assert result['response'] == "translated text"
        assert 'faithfulness_score' in result
        assert result['language_code'] == 'es'

@pytest.mark.asyncio
async def test_process_query_unsupported_language(chatbot):
    # No need to mock route_query since we'll fail at language validation
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