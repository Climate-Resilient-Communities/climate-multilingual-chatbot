import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from src.models.query_processing_chain import QueryProcessingChain

class MockNovaModel:
    def query_normalizer(self, query, language):
        return query.lower().strip()

class MockChatbot:
    def __init__(self):
        self.nova_model = MockNovaModel()
        
    async def _process_query_internal(self, query, language_name, run_manager=None):
        return {
            "success": True,
            "response": f"Test response for: {query}",
            "citations": ["Test citation"],
            "faithfulness_score": 0.9,
            "processing_time": 0.1
        }

@pytest.fixture
def mock_chatbot():
    return MockChatbot()

@pytest.fixture
def query_chain(mock_chatbot):
    return QueryProcessingChain(chatbot=mock_chatbot)

@pytest.mark.asyncio
async def test_query_processing_chain():
    # Setup
    chatbot = MockChatbot()
    chain = QueryProcessingChain(chatbot=chatbot)
    
    # Test data
    test_input = {
        "query": "What is climate change?",
        "language_name": "english"
    }
    
    # Execute chain
    result = await chain.acall(test_input)
    
    # Verify results
    assert result["success"] is True
    assert "Test response for:" in result["response"]
    assert isinstance(result["citations"], list)
    assert isinstance(result["faithfulness_score"], float)
    assert isinstance(result["processing_time"], float)

@pytest.mark.asyncio
async def test_query_processing_chain_with_callbacks():
    # Setup
    chatbot = MockChatbot()
    chain = QueryProcessingChain(chatbot=chatbot)
    
    # Mock callback manager
    mock_callback_manager = MagicMock()
    mock_callback_manager.on_text = AsyncMock()
    
    # Test data
    test_input = {
        "query": "What is climate change?",
        "language_name": "english"
    }
    
    # Execute chain with callbacks
    result = await chain._acall(test_input, run_manager=mock_callback_manager)
    
    # Verify callback interactions
    mock_callback_manager.on_text.assert_any_call("Starting ClimateChat Query Processing")
    mock_callback_manager.on_text.assert_any_call(f"Completed processing with result: {result}")
    
    # Verify results
    assert result["success"] is True
    assert isinstance(result["response"], str)
    assert isinstance(result["citations"], list)
    assert isinstance(result["faithfulness_score"], float)
    assert isinstance(result["processing_time"], float)