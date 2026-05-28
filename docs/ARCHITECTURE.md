## System Architecture

The diagram below reflects the current production architecture (updated Feb 2026) with FastAPI backend, Next.js frontend, Cohere Tiny-Aya regional model routing, HuggingFace-hosted embeddings, and community-specific RAG with Tavily web supplement.

```mermaid
flowchart TD
  U["User"] --> UI["Next.js Frontend\n`src/webui/app/`\n- Static export build\n- TypeScript + Tailwind CSS\n- Real-time SSE streaming\n- Export functionality"]

  UI --> API["FastAPI Backend\n`src/webui/api/main.py`\n- Serves both API + static files\n- CORS protection\n- Health monitoring"]
  API --> CP["ClimateQueryPipeline\n`src/models/climate_pipeline.py`"]

  CP --> QR["Query Rewriter (Nova Lite)\n`src/models/query_rewriter.py`\n- Detects: greeting, goodbye, thanks, emergency, instruction, on/off-topic/harmful\n- Outputs: classification, rewrite_en"]

  QR -- canned intent --> CANNED["Canned response\n(Translated to user language)"]
  QR -- instruction --> HOWTO["Show 'How It Works' text"]
  QR -- on-topic --> ROUTE["Language Router\n`src/models/query_routing.py`\n- Selects Tiny-Aya regional model\n- fire/earth/water/global"]

  ROUTE --> MT{Regional Model?}
  MT -- "Tiny-Aya\n(fire/earth/water/global)" --> PRE_COH["Translate to English\n(Tiny-Aya)"]
  MT -- "Nova (fallback)" --> PRE_NOVA["Translate to English\n(Nova Lite)"]

  PRE_COH --> RET["Retrieval\n`src/models/retrieval.py`\n- BGE-M3 via HuggingFace Inference API\n- Pinecone hybrid search"]
  PRE_NOVA --> RET
  RET --> TAV_SUP["Tavily Web Supplement\n(community queries only)\n- Up to 3 fresh .ca sources"]
  TAV_SUP --> RR["Rerank\n`src/models/rerank.py`\n- Cohere rerank-v4.0-fast"]
  RR --> GEN["Response Generation\n`src/models/gen_response_unified.py`\n- Tiny-Aya regional model\n- Nova Lite fallback"]

  GEN --> QG["Quality Checks\n`src/models/hallucination_guard.py`\n- Faithfulness scoring (Nova Lite)"]
  QG -- ok --> POST{Translate back?}
  QG -- low faithfulness --> TAV["Fallback Search\n(Tavily)"] --> POST

  POST -- "Tiny-Aya" --> TGT_COH["Translate to user language\n(Tiny-Aya)"]
  POST -- "Nova" --> TGT_NOVA["Translate to user language\n(Nova Lite)"]

  TGT_COH --> UIRET["Return response + citations to UI"]
  TGT_NOVA --> UIRET
  CANNED --> UI
  HOWTO --> UI
  UIRET --> UI

  subgraph Support & Config
    ENV["Environment Loader\n`src/utils/env_loader.py`\n`src/data/config/config.py`"]
    LANGS["Languages mapping\n`src/utils/languages.json`"]
    CACHE["Redis Cache\n`src/models/redis_cache.py`\n- Skip cache functionality\n- Performance optimization"]
    LOGS["System Monitoring\n`src/utils/system_monitor.py`"]
  end

  ENV --> API
  LANGS --> CP
  CACHE --> CP
  API -. metrics/monitoring .-> LOGS
  RET -. diagnostics .-> LOGS
```

## Architecture Notes

### Production Deployment
- **Single Deployment Model**: FastAPI serves both API endpoints and Next.js static files
- **Static Export**: Next.js builds to static files for optimal performance
- **Port 8000**: All traffic (frontend + API) goes through FastAPI on port 8000
- **Azure App Service**: B1/B2 plan sufficient (~$13-26/mo) — all inference is API-based, no local ML models

### Intelligent Features
- **Canned Responses**: greeting/goodbye/thanks/emergency bypass retrieval for fast responses
- **Safety Filtering**: Off-topic/harmful queries return helpful guidance messages
- **Cache Bypass**: Retry functionality skips cache for fresh responses
- **Manual Language Selection**: Users can anchor language selection to prevent auto-detection
- **Community-Specific Knowledge**: System prompt includes verified Thorncliffe Park data with hallucination guard for other communities
- **Tavily Web Supplement**: Community queries automatically pull fresh web results from trusted .ca domains

### Model Routing (Cohere Tiny-Aya Regional)
- **Tiny-Aya Fire (South Asian)**: Hindi, Bengali, Punjabi, Urdu, Gujarati, Tamil, Telugu, Marathi, Nepali, Sinhala, Malayalam, Kannada, Odia, Assamese, Sindhi, Kashmiri
- **Tiny-Aya Earth (African)**: Swahili, Yoruba, Hausa, Igbo, Amharic, Somali, Kinyarwanda, Shona, Zulu, Xhosa, and 10 more
- **Tiny-Aya Water (Asia-Pacific + Europe)**: Chinese, Japanese, Korean, Thai, Vietnamese, Indonesian, Arabic, Hebrew, Persian, Turkish, Russian, Ukrainian, Polish, Czech, Romanian, Greek, French, German, Spanish, Italian, Portuguese, Dutch, Swedish, Danish, Norwegian, Finnish, and more
- **Tiny-Aya Global (default)**: English + all languages not covered above
- **Nova Lite (fallback)**: Used for query rewriting, classification, and faithfulness evaluation

### Embeddings & Retrieval
- **BGE-M3** via HuggingFace Inference API (1024-dim dense vectors)
- **Pinecone** hybrid search (dense + sparse, alpha=0.5)
- **Cohere rerank-v4.0-fast** for document reranking
- **No local models**: All inference is API-based (~200MB install vs previous ~2.2GB)

### Performance Optimizations
- **Redis Caching**: Improves response times with intelligent bypass
- **Static Assets**: Optimized builds with compression
- **Streaming Responses**: Server-sent events for real-time user experience
- **Language Detection**: <100ms response time for language identification
- **API-only architecture**: Cold start ~30s (vs ~2-3min with local torch models)
