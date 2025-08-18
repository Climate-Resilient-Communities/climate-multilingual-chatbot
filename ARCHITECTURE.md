## System Architecture

The diagram below reflects the current production architecture with FastAPI backend, Next.js frontend, intelligent model routing, comprehensive multilingual support, and advanced safety filtering.

```mermaid
flowchart TD
  U["User"] --> UI["Next.js Frontend\n`src/webui/app/`\n- Static export build\n- TypeScript + Tailwind CSS\n- Real-time SSE streaming\n- Export functionality"]

  UI --> API["FastAPI Backend\n`src/webui/api/main.py`\n- Serves both API + static files\n- CORS protection\n- Health monitoring"]
  API --> CP["ClimateQueryPipeline\n`src/models/climate_pipeline.py`"]

  CP --> QR["Query Rewriter (LLM JSON)\n`src/models/query_rewriter.py`\n- Detects: greeting, goodbye, thanks, emergency, instruction, on/off-topic/harmful\n- Outputs: classification, rewrite_en, ask_how_to_use, how_it_works"]

  QR -- canned intent --> CANNED["Canned response\n(Translated to user language)"]
  QR -- instruction --> HOWTO["Show 'How It Works' text"]
  QR -- on-topic --> ROUTE["Language Router\n`src/models/query_routing.py`\n- Determines model: Nova vs Command‑A\n- Decides translation provider"]

  ROUTE --> MT{Model Type?}
  MT -- Command‑A --> PRE_COH["Translate to English\n(Command‑A)"]
  MT -- Nova --> PRE_NOVA["Translate to English\n(Nova)"]

  PRE_COH --> RET["Retrieval\n`src/models/retrieval.py`\n- Pinecone + BGE‑M3"]
  PRE_NOVA --> RET
  RET --> RR["Rerank\n`src/models/rerank.py` (Cohere)"]
  RR --> GEN["Response Generation\n`src/models/gen_response_nova.py` (Nova)"]

  GEN --> QG["Quality Checks\n`src/models/hallucination_guard.py`\n- Faithfulness (Cohere)"]
  QG -- ok --> POST{Translate back?}
  QG -- low faithfulness --> TAV["Fallback Search\n(Tavily)"] --> POST

  POST -- Command‑A --> TGT_COH["Translate to user language\n(Command‑A)"]
  POST -- Nova --> TGT_NOVA["Translate to user language\n(Nova)"]

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

### Intelligent Features
- **Canned Responses**: greeting/goodbye/thanks/emergency bypass retrieval for fast responses
- **Safety Filtering**: Off-topic/harmful queries return helpful guidance messages
- **Cache Bypass**: Retry functionality skips cache for fresh responses
- **Manual Language Selection**: Users can anchor language selection to prevent auto-detection

### Model Routing
- **Command‑A (22 languages)**: Arabic, Bengali, Chinese, Filipino, French, Gujarati, Korean, Persian, Russian, Tamil, Urdu, Vietnamese, Polish, Turkish, Dutch, Czech, Indonesian, Ukrainian, Romanian, Greek, Hindi, Hebrew
- **Nova (6 languages)**: English, Spanish, Japanese, German, Swedish, Danish
- **Automatic Detection**: System detects user language and routes to appropriate model

### Performance Optimizations
- **Redis Caching**: Improves response times with intelligent bypass
- **Static Assets**: Optimized builds with compression
- **Streaming Responses**: Server-sent events for real-time user experience
- **Language Detection**: <100ms response time for language identification


