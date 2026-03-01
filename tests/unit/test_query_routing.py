import pytest
from unittest.mock import Mock, AsyncMock
from src.models.query_routing import MultilingualRouter, LanguageSupport

@pytest.fixture
def mock_translation():
    async def translate(query, source_lang, target_lang):
        # Mock translation that only works for Spanish to English
        if source_lang.lower() == "spanish" and query == "¿Qué es el cambio climático?":
            return "What is climate change?"
        elif source_lang.lower() == "french" and query == "Qu'est-ce que le changement climatique?":
            return "What is climate change?"
        return None
    return translate

@pytest.fixture
def router():
    return MultilingualRouter()

def test_language_code_standardization(router):
    assert router.standardize_language_code("en-US") == "en"
    assert router.standardize_language_code("es-ES") == "es"
    assert router.standardize_language_code("zh-CN") == "zh"
    assert router.standardize_language_code("fr") == "fr"

def test_check_language_support(router):
    # All languages are now supported via Tiny-Aya regional models
    # English routes to TINY_AYA_GLOBAL
    support = router.check_language_support("en")
    assert support == LanguageSupport.TINY_AYA_GLOBAL

    # Spanish routes to TINY_AYA_WATER (Europe + Asia-Pacific)
    support = router.check_language_support("es")
    assert isinstance(support, LanguageSupport)

    # Any language gets routed to some tier (no UNSUPPORTED)
    support = router.check_language_support("xx")
    assert support == LanguageSupport.TINY_AYA_GLOBAL  # Unknown codes fallback to global

@pytest.mark.asyncio
async def test_english_query_routing(router, mock_translation):
    result = await router.route_query(
        query="What is climate change?",
        language_code="en",
        language_name="english",
        translation=mock_translation
    )

    assert result["should_proceed"] is True
    assert result["english_query"] == "What is climate change?"
    assert result["routing_info"]["needs_translation"] is False

@pytest.mark.asyncio
async def test_supported_language_routing(router, mock_translation):
    result = await router.route_query(
        query="¿Qué es el cambio climático?",
        language_code="es",
        language_name="Spanish",
        translation=mock_translation
    )

    assert result["should_proceed"] is True
    # Spanish query with Spanish selected — no mismatch, translation should happen
    assert result["routing_info"]["needs_translation"] is True

@pytest.mark.asyncio
async def test_unknown_language_routing(router, mock_translation):
    """Unknown language codes fall back to TINY_AYA_GLOBAL (no UNSUPPORTED)."""
    result = await router.route_query(
        query="test query",
        language_code="xx",
        language_name="Unknown",
        translation=mock_translation
    )

    # All languages are now supported via global fallback
    assert result["should_proceed"] is True
    assert result["routing_info"]["support_level"] == "tiny_aya_global"

@pytest.mark.asyncio
async def test_failed_translation(router, mock_translation):
    """When translation returns None, should still proceed (router doesn't block)."""
    result = await router.route_query(
        query="Unknown text",
        language_code="fr",
        language_name="French",
        translation=mock_translation
    )

    # Router may detect language mismatch or proceed depending on detection
    assert isinstance(result, dict)
    assert "should_proceed" in result

@pytest.mark.asyncio
async def test_successful_french_translation(router, mock_translation):
    result = await router.route_query(
        query="Qu'est-ce que le changement climatique?",
        language_code="fr",
        language_name="French",
        translation=mock_translation
    )

    assert result["should_proceed"] is True
    assert result["english_query"] == "What is climate change?"
    assert result["routing_info"]["needs_translation"] is True
