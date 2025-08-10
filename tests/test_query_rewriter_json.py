import asyncio
import json
import re
import sys
import os
import types

# Light-weight injection to satisfy import without heavy deps
module_nova_flow = types.ModuleType("src.models.nova_flow")
class BedrockModel: pass
module_nova_flow.BedrockModel = BedrockModel
sys.modules["src.models.nova_flow"] = module_nova_flow

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.models.query_rewriter import query_rewriter


class LLMStub:
    def __init__(self, behavior: str = "ok"):
        self.behavior = behavior

    async def content_generation(self, prompt: str, system_message: str) -> str:
        if self.behavior == "timeout":
            await asyncio.sleep(0.1)
            raise asyncio.TimeoutError()

        # Extract the current user query
        m = re.search(r'User Query:\s*"(.*?)"', prompt, re.DOTALL)
        query = (m.group(1) if m else "").lower().strip()

        # Simple intent mapping to JSON (model-style)
        def has_word(q: str, *terms: str) -> bool:
            return any(re.search(rf'(?:^|\W){re.escape(t)}(?:$|\W)', q) for t in terms)
        if query in {"", " ", "\t"}:
            return json.dumps({
                "reason": "empty",
                "language": "unknown",
                "expected_language": "en",
                "language_match": True,
                "classification": "off-topic",
                "rewrite_en": None,
                "ask_how_to_use": False,
                "how_it_works": None,
                "error": None
            })

        if query in {"?", "!!!", "...", "---"}:
            return json.dumps({
                "reason": "symbols only",
                "language": "unknown",
                "expected_language": "en",
                "language_match": True,
                "classification": "off-topic",
                "rewrite_en": None,
                "ask_how_to_use": False,
                "how_it_works": None,
                "error": None
            })

        if has_word(query, "hello", "hi", "hiya", "hey"):
            cls = "greeting"
        elif has_word(query, "bye", "goodbye"):
            cls = "goodbye"
        elif has_word(query, "thanks") or "thank you" in query:
            cls = "thanks"
        elif has_word(query, "emergency", "urgent") or "911" in query:
            cls = "emergency"
        elif (
            ("how to" in query and "use" in query)
            or "how does this work" in query
            or "help using" in query
            or "how to use" in query
        ):
            cls = "instruction"
        elif any(k in query for k in ["climate", "carbon", "emissions", "adaptation", "renewable"]):
            cls = "on-topic"
        else:
            cls = "off-topic"

        return json.dumps({
            "reason": "ok",
            "language": "en",
            "expected_language": "en",
            "language_match": True,
            "classification": cls,
            "rewrite_en": "What are local climate impacts?" if cls == "on-topic" else None,
            "ask_how_to_use": cls == "instruction",
            "how_it_works": None,
            "error": None
        })


async def run_case(query: str, expect_cls: str, expect_rewrite: bool = False):
    out = await query_rewriter([], query, LLMStub(), selected_language_code="en")
    data = json.loads(out)
    assert data["classification"] == expect_cls
    if expect_cls in {"greeting", "goodbye", "thanks", "emergency"}:
        assert data["canned"]["enabled"] is True
        assert data["canned"]["type"] == expect_cls
        assert isinstance(data["canned"]["text"], str) and len(data["canned"]["text"]) > 0
    else:
        assert data["canned"]["enabled"] is False
    if expect_rewrite:
        assert isinstance(data["rewrite_en"], str) and len(data["rewrite_en"]) > 0
    else:
        assert data["rewrite_en"] is None


async def main():
    # empty/whitespace
    print("- empty/whitespace input")
    out = await query_rewriter([], "   ", LLMStub(), "en")
    print(out)

    # symbol-only
    print("- symbol-only input")
    out = await query_rewriter([], "!!!", LLMStub(), "en")
    print(out)

    # on-topic rewrite
    print("- on-topic rewrite")
    await run_case("climate adaptation in cities", "on-topic", expect_rewrite=True)

    # canned classes
    print("- canned greeting")
    await run_case("hey", "greeting")
    print("- canned goodbye")
    await run_case("goodbye", "goodbye")
    print("- canned thanks")
    await run_case("thanks", "thanks")
    print("- canned emergency")
    await run_case("emergency 911", "emergency")

    # instruction
    print("- instruction")
    out = await query_rewriter([], "how to use this chatbot?", LLMStub(), "en")
    print(out)
    data = json.loads(out)
    assert data["classification"] == "instruction"
    assert data["ask_how_to_use"] is True
    assert isinstance(data["how_it_works"], str) and len(data["how_it_works"]) > 10

    # timeout path
    print("- timeout path")
    out = await query_rewriter([], "anything", LLMStub("timeout"), "en")
    data = json.loads(out)
    assert data["error"]["message"].startswith("Sorry, we are having technical difficulties")
    print("All JSON tests passed ✔")


if __name__ == "__main__":
    asyncio.run(main())


