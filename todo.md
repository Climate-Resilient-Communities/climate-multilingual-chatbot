## RAG Citations Improvement Plan (Human-in-the-Loop)

Scope: Improve retrieval quality and the citations shown to users in the Streamlit app.

Key code locations:
- `src/models/retrieval.py` — hybrid search (Pinecone + BGE-M3), processing, reranking hook
- `src/models/rerank.py` — Cohere reranker and returned relevance scores
- `src/models/gen_response_unified.py` — document preprocessing and final citations assembly
- `src/models/climate_pipeline.py` — end-to-end flow, faithfulness checks, outputs

Dependencies in use:
- Pinecone client: declared as `pinecone-client = ^5.0.1` (poetry) and `pinecone>=3.0.0` (requirements). Code imports `from pinecone import Pinecone` and calls `index.query(vector=..., sparse_vector=..., top_k=..., include_metadata=True)`.
- Embeddings: BGE-M3 via `FlagEmbedding`.
- Reranker: Cohere `rerank-english-v3.0`.

---

### Checklist (we will mark items complete only after you validate each step)

- [x] 1) Understand how Pinecone vector store works (version & behavior)
  - Deliverables:
    - Confirm client/version semantics we rely on (modern `pinecone` SDK, hybrid query, scoring semantics, metadata usage). See `pinecone.md`.
    - Document index fields we depend on: `chunk_text`, `title`, `url`, `section_title`, `segment_id`, keywords.
    - Note ordering and range of returned `score`; confirm higher-is-better and whether it’s similarity vs. distance.
    - Identify any namespace, filter, or consistency settings relevant to our index.
  - Code refs: `climate_pipeline._initialize_pinecone_index`, `retrieval.issue_hybrid_query`.

- [x] 2) Inspect retriever scoring and thresholds
  - Deliverables:
    - Verify `top_k` values throughout (hybrid search `top_k`, rerank `top_n`, final cap to 5 docs).
    - Confirm rerank result uses `relevance_score`; propagate both Pinecone score and rerank score to diagnostics.
    - Propose a default cutoff (e.g., drop docs below rerank score threshold and/or Pinecone score percentile).
  - Code refs: `retrieval.get_documents`, `rerank.rerank_fcn`.

- [ ] 3) Assess retriever quality (are we pulling good information?)
  - Deliverables:
    - Add optional debug/log export of retrieved docs, scores, and chosen subset per query. (Added app-path JSONL export at `logs/retrieval_app_debug.jsonl`.)
    - Propose a small evaluation harness (can use `ragas`) with representative queries to measure context precision/recall and faithfulness.
    - Identify quick wins: better alpha for hybrid weighting, better pre-clean of content, dedupe rules.
  - Code refs: `retrieval.get_query_embeddings`, `retrieval.clean_markdown_content`, `retrieval.process_search_results`.

- [x] 4) Decide which citations to show
  - Deliverables:
    - Policy for displaying only “high-confidence” citations: limit to N, drop those without URL or with very low relevance.
    - Deduplicate by URL/domain/title; prefer canonical titles; keep only one per source unless strongly justified.
    - Wire relevance/rerank scores into `citations` 
  - Code refs: `gen_response_unified._process_and_generate` (citations assembly), `retrieval.process_search_results`.

- [x] 5) No proper RAG documents / Tavily fallback
  - Deliverables:
    - Define behavior when Pinecone returns nothing (and/or Tavily is used): show “No sources for this answer” instead of placeholder citations.
    - Ensure synthetic “Conversation Context” docs are never surfaced as citations.
  - Code refs: `gen_response_unified._doc_preprocessing` (conversation fallback), citations filtering logic.

- [x] 6) Detect and handle empty/low-content hits
  - Deliverables:
    - Tighten filters in `process_search_results` for empty `chunk_text`, too-short content after cleaning, and non-informative pages.
    - Log counts of dropped docs and reasons (observability for quality).
  - Code refs: `retrieval.process_search_results` (already skips missing/short content; propose clearer thresholds & reasons).

- [ ] 7) Clean citation naming
  - Deliverables:
    - Add a title normalizer: strip extensions/hashy prefixes like `1-s2.0-...`, replace underscores, title-case, fall back to domain if needed.
    - Prefer `section_title` when helpful; otherwise derive a short, human-friendly title from URL path.
    - if the Url shows google drive, think about what we can show better for this 
    - Ensure UI truncation preserves meaning (first N chars with ellipsis) and retains tooltip with full title.
  - Code refs: `retrieval.process_search_results` (title comes from metadata), `gen_response_unified` (final assembly).

---

### Working Notes / Decisions Log

- We’ll proceed item-by-item. After your approval of each item’s deliverable, we will mark it as complete here and open PR-ready edits where changes are needed.
- Current `top_k` path observed:
  - Pinecone hybrid `top_k` (configurable) → processed → capped to ≤10 before rerank → Cohere rerank `top_n = min(top_k, 5)` → final cap to ≤5.
- Synthetic “Conversation Context” is currently excluded from citations when `url` is empty; we will keep enforcing this and harden edge cases.

---

### Next Action (awaiting your go-ahead)

Start with item 1: verify Pinecone client/version semantics and document scoring/metadata assumptions we rely on. Then propose any retriever parameter tweaks (e.g., alpha, top_k) based on the docs and our usage.


