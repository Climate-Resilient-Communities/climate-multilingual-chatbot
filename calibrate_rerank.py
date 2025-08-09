#!/usr/bin/env python3
"""
Calibrate Cohere rerank score thresholds by sampling typical queries.

Usage:
  poetry run python calibrate_rerank.py                # defaults to 0.35, 0.50, 0.60
  poetry run python calibrate_rerank.py 0.60 0.70 0.80 0.90
  CALIB_THRESHOLDS="0.6,0.7,0.8,0.9" poetry run python calibrate_rerank.py

Notes:
- This script disables in-code rerank thresholding during calibration to avoid bias from
  current RETRIEVAL_CONFIG. It still respects retrieval caps (e.g., top_k_rerank/final_max_docs).
- Uses existing retrieval stack (Pinecone + BGE-M3 + Cohere rerank).
"""

import os
import sys
import time
import asyncio
from statistics import mean
import re

from typing import List, Dict


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=".env", override=True)
    except Exception:
        pass


async def run_once(query: str):
    """Reuse our pipeline's initialization paths (no custom Pinecone wiring here)."""
    from src.data.config.config import RETRIEVAL_CONFIG
    from src.utils.env_loader import load_environment
    from src.models.retrieval import get_documents
    from src.models.climate_pipeline import ClimateQueryPipeline

    load_environment()

    # Initialize pipeline using the same code paths as the app
    index_name = os.getenv("PINECONE_INDEX", RETRIEVAL_CONFIG.get("pinecone_index", ""))

    # Disable filtering during calibration to collect raw rerank scores
    try:
        RETRIEVAL_CONFIG["min_rerank_score"] = 0.0
        RETRIEVAL_CONFIG["min_pinecone_score"] = 0.0
    except Exception:
        pass
    pipeline = ClimateQueryPipeline(index_name=index_name)

    docs = await get_documents(
        query=query,
        index=pipeline.index,
        embed_model=pipeline.embed_model,
        cohere_client=pipeline.cohere_client,
        alpha=RETRIEVAL_CONFIG.get("hybrid_alpha", 0.5),
        top_k=RETRIEVAL_CONFIG.get("top_k_retrieve", 8),
    )

    return docs


def summarize(scores: List[float]) -> Dict:
    if not scores:
        return {
            "count": 0,
            
        }
    return {
        "count": len(scores),
        "min": min(scores),
        "max": max(scores),
        "avg": mean(scores),
        "p50": sorted(scores)[len(scores)//2],
    }


async def main():
    load_env()

    sample_queries = [
        "What is climate change?",
        "How can I reduce my carbon footprint?",
        "Impact of climate change on flooding",
        "Are glaciers really melting?",
        "Heatwave adaptation tips for seniors",
        "Toronto climate action plan key points",
        "Wildfire smoke health effects and precautions",
        "Sea level rise projections for coastal cities",
        "Renewable energy options for homes",
    ]

    # Parse thresholds: CLI args or CALIB_THRESHOLDS env var, else default
    thresholds: List[float] = [0.35, 0.50, 0.60]
    env_line = os.getenv("CALIB_THRESHOLDS", "").strip()
    argv_vals = [a for a in sys.argv[1:] if a and not a.startswith("-")]
    try:
        if env_line:
            thresholds = [float(x) for x in re.split(r"[,\s]+", env_line) if x]
        elif argv_vals:
            thresholds = [float(x) for x in argv_vals]
    except Exception:
        pass

    # Normalize formatting and sort ascending for reporting
    thresholds = sorted({round(float(t), 2) for t in thresholds})
    print(f"Using thresholds: {', '.join(f'{t:.2f}' for t in thresholds)}")
    per_query_stats = []

    start = time.time()
    for q in sample_queries:
        t0 = time.time()
        try:
            docs = await run_once(q)
            rerank_scores = [float(d.get("score", 0.0)) for d in docs]
            row = {"query": q, "scores": rerank_scores}
            for th in thresholds:
                row[f">={th:.2f}"] = sum(1 for s in rerank_scores if s >= th)
            row["summary"] = summarize(rerank_scores)
            per_query_stats.append(row)
            print(f"\nQuery: {q}")
            print(f"Scores: {rerank_scores}")
            for th in thresholds:
                print(f"  >= {th:.2f}: {row[f'>={th:.2f}']}")
        except Exception as e:
            print(f"\nQuery failed: {q}: {e}")
        finally:
            print(f"  time: {time.time()-t0:.2f}s")

    # Aggregate
    print("\n=== Aggregate ===")
    totals = {f">={th:.2f}": 0 for th in thresholds}
    queries_with_at_least = {f">={th:.2f}": 0 for th in thresholds}

    for row in per_query_stats:
        scores = row["scores"]
        for th in thresholds:
            key = f">={th:.2f}"
            totals[key] += row[key]
            if row[key] >= 3:  # at least 3 useful citations
                queries_with_at_least[key] += 1

    n = len(per_query_stats)
    for th in thresholds:
        key = f">={th:.2f}"
        avg_docs = totals[key] / n if n else 0
        pct_queries = (queries_with_at_least[key] / n * 100) if n else 0
        print(f"Threshold {th:.2f}: avg docs retained = {avg_docs:.2f}, queries with >=3 docs = {pct_queries:.0f}%")

    print(f"\nTotal time: {time.time()-start:.2f}s for {n} queries")

    # Recommendation heuristic (generalized): choose the highest threshold
    # that still keeps >=60% of queries with at least 3 docs; fallback to min.
    rec = None
    for th in sorted(thresholds, reverse=True):
        key = f">={th:.2f}"
        if queries_with_at_least.get(key, 0) >= 0.6 * n:
            rec = th
            break
    if rec is None:
        rec = min(thresholds)
    print(f"\nRecommended rerank threshold: {rec:.2f}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)

