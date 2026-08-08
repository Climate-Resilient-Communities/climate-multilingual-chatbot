"""Tests for the general-purpose RAG ingestion pipeline (scripts/rag_ingest.py)."""

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.rag_ingest import (
    build_vectors,
    chunk_text,
    embed_records,
    load_documents,
    make_vector_id,
    validate_document,
    CHUNK_TARGET_CHARS,
    MIN_CHUNK_CHARS,
)


class FakeEmbedder:
    """Mimics HFEmbedder.encode() with deterministic unnormalized vectors."""
    def encode(self, texts, **kwargs):
        vecs = np.array(
            [[float(len(t) % 7 + 1)] * 1024 for t in texts], dtype=np.float32
        )
        return {"dense_vecs": vecs, "lexical_weights": [{} for _ in texts]}


def _doc(title="Test Document", text=None, **overrides):
    doc = {
        "title": title,
        "text": text or ("Climate adaptation guidance for cities. " * 20),
        "url": "https://example.com/doc",
        "doc_keywords": ["climate"],
        "segment_keywords": ["adaptation"],
        "section_title": "Testing",
    }
    doc.update(overrides)
    return doc


class TestValidation:
    def test_valid_document_passes(self):
        doc = validate_document(_doc(), origin="test")
        assert doc["title"] == "Test Document"
        assert doc["lang"] == "en"
        assert doc["source_id"]

    def test_missing_title_fails(self):
        with pytest.raises(SystemExit):
            validate_document(_doc(title=""), origin="test")

    def test_short_text_fails(self):
        with pytest.raises(SystemExit):
            validate_document(_doc(text="too short"), origin="test")

    def test_chunk_text_field_accepted(self):
        raw = _doc()
        raw["chunk_text"] = raw.pop("text")
        doc = validate_document(raw, origin="test")
        assert len(doc["text"]) >= MIN_CHUNK_CHARS

    def test_source_id_stable(self):
        a = validate_document(_doc(), origin="test")
        b = validate_document(_doc(), origin="test")
        assert a["source_id"] == b["source_id"]


class TestChunking:
    def test_short_text_single_chunk(self):
        text = "One short paragraph about climate change adaptation planning."
        assert chunk_text(text) == [text]

    def test_long_text_splits_with_min_size(self):
        paragraphs = [f"Paragraph {i}. " + ("Content sentence. " * 30) for i in range(12)]
        chunks = chunk_text("\n\n".join(paragraphs))
        assert len(chunks) > 1
        assert all(len(c) >= MIN_CHUNK_CHARS for c in chunks)
        assert all(len(c) <= 2 * CHUNK_TARGET_CHARS for c in chunks)


class TestVectorBuilding:
    def test_metadata_matches_retriever_contract(self):
        doc = validate_document(_doc(), origin="test")
        records = build_vectors([doc])
        assert len(records) == 1
        md = records[0]["metadata"]
        # Fields src/models/retrieval.py reads
        assert md["chunk_text"]
        assert md["title"] == "Test Document"
        assert isinstance(md["url"], list) and md["url"] == ["https://example.com/doc"]
        assert md["lang"] == "en"  # required by the retriever's lang filter
        assert md["section_title"] == "Testing"
        assert md["segment_id"]

    def test_multi_chunk_titles_are_unique(self):
        # Retrieval dedups by exact title, so chunk titles must differ
        long_text = "\n\n".join(
            f"Paragraph {i}. " + ("Longer content sentence here. " * 40) for i in range(10)
        )
        doc = validate_document(_doc(text=long_text), origin="test")
        records = build_vectors([doc])
        assert len(records) > 1
        titles = [r["metadata"]["title"] for r in records]
        assert len(set(titles)) == len(titles)
        assert all("part" in t for t in titles)

    def test_deterministic_ids(self):
        doc = validate_document(_doc(), origin="test")
        first = build_vectors([doc])
        second = build_vectors([doc])
        assert [r["id"] for r in first] == [r["id"] for r in second]

    def test_explicit_vector_id_honored_for_single_chunk(self):
        doc = validate_document(_doc(vector_id="tp-legacy123"), origin="test")
        records = build_vectors([doc])
        assert records[0]["id"] == "tp-legacy123"
        assert doc.get("stale_legacy_id") is None

    def test_grown_legacy_doc_marks_old_vector_stale(self):
        # A doc with a legacy vector_id that now chunks into multiple parts
        # must flag the legacy vector for pruning, not leave it behind
        long_text = "\n\n".join(
            f"Paragraph {i}. " + ("Longer content sentence here. " * 40) for i in range(10)
        )
        doc = validate_document(_doc(text=long_text, vector_id="tp-legacy123"), origin="test")
        records = build_vectors([doc])
        assert len(records) > 1
        assert all(r["id"].startswith("rag-") for r in records)
        assert doc["stale_legacy_id"] == "tp-legacy123"

    def test_make_vector_id_format(self):
        vid = make_vector_id("my-source", 3)
        assert vid.startswith("rag-") and vid.endswith("-3")


class TestEmbedding:
    def test_vectors_are_l2_normalized(self):
        doc = validate_document(_doc(), origin="test")
        records = build_vectors([doc])
        embed_records(records, FakeEmbedder())
        for r in records:
            norm = np.linalg.norm(np.array(r["values"]))
            assert abs(norm - 1.0) < 1e-5
            assert len(r["values"]) == 1024


class TestLoading:
    def test_load_json_file(self, tmp_path):
        path = tmp_path / "docs.json"
        path.write_text(json.dumps([_doc(), _doc(title="Second Doc")]), encoding="utf-8")
        docs = load_documents([path])
        assert len(docs) == 2
        assert docs[0][1]["title"] == "Test Document"

    def test_load_markdown_with_front_matter(self, tmp_path):
        path = tmp_path / "heat-waves.md"
        path.write_text(
            "---\n"
            "url: https://example.com/heat\n"
            "doc_keywords: heat, toronto\n"
            "---\n"
            "# Heat Wave Guidance\n\n" + ("Stay cool during extreme heat. " * 20),
            encoding="utf-8",
        )
        docs = load_documents([path])
        assert len(docs) == 1
        raw = docs[0][1]
        assert raw["title"] == "Heat Wave Guidance"
        assert raw["url"] == "https://example.com/heat"
        assert raw["doc_keywords"] == ["heat", "toronto"]

    def test_thorncliffe_export_is_valid(self):
        """The migrated community docs must satisfy the pipeline contract."""
        path = Path(__file__).parent.parent.parent / "data" / "rag_docs" / "thorncliffe-park.json"
        docs = load_documents([path])
        assert len(docs) == 21
        validated = [validate_document(d, origin=str(path)) for _, d in docs]
        records = build_vectors(validated)
        # Single-chunk docs keep their legacy tp- vector IDs (update-in-place)
        assert all(r["id"].startswith("tp-") for r in records if r["metadata"]["chunk_index"] == 0)
        assert all(r["metadata"]["lang"] == "en" for r in records)
