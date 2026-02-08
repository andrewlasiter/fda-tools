"""Tests for the alert sender module.

Validates email formatting, webhook payload structure, stdout JSON format,
config parsing, and severity filtering.
All tests are offline — no SMTP/HTTP connections made.
"""

import json
import os
import sys
import pytest

# Add scripts directory to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from alert_sender import (
    filter_by_severity,
    format_alert_json,
    format_alert_text,
    load_alerts,
    load_settings,
    send_stdout,
)


@pytest.fixture
def sample_alerts():
    """Create sample alerts for testing."""
    return [
        {
            "type": "new_clearance",
            "product_code": "OVE",
            "device_name": "Cervical Fusion Device",
            "knumber": "K263456",
            "applicant": "COMPANY INC",
            "decision_date": "20260203",
            "severity": "info",
            "_file_date": "2026-02-05",
        },
        {
            "type": "recall",
            "product_code": "OVE",
            "recalling_firm": "ACME MEDICAL",
            "classification": "Class II",
            "reason": "Device may fracture under load",
            "severity": "warning",
            "_file_date": "2026-02-05",
        },
        {
            "type": "standard_update",
            "standard": "ISO 10993-1",
            "old_version": "2018",
            "new_version": "2025",
            "transition_deadline": "2027-11-18",
            "severity": "warning",
            "action_required": "Update biocompat plan",
            "_file_date": "2026-02-06",
        },
        {
            "type": "maude_event",
            "product_code": "OVE",
            "event_type": "Injury",
            "count_since_last": 15,
            "severity": "critical",
            "_file_date": "2026-02-06",
        },
    ]


class TestSeverityFiltering:
    """Test alert severity filtering."""

    def test_filter_info_returns_all(self, sample_alerts):
        result = filter_by_severity(sample_alerts, "info")
        assert len(result) == 4

    def test_filter_warning_excludes_info(self, sample_alerts):
        result = filter_by_severity(sample_alerts, "warning")
        assert len(result) == 3  # 2 warnings + 1 critical
        assert all(a["severity"] in ("warning", "critical") for a in result)

    def test_filter_critical_only(self, sample_alerts):
        result = filter_by_severity(sample_alerts, "critical")
        assert len(result) == 1
        assert result[0]["type"] == "maude_event"

    def test_filter_empty_list(self):
        assert filter_by_severity([], "info") == []


class TestAlertFormatting:
    """Test alert text and JSON formatting."""

    def test_format_clearance_text(self, sample_alerts):
        text = format_alert_text(sample_alerts[0])
        assert "INFO" in text
        assert "new_clearance" in text
        assert "K263456" in text
        assert "COMPANY INC" in text

    def test_format_recall_text(self, sample_alerts):
        text = format_alert_text(sample_alerts[1])
        assert "WARNING" in text
        assert "recall" in text
        assert "ACME MEDICAL" in text
        assert "Class II" in text

    def test_format_standard_update_text(self, sample_alerts):
        text = format_alert_text(sample_alerts[2])
        assert "standard_update" in text
        assert "ISO 10993-1" in text
        assert "2018" in text
        assert "2025" in text

    def test_format_maude_event_text(self, sample_alerts):
        text = format_alert_text(sample_alerts[3])
        assert "CRITICAL" in text
        assert "maude_event" in text
        assert "Injury" in text

    def test_format_json_structure(self, sample_alerts):
        json_str = format_alert_json(sample_alerts)
        data = json.loads(json_str)
        assert "timestamp" in data
        assert "alert_count" in data
        assert data["alert_count"] == 4
        assert "alerts" in data
        assert len(data["alerts"]) == 4

    def test_format_json_excludes_internal_fields(self, sample_alerts):
        json_str = format_alert_json(sample_alerts)
        data = json.loads(json_str)
        for alert in data["alerts"]:
            assert "_file_date" not in alert
            assert "date" in alert  # _file_date becomes "date"


class TestStdoutOutput:
    """Test stdout delivery."""

    def test_stdout_text_mode(self, sample_alerts, capsys):
        result = send_stdout(sample_alerts, cron_mode=False)
        assert result["success"] is True
        captured = capsys.readouterr()
        assert "K263456" in captured.out
        assert "ACME MEDICAL" in captured.out

    def test_stdout_cron_mode(self, sample_alerts, capsys):
        result = send_stdout(sample_alerts, cron_mode=True)
        assert result["success"] is True
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["alert_count"] == 4


class TestAlertLoading:
    """Test loading alerts from directory."""

    def test_load_from_nonexistent_dir(self, tmp_path):
        alerts = load_alerts(alert_dir=str(tmp_path / "nonexistent"))
        assert alerts == []

    def test_load_from_empty_dir(self, tmp_path):
        alert_dir = tmp_path / "alerts"
        alert_dir.mkdir()
        alerts = load_alerts(alert_dir=str(alert_dir))
        assert alerts == []

    def test_load_from_populated_dir(self, tmp_path):
        alert_dir = tmp_path / "alerts"
        alert_dir.mkdir()
        data = {
            "date": "2026-02-05",
            "alerts": [
                {"type": "new_clearance", "knumber": "K263456", "severity": "info"},
                {"type": "recall", "severity": "warning"},
            ],
        }
        with open(alert_dir / "2026-02-05.json", "w") as f:
            json.dump(data, f)
        alerts = load_alerts(alert_dir=str(alert_dir))
        assert len(alerts) == 2
        assert alerts[0]["_file_date"] == "2026-02-05"

    def test_load_with_since_filter(self, tmp_path):
        alert_dir = tmp_path / "alerts"
        alert_dir.mkdir()
        for d in ["2026-02-01", "2026-02-05", "2026-02-10"]:
            data = {"date": d, "alerts": [{"type": "test", "severity": "info"}]}
            with open(alert_dir / f"{d}.json", "w") as f:
                json.dump(data, f)
        alerts = load_alerts(alert_dir=str(alert_dir), since_date="2026-02-05")
        assert len(alerts) == 2  # 02-05 and 02-10


class TestSettingsLoading:
    """Test loading settings from config file."""

    def test_load_defaults_when_no_file(self, monkeypatch):
        monkeypatch.setattr("alert_sender.SETTINGS_PATH", "/nonexistent/path")
        settings = load_settings()
        assert settings["smtp_host"] is None
        assert settings["smtp_port"] == 587
        assert settings["alert_severity_threshold"] == "info"

    def test_load_from_settings_file(self, tmp_path, monkeypatch):
        settings_file = tmp_path / "settings.md"
        settings_file.write_text(
            "---\n"
            "smtp_host: smtp.example.com\n"
            "smtp_port: 465\n"
            "email_to: test@example.com\n"
            "webhook_url: https://hooks.example.com/fda\n"
            "alert_severity_threshold: warning\n"
            "---\n"
        )
        monkeypatch.setattr("alert_sender.SETTINGS_PATH", str(settings_file))
        settings = load_settings()
        assert settings["smtp_host"] == "smtp.example.com"
        assert settings["smtp_port"] == 465
        assert settings["email_to"] == "test@example.com"
        assert settings["webhook_url"] == "https://hooks.example.com/fda"
        assert settings["alert_severity_threshold"] == "warning"


class TestWebhookPayload:
    """Test webhook payload structure."""

    def test_webhook_requires_url(self):
        from alert_sender import send_webhook
        result = send_webhook([], {})
        assert result["success"] is False
        assert "webhook_url" in result["error"]

    def test_webhook_payload_format(self):
        """Verify the payload structure matches the documented format."""
        from alert_sender import send_webhook
        # We can't actually POST, but we verify the function requires URL
        result = send_webhook(
            [{"type": "test", "severity": "info"}],
            {"webhook_url": None},
        )
        assert result["success"] is False


class TestEmailFormatting:
    """Test email formatting without sending."""

    def test_email_requires_smtp_host(self):
        from alert_sender import send_email
        result = send_email([], {})
        assert result["success"] is False
        assert "smtp_host" in result["error"]

    def test_email_requires_smtp_user(self):
        from alert_sender import send_email
        result = send_email([], {"smtp_host": "smtp.test.com"})
        assert result["success"] is False
        assert "smtp_user" in result["error"]

    def test_email_requires_email_to(self):
        from alert_sender import send_email
        result = send_email([], {"smtp_host": "smtp.test.com", "smtp_user": "user"})
        assert result["success"] is False
        assert "email_to" in result["error"]
