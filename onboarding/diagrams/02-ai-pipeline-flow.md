# AI Pipeline Flow Diagram

This document details how user queries are processed through the AI pipeline.

---

## The RAG Pipeline (Retrieval-Augmented Generation)

```
═══════════════════════════════════════════════════════════════════════════════
                        CLIMATE QUERY PIPELINE FLOW
═══════════════════════════════════════════════════════════════════════════════

  USER QUERY: "How can I prepare my home for extreme heat in Toronto?"

═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  STEP 1: LANGUAGE ROUTING                                               │
    │  ═══════════════════════                                                │
    │                                                                          │
    │  File: src/models/query_routing.py                                      │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                    MultilingualRouter                               │ │
    │  │                                                                     │ │
    │  │   Input: "How can I prepare my home for extreme heat in Toronto?"  │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   ┌──────────────────────────────────────────────┐                 │ │
    │  │   │  Language Detection                          │                 │ │
    │  │   │  • Script analysis (Latin, CJK, Arabic...)   │                 │ │
    │  │   │  • Stopword matching                         │                 │ │
    │  │   │  • Result: "en" (English)                    │                 │ │
    │  │   └──────────────────────────────────────────────┘                 │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   ┌──────────────────────────────────────────────┐                 │ │
    │  │   │  Model Selection                             │                 │ │
    │  │   │  • English → Use AWS Bedrock Nova            │                 │ │
    │  │   │  • Nova: Fast, good for EN/ES/JA/DE/SV/DA    │                 │ │
    │  │   │  • Cohere: 22+ other languages               │                 │ │
    │  │   └──────────────────────────────────────────────┘                 │ │
    │  │                                                                     │ │
    │  │   Output: {language: "en", model: "nova", needs_translation: false}│ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Time: ~50ms                                                            │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  STEP 2: CACHE CHECK                                                    │
    │  ═══════════════════                                                    │
    │                                                                          │
    │  File: src/models/redis_cache.py                                        │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                      Redis Cache Lookup                             │ │
    │  │                                                                     │ │
    │  │   1. Normalize query                                                │ │
    │  │      "how can i prepare my home for extreme heat in toronto?"      │ │
    │  │                                                                     │ │
    │  │   2. Generate cache key                                             │ │
    │  │      q:en:7f3a2b1c... (SHA256 hash)                                │ │
    │  │                                                                     │ │
    │  │   3. Check Redis                                                    │ │
    │  │      ┌─────────────┐                                               │ │
    │  │      │   Redis     │ ──▶ Cache MISS → Continue to Step 3           │ │
    │  │      │   Cache     │ ──▶ Cache HIT  → Return cached response       │ │
    │  │      └─────────────┘                                               │ │
    │  │                                                                     │ │
    │  │   4. Fuzzy match (if exact miss)                                   │ │
    │  │      • Check similar queries (92% threshold)                       │ │
    │  │      • Same language only                                          │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Time: ~10ms (cache hit) or ~5ms (cache miss check)                    │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  STEP 3: QUERY CLASSIFICATION                                           │
    │  ═══════════════════════════════                                        │
    │                                                                          │
    │  File: src/models/query_rewriter.py                                     │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                     Query Rewriter (LLM Call)                       │ │
    │  │                                                                     │ │
    │  │   Input: Query + Conversation History                               │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   ┌──────────────────────────────────────────────────────────────┐ │ │
    │  │   │  AWS Bedrock Nova - Classification Prompt                    │ │ │
    │  │   │                                                              │ │ │
    │  │   │  "Classify this query into one of:                           │ │ │
    │  │   │   - on-topic (climate-related)                               │ │ │
    │  │   │   - off-topic (not climate-related)                          │ │ │
    │  │   │   - harmful (dangerous content)                              │ │ │
    │  │   │   - greeting, goodbye, thanks                                │ │ │
    │  │   │   - emergency, instruction"                                  │ │ │
    │  │   └──────────────────────────────────────────────────────────────┘ │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   Result: {"classification": "on-topic", "rewritten_query": "..."} │ │
    │  │                                                                     │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  Fast-Path Responses (no retrieval needed)                 │   │ │
    │  │   │  • greeting → "Hello! How can I help with climate info?"  │   │ │
    │  │   │  • goodbye  → "Goodbye! Stay informed about climate."     │   │ │
    │  │   │  • thanks   → "You're welcome!"                           │   │ │
    │  │   │  • off-topic→ "I can only help with climate topics."      │   │ │
    │  │   │  • harmful  → "I cannot help with that request."          │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Time: ~500ms                                                           │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼  (Only for "on-topic" queries)
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  STEP 4: DOCUMENT RETRIEVAL                                             │
    │  ═══════════════════════════                                            │
    │                                                                          │
    │  File: src/models/retrieval.py                                          │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                     BGE-M3 Embedding Model                          │ │
    │  │                                                                     │ │
    │  │   Query: "How can I prepare my home for extreme heat in Toronto?"  │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  Generate Embeddings                                       │   │ │
    │  │   │  • Dense vector (1024 dimensions) - semantic meaning       │   │ │
    │  │   │  • Sparse vector (BM25 weights) - keyword matching         │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                              │                                          │
    │                              ▼                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                     Pinecone Vector Search                          │ │
    │  │                                                                     │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  Hybrid Search (alpha=0.5)                                 │   │ │
    │  │   │  • 50% weight on semantic similarity (dense)               │   │ │
    │  │   │  • 50% weight on keyword matching (sparse)                 │   │ │
    │  │   │                                                            │   │ │
    │  │   │  Filters Applied:                                          │   │ │
    │  │   │  • Exclude K-12 educational content                        │   │ │
    │  │   │  • Boost Canadian government sources (+25%)                │   │ │
    │  │   │  • Boost Toronto-specific content                          │   │ │
    │  │   │                                                            │   │ │
    │  │   │  Returns: Top 15 documents                                 │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                              │                                          │
    │                              ▼                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                     Cohere Reranker                                 │ │
    │  │                                                                     │ │
    │  │   Input: Query + 15 documents                                       │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  rerank-english-v3.0 Model                                 │   │ │
    │  │   │  • Scores each document for relevance (0.0 - 1.0)          │   │ │
    │  │   │  • Filters: score >= 0.70                                  │   │ │
    │  │   │  • Output: Top 5 most relevant documents                   │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  │                                                                     │ │
    │  │   Result: 5 documents about extreme heat preparedness in Toronto   │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Time: ~800ms (embedding: 100ms, search: 200ms, rerank: 500ms)         │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  STEP 5: RESPONSE GENERATION                                            │
    │  ════════════════════════════                                           │
    │                                                                          │
    │  File: src/models/gen_response_unified.py, nova_flow.py                 │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                  Prompt Construction                                │ │
    │  │                                                                     │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  System Message (Climate Expert Persona)                   │   │ │
    │  │   │  "You are a supportive climate information assistant..."   │   │ │
    │  │   │  • Canadian/Toronto context                                │   │ │
    │  │   │  • Empathetic, inclusive communication                     │   │ │
    │  │   │  • Always cite sources                                     │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  │                              +                                      │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  Retrieved Documents (Context)                             │   │ │
    │  │   │  [Doc 1: "Heat Wave Preparation Guide - Toronto.ca"]       │   │ │
    │  │   │  [Doc 2: "Extreme Heat Resilience - Ontario.ca"]           │   │ │
    │  │   │  [Doc 3: "Cooling Centres in Toronto"]                     │   │ │
    │  │   │  ...                                                       │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  │                              +                                      │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  User Query                                                │   │ │
    │  │   │  "How can I prepare my home for extreme heat in Toronto?" │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                              │                                          │
    │                              ▼                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                     LLM Response Generation                         │ │
    │  │                                                                     │ │
    │  │   Model: AWS Bedrock Nova (amazon.nova-lite-v1:0)                  │ │
    │  │   Temperature: 0.7                                                  │ │
    │  │   Max Tokens: 2000                                                  │ │
    │  │                                                                     │ │
    │  │   Output: Response with inline citations                            │ │
    │  │   "To prepare your home for extreme heat in Toronto, consider:     │ │
    │  │    1. Install window coverings [Source: toronto.ca]                │ │
    │  │    2. Check your air conditioning [Source: ontario.ca]             │ │
    │  │    3. Know your nearest cooling centre [Source: toronto.ca]        │ │
    │  │    ..."                                                             │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Time: ~1500ms                                                          │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  STEP 6: HALLUCINATION GUARD                                            │
    │  ════════════════════════════                                           │
    │                                                                          │
    │  File: src/models/hallucination_guard.py                                │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                  Faithfulness Evaluation                            │ │
    │  │                                                                     │ │
    │  │   Input: Generated Response + Retrieved Documents                   │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  Nova LLM Evaluation                                       │   │ │
    │  │   │                                                            │   │ │
    │  │   │  Checks:                                                   │   │ │
    │  │   │  1. Are all factual claims supported by context?           │   │ │
    │  │   │  2. Is there any information NOT from context?             │   │ │
    │  │   │  3. Are there any contradictions?                          │   │ │
    │  │   │                                                            │   │ │
    │  │   │  Score: 0.0 - 1.0 (1.0 = perfectly faithful)              │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │   ┌────────────────────────────────────────────────────────────┐   │ │
    │  │   │  Decision Logic                                            │   │ │
    │  │   │                                                            │   │ │
    │  │   │  Score >= 0.70  →  PASS: Return response                  │   │ │
    │  │   │  Score >= 0.10  →  WARN: Return with low confidence note  │   │ │
    │  │   │  Score <  0.10  →  FALLBACK: Try Tavily web search        │   │ │
    │  │   └────────────────────────────────────────────────────────────┘   │ │
    │  │                                                                     │ │
    │  │   Result: Score = 0.85 → PASS                                       │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Time: ~400ms                                                           │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  STEP 7: CACHE & RETURN                                                 │
    │  ═══════════════════════                                                │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                      Final Processing                               │ │
    │  │                                                                     │ │
    │  │   1. Validate citation URLs                                         │ │
    │  │      • Check if links are accessible                               │ │
    │  │      • Replace broken links with fallbacks                         │ │
    │  │                                                                     │ │
    │  │   2. Cache response in Redis                                        │ │
    │  │      • Key: q:en:7f3a2b1c...                                       │ │
    │  │      • TTL: 3600 seconds (1 hour)                                  │ │
    │  │                                                                     │ │
    │  │   3. Build final response object                                    │ │
    │  │      {                                                              │ │
    │  │        success: true,                                               │ │
    │  │        response: "To prepare your home...",                        │ │
    │  │        citations: [{title, url, snippet}, ...],                    │ │
    │  │        faithfulness_score: 0.85,                                   │ │
    │  │        processing_time: 3.2,                                       │ │
    │  │        language_used: "en",                                        │ │
    │  │        model_used: "nova"                                          │ │
    │  │      }                                                              │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Time: ~100ms                                                           │
    └─────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                              TOTAL TIME: ~3-4 seconds
═══════════════════════════════════════════════════════════════════════════════
```

---

## Processing Times Breakdown

| Step | Component | Typical Time |
|------|-----------|--------------|
| 1 | Language Routing | ~50ms |
| 2 | Cache Check | ~5-10ms |
| 3 | Query Classification | ~500ms |
| 4 | Document Retrieval | ~800ms |
| 5 | Response Generation | ~1500ms |
| 6 | Hallucination Guard | ~400ms |
| 7 | Cache & Return | ~100ms |
| **Total** | End-to-end | **~3-4 seconds** |

---

## Fallback Scenarios

```
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        FALLBACK MECHANISMS                               │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │  Scenario 1: No Relevant Documents Found                           │ │
    │  │                                                                     │ │
    │  │  Pinecone returns 0 docs OR all scores < 0.65                      │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │  ┌────────────────────────────────────────────────────────────┐    │ │
    │  │  │  Tavily Web Search                                         │    │ │
    │  │  │  • Real-time web search for climate info                   │    │ │
    │  │  │  • Results used as context for generation                  │    │ │
    │  │  └────────────────────────────────────────────────────────────┘    │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │  Scenario 2: Hallucination Score Too Low                           │ │
    │  │                                                                     │ │
    │  │  Faithfulness score < 0.10                                         │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │  ┌────────────────────────────────────────────────────────────┐    │ │
    │  │  │  Regenerate with Tavily                                    │    │ │
    │  │  │  • Search web for verified information                     │    │ │
    │  │  │  • Regenerate response with new context                    │    │ │
    │  │  └────────────────────────────────────────────────────────────┘    │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │  Scenario 3: LLM Timeout or Error                                  │ │
    │  │                                                                     │ │
    │  │  Nova or Cohere fails after 45 seconds                             │ │
    │  │                              │                                      │ │
    │  │                              ▼                                      │ │
    │  │  ┌────────────────────────────────────────────────────────────┐    │ │
    │  │  │  Graceful Degradation                                      │    │ │
    │  │  │  • Return error message                                    │    │ │
    │  │  │  • Suggest user retry                                      │    │ │
    │  │  │  • Log for monitoring                                      │    │ │
    │  │  └────────────────────────────────────────────────────────────┘    │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Files Reference

| Step | Primary File | Line Numbers |
|------|--------------|--------------|
| Language Routing | `src/models/query_routing.py` | 188-300 |
| Cache Check | `src/models/climate_pipeline.py` | 508-541 |
| Query Classification | `src/models/query_rewriter.py` | 168-300 |
| Embedding | `src/models/retrieval.py` | 83-176 |
| Vector Search | `src/models/retrieval.py` | 190-256 |
| Reranking | `src/models/rerank.py` | 56-132 |
| Response Generation | `src/models/gen_response_unified.py` | 79-165 |
| Hallucination Guard | `src/models/hallucination_guard.py` | 75-200 |
| Main Orchestrator | `src/models/climate_pipeline.py` | 349-1140 |

---

## Learn More

- [High-Level Architecture](./01-high-level-architecture.md)
- [Data Flow Diagram](./03-data-flow.md)
- [RAG System Deep Dive](../components/04-rag-system.md)
