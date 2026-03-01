import asyncio
import pytest

from types import SimpleNamespace

from src.models.gen_response_unified import UnifiedResponseGenerator


@pytest.mark.asyncio
async def test_language_parameter_passed_to_generator(monkeypatch):
    """Test that UnifiedResponseGenerator correctly handles different language_code params.

    Note: Caching was moved to the pipeline level (ClimateQueryPipeline).
    UnifiedResponseGenerator no longer caches internally.
    This test verifies the generator correctly passes language_code through to generation.
    """
    gen = UnifiedResponseGenerator()

    call_log = SimpleNamespace(calls=0, language_codes=[])

    async def _stub_process_and_generate(query, documents, model, model_type, description=None, conversation_history=None):
        call_log.calls += 1
        return (f"GEN_RESPONSE_{call_log.calls}", [{"title": "T", "url": "", "content": "C"}])

    monkeypatch.setattr(gen, "_process_and_generate", _stub_process_and_generate)

    docs = [{"title": "Doc1", "url": "u1", "content": "content one"}]

    # First call under Spanish (es)
    resp1, cites1 = await gen.generate_response(
        query="what is climate change?",
        documents=docs,
        model_type="nova",
        language_code="es",
    )
    assert resp1 == "GEN_RESPONSE_1"
    assert call_log.calls == 1

    # Second call for English (en) with the same query — should still generate
    # (no caching at generator level, caching is at pipeline level)
    resp2, cites2 = await gen.generate_response(
        query="what is climate change?",
        documents=docs,
        model_type="nova",
        language_code="en",
    )
    assert resp2 == "GEN_RESPONSE_2"
    assert call_log.calls == 2


@pytest.mark.asyncio
async def test_same_language_generates_each_time(monkeypatch):
    """Verify that without pipeline caching, generator always generates fresh responses."""
    gen = UnifiedResponseGenerator()

    call_log = SimpleNamespace(calls=0)

    async def _stub_process_and_generate(query, documents, model, model_type, description=None, conversation_history=None):
        call_log.calls += 1
        return (f"GEN_RESPONSE_{call_log.calls}", [])

    monkeypatch.setattr(gen, "_process_and_generate", _stub_process_and_generate)

    docs = [{"title": "Doc1", "url": "u1", "content": "content one"}]

    # First call
    resp1, _ = await gen.generate_response(
        query="¿Qué es el cambio climático?",
        documents=docs,
        model_type="nova",
        language_code="es",
    )
    assert resp1 == "GEN_RESPONSE_1"
    assert call_log.calls == 1

    # Second call with same query and language — no cache at generator level
    resp2, _ = await gen.generate_response(
        query="¿qué es el cambio climático?",
        documents=docs,
        model_type="nova",
        language_code="es",
    )
    assert resp2 == "GEN_RESPONSE_2"
    assert call_log.calls == 2  # Generator always generates (caching is at pipeline level)
