"""
Unit tests for Tiny-Aya model routing logic.

Verifies that language codes route to the correct regional model
(Fire/Earth/Water/Global) without hitting any live APIs.
"""

import pytest
from src.models.cohere_flow import (
    resolve_tiny_aya_model,
    FIRE_LANGUAGES,
    EARTH_LANGUAGES,
    WATER_LANGUAGES,
    CohereModel,
)
from src.models.query_routing import MultilingualRouter, LanguageSupport


# ──────────────────────────────────────────────────────────────
# resolve_tiny_aya_model() — pure function, no API calls
# ──────────────────────────────────────────────────────────────

class TestResolveTinyAyaModel:
    """Test the resolve_tiny_aya_model function returns correct model/region."""

    # FIRE: South Asian languages
    @pytest.mark.parametrize("lang_code", [
        "hi", "bn", "pa", "ur", "gu", "ta", "te", "mr",
        "ne", "si", "ml", "kn", "or", "as", "sd", "ks",
    ])
    def test_fire_languages_route_to_fire(self, lang_code):
        model_id, region = resolve_tiny_aya_model(lang_code)
        assert model_id == "tiny-aya-fire", f"{lang_code} → {model_id}"
        assert region == "fire"

    # EARTH: African languages
    @pytest.mark.parametrize("lang_code", [
        "sw", "yo", "ha", "ig", "am", "so", "rw", "sn", "zu", "xh",
        "st", "tn", "ny", "lg", "wo", "ff", "bm", "ti", "om", "rn",
    ])
    def test_earth_languages_route_to_earth(self, lang_code):
        model_id, region = resolve_tiny_aya_model(lang_code)
        assert model_id == "tiny-aya-earth", f"{lang_code} → {model_id}"
        assert region == "earth"

    # WATER: Asia-Pacific + Western Asia + Europe
    @pytest.mark.parametrize("lang_code", [
        "zh", "ja", "ko", "th", "vi", "id", "ms", "tl",  # Asia-Pacific
        "ar", "he", "fa", "tr", "ku",  # Western Asia
        "ru", "uk", "pl", "cs", "ro", "el",  # Eastern Europe
        "nl", "de", "fr", "it", "pt", "es",  # Western Europe
        "sv", "da", "no", "fi",  # Nordic
    ])
    def test_water_languages_route_to_water(self, lang_code):
        model_id, region = resolve_tiny_aya_model(lang_code)
        assert model_id == "tiny-aya-water", f"{lang_code} → {model_id}"
        assert region == "water"

    # GLOBAL: English and unknown
    @pytest.mark.parametrize("lang_code", [
        "en", "xx", "unknown", "",
    ])
    def test_global_fallback(self, lang_code):
        model_id, region = resolve_tiny_aya_model(lang_code)
        assert model_id == "tiny-aya-global", f"{lang_code} → {model_id}"
        assert region == "global"

    def test_none_defaults_to_global(self):
        """None language code should default to global (English)."""
        model_id, region = resolve_tiny_aya_model(None)
        assert model_id == "tiny-aya-global"
        assert region == "global"

    def test_locale_codes_handled(self):
        """Locale-style codes like 'en-US' should be split to base code."""
        model_id, region = resolve_tiny_aya_model("es-MX")
        assert model_id == "tiny-aya-water"  # Spanish is water
        model_id, region = resolve_tiny_aya_model("hi-IN")
        assert model_id == "tiny-aya-fire"  # Hindi is fire

    def test_case_insensitive(self):
        """Language codes should be case-insensitive."""
        model_id, _ = resolve_tiny_aya_model("FR")
        assert model_id == "tiny-aya-water"
        model_id, _ = resolve_tiny_aya_model("Hi")
        assert model_id == "tiny-aya-fire"


# ──────────────────────────────────────────────────────────────
# Language set completeness — no overlaps, expected sizes
# ──────────────────────────────────────────────────────────────

class TestLanguageSets:
    """Verify the language sets are well-formed."""

    def test_no_overlap_fire_earth(self):
        assert FIRE_LANGUAGES.isdisjoint(EARTH_LANGUAGES), \
            f"Overlap: {FIRE_LANGUAGES & EARTH_LANGUAGES}"

    def test_no_overlap_fire_water(self):
        assert FIRE_LANGUAGES.isdisjoint(WATER_LANGUAGES), \
            f"Overlap: {FIRE_LANGUAGES & WATER_LANGUAGES}"

    def test_no_overlap_earth_water(self):
        assert EARTH_LANGUAGES.isdisjoint(WATER_LANGUAGES), \
            f"Overlap: {EARTH_LANGUAGES & WATER_LANGUAGES}"

    def test_english_not_in_any_regional_set(self):
        """English should fall through to global, not be in any regional set."""
        assert "en" not in FIRE_LANGUAGES
        assert "en" not in EARTH_LANGUAGES
        assert "en" not in WATER_LANGUAGES

    def test_fire_has_expected_count(self):
        assert len(FIRE_LANGUAGES) == 16

    def test_earth_has_expected_count(self):
        assert len(EARTH_LANGUAGES) == 20

    def test_water_has_expected_count(self):
        assert len(WATER_LANGUAGES) == 52


# ──────────────────────────────────────────────────────────────
# CohereModel.with_model() — lightweight copy pattern
# ──────────────────────────────────────────────────────────────

class TestCohereModelWithModel:
    """Test the with_model() copy pattern for Tiny-Aya model switching."""

    def test_with_model_returns_new_instance(self):
        """with_model() should return a new CohereModel with the given model_id."""
        base = CohereModel(model_id="tiny-aya-global")
        switched = base.with_model("tiny-aya-fire")

        assert switched.model_id == "tiny-aya-fire"
        assert base.model_id == "tiny-aya-global"  # original unchanged

    def test_with_model_shares_client(self):
        """with_model() should share the same API client (not create new one)."""
        base = CohereModel(model_id="tiny-aya-global")
        switched = base.with_model("tiny-aya-water")

        # Both should have the same cohere client reference
        assert switched.client is base.client

    def test_with_model_preserves_client_identity(self):
        """with_model() copy should share the exact same client object (API key is inside it)."""
        base = CohereModel(model_id="tiny-aya-global")
        switched = base.with_model("tiny-aya-earth")

        # API key lives inside the shared client — verify identity, not attribute
        assert switched.client is base.client


# ──────────────────────────────────────────────────────────────
# MultilingualRouter.check_language_support — enum routing
# ──────────────────────────────────────────────────────────────

class TestRouterLanguageSupport:
    """Test the router's check_language_support returns correct LanguageSupport enum."""

    @pytest.fixture
    def router(self):
        return MultilingualRouter()

    def test_english_is_global(self, router):
        assert router.check_language_support("en") == LanguageSupport.TINY_AYA_GLOBAL

    def test_spanish_is_water(self, router):
        assert router.check_language_support("es") == LanguageSupport.TINY_AYA_WATER

    def test_hindi_is_fire(self, router):
        assert router.check_language_support("hi") == LanguageSupport.TINY_AYA_FIRE

    def test_swahili_is_earth(self, router):
        assert router.check_language_support("sw") == LanguageSupport.TINY_AYA_EARTH

    def test_unknown_falls_to_global(self, router):
        """Unknown codes should fall back to global, not raise."""
        assert router.check_language_support("xx") == LanguageSupport.TINY_AYA_GLOBAL

    def test_standardize_then_check(self, router):
        """Locale codes should standardize before checking."""
        std = router.standardize_language_code("fr-CA")
        assert router.check_language_support(std) == LanguageSupport.TINY_AYA_WATER


# ──────────────────────────────────────────────────────────────
# route_query — async integration at router level
# ──────────────────────────────────────────────────────────────

class TestRouteQueryAsync:
    """Test route_query returns correct routing_info per language."""

    @pytest.fixture
    def router(self):
        return MultilingualRouter()

    @pytest.mark.asyncio
    async def test_route_english_no_translation(self, router):
        result = await router.route_query(
            query="What is climate change?",
            language_code="en",
            language_name="english",
        )
        assert result["should_proceed"] is True
        ri = result["routing_info"]
        assert ri["needs_translation"] is False
        assert ri["support_level"] == "tiny_aya_global"
        assert ri["model_name"] == "Tiny-Aya Global"

    @pytest.mark.asyncio
    async def test_route_spanish_needs_translation(self, router):
        result = await router.route_query(
            query="test",
            language_code="es",
            language_name="spanish",
        )
        assert result["should_proceed"] is True
        ri = result["routing_info"]
        assert ri["needs_translation"] is True
        assert ri["support_level"] == "tiny_aya_water"
        assert ri["model_name"] == "Tiny-Aya Water"

    @pytest.mark.asyncio
    async def test_route_hindi_fire(self, router):
        result = await router.route_query(
            query="test",
            language_code="hi",
            language_name="hindi",
        )
        assert result["should_proceed"] is True
        ri = result["routing_info"]
        assert ri["support_level"] == "tiny_aya_fire"
        assert ri["model_name"] == "Tiny-Aya Fire"

    @pytest.mark.asyncio
    async def test_route_swahili_earth(self, router):
        result = await router.route_query(
            query="test",
            language_code="sw",
            language_name="swahili",
        )
        assert result["should_proceed"] is True
        ri = result["routing_info"]
        assert ri["support_level"] == "tiny_aya_earth"
        assert ri["model_name"] == "Tiny-Aya Earth"

    @pytest.mark.asyncio
    async def test_route_standardizes_locale_code(self, router):
        """en-US should be standardized to en before routing."""
        result = await router.route_query(
            query="What is climate change?",
            language_code="en-US",
            language_name="english",
        )
        assert result["should_proceed"] is True
        assert result["routing_info"]["needs_translation"] is False
