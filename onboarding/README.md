# Climate Multilingual Chatbot - Onboarding Guide

Welcome to the Climate Multilingual Chatbot project! This guide will help you understand how the codebase works, even if you're just getting started with AI concepts.

---

## Table of Contents

1. [What is This Project?](#what-is-this-project)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Core Concepts Explained](#core-concepts-explained)
5. [Architecture Overview](#architecture-overview)
6. [Component Deep Dives](#component-deep-dives)
7. [How Data Flows](#how-data-flows)
8. [Getting Started for Developers](#getting-started-for-developers)
9. [Additional Resources](#additional-resources)

---

## What is This Project?

The **Climate Multilingual Chatbot** is an AI-powered assistant that helps people learn about climate change. It can:

- **Answer questions** about climate change, adaptation, and environmental topics
- **Speak 180+ languages** - from English and Spanish to Urdu and Tagalog
- **Cite sources** - every answer includes links to trusted sources like IPCC, Canadian government sites, etc.
- **Maintain quality** - uses AI guardrails to prevent misinformation

### Who Uses This?

- Climate-resilient communities seeking accessible information
- People who prefer information in their native language
- Anyone wanting science-backed climate information

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Redis (for caching)
- API keys for: AWS Bedrock, Cohere, Pinecone

### Run Locally (5 minutes)

```bash
# 1. Clone and setup
git clone <repo-url>
cd climate-multilingual-chatbot

# 2. Install Python dependencies
poetry install

# 3. Install frontend dependencies
cd src/webui/app && npm install && cd ../../..

# 4. Set environment variables (create .env file)
cp .env.example .env  # Edit with your API keys

# 5. Start Redis
./start-redis.sh

# 6. Start the backend (serves both API and frontend)
poetry run uvicorn src.webui.api.main:app --port 8000

# 7. Open http://localhost:8000 in your browser
```

---

## Project Structure

```
climate-multilingual-chatbot/
├── src/
│   ├── webui/                    # Web Application
│   │   ├── api/                  # FastAPI Backend
│   │   │   ├── main.py          # App entry point
│   │   │   └── routers/         # API endpoints
│   │   └── app/                  # Next.js Frontend
│   │       ├── src/app/         # React pages
│   │       └── src/components/  # UI components
│   │
│   ├── models/                   # AI/ML Pipeline
│   │   ├── climate_pipeline.py  # Main orchestrator
│   │   ├── retrieval.py         # Document search
│   │   ├── nova_flow.py         # AWS Bedrock LLM
│   │   ├── cohere_flow.py       # Cohere LLM
│   │   └── query_rewriter.py    # Intent classification
│   │
│   ├── utils/                    # Helpers & Config
│   └── data/config/             # Configuration files
│
├── tests/                        # Test suites
├── onboarding/                   # You are here!
└── docs/                         # Additional documentation
```

### Key Files to Know

| File | What It Does | Learn More |
|------|--------------|------------|
| [`src/webui/api/main.py`](../src/webui/api/main.py) | FastAPI app entry point, starts the server | [Backend Guide](./components/01-backend.md) |
| [`src/models/climate_pipeline.py`](../src/models/climate_pipeline.py) | Main AI processing pipeline | [Pipeline Guide](./components/03-ai-pipeline.md) |
| [`src/webui/app/src/app/page.tsx`](../src/webui/app/src/app/page.tsx) | Main chat UI component | [Frontend Guide](./components/02-frontend.md) |
| [`src/models/retrieval.py`](../src/models/retrieval.py) | Vector search & embeddings | [RAG Guide](./components/04-rag-system.md) |
| [`src/data/config/config.py`](../src/data/config/config.py) | System configuration | [Config Guide](./components/06-configuration.md) |

---

## Core Concepts Explained

If you're new to AI, here are the key concepts used in this project:

### 1. Large Language Models (LLMs)

**What**: AI models trained on text that can understand and generate human language.

**In This Project**: We use two LLMs:
- **AWS Bedrock Nova** - Fast, supports 6 languages natively
- **Cohere Command A** - Slower but supports 22+ languages

**Code Location**: [`src/models/nova_flow.py`](../src/models/nova_flow.py), [`src/models/cohere_flow.py`](../src/models/cohere_flow.py)

### 2. RAG (Retrieval-Augmented Generation)

**What**: Instead of the AI making up answers, we first search a database for relevant documents, then ask the AI to answer based on those documents.

**Why**: Prevents "hallucinations" (made-up information) and ensures cited sources.

**In This Project**:
1. User asks a question
2. We search our climate document database (Pinecone)
3. We give the AI the top documents + the question
4. AI generates an answer citing those documents

**Code Location**: [`src/models/retrieval.py`](../src/models/retrieval.py)

### 3. Vector Embeddings

**What**: Converting text into numbers (vectors) that capture meaning. Similar texts have similar vectors.

**Example**: "climate change" and "global warming" would have similar vectors.

**In This Project**: We use BGE-M3, a multilingual embedding model that works across 100+ languages.

**Code Location**: [`src/models/retrieval.py:83-176`](../src/models/retrieval.py#L83-L176)

### 4. Vector Database (Pinecone)

**What**: A database optimized for storing and searching vectors quickly.

**In This Project**: We store thousands of climate documents as vectors in Pinecone, enabling fast semantic search.

### 5. Reranking

**What**: After initial search, we use another AI model to reorder results by relevance.

**In This Project**: Cohere's reranker scores each document and we keep the top 5.

**Code Location**: [`src/models/rerank.py`](../src/models/rerank.py)

### 6. Guardrails

**What**: Safety mechanisms to ensure AI behaves correctly.

**In This Project**:
- **Input Guardrail**: Blocks harmful/off-topic queries
- **Hallucination Guard**: Checks if the response is faithful to sources

**Code Location**: [`src/models/input_guardrail.py`](../src/models/input_guardrail.py), [`src/models/hallucination_guard.py`](../src/models/hallucination_guard.py)

---

## Architecture Overview

See the full architecture diagrams in [diagrams/](./diagrams/).

### High-Level View

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│     USER        │────▶│    FRONTEND     │────▶│    BACKEND      │
│   (Browser)     │     │   (Next.js)     │     │   (FastAPI)     │
│                 │◀────│                 │◀────│                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   AI PIPELINE   │
                                               │  ┌───────────┐  │
                                               │  │ Language  │  │
                                               │  │  Router   │  │
                                               │  └─────┬─────┘  │
                                               │        ▼        │
                                               │  ┌───────────┐  │
                                               │  │ Document  │  │
                                               │  │ Retrieval │  │
                                               │  └─────┬─────┘  │
                                               │        ▼        │
                                               │  ┌───────────┐  │
                                               │  │ Response  │  │
                                               │  │ Generator │  │
                                               │  └───────────┘  │
                                               └─────────────────┘
```

For detailed diagrams, see:
- [High-Level Architecture](./diagrams/01-high-level-architecture.md)
- [AI Pipeline Flow](./diagrams/02-ai-pipeline-flow.md)
- [Data Flow Diagram](./diagrams/03-data-flow.md)
- [Component Interactions](./diagrams/04-component-interactions.md)

---

## Component Deep Dives

Detailed guides for each major component:

| Component | Description | Guide |
|-----------|-------------|-------|
| **Backend (FastAPI)** | API server, routes, middleware | [01-backend.md](./components/01-backend.md) |
| **Frontend (Next.js)** | Chat UI, React components | [02-frontend.md](./components/02-frontend.md) |
| **AI Pipeline** | Main processing orchestrator | [03-ai-pipeline.md](./components/03-ai-pipeline.md) |
| **RAG System** | Document retrieval & embeddings | [04-rag-system.md](./components/04-rag-system.md) |
| **Caching (Redis)** | Response caching layer | [05-caching.md](./components/05-caching.md) |
| **Configuration** | Environment & settings | [06-configuration.md](./components/06-configuration.md) |

---

## How Data Flows

### When a User Asks a Question

```
1. USER types: "How can I prepare for flooding in Toronto?"

2. FRONTEND (Next.js)
   ├─ Captures input
   ├─ Sends POST to /api/v1/chat/query
   └─ Waits for response

3. BACKEND (FastAPI)
   ├─ Receives request
   ├─ Rate limit check
   └─ Passes to AI Pipeline

4. AI PIPELINE (ClimateQueryPipeline)
   │
   ├─ STEP 1: Route Query
   │   └─ Detect language → English → Use Nova model
   │
   ├─ STEP 2: Check Cache
   │   └─ Cache miss → Continue processing
   │
   ├─ STEP 3: Classify Intent
   │   └─ "on-topic" (climate-related)
   │
   ├─ STEP 4: Retrieve Documents
   │   ├─ Generate embeddings (BGE-M3)
   │   ├─ Search Pinecone → 15 documents
   │   └─ Rerank → Top 5 documents
   │
   ├─ STEP 5: Generate Response
   │   ├─ Build prompt with documents
   │   └─ Call Nova LLM → Response with citations
   │
   ├─ STEP 6: Quality Check
   │   └─ Hallucination guard → Score: 0.85 (good!)
   │
   └─ STEP 7: Cache & Return
       ├─ Store in Redis (1 hour TTL)
       └─ Return response + citations

5. FRONTEND displays:
   ├─ Formatted response
   ├─ Clickable citations
   └─ Feedback buttons
```

For the complete visual flow, see [Data Flow Diagram](./diagrams/03-data-flow.md).

---

## Getting Started for Developers

### First Day Checklist

- [ ] Read this README
- [ ] Clone the repository
- [ ] Set up local environment (see [STARTUP_GUIDE.md](../STARTUP_GUIDE.md))
- [ ] Run the application locally
- [ ] Send a test message in the chat
- [ ] Explore the [high-level architecture diagram](./diagrams/01-high-level-architecture.md)

### First Week Goals

- [ ] Read all component guides in [components/](./components/)
- [ ] Understand the AI pipeline flow
- [ ] Run the test suite (`pytest tests/`)
- [ ] Make a small code change and test it
- [ ] Understand how caching works

### Useful Commands

```bash
# Run backend with auto-reload
poetry run uvicorn src.webui.api.main:app --reload --port 8000

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_query_rewriter_json.py

# Check code style
flake8 src/

# Build frontend for production
cd src/webui/app && npm run build
```

---

## Additional Resources

### Documentation Files

| Document | Location | Purpose |
|----------|----------|---------|
| Main README | [`README.md`](../README.md) | Project overview |
| Startup Guide | [`STARTUP_GUIDE.md`](../STARTUP_GUIDE.md) | Local development setup |
| Architecture | [`ARCHITECTURE.md`](../ARCHITECTURE.md) | System architecture |
| Deployment | [`Deployment.md`](../Deployment.md) | Azure deployment guide |
| API Docs | [`src/webui/api/README.md`](../src/webui/api/README.md) | API endpoint documentation |
| Frontend Docs | [`src/webui/app/readme.md`](../src/webui/app/readme.md) | Frontend documentation |

### Presentation Slides

For team presentations and onboarding sessions, see [slides/](./slides/).

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Cohere Documentation](https://docs.cohere.com/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

---

## Questions?

If you have questions about the codebase:

1. Check the relevant [component guide](./components/)
2. Search the existing documentation
3. Look at the tests for usage examples
4. Ask your team lead

---

*This onboarding guide is part of the Climate Multilingual Chatbot project. Last updated: December 2024*
