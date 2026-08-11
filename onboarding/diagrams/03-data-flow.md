# Data Flow Diagram

This document shows how data moves through the Dunia — Multilingual Climate Chatbot system.

---

## Complete Request-Response Flow

```
═══════════════════════════════════════════════════════════════════════════════
                           COMPLETE DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                           1. USER INPUT                                ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║                                                                        ║
    ║    ┌────────────────────────────────────────────────────────────────┐ ║
    ║    │  User Browser                                                  │ ║
    ║    │                                                                │ ║
    ║    │  ┌──────────────────────────────────────────────────────────┐ │ ║
    ║    │  │  Chat Input Box                                          │ │ ║
    ║    │  │  ┌────────────────────────────────────────────────────┐  │ │ ║
    ║    │  │  │ "What are the effects of rising sea levels?"       │  │ │ ║
    ║    │  │  └────────────────────────────────────────────────────┘  │ │ ║
    ║    │  │                                                          │ │ ║
    ║    │  │  [Language: Spanish ▼]    [Send ▶]                      │ │ ║
    ║    │  └──────────────────────────────────────────────────────────┘ │ ║
    ║    └────────────────────────────────────────────────────────────────┘ ║
    ║                                                                        ║
    ║    Data Captured:                                                      ║
    ║    • query: "What are the effects of rising sea levels?"              ║
    ║    • language: "es" (user selected)                                   ║
    ║    • conversation_history: [{role: "user", content: "..."}, ...]      ║
    ║                                                                        ║
    ╚════════════════════════════════════════════════════════════════════════╝
                                      │
                                      │ HTTP POST /api/v1/chat/query
                                      │ Content-Type: application/json
                                      ▼
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                        2. API LAYER                                    ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║                                                                        ║
    ║    File: src/webui/api/routers/chat.py                                ║
    ║                                                                        ║
    ║    ┌────────────────────────────────────────────────────────────────┐ ║
    ║    │  Request Processing                                            │ ║
    ║    │                                                                │ ║
    ║    │  1. Parse JSON body                                            │ ║
    ║    │     {                                                          │ ║
    ║    │       "query": "What are the effects...",                     │ ║
    ║    │       "language": "es",                                        │ ║
    ║    │       "conversation_history": [...],                           │ ║
    ║    │       "stream": false,                                         │ ║
    ║    │       "skip_cache": false                                      │ ║
    ║    │     }                                                          │ ║
    ║    │                                                                │ ║
    ║    │  2. Validate with Pydantic                                     │ ║
    ║    │     • query: 1-2000 chars ✓                                   │ ║
    ║    │     • language: ISO 639-1 code ✓                              │ ║
    ║    │                                                                │ ║
    ║    │  3. Generate request_id                                        │ ║
    ║    │     request_id = "req_1703894400123"                          │ ║
    ║    │                                                                │ ║
    ║    │  4. Rate limit check                                           │ ║
    ║    │     20 req/min per IP (production)                            │ ║
    ║    └────────────────────────────────────────────────────────────────┘ ║
    ║                                                                        ║
    ╚════════════════════════════════════════════════════════════════════════╝
                                      │
                                      │ Python function call
                                      ▼
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                      3. PIPELINE PROCESSING                            ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║                                                                        ║
    ║    File: src/models/climate_pipeline.py                               ║
    ║                                                                        ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE A: Language Routing                                       ║
    ║    │                                                                │ ║
    ║      Input: query="What are the effects...", language="es"          ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  MultilingualRouter.route_query()                        │ │ ║
    ║      │  • Detect actual language of query: "en" (English)       │   ║
    ║    │ │  • User preference: "es" (Spanish)                       │ │ ║
    ║      │  • Mismatch detected → Will translate response to "es"   │   ║
    ║    │ │  • Model selection: "nova" (English query)               │ │ ║
    ║      └──────────────────────────────────────────────────────────┘   ║
    ║    │                                                                │ ║
    ║      Output: {language_code: "en", output_language: "es",           ║
    ║    │          model_type: "nova", needs_translation: true}        │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                      │                                ║
    ║                                      ▼                                ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE B: Cache Lookup                                           ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  Redis Cache Check                                       │ │ ║
    ║      │                                                          │   ║
    ║    │ │  1. Normalize: "what are the effects of rising sea..."   │ │ ║
    ║      │  2. Hash: SHA256 → "a7b9c3d..."                          │   ║
    ║    │ │  3. Key: "q:en:a7b9c3d..."                               │ │ ║
    ║      │  4. Redis GET → null (cache miss)                        │   ║
    ║    │ └──────────────────────────────────────────────────────────┘ │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                      │                                ║
    ║                                      ▼                                ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE C: Query Classification                                   ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  Query Rewriter (AWS Bedrock Nova)                       │ │ ║
    ║      │                                                          │   ║
    ║    │ │  Prompt: "Classify this query: 'What are the effects...'"│ │ ║
    ║      │                                                          │   ║
    ║    │ │  Response: {                                             │ │ ║
    ║      │    "classification": "on-topic",                         │   ║
    ║    │ │    "climate_related": true,                              │ │ ║
    ║      │    "rewritten_query": "effects of rising sea levels"     │   ║
    ║    │ │  }                                                       │ │ ║
    ║      └──────────────────────────────────────────────────────────┘   ║
    ║    │                                                                │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                      │                                ║
    ║                                      ▼                                ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE D: Document Retrieval                                     ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  1. Embedding Generation (BGE-M3)                        │ │ ║
    ║      │     Input: "effects of rising sea levels"                │   ║
    ║    │ │     Output: {                                            │ │ ║
    ║      │       dense_vec: [0.12, -0.34, 0.56, ...] (1024 dims)    │   ║
    ║    │ │       sparse_vec: {"sea": 0.8, "level": 0.7, ...}        │ │ ║
    ║      │     }                                                    │   ║
    ║    │ └──────────────────────────────────────────────────────────┘ │ ║
    ║                                      │                              ║
    ║    │                                 ▼                              │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  2. Pinecone Vector Search                               │ │ ║
    ║      │     Query: hybrid(dense_vec, sparse_vec, alpha=0.5)      │   ║
    ║    │ │     Filters: exclude_audience="K-12"                     │ │ ║
    ║      │     Result: 15 documents                                 │   ║
    ║    │ │       [                                                  │ │ ║
    ║      │         {id: "doc1", score: 0.92, title: "Sea Level..."},│   ║
    ║    │ │         {id: "doc2", score: 0.88, title: "Coastal..."},  │ │ ║
    ║      │         ...                                              │   ║
    ║    │ │       ]                                                  │ │ ║
    ║      └──────────────────────────────────────────────────────────┘   ║
    ║    │                                 │                              │ ║
    ║                                      ▼                              ║
    ║    │ ┌──────────────────────────────────────────────────────────┐ │ ║
    ║      │  3. Cohere Reranking                                     │   ║
    ║    │ │     Input: query + 15 documents                          │ │ ║
    ║      │     Model: rerank-english-v3.0                           │   ║
    ║    │ │     Output: Top 5 documents (score >= 0.70)              │ │ ║
    ║      │       [                                                  │   ║
    ║    │ │         {title: "Sea Level Rise Impacts", score: 0.95}, │ │ ║
    ║      │         {title: "Coastal Flooding Guide", score: 0.91},  │   ║
    ║    │ │         ...                                              │ │ ║
    ║      │       ]                                                  │   ║
    ║    │ └──────────────────────────────────────────────────────────┘ │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                      │                                ║
    ║                                      ▼                                ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE E: Response Generation                                    ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  AWS Bedrock Nova Generation                             │ │ ║
    ║      │                                                          │   ║
    ║    │ │  Prompt Assembly:                                        │ │ ║
    ║      │  ┌────────────────────────────────────────────────────┐  │   ║
    ║    │ │  │ SYSTEM: You are a climate information assistant..  │  │ │ ║
    ║      │  │                                                    │  │   ║
    ║    │ │  │ CONTEXT:                                           │  │ │ ║
    ║      │  │ [Doc 1: Sea Level Rise Impacts - IPCC Report...]   │  │   ║
    ║    │ │  │ [Doc 2: Coastal Flooding Guide - NOAA...]          │  │ │ ║
    ║      │  │ [Doc 3: ...]                                       │  │   ║
    ║    │ │  │                                                    │  │ │ ║
    ║      │  │ USER: What are the effects of rising sea levels?   │  │   ║
    ║    │ │  └────────────────────────────────────────────────────┘  │ │ ║
    ║      │                                                          │   ║
    ║    │ │  Generated Response (English):                           │ │ ║
    ║      │  "Rising sea levels have several significant effects:    │   ║
    ║    │ │   1. Coastal flooding becomes more frequent [IPCC]       │ │ ║
    ║      │   2. Erosion of shorelines accelerates [NOAA]            │   ║
    ║    │ │   3. Saltwater intrusion affects freshwater [EPA]..."    │ │ ║
    ║      └──────────────────────────────────────────────────────────┘   ║
    ║    │                                                                │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                      │                                ║
    ║                                      ▼                                ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE F: Quality Assurance                                      ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  Hallucination Guard                                     │ │ ║
    ║      │                                                          │   ║
    ║    │ │  Evaluate: Is response faithful to documents?            │ │ ║
    ║      │  • Claim 1: "Coastal flooding" - Found in IPCC doc ✓     │   ║
    ║    │ │  • Claim 2: "Erosion" - Found in NOAA doc ✓              │ │ ║
    ║      │  • Claim 3: "Saltwater intrusion" - Found in EPA doc ✓   │   ║
    ║    │ │                                                          │ │ ║
    ║      │  Faithfulness Score: 0.92 (excellent)                    │   ║
    ║    │ └──────────────────────────────────────────────────────────┘ │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                      │                                ║
    ║                                      ▼                                ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE G: Translation (if needed)                                ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  AWS Bedrock Nova Translation                            │ │ ║
    ║      │                                                          │   ║
    ║    │ │  Input: English response                                 │ │ ║
    ║      │  Target: Spanish ("es")                                  │   ║
    ║    │ │                                                          │ │ ║
    ║      │  Output: "El aumento del nivel del mar tiene varios      │   ║
    ║    │ │          efectos significativos:                         │ │ ║
    ║      │          1. Las inundaciones costeras se vuelven más     │   ║
    ║    │ │             frecuentes [IPCC]                            │ │ ║
    ║      │          2. La erosión de las costas se acelera [NOAA]   │   ║
    ║    │ │          ..."                                            │ │ ║
    ║      └──────────────────────────────────────────────────────────┘   ║
    ║    │                                                                │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                      │                                ║
    ║                                      ▼                                ║
    ║    ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐ ║
    ║      STAGE H: Cache & Finalize                                       ║
    ║    │                                                                │ ║
    ║      ┌──────────────────────────────────────────────────────────┐   ║
    ║    │ │  1. Store in Redis                                       │ │ ║
    ║      │     Key: "q:en:a7b9c3d..."                                │   ║
    ║    │ │     Value: {response, citations, score, ...}             │ │ ║
    ║      │     TTL: 3600 seconds (1 hour)                           │   ║
    ║    │ │                                                          │ │ ║
    ║      │  2. Build Citations Array                                │   ║
    ║    │ │     [                                                    │ │ ║
    ║      │       {title: "IPCC Sea Level Report", url: "...", ...}, │   ║
    ║    │ │       {title: "NOAA Coastal Guide", url: "...", ...},    │ │ ║
    ║      │       ...                                                │   ║
    ║    │ │     ]                                                    │ │ ║
    ║      │                                                          │   ║
    ║    │ │  3. Validate Citation URLs                               │ │ ║
    ║      │     Check each URL is accessible                         │   ║
    ║    │ └──────────────────────────────────────────────────────────┘ │ ║
    ║    └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘ ║
    ║                                                                        ║
    ╚════════════════════════════════════════════════════════════════════════╝
                                      │
                                      │ Python return
                                      ▼
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                        4. API RESPONSE                                 ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║                                                                        ║
    ║    ┌────────────────────────────────────────────────────────────────┐ ║
    ║    │  HTTP Response                                                 │ ║
    ║    │                                                                │ ║
    ║    │  Status: 200 OK                                                │ ║
    ║    │  Headers:                                                      │ ║
    ║    │    Content-Type: application/json                              │ ║
    ║    │    X-Request-ID: req_1703894400123                            │ ║
    ║    │    X-Processing-Time: 3.2s                                    │ ║
    ║    │                                                                │ ║
    ║    │  Body:                                                         │ ║
    ║    │  {                                                             │ ║
    ║    │    "success": true,                                            │ ║
    ║    │    "response": "El aumento del nivel del mar...",             │ ║
    ║    │    "citations": [                                              │ ║
    ║    │      {                                                         │ ║
    ║    │        "title": "IPCC Sea Level Report",                      │ ║
    ║    │        "url": "https://ipcc.ch/report/...",                   │ ║
    ║    │        "snippet": "Global mean sea level rose..."              │ ║
    ║    │      },                                                        │ ║
    ║    │      ...                                                       │ ║
    ║    │    ],                                                          │ ║
    ║    │    "faithfulness_score": 0.92,                                │ ║
    ║    │    "processing_time": 3.2,                                    │ ║
    ║    │    "language_used": "es",                                     │ ║
    ║    │    "model_used": "nova",                                      │ ║
    ║    │    "request_id": "req_1703894400123"                          │ ║
    ║    │  }                                                             │ ║
    ║    └────────────────────────────────────────────────────────────────┘ ║
    ║                                                                        ║
    ╚════════════════════════════════════════════════════════════════════════╝
                                      │
                                      │ HTTP Response
                                      ▼
    ╔═══════════════════════════════════════════════════════════════════════╗
    ║                        5. USER DISPLAY                                 ║
    ╠═══════════════════════════════════════════════════════════════════════╣
    ║                                                                        ║
    ║    ┌────────────────────────────────────────────────────────────────┐ ║
    ║    │  Chat Window                                                   │ ║
    ║    │                                                                │ ║
    ║    │  ┌────────────────────────────────────────────────────────┐   │ ║
    ║    │  │ 👤 You                                                 │   │ ║
    ║    │  │ What are the effects of rising sea levels?             │   │ ║
    ║    │  └────────────────────────────────────────────────────────┘   │ ║
    ║    │                                                                │ ║
    ║    │  ┌────────────────────────────────────────────────────────┐   │ ║
    ║    │  │ 🤖 Climate Assistant                                   │   │ ║
    ║    │  │                                                        │   │ ║
    ║    │  │ El aumento del nivel del mar tiene varios efectos      │   │ ║
    ║    │  │ significativos:                                        │   │ ║
    ║    │  │                                                        │   │ ║
    ║    │  │ 1. Las inundaciones costeras se vuelven más           │   │ ║
    ║    │  │    frecuentes [1]                                      │   │ ║
    ║    │  │ 2. La erosión de las costas se acelera [2]            │   │ ║
    ║    │  │ 3. La intrusión de agua salada afecta el agua         │   │ ║
    ║    │  │    dulce [3]                                           │   │ ║
    ║    │  │                                                        │   │ ║
    ║    │  │ ─────────────────────────────────────────────────────  │   │ ║
    ║    │  │ Citations:                                             │   │ ║
    ║    │  │ [1] IPCC Sea Level Report - ipcc.ch                   │   │ ║
    ║    │  │ [2] NOAA Coastal Guide - noaa.gov                     │   │ ║
    ║    │  │ [3] EPA Water Resources - epa.gov                     │   │ ║
    ║    │  │                                                        │   │ ║
    ║    │  │ [👍 Helpful]  [👎 Not Helpful]  [📥 Export PDF]       │   │ ║
    ║    │  └────────────────────────────────────────────────────────┘   │ ║
    ║    └────────────────────────────────────────────────────────────────┘ ║
    ║                                                                        ║
    ╚════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════════
```

---

## Data Structures at Each Stage

### Stage 1: User Input
```typescript
// Frontend captures
{
  query: string,           // User's question
  language: string,        // Selected language code
  conversationHistory: [   // Previous messages
    { role: "user", content: "..." },
    { role: "assistant", content: "..." }
  ]
}
```

### Stage 2: API Request
```python
# ChatRequest (Pydantic model)
{
  "query": str,                        # 1-2000 chars
  "language": Optional[str],           # ISO 639-1
  "conversation_history": List[Dict],  # Previous turns
  "stream": bool,                      # SSE streaming
  "skip_cache": bool                   # Bypass cache
}
```

### Stage 3: Pipeline Internal
```python
# Routing result
{
  "language_code": "en",
  "output_language": "es",
  "model_type": "nova",
  "needs_translation": True
}

# Retrieved documents
[
  {
    "id": "doc1",
    "title": "Sea Level Rise",
    "url": "https://...",
    "content": "...",
    "score": 0.92
  },
  ...
]
```

### Stage 4: API Response
```python
# ChatResponse
{
  "success": True,
  "response": "El aumento...",
  "citations": [
    {"title": "...", "url": "...", "snippet": "..."}
  ],
  "faithfulness_score": 0.92,
  "processing_time": 3.2,
  "language_used": "es",
  "model_used": "nova",
  "request_id": "req_..."
}
```

---

## Learn More

- [High-Level Architecture](./01-high-level-architecture.md)
- [AI Pipeline Flow](./02-ai-pipeline-flow.md)
- [Component Interactions](./04-component-interactions.md)
