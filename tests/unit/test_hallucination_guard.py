import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from src.models.hallucination_guard import extract_contexts, check_hallucination


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
    """Test hallucination check with mocked Nova model."""
    mock_nova = Mock()
    # check_hallucination uses content_generation, not query_normalizer
    mock_nova.content_generation = AsyncMock(return_value=json.dumps({
        "faithfulness_score": 0.95,
        "supported_claims": ["Climate change is real"],
        "unsupported_claims": [],
        "reasoning": "All claims are supported by context"
    }))

    with patch('src.models.hallucination_guard.BedrockModel', return_value=mock_nova):
        score = await check_hallucination(
            question="What is climate change?",
            answer="Climate change refers to long-term shifts in temperatures and weather patterns.",
            contexts=["Climate change is a long-term shift in weather patterns."]
        )

        assert score == 0.95
        mock_nova.content_generation.assert_called_once()


@pytest.mark.asyncio
async def test_check_hallucination_api_error():
    """Test fallback when Nova model raises an error."""
    mock_nova = Mock()
    mock_nova.content_generation = AsyncMock(side_effect=Exception("API Error"))

    with patch('src.models.hallucination_guard.BedrockModel', return_value=mock_nova):
        score = await check_hallucination(
            question="test question",
            answer="test answer",
            contexts=["test context"]
        )

        # Should return conservative score on error
        assert score == 0.3


@pytest.mark.asyncio
async def test_check_hallucination_invalid_json():
    """Test handling of non-JSON response from Nova model."""
    mock_nova = Mock()
    # Return a non-JSON string that contains a number
    mock_nova.content_generation = AsyncMock(return_value="Faithfulness score: 0.85")

    with patch('src.models.hallucination_guard.BedrockModel', return_value=mock_nova):
        score = await check_hallucination(
            question="What is climate change?",
            answer="Climate change is caused by greenhouse gases.",
            contexts=["Greenhouse gas emissions drive climate change."]
        )

        # Should extract score from text
        assert score == 0.85


@pytest.mark.asyncio
async def test_check_hallucination_empty_inputs():
    """Test with empty inputs returns neutral score."""
    score = await check_hallucination(
        question="",
        answer="",
        contexts=[]
    )

    assert score == 0.5  # Neutral score for invalid inputs
