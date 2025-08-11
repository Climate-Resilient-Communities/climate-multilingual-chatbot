#!/usr/bin/env python3
import os, json, uuid
from time import perf_counter
from statistics import median
import asyncio
from typing import List, Dict, Any

# Ensure src on path
import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from src.models.climate_pipeline import ClimateQueryPipeline
from src.models.retrieval import get_documents

def approx_tokens(text: str) -> int:
    if not isinstance(text, str):
        return 1
    return max(1, len(text)//4)

class StageTimer:
    def __init__(self, name: str, meta: Dict[str, Any]):
        self.name, self.meta = name, meta
    def __enter__(self):
        self.t0 = perf_counter(); return self
    def __exit__(self, *exc):
        self.meta[f"{self.name}_latency_ms"] = int((perf_counter()-self.t0)*1000)

def p(values: List[int], q: int):
    s = sorted(values)
    if not s: return None
    idx = max(0, int(len(s)*q/100)-1)
    return s[idx]

async def retrieve_only(pipeline: ClimateQueryPipeline, query: str, k: int) -> List[Dict[str, Any]]:
    index = pipeline.index
    embed = pipeline.embed_model
    # get_documents internally performs retrieval and rerank with proper async handling
    docs = await get_documents(query, index=index, embed_model=embed, cohere_client=pipeline.cohere_client, alpha=0.5, top_k=k)
    return docs

async def generate_only(pipeline: ClimateQueryPipeline, query: str, docs: List[Dict[str, Any]], model_type: str) -> str:
    response, _ = await pipeline.response_generator.generate_response(
        query=query,
        documents=docs,
        model_type=model_type,
        language_code="en",
        description=None,
        conversation_history=None,
    )
    return response

async def run_once(pipeline: ClimateQueryPipeline, query: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    m: Dict[str, Any] = {"request_id": str(uuid.uuid4()), "query_hash": hash(query)}
    t0 = perf_counter()

    # Retrieve (includes internal rerank)
    with StageTimer("retrieve", m):
        docs = await retrieve_only(pipeline, query, k=cfg.get("k", 16)) if cfg.get("k", 0) else []
    m["k_requested"] = cfg.get("k", 0)
    m["k_returned"] = len(docs)
    doc_tokens = [approx_tokens(d.get("content", d.get("chunk_text", ""))) for d in docs]
    m["avg_doc_tokens"] = int(sum(doc_tokens)/max(1,len(doc_tokens))) if docs else 0
    m["sum_doc_tokens"] = int(sum(doc_tokens))

    # Optionally slice to top_n for the LLM stage
    top_n = cfg.get("top_n", 0)
    use_docs = docs[:top_n] if (docs and top_n) else []
    context = "\n\n".join((d.get("content") or d.get("chunk_text") or "") for d in use_docs)
    m["input_tokens"] = approx_tokens(context)

    # LLM stage (skip if no docs)
    if use_docs:
        with StageTimer("llm", m):
            _ = await generate_only(pipeline, query=query, docs=use_docs, model_type=cfg.get("model", "nova"))
    else:
        m["llm_latency_ms"] = 0

    m["llm_model_name"] = cfg.get("model", "nova")
    m["ttlb_ms"] = int((perf_counter() - t0)*1000)
    return m

async def run_batch(queries: List[str], cfg: Dict[str, Any], out_path: str):
    results = []
    for q in queries:
        r = await run_once(cfg["pipeline"], q, cfg)
        results.append(r)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    def col(c): return [r[c] for r in results if c in r]
    summary = {
        "n": len(results),
        "p95_ttlb_ms": p(col("ttlb_ms"), 95),
        "p95_retrieve_ms": p(col("retrieve_latency_ms"), 95),
        "p95_rerank_ms": p(col("rerank_latency_ms"), 95),  # internal rerank not separated here
        "p95_llm_ms": p(col("llm_latency_ms"), 95),
        "avg_input_tokens": int(sum(col("input_tokens"))/len(col("input_tokens"))) if col("input_tokens") else 0,
        "k": cfg.get("k"),
        "use_rerank": cfg.get("use_rerank"),
        "top_n": cfg.get("top_n"),
        "model": cfg.get("model"),
    }
    return results, summary

async def main():
    pipeline = ClimateQueryPipeline(index_name="climate-change-adaptation-index-10-24-prod")
    golden_queries = [
        "What are the local impacts of climate change in Toronto?",
        "How can I prepare my home for flooding?",
        "What causes heat waves and how can I stay safe?",
        "How does climate change affect air quality?",
        "What are adaptation strategies for coastal flooding?",
        "How does climate change impact public health?",
        "What can communities do to increase resilience?",
        "How is wildfire smoke related to climate change?",
        "What is climate mitigation vs adaptation?",
        "What is a reasonable home energy retrofit for heat savings?",
    ]

    configs = [
        {"name":"baseline",     "k":32, "use_rerank":True,  "top_n":8,  "model":"nova", "pipeline": pipeline},
        {"name":"no_rerank",    "k":16, "use_rerank":False, "top_n":0,  "model":"nova", "pipeline": pipeline},
        {"name":"rerank_k64_n8","k":64, "use_rerank":True,  "top_n":8,  "model":"nova", "pipeline": pipeline},
        {"name":"rerank_k16_n8","k":16, "use_rerank":True,  "top_n":8,  "model":"nova", "pipeline": pipeline},
    ]

    os.makedirs(os.path.join(ROOT, "tests", "P95", "out"), exist_ok=True)

    for cfg in configs:
        out_path = os.path.join(ROOT, "tests", "P95", "out", f"{cfg['name']}.jsonl")
        rows, summary = await run_batch(golden_queries, cfg, out_path)
        print(cfg["name"], summary)

    await pipeline.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
