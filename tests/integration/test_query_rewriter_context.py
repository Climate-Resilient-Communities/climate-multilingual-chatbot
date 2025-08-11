import os
import asyncio
import json
import pytest

from src.models.query_rewriter import query_rewriter
from src.models.nova_flow import BedrockModel
from src.models.conversation_parser import conversation_parser

pytestmark = pytest.mark.asyncio


async def _run_rewriter(messages, current_query, expected_lang="en", selected_lang="en"):
    model = BedrockModel()
    try:
        formatted = conversation_parser.format_for_query_rewriter(messages)
        raw = await query_rewriter(
            conversation_history=formatted,
            user_query=current_query,
            nova_model=model,
            selected_language_code=selected_lang,
        )
        return json.loads(raw)
    finally:
        await model.close()


async def test_followup_are_you_sure_on_topic_from_history():
    messages = [
        {"role": "user", "content": "What are the impacts of climate change on winters in Canada?"},
        {"role": "assistant", "content": "Winters are warming overall, with less snow and more rain in many regions."},
    ]
    result = await _run_rewriter(messages, "are you sure?", expected_lang="en", selected_lang="en")
    assert result["language"] == "en"
    assert result["expected_language"] == "en"
    assert result["classification"] in ("on-topic", "instruction")
    if result["classification"] == "on-topic":
        assert isinstance(result.get("rewrite_en"), str) and len(result["rewrite_en"]) > 0


async def test_followup_really_keep_context():
    messages = [
        {"role": "user", "content": "How does climate change affect flooding risk in Toronto?"},
        {"role": "assistant", "content": "Heavier rainfall and urban runoff increase basement flood risks."},
    ]
    result = await _run_rewriter(messages, "really?", expected_lang="en", selected_lang="en")
    assert result["language"] == "en"
    assert result["classification"] in ("on-topic", "instruction")
    if result["classification"] == "on-topic":
        assert "flood" in (result.get("rewrite_en") or "").lower()


async def test_instruction_when_history_is_how_to_use():
    messages = [
        {"role": "user", "content": "how do i use this?"},
        {"role": "assistant", "content": "Choose a language on the left, ask climate questions, and press send."},
    ]
    result = await _run_rewriter(messages, "are you sure?", expected_lang="en", selected_lang="en")
    assert result["classification"] == "instruction"
    assert result.get("ask_how_to_use") is True


async def test_full_history_followups_are_you_sure_and_tell_me():
    # Conversation: hi how are you, What is climate change? How is it effective, then are you sure? tell me what it does
    messages = [
        {"role": "user", "content": "hi how are you"},
        {"role": "assistant", "content": "Hello! I can help with climate questions. How can I help?"},
        {"role": "user", "content": "What is climate change?"},
        {"role": "assistant", "content": "Climate change refers to long-term shifts in temperature and weather patterns, mainly due to human activities."},
        {"role": "user", "content": "How is it effective?"},
    ]

    # Follow-up 1: "are you sure?" should infer climate context
    result1 = await _run_rewriter(messages, "are you sure?", expected_lang="en", selected_lang="en")
    assert result1["language"] == "en"
    assert result1["expected_language"] == "en"
    assert result1["classification"] in ("on-topic", "instruction")
    if result1["classification"] == "on-topic":
        assert isinstance(result1.get("rewrite_en"), str) and len(result1["rewrite_en"]) > 0

    # Add the follow-up to history (simulate assistant confirming)
    messages2 = messages + [
        {"role": "assistant", "content": "Yes, based on national assessments, those effects are well-documented."}
    ]

    # Follow-up 2: "tell me what it does" should rewrite to explicit climate explanation
    result2 = await _run_rewriter(messages2, "tell me what it does", expected_lang="en", selected_lang="en")
    assert result2["language"] == "en"
    assert result2["expected_language"] == "en"
    assert result2["classification"] in ("on-topic", "instruction")
    if result2["classification"] == "on-topic":
        assert isinstance(result2.get("rewrite_en"), str) and len(result2["rewrite_en"]) > 0
