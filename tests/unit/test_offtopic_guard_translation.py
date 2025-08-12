import sys
from types import ModuleType
import pytest

# Stub heavy optional deps used by pipeline imports
if 'langsmith' not in sys.modules:
    sys.modules['langsmith'] = ModuleType('langsmith')
    sys.modules['langsmith'].traceable = lambda **kwargs: (lambda f: f)
if 'aioboto3' not in sys.modules:
    ab3 = ModuleType('aioboto3')
    class _S:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
    ab3.Session = lambda *a, **k: _S()
    sys.modules['aioboto3'] = ab3
if 'boto3' not in sys.modules:
    b3 = ModuleType('boto3')
    class _S:
        def client(self, *a, **k):
            return type('C', (), {})()
    b3.Session = lambda *a, **k: _S()
    b3.__spec__ = ModuleType('spec')  # to satisfy accelerate check
    sys.modules['boto3'] = b3
if 'botocore' not in sys.modules:
    sys.modules['botocore'] = ModuleType('botocore')
    sys.modules['botocore.config'] = ModuleType('botocore.config')
    sys.modules['botocore.config'].Config = lambda **kwargs: object()
if 'pinecone' not in sys.modules:
    pc = ModuleType('pinecone')
    class _PC:
        def __init__(self, *a, **k):
            pass
        def Index(self, *a, **k):
            class _I:
                def query(self, *a, **k):
                    return {"matches": []}
            return _I()
    pc.Pinecone = _PC
    sys.modules['pinecone'] = pc
if 'cohere' not in sys.modules:
    ch = ModuleType('cohere')
    class _Client:
        def __init__(self, *a, **k): pass
        def rerank(self, *a, **k):
            class _R: results = []
            return _R()
    ch.Client = _Client
    sys.modules['cohere'] = ch


@pytest.mark.asyncio
async def test_offtopic_guard_uses_detected_language(monkeypatch):
    from src.models.climate_pipeline import ClimateQueryPipeline
    from src.models.query_routing import MultilingualRouter
    from src.models.gen_response_unified import UnifiedResponseGenerator

    # Minimal cache stub to avoid Redis
    class FakeCache:
        def __init__(self, *args, **kwargs):
            self.redis_client = True
        async def get(self, key):
            return None
        async def set(self, key, value):
            return True

    # Patch cache usage
    monkeypatch.setattr("src.models.climate_pipeline.ClimateCache", FakeCache, raising=True)
    monkeypatch.setattr("src.models.gen_response_unified.ClimateCache", FakeCache, raising=True)

    # Avoid Pinecone and embeddings
    async def fake_get_documents(query, index, embed_model, cohere_client):
        return []
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    # Return strict JSON from query_rewriter: detected zh, classification off-topic
    import json
    async def fake_query_rewriter(conversation_history, user_query, nova_model, selected_language_code="en"):
        payload = {
            "reason": "test",
            "language": "zh",
            "expected_language": selected_language_code,
            "language_match": True,
            "classification": "off-topic",
            "rewrite_en": None,
            "canned": {"enabled": False, "type": None, "text": None},
            "ask_how_to_use": False,
            "how_it_works": None,
            "error": None,
        }
        return json.dumps(payload)
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    # Build a minimal pipeline without heavy __init__
    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    # Avoid Bedrock init inside UnifiedResponseGenerator by stubbing constructor
    class _UR( UnifiedResponseGenerator.__class__ ):
        pass
    # Build a lightweight instance by bypassing __init__
    pipeline.response_generator = object.__new__(UnifiedResponseGenerator)
    pipeline.redis_client = FakeCache()
    async def _cohere_translate(t, s, d):
        return "ENQ"
    pipeline.cohere_model = type("_Cohere", (), {})()
    setattr(pipeline.cohere_model, "translate", _cohere_translate)
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"

    # Capture translate inputs
    translate_calls = {}
    async def fake_translate(text, src, tgt):
        translate_calls["src"] = src
        translate_calls["tgt"] = tgt
        # Return sentinel to ensure translation occurred
        return "ZH_TRANSLATED_GUARD"
    # Attach translation function
    pipeline.nova_model = type("_Nova", (), {})()
    setattr(pipeline.nova_model, "translate", fake_translate)

    # Selected language Chinese; detected will also be zh → guard path translates to Chinese
    res = await pipeline.process_query(
        query="多伦多为什么天气变化这么大?",
        language_name="chinese",
        conversation_history=[],
    )

    assert res["success"] is False
    # Ensure we translated into detected language (zh → Chinese)
    assert translate_calls.get("src") == "english"
    assert translate_calls.get("tgt").lower() in {"zh", "chinese"}
    assert res["response"] == "ZH_TRANSLATED_GUARD"


