#!/usr/bin/env python3
"""
PMA Supplement Lifecycle Tracker -- Comprehensive supplement management and
impact analysis for PMA devices.

Expands on Phase 1's basic supplement categorization in pma_intelligence.py
to provide full lifecycle tracking, regulatory type classification per
21 CFR 814.39, change impact analysis, risk flagging, and supplement
dependency detection.

Supplement Types (21 CFR 814.39):
    (d) 180-Day Supplement -- labeling changes, indications
    (c) Real-Time Supplement -- design/manufacturing changes with clinical data
    (e) 30-Day Notice -- minor labeling/manufacturing changes
    (f) Panel-Track Supplement -- significant changes requiring panel review
    PAS-Related -- post-approval study submissions
    Other/Unclassified -- unmatched supplements

Usage:
    from supplement_tracker import SupplementTracker

    tracker = SupplementTracker()
    report = tracker.generate_supplement_report("P170019")
    lifecycle = tracker.track_lifecycle("P170019")
    impact = tracker.analyze_change_impact("P170019")

    # CLI usage:
    python3 supplement_tracker.py --pma P170019
    python3 supplement_tracker.py --pma P170019 --impact
    python3 supplement_tracker.py --pma P170019 --risk-flags
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Import sibling modules
from pma_data_store import PMADataStore


# ------------------------------------------------------------------
# Regulatory timeline configuration loading
# ------------------------------------------------------------------

def _load_regulatory_timelines() -> Dict:
    """Load regulatory timeline configuration from external JSON file.

    Loads timeline constants from data/regulatory_timelines.json with
    backward compatibility fallback to hardcoded defaults if config
    file is missing or invalid.

    Returns:
        Dict mapping supplement type keys to timeline configuration.
        Falls back to hardcoded defaults on load failure.
    """
    # Determine config file path (relative to script location)
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "data" / "regulatory_timelines.json"

    # Fallback defaults (backward compatibility)
    default_timelines = {
        "180_day_supplement": {
            "typical_review_days": 180,
            "cfr_citation": "21 CFR 814.39(d)",
        },
        "real_time_supplement": {
            "typical_review_days": 180,
            "cfr_citation": "21 CFR 814.39(c)",
        },
        "30_day_notice": {
            "typical_review_days": 30,
            "cfr_citation": "21 CFR 814.39(e)",
        },
        "panel_track_supplement": {
            "typical_review_days": 365,
            "cfr_citation": "21 CFR 814.39(f)",
        },
        "pas_related": {
            "typical_review_days": 90,
            "cfr_citation": "21 CFR 814.82",
        },
        "manufacturing_change": {
            "typical_review_days": 135,
            "cfr_citation": "21 CFR 814.39",
        },
        "other_unclassified": {
            "typical_review_days": 180,
            "cfr_citation": "21 CFR 814.39",
        },
    }

    # Attempt to load from configuration file
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Extract current timelines
            current_timelines = config.get("current_timelines", {})

            if current_timelines:
                # Validate that required fields exist
                loaded_timelines = {}
                for key, timeline in current_timelines.items():
                    if "typical_review_days" in timeline:
                        loaded_timelines[key] = timeline

                if loaded_timelines:
                    print(
                        f"INFO: Loaded regulatory timelines from {config_path} "
                        f"(version {config.get('metadata', {}).get('version', 'unknown')})",
                        file=sys.stderr
                    )
                    return loaded_timelines

        except (json.JSONDecodeError, OSError) as e:
            print(
                f"WARNING: Failed to load regulatory timelines from {config_path}: {e}. "
                f"Using hardcoded defaults.",
                file=sys.stderr
            )
    else:
        print(
            f"INFO: Regulatory timeline config not found at {config_path}. "
            f"Using hardcoded defaults.",
            file=sys.stderr
        )

    # Return defaults if loading failed
    return default_timelines


# Load regulatory timelines (global configuration)
_REGULATORY_TIMELINES = _load_regulatory_timelines()


# ------------------------------------------------------------------
# Supplement regulatory type definitions (21 CFR 814.39)
# ------------------------------------------------------------------

# Map internal supplement type keys to configuration keys
_TYPE_KEY_MAPPING = {
    "180_day": "180_day_supplement",
    "real_time": "real_time_supplement",
    "30_day_notice": "30_day_notice",
    "panel_track": "panel_track_supplement",
    "pas_related": "pas_related",
    "manufacturing": "manufacturing_change",
    "other": "other_unclassified",
}

# Supplement type definitions (keywords and risk levels)
# Timeline values loaded from configuration
SUPPLEMENT_REGULATORY_TYPES = {
    "180_day": {
        "label": "180-Day Supplement (21 CFR 814.39(d))",
        "cfr_section": "21 CFR 814.39(d)",
        "typical_review_days": 180,  # Will be overridden from config
        "risk_level": "medium",
        "keywords": [
            "labeling", "label change", "instructions for use", "IFU",
            "new indication", "additional indication", "expanded indication",
            "contraindication", "warning", "precaution",
            "indication expansion", "indication change",
        ],
        "description": (
            "Labeling changes including new/expanded indications, "
            "warnings, contraindications, and precautions."
        ),
    },
    "real_time": {
        "label": "Real-Time Supplement (21 CFR 814.39(c))",
        "cfr_section": "21 CFR 814.39(c)",
        "typical_review_days": 180,  # Will be overridden from config
        "risk_level": "high",
        "keywords": [
            "design change", "clinical study", "clinical data",
            "manufacturing change", "manufacturing process",
            "performance", "material change", "component change",
            "design modification",
        ],
        "description": (
            "Design changes supported by clinical data, or manufacturing "
            "changes that may affect device performance."
        ),
    },
    "30_day_notice": {
        "label": "30-Day Notice (21 CFR 814.39(e))",
        "cfr_section": "21 CFR 814.39(e)",
        "typical_review_days": 30,  # Will be overridden from config
        "risk_level": "low",
        "keywords": [
            "30-day", "30 day", "minor", "editorial",
            "minor labeling", "minor manufacturing",
        ],
        "description": (
            "Minor labeling changes or manufacturing changes without "
            "performance impact."
        ),
    },
    "panel_track": {
        "label": "Panel-Track Supplement (21 CFR 814.39(f))",
        "cfr_section": "21 CFR 814.39(f)",
        "typical_review_days": 365,  # Will be overridden from config
        "risk_level": "high",
        "keywords": [
            "panel track", "panel-track", "advisory committee",
            "significant change", "significant modification",
            "panel review",
        ],
        "description": (
            "Significant design or indication changes requiring "
            "advisory committee panel review."
        ),
    },
    "pas_related": {
        "label": "Post-Approval Study (PAS) Related",
        "cfr_section": "21 CFR 814.82",
        "typical_review_days": 90,  # Will be overridden from config
        "risk_level": "medium",
        "keywords": [
            "post-approval study", "post approval study", "PAS",
            "condition of approval", "522", "post-market surveillance",
            "post-market study", "annual report",
        ],
        "description": (
            "Supplements reporting post-approval study results, "
            "protocol amendments, or enrollment updates."
        ),
    },
    "manufacturing": {
        "label": "Manufacturing Change",
        "cfr_section": "21 CFR 814.39",
        "typical_review_days": 135,  # Will be overridden from config
        "risk_level": "medium",
        "keywords": [
            "manufacturing", "facility", "site change", "supplier",
            "process change", "sterilization", "sterilization method",
            "packaging", "shelf life",
        ],
        "description": (
            "Manufacturing facility, process, supplier, or "
            "sterilization changes."
        ),
    },
    "other": {
        "label": "Other/Unclassified",
        "cfr_section": "21 CFR 814.39",
        "typical_review_days": 180,  # Will be overridden from config
        "risk_level": "unknown",
        "keywords": [],
        "description": "Supplements not matching established patterns.",
    },
}

# Override typical_review_days from loaded configuration
for type_key, type_def in SUPPLEMENT_REGULATORY_TYPES.items():
    config_key = _TYPE_KEY_MAPPING.get(type_key, type_key)
    if config_key in _REGULATORY_TIMELINES:
        config_timeline = _REGULATORY_TIMELINES[config_key]
        type_def["typical_review_days"] = config_timeline.get(
            "typical_review_days",
            type_def["typical_review_days"]  # Fallback to hardcoded
        )
        # Update CFR section if changed in config
        type_def["cfr_section"] = config_timeline.get(
            "cfr_citation",
            type_def["cfr_section"]
        )

# Decision codes for supplement approval status
APPROVAL_STATUS_MAP = {
    "APPR": "approved",
    "APRL": "approved",   # Approved with conditions/limitations
    "APPN": "approved",   # Approved without conditions
    "DENY": "denied",
    "WDRN": "withdrawn",
    "WTDR": "withdrawn",
    "WTHI": "withdrawn",  # Withdrawn by holder
}

# Compiled keyword sets for fast matching
_KEYWORD_SETS: Dict[str, set] = {}
for _type_key, _type_def in SUPPLEMENT_REGULATORY_TYPES.items():
    _KEYWORD_SETS[_type_key] = set(
        kw.lower() for kw in _type_def["keywords"]
    )


# ------------------------------------------------------------------
# Supplement Tracker
# ------------------------------------------------------------------

class SupplementTracker:
    """Comprehensive PMA supplement lifecycle tracking and analysis.

    Expands Phase 1's basic categorization to full regulatory type
    classification, lifecycle state tracking, change impact analysis,
    dependency detection, and compliance risk flagging.
    """

    def __init__(self, store: Optional[PMADataStore] = None):
        """Initialize Supplement Tracker.

        Args:
            store: Optional PMADataStore instance.
        """
        self.store = store or PMADataStore()

    # ------------------------------------------------------------------
    # Main report generation
    # ------------------------------------------------------------------

    def generate_supplement_report(
        self,
        pma_number: str,
        refresh: bool = False,
    ) -> Dict:
        """Generate a comprehensive supplement tracking report.

        Args:
            pma_number: Base PMA number (e.g., 'P170019').
            refresh: Force refresh from API.

        Returns:
            Complete supplement report dictionary.
        """
        pma_key = pma_number.upper()

        # Load base PMA data
        api_data = self.store.get_pma_data(pma_key, refresh=refresh)
        if api_data.get("error"):
            return {
                "pma_number": pma_key,
                "error": api_data.get("error", "Data unavailable"),
            }

        # Load supplements
        supplements = self.store.get_supplements(pma_key, refresh=refresh)
        if not supplements:
            return {
                "pma_number": pma_key,
                "device_name": api_data.get("device_name", ""),
                "approval_date": api_data.get("decision_date", ""),
                "total_supplements": 0,
                "note": "No supplements found for this PMA.",
            }

        # Classify each supplement
        classified = self._classify_all_supplements(supplements)

        # Build lifecycle tracking
        lifecycle = self._build_lifecycle(classified, api_data)

        # Analyze change impact
        change_impact = self._analyze_change_impact(classified)

        # Calculate frequency analysis
        frequency = self._analyze_frequency(classified)

        # Detect risk flags
        risk_flags = self._detect_risk_flags(classified, frequency)

        # Detect dependencies
        dependencies = self._detect_dependencies(classified)

        # Build timeline
        timeline = self._build_timeline(classified, api_data)

        report = {
            "pma_number": pma_key,
            "device_name": api_data.get("device_name", ""),
            "applicant": api_data.get("applicant", ""),
            "approval_date": api_data.get("decision_date", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_supplements": len(classified),
            "regulatory_type_summary": self._summarize_types(classified),
            "approval_status_summary": self._summarize_statuses(classified),
            "supplements": classified,
            "lifecycle": lifecycle,
            "change_impact": change_impact,
            "frequency_analysis": frequency,
            "risk_flags": risk_flags,
            "dependencies": dependencies,
            "timeline": timeline,
        }

        # Cache the report
        self._save_report(pma_key, report)

        return report

    # ------------------------------------------------------------------
    # Supplement classification
    # ------------------------------------------------------------------

    def _classify_all_supplements(
        self,
        supplements: List[Dict],
    ) -> List[Dict]:
        """Classify all supplements by regulatory type and approval status.

        Args:
            supplements: Raw supplement dicts from PMADataStore.

        Returns:
            List of enriched supplement dicts with classification fields.
        """
        classified = []
        for supp in supplements:
            enriched = self._classify_supplement(supp)
            classified.append(enriched)

        # Sort by decision date ascending (chronological)
        classified.sort(key=lambda s: s.get("decision_date", ""))

        return classified

    def _classify_supplement(self, supp: Dict) -> Dict:
        """Classify a single supplement.

        Args:
            supp: Raw supplement dict.

        Returns:
            Enriched supplement dict with regulatory_type, approval_status,
            change_scope, and risk_level fields.
        """
        supp_type = supp.get("supplement_type", "").lower()
        supp_reason = supp.get("supplement_reason", "").lower()
        combined = f"{supp_type} {supp_reason}"
        decision_code = supp.get("decision_code", "").upper()

        # Determine regulatory type
        reg_type = self._determine_regulatory_type(combined)

        # Determine approval status
        approval_status = APPROVAL_STATUS_MAP.get(decision_code, "unknown")

        # Determine change scope
        change_scope = self._determine_change_scope(combined, reg_type)

        # Extract dates
        decision_date = supp.get("decision_date", "")
        submission_date = self._estimate_submission_date(
            decision_date, reg_type
        )

        # Get regulatory type definition
        reg_def = SUPPLEMENT_REGULATORY_TYPES.get(reg_type, {})

        return {
            "pma_number": supp.get("pma_number", ""),
            "supplement_number": supp.get("supplement_number", ""),
            "decision_date": decision_date,
            "estimated_submission_date": submission_date,
            "decision_code": decision_code,
            "approval_status": approval_status,
            "supplement_type_raw": supp.get("supplement_type", ""),
            "supplement_reason_raw": supp.get("supplement_reason", ""),
            "regulatory_type": reg_type,
            "regulatory_type_label": reg_def.get("label", "Unknown"),
            "cfr_section": reg_def.get("cfr_section", ""),
            "typical_review_days": reg_def.get("typical_review_days", 180),
            "risk_level": reg_def.get("risk_level", "unknown"),
            "change_scope": change_scope,
            "applicant": supp.get("applicant", ""),
            "trade_name": supp.get("trade_name", ""),
        }

    def _determine_regulatory_type(self, combined_text: str) -> str:
        """Determine the regulatory type for a supplement.

        Uses keyword matching against the combined supplement_type and
        supplement_reason fields. Checks types in priority order.

        Args:
            combined_text: Lowercased combined type + reason text.

        Returns:
            Regulatory type key.
        """
        # Check in priority order (most specific first)
        priority_order = [
            "panel_track", "pas_related", "30_day_notice",
            "real_time", "manufacturing", "180_day",
        ]

        for type_key in priority_order:
            keywords = _KEYWORD_SETS.get(type_key, set())
            for kw in keywords:
                if kw in combined_text:
                    return type_key

        return "other"

    def _determine_change_scope(
        self,
        combined_text: str,
        reg_type: str,
    ) -> str:
        """Determine the scope of change for a supplement.

        Args:
            combined_text: Lowercased combined type + reason text.
            reg_type: Determined regulatory type.

        Returns:
            Change scope string.
        """
        # Labeling-only
        labeling_kws = {"labeling", "label", "ifu", "instructions"}
        if any(kw in combined_text for kw in labeling_kws):
            if not any(kw in combined_text for kw in
                       {"design", "manufacturing", "clinical"}):
                return "labeling_only"

        # Design change
        if any(kw in combined_text for kw in
               {"design", "modification", "component", "material"}):
            return "design_change"

        # Clinical study
        if any(kw in combined_text for kw in
               {"clinical", "study", "trial", "pas", "post-approval"}):
            return "clinical_study"

        # Manufacturing
        if any(kw in combined_text for kw in
               {"manufacturing", "facility", "supplier", "sterilization",
                "process", "site"}):
            return "manufacturing_change"

        # Indication change
        if any(kw in combined_text for kw in
               {"indication", "new use", "patient population"}):
            return "indication_change"

        # Default based on regulatory type
        scope_defaults = {
            "180_day": "labeling_change",
            "real_time": "design_or_manufacturing",
            "30_day_notice": "minor_change",
            "panel_track": "significant_change",
            "pas_related": "study_update",
            "manufacturing": "manufacturing_change",
        }
        return scope_defaults.get(reg_type, "unclassified")

    def _estimate_submission_date(
        self,
        decision_date: str,
        reg_type: str,
    ) -> str:
        """Estimate submission date from decision date and typical review time.

        Args:
            decision_date: Decision date string (YYYYMMDD).
            reg_type: Regulatory type for typical review duration.

        Returns:
            Estimated submission date string (YYYY-MM-DD) or empty string.
        """
        if not decision_date or len(decision_date) < 8:
            return ""

        try:
            dd = datetime.strptime(decision_date[:8], "%Y%m%d")
            review_days = SUPPLEMENT_REGULATORY_TYPES.get(
                reg_type, {}
            ).get("typical_review_days", 180)
            estimated = dd - timedelta(days=review_days)
            return estimated.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return ""

    # ------------------------------------------------------------------
    # Lifecycle tracking
    # ------------------------------------------------------------------

    def _build_lifecycle(
        self,
        classified: List[Dict],
        api_data: Dict,
    ) -> Dict:
        """Build supplement lifecycle analysis.

        Args:
            classified: Classified supplement list.
            api_data: Base PMA API data.

        Returns:
            Lifecycle analysis dict.
        """
        if not classified:
            return {"phases": [], "current_phase": "initial_approval"}

        approval_date = api_data.get("decision_date", "")
        phases = []

        # Phase 1: Initial approval
        phases.append({
            "phase": "initial_approval",
            "date": approval_date,
            "description": "Original PMA approval",
        })

        # Group supplements by year
        by_year: Dict[int, List[Dict]] = defaultdict(list)
        for supp in classified:
            dd = supp.get("decision_date", "")
            if dd and len(dd) >= 4:
                try:
                    year = int(dd[:4])
                    by_year[year].append(supp)
                except ValueError as e:
                    print(f"Warning: Could not parse year from decision_date {dd!r}: {e}", file=sys.stderr)

        # Track phase transitions
        has_indication_expansion = False
        has_design_change = False
        has_pas_submission = False

        for supp in classified:
            scope = supp.get("change_scope", "")
            if scope == "indication_change" and not has_indication_expansion:
                has_indication_expansion = True
                phases.append({
                    "phase": "indication_expansion",
                    "date": supp.get("decision_date", ""),
                    "supplement": supp.get("supplement_number", ""),
                    "description": "First indication expansion",
                })
            if scope == "design_change" and not has_design_change:
                has_design_change = True
                phases.append({
                    "phase": "design_evolution",
                    "date": supp.get("decision_date", ""),
                    "supplement": supp.get("supplement_number", ""),
                    "description": "First design modification",
                })
            if supp.get("regulatory_type") == "pas_related" and not has_pas_submission:
                has_pas_submission = True
                phases.append({
                    "phase": "pas_reporting",
                    "date": supp.get("decision_date", ""),
                    "supplement": supp.get("supplement_number", ""),
                    "description": "Post-approval study submission",
                })

        # Determine current phase
        if classified:
            latest = classified[-1]
            current_phase = latest.get("change_scope", "active_maintenance")
        else:
            current_phase = "initial_approval"

        # Sort phases by date
        phases.sort(key=lambda p: p.get("date", ""))

        return {
            "phases": phases,
            "current_phase": current_phase,
            "total_phases": len(phases),
            "has_indication_expansion": has_indication_expansion,
            "has_design_change": has_design_change,
            "has_pas_submission": has_pas_submission,
        }

    # ------------------------------------------------------------------
    # Change impact analysis
    # ------------------------------------------------------------------

    def _analyze_change_impact(
        self,
        classified: List[Dict],
    ) -> Dict:
        """Analyze the cumulative impact of supplement changes.

        Args:
            classified: Classified supplement list.

        Returns:
            Change impact analysis dict.
        """
        if not classified:
            return {"total_changes": 0, "impact_level": "none"}

        # Count by scope
        scope_counts: Counter = Counter()
        risk_levels: Counter = Counter()
        reg_types: Counter = Counter()

        for supp in classified:
            scope_counts[supp.get("change_scope", "unknown")] += 1
            risk_levels[supp.get("risk_level", "unknown")] += 1
            reg_types[supp.get("regulatory_type", "other")] += 1

        # Calculate cumulative change burden
        # Higher burden = more/bigger changes = higher regulatory scrutiny
        burden_score = 0
        burden_weights = {
            "design_change": 10,
            "indication_change": 8,
            "clinical_study": 7,
            "significant_change": 12,
            "manufacturing_change": 5,
            "labeling_only": 2,
            "labeling_change": 2,
            "minor_change": 1,
            "study_update": 3,
        }

        for scope, count in scope_counts.items():
            weight = burden_weights.get(scope, 3)
            burden_score += weight * count

        # Determine impact level
        if burden_score >= 100:
            impact_level = "HIGH"
        elif burden_score >= 50:
            impact_level = "MODERATE"
        elif burden_score >= 20:
            impact_level = "LOW"
        else:
            impact_level = "MINIMAL"

        # Track indication changes specifically
        indication_supplements = [
            s for s in classified
            if s.get("change_scope") in ("indication_change", "labeling_change")
            and any(kw in s.get("supplement_reason_raw", "").lower()
                    for kw in ("indication", "use", "population"))
        ]

        return {
            "total_changes": len(classified),
            "scope_distribution": dict(scope_counts.most_common()),
            "risk_level_distribution": dict(risk_levels.most_common()),
            "regulatory_type_distribution": dict(reg_types.most_common()),
            "cumulative_burden_score": burden_score,
            "impact_level": impact_level,
            "indication_changes": len(indication_supplements),
            "design_changes": scope_counts.get("design_change", 0),
            "manufacturing_changes": scope_counts.get("manufacturing_change", 0),
            "high_risk_supplements": risk_levels.get("high", 0),
        }

    # ------------------------------------------------------------------
    # Frequency analysis
    # ------------------------------------------------------------------

    def _analyze_frequency(self, classified: List[Dict]) -> Dict:
        """Analyze supplement submission frequency over time.

        Args:
            classified: Classified supplement list.

        Returns:
            Frequency analysis dict.
        """
        if not classified:
            return {"avg_per_year": 0, "years_active": 0}

        # Extract years
        year_counts: Counter = Counter()
        year_type_counts: Dict[int, Counter] = defaultdict(Counter)
        dates: List[int] = []

        for supp in classified:
            dd = supp.get("decision_date", "")
            if dd and len(dd) >= 4:
                try:
                    year = int(dd[:4])
                    dates.append(year)
                    year_counts[year] += 1
                    year_type_counts[year][supp.get("regulatory_type", "other")] += 1
                except ValueError:
                    continue

        if not dates:
            return {"avg_per_year": 0, "years_active": 0}

        min_year = min(dates)
        max_year = max(dates)
        years_active = max(max_year - min_year, 1)

        # Calculate velocity trend (supplements per year over time)
        sorted_years = sorted(year_counts.keys())
        velocity_trend = []
        for year in sorted_years:
            velocity_trend.append({
                "year": year,
                "count": year_counts[year],
                "types": dict(year_type_counts[year]),
            })

        # Detect acceleration (recent years more active)
        recent_years = [y for y in sorted_years if y >= max_year - 2]
        older_years = [y for y in sorted_years if y < max_year - 2]

        recent_avg = (
            sum(year_counts[y] for y in recent_years) / max(len(recent_years), 1)
        )
        older_avg = (
            sum(year_counts[y] for y in older_years) / max(len(older_years), 1)
            if older_years else 0
        )

        trend = "accelerating" if recent_avg > older_avg * 1.5 else (
            "decelerating" if older_avg > recent_avg * 1.5 else "stable"
        )

        return {
            "first_supplement_year": min_year,
            "latest_supplement_year": max_year,
            "years_active": years_active,
            "avg_per_year": round(len(classified) / years_active, 1),
            "max_in_single_year": max(year_counts.values()) if year_counts else 0,
            "peak_year": max(year_counts, key=lambda y: year_counts.get(y, 0)) if year_counts else None,
            "year_distribution": dict(sorted(year_counts.items())),
            "velocity_trend": velocity_trend,
            "recent_avg_per_year": round(recent_avg, 1),
            "older_avg_per_year": round(older_avg, 1),
            "trend": trend,
        }

    # ------------------------------------------------------------------
    # Risk flag detection
    # ------------------------------------------------------------------

    def _detect_risk_flags(
        self,
        classified: List[Dict],
        frequency: Dict,
    ) -> List[Dict]:
        """Detect risk flags from supplement patterns.

        Args:
            classified: Classified supplement list.
            frequency: Frequency analysis results.

        Returns:
            List of risk flag dicts with severity and description.
        """
        flags = []

        # Flag 1: High supplement frequency
        avg_per_year = frequency.get("avg_per_year", 0)
        if avg_per_year > 5:
            flags.append({
                "flag": "high_supplement_frequency",
                "severity": "WARNING",
                "value": avg_per_year,
                "description": (
                    f"High supplement frequency ({avg_per_year}/year). "
                    f"May indicate ongoing device issues or rapid iteration."
                ),
            })

        # Flag 2: Multiple labeling changes (may indicate safety signals)
        labeling_count = sum(
            1 for s in classified
            if s.get("change_scope") in ("labeling_only", "labeling_change")
        )
        if labeling_count >= 5:
            flags.append({
                "flag": "frequent_labeling_changes",
                "severity": "WARNING",
                "value": labeling_count,
                "description": (
                    f"{labeling_count} labeling changes. May indicate evolving "
                    f"safety profile or expanding/restricting indications."
                ),
            })

        # Flag 3: Multiple design changes (cumulative impact concern)
        design_count = sum(
            1 for s in classified
            if s.get("change_scope") == "design_change"
        )
        if design_count >= 3:
            flags.append({
                "flag": "frequent_design_changes",
                "severity": "CAUTION",
                "value": design_count,
                "description": (
                    f"{design_count} design changes. Cumulative design modifications "
                    f"may warrant comprehensive equivalence review."
                ),
            })

        # Flag 4: Denied or withdrawn supplements
        denied = [
            s for s in classified
            if s.get("approval_status") in ("denied", "withdrawn")
        ]
        if denied:
            flags.append({
                "flag": "denied_withdrawn_supplements",
                "severity": "ALERT",
                "value": len(denied),
                "description": (
                    f"{len(denied)} supplement(s) denied or withdrawn. "
                    f"Review FDA reasoning for regulatory strategy implications."
                ),
                "affected_supplements": [
                    d.get("supplement_number", "") for d in denied
                ],
            })

        # Flag 5: Accelerating supplement trend
        trend = frequency.get("trend", "stable")
        if trend == "accelerating":
            flags.append({
                "flag": "accelerating_supplements",
                "severity": "INFO",
                "value": frequency.get("recent_avg_per_year", 0),
                "description": (
                    "Supplement frequency is accelerating in recent years. "
                    "May indicate active product development or evolving requirements."
                ),
            })

        # Flag 6: Panel-track supplements (significant changes)
        panel_track = [
            s for s in classified
            if s.get("regulatory_type") == "panel_track"
        ]
        if panel_track:
            flags.append({
                "flag": "panel_track_supplements",
                "severity": "INFO",
                "value": len(panel_track),
                "description": (
                    f"{len(panel_track)} panel-track supplement(s) filed. "
                    f"Indicates significant device changes requiring committee review."
                ),
            })

        # Flag 7: No PAS supplements when expected
        # (PMAs with >5 years and no PAS may have compliance concerns)
        years_active = frequency.get("years_active", 0)
        has_pas = any(
            s.get("regulatory_type") == "pas_related" for s in classified
        )
        if years_active >= 5 and not has_pas and len(classified) > 5:
            flags.append({
                "flag": "no_pas_detected",
                "severity": "INFO",
                "value": years_active,
                "description": (
                    f"PMA active for {years_active} years with no detected "
                    f"post-approval study supplements. Verify PAS compliance if required."
                ),
            })

        # Sort by severity (ALERT > WARNING > CAUTION > INFO)
        severity_order = {"ALERT": 0, "WARNING": 1, "CAUTION": 2, "INFO": 3}
        flags.sort(key=lambda f: severity_order.get(f["severity"], 4))

        return flags

    # ------------------------------------------------------------------
    # Dependency detection
    # ------------------------------------------------------------------

    def _detect_dependencies(self, classified: List[Dict]) -> List[Dict]:
        """Detect potential dependencies between supplements.

        Identifies supplements that likely depend on prior supplements
        based on chronological ordering and change scope relationships.

        Args:
            classified: Classified supplement list (already sorted by date).

        Returns:
            List of dependency relationship dicts.
        """
        dependencies = []

        # Track indication expansions that may require prior labeling supplements
        indication_supps = []
        labeling_supps = []
        design_supps = []

        for _i, supp in enumerate(classified):
            scope = supp.get("change_scope", "")
            _supp_num = supp.get("supplement_number", "")

            if scope in ("indication_change",):
                indication_supps.append(supp)
            elif scope in ("labeling_only", "labeling_change"):
                labeling_supps.append(supp)
            elif scope == "design_change":
                design_supps.append(supp)

        # Design changes followed by labeling changes are likely related
        for ds in design_supps:
            ds_date = ds.get("decision_date", "")
            ds_num = ds.get("supplement_number", "")
            for ls in labeling_supps:
                ls_date = ls.get("decision_date", "")
                ls_num = ls.get("supplement_number", "")
                if ds_date and ls_date and ls_date > ds_date:
                    # Labeling change within 1 year of design change
                    try:
                        ds_year = int(ds_date[:4])
                        ls_year = int(ls_date[:4])
                        if ls_year - ds_year <= 1:
                            dependencies.append({
                                "type": "design_triggers_labeling",
                                "prior_supplement": ds_num,
                                "dependent_supplement": ls_num,
                                "confidence": "POSSIBLE",
                                "description": (
                                    f"Labeling change {ls_num} may be triggered by "
                                    f"design change {ds_num}."
                                ),
                            })
                            break  # Only link closest match
                    except ValueError as e:
                        print(f"Warning: Could not parse supplement dates for dependency detection: {e}", file=sys.stderr)

        return dependencies[:20]  # Limit to 20 relationships

    # ------------------------------------------------------------------
    # Timeline generation
    # ------------------------------------------------------------------

    def _build_timeline(
        self,
        classified: List[Dict],
        api_data: Dict,
    ) -> List[Dict]:
        """Build a chronological timeline of supplement events.

        Args:
            classified: Classified supplement list.
            api_data: Base PMA data.

        Returns:
            Sorted timeline of events.
        """
        events = []

        # Add initial approval
        approval_date = api_data.get("decision_date", "")
        if approval_date:
            events.append({
                "date": approval_date,
                "event_type": "initial_approval",
                "description": f"Original PMA approval: {api_data.get('device_name', '')}",
                "supplement_number": "",
                "regulatory_type": "",
                "status": "approved",
            })

        # Add supplement events
        for supp in classified:
            events.append({
                "date": supp.get("decision_date", ""),
                "event_type": "supplement_decision",
                "description": (
                    f"{supp.get('regulatory_type_label', 'Supplement')}: "
                    f"{supp.get('supplement_reason_raw', 'N/A')[:80]}"
                ),
                "supplement_number": supp.get("supplement_number", ""),
                "regulatory_type": supp.get("regulatory_type", ""),
                "status": supp.get("approval_status", "unknown"),
                "change_scope": supp.get("change_scope", ""),
                "risk_level": supp.get("risk_level", ""),
            })

        # Sort chronologically
        events.sort(key=lambda e: e.get("date", ""))

        return events

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def _summarize_types(self, classified: List[Dict]) -> Dict:
        """Summarize supplement counts by regulatory type.

        Args:
            classified: Classified supplement list.

        Returns:
            Dict of type -> {label, count, percentage}.
        """
        type_counts: Counter = Counter()
        for supp in classified:
            type_counts[supp.get("regulatory_type", "other")] += 1

        total = len(classified)
        summary = {}
        for type_key, count in type_counts.most_common():
            type_def = SUPPLEMENT_REGULATORY_TYPES.get(type_key, {})
            summary[type_key] = {
                "label": type_def.get("label", type_key),
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0,
            }

        return summary

    def _summarize_statuses(self, classified: List[Dict]) -> Dict:
        """Summarize supplement counts by approval status.

        Args:
            classified: Classified supplement list.

        Returns:
            Dict of status -> count.
        """
        status_counts: Counter = Counter()
        for supp in classified:
            status_counts[supp.get("approval_status", "unknown")] += 1

        return dict(status_counts.most_common())

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _save_report(self, pma_number: str, report: Dict) -> None:
        """Save supplement report to cache.

        Args:
            pma_number: PMA number.
            report: Report dict.
        """
        pma_dir = self.store.get_pma_dir(pma_number)
        report_path = pma_dir / "supplement_report.json"
        tmp_path = report_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(report, f, indent=2)
            tmp_path.replace(report_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def get_cached_report(self, pma_number: str) -> Optional[Dict]:
        """Get a cached supplement report if available.

        Args:
            pma_number: PMA number.

        Returns:
            Cached report dict or None.
        """
        pma_dir = self.store.get_pma_dir(pma_number.upper())
        report_path = pma_dir / "supplement_report.json"
        if report_path.exists():
            try:
                with open(report_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to read cached supplement report for {pma_number}: {e}", file=sys.stderr)
        return None


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_supplement_report(report: Dict) -> str:
    """Format supplement report as readable text.

    Args:
        report: Supplement report dict.

    Returns:
        Formatted text output.
    """
    lines = []
    lines.append("=" * 70)
    lines.append("PMA SUPPLEMENT TRACKING REPORT")
    lines.append("=" * 70)
    lines.append(f"PMA Number:  {report.get('pma_number', 'N/A')}")
    lines.append(f"Device:      {report.get('device_name', 'N/A')}")
    lines.append(f"Applicant:   {report.get('applicant', 'N/A')}")
    lines.append(f"Approved:    {report.get('approval_date', 'N/A')}")
    lines.append(f"Total Supps: {report.get('total_supplements', 0)}")
    lines.append("")

    # Type summary
    types = report.get("regulatory_type_summary", {})
    if types:
        lines.append("--- Supplement Types ---")
        for type_key, info in types.items():
            lines.append(
                f"  {info.get('label', type_key)}: "
                f"{info.get('count', 0)} ({info.get('percentage', 0)}%)"
            )
        lines.append("")

    # Status summary
    statuses = report.get("approval_status_summary", {})
    if statuses:
        lines.append("--- Approval Status ---")
        for status, count in statuses.items():
            lines.append(f"  {status}: {count}")
        lines.append("")

    # Change impact
    impact = report.get("change_impact", {})
    if impact.get("total_changes", 0) > 0:
        lines.append("--- Change Impact ---")
        lines.append(f"  Impact Level: {impact.get('impact_level', 'N/A')}")
        lines.append(f"  Burden Score: {impact.get('cumulative_burden_score', 0)}")
        lines.append(f"  Indication Changes: {impact.get('indication_changes', 0)}")
        lines.append(f"  Design Changes: {impact.get('design_changes', 0)}")
        lines.append(f"  Manufacturing Changes: {impact.get('manufacturing_changes', 0)}")
        lines.append("")

    # Frequency
    freq = report.get("frequency_analysis", {})
    if freq.get("avg_per_year", 0) > 0:
        lines.append("--- Frequency Analysis ---")
        lines.append(f"  Average/year: {freq.get('avg_per_year', 0)}")
        lines.append(
            f"  Active years: "
            f"{freq.get('first_supplement_year', 'N/A')}-"
            f"{freq.get('latest_supplement_year', 'N/A')}"
        )
        lines.append(f"  Peak year: {freq.get('peak_year', 'N/A')} ({freq.get('max_in_single_year', 0)} supplements)")
        lines.append(f"  Trend: {freq.get('trend', 'N/A')}")
        lines.append("")

    # Risk flags
    flags = report.get("risk_flags", [])
    if flags:
        lines.append("--- Risk Flags ---")
        for flag in flags:
            lines.append(
                f"  [{flag.get('severity', 'INFO')}] "
                f"{flag.get('description', 'N/A')}"
            )
        lines.append("")

    # Timeline (last 10 events)
    timeline = report.get("timeline", [])
    if timeline:
        lines.append("--- Timeline (recent events) ---")
        for event in timeline[-10:]:
            lines.append(
                f"  {event.get('date', 'N/A')} | "
                f"{event.get('status', 'N/A'):10s} | "
                f"{event.get('description', 'N/A')[:60]}"
            )
        lines.append("")

    lines.append("=" * 70)
    lines.append(f"Generated: {report.get('generated_at', 'N/A')[:10]}")
    lines.append("This report is AI-generated from public FDA data.")
    lines.append("Independent verification by qualified RA professionals required.")
    lines.append("=" * 70)

    return "\n".join(lines)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PMA Supplement Tracker -- Comprehensive supplement lifecycle management"
    )
    parser.add_argument("--pma", help="PMA number to analyze")
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--impact", action="store_true", help="Show change impact analysis")
    parser.add_argument("--risk-flags", action="store_true", dest="risk_flags",
                        help="Show risk flags only")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.pma:
        parser.error("Specify --pma PMA_NUMBER")

    tracker = SupplementTracker()
    report = tracker.generate_supplement_report(args.pma, refresh=args.refresh)

    if args.risk_flags:
        # Show only risk flags
        flags = report.get("risk_flags", [])
        if args.json:
            print(json.dumps(flags, indent=2))
        else:
            for flag in flags:
                print(f"[{flag['severity']}] {flag['description']}")
    elif args.impact:
        # Show only change impact
        impact = report.get("change_impact", {})
        if args.json:
            print(json.dumps(impact, indent=2))
        else:
            print(json.dumps(impact, indent=2))
    elif args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_format_supplement_report(report))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
