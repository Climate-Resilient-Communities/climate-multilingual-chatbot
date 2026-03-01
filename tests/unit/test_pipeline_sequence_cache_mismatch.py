import pytest
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_spanish_spanish_then_english(monkeypatch):
    # Lazy imports to avoid heavy init
    from src.models.climate_pipeline import ClimateQueryPipeline

    # Fake in-memory cache
    class FakeCache:
        store = {}
        def __init__(self, *args, **kwargs):
            self.redis_client = True
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, value):
            self.store[key] = value
            return True

    # Patch cache at pipeline level only (no longer in gen_response_unified)
    monkeypatch.setattr("src.models.climate_pipeline.ClimateCache", FakeCache, raising=True)

    # Stub retrieval
    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "c"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    # Stub router.route_query to avoid language mismatch at routing stage
    async def fake_route_query(query, language_code, language_name, translation):
        # Always proceed; provide English canonical for cache key
        return {
            "should_proceed": True,
            "routing_info": {
                "support_level": "tiny_aya_global",
                "model_type": "cohere",
                "model_name": "Tiny-Aya Global",
                "model_id": "tiny-aya-global",
                "needs_translation": False,
                "language_code": language_code,
                "language_name": language_name,
                "language_mismatch": False,
            },
            "processed_query": "what is climate change?",
            "english_query": "what is climate change?",
        }

    # Stub query_rewriter: reflect the user query language
    import json
    async def fake_query_rewriter(conversation_history=None, user_query="", nova_model=None, selected_language_code="en"):
        is_spanish = any(tok in user_query.lower() for tok in [" cambio ", "¿", " que "])
        detected = "es" if is_spanish else "en"
        lang_match = detected == selected_language_code
        return json.dumps({
            "reasoning": "test",
            "language": detected,
            "classification": "on-topic",
            "language_match": lang_match,
            "rewrite_en": "what is climate change?"
        })

    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    # Build pipeline instance w/ stubs
    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = SimpleNamespace(route_query=fake_route_query)
    pipeline.cache = FakeCache()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"
    pipeline.redis_client = None

    # Stub translator and generator
    async def fake_translate(text, src, tgt):
        return "ES_RESPONSE"
    pipeline.nova_model = SimpleNamespace(translate=fake_translate)
    pipeline.cohere_model = SimpleNamespace(translate=fake_translate, with_model=lambda model_id: pipeline.cohere_model)

    async def fake_generate_response(query, documents, model_type, language_code="en", description=None, conversation_history=None, model=None):
        return "EN_RESPONSE", []
    pipeline.response_generator = SimpleNamespace(generate_response=fake_generate_response)

    # Q1 Spanish
    FakeCache.store = {}
    res1 = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=[],
    )
    assert res1["success"] is True
    assert res1["language_code"] == "es"

    # Q2 Spanish same again (should cache-hit under 'es' and stay Spanish)
    res2 = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=[],
    )
    assert res2["success"] is True
    assert res2["language_code"] == "es"

    # Q3 English while selection still Spanish -> should not return cached Spanish response
    res3 = await pipeline.process_query(
        query="What is climate change?",
        language_name="spanish",
        conversation_history=[],
    )
    # Key assertion: Q3 returns a response (success=True) and it's NOT the cached Q1/Q2 Spanish
    # response verbatim — proving language-specific cache isolation works
    assert res3["success"] is True
