"""
FDA-219  Supabase Connection Layer
====================================
Singleton Supabase client that reads credentials exclusively from
environment variables.  Uses an optional-import pattern: if the
``supabase`` package is not installed the module still loads and all
public API calls raise ``SupabaseConnectionError`` rather than
``ImportError``.

Environment variables (both required for a real connection)
-----------------------------------------------------------
``SUPABASE_URL``         — Project URL, e.g. ``https://xxxx.supabase.co``
``SUPABASE_SECRET_KEY``  — Service-role key (NOT the anon/public key).
                           Never commit this value; store in ``.env`` only.

Design
------
``SupabaseConfig``         — Immutable credential value object loaded from env.
``SupabaseConnectionError``— Domain exception (wraps SDK errors and missing creds).
``SupabaseClient``         — Thin facade around the SDK client with lazy init,
                             health check, table helper, rpc helper, and a
                             semantic-search helper for pgvector tables.
``get_client()``           — Module-level singleton factory.  Returns the same
                             ``SupabaseClient`` instance on every call.

Usage
-----
    from fda_tools.lib.supabase_client import get_client, SupabaseConnectionError

    client = get_client()             # raises SupabaseConnectionError if not configured
    ok = client.health_check()        # True / False

    rows = client.table("guidance_embeddings").select("*").limit(5).execute()

    # pgvector similarity search (cosine distance)
    results = client.vector_search(
        table="guidance_embeddings",
        embedding_column="embedding",
        query_vector=[0.1, 0.2, ...],   # 384 floats
        match_threshold=0.75,
        match_count=10,
    )
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional supabase-py import — no-op stub when not installed
try:
    from supabase import create_client as _create_client  # type: ignore[import]
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False
    _create_client = None  # type: ignore[assignment]


# ── Exception ─────────────────────────────────────────────────────────────────

class SupabaseConnectionError(Exception):
    """
    Raised when the Supabase client cannot be initialised or a call fails.

    Common causes:
    - ``SUPABASE_URL`` or ``SUPABASE_SECRET_KEY`` env vars not set.
    - ``supabase`` package not installed.
    - Network error reaching the Supabase project.
    """


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SupabaseConfig:
    """
    Immutable Supabase credential container loaded from environment variables.

    Attributes:
        url:        SUPABASE_URL value.
        secret_key: SUPABASE_SECRET_KEY value (service-role key).
    """
    url:        str
    secret_key: str

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        """
        Load credentials from environment variables.

        Raises:
            SupabaseConnectionError: If ``SUPABASE_URL`` or
                ``SUPABASE_SECRET_KEY`` are not set or are empty.
        """
        url        = os.environ.get("SUPABASE_URL", "").strip()
        secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()

        missing = [v for v, val in (("SUPABASE_URL", url), ("SUPABASE_SECRET_KEY", secret_key)) if not val]
        if missing:
            raise SupabaseConnectionError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set SUPABASE_URL and SUPABASE_SECRET_KEY before connecting."
            )
        return cls(url=url, secret_key=secret_key)

    def redacted(self) -> Dict[str, str]:
        """Return a dict safe for logging — secret_key is redacted."""
        return {
            "url":        self.url,
            "secret_key": f"{self.secret_key[:8]}…(redacted)",
        }


# ── Client ────────────────────────────────────────────────────────────────────

class SupabaseClient:
    """
    Thin facade around the supabase-py ``Client``.

    Initialised lazily on the first call that actually uses the connection.
    All methods raise ``SupabaseConnectionError`` if the SDK is missing or
    credentials are unavailable.

    Attributes:
        config: The ``SupabaseConfig`` used to create this client.
    """

    def __init__(self, config: SupabaseConfig) -> None:
        self.config = config
        self._client: Any = None   # underlying supabase.Client, set on first use

    # ── Lazy init ─────────────────────────────────────────────────────────────

    def _ensure_connected(self) -> Any:
        """Return the underlying SDK client, initialising it on first call."""
        if self._client is not None:
            return self._client

        if not _SUPABASE_AVAILABLE:
            raise SupabaseConnectionError(
                "supabase-py is not installed. "
                "Run `pip install supabase` to enable Supabase connectivity."
            )

        try:
            assert _create_client is not None  # guarded by _SUPABASE_AVAILABLE check above
            self._client = _create_client(self.config.url, self.config.secret_key)
            logger.debug("SupabaseClient: connected to %s", self.config.url)
            return self._client
        except Exception as exc:
            raise SupabaseConnectionError(
                f"Failed to connect to Supabase at {self.config.url}: {exc}"
            ) from exc

    # ── Public helpers ────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """
        Return ``True`` if the Supabase project is reachable, ``False`` otherwise.

        Never raises — safe to call in startup probes.
        """
        try:
            client = self._ensure_connected()
            # A simple metadata query to the auth API acts as a health probe
            client.auth.get_session()
            return True
        except SupabaseConnectionError:
            return False
        except Exception as exc:
            logger.warning("SupabaseClient.health_check: %s", exc)
            return False

    def table(self, table_name: str) -> Any:
        """
        Return a ``QueryBuilder`` for *table_name*.

        Equivalent to ``supabase.table(table_name)``.

        Raises:
            SupabaseConnectionError: If the SDK is unavailable or creds missing.
        """
        return self._ensure_connected().table(table_name)

    def rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call a Postgres function via the PostgREST RPC endpoint.

        Args:
            function_name: Name of the PL/pgSQL function.
            params:        Dict of named parameters.

        Raises:
            SupabaseConnectionError: If the SDK is unavailable or creds missing.
        """
        return self._ensure_connected().rpc(function_name, params or {})

    def vector_search(
        self,
        table:            str,
        embedding_column: str,
        query_vector:     List[float],
        match_threshold:  float = 0.75,
        match_count:      int   = 10,
        select_columns:   str   = "*",
    ) -> Any:
        """
        Perform a pgvector cosine-similarity search via a stored Postgres function.

        Expects the function ``match_<table>`` to exist in the database, with the
        signature produced by :func:`~fda_tools.lib.pgvector_schema.match_function_sql`.

        Args:
            table:            Target table name (e.g. ``"guidance_embeddings"``).
            embedding_column: Column holding the vector (e.g. ``"embedding"``).
            query_vector:     Query embedding as a list of floats.
            match_threshold:  Minimum cosine similarity (0–1).
            match_count:      Maximum number of results to return.
            select_columns:   Columns to project (passed to the function).

        Returns:
            Raw response from the Supabase RPC call.

        Raises:
            SupabaseConnectionError: If the SDK is unavailable.
        """
        logger.debug(
            "vector_search: table=%s, embedding_col=%s, threshold=%.2f, count=%d, select=%s",
            table, embedding_column, match_threshold, match_count, select_columns,
        )
        return self.rpc(
            f"match_{table}",
            {
                "query_embedding": query_vector,
                "match_threshold": match_threshold,
                "match_count":     match_count,
            },
        )

    def is_available(self) -> bool:
        """Return True if the supabase-py package is installed."""
        return _SUPABASE_AVAILABLE

    def is_configured(self) -> bool:
        """Return True if both required env vars are set (non-empty)."""
        return bool(
            os.environ.get("SUPABASE_URL", "").strip()
            and os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_singleton: Optional[SupabaseClient] = None


def get_client() -> SupabaseClient:
    """
    Return the module-level singleton ``SupabaseClient``.

    Creates the client on the first call using ``SupabaseConfig.from_env()``.
    Subsequent calls return the same instance.

    Raises:
        SupabaseConnectionError: If credentials are not configured.
    """
    global _singleton
    if _singleton is None:
        config    = SupabaseConfig.from_env()
        _singleton = SupabaseClient(config)
        logger.info("SupabaseClient singleton created for %s", config.url)
    return _singleton


def reset_singleton() -> None:
    """
    Clear the module-level singleton (for use in tests only).

    After calling this, the next ``get_client()`` call re-reads env vars.
    """
    global _singleton
    _singleton = None
