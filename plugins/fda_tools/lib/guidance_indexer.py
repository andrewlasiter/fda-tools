"""
FDA-223  [GD-001] Guidance PDF Extractor and Text Chunker
==========================================================
Extracts text from FDA guidance documents (PDF or plain text), chunks the
content into overlapping segments suitable for sentence-transformer embedding,
and returns structured ``GuidanceChunk`` objects ready for the embedding
pipeline (see :mod:`~fda_tools.lib.guidance_embedder`).

Optional dependencies
---------------------
``pdfplumber`` — preferred PDF extraction (tables + text).  Falls back to
``pypdf`` if available, then to raw text-file reading.  The module always
imports cleanly even if neither PDF library is installed.

Design
------
``GuidanceChunk``      — immutable value object for one text segment.
``PDFExtractor``       — extracts raw text from a PDF file path.
``TextChunker``        — splits text into overlapping fixed-size windows.
``GuidanceIndexer``    — orchestrates: extract → clean → chunk → tag.
``index_guidance_pdf`` — convenience one-call function.

Chunking parameters
-------------------
``CHUNK_SIZE``    = 512  tokens (approximate — uses character heuristic:
                          1 token ≈ 4 characters for English regulatory text)
``CHUNK_OVERLAP`` = 50   tokens (prevents boundary information loss)

Usage
-----
    from fda_tools.lib.guidance_indexer import index_guidance_pdf

    chunks = index_guidance_pdf(
        path="/data/guidance/ucm123456.pdf",
        doc_id="ucm123456",
        title="Design Controls Guidance",
    )
    # chunks: List[GuidanceChunk]
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Optional PDF library imports ──────────────────────────────────────────────

try:
    import pdfplumber as _pdfplumber  # type: ignore[import]
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _pdfplumber = None  # type: ignore[assignment]
    _PDFPLUMBER_AVAILABLE = False

try:
    from pypdf import PdfReader as _PdfReader  # type: ignore[import]
    _PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader as _PdfReader  # type: ignore[import,no-redef]
        _PYPDF_AVAILABLE = True
    except ImportError:
        _PdfReader = None  # type: ignore[assignment,misc]
        _PYPDF_AVAILABLE = False


# ── Constants ─────────────────────────────────────────────────────────────────

CHUNK_SIZE:    int = 512   # approximate tokens (chars / 4)
CHUNK_OVERLAP: int = 50    # approximate tokens
_CHARS_PER_TOKEN: int = 4  # English regulatory text heuristic


def _tok_to_char(tokens: int) -> int:
    return tokens * _CHARS_PER_TOKEN


# ── GuidanceChunk ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GuidanceChunk:
    """
    A single text segment from a guidance document, ready for embedding.

    Attributes:
        doc_id:     Unique identifier for the source document (e.g. ``"ucm123456"``).
        chunk_index: Zero-based position of this chunk within the document.
        text:       The extracted text content of this chunk.
        title:      Human-readable document title.
        section:    Section heading extracted from the surrounding text, if any.
        page_num:   Source page number (1-based), or 0 if unknown.
        char_start: Character offset of this chunk within the full extracted text.
        metadata:   Additional key/value pairs for filtering (e.g. ``{"year": 2023}``).
    """
    doc_id:      str
    chunk_index: int
    text:        str
    title:       str                  = ""
    section:     str                  = ""
    page_num:    int                  = 0
    char_start:  int                  = 0
    metadata:    Dict[str, Any]       = field(default_factory=dict)

    def to_embedding_metadata(self) -> Dict[str, Any]:
        """Return a flat metadata dict for storage in the ``metadata`` JSONB column."""
        return {
            "doc_id":      self.doc_id,
            "chunk_index": self.chunk_index,
            "title":       self.title,
            "section":     self.section,
            "page_num":    self.page_num,
            "char_start":  self.char_start,
            **self.metadata,
        }


# ── PDFExtractor ──────────────────────────────────────────────────────────────

class PDFExtractor:
    """
    Extract plain text from a PDF file, using the best available library.

    Priority: pdfplumber → pypdf → plain-text fallback (raises if PDF).

    Args:
        path: Path to the PDF (or plain-text) file.
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def extract(self) -> str:
        """
        Return the full extracted text of the document.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is a PDF but no PDF library is available.
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Guidance file not found: {self.path}")

        suffix = self.path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf()
        # Plain text, HTML, or other readable formats
        return self._extract_text()

    def _extract_pdf(self) -> str:
        if _PDFPLUMBER_AVAILABLE:
            return self._extract_pdfplumber()
        if _PYPDF_AVAILABLE:
            return self._extract_pypdf()
        raise ValueError(
            f"Cannot extract PDF '{self.path}': neither pdfplumber nor pypdf is installed. "
            "Run `pip install pdfplumber` or `pip install pypdf`."
        )

    def _extract_pdfplumber(self) -> str:
        assert _pdfplumber is not None
        pages: List[str] = []
        with _pdfplumber.open(str(self.path)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
        return "\n\n".join(pages)

    def _extract_pypdf(self) -> str:
        assert _PdfReader is not None
        reader = _PdfReader(str(self.path))
        pages: List[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return "\n\n".join(pages)

    def _extract_text(self) -> str:
        return self.path.read_text(encoding="utf-8", errors="replace")


# ── TextChunker ───────────────────────────────────────────────────────────────

class TextChunker:
    """
    Split a long text string into overlapping fixed-size character windows.

    Respects sentence and paragraph boundaries where possible.

    Args:
        chunk_size:    Approximate chunk size in tokens (default: ``CHUNK_SIZE``).
        chunk_overlap: Overlap between consecutive chunks in tokens (default: ``CHUNK_OVERLAP``).
    """

    def __init__(
        self,
        chunk_size:    int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self.chunk_chars   = _tok_to_char(chunk_size)
        self.overlap_chars = _tok_to_char(chunk_overlap)

    def split(self, text: str) -> List[tuple[str, int]]:
        """
        Split *text* into overlapping chunks.

        Returns:
            List of ``(chunk_text, char_start_offset)`` tuples.
        """
        text = text.strip()
        if not text:
            return []

        chunks: List[tuple[str, int]] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_chars, text_len)

            # Prefer to break at a sentence boundary (. ! ?) or paragraph (\n\n)
            if end < text_len:
                end = self._find_break(text, start, end)

            chunk = text[start:end].strip()
            if chunk:
                chunks.append((chunk, start))

            next_start = end - self.overlap_chars
            # Guard against infinite loop on very short text
            if next_start <= start:
                next_start = end
            start = next_start

        return chunks

    @staticmethod
    def _find_break(text: str, start: int, preferred_end: int) -> int:
        """
        Search backwards from *preferred_end* for a natural break point.

        Looks for paragraph breaks (\\n\\n), then sentence endings (. ! ?),
        within the last 20% of the window.
        """
        search_start = max(start, preferred_end - preferred_end // 5)

        # Paragraph break first
        para_idx = text.rfind("\n\n", search_start, preferred_end)
        if para_idx != -1:
            return para_idx + 2

        # Sentence ending
        for char in (".", "!", "?"):
            idx = text.rfind(char, search_start, preferred_end)
            if idx != -1:
                return idx + 1

        return preferred_end


# ── GuidanceIndexer ───────────────────────────────────────────────────────────

# Heading patterns: "Section 4.2", "IV. Background", "BACKGROUND", "4. Scope"
_HEADING_RE = re.compile(
    r"^(?:(?:Section\s+)?\d+(?:\.\d+)*\.?\s+|[IVXivx]+\.\s+|[A-Z][A-Z\s]{3,}:?\s*$)",
    re.MULTILINE,
)


def _detect_section(text: str, window: int = 300) -> str:
    """Return the last heading found within the first *window* characters of *text*."""
    snippet = text[:window]
    matches = list(_HEADING_RE.finditer(snippet))
    if matches:
        return matches[-1].group(0).strip().rstrip(":")
    return ""


def _clean_text(text: str) -> str:
    """Remove common PDF artefacts: page numbers, running headers, excess whitespace."""
    # Remove standalone page numbers
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
    # Collapse 3+ consecutive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove form-feed characters
    text = text.replace("\x0c", "\n")
    return text.strip()


class GuidanceIndexer:
    """
    Orchestrate guidance document extraction, cleaning, and chunking.

    Args:
        chunk_size:    Approximate chunk size in tokens.
        chunk_overlap: Overlap between consecutive chunks in tokens.
    """

    def __init__(
        self,
        chunk_size:    int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> None:
        self._chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def index_file(
        self,
        path:     str,
        doc_id:   str,
        title:    str                    = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[GuidanceChunk]:
        """
        Extract, clean, and chunk a guidance document.

        Args:
            path:     File system path to the PDF or text file.
            doc_id:   Stable identifier for this document (e.g. ``"ucm123456"``).
            title:    Human-readable document title.
            metadata: Extra key/value pairs attached to every chunk.

        Returns:
            Ordered list of ``GuidanceChunk`` objects.
        """
        extractor = PDFExtractor(path)
        raw_text  = extractor.extract()
        clean     = _clean_text(raw_text)

        if not title:
            title = Path(path).stem

        raw_chunks = self._chunker.split(clean)
        chunks: List[GuidanceChunk] = []

        for idx, (text, char_start) in enumerate(raw_chunks):
            section = _detect_section(text)
            chunks.append(GuidanceChunk(
                doc_id      = doc_id,
                chunk_index = idx,
                text        = text,
                title       = title,
                section     = section,
                page_num    = 0,          # page tracking requires pdfplumber; left for future
                char_start  = char_start,
                metadata    = dict(metadata or {}),
            ))

        logger.info(
            "GuidanceIndexer: '%s' → %d chunks (%.1f k chars)",
            doc_id, len(chunks), len(clean) / 1000,
        )
        return chunks

    def index_text(
        self,
        text:     str,
        doc_id:   str,
        title:    str                    = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[GuidanceChunk]:
        """
        Chunk a pre-extracted text string (no file I/O).

        Useful for testing or when text has already been extracted externally.
        """
        clean      = _clean_text(text)
        raw_chunks = self._chunker.split(clean)
        chunks: List[GuidanceChunk] = []

        for idx, (chunk_text, char_start) in enumerate(raw_chunks):
            section = _detect_section(chunk_text)
            chunks.append(GuidanceChunk(
                doc_id      = doc_id,
                chunk_index = idx,
                text        = chunk_text,
                title       = title,
                section     = section,
                page_num    = 0,
                char_start  = char_start,
                metadata    = dict(metadata or {}),
            ))
        return chunks


# ── Convenience function ──────────────────────────────────────────────────────

def index_guidance_pdf(
    path:     str,
    doc_id:   str,
    title:    str                    = "",
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size:    int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[GuidanceChunk]:
    """
    One-call convenience wrapper around ``GuidanceIndexer.index_file``.

    Args:
        path:          Path to the guidance PDF or text file.
        doc_id:        Unique document identifier.
        title:         Human-readable document title.
        metadata:      Extra metadata attached to every chunk.
        chunk_size:    Approximate chunk size in tokens.
        chunk_overlap: Overlap in tokens.

    Returns:
        List of ``GuidanceChunk`` objects ready for the embedding pipeline.
    """
    indexer = GuidanceIndexer(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return indexer.index_file(path=path, doc_id=doc_id, title=title, metadata=metadata)
