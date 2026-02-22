"""
FDA-236  [NPD-005] Post-Market Surveillance Integration with Signal Detection
=============================================================================
Wires together:
  - CUSUM-based MAUDE spike detection (`signal_cusum.CUSUMDetector`)
  - Cross-signal correlation (`signal_correlation.CrossSignalCorrelator`)
  - Regulatory reporting thresholds (21 CFR Part 803 MDR triggers)
  - PMS (Post-Market Surveillance) plan tracker

Post-market surveillance cycle
-------------------------------
1. Ingest: pull MAUDE adverse events and recall data by product code / K-number
2. Detect: run CUSUM detector on monthly event series
3. Correlate: cross-correlate MAUDE + recall + enforcement signals
4. Classify: map CUSUM severity → MDR reporting obligation
5. Report: flag events requiring 30-day / 5-day MDR reports per 21 CFR 803

MDR reporting thresholds (simplified)
--------------------------------------
- 30-Day MDR: device malfunction that could cause or contribute to a serious
  injury if it were to recur (21 CFR 803.50)
- 5-Day MDR: immediately life-threatening or requiring immediate action
  (21 CFR 803.53)
- PMA periodic report: >= 2x baseline adverse event rate (FDA PMA guidance)

CUSUM severity -> MDR mapping
-----------------------------
MEDIUM / HIGH  -> Flag for 30-Day MDR review
CRITICAL       -> Flag for 5-Day MDR review
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


# -- MDR obligation -----------------------------------------------------------


class MdrObligation(str, Enum):
    NONE          = "NONE"
    MONITOR       = "MONITOR"
    MDR_30_DAY    = "MDR_30_DAY"
    MDR_5_DAY     = "MDR_5_DAY"


# -- PMS signal record --------------------------------------------------------


@dataclass
class PmsSignal:
    """
    A single processed signal resulting from CUSUM analysis on a time series
    of MAUDE adverse events or recalls.
    """
    product_code:    str
    detected_at:     datetime
    severity:        str
    direction:       str
    cusum_value:     float
    event_date:      Optional[str]
    mdr_obligation:  MdrObligation
    description:     str  = ""
    cleared:         bool = False


# -- PMS device profile -------------------------------------------------------


@dataclass
class PmsDeviceProfile:
    """
    Tracks the post-market surveillance state for a single cleared device.
    """
    k_number:       str
    product_code:   str
    device_name:    str
    clearance_date: str
    signals:        List[PmsSignal] = field(default_factory=list)
    mdr_reports:    List[dict]      = field(default_factory=list)
    cusum_k:        float = 0.5
    cusum_h:        float = 5.0

    @property
    def active_signals(self) -> List[PmsSignal]:
        return [s for s in self.signals if not s.cleared]

    @property
    def highest_obligation(self) -> MdrObligation:
        obligations = [s.mdr_obligation for s in self.active_signals]
        priority = [MdrObligation.MDR_5_DAY, MdrObligation.MDR_30_DAY,
                    MdrObligation.MONITOR, MdrObligation.NONE]
        for p in priority:
            if p in obligations:
                return p
        return MdrObligation.NONE

    def clear_signal(self, signal: PmsSignal, reviewer_id: str) -> None:
        signal.cleared = True
        self.mdr_reports.append({
            "signal_product_code": signal.product_code,
            "signal_detected_at":  signal.detected_at.isoformat(),
            "mdr_obligation":      signal.mdr_obligation.value,
            "cleared_by":          reviewer_id,
            "cleared_at":          datetime.now(timezone.utc).isoformat(),
        })


# -- Severity -> MDR obligation mapping ---------------------------------------

_SEVERITY_MDR_MAP: Dict[str, MdrObligation] = {
    "LOW":      MdrObligation.NONE,
    "MEDIUM":   MdrObligation.MONITOR,
    "HIGH":     MdrObligation.MDR_30_DAY,
    "CRITICAL": MdrObligation.MDR_5_DAY,
}


def severity_to_mdr(severity: str) -> MdrObligation:
    """Map a CUSUM severity string to an MDR reporting obligation."""
    return _SEVERITY_MDR_MAP.get(severity.upper(), MdrObligation.NONE)


# -- PMS surveillance runner --------------------------------------------------


@dataclass
class PmsSurveillanceRunner:
    """
    Runs post-market surveillance CUSUM analysis for a device.

    Usage
    -----
    runner = PmsSurveillanceRunner(profile)
    new_signals = runner.run(monthly_counts, dates)
    profile.signals.extend(new_signals)
    """
    profile: PmsDeviceProfile

    def run(
        self,
        monthly_counts: List[float],
        dates:          Optional[List[str]] = None,
    ) -> List[PmsSignal]:
        """
        Analyse a time series and return new PmsSignal objects.

        Parameters
        ----------
        monthly_counts:
            Monthly MAUDE adverse event counts (or daily/weekly — any cadence).
        dates:
            Optional ISO date strings aligned with `monthly_counts`.

        Returns
        -------
        List of new PmsSignal objects (not yet appended to profile.signals).
        """
        from plugins.fda_tools.lib.signal_cusum import CUSUMDetector

        detector = CUSUMDetector(k=self.profile.cusum_k, h=self.profile.cusum_h)
        result   = detector.detect(monthly_counts, dates=dates)

        if result.insufficient_data:
            return []

        signals: List[PmsSignal] = []
        for alert in result.alerts:
            mdr = severity_to_mdr(alert.severity)
            signals.append(PmsSignal(
                product_code   = self.profile.product_code,
                detected_at    = datetime.now(timezone.utc),
                severity       = alert.severity,
                direction      = alert.direction,
                cusum_value    = max(alert.cusum_plus, alert.cusum_minus),
                event_date     = alert.date,
                mdr_obligation = mdr,
                description    = (
                    f"CUSUM {alert.direction} alert (severity={alert.severity}, "
                    f"CUSUM={max(alert.cusum_plus, alert.cusum_minus):.2f}) -- "
                    f"MDR obligation: {mdr.value}"
                ),
            ))
        return signals


# -- PMS plan tracker ---------------------------------------------------------


class PmsPlanStatus(str, Enum):
    NOT_STARTED   = "NOT_STARTED"
    ACTIVE        = "ACTIVE"
    SUSPENDED     = "SUSPENDED"
    COMPLETE      = "COMPLETE"


@dataclass
class PmsPlan:
    """
    Post-Market Surveillance plan per 21 CFR 820.100 / ISO 13485.
    Tracks required surveillance activities and their completion status.
    """
    project_id:     str
    product_code:   str
    status:         PmsPlanStatus = PmsPlanStatus.NOT_STARTED
    activities:     List[dict]    = field(default_factory=list)

    @classmethod
    def create_standard_plan(cls, project_id: str, product_code: str) -> "PmsPlan":
        """
        Create a standard PMS plan with activities for a Class II
        510(k)-cleared medical device.
        """
        plan = cls(
            project_id   = project_id,
            product_code = product_code,
            status       = PmsPlanStatus.ACTIVE,
        )
        plan.activities = [
            {
                "id":          "PMS-01",
                "title":       "MAUDE Adverse Event Monitoring",
                "frequency":   "Monthly",
                "regulation":  "21 CFR 803",
                "description": "Review MAUDE for complaints related to product code; "
                               "run CUSUM spike detection",
                "status":      "PENDING",
            },
            {
                "id":          "PMS-02",
                "title":       "Recall Watch",
                "frequency":   "Monthly",
                "regulation":  "21 CFR 806",
                "description": "Monitor FDA recall database for device and predicate recalls; "
                               "assess impact on SE predicate chain",
                "status":      "PENDING",
            },
            {
                "id":          "PMS-03",
                "title":       "MDR Submission (30-day)",
                "frequency":   "Event-triggered",
                "regulation":  "21 CFR 803.50",
                "description": "Submit MDR within 30 calendar days of a reportable event",
                "status":      "PENDING",
            },
            {
                "id":          "PMS-04",
                "title":       "MDR Submission (5-day)",
                "frequency":   "Event-triggered",
                "regulation":  "21 CFR 803.53",
                "description": "Submit MDR within 5 work days for immediately life-threatening events",
                "status":      "PENDING",
            },
            {
                "id":          "PMS-05",
                "title":       "Annual PMS Report",
                "frequency":   "Annual",
                "regulation":  "21 CFR 820.100; ISO 13485 8.2.1",
                "description": "Annual summary of PMS data, signal analysis, and CAPA actions",
                "status":      "PENDING",
            },
            {
                "id":          "PMS-06",
                "title":       "Real-World Evidence (RWE) Review",
                "frequency":   "Semi-annual",
                "regulation":  "FDA RWE Framework 2018",
                "description": "Review published RWE and clinical literature; assess need for "
                               "PMA supplement or De Novo reclassification",
                "status":      "PENDING",
            },
        ]
        return plan

    def mark_activity_complete(self, activity_id: str, completed_by: str) -> None:
        for activity in self.activities:
            if activity["id"] == activity_id:
                activity["status"]       = "COMPLETE"
                activity["completed_by"] = completed_by
                activity["completed_at"] = datetime.now(timezone.utc).isoformat()
                return
        raise KeyError(f"Activity {activity_id!r} not found in PMS plan")

    def pending_activities(self) -> List[dict]:
        return [a for a in self.activities if a["status"] == "PENDING"]

    def summary(self) -> dict:
        total     = len(self.activities)
        completed = sum(1 for a in self.activities if a["status"] == "COMPLETE")
        return {
            "project_id":   self.project_id,
            "product_code": self.product_code,
            "status":       self.status.value,
            "total":        total,
            "completed":    completed,
            "pending":      total - completed,
            "activities":   self.activities,
        }
