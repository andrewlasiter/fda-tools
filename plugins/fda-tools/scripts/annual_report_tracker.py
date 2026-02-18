#!/usr/bin/env python3
"""
PMA Annual Report Requirements Tracker -- Automated tracking of PMA annual
report obligations per 21 CFR 814.84.

Parses PMA approval data for annual report requirements, calculates due dates,
generates compliance calendars, identifies non-compliance risks, and tracks
required reporting sections based on device characteristics.

Annual Report Requirements (21 CFR 814.84):
    Within 60 days after the anniversary date of PMA approval, the holder shall
    submit a periodic report containing the following:
    1. Quantities distributed (number of devices, including returns/replacements)
    2. Corrections and removals (if any)
    3. Adverse event summaries (MAUDE cross-reference)
    4. Summary of changes made under 30-day notice or other supplements
    5. Updates on any required post-approval studies
    6. Additional manufacturing information (per approval conditions)
    7. Status of conditions of approval

Usage:
    from annual_report_tracker import AnnualReportTracker

    tracker = AnnualReportTracker()
    calendar = tracker.generate_compliance_calendar("P170019")
    status = tracker.assess_compliance("P170019")
    requirements = tracker.get_reporting_requirements("P170019")

    # CLI usage:
    python3 annual_report_tracker.py --pma P170019
    python3 annual_report_tracker.py --pma P170019 --calendar
    python3 annual_report_tracker.py --pma P170019 --compliance-status
    python3 annual_report_tracker.py --batch P170019,P200024
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
# Annual report section definitions (21 CFR 814.84(b))
# ------------------------------------------------------------------

ANNUAL_REPORT_SECTIONS = {
    "device_distribution": {
        "label": "Device Distribution Data",
        "cfr_ref": "21 CFR 814.84(b)(1)",
        "required": True,
        "description": (
            "Number of devices distributed, including the number of devices "
            "returned to the applicant, the number of devices for which the "
            "applicant received reports of failures or complaints."
        ),
    },
    "device_modifications": {
        "label": "Summary of Device Modifications",
        "cfr_ref": "21 CFR 814.84(b)(2)",
        "required": True,
        "description": (
            "Description of any changes made in the device or its labeling. "
            "Include supplements and 30-day notices filed during the period."
        ),
    },
    "corrections_removals": {
        "label": "Corrections and Removals",
        "cfr_ref": "21 CFR 814.84(b)(3)",
        "required": True,
        "description": (
            "Summary of corrections, removals, and recalls reported under "
            "21 CFR Part 806 during the reporting period."
        ),
    },
    "adverse_events": {
        "label": "Adverse Event Summaries",
        "cfr_ref": "21 CFR 814.84(b)(4)",
        "required": True,
        "description": (
            "Summaries of all reports of adverse experiences (MDRs) submitted "
            "under 21 CFR Part 803 during the reporting period."
        ),
    },
    "clinical_studies": {
        "label": "Clinical Studies / Post-Approval Studies",
        "cfr_ref": "21 CFR 814.84(b)(5)",
        "required": True,
        "description": (
            "Status of any ongoing or completed clinical investigations "
            "required as conditions of approval or initiated voluntarily."
        ),
    },
    "manufacturing_changes": {
        "label": "Manufacturing Changes",
        "cfr_ref": "21 CFR 814.84(b)(6)",
        "required": True,
        "description": (
            "Summary of manufacturing changes that did not require submission "
            "of a supplement, including process changes."
        ),
    },
    "sterilization_failures": {
        "label": "Sterilization Failures",
        "cfr_ref": "21 CFR 814.84(b)(7)",
        "required_if": "sterile_device",
        "description": (
            "Summary of sterilization failures and lot rejections. "
            "Required only for sterile devices."
        ),
    },
    "other_information": {
        "label": "Other Information",
        "cfr_ref": "21 CFR 814.84(b)(8)",
        "required_if": "approval_conditions",
        "description": (
            "Any other information as specified in the conditions of "
            "approval order for the device."
        ),
    },
}

# Device characteristics that affect required sections
DEVICE_CHARACTERISTICS = {
    "sterile_device": {
        "label": "Sterile Device",
        "keywords": [
            "sterile", "sterilization", "sterilized", "EO", "ethylene oxide",
            "gamma", "e-beam", "radiation sterilized",
        ],
        "additional_sections": ["sterilization_failures"],
    },
    "implantable": {
        "label": "Implantable Device",
        "keywords": [
            "implant", "implantable", "permanent implant",
        ],
        "additional_sections": ["explantation_data"],
    },
    "software_device": {
        "label": "Software / SaMD",
        "keywords": [
            "software", "SaMD", "algorithm", "AI", "machine learning",
        ],
        "additional_sections": ["software_updates"],
    },
}

# Grace period for annual report submission
ANNUAL_REPORT_GRACE_PERIOD_DAYS = 60  # Per 21 CFR 814.84(a)


# ------------------------------------------------------------------
# Annual Report Tracker
# ------------------------------------------------------------------

class AnnualReportTracker:
    """Automated tracking of PMA annual report obligations.

    Calculates due dates, generates compliance calendars, identifies
    required reporting sections, and assesses compliance status.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize Annual Report Tracker.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()

    # ------------------------------------------------------------------
    # Main report generation
    # ------------------------------------------------------------------

    def generate_compliance_calendar(
        self,
        pma_number: str,
        years_forward: int = 3,
        refresh: bool = False,
    ) -> Dict:
        """Generate an annual report compliance calendar for a PMA.

        Args:
            pma_number: PMA number.
            years_forward: Number of years to project forward.
            refresh: Force refresh from API.

        Returns:
            Compliance calendar dict with due dates and requirements.
        """
        pma_key = pma_number.upper()

        # Load PMA data
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        # Extract approval date
        approval_date = self._parse_date(api_data.get("decision_date", ""))
        if approval_date is None:
            return {
                "pma_number": pma_key,
                "error": "Cannot determine approval date for annual report calculation",
            }

        # Load supplements to understand device characteristics
        supplements = self.store.get_supplements(pma_key, refresh=refresh)

        # Determine device characteristics
        characteristics = self._determine_device_characteristics(
            api_data, supplements
        )

        # Determine required sections
        required_sections = self._determine_required_sections(characteristics)

        # Generate due dates
        due_dates = self._generate_due_dates(
            approval_date, years_forward
        )

        # Assess historical compliance from supplement patterns
        compliance_history = self._assess_historical_compliance(
            supplements, approval_date
        )

        # Generate non-compliance risks
        risks = self._assess_compliance_risks(
            due_dates, compliance_history, supplements
        )

        calendar = {
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "applicant": api_data.get("applicant", ""),
            "approval_date": approval_date.strftime("%Y-%m-%d"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cfr_reference": "21 CFR 814.84",
            "grace_period_days": ANNUAL_REPORT_GRACE_PERIOD_DAYS,
            "device_characteristics": characteristics,
            "required_sections": required_sections,
            "due_dates": due_dates,
            "compliance_history": compliance_history,
            "compliance_risks": risks,
            "next_due_date": self._get_next_due_date(due_dates),
            "total_reports_expected": self._count_expected_reports(approval_date),
        }

        # Cache the calendar
        self._save_calendar(pma_key, calendar)

        return calendar

    # ------------------------------------------------------------------
    # Multi-PMA batch calendar
    # ------------------------------------------------------------------

    def generate_batch_calendar(
        self,
        pma_numbers: List[str],
        refresh: bool = False,
    ) -> Dict:
        """Generate compliance calendar for multiple PMAs.

        Args:
            pma_numbers: List of PMA numbers.
            refresh: Force API refresh.

        Returns:
            Batch calendar with per-PMA calendars and consolidated deadlines.
        """
        calendars = {}
        all_deadlines = []

        for pma in pma_numbers:
            cal = self.generate_compliance_calendar(pma, refresh=refresh)
            calendars[pma.upper()] = cal
            next_due = cal.get("next_due_date")
            if next_due and isinstance(next_due, dict):
                all_deadlines.append({
                    "pma_number": pma.upper(),
                    "device_name": cal.get("device_name", ""),
                    "due_date": next_due.get("due_date", ""),
                    "grace_deadline": next_due.get("grace_deadline", ""),
                    "report_number": next_due.get("report_number", 0),
                })

        # Sort by next due date
        all_deadlines.sort(key=lambda d: d.get("due_date", ""))

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_pmas": len(pma_numbers),
            "calendars": calendars,
            "upcoming_deadlines": all_deadlines,
        }

    # ------------------------------------------------------------------
    # Date calculations
    # ------------------------------------------------------------------

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string from FDA format.

        Args:
            date_str: Date string in YYYYMMDD or YYYY-MM-DD format.

        Returns:
            Parsed datetime or None.
        """
        if not date_str:
            return None

        # Try YYYYMMDD format (FDA default)
        try:
            return datetime.strptime(date_str[:8], "%Y%m%d")
        except (ValueError, TypeError) as e:
            # Expected: try next format
            print(f"Warning: _parse_date YYYYMMDD format failed for {date_str!r}: {e}", file=sys.stderr)

        # Try YYYY-MM-DD format
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except (ValueError, TypeError) as e:
            # Expected: unrecognized date format
            print(f"Warning: _parse_date all formats failed for {date_str!r}: {e}", file=sys.stderr)

        return None

    def _generate_due_dates(
        self,
        approval_date: datetime,
        years_forward: int = 3,
    ) -> List[Dict]:
        """Generate annual report due dates.

        Annual reports are due within 60 days of the approval anniversary.

        Args:
            approval_date: Original PMA approval date.
            years_forward: Number of years to project forward.

        Returns:
            List of due date dicts.
        """
        now = datetime.now()
        due_dates = []

        # Calculate for each year since approval
        current_year = now.year
        approval_year = approval_date.year

        for year_offset in range(1, (current_year - approval_year) + years_forward + 1):
            anniversary = approval_date.replace(
                year=approval_date.year + year_offset
            )
            grace_deadline = anniversary + timedelta(
                days=ANNUAL_REPORT_GRACE_PERIOD_DAYS
            )

            # Determine status
            if grace_deadline < now:
                status = "past_due" if anniversary.year <= current_year else "future"
            elif anniversary < now:
                status = "due_now"
            else:
                status = "future"

            # Reporting period
            period_start = approval_date.replace(
                year=approval_date.year + year_offset - 1
            )
            period_end = anniversary - timedelta(days=1)

            due_dates.append({
                "report_number": year_offset,
                "anniversary_date": anniversary.strftime("%Y-%m-%d"),
                "due_date": anniversary.strftime("%Y-%m-%d"),
                "grace_deadline": grace_deadline.strftime("%Y-%m-%d"),
                "reporting_period_start": period_start.strftime("%Y-%m-%d"),
                "reporting_period_end": period_end.strftime("%Y-%m-%d"),
                "status": status,
                "year": anniversary.year,
            })

        return due_dates

    def _get_next_due_date(self, due_dates: List[Dict]) -> Optional[Dict]:
        """Get the next upcoming due date.

        Args:
            due_dates: List of due date dicts.

        Returns:
            Next due date dict, or None.
        """
        for dd in due_dates:
            if dd.get("status") in ("due_now", "future"):
                return dd
        return None

    def _count_expected_reports(self, approval_date: datetime) -> int:
        """Count the number of annual reports expected to date.

        Args:
            approval_date: Original approval date.

        Returns:
            Number of expected reports.
        """
        now = datetime.now()
        years = now.year - approval_date.year
        # Adjust if we haven't reached the anniversary month yet
        if (now.month, now.day) < (approval_date.month, approval_date.day):
            years -= 1
        return max(years, 0)

    # ------------------------------------------------------------------
    # Device characteristics
    # ------------------------------------------------------------------

    def _determine_device_characteristics(
        self,
        api_data: Dict,
        supplements: List[Dict],
    ) -> List[Dict]:
        """Determine device characteristics that affect annual report requirements.

        Args:
            api_data: PMA API data.
            supplements: Supplement list.

        Returns:
            List of identified characteristic dicts.
        """
        characteristics = []

        # Build combined text for keyword matching
        device_name = api_data.get("device_name", "").lower()
        generic_name = api_data.get("generic_name", "").lower()
        ao_statement = api_data.get("ao_statement", "").lower()

        supp_text = ""
        for s in supplements[:10]:
            supp_text += f" {s.get('supplement_type', '')} {s.get('supplement_reason', '')}"
        supp_text = supp_text.lower()

        combined = f"{device_name} {generic_name} {ao_statement} {supp_text}"

        for char_key, char_def in DEVICE_CHARACTERISTICS.items():
            for kw in char_def["keywords"]:
                if kw.lower() in combined:
                    characteristics.append({
                        "characteristic": char_key,
                        "label": char_def["label"],
                        "matched_keyword": kw,
                        "additional_sections": char_def.get("additional_sections", []),
                    })
                    break

        return characteristics

    # ------------------------------------------------------------------
    # Required sections
    # ------------------------------------------------------------------

    def _determine_required_sections(
        self,
        characteristics: List[Dict],
    ) -> List[Dict]:
        """Determine required annual report sections based on device characteristics.

        Args:
            characteristics: Identified device characteristics.

        Returns:
            List of required section dicts.
        """
        sections = []
        char_keys = set(c.get("characteristic", "") for c in characteristics)

        for sec_key, sec_def in ANNUAL_REPORT_SECTIONS.items():
            required = sec_def.get("required", False)

            # Check conditional requirements
            required_if = sec_def.get("required_if", "")
            if required_if and required_if in char_keys:
                required = True

            sections.append({
                "section": sec_key,
                "label": sec_def["label"],
                "cfr_ref": sec_def["cfr_ref"],
                "required": required,
                "description": sec_def["description"],
            })

        # Add characteristic-specific sections
        for char in characteristics:
            for extra_sec in char.get("additional_sections", []):
                if not any(s.get("section") == extra_sec for s in sections):
                    sections.append({
                        "section": extra_sec,
                        "label": extra_sec.replace("_", " ").title(),
                        "cfr_ref": "Device-specific",
                        "required": True,
                        "description": (
                            f"Additional section required for "
                            f"{char.get('label', 'this device type')}."
                        ),
                    })

        return sections

    # ------------------------------------------------------------------
    # Compliance assessment
    # ------------------------------------------------------------------

    def _assess_historical_compliance(
        self,
        supplements: List[Dict],
        approval_date: datetime,
    ) -> Dict:
        """Assess historical compliance from supplement patterns.

        Annual report supplements sometimes appear in the supplement list.
        We look for patterns suggesting annual reports were filed.

        Args:
            supplements: Supplement list.
            approval_date: Original approval date.

        Returns:
            Historical compliance dict.
        """
        # Look for annual-report related supplements
        ar_keywords = [
            "annual report", "periodic report", "annual", "yearly report"
        ]

        ar_supplements = []
        for supp in supplements:
            combined = (
                f"{supp.get('supplement_type', '')} "
                f"{supp.get('supplement_reason', '')}"
            ).lower()
            if any(kw in combined for kw in ar_keywords):
                ar_supplements.append({
                    "supplement_number": supp.get("supplement_number", ""),
                    "decision_date": supp.get("decision_date", ""),
                })

        # Count expected reports
        total_expected = self._count_expected_reports(approval_date)

        # Note: FDA does not publicly track annual report submissions
        # in openFDA, so this is necessarily incomplete. We flag the
        # information gap.

        return {
            "annual_report_supplements_detected": len(ar_supplements),
            "total_reports_expected": total_expected,
            "detected_submissions": ar_supplements,
            "completeness_note": (
                "Annual report submission data is not publicly available "
                "through openFDA. Detected count is based on supplement "
                "keyword matching and may be incomplete."
            ),
        }

    def _assess_compliance_risks(
        self,
        due_dates: List[Dict],
        compliance_history: Dict,
        supplements: List[Dict],
    ) -> List[Dict]:
        """Assess compliance risks for annual reporting.

        Args:
            due_dates: List of due date dicts.
            compliance_history: Historical compliance assessment.
            supplements: Supplement list.

        Returns:
            List of compliance risk dicts.
        """
        risks = []

        # Risk 1: Overdue reports
        _overdue = [d for d in due_dates if d.get("status") == "past_due"]
        total_expected = compliance_history.get("total_reports_expected", 0)
        if total_expected > 0:
            risks.append({
                "risk": "annual_report_compliance",
                "severity": "INFO",
                "description": (
                    f"{total_expected} annual report(s) expected since approval. "
                    f"FDA does not publicly track annual report submissions. "
                    f"Verify compliance with your regulatory files."
                ),
                "total_expected": total_expected,
            })

        # Risk 2: Upcoming deadline
        now = datetime.now()
        for dd in due_dates:
            if dd.get("status") == "due_now":
                risks.append({
                    "risk": "report_due_now",
                    "severity": "WARNING",
                    "description": (
                        f"Annual report #{dd.get('report_number', 'N/A')} "
                        f"is due now (grace deadline: {dd.get('grace_deadline', 'N/A')})."
                    ),
                    "due_date": dd.get("due_date", ""),
                    "grace_deadline": dd.get("grace_deadline", ""),
                })
                break

        # Risk 3: Upcoming deadline within 90 days
        for dd in due_dates:
            if dd.get("status") == "future":
                try:
                    due = datetime.strptime(dd.get("due_date", ""), "%Y-%m-%d")
                    if (due - now).days <= 90:
                        risks.append({
                            "risk": "approaching_deadline",
                            "severity": "INFO",
                            "description": (
                                f"Annual report #{dd.get('report_number', 'N/A')} "
                                f"due in {(due - now).days} days "
                                f"({dd.get('due_date', 'N/A')})."
                            ),
                            "due_date": dd.get("due_date", ""),
                            "days_until_due": (due - now).days,
                        })
                    break
                except (ValueError, TypeError) as e:
                    print(f"Warning: Could not parse due_date for compliance risk: {e}", file=sys.stderr)

        # Risk 4: Multiple supplements suggest active device -- check MAUDE data
        supp_count = len(supplements)
        if supp_count >= 10:
            risks.append({
                "risk": "active_device_monitoring",
                "severity": "INFO",
                "description": (
                    f"Device has {supp_count} supplements indicating active "
                    f"modifications. Ensure MAUDE data is comprehensive in annual reports."
                ),
            })

        return risks

    # ------------------------------------------------------------------
    # Enhanced: Distribution data template (FDA-66)
    # ------------------------------------------------------------------

    def generate_distribution_template(
        self,
        pma_number: str,
        reporting_period_start: str = "",
        reporting_period_end: str = "",
    ) -> Dict:
        """Generate a distribution data template per 21 CFR 814.84(b)(1).

        Args:
            pma_number: PMA number.
            reporting_period_start: Period start date (YYYY-MM-DD).
            reporting_period_end: Period end date (YYYY-MM-DD).

        Returns:
            Distribution data template dict.
        """
        return {
            "section": "device_distribution",
            "cfr_ref": "21 CFR 814.84(b)(1)",
            "pma_number": pma_number.upper(),
            "reporting_period": {
                "start": reporting_period_start,
                "end": reporting_period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "distribution_data": {
                "total_devices_distributed": None,  # Integer
                "domestic_distribution": None,  # Integer
                "international_distribution": None,  # Integer
                "distribution_by_region": {},  # region -> count
                "devices_returned": None,  # Integer
                "devices_replaced": None,  # Integer
                "return_reasons": [],  # List of {"reason": "", "count": 0}
                "failure_complaints_received": None,  # Integer
                "complaint_categories": [],  # List of {"category": "", "count": 0}
            },
            "notes": "",
            "preparer": "",
            "preparation_date": "",
        }

    # ------------------------------------------------------------------
    # Enhanced: Adverse event summary generator (FDA-66)
    # ------------------------------------------------------------------

    def generate_adverse_event_summary(
        self,
        pma_number: str,
        reporting_period_start: str = "",
        reporting_period_end: str = "",
        maude_data: Optional[List[Dict]] = None,
    ) -> Dict:
        """Generate an adverse event summary template per 21 CFR 814.84(b)(4).

        Args:
            pma_number: PMA number.
            reporting_period_start: Period start date.
            reporting_period_end: Period end date.
            maude_data: Optional MAUDE data to pre-populate summary.

        Returns:
            Adverse event summary dict.
        """
        # Pre-populate from MAUDE data if available
        mdr_summary = []
        total_events = 0
        if maude_data:
            event_types = {}
            for event in maude_data:
                etype = event.get("event_type", "Unknown")
                event_types[etype] = event_types.get(etype, 0) + 1
                total_events += 1
            for etype, count in sorted(event_types.items(), key=lambda x: -x[1]):
                mdr_summary.append({"event_type": etype, "count": count})

        return {
            "section": "adverse_events",
            "cfr_ref": "21 CFR 814.84(b)(4)",
            "pma_number": pma_number.upper(),
            "reporting_period": {
                "start": reporting_period_start,
                "end": reporting_period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_mdr_reports": total_events,
                "deaths": None,  # Integer
                "serious_injuries": None,  # Integer
                "malfunctions": None,  # Integer
                "other_events": None,  # Integer
                "event_type_breakdown": mdr_summary,
            },
            "trending_analysis": {
                "comparison_to_prior_period": "",  # increase/decrease/stable
                "new_signal_detected": False,
                "signal_description": "",
                "corrective_actions_taken": [],
            },
            "maude_cross_reference": {
                "maude_search_performed": False,
                "maude_report_numbers": [],
                "maude_search_date": "",
            },
            "narrative_summary": "",  # To be filled
            "notes": "",
            "preparer": "",
        }

    # ------------------------------------------------------------------
    # Enhanced: Device modification tracking (FDA-66)
    # ------------------------------------------------------------------

    def generate_modification_tracker(
        self,
        pma_number: str,
        supplements: Optional[List[Dict]] = None,
        reporting_period_start: str = "",
        reporting_period_end: str = "",
    ) -> Dict:
        """Generate a device modification tracking template per 21 CFR 814.84(b)(2).

        Args:
            pma_number: PMA number.
            supplements: Optional supplement data to pre-populate.
            reporting_period_start: Period start date.
            reporting_period_end: Period end date.

        Returns:
            Device modification tracker dict.
        """
        # Pre-populate from supplement data
        supplement_changes = []
        non_supplement_changes = []

        if supplements:
            for supp in supplements:
                supp_date = supp.get("decision_date", "")
                # Check if supplement falls within reporting period
                in_period = True
                if reporting_period_start and supp_date:
                    in_period = supp_date >= reporting_period_start.replace("-", "")
                if reporting_period_end and supp_date:
                    in_period = in_period and supp_date <= reporting_period_end.replace("-", "")

                if in_period:
                    supplement_changes.append({
                        "supplement_number": supp.get("supplement_number", ""),
                        "supplement_type": supp.get("supplement_type", ""),
                        "description": supp.get("supplement_reason", ""),
                        "decision_date": supp_date,
                        "decision_code": supp.get("decision_code", ""),
                    })

        return {
            "section": "device_modifications",
            "cfr_ref": "21 CFR 814.84(b)(2)",
            "pma_number": pma_number.upper(),
            "reporting_period": {
                "start": reporting_period_start,
                "end": reporting_period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "supplement_changes": supplement_changes,
            "non_supplement_changes": non_supplement_changes,
            "thirty_day_notices": [],  # List of 30-day notice changes
            "labeling_changes": [],  # List of labeling changes
            "design_changes": [],  # List of design changes
            "software_changes": [],  # List of software changes
            "total_changes": len(supplement_changes) + len(non_supplement_changes),
            "notes": "",
            "preparer": "",
        }

    # ------------------------------------------------------------------
    # Enhanced: Bibliography updates (FDA-66)
    # ------------------------------------------------------------------

    def generate_bibliography_template(
        self,
        pma_number: str,
        reporting_period_start: str = "",
        reporting_period_end: str = "",
    ) -> Dict:
        """Generate a bibliography update template for annual report.

        Args:
            pma_number: PMA number.
            reporting_period_start: Period start date.
            reporting_period_end: Period end date.

        Returns:
            Bibliography update template dict.
        """
        return {
            "section": "bibliography",
            "cfr_ref": "21 CFR 814.84 (supplementary)",
            "pma_number": pma_number.upper(),
            "reporting_period": {
                "start": reporting_period_start,
                "end": reporting_period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "new_publications": [],  # List of {"citation": "", "pmid": "", "relevance": "", "summary": ""}
            "conference_presentations": [],  # List of {"title": "", "conference": "", "date": "", "authors": ""}
            "regulatory_guidances": [],  # List of new/updated FDA guidances
            "standards_updates": [],  # List of new/updated standards
            "total_new_references": 0,
            "notes": "",
            "preparer": "",
        }

    # ------------------------------------------------------------------
    # Enhanced: Post-approval study status (FDA-66)
    # ------------------------------------------------------------------

    def generate_pas_status_template(
        self,
        pma_number: str,
        reporting_period_start: str = "",
        reporting_period_end: str = "",
    ) -> Dict:
        """Generate a post-approval study status template per 21 CFR 814.84(b)(5).

        Args:
            pma_number: PMA number.
            reporting_period_start: Period start date.
            reporting_period_end: Period end date.

        Returns:
            PAS status template dict for inclusion in annual report.
        """
        return {
            "section": "clinical_studies",
            "cfr_ref": "21 CFR 814.84(b)(5)",
            "pma_number": pma_number.upper(),
            "reporting_period": {
                "start": reporting_period_start,
                "end": reporting_period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "studies": [],  # List of study status entries -- see below
            "study_template": {
                "study_name": "",
                "study_type": "",  # Condition of Approval, Section 522, Voluntary
                "protocol_number": "",
                "irb_approval_status": "",
                "enrollment_target": None,
                "enrolled_to_date": None,
                "enrollment_completion_date": "",
                "follow_up_duration": "",
                "interim_results_available": False,
                "interim_results_summary": "",
                "study_status": "",  # Enrolling, Follow-up, Complete, Terminated
                "issues_encountered": [],
                "next_milestone": "",
                "next_milestone_date": "",
            },
            "notes": "",
            "preparer": "",
        }

    # ------------------------------------------------------------------
    # Enhanced: Manufacturing changes documentation (FDA-66)
    # ------------------------------------------------------------------

    def generate_manufacturing_changes_template(
        self,
        pma_number: str,
        reporting_period_start: str = "",
        reporting_period_end: str = "",
    ) -> Dict:
        """Generate a manufacturing changes template per 21 CFR 814.84(b)(6).

        Args:
            pma_number: PMA number.
            reporting_period_start: Period start date.
            reporting_period_end: Period end date.

        Returns:
            Manufacturing changes template dict.
        """
        return {
            "section": "manufacturing_changes",
            "cfr_ref": "21 CFR 814.84(b)(6)",
            "pma_number": pma_number.upper(),
            "reporting_period": {
                "start": reporting_period_start,
                "end": reporting_period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "process_changes": [],  # List of {"description": "", "date": "", "impact_assessment": "", "validation_status": ""}
            "facility_changes": [],  # List of facility modifications
            "supplier_changes": [],  # List of supplier or material changes
            "equipment_changes": [],  # List of manufacturing equipment changes
            "sterilization_changes": [],  # List of sterilization process changes
            "quality_system_changes": [],  # List of QMS changes
            "total_changes": 0,
            "changes_requiring_supplement": 0,
            "changes_not_requiring_supplement": 0,
            "notes": "",
            "preparer": "",
        }

    # ------------------------------------------------------------------
    # Enhanced: Labeling changes tracker (FDA-66)
    # ------------------------------------------------------------------

    def generate_labeling_changes_template(
        self,
        pma_number: str,
        reporting_period_start: str = "",
        reporting_period_end: str = "",
    ) -> Dict:
        """Generate a labeling changes tracker template.

        Args:
            pma_number: PMA number.
            reporting_period_start: Period start date.
            reporting_period_end: Period end date.

        Returns:
            Labeling changes tracker template dict.
        """
        return {
            "section": "labeling_changes",
            "cfr_ref": "21 CFR 814.84(b)(2) (labeling subset)",
            "pma_number": pma_number.upper(),
            "reporting_period": {
                "start": reporting_period_start,
                "end": reporting_period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ifu_changes": [],  # Instructions for Use changes
            "labeling_text_changes": [],  # Label text changes
            "indication_changes": [],  # Indication/intended use changes
            "warning_changes": [],  # Warning/precaution changes
            "contraindication_changes": [],  # Contraindication changes
            "promotional_material_changes": [],  # Promotional material changes
            "total_labeling_changes": 0,
            "changes_submitted_as_supplement": 0,
            "changes_submitted_as_30_day_notice": 0,
            "changes_not_requiring_submission": 0,
            "notes": "",
            "preparer": "",
        }

    # ------------------------------------------------------------------
    # Enhanced: Complete annual report outline (FDA-66)
    # ------------------------------------------------------------------

    def generate_annual_report_outline(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict:
        """Generate a complete annual report outline per 21 CFR 814.84.

        This is the primary enhanced method that assembles all sections
        into a comprehensive annual report template.

        Args:
            pma_number: PMA number.
            refresh: Force API refresh.

        Returns:
            Complete annual report outline dict.
        """
        pma_key = pma_number.upper()

        # Load PMA data for context
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        # Get approval date for period calculation
        approval_date = self._parse_date(api_data.get("decision_date", ""))
        if approval_date is None:
            return {
                "pma_number": pma_key,
                "error": "Cannot determine approval date",
            }

        # Calculate current reporting period
        now = datetime.now()
        years_since = now.year - approval_date.year
        if (now.month, now.day) < (approval_date.month, approval_date.day):
            years_since -= 1
        years_since = max(years_since, 1)

        period_start = approval_date.replace(
            year=approval_date.year + years_since - 1
        ).strftime("%Y-%m-%d")
        period_end = approval_date.replace(
            year=approval_date.year + years_since
        ).strftime("%Y-%m-%d")

        # Load supplements for modification tracking
        supplements = self.store.get_supplements(pma_key, refresh=refresh)

        # Determine device characteristics
        characteristics = self._determine_device_characteristics(api_data, supplements)

        # Build the complete outline
        outline = {
            "document_type": "PMA Annual Report",
            "cfr_ref": "21 CFR 814.84",
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "applicant": api_data.get("applicant", ""),
            "approval_date": approval_date.strftime("%Y-%m-%d"),
            "report_number": years_since,
            "reporting_period": {
                "start": period_start,
                "end": period_end,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": {
                "distribution": self.generate_distribution_template(
                    pma_key, period_start, period_end
                ),
                "modifications": self.generate_modification_tracker(
                    pma_key, supplements, period_start, period_end
                ),
                "adverse_events": self.generate_adverse_event_summary(
                    pma_key, period_start, period_end
                ),
                "pas_status": self.generate_pas_status_template(
                    pma_key, period_start, period_end
                ),
                "manufacturing": self.generate_manufacturing_changes_template(
                    pma_key, period_start, period_end
                ),
                "labeling": self.generate_labeling_changes_template(
                    pma_key, period_start, period_end
                ),
                "bibliography": self.generate_bibliography_template(
                    pma_key, period_start, period_end
                ),
            },
            "device_characteristics": characteristics,
            "submission_deadline": (
                approval_date.replace(year=approval_date.year + years_since)
                + timedelta(days=ANNUAL_REPORT_GRACE_PERIOD_DAYS)
            ).strftime("%Y-%m-%d"),
            "completion_status": {
                "sections_completed": 0,
                "sections_total": 7,
                "pct_complete": 0.0,
            },
            "disclaimer": (
                "This annual report outline is auto-generated for planning purposes. "
                "All data must be verified by qualified regulatory professionals "
                "before submission to FDA. Refer to 21 CFR 814.84 for complete requirements."
            ),
        }

        return outline

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _save_calendar(self, pma_number: str, calendar: Dict) -> None:
        """Save compliance calendar to cache."""
        pma_dir = self.store.get_pma_dir(pma_number)
        cal_path = pma_dir / "annual_report_calendar.json"
        tmp_path = cal_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(calendar, f, indent=2, default=str)
            tmp_path.replace(cal_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_calendar(calendar: Dict) -> str:
    """Format compliance calendar as readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("PMA ANNUAL REPORT COMPLIANCE CALENDAR")
    lines.append("=" * 70)
    lines.append(f"PMA Number:   {calendar.get('pma_number', 'N/A')}")
    lines.append(f"Device:       {calendar.get('device_name', 'N/A')}")
    lines.append(f"Applicant:    {calendar.get('applicant', 'N/A')}")
    lines.append(f"Approved:     {calendar.get('approval_date', 'N/A')}")
    lines.append(f"CFR Ref:      {calendar.get('cfr_reference', 'N/A')}")
    lines.append(f"Grace Period: {calendar.get('grace_period_days', 60)} days")
    lines.append("")

    # Next due date
    next_due = calendar.get("next_due_date")
    if next_due:
        lines.append("--- NEXT DUE DATE ---")
        lines.append(f"  Report #{next_due.get('report_number', 'N/A')}")
        lines.append(f"  Anniversary: {next_due.get('anniversary_date', 'N/A')}")
        lines.append(f"  Grace Deadline: {next_due.get('grace_deadline', 'N/A')}")
        lines.append(f"  Period: {next_due.get('reporting_period_start', 'N/A')} to {next_due.get('reporting_period_end', 'N/A')}")
        lines.append("")

    # Required sections
    sections = calendar.get("required_sections", [])
    if sections:
        lines.append("--- Required Report Sections ---")
        for sec in sections:
            req = "REQUIRED" if sec.get("required") else "CONDITIONAL"
            lines.append(f"  [{req}] {sec.get('label', 'N/A')}")
            lines.append(f"          {sec.get('cfr_ref', '')} -- {sec.get('description', '')[:70]}")
        lines.append("")

    # Due date calendar
    due_dates = calendar.get("due_dates", [])
    if due_dates:
        lines.append("--- Annual Report Calendar ---")
        lines.append(f"  {'#':>3s}  {'Due Date':10s}  {'Grace':10s}  {'Status':10s}")
        lines.append(f"  {'---':>3s}  {'----------':10s}  {'----------':10s}  {'----------':10s}")
        for dd in due_dates[-10:]:  # Show last 10
            lines.append(
                f"  {dd.get('report_number', 0):3d}  "
                f"{dd.get('due_date', 'N/A'):10s}  "
                f"{dd.get('grace_deadline', 'N/A'):10s}  "
                f"{dd.get('status', 'N/A'):10s}"
            )
        lines.append("")

    # Compliance risks
    risks = calendar.get("compliance_risks", [])
    if risks:
        lines.append("--- Compliance Risks ---")
        for risk in risks:
            lines.append(f"  [{risk.get('severity', 'INFO')}] {risk.get('description', 'N/A')}")
        lines.append("")

    # Device characteristics
    chars = calendar.get("device_characteristics", [])
    if chars:
        lines.append("--- Device Characteristics ---")
        for ch in chars:
            lines.append(f"  {ch.get('label', 'N/A')} (keyword: '{ch.get('matched_keyword', '')}')")
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {calendar.get('generated_at', 'N/A')[:10]}")
    lines.append(f"Total Reports Expected: {calendar.get('total_reports_expected', 'N/A')}")
    lines.append("Annual report compliance data is not publicly tracked by FDA.")
    lines.append("This calendar is for planning purposes. Verify with internal records.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PMA Annual Report Tracker -- Compliance calendar and requirements"
    )
    parser.add_argument("--pma", help="PMA number to analyze")
    parser.add_argument("--batch", help="Comma-separated PMA numbers for batch calendar")
    parser.add_argument("--calendar", action="store_true", help="Show full calendar")
    parser.add_argument("--annual-report", action="store_true", dest="annual_report",
                        help="Generate complete annual report outline (FDA-66 enhanced)")
    parser.add_argument("--distribution", action="store_true",
                        help="Generate distribution data template")
    parser.add_argument("--adverse-events", action="store_true", dest="adverse_events",
                        help="Generate adverse event summary template")
    parser.add_argument("--modifications", action="store_true",
                        help="Generate device modification tracker")
    parser.add_argument("--manufacturing", action="store_true",
                        help="Generate manufacturing changes template")
    parser.add_argument("--labeling", action="store_true",
                        help="Generate labeling changes template")
    parser.add_argument("--bibliography", action="store_true",
                        help="Generate bibliography template")
    parser.add_argument("--compliance-status", action="store_true",
                        dest="compliance_status", help="Show compliance status only")
    parser.add_argument("--years-forward", type=int, default=3,
                        dest="years_forward", help="Years to project forward (default 3)")
    parser.add_argument("--refresh", action="store_true", help="Force API refresh")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    tracker = AnnualReportTracker()

    if args.pma and args.annual_report:
        result = tracker.generate_annual_report_outline(args.pma, refresh=args.refresh)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"Annual Report Outline: {result.get('pma_number', 'N/A')}")
            print(f"Device: {result.get('device_name', 'N/A')}")
            print(f"Report #{result.get('report_number', 'N/A')}")
            print(f"Period: {result.get('reporting_period', {}).get('start', '')} to {result.get('reporting_period', {}).get('end', '')}")
            print(f"Deadline: {result.get('submission_deadline', 'N/A')}")
            sections = result.get("sections", {})
            print(f"Sections: {len(sections)}")
            for name, sec in sections.items():
                print(f"  - {name}: {sec.get('cfr_ref', 'N/A')}")
    elif args.pma and args.distribution:
        result = tracker.generate_distribution_template(args.pma)
        print(json.dumps(result, indent=2, default=str))
    elif args.pma and args.adverse_events:
        result = tracker.generate_adverse_event_summary(args.pma)
        print(json.dumps(result, indent=2, default=str))
    elif args.pma and args.modifications:
        result = tracker.generate_modification_tracker(args.pma)
        print(json.dumps(result, indent=2, default=str))
    elif args.pma and args.manufacturing:
        result = tracker.generate_manufacturing_changes_template(args.pma)
        print(json.dumps(result, indent=2, default=str))
    elif args.pma and args.labeling:
        result = tracker.generate_labeling_changes_template(args.pma)
        print(json.dumps(result, indent=2, default=str))
    elif args.pma and args.bibliography:
        result = tracker.generate_bibliography_template(args.pma)
        print(json.dumps(result, indent=2, default=str))
    elif args.batch:
        pma_list = [p.strip().upper() for p in args.batch.split(",") if p.strip()]
        result = tracker.generate_batch_calendar(pma_list, refresh=args.refresh)
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            for _pma, cal in result.get("calendars", {}).items():
                print(_format_calendar(cal))
                print()
    elif args.pma:
        result = tracker.generate_compliance_calendar(
            args.pma,
            years_forward=args.years_forward,
            refresh=args.refresh,
        )
        if args.compliance_status:
            risks = result.get("compliance_risks", [])
            if args.json:
                print(json.dumps(risks, indent=2))
            else:
                for risk in risks:
                    print(f"[{risk['severity']}] {risk['description']}")
        elif args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(_format_calendar(result))
    else:
        parser.error("Specify --pma PMA_NUMBER or --batch PMA1,PMA2")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
