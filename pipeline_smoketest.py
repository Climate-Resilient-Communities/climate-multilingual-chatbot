#!/usr/bin/env python3
"""
Pipeline smoketest: run several representative queries through the app retrieval path
using the same components (Pinecone index, BGE-M3 embeddings, Cohere reranker).
Print final counts and top titles for quick inspection.
"""
import asyncio
import time
from typing import List

from src.utils.env_loader import load_environment
from src.data.config.config import RETRIEVAL_CONFIG
from src.models.climate_pipeline import ClimateQueryPipeline
from src.models.retrieval import get_documents


QUERIES: List[str] = [
    "EV charging at home: safety and cost tips",
    "Public transit vs car emissions comparison",
    "What is a heat dome and how to stay safe?",
    "What is climate change?",
]


async def main():
    load_environment()

    # Initialize pipeline (reuses app setup)
    index_name = RETRIEVAL_CONFIG.get("pinecone_index")
    pipeline = ClimateQueryPipeline(index_name=index_name)

    index = pipeline.index
    embed_model = pipeline.embed_model
    cohere_client = pipeline.cohere_client

    alpha = float(RETRIEVAL_CONFIG.get("hybrid_alpha", 0.5))

    for q in QUERIES:
        print(f"\n=== Query: {q} ===")
        t0 = time.time()
        docs = await get_documents(q, index, embed_model, cohere_client, alpha=alpha, top_k=int(RETRIEVAL_CONFIG.get("top_k_rerank", 5)))
        dt = time.time() - t0
        print(f"Final docs: {len(docs)} in {dt:.2f}s")
        for i, d in enumerate(docs[:5], 1):
            title = (d.get("title", "") or "")[:120]
            score = float(d.get("score", 0.0))
            print(f"  {i}. {title}  (rerank={score:.3f})")


if __name__ == "__main__":
    asyncio.run(main())


