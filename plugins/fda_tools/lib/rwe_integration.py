#!/usr/bin/env python3
"""
FDA Real World Evidence (RWE) Integration Module
=================================================

Provides core functionality for integrating Real World Evidence into
FDA regulatory submissions including:
- RWE data source connector with quality assessment
- Real-world data (RWD) quality scoring framework
- RWE submission templates for 510(k) and PMA pathways
- FDA RWE Framework alignment (Dec 2018 guidance)

Regulatory basis:
- FDA Framework for FDA's Real-World Evidence Program (Dec 2018)
- 21st Century Cures Act Section 3022
- FDA Guidance: "Use of Real-World Evidence to Support Regulatory Decision-Making" (2021)
- FDA Guidance: "Submitting Documents Using Real-World Data and Real-World Evidence" (2023)

DISCLAIMER: This tool is for RESEARCH USE ONLY. RWE submissions require
review by qualified regulatory and biostatistics professionals. Do not
submit to FDA without independent professional verification.

Version: 1.0.0
Date: 2026-02-17
"""

from typing import Any, Dict, List, Optional


# ========================================================================
# CONSTANTS
# ========================================================================

# RWD Source Types recognized by FDA
RWD_SOURCE_TYPES = {
    "ehr": {
        "name": "Electronic Health Records (EHR)",
        "description": "Clinical data from hospital and outpatient electronic health record systems",
        "fda_recognized": True,
        "typical_quality": "high",
        "common_systems": ["Epic", "Cerner", "MEDITECH", "Allscripts"],
        "key_considerations": [
            "Data completeness varies by institution",
            "Structured vs unstructured data challenges",
            "Interoperability across systems",
            "May lack device-specific identifiers",
        ],
    },
    "claims": {
        "name": "Medical Claims / Insurance Data",
        "description": "Administrative claims data from payers including diagnosis, procedure, and billing codes",
        "fda_recognized": True,
        "typical_quality": "medium",
        "common_systems": ["CMS Medicare/Medicaid", "Commercial payers", "Optum", "MarketScan"],
        "key_considerations": [
            "Limited clinical detail beyond codes",
            "Coding accuracy varies",
            "Good for long-term follow-up",
            "May not capture device-specific outcomes",
        ],
    },
    "registry": {
        "name": "Patient / Disease Registries",
        "description": "Organized systems for collecting clinical and outcome data for specific devices or conditions",
        "fda_recognized": True,
        "typical_quality": "high",
        "common_systems": ["CMS Qualified Clinical Data Registry", "Society registries", "NEST"],
        "key_considerations": [
            "Purpose-built data collection",
            "Often highest quality RWD source",
            "May have selection bias",
            "Cost of participation",
        ],
    },
    "pragmatic_trial": {
        "name": "Pragmatic Clinical Trials",
        "description": "Clinical trials conducted in real-world clinical practice settings",
        "fda_recognized": True,
        "typical_quality": "high",
        "common_systems": ["PCORnet", "Health systems networks", "Point-of-care trials"],
        "key_considerations": [
            "Combines RCT rigor with real-world generalizability",
            "Protocol adherence may be lower than traditional RCTs",
            "Larger sample sizes often possible",
            "May be considered RWE by FDA",
        ],
    },
    "patient_generated": {
        "name": "Patient-Generated Health Data",
        "description": "Data from wearables, mobile apps, patient surveys, and patient-reported outcomes",
        "fda_recognized": True,
        "typical_quality": "low",
        "common_systems": ["Apple Health", "Google Fit", "Custom apps", "PRO instruments"],
        "key_considerations": [
            "Growing FDA acceptance",
            "Data quality and completeness concerns",
            "Patient engagement challenges",
            "Validation of digital endpoints needed",
        ],
    },
    "natural_history": {
        "name": "Natural History Studies",
        "description": "Studies documenting the natural course of a disease without intervention",
        "fda_recognized": True,
        "typical_quality": "medium",
        "common_systems": ["NIH natural history protocols", "FDA rare disease databases"],
        "key_considerations": [
            "Useful as external control arm",
            "Critical for rare diseases/HDE",
            "Long-term data valuable for benefit-risk",
            "Selection of appropriate comparator period important",
        ],
    },
    "sentinel": {
        "name": "FDA Sentinel System",
        "description": "FDA's national electronic system for medical product safety surveillance",
        "fda_recognized": True,
        "typical_quality": "high",
        "common_systems": ["Sentinel Distributed Database", "ARIA", "NEST collaboratives"],
        "key_considerations": [
            "FDA-managed distributed data system",
            "Primary use is post-market safety surveillance",
            "Large population coverage",
            "Structured querying capabilities",
        ],
    },
}

# RWD Quality Dimensions per FDA RWE Framework
RWD_QUALITY_DIMENSIONS = {
    "relevance": {
        "name": "Relevance",
        "description": "Data captures the appropriate population, exposure, outcomes, and follow-up",
        "max_score": 20,
        "sub_criteria": [
            "population_representativeness",
            "exposure_capture",
            "outcome_measurement",
            "follow_up_duration",
        ],
    },
    "reliability": {
        "name": "Reliability",
        "description": "Data is collected consistently with verified accuracy",
        "max_score": 20,
        "sub_criteria": [
            "data_accrual_consistency",
            "verification_procedures",
            "audit_trail",
            "data_standards_compliance",
        ],
    },
    "completeness": {
        "name": "Completeness",
        "description": "Minimal missing data across key variables",
        "max_score": 20,
        "sub_criteria": [
            "variable_completeness",
            "patient_follow_up_completeness",
            "outcome_ascertainment",
            "missing_data_patterns",
        ],
    },
    "transparency": {
        "name": "Transparency",
        "description": "Data provenance, processing, and limitations are documented",
        "max_score": 20,
        "sub_criteria": [
            "data_provenance_documented",
            "processing_steps_documented",
            "limitations_acknowledged",
            "analysis_plan_prespecified",
        ],
    },
    "regulatory_alignment": {
        "name": "Regulatory Alignment",
        "description": "Data and study design align with FDA RWE framework expectations",
        "max_score": 20,
        "sub_criteria": [
            "study_design_appropriate",
            "endpoint_fda_acceptable",
            "bias_control_adequate",
            "statistical_methods_robust",
        ],
    },
}

# FDA-recognized analytical methods for RWE
RWE_ANALYTICAL_METHODS = [
    {
        "method": "Propensity Score Matching",
        "description": "Statistical matching of treated/untreated groups on observed covariates",
        "fda_accepted": True,
        "best_for": ["observational comparisons", "registry data"],
    },
    {
        "method": "Instrumental Variables",
        "description": "Using natural experiments to estimate causal effects",
        "fda_accepted": True,
        "best_for": ["confounding by indication", "preference-based instruments"],
    },
    {
        "method": "Difference-in-Differences",
        "description": "Comparing trends before/after intervention vs control group",
        "fda_accepted": True,
        "best_for": ["policy changes", "device introduction timing"],
    },
    {
        "method": "Interrupted Time Series",
        "description": "Analyzing trends before and after intervention in time-series data",
        "fda_accepted": True,
        "best_for": ["safety surveillance", "post-market monitoring"],
    },
    {
        "method": "External Control Arms",
        "description": "Using RWD as historical or concurrent control for single-arm trials",
        "fda_accepted": True,
        "best_for": ["rare diseases", "ethical constraints on randomization"],
    },
    {
        "method": "Bayesian Adaptive Designs",
        "description": "Incorporating RWE as informative priors in trial design",
        "fda_accepted": True,
        "best_for": ["sample size reduction", "rare conditions", "pediatric devices"],
    },
]


# ========================================================================
# RWE DATA SOURCE CONNECTOR
# ========================================================================

class RWEDataSourceConnector:
    """
    Manages connections to and evaluation of Real World Data sources.

    Provides a structured framework for documenting RWD sources,
    assessing their quality, and determining fitness for FDA submissions.
    """

    def __init__(self):
        self.connected_sources = []

    def add_source(
        self,
        source_type: str,
        source_name: str,
        description: Optional[str] = None,
        data_period_start: Optional[str] = None,
        data_period_end: Optional[str] = None,
        patient_count: Optional[int] = None,
        variables_available: Optional[List[str]] = None,
        data_format: Optional[str] = None,
        access_method: Optional[str] = None,
        udi_available: bool = False,
        device_identifiable: bool = False,
        irb_approved: bool = False,
        dua_executed: bool = False,
        hipaa_compliant: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register an RWD source for use in regulatory submissions.

        Args:
            source_type: One of RWD_SOURCE_TYPES keys
            source_name: Name/identifier of the specific data source
            description: Description of what the source contains
            data_period_start: Start of available data period (ISO date)
            data_period_end: End of available data period (ISO date)
            patient_count: Approximate number of patients in dataset
            variables_available: List of key variables/fields available
            data_format: Format of the data (CSV, FHIR, HL7, etc.)
            access_method: How data is accessed (API, file transfer, etc.)
            udi_available: Whether UDI data is available for device tracking
            device_identifiable: Whether specific devices can be identified
            irb_approved: Whether IRB approval has been obtained
            dua_executed: Whether a Data Use Agreement is in place
            hipaa_compliant: Whether data handling is HIPAA compliant
            metadata: Additional metadata

        Returns:
            Source record with quality pre-assessment
        """
        if source_type not in RWD_SOURCE_TYPES:
            raise ValueError(
                f"Invalid source type '{source_type}'. "
                f"Must be one of: {', '.join(RWD_SOURCE_TYPES.keys())}"
            )

        source_def = RWD_SOURCE_TYPES[source_type]

        record = {
            "source_id": f"RWD-{len(self.connected_sources) + 1:04d}",
            "source_type": source_type,
            "source_type_name": source_def["name"],
            "source_name": source_name,
            "description": description or source_def["description"],
            "fda_recognized": source_def["fda_recognized"],
            "data_period": {
                "start": data_period_start,
                "end": data_period_end,
            },
            "patient_count": patient_count,
            "variables_available": variables_available or [],
            "data_format": data_format,
            "access_method": access_method,
            "device_tracking": {
                "udi_available": udi_available,
                "device_identifiable": device_identifiable,
            },
            "compliance": {
                "irb_approved": irb_approved,
                "dua_executed": dua_executed,
                "hipaa_compliant": hipaa_compliant,
            },
            "metadata": metadata or {},
            "added_at": datetime.now(timezone.utc).isoformat(),
            "readiness_flags": [],
            "warnings": [],
        }

        # Readiness checks
        if not irb_approved:
            record["readiness_flags"].append("IRB approval required before data access")
        if not dua_executed:
            record["readiness_flags"].append("Data Use Agreement must be executed")
        if not hipaa_compliant:
            record["warnings"].append("HIPAA compliance not confirmed - CRITICAL")
        if not device_identifiable:
            record["warnings"].append(
                "Device not specifically identifiable in data - limits causal inference"
            )
        if not udi_available:
            record["readiness_flags"].append(
                "UDI not available - consider alternative device identification methods"
            )

        self.connected_sources.append(record)
        return record

    def get_sources_summary(self) -> Dict[str, Any]:
        """Get summary of all connected data sources."""
        return {
            "total_sources": len(self.connected_sources),
            "source_types": list(set(
                s["source_type"] for s in self.connected_sources
            )),
            "total_patients": sum(
                s["patient_count"] or 0 for s in self.connected_sources
            ),
            "fda_recognized_count": sum(
                1 for s in self.connected_sources if s["fda_recognized"]
            ),
            "compliant_count": sum(
                1 for s in self.connected_sources
                if s["compliance"]["irb_approved"] and s["compliance"]["dua_executed"]
            ),
            "sources": self.connected_sources,
        }

    def recommend_sources(
        self,
        submission_type: str = "510k",
        device_type: Optional[str] = None,
        is_rare_disease: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Recommend RWD source types based on submission needs.

        Args:
            submission_type: "510k", "pma", "hde", or "de_novo"
            device_type: Category of device (implant, diagnostic, etc.)
            is_rare_disease: Whether the device targets a rare disease

        Returns:
            List of recommended source types with rationale
        """
        recommendations = []

        if submission_type in ("pma", "hde"):
            recommendations.append({
                "source_type": "registry",
                "priority": "HIGH",
                "rationale": "Registries provide the highest quality long-term outcome data for PMA/HDE",
            })
            recommendations.append({
                "source_type": "ehr",
                "priority": "HIGH",
                "rationale": "EHR data supplements registry data with broader clinical context",
            })

        if submission_type == "510k":
            recommendations.append({
                "source_type": "registry",
                "priority": "MEDIUM",
                "rationale": "Registry data can support substantial equivalence claims with outcome data",
            })
            recommendations.append({
                "source_type": "claims",
                "priority": "MEDIUM",
                "rationale": "Claims data useful for comparative safety/utilization analysis",
            })

        if is_rare_disease:
            recommendations.append({
                "source_type": "natural_history",
                "priority": "HIGH",
                "rationale": "Natural history data critical for rare disease context and external controls",
            })
            recommendations.append({
                "source_type": "patient_generated",
                "priority": "MEDIUM",
                "rationale": "Patient-reported outcomes valuable when clinical trial enrollment is limited",
            })

        if device_type and device_type.lower() in ("implant", "implantable"):
            recommendations.append({
                "source_type": "sentinel",
                "priority": "MEDIUM",
                "rationale": "Sentinel system useful for post-market implant surveillance",
            })

        # Always recommend pragmatic trials for high-evidence needs
        if submission_type in ("pma", "de_novo"):
            recommendations.append({
                "source_type": "pragmatic_trial",
                "priority": "HIGH",
                "rationale": "Pragmatic trials combine RCT rigor with real-world generalizability",
            })

        return recommendations


# ========================================================================
# RWD QUALITY ASSESSOR
# ========================================================================

class RWDQualityAssessor:
    """
    Assesses quality of Real World Data for FDA regulatory use.

    Implements the FDA RWE Framework's quality dimensions:
    relevance, reliability, completeness, transparency, and regulatory alignment.
    """

    def __init__(self):
        self.dimensions = RWD_QUALITY_DIMENSIONS.copy()
        self.assessments = []

    def assess_source(
        self,
        source_name: str,
        source_type: str,
        dimension_scores: Optional[Dict[str, Dict[str, int]]] = None,
        notes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Assess quality of an RWD source across all dimensions.

        Args:
            source_name: Name of the data source
            source_type: Type of data source (from RWD_SOURCE_TYPES)
            dimension_scores: Dict mapping dimension->sub_criteria->score (0-5)
            notes: Dict mapping dimension->notes

        Returns:
            Quality assessment with scores and recommendations
        """
        dimension_scores = dimension_scores or {}
        notes = notes or {}

        assessment = {
            "source_name": source_name,
            "source_type": source_type,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "dimensions": {},
            "overall_score": 0,
            "grade": "",
            "fit_for_purpose": {},
            "recommendations": [],
            "disclaimer": (
                "RESEARCH USE ONLY. Data quality assessments require "
                "independent verification by qualified biostatisticians."
            ),
        }

        total_score = 0
        max_possible = 0

        for dim_id, dim_def in self.dimensions.items():
            dim_scores = dimension_scores.get(dim_id, {})
            sub_results = []
            dim_total = 0
            dim_max = len(dim_def["sub_criteria"]) * 5  # Max 5 per sub-criterion

            for sub in dim_def["sub_criteria"]:
                score = dim_scores.get(sub, 0)
                # Each sub-criterion is scored 0–5 by the caller to match FDA's five-level
                # quality framework (absent → minimal → partial → adequate → exemplary).
                # Clamping prevents accidental out-of-range values from corrupting the
                # overall score, since we sum sub-scores to calculate the dimension total.
                score = max(0, min(5, score))  # Clamp to 0-5
                sub_results.append({
                    "criterion": sub,
                    "score": score,
                    "max": 5,
                })
                dim_total += score

            # Normalize raw sub-criterion points to the dimension's declared max_score
            # so that dimensions with more sub-criteria don't unfairly dominate the total.
            # Example: a dimension with 4 sub-criteria (max raw = 20) and max_score = 20
            # maps directly; a dimension with 3 sub-criteria (max raw = 15) but max_score
            # = 20 is scaled up proportionally so all dimensions contribute equally.
            normalized = round(
                (dim_total / dim_max * dim_def["max_score"]) if dim_max > 0 else 0,
                1,
            )

            assessment["dimensions"][dim_id] = {
                "name": dim_def["name"],
                "description": dim_def["description"],
                "sub_criteria": sub_results,
                "raw_score": dim_total,
                "raw_max": dim_max,
                "normalized_score": normalized,
                "max_score": dim_def["max_score"],
                "notes": notes.get(dim_id, ""),
            }

            total_score += normalized
            max_possible += dim_def["max_score"]

        assessment["overall_score"] = round(total_score, 1)
        assessment["max_score"] = max_possible

        # Grade assignment
        pct = (total_score / max_possible * 100) if max_possible > 0 else 0
        if pct >= 80:
            assessment["grade"] = "A"
        elif pct >= 65:
            assessment["grade"] = "B"
        elif pct >= 50:
            assessment["grade"] = "C"
        elif pct >= 35:
            assessment["grade"] = "D"
        else:
            assessment["grade"] = "F"

        # Fit-for-purpose thresholds are aligned with FDA's RWE Framework (2018) and
        # Real-World Evidence Program guidance:
        # - 510(k) supplementary (≥50%): RWD used alongside bench/clinical testing to
        #   support SE; high data completeness not required when primary evidence is strong.
        # - 510(k) primary (≥70%): RWD is the main clinical evidence base; requires
        #   adequate reliability and regulatory alignment.
        # - PMA supplementary (≥60%): Higher bar than 510(k) due to Class III risk level.
        # - PMA primary (≥80%): RWD alone must meet valid scientific evidence standard
        #   per 21 CFR 860.7(c)(2); Grade A quality required.
        # - Post-market surveillance (≥40%): Registry/claims data needs only basic
        #   reliability; completeness is traded for scale and real-world relevance.
        # - HDE probable benefit (≥55%): Humanitarian device exemption requires
        #   probable (not proven) benefit; lighter evidentiary standard than PMA.
        assessment["fit_for_purpose"] = {
            "510k_supplementary": pct >= 50,
            "510k_primary": pct >= 70,
            "pma_supplementary": pct >= 60,
            "pma_primary": pct >= 80,
            "post_market_surveillance": pct >= 40,
            "hde_probable_benefit": pct >= 55,
        }

        # Generate recommendations
        for dim_id, dim_result in assessment["dimensions"].items():
            if dim_result["normalized_score"] < dim_result["max_score"] * 0.5:
                assessment["recommendations"].append({
                    "dimension": dim_result["name"],
                    "priority": "HIGH",
                    "message": (
                        f"{dim_result['name']} score is below 50%. "
                        f"Address: {', '.join(d['criterion'] for d in dim_result['sub_criteria'] if d['score'] < 3)}"
                    ),
                })

        self.assessments.append(assessment)
        return assessment

    def compare_sources(
        self, assessments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Compare quality across multiple assessed sources."""
        assessments = assessments or self.assessments
        if not assessments:
            return {"error": "No assessments available for comparison"}

        comparison = {
            "sources_compared": len(assessments),
            "comparison_date": datetime.now(timezone.utc).isoformat(),
            "rankings": [],
            "dimension_leaders": {},
        }

        # Rank by overall score
        sorted_assessments = sorted(
            assessments, key=lambda a: a["overall_score"], reverse=True
        )
        for rank, a in enumerate(sorted_assessments, 1):
            comparison["rankings"].append({
                "rank": rank,
                "source_name": a["source_name"],
                "overall_score": a["overall_score"],
                "grade": a["grade"],
            })

        # Find leaders per dimension
        for dim_id in self.dimensions:
            best_source = max(
                assessments,
                key=lambda a: a["dimensions"].get(dim_id, {}).get("normalized_score", 0),
            )
            comparison["dimension_leaders"][dim_id] = {
                "source": best_source["source_name"],
                "score": best_source["dimensions"].get(dim_id, {}).get("normalized_score", 0),
            }

        return comparison

    def to_markdown(self, assessment: Dict[str, Any]) -> str:
        """Export quality assessment as markdown."""
        lines = [
            f"# RWD Quality Assessment: {assessment['source_name']}",
            "",
            f"**Source Type:** {assessment['source_type']}",
            f"**Assessed:** {assessment['assessed_at']}",
            f"**Overall Score:** {assessment['overall_score']}/{assessment['max_score']}",
            f"**Grade:** {assessment['grade']}",
            "",
            "## Dimension Scores",
            "",
            "| Dimension | Score | Max | Percentage |",
            "|-----------|-------|-----|------------|",
        ]

        for dim_id, dim_data in assessment["dimensions"].items():
            pct = round(dim_data["normalized_score"] / dim_data["max_score"] * 100, 0) if dim_data["max_score"] > 0 else 0
            lines.append(
                f"| {dim_data['name']} | {dim_data['normalized_score']} | "
                f"{dim_data['max_score']} | {pct:.0f}% |"
            )

        lines.extend(["", "## Fit-for-Purpose", ""])
        for purpose, fit in assessment["fit_for_purpose"].items():
            status = "YES" if fit else "NO"
            lines.append(f"- **{purpose.replace('_', ' ').title()}:** {status}")

        if assessment["recommendations"]:
            lines.extend(["", "## Recommendations", ""])
            for rec in assessment["recommendations"]:
                lines.append(f"- **[{rec['priority']}]** {rec['message']}")

        lines.extend([
            "",
            "---",
            f"*{assessment['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# RWE SUBMISSION TEMPLATE GENERATOR
# ========================================================================

class RWESubmissionTemplate:
    """
    Generates RWE submission templates for 510(k) and PMA pathways.

    Aligned with FDA guidance on submitting documents using RWD/RWE.
    """

    # Template sections per FDA guidance
    TEMPLATE_SECTIONS = {
        "510k": [
            {
                "number": "1",
                "title": "Executive Summary",
                "description": "Overview of RWE use, regulatory question addressed, and key findings",
                "required": True,
            },
            {
                "number": "2",
                "title": "Regulatory Context",
                "description": "How RWE supports the submission (substantial equivalence, safety, performance)",
                "required": True,
            },
            {
                "number": "3",
                "title": "Study Design and Protocol",
                "description": "Pre-specified study protocol, endpoints, population, comparators",
                "required": True,
            },
            {
                "number": "4",
                "title": "Data Source Description",
                "description": "RWD source characterization, provenance, quality assessment",
                "required": True,
            },
            {
                "number": "5",
                "title": "Data Governance and Quality",
                "description": "Data quality measures, validation steps, missing data handling",
                "required": True,
            },
            {
                "number": "6",
                "title": "Statistical Analysis Plan",
                "description": "Pre-specified statistical methods, sensitivity analyses, bias mitigation",
                "required": True,
            },
            {
                "number": "7",
                "title": "Results",
                "description": "Study results with tables, figures, and statistical analysis outputs",
                "required": True,
            },
            {
                "number": "8",
                "title": "Limitations and Bias Assessment",
                "description": "Known limitations, potential biases, sensitivity analysis results",
                "required": True,
            },
            {
                "number": "9",
                "title": "Conclusions",
                "description": "Summary of how RWE supports the regulatory decision",
                "required": True,
            },
        ],
        "pma": [
            {
                "number": "1",
                "title": "Executive Summary",
                "description": "Overview of how RWE supplements PMA clinical evidence",
                "required": True,
            },
            {
                "number": "2",
                "title": "Regulatory Framework",
                "description": "How RWE fits within the PMA evidence package (primary/supplementary)",
                "required": True,
            },
            {
                "number": "3",
                "title": "RWE Study Protocol",
                "description": "Detailed protocol including objectives, design, population, endpoints",
                "required": True,
            },
            {
                "number": "4",
                "title": "Data Sources and Linkage",
                "description": "Detailed source descriptions, data linkage methods, UDI tracking",
                "required": True,
            },
            {
                "number": "5",
                "title": "Data Quality Framework",
                "description": "Comprehensive data quality assessment per FDA RWE Framework",
                "required": True,
            },
            {
                "number": "6",
                "title": "Statistical Methods",
                "description": "Detailed SAP, causal inference methods, confounding control",
                "required": True,
            },
            {
                "number": "7",
                "title": "Clinical Results",
                "description": "Primary and secondary endpoint results, safety outcomes",
                "required": True,
            },
            {
                "number": "8",
                "title": "Sensitivity and Subgroup Analyses",
                "description": "Pre-specified and post-hoc sensitivity analyses",
                "required": True,
            },
            {
                "number": "9",
                "title": "Bias Assessment and Limitations",
                "description": "Systematic bias assessment, unmeasured confounding, generalizability",
                "required": True,
            },
            {
                "number": "10",
                "title": "Integration with Clinical Trial Data",
                "description": "How RWE complements pivotal clinical trial findings",
                "required": True,
            },
            {
                "number": "11",
                "title": "Benefit-Risk Conclusions",
                "description": "Integrated benefit-risk assessment incorporating RWE",
                "required": True,
            },
        ],
    }

    def __init__(self, submission_type: str = "510k"):
        if submission_type not in self.TEMPLATE_SECTIONS:
            raise ValueError(
                f"Invalid submission type '{submission_type}'. "
                f"Must be one of: {', '.join(self.TEMPLATE_SECTIONS.keys())}"
            )
        self.submission_type = submission_type
        self.sections = self.TEMPLATE_SECTIONS[submission_type]

    def generate(
        self,
        device_name: str,
        regulatory_question: str,
        data_sources: Optional[List[Dict[str, str]]] = None,
        study_design: Optional[str] = None,
        endpoints: Optional[List[str]] = None,
        population: Optional[str] = None,
        comparator: Optional[str] = None,
        analytical_method: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate an RWE submission template.

        Args:
            device_name: Name of the device
            regulatory_question: The regulatory question RWE addresses
            data_sources: List of data source descriptions
            study_design: Study design description
            endpoints: List of primary/secondary endpoints
            population: Study population description
            comparator: Comparator device/treatment
            analytical_method: Primary analytical method

        Returns:
            Complete RWE submission template
        """
        data_sources = data_sources or []
        endpoints = endpoints or []

        template = {
            "title": f"RWE Submission Package - {device_name}",
            "submission_type": self.submission_type,
            "device_name": device_name,
            "regulatory_question": regulatory_question,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "fda_guidance_reference": (
                "FDA Guidance: Submitting Documents Using Real-World Data "
                "and Real-World Evidence to FDA for Drug and Biological Products (2023)"
            ),
            "study_overview": {
                "design": study_design or "[TODO: Specify study design]",
                "population": population or "[TODO: Define study population]",
                "comparator": comparator or "[TODO: Identify comparator]",
                "primary_endpoints": endpoints[:3] if endpoints else ["[TODO: Define primary endpoint]"],
                "secondary_endpoints": endpoints[3:] if len(endpoints) > 3 else [],
                "analytical_method": analytical_method or "[TODO: Specify analytical method]",
                "data_sources": data_sources,
            },
            "sections": [],
            "gaps": [],
            "recommended_methods": self._recommend_methods(study_design),
            "quality_checklist": self._build_quality_checklist(),
            "disclaimer": (
                "RESEARCH USE ONLY. RWE submission packages require review "
                "by qualified regulatory and biostatistics professionals."
            ),
        }

        # Build sections with content guidance
        for section_def in self.sections:
            section = {
                "number": section_def["number"],
                "title": section_def["title"],
                "description": section_def["description"],
                "required": section_def["required"],
                "status": "not_started",
                "content_guidance": self._get_section_guidance(
                    section_def["number"], device_name, regulatory_question
                ),
                "fda_expectations": self._get_fda_expectations(section_def["number"]),
            }

            template["gaps"].append({
                "section": section_def["title"],
                "severity": "HIGH",
                "message": f"Section {section_def['number']} content not yet prepared",
            })

            template["sections"].append(section)

        return template

    def _recommend_methods(self, study_design: Optional[str]) -> List[Dict[str, Any]]:
        """Recommend analytical methods based on study design."""
        recommendations = []
        for method in RWE_ANALYTICAL_METHODS:
            rec = {
                "method": method["method"],
                "description": method["description"],
                "fda_accepted": method["fda_accepted"],
                "best_for": method["best_for"],
            }
            recommendations.append(rec)
        return recommendations

    def _get_section_guidance(
        self, section_number: str, device_name: str, regulatory_question: str
    ) -> str:
        """Get content guidance for each section."""
        guidance_510k = {
            "1": f"Summarize how RWE for {device_name} supports the regulatory question: {regulatory_question}",
            "2": "Explain how RWE supports substantial equivalence determination (safety and/or performance)",
            "3": "Document pre-specified study protocol with PICO framework (Population, Intervention, Comparator, Outcome)",
            "4": "Characterize each RWD source: type, coverage period, population, variables, quality",
            "5": "Document data quality procedures: validation rules, missing data handling, audit trail",
            "6": "Pre-specified SAP including primary analysis, sensitivity analyses, multiplicity adjustment",
            "7": "Present results aligned with protocol-specified endpoints; include CONSORT-like flow diagram",
            "8": "Systematic assessment of all potential biases; quantitative bias analysis preferred",
            "9": "Synthesize how RWE answers the regulatory question; acknowledge limitations",
        }
        guidance_pma = {
            "1": f"Overview of how RWE for {device_name} supplements PMA clinical evidence",
            "2": "Define whether RWE serves as primary evidence, supportive evidence, or for specific endpoints",
            "3": "Detailed protocol per FDA recommendations; consider registering on ClinicalTrials.gov",
            "4": "Comprehensive source documentation including data linkage, UDI tracking, provenance",
            "5": "Full quality framework assessment per FDA RWE Framework dimensions",
            "6": "Detailed SAP with causal inference methods, propensity scores, sensitivity frameworks",
            "7": "Complete clinical results for all pre-specified endpoints",
            "8": "Comprehensive sensitivity and subgroup analyses; E-value for unmeasured confounding",
            "9": "Structured bias assessment using validated frameworks (e.g., ROBINS-I)",
            "10": "Integration matrix showing how RWE findings align with pivotal trial results",
            "11": "Integrated benefit-risk assessment incorporating both trial and RWE data",
        }

        guidance = guidance_pma if self.submission_type == "pma" else guidance_510k
        return guidance.get(section_number, "Consult FDA RWE guidance for requirements")

    def _get_fda_expectations(self, section_number: str) -> List[str]:
        """Get FDA expectations for each section."""
        expectations = {
            "1": [
                "Clear statement of regulatory question",
                "Brief summary of study design and key findings",
                "Explanation of why RWE is appropriate",
            ],
            "2": [
                "Alignment with FDA's RWE framework",
                "Justification for RWE use vs traditional evidence",
            ],
            "3": [
                "PICO-formatted study question",
                "Pre-registration of study protocol",
                "Clearly defined inclusion/exclusion criteria",
            ],
            "4": [
                "Data provenance documentation",
                "Source population characteristics",
                "Variable definitions and coding systems",
            ],
            "5": [
                "Data validation procedures",
                "Missing data assessment",
                "Data quality metrics",
            ],
            "6": [
                "Pre-specified primary analysis",
                "Multiple sensitivity analyses",
                "Bias mitigation strategies",
            ],
        }
        return expectations.get(section_number, ["Consult FDA RWE guidance"])

    def _build_quality_checklist(self) -> List[Dict[str, Any]]:
        """Build RWE quality checklist aligned with FDA expectations."""
        checklist = [
            {"item": "Study protocol pre-registered", "required": True, "status": "pending"},
            {"item": "Data sources characterized and documented", "required": True, "status": "pending"},
            {"item": "Data quality assessment completed", "required": True, "status": "pending"},
            {"item": "Statistical analysis plan finalized", "required": True, "status": "pending"},
            {"item": "IRB approval obtained for all data sources", "required": True, "status": "pending"},
            {"item": "Data Use Agreements executed", "required": True, "status": "pending"},
            {"item": "HIPAA compliance confirmed", "required": True, "status": "pending"},
            {"item": "Bias assessment framework selected", "required": True, "status": "pending"},
            {"item": "Sensitivity analyses planned", "required": True, "status": "pending"},
            {"item": "Results independently verified", "required": True, "status": "pending"},
            {"item": "Limitations clearly documented", "required": True, "status": "pending"},
            {"item": "Pre-Sub meeting with FDA conducted", "required": False, "status": "pending"},
        ]
        return checklist

    def to_markdown(self, template: Dict[str, Any]) -> str:
        """Export submission template as markdown."""
        lines = [
            f"# {template['title']}",
            "",
            f"**Submission Type:** {template['submission_type'].upper()}",
            f"**Device:** {template['device_name']}",
            f"**Regulatory Question:** {template['regulatory_question']}",
            f"**Generated:** {template['generated_at']}",
            "",
            "## Study Overview",
            f"- **Design:** {template['study_overview']['design']}",
            f"- **Population:** {template['study_overview']['population']}",
            f"- **Comparator:** {template['study_overview']['comparator']}",
            f"- **Analytical Method:** {template['study_overview']['analytical_method']}",
            "",
            "### Endpoints",
        ]

        for ep in template["study_overview"]["primary_endpoints"]:
            lines.append(f"- Primary: {ep}")
        for ep in template["study_overview"]["secondary_endpoints"]:
            lines.append(f"- Secondary: {ep}")

        lines.extend(["", "## Submission Sections", ""])

        for section in template["sections"]:
            lines.append(f"### Section {section['number']}: {section['title']}")
            lines.append(f"*{section['description']}*")
            lines.append("")
            lines.append(f"**Guidance:** {section['content_guidance']}")
            lines.append("")
            if section.get("fda_expectations"):
                lines.append("**FDA Expectations:**")
                for exp in section["fda_expectations"]:
                    lines.append(f"- {exp}")
                lines.append("")

        lines.extend(["## Quality Checklist", ""])
        for item in template["quality_checklist"]:
            req = " (REQUIRED)" if item["required"] else ""
            lines.append(f"- [ ] {item['item']}{req}")

        lines.extend(["", "## Recommended Analytical Methods", ""])
        for method in template["recommended_methods"]:
            accepted = "FDA Accepted" if method["fda_accepted"] else "Not yet accepted"
            lines.append(f"- **{method['method']}** ({accepted})")
            lines.append(f"  - {method['description']}")
            lines.append(f"  - Best for: {', '.join(method['best_for'])}")

        lines.extend([
            "",
            "---",
            f"*{template['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# CONVENIENCE FUNCTIONS
# ========================================================================

def create_rwe_connector() -> RWEDataSourceConnector:
    """Create a new RWE data source connector."""
    return RWEDataSourceConnector()


def assess_rwd_quality(
    source_name: str,
    source_type: str,
    dimension_scores: Optional[Dict[str, Dict[str, int]]] = None,
) -> Dict[str, Any]:
    """Assess quality of an RWD source."""
    assessor = RWDQualityAssessor()
    return assessor.assess_source(source_name, source_type, dimension_scores)


def generate_rwe_template(
    submission_type: str,
    device_name: str,
    regulatory_question: str,
    **kwargs,
) -> Dict[str, Any]:
    """Generate an RWE submission template."""
    generator = RWESubmissionTemplate(submission_type)
    return generator.generate(device_name, regulatory_question, **kwargs)
