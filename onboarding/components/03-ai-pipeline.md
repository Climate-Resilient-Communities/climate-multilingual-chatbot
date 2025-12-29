# AI Pipeline Guide

This guide explains how the AI processing pipeline works - the "brain" of the chatbot.

---

## What is the AI Pipeline?

The **AI Pipeline** is the core processing system that:
- Takes user questions
- Finds relevant information from a climate document database
- Generates accurate, cited responses
- Ensures quality through multiple checks

**Main File**: [`src/models/climate_pipeline.py`](../../src/models/climate_pipeline.py)

**Class**: `ClimateQueryPipeline`

---

## The RAG Pattern

We use **RAG (Retrieval-Augmented Generation)**:

```
Traditional AI:
Question → LLM → Answer (may be made up!)

RAG:
Question → Search Documents → LLM + Documents → Answer (based on sources!)
```

**Why RAG?**
- Prevents hallucinations (made-up information)
- Provides citations for every claim
- Keeps information up-to-date

---

## Pipeline Steps

### Step 1: Language Routing

**File**: [`src/models/query_routing.py`](../../src/models/query_routing.py)

**Purpose**: Detect the user's language and choose the right AI model.

```
Input: "¿Qué es el cambio climático?"
       │
       ▼
Detect: Spanish (es)
       │
       ▼
Choose Model: Nova (supports Spanish)
```

**Language Support**:
| Model | Languages | Speed |
|-------|-----------|-------|
| Nova | English, Spanish, Japanese, German, Swedish, Danish | Fast |
| Command-A | Arabic, Chinese, Hindi, + 19 more | Slower |

**Key Code** (lines 188-300):
```python
class MultilingualRouter:
    def route_query(self, query: str, user_language: str):
        detected = self._detect_language(query)
        model = self._select_model(detected)
        return {
            "language_code": detected,
            "model_type": model,
            "needs_translation": detected != user_language
        }
```

---

### Step 2: Cache Check

**File**: [`src/models/redis_cache.py`](../../src/models/redis_cache.py)

**Purpose**: Return cached response if we've seen this question before.

```
Query: "What is climate change?"
       │
       ▼
Normalize: "what is climate change"
       │
       ▼
Hash: SHA256 → "a7b9c3d..."
       │
       ▼
Check Redis: q:en:a7b9c3d...
       │
       ├── HIT: Return cached response (fast!)
       └── MISS: Continue processing
```

**Cache Details**:
- TTL: 1 hour
- Key format: `q:{language}:{hash}`
- Also tries fuzzy matching (92% similar queries)

---

### Step 3: Query Classification

**File**: [`src/models/query_rewriter.py`](../../src/models/query_rewriter.py)

**Purpose**: Understand user intent and filter inappropriate queries.

```
Query: "What causes floods?"
       │
       ▼
LLM Classification:
       │
       └── Result: "on-topic" (climate-related)
```

**Intent Categories**:
| Category | Action | Example |
|----------|--------|---------|
| `on-topic` | Continue processing | "What is global warming?" |
| `off-topic` | Return redirect message | "What's the best pizza?" |
| `harmful` | Block request | Dangerous content |
| `greeting` | Return friendly hello | "Hi!" |
| `goodbye` | Return farewell | "Bye!" |
| `thanks` | Return acknowledgment | "Thank you!" |

**Key Code** (lines 168-300):
```python
async def query_rewriter(query: str, history: list):
    # Call LLM to classify
    result = await nova.classify(
        query,
        categories=["on-topic", "off-topic", "harmful", ...]
    )
    return {
        "classification": result.category,
        "rewritten_query": result.rewrite
    }
```

---

### Step 4: Document Retrieval

**File**: [`src/models/retrieval.py`](../../src/models/retrieval.py)

**Purpose**: Find the most relevant climate documents.

```
Query: "How to prepare for floods?"
       │
       ▼
Generate Embeddings (BGE-M3):
   Dense: [0.12, -0.34, 0.56, ...]  (meaning)
   Sparse: {"flood": 0.9, "prepare": 0.8}  (keywords)
       │
       ▼
Search Pinecone (hybrid):
   • 50% semantic similarity
   • 50% keyword matching
       │
       ▼
Raw Results: 15 documents
       │
       ▼
Rerank with Cohere:
   • Score each for relevance
   • Keep top 5 (score ≥ 0.70)
       │
       ▼
Final: 5 highly relevant documents
```

**Configuration** (from [`config.py`](../../src/data/config/config.py)):
```python
RETRIEVAL_CONFIG = {
    "top_k_retrieve": 15,      # Initial fetch
    "top_k_rerank": 5,         # Final count
    "min_rerank_score": 0.70,  # Quality threshold
    "hybrid_alpha": 0.5        # Dense/sparse balance
}
```

---

### Step 5: Response Generation

**File**: [`src/models/gen_response_unified.py`](../../src/models/gen_response_unified.py)

**Purpose**: Generate a helpful response using retrieved documents.

```
Prompt Assembly:
┌────────────────────────────────────────────────┐
│ SYSTEM: You are a climate information expert  │
│ who provides accurate, cited information...    │
├────────────────────────────────────────────────┤
│ CONTEXT (Retrieved Documents):                │
│ [1] Flood Preparedness Guide - Toronto.ca     │
│ [2] Emergency Planning - Ontario.ca           │
│ [3] Climate Adaptation - Canada.ca            │
├────────────────────────────────────────────────┤
│ USER: How to prepare for floods?              │
└────────────────────────────────────────────────┘
       │
       ▼
LLM Generates:
"To prepare for floods, you should:
1. Create an emergency kit [1]
2. Know your evacuation routes [2]
3. Install flood barriers [3]..."
```

**System Message** ([`system_messages.py`](../../src/models/system_messages.py)):
- Acts as supportive climate educator
- Always cites sources
- Focuses on Canadian/Toronto context
- Uses inclusive, accessible language

---

### Step 6: Hallucination Check

**File**: [`src/models/hallucination_guard.py`](../../src/models/hallucination_guard.py)

**Purpose**: Verify the response is faithful to the source documents.

```
Response: "You should stockpile 1000 sandbags..."
Documents: [No mention of sandbags]
       │
       ▼
Faithfulness Evaluation:
   • Claim 1: Supported ✓
   • Claim 2: Supported ✓
   • Claim 3: NOT SUPPORTED ✗
       │
       ▼
Score: 0.67 (below 0.70 threshold)
       │
       ▼
Action: Flag for review or use Tavily fallback
```

**Score Thresholds**:
| Score | Action |
|-------|--------|
| ≥ 0.70 | PASS - Return response |
| 0.10-0.70 | WARN - Return with low confidence |
| < 0.10 | FAIL - Try web search fallback |

**Key Code** (lines 75-200):
```python
async def check_hallucination(response: str, documents: list):
    result = await nova.classify(
        prompt=f"Is this response faithful to the context?",
        context=documents,
        response=response
    )
    return {
        "faithfulness_score": result.score,
        "unsupported_claims": result.issues
    }
```

---

### Step 7: Translation & Return

**Purpose**: Translate to user's language if needed, cache, and return.

```
English Response: "To prepare for floods..."
User Language: Spanish
       │
       ▼
Translate (Nova):
"Para prepararse para inundaciones..."
       │
       ▼
Cache in Redis (1 hour)
       │
       ▼
Return to User:
{
  response: "Para prepararse...",
  citations: [...],
  faithfulness_score: 0.85,
  processing_time: 3.2
}
```

---

## Complete Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ClimateQueryPipeline.process_query()             │
│                                                                      │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐       │
│   │ 1. Route │──▶│ 2. Cache │──▶│3.Classify│──▶│4.Retrieve│       │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘       │
│        │              │              │              │               │
│        │         HIT? Return    greeting/      No docs?            │
│        │              │         off-topic?     Tavily              │
│        │              │         Return canned  fallback            │
│        │              │                                            │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐                      │
│   │5.Generate│──▶│ 6. Guard │──▶│7.Translate│──▶ Return           │
│   └──────────┘   └──────────┘   └──────────┘                      │
│                       │                                            │
│                  Low score?                                        │
│                  Tavily fallback                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Processing Times

| Step | Typical Time |
|------|-------------|
| Language Routing | ~50ms |
| Cache Check | ~5-10ms |
| Query Classification | ~500ms |
| Document Retrieval + Rerank | ~800ms |
| Response Generation | ~1500ms |
| Hallucination Check | ~400ms |
| Translation | ~300ms |
| **Total** | **~3-4 seconds** |

---

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| [`climate_pipeline.py`](../../src/models/climate_pipeline.py) | Main orchestrator | ~1300 |
| [`query_routing.py`](../../src/models/query_routing.py) | Language routing | ~550 |
| [`query_rewriter.py`](../../src/models/query_rewriter.py) | Intent classification | ~470 |
| [`retrieval.py`](../../src/models/retrieval.py) | Document search | ~1140 |
| [`rerank.py`](../../src/models/rerank.py) | Result reranking | ~130 |
| [`gen_response_unified.py`](../../src/models/gen_response_unified.py) | Response generation | ~335 |
| [`hallucination_guard.py`](../../src/models/hallucination_guard.py) | Quality checking | ~420 |
| [`nova_flow.py`](../../src/models/nova_flow.py) | AWS Bedrock integration | ~516 |
| [`cohere_flow.py`](../../src/models/cohere_flow.py) | Cohere integration | ~373 |

---

## Learn More

- [RAG System Deep Dive](./04-rag-system.md)
- [Caching Guide](./05-caching.md)
- [Data Flow Diagram](../diagrams/03-data-flow.md)
