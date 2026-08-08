# RAG Document Update Pipeline

How documents get into (and out of) the chatbot's Pinecone knowledge base.

```
data/rag_docs/*.{json,jsonl,md,txt}
        │
        ▼
scripts/rag_ingest.py
  1. load + validate      (title, min length, unique source_id)
  2. chunk                (~2400 chars, paragraph boundaries, 300-char overlap)
  3. embed                (BGE-M3 via HuggingFace Inference API, 1024-dim,
                           L2-normalized — same embedder the runtime uses)
  4. upsert               (deterministic IDs → edits update in place)
  5. prune                (stale chunks of shrunk docs are deleted)
        │
        ▼
Pinecone index  ←──  src/models/retrieval.py (runtime hybrid search)
```

## Quick start

```bash
# Required environment
export PINECONE_API_KEY=...
export HF_TOKEN=...                  # HuggingFace API token for BGE-M3
export PINECONE_INDEX_NAME=...       # optional; defaults to the prod index

# Ingest everything under data/rag_docs/
python -m scripts.rag_ingest

# Validate and embed without touching Pinecone
python -m scripts.rag_ingest --dry-run

# Ingest one file
python -m scripts.rag_ingest --file data/rag_docs/thorncliffe-park.json

# Remove a document's vectors entirely
python -m scripts.rag_ingest --delete-source thorncliffe-park-00
```

## Automation

`.github/workflows/rag-ingest.yml` runs the ingestion automatically on every
push to `main` that touches `data/rag_docs/**` or the ingest script, and can
be run manually from the Actions tab (with an optional dry-run flag).

Repository secrets required: `PINECONE_API_KEY`, `HF_TOKEN`.
Optional repository variable: `PINECONE_INDEX_NAME`.

## Design decisions (retriever compatibility)

These constraints come from `src/models/retrieval.py` and the legacy corpus —
breaking any of them makes newly ingested docs invisible or mangled:

| Constraint | Why |
|---|---|
| `lang` metadata field is always written (default `"en"`) | The retriever's primary query filters on `{"lang": {"$eq": "en"}}`; Pinecone `$eq` excludes vectors missing the field. |
| `url` is stored as a **list** | The legacy corpus stores `url` as a list and retrieval code indexes `url[0]`. |
| Chunk titles are unique (`"Title — part 2"`) | Retrieval deduplicates results by exact title and keeps only the first hit. |
| Dense vectors are **L2-normalized** | The legacy corpus was embedded with a normalizing local model; unnormalized vectors would sit on a different score scale than the similarity thresholds are tuned for. |
| Vector IDs are deterministic (`rag-<sha256(source_id)>-<chunk#>`) | Re-running the pipeline updates documents in place instead of duplicating them. |
| `PINECONE_INDEX_NAME` is honored by both the runtime and the ingest script | Prevents ingesting into an index the app never queries. |

## Community documents

Community-specific knowledge (e.g. the Thorncliffe Park collection in
`data/rag_docs/thorncliffe-park.json`) lives in the vector database, not in
the system prompt. The chatbot retrieves it like any other document when a
query mentions the community, and the system prompt instructs the model never
to fabricate neighbourhood-level data that isn't in retrieved documents.

To add a new community: create `data/rag_docs/<community>.json` with its
documents and merge to `main` — the Action ingests it. No code changes needed.

The Thorncliffe entries carry explicit `vector_id` values matching the IDs
originally written by the retired one-off ingest script, so re-ingesting them
updates the existing vectors instead of creating duplicates.
