"""
SQLite-backed persistent session store for the FDA Tools Bridge Server.

Replaces the in-memory ``SESSIONS`` dict so that active sessions survive
server restarts.  All public methods are thread-safe (single threading.Lock
guards every SQLite call).

Session expiry:
    Sessions idle for more than SESSION_EXPIRY_HOURS (default 24) are
    deleted automatically.  Call :meth:`expire_old` on startup to reap
    stale sessions before loading the count.

Database:
    Stored at ``~/fda-510k-data/bridge/sessions.db`` (WAL mode).
    Created automatically on first use; the directory is also created if
    it does not exist.
"""

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_SESSION_DB: str = os.path.expanduser("~/fda-510k-data/bridge/sessions.db")
SESSION_EXPIRY_HOURS: int = 24

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    context_json  TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}'
)
"""


class SessionStore:
    """Persistent session store backed by SQLite.

    Args:
        db_path: Path to the SQLite database file.  Defaults to
            ``~/fda-510k-data/bridge/sessions.db``.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path or DEFAULT_SESSION_DB)
        self._lock = threading.Lock()
        self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_or_get(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new session or touch an existing one.

        If *session_id* is provided and already exists in the database,
        ``last_accessed`` is refreshed and the session dict is returned.
        Otherwise a new session row is inserted.

        Args:
            user_id: Identifier for the session owner.
            session_id: Requested session ID.  A UUID is generated if
                ``None``.

        Returns:
            Session dict with keys: ``session_id``, ``user_id``,
            ``created_at``, ``last_accessed``, ``context``, ``metadata``.
        """
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._connect()
            try:
                if session_id:
                    row = conn.execute(
                        "SELECT * FROM sessions WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()
                    if row:
                        conn.execute(
                            "UPDATE sessions SET last_accessed = ? WHERE session_id = ?",
                            (now, session_id),
                        )
                        conn.commit()
                        return self._row_to_dict(dict(row), override_last_accessed=now)

                new_id = session_id or str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO sessions
                           (session_id, user_id, created_at, last_accessed,
                            context_json, metadata_json)
                       VALUES (?, ?, ?, ?, '{}', '{}')""",
                    (new_id, user_id, now, now),
                )
                conn.commit()
                return {
                    "session_id": new_id,
                    "user_id": user_id,
                    "created_at": now,
                    "last_accessed": now,
                    "context": {},
                    "metadata": {},
                }
            finally:
                conn.close()

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the session dict for *session_id*, or ``None``."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                return self._row_to_dict(dict(row)) if row else None
            finally:
                conn.close()

    def list_all(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all sessions, optionally filtered by *user_id*.

        Results are ordered by ``last_accessed`` descending (most recent
        first).
        """
        with self._lock:
            conn = self._connect()
            try:
                if user_id:
                    rows = conn.execute(
                        "SELECT * FROM sessions WHERE user_id = ? ORDER BY last_accessed DESC",
                        (user_id,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM sessions ORDER BY last_accessed DESC",
                    ).fetchall()
                return [self._row_to_dict(dict(r)) for r in rows]
            finally:
                conn.close()

    def count(self, user_id: Optional[str] = None) -> int:
        """Return the number of sessions, optionally filtered by *user_id*."""
        with self._lock:
            conn = self._connect()
            try:
                if user_id:
                    return conn.execute(
                        "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                        (user_id,),
                    ).fetchone()[0]
                return conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            finally:
                conn.close()

    def update_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Persist *context* for *session_id* and refresh ``last_accessed``.

        Returns:
            ``True`` if the session was found and updated, ``False`` if not.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "UPDATE sessions SET context_json = ?, last_accessed = ? WHERE session_id = ?",
                    (json.dumps(context), now, session_id),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def delete(self, session_id: str) -> bool:
        """Delete a session by ID.

        Returns:
            ``True`` if the session existed and was deleted.
        """
        with self._lock:
            conn = self._connect()
            try:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?", (session_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def expire_old(self, max_age_hours: int = SESSION_EXPIRY_HOURS) -> List[str]:
        """Delete sessions idle for longer than *max_age_hours*.

        Args:
            max_age_hours: Maximum allowed idle time in hours (default 24).

        Returns:
            List of session IDs that were deleted.
        """
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        ).isoformat()

        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT session_id FROM sessions WHERE last_accessed < ?",
                    (cutoff,),
                ).fetchall()
                expired = [r[0] for r in rows]
                if expired:
                    placeholders = ",".join("?" * len(expired))
                    conn.execute(
                        f"DELETE FROM sessions WHERE session_id IN ({placeholders})",
                        expired,
                    )
                    conn.commit()
                return expired
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        """Open and configure a SQLite connection."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        """Create the sessions table if it does not already exist."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(_CREATE_TABLE)
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _row_to_dict(
        row: Dict[str, Any],
        override_last_accessed: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert a SQLite row dict to the canonical session dict."""
        return {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "created_at": row["created_at"],
            "last_accessed": override_last_accessed or row["last_accessed"],
            "context": json.loads(row.get("context_json") or "{}"),
            "metadata": json.loads(row.get("metadata_json") or "{}"),
        }
