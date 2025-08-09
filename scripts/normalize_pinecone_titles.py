#!/usr/bin/env python3
"""
Normalize document titles stored in Pinecone metadata.

This script iterates through vectors in the configured Pinecone index,
derives a cleaned title using src.models.title_normalizer.normalize_title,
and updates metadata when the normalized title differs.

Requirements:
  - Environment variables: PINECONE_API_KEY, optional PINECONE_ENV
  - Config: RETRIEVAL_CONFIG["pinecone_index"] set to index name

Usage:
  python scripts/normalize_pinecone_titles.py [--limit 100] [--dry-run]

Notes:
  - Uses Pinecone v3 SDK (from pinecone import Pinecone)
  - Relies on Index.list(...) pagination if available. If your SDK does not
    support listing vectors, you will need to provide IDs from your ingestion
    pipeline and update via index.update(id=..., set_metadata={...}).
"""

import argparse
import os
import sys
from typing import Iterator, Tuple, Dict, Any

from src.utils.env_loader import load_environment
from src.data.config.config import RETRIEVAL_CONFIG
from src.models.title_normalizer import normalize_title


def iter_vectors(index, page_size: int) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Yield (id, metadata) for each vector using Index.list pagination if available."""
    cursor = None
    while True:
        # Call signatures vary across SDK versions; try both
        try:
            if cursor:
                res = index.list(limit=page_size, include_metadata=True, pagination_token=cursor)
            else:
                res = index.list(limit=page_size, include_metadata=True)
        except TypeError:
            # Fallback: older SDK may accept 'cursor' instead of 'pagination_token'
            if cursor:
                res = index.list(limit=page_size, include_metadata=True, cursor=cursor)
            else:
                res = index.list(limit=page_size, include_metadata=True)

        # Normalize response access across SDK versions
        vectors = getattr(res, "vectors", None) or (res.get("vectors") if isinstance(res, dict) else None) or []
        for v in vectors:
            vid = getattr(v, "id", None) or (v.get("id") if isinstance(v, dict) else None)
            metadata = getattr(v, "metadata", None) or (v.get("metadata") if isinstance(v, dict) else {})
            if vid is not None:
                yield str(vid), (metadata or {})

        # Pagination token
        next_token = None
        if hasattr(res, "pagination"):
            next_token = getattr(res.pagination, "next", None)
        elif isinstance(res, dict):
            pagination = res.get("pagination") or {}
            next_token = pagination.get("next")

        if not next_token:
            break
        cursor = next_token


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Pinecone titles in metadata")
    parser.add_argument("--limit", type=int, default=200, help="Page size when listing vectors")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without updating metadata")
    args = parser.parse_args()

    load_environment()
    index_name = RETRIEVAL_CONFIG.get("pinecone_index") or os.getenv("PINECONE_INDEX_NAME")
    if not index_name:
        print("ERROR: No index name configured (RETRIEVAL_CONFIG.pinecone_index or PINECONE_INDEX_NAME)")
        return 2

    try:
        from pinecone import Pinecone
    except Exception as e:
        print(f"ERROR: Failed to import pinecone SDK: {e}")
        return 3

    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("ERROR: PINECONE_API_KEY not set")
        return 4

    pc = Pinecone(api_key=api_key)
    index = pc.Index(index_name)

    total = 0
    changed = 0
    skipped = 0
    failed = 0

    print(f"Scanning index '{index_name}' for title normalization (page size={args.limit})...")

    for vid, md in iter_vectors(index, args.limit):
        total += 1
        raw_title = md.get("title", "")
        sec_title = md.get("section_title", "")
        url = md.get("url", [])

        normalized = normalize_title(raw_title, sec_title, url)
        if normalized and normalized != raw_title:
            changed += 1
            print(f"- id={vid} title: '{raw_title}' -> '{normalized}'")
            if not args.dry_run:
                try:
                    # Update only the title; preserve other metadata
                    # Pinecone v3 supports partial metadata update via set_metadata
                    index.update(id=vid, set_metadata={"title": normalized})
                except Exception as e:
                    failed += 1
                    print(f"  ERROR updating id={vid}: {e}")
        else:
            skipped += 1

    print("\nDone.")
    print(f"Total scanned: {total}")
    print(f"Changed titles: {changed}")
    print(f"Skipped (no change): {skipped}")
    print(f"Failed updates: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


