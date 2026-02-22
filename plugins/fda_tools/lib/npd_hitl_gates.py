"""
FDA-233  [NPD-002] Human Regulatory Expert HITL Gate Design
============================================================
Defines the 5 Human-in-the-Loop (HITL) gates in the NPD workflow where
a qualified regulatory professional MUST review and approve before the
autonomous agent pipeline can advance.

Gate philosophy
---------------
Fully autonomous AI execution is appropriate for data gathering, analysis,
and draft generation.  Human judgment is irreplaceable at decision points
that are:
  1. Legally consequential (regulatory pathway selection)
  2. Scientifically complex (predicate device suitability)
  3. Patient-safety-critical (submission readiness)
  4. Post-submission (FDA negotiation and clearance conditions)
  5. Long-term commitment (post-market surveillance strategy)

Each gate:
  - Specifies the NPD stage transition it guards
  - Lists the required reviewer role(s)
  - Carries a structured checklist of items for the human reviewer
  - Produces an approval record stored in the audit trail (21 CFR Part 11)

Gate IDs
--------
GATE_CLASSIFY   : After CLASSIFY → before PREDICATE
GATE_PREDICATE  : After PREDICATE → before PATHWAY
GATE_PATHWAY    : After PATHWAY → before PRESUB
GATE_SUBMIT     : After REVIEW → before SUBMIT
GATE_CLEARED    : After FDA_REVIEW → before CLEARED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


# ── Enums ─────────────────────────────────────────────────────────────────────


class GateId(str, Enum):
    GATE_CLASSIFY  = "GATE_CLASSIFY"
    GATE_PREDICATE = "GATE_PREDICATE"
    GATE_PATHWAY   = "GATE_PATHWAY"
    GATE_SUBMIT    = "GATE_SUBMIT"
    GATE_CLEARED   = "GATE_CLEARED"

    @property
    def display_name(self) -> str:
        return self.value.replace("GATE_", "").replace("_", " ").title() + " Gate"


class GateStatus(str, Enum):
    PENDING   = "PENDING"    # Awaiting human review
    APPROVED  = "APPROVED"   # Approved — pipeline may advance
    REJECTED  = "REJECTED"   # Rejected — pipeline must revise before re-submission
    ESCALATED = "ESCALATED"  # Escalated to senior RA professional / regulatory counsel


class ReviewerRole(str, Enum):
    RA_LEAD     = "RA_LEAD"      # Regulatory Affairs Lead
    RA_MANAGER  = "RA_MANAGER"   # Regulatory Affairs Manager
    QA_LEAD     = "QA_LEAD"      # Quality Assurance Lead
    ENGINEER    = "ENGINEER"     # Design / R&D Engineer
    REG_COUNSEL = "REG_COUNSEL"  # External Regulatory Counsel


# ── Checklist item ────────────────────────────────────────────────────────────


@dataclass
class ChecklistItem:
    id:          str
    text:        str
    required:    bool  = True    # Must be checked before approval
    help_url:    Optional[str] = None  # Link to guidance or SOP


# ── Gate definition ───────────────────────────────────────────────────────────


@dataclass
class HitlGate:
    """Static definition of a HITL gate."""
    gate_id:            GateId
    from_stage:         str            # NPD stage that must be complete
    to_stage:           str            # NPD stage that becomes unlocked on approval
    title:              str
    description:        str
    required_reviewers: List[ReviewerRole]
    checklist:          List[ChecklistItem]
    sla_hours:          int = 48       # Expected human review turnaround
    escalation_hours:   int = 96       # Auto-escalate if not reviewed by this time


# ── Gate approval record ──────────────────────────────────────────────────────


@dataclass
class GateApprovalRecord:
    """
    Immutable audit record created when a gate is resolved.
    Stored in the 21 CFR Part 11 audit trail.
    """
    gate_id:            GateId
    project_id:         str
    status:             GateStatus
    reviewer_id:        str
    reviewer_role:      ReviewerRole
    timestamp:          datetime
    checked_items:      List[str]       = field(default_factory=list)  # item IDs
    comments:           str             = ""
    override_reason:    Optional[str]   = None   # set if APPROVED with unchecked required items


# ── Gate registry ─────────────────────────────────────────────────────────────


HITL_GATES: Dict[GateId, HitlGate] = {

    GateId.GATE_CLASSIFY: HitlGate(
        gate_id    = GateId.GATE_CLASSIFY,
        from_stage = "CLASSIFY",
        to_stage   = "PREDICATE",
        title      = "Device Classification Review",
        description = (
            "Verify that the AI-suggested device classification is correct before "
            "initiating predicate search.  An incorrect classification invalidates "
            "the entire downstream regulatory strategy."
        ),
        required_reviewers = [ReviewerRole.RA_LEAD],
        sla_hours          = 24,
        escalation_hours   = 48,
        checklist          = [
            ChecklistItem(
                id   = "CLS-01",
                text = "Confirm product code (3-letter FDA code) is correct for the intended use",
                help_url = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPCD/classification.cfm",
            ),
            ChecklistItem(
                id   = "CLS-02",
                text = "Confirm device class (I / II / III) and applicable 21 CFR Part citation",
            ),
            ChecklistItem(
                id   = "CLS-03",
                text = "Confirm device is NOT exempt from 510(k) requirements",
            ),
            ChecklistItem(
                id   = "CLS-04",
                text = "Confirm no combination product (drug/device/biologic) classification applies",
                required = False,
            ),
            ChecklistItem(
                id   = "CLS-05",
                text = "Verify Humanitarian Device Exemption (HDE) is not the appropriate pathway",
                required = False,
            ),
        ],
    ),

    GateId.GATE_PREDICATE: HitlGate(
        gate_id    = GateId.GATE_PREDICATE,
        from_stage = "PREDICATE",
        to_stage   = "PATHWAY",
        title      = "Predicate Device Selection Review",
        description = (
            "Approve the AI-selected predicate device(s) before the substantial "
            "equivalence strategy is locked in.  A weak predicate is the #1 cause "
            "of 510(k) RTAs and non-substantive deficiencies."
        ),
        required_reviewers = [ReviewerRole.RA_LEAD, ReviewerRole.ENGINEER],
        sla_hours          = 48,
        escalation_hours   = 96,
        checklist          = [
            ChecklistItem(
                id   = "PRE-01",
                text = "Predicate device K-number is valid and currently cleared (not recalled)",
            ),
            ChecklistItem(
                id   = "PRE-02",
                text = "Same intended use as subject device — or differences fully justifiable",
            ),
            ChecklistItem(
                id   = "PRE-03",
                text = "Same or equivalent technological characteristics",
            ),
            ChecklistItem(
                id   = "PRE-04",
                text = "Predicate recall / MAUDE health status is HEALTHY (not TOXIC or CAUTION)",
                help_url = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfRes/res.cfm",
            ),
            ChecklistItem(
                id   = "PRE-05",
                text = "Split predicate strategy (if used) is documented with clear rationale",
                required = False,
            ),
        ],
    ),

    GateId.GATE_PATHWAY: HitlGate(
        gate_id    = GateId.GATE_PATHWAY,
        from_stage = "PATHWAY",
        to_stage   = "PRESUB",
        title      = "Regulatory Pathway Approval",
        description = (
            "Formal approval of the submission pathway (510(k) / De Novo / PMA).  "
            "This decision commits significant R&D and regulatory resources and "
            "cannot be easily reversed once Pre-Submission discussions begin."
        ),
        required_reviewers = [ReviewerRole.RA_MANAGER],
        sla_hours          = 72,
        escalation_hours   = 120,
        checklist          = [
            ChecklistItem(
                id   = "PATH-01",
                text = "510(k) pathway confirmed: valid predicate exists, no new intended use requiring De Novo",
            ),
            ChecklistItem(
                id   = "PATH-02",
                text = "Pre-Submission (Q-Sub) interaction with FDA is recommended and planned",
            ),
            ChecklistItem(
                id   = "PATH-03",
                text = "Special controls and performance testing requirements are understood",
            ),
            ChecklistItem(
                id   = "PATH-04",
                text = "Clinical data requirements assessed — bench/in-vitro sufficient OR clinical study planned",
            ),
            ChecklistItem(
                id   = "PATH-05",
                text = "Estimated submission timeline, resource plan, and budget approved by management",
                required = False,
            ),
        ],
    ),

    GateId.GATE_SUBMIT: HitlGate(
        gate_id    = GateId.GATE_SUBMIT,
        from_stage = "REVIEW",
        to_stage   = "SUBMIT",
        title      = "Submission Readiness Sign-Off",
        description = (
            "Final human review before the 510(k) package is submitted to FDA.  "
            "This gate is the most critical: once filed, the 180-day FDA review "
            "clock starts and deficiencies trigger AI letters that extend timelines."
        ),
        required_reviewers = [ReviewerRole.RA_MANAGER, ReviewerRole.QA_LEAD],
        sla_hours          = 72,
        escalation_hours   = 168,
        checklist          = [
            ChecklistItem(
                id   = "SUB-01",
                text = "SRI (Submission Readiness Index) score ≥ 80/100",
            ),
            ChecklistItem(
                id   = "SUB-02",
                text = "All CRITICAL TODOs resolved in every section",
            ),
            ChecklistItem(
                id   = "SUB-03",
                text = "eSTAR XML validated — all required fields populated",
            ),
            ChecklistItem(
                id   = "SUB-04",
                text = "Substantial equivalence argument is complete and logically sound",
            ),
            ChecklistItem(
                id   = "SUB-05",
                text = "Labeling (IFU, label copy, artwork) matches device description and intended use",
            ),
            ChecklistItem(
                id   = "SUB-06",
                text = "Form 3514 (Cover Sheet) signed by authorized company representative",
            ),
            ChecklistItem(
                id   = "SUB-07",
                text = "All performance test reports included and summaries accurate",
            ),
            ChecklistItem(
                id   = "SUB-08",
                text = "Biocompatibility evaluation addresses ISO 10993 applicable endpoints",
            ),
            ChecklistItem(
                id   = "SUB-09",
                text = "Sterility / shelf-life data complete and expiration dating defined",
            ),
            ChecklistItem(
                id   = "SUB-10",
                text = "Software documentation (SOUP, SBOM, cybersecurity) included if applicable",
                required = False,
            ),
        ],
    ),

    GateId.GATE_CLEARED: HitlGate(
        gate_id    = GateId.GATE_CLEARED,
        from_stage = "FDA_REVIEW",
        to_stage   = "CLEARED",
        title      = "Post-Clearance Commercialization Approval",
        description = (
            "Verify that all clearance conditions are understood and documented "
            "before initiating commercialization.  Special conditions or restrictions "
            "in the clearance order must be captured in the Quality System."
        ),
        required_reviewers = [ReviewerRole.RA_LEAD, ReviewerRole.QA_LEAD],
        sla_hours          = 48,
        escalation_hours   = 96,
        checklist          = [
            ChecklistItem(
                id   = "CLR-01",
                text = "510(k) clearance order reviewed — device name and intended use match submission",
            ),
            ChecklistItem(
                id   = "CLR-02",
                text = "Any special conditions or restrictions in clearance order captured in QMS",
            ),
            ChecklistItem(
                id   = "CLR-03",
                text = "MDR (Medical Device Reporting) procedures established per 21 CFR Part 803",
            ),
            ChecklistItem(
                id   = "CLR-04",
                text = "Recall procedure documented per 21 CFR Part 806",
            ),
            ChecklistItem(
                id   = "CLR-05",
                text = "Post-market surveillance plan (PMS) activated and responsible parties assigned",
            ),
            ChecklistItem(
                id   = "CLR-06",
                text = "Device registration and listing submitted on FDA Unified Registration System (FURLS)",
                help_url = "https://www.fda.gov/medical-devices/how-study-and-market-your-device/device-registration-and-listing",
            ),
        ],
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────


def get_gate(gate_id: GateId) -> HitlGate:
    """Retrieve the static gate definition by ID."""
    return HITL_GATES[gate_id]


def get_gate_for_transition(from_stage: str, to_stage: str) -> Optional[HitlGate]:
    """Return the gate guarding a specific stage transition, or None."""
    for gate in HITL_GATES.values():
        if gate.from_stage == from_stage and gate.to_stage == to_stage:
            return gate
    return None


def all_gates_in_order() -> List[HitlGate]:
    """Return all 5 gates in workflow order."""
    ordered_ids = [
        GateId.GATE_CLASSIFY,
        GateId.GATE_PREDICATE,
        GateId.GATE_PATHWAY,
        GateId.GATE_SUBMIT,
        GateId.GATE_CLEARED,
    ]
    return [HITL_GATES[gid] for gid in ordered_ids]


def create_approval_record(
    gate_id:       GateId,
    project_id:    str,
    status:        GateStatus,
    reviewer_id:   str,
    reviewer_role: ReviewerRole,
    checked_items: List[str],
    comments:      str = "",
    override_reason: Optional[str] = None,
) -> GateApprovalRecord:
    """
    Factory for creating a GateApprovalRecord.
    Validates that all required checklist items are checked when APPROVED.
    Raises ValueError if required items are missing without an override_reason.
    """
    gate = HITL_GATES[gate_id]
    if status == GateStatus.APPROVED:
        required_ids = {item.id for item in gate.checklist if item.required}
        missing = required_ids - set(checked_items)
        if missing and not override_reason:
            raise ValueError(
                f"Cannot approve gate {gate_id.value}: "
                f"required checklist items not checked: {sorted(missing)}"
            )

    return GateApprovalRecord(
        gate_id        = gate_id,
        project_id     = project_id,
        status         = status,
        reviewer_id    = reviewer_id,
        reviewer_role  = reviewer_role,
        timestamp      = datetime.now(timezone.utc),
        checked_items  = list(checked_items),
        comments       = comments,
        override_reason = override_reason,
    )
