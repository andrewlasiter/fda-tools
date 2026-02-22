"""
FDA-262  [SEC-011] SOC 2 Type II Controls Implementation
=========================================================
Implements the Trust Services Criteria (TSC) controls required for
SOC 2 Type II certification of the MDRP cloud platform.

Coverage
--------
CC6   — Logical and Physical Access Controls
CC7   — System Operations
CC8   — Change Management
A1    — Availability

Design principles
-----------------
- Controls are *executable* — each control has a check() method that
  returns a ControlResult (PASS / FAIL / NOT_APPLICABLE) with evidence.
- The ControlRegistry aggregates all controls for the compliance report.
- 21 CFR Part 11 audit trails satisfy CC6 and CC7 requirements.
- Evidence is structured so it can be exported to auditor tooling.

Usage
-----
    registry = ControlRegistry()
    report = registry.run_all()
    print(report.summary())
"""

from __future__ import annotations

import hmac
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class ControlStatus(Enum):
    PASS           = "PASS"
    FAIL           = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR          = "ERROR"


class TrustServicesCriteria(Enum):
    CC6 = "CC6 - Logical and Physical Access Controls"
    CC7 = "CC7 - System Operations"
    CC8 = "CC8 - Change Management"
    A1  = "A1 - Availability"


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ControlResult:
    """Result of a single control check."""
    control_id:  str
    criteria:    TrustServicesCriteria
    title:       str
    status:      ControlStatus
    evidence:    str
    remediation: str = ""
    checked_at:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details:     Dict[str, Any] = field(default_factory=dict)

    def passed(self) -> bool:
        return self.status == ControlStatus.PASS


@dataclass
class ComplianceReport:
    """Aggregated SOC 2 compliance report."""
    run_at:   str
    results:  List[ControlResult]
    platform: str = "MDRP Cloud"

    def summary(self) -> str:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed())
        failed = sum(1 for r in self.results if r.status == ControlStatus.FAIL)
        na     = sum(1 for r in self.results if r.status == ControlStatus.NOT_APPLICABLE)
        lines  = [
            f"SOC 2 Type II Control Report — {self.run_at}",
            f"Platform: {self.platform}",
            f"Controls: {total} total | {passed} PASS | {failed} FAIL | {na} N/A",
            "",
        ]
        for r in self.results:
            icon = "✓" if r.passed() else ("~" if r.status == ControlStatus.NOT_APPLICABLE else "✗")
            lines.append(f"  [{icon}] {r.control_id}: {r.title} — {r.status.value}")
            if r.status == ControlStatus.FAIL and r.remediation:
                lines.append(f"       → {r.remediation}")
        return "\n".join(lines)

    def failed_controls(self) -> List[ControlResult]:
        return [r for r in self.results if r.status == ControlStatus.FAIL]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "run_at":   self.run_at,
            "platform": self.platform,
            "results":  [
                {
                    "control_id":  r.control_id,
                    "criteria":    r.criteria.value,
                    "title":       r.title,
                    "status":      r.status.value,
                    "evidence":    r.evidence,
                    "remediation": r.remediation,
                    "checked_at":  r.checked_at,
                }
                for r in self.results
            ],
        }


# ── CC6 — Logical and Physical Access Controls ────────────────────────────────

class CC6_LogicalAccess:
    """
    CC6.1  — Logical access security measures restrict access to information
              assets to authorised individuals only.
    CC6.3  — Role-based access control (RBAC) restricts access to the minimum
              necessary privilege.
    CC6.6  — Logical access security measures for infrastructure include
              network segmentation and encryption in transit.
    CC6.7  — Multi-factor authentication (MFA) is required for all
              administrator and privileged user accounts.
    """

    REQUIRED_ROLES = frozenset(["admin", "ra_lead", "engineer", "viewer"])
    MIN_PASSWORD_LENGTH = 12

    @staticmethod
    def check_rbac(defined_roles: List[str]) -> ControlResult:
        """CC6.1 / CC6.3 — All four MDRP roles must be defined."""
        role_set = frozenset(defined_roles)
        missing  = CC6_LogicalAccess.REQUIRED_ROLES - role_set
        status   = ControlStatus.PASS if not missing else ControlStatus.FAIL
        return ControlResult(
            control_id  = "CC6.1",
            criteria    = TrustServicesCriteria.CC6,
            title       = "RBAC role completeness",
            status      = status,
            evidence    = f"Defined roles: {sorted(role_set)}",
            remediation = f"Add missing roles: {sorted(missing)}" if missing else "",
            details     = {"defined": sorted(role_set), "missing": sorted(missing)},
        )

    @staticmethod
    def check_password_policy(min_length: int, requires_mfa: bool) -> ControlResult:
        """CC6.7 — Password length ≥ 12 and MFA must be enforced."""
        length_ok = min_length >= CC6_LogicalAccess.MIN_PASSWORD_LENGTH
        status    = ControlStatus.PASS if (length_ok and requires_mfa) else ControlStatus.FAIL
        issues    = []
        if not length_ok:
            issues.append(f"min_length={min_length} < {CC6_LogicalAccess.MIN_PASSWORD_LENGTH}")
        if not requires_mfa:
            issues.append("MFA not required")
        return ControlResult(
            control_id  = "CC6.7",
            criteria    = TrustServicesCriteria.CC6,
            title       = "Password policy and MFA enforcement",
            status      = status,
            evidence    = f"min_length={min_length}, mfa={requires_mfa}",
            remediation = "; ".join(issues) if issues else "",
        )

    @staticmethod
    def check_tls_enforcement(tls_version: str, hsts_enabled: bool) -> ControlResult:
        """CC6.6 — TLS 1.2+ and HSTS must be enabled for all endpoints."""
        tls_ok = tls_version in ("TLSv1.2", "TLSv1.3", "TLSv1.2+1.3")
        status  = ControlStatus.PASS if (tls_ok and hsts_enabled) else ControlStatus.FAIL
        issues  = []
        if not tls_ok:
            issues.append(f"TLS version '{tls_version}' not acceptable (need 1.2+)")
        if not hsts_enabled:
            issues.append("HSTS not enabled")
        return ControlResult(
            control_id  = "CC6.6",
            criteria    = TrustServicesCriteria.CC6,
            title       = "Encryption in transit (TLS + HSTS)",
            status      = status,
            evidence    = f"tls={tls_version}, hsts={hsts_enabled}",
            remediation = "; ".join(issues) if issues else "",
        )

    @staticmethod
    def check_session_token_entropy(token_bytes: int) -> ControlResult:
        """CC6.1 — Session tokens must use ≥ 32 bytes of cryptographic entropy."""
        ok     = token_bytes >= 32
        status = ControlStatus.PASS if ok else ControlStatus.FAIL
        return ControlResult(
            control_id  = "CC6.1b",
            criteria    = TrustServicesCriteria.CC6,
            title       = "Session token entropy",
            status      = status,
            evidence    = f"token_bytes={token_bytes}",
            remediation = "Use secrets.token_bytes(32) or equivalent" if not ok else "",
            details     = {
                "sample_token_hex": secrets.token_hex(token_bytes),
                "required_bytes":   32,
            },
        )


# ── CC7 — System Operations ───────────────────────────────────────────────────

class CC7_SystemOperations:
    """
    CC7.1  — Monitoring infrastructure detects and reports anomalies.
    CC7.2  — Incident response procedures are documented and tested.
    CC7.3  — Security events are logged to an immutable audit trail
              (21 CFR Part 11 compliant).
    """

    @staticmethod
    def check_audit_log_immutability(
        log_table: str,
        has_append_only: bool,
        has_row_level_security: bool,
    ) -> ControlResult:
        """CC7.3 — Audit log must be append-only and protected by RLS."""
        status = ControlStatus.PASS if (has_append_only and has_row_level_security) else ControlStatus.FAIL
        issues = []
        if not has_append_only:
            issues.append("audit table is not append-only (missing DDL trigger or policy)")
        if not has_row_level_security:
            issues.append("row-level security not enabled on audit table")
        return ControlResult(
            control_id  = "CC7.3",
            criteria    = TrustServicesCriteria.CC7,
            title       = "Immutable audit log (21 CFR Part 11)",
            status      = status,
            evidence    = f"table={log_table}, append_only={has_append_only}, rls={has_row_level_security}",
            remediation = "; ".join(issues) if issues else "",
        )

    @staticmethod
    def check_health_monitoring(
        health_endpoint: str,
        alert_latency_ms: int,
    ) -> ControlResult:
        """CC7.1 — Health endpoint must exist and alerting latency ≤ 5 min (300 000 ms)."""
        endpoint_ok = bool(health_endpoint)
        latency_ok  = alert_latency_ms <= 300_000
        status      = ControlStatus.PASS if (endpoint_ok and latency_ok) else ControlStatus.FAIL
        issues      = []
        if not endpoint_ok:
            issues.append("No health endpoint configured")
        if not latency_ok:
            issues.append(f"Alert latency {alert_latency_ms}ms exceeds 300 000ms SLA")
        return ControlResult(
            control_id  = "CC7.1",
            criteria    = TrustServicesCriteria.CC7,
            title       = "Health monitoring and alerting latency",
            status      = status,
            evidence    = f"endpoint={health_endpoint}, alert_latency_ms={alert_latency_ms}",
            remediation = "; ".join(issues) if issues else "",
        )

    @staticmethod
    def check_incident_response_plan(plan_exists: bool, last_tested_iso: Optional[str]) -> ControlResult:
        """CC7.2 — IRP must exist and have been tested within the past 12 months."""
        if not plan_exists:
            return ControlResult(
                control_id  = "CC7.2",
                criteria    = TrustServicesCriteria.CC7,
                title       = "Incident response plan",
                status      = ControlStatus.FAIL,
                evidence    = "No incident response plan found",
                remediation = "Document and publish an IRP with roles, escalation paths, and SLAs",
            )

        tested_recently = False
        if last_tested_iso:
            try:
                last_tested = datetime.fromisoformat(last_tested_iso)
                if last_tested.tzinfo is None:
                    last_tested = last_tested.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                tested_recently = (now - last_tested).days <= 365
            except ValueError:
                pass

        status = ControlStatus.PASS if tested_recently else ControlStatus.FAIL
        return ControlResult(
            control_id  = "CC7.2",
            criteria    = TrustServicesCriteria.CC7,
            title       = "Incident response plan",
            status      = status,
            evidence    = f"plan_exists=True, last_tested={last_tested_iso}",
            remediation = "Conduct and document an IRP tabletop exercise (required annually)" if not tested_recently else "",
        )


# ── CC8 — Change Management ───────────────────────────────────────────────────

class CC8_ChangeManagement:
    """
    CC8.1  — Changes to infrastructure and software follow an authorised
              change management process (PR review, CI/CD gates, rollback).
    """

    @staticmethod
    def check_pr_review_policy(
        branch_protections: Dict[str, Any],
    ) -> ControlResult:
        """
        CC8.1 — master branch must require ≥ 1 approving review, status checks,
        and dismiss stale reviews.
        """
        required_reviews = branch_protections.get("required_approving_review_count", 0)
        checks_required  = branch_protections.get("required_status_checks", False)
        dismiss_stale    = branch_protections.get("dismiss_stale_reviews", False)

        issues = []
        if required_reviews < 1:
            issues.append("require at least 1 approving PR review")
        if not checks_required:
            issues.append("require passing CI status checks before merge")
        if not dismiss_stale:
            issues.append("enable 'dismiss stale reviews on new pushes'")

        status = ControlStatus.PASS if not issues else ControlStatus.FAIL
        return ControlResult(
            control_id  = "CC8.1",
            criteria    = TrustServicesCriteria.CC8,
            title       = "PR review and branch protection policy",
            status      = status,
            evidence    = (
                f"required_reviews={required_reviews}, "
                f"ci_checks={checks_required}, "
                f"dismiss_stale={dismiss_stale}"
            ),
            remediation = "; ".join(issues) if issues else "",
        )

    @staticmethod
    def check_rollback_capability(rollback_workflow_exists: bool) -> ControlResult:
        """CC8.1 — A documented rollback procedure must exist and be executable."""
        status = ControlStatus.PASS if rollback_workflow_exists else ControlStatus.FAIL
        return ControlResult(
            control_id  = "CC8.1b",
            criteria    = TrustServicesCriteria.CC8,
            title       = "Rollback capability",
            status      = status,
            evidence    = f"rollback_workflow={rollback_workflow_exists}",
            remediation = "Create .github/workflows/rollback.yml" if not rollback_workflow_exists else "",
        )

    @staticmethod
    def check_secret_scanning(
        secret_patterns_blocked: List[str],
    ) -> ControlResult:
        """CC8.1 — CI must prevent secrets from being committed to the repository."""
        # Minimum: check for AWS keys, generic API keys, Supabase keys
        REQUIRED_PATTERNS = ["aws_", "supabase", "api_key", "secret"]
        covered = [p for p in REQUIRED_PATTERNS if any(p in s.lower() for s in secret_patterns_blocked)]
        missing = [p for p in REQUIRED_PATTERNS if p not in [c for c in covered]]
        status  = ControlStatus.PASS if not missing else ControlStatus.FAIL
        return ControlResult(
            control_id  = "CC8.1c",
            criteria    = TrustServicesCriteria.CC8,
            title       = "Secret scanning in CI",
            status      = status,
            evidence    = f"patterns_covered={covered}",
            remediation = f"Add secret-scanning patterns for: {missing}" if missing else "",
        )


# ── A1 — Availability ─────────────────────────────────────────────────────────

class A1_Availability:
    """
    A1.1  — Availability commitments and SLOs are defined.
    A1.2  — Infrastructure is designed for fault tolerance and recovery.
    A1.3  — Backup and recovery procedures are tested regularly.
    """

    SLO_TARGET_PERCENT = 99.9  # Three nines

    @staticmethod
    def check_slo_definition(
        target_percent: float,
        error_budget_window_days: int,
    ) -> ControlResult:
        """A1.1 — SLO must be defined at ≥ 99.9% with a rolling error budget window."""
        meets_target    = target_percent >= A1_Availability.SLO_TARGET_PERCENT
        valid_window    = error_budget_window_days in (7, 14, 28, 30)
        status          = ControlStatus.PASS if (meets_target and valid_window) else ControlStatus.FAIL
        issues          = []
        if not meets_target:
            issues.append(f"SLO target {target_percent}% < required {A1_Availability.SLO_TARGET_PERCENT}%")
        if not valid_window:
            issues.append(f"error budget window {error_budget_window_days}d is not standard (7/14/28/30)")
        return ControlResult(
            control_id  = "A1.1",
            criteria    = TrustServicesCriteria.A1,
            title       = "SLO definition",
            status      = status,
            evidence    = f"target={target_percent}%, window={error_budget_window_days}d",
            remediation = "; ".join(issues) if issues else "",
        )

    @staticmethod
    def check_backup_policy(
        backup_frequency_hours: int,
        last_restore_test_iso: Optional[str],
    ) -> ControlResult:
        """
        A1.3 — Backups must run ≥ daily (≤ 24 h) and a restore test must have
               been completed within the past 90 days.
        """
        freq_ok    = backup_frequency_hours <= 24
        restore_ok = False
        if last_restore_test_iso:
            try:
                last = datetime.fromisoformat(last_restore_test_iso)
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                restore_ok = (datetime.now(timezone.utc) - last).days <= 90
            except ValueError:
                pass

        issues = []
        if not freq_ok:
            issues.append(f"backup_frequency {backup_frequency_hours}h > 24h SLA")
        if not restore_ok:
            issues.append("No restore test recorded in the past 90 days")

        status = ControlStatus.PASS if (freq_ok and restore_ok) else ControlStatus.FAIL
        return ControlResult(
            control_id  = "A1.3",
            criteria    = TrustServicesCriteria.A1,
            title       = "Backup frequency and restore testing",
            status      = status,
            evidence    = f"freq={backup_frequency_hours}h, last_restore={last_restore_test_iso}",
            remediation = "; ".join(issues) if issues else "",
        )

    @staticmethod
    def check_multi_az(
        regions: List[str],
        availability_zones_per_region: int,
    ) -> ControlResult:
        """A1.2 — Platform must be deployed across ≥ 2 AZs for fault tolerance."""
        multi_az = availability_zones_per_region >= 2
        status   = ControlStatus.PASS if multi_az else ControlStatus.FAIL
        return ControlResult(
            control_id  = "A1.2",
            criteria    = TrustServicesCriteria.A1,
            title       = "Multi-AZ fault tolerance",
            status      = status,
            evidence    = f"regions={regions}, azs_per_region={availability_zones_per_region}",
            remediation = "Deploy across at least 2 availability zones" if not multi_az else "",
        )


# ── Control Registry ─────────────────────────────────────────────────────────

class ControlRegistry:
    """
    Aggregates all SOC 2 controls and runs them against the current
    platform configuration.

    In production, `config` is loaded from the environment / Terraform
    state / infrastructure-as-code outputs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}

    # -- CC6 checks -----------------------------------------------------------

    def _cc6_checks(self) -> List[ControlResult]:
        cfg = self._config.get("access_control", {})
        return [
            CC6_LogicalAccess.check_rbac(
                defined_roles=cfg.get("defined_roles", []),
            ),
            CC6_LogicalAccess.check_password_policy(
                min_length=cfg.get("min_password_length", 0),
                requires_mfa=cfg.get("mfa_required", False),
            ),
            CC6_LogicalAccess.check_tls_enforcement(
                tls_version=cfg.get("tls_version", ""),
                hsts_enabled=cfg.get("hsts_enabled", False),
            ),
            CC6_LogicalAccess.check_session_token_entropy(
                token_bytes=cfg.get("session_token_bytes", 0),
            ),
        ]

    # -- CC7 checks -----------------------------------------------------------

    def _cc7_checks(self) -> List[ControlResult]:
        cfg = self._config.get("operations", {})
        return [
            CC7_SystemOperations.check_audit_log_immutability(
                log_table=cfg.get("audit_log_table", ""),
                has_append_only=cfg.get("audit_append_only", False),
                has_row_level_security=cfg.get("audit_rls_enabled", False),
            ),
            CC7_SystemOperations.check_health_monitoring(
                health_endpoint=cfg.get("health_endpoint", ""),
                alert_latency_ms=cfg.get("alert_latency_ms", 999_999),
            ),
            CC7_SystemOperations.check_incident_response_plan(
                plan_exists=cfg.get("irp_exists", False),
                last_tested_iso=cfg.get("irp_last_tested_iso", None),
            ),
        ]

    # -- CC8 checks -----------------------------------------------------------

    def _cc8_checks(self) -> List[ControlResult]:
        cfg = self._config.get("change_management", {})
        return [
            CC8_ChangeManagement.check_pr_review_policy(
                branch_protections=cfg.get("branch_protections", {}),
            ),
            CC8_ChangeManagement.check_rollback_capability(
                rollback_workflow_exists=cfg.get("rollback_workflow_exists", False),
            ),
            CC8_ChangeManagement.check_secret_scanning(
                secret_patterns_blocked=cfg.get("secret_patterns", []),
            ),
        ]

    # -- A1 checks ------------------------------------------------------------

    def _a1_checks(self) -> List[ControlResult]:
        cfg = self._config.get("availability", {})
        return [
            A1_Availability.check_slo_definition(
                target_percent=cfg.get("slo_target_percent", 0.0),
                error_budget_window_days=cfg.get("error_budget_window_days", 0),
            ),
            A1_Availability.check_backup_policy(
                backup_frequency_hours=cfg.get("backup_frequency_hours", 999),
                last_restore_test_iso=cfg.get("last_restore_test_iso", None),
            ),
            A1_Availability.check_multi_az(
                regions=cfg.get("regions", []),
                availability_zones_per_region=cfg.get("azs_per_region", 0),
            ),
        ]

    # -- Public API -----------------------------------------------------------

    def run_all(self) -> ComplianceReport:
        """Run all controls and return a ComplianceReport."""
        results = (
            self._cc6_checks()
            + self._cc7_checks()
            + self._cc8_checks()
            + self._a1_checks()
        )
        return ComplianceReport(
            run_at  = datetime.now(timezone.utc).isoformat(),
            results = results,
        )

    def run_criteria(self, criteria: TrustServicesCriteria) -> List[ControlResult]:
        """Run only the controls for a specific TSC category."""
        all_checks = {
            TrustServicesCriteria.CC6: self._cc6_checks,
            TrustServicesCriteria.CC7: self._cc7_checks,
            TrustServicesCriteria.CC8: self._cc8_checks,
            TrustServicesCriteria.A1:  self._a1_checks,
        }
        return all_checks[criteria]()


# ── Input validation helpers (OWASP A01 — Broken Access Control) ────────────
# Used by bridge API request handlers.

_SQL_INJECTION_PATTERN  = re.compile(
    r"('|--|;|\bOR\b|\bAND\b|\bDROP\b|\bINSERT\b|\bDELETE\b|\bUPDATE\b|\bUNION\b)",
    re.IGNORECASE,
)
_XSS_PATTERN = re.compile(r"<\s*script|javascript\s*:|on\w+\s*=", re.IGNORECASE)
_PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\")


def sanitize_input(value: str, field_name: str = "input") -> str:
    """
    Lightweight input sanitisation for API boundary values.

    Raises ValueError on detected injection patterns.
    Does NOT replace or escape — fail-fast on suspicious input.
    """
    if _SQL_INJECTION_PATTERN.search(value):
        raise ValueError(f"Potential SQL injection detected in field '{field_name}'")
    if _XSS_PATTERN.search(value):
        raise ValueError(f"Potential XSS pattern detected in field '{field_name}'")
    if _PATH_TRAVERSAL_PATTERN.search(value):
        raise ValueError(f"Path traversal pattern detected in field '{field_name}'")
    return value


def generate_csrf_token() -> str:
    """Generate a cryptographically secure 256-bit CSRF token."""
    return secrets.token_hex(32)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Timing-safe string comparison for HMAC / token validation.
    Prevents timing side-channel attacks on authentication tokens.
    """
    return hmac.compare_digest(a.encode(), b.encode())
