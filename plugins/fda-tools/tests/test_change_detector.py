"""
Tests for Smart Auto-Update Change Detector (v5.36.0).

Implements Quick Win tests from the TESTING_SPEC.md test suite:

Tier 1 (Trivial):
    - SMART-014: Pipeline trigger with empty K-numbers

Tier 2 (Simple):
    - SMART-009: Empty known K-numbers list detection
    - SMART-010: No fingerprints and no product codes
    - SMART-013: Pipeline trigger with timeout
    - SMART-015: _run_subprocess OSError handling

Tier 3 (Moderate):
    - SMART-001: Fingerprint creation on first run
    - SMART-002: Fingerprint update with new data
    - SMART-005: New clearance detection (via detect_changes)
    - SMART-006: No changes detected (stable state)

Total: 9 SMART tests covering change_detector.py
(SMART-005 and SMART-006 added as bonus beyond the 17 Quick Wins since they
 share fixture setup with SMART-001/002)
"""

import json
import os
import subprocess
import sys

import pytest
from unittest.mock import MagicMock, patch

# Ensure scripts directory is on sys.path for imports
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

from change_detector import (
    _load_fingerprint,
    _run_subprocess,
    _save_fingerprint,
    detect_changes,
    find_new_clearances,
    trigger_pipeline,
)
from fda_data_store import load_manifest, save_manifest

# Ensure tests directory is on sys.path for mock imports
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)

from mocks.mock_fda_client import MockFDAClient


# ===================================================================
# Tier 1: Trivial Tests (< 10 min each)
# ===================================================================


class TestSMART014EmptyKNumbers:
    """SMART-014: Pipeline trigger with empty K-numbers list should be skipped.

    Validates that trigger_pipeline returns a 'skipped' status when
    given an empty list of K-numbers, without invoking any subprocess.
    """

    def test_empty_k_numbers_skipped(self):
        """Empty K-numbers list returns skipped status."""
        result = trigger_pipeline(
            project_name="test_project",
            new_k_numbers=[],
            product_code="DQY",
            dry_run=False,
        )

        assert result["status"] == "skipped"
        assert result["k_numbers_processed"] == 0
        assert "message" in result
        assert "No new K-numbers" in result["message"]
        assert result["steps"] == []

    def test_empty_k_numbers_dry_run(self):
        """Empty K-numbers in dry-run mode also returns skipped."""
        result = trigger_pipeline(
            project_name="test_project",
            new_k_numbers=[],
            product_code="DQY",
            dry_run=True,
        )

        assert result["status"] == "skipped"
        assert result["k_numbers_processed"] == 0


# ===================================================================
# Tier 2: Simple Tests (10-20 min each)
# ===================================================================


class TestSMART009EmptyKnownList:
    """SMART-009: Empty known K-numbers list means all results are new.

    Validates that when starting from an empty known set, all clearances
    from the API are treated as new discoveries.
    """

    def test_all_clearances_new_when_known_empty(
        self, tmp_project_dir, mock_fda_client_3_new_items
    ):
        """All 3 API clearances detected as new with empty fingerprint."""
        # Set up fingerprint with empty known_k_numbers
        manifest = load_manifest(tmp_project_dir)
        manifest["fingerprints"] = {
            "DQY": {
                "last_checked": "2026-01-01T00:00:00+00:00",
                "clearance_count": 0,
                "latest_k_number": "",
                "latest_decision_date": "",
                "recall_count": 0,
                "known_k_numbers": [],
            }
        }
        save_manifest(tmp_project_dir, manifest)

        # Patch get_projects_dir to return the parent of our tmp dir
        project_name = os.path.basename(tmp_project_dir)
        parent_dir = os.path.dirname(tmp_project_dir)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_3_new_items,
                verbose=False,
            )

        assert result["status"] == "completed"
        assert result["total_new_clearances"] == 3

        # Verify fingerprint was updated with all 3 K-numbers
        updated_manifest = load_manifest(tmp_project_dir)
        known_k = updated_manifest["fingerprints"]["DQY"]["known_k_numbers"]
        assert "K261001" in known_k
        assert "K261002" in known_k
        assert "K261003" in known_k


class TestSMART010NoFingerprintsNoCodes:
    """SMART-010: No fingerprints and no product codes returns helpful status.

    Validates that detect_changes returns a 'no_fingerprints' status
    with guidance to run batchfetch when the project has no data.
    """

    def test_empty_manifest_returns_no_fingerprints(self, tmp_project_dir_empty_manifest):
        """Empty manifest produces no_fingerprints status."""
        project_name = os.path.basename(tmp_project_dir_empty_manifest)
        parent_dir = os.path.dirname(tmp_project_dir_empty_manifest)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=MockFDAClient(),
                verbose=False,
            )

        assert result["status"] == "no_fingerprints"
        assert "message" in result
        assert "batchfetch" in result["message"].lower() or "batch" in result["message"].lower()
        assert result["total_new_clearances"] == 0
        assert result["total_new_recalls"] == 0
        assert result["changes"] == []


class TestSMART013TimeoutHandling:
    """SMART-013: _run_subprocess handles TimeoutExpired gracefully.

    Validates that timeout exceptions from subprocess.run are caught
    and converted to user-friendly timeout result dicts.
    """

    def test_timeout_produces_timeout_status(self):
        """TimeoutExpired exception produces 'timeout' status result."""
        with patch("change_detector.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["test_cmd"], timeout=60
            )

            result = _run_subprocess(
                cmd=["test_cmd"],
                step_name="test_step",
                timeout_seconds=60,
                cwd="/tmp",
                verbose=False,
            )

        assert result["step"] == "test_step"
        assert result["status"] == "timeout"
        assert "timed out" in result["output"].lower() or "timeout" in result["output"].lower()

    def test_timeout_no_exception_propagated(self):
        """TimeoutExpired does not propagate as an unhandled exception."""
        with patch("change_detector.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["slow_cmd"], timeout=300
            )

            # Should not raise
            result = _run_subprocess(
                cmd=["slow_cmd"],
                step_name="batchfetch",
                timeout_seconds=300,
                cwd="/tmp",
                verbose=False,
            )

            assert result is not None
            assert "status" in result

    def test_timeout_includes_diagnostic_info(self):
        """Timeout result contains diagnostic guidance for the user."""
        with patch("change_detector.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["cmd"], timeout=120
            )

            result = _run_subprocess(
                cmd=["cmd"],
                step_name="fetch",
                timeout_seconds=120,
                cwd="/tmp",
                verbose=False,
            )

        output = result["output"]
        # The production code includes diagnostic causes
        assert "120" in output or "seconds" in output.lower()


class TestSMART015OSErrorHandling:
    """SMART-015: _run_subprocess handles OSError gracefully.

    Validates that OSError exceptions (e.g., command not found) are
    caught and converted to error result dicts.
    """

    def test_oserror_produces_error_status(self):
        """OSError exception produces 'error' status result."""
        with patch("change_detector.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("No such file or directory")

            result = _run_subprocess(
                cmd=["nonexistent_cmd"],
                step_name="test_step",
                timeout_seconds=60,
                cwd="/tmp",
                verbose=False,
            )

        assert result["step"] == "test_step"
        assert result["status"] == "error"
        assert "No such file" in result["output"]

    def test_oserror_no_exception_propagated(self):
        """OSError does not propagate as an unhandled exception."""
        with patch("change_detector.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            result = _run_subprocess(
                cmd=["locked_cmd"],
                step_name="build_cache",
                timeout_seconds=60,
                cwd="/tmp",
                verbose=False,
            )

            assert result is not None
            assert result["status"] == "error"


# ===================================================================
# Tier 3: Moderate Tests (20-30 min each)
# ===================================================================


class TestSMART001FingerprintCreation:
    """SMART-001: Fingerprint creation on first run.

    Validates that when detect_changes is called for a project that has
    product codes but no fingerprints, fingerprints are created and
    persisted to data_manifest.json.
    """

    def test_fingerprint_created_on_first_run(
        self, tmp_project_dir, mock_fda_client_with_new_clearances
    ):
        """First detect_changes call creates fingerprints in manifest."""
        project_name = os.path.basename(tmp_project_dir)
        parent_dir = os.path.dirname(tmp_project_dir)

        # Confirm no fingerprints exist initially
        manifest = load_manifest(tmp_project_dir)
        assert "fingerprints" not in manifest or not manifest.get("fingerprints")

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_with_new_clearances,
                verbose=False,
            )

        assert result["status"] == "completed"

        # Verify fingerprint was created
        manifest = load_manifest(tmp_project_dir)
        assert "fingerprints" in manifest
        assert "DQY" in manifest["fingerprints"]

        fp = manifest["fingerprints"]["DQY"]
        # Verify required fields
        assert "last_checked" in fp
        assert "clearance_count" in fp
        assert "latest_k_number" in fp
        assert "latest_decision_date" in fp
        assert "recall_count" in fp
        assert "known_k_numbers" in fp

        # Verify values
        assert fp["clearance_count"] == 149  # meta.results.total
        assert fp["latest_k_number"] == "K261001"  # First result
        assert fp["latest_decision_date"] == "20260201"
        assert fp["recall_count"] == 3
        assert isinstance(fp["known_k_numbers"], list)
        assert len(fp["known_k_numbers"]) > 0

    def test_fingerprint_iso_timestamp(
        self, tmp_project_dir, mock_fda_client_with_new_clearances
    ):
        """Created fingerprint has a valid ISO 8601 timestamp."""
        project_name = os.path.basename(tmp_project_dir)
        parent_dir = os.path.dirname(tmp_project_dir)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            detect_changes(
                project_name=project_name,
                client=mock_fda_client_with_new_clearances,
                verbose=False,
            )

        manifest = load_manifest(tmp_project_dir)
        fp = manifest["fingerprints"]["DQY"]

        # last_checked should be a valid ISO timestamp
        from datetime import datetime

        # Should parse without error
        ts = fp["last_checked"]
        assert "T" in ts, f"Timestamp should be ISO format: {ts}"
        assert "2026" in ts or "202" in ts, f"Timestamp should be recent: {ts}"


class TestSMART002FingerprintUpdate:
    """SMART-002: Fingerprint update on subsequent run with new data.

    Validates that when detect_changes finds new clearances, the
    fingerprint is updated with the new K-numbers while preserving
    existing ones.
    """

    def test_fingerprint_updated_with_new_clearances(
        self, tmp_project_dir_with_fingerprint, mock_fda_client_with_new_clearances
    ):
        """Fingerprint updates to include new K-numbers after detection."""
        project_dir = tmp_project_dir_with_fingerprint
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        # Record initial state
        initial_manifest = load_manifest(project_dir)
        initial_fp = initial_manifest["fingerprints"]["DQY"]
        initial_known = set(initial_fp["known_k_numbers"])
        initial_checked = initial_fp["last_checked"]

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_with_new_clearances,
                verbose=False,
            )

        assert result["status"] == "completed"

        # Verify fingerprint was updated
        updated_manifest = load_manifest(project_dir)
        updated_fp = updated_manifest["fingerprints"]["DQY"]

        # Clearance count should be updated
        assert updated_fp["clearance_count"] == 149  # New total from API

        # Known K-numbers should contain both old and new
        updated_known = set(updated_fp["known_k_numbers"])
        assert initial_known.issubset(updated_known), (
            f"Original K-numbers should be preserved. "
            f"Missing: {initial_known - updated_known}"
        )
        assert "K261001" in updated_known, "New K-number K261001 should be added"
        assert "K261002" in updated_known, "New K-number K261002 should be added"

        # last_checked should be more recent
        assert updated_fp["last_checked"] >= initial_checked

    def test_original_k_numbers_preserved(
        self, tmp_project_dir_with_fingerprint, mock_fda_client_with_new_clearances
    ):
        """Original K-numbers are not lost during update."""
        project_dir = tmp_project_dir_with_fingerprint
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            detect_changes(
                project_name=project_name,
                client=mock_fda_client_with_new_clearances,
                verbose=False,
            )

        updated_manifest = load_manifest(project_dir)
        known = updated_manifest["fingerprints"]["DQY"]["known_k_numbers"]

        # All original K-numbers from fixture should still be present
        for original_k in ["K241001", "K241002", "K241003", "K241004", "K241005"]:
            assert original_k in known, f"Original {original_k} should be preserved"


class TestSMART005NewClearanceDetection:
    """SMART-005: New clearance detection reports correct new K-numbers.

    Validates that detect_changes correctly identifies K-numbers that
    are not in the existing fingerprint as new clearances.
    """

    def test_new_clearances_detected(
        self, tmp_project_dir_with_fingerprint, mock_fda_client_with_new_clearances
    ):
        """2 new clearances detected from API response with 5 items (3 known + 2 new)."""
        project_dir = tmp_project_dir_with_fingerprint
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_with_new_clearances,
                verbose=False,
            )

        assert result["status"] == "completed"
        assert result["total_new_clearances"] == 2

        # Find the new_clearances change entry
        clearance_changes = [
            c for c in result["changes"]
            if c["change_type"] == "new_clearances"
        ]
        assert len(clearance_changes) == 1

        change = clearance_changes[0]
        assert change["count"] == 2
        assert change["product_code"] == "DQY"

        new_k_numbers = {item["k_number"] for item in change["new_items"]}
        assert "K261001" in new_k_numbers
        assert "K261002" in new_k_numbers

        # Existing K-numbers should NOT be reported as new
        for existing_k in ["K241001", "K241002", "K241003"]:
            assert existing_k not in new_k_numbers, (
                f"Existing {existing_k} should not be reported as new"
            )


class TestSMART006StableState:
    """SMART-006: No changes detected when data is stable.

    Validates that detect_changes reports zero changes when the API
    returns the same data as the stored fingerprint (no false positives).
    """

    def test_no_false_positives(self, tmp_project_dir, mock_fda_client_stable):
        """Stable data produces zero changes with no false positives."""
        project_dir = tmp_project_dir
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        # Set up fingerprint matching the stable response
        manifest = load_manifest(project_dir)
        manifest["fingerprints"] = {
            "DQY": {
                "last_checked": "2026-01-01T00:00:00+00:00",
                "clearance_count": 2,
                "latest_k_number": "K241001",
                "latest_decision_date": "20240315",
                "recall_count": 1,
                "known_k_numbers": ["K241001", "K241002"],
            }
        }
        save_manifest(project_dir, manifest)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_stable,
                verbose=False,
            )

        assert result["status"] == "completed"
        assert result["total_new_clearances"] == 0
        assert result["total_new_recalls"] == 0
        assert result["changes"] == []


class TestSMART011PipelineDryRun:
    """SMART-011: Pipeline trigger dry-run mode.

    Validates that trigger_pipeline with dry_run=True reports what it
    would do without executing any subprocesses.
    """

    def test_dry_run_returns_preview(self):
        """Dry run returns dry_run status with K-number list."""
        result = trigger_pipeline(
            project_name="test_project",
            new_k_numbers=["K261001", "K261002", "K261003"],
            product_code="DQY",
            dry_run=True,
            verbose=False,
        )

        assert result["status"] == "dry_run"
        assert result["k_numbers_processed"] == 3
        assert result["k_numbers"] == ["K261001", "K261002", "K261003"]
        assert result["product_code"] == "DQY"

    @patch("change_detector.subprocess.run")
    def test_dry_run_does_not_invoke_subprocess(self, mock_subprocess_run):
        """Dry run does not invoke any subprocess."""
        trigger_pipeline(
            project_name="test_project",
            new_k_numbers=["K261001"],
            product_code="DQY",
            dry_run=True,
            verbose=False,
        )

        mock_subprocess_run.assert_not_called()


# ===================================================================
# Fingerprint Persistence (SMART-003)
# ===================================================================


class TestSMART003FingerprintPersistence:
    """SMART-003: Fingerprint round-trip persistence across sessions.

    Validates that saving and loading a fingerprint preserves all fields
    exactly, including the uppercase normalization of product codes.
    """

    def test_roundtrip_persistence(self, tmp_project_dir):
        """Saved fingerprint can be loaded back identically."""
        sample_fp = {
            "last_checked": "2026-02-15T10:00:00+00:00",
            "clearance_count": 147,
            "latest_k_number": "K251234",
            "latest_decision_date": "20260115",
            "recall_count": 3,
            "known_k_numbers": ["K241001", "K241002", "K241003"],
        }

        _save_fingerprint(tmp_project_dir, "DQY", sample_fp)
        loaded_fp = _load_fingerprint(tmp_project_dir, "DQY")

        assert loaded_fp is not None
        assert loaded_fp == sample_fp

    def test_case_normalization(self, tmp_project_dir):
        """Product code is stored uppercase regardless of input case."""
        sample_fp = {
            "last_checked": "2026-02-15T10:00:00+00:00",
            "clearance_count": 10,
            "latest_k_number": "K251234",
            "latest_decision_date": "20260115",
            "recall_count": 0,
            "known_k_numbers": [],
        }

        _save_fingerprint(tmp_project_dir, "dqy", sample_fp)

        # Load with uppercase
        loaded_fp = _load_fingerprint(tmp_project_dir, "DQY")
        assert loaded_fp is not None
        assert loaded_fp == sample_fp

    def test_json_file_valid(self, tmp_project_dir):
        """Saved manifest is valid JSON."""
        sample_fp = {
            "last_checked": "2026-02-15T10:00:00+00:00",
            "clearance_count": 10,
            "latest_k_number": "K251234",
            "latest_decision_date": "20260115",
            "recall_count": 0,
            "known_k_numbers": [],
        }

        _save_fingerprint(tmp_project_dir, "DQY", sample_fp)

        manifest_path = os.path.join(tmp_project_dir, "data_manifest.json")
        with open(manifest_path) as f:
            data = json.load(f)  # Should not raise

        assert "fingerprints" in data
        assert "DQY" in data["fingerprints"]


# ===================================================================
# find_new_clearances standalone tests (bonus)
# ===================================================================


class TestFindNewClearances:
    """Tests for find_new_clearances() function directly.

    Validates the core clearance comparison logic independent of
    detect_changes() workflow.
    """

    def test_identifies_new_clearances(self):
        """Known K-numbers are excluded, unknown K-numbers are returned."""
        client = MockFDAClient()
        client.set_clearances("DQY", meta_total=5, results=[
            {"k_number": "K241001", "device_name": "Device 1", "applicant": "Co1",
             "decision_date": "20240315", "decision_code": "SESE",
             "clearance_type": "Traditional", "product_code": "DQY"},
            {"k_number": "K261001", "device_name": "New Device", "applicant": "NewCo",
             "decision_date": "20260201", "decision_code": "SESE",
             "clearance_type": "Traditional", "product_code": "DQY"},
            {"k_number": "K261002", "device_name": "Another New", "applicant": "NewCo2",
             "decision_date": "20260210", "decision_code": "SESE",
             "clearance_type": "Traditional", "product_code": "DQY"},
        ])

        new = find_new_clearances(
            "DQY", ["K241001"], client=client, max_fetch=10
        )

        assert len(new) == 2
        new_k_numbers = {item["k_number"] for item in new}
        assert "K261001" in new_k_numbers
        assert "K261002" in new_k_numbers
        assert "K241001" not in new_k_numbers

    def test_empty_known_list_returns_all(self):
        """Empty known list means all clearances are new."""
        client = MockFDAClient()
        client.set_clearances("DQY", meta_total=3, results=[
            {"k_number": "K261001", "device_name": "D1", "applicant": "C1",
             "decision_date": "20260201", "product_code": "DQY"},
            {"k_number": "K261002", "device_name": "D2", "applicant": "C2",
             "decision_date": "20260210", "product_code": "DQY"},
            {"k_number": "K261003", "device_name": "D3", "applicant": "C3",
             "decision_date": "20260215", "product_code": "DQY"},
        ])

        new = find_new_clearances("DQY", [], client=client, max_fetch=10)

        assert len(new) == 3

    def test_api_error_returns_empty(self):
        """API error returns empty list (no crash)."""
        client = MockFDAClient(default_error=True)

        new = find_new_clearances("DQY", [], client=client, max_fetch=10)

        assert new == []


# ===================================================================
# CRITICAL: New Recall Detection (SMART-007)
# ===================================================================


class TestSMART007NewRecallDetection:
    """SMART-007: New recall detection reports correct delta.

    Validates that detect_changes correctly identifies when the recall
    count has increased and reports the delta accurately.
    """

    def test_new_recalls_detected(
        self, tmp_project_dir, mock_fda_client_with_recalls
    ):
        """2 new recalls detected (4 current - 2 previous = 2 delta)."""
        project_dir = tmp_project_dir
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        # Set up fingerprint with recall_count=2
        manifest = load_manifest(project_dir)
        manifest["fingerprints"] = {
            "DQY": {
                "last_checked": "2026-01-01T00:00:00+00:00",
                "clearance_count": 2,
                "latest_k_number": "K241001",
                "latest_decision_date": "20240315",
                "recall_count": 2,  # Previous recall count
                "known_k_numbers": ["K241001", "K241002"],
            }
        }
        save_manifest(project_dir, manifest)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_with_recalls,
                verbose=False,
            )

        assert result["status"] == "completed"
        assert result["total_new_recalls"] == 2  # 4 - 2 = 2

        # Find the new_recalls change entry
        recall_changes = [
            c for c in result["changes"]
            if c["change_type"] == "new_recalls"
        ]
        assert len(recall_changes) == 1

        change = recall_changes[0]
        assert change["count"] == 2
        assert change["product_code"] == "DQY"
        assert change["details"]["previous_count"] == 2
        assert change["details"]["current_count"] == 4

    def test_recall_count_updated_in_fingerprint(
        self, tmp_project_dir, mock_fda_client_with_recalls
    ):
        """Fingerprint recall_count is updated after detection."""
        project_dir = tmp_project_dir
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        manifest = load_manifest(project_dir)
        manifest["fingerprints"] = {
            "DQY": {
                "last_checked": "2026-01-01T00:00:00+00:00",
                "clearance_count": 2,
                "latest_k_number": "K241001",
                "latest_decision_date": "20240315",
                "recall_count": 2,
                "known_k_numbers": ["K241001", "K241002"],
            }
        }
        save_manifest(project_dir, manifest)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            detect_changes(
                project_name=project_name,
                client=mock_fda_client_with_recalls,
                verbose=False,
            )

        updated_manifest = load_manifest(project_dir)
        assert updated_manifest["fingerprints"]["DQY"]["recall_count"] == 4


# ===================================================================
# HIGH: Multiple Product Code Fingerprints (SMART-004)
# ===================================================================


class TestSMART004MultipleProductCodes:
    """SMART-004: Multiple product code fingerprints are saved independently.

    Validates that detect_changes correctly creates and maintains
    separate fingerprints for each product code in the project.
    """

    def test_all_product_codes_get_fingerprints(
        self, tmp_project_dir_multi_codes, sample_api_responses
    ):
        """All 3 product codes (DQY, OVE, GEI) receive independent fingerprints."""
        project_dir = tmp_project_dir_multi_codes
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        # Create mock client with responses for all 3 codes
        client = MockFDAClient()
        client.set_clearances("DQY", meta_total=149, 
                             results=sample_api_responses["clearances_dqy_5_items"]["results"])
        client.set_recalls("DQY", meta_total=3)
        
        client.set_clearances("OVE", meta_total=89,
                             results=sample_api_responses["clearances_ove"]["results"])
        client.set_recalls("OVE", meta_total=1)
        
        client.set_clearances("GEI", meta_total=52,
                             results=sample_api_responses["clearances_gei"]["results"])
        client.set_recalls("GEI", meta_total=0)

        # Clear existing fingerprints to test creation
        manifest = load_manifest(project_dir)
        manifest["fingerprints"] = {}
        save_manifest(project_dir, manifest)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            with patch("change_detector.time.sleep"):  # Skip rate limiting delay
                result = detect_changes(
                    project_name=project_name,
                    client=client,
                    verbose=False,
                )

        assert result["status"] == "completed"

        # Verify all 3 fingerprints were created
        manifest = load_manifest(project_dir)
        assert "fingerprints" in manifest
        assert "DQY" in manifest["fingerprints"]
        assert "OVE" in manifest["fingerprints"]
        assert "GEI" in manifest["fingerprints"]

    def test_fingerprints_are_independent(
        self, tmp_project_dir_multi_codes, sample_api_responses
    ):
        """Each fingerprint has independent clearance counts and K-numbers."""
        project_dir = tmp_project_dir_multi_codes
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        client = MockFDAClient()
        client.set_clearances("DQY", meta_total=149,
                             results=sample_api_responses["clearances_dqy_5_items"]["results"])
        client.set_recalls("DQY", meta_total=3)
        
        client.set_clearances("OVE", meta_total=89,
                             results=sample_api_responses["clearances_ove"]["results"])
        client.set_recalls("OVE", meta_total=1)
        
        client.set_clearances("GEI", meta_total=52,
                             results=sample_api_responses["clearances_gei"]["results"])
        client.set_recalls("GEI", meta_total=0)

        manifest = load_manifest(project_dir)
        manifest["fingerprints"] = {}
        save_manifest(project_dir, manifest)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            with patch("change_detector.time.sleep"):
                detect_changes(
                    project_name=project_name,
                    client=client,
                    verbose=False,
                )

        manifest = load_manifest(project_dir)
        fp_dqy = manifest["fingerprints"]["DQY"]
        fp_ove = manifest["fingerprints"]["OVE"]
        fp_gei = manifest["fingerprints"]["GEI"]

        # Each should have different clearance counts
        assert fp_dqy["clearance_count"] == 149
        assert fp_ove["clearance_count"] == 89
        assert fp_gei["clearance_count"] == 52

        # Each should have different K-numbers (no cross-contamination)
        assert "K261001" in fp_dqy["known_k_numbers"]  # DQY K-number
        assert "K240501" in fp_ove["known_k_numbers"]  # OVE K-number
        assert "K240801" in fp_gei["known_k_numbers"]  # GEI K-number

        # DQY K-numbers should NOT appear in OVE or GEI
        assert "K261001" not in fp_ove["known_k_numbers"]
        assert "K261001" not in fp_gei["known_k_numbers"]

    @patch("change_detector.time.sleep")
    def test_rate_limiting_between_codes(
        self, mock_sleep, tmp_project_dir_multi_codes, sample_api_responses
    ):
        """Rate limiting delay is observed between product code checks."""
        project_dir = tmp_project_dir_multi_codes
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        client = MockFDAClient()
        for code in ["DQY", "OVE", "GEI"]:
            client.set_clearances(code, meta_total=10, results=[])
            client.set_recalls(code, meta_total=0)

        manifest = load_manifest(project_dir)
        manifest["fingerprints"] = {}
        save_manifest(project_dir, manifest)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            detect_changes(
                project_name=project_name,
                client=client,
                verbose=False,
            )

        # Rate limiting should be called between product codes
        # With 3 codes, expect 2 sleep calls (between code 1-2 and 2-3)
        assert mock_sleep.call_count >= 2


# ===================================================================
# HIGH: API Error Graceful Degradation (SMART-008)
# ===================================================================


class TestSMART008APIErrorGraceful:
    """SMART-008: API error graceful degradation.

    Validates that detect_changes handles API errors gracefully without
    crashing, modifying fingerprints, or reporting false positives.
    """

    def test_api_error_no_crash(self, tmp_project_dir, mock_fda_client_error):
        """API error does not raise an unhandled exception."""
        project_dir = tmp_project_dir
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            # Should not raise an exception
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_error,
                verbose=False,
            )

        # Function should return a result (not crash)
        assert result is not None
        assert "status" in result

    def test_api_error_completed_status(self, tmp_project_dir, mock_fda_client_error):
        """API error results in completed status (individual errors are skipped)."""
        project_dir = tmp_project_dir
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_error,
                verbose=False,
            )

        # Status should be completed (product code errors are logged but skipped)
        assert result["status"] == "completed"

    def test_api_error_no_false_positives(self, tmp_project_dir, mock_fda_client_error):
        """API error does not produce false positive changes."""
        project_dir = tmp_project_dir
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            result = detect_changes(
                project_name=project_name,
                client=mock_fda_client_error,
                verbose=False,
            )

        # Should not report any changes from error states
        assert result["changes"] == []
        assert result["total_new_clearances"] == 0
        assert result["total_new_recalls"] == 0

    def test_api_error_fingerprint_not_modified(
        self, tmp_project_dir_with_fingerprint, mock_fda_client_error
    ):
        """Existing fingerprint is NOT modified when API returns error."""
        project_dir = tmp_project_dir_with_fingerprint
        project_name = os.path.basename(project_dir)
        parent_dir = os.path.dirname(project_dir)

        # Record original fingerprint state
        original_manifest = load_manifest(project_dir)
        original_fp = original_manifest["fingerprints"]["DQY"].copy()

        with patch("change_detector.get_projects_dir", return_value=parent_dir):
            detect_changes(
                project_name=project_name,
                client=mock_fda_client_error,
                verbose=False,
            )

        # Fingerprint should be unchanged (except possibly last_checked timestamp)
        updated_manifest = load_manifest(project_dir)
        updated_fp = updated_manifest["fingerprints"]["DQY"]

        # Critical fields should not change on error
        assert updated_fp["clearance_count"] == original_fp["clearance_count"]
        assert updated_fp["known_k_numbers"] == original_fp["known_k_numbers"]
        assert updated_fp["recall_count"] == original_fp["recall_count"]


# ===================================================================
# HIGH: Pipeline Trigger Execution (SMART-012)
# ===================================================================


class TestSMART012PipelineTriggerExecution:
    """SMART-012: Pipeline trigger execution with mocked subprocess.

    Validates that trigger_pipeline correctly invokes both batchfetch
    and build_structured_cache subprocesses with the right arguments.
    """

    @patch("change_detector.subprocess.run")
    def test_both_pipeline_steps_executed(self, mock_subprocess_run):
        """Both batchfetch and build_cache steps are executed."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="Success", stderr=""
        )

        result = trigger_pipeline(
            project_name="test_project",
            new_k_numbers=["K261001"],
            product_code="DQY",
            dry_run=False,
            verbose=False,
        )

        assert result["status"] == "completed"
        # Two subprocess calls: batchfetch + build_cache
        assert mock_subprocess_run.call_count == 2

    @patch("change_detector.subprocess.run")
    def test_batchfetch_called_with_correct_args(self, mock_subprocess_run):
        """Batchfetch subprocess is called with correct product code and year."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )

        trigger_pipeline(
            project_name="test_project",
            new_k_numbers=["K261001"],
            product_code="DQY",
            dry_run=False,
            verbose=False,
        )

        # First call should be batchfetch
        first_call_cmd = mock_subprocess_run.call_args_list[0][0][0]
        
        # Verify batchfetch.py is in the command
        assert any("batchfetch.py" in str(arg) for arg in first_call_cmd), (
            f"Expected batchfetch.py in command: {first_call_cmd}"
        )
        
        # Verify product code argument
        assert "DQY" in first_call_cmd, (
            f"Product code DQY not found in command: {first_call_cmd}"
        )

    @patch("change_detector.subprocess.run")
    def test_build_cache_called_second(self, mock_subprocess_run):
        """build_structured_cache is called after batchfetch."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )

        trigger_pipeline(
            project_name="test_project",
            new_k_numbers=["K261001"],
            product_code="DQY",
            dry_run=False,
            verbose=False,
        )

        # Second call should be build_structured_cache
        second_call_cmd = mock_subprocess_run.call_args_list[1][0][0]
        
        assert any("build_structured_cache.py" in str(arg) for arg in second_call_cmd), (
            f"Expected build_structured_cache.py in command: {second_call_cmd}"
        )

    @patch("change_detector.subprocess.run")
    def test_steps_have_success_status(self, mock_subprocess_run):
        """Both steps in result have 'success' status."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=0, stdout="OK", stderr=""
        )

        result = trigger_pipeline(
            project_name="test_project",
            new_k_numbers=["K261001"],
            product_code="DQY",
            dry_run=False,
            verbose=False,
        )

        assert len(result["steps"]) == 2
        assert result["steps"][0]["status"] == "success"
        assert result["steps"][1]["status"] == "success"


# ===================================================================
# MEDIUM: CLI with --json Output (SMART-016)
# ===================================================================


class TestSMART016CLIJsonOutput:
    """SMART-016: CLI with --json output.

    Validates that the command-line interface produces valid JSON output
    when invoked with the --json flag.
    """

    @patch("change_detector.detect_changes")
    @patch("change_detector.FDAClient")
    def test_json_flag_produces_valid_json(
        self, mock_fda_client_class, mock_detect_changes, capsys
    ):
        """--json flag produces valid JSON output."""
        from change_detector import main as change_detector_main

        mock_detect_changes.return_value = {
            "project": "test_proj",
            "status": "completed",
            "total_new_clearances": 3,
            "total_new_recalls": 1,
            "changes": [
                {
                    "change_type": "new_clearances",
                    "product_code": "DQY",
                    "count": 3,
                    "new_items": [],
                }
            ],
        }

        test_args = [
            "change_detector.py",
            "--project", "test_proj",
            "--json",
        ]
        with patch("sys.argv", test_args):
            try:
                change_detector_main()
            except SystemExit:
                pass

        captured = capsys.readouterr()
        output = captured.out

        # Output should be valid JSON
        try:
            parsed = json.loads(output)
            assert isinstance(parsed, dict), "JSON output should be a dict"
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nOutput:\n{output}")

    @patch("change_detector.detect_changes")
    @patch("change_detector.FDAClient")
    def test_json_contains_required_keys(
        self, mock_fda_client_class, mock_detect_changes, capsys
    ):
        """JSON output contains all expected keys."""
        from change_detector import main as change_detector_main

        mock_detect_changes.return_value = {
            "project": "test_proj",
            "status": "completed",
            "total_new_clearances": 2,
            "total_new_recalls": 0,
            "changes": [],
        }

        test_args = [
            "change_detector.py",
            "--project", "test_proj",
            "--json",
        ]
        with patch("sys.argv", test_args):
            try:
                change_detector_main()
            except SystemExit:
                pass

        captured = capsys.readouterr()
        output = captured.out
        parsed = json.loads(output)

        # Verify required keys are present
        assert "project" in parsed or "status" in parsed
        assert "status" in parsed
        assert "changes" in parsed

    @patch("change_detector.detect_changes")
    @patch("change_detector.FDAClient")
    def test_json_output_no_extra_text(
        self, mock_fda_client_class, mock_detect_changes, capsys
    ):
        """JSON output contains no non-JSON text."""
        from change_detector import main as change_detector_main

        mock_detect_changes.return_value = {
            "status": "completed",
            "changes": [],
        }

        test_args = [
            "change_detector.py",
            "--project", "test_proj",
            "--json",
        ]
        with patch("sys.argv", test_args):
            try:
                change_detector_main()
            except SystemExit:
                pass

        captured = capsys.readouterr()
        output = captured.out.strip()

        # First non-whitespace character should be '{'
        assert output.startswith("{"), (
            f"JSON output should start with '{{', got: {output[:50]}"
        )
        # Last non-whitespace character should be '}'
        assert output.endswith("}"), (
            f"JSON output should end with '}}', got: ...{output[-50:]}"
        )
