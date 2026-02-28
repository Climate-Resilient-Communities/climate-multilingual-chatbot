# Climate Multilingual Chatbot - Infrastructure & Architecture (Updated Feb 2026)

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [What Changed (Feb 2026)](#what-changed-feb-2026)
3. [Pipeline Flow](#pipeline-flow)
4. [LLM Providers & Models](#llm-providers--models)
5. [Language Routing (Tiny-Aya Regional Models)](#language-routing-tiny-aya-regional-models)
6. [RAG Implementation](#rag-implementation)
7. [Frontend Architecture](#frontend-architecture)
8. [API Layer](#api-layer)
9. [Azure Deployment](#azure-deployment)
10. [Redis Caching Strategy](#redis-caching-strategy)
11. [Environment Variables](#environment-variables)
12. [Monitoring & Logging](#monitoring--logging)
13. [Known Issues & Technical Debt](#known-issues--technical-debt)
14. [Deployment Checklist](#deployment-checklist)

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
    +--> Language Routing (MultilingualRouter -> Tiny-Aya regional selection)
    +--> Query Rewriting (BedrockModel / Nova Lite)
    +--> Input Guards (keyword + LLM-based topic checks)
    +--> Document Retrieval (BGE-M3 via HF Inference API -> Pinecone hybrid search)
    +--> Reranking (Cohere rerank-v4.0-fast)
    +--> Response Generation (Tiny-Aya regional model via Cohere API)
    +--> Hallucination Guard (Nova Lite faithfulness check)
    +--> Translation (Cohere Tiny-Aya, Nova Lite fallback)
    +--> Redis Cache (read/write)
    |
    v
Response + Citations
```

**Key Design Decisions:**
- Monolithic deployment: frontend static files served by FastAPI
- English-first generation: all responses generated in English, then translated
- Hybrid search: dense (BGE-M3 via HuggingFace Inference API) + sparse vectors via Pinecone
- Model routing: Cohere Tiny-Aya regional models for generation/translation, Nova as fallback
- No local ML models: all inference is API-based (HuggingFace, Cohere, AWS Bedrock)

---

## What Changed (Feb 2026)

This section summarizes all architectural changes made in the Feb 2026 overhaul.

### Removed Dependencies (~2GB reduction)

| Package | Size | Reason for Removal |
|---------|------|--------------------|
| `torch` | ~800MB | BGE-M3 embeddings moved to HuggingFace Inference API |
| `transformers` | ~400MB | No local model loading needed |
| `FlagEmbedding` | ~50MB | Replaced by `HFEmbedder` class calling HF API |
| `sentence-transformers` | ~100MB | Not used after HF API migration |
| `safetensors` | ~10MB | Only needed for local model loading |
| `tokenizers` | ~10MB | Only needed for local model loading |
| `opencensus` + extensions | ~20MB | Not imported anywhere in source code |
| `azure-storage-blob` | ~10MB | Not imported anywhere in source code |
| ClimateBERT | ~300MB | Topic moderation uses keyword + LLM, not BERT |

**Net result:** Python install size dropped from ~2.2GB to ~200MB. RAM at rest dropped from ~1.5-2GB to ~200-400MB.

### Model Changes

| Component | Before | After |
|-----------|--------|-------|
| **Embeddings** | `BGEM3FlagModel` (local, FlagEmbedding) | `HFEmbedder` (HuggingFace Inference API) |
| **Chat/Generation** | Cohere `command-a-03-2025` + Nova | Cohere Tiny-Aya regional models (`tiny-aya-global/fire/earth/water`) |
| **Translation** | Nova Lite (primary) | Cohere Tiny-Aya (primary), Nova Lite (fallback) |
| **Reranking** | Cohere `rerank-english-v3.0` | Cohere `rerank-v4.0-fast` |
| **Topic Moderation** | ClimateBERT (removed earlier) | Keyword + Nova LLM (unchanged) |

### Azure App Service Plan

With torch/transformers removed, the app no longer needs a high-memory plan:

| Plan | vCPU | RAM | Price | Recommendation |
|------|------|-----|-------|----------------|
| **B1** | 1 | 1.75 GB | ~$13/mo | Sufficient for API-only workload |
| **B2** | 2 | 3.5 GB | ~$26/mo | Recommended if running Streamlit + FastAPI together |
| B3 | 4 | 7 GB | ~$53/mo | Overkill - was needed when running torch |

### Files Modified

| File | Change |
|------|--------|
| `src/models/cohere_flow.py` | Added `HFEmbedder`, `resolve_tiny_aya_model()`, `with_model()`, language frozensets |
| `src/models/query_routing.py` | Replaced `COMMAND_A`/`NOVA` enum with `TINY_AYA_GLOBAL/FIRE/EARTH/WATER/NOVA` |
| `src/models/climate_pipeline.py` | Uses `HFEmbedder()` and Tiny-Aya routing with `cohere_model.with_model()` |
| `src/models/retrieval.py` | Removed local FlagEmbedding import, works with HFEmbedder |
| `src/models/rerank.py` | Model changed to `rerank-v4.0-fast` |
| `src/main_nova.py` | Uses `HFEmbedder` instead of `BGEM3FlagModel` |
| `src/webui/api/routers/languages.py` | Uses Tiny-Aya language sets instead of `COMMAND_A_SUPPORTED_LANGUAGES` |
| `src/webui/api/routers/chat.py` | Updated model routing for Tiny-Aya |
| `src/webui/api/routers/streaming.py` | Updated model routing for Tiny-Aya |
| `requirements.txt` | Removed torch/transformers/FlagEmbedding, added `huggingface-hub>=0.25.0` |
| `pyproject.toml` | Removed heavy deps, added `huggingface-hub ^0.25.0` |

---

## Pipeline Flow

The core pipeline lives in `src/models/climate_pipeline.py` (`ClimateQueryPipeline`).

### Step-by-Step Processing:

| Step | Module | Description | Timeout |
|------|--------|-------------|---------|
| 1. Cache Check | `redis_cache.py` | Exact + fuzzy cache lookup | - |
| 2. Language Routing | `query_routing.py` | Detect language, select Tiny-Aya regional model | - |
| 3. Query Rewriting | `query_rewriter.py` | Classify intent + rewrite to English | 30s |
| 4. Input Guards | `input_guardrail.py` | Topic moderation (climate-only) | - |
| 5. Document Retrieval | `retrieval.py` | HFEmbedder (BGE-M3 via HF API) -> Pinecone search -> Cohere rerank | - |
| 6. Response Generation | `gen_response_unified.py` | Tiny-Aya (Cohere) or Nova generates English response | 45s |
| 7. Hallucination Guard | `hallucination_guard.py` | Faithfulness scoring via Nova Lite | 15s |
| 8. Translation | `cohere_flow.py` / `nova_flow.py` | Translate to target language if needed | 30s |
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

### Cohere (Primary - Chat, Translation, Reranking)

- **Client**: `src/models/cohere_flow.py` (`CohereModel`)
- **Chat Models**: Tiny-Aya regional models (see [Language Routing](#language-routing-tiny-aya-regional-models))
  - `tiny-aya-global` (default - English + catch-all)
  - `tiny-aya-fire` (South Asian languages)
  - `tiny-aya-earth` (African languages)
  - `tiny-aya-water` (Asia-Pacific + Western Asia + European languages)
- **Rerank Model**: `rerank-v4.0-fast`
- **Used For**: Response generation, translation, classification, query normalization, document reranking
- **Invocation**: Sync client via `asyncio.get_event_loop().run_in_executor()`
- **Model Switching**: `CohereModel.with_model(model_id)` creates a lightweight copy sharing the same API client
- **Rerank Timeout**: 10s (via `ThreadPoolExecutor` + `future.result(timeout=10)`)
- **Rerank Payload**: Documents clipped to 1500 chars each to control payload size

### AWS Bedrock (Nova - Fallback)

- **Client**: `src/models/nova_flow.py` (`BedrockModel`)
- **Default Model**: `amazon.nova-lite-v1:0`
- **Region**: `us-east-1`
- **Used For**: Query rewriting, classification, fallback translation, faithfulness evaluation
- **Parameters**:
  - `temperature`: 0.1 (deterministic)
  - `topP`: 0.9
  - `maxTokens`: 800 (content gen) / 1500 (responses) / 10000 (translation/normalization)
- **Invocation**: Sync client via `asyncio.to_thread()` to avoid event loop issues
- **Timeouts**: 30s hard timeout via `asyncio.wait_for()`
- **Retry**: 2 max attempts with adaptive mode (botocore built-in)

### HuggingFace Inference API (Embeddings)

- **Client**: `src/models/cohere_flow.py` (`HFEmbedder`)
- **Model**: `BAAI/bge-m3`
- **Used For**: Dense query embeddings (1024-dim vectors) for Pinecone hybrid search
- **API Method**: `InferenceClient.feature_extraction()`
- **Batch Size**: 32 texts per API call
- **Output Handling**: Handles 1D, 2D, and 3D array shapes from HF API (takes CLS token for 3D)
- **Sparse Weights**: Returns empty dicts (pipeline handles sparse-absent via alpha weighting)
- **Auth**: `HF_TOKEN` environment variable
- **Drop-in Replacement**: Returns same `{'dense_vecs': np.ndarray, 'lexical_weights': [...]}` dict as the old local `BGEM3FlagModel`

### Removed Models

| Model | Status | Reason |
|-------|--------|--------|
| ClimateBERT (`distilroberta-base-climate-detector`) | Removed Feb 2026 | Never called in active pipeline; pulled in torch/transformers for zero benefit |
| Local BGE-M3 (`BGEM3FlagModel`) | Replaced Feb 2026 | Moved to HuggingFace Inference API; same 1024-dim vectors, no local GPU/CPU needed |
| Cohere `command-a-03-2025` | Replaced Feb 2026 | Switched to Tiny-Aya regional models for better multilingual coverage |
| Cohere `rerank-english-v3.0` | Upgraded Feb 2026 | Upgraded to `rerank-v4.0-fast` for improved performance |

---

## Language Routing (Tiny-Aya Regional Models)

Language routing is handled by `src/models/query_routing.py` (`MultilingualRouter`) with regional language sets defined in `src/models/cohere_flow.py`.

### Model Selection Logic

```python
def resolve_tiny_aya_model(language_code: str) -> Tuple[str, str]:
    """Priority: fire -> earth -> water -> global."""
    lc = (language_code or 'en').lower().split('-')[0]
    if lc in FIRE_LANGUAGES:  return 'tiny-aya-fire', 'fire'
    if lc in EARTH_LANGUAGES: return 'tiny-aya-earth', 'earth'
    if lc in WATER_LANGUAGES: return 'tiny-aya-water', 'water'
    return 'tiny-aya-global', 'global'
```

### Regional Model Coverage

| Model | Region | Languages |
|-------|--------|-----------|
| `tiny-aya-fire` | South Asian | hi, bn, pa, ur, gu, ta, te, mr, ne, si, ml, kn, or, as, sd, ks |
| `tiny-aya-earth` | African | sw, yo, ha, ig, am, so, rw, sn, zu, xh, st, tn, ny, lg, wo, ff, bm, ti, om, rn |
| `tiny-aya-water` | Asia-Pacific + Western Asia + Europe | zh, ja, ko, th, vi, id, ms, tl, my, km, lo, mn, ka, jv, ar, he, fa, tr, ku, ru, uk, pl, cs, ro, el, bg, sr, hr, sk, sl, hu, lt, lv, et, nl, de, fr, it, pt, es, sv, da, no, fi, is, ca, gl, eu, sq, bs, mk, mt |
| `tiny-aya-global` | Global (default) | en + all other languages not in fire/earth/water |

### Routing Enum

```python
class LanguageSupport(Enum):
    TINY_AYA_GLOBAL = "tiny_aya_global"
    TINY_AYA_FIRE   = "tiny_aya_fire"
    TINY_AYA_EARTH  = "tiny_aya_earth"
    TINY_AYA_WATER  = "tiny_aya_water"
    NOVA            = "nova"  # Fallback only
```

### Model Switching Pattern

The `CohereModel.with_model()` method creates a lightweight copy that shares the same authenticated API client but uses a different model ID. This avoids creating new HTTP connections for each regional model:

```python
# In climate_pipeline.py
model_id, region = resolve_tiny_aya_model(language_code)
regional_model = self.cohere_model.with_model(model_id)
response = await regional_model.generate_response(query, documents)
```

---

## RAG Implementation

### Embedding & Search

```
Query -> HFEmbedder (BGE-M3 via HuggingFace Inference API) -> {dense_vec (1024-dim)}
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
                    (rerank-v4.0-fast)
                              |
                              v
                    Final Ranked Documents
```

### Embedding Details

- **Model**: `BAAI/bge-m3` via HuggingFace Inference API
- **Dimensions**: 1024 (matches existing Pinecone index - no re-embedding needed)
- **Class**: `HFEmbedder` in `src/models/cohere_flow.py`
- **Interface**: Identical to old `BGEM3FlagModel.encode()` - returns `{'dense_vecs': np.ndarray, 'lexical_weights': [...]}`
- **Sparse vectors**: Empty dicts (HF Inference API doesn't return lexical weights; pipeline handles this via alpha weighting)

### Key Configuration (from `src/data/config/config.py`):

- **Pinecone Index**: Environment-driven (`PINECONE_INDEX_NAME`)
- **Top-K**: 8 (default)
- **Alpha**: 0.5 (50% dense, 50% sparse)
- **Domain Blocklist**: `{"lsf-lst.ca", "climatelearning.ca"}`
- **Audience Blocklist**: K-12 educational content patterns

### Reranking

- **Model**: `rerank-v4.0-fast` (upgraded from `rerank-english-v3.0`)
- **Timeout**: 10s hard timeout via `ThreadPoolExecutor`
- **Payload Control**: Documents clipped to 1500 chars each
- **Fallback**: If reranking fails or times out, returns original Pinecone-ordered documents

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
| GET | `/api/v1/languages/supported` | Get supported languages by region |
| POST | `/api/v1/languages/validate` | Language detection + model recommendation |
| POST | `/api/v1/feedback/submit` | User feedback |
| GET/POST | `/api/v1/consent/*` | Consent management |
| GET | `/health` | Basic liveness |
| GET | `/health/ready` | Readiness (checks prewarm) |
| GET | `/health/live` | Liveness |

**Languages Endpoint Response (updated):**

The `/api/v1/languages/supported` endpoint now returns languages grouped by Tiny-Aya region:

```json
{
  "tiny_aya_fire_languages": [{"code": "hi", "name": "hindi"}, ...],
  "tiny_aya_earth_languages": [{"code": "sw", "name": "swahili"}, ...],
  "tiny_aya_water_languages": [{"code": "zh", "name": "chinese"}, ...],
  "tiny_aya_global_note": "English and all other languages not listed above",
  "default_language": "en",
  "total_supported": 69
}
```

**Middleware:**
- Request ID injection (UUID per request)
- Request logging (timing, status)
- Rate limiting (in-memory, per IP)
- CORS (environment-driven origins)

**Initialization:**
- Async lifespan context manager
- Background prewarm task for embeddings (single HFEmbedder warmup call) and Pinecone index
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
- **Recommended Plan**: B1 (1 vCPU, 1.75GB RAM, ~$13/mo) or B2 (~$26/mo with headroom)
- **Startup**: `scripts/startup.sh`
- **Runtime**: Python 3.11
- **Server**: Uvicorn on `$PORT`
- **Working Dir**: `/home/site/wwwroot`
- **Static Files**: `src/webui/app/out/` served at `/_next`
- **Auth**: OIDC token-based (Azure RBAC)

**Why B1/B2 is sufficient:** All heavy computation (embeddings, chat, reranking) is offloaded to external APIs (HuggingFace, Cohere, AWS Bedrock). The app is an API orchestrator, not an ML inference server.

### Startup Script Flow (`scripts/startup.sh`)

1. Set working directory to Azure wwwroot
2. Create/activate virtualenv
3. Install dependencies (~200MB total, completes in ~30s)
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
| `COHERE_API_KEY` | Cohere API (Tiny-Aya chat, reranking, translation) |
| `PINECONE_API_KEY` | Pinecone vector database |
| `TAVILY_API_KEY` | Web search fallback |
| `HF_TOKEN` | HuggingFace Inference API (BGE-M3 embeddings) |

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
| `HUGGINGFACE_TOKEN` | Alternative name for `HF_TOKEN` (fallback) |
| `DISABLE_RATE_LIMIT` | Dev override for rate limiting |
| `ENABLE_LOCAL_CHAT_LOGS` | File-based chat logging |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL |
| `NEXT_PUBLIC_ENVIRONMENT` | Frontend environment flag |

**Note:** `HF_TOKEN` is the primary env var name for HuggingFace authentication. `HUGGINGFACE_TOKEN` is accepted as a fallback. Set this in Azure App Service configuration and in your local `.env` file.

---

## Monitoring & Logging

### Logging Configuration (`src/utils/logging_config.py`)

- **Console**: INFO level
- **File** (`app.log`): DEBUG level, 10MB rotating, 5 backups
- **Error File** (`error.log`): ERROR level, 10MB rotating, 5 backups
- **Encoding**: UTF-8

### External Dependency Logging

All external API calls include structured log lines for monitoring:

```
dep=cohere_rerank host=api.cohere.com op=rerank ms=245.3 status=OK
dep=cohere_rerank payload_chars=12000 n_docs=8
dep=pinecone host=xxx.pinecone.io op=init status=OK
```

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

8. **Sparse vectors not available from HF API** - The HuggingFace Inference API for BGE-M3 returns dense vectors only. Lexical/sparse weights are returned as empty dicts. The pipeline handles this gracefully via alpha weighting, but hybrid search effectiveness may be slightly reduced compared to local BGE-M3 with full sparse support.

9. **Duplicate AppHeader components** - Two versions exist (`src/components/chat/` and `src/app/components/chat/`).

10. **Async Redis wrapping** - `consent.py` wraps sync Redis with `asyncio.to_thread()`. Should use async Redis driver.

11. **Legacy wrapper files** - `main_nova.py` is a legacy wrapper around `ClimateQueryPipeline`. Most traffic should go through the FastAPI endpoints directly.

### Low Priority

12. **Unused npm dependencies** - `@hookform/resolvers`, `react-day-picker`, `recharts`, `embla-carousel-react`, `date-fns` appear unused.

13. **Debug console.logs in production** - Frontend has emoji-prefixed debug logs that should be removed.

14. **Documentation files may reference old architecture** - `docs/pinecone.md`, `onboarding/` docs still reference FlagEmbedding/BGEM3FlagModel. These are informational only and don't affect runtime.

---

## Deployment Checklist

### Pre-Deploy

- [ ] All environment variables set in Azure App Service (including `HF_TOKEN`)
- [ ] Redis instance running and accessible
- [ ] Pinecone index populated and accessible (1024-dim dense vectors)
- [ ] AWS Bedrock access configured (us-east-1)
- [ ] Cohere API key active (supports Tiny-Aya models + rerank-v4.0-fast)
- [ ] HuggingFace API token active (`HF_TOKEN`)
- [ ] Next.js frontend builds successfully (`npm run build`)
- [ ] Python dependencies install cleanly (~200MB)
- [ ] Azure App Service plan is B1 or higher

### Post-Deploy

- [ ] `/health` returns 200
- [ ] `/health/ready` returns `prewarm_completed: true` (may take 10-15s - faster than before)
- [ ] Test chat query in English (should route to `tiny-aya-global`)
- [ ] Test chat query in Hindi (should route to `tiny-aya-fire`)
- [ ] Test chat query in Spanish (should route to `tiny-aya-water`)
- [ ] Verify Redis connectivity (check cache hits in logs)
- [ ] Verify Pinecone retrieval (check document count in response)
- [ ] Check CORS headers match frontend origin
- [ ] Verify rate limiting is active (`DISABLE_RATE_LIMIT` not set)

### Rollback Plan

1. Azure App Service supports deployment slots - use staging slot
2. Previous deployment available via Azure deployment history
3. Redis cache is independent - no data migration needed
4. Pinecone index is read-only from app perspective (1024-dim vectors unchanged)

---

## File Structure Reference

```
src/
├── models/
│   ├── climate_pipeline.py      # Main orchestrator (entry point)
│   ├── query_rewriter.py        # Intent classification + English rewriting
│   ├── query_routing.py         # Language detection + Tiny-Aya model selection
│   ├── retrieval.py             # HFEmbedder + Pinecone hybrid search
│   ├── rerank.py                # Cohere rerank-v4.0-fast
│   ├── gen_response_unified.py  # Unified Tiny-Aya/Nova response generation
│   ├── nova_flow.py             # AWS Bedrock Nova client (fallback)
│   ├── cohere_flow.py           # Cohere API client + HFEmbedder + Tiny-Aya routing
│   ├── hallucination_guard.py   # Faithfulness scoring
│   ├── redis_cache.py           # Redis cache wrapper
│   ├── conversation_parser.py   # History format standardization
│   ├── input_guardrail.py       # Topic moderation (keyword + LLM)
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
│   │   │   ├── languages.py     # Language support (Tiny-Aya regions)
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
