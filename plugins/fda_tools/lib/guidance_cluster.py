"""
FDA-234  [GD-004] Hierarchical Clustering + Dendrogram for Guidance Embeddings
===============================================================================
Performs Ward-linkage agglomerative clustering on sentence-transformer embeddings
of regulatory guidance document chunks stored in the ``guidance_embeddings`` table.

Background
----------
Ward's minimum-variance criterion merges the pair of clusters that minimises the
total within-cluster sum of squares, producing compact, roughly equal-sized
clusters.  For guidance document embeddings this groups thematically similar
sections (e.g. "biocompatibility testing", "software validation") without
requiring a pre-specified number of clusters.

Design
------
``ClusterNode``      — immutable value object for a single node in the linkage tree.
``DendrogramData``   — serialisable dendrogram ready for D3.js / Tremor visualisation.
``ClusterResult``    — output of a clustering run (labels + dendrogram + metadata).
``GuidanceClusterer``— stateful clusterer; call ``fit(embeddings)`` then inspect results.
``cluster_embeddings``— stateless convenience function for one-call clustering.

Algorithm
---------
1. Compute pairwise cosine distance matrix from L2-normalised embeddings.
2. Apply Ward linkage (scipy ``linkage(Z, method="ward")``) on the distance matrix.
3. Cut the dendrogram at *n_clusters* using ``fcluster`` to obtain flat labels.
4. Build ``DendrogramData`` mirroring scipy's ``dendrogram()`` output structure so the
   D3.js frontend (FDA-247) can render it directly.

Usage
-----
    from fda_tools.lib.guidance_cluster import GuidanceClusterer

    # embeddings: list of 384-dim float lists (one per chunk)
    clusterer = GuidanceClusterer(n_clusters=8)
    result    = clusterer.fit(embeddings)
    print(result.labels)             # [0, 2, 0, 1, 3, …] cluster index per chunk
    print(result.dendrogram.icoord)  # D3-ready coordinates

    # Convenience
    from fda_tools.lib.guidance_cluster import cluster_embeddings
    result = cluster_embeddings(embeddings, n_clusters=6)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ── Optional scipy import ─────────────────────────────────────────────────────

try:
    from scipy.cluster.hierarchy import (  # type: ignore[import]
        dendrogram as _scipy_dendrogram,
        fcluster as _scipy_fcluster,
        linkage as _scipy_linkage,
    )
    from scipy.spatial.distance import pdist as _scipy_pdist  # type: ignore[import]
    _SCIPY_AVAILABLE = True
except ImportError:
    _scipy_linkage      = None  # type: ignore[assignment]
    _scipy_fcluster     = None  # type: ignore[assignment]
    _scipy_dendrogram   = None  # type: ignore[assignment]
    _scipy_pdist        = None  # type: ignore[assignment]
    _SCIPY_AVAILABLE    = False


# ── Exceptions ────────────────────────────────────────────────────────────────

class ClusteringUnavailableError(ImportError):
    """Raised when scipy is not installed and clustering is requested."""


# ── Value objects ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClusterNode:
    """
    A single merge event in the Ward linkage tree.

    Attributes:
        left_id:   Index of the left child cluster (< n_samples = leaf; ≥ n_samples = merge).
        right_id:  Index of the right child cluster.
        distance:  Ward distance at which these clusters were merged.
        count:     Total number of original observations in this merged cluster.
    """
    left_id:  int
    right_id: int
    distance: float
    count:    int


@dataclass(frozen=True)
class DendrogramData:
    """
    Dendrogram coordinates ready for D3.js / Tremor visualisation.

    Mirrors the dict returned by ``scipy.cluster.hierarchy.dendrogram()``.

    Attributes:
        icoord:  List of [x1, x2, x3, x4] for each U-shape (x-axis positions).
        dcoord:  List of [y1, y2, y3, y4] for each U-shape (y-axis = distance).
        ivl:     Leaf labels (strings) in left-to-right order.
        leaves:  Original observation indices in leaf order.
        color_list: Colour string for each link segment.
    """
    icoord:     List[List[float]]
    dcoord:     List[List[float]]
    ivl:        List[str]
    leaves:     List[int]
    color_list: List[str]

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dict suitable for the frontend."""
        return {
            "icoord":     self.icoord,
            "dcoord":     self.dcoord,
            "ivl":        self.ivl,
            "leaves":     self.leaves,
            "color_list": self.color_list,
        }


@dataclass
class ClusterResult:
    """
    Output of a complete clustering run.

    Attributes:
        labels:       Cluster index (0-based) for each input embedding.
        n_clusters:   Number of clusters requested.
        n_samples:    Number of embeddings clustered.
        linkage_matrix: Raw ``(n-1, 4)`` Ward linkage matrix rows (as list of lists).
        dendrogram:   Pre-computed ``DendrogramData`` for visualisation.
        nodes:        Merge tree as ``ClusterNode`` list (one per merge step).
        inertia:      Sum of within-cluster variances (lower = more compact clusters).
    """
    labels:         List[int]
    n_clusters:     int
    n_samples:      int
    linkage_matrix: List[List[float]]  = field(default_factory=list)
    dendrogram:     Optional[DendrogramData] = None
    nodes:          List[ClusterNode]  = field(default_factory=list)
    inertia:        float              = 0.0

    @property
    def cluster_sizes(self) -> Dict[int, int]:
        """Return ``{cluster_id: count}`` for each cluster."""
        sizes: Dict[int, int] = {}
        for lbl in self.labels:
            sizes[lbl] = sizes.get(lbl, 0) + 1
        return sizes

    def as_dict(self) -> Dict[str, Any]:
        return {
            "n_clusters":  self.n_clusters,
            "n_samples":   self.n_samples,
            "inertia":     round(self.inertia, 6),
            "cluster_sizes": self.cluster_sizes,
            "dendrogram":  self.dendrogram.as_dict() if self.dendrogram else None,
        }


# ── Pure-Python fallbacks ─────────────────────────────────────────────────────

def _cosine_distance(u: Sequence[float], v: Sequence[float]) -> float:
    """Cosine distance = 1 − cosine_similarity."""
    dot  = sum(a * b for a, b in zip(u, v))
    nu   = math.sqrt(sum(a * a for a in u))
    nv   = math.sqrt(sum(b * b for b in v))
    if nu == 0 or nv == 0:
        return 1.0
    sim = dot / (nu * nv)
    return 1.0 - max(-1.0, min(1.0, sim))



def _simple_agglomerative(
    embeddings: List[List[float]],
    n_clusters: int,
) -> Tuple[List[int], float]:
    """
    Minimal single-linkage fallback (no scipy).

    Uses single-linkage (nearest-neighbour) rather than Ward because Ward
    requires a distance matrix update formula that is substantially more
    complex to implement correctly without scipy.  The fallback is clearly
    documented so callers know the difference.

    Returns ``(labels, inertia)`` where labels are 0-based cluster indices.
    """
    n = len(embeddings)
    if n_clusters >= n:
        return list(range(n)), 0.0

    # Each point starts as its own cluster (represented as frozenset of indices)
    clusters: List[List[int]] = [[i] for i in range(n)]

    while len(clusters) > n_clusters:
        best_d   = float("inf")
        best_i   = 0
        best_j   = 1
        for ci in range(len(clusters)):
            for cj in range(ci + 1, len(clusters)):
                # Single-linkage: minimum distance between any pair
                d = min(
                    _cosine_distance(embeddings[a], embeddings[b])
                    for a in clusters[ci]
                    for b in clusters[cj]
                )
                if d < best_d:
                    best_d = d
                    best_i = ci
                    best_j = cj
        # Merge best_j into best_i
        clusters[best_i] = clusters[best_i] + clusters[best_j]
        clusters.pop(best_j)

    labels = [0] * n
    for cluster_id, members in enumerate(clusters):
        for idx in members:
            labels[idx] = cluster_id

    # Inertia: sum of within-cluster pairwise cosine distances
    inertia = 0.0
    for members in clusters:
        for a in members:
            for b in members:
                if a < b:
                    inertia += _cosine_distance(embeddings[a], embeddings[b])

    return labels, inertia


def _make_minimal_dendrogram(n: int) -> DendrogramData:
    """Return a trivially empty DendrogramData when scipy is unavailable."""
    return DendrogramData(
        icoord     = [],
        dcoord     = [],
        ivl        = [str(i) for i in range(n)],
        leaves     = list(range(n)),
        color_list = [],
    )


# ── GuidanceClusterer ─────────────────────────────────────────────────────────

class GuidanceClusterer:
    """
    Agglomerative (Ward) clusterer for guidance document embeddings.

    Args:
        n_clusters:  Target number of flat clusters (used in ``fcluster``).
        labels:      Optional list of string labels for dendrogram leaf nodes.
                     If ``None``, integer indices are used.
        require_scipy: If ``True``, raise ``ClusteringUnavailableError`` when scipy
                       is not installed.  If ``False`` (default), fall back to the
                       single-linkage pure-Python implementation.
    """

    def __init__(
        self,
        n_clusters:    int  = 8,
        labels:        Optional[List[str]] = None,
        require_scipy: bool = False,
    ) -> None:
        if n_clusters < 1:
            raise ValueError(f"n_clusters must be ≥ 1, got {n_clusters}")
        self.n_clusters    = n_clusters
        self.labels        = labels
        self.require_scipy = require_scipy
        self._result: Optional[ClusterResult] = None

    # ── Primary API ──────────────────────────────────────────────────────────

    def fit(self, embeddings: List[List[float]]) -> ClusterResult:
        """
        Cluster *embeddings* and return a ``ClusterResult``.

        Args:
            embeddings: List of embedding vectors (all must be the same dimension).

        Returns:
            A ``ClusterResult`` with flat labels, linkage matrix, and dendrogram.

        Raises:
            ValueError: If fewer than 2 embeddings are provided.
            ClusteringUnavailableError: If ``require_scipy=True`` and scipy is absent.
        """
        if len(embeddings) < 2:
            raise ValueError(
                f"At least 2 embeddings required for clustering, got {len(embeddings)}"
            )

        n = len(embeddings)
        effective_k = min(self.n_clusters, n)

        if _SCIPY_AVAILABLE:
            self._result = self._fit_scipy(embeddings, effective_k)
        else:
            if self.require_scipy:
                raise ClusteringUnavailableError(
                    "scipy is required for Ward clustering but is not installed. "
                    "Install it with: pip install scipy"
                )
            self._result = self._fit_fallback(embeddings, effective_k)

        return self._result

    # ── Scipy path ────────────────────────────────────────────────────────────

    def _fit_scipy(self, embeddings: List[List[float]], k: int) -> ClusterResult:
        assert _scipy_pdist is not None
        assert _scipy_linkage is not None
        assert _scipy_fcluster is not None
        assert _scipy_dendrogram is not None

        n = len(embeddings)

        # 1. Pairwise cosine distances (condensed)
        dist_vec = _scipy_pdist(embeddings, metric="cosine")

        # 2. Ward linkage on distance matrix
        Z = _scipy_linkage(dist_vec, method="ward")  # (n-1, 4) array

        # 3. Flat cluster labels (1-based from scipy → convert to 0-based)
        raw_labels = _scipy_fcluster(Z, k, criterion="maxclust")
        labels = [int(lbl) - 1 for lbl in raw_labels]

        # 4. Linkage matrix as Python list
        linkage_list = Z.tolist()

        # 5. ClusterNodes
        nodes = [
            ClusterNode(
                left_id  = int(row[0]),
                right_id = int(row[1]),
                distance = float(row[2]),
                count    = int(row[3]),
            )
            for row in linkage_list
        ]

        # 6. Dendrogram data
        leaf_labels = self.labels or [str(i) for i in range(n)]
        ddata = _scipy_dendrogram(
            Z,
            labels       = leaf_labels,
            no_plot      = True,
            color_threshold = 0,
        )
        dendrogram = DendrogramData(
            icoord     = ddata["icoord"],
            dcoord     = ddata["dcoord"],
            ivl        = list(ddata["ivl"]),
            leaves     = list(ddata["leaves"]),
            color_list = list(ddata["color_list"]),
        )

        # 7. Inertia: sum of distances² within clusters (approximation via linkage)
        inertia = float(sum(row[2] ** 2 * row[3] for row in linkage_list[-k:]))

        return ClusterResult(
            labels         = labels,
            n_clusters     = k,
            n_samples      = n,
            linkage_matrix = linkage_list,
            dendrogram     = dendrogram,
            nodes          = nodes,
            inertia        = inertia,
        )

    # ── Fallback path (no scipy) ──────────────────────────────────────────────

    def _fit_fallback(self, embeddings: List[List[float]], k: int) -> ClusterResult:
        n = len(embeddings)
        labels, inertia = _simple_agglomerative(embeddings, k)
        dendrogram = _make_minimal_dendrogram(n)
        return ClusterResult(
            labels     = labels,
            n_clusters = k,
            n_samples  = n,
            dendrogram = dendrogram,
            inertia    = inertia,
        )

    # ── Post-fit helpers ──────────────────────────────────────────────────────

    @property
    def result(self) -> Optional[ClusterResult]:
        """Return the most recent ``ClusterResult``, or ``None`` if not yet fitted."""
        return self._result

    def recut(self, n_clusters: int) -> ClusterResult:
        """
        Re-apply ``fcluster`` at a different *n_clusters* without recomputing linkage.

        Only available when scipy is installed and ``fit()`` has been called.

        Args:
            n_clusters: New target cluster count.

        Returns:
            Updated ``ClusterResult`` (stored as ``self.result``).

        Raises:
            RuntimeError: If ``fit()`` has not been called yet.
            ClusteringUnavailableError: If scipy is not installed.
        """
        if self._result is None:
            raise RuntimeError("Call fit() before recut()")
        if not _SCIPY_AVAILABLE or _scipy_fcluster is None:
            raise ClusteringUnavailableError(
                "recut() requires scipy; current result used single-linkage fallback."
            )
        assert _scipy_fcluster is not None
        import numpy as _np
        Z = _np.array(self._result.linkage_matrix)
        raw_labels = _scipy_fcluster(Z, n_clusters, criterion="maxclust")
        labels = [int(lbl) - 1 for lbl in raw_labels]
        self._result = ClusterResult(
            labels         = labels,
            n_clusters     = n_clusters,
            n_samples      = self._result.n_samples,
            linkage_matrix = self._result.linkage_matrix,
            dendrogram     = self._result.dendrogram,
            nodes          = self._result.nodes,
            inertia        = self._result.inertia,
        )
        return self._result


# ── Convenience function ──────────────────────────────────────────────────────

def cluster_embeddings(
    embeddings:    List[List[float]],
    n_clusters:    int = 8,
    labels:        Optional[List[str]] = None,
    require_scipy: bool = False,
) -> ClusterResult:
    """
    One-call convenience function for Ward-linkage clustering.

    Args:
        embeddings:    List of embedding vectors (same dimension for all).
        n_clusters:    Target number of clusters.
        labels:        Optional string labels for dendrogram leaves.
        require_scipy: Raise ``ClusteringUnavailableError`` if scipy absent.

    Returns:
        A ``ClusterResult`` with flat labels and dendrogram data.
    """
    return GuidanceClusterer(
        n_clusters    = n_clusters,
        labels        = labels,
        require_scipy = require_scipy,
    ).fit(embeddings)
