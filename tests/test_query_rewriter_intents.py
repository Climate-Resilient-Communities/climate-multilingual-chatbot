import asyncio
import re

import pytest

from src.models.query_rewriter import query_rewriter


class DummyBedrockModel:
    async def content_generation(self, prompt: str, system_message: str) -> str:
        # Return canned outputs based on presence of keywords in the prompt to simulate LLM behavior
        lower = prompt.lower()
        if 'hola' in lower or 'bonjour' in lower or 'hello' in lower:
            return (
                "Reasoning: greeting detected\nLanguage: es\nClassification: on-topic\nExpectedLanguage: en\nLanguageMatch: no\n"
                "Rewritten: N/A\nCanned: yes\nCannedType: greeting\nCannedText: Hey im multilingual Chatbot, how can I help you?"
            )
        if 'adios' in lower or 'adiós' in lower or 'goodbye' in lower:
            return (
                "Reasoning: goodbye detected\nLanguage: es\nClassification: on-topic\nExpectedLanguage: en\nLanguageMatch: no\n"
                "Rewritten: N/A\nCanned: yes\nCannedType: goodbye\nCannedText: Thank you for coming hope to chat with you again!"
            )
        if 'gracias' in lower or 'thanks' in lower:
            return (
                "Reasoning: thanks detected\nLanguage: es\nClassification: on-topic\nExpectedLanguage: en\nLanguageMatch: no\n"
                "Rewritten: N/A\nCanned: yes\nCannedType: thanks\nCannedText: You're welcome! If you have more questions, I'm here to help."
            )
        if 'emergency' in lower or '911' in lower:
            return (
                "Reasoning: emergency detected\nLanguage: en\nClassification: on-topic\nExpectedLanguage: en\nLanguageMatch: yes\n"
                "Rewritten: N/A\nCanned: yes\nCannedType: emergency\nCannedText: If this is an emergency, please contact local authorities immediately (e.g., 911 in the U.S. or your local emergency number)."
            )
        return (
            "Reasoning: default\nLanguage: en\nClassification: on-topic\nExpectedLanguage: en\nLanguageMatch: yes\n"
            "Rewritten: What are key climate actions?\nCanned: no\nCannedType: none\nCannedText: N/A"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("text,expected_contains", [
    ("hello", "Canned: yes"),
    ("hola", "Canned: yes"),
    ("bonjour", "Canned: yes"),
    ("adios", "CannedType: goodbye"),
    ("gracias", "CannedType: thanks"),
    ("thanks", "CannedType: thanks"),
    ("emergency help", "CannedType: emergency"),
    ("911 please", "CannedType: emergency"),
])
async def test_query_rewriter_canned_intents(text, expected_contains):
    out = await query_rewriter(
        conversation_history=[],
        user_query=text,
        nova_model=DummyBedrockModel(),
        selected_language_code="en",
    )
    assert expected_contains in out
    assert "CannedText:" in out


@pytest.mark.asyncio
async def test_pipeline_short_circuits_on_canned(monkeypatch):
    from src.models.climate_pipeline import ClimateQueryPipeline

    class DummyPipeline(ClimateQueryPipeline):
        async def _route_model(self, language_name, query):
            return {"model_name": "test-model", "model_type": "test", "english_query": query}

    async def canned_rewriter(**kwargs):
        return (
            "Reasoning: Detected canned intent\nLanguage: unknown\nClassification: on-topic\n"
            "ExpectedLanguage: en\nLanguageMatch: yes\nRewritten: N/A\nCanned: yes\nCannedType: greeting\n"
            "CannedText: Hey im multilingual Chatbot, how can I help you?"
        )

    monkeypatch.setattr("src.models.climate_pipeline.query_rewriter", canned_rewriter)
    pipeline = DummyPipeline(index_name="dummy-index")

    result = await pipeline.process_query("hello", "English", conversation_history=[])
    assert result["success"] is True
    assert result["retrieval_source"] == "canned"
    assert "Hey im multilingual Chatbot" in result["response"]


