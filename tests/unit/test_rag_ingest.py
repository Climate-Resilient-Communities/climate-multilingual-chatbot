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


def _write_minimal_pdf(path, text):
    """Create a tiny one-page born-digital PDF containing `text`."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n").encode()
    path.write_bytes(bytes(out))


class TestCollections:
    def test_collection_id_format(self):
        vid = make_vector_id("my-source", 2, collection="pdfs")
        assert vid.startswith("rag-pdfs-") and vid.endswith("-2")
        assert len(vid.split("-")) == 4

    def test_collection_slug_sanitized(self):
        from scripts.rag_ingest import slugify_collection
        assert slugify_collection("My PDFs-2026!") == "mypdfs2026"
        with pytest.raises(SystemExit):
            slugify_collection("---")

    def test_repo_sweep_never_touches_collection_vectors(self):
        from scripts.rag_ingest import prune_removed_sources
        kept = validate_document(_doc(source_id="kept-doc"), origin="test")
        collection_vid = make_vector_id("some-pdf", 0, collection="pdfs")
        removed_repo_vid = make_vector_id("removed-doc", 0)
        index = TestRemovedSourcePrune.FakeIndex([collection_vid, removed_repo_vid])
        prune_removed_sources(index, [kept])          # repo sweep
        assert removed_repo_vid in index.deleted
        assert collection_vid not in index.deleted

    def test_collection_sweep_scoped_to_its_namespace(self):
        from scripts.rag_ingest import prune_removed_sources
        kept = validate_document(_doc(source_id="kept-pdf"), origin="test")
        kept_vid = make_vector_id("kept-pdf", 0, collection="pdfs")
        removed_vid = make_vector_id("removed-pdf", 0, collection="pdfs")
        other_collection_vid = make_vector_id("other-doc", 0, collection="reports")
        repo_vid = make_vector_id("repo-doc", 0)
        index = TestRemovedSourcePrune.FakeIndex(
            [kept_vid, removed_vid, other_collection_vid, repo_vid])
        prune_removed_sources(index, [kept], collection="pdfs")
        assert removed_vid in index.deleted
        assert kept_vid not in index.deleted
        assert other_collection_vid not in index.deleted
        assert repo_vid not in index.deleted

    def test_external_dir_requires_collection(self, tmp_path):
        from scripts.rag_ingest import resolve_collection, DEFAULT_DOCS_DIR
        external = tmp_path / "doc.json"
        with pytest.raises(SystemExit):
            resolve_collection(None, [external])
        assert resolve_collection("pdfs", [external]) == "pdfs"
        repo_file = DEFAULT_DOCS_DIR / "thorncliffe-park.json"
        assert resolve_collection(None, [repo_file]) is None
        with pytest.raises(SystemExit):
            resolve_collection("pdfs", [repo_file])


class TestPdfLoading:
    def test_pdf_extracted_chunked_and_built(self, tmp_path):
        pytest.importorskip("pypdf")
        pdf = tmp_path / "flood-preparedness-guide.pdf"
        _write_minimal_pdf(pdf, "Climate adaptation and flooding preparedness guidance for cities. " * 4)
        (tmp_path / "flood-preparedness-guide.pdf.meta.json").write_text(
            '{"url": "https://example.com/guide", "doc_keywords": ["flooding"]}',
            encoding="utf-8",
        )
        loaded = load_documents([pdf])
        assert len(loaded) == 1
        doc = validate_document(loaded[0][1], origin=str(pdf))
        assert doc["title"] == "Flood Preparedness Guide"
        assert doc["url"] == "https://example.com/guide"
        assert doc["doc_keywords"] == ["flooding"]
        records = build_vectors([doc], collection="pdfs")
        assert records[0]["id"].startswith("rag-pdfs-")
        assert records[0]["metadata"]["url"] == ["https://example.com/guide"]
        assert records[0]["metadata"]["lang"] == "en"

    def test_sidecar_json_not_loaded_as_document(self, tmp_path):
        pytest.importorskip("pypdf")
        pdf = tmp_path / "guide.pdf"
        _write_minimal_pdf(pdf, "Climate adaptation guidance for cities and towns. " * 5)
        sidecar = tmp_path / "guide.pdf.meta.json"
        sidecar.write_text('{"title": "The Guide"}', encoding="utf-8")
        loaded = load_documents([pdf, sidecar])
        assert len(loaded) == 1

    def test_imageonly_pdf_rejected_with_clear_error(self, tmp_path):
        pytest.importorskip("pypdf")
        pdf = tmp_path / "scanned.pdf"
        _write_minimal_pdf(pdf, "x")  # effectively no extractable text
        with pytest.raises(SystemExit, match="OCR"):
            load_documents([pdf])


class TestRemovedSourcePrune:
    class FakeIndex:
        def __init__(self, ids):
            self._ids = ids
            self.deleted = []

        def list(self, prefix=""):
            yield [i for i in self._ids if i.startswith(prefix)]

        def delete(self, ids):
            self.deleted.extend(ids)

    def test_removed_source_vectors_deleted(self):
        from scripts.rag_ingest import prune_removed_sources, make_vector_id
        import hashlib

        kept = validate_document(_doc(source_id="kept-doc"), origin="test")
        kept_id = make_vector_id("kept-doc", 0)
        removed_id = make_vector_id("removed-doc", 0)
        legacy_id = "tp-legacy123"  # outside the rag- namespace: untouched

        index = self.FakeIndex([kept_id, removed_id, legacy_id])
        prune_removed_sources(index, [kept])

        assert removed_id in index.deleted
        assert kept_id not in index.deleted
        assert legacy_id not in index.deleted


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
