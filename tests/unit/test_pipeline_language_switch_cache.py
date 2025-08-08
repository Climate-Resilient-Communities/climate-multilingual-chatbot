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

    # Monkeypatch ClimateCache usage at both pipeline and generator sites
    monkeypatch.setattr("src.models.climate_pipeline.ClimateCache", FakeCache, raising=True)
    monkeypatch.setattr("src.models.gen_response_unified.ClimateCache", FakeCache, raising=True)

    # Stub get_documents to avoid Pinecone/embeddings
    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "c"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    # Stub query_rewriter to return combined classification + language + rewritten output
    async def fake_query_rewriter(conversation_history, user_query, nova_model):
        # If contains Spanish token, detect es; else en
        is_spanish = "¿" in user_query or " qué " in f" {user_query.lower()} " or " cambio clim" in user_query.lower()
        lang = "es" if is_spanish else "en"
        return (
            f"Reasoning: test\n"
            f"Language: {lang}\n"
            f"Classification: on-topic\n"
            f"Rewritten: what is climate change?"
        )
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    # Build a minimal pipeline instance without running heavy __init__
    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = UnifiedResponseGenerator()
    pipeline.redis_client = FakeCache()
    pipeline.nova_model = type("_Nova", (), {"translate": staticmethod(lambda text, s, t: text)})()  # identity translate by default
    pipeline.cohere_model = type("_Cohere", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"

    # Force translation for non-English by stubbing translate to return ES response
    async def fake_translate(text, src, tgt):
        return "ES_RESPONSE"
    # attach async method to nova_model
    setattr(pipeline.nova_model, "translate", fake_translate)

    # Stub generator to always return English response before translation
    async def fake_generate_response(query, documents, model_type, language_code="en", description=None, conversation_history=None):
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
    # No translation, response should be English stub
    assert res_en["response"] == "EN_RESPONSE"

    # 2) Switch to Spanish, ask Spanish version
    res_es = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=[],
    )
    assert res_es["success"] is True
    assert res_es["language_code"] == "es"
    # Should be translated to Spanish by pipeline step 8
    assert res_es["response"] == "ES_RESPONSE"


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
    monkeypatch.setattr("src.models.gen_response_unified.ClimateCache", FakeCache, raising=True)

    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "c"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    async def fake_query_rewriter(conversation_history, user_query, nova_model):
        # Detect language solely from current user query, not history
        is_spanish = "¿" in user_query or " cambio clim" in user_query.lower()
        lang = "es" if is_spanish else "en"
        return (
            f"Reasoning: test\n"
            f"Language: {lang}\n"
            f"Classification: on-topic\n"
            f"Rewritten: what is climate change?"
        )
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = UnifiedResponseGenerator()
    pipeline.redis_client = FakeCache()
    pipeline.nova_model = type("_Nova", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.cohere_model = type("_Cohere", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"

    async def fake_translate(text, src, tgt):
        return "ES_RESPONSE"
    setattr(pipeline.nova_model, "translate", fake_translate)

    async def fake_generate_response(query, documents, model_type, language_code="en", description=None, conversation_history=None):
        return "EN_RESPONSE", []
    monkeypatch.setattr(pipeline.response_generator, "generate_response", fake_generate_response, raising=True)

    # English conversation history; Spanish selection and Spanish query
    history = [{"query": "What is climate change?", "response": "It is ...", "language_code": "en"},
               {"query": "How does it affect Toronto?", "response": "...", "language_code": "en"}]

    res_es = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="spanish",
        conversation_history=history,
    )
    assert res_es["success"] is True
    assert res_es["language_code"] == "es"
    assert res_es["response"] == "ES_RESPONSE"


@pytest.mark.asyncio
async def test_english_selected_spanish_query_rejected(monkeypatch):
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
    monkeypatch.setattr("src.models.gen_response_unified.ClimateCache", FakeCache, raising=True)

    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "c"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    async def fake_query_rewriter(conversation_history, user_query, nova_model):
        # force Spanish detection for the user message
        return (
            "Reasoning: test\n"
            "Language: es\n"
            "Classification: on-topic\n"
            "Rewritten: what is climate change?"
        )
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = UnifiedResponseGenerator()
    pipeline.redis_client = FakeCache()
    pipeline.nova_model = type("_Nova", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.cohere_model = type("_Cohere", (), {"translate": staticmethod(lambda text, s, t: text)})()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"

    # English selected, Spanish query should be rejected with language switch prompt
    res = await pipeline.process_query(
        query="¿Qué es el cambio climático?",
        language_name="english",
        conversation_history=[{"query": "What is climate change?", "response": "...", "language_code": "en"}],
    )
    assert res["success"] is False
    assert "switch the language" in res["response"].lower()


