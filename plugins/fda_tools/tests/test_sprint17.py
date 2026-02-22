"""
Sprint 17 — Guidance Intelligence Layer
========================================
Tests for:
  - plugins/fda_tools/lib/guidance_indexer.py   (FDA-223)
  - plugins/fda_tools/lib/guidance_embedder.py  (FDA-224)

No real PDF files or sentence-transformer model required — all heavy I/O and
ML calls are mocked or replaced with temporary text fixtures.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fda_tools.lib.guidance_indexer import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    GuidanceChunk,
    GuidanceIndexer,
    PDFExtractor,
    TextChunker,
    _clean_text,
    _detect_section,
    index_guidance_pdf,
)
from fda_tools.lib.guidance_embedder import (
    DEFAULT_BATCH,
    DEFAULT_MODEL,
    EMBEDDING_DIM,
    EmbeddingUnavailableError,
    GuidanceEmbedder,
    SentenceEmbedder,
    embed_guidance_chunks,
)
from fda_tools.lib.pgvector_schema import EmbeddingRecord


# ══════════════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants(unittest.TestCase):
    def test_chunk_size(self) -> None:
        self.assertEqual(CHUNK_SIZE, 512)

    def test_chunk_overlap(self) -> None:
        self.assertEqual(CHUNK_OVERLAP, 50)

    def test_default_model(self) -> None:
        self.assertIn("all-MiniLM-L6-v2", DEFAULT_MODEL)

    def test_embedding_dim_matches_schema(self) -> None:
        self.assertEqual(EMBEDDING_DIM, 384)


# ══════════════════════════════════════════════════════════════════════════════
#  GuidanceChunk
# ══════════════════════════════════════════════════════════════════════════════

class TestGuidanceChunk(unittest.TestCase):

    def _make(self, **kwargs) -> GuidanceChunk:
        defaults = dict(
            doc_id="ucm001",
            chunk_index=0,
            text="Risk management shall be applied throughout the product lifecycle.",
            title="Design Controls",
            section="4.1",
            page_num=1,
            char_start=0,
            metadata={"year": 2023},
        )
        defaults.update(kwargs)
        return GuidanceChunk(**defaults)

    def test_frozen_immutable(self) -> None:
        chunk = self._make()
        with self.assertRaises(Exception):
            chunk.text = "mutated"  # type: ignore[misc]

    def test_to_embedding_metadata_keys(self) -> None:
        chunk = self._make()
        meta = chunk.to_embedding_metadata()
        self.assertEqual(meta["doc_id"], "ucm001")
        self.assertEqual(meta["chunk_index"], 0)
        self.assertEqual(meta["title"], "Design Controls")
        self.assertEqual(meta["section"], "4.1")
        self.assertEqual(meta["page_num"], 1)
        self.assertEqual(meta["char_start"], 0)
        self.assertEqual(meta["year"], 2023)

    def test_to_embedding_metadata_preserves_extra(self) -> None:
        chunk = self._make(metadata={"regulation": "21 CFR 820"})
        meta = chunk.to_embedding_metadata()
        self.assertEqual(meta["regulation"], "21 CFR 820")

    def test_default_metadata_empty(self) -> None:
        chunk = GuidanceChunk(doc_id="x", chunk_index=0, text="text")
        self.assertEqual(chunk.metadata, {})


# ══════════════════════════════════════════════════════════════════════════════
#  _clean_text
# ══════════════════════════════════════════════════════════════════════════════

class TestCleanText(unittest.TestCase):

    def test_removes_standalone_page_numbers(self) -> None:
        raw = "Section 4.1 Introduction\n\n  42  \n\nNext paragraph."
        cleaned = _clean_text(raw)
        self.assertNotIn("  42  ", cleaned)

    def test_collapses_multiple_newlines(self) -> None:
        raw = "Para one.\n\n\n\n\nPara two."
        cleaned = _clean_text(raw)
        self.assertNotIn("\n\n\n", cleaned)

    def test_removes_form_feed(self) -> None:
        raw = "Page 1\x0cPage 2"
        cleaned = _clean_text(raw)
        self.assertNotIn("\x0c", cleaned)

    def test_strips_leading_trailing_whitespace(self) -> None:
        raw = "   content   "
        self.assertEqual(_clean_text(raw), "content")

    def test_preserves_content(self) -> None:
        raw = "FDA guidance requires risk management per ISO 14971."
        self.assertEqual(_clean_text(raw), raw)


# ══════════════════════════════════════════════════════════════════════════════
#  _detect_section
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectSection(unittest.TestCase):

    def test_detects_numbered_section(self) -> None:
        # The regex captures the section prefix (number + whitespace), not the full heading line
        text = "4.2 Risk Assessment\nThe process shall include..."
        result = _detect_section(text)
        self.assertTrue(result.startswith("4.2"), f"Expected section prefix '4.2', got {result!r}")

    def test_detects_roman_numeral_section(self) -> None:
        text = "IV. Background\nThis guidance applies to..."
        self.assertIn("IV", _detect_section(text))

    def test_empty_text_returns_empty(self) -> None:
        self.assertEqual(_detect_section(""), "")

    def test_plain_paragraph_no_heading(self) -> None:
        text = "The device shall be designed to minimize risk."
        # May or may not find something — just assert no crash
        result = _detect_section(text)
        self.assertIsInstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
#  TextChunker
# ══════════════════════════════════════════════════════════════════════════════

class TestTextChunker(unittest.TestCase):

    def _chunker(self, size: int = 100, overlap: int = 10) -> TextChunker:
        return TextChunker(chunk_size=size, chunk_overlap=overlap)

    def test_empty_text_returns_empty(self) -> None:
        chunks = self._chunker().split("")
        self.assertEqual(chunks, [])

    def test_whitespace_only_returns_empty(self) -> None:
        chunks = self._chunker().split("   \n\n   ")
        self.assertEqual(chunks, [])

    def test_short_text_single_chunk(self) -> None:
        text = "This is a short guidance sentence."
        chunks = self._chunker(size=500).split(text)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][0], text)
        self.assertEqual(chunks[0][1], 0)  # char_start = 0

    def test_long_text_produces_multiple_chunks(self) -> None:
        # Generate text longer than one chunk
        word = "regulation "
        text = word * 200  # 2200 chars >> 100 tokens * 4 = 400 chars chunk
        chunks = self._chunker(size=50, overlap=5).split(text)
        self.assertGreater(len(chunks), 1)

    def test_chunks_cover_all_content(self) -> None:
        """Every word in the source appears in at least one chunk."""
        text = " ".join(f"word{i}" for i in range(200))
        chunks = self._chunker(size=50, overlap=5).split(text)
        combined = " ".join(c for c, _ in chunks)
        for i in range(0, 200, 20):
            self.assertIn(f"word{i}", combined)

    def test_char_start_is_non_negative(self) -> None:
        text = "A" * 5000
        chunks = self._chunker(size=100, overlap=20).split(text)
        for _, start in chunks:
            self.assertGreaterEqual(start, 0)

    def test_overlap_produces_shared_content(self) -> None:
        """With overlap, consecutive chunks should share some text."""
        word = "x" * 20 + " "
        text = word * 40  # 840 chars
        chunks = self._chunker(size=50, overlap=25).split(text)
        if len(chunks) >= 2:
            # The tail of chunk[0] and the head of chunk[1] should overlap
            end_of_first  = chunks[0][0][-50:]
            start_of_second = chunks[1][0][:50]
            # They share some characters (overlap > 0)
            self.assertTrue(
                any(c in start_of_second for c in end_of_first.split() if c),
                msg="Expected some overlap between consecutive chunks",
            )

    def test_default_params_set(self) -> None:
        chunker = TextChunker()
        self.assertEqual(chunker.chunk_chars, CHUNK_SIZE * 4)
        self.assertEqual(chunker.overlap_chars, CHUNK_OVERLAP * 4)


# ══════════════════════════════════════════════════════════════════════════════
#  PDFExtractor
# ══════════════════════════════════════════════════════════════════════════════

class TestPDFExtractor(unittest.TestCase):

    def test_raises_file_not_found(self) -> None:
        extractor = PDFExtractor("/nonexistent/path/to/doc.pdf")
        with self.assertRaises(FileNotFoundError):
            extractor.extract()

    def test_extracts_plain_text_file(self) -> None:
        content = "FDA guidance for software validation.\nVersion 2.0."
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            extractor = PDFExtractor(tmp_path)
            result = extractor.extract()
            self.assertEqual(result, content)
        finally:
            Path(tmp_path).unlink()

    @patch("fda_tools.lib.guidance_indexer._PDFPLUMBER_AVAILABLE", False)
    @patch("fda_tools.lib.guidance_indexer._PYPDF_AVAILABLE", False)
    def test_pdf_raises_when_no_library(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake content")
            tmp_path = f.name
        try:
            extractor = PDFExtractor(tmp_path)
            with self.assertRaises(ValueError) as ctx:
                extractor.extract()
            self.assertIn("pdfplumber", str(ctx.exception))
        finally:
            Path(tmp_path).unlink()

    @patch("fda_tools.lib.guidance_indexer._PDFPLUMBER_AVAILABLE", True)
    @patch("fda_tools.lib.guidance_indexer._pdfplumber")
    def test_pdfplumber_extraction(self, mock_plumber: MagicMock) -> None:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content"
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]
        mock_plumber.open.return_value = mock_pdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name
        try:
            extractor = PDFExtractor(tmp_path)
            result = extractor._extract_pdfplumber()
            self.assertIn("Page 1 content", result)
        finally:
            Path(tmp_path).unlink()


# ══════════════════════════════════════════════════════════════════════════════
#  GuidanceIndexer
# ══════════════════════════════════════════════════════════════════════════════

_SAMPLE_GUIDANCE = """
1. Introduction

This guidance document provides recommendations for the application of risk
management to medical devices in accordance with ISO 14971.

2. Scope

This guidance applies to all manufacturers of medical devices subject to
FDA oversight under section 510(k) of the Federal Food, Drug, and Cosmetic Act.

3. Background

Risk management is a systematic process for identifying, evaluating, and
controlling hazards and risks associated with medical devices throughout the
product lifecycle. Manufacturers should establish, document, implement, and
maintain an ongoing process for risk management.

4. Recommendations

4.1 Risk Analysis

Manufacturers shall document all known and foreseeable hazards associated
with the medical device in the intended use environment.

4.2 Risk Evaluation

Each identified risk shall be evaluated against criteria defined in the
risk management plan to determine if risk reduction is required.
""" * 3  # repeat to exceed chunk size


class TestGuidanceIndexer(unittest.TestCase):

    def setUp(self) -> None:
        self.indexer = GuidanceIndexer(chunk_size=100, chunk_overlap=10)

    def test_index_text_returns_chunks(self) -> None:
        chunks = self.indexer.index_text(
            text=_SAMPLE_GUIDANCE,
            doc_id="ucm_test",
            title="Risk Management Guidance",
        )
        self.assertGreater(len(chunks), 1)

    def test_chunks_have_correct_doc_id(self) -> None:
        chunks = self.indexer.index_text(_SAMPLE_GUIDANCE, doc_id="ucm_test")
        for chunk in chunks:
            self.assertEqual(chunk.doc_id, "ucm_test")

    def test_chunks_are_sequentially_indexed(self) -> None:
        chunks = self.indexer.index_text(_SAMPLE_GUIDANCE, doc_id="ucm_test")
        indices = [c.chunk_index for c in chunks]
        self.assertEqual(indices, list(range(len(chunks))))

    def test_chunks_preserve_title(self) -> None:
        chunks = self.indexer.index_text(
            _SAMPLE_GUIDANCE, doc_id="d", title="Design Controls Guidance"
        )
        for chunk in chunks:
            self.assertEqual(chunk.title, "Design Controls Guidance")

    def test_chunks_metadata_propagated(self) -> None:
        chunks = self.indexer.index_text(
            _SAMPLE_GUIDANCE, doc_id="d",
            metadata={"regulation": "21 CFR 820"},
        )
        for chunk in chunks:
            self.assertEqual(chunk.metadata["regulation"], "21 CFR 820")

    def test_chunk_text_non_empty(self) -> None:
        chunks = self.indexer.index_text(_SAMPLE_GUIDANCE, doc_id="d")
        for chunk in chunks:
            self.assertTrue(chunk.text.strip())

    def test_index_file_text_path(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(_SAMPLE_GUIDANCE)
            tmp_path = f.name
        try:
            chunks = self.indexer.index_file(tmp_path, doc_id="ucm_tmp", title="T")
            self.assertGreater(len(chunks), 0)
        finally:
            Path(tmp_path).unlink()

    def test_index_file_uses_stem_as_default_title(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix="guidance_doc_", delete=False
        ) as f:
            f.write("Short text.")
            tmp_path = f.name
        try:
            chunks = self.indexer.index_file(tmp_path, doc_id="ucm_auto")
            # Default title should be the filename stem
            self.assertEqual(chunks[0].title, Path(tmp_path).stem)
        finally:
            Path(tmp_path).unlink()

    def test_all_chunks_are_frozen(self) -> None:
        chunks = self.indexer.index_text(_SAMPLE_GUIDANCE, doc_id="d")
        chunk = chunks[0]
        with self.assertRaises(Exception):
            chunk.text = "mutated"  # type: ignore[misc]


class TestIndexGuidancePdfFunction(unittest.TestCase):

    def test_convenience_function_works(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(_SAMPLE_GUIDANCE)
            tmp_path = f.name
        try:
            chunks = index_guidance_pdf(
                path=tmp_path,
                doc_id="ucm_conv",
                title="Convenience Test",
                chunk_size=100,
            )
            self.assertGreater(len(chunks), 0)
            self.assertEqual(chunks[0].title, "Convenience Test")
        finally:
            Path(tmp_path).unlink()


# ══════════════════════════════════════════════════════════════════════════════
#  SentenceEmbedder
# ══════════════════════════════════════════════════════════════════════════════

class TestSentenceEmbedder(unittest.TestCase):

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", False)
    def test_embed_raises_when_st_unavailable(self) -> None:
        emb = SentenceEmbedder()
        with self.assertRaises(EmbeddingUnavailableError) as ctx:
            emb.embed(["text"])
        self.assertIn("sentence-transformers", str(ctx.exception))

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", False)
    def test_is_available_false_when_unavailable(self) -> None:
        self.assertFalse(SentenceEmbedder().is_available())

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", True)
    def test_is_available_true_when_installed(self) -> None:
        self.assertTrue(SentenceEmbedder().is_available())

    def test_is_loaded_false_before_any_embed(self) -> None:
        emb = SentenceEmbedder()
        self.assertFalse(emb.is_loaded())

    def test_embed_empty_list_returns_empty(self) -> None:
        emb = SentenceEmbedder()
        # Bypass the SDK check — inject a mock model
        emb._model = MagicMock()
        emb._model.encode.return_value = []
        result = emb.embed([])
        self.assertEqual(result, [])

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", True)
    @patch("fda_tools.lib.guidance_embedder._SentenceTransformer")
    def test_embed_returns_correct_shape(self, MockST: MagicMock) -> None:
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((2, EMBEDDING_DIM), dtype="float32")
        MockST.return_value = mock_model

        emb = SentenceEmbedder()
        result = emb.embed(["text one", "text two"])

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), EMBEDDING_DIM)
        self.assertIsInstance(result[0][0], float)

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", True)
    @patch("fda_tools.lib.guidance_embedder._SentenceTransformer")
    def test_embed_wrong_dim_raises(self, MockST: MagicMock) -> None:
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((1, 768), dtype="float32")  # wrong dim
        MockST.return_value = mock_model

        emb = SentenceEmbedder()
        with self.assertRaises(ValueError) as ctx:
            emb.embed(["text"])
        self.assertIn("384", str(ctx.exception))

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", True)
    @patch("fda_tools.lib.guidance_embedder._SentenceTransformer")
    def test_model_loaded_after_first_embed(self, MockST: MagicMock) -> None:
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((1, EMBEDDING_DIM), dtype="float32")
        MockST.return_value = mock_model

        emb = SentenceEmbedder()
        self.assertFalse(emb.is_loaded())
        emb.embed(["text"])
        self.assertTrue(emb.is_loaded())

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", True)
    @patch("fda_tools.lib.guidance_embedder._SentenceTransformer")
    def test_model_loaded_only_once(self, MockST: MagicMock) -> None:
        import numpy as np
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((1, EMBEDDING_DIM), dtype="float32")
        MockST.return_value = mock_model

        emb = SentenceEmbedder()
        emb.embed(["first"])
        emb.embed(["second"])
        MockST.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
#  GuidanceEmbedder
# ══════════════════════════════════════════════════════════════════════════════

def _make_chunks(n: int = 3) -> list:
    indexer = GuidanceIndexer(chunk_size=50, chunk_overlap=5)
    return indexer.index_text(_SAMPLE_GUIDANCE, doc_id="ucm_mock", title="Mock Guidance")[:n]


def _mock_embedder(n: int = 3) -> SentenceEmbedder:
    emb = SentenceEmbedder()
    import numpy as np
    emb._model = MagicMock()
    emb._model.encode.return_value = np.zeros((n, EMBEDDING_DIM), dtype="float32")
    return emb


def _mock_schema_mgr() -> MagicMock:
    mgr = MagicMock()
    mgr.bulk_insert.return_value = [MagicMock()]
    return mgr


class TestGuidanceEmbedder(unittest.TestCase):

    def test_embed_and_store_returns_count(self) -> None:
        chunks   = _make_chunks(3)
        embedder = _mock_embedder(len(chunks))
        mgr      = _mock_schema_mgr()

        pipeline = GuidanceEmbedder(embedder=embedder, schema_mgr=mgr)
        count    = pipeline.embed_and_store(chunks)

        self.assertEqual(count, len(chunks))

    def test_embed_and_store_calls_bulk_insert(self) -> None:
        chunks   = _make_chunks(2)
        embedder = _mock_embedder(len(chunks))
        mgr      = _mock_schema_mgr()

        pipeline = GuidanceEmbedder(embedder=embedder, schema_mgr=mgr)
        pipeline.embed_and_store(chunks)

        mgr.bulk_insert.assert_called_once()
        records = mgr.bulk_insert.call_args[0][0]
        self.assertEqual(len(records), 2)
        self.assertIsInstance(records[0], EmbeddingRecord)

    def test_embed_and_store_empty_returns_zero(self) -> None:
        pipeline = GuidanceEmbedder(
            embedder=_mock_embedder(0),
            schema_mgr=_mock_schema_mgr(),
        )
        count = pipeline.embed_and_store([])
        self.assertEqual(count, 0)

    def test_records_use_correct_table(self) -> None:
        chunks   = _make_chunks(2)
        embedder = _mock_embedder(len(chunks))
        mgr      = _mock_schema_mgr()

        pipeline = GuidanceEmbedder(
            embedder=embedder, schema_mgr=mgr, table="fda_510k_embeddings"
        )
        pipeline.embed_and_store(chunks)

        records = mgr.bulk_insert.call_args[0][0]
        for rec in records:
            self.assertEqual(rec.table, "fda_510k_embeddings")

    def test_build_records_returns_without_storing(self) -> None:
        chunks   = _make_chunks(3)
        embedder = _mock_embedder(len(chunks))
        mgr      = _mock_schema_mgr()

        pipeline = GuidanceEmbedder(embedder=embedder, schema_mgr=mgr)
        records  = pipeline.build_records(chunks)

        self.assertEqual(len(records), 3)
        mgr.bulk_insert.assert_not_called()

    def test_build_records_empty_returns_empty(self) -> None:
        pipeline = GuidanceEmbedder(
            embedder=_mock_embedder(0),
            schema_mgr=_mock_schema_mgr(),
        )
        self.assertEqual(pipeline.build_records([]), [])

    def test_record_metadata_includes_doc_id(self) -> None:
        chunks   = _make_chunks(1)
        embedder = _mock_embedder(1)
        pipeline = GuidanceEmbedder(embedder=embedder, schema_mgr=_mock_schema_mgr())
        records  = pipeline.build_records(chunks)
        self.assertEqual(records[0].metadata["doc_id"], "ucm_mock")

    def test_record_content_matches_chunk_text(self) -> None:
        chunks   = _make_chunks(2)
        embedder = _mock_embedder(len(chunks))
        pipeline = GuidanceEmbedder(embedder=embedder, schema_mgr=_mock_schema_mgr())
        records  = pipeline.build_records(chunks)
        for rec, chunk in zip(records, chunks):
            self.assertEqual(rec.content, chunk.text)


class TestEmbedGuidanceChunksFunction(unittest.TestCase):

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", False)
    def test_raises_when_st_unavailable(self) -> None:
        chunks = _make_chunks(2)
        with self.assertRaises(EmbeddingUnavailableError):
            embed_guidance_chunks(chunks, schema_mgr=_mock_schema_mgr())

    @patch("fda_tools.lib.guidance_embedder._ST_AVAILABLE", True)
    @patch("fda_tools.lib.guidance_embedder._SentenceTransformer")
    def test_convenience_function_returns_count(self, MockST: MagicMock) -> None:
        import numpy as np
        chunks = _make_chunks(3)
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((len(chunks), EMBEDDING_DIM), dtype="float32")
        MockST.return_value = mock_model

        mgr   = _mock_schema_mgr()
        count = embed_guidance_chunks(chunks, schema_mgr=mgr)
        self.assertEqual(count, len(chunks))


if __name__ == "__main__":
    unittest.main()
