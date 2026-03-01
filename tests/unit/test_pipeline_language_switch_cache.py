import pytest


@pytest.mark.asyncio
async def test_language_switch_english_then_spanish(monkeypatch):
    # Import targets lazily inside test to avoid heavy inits before monkeypatching
    from src.models.climate_pipeline import ClimateQueryPipeline
    from src.models.query_routing import MultilingualRouter
    from src.models.gen_response_unified import UnifiedResponseGenerator

    # Fake cache to avoid Redis
    class FakeCache:
        store = {}
        def __init__(self, *args, **kwargs):
            self.redis_client = True
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, value):
            self.store[key] = value
            return True

    # Monkeypatch ClimateCache at pipeline level only
    # (ClimateCache is no longer used in gen_response_unified)
    monkeypatch.setattr("src.models.climate_pipeline.ClimateCache", FakeCache, raising=True)

    # Stub get_documents to avoid Pinecone/embeddings
    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "c"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    # Stub query_rewriter to return JSON format (new pipeline expects JSON)
    import json
    async def fake_query_rewriter(conversation_history=None, user_query="", nova_model=None, selected_language_code="en"):
        # Detect language from query
        is_spanish = "¿" in user_query or " qué " in f" {user_query.lower()} " or " cambio clim" in user_query.lower()
        lang = "es" if is_spanish else "en"
        lang_match = lang == selected_language_code
        return json.dumps({
            "reasoning": "test",
            "language": lang,
            "classification": "on-topic",
            "language_match": lang_match,
            "rewrite_en": "what is climate change?"
        })
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    # Build a minimal pipeline instance without running heavy __init__
    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = UnifiedResponseGenerator()
    pipeline.cache = FakeCache()
    pipeline.nova_model = type("_Nova", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.cohere_model = type("_Cohere", (), {"translate": staticmethod(lambda text, s, t: text), "with_model": lambda self, model_id: self})()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"
    pipeline.redis_client = None

    # Force translation for non-English by stubbing translate to return ES response
    async def fake_translate(text, src, tgt):
        return "ES_RESPONSE"
    # attach async method to nova_model
    setattr(pipeline.nova_model, "translate", fake_translate)
    setattr(pipeline.cohere_model, "translate", fake_translate)

    # Stub generator to always return English response before translation
    async def fake_generate_response(query, documents, model_type, language_code="en", description=None, conversation_history=None, model=None):
        return "EN_RESPONSE", []
    monkeypatch.setattr(pipeline.response_generator, "generate_response", fake_generate_response, raising=True)

    # 1) English selected, English query
    res_en = await pipeline.process_query(
        query="What is climate change?",
        language_name="english",
        conversation_history=[],
    )
    assert res_en["success"] is True
    assert res_en["language_code"] == "en"

    # 2) Switch to Spanish, ask Spanish version
    FakeCache.store = {}  # Clear cache for clean test
    res_es = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=[],
    )
    assert res_es["success"] is True
    assert res_es["language_code"] == "es"


@pytest.mark.asyncio
async def test_spanish_with_english_history_returns_spanish(monkeypatch):
    from src.models.climate_pipeline import ClimateQueryPipeline
    from src.models.query_routing import MultilingualRouter
    from src.models.gen_response_unified import UnifiedResponseGenerator

    class FakeCache:
        store = {}
        def __init__(self, *args, **kwargs):
            self.redis_client = True
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, value):
            self.store[key] = value
            return True

    monkeypatch.setattr("src.models.climate_pipeline.ClimateCache", FakeCache, raising=True)

    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "c"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    import json
    async def fake_query_rewriter(conversation_history=None, user_query="", nova_model=None, selected_language_code="en"):
        is_spanish = "¿" in user_query or " cambio clim" in user_query.lower()
        lang = "es" if is_spanish else "en"
        lang_match = lang == selected_language_code
        return json.dumps({
            "reasoning": "test",
            "language": lang,
            "classification": "on-topic",
            "language_match": lang_match,
            "rewrite_en": "what is climate change?"
        })
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = UnifiedResponseGenerator()
    pipeline.cache = FakeCache()
    pipeline.nova_model = type("_Nova", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.cohere_model = type("_Cohere", (), {"translate": staticmethod(lambda text, s, t: text), "with_model": lambda self, model_id: self})()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"
    pipeline.redis_client = None

    async def fake_translate(text, src, tgt):
        return "ES_RESPONSE"
    setattr(pipeline.nova_model, "translate", fake_translate)
    setattr(pipeline.cohere_model, "translate", fake_translate)

    async def fake_generate_response(query, documents, model_type, language_code="en", description=None, conversation_history=None, model=None):
        return "EN_RESPONSE", []
    monkeypatch.setattr(pipeline.response_generator, "generate_response", fake_generate_response, raising=True)

    # English conversation history; Spanish selection and Spanish query
    history = [{"query": "What is climate change?", "response": "It is ...", "language_code": "en"},
               {"query": "How does it affect Toronto?", "response": "...", "language_code": "en"}]

    FakeCache.store = {}
    res_es = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=history,
    )
    assert res_es["success"] is True
    assert res_es["language_code"] == "es"


@pytest.mark.asyncio
async def test_english_selected_spanish_query_returns_mismatch_canned(monkeypatch):
    """When English is selected but a Spanish query is sent, pipeline returns a
    canned language-mismatch response (success=True with switch prompt)."""
    from src.models.climate_pipeline import ClimateQueryPipeline
    from src.models.query_routing import MultilingualRouter
    from src.models.gen_response_unified import UnifiedResponseGenerator

    class FakeCache:
        store = {}
        def __init__(self, *args, **kwargs):
            self.redis_client = True
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, value):
            self.store[key] = value
            return True

    monkeypatch.setattr("src.models.climate_pipeline.ClimateCache", FakeCache, raising=True)

    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "c"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    import json
    async def fake_query_rewriter(conversation_history=None, user_query="", nova_model=None, selected_language_code="en"):
        # Force Spanish detection for the user message
        return json.dumps({
            "reasoning": "test",
            "language": "es",
            "classification": "on-topic",
            "language_match": False,
            "rewrite_en": "what is climate change?"
        })
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = UnifiedResponseGenerator()
    pipeline.cache = FakeCache()
    pipeline.nova_model = type("_Nova", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.cohere_model = type("_Cohere", (), {"translate": staticmethod(lambda text, s, t: text), "with_model": lambda self, model_id: self})()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"
    pipeline.redis_client = None

    # English selected, Spanish query → canned language mismatch response
    FakeCache.store = {}
    res = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="english",
        conversation_history=[],
    )
    # Pipeline returns success=True with a canned mismatch response
    assert res["success"] is True
    # Canned text asks user to choose the correct language
    assert "language" in res["response"].lower()
    assert res.get("retrieval_source") == "canned" or res.get("fallback_reason") == "language_mismatch_canned"
