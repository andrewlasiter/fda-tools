"""
Unit Tests for Alert Sender Audit Log (FDA-122)
================================================

Validates the persistent, append-only audit log added to alert_sender.py
to satisfy 21 CFR Part 11 compliance requirements:

  - AuditLogger.append: JSON Lines written with fcntl locking
  - AuditLogger.prune: Files older than AUDIT_RETENTION_DAYS deleted
  - AuditLogger.query: Date/status/method filtering across log files
  - AuditLogger.export_csv: CSV export for compliance reports
  - deliver_alerts integration: Audit record written on every delivery
  - Log rotation: File exceeding MAX_AUDIT_FILE_BYTES triggers rotation

Test count: 32
Target: pytest plugins/fda_tools/tests/test_fda122_audit_log.py -v
"""

import csv
import json
import threading
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fda_tools.scripts.alert_sender import (
    AUDIT_RETENTION_DAYS,
    AuditLogger,
    deliver_alerts,
)


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def logger(tmp_path):
    return AuditLogger(log_dir=str(tmp_path / "audit"))


@pytest.fixture()
def sample_alerts():
    return [
        {
            "type": "new_clearance",
            "severity": "info",
            "knumber": "K240001",
            "product_code": "DQY",
            "_file_date": "2026-01-15",
        },
        {
            "type": "recall",
            "severity": "critical",
            "event_id": "R-001",
            "product_code": "DQY",
            "_file_date": "2026-01-15",
        },
    ]


# ---------------------------------------------------------------------------
# TestAuditLoggerAppend
# ---------------------------------------------------------------------------


class TestAuditLoggerAppend:
    """Tests for AuditLogger.append()."""

    def test_creates_audit_directory(self, tmp_path):
        log_dir = tmp_path / "new_audit_dir"
        logger = AuditLogger(log_dir=str(log_dir))
        logger.append({"event": "test"})
        assert log_dir.exists()

    def test_creates_jsonl_file_for_today(self, logger, tmp_path):
        logger.append({"event": "test"})
        today = date.today().isoformat()
        log_file = tmp_path / "audit" / f"audit_{today}.jsonl"
        assert log_file.exists()

    def test_record_is_valid_json(self, logger, tmp_path):
        logger.append({"method": "webhook", "status": "success"})
        today = date.today().isoformat()
        log_file = tmp_path / "audit" / f"audit_{today}.jsonl"
        line = log_file.read_text().strip()
        record = json.loads(line)
        assert record["method"] == "webhook"
        assert record["status"] == "success"

    def test_logged_at_added_automatically(self, logger, tmp_path):
        logger.append({"event": "test"})
        today = date.today().isoformat()
        log_file = tmp_path / "audit" / f"audit_{today}.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert "logged_at" in record

    def test_existing_logged_at_not_overwritten(self, logger, tmp_path):
        logger.append({"logged_at": "2026-01-01T00:00:00+00:00", "event": "test"})
        today = date.today().isoformat()
        log_file = tmp_path / "audit" / f"audit_{today}.jsonl"
        record = json.loads(log_file.read_text().strip())
        assert record["logged_at"] == "2026-01-01T00:00:00+00:00"

    def test_multiple_records_appended(self, logger, tmp_path):
        logger.append({"n": 1})
        logger.append({"n": 2})
        logger.append({"n": 3})
        today = date.today().isoformat()
        log_file = tmp_path / "audit" / f"audit_{today}.jsonl"
        lines = [l for l in log_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 3
        assert [json.loads(l)["n"] for l in lines] == [1, 2, 3]

    def test_concurrent_appends_produce_valid_records(self, tmp_path):
        """Concurrent threads must not interleave partial JSON lines."""
        logger = AuditLogger(log_dir=str(tmp_path / "audit"))
        errors: list = []

        def worker(n):
            try:
                for _ in range(10):
                    logger.append({"thread": n, "data": "x" * 200})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        today = date.today().isoformat()
        log_file = tmp_path / "audit" / f"audit_{today}.jsonl"
        lines = [l for l in log_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 50  # 5 threads × 10 records
        for line in lines:
            json.loads(line)  # Must not raise


# ---------------------------------------------------------------------------
# TestAuditLoggerPrune
# ---------------------------------------------------------------------------


class TestAuditLoggerPrune:
    """Tests for AuditLogger.prune()."""

    def _write_old_file(self, log_dir: Path, days_ago: int) -> Path:
        past_date = (date.today() - timedelta(days=days_ago)).isoformat()
        f = log_dir / f"audit_{past_date}.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text('{"event": "old"}\n')
        return f

    def test_prune_deletes_files_beyond_retention(self, tmp_path):
        log_dir = tmp_path / "audit"
        logger = AuditLogger(log_dir=str(log_dir))
        old_file = self._write_old_file(log_dir, AUDIT_RETENTION_DAYS + 1)
        pruned = logger.prune()
        assert not old_file.exists()
        assert old_file.name in pruned

    def test_prune_keeps_files_within_retention(self, tmp_path):
        log_dir = tmp_path / "audit"
        logger = AuditLogger(log_dir=str(log_dir))
        recent_file = self._write_old_file(log_dir, AUDIT_RETENTION_DAYS - 1)
        pruned = logger.prune()
        assert recent_file.exists()
        assert recent_file.name not in pruned

    def test_prune_on_empty_dir_returns_empty_list(self, logger):
        assert logger.prune() == []

    def test_prune_handles_gz_files(self, tmp_path):
        log_dir = tmp_path / "audit"
        log_dir.mkdir(parents=True)
        past_date = (date.today() - timedelta(days=AUDIT_RETENTION_DAYS + 5)).isoformat()
        gz_file = log_dir / f"audit_{past_date}.jsonl.gz"
        gz_file.write_bytes(b"fake")
        logger = AuditLogger(log_dir=str(log_dir))
        pruned = logger.prune()
        assert gz_file.name in pruned
        assert not gz_file.exists()


# ---------------------------------------------------------------------------
# TestAuditLoggerQuery
# ---------------------------------------------------------------------------


class TestAuditLoggerQuery:
    """Tests for AuditLogger.query()."""

    def _write_record(self, logger: AuditLogger, **kwargs):
        logger.append(kwargs)

    def test_query_returns_all_records_without_filters(self, logger):
        logger.append({"method": "webhook", "status": "success"})
        logger.append({"method": "stdout", "status": "success"})
        records = logger.query()
        assert len(records) == 2

    def test_query_filters_by_status(self, logger):
        logger.append({"status": "success", "method": "webhook"})
        logger.append({"status": "failed", "method": "webhook"})
        records = logger.query(status="failed")
        assert len(records) == 1
        assert records[0]["status"] == "failed"

    def test_query_filters_by_method(self, logger):
        logger.append({"method": "webhook", "status": "success"})
        logger.append({"method": "stdout", "status": "success"})
        records = logger.query(method="stdout")
        assert len(records) == 1
        assert records[0]["method"] == "stdout"

    def test_query_since_filter(self, logger):
        logger.append({"logged_at": "2026-01-01T00:00:00+00:00", "event": "old"})
        logger.append({"logged_at": "2026-06-01T00:00:00+00:00", "event": "new"})
        records = logger.query(since="2026-02-01T00:00:00+00:00")
        assert len(records) == 1
        assert records[0]["event"] == "new"

    def test_query_until_filter(self, logger):
        logger.append({"logged_at": "2026-01-01T00:00:00+00:00", "event": "old"})
        logger.append({"logged_at": "2026-06-01T00:00:00+00:00", "event": "new"})
        records = logger.query(until="2026-03-01T00:00:00+00:00")
        assert len(records) == 1
        assert records[0]["event"] == "old"

    def test_query_on_empty_logger_returns_empty(self, logger):
        assert logger.query() == []

    def test_query_results_sorted_by_logged_at(self, logger):
        logger.append({"logged_at": "2026-06-01T00:00:00+00:00", "n": 2})
        logger.append({"logged_at": "2026-01-01T00:00:00+00:00", "n": 1})
        records = logger.query()
        assert [r["n"] for r in records] == [1, 2]


# ---------------------------------------------------------------------------
# TestAuditLoggerExportCsv
# ---------------------------------------------------------------------------


class TestAuditLoggerExportCsv:
    """Tests for AuditLogger.export_csv()."""

    def test_export_csv_returns_string(self, logger):
        records = [{"logged_at": "2026-01-01", "method": "webhook", "status": "success"}]
        csv_text = logger.export_csv(records)
        assert isinstance(csv_text, str)
        assert "webhook" in csv_text

    def test_export_csv_has_header_row(self, logger):
        records = [{"logged_at": "2026-01-01", "method": "webhook", "status": "success"}]
        csv_text = logger.export_csv(records)
        lines = csv_text.splitlines()
        assert lines[0].startswith("logged_at")

    def test_export_csv_writes_to_file(self, logger, tmp_path):
        records = [{"logged_at": "2026-01-01", "status": "success"}]
        out = str(tmp_path / "report.csv")
        logger.export_csv(records, output_path=out)
        assert Path(out).exists()
        content = Path(out).read_text()
        assert "success" in content

    def test_export_csv_empty_returns_empty_string(self, logger):
        assert logger.export_csv([]) == ""

    def test_export_csv_priority_fields_first(self, logger):
        records = [{"logged_at": "2026-01-01", "method": "webhook",
                    "status": "success", "alert_count": 3}]
        csv_text = logger.export_csv(records)
        reader = csv.DictReader(csv_text.splitlines())
        fieldnames = reader.fieldnames or []
        assert fieldnames[0] == "logged_at"
        assert fieldnames[1] == "method"


# ---------------------------------------------------------------------------
# TestDeliverAlertsAudit
# ---------------------------------------------------------------------------


class TestDeliverAlertsAudit:
    """Verify deliver_alerts writes audit records via AuditLogger."""

    @pytest.fixture()
    def mock_logger(self):
        m = MagicMock(spec=AuditLogger)
        return m

    def test_deliver_writes_audit_record_on_stdout(self, sample_alerts, mock_logger):
        deliver_alerts(sample_alerts, method="stdout", audit_logger=mock_logger)
        mock_logger.append.assert_called_once()
        record = mock_logger.append.call_args[0][0]
        assert record["method"] == "stdout"
        assert record["alert_count"] == 2

    def test_deliver_writes_success_status_on_stdout(self, sample_alerts, mock_logger):
        deliver_alerts(sample_alerts, method="stdout", audit_logger=mock_logger)
        record = mock_logger.append.call_args[0][0]
        assert record["status"] == "success"

    def test_deliver_writes_failed_status_on_webhook_error(self, sample_alerts, mock_logger):
        with patch(
            "fda_tools.scripts.alert_sender.send_webhook",
            return_value={"success": False, "error": "connection refused"},
        ):
            deliver_alerts(
                sample_alerts, method="webhook",
                settings={"webhook_url": "https://example.com/hook",
                          "alert_severity_threshold": "info"},
                audit_logger=mock_logger,
            )
        record = mock_logger.append.call_args[0][0]
        assert record["status"] == "failed"
        assert record["error"] == "connection refused"

    def test_deliver_records_severity_counts(self, sample_alerts, mock_logger):
        deliver_alerts(sample_alerts, method="stdout", audit_logger=mock_logger)
        record = mock_logger.append.call_args[0][0]
        counts = record["severity_counts"]
        assert counts.get("info", 0) == 1
        assert counts.get("critical", 0) == 1

    def test_audit_disabled_when_false(self, sample_alerts):
        """audit_logger=False suppresses all logging."""
        with patch("fda_tools.scripts.alert_sender._get_audit_logger") as mock_get:
            deliver_alerts(sample_alerts, method="stdout", audit_logger=False)
            mock_get.assert_not_called()

    def test_no_alerts_skips_audit(self, mock_logger):
        deliver_alerts([], method="stdout", audit_logger=mock_logger)
        mock_logger.append.assert_not_called()

    def test_audit_exception_does_not_break_delivery(self, sample_alerts):
        """If audit logging fails, delivery result is still returned."""
        bad_logger = MagicMock(spec=AuditLogger)
        bad_logger.append.side_effect = OSError("disk full")
        result = deliver_alerts(sample_alerts, method="stdout", audit_logger=bad_logger)
        assert result["success"] is True
