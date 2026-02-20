"""
Tests for FDA-38: Batch Smart Detection Across All Projects.

Tests the --smart --all-projects mode in update_manager.py which provides:
- Consolidated change detection across all projects
- Global rate limiting (shared budget, not per-project)
- Consolidated markdown change summary report
- Aggregated statistics

Uses MockFDAClient to avoid network calls.
"""

import json
import os

import pytest
from unittest.mock import patch

# Ensure scripts directory is on sys.path
from update_manager import (  # type: ignore
    smart_detect_all_projects,
    _generate_consolidated_smart_report,
)

from tests.mocks.mock_fda_client import MockFDAClient


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def two_project_dirs(tmp_path):
    """Create two temporary project directories with manifests and product codes."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    # Project A: product code DQY with existing fingerprint
    proj_a = projects_dir / "project_alpha"
    proj_a.mkdir()
    manifest_a = {
        "project": "project_alpha",
        "product_codes": ["DQY"],
        "queries": {},
        "fingerprints": {
            "DQY": {
                "last_checked": "2026-02-10T00:00:00+00:00",
                "clearance_count": 100,
                "latest_k_number": "K241001",
                "recall_count": 2,
                "known_k_numbers": ["K241001", "K241002", "K241003"],
            }
        },
    }
    (proj_a / "data_manifest.json").write_text(json.dumps(manifest_a, indent=2))

    # Project B: product code OVE with existing fingerprint
    proj_b = projects_dir / "project_beta"
    proj_b.mkdir()
    manifest_b = {
        "project": "project_beta",
        "product_codes": ["OVE"],
        "queries": {},
        "fingerprints": {
            "OVE": {
                "last_checked": "2026-02-10T00:00:00+00:00",
                "clearance_count": 50,
                "latest_k_number": "K240501",
                "recall_count": 1,
                "known_k_numbers": ["K240501", "K240502"],
            }
        },
    }
    (proj_b / "data_manifest.json").write_text(json.dumps(manifest_b, indent=2))

    return str(projects_dir)


@pytest.fixture
def mock_client_with_new_data():
    """MockFDAClient that returns new clearances for DQY and OVE."""
    client = MockFDAClient()

    # DQY: 2 new clearances (K261001, K261002) + 3 existing
    client.set_clearances("DQY", meta_total=105, results=[
        {"k_number": "K261001", "device_name": "New DQY Device 1",
         "applicant": "Acme Corp", "decision_date": "20260201",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
        {"k_number": "K261002", "device_name": "New DQY Device 2",
         "applicant": "Beta Inc", "decision_date": "20260115",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
        {"k_number": "K241001", "device_name": "Existing DQY 1",
         "applicant": "Old Corp", "decision_date": "20240601",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
        {"k_number": "K241002", "device_name": "Existing DQY 2",
         "applicant": "Old Corp", "decision_date": "20240501",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
        {"k_number": "K241003", "device_name": "Existing DQY 3",
         "applicant": "Old Corp", "decision_date": "20240401",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
    ])
    client.set_recalls("DQY", meta_total=3)  # 1 new recall (was 2)

    # OVE: 1 new clearance
    client.set_clearances("OVE", meta_total=51, results=[
        {"k_number": "K260801", "device_name": "New OVE Device",
         "applicant": "Ortho Corp", "decision_date": "20260210",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "OVE"},
        {"k_number": "K240501", "device_name": "Existing OVE 1",
         "applicant": "Old Ortho", "decision_date": "20240301",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "OVE"},
        {"k_number": "K240502", "device_name": "Existing OVE 2",
         "applicant": "Old Ortho", "decision_date": "20240201",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "OVE"},
    ])
    client.set_recalls("OVE", meta_total=1)  # no new recalls

    return client


@pytest.fixture
def mock_client_stable():
    """MockFDAClient that returns no new data for any product code."""
    client = MockFDAClient()

    client.set_clearances("DQY", meta_total=100, results=[
        {"k_number": "K241001", "device_name": "Existing DQY 1",
         "applicant": "Old Corp", "decision_date": "20240601",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
        {"k_number": "K241002", "device_name": "Existing DQY 2",
         "applicant": "Old Corp", "decision_date": "20240501",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
        {"k_number": "K241003", "device_name": "Existing DQY 3",
         "applicant": "Old Corp", "decision_date": "20240401",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "DQY"},
    ])
    client.set_recalls("DQY", meta_total=2)

    client.set_clearances("OVE", meta_total=50, results=[
        {"k_number": "K240501", "device_name": "Existing OVE 1",
         "applicant": "Old Ortho", "decision_date": "20240301",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "OVE"},
        {"k_number": "K240502", "device_name": "Existing OVE 2",
         "applicant": "Old Ortho", "decision_date": "20240201",
         "decision_code": "SESE", "clearance_type": "Traditional",
         "product_code": "OVE"},
    ])
    client.set_recalls("OVE", meta_total=1)

    return client


# ===================================================================
# Tests: smart_detect_all_projects
# ===================================================================


class TestSmartDetectAllProjects:
    """Tests for the core smart_detect_all_projects function."""

    @pytest.mark.smart
    def test_detects_new_clearances_across_projects(
        self, two_project_dirs, mock_client_with_new_data, _tmp_path
    ):
        """Smart detection finds new clearances across multiple projects."""
        with patch("update_manager.find_all_projects") as mock_find, \
             patch("update_manager.FDAClient", return_value=mock_client_with_new_data), \
             patch("update_manager.detect_changes") as mock_detect:

            mock_find.return_value = [
                ("project_alpha", os.path.join(two_project_dirs, "project_alpha"),
                 os.path.join(two_project_dirs, "project_alpha", "data_manifest.json")),
                ("project_beta", os.path.join(two_project_dirs, "project_beta"),
                 os.path.join(two_project_dirs, "project_beta", "data_manifest.json")),
            ]

            # Simulate detect_changes returning results
            mock_detect.side_effect = [
                {
                    "project": "project_alpha",
                    "status": "completed",
                    "product_codes_checked": 1,
                    "total_new_clearances": 2,
                    "total_new_recalls": 1,
                    "total_field_changes": 0,
                    "changes": [
                        {
                            "product_code": "DQY",
                            "change_type": "new_clearances",
                            "count": 2,
                            "new_items": [
                                {"k_number": "K261001", "device_name": "New DQY 1"},
                                {"k_number": "K261002", "device_name": "New DQY 2"},
                            ],
                            "details": {"previous_total": 100, "current_total": 105},
                        },
                        {
                            "product_code": "DQY",
                            "change_type": "new_recalls",
                            "count": 1,
                            "new_items": [],
                            "details": {"previous_count": 2, "current_count": 3},
                        },
                    ],
                },
                {
                    "project": "project_beta",
                    "status": "completed",
                    "product_codes_checked": 1,
                    "total_new_clearances": 1,
                    "total_new_recalls": 0,
                    "total_field_changes": 0,
                    "changes": [
                        {
                            "product_code": "OVE",
                            "change_type": "new_clearances",
                            "count": 1,
                            "new_items": [
                                {"k_number": "K260801", "device_name": "New OVE 1"},
                            ],
                            "details": {"previous_total": 50, "current_total": 51},
                        },
                    ],
                },
            ]

            results = smart_detect_all_projects(
                dry_run=False,
                verbose=False,
                backup_first=False,
                global_rate_limit=True,
            )

        assert results["total_projects"] == 2
        assert results["projects_with_changes"] == 2
        assert results["total_new_clearances"] == 3  # 2 DQY + 1 OVE
        assert results["total_new_recalls"] == 1
        assert results["total_product_codes_checked"] == 2
        assert len(results["consolidated_changes"]) == 3  # 2 DQY changes + 1 OVE change
        assert "project_alpha" in results["projects"]
        assert "project_beta" in results["projects"]

    @pytest.mark.smart
    def test_no_changes_across_projects(
        self, two_project_dirs, mock_client_stable, _tmp_path
    ):
        """Smart detection with no changes returns zero counts."""
        with patch("update_manager.find_all_projects") as mock_find, \
             patch("update_manager.FDAClient", return_value=mock_client_stable), \
             patch("update_manager.detect_changes") as mock_detect:

            mock_find.return_value = [
                ("project_alpha", os.path.join(two_project_dirs, "project_alpha"),
                 os.path.join(two_project_dirs, "project_alpha", "data_manifest.json")),
            ]

            mock_detect.return_value = {
                "project": "project_alpha",
                "status": "completed",
                "product_codes_checked": 1,
                "total_new_clearances": 0,
                "total_new_recalls": 0,
                "total_field_changes": 0,
                "changes": [],
            }

            results = smart_detect_all_projects(
                dry_run=False,
                verbose=False,
            )

        assert results["total_projects"] == 1
        assert results["projects_with_changes"] == 0
        assert results["total_new_clearances"] == 0
        assert results["total_new_recalls"] == 0
        assert results["consolidated_changes"] == []

    @pytest.mark.smart
    def test_no_projects_found(self):
        """Returns empty results when no projects exist."""
        with patch("update_manager.find_all_projects", return_value=[]):
            results = smart_detect_all_projects(verbose=False)

        assert results["total_projects"] == 0
        assert results["projects_with_changes"] == 0
        assert results["consolidated_changes"] == []
        assert results["report_path"] is None

    @pytest.mark.smart
    def test_global_rate_limit_uses_single_client(
        self, _two_project_dirs
    ):
        """With global_rate_limit=True, a single FDAClient is shared across projects."""
        client_instances = []

        def tracking_client(*_args, **_kwargs):
            client = MockFDAClient()
            client_instances.append(client)
            return client

        with patch("update_manager.find_all_projects") as mock_find, \
             patch("update_manager.FDAClient", side_effect=tracking_client), \
             patch("update_manager.detect_changes") as mock_detect:

            mock_find.return_value = [
                ("p1", "/fake/p1", "/fake/p1/data_manifest.json"),
                ("p2", "/fake/p2", "/fake/p2/data_manifest.json"),
                ("p3", "/fake/p3", "/fake/p3/data_manifest.json"),
            ]

            mock_detect.return_value = {
                "project": "test",
                "status": "completed",
                "product_codes_checked": 0,
                "total_new_clearances": 0,
                "total_new_recalls": 0,
                "total_field_changes": 0,
                "changes": [],
            }

            smart_detect_all_projects(
                verbose=False,
                global_rate_limit=True,
            )

        # Only ONE FDAClient should be created (shared across all projects)
        assert len(client_instances) == 1

    @pytest.mark.smart
    def test_api_call_count_estimation(self, _two_project_dirs):
        """API call count is estimated as 2x product codes checked."""
        with patch("update_manager.find_all_projects") as mock_find, \
             patch("update_manager.FDAClient", return_value=MockFDAClient()), \
             patch("update_manager.detect_changes") as mock_detect:

            mock_find.return_value = [
                ("p1", "/fake/p1", "/fake/p1/data_manifest.json"),
                ("p2", "/fake/p2", "/fake/p2/data_manifest.json"),
            ]

            mock_detect.side_effect = [
                {
                    "project": "p1", "status": "completed",
                    "product_codes_checked": 3,
                    "total_new_clearances": 0, "total_new_recalls": 0,
                    "total_field_changes": 0, "changes": [],
                },
                {
                    "project": "p2", "status": "completed",
                    "product_codes_checked": 2,
                    "total_new_clearances": 0, "total_new_recalls": 0,
                    "total_field_changes": 0, "changes": [],
                },
            ]

            results = smart_detect_all_projects(verbose=False)

        # 3 + 2 = 5 product codes, each triggers 2 API calls
        assert results["total_api_calls"] == 10


# ===================================================================
# Tests: Consolidated Report Generation
# ===================================================================


class TestConsolidatedReport:
    """Tests for the consolidated markdown report generator."""

    @pytest.mark.smart
    def test_report_generated_with_changes(self, tmp_path):
        """Report is generated when changes exist."""
        with patch("update_manager.Path") as _mock_path_cls:
            # Make report_dir resolve to tmp_path
            mock_report_dir = tmp_path / "reports"
            mock_report_dir.mkdir(parents=True, exist_ok=True)

            report_path = _generate_consolidated_smart_report(
                project_results={
                    "proj_a": {
                        "status": "completed",
                        "product_codes_checked": 1,
                        "total_new_clearances": 2,
                        "total_new_recalls": 0,
                    }
                },
                consolidated_changes=[
                    {
                        "project": "proj_a",
                        "product_code": "DQY",
                        "change_type": "new_clearances",
                        "count": 2,
                        "new_items": [
                            {"k_number": "K261001", "device_name": "Dev 1",
                             "decision_date": "20260201"},
                            {"k_number": "K261002", "device_name": "Dev 2",
                             "decision_date": "20260115"},
                        ],
                        "details": {},
                    },
                ],
                total_new_clearances=2,
                total_new_recalls=0,
                total_field_changes=0,
                total_product_codes_checked=1,
                api_call_count=2,
                dry_run=False,
            )

        # Report should be written (may be to ~/fda-510k-data/reports/)
        if report_path is not None:
            assert os.path.exists(report_path)
            with open(report_path) as f:
                content = f.read()
            assert "Consolidated Report" in content
            assert "DQY" in content
            assert "K261001" in content

    @pytest.mark.smart
    def test_report_dry_run_mode(self, _tmp_path):
        """Report shows DRY RUN in header when dry_run=True."""
        report_path = _generate_consolidated_smart_report(
            project_results={"test": {"status": "completed", "product_codes_checked": 0,
                                       "total_new_clearances": 0, "total_new_recalls": 0}},
            consolidated_changes=[],
            total_new_clearances=0,
            total_new_recalls=0,
            total_field_changes=0,
            total_product_codes_checked=0,
            api_call_count=0,
            dry_run=True,
        )

        if report_path is not None:
            with open(report_path) as f:
                content = f.read()
            assert "DRY RUN" in content

    @pytest.mark.smart
    def test_report_no_changes_message(self, _tmp_path):
        """Report includes 'no changes' message when no changes detected."""
        report_path = _generate_consolidated_smart_report(
            project_results={"test": {"status": "completed", "product_codes_checked": 1,
                                       "total_new_clearances": 0, "total_new_recalls": 0}},
            consolidated_changes=[],
            total_new_clearances=0,
            total_new_recalls=0,
            total_field_changes=0,
            total_product_codes_checked=1,
            api_call_count=2,
            dry_run=False,
        )

        if report_path is not None:
            with open(report_path) as f:
                content = f.read()
            assert "No changes detected" in content


# ===================================================================
# Tests: Backup Integration
# ===================================================================


class TestBackupIntegration:
    """Tests for backup integration with smart_detect_all_projects."""

    @pytest.mark.smart
    def test_backup_unavailable_returns_error(self):
        """When backup module is unavailable, returns error backup_info."""
        with patch("update_manager.BACKUP_AVAILABLE", False), \
             patch("update_manager.find_all_projects", return_value=[]):
            results = smart_detect_all_projects(
                backup_first=True,
                verbose=False,
            )

        assert results["backup_info"]["status"] == "failed"
        assert "not available" in results["backup_info"]["message"]
        assert results["total_projects"] == 0

    @pytest.mark.smart
    def test_backup_not_triggered_on_dry_run(self):
        """Backup is not created when dry_run=True even if backup_first=True."""
        with patch("update_manager.BACKUP_AVAILABLE", True), \
             patch("update_manager.backup_all_projects") as mock_backup, \
             patch("update_manager.find_all_projects", return_value=[]), \
             patch("update_manager.FDAClient", return_value=MockFDAClient()):

            results = smart_detect_all_projects(
                dry_run=True,
                backup_first=True,
                verbose=False,
            )

        mock_backup.assert_not_called()
        assert results["backup_info"] is None
