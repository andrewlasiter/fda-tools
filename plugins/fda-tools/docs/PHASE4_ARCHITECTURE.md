# Phase 4 Automation Architecture Design

**Author:** Architecture Reviewer
**Date:** 2026-02-13
**Status:** DESIGN PROPOSAL
**Scope:** Automated Gap Analysis, Smart Predicate Recommendations, Executive Summary Generation

---

## 1. Architectural Context and Assessment of Current State

### 1.1 Current Module Landscape

```
plugins/fda-predicate-assistant/
    lib/
        fda_enrichment.py       (816 lines, FDAEnrichment class, Phases 1-3)
        disclaimers.py          (363 lines, output disclaimer generation)
    scripts/
        batchfetch.py           (1156 lines, CLI download tool)
        gap_analysis.py         (341 lines, PMN-vs-CSV gap detection)
        ...11 other scripts
    commands/
        batchfetch.md           (2349 lines, interactive enrichment command)
        compare-se.md           (SE table generation -- subject vs predicate)
        review.md               (predicate scoring, accept/reject)
        gap-analysis.md         (PMN gap analysis command)
        propose.md              (manual predicate proposal)
        ...40 other commands
```

### 1.2 Current Data Flow

```
                              batchfetch.md (command)
                                    |
                    [CLI args, AskUserQuestion]
                                    |
                                    v
                  batchfetch.py (script) --> 510k_download.csv
                                    |                  |
                               [--enrich]              |
                                    |                  v
                                    v            gap_analysis.py
                            fda_enrichment.py          |
                           (FDAEnrichment class)       v
                                    |           gap_manifest.csv
                                    v
                    +----------------------------------+
                    |   6 Output Files Per Project     |
                    |   - 510k_download.csv (enriched) |
                    |   - enrichment_report.html       |
                    |   - quality_report.md            |
                    |   - regulatory_context.md        |
                    |   - intelligence_report.md       |
                    |   - competitive_intelligence.md  |
                    |   - enrichment_metadata.json     |
                    +----------------------------------+
```

### 1.3 Current Architectural Concerns

**Concern 1: Monolithic batchfetch.md**
The `batchfetch.md` command file is 2349 lines and contains inline Python that duplicates logic from `fda_enrichment.py`. Report generation functions (`generate_enrichment_process_report`, `generate_regulatory_context`, `generate_intelligence_report`, `generate_competitive_intelligence`) are defined inline in the markdown command file rather than in the lib module. This creates a maintenance burden where changes must be synchronized in two places.

**Concern 2: `fda_enrichment.py` Scope Creep**
The enrichment module already spans three phases (data integrity, intelligence, analytics) at 816 lines. Adding three more automation features to this module would push it past 1500 lines, creating a single class with too many responsibilities.

**Concern 3: Gap Analysis Isolation**
The existing `gap_analysis.py` script performs PMN-database-level gap detection (missing K-numbers, missing PDFs) but has no connection to the enrichment pipeline. Phase 4's "automated gap analysis" is a different concept entirely -- it compares subject device characteristics against predicate device characteristics to identify specification gaps. These are two fundamentally different operations sharing the same name, which creates confusion.

**Concern 4: No Shared Data Contract**
The enrichment pipeline produces CSV rows with 53+ columns, but there is no formal schema definition. Downstream consumers (compare-se.md, review.md, propose.md) each parse `review.json` and `device_profile.json` independently. Phase 4 features need to consume enrichment output AND project data, requiring a clear contract between producers and consumers.

---

## 2. Recommended Module Structure

### 2.1 Decision: New Module, Not Extension

**Recommendation:** Create a new `fda_automation.py` module in `lib/` rather than extending `fda_enrichment.py`.

**Rationale:**

| Option | Pros | Cons |
|--------|------|------|
| Extend `fda_enrichment.py` | Single import, shared API client | Violates SRP, 1500+ lines, couples enrichment to automation |
| New `fda_automation.py` | Clean separation, testable independently, clear ownership | New import required, must share API client |
| Functions in `batchfetch.md` | Zero Python file changes | Untestable, unmaintainable, duplicates further |

`fda_enrichment.py` is a data acquisition and scoring module. Phase 4 is a data analysis and recommendation module. These are different responsibilities that warrant different modules.

### 2.2 Module Organization

```
lib/
    fda_enrichment.py       (UNCHANGED - 816 lines, Phases 1-3)
    fda_automation.py       (NEW - ~600 lines, Phase 4)
    disclaimers.py          (EXTENDED - add automation disclaimers)
    _shared.py              (NEW - ~80 lines, shared utilities)
```

### 2.3 `_shared.py` -- Shared Utilities

This module extracts the API client and common data types currently embedded in `FDAEnrichment` so both modules can use them without inheritance coupling.

```python
"""
Shared utilities for FDA enrichment and automation modules.
Extracts common dependencies to prevent circular imports.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError
import json
import time


class FDAAPIClient:
    """
    Shared openFDA API client with rate limiting and error handling.

    Used by both FDAEnrichment (Phases 1-3) and FDAAutomation (Phase 4).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.fda.gov/device"
        self.call_count = 0
        self.error_count = 0

    def query(self, endpoint: str, params: Dict[str, Any],
              timeout: int = 10) -> Optional[Dict]:
        """
        Query openFDA API with rate limiting.

        Args:
            endpoint: API endpoint (e.g., 'event', 'recall', '510k')
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response or None on error
        """
        if self.api_key:
            params['api_key'] = self.api_key

        query_string = '&'.join(
            [f"{k}={quote(str(v))}" for k, v in params.items()]
        )
        url = f"{self.base_url}/{endpoint}.json?{query_string}"

        try:
            req = Request(
                url,
                headers={'User-Agent': 'FDA-Predicate-Assistant/4.0'}
            )
            response = urlopen(req, timeout=timeout)
            data = json.loads(response.read().decode('utf-8'))
            self.call_count += 1
            time.sleep(0.25)  # Rate limit: 4 req/sec
            return data
        except HTTPError as e:
            self.error_count += 1
            return None
        except (URLError, Exception):
            self.error_count += 1
            return None


# Standard data types for inter-module contracts
class DeviceProfile:
    """
    Canonical device representation shared across modules.
    Provides a typed contract instead of raw dicts.
    """

    def __init__(self, k_number: str, product_code: str, **kwargs):
        self.k_number = k_number
        self.product_code = product_code
        self.device_name = kwargs.get('device_name', '')
        self.applicant = kwargs.get('applicant', '')
        self.decision_date = kwargs.get('decision_date', '')
        self.intended_use = kwargs.get('intended_use', '')
        self.device_description = kwargs.get('device_description', '')
        self.classification = kwargs.get('classification', '')
        self.regulation_number = kwargs.get('regulation_number', '')
        self.enrichment_data = kwargs.get('enrichment_data', {})

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> 'DeviceProfile':
        """Construct from enriched CSV row."""
        return cls(
            k_number=row.get('KNUMBER', ''),
            product_code=row.get('PRODUCTCODE', ''),
            device_name=row.get('DEVICENAME', ''),
            applicant=row.get('APPLICANT', ''),
            decision_date=row.get('DECISIONDATE', ''),
            enrichment_data=row
        )

    @classmethod
    def from_review_json(cls, predicate: Dict) -> 'DeviceProfile':
        """Construct from review.json predicate entry."""
        return cls(
            k_number=predicate.get('k_number', ''),
            product_code=predicate.get('product_code', ''),
            device_name=predicate.get('device_name', ''),
            applicant=predicate.get('applicant', ''),
            decision_date=predicate.get('clearance_date', ''),
            intended_use=predicate.get('intended_use', ''),
            enrichment_data=predicate
        )
```

**Migration note:** `FDAEnrichment.api_query()` would be refactored to delegate to `FDAAPIClient.query()` in a future version. For Phase 4 initial delivery, `fda_automation.py` uses `FDAAPIClient` directly while `fda_enrichment.py` keeps its internal implementation unchanged. This avoids a risky refactor of a production module.

### 2.4 `fda_automation.py` -- Phase 4 Core Module

```python
"""
FDA Automation Module - Phase 4
================================

Automated analysis features for FDA 510(k) predicate assessment:
- Feature 1: Automated Gap Analysis (subject vs predicate spec comparison)
- Feature 2: Smart Predicate Recommendations (ML-free scoring and ranking)
- Feature 3: Executive Summary Generation (natural language insights)

Version: 4.0.0
Date: 2026-02-XX

IMPORTANT: This module provides analytical insights for research purposes.
All output MUST be independently verified by qualified RA professionals.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from ._shared import FDAAPIClient, DeviceProfile

import json
import re


class GapAnalyzer:
    """
    Feature 1: Automated specification gap analysis.

    Compares subject device profile against one or more predicate
    devices to identify specification gaps, differences, and
    areas requiring additional justification.

    NOT to be confused with scripts/gap_analysis.py which identifies
    missing K-numbers in download manifests.
    """
    ...


class PredicateRecommender:
    """
    Feature 2: Smart predicate recommendations.

    Ranks candidate predicates from enriched CSV data based on
    multi-dimensional scoring:
    - Intended use similarity
    - Technology alignment
    - Clearance recency
    - Safety profile (recalls, MAUDE)
    - Predicate acceptability (from Phase 2)
    """
    ...


class ExecutiveSummaryGenerator:
    """
    Feature 3: Executive summary generation.

    Produces natural language reports synthesizing enrichment
    data, gap analysis, and recommendations into actionable
    strategic guidance.
    """
    ...


class FDAAutomation:
    """
    Facade class coordinating all Phase 4 automation features.

    Provides a unified entry point that orchestrates gap analysis,
    recommendations, and summary generation in the correct sequence.
    """
    ...
```

---

## 3. Detailed Data Flow Design

### 3.1 Feature Dependency Graph

The three Phase 4 features have a clear sequential dependency:

```
                     +-------------------+
                     |  Enriched CSV     |  (from Phase 1-3)
                     |  review.json      |  (from /fda:review)
                     |  device_profile   |  (from /fda:import)
                     +--------+----------+
                              |
                              v
                 +------------------------+
                 |  1. Gap Analyzer       |
                 |  (compare specs)       |
                 +--------+---------------+
                          |
              gap_analysis_result (dict)
                          |
               +----------+----------+
               |                     |
               v                     v
  +---------------------+  +------------------------+
  | 2. Predicate        |  | 3. Executive Summary   |
  |    Recommender      |  |    Generator           |
  |    (rank candidates)|  |    (synthesize all)    |
  +--------+------------+  +--------+---------------+
           |                         |
  recommendation_result      summary_result
           |                         |
           +------------+------------+
                        |
                        v
              +-------------------+
              |  Output Files     |
              |  - gap_report.md  |
              |  - recommend.md   |
              |  - exec_summary   |
              +-------------------+
```

### 3.2 Feature 2 Can Run Independently

While the full pipeline is sequential, Feature 2 (Predicate Recommender) can also operate independently of Feature 1 -- it only needs the enriched CSV. This is important because users may want recommendations before they have a fully defined subject device.

```
Independent mode:          Sequential mode:

  enriched CSV               enriched CSV + device_profile
       |                              |
       v                              v
  Recommender              Gap Analyzer --> Recommender --> Summary
       |                                                      |
       v                                                      v
  recommend.md             gap_report.md + recommend.md + exec_summary.md
```

### 3.3 Input Data Contracts

**Gap Analyzer Inputs:**

| Input | Source | Required | Content |
|-------|--------|----------|---------|
| Subject device profile | `device_profile.json` or user input | YES | Device specs, intended use, technology characteristics |
| Predicate devices | `review.json` (accepted predicates) | YES | 1-3 predicate K-numbers with clearance data |
| Enriched predicate data | Enriched CSV rows | PREFERRED | MAUDE, recalls, acceptability from Phases 1-3 |
| SE comparison table | `se_comparison.md` | OPTIONAL | Pre-existing spec comparison (if available) |

**Predicate Recommender Inputs:**

| Input | Source | Required | Content |
|-------|--------|----------|---------|
| Candidate pool | Enriched CSV (all rows) | YES | Full set of cleared devices in product code |
| Subject intended use | `device_profile.json` | PREFERRED | For similarity scoring |
| Gap analysis results | `GapAnalyzer` output | OPTIONAL | Weights recommendations toward gap-filling |
| Exclusion list | User or `review.json` rejected | OPTIONAL | K-numbers to exclude |

**Executive Summary Inputs:**

| Input | Source | Required | Content |
|-------|--------|----------|---------|
| Gap analysis results | `GapAnalyzer` output | PREFERRED | Specification gaps and risk areas |
| Recommendations | `PredicateRecommender` output | PREFERRED | Ranked predicate candidates |
| Enrichment metadata | `enrichment_metadata.json` | YES | Data quality and completeness |
| Intelligence report | `intelligence_report.md` | OPTIONAL | Phase 2 strategic insights |

### 3.4 Output Data Contracts

**Gap Analyzer Output:**

```python
GapAnalysisResult = {
    "subject_device": {
        "k_number": str,       # "N/A" if subject not yet cleared
        "product_code": str,
        "device_name": str
    },
    "predicates_analyzed": [
        {
            "k_number": str,
            "device_name": str,
            "acceptability": str   # from Phase 2
        }
    ],
    "gaps": [
        {
            "dimension": str,       # e.g., "intended_use", "technology", "materials"
            "severity": str,        # "CRITICAL", "MAJOR", "MINOR", "INFORMATIONAL"
            "subject_value": str,   # what the subject device has
            "predicate_value": str, # what the predicate has
            "gap_description": str, # human-readable gap explanation
            "mitigation": str,      # suggested approach to address gap
            "fda_reference": str    # relevant guidance or CFR
        }
    ],
    "risk_summary": {
        "critical_gaps": int,
        "major_gaps": int,
        "minor_gaps": int,
        "overall_risk": str,       # "LOW", "MODERATE", "HIGH"
        "recommendation": str      # strategic recommendation
    },
    "timestamp": str,
    "disclaimer": str
}
```

**Predicate Recommender Output:**

```python
RecommendationResult = {
    "search_criteria": {
        "product_code": str,
        "intended_use_keywords": [str],
        "year_range": str,
        "candidate_pool_size": int
    },
    "recommendations": [
        {
            "rank": int,
            "k_number": str,
            "device_name": str,
            "applicant": str,
            "clearance_date": str,
            "composite_score": float,     # 0-100
            "score_breakdown": {
                "intended_use_match": float,   # 0-25
                "technology_match": float,     # 0-25
                "recency_score": float,        # 0-20
                "safety_score": float,         # 0-20
                "acceptability_score": float   # 0-10
            },
            "rationale": str,
            "risk_flags": [str],
            "gap_coverage": [str]          # which gaps this predicate covers
        }
    ],
    "excluded_devices": [
        {
            "k_number": str,
            "reason": str   # "recalled", "too_old", "user_rejected", etc.
        }
    ],
    "timestamp": str,
    "disclaimer": str
}
```

---

## 4. Integration Strategy

### 4.1 Integration Point Decision

**Recommendation:** Post-enrichment, invoked via a new command.

**Three options evaluated:**

| Integration Point | Description | Verdict |
|-------------------|-------------|---------|
| During enrichment (`--automate` flag on batchfetch) | Run Phase 4 as part of enrichment | REJECTED -- couples batch download to analysis |
| Post-enrichment batch step | New `--analyze` flag on batchfetch | REJECTED -- batchfetch.md is already 2349 lines |
| Separate command (`/fda:automate`) | New command that reads enrichment output | RECOMMENDED |

**Rationale:** Phase 4 features require project-level context (device_profile.json, review.json) that does not exist during initial batch fetch. The enrichment pipeline processes raw CSV rows. Automation requires a user who has already identified their subject device and selected predicates. These are fundamentally different workflow stages.

### 4.2 Command Structure

New command: `commands/automate.md`

```
/fda-predicate-assistant:automate --project NAME [--mode full|gaps|recommend|summary]
    [--subject-description TEXT] [--full-auto]
```

**Modes:**

| Mode | Features Run | When to Use |
|------|-------------|-------------|
| `full` (default) | Gap Analysis + Recommendations + Summary | Complete automated analysis |
| `gaps` | Gap Analysis only | When predicates are already selected |
| `recommend` | Recommendations only | When looking for predicates |
| `summary` | Executive Summary only | After manual gap + recommendation work |

### 4.3 Workflow Integration

Phase 4 fits into the existing pipeline at position 5:

```
EXISTING PIPELINE:
  1. /fda:batchfetch --enrich      -->  enriched CSV + reports
  2. /fda:review                   -->  review.json (accepted predicates)
  3. /fda:compare-se               -->  se_comparison.md
  4. /fda:draft                    -->  submission draft sections

EXTENDED PIPELINE (Phase 4 inserted):
  1. /fda:batchfetch --enrich      -->  enriched CSV + reports
  2. /fda:review                   -->  review.json (accepted predicates)
  3. /fda:automate --project NAME  -->  gap_report.md + recommend.md + exec_summary.md
  4. /fda:compare-se               -->  se_comparison.md (informed by gap report)
  5. /fda:draft                    -->  submission draft sections (informed by automation)
```

**Key integration:** The `/fda:automate` output feeds downstream commands:
- `gap_report.md` informs `/fda:compare-se` which rows need emphasis
- `recommend.md` informs `/fda:review --re-review` if better predicates found
- `exec_summary.md` informs `/fda:draft` for cover letter and SE discussion

### 4.4 Data File Integration

```
~/fda-510k-data/projects/{PROJECT_NAME}/
    query.json                    # (existing) batchfetch parameters
    510k_download.csv             # (existing) enriched device data
    review.json                   # (existing) accepted/rejected predicates
    device_profile.json           # (existing) subject device specs
    se_comparison.md              # (existing) SE comparison table
    enrichment_metadata.json      # (existing) Phase 1 provenance
    quality_report.md             # (existing) Phase 1 quality
    regulatory_context.md         # (existing) Phase 1 CFR
    intelligence_report.md        # (existing) Phase 2 intelligence
    competitive_intelligence_*.md # (existing) Phase 3 market
    automation/                   # (NEW) Phase 4 output directory
        gap_analysis.json         # (NEW) machine-readable gap results
        gap_report.md             # (NEW) human-readable gap report
        recommendations.json      # (NEW) machine-readable recommendations
        recommend.md              # (NEW) human-readable recommendation report
        executive_summary.md      # (NEW) synthesized strategic summary
        automation_metadata.json  # (NEW) run provenance and disclaimers
```

The `automation/` subdirectory isolates Phase 4 output from existing files, preventing namespace collisions and making it clear which files are automation-generated.

---

## 5. Detailed Component Design

### 5.1 GapAnalyzer

```python
class GapAnalyzer:
    """
    Compares subject device specifications against predicate device
    specifications to identify gaps requiring justification in a
    510(k) submission.

    Gap Dimensions (ordered by regulatory significance):
    1. Intended Use / Indications for Use
    2. Technological Characteristics
    3. Materials / Biocompatibility
    4. Performance Specifications
    5. Sterilization Method
    6. Shelf Life
    7. Software / Firmware
    8. Electrical Safety
    9. Human Factors / Usability
    10. Labeling / IFU
    """

    # Severity classification criteria
    SEVERITY_RULES = {
        'CRITICAL': [
            'intended_use_expansion',    # broader IFU than predicate
            'new_material_body_contact',  # new material touching patient
            'technology_change',          # fundamentally different mechanism
        ],
        'MAJOR': [
            'sterilization_method_change',
            'software_level_of_concern_higher',
            'new_energy_source',
            'shelf_life_longer_unvalidated',
        ],
        'MINOR': [
            'dimensional_change',
            'packaging_change',
            'labeling_format_change',
            'supplier_change_same_material',
        ]
    }

    def __init__(self, api_client: Optional[FDAAPIClient] = None):
        self.api_client = api_client

    def analyze(
        self,
        subject: DeviceProfile,
        predicates: List[DeviceProfile],
        se_comparison: Optional[Dict] = None,
        enrichment_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Run full gap analysis.

        Args:
            subject: Subject device profile
            predicates: List of predicate device profiles
            se_comparison: Pre-existing SE comparison data (optional)
            enrichment_data: Phase 1-3 enrichment data (optional)

        Returns:
            GapAnalysisResult dict
        """
        gaps = []

        for predicate in predicates:
            gaps.extend(self._compare_intended_use(subject, predicate))
            gaps.extend(self._compare_technology(subject, predicate))
            gaps.extend(self._compare_materials(subject, predicate))
            gaps.extend(self._compare_performance(subject, predicate))
            gaps.extend(self._compare_sterilization(subject, predicate))
            gaps.extend(self._compare_software(subject, predicate))

        # Deduplicate gaps across predicates
        gaps = self._deduplicate_gaps(gaps)

        # Score overall risk
        risk_summary = self._calculate_risk_summary(gaps)

        return {
            'subject_device': { ... },
            'predicates_analyzed': [ ... ],
            'gaps': gaps,
            'risk_summary': risk_summary,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'disclaimer': AUTOMATION_GAP_DISCLAIMER
        }

    def _compare_intended_use(
        self,
        subject: DeviceProfile,
        predicate: DeviceProfile
    ) -> List[Dict]:
        """
        Compare intended use statements using keyword extraction
        and semantic field matching.

        Checks for:
        - IFU expansion (subject broader than predicate)
        - New patient population
        - New anatomical site
        - New clinical indication
        - Duration of use change
        """
        ...

    def _compare_technology(
        self,
        subject: DeviceProfile,
        predicate: DeviceProfile
    ) -> List[Dict]:
        """
        Compare technological characteristics.

        Checks for:
        - Different operating principle
        - New energy source
        - New active ingredient
        - Different delivery mechanism
        - Software-based processing differences
        """
        ...
```

### 5.2 PredicateRecommender

```python
class PredicateRecommender:
    """
    Ranks candidate predicates using a composite scoring model.

    Scoring Model (100 points total):
    - Intended Use Match:    25 pts (keyword overlap + IFU field similarity)
    - Technology Match:      25 pts (product code, device name similarity)
    - Recency:               20 pts (linear decay, 0 pts at 15+ years)
    - Safety Profile:        20 pts (recall count, MAUDE classification)
    - Acceptability:         10 pts (Phase 2 assessment bonus)

    Design Decision: Rule-based scoring, not ML.
    Rationale:
    - Regulatory domain requires explainability
    - Training data insufficient for ML (each product code has ~50-500 devices)
    - Score components must map to FDA guidance criteria
    - RA professionals need to audit every recommendation
    """

    SCORING_WEIGHTS = {
        'intended_use_match': 25,
        'technology_match': 25,
        'recency_score': 20,
        'safety_score': 20,
        'acceptability_score': 10
    }

    def __init__(self, api_client: Optional[FDAAPIClient] = None):
        self.api_client = api_client

    def recommend(
        self,
        candidates: List[DeviceProfile],
        subject: Optional[DeviceProfile] = None,
        gap_results: Optional[Dict] = None,
        exclusions: Optional[List[str]] = None,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Rank candidates and return top N recommendations.

        Args:
            candidates: All enriched devices from CSV
            subject: Subject device profile (for similarity scoring)
            gap_results: Gap analysis output (for gap-coverage scoring)
            exclusions: K-numbers to exclude
            top_n: Number of recommendations to return

        Returns:
            RecommendationResult dict
        """
        exclusion_set = set(exclusions or [])
        scored = []

        for candidate in candidates:
            if candidate.k_number in exclusion_set:
                continue

            score = self._score_candidate(candidate, subject, gap_results)
            scored.append((candidate, score))

        # Sort by composite score descending
        scored.sort(key=lambda x: x[1]['composite'], reverse=True)

        return {
            'search_criteria': { ... },
            'recommendations': [
                self._format_recommendation(rank, device, score)
                for rank, (device, score) in enumerate(scored[:top_n], 1)
            ],
            'excluded_devices': [ ... ],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'disclaimer': AUTOMATION_RECOMMEND_DISCLAIMER
        }

    def _score_intended_use(
        self,
        candidate: DeviceProfile,
        subject: DeviceProfile
    ) -> float:
        """
        Score intended use similarity (0-25).

        Method: Jaccard similarity on normalized keyword sets extracted
        from intended use / indications for use text.

        Falls back to product code match (15/25) when IFU text
        is unavailable.
        """
        ...

    def _score_technology(
        self,
        candidate: DeviceProfile,
        subject: DeviceProfile
    ) -> float:
        """
        Score technology alignment (0-25).

        Components:
        - Same product code: 15 pts
        - Device name word overlap: 5 pts
        - Same advisory committee: 5 pts
        """
        ...

    def _score_recency(self, candidate: DeviceProfile) -> float:
        """
        Score clearance recency (0-20).

        Linear decay from 20 (this year) to 0 (15+ years ago).
        Formula: max(0, 20 - (age_years * 20/15))
        """
        ...

    def _score_safety(
        self,
        candidate: DeviceProfile
    ) -> float:
        """
        Score safety profile (0-20).

        Components:
        - No recalls: 10 pts (0 if any recalls)
        - MAUDE classification EXCELLENT/GOOD: 5 pts
        - No Class I recalls: 5 pts
        """
        ...

    def _score_acceptability(self, candidate: DeviceProfile) -> float:
        """
        Score Phase 2 acceptability (0-10).

        Direct mapping from Phase 2 assessment:
        - ACCEPTABLE: 10 pts
        - REVIEW_REQUIRED: 5 pts
        - NOT_RECOMMENDED: 0 pts
        """
        ...
```

### 5.3 ExecutiveSummaryGenerator

```python
class ExecutiveSummaryGenerator:
    """
    Generates a markdown executive summary synthesizing all
    enrichment and automation data into a strategic narrative.

    Output sections:
    1. Project Overview (device, product code, candidate pool)
    2. Gap Analysis Summary (critical/major/minor gaps)
    3. Recommended Predicates (top 3-5 with rationale)
    4. Risk Assessment (overall submission risk level)
    5. Resource & Timeline Estimate
    6. Recommended Next Steps
    """

    def generate(
        self,
        gap_results: Optional[Dict] = None,
        recommendations: Optional[Dict] = None,
        enrichment_metadata: Optional[Dict] = None,
        intelligence_data: Optional[Dict] = None,
        project_name: str = ''
    ) -> str:
        """
        Generate markdown executive summary.

        Can operate with partial inputs -- sections are omitted
        when their source data is unavailable.

        Returns:
            Markdown-formatted executive summary string
        """
        sections = []
        sections.append(self._header(project_name))
        sections.append(self._disclaimer())

        if gap_results:
            sections.append(self._gap_summary(gap_results))

        if recommendations:
            sections.append(self._recommendation_summary(recommendations))

        if gap_results or recommendations:
            sections.append(self._risk_assessment(gap_results, recommendations))

        sections.append(self._resource_estimate(
            gap_results, recommendations, enrichment_metadata
        ))
        sections.append(self._next_steps(gap_results, recommendations))
        sections.append(self._footer())

        return '\n\n'.join(sections)
```

### 5.4 FDAAutomation Facade

```python
class FDAAutomation:
    """
    Facade class coordinating Phase 4 automation features.

    Usage:
        automation = FDAAutomation(api_key="...", project_dir="/path/to/project")
        results = automation.run_full_analysis()
        # results contains gap_analysis, recommendations, executive_summary
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_dir: Optional[str] = None
    ):
        self.api_client = FDAAPIClient(api_key=api_key)
        self.project_dir = project_dir
        self.gap_analyzer = GapAnalyzer(api_client=self.api_client)
        self.recommender = PredicateRecommender(api_client=self.api_client)
        self.summary_generator = ExecutiveSummaryGenerator()

    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run complete Phase 4 pipeline:
        1. Load project data
        2. Run gap analysis
        3. Generate recommendations
        4. Produce executive summary
        5. Write all output files

        Returns:
            Dict with all results and file paths
        """
        # 1. Load inputs
        subject, predicates, candidates = self._load_project_data()

        # 2. Gap analysis
        gap_results = self.gap_analyzer.analyze(subject, predicates)

        # 3. Recommendations (informed by gaps)
        exclusions = [p.k_number for p in predicates]  # exclude already-selected
        recommendations = self.recommender.recommend(
            candidates, subject, gap_results, exclusions
        )

        # 4. Executive summary
        summary = self.summary_generator.generate(
            gap_results, recommendations
        )

        # 5. Write outputs
        output_paths = self._write_outputs(
            gap_results, recommendations, summary
        )

        return {
            'gap_analysis': gap_results,
            'recommendations': recommendations,
            'executive_summary': summary,
            'output_files': output_paths
        }

    def run_gap_analysis_only(self) -> Dict[str, Any]:
        """Run gap analysis without recommendations or summary."""
        ...

    def run_recommendations_only(self) -> Dict[str, Any]:
        """Run recommendations without gap analysis."""
        ...

    def run_summary_only(self) -> Dict[str, Any]:
        """Generate summary from existing automation output files."""
        ...

    def _load_project_data(self) -> Tuple:
        """
        Load subject, predicates, and candidates from project directory.

        Reads:
        - device_profile.json -> subject DeviceProfile
        - review.json -> predicate DeviceProfiles
        - 510k_download.csv -> candidate DeviceProfiles
        """
        ...

    def _write_outputs(self, gap_results, recommendations, summary) -> Dict:
        """
        Write all output files to project automation/ directory.

        Creates:
        - automation/gap_analysis.json
        - automation/gap_report.md
        - automation/recommendations.json
        - automation/recommend.md
        - automation/executive_summary.md
        - automation/automation_metadata.json
        """
        ...
```

---

## 6. API Between Components

### 6.1 Internal APIs (Python)

```
FDAAutomation (Facade)
    |
    +-- FDAAPIClient           (shared HTTP client)
    |       .query(endpoint, params) -> Optional[Dict]
    |
    +-- GapAnalyzer
    |       .analyze(subject, predicates, ...) -> GapAnalysisResult
    |       ._compare_intended_use(...) -> List[Gap]
    |       ._compare_technology(...) -> List[Gap]
    |       ._compare_materials(...) -> List[Gap]
    |       ._deduplicate_gaps(gaps) -> List[Gap]
    |       ._calculate_risk_summary(gaps) -> RiskSummary
    |
    +-- PredicateRecommender
    |       .recommend(candidates, subject, ...) -> RecommendationResult
    |       ._score_candidate(...) -> ScoreBreakdown
    |       ._score_intended_use(...) -> float
    |       ._score_technology(...) -> float
    |       ._score_recency(...) -> float
    |       ._score_safety(...) -> float
    |       ._score_acceptability(...) -> float
    |
    +-- ExecutiveSummaryGenerator
            .generate(gap_results, recommendations, ...) -> str
            ._header(project) -> str
            ._gap_summary(results) -> str
            ._recommendation_summary(results) -> str
            ._risk_assessment(gaps, recs) -> str
            ._resource_estimate(...) -> str
            ._next_steps(...) -> str
```

### 6.2 Command-to-Module API

The `automate.md` command invokes the module via inline Python:

```python
# In automate.md Step 4: Execute Analysis
sys.path.insert(0, str(lib_path))
from fda_automation import FDAAutomation

automation = FDAAutomation(
    api_key=api_key,
    project_dir=project_dir
)

if mode == 'full':
    results = automation.run_full_analysis()
elif mode == 'gaps':
    results = automation.run_gap_analysis_only()
elif mode == 'recommend':
    results = automation.run_recommendations_only()
elif mode == 'summary':
    results = automation.run_summary_only()
```

### 6.3 Cross-Command Data API

Phase 4 output files serve as the data API for downstream commands:

```
automate.md writes:
    automation/gap_analysis.json    <-- read by compare-se.md (emphasis rows)
    automation/recommendations.json <-- read by review.md --re-review (new candidates)
    automation/executive_summary.md <-- read by draft.md (cover letter content)
```

Each downstream command checks for the existence of these files:

```python
# In compare-se.md Step 1 (proposed enhancement)
gap_file = os.path.join(project_dir, 'automation', 'gap_analysis.json')
if os.path.exists(gap_file):
    with open(gap_file) as f:
        gap_data = json.load(f)
    # Highlight rows corresponding to CRITICAL and MAJOR gaps
```

---

## 7. Output Strategy

### 7.1 Decision: Separate Files, Not CSV Columns

**Recommendation:** Phase 4 output goes into separate files in an `automation/` subdirectory, NOT as additional CSV columns.

**Rationale:**

| Approach | Pros | Cons |
|----------|------|------|
| New CSV columns | Single file, backward compatible | CSV already has 53 columns, gap analysis is per-project not per-row |
| Append to existing reports | Fewer files | Mixes Phase 1-3 data with Phase 4 analysis |
| Separate files in subdirectory | Clean separation, machine + human readable | More files to track |

Gap analysis is fundamentally a project-level operation (one subject vs. N predicates), not a per-device-row operation. It cannot be expressed as CSV columns. Recommendations could theoretically be CSV columns (a score per row), but the rationale text, gap coverage, and score breakdown require richer structure than CSV supports.

### 7.2 File Format Strategy

| File | Format | Purpose | Consumer |
|------|--------|---------|----------|
| `gap_analysis.json` | JSON | Machine-readable gap data | compare-se.md, draft.md, tests |
| `gap_report.md` | Markdown | Human-readable gap report | RA professional review |
| `recommendations.json` | JSON | Machine-readable ranked predicates | review.md, tests |
| `recommend.md` | Markdown | Human-readable recommendation report | RA professional review |
| `executive_summary.md` | Markdown | Strategic narrative synthesis | Cover letter, management review |
| `automation_metadata.json` | JSON | Run provenance, disclaimers, timing | Audit trail |

Dual-format (JSON + Markdown) for gap analysis and recommendations follows the established pattern from Phase 1 (`enrichment_metadata.json` + `quality_report.md`).

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/test_fda_automation.py

class TestGapAnalyzer:
    """Test gap analysis with known device pairs."""

    def test_identical_devices_no_gaps(self):
        """Two identical profiles should produce zero gaps."""

    def test_ifu_expansion_detected(self):
        """Broader subject IFU should produce CRITICAL gap."""

    def test_material_change_detected(self):
        """Different patient-contact material should produce CRITICAL gap."""

    def test_sterilization_change_detected(self):
        """EO vs gamma sterilization should produce MAJOR gap."""

    def test_dimensional_change_minor(self):
        """Size difference within range should produce MINOR gap."""

    def test_deduplication_across_predicates(self):
        """Same gap found against two predicates should appear once."""


class TestPredicateRecommender:
    """Test recommendation scoring."""

    def test_same_product_code_scored_higher(self):
        """Candidate with matching product code gets technology bonus."""

    def test_recent_clearance_scored_higher(self):
        """2024 clearance scores higher than 2010 clearance."""

    def test_recalled_device_penalized(self):
        """Device with recalls gets lower safety score."""

    def test_not_recommended_excluded(self):
        """Phase 2 NOT_RECOMMENDED devices score 0 on acceptability."""

    def test_exclusion_list_respected(self):
        """Excluded K-numbers do not appear in results."""

    def test_top_n_respected(self):
        """Only top N recommendations returned."""


class TestExecutiveSummaryGenerator:
    """Test summary generation."""

    def test_partial_inputs_handled(self):
        """Summary generates with only gap results (no recommendations)."""

    def test_all_sections_present(self):
        """Full input produces all expected sections."""

    def test_disclaimer_included(self):
        """Output always includes verification disclaimer."""


class TestFDAAutomation:
    """Integration tests for facade."""

    def test_full_pipeline_with_mock_data(self):
        """End-to-end test with synthetic project data."""

    def test_output_files_created(self):
        """All expected files written to automation/ directory."""
```

### 8.2 Test Data

Create synthetic test fixtures:

```
tests/fixtures/
    phase4_test_project/
        device_profile.json      # Synthetic subject device
        review.json              # 2 accepted predicates
        510k_download.csv        # 20 enriched candidate rows
        enrichment_metadata.json # Phase 1 metadata
```

---

## 9. Migration and Rollout Plan

### 9.1 Phase 4a: Foundation (4 hours)

1. Create `lib/_shared.py` with `FDAAPIClient` and `DeviceProfile`
2. Create `lib/fda_automation.py` with class skeletons
3. Create `tests/test_fda_automation.py` with test skeletons
4. Create `tests/fixtures/phase4_test_project/` with synthetic data

### 9.2 Phase 4b: Gap Analysis (6 hours)

1. Implement `GapAnalyzer` with all comparison methods
2. Implement gap report markdown generation
3. Write unit tests for gap analysis
4. Validate against known device pairs (DQY catheter, OVE fusion cage)

### 9.3 Phase 4c: Recommendations (5 hours)

1. Implement `PredicateRecommender` with all scoring components
2. Implement recommendation report markdown generation
3. Write unit tests for scoring model
4. Validate scoring against manually ranked predicates

### 9.4 Phase 4d: Summary and Integration (5 hours)

1. Implement `ExecutiveSummaryGenerator`
2. Implement `FDAAutomation` facade
3. Create `commands/automate.md` command
4. Add automation disclaimers to `disclaimers.py`
5. End-to-end integration test

### 9.5 Phase 4e: Downstream Integration (2 hours)

1. Update `compare-se.md` to read `automation/gap_analysis.json`
2. Update `draft.md` to read `automation/executive_summary.md`
3. Update pipeline documentation

**Total estimated effort: 22 hours**

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gap analysis accuracy -- false positives | HIGH | MEDIUM | Conservative severity (default to INFORMATIONAL, require evidence for CRITICAL) |
| Recommendation scoring bias | MEDIUM | HIGH | Transparent score breakdown, all weights documented, RA professional review required |
| Scope creep into ML territory | MEDIUM | HIGH | Explicit design decision: rule-based only, no training data dependency |
| batchfetch.md further growth | LOW | MEDIUM | Separate command file, no changes to batchfetch.md |
| Breaking existing module interfaces | LOW | HIGH | New module with no changes to fda_enrichment.py |
| Insufficient subject device data | HIGH | MEDIUM | Graceful degradation: recommend without gap analysis when subject profile incomplete |
| Users treating automation output as regulatory advice | HIGH | HIGH | Prominent disclaimers on every output file, RESEARCH USE ONLY labeling |

---

## 11. Architectural Decisions Record

### ADR-001: Separate Module Over Extension

**Context:** Phase 4 features could extend `fda_enrichment.py` or live in a new module.
**Decision:** New `fda_automation.py` module.
**Consequences:** Clean separation of concerns, independent testability, no risk to existing production code. Requires shared API client extraction.

### ADR-002: Rule-Based Scoring Over ML

**Context:** "Smart predicate recommendations" could use ML or rule-based scoring.
**Decision:** Rule-based composite scoring with transparent weights.
**Consequences:** Explainable recommendations that map to FDA guidance criteria. RA professionals can audit and understand every score component. No training data dependency. Scores may be less "intelligent" than ML but are fully traceable.

### ADR-003: Separate Command Over batchfetch Extension

**Context:** Automation could run inside batchfetch or as a separate command.
**Decision:** New `/fda:automate` command.
**Consequences:** batchfetch.md stays at current size, automation has its own workflow with project context requirements. Users must run an additional command (minor friction).

### ADR-004: Dual-Format Output (JSON + Markdown)

**Context:** Output could be JSON only, Markdown only, or both.
**Decision:** Both JSON (machine-readable) and Markdown (human-readable) for gap analysis and recommendations.
**Consequences:** Downstream commands can programmatically consume JSON. RA professionals can read Markdown reports directly. Two files per feature instead of one.

### ADR-005: Subdirectory Isolation

**Context:** Phase 4 files could go in the project root or a subdirectory.
**Decision:** `automation/` subdirectory within the project.
**Consequences:** Clear provenance (all automation-generated files in one place), no collision with existing files, easy to delete/regenerate.

---

## 12. Summary

Phase 4 introduces three tightly connected but architecturally isolated automation features into the FDA Predicate Assistant. The design prioritizes:

1. **Separation of concerns** -- New module (`fda_automation.py`) with no changes to existing production code
2. **Explainability** -- Rule-based scoring with transparent weights instead of opaque ML
3. **Graceful degradation** -- Each feature operates independently when upstream data is incomplete
4. **Regulatory discipline** -- Prominent disclaimers, research-only labeling, RA professional verification requirements
5. **Testability** -- Unit tests with synthetic fixtures, no live API dependency for core logic
6. **Evolutionary architecture** -- Shared `FDAAPIClient` enables future refactoring of `fda_enrichment.py` without breaking Phase 4

The estimated effort is 22 hours across 5 sub-phases, with the foundation and gap analysis as the highest-priority deliverables.
