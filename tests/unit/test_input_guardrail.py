import pytest
from unittest.mock import Mock, patch
from src.models.input_guardrail import topic_moderation

@pytest.fixture
def mock_pipeline():
    class MockResult:
        def __init__(self, label, score):
            self.label = label
            self.score = score

    def mock_classify(text):
        # Return low score for non-climate content, high for climate
        if "climate" in text.lower() or "global warming" in text.lower():
            return [{"label": "LABEL_1", "score": 0.95}]
        return [{"label": "LABEL_0", "score": 0.15}]

    pipeline = Mock()
    pipeline.side_effect = mock_classify
    return pipeline

@pytest.mark.asyncio
async def test_topic_moderation_climate_related():
    with patch('ray.get') as mock_ray_get:
        pipeline = Mock()
        pipeline.return_value = [{"label": "LABEL_1", "score": 0.95}]
        mock_ray_get.return_value = "yes"  # Ray task should return "yes" directly
        
        result = await topic_moderation.remote(
            "What are the effects of climate change on polar ice caps?",
            pipeline
        )
        
        assert result == "yes"

@pytest.mark.asyncio
async def test_topic_moderation_non_climate():
    with patch('ray.get') as mock_ray_get:
        pipeline = Mock()
        pipeline.return_value = [{"label": "LABEL_0", "score": 0.15}]
        mock_ray_get.return_value = "no"  # Ray task should return "no" directly
        
        result = await topic_moderation.remote(
            "What is the best recipe for chocolate cake?",
            pipeline
        )
        
        assert result == "no"

@pytest.mark.asyncio
async def test_topic_moderation_ambiguous():
    with patch('ray.get') as mock_ray_get:
        pipeline = Mock()
        pipeline.return_value = [{"label": "LABEL_1", "score": 0.55}]
        mock_ray_get.return_value = "no"  # Low confidence should return "no"
        
        result = await topic_moderation.remote(
            "How does weather affect farming?",
            pipeline
        )
        
        assert result == "no"

@pytest.mark.asyncio
async def test_topic_moderation_error_handling():
    with patch('ray.get') as mock_ray_get:
        pipeline = Mock()
        pipeline.side_effect = Exception("Pipeline error")
        mock_ray_get.side_effect = Exception("Processing error")
        
        with pytest.raises(Exception):
            await topic_moderation.remote("test query", pipeline)

@pytest.mark.asyncio
async def test_topic_moderation_empty_query():
    with patch('ray.get') as mock_ray_get:
        pipeline = Mock()
        pipeline.return_value = [{"label": "LABEL_0", "score": 0.0}]
        mock_ray_get.return_value = "no"
        
        result = await topic_moderation.remote("", pipeline)
        assert result == "no"

@pytest.mark.asyncio
async def test_topic_moderation_low_confidence():
    with patch('ray.get') as mock_ray_get:
        pipeline = Mock()
        pipeline.return_value = [{"label": "LABEL_1", "score": 0.3}]
        mock_ray_get.return_value = "no"  # Low confidence should return "no"
        
        result = await topic_moderation.remote(
            "Tell me about environmental factors",
            pipeline
        )
        
        assert result == "no"