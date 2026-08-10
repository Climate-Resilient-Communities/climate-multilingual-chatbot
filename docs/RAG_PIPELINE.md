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
  5. prune                (stale chunks of shrunk docs are deleted; on full-corpus
                           runs, vectors of documents removed from data/rag_docs
                           are deleted too — the rag-<hash>-<chunk> ID scheme is
                           the manifest. Docs pinned to legacy vector IDs need
                           --delete-source if removed.)
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

## Large documents (PDFs) — local ingestion

Big source materials (e.g. 100MB PDF reports) must **never** be committed to
git — GitHub rejects files over 100MB and the repo would bloat permanently
(`data/rag_docs/**/*.pdf` is gitignored as a guard). Ingest them locally
instead, from any machine that has the two keys in its environment:

```bash
pip install pypdf
export PINECONE_API_KEY=...   # same values as the Azure App Service settings
export HF_TOKEN=...

python -m scripts.rag_ingest --dir ~/climate-pdfs --collection pdfs --dry-run
python -m scripts.rag_ingest --dir ~/climate-pdfs --collection pdfs
```

- Text is extracted per page (born-digital PDFs; scanned/image PDFs need OCR
  first, e.g. `ocrmypdf`), chunked, embedded, and upserted like any other doc.
- Title comes from a sidecar file > PDF metadata > the filename. Add a
  `<name>.pdf.meta.json` next to a PDF to set `title`, `url`, keywords, etc.
- **Collections are isolated namespaces**: vectors from `--collection pdfs`
  get IDs shaped `rag-pdfs-<hash>-<chunk>`, and each collection's
  removed-source sweep only ever touches its own namespace — so the GitHub
  Action syncing `data/rag_docs/` can never delete locally ingested PDFs,
  and re-running the local ingest updates them in place.
- Ingesting anything outside `data/rag_docs/` *requires* `--collection`;
  the tool refuses to run without it.

## Automation

`.github/workflows/rag-ingest.yml` runs the ingestion automatically on every
push to `main` that touches `data/rag_docs/**` or the ingest script, and can
be run manually from the Actions tab (with an optional dry-run flag).

Where the keys live matters: the **runtime app** reads them from Azure App
Service settings, but GitHub Actions runners cannot see Azure configuration.
CI ingestion therefore needs the two keys copied into GitHub as repository
secrets (`PINECONE_API_KEY`, `HF_TOKEN`; optional repository variable
`PINECONE_INDEX_NAME`). Until they are added the workflow skips with a
warning — alternatively, run the ingest locally (above) or from the Azure
App Service SSH console, where the environment already has the keys.

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
