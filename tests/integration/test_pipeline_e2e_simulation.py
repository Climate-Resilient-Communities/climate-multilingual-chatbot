"""
End-to-End Pipeline Simulation Tests

These tests simulate a REAL user asking a question and verify it goes through
the entire pipeline: Routing → Rewriting → Retrieval → Generation → Translation.

NO MOCKS — these hit real APIs (Pinecone, Cohere, HuggingFace, AWS Bedrock).
They require live API keys configured in .env.

Tests cover:
1. Full pipeline flow for multiple languages
2. Response timing (speed budgets)
3. Tiny-Aya model routing verification per language
4. Off-topic/harmful query rejection
5. Language mismatch handling
"""

import os
import sys
import time
import asyncio
import logging
import pytest
from typing import Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.env_loader import load_environment
from src.models.climate_pipeline import ClimateQueryPipeline

# Load environment before evaluating skipif conditions
load_environment()

logger = logging.getLogger(__name__)

# Production index name
INDEX_NAME = "climate-change-adaptation-index-10-24-prod"


_LIVE_API_REQUIRED = not all([
    os.getenv('COHERE_API_KEY'),
    os.getenv('AWS_ACCESS_KEY_ID'),
    os.getenv('PINECONE_API_KEY'),
    os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN') or os.getenv('HF_API_TOKEN'),
])

pytestmark = pytest.mark.skipif(
    _LIVE_API_REQUIRED,
    reason="Requires live API keys (COHERE_API_KEY, AWS credentials, PINECONE_API_KEY, HF_TOKEN)"
)


@pytest.fixture(scope="module")
def pipeline():
    """Initialize the real pipeline once for all tests in this module."""
    # Flush Redis to prevent stale cached results from prior runs
    # contaminating model_used assertions (e.g., English returning "Water"
    # from a cached Spanish query with the same text).
    try:
        import redis
        redis.Redis().flushall()
    except Exception:
        pass  # Redis may not be running
    pipe = ClimateQueryPipeline(index_name=INDEX_NAME)
    return pipe


# ──────────────────────────────────────────────────────────────
# 1. FULL E2E SIMULATION — question goes through all pipeline stages
# ──────────────────────────────────────────────────────────────

class TestFullPipelineSimulation:
    """Simulate a real user asking a question end-to-end."""

    @pytest.mark.asyncio
    async def test_english_climate_question_e2e(self, pipeline):
        """English question goes through all pipeline stages and returns a complete response."""
        result = await pipeline.process_query(
            query="What causes climate change?",
            language_name="english",
        )

        # Must succeed
        assert result["success"] is True, f"Pipeline failed: {result.get('response', result.get('message'))}"

        # Must have a real response (not empty, not error)
        response = result["response"]
        assert isinstance(response, str)
        assert len(response) > 50, f"Response too short ({len(response)} chars): {response[:100]}"

        # Must have citations from RAG
        assert "citations" in result
        assert isinstance(result["citations"], list)

        # Must report processing time
        assert "processing_time" in result
        assert result["processing_time"] > 0

        # Must report which model was used
        assert "model_used" in result
        assert result["model_used"] != "N/A"

        # Must report the correct language
        assert result["language_code"] == "en"

    @pytest.mark.asyncio
    async def test_spanish_climate_question_e2e(self, pipeline):
        """Spanish question goes through routing → translation → generation → back-translation."""
        result = await pipeline.process_query(
            query="¿Qué causa el cambio climático?",
            language_name="spanish",
        )

        assert result["success"] is True, f"Pipeline failed: {result.get('response', result.get('message'))}"
        assert len(result["response"]) > 30
        assert result["language_code"] == "es"

    @pytest.mark.asyncio
    async def test_french_climate_question_e2e(self, pipeline):
        """French question flows through the full pipeline."""
        result = await pipeline.process_query(
            query="Quels sont les effets du changement climatique?",
            language_name="french",
        )

        assert result["success"] is True, f"Pipeline failed: {result.get('response', result.get('message'))}"
        assert len(result["response"]) > 30
        assert result["language_code"] == "fr"

    @pytest.mark.asyncio
    async def test_hindi_climate_question_e2e(self, pipeline):
        """Hindi question routes to Tiny-Aya Fire model."""
        result = await pipeline.process_query(
            query="जलवायु परिवर्तन क्या है?",
            language_name="hindi",
        )

        assert result["success"] is True, f"Pipeline failed: {result.get('response', result.get('message'))}"
        assert result["language_code"] == "hi"

    @pytest.mark.asyncio
    async def test_swahili_climate_question_e2e(self, pipeline):
        """Swahili question routes to Tiny-Aya Earth model."""
        result = await pipeline.process_query(
            query="Nini kinachosababisha mabadiliko ya hali ya hewa?",
            language_name="swahili",
        )

        assert result["success"] is True, f"Pipeline failed: {result.get('response', result.get('message'))}"
        assert result["language_code"] == "sw"


# ──────────────────────────────────────────────────────────────
# 2. RESPONSE TIMING — each query must complete within budget
# ──────────────────────────────────────────────────────────────

class TestResponseTiming:
    """Measure and enforce speed budgets for pipeline queries."""

    MAX_RESPONSE_TIME_SECONDS = 180.0  # Budget: 180s — live API calls (HF + Pinecone + Cohere)

    @pytest.mark.asyncio
    async def test_english_query_speed(self, pipeline):
        """English queries should be fast (no translation needed)."""
        start = time.time()
        result = await pipeline.process_query(
            query="How does renewable energy help fight climate change?",
            language_name="english",
        )
        elapsed = time.time() - start

        assert result["success"] is True, f"Query failed: {result}"
        assert elapsed < self.MAX_RESPONSE_TIME_SECONDS, (
            f"English query took {elapsed:.1f}s (budget: {self.MAX_RESPONSE_TIME_SECONDS}s)"
        )
        logger.info(f"English query completed in {elapsed:.1f}s")

        # Verify pipeline reports timing accurately
        reported_time = result.get("processing_time", 0)
        assert abs(reported_time - elapsed) < 5.0, (
            f"Reported time ({reported_time:.1f}s) differs from wall clock ({elapsed:.1f}s)"
        )

    @pytest.mark.asyncio
    async def test_spanish_query_speed(self, pipeline):
        """Spanish queries include translation overhead but should still be within budget."""
        start = time.time()
        result = await pipeline.process_query(
            query="¿Cómo afecta el cambio climático al agua?",
            language_name="spanish",
        )
        elapsed = time.time() - start

        assert result["success"] is True, f"Query failed: {result}"
        assert elapsed < self.MAX_RESPONSE_TIME_SECONDS, (
            f"Spanish query took {elapsed:.1f}s (budget: {self.MAX_RESPONSE_TIME_SECONDS}s)"
        )
        logger.info(f"Spanish query (with translation) completed in {elapsed:.1f}s")

    @pytest.mark.asyncio
    async def test_multi_query_sequential_speed(self, pipeline):
        """Three sequential queries should all complete within individual budgets.

        Retries once on transient API failures (504, 502, connection errors).
        """
        queries = [
            ("What is a carbon footprint?", "english"),
            ("¿Qué es la energía solar?", "spanish"),
            ("Was ist der Treibhauseffekt?", "german"),
        ]

        for query, lang in queries:
            result = None
            for attempt in range(2):  # retry once on transient failure
                start = time.time()
                result = await pipeline.process_query(
                    query=query,
                    language_name=lang,
                    skip_cache=True,
                )
                elapsed = time.time() - start

                if result["success"]:
                    break
                # Retry only on transient retrieval/API errors
                resp = result.get("response", "")
                if attempt == 0 and ("504" in resp or "502" in resp or "Time-out" in resp):
                    logger.warning(f"{lang} query hit transient error, retrying: {resp[:100]}")
                    await asyncio.sleep(2)
                    continue
                break  # non-transient failure, don't retry

            assert result["success"] is True, f"{lang} query failed: {result}"
            assert elapsed < self.MAX_RESPONSE_TIME_SECONDS, (
                f"{lang} query took {elapsed:.1f}s"
            )
            logger.info(f"{lang.capitalize()} query: {elapsed:.1f}s")


# ──────────────────────────────────────────────────────────────
# 3. TINY-AYA MODEL ROUTING — verify correct model per language
# ──────────────────────────────────────────────────────────────

class TestTinyAyaRouting:
    """Verify each language routes to the correct Tiny-Aya regional model.

    All tests use skip_cache=True to bypass Redis cache and test
    actual model routing logic (cache may contain stale model_used values
    from previous runs).
    """

    @pytest.mark.asyncio
    async def test_english_routes_to_global(self, pipeline):
        """English → Tiny-Aya Global."""
        result = await pipeline.process_query(
            query="What is climate change adaptation?",
            language_name="english",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "global" in result["model_used"].lower(), (
            f"English should route to Global, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_spanish_routes_to_water(self, pipeline):
        """Spanish → Tiny-Aya Water (Europe)."""
        result = await pipeline.process_query(
            query="¿Qué es la adaptación al cambio climático?",
            language_name="spanish",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "water" in result["model_used"].lower(), (
            f"Spanish should route to Water, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_french_routes_to_water(self, pipeline):
        """French → Tiny-Aya Water (Europe)."""
        result = await pipeline.process_query(
            query="Qu'est-ce que l'adaptation au changement climatique?",
            language_name="french",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "water" in result["model_used"].lower(), (
            f"French should route to Water, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_german_routes_to_water(self, pipeline):
        """German → Tiny-Aya Water (Europe)."""
        result = await pipeline.process_query(
            query="Was ist Klimaanpassung?",
            language_name="german",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "water" in result["model_used"].lower(), (
            f"German should route to Water, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_chinese_routes_to_water(self, pipeline):
        """Chinese → Tiny-Aya Water (Asia-Pacific)."""
        result = await pipeline.process_query(
            query="什么是气候变化适应?",
            language_name="chinese",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "water" in result["model_used"].lower(), (
            f"Chinese should route to Water, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_hindi_routes_to_fire(self, pipeline):
        """Hindi → Tiny-Aya Fire (South Asian)."""
        result = await pipeline.process_query(
            query="जलवायु परिवर्तन अनुकूलन क्या है?",
            language_name="hindi",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "fire" in result["model_used"].lower(), (
            f"Hindi should route to Fire, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_bengali_routes_to_fire(self, pipeline):
        """Bengali → Tiny-Aya Fire (South Asian)."""
        result = await pipeline.process_query(
            query="জলবায়ু পরিবর্তন কী?",
            language_name="bengali",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "fire" in result["model_used"].lower(), (
            f"Bengali should route to Fire, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_swahili_routes_to_earth(self, pipeline):
        """Swahili → Tiny-Aya Earth (African)."""
        result = await pipeline.process_query(
            query="Nini maana ya kubadilika kwa hali ya hewa?",
            language_name="swahili",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "earth" in result["model_used"].lower(), (
            f"Swahili should route to Earth, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_yoruba_routes_to_earth(self, pipeline):
        """Yoruba → Tiny-Aya Earth (African).

        Note: Pinecone index has limited Yoruba content, so response generation
        may fail. We verify routing regardless of content availability.
        """
        result = await pipeline.process_query(
            query="Kini iyipada oju-ọjọ?",
            language_name="yoruba",
            skip_cache=True,
        )
        # Verify routing regardless of success — content gaps are expected for Yoruba
        assert "earth" in result["model_used"].lower(), (
            f"Yoruba should route to Earth, got: {result['model_used']}"
        )

    @pytest.mark.asyncio
    async def test_portuguese_routes_to_water(self, pipeline):
        """Portuguese → Tiny-Aya Water (Europe)."""
        result = await pipeline.process_query(
            query="O que é mudança climática?",
            language_name="portuguese",
            skip_cache=True,
        )
        assert result["success"] is True
        assert "water" in result["model_used"].lower(), (
            f"Portuguese should route to Water, got: {result['model_used']}"
        )


# ──────────────────────────────────────────────────────────────
# 4. TOPIC MODERATION — off-topic and harmful queries blocked
# ──────────────────────────────────────────────────────────────

class TestTopicModeration:
    """Verify off-topic and harmful queries are properly rejected."""

    @pytest.mark.asyncio
    async def test_off_topic_rejected(self, pipeline):
        """Off-topic query about cooking should be rejected."""
        result = await pipeline.process_query(
            query="What is the best recipe for lasagna?",
            language_name="english",
        )
        # Pipeline should either fail or return a canned off-topic response
        if result["success"] is True:
            # If success, the response should be a canned off-topic message
            assert result.get("retrieval_source") == "canned" or \
                   result.get("fallback_reason") in ["off_topic_canned", "off-topic"], \
                   f"Off-topic query succeeded without canned response: {result['response'][:100]}"

    @pytest.mark.asyncio
    async def test_climate_query_accepted(self, pipeline):
        """On-topic climate query should be accepted."""
        result = await pipeline.process_query(
            query="How does flooding affect cities like Toronto?",
            language_name="english",
        )
        assert result["success"] is True, f"Climate query was rejected: {result}"
        assert len(result["response"]) > 50


# ──────────────────────────────────────────────────────────────
# 5. LANGUAGE MISMATCH HANDLING
# ──────────────────────────────────────────────────────────────

class TestLanguageMismatch:
    """Verify pipeline handles language mismatch gracefully."""

    @pytest.mark.asyncio
    async def test_english_selected_spanish_query(self, pipeline):
        """English selected but Spanish query → canned mismatch response."""
        result = await pipeline.process_query(
            query="¿Qué es el cambio climático?",
            language_name="english",
        )
        # Should return success with a mismatch canned response
        assert result["success"] is True
        assert "language" in result["response"].lower(), \
            f"Expected language mismatch message, got: {result['response'][:100]}"
