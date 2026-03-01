"""Test that all critical modules can be imported successfully."""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))


def test_nova_flow_import():
    from src.models.nova_flow import BedrockModel
    assert BedrockModel is not None


def test_cohere_flow_import():
    from src.models.cohere_flow import CohereModel, HFEmbedder
    assert CohereModel is not None
    assert HFEmbedder is not None


def test_input_guardrail_import():
    from src.models.input_guardrail import topic_moderation
    assert topic_moderation is not None


def test_retrieval_import():
    from src.models.retrieval import get_documents, get_hybrid_results
    assert get_documents is not None
    assert get_hybrid_results is not None


def test_query_routing_import():
    from src.models.query_routing import MultilingualRouter, LanguageSupport
    assert MultilingualRouter is not None
    assert LanguageSupport is not None


def test_hallucination_guard_import():
    from src.models.hallucination_guard import check_hallucination
    assert check_hallucination is not None


def test_redis_cache_import():
    from src.models.redis_cache import ClimateCache
    assert ClimateCache is not None


def test_gen_response_nova_import():
    from src.models.gen_response_nova import generate_chat_response, doc_preprocessing
    assert generate_chat_response is not None
    assert doc_preprocessing is not None


def test_gen_response_unified_import():
    from src.models.gen_response_unified import UnifiedResponseGenerator
    assert UnifiedResponseGenerator is not None


def test_tiny_aya_language_sets_import():
    from src.models.cohere_flow import FIRE_LANGUAGES, EARTH_LANGUAGES, WATER_LANGUAGES
    assert len(FIRE_LANGUAGES) > 0
    assert len(EARTH_LANGUAGES) > 0
    assert len(WATER_LANGUAGES) > 0


def test_resolve_tiny_aya_model_import():
    from src.models.cohere_flow import resolve_tiny_aya_model
    assert resolve_tiny_aya_model is not None
