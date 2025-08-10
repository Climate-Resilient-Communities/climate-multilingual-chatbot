## Pinecone Notes (for RAG and Citations)

These are working notes on how we use Pinecone today and what to verify/tune as we improve RAG citation quality.

### Client and Version
- Current declarations:
  - `pyproject.toml`: `pinecone-client = ^5.0.1`
  - `requirements.txt`: `pinecone>=3.0.0  # Updated from pinecone-client to pinecone per official recommendation`
- Code imports: `from pinecone import Pinecone`; usage matches newer SDK (v3+ API): `pc = Pinecone(api_key=...); index = pc.Index(name)`.
- Recommendation: standardize on the newer `pinecone` package (not `pinecone-client`) in both dependency files to avoid API drift.

### Our Retrieval Flow (high‑level)
1) Embed query with BGE‑M3 (dense + sparse) via FlagEmbedding.
2) Hybrid query to Pinecone with weighted dense/sparse vectors.
3) Process matches (+ clean/dedupe) and forward to Cohere reranker.
4) Keep top few docs (≤5) for generation and citations.

Key call sites:

```100:112:src/models/retrieval.py
def issue_hybrid_query(index, sparse_embedding: Dict, dense_embedding: List[float], 
                      alpha: float, top_k: int):
    scaled_sparse, scaled_dense = weight_by_alpha(sparse_embedding, dense_embedding, alpha)
    result = index.query(
        vector=scaled_dense,
        sparse_vector=scaled_sparse,
        top_k=top_k,
        include_metadata=True
    )
    return result
```

```231:264:src/models/retrieval.py
for match in search_results.matches:
    title = match.metadata.get('title', 'No Title')
    content = match.metadata.get('chunk_text', '')
    # ... content cleaning, length checks ...
    doc = {
        'title': title,
        'content': content,
        'score': float(match.score),
        'section_title': match.metadata.get('section_title', '').strip(),
        'segment_id': match.metadata.get('segment_id', ''),
        'doc_keywords': match.metadata.get('doc_keywords', []),
        'segment_keywords': match.metadata.get('segment_keywords', []),
        'url': match.metadata.get('url', [])
    }
```

### Current Parameters (defaults in code)
- Hybrid weight `alpha`: default 0.5 (equal weight dense/sparse) in `get_documents`.
- `top_k` from Pinecone: default 8; capped to ≤10 before rerank.
- Rerank with Cohere `rerank-english-v3.0`, `top_n = min(top_k, 5)`; final doc cap ≤5.

### Index Schema Assumptions
We expect the following metadata in each vector record:
- `chunk_text` (string): main text chunk used as context.
- `title` (string): human‑readable document title.
- `url` (string or list[str]): canonical source URL (citations prefer this).
- `section_title` (string), `segment_id` (string), `doc_keywords`/`segment_keywords` (lists): optional enrichments.

If any of the above is missing or `chunk_text` is too short (< ~10 chars post‑cleaning), the match is dropped.

### Scoring and Ordering
- Pinecone returns a `score` per match. Interpretation depends on index metric:
  - Cosine / dot‑product: similarity (higher is better)
  - Euclidean: distance (lower is better)
- Our code treats higher as better; confirm index metric is cosine or dot‑product.
- Cohere reranker returns `relevance_score` (0–1). We currently overwrite doc `score` with rerank score and keep top N.

### What To Verify
- Index metric (cosine vs dot‑product) and whether `score` is comparable across queries.
- Namespace/language partitioning (if any). Might consider per‑language namespace or metadata filter if needed.
- Whether filters (e.g., `filter={"type": "pdf"}`) would help remove noisy sources at query time.

Suggested quick check (v3+ SDK):

```python
from pinecone import Pinecone
import os

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
name = os.environ.get("PINECONE_INDEX", "climate-chatbot-index")

print(pc.list_indexes())
try:
    print(pc.describe_index(name))
except Exception as e:
    print("describe_index failed:", e)

idx = pc.Index(name)
try:
    print(idx.describe_index_stats())
except Exception as e:
    print("describe_index_stats failed:", e)
```

If `describe_index` reports `metric: "cosine"`, our scoring assumption is valid.

### Suggested Improvements (for later tasks)
- Thresholding: Drop matches below a rerank score cutoff (e.g., <0.35–0.45) and/or Pinecone score percentile.
- Dedupe by normalized URL host/path and by cleaned title; keep the best‐scored segment per source.
- Title normalization: strip hashes/IDs, replace underscores, title‑case; fallback to domain+path segment if missing.
- Adaptive `alpha`: consider more sparse weight for keyword‑like queries; more dense for semantic/long queries.
- Diagnostics: Log a compact table per query (pinecone score, rerank score, title/url, retained/dropped reason).
- Retrieval safeguards: if no valid RAG docs after filtering, do not show citations; clearly state “No sources available for this answer.”

### Minimal Usage Snippet (reference)

```python
from pinecone import Pinecone

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("<index-name>")
res = index.query(
    vector=dense,               # list[float]
    sparse_vector={             # {indices: [...], values: [...]} from BGE-M3 lexical weights
        "indices": indices,
        "values": values,
    },
    top_k=8,
    include_metadata=True,
    # filter={"lang": "en"},   # optional
)
for m in res.matches:
    print(m.id, m.score, m.metadata.get("title"))
```

### Open Questions / TODOs
- Confirm index metric and typical score ranges; tune cutoffs accordingly.
- Decide on final `alpha`, `top_k` defaults per latency/quality target.
- Confirm all ingesters upsert the metadata fields we rely on (`chunk_text`, `title`, `url`).

### Action Items
1) Unify dependency to `pinecone>=3.x` in both Poetry and requirements, re‑lock.
2) Startup: log index metric once to validate scoring assumption.
3) Consider metadata filters (language/doc_type) to cut noise.
4) Log both Pinecone score and rerank score for retained citations (observability).


