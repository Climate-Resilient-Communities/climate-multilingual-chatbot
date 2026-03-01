"""
Unit tests for the query_rewriter module rewriting logic.

The query_rewriter now:
- Accepts: (conversation_history, user_query, nova_model, selected_language_code="en")
- Calls nova_model.content_generation(prompt=..., system_message=...) once
- Returns a JSON string with keys: reason, language, expected_language,
  language_match, classification, rewrite_en, canned, ask_how_to_use,
  how_it_works, error
"""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.models.query_rewriter import query_rewriter


def _make_model_json_response(
    classification="on-topic",
    language="en",
    rewrite_en=None,
    reason="test",
    language_match=True,
    ask_how_to_use=False,
):
    """Helper to build the JSON string the LLM would return."""
    return json.dumps({
        "reason": reason,
        "language": language,
        "expected_language": "en",
        "language_match": language_match,
        "classification": classification,
        "rewrite_en": rewrite_en,
        "ask_how_to_use": ask_how_to_use,
        "how_it_works": None,
        "error": None,
    })


def _mock_model(response_json: str):
    """Create a mock BedrockModel whose content_generation returns the given JSON."""
    model = MagicMock()
    model.content_generation = AsyncMock(return_value=response_json)
    return model


# --- Test Cases for Vague Follow-ups ---
vague_follow_up_cases = [
    (
        "Vague 'what else'",
        ["User: How can I reduce my carbon footprint at home?", "AI: You can use energy-efficient appliances and reduce water usage."],
        "what else?",
        "Besides using energy-efficient appliances and reducing water usage, what are other ways to reduce my carbon footprint at home?"
    ),
    (
        "Vague 'what does this mean'",
        ["User: What is ocean acidification?", "AI: It's the ongoing decrease in the pH of the Earth's oceans, caused by the uptake of carbon dioxide."],
        "what does this mean?",
        "What are the consequences of the ongoing decrease in the pH of the Earth's oceans due to carbon dioxide uptake?"
    ),
    (
        "Vague 'something else'",
        ["User: Tell me about solar power.", "AI: Solar power involves converting sunlight into electricity."],
        "can you look up something else",
        "Can you provide information on a different topic related to climate change other than solar power?"
    ),
    (
        "Vague 'why'",
        ["User: Deforestation is a major contributor to climate change.", "AI: Yes, it accounts for a significant portion of greenhouse gas emissions."],
        "why?",
        "Why does deforestation account for a significant portion of greenhouse gas emissions?"
    ),
    (
        "Vague 'how'",
        ["User: We need to transition to renewable energy.", "AI: This transition is crucial for mitigating climate change."],
        "how?",
        "How can we effectively transition to renewable energy to mitigate climate change?"
    ),
    (
        "Vague 'explain more'",
        ["User: What are carbon offsets?", "AI: They are credits for reductions in greenhouse gas emissions made at another location."],
        "explain more",
        "Can you explain in more detail how carbon offsets work as credits for greenhouse gas emission reductions?"
    ),
    (
        "Vague 'and then'",
        ["User: So, melting glaciers cause sea levels to rise.", "AI: Correct, that is the primary mechanism."],
        "and then?",
        "What happens after sea levels rise due to melting glaciers?"
    ),
    (
        "Vague 'like what'",
        ["User: There are many things individuals can do.", "AI: Yes, small changes in daily habits can have a large collective impact."],
        "like what?",
        "What are some examples of small changes in daily habits that individuals can make to have a collective impact on climate change?"
    ),
    (
        "Vague 'tell me about that'",
        ["User: The Kyoto Protocol was an international treaty.", "AI: It committed state parties to reduce greenhouse gas emissions."],
        "tell me about that",
        "Can you tell me more about the Kyoto Protocol and its commitment to reducing greenhouse gas emissions?"
    ),
    (
        "Vague 'go on'",
        ["User: Climate change affects biodiversity.", "AI: It leads to habitat loss for many species."],
        "go on",
        "Besides habitat loss, what are the other ways that climate change affects biodiversity?"
    ),
]

# --- Test Cases for Off-Topic Rejection (Should Not Rewrite) ---
off_topic_rejection_cases = [
    (
        "Off-topic: Sports",
        ["User: What is climate change?", "AI: A change in weather patterns."],
        "Who won the game last night?",
    ),
    (
        "Off-topic: Cooking",
        ["User: Tell me about renewable energy.", "AI: It comes from sources like sun and wind."],
        "How do I bake a cake?",
    ),
    (
        "Off-topic: Celebrity Gossip",
        ["User: What is a carbon tax?", "AI: It's a fee on carbon emissions."],
        "What's the latest news about that actor?",
    ),
    (
        "Off-topic: Personal Advice",
        ["User: How can I help the environment?", "AI: By recycling and reducing waste."],
        "Should I change my job?",
    ),
    (
        "Off-topic: Tech Support",
        ["User: What is geothermal energy?", "AI: It's heat from the Earth."],
        "My computer is running slow, can you help?",
    ),
]

# --- Test Cases for Long Conversation History ---
long_history_cases = [
    (
        "Long History: Summarization",
        ["User: A", "AI: B"] * 20,
        "So what's the main point?",
        "Given the long preceding discussion, what is the main point of our conversation about climate change?"
    ),
    (
        "Long History: Specific Detail Recall",
        ["User: My main concern is water scarcity in Arizona.", "AI: Arizona is implementing several water conservation programs."] + ["User: A", "AI: B"] * 15,
        "What were those programs in my state again?",
        "Referring back to our earlier discussion, what were the specific water conservation programs being implemented in Arizona?"
    ),
    (
        "Long History: Topic Shift",
        ["User: Let's talk about electric vehicles.", "AI: They are a key part of reducing transport emissions."] * 10,
        "Okay, now I want to know about agriculture.",
        "Shifting topics from electric vehicles, what is the impact of climate change on agriculture?"
    ),
    (
        "Long History: Contradiction Check",
        ["User: You said solar is the most efficient.", "AI: Yes, in many regions it is."] + ["User: A", "AI: B"] * 10 + ["User: But what about wind?", "AI: Wind is also highly efficient."],
        "Which one is it?",
        "Earlier you stated solar power is the most efficient, but later said wind is also highly efficient. Can you clarify which renewable energy source is more efficient?"
    ),
    (
        "Long History: Synthesis",
        ["User: Tell me about carbon tax.", "AI: It's a policy tool."] + ["User: Tell me about cap and trade.", "AI: It's another policy tool."] * 5,
        "How do they compare?",
        "Based on our discussion of both carbon tax and cap and trade, how do these two policy tools compare for reducing emissions?"
    ),
]

# --- 10 New Multilingual Test Cases ---
multilingual_rewriting_cases = [
    (
        "Spanish Rewrite",
        ["Usuario: ¿Cómo puedo reducir mi huella de carbono en casa?", "AI: Puede usar electrodomésticos de bajo consumo y reducir el uso de agua."],
        "¿qué más?",
        "Besides using energy-efficient appliances and reducing water usage, what are other ways to reduce my carbon footprint at home?"
    ),
    (
        "Arabic Rewrite",
        ["المستخدم: ما هو تحمض المحيطات؟", "الذكاء الاصطناعي: هو النقصان المستمر في درجة حموضة محيطات الأرض، بسبب امتصاص ثاني أكسيد الكربون."],
        "ماذا يعني هذا؟",
        "What are the consequences of the ongoing decrease in the pH of the Earth's oceans due to carbon dioxide uptake?"
    ),
    (
        "Chinese Rewrite",
        ["用户: 森林砍伐是气候变化的一个主要因素。", "AI: 是的，它占了温室气体排放的很大一部分。"],
        "为什么？",
        "Why does deforestation account for a significant portion of greenhouse gas emissions?"
    ),
    (
        "Hindi Rewrite",
        ["उपयोगकर्ता: हमें नवीकरणीय ऊर्जा पर स्विच करने की आवश्यकता है।", "एआई: जलवायु परिवर्तन को कम करने के लिए यह संक्रमण महत्वपूर्ण है।"],
        "कैसे?",
        "How can we effectively transition to renewable energy to mitigate climate change?"
    ),
    (
        "Tagalog Rewrite",
        ["Gumagamit: Ano ang mga carbon offset?", "AI: Ang mga ito ay mga kredito para sa pagbabawas sa mga greenhouse gas emission na ginawa sa ibang lokasyon."],
        "ipaliwanag pa",
        "Can you explain in more detail how carbon offsets work as credits for greenhouse gas emission reductions?"
    ),
    (
        "Russian Rewrite",
        ["Пользователь: Расскажите мне о Киотском протоколе.", "AI: Это было международное соглашение, которое обязывало государства-участники сократить выбросы парниковых газов."],
        "расскажи мне об этом",
        "Can you tell me more about the Kyoto Protocol and its commitment to reducing greenhouse gas emissions?"
    ),
    (
        "French Rewrite",
        ["Utilisateur: Le changement climatique affecte la biodiversité.", "AI: Il entraîne une perte d'habitat pour de nombreuses espèces."],
        "continuez",
        "Besides habitat loss, what are the other ways that climate change affects biodiversity?"
    ),
    (
        "Urdu Rewrite",
        ["صارف: کیا افراد کچھ کر سکتے ہیں؟", "AI: ہاں، روزمرہ کی عادات میں چھوٹی تبدیلیاں بڑا اجتماعی اثر ڈال سکتی ہیں۔"],
        "مثال کے طور پر؟",
        "What are some examples of small changes in daily habits that individuals can make to have a collective impact on climate change?"
    ),
    (
        "Spanish Long History Rewrite",
        ["Usuario: Mi principal preocupación es la escasez de agua en Arizona.", "AI: Arizona está implementando varios programas de conservación de agua."] + ["Usuario: A", "AI: B"] * 5,
        "¿Cuáles eran esos programas en mi estado de nuevo?",
        "Referring back to our earlier discussion, what were the specific water conservation programs being implemented in Arizona?"
    ),
    (
        "French Long History Rewrite",
        ["Utilisateur: Vous avez dit que le solaire est le plus efficace.", "AI: Oui, dans de nombreuses régions, c'est le cas."] + ["Utilisateur: A", "AI: B"] * 5,
        "Lequel est-ce?",
        "Earlier you stated solar power is the most efficient, can you clarify?"
    ),
]


@pytest.mark.parametrize("test_name, history, query, expected_rewrite", vague_follow_up_cases + long_history_cases + multilingual_rewriting_cases)
@pytest.mark.asyncio
async def test_on_topic_rewriting(test_name, history, query, expected_rewrite):
    """Tests that on-topic queries return JSON with the correct rewrite in rewrite_en."""
    model_response = _make_model_json_response(
        classification="on-topic",
        rewrite_en=expected_rewrite,
        reason="Follow-up question",
    )
    mock_model = _mock_model(model_response)

    result_str = await query_rewriter(
        conversation_history=history,
        user_query=query,
        nova_model=mock_model,
        selected_language_code="en",
    )

    result = json.loads(result_str)
    assert result["classification"] == "on-topic", f"Failed: {test_name}"
    assert result["rewrite_en"] == expected_rewrite, f"Rewrite mismatch: {test_name}"
    mock_model.content_generation.assert_called_once()


@pytest.mark.parametrize("test_name, history, query", off_topic_rejection_cases)
@pytest.mark.asyncio
async def test_off_topic_rejection(test_name, history, query):
    """Tests that off-topic queries are classified as off-topic with a canned response."""
    model_response = _make_model_json_response(
        classification="off-topic",
        reason="Unrelated topic",
    )
    mock_model = _mock_model(model_response)

    result_str = await query_rewriter(
        conversation_history=history,
        user_query=query,
        nova_model=mock_model,
        selected_language_code="en",
    )

    result = json.loads(result_str)
    assert result["classification"] == "off-topic", f"Failed: {test_name}"
    assert result["rewrite_en"] is None
    assert result["canned"]["enabled"] is True
    assert result["canned"]["type"] == "off-topic"
    mock_model.content_generation.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
