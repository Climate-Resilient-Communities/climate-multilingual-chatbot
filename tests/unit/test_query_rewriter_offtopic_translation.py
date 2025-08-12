import asyncio
import json
import sys
from types import ModuleType

import pytest

# Stub aioboto3 before importing modules that require it
if 'aioboto3' not in sys.modules:
    sys.modules['aioboto3'] = ModuleType('aioboto3')

from src.models.query_rewriter import query_rewriter


class DummyNova:
    async def content_generation(self, prompt: str, system_message: str = None):
        # Simulate a conservative model output: marks Chinese query off-topic and no rewrite_en
        return '{"reason":"test","language":"zh","expected_language":"zh","language_match":true,"classification":"off-topic","rewrite_en":null,"ask_how_to_use":false,"how_it_works":null,"error":null}'

    async def translate(self, text: str, source_lang: str = None, target_lang: str = None):
        # Provide a simple English translation that contains in-scope keywords
        return "Rotate stock using FIFO to avoid food waste"


@pytest.mark.asyncio
async def test_offtopic_non_english_gets_translated_and_flipped():
    convo = ["user: context irrelevant"]
    user_query = "合理轮换存货：采用先进先出的原则，避免食物过期浪费。"
    nova = DummyNova()

    out = await query_rewriter(convo, user_query, nova_model=nova, selected_language_code="zh")
    data = json.loads(out)

    assert data["expected_language"] == "zh"
    # Should be flipped to on-topic due to translation containing 'waste'
    assert data["classification"] == "on-topic"
    # rewrite_en should be populated by fallback translation
    assert isinstance(data.get("rewrite_en"), str) and len(data["rewrite_en"]) > 0


