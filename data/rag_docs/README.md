# RAG Documents

This directory is the source of truth for curated documents in the chatbot's
Pinecone knowledge base. Every `.json`, `.jsonl`, `.md`, and `.txt` file here
is ingested by `scripts/rag_ingest.py` — automatically via the
[`rag-ingest` GitHub Action](../../.github/workflows/rag-ingest.yml) whenever
files in this directory change on `main`, or manually:

```bash
python -m scripts.rag_ingest            # ingest everything in this directory
python -m scripts.rag_ingest --dry-run  # validate + embed without writing
```

## Adding or updating documents

**JSON** (list of documents, preferred for curated collections):

```json
[
  {
    "title": "Unique, human-readable document title",
    "text": "Full document text...",
    "url": "https://authoritative-source.example",
    "doc_keywords": ["flooding", "toronto"],
    "segment_keywords": ["basement flooding"],
    "section_title": "Collection name",
    "source_id": "stable-doc-slug"
  }
]
```

**Markdown** (one document per file, optional front matter):

```markdown
---
url: https://authoritative-source.example
doc_keywords: heat, toronto
---
# Document Title

Document text...
```

## Rules

- `title` must be unique across the whole knowledge base — retrieval
  deduplicates by exact title.
- `source_id` is the update key: keep it stable so edits update the existing
  vectors instead of creating duplicates. It defaults to a hash of
  `title:url`, so renaming a doc without setting `source_id` orphans the old
  vectors (remove them with `--delete-source <old-id>`).
- Text under 200 characters is rejected — not worth indexing.
- Long documents are chunked automatically (~2400 chars per chunk, paragraph
  boundaries, with overlap); chunk titles get a `— part N` suffix.

## Large files (PDFs)

Do **not** put big PDFs in this directory — GitHub rejects files over 100MB
and the repo would bloat permanently (`*.pdf` here is gitignored as a guard).
Ingest them locally instead, into an isolated collection namespace:

```bash
pip install pypdf
python -m scripts.rag_ingest --dir ~/climate-pdfs --collection pdfs
```

See `docs/RAG_PIPELINE.md` for the full pipeline documentation, including
local PDF ingestion and where the API keys need to live.
