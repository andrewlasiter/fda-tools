"""
Unit Tests for Persistent Bridge Sessions (FDA-121)
====================================================

Validates the SQLite-backed SessionStore introduced to replace the
in-memory SESSIONS dict in bridge/server.py:

  - SessionStore.__init__: creates DB file and schema on first use
  - SessionStore.create_or_get: upsert — new vs existing session logic
  - SessionStore.get: read by session_id, None for unknown ID
  - SessionStore.list_all: list with optional user_id filter
  - SessionStore.count: count with optional user_id filter
  - SessionStore.update_context: persist context dict, touch last_accessed
  - SessionStore.delete: remove session, returns bool
  - SessionStore.expire_old: auto-expire idle sessions
  - Persistence: sessions survive store re-instantiation (simulates restart)
  - Concurrency: concurrent writes do not corrupt the database

Test count: 26
Target: pytest plugins/fda_tools/tests/test_fda121_session_persistence.py -v
"""

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from fda_tools.bridge.session_store import (
    SESSION_EXPIRY_HOURS,
    SessionStore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path):
    """SessionStore backed by a temp-dir DB."""
    return SessionStore(db_path=str(tmp_path / "sessions.db"))


# ---------------------------------------------------------------------------
# TestSessionStoreInit
# ---------------------------------------------------------------------------


class TestSessionStoreInit:
    """Tests for SessionStore initialisation."""

    def test_creates_db_file(self, tmp_path):
        db = tmp_path / "sessions.db"
        SessionStore(db_path=str(db))
        assert db.exists()

    def test_creates_sessions_table(self, tmp_path):
        db = tmp_path / "sessions.db"
        SessionStore(db_path=str(db))
        import sqlite3
        conn = sqlite3.connect(str(db))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "sessions" in tables

    def test_existing_db_not_wiped_on_reinit(self, tmp_path):
        db = tmp_path / "sessions.db"
        store = SessionStore(db_path=str(db))
        store.create_or_get("alice")
        # Reinitialise (simulates a restart)
        store2 = SessionStore(db_path=str(db))
        assert store2.count() == 1


# ---------------------------------------------------------------------------
# TestCreateOrGet
# ---------------------------------------------------------------------------


class TestCreateOrGet:
    """Tests for SessionStore.create_or_get()."""

    def test_new_session_returns_dict(self, store):
        s = store.create_or_get("alice")
        assert isinstance(s, dict)
        assert s["user_id"] == "alice"

    def test_new_session_has_uuid_if_no_id_given(self, store):
        s = store.create_or_get("alice")
        # UUIDs have 4 hyphens
        assert s["session_id"].count("-") == 4

    def test_custom_session_id_honored(self, store):
        s = store.create_or_get("bob", session_id="my-custom-id")
        assert s["session_id"] == "my-custom-id"

    def test_existing_session_returned(self, store):
        s1 = store.create_or_get("alice")
        s2 = store.create_or_get("alice", session_id=s1["session_id"])
        assert s2["session_id"] == s1["session_id"]
        assert s2["created_at"] == s1["created_at"]

    def test_last_accessed_refreshed_on_return(self, store):
        s1 = store.create_or_get("alice")
        original_time = s1["last_accessed"]
        time.sleep(0.01)  # ensure clock advances
        s2 = store.create_or_get("alice", session_id=s1["session_id"])
        assert s2["last_accessed"] >= original_time

    def test_empty_context_on_new_session(self, store):
        s = store.create_or_get("alice")
        assert s["context"] == {}

    def test_count_increments_for_new_sessions(self, store):
        store.create_or_get("alice")
        store.create_or_get("bob")
        assert store.count() == 2


# ---------------------------------------------------------------------------
# TestGet
# ---------------------------------------------------------------------------


class TestGet:
    """Tests for SessionStore.get()."""

    def test_get_existing_returns_dict(self, store):
        s = store.create_or_get("alice")
        result = store.get(s["session_id"])
        assert result is not None
        assert result["session_id"] == s["session_id"]

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("does-not-exist") is None

    def test_get_data_round_trips(self, store):
        s = store.create_or_get("carol")
        result = store.get(s["session_id"])
        assert result["user_id"] == "carol"
        assert isinstance(result["context"], dict)


# ---------------------------------------------------------------------------
# TestListAll
# ---------------------------------------------------------------------------


class TestListAll:
    """Tests for SessionStore.list_all()."""

    def test_list_returns_all_sessions(self, store):
        store.create_or_get("alice")
        store.create_or_get("bob")
        results = store.list_all()
        assert len(results) == 2

    def test_list_filters_by_user_id(self, store):
        store.create_or_get("alice")
        store.create_or_get("alice")
        store.create_or_get("bob")
        results = store.list_all(user_id="alice")
        assert len(results) == 2
        assert all(r["user_id"] == "alice" for r in results)

    def test_list_empty_when_no_sessions(self, store):
        assert store.list_all() == []


# ---------------------------------------------------------------------------
# TestCount
# ---------------------------------------------------------------------------


class TestCount:
    """Tests for SessionStore.count()."""

    def test_count_all(self, store):
        store.create_or_get("alice")
        store.create_or_get("bob")
        assert store.count() == 2

    def test_count_with_user_filter(self, store):
        store.create_or_get("alice")
        store.create_or_get("alice")
        store.create_or_get("bob")
        assert store.count(user_id="alice") == 2
        assert store.count(user_id="bob") == 1


# ---------------------------------------------------------------------------
# TestUpdateContext
# ---------------------------------------------------------------------------


class TestUpdateContext:
    """Tests for SessionStore.update_context()."""

    def test_update_context_persists(self, store, tmp_path):
        s = store.create_or_get("alice")
        ctx = {"project_path": "/tmp/project", "command": "research"}
        store.update_context(s["session_id"], ctx)
        # Re-read from DB
        result = store.get(s["session_id"])
        assert result["context"] == ctx

    def test_update_context_returns_true_on_existing(self, store):
        s = store.create_or_get("alice")
        assert store.update_context(s["session_id"], {"x": 1}) is True

    def test_update_context_returns_false_on_missing(self, store):
        assert store.update_context("no-such-id", {"x": 1}) is False


# ---------------------------------------------------------------------------
# TestDelete
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for SessionStore.delete()."""

    def test_delete_removes_session(self, store):
        s = store.create_or_get("alice")
        store.delete(s["session_id"])
        assert store.get(s["session_id"]) is None

    def test_delete_returns_true_on_existing(self, store):
        s = store.create_or_get("alice")
        assert store.delete(s["session_id"]) is True

    def test_delete_returns_false_on_missing(self, store):
        assert store.delete("no-such-id") is False


# ---------------------------------------------------------------------------
# TestExpireOld
# ---------------------------------------------------------------------------


class TestExpireOld:
    """Tests for SessionStore.expire_old()."""

    def _write_old_session(self, store: SessionStore, hours_ago: int, user: str = "old") -> str:
        """Insert a session whose last_accessed is *hours_ago* in the past."""
        s = store.create_or_get(user)
        past = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        import sqlite3
        conn = sqlite3.connect(str(store.db_path))
        conn.execute(
            "UPDATE sessions SET last_accessed = ? WHERE session_id = ?",
            (past, s["session_id"]),
        )
        conn.commit()
        conn.close()
        return s["session_id"]

    def test_expire_deletes_old_sessions(self, store):
        old_id = self._write_old_session(store, hours_ago=SESSION_EXPIRY_HOURS + 1)
        expired = store.expire_old()
        assert old_id in expired
        assert store.get(old_id) is None

    def test_expire_keeps_recent_sessions(self, store):
        store.create_or_get("alice")  # just-created, definitely recent
        expired = store.expire_old()
        assert store.count() == 1
        assert expired == []

    def test_expire_returns_list_of_ids(self, store):
        old1 = self._write_old_session(store, hours_ago=SESSION_EXPIRY_HOURS + 2, user="u1")
        old2 = self._write_old_session(store, hours_ago=SESSION_EXPIRY_HOURS + 3, user="u2")
        expired = store.expire_old()
        assert old1 in expired
        assert old2 in expired

    def test_expire_on_empty_store_returns_empty(self, store):
        assert store.expire_old() == []


# ---------------------------------------------------------------------------
# TestPersistence (restart simulation)
# ---------------------------------------------------------------------------


class TestPersistence:
    """Sessions must survive store re-instantiation (server restart)."""

    def test_sessions_survive_reinit(self, tmp_path):
        db = str(tmp_path / "sessions.db")
        store1 = SessionStore(db_path=db)
        s = store1.create_or_get("alice", session_id="persistent-id")

        # Simulate restart: create a new store pointing at the same file
        store2 = SessionStore(db_path=db)
        result = store2.get("persistent-id")
        assert result is not None
        assert result["user_id"] == "alice"

    def test_context_survives_reinit(self, tmp_path):
        db = str(tmp_path / "sessions.db")
        store1 = SessionStore(db_path=db)
        s = store1.create_or_get("alice")
        store1.update_context(s["session_id"], {"key": "value"})

        store2 = SessionStore(db_path=db)
        result = store2.get(s["session_id"])
        assert result["context"] == {"key": "value"}

    def test_count_correct_after_reinit(self, tmp_path):
        db = str(tmp_path / "sessions.db")
        store1 = SessionStore(db_path=db)
        store1.create_or_get("alice")
        store1.create_or_get("bob")

        store2 = SessionStore(db_path=db)
        assert store2.count() == 2


# ---------------------------------------------------------------------------
# TestConcurrency
# ---------------------------------------------------------------------------


class TestConcurrency:
    """Concurrent writes must not corrupt the database."""

    def test_concurrent_creates_no_corruption(self, tmp_path):
        db = str(tmp_path / "sessions.db")
        store = SessionStore(db_path=db)
        errors: list = []

        def worker(user_id: str):
            try:
                for _ in range(5):
                    store.create_or_get(user_id)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(f"user{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        # 10 users × 5 calls each, every call without a session_id
        # creates a new UUID session → 50 rows total, all valid.
        assert store.count() == 50
        # All sessions are queryable (no corrupted rows)
        sessions = store.list_all()
        for s in sessions:
            assert s["session_id"] is not None
            assert isinstance(s["context"], dict)
