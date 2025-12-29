# Component Interactions Diagram

This document shows how different components in the system communicate with each other.

---

## Frontend-Backend Communication

```
═══════════════════════════════════════════════════════════════════════════════
                    FRONTEND ←→ BACKEND COMMUNICATION
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         NEXT.JS FRONTEND                                 │
    │                     (src/webui/app/src/app/)                            │
    │                                                                          │
    │  ┌───────────────────────────────────────────────────────────────────┐  │
    │  │                    page.tsx (Main Component)                       │  │
    │  │                                                                    │  │
    │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
    │  │  │ ChatWindow  │  │ AppHeader   │  │ Citations   │               │  │
    │  │  │             │  │             │  │ Panel       │               │  │
    │  │  │ • Messages  │  │ • Language  │  │ • Sources   │               │  │
    │  │  │ • Input     │  │   selector  │  │ • Export    │               │  │
    │  │  │ • Streaming │  │ • New chat  │  │ • Feedback  │               │  │
    │  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │  │
    │  │         │                │                │                       │  │
    │  │         └────────────────┼────────────────┘                       │  │
    │  │                          │                                        │  │
    │  │                          ▼                                        │  │
    │  │  ┌───────────────────────────────────────────────────────────┐   │  │
    │  │  │                   ApiClient (lib/api.ts)                   │   │  │
    │  │  │                                                            │   │  │
    │  │  │  Methods:                                                  │   │  │
    │  │  │  • sendChatQuery(query, language, history)                │   │  │
    │  │  │  • streamChatQuery(query, language, history)              │   │  │
    │  │  │  • submitFeedback(messageId, type, categories)            │   │  │
    │  │  │  • detectLanguage(text)                                   │   │  │
    │  │  │  • getSupportedLanguages()                                │   │  │
    │  │  │  • checkConsent() / acceptConsent()                       │   │  │
    │  │  └───────────────────────────────────────────────────────────┘   │  │
    │  │                                                                    │  │
    │  └────────────────────────────────────────────────────────────────────┘  │
    │                                                                          │
    └──────────────────────────────────┬───────────────────────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
            ▼                          ▼                          ▼
    ┌───────────────┐        ┌────────────────┐        ┌────────────────┐
    │  POST /chat/  │        │ GET /languages/│        │POST /feedback/ │
    │    query      │        │   supported    │        │    submit      │
    └───────┬───────┘        └───────┬────────┘        └───────┬────────┘
            │                        │                          │
            └────────────────────────┼──────────────────────────┘
                                     │
                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         FASTAPI BACKEND                                  │
    │                      (src/webui/api/main.py)                            │
    │                                                                          │
    │  ┌───────────────────────────────────────────────────────────────────┐  │
    │  │                         API Routers                                │  │
    │  │                                                                    │  │
    │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐ │  │
    │  │  │  chat.py     │ │ languages.py │ │ feedback.py  │ │consent.py │ │  │
    │  │  │              │ │              │ │              │ │           │ │  │
    │  │  │ /query       │ │ /supported   │ │ /submit      │ │ /check    │ │  │
    │  │  │ /stream      │ │ /validate    │ │ /categories  │ │ /accept   │ │  │
    │  │  │ /test        │ │ /test        │ │ /test        │ │ /revoke   │ │  │
    │  │  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘ │  │
    │  │                                                                    │  │
    │  └────────────────────────────────────────────────────────────────────┘  │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoint Details

### Chat Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  POST /api/v1/chat/query                                                    │
│  ═══════════════════════                                                    │
│                                                                              │
│  Request:                              Response:                             │
│  ┌──────────────────────────┐         ┌──────────────────────────────────┐ │
│  │ {                        │         │ {                                │ │
│  │   "query": "...",        │   ──▶   │   "success": true,               │ │
│  │   "language": "en",      │         │   "response": "...",             │ │
│  │   "conversation_history":│         │   "citations": [...],            │ │
│  │     [...],               │         │   "faithfulness_score": 0.85,    │ │
│  │   "stream": false,       │         │   "processing_time": 3.2,        │ │
│  │   "skip_cache": false    │         │   "language_used": "en",         │ │
│  │ }                        │         │   "model_used": "nova"           │ │
│  └──────────────────────────┘         │ }                                │ │
│                                        └──────────────────────────────────┘ │
│  Rate Limit: 20 req/min (prod)                                              │
│  Timeout: 60 seconds                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  POST /api/v1/chat/stream                                                   │
│  ════════════════════════                                                   │
│                                                                              │
│  Request: Same as /query                                                    │
│                                                                              │
│  Response: Server-Sent Events (SSE)                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ data: {"type": "progress", "stage": "initializing"}                  │  │
│  │ data: {"type": "language_detected", "language": "en", "model": ".."}│  │
│  │ data: {"type": "progress", "stage": "retrieving_documents"}          │  │
│  │ data: {"type": "progress", "stage": "generating_response"}           │  │
│  │ data: {"type": "token", "content": "Climate ", "partial": "Climate"} │  │
│  │ data: {"type": "token", "content": "change ", "partial": "Climate..."}│  │
│  │ ...                                                                   │  │
│  │ data: {"type": "complete", "final_response": "...", "citations": [...]}│
│  │ data: {"type": "end"}                                                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Language Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GET /api/v1/languages/supported                                            │
│  ═══════════════════════════════                                            │
│                                                                              │
│  Response:                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                    │  │
│  │   "command_a_languages": [                                          │  │
│  │     {"code": "ar", "name": "Arabic"},                               │  │
│  │     {"code": "zh", "name": "Chinese"},                              │  │
│  │     ...22 languages                                                 │  │
│  │   ],                                                                 │  │
│  │   "nova_languages": [                                                │  │
│  │     {"code": "en", "name": "English"},                              │  │
│  │     {"code": "es", "name": "Spanish"},                              │  │
│  │     ...183 languages                                                │  │
│  │   ],                                                                 │  │
│  │   "default_language": "en",                                         │  │
│  │   "total_supported": 183                                            │  │
│  │ }                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  POST /api/v1/languages/validate                                            │
│  ═══════════════════════════════                                            │
│                                                                              │
│  Request:                              Response:                             │
│  ┌──────────────────────────┐         ┌──────────────────────────────────┐ │
│  │ {                        │         │ {                                │ │
│  │   "text": "Bonjour..."   │   ──▶   │   "detected_language": "fr",     │ │
│  │ }                        │         │   "confidence": 0.95,            │ │
│  └──────────────────────────┘         │   "recommended_model": "nova",   │ │
│                                        │   "is_supported": true           │ │
│                                        │ }                                │ │
│                                        └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Backend-Pipeline Communication

```
═══════════════════════════════════════════════════════════════════════════════
                    BACKEND ←→ AI PIPELINE COMMUNICATION
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      FastAPI Router (chat.py)                            │
    │                                                                          │
    │   async def process_chat_query():                                        │
    │       # 1. Parse input                                                   │
    │       request = ChatRequest.model_validate(data)                         │
    │                                                                          │
    │       # 2. Get pipeline from dependency injection                        │
    │       pipeline = get_pipeline()  # ClimateQueryPipeline                  │
    │                                                                          │
    │       # 3. Call pipeline                                                 │
    │       result = await pipeline.process_query(                             │
    │           query=request.query,                                           │
    │           language=request.language,                                     │
    │           conversation_history=parsed_history,                           │
    │           skip_cache=request.skip_cache                                  │
    │       )                                                                  │
    │                                                                          │
    │       # 4. Format response                                               │
    │       return ChatResponse(**result)                                      │
    │                                                                          │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        │ await process_query()
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                   ClimateQueryPipeline (climate_pipeline.py)             │
    │                                                                          │
    │  ┌───────────────────────────────────────────────────────────────────┐  │
    │  │                        Pipeline Components                         │  │
    │  │                                                                    │  │
    │  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐         │  │
    │  │  │ Multilingual│     │   Query     │     │  Response   │         │  │
    │  │  │   Router    │────▶│  Rewriter   │────▶│  Generator  │         │  │
    │  │  │             │     │             │     │             │         │  │
    │  │  │ Detects     │     │ Classifies  │     │ Generates   │         │  │
    │  │  │ language,   │     │ intent,     │     │ response    │         │  │
    │  │  │ selects     │     │ rewrites    │     │ with LLM    │         │  │
    │  │  │ model       │     │ query       │     │             │         │  │
    │  │  └─────────────┘     └─────────────┘     └─────────────┘         │  │
    │  │         │                   │                   │                 │  │
    │  │         │                   │                   │                 │  │
    │  │         ▼                   ▼                   ▼                 │  │
    │  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐         │  │
    │  │  │   Redis     │     │  Retrieval  │     │Hallucination│         │  │
    │  │  │   Cache     │     │  Pipeline   │     │   Guard     │         │  │
    │  │  │             │     │             │     │             │         │  │
    │  │  │ Caches      │     │ BGE-M3 +    │     │ Validates   │         │  │
    │  │  │ responses   │     │ Pinecone +  │     │ faithfulness│         │  │
    │  │  │ (1hr TTL)   │     │ Cohere      │     │ to sources  │         │  │
    │  │  └─────────────┘     └─────────────┘     └─────────────┘         │  │
    │  │                                                                    │  │
    │  └────────────────────────────────────────────────────────────────────┘  │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Internal Communication

```
═══════════════════════════════════════════════════════════════════════════════
                    PIPELINE INTERNAL COMPONENT FLOW
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        ClimateQueryPipeline                              │
    │                                                                          │
    │  process_query(query, language, conversation_history, skip_cache)        │
    │                                                                          │
    │  ═══════════════════════════════════════════════════════════════════    │
    │                                                                          │
    │  Step 1: ROUTING                                                         │
    │  ┌───────────────┐                                                       │
    │  │router.route_  │──────▶ routing_info = {                              │
    │  │   query()     │           language_code: "en",                       │
    │  └───────────────┘           model_type: "nova",                        │
    │  query_routing.py             needs_translation: false                  │
    │  Line 188-300               }                                           │
    │                                    │                                     │
    │                                    ▼                                     │
    │  Step 2: CACHE CHECK                                                     │
    │  ┌───────────────┐                                                       │
    │  │cache.get()    │──────▶ cached_result or None                         │
    │  └───────────────┘                                                       │
    │  redis_cache.py                    │                                     │
    │  Line 81-109             ┌─────────┴─────────┐                          │
    │                          │                   │                          │
    │                     Cache HIT           Cache MISS                      │
    │                          │                   │                          │
    │                          ▼                   ▼                          │
    │                     Return cached     Continue processing               │
    │                                              │                          │
    │                                              ▼                          │
    │  Step 3: QUERY CLASSIFICATION                                            │
    │  ┌───────────────┐                                                       │
    │  │query_rewriter │──────▶ classification = {                            │
    │  │   ()          │           classification: "on-topic",                │
    │  └───────────────┘           rewritten_query: "...",                    │
    │  query_rewriter.py           climate_related: true                      │
    │  Line 168-300               }                                           │
    │                                    │                                     │
    │                          ┌─────────┴──────────┐                         │
    │                          │                    │                         │
    │                    "greeting/goodbye/      "on-topic"                   │
    │                     thanks/off-topic"          │                        │
    │                          │                     │                        │
    │                          ▼                     ▼                        │
    │                    Return canned          Continue                      │
    │                    response                    │                        │
    │                                                ▼                        │
    │  Step 4: DOCUMENT RETRIEVAL                                              │
    │  ┌───────────────┐                                                       │
    │  │get_query_     │──────▶ embeddings = {                                │
    │  │embeddings()   │           dense_vecs: [...],                         │
    │  └───────────────┘           lexical_weights: [...]                     │
    │  retrieval.py              }                                            │
    │  Line 83-176                     │                                       │
    │                                  ▼                                       │
    │  ┌───────────────┐                                                       │
    │  │pinecone.query │──────▶ raw_results = [15 documents]                  │
    │  │   ()          │                                                       │
    │  └───────────────┘                                                       │
    │  retrieval.py                    │                                       │
    │  Line 190-256                    ▼                                       │
    │  ┌───────────────┐                                                       │
    │  │rerank_fcn()   │──────▶ ranked_docs = [5 documents]                   │
    │  └───────────────┘                                                       │
    │  rerank.py                       │                                       │
    │  Line 56-132                     ▼                                       │
    │                                                                          │
    │  Step 5: RESPONSE GENERATION                                             │
    │  ┌───────────────┐                                                       │
    │  │generator.     │──────▶ generation_result = {                         │
    │  │generate_      │           response: "...",                           │
    │  │response()     │           citations: [...]                           │
    │  └───────────────┘         }                                            │
    │  gen_response_unified.py         │                                       │
    │  Line 79-165                     ▼                                       │
    │                                                                          │
    │  Step 6: HALLUCINATION CHECK                                             │
    │  ┌───────────────┐                                                       │
    │  │check_         │──────▶ faithfulness_score = 0.85                     │
    │  │hallucination  │                                                       │
    │  │()             │                                                       │
    │  └───────────────┘                                                       │
    │  hallucination_guard.py          │                                       │
    │  Line 75-200           ┌─────────┴─────────┐                            │
    │                        │                   │                            │
    │                   score >= 0.70       score < 0.10                      │
    │                        │                   │                            │
    │                        ▼                   ▼                            │
    │                   Use response       Try Tavily                         │
    │                        │             fallback                           │
    │                        │                   │                            │
    │                        └─────────┬─────────┘                            │
    │                                  ▼                                       │
    │  Step 7: TRANSLATION (if needed)                                         │
    │  ┌───────────────┐                                                       │
    │  │nova.translate │──────▶ translated_response                           │
    │  │()             │                                                       │
    │  └───────────────┘                                                       │
    │  nova_flow.py                    │                                       │
    │  Line 200+                       ▼                                       │
    │                                                                          │
    │  Step 8: CACHE & RETURN                                                  │
    │  ┌───────────────┐                                                       │
    │  │cache.set()    │──────▶ Stored in Redis (1hr TTL)                     │
    │  └───────────────┘                                                       │
    │  redis_cache.py                  │                                       │
    │  Line 111-137                    ▼                                       │
    │                                                                          │
    │  return {                                                                │
    │      success: True,                                                      │
    │      response: "...",                                                    │
    │      citations: [...],                                                   │
    │      faithfulness_score: 0.85,                                          │
    │      processing_time: 3.2,                                              │
    │      language_used: "en",                                               │
    │      model_used: "nova"                                                 │
    │  }                                                                       │
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## External Service Communication

```
═══════════════════════════════════════════════════════════════════════════════
                    EXTERNAL SERVICE INTEGRATIONS
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      ClimateQueryPipeline                                │
    │                                                                          │
    │  ┌─────────────────────────────────────────────────────────────────────┐│
    │  │                        AWS Bedrock (Nova)                           ││
    │  │                                                                     ││
    │  │  Connection:                                                        ││
    │  │  ┌─────────────────────────────────────────────────────────────┐   ││
    │  │  │  boto3.client('bedrock-runtime')                            │   ││
    │  │  │  Region: us-east-1                                          │   ││
    │  │  │  Model: amazon.nova-lite-v1:0                               │   ││
    │  │  └─────────────────────────────────────────────────────────────┘   ││
    │  │                                                                     ││
    │  │  Used for:                                                          ││
    │  │  • Query classification                                             ││
    │  │  • Response generation (6 languages)                                ││
    │  │  • Translation                                                      ││
    │  │  • Hallucination evaluation                                         ││
    │  │                                                                     ││
    │  │  File: src/models/nova_flow.py                                      ││
    │  └─────────────────────────────────────────────────────────────────────┘│
    │                                                                          │
    │  ┌─────────────────────────────────────────────────────────────────────┐│
    │  │                           Cohere API                                ││
    │  │                                                                     ││
    │  │  Connection:                                                        ││
    │  │  ┌─────────────────────────────────────────────────────────────┐   ││
    │  │  │  cohere.Client(api_key=COHERE_API_KEY)                      │   ││
    │  │  └─────────────────────────────────────────────────────────────┘   ││
    │  │                                                                     ││
    │  │  Used for:                                                          ││
    │  │  • Document reranking (rerank-english-v3.0)                         ││
    │  │  • Response generation (Command-A, 22 languages)                    ││
    │  │                                                                     ││
    │  │  File: src/models/cohere_flow.py, src/models/rerank.py              ││
    │  └─────────────────────────────────────────────────────────────────────┘│
    │                                                                          │
    │  ┌─────────────────────────────────────────────────────────────────────┐│
    │  │                         Pinecone Vector DB                          ││
    │  │                                                                     ││
    │  │  Connection:                                                        ││
    │  │  ┌─────────────────────────────────────────────────────────────┐   ││
    │  │  │  pinecone.init(api_key=PINECONE_API_KEY, environment=...)   │   ││
    │  │  │  Index: climate-change-adaptation-index-10-24-prod          │   ││
    │  │  └─────────────────────────────────────────────────────────────┘   ││
    │  │                                                                     ││
    │  │  Used for:                                                          ││
    │  │  • Hybrid vector search (dense + sparse)                            ││
    │  │  • Document storage (10K+ climate documents)                        ││
    │  │                                                                     ││
    │  │  File: src/models/retrieval.py                                      ││
    │  └─────────────────────────────────────────────────────────────────────┘│
    │                                                                          │
    │  ┌─────────────────────────────────────────────────────────────────────┐│
    │  │                             Redis Cache                             ││
    │  │                                                                     ││
    │  │  Connection:                                                        ││
    │  │  ┌─────────────────────────────────────────────────────────────┐   ││
    │  │  │  redis.Redis(host=REDIS_HOST, port=6379, ...)               │   ││
    │  │  └─────────────────────────────────────────────────────────────┘   ││
    │  │                                                                     ││
    │  │  Used for:                                                          ││
    │  │  • Response caching (1 hour TTL)                                    ││
    │  │  • Session storage                                                  ││
    │  │  • Feedback storage                                                 ││
    │  │  • Consent tracking                                                 ││
    │  │                                                                     ││
    │  │  File: src/models/redis_cache.py                                    ││
    │  └─────────────────────────────────────────────────────────────────────┘│
    │                                                                          │
    │  ┌─────────────────────────────────────────────────────────────────────┐│
    │  │                      Tavily Web Search (Fallback)                   ││
    │  │                                                                     ││
    │  │  Connection:                                                        ││
    │  │  ┌─────────────────────────────────────────────────────────────┐   ││
    │  │  │  TavilyClient(api_key=TAVILY_API_KEY)                       │   ││
    │  │  └─────────────────────────────────────────────────────────────┘   ││
    │  │                                                                     ││
    │  │  Used for:                                                          ││
    │  │  • Fallback when Pinecone has no relevant docs                      ││
    │  │  • Fallback when hallucination score is too low                     ││
    │  │                                                                     ││
    │  │  File: src/models/climate_pipeline.py                               ││
    │  └─────────────────────────────────────────────────────────────────────┘│
    │                                                                          │
    └─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Dependencies Summary

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY GRAPH                                    │
│                                                                             │
│                        ┌──────────────┐                                    │
│                        │   main.py    │                                    │
│                        │  (FastAPI)   │                                    │
│                        └───────┬──────┘                                    │
│                                │                                            │
│           ┌────────────────────┼────────────────────┐                      │
│           │                    │                    │                      │
│           ▼                    ▼                    ▼                      │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│   │   chat.py    │     │languages.py  │     │ feedback.py  │              │
│   └───────┬──────┘     └──────────────┘     └──────────────┘              │
│           │                                                                 │
│           ▼                                                                 │
│   ┌──────────────────────────────────────┐                                 │
│   │        ClimateQueryPipeline          │                                 │
│   │       (climate_pipeline.py)          │                                 │
│   └───────┬────────┬────────┬────────────┘                                 │
│           │        │        │                                               │
│     ┌─────┘        │        └─────┐                                        │
│     │              │              │                                        │
│     ▼              ▼              ▼                                        │
│ ┌────────┐   ┌──────────┐   ┌──────────┐                                  │
│ │router  │   │retrieval │   │generator │                                  │
│ │.py     │   │.py       │   │.py       │                                  │
│ └────────┘   └─────┬────┘   └────┬─────┘                                  │
│                    │             │                                         │
│              ┌─────┴─────┐       │                                         │
│              │           │       │                                         │
│              ▼           ▼       ▼                                         │
│         ┌────────┐  ┌────────┐ ┌────────────┐                             │
│         │BGE-M3  │  │rerank  │ │nova_flow   │                             │
│         │        │  │.py     │ │cohere_flow │                             │
│         └────────┘  └────────┘ └────────────┘                             │
│                                                                             │
│   EXTERNAL:  Pinecone   Cohere   AWS Bedrock   Redis   Tavily             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Learn More

- [High-Level Architecture](./01-high-level-architecture.md)
- [AI Pipeline Flow](./02-ai-pipeline-flow.md)
- [Data Flow Diagram](./03-data-flow.md)
