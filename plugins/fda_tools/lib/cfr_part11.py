"""
FDA-263  [SEC-012] 21 CFR Part 11 Compliance Audit
====================================================
Implements the six core controls required by 21 CFR Part 11 for electronic
records and electronic signatures used in FDA regulatory submissions.

21 CFR Part 11 requirements addressed
--------------------------------------
§11.10(a)  — System validation (ability to generate accurate copies)
§11.10(b)  — Ability to generate accurate and complete copies for inspection
§11.10(c)  — Record protection and archiving (retention ≥ record lifetime)
§11.10(d)  — Limiting system access to authorised individuals only
§11.10(e)  — Secure, computer-generated, time-stamped audit trails
§11.10(f)  — Sequence of steps to ensure record integrity
§11.10(g)  — Authority checks ensuring only authorised individuals can use the system
§11.10(h)  — Device checks to ensure valid data input from the source
§11.10(i)  — Education and training
§11.50     — Electronic signature components and controls
§11.70     — Electronic signature/record link (signature permanently bound to record)

Architecture
-------------
The `AuditRecord` is the atom of Part 11 compliance.  Every electronic record
mutation must produce an `AuditRecord` with:
  - User identity (user_id, display_name)
  - Action taken (CREATE / UPDATE / DELETE / SIGN / APPROVE / EXPORT)
  - Timestamp in UTC (timezone-aware ISO 8601)
  - Record fingerprint (SHA-256 of the content)
  - Optional electronic signature

The `Part11AuditLog` stores records in an append-only list.  In production
this maps to a PostgreSQL append-only table protected by Row Level Security
and a `BEFORE UPDATE/DELETE` trigger that raises an exception.

Usage
-----
    log      = Part11AuditLog()
    record   = AuditRecord.create(
        user_id     = "alice@example.com",
        action      = AuditAction.UPDATE,
        record_type = "submission_section",
        record_id   = "section-510k-desc",
        content     = section_html,
    )
    log.append(record)

    # Electronic signature
    sig = ElectronicSignature.sign(record, user_id="alice@example.com",
                                   meaning="I authored this section")
    record.attach_signature(sig)

    # Export for FDA inspection
    report = Part11ComplianceReport.generate(log)
    print(report.summary())
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, ClassVar, Dict, List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class AuditAction(Enum):
    """Actions that must be tracked per 21 CFR §11.10(e)."""
    CREATE   = "CREATE"
    READ     = "READ"
    UPDATE   = "UPDATE"
    DELETE   = "DELETE"
    SIGN     = "SIGN"
    APPROVE  = "APPROVE"
    REJECT   = "REJECT"
    EXPORT   = "EXPORT"
    LOGIN    = "LOGIN"
    LOGOUT   = "LOGOUT"
    ACCESS_DENIED = "ACCESS_DENIED"


class RecordIntegrity(Enum):
    """Integrity status of an audit record."""
    VALID       = "VALID"
    TAMPERED    = "TAMPERED"
    UNVERIFIED  = "UNVERIFIED"


class SignatureStatus(Enum):
    """Electronic signature validity status."""
    VALID    = "VALID"
    INVALID  = "INVALID"
    ABSENT   = "ABSENT"


# ── Electronic signature ──────────────────────────────────────────────────────

@dataclass
class ElectronicSignature:
    """
    §11.50 — Electronic signature for a specific audit record.

    The signature is a keyed HMAC-SHA256 over the record fingerprint,
    binding the signer's identity and stated meaning to the content hash.

    Production: replace HMAC key with an HSM-managed key or PKI certificate.
    """
    signer_id:   str
    signer_name: str
    meaning:     str       # e.g. "I authored this document"
    timestamp:   str       # ISO 8601 UTC
    signature:   str       # hex HMAC-SHA256
    record_hash: str       # SHA-256 fingerprint of the signed record

    @classmethod
    def sign(
        cls,
        record_hash: str,
        signer_id: str,
        signer_name: str,
        meaning: str,
        signing_key: Optional[str] = None,
    ) -> "ElectronicSignature":
        """
        Create a new electronic signature over a record hash.

        Args:
            record_hash:  SHA-256 hex digest of the record content.
            signer_id:    User ID (email or UUID) of the signer.
            signer_name:  Display name of the signer.
            meaning:      Stated intent of the signature.
            signing_key:  HMAC key (hex). Defaults to `CFR_PART11_SIGNING_KEY` env var.
        """
        key = signing_key or os.environ.get("CFR_PART11_SIGNING_KEY", "")
        if not key:
            raise ValueError(
                "CFR_PART11_SIGNING_KEY is not configured. "
                "Set the environment variable to a stable HMAC key before signing. "
                "Ephemeral keys are forbidden — they make signatures unverifiable, "
                "violating 21 CFR §11.50 and §11.70."
            )
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = f"{record_hash}|{signer_id}|{meaning}|{timestamp}".encode("utf-8")
        sig_hex = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return cls(
            signer_id   = signer_id,
            signer_name = signer_name,
            meaning     = meaning,
            timestamp   = timestamp,
            signature   = sig_hex,
            record_hash = record_hash,
        )

    def verify(self, signing_key: Optional[str] = None) -> bool:
        """
        Verify the HMAC signature.  Returns True if the signature is valid.
        Uses constant-time comparison to prevent timing attacks.
        """
        key = signing_key or os.environ.get("CFR_PART11_SIGNING_KEY", "")
        if not key:
            return False
        payload = f"{self.record_hash}|{self.signer_id}|{self.meaning}|{self.timestamp}".encode()
        expected = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)

    def to_dict(self) -> Dict[str, str]:
        return {
            "signer_id":   self.signer_id,
            "signer_name": self.signer_name,
            "meaning":     self.meaning,
            "timestamp":   self.timestamp,
            "signature":   self.signature,
            "record_hash": self.record_hash,
        }


# ── Audit record ──────────────────────────────────────────────────────────────

@dataclass
class AuditRecord:
    """
    §11.10(e) — Computer-generated, time-stamped audit trail entry.

    An AuditRecord is immutable once created.  The `fingerprint` field is
    the SHA-256 hash of the content at the time of recording.  Any post-hoc
    modification to `content` will produce a fingerprint mismatch detectable
    by `verify_integrity()`.
    """
    record_id:    str            # Unique ID of this audit entry
    user_id:      str            # Operator identity (human or AI agent)
    display_name: str            # Human-readable name for reports
    action:       AuditAction    # What was done
    record_type:  str            # Type of electronic record (e.g. "submission_section")
    subject_id:   str            # ID of the record being acted upon
    timestamp:    str            # UTC ISO 8601 — §11.10(e) requires timezone
    fingerprint:  str            # SHA-256 of `content` at capture time
    content:      str = ""       # Serialised record content (may be empty for LOGINs)
    agent_id:     Optional[str] = None  # AI agent identity (e.g. "fda-drafting-agent"); §11.70
    metadata:     Dict[str, Any] = field(default_factory=dict)
    signature:    Optional[ElectronicSignature] = None

    @classmethod
    def create(
        cls,
        user_id:      str,
        display_name: str,
        action:       AuditAction,
        record_type:  str,
        subject_id:   str,
        content:      str = "",
        metadata:     Optional[Dict[str, Any]] = None,
    ) -> "AuditRecord":
        """Construct a new AuditRecord with an automatic timestamp and fingerprint."""
        timestamp   = datetime.now(timezone.utc).isoformat()
        fingerprint = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record_id   = secrets.token_hex(16)
        return cls(
            record_id    = record_id,
            user_id      = user_id,
            display_name = display_name,
            action       = action,
            record_type  = record_type,
            subject_id   = subject_id,
            timestamp    = timestamp,
            fingerprint  = fingerprint,
            content      = content,
            metadata     = metadata or {},
        )

    def verify_integrity(self) -> RecordIntegrity:
        """
        Recompute SHA-256 of `content` and compare to stored `fingerprint`.
        Returns TAMPERED if they differ.
        """
        computed = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if hmac.compare_digest(computed, self.fingerprint):
            return RecordIntegrity.VALID
        return RecordIntegrity.TAMPERED

    def attach_signature(self, sig: ElectronicSignature) -> None:
        """§11.70 — Link the electronic signature to this record permanently."""
        self.signature = sig

    def signature_status(self, signing_key: Optional[str] = None) -> SignatureStatus:
        if self.signature is None:
            return SignatureStatus.ABSENT
        return SignatureStatus.VALID if self.signature.verify(signing_key) else SignatureStatus.INVALID

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "record_id":    self.record_id,
            "user_id":      self.user_id,
            "display_name": self.display_name,
            "action":       self.action.value,
            "record_type":  self.record_type,
            "subject_id":   self.subject_id,
            "timestamp":    self.timestamp,
            "fingerprint":  self.fingerprint,
            "metadata":     self.metadata,
        }
        if self.signature:
            d["signature"] = self.signature.to_dict()
        return d


# ── Append-only audit log ─────────────────────────────────────────────────────

class Part11AuditLog:
    """
    §11.10(e) — Secure, computer-generated, time-stamped audit trail.

    The log is append-only; existing records cannot be modified or removed.
    In production: backed by a PostgreSQL append-only table with:
      - A BEFORE UPDATE/DELETE trigger that raises an exception
      - Row Level Security allowing INSERT but not UPDATE/DELETE
      - Periodic archival to immutable object storage (S3 WORM / Azure Immutable Blob)
    """

    def __init__(self) -> None:
        self._records: List[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        """Add a record to the audit log. Raises if record_id already exists."""
        existing_ids = {r.record_id for r in self._records}
        if record.record_id in existing_ids:
            raise ValueError(f"Duplicate record_id: {record.record_id}")
        self._records.append(record)

    def __len__(self) -> int:
        return len(self._records)

    def records(self) -> List[AuditRecord]:
        """Return a snapshot (copy) of the records list."""
        return list(self._records)

    def filter(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        record_type: Optional[str] = None,
        subject_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[AuditRecord]:
        """
        Return filtered records for inspection or reporting.
        All parameters are optional; unspecified parameters match all records.
        """
        results = list(self._records)
        if user_id:
            results = [r for r in results if r.user_id == user_id]
        if action:
            results = [r for r in results if r.action == action]
        if record_type:
            results = [r for r in results if r.record_type == record_type]
        if subject_id:
            results = [r for r in results if r.subject_id == subject_id]
        if since:
            since_tz = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
            results = [r for r in results if _parse_ts(r.timestamp) >= since_tz]
        if until:
            until_tz = until if until.tzinfo else until.replace(tzinfo=timezone.utc)
            results = [r for r in results if _parse_ts(r.timestamp) <= until_tz]
        return results

    def verify_all(self) -> Dict[str, RecordIntegrity]:
        """Verify integrity of all records. Returns {record_id: integrity_status}."""
        return {r.record_id: r.verify_integrity() for r in self._records}

    def export_json(self) -> str:
        """§11.10(b) — Export complete audit log as JSON for FDA inspection."""
        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(self._records),
            "records": [r.to_dict() for r in self._records],
        }
        return json.dumps(payload, indent=2)


def _parse_ts(iso: str) -> datetime:
    dt = datetime.fromisoformat(iso)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── Access control checks — §11.10(d) and §11.10(g) ─────────────────────────

@dataclass
class AccessControlPolicy:
    """
    §11.10(d)(g) — Limiting access to authorised users with authority checks.

    Maps record_type + action to the minimum required MdrpRole.
    """
    # action → minimum role value required
    # Roles in ascending privilege order: viewer < engineer < ra_lead < admin
    _ROLE_ORDER: ClassVar[List[str]] = ["viewer", "engineer", "ra_lead", "admin"]

    # Default policy: read = viewer; create/update = engineer; approve/sign = ra_lead; delete = admin
    _DEFAULT_POLICY: ClassVar[Dict[str, str]] = {
        "READ":          "viewer",
        "CREATE":        "engineer",
        "UPDATE":        "engineer",
        "EXPORT":        "engineer",
        "SIGN":          "ra_lead",
        "APPROVE":       "ra_lead",
        "REJECT":        "ra_lead",
        "DELETE":        "admin",
        "LOGIN":         "viewer",
        "LOGOUT":        "viewer",
        "ACCESS_DENIED": "viewer",
    }

    overrides: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def required_role(self, action: AuditAction, record_type: str = "") -> str:
        """Return the minimum role name required for this action + record_type."""
        # Check type-specific override first
        if record_type in self.overrides and action.value in self.overrides[record_type]:
            return self.overrides[record_type][action.value]
        return self._DEFAULT_POLICY.get(action.value, "ra_lead")

    def is_authorised(
        self,
        user_role: str,
        action: AuditAction,
        record_type: str = "",
    ) -> bool:
        """Return True if user_role meets or exceeds the required role for this action."""
        required = self.required_role(action, record_type)
        try:
            user_idx     = self._ROLE_ORDER.index(user_role.lower())
            required_idx = self._ROLE_ORDER.index(required.lower())
            return user_idx >= required_idx
        except ValueError:
            return False


# ── 21 CFR Part 11 compliance report ─────────────────────────────────────────

@dataclass
class Part11Finding:
    """A single compliance finding from the audit."""
    control:     str   # e.g. "§11.10(e) — Audit trail"
    status:      str   # "PASS" | "FAIL" | "PARTIAL"
    evidence:    str
    remediation: str = ""


@dataclass
class Part11ComplianceReport:
    """
    §11.10(b) — Complete compliance report for FDA inspection.
    Generated from a Part11AuditLog and configuration introspection.
    """
    generated_at:  str
    record_count:  int
    findings:      List[Part11Finding]
    integrity_map: Dict[str, RecordIntegrity]

    @classmethod
    def generate(
        cls,
        log: Part11AuditLog,
        config: Optional[Dict[str, Any]] = None,
    ) -> "Part11ComplianceReport":
        cfg = config or {}
        findings: List[Part11Finding] = []

        # §11.10(e) — Audit trail present and populated
        findings.append(Part11Finding(
            control  = "§11.10(e) — Time-stamped audit trail",
            status   = "PASS" if len(log) > 0 else "PARTIAL",
            evidence = f"{len(log)} audit records found",
            remediation = "Ensure all record mutations produce an AuditRecord" if len(log) == 0 else "",
        ))

        # §11.10(e) — All records have timezone-aware timestamps
        bad_ts = [r.record_id for r in log.records() if not _has_timezone(r.timestamp)]
        findings.append(Part11Finding(
            control  = "§11.10(e) — UTC timestamps",
            status   = "PASS" if not bad_ts else "FAIL",
            evidence = f"{len(bad_ts)} records with non-UTC timestamps" if bad_ts
                       else "All timestamps are timezone-aware UTC",
            remediation = "Use datetime.now(timezone.utc) for all AuditRecord timestamps" if bad_ts else "",
        ))

        # §11.10(f) — Record integrity (no tampering)
        integrity_map = log.verify_all()
        tampered = [rid for rid, status in integrity_map.items()
                    if status == RecordIntegrity.TAMPERED]
        findings.append(Part11Finding(
            control  = "§11.10(f) — Record integrity (SHA-256 fingerprint)",
            status   = "PASS" if not tampered else "FAIL",
            evidence = f"{len(tampered)} tampered records detected" if tampered
                       else f"All {len(integrity_map)} records pass integrity check",
            remediation = f"Investigate and quarantine: {tampered}" if tampered else "",
        ))

        # §11.50 — Electronic signatures on approved records
        approved = log.filter(action=AuditAction.APPROVE)
        unsigned = [r.record_id for r in approved if r.signature_status() == SignatureStatus.ABSENT]
        findings.append(Part11Finding(
            control  = "§11.50 — Electronic signatures on approved records",
            status   = "PASS" if not unsigned else "FAIL",
            evidence = f"{len(unsigned)} approved records lack signatures" if unsigned
                       else f"All {len(approved)} approved records are signed",
            remediation = "Call record.attach_signature() before marking APPROVE" if unsigned else "",
        ))

        # §11.10(d) — Retention policy configured
        retention_days = cfg.get("retention_days", 0)
        findings.append(Part11Finding(
            control  = "§11.10(c) — Record retention policy",
            status   = "PASS" if retention_days >= 3650 else "FAIL",  # ≥ 10 years per GCP
            evidence = f"Retention configured: {retention_days} days",
            remediation = "Configure retention ≥ 3650 days (10 years) for regulatory records" if retention_days < 3650 else "",
        ))

        # §11.10(i) — Training records exist
        # Supports both legacy bool flag and richer training_count/topics from
        # training_records.TrainingRecordStore.compliance_summary().
        has_training  = cfg.get("training_records_exist", False)
        train_count   = cfg.get("training_count", 0)
        train_topics  = cfg.get("part11_topics_covered", [])
        train_users   = cfg.get("training_users", [])
        # Either legacy flag OR explicit count satisfies the check
        compliant     = has_training or train_count > 0
        if compliant and train_topics:
            evidence = (
                f"Training records: {train_count} record(s), "
                f"{len(train_users)} user(s). Part 11 topics covered: "
                + ", ".join(train_topics)
            )
        elif compliant:
            evidence = f"Training records present ({train_count or 'legacy flag'})"
        else:
            evidence = "No training records found — §11.10(i) requires documented training"
        findings.append(Part11Finding(
            control  = "§11.10(i) — Training records",
            status   = "PASS" if compliant else "FAIL",
            evidence = evidence,
            remediation = (
                "Add training records via POST /compliance/training. "
                "Cover topics: part_11_overview, electronic_signatures, "
                "audit_trail_management per §11.10(i)."
            ) if not compliant else "",
        ))

        return cls(
            generated_at  = datetime.now(timezone.utc).isoformat(),
            record_count  = len(log),
            findings      = findings,
            integrity_map = integrity_map,
        )

    def summary(self) -> str:
        total  = len(self.findings)
        passed = sum(1 for f in self.findings if f.status == "PASS")
        failed = sum(1 for f in self.findings if f.status == "FAIL")
        lines  = [
            f"21 CFR Part 11 Compliance Report — {self.generated_at}",
            f"Records audited: {self.record_count}",
            f"Controls: {total} | PASS: {passed} | FAIL: {failed}",
            "",
        ]
        for f in self.findings:
            icon = "✓" if f.status == "PASS" else "✗"
            lines.append(f"  [{icon}] {f.control}")
            lines.append(f"       Evidence: {f.evidence}")
            if f.remediation:
                lines.append(f"       → {f.remediation}")
        return "\n".join(lines)

    def passed(self) -> bool:
        return all(f.status == "PASS" for f in self.findings)

    def failed_controls(self) -> List[Part11Finding]:
        return [f for f in self.findings if f.status == "FAIL"]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "generated_at":  self.generated_at,
            "record_count":  self.record_count,
            "findings": [
                {
                    "control":     f.control,
                    "status":      f.status,
                    "evidence":    f.evidence,
                    "remediation": f.remediation,
                }
                for f in self.findings
            ],
        }


def _has_timezone(iso: str) -> bool:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.tzinfo is not None
    except ValueError:
        return False


# ── Convenience decorator ─────────────────────────────────────────────────────

def audit(
    log: Part11AuditLog,
    user_id: str,
    display_name: str,
    action: AuditAction,
    record_type: str,
    subject_id: str,
) -> Callable:
    """
    Decorator that automatically appends an AuditRecord to `log` after the
    decorated function runs.  The return value of the function is serialised
    as the audit record `content`.

    Example::

        @audit(log, user_id="alice", display_name="Alice",
               action=AuditAction.UPDATE, record_type="section",
               subject_id="section-desc")
        def update_section(html: str) -> str:
            return html
    """
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            content = json.dumps(result, default=str) if result is not None else ""
            record  = AuditRecord.create(
                user_id      = user_id,
                display_name = display_name,
                action       = action,
                record_type  = record_type,
                subject_id   = subject_id,
                content      = content,
            )
            log.append(record)
            return result
        return wrapper
    return decorator
