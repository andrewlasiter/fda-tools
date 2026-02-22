"""
FDA-234  [GD-004] Guidance Document Clustering
================================================
Hierarchical clustering of FDA guidance document embeddings using
scipy Ward linkage.  Exposes cluster labels and dendrogram coordinates
for frontend D3.js rendering.

Algorithm
---------
1. Fetch all ``guidance_chunks`` embeddings from pgvector
2. Average per-document embeddings → one 384-d vector per document
3. Compute cosine distance matrix
4. Ward linkage agglomerative clustering
5. Elbow method (within-cluster sum of squares) to pick optimal k ∈ [2, 20]
6. Return cluster labels + dendrogram icoord/dcoord/labels (scipy format)

Output JSON
-----------
{
  "k":           8,
  "n_docs":      45,
  "generated_at": "...",
  "cache_hash":  "abc123",
  "clusters": [
    {
      "cluster_id": 0,
      "label":      "Biocompatibility & Materials Testing",
      "doc_count":  6,
      "docs": [{"doc_id": "...", "doc_title": "...", "doc_url": "..."}]
    }
  ],
  "dendrogram": {
    "icoord": [[...], ...],
    "dcoord": [[...], ...],
    "labels": ["Doc title 1", ...]
  }
}

Caching
-------
Results are cached to ``<cache_dir>/guidance_clusters_{hash}.json`` where
*hash* is the SHA-256 of all ``guidance_chunks`` row IDs + modified_at
timestamps.  Re-clusters only when the guidance index changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Optional dependencies ─────────────────────────────────────────────────────

try:
    import numpy as _np_module
    _NP_AVAILABLE = True
except ImportError:
    _np_module = None  # type: ignore[assignment]
    _NP_AVAILABLE = False

try:
    from scipy.cluster.hierarchy import (  # type: ignore[import]
        linkage as _linkage,
        fcluster as _fcluster,
        dendrogram as _dendrogram,
    )
    from scipy.spatial.distance import pdist as _pdist  # type: ignore[import]
    _SCIPY_AVAILABLE = True
except ImportError:
    _linkage = _fcluster = _dendrogram = _pdist = None  # type: ignore[assignment]
    _SCIPY_AVAILABLE = False

try:
    import psycopg2 as _psycopg2_module  # type: ignore[import]
    _PG_AVAILABLE = True
except ImportError:
    _psycopg2_module = None  # type: ignore[assignment]
    _PG_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_MIN_K = 2
DEFAULT_MAX_K = 20
CACHE_TTL_HOURS = 12


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ClusterDoc:
    doc_id:    str
    doc_title: str
    doc_url:   str


@dataclass
class Cluster:
    cluster_id: int
    label:      str
    doc_count:  int
    docs:       List[ClusterDoc] = field(default_factory=list)


@dataclass
class DendrogramData:
    icoord: List[List[float]]
    dcoord: List[List[float]]
    labels: List[str]


@dataclass
class ClusterResult:
    k:            int
    n_docs:       int
    generated_at: str
    cache_hash:   str
    clusters:     List[Cluster]
    dendrogram:   DendrogramData


# ── Database helpers ──────────────────────────────────────────────────────────

def _fetch_doc_embeddings(
    db_url: str,
) -> Tuple[List[Dict], str]:
    """
    Fetch per-document average embeddings from guidance_chunks.

    Returns (docs, index_hash) where docs is a list of::

        {"doc_id": str, "doc_title": str, "doc_url": str, "embedding": list[float]}

    and index_hash is a SHA-256 fingerprint of the current index state.
    """
    if not _PG_AVAILABLE or _psycopg2_module is None:
        raise ImportError("psycopg2 is required for clustering")

    conn = _psycopg2_module.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    doc_id,
                    MAX(doc_title) AS doc_title,
                    MAX(doc_url)   AS doc_url,
                    AVG(embedding::float[]) AS avg_embedding,
                    string_agg(id::text, ',' ORDER BY id) AS id_list
                FROM guidance_chunks
                WHERE embedding IS NOT NULL
                GROUP BY doc_id
                ORDER BY doc_id
            """)
            rows = cur.fetchall()
    finally:
        conn.close()

    docs = []
    hash_input = ""
    for row in rows:
        doc_id, doc_title, doc_url, avg_emb, id_list = row
        docs.append({
            "doc_id":    doc_id,
            "doc_title": doc_title or doc_id,
            "doc_url":   doc_url or "",
            "embedding": avg_emb,
        })
        hash_input += id_list

    index_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    return docs, index_hash


# ── Clustering ────────────────────────────────────────────────────────────────

def _elbow_k(Z, min_k: int, max_k: int, n_docs: int) -> int:
    """
    Pick optimal k via the elbow in within-cluster sum-of-squares.

    The last column of the linkage matrix Z contains the distance at
    each merge step.  We look for the largest acceleration in the
    merge distance sequence (second derivative maximum).
    """
    if n_docs <= min_k:
        return n_docs
    if n_docs <= 3:
        return min(2, n_docs)

    max_k = min(max_k, n_docs - 1)
    # Merge distances in reverse (largest first = top of dendrogram)
    last = Z[:, 2][::-1]
    n = min(max_k - min_k + 1, len(last) - 1)
    if n < 1:
        return min_k

    accel = [last[i - 1] - 2 * last[i] + last[i + 1] for i in range(1, n)]
    if not accel:
        return min_k

    k = accel.index(max(accel)) + 2   # +2: index offset + 1 for cluster count
    return max(min_k, min(k, max_k))


def _auto_label(cluster_idx: int, docs: List[ClusterDoc]) -> str:
    """
    Heuristic cluster label from document titles.

    Finds the most common non-stop-word bigram across titles in the cluster.
    Falls back to ``Cluster {n}`` for small or homogeneous clusters.
    """
    STOP = {
        "guidance", "for", "the", "of", "on", "and", "to", "in",
        "a", "an", "with", "document", "fda", "device", "devices",
    }
    from collections import Counter
    bigrams: Counter = Counter()
    for doc in docs:
        words = [w.lower().strip("():,") for w in doc.doc_title.split()]
        words = [w for w in words if w and w not in STOP]
        for i in range(len(words) - 1):
            bigrams[(words[i], words[i + 1])] += 1

    if not bigrams:
        return f"Cluster {cluster_idx + 1}"

    top = bigrams.most_common(1)[0][0]
    return " ".join(w.title() for w in top)


def cluster_guidance(
    db_url:   Optional[str] = None,
    min_k:    int = DEFAULT_MIN_K,
    max_k:    int = DEFAULT_MAX_K,
    cache_dir: Optional[Path] = None,
    force:    bool = False,
) -> ClusterResult:
    """
    Run Ward linkage clustering on guidance document embeddings.

    Parameters
    ----------
    db_url    : PostgreSQL DSN (falls back to DATABASE_URL env var)
    min_k     : minimum cluster count
    max_k     : maximum cluster count
    cache_dir : directory for JSON result cache
    force     : bypass cache and always recompute

    Returns
    -------
    :class:`ClusterResult`
    """
    if not _SCIPY_AVAILABLE:
        raise ImportError(
            "scipy is required for clustering. "
            "Run: pip install scipy numpy"
        )
    if not _NP_AVAILABLE or _np_module is None:
        raise ImportError("numpy is required. Run: pip install numpy")

    db_url = db_url or os.getenv("DATABASE_URL")
    if not db_url:
        raise EnvironmentError("DATABASE_URL not set")

    if cache_dir is None:
        cache_dir = Path(os.getenv("FDA_DATA_DIR", Path.home() / ".fda-data")) / "cluster_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Fetch embeddings + compute index hash
    logger.info("Fetching guidance document embeddings…")
    raw_docs, index_hash = _fetch_doc_embeddings(db_url)
    n_docs = len(raw_docs)
    logger.info("Found %d documents with embeddings", n_docs)

    if n_docs < 2:
        raise ValueError(f"Need at least 2 documents to cluster (found {n_docs})")

    # Cache check
    cache_file = cache_dir / f"guidance_clusters_{index_hash}.json"
    if not force and cache_file.exists():
        age_h = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_h < CACHE_TTL_HOURS:
            logger.info("Cache hit: %s (%.1fh old)", cache_file.name, age_h)
            data = json.loads(cache_file.read_text())
            return _deserialize(data)

    # Build embedding matrix
    np = _np_module
    mat = np.array([d["embedding"] for d in raw_docs], dtype=np.float32)

    # Normalise rows → cosine distance via euclidean on unit vectors
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms

    # Ward linkage on cosine distance
    logger.info("Computing Ward linkage (n=%d)…", n_docs)
    dist_vec = _pdist(mat, metric="cosine")  # type: ignore[operator]
    Z = _linkage(dist_vec, method="ward")    # type: ignore[operator]

    # Pick k
    k = _elbow_k(Z, min_k, min(max_k, n_docs - 1), n_docs)
    logger.info("Optimal k = %d", k)

    # Assign cluster labels (scipy clusters are 1-indexed)
    labels_arr = _fcluster(Z, k, criterion="maxclust")  # type: ignore[operator]

    # Build cluster objects
    cluster_map: Dict[int, List[int]] = {}
    for i, cid in enumerate(labels_arr):
        cluster_map.setdefault(int(cid), []).append(i)

    clusters: List[Cluster] = []
    for cid, indices in sorted(cluster_map.items()):
        docs_in = [
            ClusterDoc(
                doc_id    = raw_docs[i]["doc_id"],
                doc_title = raw_docs[i]["doc_title"],
                doc_url   = raw_docs[i]["doc_url"],
            )
            for i in indices
        ]
        clusters.append(Cluster(
            cluster_id = cid - 1,   # 0-indexed for frontend
            label      = _auto_label(cid - 1, docs_in),
            doc_count  = len(docs_in),
            docs       = docs_in,
        ))

    # Dendrogram coordinates (for D3.js)
    doc_titles = [d["doc_title"] for d in raw_docs]
    ddata = _dendrogram(Z, labels=doc_titles, no_plot=True)  # type: ignore[operator]

    dendro = DendrogramData(
        icoord = ddata["icoord"],
        dcoord = ddata["dcoord"],
        labels = list(ddata["ivl"]),
    )

    result = ClusterResult(
        k            = k,
        n_docs       = n_docs,
        generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        cache_hash   = index_hash,
        clusters     = clusters,
        dendrogram   = dendro,
    )

    # Write cache
    cache_file.write_text(json.dumps(_serialize(result)))
    logger.info("Clustering complete. %d clusters written to %s", k, cache_file.name)

    # Purge old cache files for this dataset (keep current only)
    for old in cache_dir.glob("guidance_clusters_*.json"):
        if old != cache_file:
            old.unlink(missing_ok=True)

    return result


# ── Serialisation ─────────────────────────────────────────────────────────────

def _serialize(r: ClusterResult) -> dict:
    return {
        "k":            r.k,
        "n_docs":       r.n_docs,
        "generated_at": r.generated_at,
        "cache_hash":   r.cache_hash,
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "label":      c.label,
                "doc_count":  c.doc_count,
                "docs": [
                    {"doc_id": d.doc_id, "doc_title": d.doc_title, "doc_url": d.doc_url}
                    for d in c.docs
                ],
            }
            for c in r.clusters
        ],
        "dendrogram": {
            "icoord": r.dendrogram.icoord,
            "dcoord": r.dendrogram.dcoord,
            "labels": r.dendrogram.labels,
        },
    }


def _deserialize(data: dict) -> ClusterResult:
    return ClusterResult(
        k            = data["k"],
        n_docs       = data["n_docs"],
        generated_at = data["generated_at"],
        cache_hash   = data["cache_hash"],
        clusters = [
            Cluster(
                cluster_id = c["cluster_id"],
                label      = c["label"],
                doc_count  = c["doc_count"],
                docs = [ClusterDoc(**d) for d in c["docs"]],
            )
            for c in data["clusters"]
        ],
        dendrogram = DendrogramData(**data["dendrogram"]),
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(description="Guidance Document Clustering (FDA-234)")
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--min-k", type=int, default=DEFAULT_MIN_K)
    parser.add_argument("--max-k", type=int, default=DEFAULT_MAX_K)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="Bypass cache")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    result = cluster_guidance(
        db_url    = args.db_url,
        min_k     = args.min_k,
        max_k     = args.max_k,
        force     = args.force,
    )

    output_str = json.dumps(_serialize(result), indent=2)
    if args.output:
        args.output.write_text(output_str)
        logger.info("Written to %s", args.output)
    else:
        print(output_str)


if __name__ == "__main__":
    _cli()
