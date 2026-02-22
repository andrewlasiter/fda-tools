"""
FDA-233  [GD-003] Cosine Similarity Search API
================================================
Public search API for regulatory guidance documents stored in the
``guidance_embeddings`` Supabase table.  Takes a plain-English query,
generates a sentence-transformer embedding, executes a pgvector cosine
similarity search, and returns ranked ``GuidanceSearchResult`` objects.

Design
------
``GuidanceSearchResult``  — immutable value object for one search hit.
``GuidanceSearchClient``  — facade that wires together:
                             1. ``SentenceEmbedder`` (FDA-224)
                             2. ``SupabaseClient.vector_search`` (FDA-219)
                             3. Result parsing + ranking
``search_guidance``       — convenience one-call function.

Usage
-----
    from fda_tools.lib.guidance_search import GuidanceSearchClient
    from fda_tools.lib.supabase_client import get_client
    from fda_tools.lib.guidance_embedder import SentenceEmbedder

    client  = GuidanceSearchClient(
        supabase_client = get_client(),
        embedder        = SentenceEmbedder(),
    )
    results = client.search("risk management ISO 14971 medical device")
    for r in results:
        print(r.similarity, r.content[:80])

Filtering
---------
Results can be filtered post-search by metadata keys via ``filter_by``:

    results = client.search(
        "software validation",
        filter_by={"doc_id": "ucm123456"},
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fda_tools.lib.guidance_embedder import SentenceEmbedder

logger = logging.getLogger(__name__)

# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GuidanceSearchResult:
    """
    A single ranked result from a cosine similarity search.

    Attributes:
        content:    The matched text chunk.
        similarity: Cosine similarity score (0–1); higher is more relevant.
        doc_id:     Source document identifier.
        title:      Human-readable document title.
        section:    Section heading of the matched chunk, if known.
        chunk_index: Position of this chunk within the source document.
        metadata:   Full JSONB metadata dict from the Supabase row.
        row_id:     Supabase row surrogate PK (``BIGINT``), or ``None``.
    """
    content:     str
    similarity:  float
    doc_id:      str                = ""
    title:       str                = ""
    section:     str                = ""
    chunk_index: int                = 0
    metadata:    Dict[str, Any]     = field(default_factory=dict)
    row_id:      Optional[int]      = None

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of this result."""
        return {
            "row_id":      self.row_id,
            "doc_id":      self.doc_id,
            "title":       self.title,
            "section":     self.section,
            "chunk_index": self.chunk_index,
            "similarity":  round(self.similarity, 4),
            "content":     self.content,
            "metadata":    self.metadata,
        }


def _parse_result(row: Dict[str, Any]) -> GuidanceSearchResult:
    """Parse a raw Supabase row dict into a ``GuidanceSearchResult``."""
    meta = row.get("metadata") or {}
    return GuidanceSearchResult(
        content     = row.get("content", ""),
        similarity  = float(row.get("similarity", 0.0)),
        doc_id      = str(meta.get("doc_id", "")),
        title       = str(meta.get("title", "")),
        section     = str(meta.get("section", "")),
        chunk_index = int(meta.get("chunk_index", 0)),
        metadata    = meta,
        row_id      = row.get("id"),
    )


# ── Client ─────────────────────────────────────────────────────────────────────

class GuidanceSearchClient:
    """
    Semantic search client for the ``guidance_embeddings`` table.

    Args:
        supabase_client: A connected :class:`~fda_tools.lib.supabase_client.SupabaseClient`.
        embedder:        A :class:`~fda_tools.lib.guidance_embedder.SentenceEmbedder`
                         instance (default: new instance with default model).
        table:           Supabase table name (default: ``"guidance_embeddings"``).
        default_k:       Default number of results to return.
        default_threshold: Default minimum similarity score.
    """

    def __init__(
        self,
        supabase_client: Any,
        embedder:        Optional[SentenceEmbedder] = None,
        table:           str   = "guidance_embeddings",
        default_k:       int   = 10,
        default_threshold: float = 0.75,
    ) -> None:
        self._client    = supabase_client
        self._embedder  = embedder or SentenceEmbedder()
        self.table      = table
        self.default_k  = default_k
        self.default_threshold = default_threshold

    # ── Core search ──────────────────────────────────────────────────────────

    def search(
        self,
        query:      str,
        k:          Optional[int]   = None,
        threshold:  Optional[float] = None,
        filter_by:  Optional[Dict[str, Any]] = None,
    ) -> List[GuidanceSearchResult]:
        """
        Semantic search for guidance document chunks matching *query*.

        Args:
            query:     Plain-English query string.
            k:         Maximum number of results (defaults to ``default_k``).
            threshold: Minimum cosine similarity (defaults to ``default_threshold``).
            filter_by: Optional dict of metadata key→value pairs to filter
                       results post-search (applied in Python after Supabase returns).

        Returns:
            List of ``GuidanceSearchResult`` sorted by similarity descending.

        Raises:
            fda_tools.lib.guidance_embedder.EmbeddingUnavailableError:
                If sentence-transformers is not installed.
            fda_tools.lib.supabase_client.SupabaseConnectionError:
                If Supabase is not configured or unreachable.
        """
        max_results = k or self.default_k
        min_sim     = threshold if threshold is not None else self.default_threshold

        # 1. Embed the query
        vectors = self._embedder.embed([query])
        query_vector = vectors[0]

        # 2. Vector search in Supabase
        response = self._client.vector_search(
            table            = self.table,
            embedding_column = "embedding",
            query_vector     = query_vector,
            match_threshold  = min_sim,
            match_count      = max_results,
        ).execute()

        rows: List[Dict[str, Any]] = response.data if hasattr(response, "data") else []

        # 3. Parse rows
        results = [_parse_result(row) for row in rows]

        # 4. Post-search metadata filter
        if filter_by:
            results = [
                r for r in results
                if all(r.metadata.get(k) == v for k, v in filter_by.items())
            ]

        # 5. Sort by similarity descending (Supabase already sorts, but ensure stability)
        results.sort(key=lambda r: r.similarity, reverse=True)

        logger.debug(
            "GuidanceSearchClient.search: query=%r → %d results (threshold=%.2f)",
            query[:60], len(results), min_sim,
        )
        return results

    # ── Convenience helpers ───────────────────────────────────────────────────

    def search_by_doc(
        self,
        query:  str,
        doc_id: str,
        k:      int   = 10,
    ) -> List[GuidanceSearchResult]:
        """Search within a single document identified by *doc_id*."""
        return self.search(query, k=k, filter_by={"doc_id": doc_id})

    def top_result(
        self,
        query:     str,
        threshold: float = 0.75,
    ) -> Optional[GuidanceSearchResult]:
        """Return the single best matching chunk, or ``None`` if none meet *threshold*."""
        results = self.search(query, k=1, threshold=threshold)
        return results[0] if results else None

    def explain(
        self,
        query:     str,
        k:         int   = 5,
        threshold: float = 0.5,
    ) -> str:
        """
        Return a human-readable explanation of search results for debugging.

        Args:
            query:     The search query.
            k:         Number of results to include.
            threshold: Minimum similarity.

        Returns:
            Formatted multi-line string.
        """
        results = self.search(query, k=k, threshold=threshold)
        if not results:
            return f"No results found for query: {query!r} (threshold={threshold})"
        lines = [f"Search results for: {query!r}", f"{'─' * 60}"]
        for i, r in enumerate(results, 1):
            lines.append(
                f"{i}. [{r.similarity:.3f}] {r.title or r.doc_id} §{r.section}"
            )
            lines.append(f"   {r.content[:120].strip()}...")
        return "\n".join(lines)


# ── Convenience function ──────────────────────────────────────────────────────

def search_guidance(
    query:           str,
    supabase_client: Any,
    k:               int   = 10,
    threshold:       float = 0.75,
    filter_by:       Optional[Dict[str, Any]] = None,
    embedder:        Optional[SentenceEmbedder] = None,
    table:           str   = "guidance_embeddings",
) -> List[GuidanceSearchResult]:
    """
    One-call convenience function for semantic guidance search.

    Args:
        query:           Plain-English regulatory query.
        supabase_client: Connected SupabaseClient.
        k:               Max results.
        threshold:       Min cosine similarity.
        filter_by:       Metadata filters.
        embedder:        Optional pre-loaded SentenceEmbedder.
        table:           Target Supabase table.

    Returns:
        List of ``GuidanceSearchResult`` sorted by similarity.
    """
    client = GuidanceSearchClient(
        supabase_client   = supabase_client,
        embedder          = embedder,
        table             = table,
        default_k         = k,
        default_threshold = threshold,
    )
    return client.search(query, filter_by=filter_by)
