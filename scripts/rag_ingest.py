"""
General-purpose RAG document ingestion/update pipeline for Pinecone.

Loads documents from data/rag_docs/ (JSON, JSONL, Markdown, or plain text),
chunks them, embeds with the same BGE-M3 embedder the runtime uses, and
upserts into the same Pinecone index the retriever queries. Re-running is
idempotent: vector IDs are deterministic, so edited documents update in
place and unchanged documents are simply overwritten with identical data.

Usage:
    python -m scripts.rag_ingest                       # ingest data/rag_docs/
    python -m scripts.rag_ingest --dir path/to/docs    # ingest another folder
    python -m scripts.rag_ingest --file doc.json       # ingest a single file
    python -m scripts.rag_ingest --dry-run             # embed + print, no upsert
    python -m scripts.rag_ingest --delete-source ID    # remove a doc's vectors

Document format (JSON list / JSONL, one object per document):
    {
      "title":            "Human-readable document title (required)",
      "text":             "Full document text (required; 'chunk_text' also accepted)",
      "url":              "https://source.example",           # optional
      "doc_keywords":     ["flooding", "toronto"],            # optional
      "segment_keywords": ["basement flooding"],              # optional
      "section_title":    "Collection name",                  # optional
      "lang":             "en",                               # optional, default en
      "source_id":        "stable-doc-slug",                  # optional, defaults to title+url hash
      "vector_id":        "legacy-vector-id"                  # optional, single-chunk docs only
    }

Markdown/plain-text files: the whole file is one document; the first
`# heading` (or the filename) becomes the title. Optional YAML-ish front
matter lines at the top ("key: value" between --- markers) may set url,
title, section_title, lang, and comma-separated keywords.

Metadata written per vector matches what src/models/retrieval.py reads:
    chunk_text, title, url (LIST — legacy corpus format), doc_keywords,
    segment_keywords, section_title, segment_id, lang, source_id, chunk_index.

Requires: PINECONE_API_KEY, HF_TOKEN in the environment.
Honors PINECONE_INDEX_NAME (same variable the runtime uses).
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils.env_loader import load_environment  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DOCS_DIR = Path(__file__).parent.parent / "data" / "rag_docs"
DEFAULT_INDEX = "climate-change-adaptation-index-10-24-prod"

# Chunking: sized so most curated documents stay single-chunk, while long
# scraped/pasted documents split on paragraph boundaries with overlap.
CHUNK_TARGET_CHARS = 2400
CHUNK_OVERLAP_CHARS = 300
MIN_CHUNK_CHARS = 200

EMBED_BATCH = 32
UPSERT_BATCH = 100


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _front_matter(text: str) -> tuple[Dict[str, str], str]:
    """Parse a leading '---' front-matter block of simple 'key: value' lines."""
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    meta: Dict[str, str] = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return meta, "\n".join(lines[i + 1:]).strip()
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip().lower()] = value.strip()
    return {}, text  # no closing marker — treat as regular content


def _doc_from_text_file(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    meta, body = _front_matter(raw)

    title = meta.get("title")
    if not title:
        heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = heading.group(1).strip() if heading else path.stem.replace("-", " ").replace("_", " ").title()

    doc: Dict[str, Any] = {
        "title": title,
        "text": body,
        "url": meta.get("url", ""),
        "section_title": meta.get("section_title", ""),
        "lang": meta.get("lang", "en"),
        "source_id": meta.get("source_id") or path.stem,
    }
    for key in ("doc_keywords", "segment_keywords"):
        if meta.get(key):
            doc[key] = [k.strip() for k in meta[key].split(",") if k.strip()]
    return doc


def load_documents(paths: Iterable[Path]) -> List[tuple[str, Dict[str, Any]]]:
    """Return (origin, raw_doc) pairs from every supported file."""
    docs: List[tuple[str, Dict[str, Any]]] = []
    for path in paths:
        try:
            if path.suffix.lower() == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                items = data if isinstance(data, list) else [data]
                docs.extend((str(path), item) for item in items)
            elif path.suffix.lower() == ".jsonl":
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        docs.append((str(path), json.loads(line)))
            elif path.suffix.lower() in (".md", ".txt"):
                docs.append((str(path), _doc_from_text_file(path)))
            else:
                logger.debug(f"Skipping unsupported file: {path}")
                continue
            logger.info(f"Loaded {path}")
        except Exception as e:
            raise SystemExit(f"Failed to load {path}: {e}")
    return docs


def validate_document(doc: Dict[str, Any], origin: str) -> Dict[str, Any]:
    title = (doc.get("title") or "").strip()
    text = (doc.get("text") or doc.get("chunk_text") or "").strip()
    if not title:
        raise SystemExit(f"Document from {origin} is missing 'title': {str(doc)[:120]}")
    if len(text) < MIN_CHUNK_CHARS:
        raise SystemExit(
            f"Document '{title}' ({origin}) text is too short ({len(text)} chars, "
            f"minimum {MIN_CHUNK_CHARS}) — not worth indexing."
        )
    url = doc.get("url") or ""
    source_id = (doc.get("source_id") or "").strip() or hashlib.sha256(
        f"{title}:{url}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "title": title,
        "text": text,
        "url": url,
        "doc_keywords": list(doc.get("doc_keywords") or []),
        "segment_keywords": list(doc.get("segment_keywords") or []),
        "section_title": doc.get("section_title") or "",
        "lang": (doc.get("lang") or "en").lower(),
        "source_id": source_id,
        "vector_id": doc.get("vector_id"),
    }


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, target: int = CHUNK_TARGET_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
    """Split on paragraph boundaries into ~target-char chunks with overlap."""
    if len(text) <= target:
        return [text]

    paragraphs = re.split(r"\n\s*\n", text)
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current and len(current) + len(para) + 2 > target:
            chunks.append(current.strip())
            # Overlap: carry the tail of the previous chunk forward for context
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current.strip():
        chunks.append(current.strip())

    # Guard: a single paragraph longer than 2×target gets hard-split
    final: List[str] = []
    for chunk in chunks:
        while len(chunk) > 2 * target:
            final.append(chunk[:target])
            chunk = chunk[target - overlap:]
        final.append(chunk)
    return [c for c in final if len(c) >= MIN_CHUNK_CHARS] or [text[:target]]


# ---------------------------------------------------------------------------
# Vector building
# ---------------------------------------------------------------------------

def make_vector_id(source_id: str, chunk_index: int) -> str:
    return f"rag-{hashlib.sha256(source_id.encode('utf-8')).hexdigest()[:16]}-{chunk_index}"


def build_vectors(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for doc in docs:
        chunks = chunk_text(doc["text"])
        multi = len(chunks) > 1
        # A doc that carried a legacy vector_id but now splits into multiple
        # chunks gets fresh deterministic IDs — mark the legacy vector stale
        # so prune can remove it instead of leaving outdated content behind.
        doc["stale_legacy_id"] = doc["vector_id"] if (doc["vector_id"] and multi) else None
        for i, chunk in enumerate(chunks):
            # Retrieval dedups by exact title and keeps only the first hit,
            # so multi-chunk documents need unique per-chunk titles.
            title = f"{doc['title']} — part {i + 1}" if multi else doc["title"]
            vec_id = doc["vector_id"] if (doc["vector_id"] and not multi) else make_vector_id(doc["source_id"], i)
            records.append({
                "id": vec_id,
                "chunk": chunk,
                "metadata": {
                    "chunk_text": chunk,
                    "title": title,
                    # url as a LIST matches the legacy corpus; several
                    # retrieval paths index url[0].
                    "url": [doc["url"]] if doc["url"] else [],
                    "doc_keywords": doc["doc_keywords"],
                    "segment_keywords": doc["segment_keywords"],
                    "section_title": doc["section_title"],
                    "segment_id": f"{doc['source_id']}-{i}",
                    # The retriever's primary query filters on lang — vectors
                    # without this field are invisible to the filtered path.
                    "lang": doc["lang"],
                    "source_id": doc["source_id"],
                    "chunk_index": i,
                },
            })
        logger.info(f"  '{doc['title']}' → {len(chunks)} chunk(s) [source_id={doc['source_id']}]")
    return records


def embed_records(records: List[Dict[str, Any]], embedder) -> None:
    """Attach L2-normalized dense vectors to records in place (BGE-M3, 1024-dim)."""
    texts = [r["chunk"] for r in records]
    all_vecs: List[np.ndarray] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        result = embedder.encode(batch)
        all_vecs.append(np.asarray(result["dense_vecs"], dtype=np.float32))
        logger.info(f"  Embedded {min(i + EMBED_BATCH, len(texts))}/{len(texts)}")
    dense = np.concatenate(all_vecs, axis=0)
    # L2-normalize so new vectors share the legacy corpus's score scale
    norms = np.linalg.norm(dense, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    dense = dense / norms
    for record, vec in zip(records, dense):
        record["values"] = vec.tolist()


# ---------------------------------------------------------------------------
# Pinecone operations
# ---------------------------------------------------------------------------

def get_index(index_name: str):
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(index_name)


def upsert_records(index, records: List[Dict[str, Any]]) -> None:
    payload = [
        {"id": r["id"], "values": r["values"], "metadata": r["metadata"]}
        for r in records
    ]
    for i in range(0, len(payload), UPSERT_BATCH):
        batch = payload[i:i + UPSERT_BATCH]
        index.upsert(vectors=batch)
        logger.info(f"  Upserted {min(i + UPSERT_BATCH, len(payload))}/{len(payload)}")


def prune_stale_chunks(index, docs: List[Dict[str, Any]], records: List[Dict[str, Any]]) -> None:
    """Delete leftover chunks from docs that shrank since the last ingest."""
    stale_legacy = [d["stale_legacy_id"] for d in docs if d.get("stale_legacy_id")]
    if stale_legacy:
        try:
            index.delete(ids=stale_legacy)
            logger.info(f"  Pruned {len(stale_legacy)} superseded legacy vector(s)")
        except Exception as e:
            logger.warning(f"  Legacy-vector prune skipped: {e}")

    counts: Dict[str, int] = {}
    for r in records:
        sid = r["metadata"]["source_id"]
        counts[sid] = max(counts.get(sid, 0), r["metadata"]["chunk_index"] + 1)
    for doc in docs:
        sid = doc["source_id"]
        prefix = f"rag-{hashlib.sha256(sid.encode('utf-8')).hexdigest()[:16]}-"
        try:
            stale = [
                vid for page in index.list(prefix=prefix) for vid in page
                if int(str(vid).rsplit("-", 1)[-1]) >= counts.get(sid, 0)
            ]
            if stale:
                index.delete(ids=stale)
                logger.info(f"  Pruned {len(stale)} stale chunk(s) for source '{sid}'")
        except Exception as e:
            logger.warning(f"  Prune skipped for '{sid}' (list API unavailable?): {e}")


def prune_removed_sources(index, docs: List[Dict[str, Any]]) -> None:
    """Delete vectors whose source document was removed from the corpus.

    The deterministic ID scheme (rag-<sha16(source_id)>-<chunk>) doubles as the
    manifest: any rag-* vector whose source-hash segment is absent from the
    current corpus belongs to a deleted document. Only run this for a FULL
    corpus ingest — a single-file run must never delete other files' vectors.
    """
    current_hashes = {
        hashlib.sha256(d["source_id"].encode("utf-8")).hexdigest()[:16] for d in docs
    }
    try:
        stale_ids = []
        for page in index.list(prefix="rag-"):
            for vid in page:
                parts = str(vid).split("-")
                if len(parts) >= 3 and parts[0] == "rag" and parts[1] not in current_hashes:
                    stale_ids.append(str(vid))
        if stale_ids:
            for i in range(0, len(stale_ids), 1000):
                index.delete(ids=stale_ids[i:i + 1000])
            logger.info(f"  Pruned {len(stale_ids)} vector(s) from sources removed from the corpus")
    except Exception as e:
        logger.warning(f"  Removed-source prune skipped (list API unavailable?): {e}")

    # Docs pinned to legacy vector IDs live outside the rag- namespace and
    # cannot be swept automatically if their entry is deleted later.
    legacy = [d["source_id"] for d in docs if d.get("vector_id")]
    if legacy:
        logger.info(
            f"  Note: {len(legacy)} document(s) use legacy vector IDs; if one is removed "
            f"from the corpus later, delete its vector with --delete-source <source_id>."
        )


def delete_source(index, source_id: str) -> None:
    prefix = f"rag-{hashlib.sha256(source_id.encode('utf-8')).hexdigest()[:16]}-"
    ids = [vid for page in index.list(prefix=prefix) for vid in page]
    if ids:
        index.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} vector(s) for source '{source_id}'")
    else:
        logger.info(f"No vectors found for source '{source_id}' (prefix {prefix})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest/update RAG documents in Pinecone")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DOCS_DIR,
                        help=f"Directory of docs to ingest (default: {DEFAULT_DOCS_DIR})")
    parser.add_argument("--file", type=Path, action="append", default=None,
                        help="Ingest specific file(s) instead of --dir")
    parser.add_argument("--dry-run", action="store_true",
                        help="Load, chunk, and embed but skip all Pinecone writes")
    parser.add_argument("--no-prune", action="store_true",
                        help="Skip deleting stale chunks of shrunk documents")
    parser.add_argument("--delete-source", metavar="SOURCE_ID",
                        help="Delete all vectors for one source_id, then exit")
    args = parser.parse_args()

    load_environment()

    index_name = os.getenv("PINECONE_INDEX_NAME") or DEFAULT_INDEX
    logger.info(f"Target index: {index_name}")

    if args.delete_source:
        delete_source(get_index(index_name), args.delete_source)
        return

    if args.file:
        paths = args.file
    else:
        if not args.dir.is_dir():
            raise SystemExit(f"Docs directory not found: {args.dir}")
        paths = sorted(
            p for p in args.dir.rglob("*")
            if p.is_file() and p.suffix.lower() in (".json", ".jsonl", ".md", ".txt")
            and p.name.lower() != "readme.md"
        )
    if not paths:
        raise SystemExit("No documents found to ingest.")

    raw_docs = load_documents(paths)
    docs = [validate_document(d, origin=origin) for origin, d in raw_docs]
    logger.info(f"Validated {len(docs)} document(s)")

    # Duplicate source_id guard — two docs sharing an ID would overwrite each other
    seen: Dict[str, str] = {}
    for doc in docs:
        if doc["source_id"] in seen:
            raise SystemExit(
                f"Duplicate source_id '{doc['source_id']}' for '{doc['title']}' "
                f"and '{seen[doc['source_id']]}' — give one an explicit unique source_id."
            )
        seen[doc["source_id"]] = doc["title"]

    logger.info("Chunking...")
    from src.models.cohere_flow import HFEmbedder
    records = build_vectors(docs)
    logger.info(f"Built {len(records)} chunk(s) from {len(docs)} document(s)")

    logger.info("Embedding with BGE-M3 (HuggingFace Inference API)...")
    embedder = HFEmbedder()
    embed_records(records, embedder)

    if args.dry_run:
        logger.info("DRY RUN — skipping Pinecone upsert")
        for r in records:
            logger.info(
                f"  Would upsert {r['id']} | dim={len(r['values'])} | "
                f"title='{r['metadata']['title'][:60]}' | lang={r['metadata']['lang']} | "
                f"{len(r['metadata']['chunk_text'])} chars"
            )
        return

    index = get_index(index_name)
    logger.info(f"Upserting {len(records)} vector(s)...")
    upsert_records(index, records)

    if not args.no_prune:
        prune_stale_chunks(index, docs, records)
        # Removed-source sweep only makes sense when the full corpus was loaded
        if not args.file:
            prune_removed_sources(index, docs)

    try:
        stats = index.describe_index_stats()
        logger.info(f"Done. Index now has {stats.total_vector_count} total vectors")
    except Exception:
        logger.info("Done.")


if __name__ == "__main__":
    main()
