"""
Unit tests for PostgreSQLDatabase (FDA-191).

All psycopg2 interactions are mocked so no live database is needed.
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(pool_mock):
    """Import and construct a PostgreSQLDatabase with a mocked connection pool."""
    from fda_tools.lib.postgres_database import PostgreSQLDatabase

    with patch(
        "fda_tools.lib.postgres_database.pool.ThreadedConnectionPool",
        return_value=pool_mock,
    ):
        db = PostgreSQLDatabase(
            host="localhost",
            port=6432,
            database="fda_offline",
            user="fda_user",
            password="testpass",
            pool_size=5,
        )
    return db


def _make_conn_mock(rows=None):
    """Build a mock psycopg2 connection and cursor."""
    cur = MagicMock()
    cur.fetchone.return_value = rows[0] if rows else None
    cur.fetchall.return_value = rows or []
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cur


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pool_mock():
    return MagicMock()


@pytest.fixture
def db(pool_mock):
    return _make_db(pool_mock)


# ---------------------------------------------------------------------------
# 1. Initialisation
# ---------------------------------------------------------------------------


class TestInit:
    def test_pool_created_on_init(self, pool_mock, db):
        assert db.pool is pool_mock

    def test_default_port_is_pgbouncer(self, pool_mock):
        from fda_tools.lib.postgres_database import PostgreSQLDatabase

        with patch(
            "fda_tools.lib.postgres_database.pool.ThreadedConnectionPool",
            return_value=pool_mock,
        ) as mock_pool_cls:
            PostgreSQLDatabase(password="pw")
        _, kwargs = mock_pool_cls.call_args
        assert kwargs["port"] == 6432

    def test_pool_init_failure_raises(self):
        from fda_tools.lib.postgres_database import PostgreSQLDatabase

        with patch(
            "fda_tools.lib.postgres_database.pool.ThreadedConnectionPool",
            side_effect=Exception("connection refused"),
        ):
            with pytest.raises(Exception, match="connection refused"):
                PostgreSQLDatabase(password="pw")

    def test_password_from_env(self, monkeypatch):
        from fda_tools.lib.postgres_database import PostgreSQLDatabase

        monkeypatch.setenv("DB_PASSWORD", "env_pass")
        pool_mock = MagicMock()
        with patch(
            "fda_tools.lib.postgres_database.pool.ThreadedConnectionPool",
            return_value=pool_mock,
        ):
            db = PostgreSQLDatabase()
        assert db.password == "env_pass"

    def test_endpoint_tables_complete(self, db):
        expected = {"510k", "classification", "maude", "recalls", "pma", "udi", "enforcement"}
        assert set(db.ENDPOINT_TABLES.keys()) == expected

    def test_primary_keys_complete(self, db):
        assert set(db.PRIMARY_KEYS.keys()) == set(db.ENDPOINT_TABLES.keys())


# ---------------------------------------------------------------------------
# 2. compute_checksum
# ---------------------------------------------------------------------------


class TestComputeChecksum:
    def test_returns_hex_string(self, db):
        result = db.compute_checksum({"k_number": "K123456", "value": 42})
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex length

    def test_deterministic(self, db):
        data = {"a": 1, "b": [2, 3]}
        assert db.compute_checksum(data) == db.compute_checksum(data)

    def test_order_independent(self, db):
        assert db.compute_checksum({"a": 1, "b": 2}) == db.compute_checksum({"b": 2, "a": 1})

    def test_different_data_different_checksum(self, db):
        assert db.compute_checksum({"a": 1}) != db.compute_checksum({"a": 2})

    def test_checksum_uses_hmac_sha256(self, db):
        data = {"x": "y"}
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(
            db.secret_key.encode(), canonical.encode(), hashlib.sha256
        ).hexdigest()
        assert db.compute_checksum(data) == expected


# ---------------------------------------------------------------------------
# 3. get_connection context manager
# ---------------------------------------------------------------------------


class TestGetConnection:
    def test_returns_conn_and_commits(self, db, pool_mock):
        conn = MagicMock()
        pool_mock.getconn.return_value = conn

        with db.get_connection() as c:
            assert c is conn

        conn.commit.assert_called_once()
        pool_mock.putconn.assert_called_once_with(conn)

    def test_rolls_back_on_error(self, db, pool_mock):
        conn = MagicMock()
        pool_mock.getconn.return_value = conn

        with pytest.raises(ValueError):
            with db.get_connection():
                raise ValueError("oops")

        conn.rollback.assert_called_once()
        pool_mock.putconn.assert_called_once_with(conn)

    def test_raises_when_pool_none(self, db):
        db.pool = None
        with pytest.raises(RuntimeError, match="not initialized"):
            with db.get_connection():
                pass


# ---------------------------------------------------------------------------
# 4. upsert_record — all 7 endpoints
# ---------------------------------------------------------------------------


class TestUpsertRecord:
    ENDPOINTS = [
        ("510k", "K123456", {"k_number": "K123456", "device_name": "Widget", "applicant": "Acme"}),
        ("classification", "ABC", {"product_code": "ABC", "device_class": "2"}),
        ("maude", "EV001", {"event_key": "EV001", "event_type": "malfunction"}),
        ("recalls", "Z-0001-2024", {"recall_number": "Z-0001-2024", "recalling_firm": "FirmX"}),
        ("pma", "P240001", {"pma_number": "P240001", "device_name": "Heart Valve"}),
        ("udi", "DI123", {"di": "DI123", "brand_name": "UDI Device"}),
        ("enforcement", "Z-0002-2024", {"recall_number": "Z-0002-2024", "status": "Ongoing"}),
    ]

    @pytest.mark.parametrize("endpoint,record_id,data", ENDPOINTS)
    def test_upsert_succeeds(self, db, pool_mock, endpoint, record_id, data):
        conn, cur = _make_conn_mock()
        pool_mock.getconn.return_value = conn

        result = db.upsert_record(endpoint, record_id, data)

        assert result is True
        cur.execute.assert_called()  # at least SET LOCAL + INSERT

    def test_invalid_endpoint_raises(self, db):
        with pytest.raises(ValueError, match="Unknown endpoint"):
            db.upsert_record("unknown", "id1", {})

    def test_audit_session_variable_set(self, db, pool_mock):
        conn, cur = _make_conn_mock()
        pool_mock.getconn.return_value = conn

        db.upsert_record("510k", "K000001", {"device_name": "Test"})

        # First execute call should set app.user_id
        first_call = cur.execute.call_args_list[0]
        assert "app.user_id" in str(first_call)

    def test_checksum_stored(self, db, pool_mock):
        conn, cur = _make_conn_mock()
        pool_mock.getconn.return_value = conn

        data = {"k_number": "K999", "device_name": "Sensor"}
        expected_checksum = db.compute_checksum(data)

        db.upsert_record("510k", "K999", data)

        # checksum should appear in one of the execute args
        all_args = [str(c) for c in cur.execute.call_args_list]
        assert any(expected_checksum in a for a in all_args)


# ---------------------------------------------------------------------------
# 5. get_record
# ---------------------------------------------------------------------------


class TestGetRecord:
    def test_returns_record_when_found(self, db, pool_mock):
        row = {"k_number": "K111", "device_name": "Widget", "openfda_json": {}}
        conn, _ = _make_conn_mock(rows=[row])
        pool_mock.getconn.return_value = conn

        result = db.get_record("510k", "K111")

        assert result == row

    def test_returns_none_when_not_found(self, db, pool_mock):
        conn, cur = _make_conn_mock(rows=[])
        cur.fetchone.return_value = None
        pool_mock.getconn.return_value = conn

        result = db.get_record("510k", "K999")

        assert result is None

    def test_invalid_endpoint_raises(self, db):
        with pytest.raises(ValueError, match="Unknown endpoint"):
            db.get_record("unknown", "id")

    def test_uses_correct_pk_column_for_classification(self, db, pool_mock):
        conn, cur = _make_conn_mock(rows=[None])
        cur.fetchone.return_value = None
        pool_mock.getconn.return_value = conn

        db.get_record("classification", "ABC")

        # The SQL should reference product_code
        sql_str = str(cur.execute.call_args)
        assert "product_code" in sql_str


# ---------------------------------------------------------------------------
# 6. query_records
# ---------------------------------------------------------------------------


class TestQueryRecords:
    def test_returns_empty_list_no_results(self, db, pool_mock):
        conn, _ = _make_conn_mock(rows=[])
        pool_mock.getconn.return_value = conn

        result = db.query_records("510k")

        assert result == []

    def test_returns_list_of_dicts(self, db, pool_mock):
        rows = [
            {"k_number": "K001", "device_name": "A"},
            {"k_number": "K002", "device_name": "B"},
        ]
        conn, cur = _make_conn_mock(rows=rows)
        cur.fetchall.return_value = rows
        pool_mock.getconn.return_value = conn

        result = db.query_records("510k")

        assert len(result) == 2
        assert result[0]["k_number"] == "K001"

    def test_passes_limit_and_offset(self, db, pool_mock):
        conn, cur = _make_conn_mock(rows=[])
        cur.fetchall.return_value = []
        pool_mock.getconn.return_value = conn

        db.query_records("510k", limit=25, offset=50)

        call_args_str = str(cur.execute.call_args)
        assert "25" in call_args_str
        assert "50" in call_args_str

    def test_invalid_endpoint_raises(self, db):
        with pytest.raises(ValueError, match="Unknown endpoint"):
            db.query_records("unknown")

    def test_column_filter_applied(self, db, pool_mock):
        conn, cur = _make_conn_mock(rows=[])
        cur.fetchall.return_value = []
        pool_mock.getconn.return_value = conn

        db.query_records("510k", filters={"device_name": "Widget"})

        call_str = str(cur.execute.call_args)
        assert "Widget" in call_str

    def test_jsonb_filter_applied(self, db, pool_mock):
        conn, cur = _make_conn_mock(rows=[])
        cur.fetchall.return_value = []
        pool_mock.getconn.return_value = conn

        db.query_records("510k", filters={"openfda.regulation_number": "870.3610"})

        call_str = str(cur.execute.call_args)
        assert "870.3610" in call_str


# ---------------------------------------------------------------------------
# 7. is_stale
# ---------------------------------------------------------------------------


class TestIsStale:
    def test_returns_true_when_record_missing(self, db, pool_mock):
        conn, cur = _make_conn_mock()
        cur.fetchone.return_value = None
        pool_mock.getconn.return_value = conn

        assert db.is_stale("510k", "K_MISSING") is True

    def test_returns_true_when_cached_at_missing(self, db, pool_mock):
        conn, _ = _make_conn_mock(rows=[{"k_number": "K1", "cached_at": None}])
        pool_mock.getconn.return_value = conn

        assert db.is_stale("510k", "K1", ttl_hours=168) is True

    def test_fresh_record_is_not_stale(self, db, pool_mock):
        now = datetime.now()
        conn, _ = _make_conn_mock(rows=[{"k_number": "K1", "cached_at": now}])
        pool_mock.getconn.return_value = conn

        assert db.is_stale("510k", "K1", ttl_hours=168) is False

    def test_old_record_is_stale(self, db, pool_mock):
        old_time = datetime.now() - timedelta(hours=200)
        conn, _ = _make_conn_mock(rows=[{"k_number": "K1", "cached_at": old_time}])
        pool_mock.getconn.return_value = conn

        assert db.is_stale("510k", "K1", ttl_hours=168) is True

    def test_fetches_ttl_from_db_when_not_provided(self, db, pool_mock):
        now = datetime.now()
        conn = MagicMock()

        # First cursor call: get_record (returns fresh record)
        cur1 = MagicMock()
        cur1.fetchone.return_value = {"k_number": "K1", "cached_at": now}
        cur1.__enter__ = lambda s: s
        cur1.__exit__ = MagicMock(return_value=False)

        # Second cursor call: SELECT ttl_hours FROM refresh_metadata
        cur2 = MagicMock()
        cur2.fetchone.return_value = (168,)
        cur2.__enter__ = lambda s: s
        cur2.__exit__ = MagicMock(return_value=False)

        conn.cursor.side_effect = [cur1, cur2]
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        pool_mock.getconn.return_value = conn

        result = db.is_stale("510k", "K1")  # no ttl_hours argument
        assert result is False


# ---------------------------------------------------------------------------
# 8. get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    def test_returns_dict_with_counts(self, db, pool_mock):
        conn = MagicMock()
        cur = MagicMock()

        # Return count=0 for each endpoint, then empty for metadata/audit/size
        cur.fetchone.side_effect = [
            {"count": 0},  # 510k
            {"count": 0},  # classification
            {"count": 0},  # maude
            {"count": 0},  # recalls
            {"count": 0},  # pma
            {"count": 0},  # udi
            {"count": 0},  # enforcement
            {"count": 5},  # audit_log
            {"size": "1 MB"},  # database size
        ]
        cur.fetchall.return_value = []  # refresh_metadata
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)

        conn.cursor.return_value = cur
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        pool_mock.getconn.return_value = conn

        stats = db.get_stats()

        assert "510k_count" in stats
        assert "audit_events" in stats
        assert "database_size" in stats

    def test_includes_all_endpoints(self, db, pool_mock):
        conn = MagicMock()
        cur = MagicMock()

        cur.fetchone.return_value = {"count": 0, "size": "1 MB"}
        cur.fetchall.return_value = []
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = cur
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        pool_mock.getconn.return_value = conn

        stats = db.get_stats()

        for endpoint in db.ENDPOINT_TABLES:
            assert f"{endpoint}_count" in stats


# ---------------------------------------------------------------------------
# 9. close
# ---------------------------------------------------------------------------


class TestClose:
    def test_closes_pool(self, db, pool_mock):
        db.close()
        pool_mock.closeall.assert_called_once()

    def test_close_when_pool_none_is_safe(self, db):
        db.pool = None
        db.close()  # should not raise
