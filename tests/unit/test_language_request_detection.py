"""
Tests for explicit output-language request handling.

Covers:
- detect_language_request(): parsing "write me a message in Spanish"-style
  directives out of a query
- _is_predominantly_non_latin(): script detection used by the generation
  language-integrity guard (the fix for the "answers come back as numbers" bug)
- _has_alphabetic_content(): the cache sanity check
- End-to-end pipeline behavior: an explicit language request overrides the
  dropdown selection for the response translation
"""

import json
import pytest

from src.models.query_rewriter import detect_language_request
from src.models.gen_response_unified import _is_predominantly_non_latin
from src.models.climate_pipeline import _has_alphabetic_content


class TestDetectLanguageRequest:
    @pytest.mark.parametrize("text,expected", [
        ("write me a message in Spanish", "es"),
        ("write me a message in Spanish about flooding", "es"),
        ("can you answer in French? what causes heat waves", "fr"),
        ("respond in Urdu please", "ur"),
        ("translate this to German", "de"),
        ("translate my last answer into French", "fr"),
        ("write a note in english about heat waves", "en"),
        ("draft a message in Polish for my neighbours", "pl"),
        # Cross-language endonyms
        ("escribe un mensaje en inglés sobre inundaciones", "en"),
        # Non-Latin scripts
        ("用中文回答：什么是气候变化", "zh"),
        ("日本語で答えてください", "ja"),
        ("напиши по-русски о наводнениях", "ru"),
    ])
    def test_detects_explicit_requests(self, text, expected):
        assert detect_language_request(text) == expected

    @pytest.mark.parametrize("text", [
        "what is climate change?",
        "is Spanish spoken in Toronto?",
        "tell me about the Spanish approach to climate adaptation",
        "how do heat waves affect people in French Polynesia?",
        "write about flood risks for people in Germany",
        "",
        None,
    ])
    def test_no_false_positives(self, text):
        assert detect_language_request(text) is None


class TestScriptDetection:
    def test_pure_english_is_latin(self):
        assert not _is_predominantly_non_latin(
            "Climate change refers to long-term shifts in temperatures and weather patterns."
        )

    def test_mostly_english_with_a_few_cjk_chars_is_latin(self):
        assert not _is_predominantly_non_latin(
            "Climate change is real. 气候变化 This matters because temperatures keep rising."
        )

    def test_chinese_answer_is_non_latin(self):
        assert _is_predominantly_non_latin("气候变化是指温度和天气模式的长期变化。" * 3)

    def test_urdu_answer_is_non_latin(self):
        assert _is_predominantly_non_latin("موسمیاتی تبدیلی درجہ حرارت اور موسم کے انداز میں طویل مدتی تبدیلیوں کو کہتے ہیں۔")

    def test_digits_only_is_not_flagged(self):
        # Fewer than 20 letters → not enough signal to translate
        assert not _is_predominantly_non_latin("2050 1.5 30% 26.9")

    def test_accented_latin_is_latin(self):
        assert not _is_predominantly_non_latin(
            "El cambio climático se refiere a los cambios a largo plazo de las temperaturas."
        )


class TestCacheSanityCheck:
    def test_real_answer_passes(self):
        assert _has_alphabetic_content("Climate change refers to long-term shifts.")

    def test_non_latin_answer_passes(self):
        assert _has_alphabetic_content("气候变化是指温度和天气模式的长期变化。")

    def test_digits_only_fails(self):
        assert not _has_alphabetic_content("2050 1.5 30% 26.9 ...")

    def test_empty_and_non_string_fail(self):
        assert not _has_alphabetic_content("")
        assert not _has_alphabetic_content(None)
        assert not _has_alphabetic_content(0.85)


@pytest.mark.asyncio
async def test_pipeline_honors_explicit_language_request(monkeypatch):
    """English dropdown + "write me a message in Spanish about flooding" →
    the answer is translated to Spanish, not returned in English."""
    from src.models.climate_pipeline import ClimateQueryPipeline
    from src.models.query_routing import MultilingualRouter

    class FakeCache:
        store = {}
        def __init__(self, *args, **kwargs):
            self.redis_client = True
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, value):
            self.store[key] = value
            return True
        async def get_list(self, key, start, end):
            return []
        async def add_to_list(self, key, value):
            return True

    async def fake_get_documents(query, index, embed_model, cohere_client):
        return [{"title": "Doc", "url": "u", "content": "flooding preparedness info"}]
    monkeypatch.setattr("src.models.climate_pipeline.get_documents", fake_get_documents, raising=True)

    async def fake_query_rewriter(conversation_history=None, user_query="", nova_model=None, selected_language_code="en"):
        return json.dumps({
            "reasoning": "test",
            "language": "en",
            "classification": "on-topic",
            "language_match": True,
            "requested_language": "es",
            "rewrite_en": "Write a short message about flooding preparedness.",
        })
    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", fake_query_rewriter, raising=True)

    async def fake_check_hallucination(**kwargs):
        return 0.9
    monkeypatch.setattr("src.models.climate_pipeline.check_hallucination", fake_check_hallucination, raising=True)

    english_answer = "Here is a short message about flooding preparedness."
    spanish_answer = "Aquí hay un mensaje corto sobre la preparación para inundaciones."

    class FakeGenerator:
        async def generate_response(self, **kwargs):
            return english_answer, []

    translate_calls = []

    class _Cohere:
        async def translate(self, text, s=None, t=None):
            translate_calls.append((text, s, t))
            return spanish_answer
        def with_model(self, model_id):
            return self

    class _Nova:
        async def translate(self, text, s=None, t=None):
            return text

    pipeline = object.__new__(ClimateQueryPipeline)
    pipeline.router = MultilingualRouter()
    pipeline.response_generator = FakeGenerator()
    pipeline.cache = FakeCache()
    pipeline.nova_model = _Nova()
    pipeline.cohere_model = _Cohere()
    pipeline.embed_model = object()
    pipeline.index = object()
    pipeline.cohere_client = object()
    pipeline.COHERE_API_KEY = "x"
    pipeline.redis_client = None

    FakeCache.store = {}
    res = await pipeline.process_query(
        query="write me a message in Spanish about flooding",
        language_name="english",
        conversation_history=[],
    )

    assert res["success"] is True
    assert res["response"] == spanish_answer
    assert res["language_code"] == "es"
    # The translation target was Spanish
    assert any(t and "spanish" in str(t).lower() for (_, _, t) in translate_calls)
