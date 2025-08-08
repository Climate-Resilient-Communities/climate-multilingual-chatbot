import asyncio
import pytest

from types import SimpleNamespace

from src.models.gen_response_unified import UnifiedResponseGenerator, ClimateCache as RealClimateCache


class FakeCache:
    store = {}

    def __init__(self, *args, **kwargs):
        # simulate having a client
        self.redis_client = True

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value):
        self.store[key] = value
        return True


@pytest.mark.asyncio
async def test_language_scoped_cache_isolation(monkeypatch):
    # Replace ClimateCache with FakeCache
    monkeypatch.setattr(
        "src.models.gen_response_unified.ClimateCache",
        FakeCache,
        raising=True,
    )

    gen = UnifiedResponseGenerator()

    # Stub document processing/generation to avoid external calls
    call_log = SimpleNamespace(calls=0)

    async def _stub_process_and_generate(query, documents, model, model_type, description=None, conversation_history=None):
        call_log.calls += 1
        # Return distinct payloads per invocation
        return (f"GEN_RESPONSE_{call_log.calls}", [{"title": "T", "url": "", "content": "C"}])

    monkeypatch.setattr(gen, "_process_and_generate", _stub_process_and_generate)

    docs = [{"title": "Doc1", "url": "u1", "content": "content one"}]

    # First call under Spanish (es)
    resp1, cites1 = await gen.generate_response(
        query="what is climate change?",  # processed English query from a Spanish input
        documents=docs,
        model_type="nova",
        language_code="es",
    )
    assert resp1 == "GEN_RESPONSE_1"
    assert call_log.calls == 1

    # Second call for English (en) with the same query and docs should NOT hit the es cache
    resp2, cites2 = await gen.generate_response(
        query="what is climate change?",
        documents=docs,
        model_type="nova",
        language_code="en",
    )
    assert resp2 == "GEN_RESPONSE_2"
    assert call_log.calls == 2

    # Ensure keys are stored under separate language namespaces
    keys = list(FakeCache.store.keys())
    assert any(k.startswith("es:") for k in keys)
    assert any(k.startswith("en:") for k in keys)


@pytest.mark.asyncio
async def test_cache_hit_within_same_language(monkeypatch):
    # Fresh fake cache
    FakeCache.store = {}
    monkeypatch.setattr(
        "src.models.gen_response_unified.ClimateCache",
        FakeCache,
        raising=True,
    )

    gen = UnifiedResponseGenerator()

    call_log = SimpleNamespace(calls=0)

    async def _stub_process_and_generate(query, documents, model, model_type, description=None, conversation_history=None):
        call_log.calls += 1
        return (f"GEN_RESPONSE_{call_log.calls}", [])

    monkeypatch.setattr(gen, "_process_and_generate", _stub_process_and_generate)

    docs = [{"title": "Doc1", "url": "u1", "content": "content one"}]

    # First call creates cache for 'es'
    resp1, _ = await gen.generate_response(
        query="¿Qué es el cambio climático?",
        documents=docs,
        model_type="nova",
        language_code="es",
    )
    assert resp1 == "GEN_RESPONSE_1"
    assert call_log.calls == 1

    # Second call with same language and normalized query should cache-hit
    resp2, _ = await gen.generate_response(
        query="¿qué es el cambio climático?",  # case difference
        documents=docs,
        model_type="nova",
        language_code="es",
    )
    assert resp2 == "GEN_RESPONSE_1"  # should return cached response
    assert call_log.calls == 1  # no new generation


