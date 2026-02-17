"""
pytest Test Suite for FDA Smart Change Detector
================================================

Comprehensive mock-based test suite for change_detector.py module.
Tests all critical paths with mocked dependencies (FDAClient, file I/O, subprocess).

Version: 1.0.0
Date: 2026-02-17

Usage:
    pytest tests/test_change_detector.py -v
    pytest tests/test_change_detector.py::TestFingerprintCRUD -v
    pytest tests/test_change_detector.py::TestNewClearanceDetection -v
    pytest tests/test_change_detector.py::TestRecallMonitoring -v
    pytest tests/test_change_detector.py::TestPipelineTrigger -v
    pytest tests/test_change_detector.py::TestErrorHandling -v
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sys

# Add scripts directory to path
scripts_path = Path(__file__).parent.parent / 'plugins' / 'fda-tools' / 'scripts'
sys.path.insert(0, str(scripts_path))

from change_detector import (  # type: ignore
    _load_fingerprint,
    _save_fingerprint,
    find_new_clearances,
    _detect_field_changes,
    _generate_diff_report,
    detect_changes,
    trigger_pipeline,
    _run_subprocess,
)


class TestFingerprintCRUD:
    """Test fingerprint CRUD operations"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = os.path.join(tmpdir, "test_project")
            os.makedirs(project_dir)
            yield project_dir

    @pytest.fixture
    def sample_fingerprint(self):
        """Sample fingerprint data"""
        return {
            "last_checked": "2026-02-16T10:00:00+00:00",
            "clearance_count": 147,
            "latest_k_number": "K251234",
            "latest_decision_date": "20260115",
            "recall_count": 3,
            "known_k_numbers": ["K251234", "K250987", "K250745"],
            "device_data": {
                "K251234": {
                    "k_number": "K251234",
                    "device_name": "Test Device",
                    "applicant": "Test Corp",
                    "decision_date": "20260115",
                }
            }
        }

    @patch('change_detector.load_manifest')
    def test_load_fingerprint_exists(self, mock_load_manifest, temp_project_dir, sample_fingerprint):
        """Test loading an existing fingerprint"""
        mock_load_manifest.return_value = {
            "fingerprints": {
                "DQY": sample_fingerprint
            }
        }

        result = _load_fingerprint(temp_project_dir, "DQY")

        assert result is not None, "Should return fingerprint"
        assert result["latest_k_number"] == "K251234"
        assert result["clearance_count"] == 147
        assert len(result["known_k_numbers"]) == 3
        mock_load_manifest.assert_called_once_with(temp_project_dir)

    @patch('change_detector.load_manifest')
    def test_load_fingerprint_not_exists(self, mock_load_manifest, temp_project_dir):
        """Test loading a non-existent fingerprint"""
        mock_load_manifest.return_value = {"fingerprints": {}}

        result = _load_fingerprint(temp_project_dir, "DQY")

        assert result is None, "Should return None for non-existent fingerprint"

    @patch('change_detector.load_manifest')
    def test_load_fingerprint_case_insensitive(self, mock_load_manifest, temp_project_dir, sample_fingerprint):
        """Test fingerprint loading is case-insensitive"""
        mock_load_manifest.return_value = {
            "fingerprints": {
                "DQY": sample_fingerprint
            }
        }

        result = _load_fingerprint(temp_project_dir, "dqy")

        assert result is not None, "Should find fingerprint regardless of case"
        assert result["latest_k_number"] == "K251234"

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_save_fingerprint_new(self, mock_save_manifest, mock_load_manifest, temp_project_dir, sample_fingerprint):
        """Test saving a new fingerprint"""
        mock_load_manifest.return_value = {"fingerprints": {}}

        _save_fingerprint(temp_project_dir, "DQY", sample_fingerprint)

        mock_save_manifest.assert_called_once()
        saved_manifest = mock_save_manifest.call_args[0][1]
        assert "fingerprints" in saved_manifest
        assert "DQY" in saved_manifest["fingerprints"]
        assert saved_manifest["fingerprints"]["DQY"]["latest_k_number"] == "K251234"

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_save_fingerprint_update(self, mock_save_manifest, mock_load_manifest, temp_project_dir, sample_fingerprint):
        """Test updating an existing fingerprint"""
        mock_load_manifest.return_value = {
            "fingerprints": {
                "DQY": {
                    "last_checked": "2026-02-15T10:00:00+00:00",
                    "clearance_count": 145,
                }
            }
        }

        _save_fingerprint(temp_project_dir, "DQY", sample_fingerprint)

        mock_save_manifest.assert_called_once()
        saved_manifest = mock_save_manifest.call_args[0][1]
        assert saved_manifest["fingerprints"]["DQY"]["clearance_count"] == 147

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_save_fingerprint_case_normalized(self, mock_save_manifest, mock_load_manifest, temp_project_dir, sample_fingerprint):
        """Test fingerprint keys are normalized to uppercase"""
        mock_load_manifest.return_value = {"fingerprints": {}}

        _save_fingerprint(temp_project_dir, "dqy", sample_fingerprint)

        saved_manifest = mock_save_manifest.call_args[0][1]
        assert "DQY" in saved_manifest["fingerprints"], "Product code should be uppercase"


class TestNewClearanceDetection:
    """Test new clearance detection logic"""

    @pytest.fixture
    def mock_client(self):
        """Mock FDAClient for testing"""
        client = MagicMock()
        return client

    def test_find_new_clearances_with_new_devices(self, mock_client):
        """Test detection of new clearances"""
        known_k_numbers = ["K240001", "K240002"]
        mock_client.get_clearances.return_value = {
            "results": [
                {
                    "k_number": "K240003",
                    "device_name": "New Device 1",
                    "applicant": "Company A",
                    "decision_date": "20240115",
                    "decision_code": "SESE",
                    "clearance_type": "Traditional",
                },
                {
                    "k_number": "K240002",
                    "device_name": "Existing Device",
                    "applicant": "Company B",
                    "decision_date": "20240110",
                    "decision_code": "SESE",
                    "clearance_type": "Traditional",
                },
                {
                    "k_number": "K240004",
                    "device_name": "New Device 2",
                    "applicant": "Company C",
                    "decision_date": "20240112",
                    "decision_code": "SESE",
                    "clearance_type": "Traditional",
                }
            ],
            "degraded": False,
            "error": None,
        }

        new_clearances = find_new_clearances("DQY", known_k_numbers, mock_client, max_fetch=100)

        assert len(new_clearances) == 2, "Should find 2 new clearances"
        assert new_clearances[0]["k_number"] == "K240003"
        assert new_clearances[1]["k_number"] == "K240004"
        assert new_clearances[0]["device_name"] == "New Device 1"

    def test_find_new_clearances_no_new_devices(self, mock_client):
        """Test when no new clearances exist"""
        known_k_numbers = ["K240001", "K240002", "K240003"]
        mock_client.get_clearances.return_value = {
            "results": [
                {"k_number": "K240001", "device_name": "Device 1", "applicant": "Company A",
                 "decision_date": "20240101", "decision_code": "SESE", "clearance_type": "Traditional"},
                {"k_number": "K240002", "device_name": "Device 2", "applicant": "Company B",
                 "decision_date": "20240102", "decision_code": "SESE", "clearance_type": "Traditional"},
            ],
            "degraded": False,
            "error": None,
        }

        new_clearances = find_new_clearances("DQY", known_k_numbers, mock_client)

        assert len(new_clearances) == 0, "Should find no new clearances"

    def test_find_new_clearances_case_insensitive(self, mock_client):
        """Test K-number comparison is case-insensitive"""
        known_k_numbers = ["k240001", "k240002"]  # lowercase
        mock_client.get_clearances.return_value = {
            "results": [
                {"k_number": "K240001", "device_name": "Device 1", "applicant": "Company A",
                 "decision_date": "20240101", "decision_code": "SESE", "clearance_type": "Traditional"},
                {"k_number": "K240003", "device_name": "Device 3", "applicant": "Company C",
                 "decision_date": "20240103", "decision_code": "SESE", "clearance_type": "Traditional"},
            ],
            "degraded": False,
            "error": None,
        }

        new_clearances = find_new_clearances("DQY", known_k_numbers, mock_client)

        assert len(new_clearances) == 1, "Should find 1 new clearance"
        assert new_clearances[0]["k_number"] == "K240003"

    def test_find_new_clearances_api_error(self, mock_client):
        """Test handling of API errors"""
        known_k_numbers = ["K240001"]
        mock_client.get_clearances.return_value = {
            "degraded": True,
            "error": "API timeout",
            "results": []
        }

        new_clearances = find_new_clearances("DQY", known_k_numbers, mock_client)

        assert len(new_clearances) == 0, "Should return empty list on API error"

    def test_find_new_clearances_empty_k_number(self, mock_client):
        """Test handling of empty K-numbers in API response"""
        known_k_numbers = ["K240001"]
        mock_client.get_clearances.return_value = {
            "results": [
                {"k_number": "", "device_name": "Device with no K", "applicant": "Company X",
                 "decision_date": "20240101", "decision_code": "SESE", "clearance_type": "Traditional"},
                {"k_number": "K240002", "device_name": "Device 2", "applicant": "Company Y",
                 "decision_date": "20240102", "decision_code": "SESE", "clearance_type": "Traditional"},
            ],
            "degraded": False,
            "error": None,
        }

        new_clearances = find_new_clearances("DQY", known_k_numbers, mock_client)

        assert len(new_clearances) == 1, "Should skip devices with empty K-numbers"
        assert new_clearances[0]["k_number"] == "K240002"


class TestFieldChangeDetection:
    """Test field-level change detection"""

    @pytest.fixture
    def stored_devices(self):
        """Sample stored device data"""
        return {
            "K240001": {
                "k_number": "K240001",
                "device_name": "Original Device Name",
                "applicant": "Original Company",
                "decision_date": "20240101",
                "decision_code": "SESE",
                "clearance_type": "Traditional",
                "product_code": "DQY",
            },
            "K240002": {
                "k_number": "K240002",
                "device_name": "Device 2",
                "applicant": "Company B",
                "decision_date": "20240115",
                "decision_code": "SESE",
                "clearance_type": "Traditional",
                "product_code": "DQY",
            }
        }

    def test_detect_field_changes_applicant_change(self, stored_devices):
        """Test detection of applicant name change (acquisition)"""
        current_devices = [
            {
                "k_number": "K240001",
                "device_name": "Original Device Name",
                "applicant": "Acquired Company LLC",  # Changed
                "decision_date": "20240101",
                "decision_code": "SESE",
                "clearance_type": "Traditional",
                "product_code": "DQY",
            }
        ]

        changes = _detect_field_changes(stored_devices, current_devices)

        assert len(changes) == 1, "Should detect 1 field change"
        assert changes[0]["k_number"] == "K240001"
        assert changes[0]["field"] == "applicant"
        assert changes[0]["before"] == "Original Company"
        assert changes[0]["after"] == "Acquired Company LLC"

    def test_detect_field_changes_decision_date_correction(self, stored_devices):
        """Test detection of decision date correction"""
        current_devices = [
            {
                "k_number": "K240001",
                "device_name": "Original Device Name",
                "applicant": "Original Company",
                "decision_date": "20240102",  # Changed from 20240101
                "decision_code": "SESE",
                "clearance_type": "Traditional",
                "product_code": "DQY",
            }
        ]

        changes = _detect_field_changes(stored_devices, current_devices)

        assert len(changes) == 1
        assert changes[0]["field"] == "decision_date"
        assert changes[0]["before"] == "20240101"
        assert changes[0]["after"] == "20240102"

    def test_detect_field_changes_multiple_fields(self, stored_devices):
        """Test detection of multiple field changes for same device"""
        current_devices = [
            {
                "k_number": "K240001",
                "device_name": "Updated Device Name",  # Changed
                "applicant": "New Owner Corp",  # Changed
                "decision_date": "20240101",
                "decision_code": "SESE",
                "clearance_type": "Abbreviated",  # Changed
                "product_code": "DQY",
            }
        ]

        changes = _detect_field_changes(stored_devices, current_devices)

        assert len(changes) == 3, "Should detect 3 field changes"
        changed_fields = {c["field"] for c in changes}
        assert "device_name" in changed_fields
        assert "applicant" in changed_fields
        assert "clearance_type" in changed_fields

    def test_detect_field_changes_no_changes(self, stored_devices):
        """Test when no fields have changed"""
        current_devices = [
            stored_devices["K240001"].copy(),
            stored_devices["K240002"].copy(),
        ]

        changes = _detect_field_changes(stored_devices, current_devices)

        assert len(changes) == 0, "Should detect no changes"

    def test_detect_field_changes_whitespace_normalization(self, stored_devices):
        """Test that whitespace differences are normalized"""
        current_devices = [
            {
                "k_number": "K240001",
                "device_name": "  Original Device Name  ",  # Extra whitespace
                "applicant": "Original Company",
                "decision_date": "20240101",
                "decision_code": "SESE",
                "clearance_type": "Traditional",
                "product_code": "DQY",
            }
        ]

        changes = _detect_field_changes(stored_devices, current_devices)

        assert len(changes) == 0, "Should not detect changes for whitespace-only differences"

    def test_detect_field_changes_new_device_ignored(self, stored_devices):
        """Test that devices not in stored data are ignored"""
        current_devices = [
            {
                "k_number": "K240999",  # Not in stored_devices
                "device_name": "Brand New Device",
                "applicant": "New Company",
                "decision_date": "20240201",
                "decision_code": "SESE",
                "clearance_type": "Traditional",
                "product_code": "DQY",
            }
        ]

        changes = _detect_field_changes(stored_devices, current_devices)

        assert len(changes) == 0, "Should not report changes for new devices"


class TestRecallMonitoring:
    """Test recall monitoring logic"""

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_detect_changes_new_recalls(self, _, mock_load_manifest):
        """Test detection of new recalls"""
        mock_load_manifest.return_value = {
            "product_codes": ["DQY"],
            "fingerprints": {
                "DQY": {
                    "known_k_numbers": ["K240001"],
                    "clearance_count": 100,
                    "recall_count": 2,  # Previous count
                    "device_data": {}
                }
            }
        }

        mock_client = MagicMock()
        mock_client.get_clearances.return_value = {
            "results": [{"k_number": "K240001", "device_name": "Device 1", "applicant": "Company A",
                        "decision_date": "20240101", "decision_code": "SESE", "clearance_type": "Traditional"}],
            "meta": {"results": {"total": 100}},
            "degraded": False,
            "error": None,
        }
        mock_client.get_recalls.return_value = {
            "meta": {"results": {"total": 5}},  # New count
            "degraded": False,
            "error": None,
        }

        with patch('change_detector.get_projects_dir', return_value="/tmp/projects"):
            with patch('os.path.exists', return_value=True):
                result = detect_changes("test_project", client=mock_client, verbose=False)

        assert result["status"] == "completed"
        assert result["total_new_recalls"] == 3, "Should detect 3 new recalls"

        # Check that a recall change was recorded
        recall_changes = [c for c in result["changes"] if c["change_type"] == "new_recalls"]
        assert len(recall_changes) == 1
        assert recall_changes[0]["details"]["previous_count"] == 2
        assert recall_changes[0]["details"]["current_count"] == 5

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_detect_changes_no_recall_increase(self, _, mock_load_manifest):
        """Test when recall count hasn't increased"""
        mock_load_manifest.return_value = {
            "product_codes": ["DQY"],
            "fingerprints": {
                "DQY": {
                    "known_k_numbers": ["K240001"],
                    "clearance_count": 100,
                    "recall_count": 5,
                    "device_data": {}
                }
            }
        }

        mock_client = MagicMock()
        mock_client.get_clearances.return_value = {
            "results": [{"k_number": "K240001", "device_name": "Device 1", "applicant": "Company A",
                        "decision_date": "20240101", "decision_code": "SESE", "clearance_type": "Traditional"}],
            "meta": {"results": {"total": 100}},
            "degraded": False,
            "error": None,
        }
        mock_client.get_recalls.return_value = {
            "meta": {"results": {"total": 5}},  # Same count
            "degraded": False,
            "error": None,
        }

        with patch('change_detector.get_projects_dir', return_value="/tmp/projects"):
            with patch('os.path.exists', return_value=True):
                result = detect_changes("test_project", client=mock_client, verbose=False)

        assert result["total_new_recalls"] == 0, "Should detect no new recalls"


class TestDiffReportGeneration:
    """Test diff report generation"""

    def test_generate_diff_report_with_changes(self):
        """Test diff report generation with field changes"""
        diff_changes = [
            {
                "k_number": "K240001",
                "field": "applicant",
                "before": "Old Company",
                "after": "New Company",
            },
            {
                "k_number": "K240001",
                "field": "device_name",
                "before": "Old Name",
                "after": "New Name",
            },
            {
                "k_number": "K240002",
                "field": "decision_date",
                "before": "20240101",
                "after": "20240102",
            }
        ]

        report = _generate_diff_report(
            diff_changes,
            "DQY",
            "2026-02-17T10:00:00+00:00",
            output_path=None
        )

        assert "# FDA Field-Level Change Report" in report
        assert "**Product Code:** DQY" in report
        assert "**Changes Detected:** 3" in report
        assert "K240001" in report
        assert "K240002" in report
        assert "applicant" in report
        assert "Old Company" in report
        assert "New Company" in report

    def test_generate_diff_report_no_changes(self):
        """Test diff report with no changes"""
        diff_changes = []

        report = _generate_diff_report(
            diff_changes,
            "DQY",
            "2026-02-17T10:00:00+00:00",
            output_path=None
        )

        assert "No field-level changes detected" in report
        assert "**Changes Detected:** 0" in report

    def test_generate_diff_report_pipe_escaping(self):
        """Test that pipe characters in values are escaped"""
        diff_changes = [
            {
                "k_number": "K240001",
                "field": "device_name",
                "before": "Device | Model A",
                "after": "Device | Model B",
            }
        ]

        report = _generate_diff_report(
            diff_changes,
            "DQY",
            "2026-02-17T10:00:00+00:00",
            output_path=None
        )

        assert "Device \\| Model A" in report
        assert "Device \\| Model B" in report


class TestPipelineTrigger:
    """Test pipeline trigger with dry-run"""

    def test_trigger_pipeline_dry_run(self):
        """Test pipeline trigger in dry-run mode"""
        new_k_numbers = ["K240001", "K240002", "K240003"]

        result = trigger_pipeline(
            "test_project",
            new_k_numbers,
            "DQY",
            dry_run=True,
            verbose=False
        )

        assert result["status"] == "dry_run"
        assert result["k_numbers_processed"] == 3
        assert result["k_numbers"] == new_k_numbers
        assert len(result["steps"]) == 1
        assert result["steps"][0]["step"] == "dry_run"

    def test_trigger_pipeline_no_k_numbers(self):
        """Test pipeline trigger with no K-numbers"""
        result = trigger_pipeline(
            "test_project",
            [],
            "DQY",
            dry_run=False,
            verbose=False
        )

        assert result["status"] == "skipped"
        assert result["k_numbers_processed"] == 0
        assert "No new K-numbers" in result["message"]

    @patch('change_detector._run_subprocess')
    def test_trigger_pipeline_success(self, mock_run_subprocess):
        """Test successful pipeline execution"""
        mock_run_subprocess.return_value = {
            "step": "batchfetch",
            "status": "success",
            "returncode": 0,
            "output": "Success",
            "error": ""
        }

        new_k_numbers = ["K240001"]

        with patch('pathlib.Path.exists', return_value=True):
            result = trigger_pipeline(
                "test_project",
                new_k_numbers,
                "DQY",
                dry_run=False,
                verbose=False
            )

        assert result["status"] == "completed"
        assert result["k_numbers_processed"] == 1
        assert mock_run_subprocess.call_count == 2  # batchfetch + build_cache

    @patch('change_detector._run_subprocess')
    def test_trigger_pipeline_partial_failure(self, mock_run_subprocess):
        """Test pipeline with partial failures"""
        # First call succeeds, second fails
        mock_run_subprocess.side_effect = [
            {"step": "batchfetch", "status": "success", "returncode": 0, "output": "OK", "error": ""},
            {"step": "build_cache", "status": "error", "returncode": 1, "output": "", "error": "Failed"}
        ]

        new_k_numbers = ["K240001"]

        with patch('pathlib.Path.exists', return_value=True):
            result = trigger_pipeline(
                "test_project",
                new_k_numbers,
                "DQY",
                dry_run=False,
                verbose=False
            )

        assert result["status"] == "partial"

    def test_trigger_pipeline_missing_scripts(self):
        """Test pipeline when scripts don't exist"""
        new_k_numbers = ["K240001"]

        with patch('pathlib.Path.exists', return_value=False):
            result = trigger_pipeline(
                "test_project",
                new_k_numbers,
                "DQY",
                dry_run=False,
                verbose=False
            )

        # Should skip steps when scripts don't exist
        assert result["status"] in ["error", "partial"]
        skipped_steps = [s for s in result["steps"] if s["status"] == "skipped"]
        assert len(skipped_steps) > 0


class TestSubprocessExecution:
    """Test subprocess execution helper"""

    @patch('subprocess.run')
    def test_run_subprocess_success(self, mock_run):
        """Test successful subprocess execution"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "test"],
            returncode=0,
            stdout="Success output",
            stderr=""
        )

        result = _run_subprocess(
            ["echo", "test"],
            "test_step",
            timeout_seconds=10,
            cwd="/tmp",
            verbose=False
        )

        assert result["step"] == "test_step"
        assert result["status"] == "success"
        assert result["returncode"] == 0
        assert "Success output" in result["output"]

    @patch('subprocess.run')
    def test_run_subprocess_error(self, mock_run):
        """Test subprocess execution with error"""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["false"],
            returncode=1,
            stdout="",
            stderr="Error occurred"
        )

        result = _run_subprocess(
            ["false"],
            "failing_step",
            timeout_seconds=10,
            cwd="/tmp",
            verbose=False
        )

        assert result["step"] == "failing_step"
        assert result["status"] == "error"
        assert result["returncode"] == 1
        assert "Error occurred" in result["error"]

    @patch('subprocess.run')
    def test_run_subprocess_timeout(self, mock_run):
        """Test subprocess execution timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "100"],
            timeout=5
        )

        result = _run_subprocess(
            ["sleep", "100"],
            "timeout_step",
            timeout_seconds=5,
            cwd="/tmp",
            verbose=False
        )

        assert result["step"] == "timeout_step"
        assert result["status"] == "timeout"
        assert "timed out" in result["output"]

    @patch('subprocess.run')
    def test_run_subprocess_os_error(self, mock_run):
        """Test subprocess execution with OSError"""
        mock_run.side_effect = OSError("Command not found")

        result = _run_subprocess(
            ["nonexistent_command"],
            "os_error_step",
            timeout_seconds=10,
            cwd="/tmp",
            verbose=False
        )

        assert result["step"] == "os_error_step"
        assert result["status"] == "error"
        assert "Command not found" in result["output"]


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch('change_detector.get_projects_dir')
    def test_detect_changes_project_not_found(self, mock_get_projects_dir):
        """Test error handling when project directory doesn't exist"""
        mock_get_projects_dir.return_value = "/tmp/projects"

        with patch('os.path.exists', return_value=False):
            result = detect_changes("nonexistent_project", verbose=False)

        assert result["status"] == "error"
        assert "not found" in result["error"]

    @patch('change_detector.load_manifest')
    def test_detect_changes_no_fingerprints(self, mock_load_manifest):
        """Test handling when no fingerprints exist"""
        mock_load_manifest.return_value = {
            "product_codes": [],
            "fingerprints": {}
        }

        mock_client = MagicMock()

        with patch('change_detector.get_projects_dir', return_value="/tmp/projects"):
            with patch('os.path.exists', return_value=True):
                result = detect_changes("test_project", client=mock_client, verbose=False)

        assert result["status"] == "no_fingerprints"
        assert result["total_new_clearances"] == 0
        assert result["total_new_recalls"] == 0

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_detect_changes_api_degraded(self, _, mock_load_manifest):
        """Test handling of degraded API responses"""
        mock_load_manifest.return_value = {
            "product_codes": ["DQY"],
            "fingerprints": {
                "DQY": {
                    "known_k_numbers": [],
                    "clearance_count": 0,
                    "recall_count": 0,
                    "device_data": {}
                }
            }
        }

        mock_client = MagicMock()
        mock_client.get_clearances.return_value = {
            "degraded": True,
            "error": "API timeout",
            "results": []
        }

        with patch('change_detector.get_projects_dir', return_value="/tmp/projects"):
            with patch('os.path.exists', return_value=True):
                result = detect_changes("test_project", client=mock_client, verbose=False)

        # Should complete without crashing
        assert result["status"] == "completed"
        assert result["total_new_clearances"] == 0

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_detect_changes_api_error_recalls(self, _, mock_load_manifest):
        """Test handling of API errors for recalls"""
        mock_load_manifest.return_value = {
            "product_codes": ["DQY"],
            "fingerprints": {
                "DQY": {
                    "known_k_numbers": ["K240001"],
                    "clearance_count": 100,
                    "recall_count": 2,
                    "device_data": {}
                }
            }
        }

        mock_client = MagicMock()
        mock_client.get_clearances.return_value = {
            "results": [{"k_number": "K240001", "device_name": "Device 1", "applicant": "Company A",
                        "decision_date": "20240101", "decision_code": "SESE", "clearance_type": "Traditional"}],
            "meta": {"results": {"total": 100}},
            "degraded": False,
            "error": None,
        }
        mock_client.get_recalls.return_value = {
            "degraded": True,
            "error": "Network timeout",
            "meta": {"results": {"total": 0}}
        }

        with patch('change_detector.get_projects_dir', return_value="/tmp/projects"):
            with patch('os.path.exists', return_value=True):
                result = detect_changes("test_project", client=mock_client, verbose=False)

        # Should handle gracefully and keep previous recall count
        assert result["status"] == "completed"

    @patch('change_detector.load_manifest')
    def test_detect_changes_corrupted_fingerprint(self, mock_load_manifest):
        """Test handling of corrupted fingerprint data"""
        mock_load_manifest.return_value = {
            "product_codes": ["DQY"],
            "fingerprints": {
                "DQY": {
                    # Missing required fields
                    "last_checked": "2026-02-16T10:00:00+00:00",
                }
            }
        }

        mock_client = MagicMock()
        mock_client.get_clearances.return_value = {
            "results": [],
            "meta": {"results": {"total": 0}},
            "degraded": False,
            "error": None,
        }
        mock_client.get_recalls.return_value = {
            "meta": {"results": {"total": 0}},
            "degraded": False,
            "error": None,
        }

        with patch('change_detector.get_projects_dir', return_value="/tmp/projects"):
            with patch('os.path.exists', return_value=True):
                with patch('change_detector.save_manifest'):
                    # Should handle gracefully with .get() defaults
                    result = detect_changes("test_project", client=mock_client, verbose=False)

        assert result["status"] == "completed"


class TestDetectChangesIntegration:
    """Test complete detect_changes workflow"""

    @patch('change_detector.load_manifest')
    @patch('change_detector.save_manifest')
    def test_detect_changes_complete_workflow(self, mock_save_manifest, mock_load_manifest):
        """Test complete change detection workflow"""
        mock_load_manifest.return_value = {
            "product_codes": ["DQY"],
            "fingerprints": {
                "DQY": {
                    "known_k_numbers": ["K240001", "K240002"],
                    "clearance_count": 100,
                    "recall_count": 2,
                    "device_data": {
                        "K240001": {
                            "k_number": "K240001",
                            "device_name": "Old Name",
                            "applicant": "Old Company",
                            "decision_date": "20240101",
                            "decision_code": "SESE",
                            "clearance_type": "Traditional",
                        }
                    }
                }
            }
        }

        mock_client = MagicMock()
        mock_client.get_clearances.return_value = {
            "results": [
                {
                    "k_number": "K240001",
                    "device_name": "New Name",  # Changed
                    "applicant": "Old Company",
                    "decision_date": "20240101",
                    "decision_code": "SESE",
                    "clearance_type": "Traditional",
                },
                {
                    "k_number": "K240002",
                    "device_name": "Device 2",
                    "applicant": "Company B",
                    "decision_date": "20240102",
                    "decision_code": "SESE",
                    "clearance_type": "Traditional",
                },
                {
                    "k_number": "K240003",  # New device
                    "device_name": "Device 3",
                    "applicant": "Company C",
                    "decision_date": "20240103",
                    "decision_code": "SESE",
                    "clearance_type": "Traditional",
                }
            ],
            "meta": {"results": {"total": 103}},  # Increased
            "degraded": False,
            "error": None,
        }
        mock_client.get_recalls.return_value = {
            "meta": {"results": {"total": 4}},  # Increased
            "degraded": False,
            "error": None,
        }

        with patch('change_detector.get_projects_dir', return_value="/tmp/projects"):
            with patch('os.path.exists', return_value=True):
                with patch('time.sleep'):  # Skip rate limiting
                    result = detect_changes(
                        "test_project",
                        client=mock_client,
                        verbose=False,
                        detect_field_diffs=True
                    )

        assert result["status"] == "completed"
        assert result["product_codes_checked"] == 1
        assert result["total_new_clearances"] == 1
        assert result["total_new_recalls"] == 2
        assert result["total_field_changes"] == 1  # device_name change

        # Verify fingerprint was updated
        mock_save_manifest.assert_called()
        saved_manifest = mock_save_manifest.call_args[0][1]
        assert saved_manifest["fingerprints"]["DQY"]["clearance_count"] == 103
        assert saved_manifest["fingerprints"]["DQY"]["recall_count"] == 4
        assert "K240003" in saved_manifest["fingerprints"]["DQY"]["known_k_numbers"]


# Test configuration
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
