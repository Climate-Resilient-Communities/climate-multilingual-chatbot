#!/usr/bin/env python3
import asyncio
import json
from src.models.query_rewriter import query_rewriter
from src.models.nova_flow import BedrockModel
from src.models.conversation_parser import conversation_parser

async def main() -> None:
    model = BedrockModel()
    try:
        messages = [
            {"role": "user", "content": "hi how are you"},
            {"role": "assistant", "content": "Hello! I can help with climate questions. How can I help?"},
            {"role": "user", "content": "What is climate change?"},
            {"role": "assistant", "content": "Climate change refers to long-term shifts in temperature and weather patterns, mainly due to human activities."},
            {"role": "user", "content": "How is it effective?"},
        ]
        history = conversation_parser.format_for_query_rewriter(messages)

        for q in ("are you sure?", "tell me what it does"):
            raw = await query_rewriter(
                conversation_history=history,
                user_query=q,
                nova_model=model,
                selected_language_code="en",
            )
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw}
            print("\nCASE:", q)
            print(json.dumps(data, ensure_ascii=False, indent=2))
            print("rewrite_en:", data.get("rewrite_en"))
    finally:
        await model.close()

if __name__ == "__main__":
    asyncio.run(main())
