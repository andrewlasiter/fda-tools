#!/usr/bin/env python3
"""
Post-Approval Study (PAS) Monitor -- Track PAS obligations and compliance
for PMA devices per 21 CFR 814.82 (Section 522 studies).

Parses PMA approval data and supplement history for PAS requirements,
tracks study milestones, monitors compliance status, and generates
alerts for overdue or at-risk studies.

PAS Types:
    1. Continued Approval Study -- Required to maintain PMA approval
    2. Pediatric Study -- Per Pediatric Medical Device Safety Act
    3. 522 Post-Market Surveillance -- FDA-ordered per 21 CFR 822
    4. Voluntary Post-Approval Study -- Manufacturer-initiated

PAS Milestones:
    - Protocol approval
    - Enrollment initiation
    - Interim reports (annually or at enrollment milestones)
    - Enrollment completion
    - Follow-up completion
    - Final report submission
    - FDA review of final results

Usage:
    from pas_monitor import PASMonitor

    monitor = PASMonitor()
    report = monitor.generate_pas_report("P170019")
    milestones = monitor.track_milestones("P170019")
    compliance = monitor.assess_pas_compliance("P170019")

    # CLI usage:
    python3 pas_monitor.py --pma P170019
    python3 pas_monitor.py --pma P170019 --milestones
    python3 pas_monitor.py --pma P170019 --compliance
    python3 pas_monitor.py --batch P170019,P200024
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# PAS type definitions
# ------------------------------------------------------------------

PAS_TYPES = {
    "continued_approval": {
        "label": "Continued Approval Study",
        "cfr_ref": "21 CFR 814.82(a)(2)",
        "description": (
            "Study required as a condition of PMA approval to verify "
            "the long-term safety and effectiveness of the device."
        ),
        "typical_duration_years": 5,
        "interim_reporting": "annually",
        "keywords": [
            "condition of approval", "continued approval",
            "approval condition", "conditions of approval",
            "post-approval study", "post approval study",
        ],
    },
    "pediatric": {
        "label": "Pediatric Study",
        "cfr_ref": "Pediatric Medical Device Safety Act",
        "description": (
            "Study required to evaluate device safety and effectiveness "
            "in pediatric populations."
        ),
        "typical_duration_years": 7,
        "interim_reporting": "annually",
        "keywords": [
            "pediatric", "pediatric study", "pediatric population",
            "children", "adolescent",
        ],
    },
    "section_522": {
        "label": "Section 522 Post-Market Surveillance",
        "cfr_ref": "21 CFR 822 (Section 522)",
        "description": (
            "FDA-ordered post-market surveillance study to gather "
            "additional safety and effectiveness data."
        ),
        "typical_duration_years": 3,
        "interim_reporting": "annually",
        "keywords": [
            "522", "section 522", "post-market surveillance",
            "postmarket surveillance", "surveillance order",
            "522 order", "522 study",
        ],
    },
    "voluntary": {
        "label": "Voluntary Post-Approval Study",
        "cfr_ref": "N/A (manufacturer-initiated)",
        "description": (
            "Study initiated voluntarily by the manufacturer to "
            "gather additional clinical data."
        ),
        "typical_duration_years": 3,
        "interim_reporting": "as specified",
        "keywords": [
            "voluntary study", "voluntary post-approval",
            "registry", "post-market registry",
        ],
    },
}

# PAS study status classifications
PAS_STATUS = {
    "required": "Study required but not yet initiated",
    "protocol_review": "Protocol submitted for FDA review",
    "enrolling": "Actively enrolling patients",
    "enrollment_complete": "Enrollment completed, follow-up ongoing",
    "follow_up_complete": "Follow-up completed, final report pending",
    "final_report_submitted": "Final report submitted to FDA",
    "completed": "Study completed and accepted by FDA",
    "terminated": "Study terminated early",
    "delayed": "Study delayed or enrollment behind schedule",
    "unknown": "Study status unknown from available data",
}

# PAS milestone definitions
PAS_MILESTONES = [
    {"id": "protocol_submission", "label": "Protocol Submission",
     "typical_offset_months": 6, "required": True},
    {"id": "protocol_approval", "label": "Protocol Approval by FDA",
     "typical_offset_months": 12, "required": True},
    {"id": "enrollment_start", "label": "Enrollment Initiation",
     "typical_offset_months": 18, "required": True},
    {"id": "interim_report_1", "label": "First Interim Report",
     "typical_offset_months": 30, "required": True},
    {"id": "enrollment_50pct", "label": "50% Enrollment Milestone",
     "typical_offset_months": 36, "required": False},
    {"id": "enrollment_complete", "label": "Enrollment Completion",
     "typical_offset_months": 48, "required": True},
    {"id": "interim_report_2", "label": "Second Interim Report",
     "typical_offset_months": 54, "required": True},
    {"id": "follow_up_complete", "label": "Follow-up Completion",
     "typical_offset_months": 72, "required": True},
    {"id": "final_report", "label": "Final Report Submission",
     "typical_offset_months": 78, "required": True},
    {"id": "fda_review_complete", "label": "FDA Review Complete",
     "typical_offset_months": 84, "required": True},
]


# ------------------------------------------------------------------
# PAS Monitor
# ------------------------------------------------------------------

class PASMonitor:
    """Post-Approval Study monitoring and compliance tracking.

    Identifies PAS obligations from PMA approval data, tracks study
    milestones, detects compliance issues, and generates alerts.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize PAS Monitor.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()

    # ------------------------------------------------------------------
    # Main report generation
    # ------------------------------------------------------------------

    def generate_pas_report(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict:
        """Generate a comprehensive PAS monitoring report.

        Args:
            pma_number: PMA number.
            refresh: Force API refresh.

        Returns:
            PAS monitoring report dict.
        """
        pma_key = pma_number.upper()

        # Load PMA data
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        # Load supplements
        supplements = self.store.get_supplements(pma_key, refresh=refresh)

        # Load extracted sections (for PAS requirement detection)
        sections = self.store.get_extracted_sections(pma_key)

        # Identify PAS requirements
        pas_requirements = self._identify_pas_requirements(
            api_data, supplements, sections
        )

        # Identify PAS-related supplements
        pas_supplements = self._identify_pas_supplements(supplements)

        # Determine PAS status from supplement patterns
        pas_status = self._determine_pas_status(
            pas_requirements, pas_supplements, api_data
        )

        # Generate milestone timeline
        milestones = self._generate_milestone_timeline(
            pas_requirements, pas_supplements, api_data
        )

        # Assess compliance
        compliance = self._assess_compliance(
            pas_requirements, pas_status, milestones, api_data
        )

        # Generate alerts
        alerts = self._generate_alerts(
            pas_requirements, pas_status, compliance, api_data
        )

        report = {
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "applicant": api_data.get("applicant", ""),
            "approval_date": api_data.get("decision_date", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pas_required": len(pas_requirements) > 0,
            "total_pas_requirements": len(pas_requirements),
            "pas_requirements": pas_requirements,
            "pas_supplements": pas_supplements,
            "pas_status": pas_status,
            "milestones": milestones,
            "compliance": compliance,
            "alerts": alerts,
        }

        # Cache the report
        self._save_report(pma_key, report)

        return report

    # ------------------------------------------------------------------
    # PAS requirement identification
    # ------------------------------------------------------------------

    def _identify_pas_requirements(
        self,
        api_data: Dict,
        supplements: List[Dict],
        sections: Optional[Dict],
    ) -> List[Dict]:
        """Identify PAS requirements from PMA data and sections.

        Args:
            api_data: PMA API data.
            supplements: Supplement list.
            sections: Extracted SSED sections (if available).

        Returns:
            List of identified PAS requirement dicts.
        """
        requirements = []

        # Source 1: AO statement
        ao_statement = api_data.get("ao_statement", "").lower()

        # Source 2: Combined supplement text
        supp_text = ""
        for s in supplements[:20]:
            supp_text += (
                f" {s.get('supplement_type', '')} "
                f"{s.get('supplement_reason', '')}"
            )
        supp_text = supp_text.lower()

        # Source 3: Extracted clinical sections
        clinical_text = ""
        if sections:
            section_dict = sections.get("sections", sections)
            for key in ("clinical_studies", "general_information"):
                sec = section_dict.get(key, {})
                if isinstance(sec, dict):
                    clinical_text += f" {sec.get('content', '')}"
                elif isinstance(sec, str):
                    clinical_text += f" {sec}"
        clinical_text = clinical_text.lower()

        combined = f"{ao_statement} {supp_text} {clinical_text}"

        # Check for each PAS type
        for type_key, type_def in PAS_TYPES.items():
            for kw in type_def["keywords"]:
                if kw.lower() in combined:
                    # Determine source
                    source = "unknown"
                    if kw.lower() in ao_statement:
                        source = "ao_statement"
                    elif kw.lower() in supp_text:
                        source = "supplement_history"
                    elif kw.lower() in clinical_text:
                        source = "ssed_sections"

                    requirements.append({
                        "type": type_key,
                        "label": type_def["label"],
                        "cfr_ref": type_def["cfr_ref"],
                        "description": type_def["description"],
                        "detected_keyword": kw,
                        "source": source,
                        "typical_duration_years": type_def["typical_duration_years"],
                        "interim_reporting": type_def["interim_reporting"],
                        "confidence": self._calculate_pas_confidence(
                            type_key, source, combined
                        ),
                    })
                    break  # One match per type is sufficient

        return requirements

    def _calculate_pas_confidence(
        self,
        pas_type: str,
        source: str,
        text: str,
    ) -> float:
        """Calculate confidence that a PAS requirement exists.

        Args:
            pas_type: PAS type key.
            source: Detection source.
            text: Combined search text.

        Returns:
            Confidence score (0.0 to 1.0).
        """
        base_confidence = {
            "ao_statement": 0.95,
            "supplement_history": 0.80,
            "ssed_sections": 0.70,
            "unknown": 0.50,
        }

        conf = base_confidence.get(source, 0.50)

        # Boost for multiple keyword matches
        type_def = PAS_TYPES.get(pas_type, {})
        matches = sum(
            1 for kw in type_def.get("keywords", [])
            if kw.lower() in text
        )
        if matches >= 3:
            conf = min(conf + 0.15, 1.0)
        elif matches >= 2:
            conf = min(conf + 0.10, 1.0)

        return round(conf, 2)

    # ------------------------------------------------------------------
    # PAS supplement identification
    # ------------------------------------------------------------------

    def _identify_pas_supplements(
        self,
        supplements: List[Dict],
    ) -> List[Dict]:
        """Identify supplements related to PAS.

        Args:
            supplements: Full supplement list.

        Returns:
            List of PAS-related supplement dicts.
        """
        pas_keywords = set()
        for type_def in PAS_TYPES.values():
            for kw in type_def["keywords"]:
                pas_keywords.add(kw.lower())

        # Additional keywords for PAS submissions
        pas_keywords.update([
            "enrollment", "interim report", "final report",
            "study update", "protocol", "protocol amendment",
            "study results",
        ])

        pas_supplements = []
        for supp in supplements:
            combined = (
                f"{supp.get('supplement_type', '')} "
                f"{supp.get('supplement_reason', '')}"
            ).lower()

            matched_keywords = [
                kw for kw in pas_keywords if kw in combined
            ]

            if matched_keywords:
                pas_supplements.append({
                    "pma_number": supp.get("pma_number", ""),
                    "supplement_number": supp.get("supplement_number", ""),
                    "decision_date": supp.get("decision_date", ""),
                    "decision_code": supp.get("decision_code", ""),
                    "supplement_type": supp.get("supplement_type", ""),
                    "supplement_reason": supp.get("supplement_reason", ""),
                    "matched_keywords": matched_keywords,
                    "likely_milestone": self._infer_milestone(
                        combined, matched_keywords
                    ),
                })

        return pas_supplements

    def _infer_milestone(
        self,
        text: str,
        _keywords: List[str],
    ) -> str:
        """Infer which PAS milestone a supplement represents.

        Args:
            text: Combined supplement text.
            _keywords: Matched keywords.

        Returns:
            Inferred milestone ID.
        """
        if any(kw in text for kw in ["protocol", "protocol amendment"]):
            return "protocol_submission"
        if any(kw in text for kw in ["enrollment", "enrolling"]):
            return "enrollment_update"
        if any(kw in text for kw in ["interim report", "interim"]):
            return "interim_report"
        if any(kw in text for kw in ["final report", "final results"]):
            return "final_report"
        if any(kw in text for kw in ["study results", "study completion"]):
            return "follow_up_complete"
        return "pas_update"

    # ------------------------------------------------------------------
    # PAS status determination
    # ------------------------------------------------------------------

    def _determine_pas_status(
        self,
        requirements: List[Dict],
        pas_supplements: List[Dict],
        api_data: Dict,
    ) -> Dict:
        """Determine overall PAS status from available data.

        Args:
            requirements: Identified PAS requirements.
            pas_supplements: PAS-related supplements.
            api_data: PMA API data.

        Returns:
            PAS status dict.
        """
        if not requirements:
            return {
                "overall_status": "no_pas_required",
                "description": "No post-approval study requirements detected.",
                "per_study": [],
            }

        per_study = []
        for req in requirements:
            pas_type = req.get("type", "unknown")

            # Find related supplements for this study type
            related_supps = []
            type_keywords = set(
                kw.lower() for kw in PAS_TYPES.get(pas_type, {}).get("keywords", [])
            )

            for ps in pas_supplements:
                if any(kw in type_keywords for kw in ps.get("matched_keywords", [])):
                    related_supps.append(ps)

            # Infer status from supplement timeline
            status = self._infer_study_status(related_supps, api_data)

            per_study.append({
                "type": pas_type,
                "label": req.get("label", ""),
                "status": status,
                "status_description": PAS_STATUS.get(status, "Unknown status"),
                "related_supplements": len(related_supps),
                "latest_supplement": (
                    related_supps[-1].get("decision_date", "")
                    if related_supps else ""
                ),
            })

        # Determine overall status
        statuses = [s.get("status", "unknown") for s in per_study]
        if all(s == "completed" for s in statuses):
            overall = "all_completed"
        elif any(s in ("delayed", "terminated") for s in statuses):
            overall = "at_risk"
        elif any(s in ("enrolling", "enrollment_complete") for s in statuses):
            overall = "in_progress"
        elif any(s == "required" for s in statuses):
            overall = "pending_initiation"
        else:
            overall = "unknown"

        return {
            "overall_status": overall,
            "description": PAS_STATUS.get(overall, "Unknown overall status"),
            "per_study": per_study,
        }

    def _infer_study_status(
        self,
        related_supplements: List[Dict],
        api_data: Dict,
    ) -> str:
        """Infer PAS study status from supplement patterns.

        Args:
            related_supplements: PAS-related supplements.
            api_data: PMA API data.

        Returns:
            Inferred status string.
        """
        if not related_supplements:
            # No supplements detected -- check how old the PMA is
            dd = api_data.get("decision_date", "")
            if dd and len(dd) >= 4:
                try:
                    approval_year = int(dd[:4])
                    current_year = datetime.now().year
                    years_since = current_year - approval_year
                    if years_since >= 3:
                        return "unknown"  # Should have some activity by now
                    elif years_since >= 1:
                        return "protocol_review"  # Protocol likely under review
                    else:
                        return "required"
                except ValueError as e:
                    print(f"Warning: Could not parse approval year for study status inference: {e}", file=sys.stderr)
            return "required"

        # Look at milestones in supplements
        milestones_seen = set()
        for supp in related_supplements:
            milestones_seen.add(supp.get("likely_milestone", ""))

        if "final_report" in milestones_seen:
            return "final_report_submitted"
        elif "follow_up_complete" in milestones_seen:
            return "follow_up_complete"
        elif "enrollment_update" in milestones_seen:
            return "enrolling"
        elif "interim_report" in milestones_seen:
            return "enrolling"
        elif "protocol_submission" in milestones_seen:
            return "protocol_review"

        return "unknown"

    # ------------------------------------------------------------------
    # Milestone timeline
    # ------------------------------------------------------------------

    def _generate_milestone_timeline(
        self,
        requirements: List[Dict],
        pas_supplements: List[Dict],
        api_data: Dict,
    ) -> List[Dict]:
        """Generate PAS milestone timeline.

        Args:
            requirements: PAS requirements.
            pas_supplements: PAS-related supplements.
            api_data: PMA API data.

        Returns:
            List of milestone dicts with expected/actual dates.
        """
        if not requirements:
            return []

        approval_date = self._parse_date(api_data.get("decision_date", ""))
        if approval_date is None:
            return []

        milestones = []
        for milestone_def in PAS_MILESTONES:
            expected_date = approval_date + timedelta(
                days=milestone_def["typical_offset_months"] * 30
            )

            # Check if any supplement matches this milestone
            actual_date = None
            matched_supplement = None
            for ps in pas_supplements:
                if ps.get("likely_milestone") == milestone_def["id"]:
                    actual_date = ps.get("decision_date", "")
                    matched_supplement = ps.get("supplement_number", "")
                    break

            # Determine status
            now = datetime.now()
            if actual_date:
                status = "completed"
            elif expected_date < now:
                status = "overdue"
            elif (expected_date - now).days <= 90:
                status = "upcoming"
            else:
                status = "future"

            milestones.append({
                "milestone_id": milestone_def["id"],
                "label": milestone_def["label"],
                "expected_date": expected_date.strftime("%Y-%m-%d"),
                "actual_date": actual_date or None,
                "matched_supplement": matched_supplement,
                "required": milestone_def["required"],
                "status": status,
            })

        return milestones

    # ------------------------------------------------------------------
    # Compliance assessment
    # ------------------------------------------------------------------

    def _assess_compliance(
        self,
        requirements: List[Dict],
        _pas_status: Dict,
        milestones: List[Dict],
        _api_data: Dict,
    ) -> Dict:
        """Assess PAS compliance status.

        Args:
            requirements: PAS requirements.
            _pas_status: Current PAS status.
            milestones: Milestone timeline.
            _api_data: PMA API data.

        Returns:
            Compliance assessment dict.
        """
        if not requirements:
            return {
                "compliance_status": "not_applicable",
                "description": "No PAS requirements detected.",
                "overdue_milestones": 0,
                "completed_milestones": 0,
            }

        overdue = [m for m in milestones if m.get("status") == "overdue"]
        completed = [m for m in milestones if m.get("status") == "completed"]
        upcoming = [m for m in milestones if m.get("status") == "upcoming"]
        required_milestones = [m for m in milestones if m.get("required")]

        # Calculate compliance score
        total_required = len(required_milestones)
        completed_required = len([
            m for m in milestones
            if m.get("required") and m.get("status") == "completed"
        ])
        overdue_required = len([
            m for m in milestones
            if m.get("required") and m.get("status") == "overdue"
        ])

        if total_required > 0:
            compliance_score = round(
                completed_required / total_required * 100, 1
            )
        else:
            compliance_score = 0

        # Determine compliance status
        if overdue_required >= 3:
            compliance_status = "NON_COMPLIANT"
        elif overdue_required >= 1:
            compliance_status = "AT_RISK"
        elif compliance_score >= 100:
            compliance_status = "COMPLIANT"
        elif compliance_score >= 50:
            compliance_status = "ON_TRACK"
        else:
            compliance_status = "INSUFFICIENT_DATA"

        return {
            "compliance_status": compliance_status,
            "compliance_score": compliance_score,
            "total_milestones": len(milestones),
            "required_milestones": total_required,
            "completed_milestones": len(completed),
            "overdue_milestones": len(overdue),
            "upcoming_milestones": len(upcoming),
            "overdue_details": [
                {
                    "milestone": m.get("label", ""),
                    "expected_date": m.get("expected_date", ""),
                }
                for m in overdue
            ],
            "data_completeness_note": (
                "PAS compliance data is inferred from publicly available "
                "supplement history. Actual compliance may differ. "
                "Cross-reference with internal study management records."
            ),
        }

    # ------------------------------------------------------------------
    # Alert generation
    # ------------------------------------------------------------------

    def _generate_alerts(
        self,
        requirements: List[Dict],
        pas_status: Dict,
        compliance: Dict,
        _api_data: Dict,
    ) -> List[Dict]:
        """Generate PAS monitoring alerts.

        Args:
            requirements: PAS requirements.
            pas_status: Current PAS status.
            compliance: Compliance assessment.
            api_data: PMA API data.

        Returns:
            List of alert dicts.
        """
        alerts = []

        if not requirements:
            return alerts

        # Alert 1: PAS required
        for req in requirements:
            alerts.append({
                "alert_type": "pas_requirement_detected",
                "severity": "INFO",
                "description": (
                    f"{req.get('label', 'PAS')} detected. "
                    f"Source: {req.get('source', 'unknown')}. "
                    f"Confidence: {req.get('confidence', 0):.0%}"
                ),
                "cfr_ref": req.get("cfr_ref", ""),
            })

        # Alert 2: Overdue milestones
        overdue_details = compliance.get("overdue_details", [])
        for od in overdue_details:
            alerts.append({
                "alert_type": "overdue_milestone",
                "severity": "WARNING",
                "description": (
                    f"Milestone '{od.get('milestone', 'N/A')}' is overdue. "
                    f"Expected by: {od.get('expected_date', 'N/A')}"
                ),
            })

        # Alert 3: At-risk compliance
        comp_status = compliance.get("compliance_status", "")
        if comp_status in ("NON_COMPLIANT", "AT_RISK"):
            alerts.append({
                "alert_type": "compliance_risk",
                "severity": "ALERT",
                "description": (
                    f"PAS compliance status: {comp_status}. "
                    f"Score: {compliance.get('compliance_score', 0)}%. "
                    f"{compliance.get('overdue_milestones', 0)} overdue milestone(s)."
                ),
            })

        # Alert 4: Overall status concerns
        overall = pas_status.get("overall_status", "unknown")
        if overall == "at_risk":
            alerts.append({
                "alert_type": "study_at_risk",
                "severity": "WARNING",
                "description": (
                    "One or more PAS studies are at risk (delayed or terminated). "
                    "Review study management plan."
                ),
            })

        # Sort by severity
        severity_order = {"ALERT": 0, "WARNING": 1, "CAUTION": 2, "INFO": 3}
        alerts.sort(key=lambda a: severity_order.get(a.get("severity", "INFO"), 4))

        return alerts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str[:8], "%Y%m%d")
        except (ValueError, TypeError) as e:
            # Expected: try next format
            print(f"Warning: _parse_date YYYYMMDD format failed for {date_str!r}: {e}", file=sys.stderr)
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            # Expected: unrecognized date format
            print(f"Warning: _parse_date all formats failed for {date_str!r}: {e}", file=sys.stderr)
        return None

    def _save_report(self, pma_number: str, report: Dict) -> None:
        """Save PAS report to cache."""
        pma_dir = self.store.get_pma_dir(pma_number)
        report_path = pma_dir / "pas_report.json"
        tmp_path = report_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
            tmp_path.replace(report_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_pas_report(report: Dict) -> str:
    """Format PAS report as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("POST-APPROVAL STUDY (PAS) MONITORING REPORT")
    lines.append("=" * 70)
    lines.append(f"PMA Number:  {report.get('pma_number', 'N/A')}")
    lines.append(f"Device:      {report.get('device_name', 'N/A')}")
    lines.append(f"Applicant:   {report.get('applicant', 'N/A')}")
    lines.append(f"Approved:    {report.get('approval_date', 'N/A')}")
    lines.append(f"PAS Required: {'YES' if report.get('pas_required') else 'NO'}")
    lines.append("")

    # PAS requirements
    reqs = report.get("pas_requirements", [])
    if reqs:
        lines.append("--- PAS Requirements ---")
        for req in reqs:
            lines.append(
                f"  [{req.get('type', 'N/A')}] {req.get('label', 'N/A')}"
            )
            lines.append(
                f"    CFR: {req.get('cfr_ref', 'N/A')} | "
                f"Source: {req.get('source', 'N/A')} | "
                f"Confidence: {req.get('confidence', 0):.0%}"
            )
        lines.append("")

    # PAS status
    status = report.get("pas_status", {})
    if status.get("overall_status") != "no_pas_required":
        lines.append("--- PAS Status ---")
        lines.append(f"  Overall: {status.get('overall_status', 'N/A')}")
        for study in status.get("per_study", []):
            lines.append(
                f"  {study.get('label', 'N/A')}: "
                f"{study.get('status', 'N/A')} "
                f"({study.get('related_supplements', 0)} related supplements)"
            )
        lines.append("")

    # Milestones
    milestones = report.get("milestones", [])
    if milestones:
        lines.append("--- Milestone Timeline ---")
        lines.append(f"  {'Milestone':<30s} {'Expected':10s} {'Actual':10s} {'Status':10s}")
        lines.append(f"  {'-'*30} {'----------':10s} {'----------':10s} {'----------':10s}")
        for m in milestones:
            actual = m.get("actual_date", "") or "---"
            lines.append(
                f"  {m.get('label', 'N/A'):<30s} "
                f"{m.get('expected_date', 'N/A'):10s} "
                f"{actual:10s} "
                f"{m.get('status', 'N/A'):10s}"
            )
        lines.append("")

    # Compliance
    compliance = report.get("compliance", {})
    if compliance.get("compliance_status") != "not_applicable":
        lines.append("--- Compliance Assessment ---")
        lines.append(f"  Status: {compliance.get('compliance_status', 'N/A')}")
        lines.append(f"  Score: {compliance.get('compliance_score', 0)}%")
        lines.append(f"  Completed: {compliance.get('completed_milestones', 0)}/{compliance.get('total_milestones', 0)}")
        lines.append(f"  Overdue: {compliance.get('overdue_milestones', 0)}")
        lines.append("")

    # Alerts
    alerts = report.get("alerts", [])
    if alerts:
        lines.append("--- Alerts ---")
        for alert in alerts:
            lines.append(
                f"  [{alert.get('severity', 'INFO')}] "
                f"{alert.get('description', 'N/A')}"
            )
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {report.get('generated_at', 'N/A')[:10]}")
    lines.append("PAS data is inferred from public FDA supplement history.")
    lines.append("Cross-reference with internal study records for accuracy.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PAS Monitor -- Post-Approval Study tracking and compliance"
    )
    parser.add_argument("--pma", help="PMA number to analyze")
    parser.add_argument("--batch", help="Comma-separated PMA numbers")
    parser.add_argument("--milestones", action="store_true",
                        help="Show milestone timeline only")
    parser.add_argument("--compliance", action="store_true",
                        help="Show compliance status only")
    parser.add_argument("--alerts", action="store_true",
                        help="Show alerts only")
    parser.add_argument("--refresh", action="store_true",
                        help="Force API refresh")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    monitor = PASMonitor()

    result = None

    if args.batch:
        pma_list = [p.strip().upper() for p in args.batch.split(",") if p.strip()]
        reports = {}
        for pma in pma_list:
            reports[pma] = monitor.generate_pas_report(pma, refresh=args.refresh)
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_pmas": len(pma_list),
            "reports": reports,
        }
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            for pma, rep in reports.items():
                print(_format_pas_report(rep))
                print()

    elif args.pma:
        result = monitor.generate_pas_report(args.pma, refresh=args.refresh)

        if args.milestones:
            milestones = result.get("milestones", [])
            if args.json:
                print(json.dumps(milestones, indent=2, default=str))
            else:
                for m in milestones:
                    actual = m.get("actual_date", "") or "---"
                    print(
                        f"{m.get('label', 'N/A'):<30s} "
                        f"{m.get('expected_date', 'N/A'):10s} "
                        f"{actual:10s} "
                        f"{m.get('status', 'N/A'):10s}"
                    )
        elif args.compliance:
            compliance = result.get("compliance", {})
            if args.json:
                print(json.dumps(compliance, indent=2))
            else:
                print(f"Status: {compliance.get('compliance_status', 'N/A')}")
                print(f"Score: {compliance.get('compliance_score', 0)}%")
                print(f"Overdue: {compliance.get('overdue_milestones', 0)}")
        elif args.alerts:
            alerts = result.get("alerts", [])
            if args.json:
                print(json.dumps(alerts, indent=2))
            else:
                for alert in alerts:
                    print(f"[{alert['severity']}] {alert['description']}")
        elif args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(_format_pas_report(result))
    else:
        parser.error("Specify --pma PMA_NUMBER or --batch PMA1,PMA2")

    if args.output and result:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
