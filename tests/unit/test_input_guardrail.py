import pytest
from src.models.input_guardrail import topic_moderation


@pytest.mark.asyncio
async def test_topic_moderation_climate_related():
    result = await topic_moderation(
        "What are the effects of climate change on polar ice caps?"
    )

    assert result["passed"] is True
    assert result["reason"] == "climate_keywords"


@pytest.mark.asyncio
async def test_topic_moderation_non_climate():
    result = await topic_moderation(
        "What is the best recipe for chocolate cake?"
    )

    assert result["passed"] is False


@pytest.mark.asyncio
async def test_topic_moderation_off_topic_shopping():
    result = await topic_moderation(
        "Where can I buy new shoes?"
    )

    assert result["passed"] is False
    assert result["reason"] == "explicitly_off_topic"


@pytest.mark.asyncio
async def test_topic_moderation_empty_query():
    result = await topic_moderation("")
    assert result["passed"] is False


@pytest.mark.asyncio
async def test_topic_moderation_climate_keywords():
    result = await topic_moderation(
        "How does weather affect farming?"
    )

    assert result["passed"] is True
    assert result["reason"] == "climate_keywords"


@pytest.mark.asyncio
async def test_topic_moderation_error_handling():
    # topic_moderation should not crash even with unusual input
    result = await topic_moderation("test query")
    assert "passed" in result
    assert "reason" in result
