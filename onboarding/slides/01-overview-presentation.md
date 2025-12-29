# Climate Multilingual Chatbot
## Technical Overview Presentation

---

# Slide 1: Welcome

## Climate Multilingual Chatbot

**An AI-powered assistant for climate change information**

- 180+ languages supported
- Source-cited responses
- Built for climate-resilient communities

---

# Slide 2: What Problem Are We Solving?

## The Challenge

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   "I want to learn about climate change,                    │
│    but I can't find information in my language"             │
│                                                              │
│   "I don't trust AI answers - they might be made up"        │
│                                                              │
│   "I need information specific to my region"                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Our Solution

- **Multilingual**: Answers in 180+ languages
- **Cited**: Every claim has a source
- **Local**: Canadian/Toronto-focused content

---

# Slide 3: High-Level Architecture

```
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │             │     │             │     │             │
    │   Browser   │────▶│   FastAPI   │────▶│ AI Pipeline │
    │  (Next.js)  │     │   Backend   │     │    (RAG)    │
    │             │◀────│             │◀────│             │
    └─────────────┘     └─────────────┘     └─────────────┘
                               │                   │
                               ▼                   ▼
                         ┌───────────┐      ┌───────────┐
                         │   Redis   │      │ External  │
                         │   Cache   │      │   APIs    │
                         └───────────┘      └───────────┘
```

**Three Main Layers:**
1. Frontend (React/Next.js)
2. Backend (FastAPI)
3. AI Pipeline (RAG)

---

# Slide 4: Technology Stack

## Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| shadcn/ui | Components |

## Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | API framework |
| Python 3.11 | Runtime |
| Uvicorn | ASGI server |

## AI/ML
| Technology | Purpose |
|------------|---------|
| AWS Bedrock Nova | LLM (6 languages) |
| Cohere Command-A | LLM (22+ languages) |
| BGE-M3 | Embeddings |
| Pinecone | Vector database |

---

# Slide 5: What is RAG?

## Retrieval-Augmented Generation

```
┌────────────────────────────────────────────────────────────┐
│                                                             │
│  Traditional AI:                                            │
│  Question → LLM → Answer (might be made up!)               │
│                                                             │
│  RAG (Our Approach):                                        │
│  Question → Search Docs → LLM + Docs → Cited Answer!       │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Why RAG?

- **No hallucinations**: Grounded in real documents
- **Citations**: Every claim has a source
- **Up-to-date**: Database can be updated
- **Trustworthy**: Verifiable information

---

# Slide 6: The RAG Pipeline

## 7 Steps to Generate a Response

```
1. ROUTE      →  Detect language, select model
      │
2. CACHE      →  Check for cached response
      │
3. CLASSIFY   →  Is this on-topic? Off-topic?
      │
4. RETRIEVE   →  Search 10,000+ climate documents
      │
5. RERANK     →  Score and select top 5 documents
      │
6. GENERATE   →  Create response with citations
      │
7. VALIDATE   →  Check for hallucinations
```

**Processing time: 3-4 seconds**

---

# Slide 7: Multilingual Support

## 180+ Languages

**Native LLM Support:**
- Nova: English, Spanish, Japanese, German, Swedish, Danish
- Command-A: Arabic, Chinese, Hindi, French, + 18 more

**Translation Support:**
- All 180+ languages via translation layer

## Language Routing

```
Query: "¿Qué es el cambio climático?"
         │
         ▼
Detected: Spanish (es)
         │
         ▼
Model: Nova (supports Spanish)
```

---

# Slide 8: Document Retrieval

## How We Find Relevant Information

```
Query: "How to prepare for floods?"
         │
         ▼
┌────────────────────────────────────────┐
│  1. Generate Embeddings (BGE-M3)       │
│     • Dense vector (meaning)           │
│     • Sparse vector (keywords)         │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  2. Search Pinecone (Hybrid)           │
│     • 50% semantic similarity          │
│     • 50% keyword matching             │
│     → Returns 15 documents             │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│  3. Rerank with Cohere                 │
│     • Score each document              │
│     → Returns top 5 documents          │
└────────────────────────────────────────┘
```

---

# Slide 9: Quality Assurance

## Hallucination Guard

**Problem**: LLMs can make things up

**Solution**: Verify every response against source documents

```
Response: "Toronto plans to reduce emissions by 65%..."
Documents: [Contains this claim? ✓]

Score: 0.92 (High faithfulness) → PASS
```

## Score Thresholds

| Score | Action |
|-------|--------|
| ≥ 0.70 | Return response |
| 0.10-0.70 | Return with warning |
| < 0.10 | Try web search fallback |

---

# Slide 10: Caching Strategy

## Speed Through Redis Cache

```
First request:  "What is climate change?" → 3.2 seconds
Second request: "What is climate change?" → 0.05 seconds
```

## Cache Features

- **Key format**: `q:{language}:{hash}`
- **TTL**: 1 hour
- **Fuzzy matching**: 92% similarity threshold

## Impact

- 30-50% of queries served from cache
- 60x faster for cached responses

---

# Slide 11: API Design

## RESTful Endpoints

```
POST /api/v1/chat/query      # Process chat query
POST /api/v1/chat/stream     # Stream response (SSE)
GET  /api/v1/languages/supported  # List languages
POST /api/v1/feedback/submit # Submit feedback
GET  /api/v1/health          # Health check
```

## Request/Response Example

**Request:**
```json
{
  "query": "What causes floods?",
  "language": "en",
  "conversation_history": []
}
```

**Response:**
```json
{
  "success": true,
  "response": "Floods are caused by...",
  "citations": [{"title": "...", "url": "..."}],
  "faithfulness_score": 0.85
}
```

---

# Slide 12: Frontend Architecture

## React Component Structure

```
page.tsx (Main Chat Page)
├── AppHeader
│   ├── Language Selector
│   ├── New Chat Button
│   └── Export Button
│
├── ChatWindow
│   └── ChatMessage (multiple)
│       ├── Message Content
│       ├── Citations
│       └── Feedback Buttons
│
└── ConsentDialog
```

## Key Technologies

- React 18 with hooks
- TypeScript for type safety
- Tailwind for styling
- shadcn/ui for accessible components

---

# Slide 13: Security Features

## Input Validation

- Query length: 1-2000 characters
- Language code validation
- PII detection in feedback

## Rate Limiting

| Environment | Limit |
|-------------|-------|
| Production | 20 req/min |
| Staging | 30 req/min |
| Development | 60 req/min |

## Content Filtering

- Harmful query detection
- Off-topic query handling
- Prompt injection prevention

---

# Slide 14: Deployment

## Azure App Service

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure App Service                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ FastAPI (Port 8000)                                  │   │
│  │ ├── Serves API endpoints (/api/v1/*)                │   │
│  │ └── Serves static frontend (Next.js build)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ External Services                                    │   │
│  │ ├── AWS Bedrock (Nova)                              │   │
│  │ ├── Cohere API                                       │   │
│  │ ├── Pinecone (Vector DB)                            │   │
│  │ └── Redis (Cache)                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## CI/CD

- GitHub Actions workflow
- Automatic deployment on push
- Security scans (npm audit, pip-audit)

---

# Slide 15: Key Files to Know

## Must-Read Files for New Developers

| File | Purpose |
|------|---------|
| `src/webui/api/main.py` | Backend entry point |
| `src/models/climate_pipeline.py` | AI orchestration |
| `src/webui/app/src/app/page.tsx` | Frontend main page |
| `src/models/retrieval.py` | Document search |
| `src/data/config/config.py` | Configuration |

## Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview |
| `STARTUP_GUIDE.md` | Local setup |
| `ARCHITECTURE.md` | System design |
| `onboarding/` | This folder! |

---

# Slide 16: Getting Started

## First Day Checklist

- [ ] Clone the repository
- [ ] Set up local environment
- [ ] Run the application
- [ ] Send a test message
- [ ] Read the architecture diagrams

## Commands to Know

```bash
# Start backend
poetry run uvicorn src.webui.api.main:app --port 8000

# Start frontend (dev)
cd src/webui/app && npm run dev

# Run tests
pytest tests/

# Build frontend
cd src/webui/app && npm run build
```

---

# Slide 17: Questions?

## Resources

- **Onboarding Guide**: `onboarding/README.md`
- **Architecture Diagrams**: `onboarding/diagrams/`
- **Component Guides**: `onboarding/components/`
- **API Documentation**: `src/webui/api/README.md`

## Key Concepts to Understand

1. **RAG** - Retrieval-Augmented Generation
2. **Embeddings** - Text to vectors
3. **Vector Search** - Semantic similarity
4. **LLMs** - Large Language Models

---

# Slide 18: Summary

## What We Built

A production-ready AI chatbot that:

- Answers climate questions in 180+ languages
- Provides cited, trustworthy information
- Uses RAG to prevent hallucinations
- Caches responses for performance
- Deploys easily to Azure

## What Makes It Special

- **Multilingual First**: Not just translation
- **Quality Focus**: Hallucination guard
- **Canadian Context**: Local information
- **Open Architecture**: Easy to extend

---

*Thank you for joining the Climate Multilingual Chatbot team!*
