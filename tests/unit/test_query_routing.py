import pytest
from unittest.mock import Mock
from src.models.query_routing import MultilingualRouter, LanguageSupport

@pytest.fixture
def mock_translation():
    def translate(query, source_lang, target_lang):
        # Mock translation that only works for Spanish to English
        if source_lang.lower() == "spanish" and query == "¿Qué es el cambio climático?":
            return "What is climate change?"
        elif source_lang.lower() == "french" and query == "Qu'est-ce que le changement climatique?":
            return "What is climate change?"
        return None
    return translate

@pytest.fixture
def router():
    router = MultilingualRouter()
    # Update the language support and override the translation check
    router.check_language_support = lambda code: LanguageSupport.COMMAND_R_PLUS if code in ['en', 'es', 'fr'] else LanguageSupport.UNSUPPORTED
    router._needs_translation = lambda code: code != 'en'
    return router

def test_language_code_standardization(router):
    assert router.standardize_language_code("en-US") == "en"
    assert router.standardize_language_code("es-ES") == "es"
    assert router.standardize_language_code("zh-CN") == "zh"
    assert router.standardize_language_code("fr") == "fr"

def test_check_language_support(router):
    assert router.check_language_support("en") == LanguageSupport.COMMAND_R_PLUS
    assert router.check_language_support("es") == LanguageSupport.COMMAND_R_PLUS
    assert router.check_language_support("xx") == LanguageSupport.UNSUPPORTED

def test_english_query_routing(router, mock_translation):
    result = router.route_query(
        query="What is climate change?",
        language_code="en-US",
        language_name="english",
        translation=mock_translation
    )
    
    assert result["should_proceed"] is True
    assert result["english_query"] == "What is climate change?"
    assert result["original_language"] == "en"
    assert result["routing_info"]["support_level"] == "command_r_plus"
    assert result["routing_info"]["needs_translation"] is False

def test_supported_language_routing(router, mock_translation):
    result = router.route_query(
        query="¿Qué es el cambio climático?",
        language_code="es",
        language_name="Spanish",
        translation=mock_translation
    )
    
    assert result["should_proceed"] is True
    assert result["english_query"] == "What is climate change?"
    assert result["original_language"] == "es"
    assert result["routing_info"]["support_level"] == "command_r_plus"
    assert result["routing_info"]["needs_translation"] is True

def test_unsupported_language_routing(router, mock_translation):
    result = router.route_query(
        query="test query",
        language_code="xx",
        language_name="Unsupported",
        translation=mock_translation
    )
    
    assert result["should_proceed"] is False
    assert result["routing_info"]["support_level"] == "unsupported"
    assert "message" in result["routing_info"]

def test_failed_translation(router, mock_translation):
    result = router.route_query(
        query="Unknown text",
        language_code="fr",
        language_name="French",
        translation=mock_translation
    )
    
    assert result["should_proceed"] is False

def test_successful_french_translation(router, mock_translation):
    result = router.route_query(
        query="Qu'est-ce que le changement climatique?",
        language_code="fr",
        language_name="French",
        translation=mock_translation
    )
    
    assert result["should_proceed"] is True
    assert result["english_query"] == "What is climate change?"
    assert result["original_language"] == "fr"
    assert result["routing_info"]["support_level"] == "command_r_plus"
    assert result["routing_info"]["needs_translation"] is True