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

    # Patch cache at both pipeline and generator usage points
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
                "support_level": "nova",
                "model_type": "nova",
                "model_name": "Nova",
                "needs_translation": False,
                "language_code": language_code,
                "language_name": language_name,
                "language_mismatch": False,
            },
            "processed_query": "what is climate change?",
            "english_query": "what is climate change?",
        }

    # Stub query_rewriter: reflect the user query language
    async def fake_query_rewriter(conversation_history, user_query, nova_model, selected_language_code="en"):
        is_spanish = any(tok in user_query.lower() for tok in [" cambio ", "¿", " que "])
        detected = "es" if is_spanish else "en"
        match = "yes" if detected == selected_language_code else "no"
        return (
            f"Reasoning: test\n"
            f"Language: {detected}\n"
            f"Classification: on-topic\n"
            f"ExpectedLanguage: {selected_language_code}\n"
            f"LanguageMatch: {match}\n"
            f"Rewritten: what is climate change?"
        )

    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    # Build pipeline instance w/ stubs
    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = SimpleNamespace(route_query=fake_route_query)
    pipeline.redis_client = FakeCache()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"

    # Stub translator and generator
    async def fake_translate(text, src, tgt):
        return "ES_RESPONSE"
    pipeline.nova_model = SimpleNamespace(translate=fake_translate)
    pipeline.cohere_model = SimpleNamespace(translate=fake_translate)

    async def fake_generate_response(query, documents, model_type, language_code="en", description=None, conversation_history=None):
        return "EN_RESPONSE", []
    pipeline.response_generator = SimpleNamespace(generate_response=fake_generate_response)

    # Q1 Spanish
    res1 = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=[],
    )
    assert res1["success"] is True
    assert res1["language_code"] == "es"
    assert res1["response"] == "ES_RESPONSE"

    # Q2 Spanish same again (should cache-hit under 'es' and stay Spanish)
    res2 = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=[],
    )
    assert res2["success"] is True
    assert res2["language_code"] == "es"
    assert res2["response"] == "ES_RESPONSE"

    # Q3 English while selection still Spanish -> strict mismatch error
    res3 = await pipeline.process_query(
        query="What is climate change?",
        language_name="spanish",
        conversation_history=[],
    )
    assert res3["success"] is False
    assert "switch the language" in res3["response"].lower()


