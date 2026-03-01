"""
Test that off-topic guard translates canned response to the detected query language.

The pipeline now:
- Uses ClimateCache from redis_cache (not gen_response_unified)
- Returns success=True with canned responses for off-topic queries
- Uses cohere_model.translate for off-topic canned response translation
"""

import json
import pytest
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_offtopic_guard_uses_detected_language(monkeypatch):
    from src.models.climate_pipeline import ClimateQueryPipeline

    # Fake in-memory cache
    class FakeCache:
        def __init__(self, *args, **kwargs):
            self.redis_client = True
        async def get(self, key):
            return None
        async def set(self, key, value):
            return True

    # Patch cache at pipeline level only (ClimateCache is in redis_cache, not gen_response_unified)
    monkeypatch.setattr("src.models.climate_pipeline.ClimateCache", FakeCache, raising=True)

    # Avoid retrieval
    async def fake_get_documents(query, index, embed_model, cohere_client):
        return []
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    # Return strict JSON from query_rewriter: detected zh, classification off-topic
    async def fake_query_rewriter(conversation_history=None, user_query="", nova_model=None, selected_language_code="en"):
        payload = {
            "reason": "test",
            "language": "zh",
            "expected_language": selected_language_code,
            "language_match": selected_language_code == "zh",
            "classification": "off-topic",
            "rewrite_en": None,
            "canned": {"enabled": False, "type": None, "text": None},
            "ask_how_to_use": False,
            "how_it_works": None,
            "error": None,
        }
        return json.dumps(payload)
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    # Stub router
    async def fake_route_query(query, language_code, language_name, translation):
        return {
            "should_proceed": True,
            "routing_info": {
                "support_level": "tiny_aya_water",
                "model_type": "cohere",
                "model_name": "Tiny-Aya Water",
                "model_id": "tiny-aya-water",
                "needs_translation": False,
                "language_mismatch": False,
            },
            "processed_query": query,
            "english_query": "Why does the weather change so much in Toronto?",
        }

    # Build pipeline instance without heavy __init__
    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = SimpleNamespace(route_query=fake_route_query)
    pipeline.cache = FakeCache()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"
    pipeline.redis_client = None

    # Capture translate calls on cohere_model (pipeline uses cohere_model.translate for off-topic)
    translate_calls = {}
    async def fake_translate(text, src, tgt):
        translate_calls["text"] = text
        translate_calls["src"] = src
        translate_calls["tgt"] = tgt
        return "ZH_TRANSLATED_GUARD"

    pipeline.nova_model = SimpleNamespace(translate=fake_translate, content_generation=lambda *a, **k: None)
    pipeline.cohere_model = SimpleNamespace(
        translate=fake_translate,
        with_model=lambda model_id: pipeline.cohere_model,
    )

    # Selected language Chinese; query also Chinese
    res = await pipeline.process_query(
        query="多伦多为什么天气变化这么大?",
        language_name="chinese",
        conversation_history=[],
    )

    # Off-topic returns success=True with a canned response (translated to detected language)
    assert res["success"] is True
    assert res["retrieval_source"] == "canned"
    # The off-topic branch translates the canned English message to Chinese
    assert translate_calls.get("src") == "english"
    assert translate_calls.get("tgt").lower() in {"zh", "chinese"}
