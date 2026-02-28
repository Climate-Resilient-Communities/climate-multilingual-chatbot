# Climate Multilingual Chatbot - Infrastructure & Architecture

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Pipeline Flow](#pipeline-flow)
3. [LLM Providers & Models](#llm-providers--models)
4. [RAG Implementation](#rag-implementation)
5. [Frontend Architecture](#frontend-architecture)
6. [API Layer](#api-layer)
7. [Azure Deployment](#azure-deployment)
8. [Redis Caching Strategy](#redis-caching-strategy)
9. [Environment Variables](#environment-variables)
10. [Monitoring & Logging](#monitoring--logging)
11. [Known Issues & Technical Debt](#known-issues--technical-debt)
12. [Deployment Checklist](#deployment-checklist)

---

## System Architecture Overview

```
User Browser
    |
    v
Next.js Frontend (Static Export)
    |  POST /api/v1/chat/query
    v
FastAPI Backend (Uvicorn)
    |
    +--> Language Routing (MultilingualRouter)
    +--> Query Rewriting (BedrockModel / Nova Lite)
    +--> Input Guards (ClimateBERT + keyword checks)
    +--> Document Retrieval (BGE-M3 -> Pinecone hybrid search)
    +--> Reranking (Cohere rerank API)
    +--> Response Generation (Nova or Cohere Command A)
    +--> Hallucination Guard (Nova Lite faithfulness check)
    +--> Translation (Nova Lite, if non-English)
    +--> Redis Cache (read/write)
    |
    v
Response + Citations
```

**Key Design Decisions:**
- Monolithic deployment: frontend static files served by FastAPI
- English-first generation: all responses generated in English, then translated
- Hybrid search: dense (BGE-M3) + sparse (BM25-style) vectors via Pinecone
- Model routing: Cohere Command A for well-supported languages, Nova for others

---

## Pipeline Flow

The core pipeline lives in `src/models/climate_pipeline.py` (`ClimateQueryPipeline`).

### Step-by-Step Processing:

| Step | Module | Description | Timeout |
|------|--------|-------------|---------|
| 1. Cache Check | `redis_cache.py` | Exact + fuzzy cache lookup | - |
| 2. Language Routing | `query_routing.py` | Detect language, select model | - |
| 3. Query Rewriting | `query_rewriter.py` | Classify intent + rewrite to English | 30s |
| 4. Input Guards | `input_guardrail.py` | Topic moderation (climate-only) | - |
| 5. Document Retrieval | `retrieval.py` | BGE-M3 embed -> Pinecone search -> Cohere rerank | - |
| 6. Response Generation | `gen_response_unified.py` | Nova or Cohere generates English response | 45s |
| 7. Hallucination Guard | `hallucination_guard.py` | Faithfulness scoring via Nova Lite | 15s |
| 8. Translation | `nova_flow.py` | Translate to target language if needed | 30s |
| 9. Cache Storage | `redis_cache.py` | Store result + English version | - |

### Classification Categories (from Query Rewriter):

- `on-topic` - Climate/environment/sustainability query -> proceed
- `off-topic` - Non-climate query -> return canned rejection
- `harmful` - Dangerous/inappropriate -> return canned rejection
- `greeting` / `goodbye` / `thanks` -> return canned conversational response
- `emergency` -> return emergency guidance
- `instruction` -> return "how it works" explanation

### Fallback Chain:

1. Pinecone RAG retrieval
2. If no docs -> Tavily web search fallback
3. If hallucination score < 0.1 -> Tavily web search fallback
4. If translation fails -> return English response

---

## LLM Providers & Models

### AWS Bedrock (Nova)

- **Client**: `src/models/nova_flow.py` (`BedrockModel`)
- **Default Model**: `amazon.nova-lite-v1:0`
- **Region**: `us-east-1`
- **Used For**: Query rewriting, classification, translation, response generation, faithfulness evaluation
- **Parameters**:
  - `temperature`: 0.1 (deterministic)
  - `topP`: 0.9
  - `maxTokens`: 800 (content gen) / 1500 (responses) / 10000 (translation/normalization)
- **Invocation**: Sync client via `asyncio.to_thread()` to avoid event loop issues
- **Timeouts**: 30s hard timeout via `asyncio.wait_for()`
- **Retry**: 2 max attempts with adaptive mode (botocore built-in)

### Cohere

- **Client**: `src/models/cohere_flow.py` (`CohereModel`)
- **Chat Model**: `command-a-03-2025`
- **Rerank Model**: `rerank-english-v3.0`
- **Used For**: Response generation (supported languages), document reranking
- **Invocation**: Sync client via `asyncio.to_thread()`
- **Rerank Timeout**: 10s

### BGE-M3 (Local Model)

- **Library**: FlagEmbedding (`BGEM3FlagModel`)
- **Used For**: Dense + sparse query/document embeddings
- **Returns**: Dense vectors (1024 dim) + lexical weights (sparse)
- **Cache**: In-memory LRU cache (5000 entries, configurable via `EMBEDDING_CACHE_MAX_SIZE`)

### ClimateBERT (Optional)

- **Model**: `climatebert/distilroberta-base-climate-detector`
- **Used For**: ML-based topic classification (backup to keyword/LLM checks)
- **Loading Priority**: Azure path -> Local path -> HuggingFace download

---

## RAG Implementation

### Embedding & Search

```
Query -> BGE-M3 encode -> {dense_vec, sparse_weights}
                              |
                              v
                    Pinecone Hybrid Query
                    (alpha=0.5 dense/sparse blend)
                              |
                              v
                    Raw Results (top_k=8)
                              |
                    +---------+---------+
                    |                   |
            Domain Boosting     K-12 Filtering
            (prefer .gov, etc)  (remove educational)
                    |                   |
                    +---------+---------+
                              |
                              v
                    Cohere Rerank API
                    (rerank-english-v3.0)
                              |
                              v
                    Final Ranked Documents
```

### Key Configuration (from `src/data/config/config.py`):

- **Pinecone Index**: Environment-driven (`PINECONE_INDEX_NAME`)
- **Top-K**: 8 (default)
- **Alpha**: 0.5 (50% dense, 50% sparse)
- **Domain Blocklist**: `{"lsf-lst.ca", "climatelearning.ca"}`
- **Audience Blocklist**: K-12 educational content patterns

### Fuzzy Cache Matching

The pipeline supports fuzzy cache matching (Jaccard similarity >= 0.92) to reuse cached responses for near-duplicate queries in the same language.

---

## Frontend Architecture

### Stack

- **Framework**: Next.js 15 (static export)
- **UI**: React 19, Tailwind CSS, shadcn/ui (Radix primitives)
- **Language**: TypeScript

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `page.tsx` | `src/webui/app/src/app/page.tsx` | Main chat interface, message handling |
| `ChatWindow` | `src/components/chat/chat-window.tsx` | Message display, scroll, sample questions |
| `ChatMessage` | `src/components/chat/chat-message.tsx` | Individual message rendering, feedback |
| `AppHeader` | `src/app/components/chat/app-header.tsx` | Nav, language selector, FAQ |
| `CitationsPopover` | `src/components/chat/citations-popover.tsx` | Desktop citations |
| `CitationsSheet` | `src/components/chat/citations-sheet.tsx` | Mobile citations |
| `ConsentDialog` | `src/components/chat/consent-dialog.tsx` | Terms acceptance |
| `ExportButton` | `src/components/chat/export-button.tsx` | Download/share conversation |

### API Client

- `src/webui/app/src/lib/api.ts` - All API communication
- Supports both polling (`sendChatQuery`) and streaming (`streamChatQuery`)
- Currently uses polling only (`stream: false`)

### Language Detection

Client-side phrase matching for 28 languages with confidence scoring.
Falls back to backend `/api/v1/languages/validate` if confidence < 0.5.

### State Management

- React `useState` - no external state library
- Conversation history is client-side only (lost on page refresh)
- No local storage persistence

---

## API Layer

### FastAPI App (`src/webui/api/main.py`)

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/chat/query` | Main chat processing |
| POST | `/api/v1/chat/stream` | SSE streaming (implemented but unused) |
| POST | `/api/v1/languages/validate` | Language detection |
| POST | `/api/v1/feedback/submit` | User feedback |
| GET/POST | `/api/v1/consent/*` | Consent management |
| GET | `/health` | Basic liveness |
| GET | `/health/ready` | Readiness (checks prewarm) |
| GET | `/health/live` | Liveness |

**Middleware:**
- Request ID injection (UUID per request)
- Request logging (timing, status)
- Rate limiting (in-memory, per IP)
- CORS (environment-driven origins)

**Initialization:**
- Async lifespan context manager
- Background prewarm task for heavy resources (BGE-M3, Pinecone index)
- Global pipeline, cache, router, parser instances via FastAPI dependency injection

---

## Azure Deployment

### CI/CD Pipeline (`.github/workflows/deploy-azure.yml`)

```
Push to main
    |
    v
GitHub Actions Runner
    |
    +--> Setup Node.js 20, Python 3.11
    +--> npm install + build (static export)
    +--> pip install requirements.txt
    +--> npm audit + pip-audit
    +--> Azure CLI: set startup command
    +--> azure/webapps-deploy (production slot)
    +--> Health check (60s timeout)
```

### Azure App Service Configuration

- **App Name**: `ClimateReslianceAPP`
- **Startup**: `scripts/startup.sh`
- **Runtime**: Python 3.11
- **Server**: Uvicorn on `$PORT`
- **Working Dir**: `/home/site/wwwroot`
- **Static Files**: `src/webui/app/out/` served at `/_next`
- **Auth**: OIDC token-based (Azure RBAC)

### Startup Script Flow (`scripts/startup.sh`)

1. Set working directory to Azure wwwroot
2. Create/activate virtualenv
3. Install dependencies
4. Export PYTHONPATH
5. Start Uvicorn

### Static File Serving

FastAPI serves the Next.js static export:
- `/_next/*` -> static assets (JS, CSS, images)
- `/*` (catch-all) -> `index.html` (SPA routing)
- `/api/*` -> API routes

---

## Redis Caching Strategy

### Connection (`src/models/redis_cache.py`)

```python
ClimateCache(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    socket_timeout=5s,
    socket_connect_timeout=5s,
    retry_on_timeout=True,
    decode_responses=True
)
```

### Cache Key Format

```
q:{language_code}:{sha256(language_code:normalized_query)}
```

**Important**: Cache keys do NOT include model_type. This is intentional - allows cache sharing across models for the same query+language.

### What's Cached

- Full responses (translated to requested language)
- Citations
- Faithfulness scores
- Processing metadata
- English version (also cached separately for cross-language reuse)

### TTL

- Default: 3600s (1 hour)
- Configurable via `REDIS_CONFIG["expiration"]`

### Redis Persistence (Production)

```conf
save 60 1       # RDB every 60s if 1+ change
appendonly yes  # AOF enabled
appendfsync everysec
maxmemory 512mb
maxmemory-policy allkeys-lru
```

---

## Environment Variables

### Required

| Variable | Purpose |
|----------|---------|
| `AWS_ACCESS_KEY_ID` | AWS Bedrock authentication |
| `AWS_SECRET_ACCESS_KEY` | AWS Bedrock authentication |
| `COHERE_API_KEY` | Cohere API (reranking + generation) |
| `PINECONE_API_KEY` | Pinecone vector database |
| `TAVILY_API_KEY` | Web search fallback |

### Infrastructure

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_HOST` | `localhost` | Redis connection |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | - | Redis auth (optional) |
| `PORT` | - | App server port (set by Azure) |
| `CORS_ORIGINS` | - | Allowed CORS origins (CSV) |
| `ENVIRONMENT` | - | `development`/`staging`/`production` |

### Optional

| Variable | Purpose |
|----------|---------|
| `LANGSMITH_API_KEY` | LangSmith tracing |
| `LANGSMITH_PROJECT` | LangSmith project name |
| `HF_API_TOKEN` | Hugging Face model access |
| `DISABLE_RATE_LIMIT` | Dev override for rate limiting |
| `ENABLE_LOCAL_CHAT_LOGS` | File-based chat logging |
| `EMBEDDING_CACHE_MAX_SIZE` | In-memory embedding cache size |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL |
| `NEXT_PUBLIC_ENVIRONMENT` | Frontend environment flag |

---

## Monitoring & Logging

### Logging Configuration (`src/utils/logging_config.py`)

- **Console**: INFO level
- **File** (`app.log`): DEBUG level, 10MB rotating, 5 backups
- **Error File** (`error.log`): ERROR level, 10MB rotating, 5 backups
- **Encoding**: UTF-8

### System Monitor (`src/utils/system_monitor.py`)

Background async loop (every 60s) tracking:
- CPU usage (alert threshold: 80%)
- Memory usage (alert threshold: 85%)
- Disk usage (alert threshold: 90%)
- Process-specific metrics

### Metrics Collector (`src/utils/metrics.py`)

Thread-safe singleton tracking:
- Operation latency (p50, p95, p99)
- Error rates per operation
- Cache hit/miss rates

### Analytics (`src/utils/analytics.py`)

- Daily query counts
- Unique users
- Language distribution
- Processing times
- Trending topics (keyword extraction)

---

## Known Issues & Technical Debt

### Critical

1. **Streaming endpoint implemented but unused** - `/api/v1/chat/stream` is fully implemented in backend and partially in frontend, but frontend always uses `stream: false`. Either integrate or remove to reduce maintenance burden.

2. **Conversation history not persisted** - Client-side only, lost on page refresh. No local storage or session management.

3. **Cache ignores conversation context** - Cache key is `language + query` only. Multi-turn follow-ups may get wrong cached response if the exact same question was asked in a different conversation context.

### High Priority

4. **Rate limiting is in-memory** - Not shared across workers/instances. Should use Redis-based rate limiter for production.

5. **Pipeline timeout defaults are hardcoded** - Timeouts (30s rewriter, 45s generation, 15s hallucination check) should be configurable via environment variables.

6. **Security scans are non-blocking in CI** - `pip-audit` failures don't prevent deployment.

7. **No actual test suite in CI** - Test step is a placeholder echo command.

### Medium Priority

8. **URL validation disabled** - CORS-related false positives caused it to be commented out. ~400 lines of dead code remain.

9. **Duplicate AppHeader components** - Two versions exist (`src/components/chat/` and `src/app/components/chat/`).

10. **Async Redis wrapping** - `consent.py` wraps sync Redis with `asyncio.to_thread()`. Should use async Redis driver.

11. **Language routing fallback** - Defaults to Cohere Command A on error, which may not support the detected language.

### Low Priority

12. **Unused npm dependencies** - `@hookform/resolvers`, `react-day-picker`, `recharts`, `embla-carousel-react`, `date-fns` appear unused.

13. **Debug console.logs in production** - Frontend has emoji-prefixed debug logs that should be removed.

14. **Legacy wrapper files** - `main_nova.py` and `main_nova_new.py` are near-identical wrappers around `ClimateQueryPipeline`.

---

## Deployment Checklist

### Pre-Deploy

- [ ] All environment variables set in Azure App Service
- [ ] Redis instance running and accessible
- [ ] Pinecone index populated and accessible
- [ ] AWS Bedrock access configured (us-east-1)
- [ ] Cohere API key active
- [ ] Next.js frontend builds successfully (`npm run build`)
- [ ] Python dependencies install cleanly

### Post-Deploy

- [ ] `/health` returns 200
- [ ] `/health/ready` returns `prewarm_completed: true` (may take 30-60s)
- [ ] Test chat query in target language
- [ ] Verify Redis connectivity (check cache hits in logs)
- [ ] Verify Pinecone retrieval (check document count in response)
- [ ] Check CORS headers match frontend origin
- [ ] Verify rate limiting is active (`DISABLE_RATE_LIMIT` not set)

### Rollback Plan

1. Azure App Service supports deployment slots - use staging slot
2. Previous deployment available via Azure deployment history
3. Redis cache is independent - no data migration needed
4. Pinecone index is read-only from app perspective

---

## File Structure Reference

```
src/
├── models/
│   ├── climate_pipeline.py      # Main orchestrator (entry point)
│   ├── query_rewriter.py        # Intent classification + English rewriting
│   ├── query_routing.py         # Language detection + model selection
│   ├── retrieval.py             # BGE-M3 + Pinecone hybrid search
│   ├── rerank.py                # Cohere document reranking
│   ├── gen_response_unified.py  # Unified Nova/Cohere response generation
│   ├── nova_flow.py             # AWS Bedrock Nova client
│   ├── cohere_flow.py           # Cohere API client
│   ├── hallucination_guard.py   # Faithfulness scoring
│   ├── redis_cache.py           # Redis cache wrapper
│   ├── conversation_parser.py   # History format standardization
│   ├── input_guardrail.py       # Topic moderation
│   ├── title_normalizer.py      # Citation title cleanup
│   ├── batch_optimizer.py       # Batch processing (unused)
│   └── system_messages.py       # Shared system prompts
├── utils/
│   ├── env_loader.py            # Environment variable management
│   ├── logging_config.py        # Logging setup
│   ├── system_init.py           # Component initialization
│   ├── system_monitor.py        # Resource monitoring
│   ├── metrics.py               # Performance metrics
│   ├── analytics.py             # Usage analytics
│   ├── error_handler.py         # Error types and recovery
│   └── input_validator.py       # Input sanitization
├── webui/
│   ├── api/
│   │   ├── main.py              # FastAPI app + middleware
│   │   ├── routers/
│   │   │   ├── chat.py          # Chat endpoint
│   │   │   ├── streaming.py     # SSE streaming endpoint
│   │   │   ├── languages.py     # Language detection
│   │   │   ├── feedback.py      # User feedback
│   │   │   └── consent.py       # Consent management
│   │   └── utils/
│   │       └── link_validator.py # URL validation
│   └── app/                     # Next.js frontend
│       ├── src/
│       │   ├── app/             # Pages + layouts
│       │   ├── components/      # React components
│       │   ├── hooks/           # Custom hooks
│       │   └── lib/             # API client + utilities
│       └── out/                 # Static export (build output)
├── data/
│   └── config/
│       └── config.py            # Centralized configuration
scripts/
├── startup.sh                   # Azure startup script
├── build.sh                     # Local build script
├── start-redis.sh               # Redis startup
└── redis.conf                   # Redis configuration
.github/
└── workflows/
    └── deploy-azure.yml         # CI/CD pipeline
```
