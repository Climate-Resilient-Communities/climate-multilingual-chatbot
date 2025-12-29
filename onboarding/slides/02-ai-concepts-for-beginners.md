# AI Concepts for Beginners
## Understanding the Technology Behind the Chatbot

---

# Slide 1: Welcome

## AI Concepts for Beginners

**What you'll learn:**

- What is AI and how does it work?
- What are LLMs (Large Language Models)?
- What is RAG (Retrieval-Augmented Generation)?
- How does our chatbot use these technologies?

**No prior AI knowledge required!**

---

# Slide 2: What is AI?

## Artificial Intelligence Basics

**AI** = Computers that can perform tasks that normally require human intelligence

```
Human Task          →    AI Can Help
─────────────────────────────────────
Understanding text  →    Chatbots
Recognizing images  →    Photo apps
Making decisions    →    Recommendations
Generating content  →    Writing assistants
```

## Our Chatbot Uses AI To:

- Understand your questions
- Find relevant information
- Generate helpful responses
- Translate between languages

---

# Slide 3: What is Machine Learning?

## How AI "Learns"

```
Traditional Programming:
┌──────────────┐
│ Rules        │ ──▶ Computer ──▶ Output
│ (Written by  │
│  humans)     │
└──────────────┘

Machine Learning:
┌──────────────┐
│ Data         │ ──▶ Computer ──▶ "Rules"
│ (Lots of     │     (Learns     (Learned by
│  examples)   │      patterns)   computer)
└──────────────┘
```

**Example**: Instead of writing rules for "what is spam email", we show the computer millions of spam and non-spam emails, and it learns the patterns.

---

# Slide 4: What are LLMs?

## Large Language Models

**LLM** = AI trained on massive amounts of text to understand and generate language

```
Training Data: Books, websites, articles (billions of words)
         │
         ▼
┌─────────────────────────────────────────────────────┐
│                                                      │
│   LLM learns:                                        │
│   • Grammar and language patterns                    │
│   • Facts and knowledge                              │
│   • How to answer questions                          │
│   • How to write different styles                    │
│                                                      │
└─────────────────────────────────────────────────────┘
         │
         ▼
Output: Can understand and generate human-like text
```

**Examples**: ChatGPT, Claude, GPT-4

---

# Slide 5: Our LLMs

## Two Models, Different Strengths

### AWS Bedrock Nova
- Fast response times
- Good for 6 languages (English, Spanish, Japanese, German, Swedish, Danish)
- Used for most queries

### Cohere Command-A
- Supports 22+ languages natively
- Better for Arabic, Chinese, Hindi, etc.
- Used when Nova doesn't support the language

```
Query Language → Router → Select Best Model
     │
     ├── English    → Nova (fast)
     ├── Spanish    → Nova (fast)
     ├── Arabic     → Command-A
     ├── Chinese    → Command-A
     └── Other      → Nova + Translation
```

---

# Slide 6: The Problem with LLMs

## Why We Need More Than Just an LLM

**The Hallucination Problem:**

```
User: "What is Toronto's climate plan?"

Pure LLM Response:
"Toronto's 2023 Climate Action Plan aims to reduce
 emissions by 75% by 2030..."  ← Made up! Not accurate!
```

**LLMs can confidently generate incorrect information** because they're trained to produce fluent text, not to verify facts.

## The Solution: RAG

Instead of relying on the LLM's memory, we:
1. Search for real documents
2. Give those documents to the LLM
3. Ask it to answer based on the documents

---

# Slide 7: What is RAG?

## Retrieval-Augmented Generation

```
Step 1: RETRIEVE
┌─────────────────────────────────────────────────────────────┐
│ User asks: "What is Toronto's climate plan?"                │
│                                                              │
│ System searches document database                           │
│ → Finds: Toronto's actual climate plan documents            │
└─────────────────────────────────────────────────────────────┘

Step 2: AUGMENT
┌─────────────────────────────────────────────────────────────┐
│ Combine:                                                     │
│ • User's question                                           │
│ • Retrieved documents                                       │
│ • Instructions to cite sources                              │
└─────────────────────────────────────────────────────────────┘

Step 3: GENERATE
┌─────────────────────────────────────────────────────────────┐
│ LLM creates response based on ACTUAL documents              │
│ → "According to Toronto.ca, the plan aims for..."          │
│ → Includes citations!                                       │
└─────────────────────────────────────────────────────────────┘
```

---

# Slide 8: What are Embeddings?

## Turning Text into Numbers

**Problem**: Computers don't understand words, only numbers

**Solution**: Convert text to numbers that capture meaning

```
Text                      →    Embedding (numbers)
──────────────────────────────────────────────────────
"climate change"          →    [0.12, -0.34, 0.56, ...]
"global warming"          →    [0.11, -0.32, 0.58, ...]  ← Similar!
"pizza recipe"            →    [0.78, 0.21, -0.45, ...]  ← Different!
```

**Key Insight**: Similar meanings = Similar numbers

## Why This Matters

With embeddings, we can:
- Find documents with similar meaning (not just matching words)
- Search in any language
- Understand context and synonyms

---

# Slide 9: Vector Database

## Where We Store Our Documents

**Traditional Database:**
```
SELECT * FROM documents WHERE text LIKE '%climate%'
→ Only finds exact keyword matches
```

**Vector Database (Pinecone):**
```
Find documents similar to embedding([0.12, -0.34, ...])
→ Finds semantically similar content!
```

## Our Document Collection

- 10,000+ climate documents
- From trusted sources (IPCC, Canadian government, etc.)
- Each document stored as an embedding

---

# Slide 10: Semantic Search

## Finding Meaning, Not Just Words

```
Query: "How do I stay cool in hot weather?"

Keyword Search would find:
├── Documents with "cool" ✓
├── Documents with "hot" ✓
└── Documents with "weather" ✓

Semantic Search finds:
├── "Air Conditioning Tips" ✓
├── "Heat Wave Preparedness" ✓
├── "Cooling Centers in Toronto" ✓
└── "Hydration During Extreme Heat" ✓

→ Understands meaning, not just words!
```

---

# Slide 11: Reranking

## Finding the BEST Documents

After initial search returns ~15 documents, we need to find the 5 best ones.

```
Initial Results (from Pinecone):
  1. Heat Wave Safety (score: 0.88)
  2. Climate Change Overview (score: 0.85)
  3. AC Installation Guide (score: 0.82)  ← Actually most relevant!
  ...

After Reranking (Cohere):
  1. AC Installation Guide (score: 0.95)  ← Now ranked first!
  2. Heat Wave Safety (score: 0.89)
  3. Cooling Your Home (score: 0.84)
  ...
```

**Reranking uses a smarter model** to determine which documents really answer the question.

---

# Slide 12: Response Generation

## Creating the Final Answer

```
┌─────────────────────────────────────────────────────────────┐
│ PROMPT TO LLM:                                              │
│                                                              │
│ System: You are a helpful climate assistant.                │
│         Always cite your sources.                           │
│                                                              │
│ Documents:                                                   │
│ [1] "Install window films to reduce heat..."               │
│ [2] "Use fans to improve air circulation..."               │
│ [3] "Keep blinds closed during peak sun..."                │
│                                                              │
│ User: How do I keep my home cool?                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM RESPONSE:                                               │
│                                                              │
│ To keep your home cool during hot weather:                  │
│                                                              │
│ 1. Install window films to block heat [1]                   │
│ 2. Use fans to improve air circulation [2]                  │
│ 3. Keep blinds closed during peak sunlight [3]              │
│                                                              │
│ ← Every claim has a citation!                               │
└─────────────────────────────────────────────────────────────┘
```

---

# Slide 13: Hallucination Guard

## Making Sure Answers Are Accurate

**Problem**: Even with RAG, LLMs can sometimes add information that's not in the documents.

**Solution**: Check every response for "faithfulness"

```
Response: "Toronto will provide $500 rebates for AC units..."

Check against documents:
  ├── Is this claim in Document 1? ❌
  ├── Is this claim in Document 2? ❌
  └── Is this claim in Document 3? ❌

Result: NOT SUPPORTED → Flag for review or regenerate
```

## Faithfulness Score

| Score | Meaning |
|-------|---------|
| 0.90+ | Excellent - all claims supported |
| 0.70-0.90 | Good - mostly supported |
| < 0.70 | Concerning - may need review |

---

# Slide 14: Caching

## Making Repeated Questions Fast

```
Without Cache:
User 1: "What is climate change?" → 3 seconds
User 2: "What is climate change?" → 3 seconds  (same work!)
User 3: "What is climate change?" → 3 seconds  (same work!)

With Cache:
User 1: "What is climate change?" → 3 seconds (processed)
User 2: "What is climate change?" → 0.05 seconds (from cache!)
User 3: "What is climate change?" → 0.05 seconds (from cache!)
```

**Redis** stores responses for 1 hour, so the same questions don't need to be reprocessed.

---

# Slide 15: Multilingual Processing

## How Languages Are Handled

```
User Query: "¿Cómo puedo reducir mi huella de carbono?"
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Detect Language: Spanish (es)                            │
│ 2. Select Model: Nova (supports Spanish)                    │
│ 3. Process Query: In Spanish                                │
│ 4. Search Documents: Multilingual embeddings work!          │
│ 5. Generate Response: In Spanish                            │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
Response in Spanish: "Para reducir su huella de carbono..."
```

**Key Technology**: BGE-M3 embeddings work across 100+ languages, so we can search documents regardless of the query language.

---

# Slide 16: Complete Pipeline

## Putting It All Together

```
User Types Question
        │
        ▼
┌───────────────┐
│ 1. Language   │ ──▶ Detect language, choose LLM
│    Routing    │
└───────────────┘
        │
        ▼
┌───────────────┐
│ 2. Cache      │ ──▶ Check if already answered
│    Check      │
└───────────────┘
        │
        ▼
┌───────────────┐
│ 3. Classify   │ ──▶ Is this about climate?
│    Intent     │
└───────────────┘
        │
        ▼
┌───────────────┐
│ 4. Embed &    │ ──▶ Search document database
│    Search     │
└───────────────┘
        │
        ▼
┌───────────────┐
│ 5. Rerank     │ ──▶ Find the 5 best documents
└───────────────┘
        │
        ▼
┌───────────────┐
│ 6. Generate   │ ──▶ Create response with citations
└───────────────┘
        │
        ▼
┌───────────────┐
│ 7. Validate   │ ──▶ Check for hallucinations
└───────────────┘
        │
        ▼
Response Displayed to User (3-4 seconds total)
```

---

# Slide 17: Key Takeaways

## What You've Learned

| Concept | One-Line Summary |
|---------|-----------------|
| **LLM** | AI that understands and generates text |
| **RAG** | Search first, then generate with sources |
| **Embedding** | Convert text to numbers that capture meaning |
| **Vector DB** | Store and search by meaning, not keywords |
| **Reranking** | Find the truly best documents |
| **Hallucination Guard** | Verify claims against sources |
| **Caching** | Store answers to avoid repeat work |

## Why This Matters

Our chatbot provides **trustworthy**, **cited** climate information in **180+ languages** because of these technologies working together.

---

# Slide 18: Questions?

## Explore More

- **Onboarding README**: `onboarding/README.md`
- **RAG Deep Dive**: `onboarding/components/04-rag-system.md`
- **AI Pipeline**: `onboarding/components/03-ai-pipeline.md`

## Key Files to Explore

| Concept | Code Location |
|---------|--------------|
| Embeddings | `src/models/retrieval.py` |
| LLM Calls | `src/models/nova_flow.py` |
| RAG Pipeline | `src/models/climate_pipeline.py` |
| Hallucination Guard | `src/models/hallucination_guard.py` |

---

*You're now ready to understand the Climate Multilingual Chatbot's AI!*
