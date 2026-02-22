"""
FDA-224  [GD-002] Sentence-Transformer Embedding Pipeline
==========================================================
Generates 384-dimensional embeddings for ``GuidanceChunk`` objects using the
*all-MiniLM-L6-v2* sentence-transformer model and stores them in Supabase via
:class:`~fda_tools.lib.pgvector_schema.SchemaManager`.

Optional dependency
-------------------
``sentence_transformers`` — if not installed, the module still imports cleanly.
All embedding calls raise ``EmbeddingUnavailableError`` with an installation
hint.  This preserves the air-gapped / on-prem compatibility guarantee
established in :mod:`~fda_tools.lib.supabase_client`.

Design
------
``EmbeddingUnavailableError`` — domain exception when the SDK is missing.
``SentenceEmbedder``          — thin facade around the sentence-transformers
                                 ``SentenceTransformer`` class with lazy model
                                 loading and batch processing.
``GuidanceEmbedder``          — orchestrates: chunks → embeddings →
                                 ``EmbeddingRecord`` list → ``SchemaManager.bulk_insert``.
``embed_guidance_chunks``     — convenience one-call function.

Model
-----
Default: ``"sentence-transformers/all-MiniLM-L6-v2"``
Dimension: 384 (matches ``pgvector_schema.EMBEDDING_DIM``)
Normalisation: L2-normalised by default (``normalize_embeddings=True``)

Usage
-----
    from fda_tools.lib.guidance_embedder import embed_guidance_chunks
    from fda_tools.lib.supabase_client import get_client
    from fda_tools.lib.pgvector_schema import SchemaManager

    schema_mgr = SchemaManager(get_client())
    inserted   = embed_guidance_chunks(chunks, schema_mgr)
    # inserted: int — number of rows written to Supabase
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from fda_tools.lib.pgvector_schema import EMBEDDING_DIM, EmbeddingRecord

logger = logging.getLogger(__name__)

# ── Optional sentence-transformers import ─────────────────────────────────────

try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer  # type: ignore[import]
    _ST_AVAILABLE = True
except ImportError:
    _SentenceTransformer = None  # type: ignore[assignment,misc]
    _ST_AVAILABLE = False

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH = 64


# ── Exception ─────────────────────────────────────────────────────────────────

class EmbeddingUnavailableError(Exception):
    """
    Raised when sentence-transformers is not installed.

    Provides an installation hint in the message.
    """


# ── SentenceEmbedder ──────────────────────────────────────────────────────────

class SentenceEmbedder:
    """
    Thin facade around ``SentenceTransformer`` with lazy model loading.

    Args:
        model_name: HuggingFace model identifier (default: ``DEFAULT_MODEL``).
        batch_size: Number of texts per encoding batch (default: ``DEFAULT_BATCH``).
        device:     Torch device string (``"cpu"``, ``"cuda"``, etc.).
                    ``None`` lets sentence-transformers auto-detect.
    """

    def __init__(
        self,
        model_name: str            = DEFAULT_MODEL,
        batch_size: int            = DEFAULT_BATCH,
        device:     Optional[str]  = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.device     = device
        self._model: Any = None

    # ── Lazy model load ───────────────────────────────────────────────────────

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        if not _ST_AVAILABLE:
            raise EmbeddingUnavailableError(
                "sentence-transformers is not installed. "
                "Run `pip install sentence-transformers` to enable embedding generation."
            )
        assert _SentenceTransformer is not None
        kwargs: dict[str, Any] = {}
        if self.device is not None:
            kwargs["device"] = self.device
        self._model = _SentenceTransformer(self.model_name, **kwargs)
        logger.debug("SentenceEmbedder: loaded model '%s'", self.model_name)
        return self._model

    # ── Public API ────────────────────────────────────────────────────────────

    def embed(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        Encode a list of text strings into embedding vectors.

        Args:
            texts:     List of strings to embed.
            normalize: Whether to L2-normalise the output vectors (default True).

        Returns:
            List of embedding vectors, each a list of ``EMBEDDING_DIM`` floats.

        Raises:
            EmbeddingUnavailableError: If sentence-transformers is not installed.
            ValueError: If the model output dimension != ``EMBEDDING_DIM``.
        """
        if not texts:
            return []

        model = self._ensure_model()
        vectors = model.encode(
            texts,
            batch_size          = self.batch_size,
            normalize_embeddings = normalize,
            show_progress_bar   = False,
        )

        result: List[List[float]] = []
        for vec in vectors:
            floats = [float(x) for x in vec]
            if len(floats) != EMBEDDING_DIM:
                raise ValueError(
                    f"Model '{self.model_name}' produced {len(floats)}-dim embedding; "
                    f"expected {EMBEDDING_DIM}. Check EMBEDDING_DIM constant."
                )
            result.append(floats)

        return result

    def is_available(self) -> bool:
        """Return True if sentence-transformers is installed."""
        return _ST_AVAILABLE

    def is_loaded(self) -> bool:
        """Return True if the model has been loaded into memory."""
        return self._model is not None


# ── GuidanceEmbedder ──────────────────────────────────────────────────────────

class GuidanceEmbedder:
    """
    End-to-end pipeline: ``GuidanceChunk`` list → embeddings → Supabase.

    Args:
        embedder:    A ``SentenceEmbedder`` instance.
        schema_mgr:  A ``SchemaManager`` connected to Supabase.
        table:       Target Supabase table (default: ``"guidance_embeddings"``).
    """

    def __init__(
        self,
        embedder:   SentenceEmbedder,
        schema_mgr: Any,
        table:      str = "guidance_embeddings",
    ) -> None:
        self.embedder   = embedder
        self.schema_mgr = schema_mgr
        self.table      = table

    def embed_and_store(self, chunks: List[Any]) -> int:
        """
        Embed all *chunks* and write them to Supabase.

        Args:
            chunks: List of ``GuidanceChunk`` objects (from ``guidance_indexer``).

        Returns:
            Number of rows successfully written.

        Raises:
            EmbeddingUnavailableError: If sentence-transformers is not installed.
        """
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        vectors = self.embedder.embed(texts)

        records: List[EmbeddingRecord] = []
        for chunk, vector in zip(chunks, vectors):
            records.append(EmbeddingRecord(
                table    = self.table,
                content  = chunk.text,
                embedding = vector,
                metadata = chunk.to_embedding_metadata(),
            ))

        self.schema_mgr.bulk_insert(records)
        logger.info(
            "GuidanceEmbedder: stored %d embeddings → table '%s'",
            len(records), self.table,
        )
        return len(records)

    def build_records(self, chunks: List[Any]) -> List[EmbeddingRecord]:
        """
        Embed chunks and return ``EmbeddingRecord`` objects without storing.

        Useful for inspection, dry-runs, or custom storage logic.
        """
        if not chunks:
            return []
        texts   = [c.text for c in chunks]
        vectors = self.embedder.embed(texts)
        return [
            EmbeddingRecord(
                table     = self.table,
                content   = chunk.text,
                embedding = vector,
                metadata  = chunk.to_embedding_metadata(),
            )
            for chunk, vector in zip(chunks, vectors)
        ]


# ── Convenience function ──────────────────────────────────────────────────────

def embed_guidance_chunks(
    chunks:     List[Any],
    schema_mgr: Any,
    model_name: str           = DEFAULT_MODEL,
    batch_size: int           = DEFAULT_BATCH,
    device:     Optional[str] = None,
    table:      str           = "guidance_embeddings",
) -> int:
    """
    One-call convenience function: embed chunks and store in Supabase.

    Args:
        chunks:     List of ``GuidanceChunk`` from ``guidance_indexer``.
        schema_mgr: Connected ``SchemaManager`` instance.
        model_name: HuggingFace model (default: all-MiniLM-L6-v2).
        batch_size: Encoding batch size.
        device:     Torch device string, or None for auto.
        table:      Target Supabase table name.

    Returns:
        Number of rows written.

    Raises:
        EmbeddingUnavailableError: If sentence-transformers is not installed.
    """
    embedder = SentenceEmbedder(
        model_name = model_name,
        batch_size = batch_size,
        device     = device,
    )
    pipeline = GuidanceEmbedder(
        embedder   = embedder,
        schema_mgr = schema_mgr,
        table      = table,
    )
    return pipeline.embed_and_store(chunks)
