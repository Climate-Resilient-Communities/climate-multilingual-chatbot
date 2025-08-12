import asyncio
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

# Lightweight stubs for optional heavy deps imported by nova_flow
if 'aioboto3' not in sys.modules:
    sys.modules['aioboto3'] = ModuleType('aioboto3')
if 'botocore' not in sys.modules:
    sys.modules['botocore'] = ModuleType('botocore')
    sys.modules['botocore.config'] = ModuleType('botocore.config')
    sys.modules['botocore.config'].Config = lambda **kwargs: object()

from src.models.query_rewriter import query_rewriter


class DummyNovaDynamic:
    """Configurable dummy nova model for query_rewriter tests."""

    def __init__(self, *, raw_json: str = None, translate_text: str | None = None,
                 raise_timeout: bool = False, raise_error: bool = False):
        self._raw_json = raw_json
        self._translate_text = translate_text
        self._raise_timeout = raise_timeout
        self._raise_error = raise_error

    async def content_generation(self, prompt: str, system_message: str = None):
        if self._raise_timeout:
            raise asyncio.TimeoutError()
        if self._raise_error:
            raise RuntimeError("boom")
        return self._raw_json or "{}"

    async def translate(self, text: str, source_lang: str = None, target_lang: str = None):
        return self._translate_text if self._translate_text is not None else text


@pytest.mark.asyncio
async def test_cn_weather_keyword_triggers_on_topic_without_rewrite():
    # Model says off-topic with no rewrite, but original has 天气 (weather)
    raw = json.dumps({
        "reason": "test", "language": "zh", "expected_language": "zh",
        "language_match": True, "classification": "off-topic",
        "rewrite_en": None, "ask_how_to_use": False, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw)
    out = await query_rewriter(["user: prev"], "多伦多为什么天气变化这么大", nova, selected_language_code="zh")
    data = json.loads(out)
    assert data["classification"] == "on-topic"


@pytest.mark.asyncio
async def test_ar_weather_keyword_triggers_on_topic():
    raw = json.dumps({
        "reason": "test", "language": "ar", "expected_language": "ar",
        "language_match": True, "classification": "off-topic",
        "rewrite_en": None, "ask_how_to_use": False, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw)
    out = await query_rewriter([], "لماذا الطقس يتغير كثيرا في تورونتو؟", nova, selected_language_code="ar")
    data = json.loads(out)
    assert data["classification"] == "on-topic"


@pytest.mark.asyncio
async def test_offtopic_but_rewrite_en_contains_climate_terms():
    raw = json.dumps({
        "reason": "test", "language": "es", "expected_language": "es",
        "language_match": True, "classification": "off-topic",
        "rewrite_en": "What are the impacts of climate change?",
        "ask_how_to_use": False, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw)
    out = await query_rewriter([], "¿Por qué cambia tanto el clima?", nova, selected_language_code="es")
    data = json.loads(out)
    assert data["classification"] == "on-topic"


@pytest.mark.asyncio
async def test_translation_fallback_sets_on_topic_and_rewrite_en():
    # Model says off-topic with no rewrite; translation returns heat wave
    raw = json.dumps({
        "reason": "test", "language": "zh", "expected_language": "zh",
        "language_match": True, "classification": "off-topic",
        "rewrite_en": None, "ask_how_to_use": False, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw, translate_text="Why is there a heat wave in Toronto?")
    # Avoid using 天气 so the early user_query keyword guard doesn't flip it;
    # this forces the translation-fallback path to populate rewrite_en.
    out = await query_rewriter([], "多伦多最近为何这么闷热？", nova, selected_language_code="zh")
    data = json.loads(out)
    assert data["classification"] == "on-topic"
    assert isinstance(data.get("rewrite_en"), str) and len(data["rewrite_en"]) > 0


@pytest.mark.asyncio
async def test_on_topic_passthrough_with_rewrite():
    raw = json.dumps({
        "reason": "ok", "language": "en", "expected_language": "en",
        "language_match": True, "classification": "on-topic",
        "rewrite_en": "What are the causes of global warming?",
        "ask_how_to_use": False, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw)
    out = await query_rewriter([], "Causes of global warming?", nova, selected_language_code="en")
    data = json.loads(out)
    assert data["classification"] == "on-topic"
    assert data["rewrite_en"].startswith("What are the causes")


@pytest.mark.asyncio
async def test_greeting_classification_has_no_rewrite():
    raw = json.dumps({
        "reason": "ok", "language": "en", "expected_language": "en",
        "language_match": True, "classification": "greeting",
        "rewrite_en": None, "ask_how_to_use": False, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw)
    out = await query_rewriter([], "hello", nova, selected_language_code="en")
    data = json.loads(out)
    assert data["classification"] == "greeting"
    assert data["rewrite_en"] is None


@pytest.mark.asyncio
async def test_instruction_sets_help_text():
    raw = json.dumps({
        "reason": "ok", "language": "en", "expected_language": "en",
        "language_match": True, "classification": "instruction",
        "rewrite_en": None, "ask_how_to_use": True, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw)
    out = await query_rewriter([], "how do I use this?", nova, selected_language_code="en")
    data = json.loads(out)
    assert data["classification"] == "instruction"
    assert data["ask_how_to_use"] is True
    assert isinstance(data["how_it_works"], str) and len(data["how_it_works"]) > 10


@pytest.mark.asyncio
async def test_invalid_empty_query_off_topic():
    nova = DummyNovaDynamic(raw_json="{}")
    out = await query_rewriter([], "   ", nova, selected_language_code="en")
    data = json.loads(out)
    assert data["classification"] == "off-topic"


@pytest.mark.asyncio
async def test_timeout_fallback_uses_keyword_heuristic():
    nova = DummyNovaDynamic(raise_timeout=True)
    out = await query_rewriter([], "flood preparation tips", nova, selected_language_code="en")
    data = json.loads(out)
    assert data["reason"].startswith("Rewriter timeout")
    assert data["classification"] == "on-topic"


@pytest.mark.asyncio
async def test_generic_error_fallback_preserves_language_and_scope():
    nova = DummyNovaDynamic(raise_error=True)
    out = await query_rewriter([], "renewable energy benefits", nova, selected_language_code="es")
    data = json.loads(out)
    assert data["error"]["message"].startswith("Technical difficulties")
    assert data["expected_language"] == "es"
    assert data["classification"] == "on-topic"


@pytest.mark.asyncio
async def test_language_match_flag_derived_from_detected_vs_expected():
    raw = json.dumps({
        "reason": "ok", "language": "es", "expected_language": "en",
        "language_match": False, "classification": "off-topic",
        "rewrite_en": None, "ask_how_to_use": False, "how_it_works": None, "error": None
    })
    nova = DummyNovaDynamic(raw_json=raw)
    out = await query_rewriter([], "hola", nova, selected_language_code="en")
    data = json.loads(out)
    assert data["language"] == "es"
    assert data["expected_language"] == "en"
    assert data["language_match"] is False


