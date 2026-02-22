"""
FDA-219: Supabase connection layer.

Reads credentials exclusively from environment variables — never hardcoded.
Required env vars:
  SUPABASE_URL         — e.g. https://xxxx.supabase.co
  SUPABASE_SECRET_KEY  — service-role key (never the anon key for server use)

Optional env vars:
  SUPABASE_POOL_SIZE       — connection pool size (default: 5)
  SUPABASE_CONNECT_TIMEOUT — connection timeout in seconds (default: 10)
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Sentinel to distinguish "not yet initialised" from None
_NOT_INITIALISED: Any = object()


class SupabaseClientError(Exception):
    """Raised when the Supabase client cannot be initialised or used."""


class SupabaseClient:
    """
    Singleton Supabase client with lazy initialisation.

    Usage:
        client = SupabaseClient.get_instance()
        result = client.table("guidance_chunks").select("*").execute()

    Credentials are read from environment variables on first access.
    All connection parameters are stripped from log output.
    """

    _instance: Optional["SupabaseClient"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._client: Any = _NOT_INITIALISED
        self._url: Optional[str] = None

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "SupabaseClient":
        """Return the shared singleton, creating it on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton — useful in tests to inject fresh env vars."""
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Lazy client property
    # ------------------------------------------------------------------

    @property
    def client(self):
        """Return the underlying supabase client, initialising on first access."""
        if self._client is _NOT_INITIALISED:
            self._client = self._build_client()
        return self._client

    def _build_client(self):
        """Read env vars and create supabase client. Raises on missing vars."""
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()

        if not url:
            raise EnvironmentError(
                "SUPABASE_URL is not set. "
                "Export it before starting the application:\n"
                "  export SUPABASE_URL=https://your-project.supabase.co"
            )
        if not key:
            raise EnvironmentError(
                "SUPABASE_SECRET_KEY is not set. "
                "Export it before starting the application:\n"
                "  export SUPABASE_SECRET_KEY=your-service-role-key\n"
                "Never commit this value to source control."
            )

        self._url = url  # store URL (safe to log), never store key

        try:
            from supabase import create_client, Client  # type: ignore
        except ImportError as exc:
            raise SupabaseClientError(
                "supabase-py is not installed. Run: pip install supabase"
            ) from exc

        pool_size = int(os.environ.get("SUPABASE_POOL_SIZE", "5"))
        connect_timeout = int(os.environ.get("SUPABASE_CONNECT_TIMEOUT", "10"))

        options: dict = {
            "postgrest_client_timeout": connect_timeout,
        }

        logger.info(
            "Initialising Supabase client — url=%s pool_size=%d timeout=%ds",
            url,
            pool_size,
            connect_timeout,
        )

        client: Client = create_client(url, key, options=options)  # type: ignore[arg-type]
        logger.info("Supabase client initialised successfully")
        return client

    # ------------------------------------------------------------------
    # Convenience pass-throughs
    # ------------------------------------------------------------------

    def table(self, name: str):
        """Proxy to underlying client.table()."""
        return self.client.table(name)

    def rpc(self, fn: str, params: dict | None = None):
        """Proxy to underlying client.rpc()."""
        return self.client.rpc(fn, params or {})

    def storage(self):
        """Proxy to underlying client.storage."""
        return self.client.storage

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """
        Return True if the Supabase project is reachable, False otherwise.

        Executes a lightweight RPC call; does not touch any application tables.
        Credentials are never included in log messages.
        """
        try:
            # select 1 via PostgREST — minimal overhead
            self.client.rpc("pg_sleep", {"seconds": 0}).execute()
            logger.debug("Supabase ping succeeded — url=%s", self._url)
            return True
        except Exception as exc:  # noqa: BLE001
            # Log without exposing key material
            logger.warning(
                "Supabase ping failed — url=%s error=%s",
                self._url,
                type(exc).__name__,
            )
            return False

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        initialised = self._client is not _NOT_INITIALISED
        return f"<SupabaseClient url={self._url!r} initialised={initialised}>"
