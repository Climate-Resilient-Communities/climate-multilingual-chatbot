#!/usr/bin/env python3
import asyncio
from src.models.climate_pipeline import ClimateQueryPipeline

async def main():
    pipe = ClimateQueryPipeline()
    try:
        # Case 1: Off-topic English query should return gentle guidance and not proceed
        res1 = await pipe.process_query(
            query="do ufos visit earth? explain please",
            language_name="english",
            conversation_history=[],
        )
        print("CASE 1: off-topic (ufos)")
        print(" success:", res1.get("success"))
        print(" response:", (res1.get("response") or "")[:220])

        # Case 2: Spanish selected + English query should return Whoops message
        res2 = await pipe.process_query(
            query="why is summer hotter now?",
            language_name="spanish",
            conversation_history=[],
        )
        print("\nCASE 2: mismatch (spanish selected, english query)")
        print(" success:", res2.get("success"))
        print(" response:", (res2.get("response") or "")[:220])

        # Case 3: Spanish selected + Spanish off-topic should return translated guidance
        res3 = await pipe.process_query(
            query="¿Existen los ovnis?",
            language_name="spanish",
            conversation_history=[],
        )
        print("\nCASE 3: off-topic in Spanish (should be translated guidance)")
        print(" success:", res3.get("success"))
        print(" response:", (res3.get("response") or "")[:220])
    finally:
        await pipe.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
