import pytest

from src.models.query_routing import MultilingualRouter


@pytest.mark.asyncio
async def test_mismatch_english_selected_spanish_query_detected():
    """When English is selected but Spanish query is sent, router detects mismatch
    but still proceeds (mismatch is handled at pipeline level, not router level)."""
    router = MultilingualRouter()
    query = "¿Qué es el cambio climático?"
    result = await router.route_query(
        query=query,
        language_code="en",
        language_name="english",
        translation=None,
    )

    # Router now returns should_proceed=True with language_mismatch flag
    # (mismatch blocking is handled by the pipeline's query rewriter, not the router)
    assert result["should_proceed"] is True
    info = result["routing_info"]
    assert info.get("language_mismatch") is True
    assert "switch" in (info.get("message") or "").lower()
    # Query is passed through unchanged
    assert result["processed_query"] == query
    assert result["english_query"] == query


@pytest.mark.asyncio
async def test_mismatch_spanish_selected_english_query_detected():
    """When Spanish is selected but English query is sent, router detects mismatch."""
    router = MultilingualRouter()
    query = "What is climate change?"
    result = await router.route_query(
        query=query,
        language_code="es",
        language_name="spanish",
        translation=None,
    )

    assert result["should_proceed"] is True
    info = result["routing_info"]
    # English query detected while Spanish selected — mismatch flagged
    assert info.get("language_mismatch") is True
    assert result["processed_query"] == query
    assert result["english_query"] == query
