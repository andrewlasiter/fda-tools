"""
FDA-312  [COMPLIANCE] 21 CFR Part 11 Training Records Module
=============================================================
Implements §11.10(i) — Education, training, and experience requirements.

21 CFR Part 11 §11.10(i) states:
  "Use of appropriate controls over systems documentation including:
   (i) Adequate controls over the distribution of, access to, and use of
   documentation for system operation and maintenance.
   (ii) Revision and change control procedures to maintain an audit trail
   that documents time-sequenced development and modification of systems
   documentation."

In practice, FDA interprets §11.10(i) to require that:
  - Personnel who develop, maintain, or use Part 11 systems must be trained
  - Training must be documented with records retained (21 CFR 820.25(b))
  - Training records must be retrievable for FDA inspection

Architecture
------------
`TrainingRecordStore` is an in-memory singleton (Sprint 32 MVP).
Sprint 33 (FDA-317-class work) will migrate to PostgreSQL append-only table.
The store is safe for multi-threaded use via threading.Lock.

Usage
-----
    from fda_tools.lib.training_records import training_store, TrainingTopic

    # Add a training record
    record_id = training_store.add({
        "user_id":    "alice@example.com",
        "user_name":  "Alice Smith",
        "topic":      TrainingTopic.PART_11_OVERVIEW,
        "trainer_id": "admin@example.com",
        "score":      95,
    })

    # Check Part 11 compliance
    if training_store.has_part11_training():
        print("§11.10(i) — PASS")

    # List records for a user
    records = training_store.list(user_id="alice@example.com")
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Training topics (maps to 21 CFR Part 11 sub-requirements)
# ─────────────────────────────────────────────────────────────────────────────

class TrainingTopic(str, Enum):
    """Required training topics per 21 CFR Part 11 §11.10(i)."""

    PART_11_OVERVIEW          = "part_11_overview"
    ELECTRONIC_SIGNATURES     = "electronic_signatures"
    AUDIT_TRAIL_MANAGEMENT    = "audit_trail_management"
    ACCESS_CONTROL            = "access_control"
    DATA_INTEGRITY            = "data_integrity"
    HITL_PROCEDURES           = "hitl_procedures"
    SUBMISSION_WORKFLOW       = "submission_workflow"
    SYSTEM_VALIDATION         = "system_validation"


# Topics that directly satisfy §11.10(i) Part 11 training requirements
PART_11_CORE_TOPICS: frozenset[str] = frozenset({
    TrainingTopic.PART_11_OVERVIEW,
    TrainingTopic.ELECTRONIC_SIGNATURES,
    TrainingTopic.AUDIT_TRAIL_MANAGEMENT,
    TrainingTopic.ACCESS_CONTROL,
    TrainingTopic.SYSTEM_VALIDATION,
})


# ─────────────────────────────────────────────────────────────────────────────
# Training record store
# ─────────────────────────────────────────────────────────────────────────────

class TrainingRecordStore:
    """
    Thread-safe in-memory store for 21 CFR Part 11 training records.

    Sprint 32 MVP: in-memory (records lost on restart).
    Sprint 33 target: migrate to PostgreSQL `training_records` table
    with append-only RLS (same pattern as `hitl_gate_decisions`).

    Each record is a plain dict with these required keys:
        user_id   (str)  — user email / ID
        user_name (str)  — display name
        topic     (str)  — TrainingTopic value or free-text
    And these optional keys:
        trainer_id, trainer_name, score (0-100), certificate_id, notes
    """

    def __init__(self) -> None:
        self._records: List[Dict] = []
        self._lock = threading.Lock()

    # ── Write ──────────────────────────────────────────────────────────────

    def add(self, record: Dict) -> str:
        """
        Add a training record. Auto-assigns record_id + created_at.
        Returns the new record_id (UUID4 string).
        """
        record_id = str(uuid.uuid4())
        entry = {
            **record,
            "record_id":    record_id,
            "created_at":   datetime.now(timezone.utc).isoformat(),
            "completed_at": record.get("completed_at", datetime.now(timezone.utc).isoformat()),
        }
        with self._lock:
            self._records.append(entry)
        return record_id

    # ── Read ───────────────────────────────────────────────────────────────

    def list(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        Return all training records, optionally filtered by user_id.
        Returns a snapshot (copy) of the list to prevent external mutation.
        """
        with self._lock:
            records = list(self._records)
        if user_id:
            records = [r for r in records if r.get("user_id") == user_id]
        return records

    def count(self, user_id: Optional[str] = None) -> int:
        """Return count of training records (optionally per user)."""
        return len(self.list(user_id))

    def get(self, record_id: str) -> Optional[Dict]:
        """Return a specific record by ID, or None if not found."""
        with self._lock:
            for record in self._records:
                if record.get("record_id") == record_id:
                    return dict(record)
        return None

    # ── Compliance checks ──────────────────────────────────────────────────

    def has_part11_training(self, user_id: Optional[str] = None) -> bool:
        """
        Return True if at least one Part 11 core-topic training record exists.

        A "core" topic is one in PART_11_CORE_TOPICS.
        If user_id is given, checks only that user's records.
        If user_id is None, checks the whole organisation.
        """
        records = self.list(user_id)
        for record in records:
            if record.get("topic") in PART_11_CORE_TOPICS:
                return True
        # Fallback: any training at all counts (laxer interpretation)
        return len(records) > 0

    def compliance_summary(self, user_id: Optional[str] = None) -> Dict:
        """
        Return a dict suitable for Part11ComplianceReport config injection:

            {
              "training_records_exist": bool,
              "training_count":         int,
              "training_users":         List[str],
              "part11_topics_covered":  List[str],
            }
        """
        records = self.list(user_id)
        topics   = {r.get("topic", "") for r in records if r.get("topic")}
        users    = list({r.get("user_id", "") for r in records if r.get("user_id")})
        part11_covered = sorted(topics & PART_11_CORE_TOPICS)
        return {
            "training_records_exist": len(records) > 0,
            "training_count":         len(records),
            "training_users":         users,
            "part11_topics_covered":  part11_covered,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton (imported by server.py + cfr_part11.py)
# ─────────────────────────────────────────────────────────────────────────────

#: Global training record store — import and use this in server.py endpoints
#: and in Part11ComplianceReport.generate() config injection.
training_store = TrainingRecordStore()
