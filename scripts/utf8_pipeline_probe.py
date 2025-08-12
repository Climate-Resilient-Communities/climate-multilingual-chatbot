#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import locale
import os

from src.models.climate_pipeline import ClimateQueryPipeline


Q1 = "气候变化会如何影响加拿大的冬天"
Q2 = "气候/冬天/影响/加拿大"


def dbg(s: str) -> None:
    print("PY IN → str repr:", repr(s))
    print("PY IN → codepoints first 20:", [ord(c) for c in s[:20]])
    print("PY IN → len:", len(s))
    print(
        "stdout.encoding:", sys.stdout.encoding,
        "default:", sys.getdefaultencoding(),
        "locale:", locale.getpreferredencoding(False),
    )
    print("-")


async def main():
    os.environ.setdefault(
        "PIPELINE_LOG_FILE",
        os.path.join(os.getcwd(), "logs", "pipeline_debug.log"),
    )
    qp = ClimateQueryPipeline(index_name="climate-change-adaptation-index-10-24-prod")
    for q in [Q1, Q2]:
        dbg(q)
        res = await qp.process_query(query=q, language_name="chinese", conversation_history=[])
        print("Result success:", res.get("success"), "response:", (res.get("response") or "")[:200])


if __name__ == "__main__":
    asyncio.run(main())

















