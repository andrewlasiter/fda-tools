"""
FDA-235  [NPD-004] Regulatory Submission Automation (510(k) + De Novo + PMA)
=============================================================================
Provides:
  1. `SubmissionType` — pathway enum (510K / DE_NOVO / PMA)
  2. `SubmissionRequirements` — per-pathway checklist of required sections and
     performance data (derived from FDA guidance documents)
  3. `SubmissionPackage` — container tracking which sections are drafted,
     reviewed, and complete; computes Submission Readiness Index (SRI)
  4. `SubmissionAutomator` — orchestrates agents across the DRAFTING → REVIEW
     → SUBMIT stages, tracking section status

SRI scoring (0–100)
--------------------
Each required section contributes equally.  An optional section contributes
only if present and drafted.  Reviewed sections score 1.5× vs. draft-only.
Score = (drafted×1.0 + reviewed×0.5 extra bonus) / max_possible × 100

The SRI mirrors the GATE_SUBMIT checklist item SUB-01 (SRI ≥ 80/100).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


# ── Pathway enum ──────────────────────────────────────────────────────────────


class SubmissionType(str, Enum):
    SUBMISSION_510K = "510K"
    DE_NOVO         = "DE_NOVO"
    PMA             = "PMA"

    @property
    def display_name(self) -> str:
        return {"510K": "510(k) Premarket Notification",
                "DE_NOVO": "De Novo Classification Request",
                "PMA": "Premarket Approval"}[self.value]


# ── Section status ────────────────────────────────────────────────────────────


class SectionStatus(str, Enum):
    MISSING   = "MISSING"    # Not started
    DRAFT     = "DRAFT"      # AI-generated draft exists
    REVIEWED  = "REVIEWED"   # Human-reviewed (HITL or RA professional)
    APPROVED  = "APPROVED"   # Formally approved for submission


# ── Section definition ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SubmissionSection:
    id:          str
    title:       str
    required:    bool  = True
    description: str   = ""
    guidance:    str   = ""   # FDA guidance document reference


# ── Per-pathway requirements ──────────────────────────────────────────────────


SUBMISSION_REQUIREMENTS: Dict[SubmissionType, List[SubmissionSection]] = {

    SubmissionType.SUBMISSION_510K: [
        SubmissionSection("cover-letter",    "Cover Letter (Form FDA 3514)", required=True,
                          description="Cover letter signed by authorized representative",
                          guidance="21 CFR 807.87"),
        SubmissionSection("indications",     "Indications for Use Statement", required=True,
                          description="Precise intended use and indications for use",
                          guidance="21 CFR 807.87(e); FDA IFU Guidance 2019"),
        SubmissionSection("device-desc",     "Device Description", required=True,
                          description="Complete technical description of device and accessories",
                          guidance="21 CFR 807.87(f)"),
        SubmissionSection("substantial-equiv","Substantial Equivalence Discussion", required=True,
                          description="Comparison to predicate device — intended use + tech characteristics",
                          guidance="21 CFR 807.87(f); FDA SE Guidance 2019"),
        SubmissionSection("proposed-labeling","Proposed Labeling (IFU + Label Copy)", required=True,
                          description="Draft IFU, labeling, and artwork meeting 21 CFR Part 801",
                          guidance="21 CFR 801; FDA Labeling Guidance"),
        SubmissionSection("performance-testing","Performance Testing Summary", required=True,
                          description="Bench, in-vitro, or clinical performance test results",
                          guidance="FDA Testing Guidance for device class"),
        SubmissionSection("biocompatibility", "Biocompatibility Evaluation (ISO 10993)", required=True,
                          description="ISO 10993-1 biocompatibility risk assessment and test results",
                          guidance="ISO 10993-1; FDA Biocompatibility Guidance 2020"),
        SubmissionSection("sterility",        "Sterility and Shelf Life", required=False,
                          description="Sterilization validation, sterility assurance level, expiration",
                          guidance="ISO 11135 / ISO 11137 / ANSI/AAMI ST72"),
        SubmissionSection("software",         "Software Documentation (IEC 62304 / Cybersecurity)", required=False,
                          description="SaMD level, SOUP list, SBOM, cybersecurity controls",
                          guidance="FDA Software Guidance 2023; IEC 62304; IEC 62443"),
        SubmissionSection("standards",        "Declaration of Conformity (applicable standards)", required=True,
                          description="List of consensus standards applied with compliance declarations",
                          guidance="FDA Standards Program; ISO/ASTM applicable to device class"),
        SubmissionSection("reprocessing",     "Reprocessing Instructions (if reusable)", required=False,
                          description="Validated cleaning, disinfection, and sterilization instructions",
                          guidance="FDA Reprocessing Guidance 2015; AAMI TIR30"),
    ],

    SubmissionType.DE_NOVO: [
        SubmissionSection("cover-letter",    "Cover Letter", required=True),
        SubmissionSection("device-desc",     "Device Description", required=True),
        SubmissionSection("indications",     "Indications for Use", required=True),
        SubmissionSection("classification",  "Classification Rationale (De Novo)", required=True,
                          description="Justification for Class II classification with special controls proposal",
                          guidance="21 CFR 513(f)(2); FDA De Novo Guidance 2021"),
        SubmissionSection("special-controls","Proposed Special Controls", required=True,
                          description="Draft special controls order with specific performance criteria",
                          guidance="FDA De Novo Guidance 2021"),
        SubmissionSection("performance-testing","Performance Testing Summary", required=True),
        SubmissionSection("biocompatibility","Biocompatibility Evaluation", required=True),
        SubmissionSection("proposed-labeling","Proposed Labeling", required=True),
        SubmissionSection("risk-management",  "Risk Management File (ISO 14971)", required=True,
                          description="Risk analysis, risk evaluation, and risk control measures",
                          guidance="ISO 14971:2019"),
        SubmissionSection("software",         "Software Documentation", required=False),
    ],

    SubmissionType.PMA: [
        SubmissionSection("cover-letter",      "Cover Letter", required=True),
        SubmissionSection("device-desc",       "Device Description", required=True),
        SubmissionSection("indications",       "Indications for Use", required=True),
        SubmissionSection("clinical-data",     "Clinical Investigation Report", required=True,
                          description="Full IDE clinical study report with statistical analysis",
                          guidance="21 CFR 814.20(b)(6); ICH E6 GCP"),
        SubmissionSection("non-clinical",      "Non-Clinical Studies Summary", required=True),
        SubmissionSection("biocompatibility",  "Biocompatibility Evaluation", required=True),
        SubmissionSection("sterility",         "Sterility and Manufacturing", required=True),
        SubmissionSection("proposed-labeling", "Proposed Labeling", required=True),
        SubmissionSection("risk-management",   "Risk Management File (ISO 14971)", required=True),
        SubmissionSection("qms-summary",       "Quality System Summary (21 CFR Part 820)", required=True,
                          description="Manufacturing facility QMS description and controls",
                          guidance="21 CFR 820; ISO 13485"),
        SubmissionSection("software",          "Software Documentation", required=False),
        SubmissionSection("pms-plan",          "Post-Market Surveillance Plan", required=True,
                          description="Post-approval study plan and periodic reporting commitment",
                          guidance="21 CFR 814.82; FDA PMS Guidance"),
    ],
}


# ── Submission package ────────────────────────────────────────────────────────


@dataclass
class SubmissionPackage:
    """
    Tracks the drafting and review status of every section in a submission.

    Instantiate via `SubmissionPackage.for_pathway(submission_type, project_id)`.
    """
    project_id:      str
    submission_type: SubmissionType
    sections:        Dict[str, SubmissionSection]          # section_id → definition
    status:          Dict[str, SectionStatus] = field(default_factory=dict)
    notes:           Dict[str, str]           = field(default_factory=dict)

    @classmethod
    def for_pathway(
        cls,
        submission_type: SubmissionType,
        project_id:      str,
    ) -> "SubmissionPackage":
        sections = {s.id: s for s in SUBMISSION_REQUIREMENTS[submission_type]}
        status   = {s_id: SectionStatus.MISSING for s_id in sections}
        return cls(
            project_id      = project_id,
            submission_type = submission_type,
            sections        = sections,
            status          = status,
        )

    # ── Status updates ────────────────────────────────────────────────────────

    def mark_drafted(self, section_id: str, note: str = "") -> None:
        """Mark a section as AI-drafted."""
        if section_id not in self.sections:
            raise KeyError(f"Unknown section: {section_id!r}")
        self.status[section_id] = SectionStatus.DRAFT
        if note:
            self.notes[section_id] = note

    def mark_reviewed(self, section_id: str, note: str = "") -> None:
        """Mark a section as human-reviewed."""
        if section_id not in self.sections:
            raise KeyError(f"Unknown section: {section_id!r}")
        self.status[section_id] = SectionStatus.REVIEWED
        if note:
            self.notes[section_id] = note

    def mark_approved(self, section_id: str) -> None:
        """Mark a section as approved for submission."""
        if section_id not in self.sections:
            raise KeyError(f"Unknown section: {section_id!r}")
        self.status[section_id] = SectionStatus.APPROVED

    # ── SRI computation ───────────────────────────────────────────────────────

    def compute_sri(self) -> float:
        """
        Compute the Submission Readiness Index (0–100).

        Required sections:
          DRAFT    → 1.0 point
          REVIEWED → 1.5 points
          APPROVED → 2.0 points

        Optional sections contribute at 0.5× the above if present.

        Score = earned / max_possible × 100
        """
        required_ids  = [s_id for s_id, s in self.sections.items() if s.required]
        optional_ids  = [s_id for s_id, s in self.sections.items() if not s.required]

        weights = {
            SectionStatus.MISSING:  0.0,
            SectionStatus.DRAFT:    1.0,
            SectionStatus.REVIEWED: 1.5,
            SectionStatus.APPROVED: 2.0,
        }

        earned = 0.0
        max_possible = 0.0

        for s_id in required_ids:
            max_possible += weights[SectionStatus.APPROVED]  # 2.0 per required
            earned       += weights[self.status.get(s_id, SectionStatus.MISSING)]

        for s_id in optional_ids:
            st = self.status.get(s_id, SectionStatus.MISSING)
            if st != SectionStatus.MISSING:
                max_possible += weights[SectionStatus.APPROVED] * 0.5
                earned       += weights[st] * 0.5

        if max_possible == 0:
            return 0.0
        return round(earned / max_possible * 100, 1)

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> dict:
        sri = self.compute_sri()
        counts = {s.value: 0 for s in SectionStatus}
        for st in self.status.values():
            counts[st.value] += 1
        return {
            "project_id":      self.project_id,
            "submission_type": self.submission_type.value,
            "pathway_name":    self.submission_type.display_name,
            "sri":             sri,
            "sri_gate_ready":  sri >= 80.0,
            "total_sections":  len(self.sections),
            "section_counts":  counts,
            "sections": [
                {
                    "id":       s_id,
                    "title":    self.sections[s_id].title,
                    "required": self.sections[s_id].required,
                    "status":   self.status.get(s_id, SectionStatus.MISSING).value,
                    "note":     self.notes.get(s_id, ""),
                }
                for s_id in self.sections
            ],
        }


# ── Submission automator ──────────────────────────────────────────────────────


@dataclass
class SubmissionAutomator:
    """
    Orchestrates the DRAFTING and REVIEW stages of the NPD pipeline.

    In the full platform this triggers Claude Code sub-agents for each
    section.  Here we expose the orchestration logic so it can be tested
    independently and wired into the NPD state machine.
    """
    package: SubmissionPackage

    def sections_needing_draft(self) -> List[str]:
        """Return required section IDs that are still MISSING."""
        return [
            s_id for s_id, s in self.package.sections.items()
            if s.required and self.package.status[s_id] == SectionStatus.MISSING
        ]

    def sections_needing_review(self) -> List[str]:
        """Return section IDs drafted but not yet reviewed."""
        return [
            s_id for s_id in self.package.sections
            if self.package.status[s_id] == SectionStatus.DRAFT
        ]

    def is_ready_for_gate(self) -> bool:
        """Return True if the package meets the GATE_SUBMIT SRI ≥ 80 threshold."""
        return self.package.compute_sri() >= 80.0

    def draft_section(self, section_id: str, agent_output: str) -> None:
        """Record that an AI agent has produced a draft for the given section."""
        self.package.mark_drafted(section_id, note=agent_output[:200])

    def review_section(
        self,
        section_id:  str,
        reviewer_id: str,
        notes:       str = "",
    ) -> None:
        """Record that a human reviewer has reviewed the section."""
        note = f"Reviewed by {reviewer_id}" + (f": {notes}" if notes else "")
        self.package.mark_reviewed(section_id, note=note)
