"""Tests for the agentic clarify-or-answer step on location-dependent queries."""

import json
import pytest

from src.models.query_rewriter import needs_location_fallback


class TestNeedsLocationFallback:
    @pytest.mark.parametrize("text", [
        "local flooding",
        "flooding near me",
        "cooling centres in my area",
        "what's the flood risk in my neighbourhood?",
        "air quality around here",
    ])
    def test_local_queries_without_place_need_location(self, text):
        assert needs_location_fallback(text)

    @pytest.mark.parametrize("text", [
        "local flooding in Toronto",
        "flooding near me in Scarborough",
        "what is climate change?",
        "how do heat waves form?",
        "flooding in Thorncliffe Park",
    ])
    def test_place_or_general_queries_do_not(self, text):
        assert not needs_location_fallback(text)

    def test_location_in_history_counts(self):
        assert not needs_location_fallback(
            "local flooding", history=["Q: what about Scarborough?", "A: Scarborough faces..."]
        )


@pytest.mark.asyncio
async def test_pipeline_asks_for_location_then_answers(monkeypatch):
    """'local flooding' with no location → clarifying question; once history
    contains the community, the pipeline answers instead of re-asking."""
    from src.models.climate_pipeline import ClimateQueryPipeline
    from src.models.query_routing import MultilingualRouter

    class FakeCache:
        def __init__(self, *a, **k):
            self.redis_client = True
        async def get(self, key):
            return None
        async def set(self, key, value, *a, **k):
            return True
        async def get_list(self, key, start, end):
            return []
        async def add_to_list(self, key, value):
            return True

    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Thorncliffe Park Flood Vulnerability", "url": "u", "content": "flood info"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    async def fake_check_hallucination(**kwargs):
        return 0.9
    monkeypatch.setattr("src.models.climate_pipeline.check_hallucination", fake_check_hallucination, raising=True)

    rewriter_outputs = {}

    async def fake_query_rewriter(conversation_history=None, user_query="", nova_model=None, selected_language_code="en"):
        return json.dumps(rewriter_outputs)
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    class FakeGenerator:
        async def generate_response(self, **kwargs):
            return "Flooding guidance for Thorncliffe Park with preparation steps.", []

    class _Model:
        async def translate(self, text, s=None, t=None):
            return text
        def with_model(self, model_id):
            return self

    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = FakeGenerator()
    pipeline.cache = FakeCache()
    pipeline.nova_model = _Model()
    pipeline.cohere_model = _Model()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"
    pipeline.redis_client = None

    base = {
        "reason": "t", "language": "en", "expected_language": "en", "language_match": True,
        "classification": "on-topic", "requested_language": None,
        "canned": {"enabled": False, "type": None, "text": None},
        "ask_how_to_use": False, "how_it_works": None, "error": None,
    }

    # Turn 1: local question, no location → clarify
    rewriter_outputs.clear()
    rewriter_outputs.update({**base, "rewrite_en": "What should I know about flooding in my area?",
                             "location": None, "needs_location": True})
    res = await pipeline.process_query(query="local flooding", language_name="english", conversation_history=[])
    assert res["success"] is True
    assert res["retrieval_source"] == "clarify"
    assert "which city or neighbourhood" in res["response"].lower()

    # Turn 2: location now known → real answer, no clarify
    rewriter_outputs.clear()
    rewriter_outputs.update({**base, "rewrite_en": "What should I know about flooding in Thorncliffe Park?",
                             "location": "Thorncliffe Park", "needs_location": False})
    res = await pipeline.process_query(
        query="I'm in Thorncliffe Park", language_name="english",
        conversation_history=[{"role": "user", "content": "local flooding"},
                              {"role": "assistant", "content": "Which city or neighbourhood are you in?"}],
    )
    assert res["success"] is True
    assert res["retrieval_source"] != "clarify"
    assert "Thorncliffe" in res["response"]
