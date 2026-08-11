# High-Level Architecture Diagram

This document provides a visual overview of the Dunia — Multilingual Climate Chatbot system architecture.

---

## System Overview

```
                                    DUNIA — MULTILINGUAL CLIMATE CHATBOT
    ════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                              USER LAYER                                  │
    │  ┌─────────────────────────────────────────────────────────────────┐    │
    │  │                         Web Browser                              │    │
    │  │   • Desktop / Mobile                                             │    │
    │  │   • 180+ Language Support                                        │    │
    │  │   • Real-time Chat Interface                                     │    │
    │  └─────────────────────────────────────────────────────────────────┘    │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        │ HTTPS
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           PRESENTATION LAYER                             │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                    Next.js 14 Frontend                              │ │
    │  │                                                                     │ │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │ │
    │  │  │ Chat Window  │  │  Language    │  │   Citations Panel        │  │ │
    │  │  │              │  │  Selector    │  │   • Source Links         │  │ │
    │  │  │ • Messages   │  │  (180+)      │  │   • PDF Export           │  │ │
    │  │  │ • Streaming  │  │              │  │   • Feedback             │  │ │
    │  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │ │
    │  │                                                                     │ │
    │  │  Tech: React 18, TypeScript, Tailwind CSS, shadcn/ui               │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Location: src/webui/app/                                               │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        │ REST API / SSE
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                            APPLICATION LAYER                             │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │                    FastAPI Backend (Port 8000)                      │ │
    │  │                                                                     │ │
    │  │  ┌──────────────────────────────────────────────────────────────┐  │ │
    │  │  │                      API Routers                              │  │ │
    │  │  │  ┌────────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │  │ │
    │  │  │  │   /chat    │ │/languages │ │ /feedback │ │  /consent   │  │  │ │
    │  │  │  │  • query   │ │ • list    │ │ • submit  │ │  • check    │  │  │ │
    │  │  │  │  • stream  │ │ • detect  │ │ • types   │ │  • accept   │  │  │ │
    │  │  │  └────────────┘ └───────────┘ └───────────┘ └─────────────┘  │  │ │
    │  │  └──────────────────────────────────────────────────────────────┘  │ │
    │  │                                                                     │ │
    │  │  ┌──────────────────────────────────────────────────────────────┐  │ │
    │  │  │                      Middleware                               │  │ │
    │  │  │  • Rate Limiting (20 req/min prod)                           │  │ │
    │  │  │  • CORS Protection                                            │  │ │
    │  │  │  • Request Logging                                            │  │ │
    │  │  │  • Error Handling                                             │  │ │
    │  │  └──────────────────────────────────────────────────────────────┘  │ │
    │  │                                                                     │ │
    │  │  Tech: FastAPI, Uvicorn, Python 3.11+                              │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Location: src/webui/api/                                               │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          AI PROCESSING LAYER                             │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────────┐ │
    │  │               ClimateQueryPipeline (Orchestrator)                   │ │
    │  │                                                                     │ │
    │  │  ┌───────────────────────────────────────────────────────────────┐ │ │
    │  │  │ Route → Rewrite → Retrieve → Rerank → Generate → Guard → Cache│ │ │
    │  │  └───────────────────────────────────────────────────────────────┘ │ │
    │  │                                                                     │ │
    │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │ │
    │  │  │  Language   │ │   Query     │ │  Response   │ │Hallucination│   │ │
    │  │  │   Router    │ │  Rewriter   │ │  Generator  │ │   Guard     │   │ │
    │  │  │             │ │             │ │             │ │             │   │ │
    │  │  │ • 180+ lang │ │ • Intent    │ │ • Nova/     │ │ • Faithful- │   │ │
    │  │  │ • Model     │ │   classify  │ │   Cohere    │ │   ness      │   │ │
    │  │  │   selection │ │ • Canned    │ │ • Citation  │ │   scoring   │   │ │
    │  │  │             │ │   responses │ │   building  │ │ • Fallback  │   │ │
    │  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │ │
    │  │                                                                     │ │
    │  │  ┌─────────────────────────────────────────────────────────────┐   │ │
    │  │  │                    Document Retrieval                        │   │ │
    │  │  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐      │   │ │
    │  │  │  │  BGE-M3       │ │    Pinecone   │ │    Cohere     │      │   │ │
    │  │  │  │  Embeddings   │ │  Vector DB    │ │   Reranker    │      │   │ │
    │  │  │  │               │ │               │ │               │      │   │ │
    │  │  │  │ • Multilingual│ │ • Hybrid      │ │ • Relevance   │      │   │ │
    │  │  │  │ • Dense+Sparse│ │   search      │ │   scoring     │      │   │ │
    │  │  │  └───────────────┘ └───────────────┘ └───────────────┘      │   │ │
    │  │  └─────────────────────────────────────────────────────────────┘   │ │
    │  │                                                                     │ │
    │  └────────────────────────────────────────────────────────────────────┘ │
    │                                                                          │
    │  Location: src/models/                                                  │
    └───────────────────────────────────┬─────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                          EXTERNAL SERVICES LAYER                         │
    │                                                                          │
    │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐            │
    │  │    AWS     │ │   Cohere   │ │  Pinecone  │ │   Redis    │            │
    │  │  Bedrock   │ │    API     │ │  Vector DB │ │   Cache    │            │
    │  │            │ │            │ │            │ │            │            │
    │  │ Nova LLM   │ │ Command-A  │ │ Climate    │ │ Response   │            │
    │  │ 6 langs    │ │ 22+ langs  │ │ Documents  │ │ Caching    │            │
    │  │            │ │ Reranking  │ │ 10K+ docs  │ │ 1hr TTL    │            │
    │  └────────────┘ └────────────┘ └────────────┘ └────────────┘            │
    │                                                                          │
    │  ┌────────────┐                                                          │
    │  │   Tavily   │  ◄── Fallback when documents are insufficient            │
    │  │ Web Search │                                                          │
    │  └────────────┘                                                          │
    └─────────────────────────────────────────────────────────────────────────┘

    ════════════════════════════════════════════════════════════════════════════
```

---

## Simplified View

For those who prefer a simpler mental model:

```
    ┌───────────┐          ┌───────────┐          ┌───────────┐
    │           │   HTTP   │           │  Python  │           │
    │   User    │ ───────▶ │  FastAPI  │ ───────▶ │ AI Models │
    │  Browser  │          │  Server   │          │  Pipeline │
    │           │ ◀─────── │           │ ◀─────── │           │
    └───────────┘          └───────────┘          └───────────┘
                                │                       │
                                │                       │
                                ▼                       ▼
                          ┌───────────┐          ┌───────────┐
                          │   Redis   │          │  External │
                          │   Cache   │          │   APIs    │
                          └───────────┘          └───────────┘
```

---

## Technology Stack Summary

| Layer | Technologies | Purpose |
|-------|-------------|---------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind, shadcn/ui | User interface |
| **Backend** | FastAPI, Uvicorn, Python 3.11 | API server |
| **AI/ML** | AWS Bedrock Nova, Cohere Command-A, BGE-M3, LangChain | Language models |
| **Vector DB** | Pinecone | Document storage & search |
| **Caching** | Redis | Response caching |
| **Deployment** | Azure App Service, GitHub Actions | CI/CD |

---

## Key File Locations

```
src/
├── webui/
│   ├── api/
│   │   ├── main.py              ← FastAPI application entry
│   │   └── routers/
│   │       ├── chat.py          ← Chat endpoints
│   │       ├── languages.py     ← Language endpoints
│   │       ├── feedback.py      ← Feedback endpoints
│   │       └── consent.py       ← Consent endpoints
│   │
│   └── app/
│       └── src/
│           ├── app/
│           │   └── page.tsx     ← Main chat component
│           └── components/
│               └── chat/        ← Chat UI components
│
└── models/
    ├── climate_pipeline.py      ← Main AI orchestrator
    ├── query_routing.py         ← Language routing
    ├── retrieval.py             ← Document retrieval
    ├── nova_flow.py             ← AWS Bedrock integration
    ├── cohere_flow.py           ← Cohere integration
    └── hallucination_guard.py   ← Quality checking
```

---

## Learn More

- [AI Pipeline Flow](./02-ai-pipeline-flow.md) - Detailed processing steps
- [Data Flow Diagram](./03-data-flow.md) - How data moves through the system
- [Component Interactions](./04-component-interactions.md) - How components communicate
