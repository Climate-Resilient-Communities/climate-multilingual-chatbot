import pytest

from src.models.query_routing import MultilingualRouter


@pytest.mark.asyncio
async def test_mismatch_english_selected_spanish_query_prompts_language_switch():
    router = MultilingualRouter()
    query = "¿Qué es el cambio climático?"
    result = await router.route_query(
        query=query,
        language_code="en",
        language_name="english",
        translation=None,
    )

    assert result["should_proceed"] is False
    info = result["routing_info"]
    assert info.get("language_mismatch") is True
    assert "switch" in (info.get("message") or "").lower()
    # Did not transform the query
    assert result["processed_query"] == query
    assert result["english_query"] == query


@pytest.mark.asyncio
async def test_mismatch_spanish_selected_english_query_routes_without_translation():
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
    assert info.get("language_mismatch") is True
    # It should proceed with Nova in English without translating
    assert info.get("model_type") == "nova"
    assert info.get("needs_translation") is False
    assert result["processed_query"] == query
    assert result["english_query"] == query

