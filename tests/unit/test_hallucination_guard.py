import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.models.hallucination_guard import extract_contexts, check_hallucination
from ragas.dataset_schema import SingleTurnSample

@pytest.fixture
def sample_docs():
    return [
        {
            'content': 'This is a test document about climate change and its effects on the environment.',
            'title': 'Climate Change Doc 1',
            'score': 0.95
        },
        {
            'content': 'Global warming leads to rising sea levels and extreme weather patterns.',
            'title': 'Climate Change Doc 2',
            'score': 0.85
        },
        {
            'content': 'Renewable energy sources can help mitigate climate change impacts.',
            'title': 'Climate Change Doc 3',
            'score': 0.75
        }
    ]

def test_extract_contexts_success(sample_docs):
    contexts = extract_contexts(sample_docs)
    
    assert len(contexts) == 3
    assert all(isinstance(ctx, str) for ctx in contexts)
    assert contexts[0] == sample_docs[0]['content']

def test_extract_contexts_with_max_limit(sample_docs):
    contexts = extract_contexts(sample_docs, max_contexts=2)
    
    assert len(contexts) == 2
    assert contexts[0] == sample_docs[0]['content']
    assert contexts[1] == sample_docs[1]['content']

def test_extract_contexts_empty_docs():
    contexts = extract_contexts([])
    assert len(contexts) == 0

def test_extract_contexts_missing_content(sample_docs):
    docs_missing_content = [{'title': 'Test'}]
    contexts = extract_contexts(docs_missing_content)
    assert len(contexts) == 1
    assert contexts[0] == ''

@pytest.mark.asyncio
async def test_check_hallucination_success():
    mock_nova = Mock()
    mock_nova.query_normalizer.return_value = "0.95"
    
    with patch('src.models.hallucination_guard.BedrockModel', return_value=mock_nova):
        score = await check_hallucination(
            question="What is climate change?",
            answer="Climate change refers to long-term shifts in temperatures and weather patterns.",
            contexts=["Climate change is a long-term shift in weather patterns."]
        )
        
        assert score == 0.95
        mock_nova.query_normalizer.assert_called_once()

@pytest.mark.asyncio
async def test_check_hallucination_api_error():
    mock_nova = Mock()
    mock_nova.query_normalizer.side_effect = Exception("API Error")
    
    with patch('src.models.hallucination_guard.BedrockModel', return_value=mock_nova):
        score = await check_hallucination(
            question="test question",
            answer="test answer",
            contexts=["test context"]
        )
        
        assert score == 0.0

@pytest.mark.asyncio
async def test_check_hallucination_long_inputs():
    mock_nova = Mock()
    mock_nova.query_normalizer.return_value = "0.85"
    
    with patch('src.models.hallucination_guard.BedrockModel', return_value=mock_nova):
        long_question = " ".join(["climate"] * 200)
        long_answer = " ".join(["response"] * 300)
        long_context = " ".join(["context"] * 300)
        
        score = await check_hallucination(
            question=long_question,
            answer=long_answer,
            contexts=[long_context]
        )
        
        assert score == 0.85
        # Verify inputs were truncated
        call_args = mock_nova.query_normalizer.call_args[1]
        assert "query" in call_args
        assert len(call_args["query"].split()) < 1000  # Ensure prompt is not too long