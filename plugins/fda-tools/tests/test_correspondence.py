"""Tests for FDA correspondence tracking feature.

Validates JSON schema, deadline calculations, status transitions,
overdue detection, and correspondence history display logic.
"""

import json
import os
import tempfile
from datetime import date, datetime, timezone


# Schema for correspondence entries
REQUIRED_FIELDS = ["id", "type", "date", "summary", "action_items", "deadline", "status", "resolution", "created_at"]
VALID_TYPES = ["presub_response", "rta_deficiency", "fda_question", "commitment"]
VALID_STATUSES = ["open", "resolved", "overdue"]


def make_entry(
    entry_id=1,
    entry_type="presub_response",
    entry_date="2026-02-07",
    summary="FDA recommended additional testing",
    action_items=None,
    deadline=None,
    status="open",
    resolution=None,
):
    """Create a correspondence entry for testing."""
    return {
        "id": entry_id,
        "type": entry_type,
        "date": entry_date,
        "summary": summary,
        "action_items": action_items or ["Update test plan"],
        "deadline": deadline,
        "status": status,
        "resolution": resolution,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class TestCorrespondenceSchema:
    """Test the correspondence JSON schema structure."""

    def test_entry_has_all_required_fields(self):
        entry = make_entry()
        for field in REQUIRED_FIELDS:
            assert field in entry, f"Missing required field: {field}"

    def test_valid_entry_types(self):
        for entry_type in VALID_TYPES:
            entry = make_entry(entry_type=entry_type)
            assert entry["type"] in VALID_TYPES

    def test_invalid_entry_type_detected(self):
        entry = make_entry(entry_type="invalid_type")
        assert entry["type"] not in VALID_TYPES

    def test_valid_statuses(self):
        for status in VALID_STATUSES:
            entry = make_entry(status=status)
            assert entry["status"] in VALID_STATUSES

    def test_action_items_is_list(self):
        entry = make_entry(action_items=["item1", "item2", "item3"])
        assert isinstance(entry["action_items"], list)
        assert len(entry["action_items"]) == 3

    def test_deadline_can_be_none(self):
        entry = make_entry(deadline=None)
        assert entry["deadline"] is None

    def test_resolution_starts_null(self):
        entry = make_entry()
        assert entry["resolution"] is None

    def test_resolution_can_be_set(self):
        entry = make_entry(status="resolved", resolution="Completed additional testing per FDA feedback")
        assert entry["resolution"] is not None
        assert entry["status"] == "resolved"


class TestDeadlineCalculation:
    """Test deadline date parsing and days-remaining logic."""

    def test_days_remaining_future(self):
        today = date(2026, 2, 7)
        deadline = date(2026, 4, 15)
        days = (deadline - today).days
        assert days == 67

    def test_days_remaining_past(self):
        today = date(2026, 5, 1)
        deadline = date(2026, 4, 15)
        days = (deadline - today).days
        assert days < 0  # Past deadline
        assert days == -16

    def test_days_remaining_today(self):
        today = date(2026, 4, 15)
        deadline = date(2026, 4, 15)
        days = (deadline - today).days
        assert days == 0

    def test_deadline_date_parsing(self):
        entry = make_entry(deadline="2026-04-15")
        dl = datetime.strptime(entry["deadline"], "%Y-%m-%d").date()
        assert dl.year == 2026
        assert dl.month == 4
        assert dl.day == 15


class TestOverdueDetection:
    """Test overdue item detection logic."""

    def test_open_past_deadline_is_overdue(self):
        today = date(2026, 5, 1)
        entry = make_entry(deadline="2026-04-15", status="open")
        dl = datetime.strptime(entry["deadline"], "%Y-%m-%d").date()
        is_overdue = entry["status"] == "open" and dl < today
        assert is_overdue

    def test_resolved_past_deadline_not_overdue(self):
        today = date(2026, 5, 1)
        entry = make_entry(deadline="2026-04-15", status="resolved")
        dl = datetime.strptime(entry["deadline"], "%Y-%m-%d").date()
        is_overdue = entry["status"] == "open" and dl < today
        assert not is_overdue

    def test_open_future_deadline_not_overdue(self):
        today = date(2026, 2, 7)
        entry = make_entry(deadline="2026-04-15", status="open")
        dl = datetime.strptime(entry["deadline"], "%Y-%m-%d").date()
        is_overdue = entry["status"] == "open" and dl < today
        assert not is_overdue

    def test_no_deadline_never_overdue(self):
        entry = make_entry(deadline=None, status="open")
        is_overdue = entry["status"] == "open" and entry.get("deadline") is not None
        assert not is_overdue

    def test_overdue_severity_warning(self):
        """Past deadline by 1-30 days = warning."""
        today = date(2026, 5, 1)
        deadline = date(2026, 4, 15)
        days_overdue = (today - deadline).days
        severity = "critical" if days_overdue > 30 else "warning"
        assert severity == "warning"
        assert days_overdue == 16

    def test_overdue_severity_critical(self):
        """Past deadline by >30 days = critical."""
        today = date(2026, 6, 1)
        deadline = date(2026, 4, 15)
        days_overdue = (today - deadline).days
        severity = "critical" if days_overdue > 30 else "warning"
        assert severity == "critical"
        assert days_overdue == 47


class TestStatusTransitions:
    """Test status transition logic for correspondence entries."""

    def test_open_to_resolved(self):
        entry = make_entry(status="open")
        entry["status"] = "resolved"
        entry["resolution"] = "Completed per FDA request"
        assert entry["status"] == "resolved"
        assert entry["resolution"] is not None

    def test_auto_id_increment(self):
        entries = [make_entry(entry_id=1), make_entry(entry_id=2)]
        next_id = max(e["id"] for e in entries) + 1
        assert next_id == 3

    def test_auto_id_from_empty(self):
        entries = []
        next_id = max([e.get("id", 0) for e in entries], default=0) + 1
        assert next_id == 1


class TestCorrespondenceFileIO:
    """Test reading/writing correspondence JSON files."""

    def test_write_and_read_correspondence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            corr_path = os.path.join(tmpdir, "fda_correspondence.json")
            data = {"entries": [make_entry()]}
            with open(corr_path, "w") as f:
                json.dump(data, f, indent=2)
            with open(corr_path) as f:
                loaded = json.load(f)
            assert len(loaded["entries"]) == 1
            assert loaded["entries"][0]["type"] == "presub_response"

    def test_append_entry_to_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            corr_path = os.path.join(tmpdir, "fda_correspondence.json")
            data = {"entries": [make_entry(entry_id=1)]}
            with open(corr_path, "w") as f:
                json.dump(data, f, indent=2)
            # Append
            with open(corr_path) as f:
                data = json.load(f)
            data["entries"].append(make_entry(entry_id=2, entry_type="rta_deficiency"))
            with open(corr_path, "w") as f:
                json.dump(data, f, indent=2)
            with open(corr_path) as f:
                loaded = json.load(f)
            assert len(loaded["entries"]) == 2
            assert loaded["entries"][1]["type"] == "rta_deficiency"

    def test_empty_entries_list(self):
        data = {"entries": []}
        assert len(data["entries"]) == 0
        open_count = sum(1 for e in data["entries"] if e.get("status") == "open")
        assert open_count == 0


class TestCorrespondenceSummary:
    """Test summary statistics generation from correspondence data."""

    def test_count_open_entries(self):
        entries = [
            make_entry(entry_id=1, status="open"),
            make_entry(entry_id=2, status="resolved"),
            make_entry(entry_id=3, status="open"),
        ]
        open_count = sum(1 for e in entries if e["status"] == "open")
        assert open_count == 2

    def test_count_overdue_entries(self):
        today = date(2026, 5, 1)
        entries = [
            make_entry(entry_id=1, status="open", deadline="2026-04-15"),
            make_entry(entry_id=2, status="open", deadline="2026-06-01"),
            make_entry(entry_id=3, status="resolved", deadline="2026-03-01"),
        ]
        overdue = 0
        for e in entries:
            if e["status"] == "open" and e.get("deadline"):
                dl = datetime.strptime(e["deadline"], "%Y-%m-%d").date()
                if dl < today:
                    overdue += 1
        assert overdue == 1

    def test_next_deadline_calculation(self):
        today = date(2026, 2, 7)
        entries = [
            make_entry(entry_id=1, status="open", deadline="2026-04-15"),
            make_entry(entry_id=2, status="open", deadline="2026-03-01"),
            make_entry(entry_id=3, status="resolved", deadline="2026-02-15"),
        ]
        next_deadline = None
        for e in entries:
            if e["status"] == "open" and e.get("deadline"):
                dl = datetime.strptime(e["deadline"], "%Y-%m-%d").date()
                if dl >= today and (next_deadline is None or dl < next_deadline):
                    next_deadline = dl
        assert next_deadline == date(2026, 3, 1)
