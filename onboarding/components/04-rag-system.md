# RAG System Deep Dive

This guide explains Retrieval-Augmented Generation (RAG) - the core AI pattern used in this chatbot.

---

## What is RAG?

**RAG (Retrieval-Augmented Generation)** is a technique that:

1. **Retrieves** relevant documents from a knowledge base
2. **Augments** the AI prompt with those documents
3. **Generates** a response based on the retrieved information

```
Without RAG:
User: "What's Toronto's climate plan?"
AI: *Makes something up* ❌

With RAG:
User: "What's Toronto's climate plan?"
System: *Finds Toronto's actual climate plan documents*
AI: *Answers based on those documents* ✓
```

---

## Why Use RAG?

| Problem | RAG Solution |
|---------|-------------|
| AI makes up facts | Answers grounded in documents |
| Can't cite sources | Every claim has a source |
| Knowledge is outdated | Database can be updated |
| Generic responses | Specific, contextual answers |

---

## Our RAG Implementation

### Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAG PIPELINE                                 │
│                                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │  Query   │──▶│ Embedding│──▶│  Vector  │──▶│ Reranking│        │
│  │          │   │          │   │  Search  │   │          │        │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘        │
│                                                    │                │
│                                                    ▼                │
│                                            ┌──────────────┐        │
│                                            │  Generation  │        │
│                                            │  with Docs   │        │
│                                            └──────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: Embeddings

**File**: [`src/models/retrieval.py`](../../src/models/retrieval.py) (lines 83-176)

### What are Embeddings?

Embeddings convert text into numbers (vectors) that capture meaning:

```
"climate change" → [0.12, -0.34, 0.56, ..., 0.89]  (1024 numbers)
"global warming"  → [0.11, -0.32, 0.58, ..., 0.87]  (similar!)
"pizza recipe"    → [0.78, 0.21, -0.45, ..., -0.12] (very different)
```

**Similar meanings = Similar vectors**

### Our Embedding Model: BGE-M3

**Model**: `BAAI/bge-m3` (FlagEmbedding)

**Features**:
- **Multilingual**: Works across 100+ languages
- **Hybrid**: Produces both dense AND sparse embeddings

```python
# Dense embeddings (semantic meaning)
dense_vec = [0.12, -0.34, 0.56, ...]  # 1024 dimensions

# Sparse embeddings (keyword matching, like BM25)
sparse_vec = {
    "climate": 0.92,
    "change": 0.85,
    "impact": 0.78
}
```

### Code Example

```python
# src/models/retrieval.py
def get_query_embeddings(query: str) -> dict:
    """Generate both dense and sparse embeddings."""

    # Load model (cached)
    model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)

    # Generate embeddings
    output = model.encode(
        [query],
        return_dense=True,
        return_sparse=True
    )

    return {
        "dense_vecs": output["dense_vecs"][0],
        "lexical_weights": output["lexical_weights"][0]
    }
```

---

## Component 2: Vector Database (Pinecone)

**File**: [`src/models/retrieval.py`](../../src/models/retrieval.py) (lines 190-256)

### What is a Vector Database?

A database optimized for storing and searching embeddings:

```
Traditional Database:
  SELECT * FROM docs WHERE title LIKE '%climate%'
  (Only finds exact keyword matches)

Vector Database:
  Find docs similar to embedding([0.12, -0.34, ...])
  (Finds semantically similar content!)
```

### Our Setup

**Service**: Pinecone
**Index**: `climate-change-adaptation-index-10-24-prod`
**Contents**: 10,000+ climate documents

Each document stored as:
```python
{
    "id": "doc_12345",
    "values": [0.12, -0.34, ...],  # Dense embedding
    "sparse_values": {...},        # Sparse embedding
    "metadata": {
        "title": "Toronto Climate Action Plan",
        "url": "https://toronto.ca/...",
        "content": "Full document text..."
    }
}
```

### Hybrid Search

We combine two search methods:

```
Hybrid Search (alpha = 0.5):
  │
  ├── 50% Dense (Semantic)
  │   "What causes rising temperatures?"
  │   Matches: "global warming factors", "heat increase causes"
  │
  └── 50% Sparse (Keywords)
      "What causes rising temperatures?"
      Matches: documents containing "rising", "temperatures", "causes"
```

**Why hybrid?**
- Dense catches meaning ("hot weather" = "high temperatures")
- Sparse catches specific terms ("PM2.5", "IPCC")
- Combined = best of both worlds

### Code Example

```python
# src/models/retrieval.py
def get_hybrid_results(query_embedding, top_k=15):
    """Search Pinecone with hybrid approach."""

    # Create sparse vector from lexical weights
    sparse_vector = {
        "indices": list(query_embedding["lexical_weights"].keys()),
        "values": list(query_embedding["lexical_weights"].values())
    }

    # Hybrid query
    results = index.query(
        vector=query_embedding["dense_vecs"],
        sparse_vector=sparse_vector,
        top_k=top_k,
        include_metadata=True,
        alpha=0.5  # Balance between dense and sparse
    )

    return results.matches
```

---

## Component 3: Reranking

**File**: [`src/models/rerank.py`](../../src/models/rerank.py)

### Why Rerank?

Vector search is fast but approximate. Reranking uses a smarter model to find the *truly* best results:

```
Initial Search (Pinecone): 15 documents
  Doc A: score 0.92
  Doc B: score 0.88
  Doc C: score 0.85
  ...
        │
        ▼
Reranking (Cohere): 5 documents
  Doc C: score 0.95  ← Actually most relevant!
  Doc A: score 0.89
  Doc E: score 0.82
  ...
```

### Our Reranker

**Model**: Cohere `rerank-english-v3.0`

**Process**:
1. Take top 15 documents from Pinecone
2. Score each against the original query
3. Keep top 5 with score ≥ 0.70

### Code Example

```python
# src/models/rerank.py
async def rerank_fcn(query: str, documents: list, top_k: int = 5):
    """Rerank documents using Cohere."""

    # Prepare documents
    doc_texts = [doc["content"][:1500] for doc in documents]

    # Call Cohere reranker
    response = cohere_client.rerank(
        model="rerank-english-v3.0",
        query=query,
        documents=doc_texts,
        top_n=top_k,
        return_documents=False
    )

    # Filter by minimum score
    MIN_SCORE = 0.70
    results = [r for r in response.results if r.relevance_score >= MIN_SCORE]

    return [documents[r.index] for r in results]
```

---

## Component 4: Augmented Generation

**File**: [`src/models/gen_response_unified.py`](../../src/models/gen_response_unified.py)

### The Prompt Structure

```
┌────────────────────────────────────────────────────────────────────┐
│ SYSTEM MESSAGE                                                      │
│ You are a climate information expert. Always cite your sources.   │
│ Be helpful, accurate, and inclusive.                               │
├────────────────────────────────────────────────────────────────────┤
│ RETRIEVED DOCUMENTS (Context)                                      │
│                                                                     │
│ [Document 1: Toronto Climate Action Plan]                          │
│ Toronto aims to reduce emissions by 65% by 2030...                │
│                                                                     │
│ [Document 2: Ontario Flood Preparedness Guide]                     │
│ Residents should prepare emergency kits containing...              │
│                                                                     │
│ [Document 3: Canada Climate Adaptation Strategy]                   │
│ The federal government has allocated $1.3B for...                  │
├────────────────────────────────────────────────────────────────────┤
│ USER QUERY                                                          │
│ How can I prepare for climate change in Toronto?                   │
└────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────────────────┐
│ AI RESPONSE                                                         │
│                                                                     │
│ To prepare for climate change in Toronto, you can:                 │
│                                                                     │
│ 1. **Reduce your carbon footprint** - Toronto aims to cut          │
│    emissions by 65% by 2030 [1]                                    │
│                                                                     │
│ 2. **Prepare for extreme weather** - Create an emergency kit       │
│    with water, food, and medications [2]                           │
│                                                                     │
│ 3. **Take advantage of programs** - Federal funding of $1.3B      │
│    is available for home improvements [3]                          │
│                                                                     │
│ Sources:                                                            │
│ [1] Toronto Climate Action Plan - toronto.ca                       │
│ [2] Ontario Flood Preparedness - ontario.ca                        │
│ [3] Canada Climate Adaptation - canada.ca                          │
└────────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Ground in documents**: Only use information from retrieved docs
2. **Cite everything**: Every claim must reference a source
3. **Don't hallucinate**: If info isn't in docs, say "I don't have information about that"
4. **Be helpful**: Provide actionable advice

---

## Quality Control

### Similarity Filtering

**File**: [`src/data/config/config.py`](../../src/data/config/config.py)

```python
RETRIEVAL_CONFIG = {
    "similarity_base": 0.65,      # Minimum score to include
    "similarity_fallback": 0.55,  # Lower threshold for fallback
    "adaptive_margin": 0.10       # Gap from top score
}
```

If no documents meet the threshold, we use Tavily web search as fallback.

### Domain Boosting

We prefer authoritative sources:

```python
DOMAIN_BOOST_CONFIG = {
    "preferred_domains": [
        "canada.gc.ca",
        "ontario.ca",
        "toronto.ca",
        "ipcc.ch",
        "climatechange.gc.ca"
    ],
    "boost_weight": 0.25  # 25% score boost
}
```

### Content Filtering

We exclude certain content types:

```python
AUDIENCE_BLOCKLIST = [
    "K-12", "K-2", "Gr. 5-8",
    "lesson plan", "curriculum",
    "worksheet", "classroom"
]
```

---

## Complete RAG Flow

```
1. User: "How do I reduce my carbon footprint?"
         │
         ▼
2. Embedding: [0.12, -0.34, 0.56, ...]
         │
         ▼
3. Pinecone Search: 15 documents about carbon reduction
         │
         ▼
4. Rerank: Top 5 most relevant documents
         │
         ▼
5. Build Prompt: System + Documents + Query
         │
         ▼
6. Generate: "To reduce your carbon footprint: 1. ... [1]"
         │
         ▼
7. Verify: Hallucination check (score: 0.88 ✓)
         │
         ▼
8. Return: Response with citations
```

---

## Key Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `top_k_retrieve` | 15 | Documents from Pinecone |
| `top_k_rerank` | 5 | Final documents used |
| `min_rerank_score` | 0.70 | Quality threshold |
| `hybrid_alpha` | 0.5 | Dense/sparse balance |
| `embedding_model` | BGE-M3 | Multilingual embeddings |
| `rerank_model` | Cohere v3 | Document reranking |

---

## Key Files

| File | Purpose |
|------|---------|
| [`retrieval.py`](../../src/models/retrieval.py) | Embeddings + Pinecone |
| [`rerank.py`](../../src/models/rerank.py) | Cohere reranking |
| [`gen_response_unified.py`](../../src/models/gen_response_unified.py) | Response generation |
| [`config.py`](../../src/data/config/config.py) | RAG configuration |

---

## Learn More

- [AI Pipeline Guide](./03-ai-pipeline.md)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Cohere Documentation](https://docs.cohere.com/)
- [BGE-M3 on HuggingFace](https://huggingface.co/BAAI/bge-m3)
