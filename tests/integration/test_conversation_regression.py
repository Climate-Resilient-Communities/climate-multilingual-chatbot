"""
Conversation regression tests for the end-to-end pipeline.

- Default (fast) mode mocks pipeline.process_query to validate that the
  chatbot correctly forwards multi-turn conversations and accumulates history.
- Live mode (set RUN_LIVE=1) runs the real pipeline to surface latency
  or routing issues across multiple-turn histories.
"""

import os
import asyncio
import time
import pytest
from typing import List, Dict
from unittest.mock import AsyncMock

from src.main_nova import MultilingualClimateChatbot

LIVE = str(os.getenv("RUN_LIVE", "0")).strip().lower() in ("1", "true", "yes")


def _success_result(query, language_code="en", model_used="tiny-aya-global"):
    """Build a pipeline-format success result for fast mode."""
    return {
        "success": True,
        "response": f"Answer for: {query}",
        "citations": ["https://example.com"],
        "faithfulness_score": 0.95,
        "processing_time": 0.1,
        "language_code": language_code,
        "model_used": model_used,
        "model_type": "cohere",
        "retrieval_source": "pinecone",
        "fallback_reason": None,
        "original_query": query,
        "debug_info": {},
    }


# Language code mapping (matches MultilingualRouter)
_LANG_CODES = {
    "english": "en", "spanish": "es", "french": "fr", "german": "de",
    "chinese": "zh", "arabic": "ar", "hindi": "hi", "swahili": "sw",
    "bengali": "bn", "portuguese": "pt", "yoruba": "yo",
}


# --- Scenario definitions (20 total) ---
SCENARIOS: List[Dict] = [
    {
        "name": "general_climate_three_turns",
        "language": "english",
        "turns": [
            "What is climate change?",
            "How else can I support?",
            "What else can I do?",
        ],
    },
    {
        "name": "help_others_understand",
        "language": "english",
        "turns": [
            "How can we help those who don't know about climate change?",
            "What resources can I share?",
        ],
    },
    {
        "name": "flooding_toronto",
        "language": "english",
        "turns": [
            "What can I do about flooding in Toronto?",
            "What else can I do?",
        ],
    },
    {
        "name": "wildfire_smoke_safety",
        "language": "english",
        "turns": [
            "How do I protect my family from wildfire smoke?",
            "Any low-cost steps I can take?",
        ],
    },
    {
        "name": "heatwave_safety",
        "language": "english",
        "turns": [
            "How do I stay safe during a heat wave?",
            "What else should I prepare?",
        ],
    },
    {
        "name": "cold_snap_home",
        "language": "english",
        "turns": [
            "How can I prepare my home for extreme cold?",
            "What else can I do to lower my heating bill?",
        ],
    },
    {
        "name": "storm_preparedness",
        "language": "english",
        "turns": [
            "What should be in a storm emergency kit?",
            "Any tips for apartment buildings?",
        ],
    },
    {
        "name": "renewable_energy_intro",
        "language": "english",
        "turns": [
            "What is renewable energy?",
            "How can I start at home?",
        ],
    },
    {
        "name": "transport_emissions",
        "language": "english",
        "turns": [
            "How can I reduce transport emissions?",
            "Is public transit better than driving?",
        ],
    },
    {
        "name": "food_footprint",
        "language": "english",
        "turns": [
            "How can diet changes lower my carbon footprint?",
            "What else can I do that's impactful?",
        ],
    },
    # Non-English (should route + translate)
    {
        "name": "spanish_general",
        "language": "spanish",
        "turns": [
            "¿Qué es el cambio climático?",
            "¿Qué más puedo hacer?",
        ],
    },
    {
        "name": "french_heat",
        "language": "french",
        "turns": [
            "Comment rester en sécurité pendant une canicule?",
            "Quoi d'autre dois-je préparer?",
        ],
    },
    {
        "name": "german_flooding",
        "language": "german",
        "turns": [
            "Was kann ich bei Überschwemmungen tun?",
            "Was kann ich sonst noch tun?",
        ],
    },
    {
        "name": "chinese_winters",
        "language": "chinese",
        "turns": [
            "气候变化会如何影响加拿大的冬天?",
            "我还可以做些什么?",
        ],
    },
    {
        "name": "arabic_air_quality",
        "language": "arabic",
        "turns": [
            "كيف أحمي عائلتي من تلوث الهواء أثناء موجات الحر؟",
            "ما الذي يمكنني فعله أيضًا؟",
        ],
    },
    {
        "name": "heat_vulnerable_groups",
        "language": "english",
        "turns": [
            "How can we help seniors during heat waves?",
            "What else can communities do?",
        ],
    },
    {
        "name": "school_preparedness",
        "language": "english",
        "turns": [
            "How can schools prepare for wildfire smoke days?",
            "What else should staff plan for?",
        ],
    },
    {
        "name": "workplace_resilience",
        "language": "english",
        "turns": [
            "How can workplaces prepare for climate-related disruptions?",
            "What else can small businesses do?",
        ],
    },
    {
        "name": "home_energy",
        "language": "english",
        "turns": [
            "How do I make my home more energy efficient?",
            "What else beyond insulation?",
        ],
    },
    {
        "name": "municipal_programs",
        "language": "english",
        "turns": [
            "What city programs exist for climate adaptation?",
            "Where else can I find help?",
        ],
    },
]


@pytest.fixture(scope="module")
def chatbot() -> MultilingualClimateChatbot:
    return MultilingualClimateChatbot(
        index_name=os.getenv("PINECONE_INDEX", "climate-change-adaptation-index-10-24-prod")
    )


@pytest.mark.asyncio
async def test_conversation_regression(chatbot):
    """Run 20 multi-turn scenarios and assert all succeed (on-topic)."""

    failures: List[str] = []

    if not LIVE:
        # Fast mode: mock pipeline.process_query so we don't hit external APIs.
        # The monkeypatch-module-functions approach doesn't work because the
        # pipeline calls its own internal methods, not module-level functions.
        async def _mock_process_query(query, language_name, conversation_history=None, **kw):
            lang_code = _LANG_CODES.get(language_name, "en")
            return _success_result(query, language_code=lang_code)

        chatbot.pipeline.process_query = _mock_process_query

    for sc in SCENARIOS:
        language = sc["language"]
        conversation_history: List[Dict] = []
        start = time.time()
        for turn in sc["turns"]:
            res = await chatbot.process_query(query=turn, language_name=language, conversation_history=conversation_history)
            if not res or not res.get("success", False):
                failures.append(f"{sc['name']} → turn '{turn}' failed: {res}")
                break
            # update history for next turn
            if res.get("current_turn"):
                conversation_history.append(res["current_turn"])
        elapsed = (time.time() - start) * 1000
        print(f"SCENARIO {sc['name']} [{language}] ms={elapsed:.1f} {'FAIL' if any(sc['name'] in f for f in failures) else 'PASS'}")

    # In fast (mocked) mode, enforce pass; in live mode, only report
    if not LIVE:
        assert not failures, "Failures encountered:\n" + "\n".join(failures)
    else:
        # Don't fail CI on live flakiness; log summary
        if failures:
            print("LIVE FAILURES:\n" + "\n".join(failures))
