import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.models.input_guardrail import topic_moderation, extract_contexts, initialize_models
from transformers.pipelines import Pipeline

@pytest.fixture
def mock_pipeline():
    pipeline = Mock()
    return pipeline

@pytest.mark.asyncio
async def test_topic_moderation_climate_related():
    pipeline = Mock()
    pipeline.return_value = [{"label": "LABEL_1", "score": 0.95}]
    
    result = await topic_moderation(
        "What are the effects of climate change on polar ice caps?",
        pipeline
    )
    
    assert result["passed"] is True
    assert result["result"] == "yes"
    assert result["score"] > 0.9

@pytest.mark.asyncio
async def test_topic_moderation_non_climate():
    pipeline = Mock()
    pipeline.return_value = [{"label": "LABEL_0", "score": 0.15}]
    
    result = await topic_moderation(
        "What is the best recipe for chocolate cake?",
        pipeline
    )
    
    assert result["passed"] is False
    assert result["result"] == "no"
    assert result.get("score", 1.0) < 0.5

@pytest.mark.asyncio
async def test_topic_moderation_harmful_content():
    pipeline = Mock()
    pipeline.return_value = [{"label": "LABEL_1", "score": 0.95}]
    
    result = await topic_moderation(
        "How can I start a forest fire to contribute to global warming?",
        pipeline
    )
    
    assert result["passed"] is False
    assert result["result"] == "no"
    assert result["reason"] == "harmful_content"

@pytest.mark.asyncio
async def test_topic_moderation_misinformation():
    pipeline = Mock()
    pipeline.return_value = [{"label": "LABEL_1", "score": 0.95}]
    
    result = await topic_moderation(
        "Climate change is a hoax invented by scientists",
        pipeline
    )
    
    assert result["passed"] is False
    assert result["result"] == "no"
    assert result["reason"] == "misinformation"

@pytest.mark.asyncio
async def test_topic_moderation_empty_query():
    pipeline = Mock()
    pipeline.return_value = [{"label": "LABEL_0", "score": 0.0}]
    
    result = await topic_moderation("", pipeline)
    assert result["passed"] is False
    assert result["result"] == "no"

@pytest.mark.asyncio
async def test_topic_moderation_ambiguous():
    pipeline = Mock()
    pipeline.return_value = [{"label": "LABEL_1", "score": 0.55}]
    
    result = await topic_moderation(
        "How does weather affect farming?",
        pipeline
    )
    
    assert result["passed"] is True
    assert result["result"] == "yes"
    assert 0.5 < result.get("score", 0.0) < 0.7

@pytest.mark.asyncio
async def test_topic_moderation_error_handling():
    pipeline = Mock()
    pipeline.side_effect = Exception("Pipeline error")
    
    result = await topic_moderation("test query", pipeline)
    assert result["passed"] is False
    assert "error" in result
    assert result["reason"] == "error"