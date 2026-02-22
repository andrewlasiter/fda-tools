"""
Sprint 11 tests — FDA-256, FDA-261, FDA-262
============================================
Covers:
  FDA-262 [SEC-011] SOC 2 Type II controls
  FDA-261 [SEC-010] OWASP input validation helpers
  FDA-256 [DESK-003] Electron release workflow shape
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso(delta_days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).isoformat()


# ═════════════════════════════════════════════════════════════════════════════
# CC6 — Logical and Physical Access Controls
# ═════════════════════════════════════════════════════════════════════════════

class TestCC6LogicalAccess:

    def test_rbac_all_roles_present(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_rbac(["admin", "ra_lead", "engineer", "viewer"])
        assert result.status == ControlStatus.PASS

    def test_rbac_missing_roles_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_rbac(["admin"])
        assert result.status == ControlStatus.FAIL
        assert "ra_lead" in result.remediation or "engineer" in result.remediation

    def test_rbac_result_has_correct_control_id(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess
        result = CC6_LogicalAccess.check_rbac(["admin", "ra_lead", "engineer", "viewer"])
        assert result.control_id == "CC6.1"

    def test_password_policy_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_password_policy(min_length=16, requires_mfa=True)
        assert result.status == ControlStatus.PASS

    def test_password_policy_short_length_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_password_policy(min_length=8, requires_mfa=True)
        assert result.status == ControlStatus.FAIL

    def test_password_policy_no_mfa_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_password_policy(min_length=16, requires_mfa=False)
        assert result.status == ControlStatus.FAIL
        assert "MFA" in result.remediation

    def test_tls_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_tls_enforcement("TLSv1.2+1.3", hsts_enabled=True)
        assert result.status == ControlStatus.PASS

    def test_tls_old_version_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_tls_enforcement("TLSv1.0", hsts_enabled=True)
        assert result.status == ControlStatus.FAIL

    def test_tls_no_hsts_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_tls_enforcement("TLSv1.3", hsts_enabled=False)
        assert result.status == ControlStatus.FAIL

    def test_session_token_entropy_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_session_token_entropy(token_bytes=32)
        assert result.status == ControlStatus.PASS

    def test_session_token_entropy_too_small_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC6_LogicalAccess, ControlStatus
        result = CC6_LogicalAccess.check_session_token_entropy(token_bytes=16)
        assert result.status == ControlStatus.FAIL


# ═════════════════════════════════════════════════════════════════════════════
# CC7 — System Operations
# ═════════════════════════════════════════════════════════════════════════════

class TestCC7SystemOperations:

    def test_audit_log_immutable_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC7_SystemOperations, ControlStatus
        result = CC7_SystemOperations.check_audit_log_immutability(
            log_table="audit_events",
            has_append_only=True,
            has_row_level_security=True,
        )
        assert result.status == ControlStatus.PASS

    def test_audit_log_no_rls_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC7_SystemOperations, ControlStatus
        result = CC7_SystemOperations.check_audit_log_immutability(
            log_table="audit_events",
            has_append_only=True,
            has_row_level_security=False,
        )
        assert result.status == ControlStatus.FAIL

    def test_health_monitoring_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC7_SystemOperations, ControlStatus
        result = CC7_SystemOperations.check_health_monitoring(
            health_endpoint="/api/health",
            alert_latency_ms=60_000,
        )
        assert result.status == ControlStatus.PASS

    def test_health_monitoring_latency_too_high_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC7_SystemOperations, ControlStatus
        result = CC7_SystemOperations.check_health_monitoring(
            health_endpoint="/api/health",
            alert_latency_ms=600_000,
        )
        assert result.status == ControlStatus.FAIL

    def test_irp_tested_recently_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC7_SystemOperations, ControlStatus
        result = CC7_SystemOperations.check_incident_response_plan(
            plan_exists=True,
            last_tested_iso=_now_iso(delta_days=-30),
        )
        assert result.status == ControlStatus.PASS

    def test_irp_not_tested_recently_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC7_SystemOperations, ControlStatus
        result = CC7_SystemOperations.check_incident_response_plan(
            plan_exists=True,
            last_tested_iso=_now_iso(delta_days=-400),
        )
        assert result.status == ControlStatus.FAIL

    def test_irp_no_plan_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC7_SystemOperations, ControlStatus
        result = CC7_SystemOperations.check_incident_response_plan(
            plan_exists=False,
            last_tested_iso=None,
        )
        assert result.status == ControlStatus.FAIL


# ═════════════════════════════════════════════════════════════════════════════
# CC8 — Change Management
# ═════════════════════════════════════════════════════════════════════════════

class TestCC8ChangeManagement:

    def _good_branch_protections(self):
        return {
            "required_approving_review_count": 1,
            "required_status_checks": True,
            "dismiss_stale_reviews": True,
        }

    def test_pr_review_policy_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC8_ChangeManagement, ControlStatus
        result = CC8_ChangeManagement.check_pr_review_policy(self._good_branch_protections())
        assert result.status == ControlStatus.PASS

    def test_pr_review_no_required_reviews_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC8_ChangeManagement, ControlStatus
        bp = self._good_branch_protections()
        bp["required_approving_review_count"] = 0
        result = CC8_ChangeManagement.check_pr_review_policy(bp)
        assert result.status == ControlStatus.FAIL

    def test_pr_review_no_ci_checks_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC8_ChangeManagement, ControlStatus
        bp = self._good_branch_protections()
        bp["required_status_checks"] = False
        result = CC8_ChangeManagement.check_pr_review_policy(bp)
        assert result.status == ControlStatus.FAIL

    def test_rollback_workflow_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC8_ChangeManagement, ControlStatus
        result = CC8_ChangeManagement.check_rollback_capability(rollback_workflow_exists=True)
        assert result.status == ControlStatus.PASS

    def test_rollback_workflow_missing_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC8_ChangeManagement, ControlStatus
        result = CC8_ChangeManagement.check_rollback_capability(rollback_workflow_exists=False)
        assert result.status == ControlStatus.FAIL

    def test_secret_scanning_passes(self):
        from plugins.fda_tools.lib.soc2_controls import CC8_ChangeManagement, ControlStatus
        result = CC8_ChangeManagement.check_secret_scanning(
            secret_patterns_blocked=["AWS_KEY", "SUPABASE_KEY", "API_KEY", "SECRET_TOKEN"]
        )
        assert result.status == ControlStatus.PASS

    def test_secret_scanning_missing_patterns_fails(self):
        from plugins.fda_tools.lib.soc2_controls import CC8_ChangeManagement, ControlStatus
        result = CC8_ChangeManagement.check_secret_scanning(secret_patterns_blocked=[])
        assert result.status == ControlStatus.FAIL


# ═════════════════════════════════════════════════════════════════════════════
# A1 — Availability
# ═════════════════════════════════════════════════════════════════════════════

class TestA1Availability:

    def test_slo_definition_passes(self):
        from plugins.fda_tools.lib.soc2_controls import A1_Availability, ControlStatus
        result = A1_Availability.check_slo_definition(
            target_percent=99.9,
            error_budget_window_days=28,
        )
        assert result.status == ControlStatus.PASS

    def test_slo_below_target_fails(self):
        from plugins.fda_tools.lib.soc2_controls import A1_Availability, ControlStatus
        result = A1_Availability.check_slo_definition(
            target_percent=99.5,
            error_budget_window_days=28,
        )
        assert result.status == ControlStatus.FAIL

    def test_backup_policy_passes(self):
        from plugins.fda_tools.lib.soc2_controls import A1_Availability, ControlStatus
        result = A1_Availability.check_backup_policy(
            backup_frequency_hours=6,
            last_restore_test_iso=_now_iso(delta_days=-15),
        )
        assert result.status == ControlStatus.PASS

    def test_backup_too_infrequent_fails(self):
        from plugins.fda_tools.lib.soc2_controls import A1_Availability, ControlStatus
        result = A1_Availability.check_backup_policy(
            backup_frequency_hours=48,
            last_restore_test_iso=_now_iso(delta_days=-15),
        )
        assert result.status == ControlStatus.FAIL

    def test_backup_restore_test_stale_fails(self):
        from plugins.fda_tools.lib.soc2_controls import A1_Availability, ControlStatus
        result = A1_Availability.check_backup_policy(
            backup_frequency_hours=6,
            last_restore_test_iso=_now_iso(delta_days=-120),
        )
        assert result.status == ControlStatus.FAIL

    def test_multi_az_passes(self):
        from plugins.fda_tools.lib.soc2_controls import A1_Availability, ControlStatus
        result = A1_Availability.check_multi_az(
            regions=["us-east-1"],
            availability_zones_per_region=3,
        )
        assert result.status == ControlStatus.PASS

    def test_single_az_fails(self):
        from plugins.fda_tools.lib.soc2_controls import A1_Availability, ControlStatus
        result = A1_Availability.check_multi_az(
            regions=["us-east-1"],
            availability_zones_per_region=1,
        )
        assert result.status == ControlStatus.FAIL


# ═════════════════════════════════════════════════════════════════════════════
# Control Registry
# ═════════════════════════════════════════════════════════════════════════════

class TestControlRegistry:

    def _full_passing_config(self):
        return {
            "access_control": {
                "defined_roles": ["admin", "ra_lead", "engineer", "viewer"],
                "min_password_length": 16,
                "mfa_required": True,
                "tls_version": "TLSv1.2+1.3",
                "hsts_enabled": True,
                "session_token_bytes": 32,
            },
            "operations": {
                "audit_log_table": "audit_events",
                "audit_append_only": True,
                "audit_rls_enabled": True,
                "health_endpoint": "/api/health",
                "alert_latency_ms": 60_000,
                "irp_exists": True,
                "irp_last_tested_iso": _now_iso(delta_days=-30),
            },
            "change_management": {
                "branch_protections": {
                    "required_approving_review_count": 1,
                    "required_status_checks": True,
                    "dismiss_stale_reviews": True,
                },
                "rollback_workflow_exists": True,
                "secret_patterns": ["AWS_KEY", "SUPABASE_KEY", "API_KEY", "SECRET_TOKEN"],
            },
            "availability": {
                "slo_target_percent": 99.9,
                "error_budget_window_days": 28,
                "backup_frequency_hours": 6,
                "last_restore_test_iso": _now_iso(delta_days=-15),
                "regions": ["us-east-1"],
                "azs_per_region": 3,
            },
        }

    def test_run_all_returns_compliance_report(self):
        from plugins.fda_tools.lib.soc2_controls import ControlRegistry, ComplianceReport
        registry = ControlRegistry(self._full_passing_config())
        report = registry.run_all()
        assert isinstance(report, ComplianceReport)

    def test_run_all_has_13_controls(self):
        from plugins.fda_tools.lib.soc2_controls import ControlRegistry
        registry = ControlRegistry(self._full_passing_config())
        report = registry.run_all()
        assert len(report.results) == 13  # 4 CC6 + 3 CC7 + 3 CC8 + 3 A1

    def test_run_all_passing_config_no_failures(self):
        from plugins.fda_tools.lib.soc2_controls import ControlRegistry
        registry = ControlRegistry(self._full_passing_config())
        report = registry.run_all()
        assert len(report.failed_controls()) == 0

    def test_run_all_empty_config_has_failures(self):
        from plugins.fda_tools.lib.soc2_controls import ControlRegistry
        registry = ControlRegistry({})
        report = registry.run_all()
        assert len(report.failed_controls()) > 0

    def test_summary_contains_pass_fail_counts(self):
        from plugins.fda_tools.lib.soc2_controls import ControlRegistry
        registry = ControlRegistry(self._full_passing_config())
        report = registry.run_all()
        summary = report.summary()
        assert "PASS" in summary

    def test_as_dict_is_serialisable(self):
        import json
        from plugins.fda_tools.lib.soc2_controls import ControlRegistry
        registry = ControlRegistry(self._full_passing_config())
        report = registry.run_all()
        d = report.as_dict()
        # Ensure it's JSON serialisable
        json.dumps(d)

    def test_run_criteria_cc6_only(self):
        from plugins.fda_tools.lib.soc2_controls import ControlRegistry, TrustServicesCriteria
        registry = ControlRegistry(self._full_passing_config())
        results = registry.run_criteria(TrustServicesCriteria.CC6)
        assert all(r.criteria == TrustServicesCriteria.CC6 for r in results)
        assert len(results) == 4


# ═════════════════════════════════════════════════════════════════════════════
# OWASP Input Validation (FDA-261)
# ═════════════════════════════════════════════════════════════════════════════

class TestOwaspInputValidation:

    def test_clean_input_passes(self):
        from plugins.fda_tools.lib.soc2_controls import sanitize_input
        result = sanitize_input("DQY", "product_code")
        assert result == "DQY"

    def test_sql_injection_detected(self):
        import pytest
        from plugins.fda_tools.lib.soc2_controls import sanitize_input
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_input("'; DROP TABLE users; --", "query")

    def test_or_injection_detected(self):
        import pytest
        from plugins.fda_tools.lib.soc2_controls import sanitize_input
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_input("1 OR 1=1", "id")

    def test_xss_script_tag_detected(self):
        import pytest
        from plugins.fda_tools.lib.soc2_controls import sanitize_input
        with pytest.raises(ValueError, match="XSS"):
            sanitize_input("<script>alert(1)</script>", "name")

    def test_xss_event_handler_detected(self):
        import pytest
        from plugins.fda_tools.lib.soc2_controls import sanitize_input
        with pytest.raises(ValueError, match="XSS"):
            sanitize_input('<img onerror="evil()">', "description")

    def test_path_traversal_detected(self):
        import pytest
        from plugins.fda_tools.lib.soc2_controls import sanitize_input
        with pytest.raises(ValueError, match="traversal"):
            sanitize_input("../../etc/passwd", "filename")

    def test_csrf_token_is_64_hex_chars(self):
        from plugins.fda_tools.lib.soc2_controls import generate_csrf_token
        token = generate_csrf_token()
        assert len(token) == 64
        assert re.match(r"^[0-9a-f]+$", token)

    def test_csrf_tokens_are_unique(self):
        from plugins.fda_tools.lib.soc2_controls import generate_csrf_token
        tokens = {generate_csrf_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_constant_time_compare_equal(self):
        from plugins.fda_tools.lib.soc2_controls import constant_time_compare
        assert constant_time_compare("abc", "abc") is True

    def test_constant_time_compare_not_equal(self):
        from plugins.fda_tools.lib.soc2_controls import constant_time_compare
        assert constant_time_compare("abc", "xyz") is False


# ═════════════════════════════════════════════════════════════════════════════
# FDA-256 — Electron release workflow structure
# ═════════════════════════════════════════════════════════════════════════════

class TestElectronReleaseWorkflow:

    def _load_workflow(self) -> str:
        # parents: [0]=tests, [1]=fda_tools, [2]=plugins, [3]=fda-tools (repo root)
        workflow_path = Path(__file__).parents[3] / ".github" / "workflows" / "electron-release.yml"
        return workflow_path.read_text(encoding="utf-8")

    def test_workflow_file_exists(self):
        workflow_path = Path(__file__).parents[3] / ".github" / "workflows" / "electron-release.yml"
        assert workflow_path.exists(), "electron-release.yml not found"

    def test_workflow_triggers_on_desktop_tag(self):
        content = self._load_workflow()
        assert "desktop" in content
        assert "tags:" in content

    def test_workflow_has_three_platform_jobs(self):
        content = self._load_workflow()
        assert "build-windows:" in content
        assert "build-macos:" in content
        assert "build-linux:" in content

    def test_workflow_uses_win_signing_secrets(self):
        content = self._load_workflow()
        assert "WIN_CSC_LINK" in content
        assert "WIN_CSC_KEY_PASSWORD" in content

    def test_workflow_uses_apple_signing_secrets(self):
        content = self._load_workflow()
        assert "APPLE_ID" in content
        assert "APPLE_APP_SPECIFIC_PASSWORD" in content
        assert "APPLE_TEAM_ID" in content

    def test_workflow_publishes_always(self):
        content = self._load_workflow()
        assert "--publish always" in content

    def test_workflow_uses_node_20(self):
        content = self._load_workflow()
        assert "node-version: '20'" in content

    def test_workflow_has_verify_job(self):
        content = self._load_workflow()
        assert "verify-release:" in content
        assert "needs:" in content
