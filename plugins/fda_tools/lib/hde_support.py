#!/usr/bin/env python3
"""
FDA Humanitarian Device Exemption (HDE) Support Module
======================================================

Provides core functionality for HDE submission preparation including:
- HDE submission outline generation (21 CFR 814 Subpart H)
- Rare disease prevalence validation (<8,000 patients/year in US)
- Probable benefit analysis template generation
- IRB approval tracking and status management
- Annual distribution report generation (21 CFR 814.126)

Regulatory basis:
- 21 CFR 814 Subpart H (Humanitarian Use Devices)
- Section 520(m) of the FD&C Act
- FDA Guidance: "Humanitarian Device Exemption (HDE) Program" (2019)

DISCLAIMER: This tool is for RESEARCH USE ONLY. HDE submissions require
review by qualified regulatory professionals. Do not submit to FDA
without independent professional verification.

Version: 1.0.0
Date: 2026-02-17
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ========================================================================
# CONSTANTS
# ========================================================================

HDE_PREVALENCE_THRESHOLD = 8000  # patients per year in US

HDE_SUBMISSION_SECTIONS = [
    {
        "number": "1",
        "title": "Administrative Information",
        "description": "Cover letter, table of contents, applicant info, device trade name",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(1)",
    },
    {
        "number": "2",
        "title": "Indications for Use / Intended Use",
        "description": "Statement of intended use for the HUD, disease or condition treated",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(2)",
    },
    {
        "number": "3",
        "title": "Device Description",
        "description": "Complete device description, materials, design, components, principles of operation",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(3)",
    },
    {
        "number": "4",
        "title": "Humanitarian Use Designation (HUD) Request",
        "description": "Documentation of HUD designation from OOPD, including designation number",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(2)",
    },
    {
        "number": "5",
        "title": "Prevalence Documentation",
        "description": "Evidence that disease/condition affects <8,000 individuals per year in the US",
        "required": True,
        "cfr_reference": "Section 520(m)(6)(A) FD&C Act",
    },
    {
        "number": "6",
        "title": "Probable Benefit",
        "description": "Data demonstrating probable benefit outweighs risk of injury or illness. Not required to demonstrate effectiveness.",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(4)",
    },
    {
        "number": "7",
        "title": "Safety Data",
        "description": "Safety data including bench testing, animal testing, and any available clinical data",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(4)",
    },
    {
        "number": "8",
        "title": "Alternatives Analysis",
        "description": "Description of alternative treatments/devices and why HDE is appropriate",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(5)",
    },
    {
        "number": "9",
        "title": "Manufacturing Information",
        "description": "Description of methods, facilities, and controls used in manufacturing",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(3)",
    },
    {
        "number": "10",
        "title": "Labeling",
        "description": "Proposed labeling including statement: 'Humanitarian Device. Authorized by Federal law for use in [condition]. The effectiveness of this device for this use has not been demonstrated.'",
        "required": True,
        "cfr_reference": "21 CFR 814.104(b)(6)",
    },
    {
        "number": "11",
        "title": "IRB Information",
        "description": "Documentation of IRB approval or exemption status at each facility",
        "required": True,
        "cfr_reference": "21 CFR 814.124",
    },
    {
        "number": "12",
        "title": "Informed Consent",
        "description": "Sample informed consent form for patient use",
        "required": True,
        "cfr_reference": "21 CFR 50",
    },
    {
        "number": "13",
        "title": "Risk Analysis",
        "description": "Comprehensive risk analysis (ISO 14971) with risk-benefit determination",
        "required": True,
        "cfr_reference": "ISO 14971",
    },
    {
        "number": "14",
        "title": "Biocompatibility",
        "description": "Biocompatibility testing per ISO 10993 (if applicable)",
        "required": False,
        "cfr_reference": "21 CFR 814.104(b)(4)",
    },
    {
        "number": "15",
        "title": "Software Documentation",
        "description": "Software documentation per FDA guidance (if applicable)",
        "required": False,
        "cfr_reference": "IEC 62304",
    },
    {
        "number": "16",
        "title": "Clinical Data Summary",
        "description": "Summary of any clinical investigations or literature references",
        "required": False,
        "cfr_reference": "21 CFR 814.104(b)(4)",
    },
]

# Probable benefit evidence categories
PROBABLE_BENEFIT_CATEGORIES = [
    {
        "id": "bench_testing",
        "name": "Bench Testing Data",
        "description": "Laboratory testing demonstrating device performance",
        "weight": 0.20,
        "examples": ["mechanical testing", "electrical safety", "durability", "sterility"],
    },
    {
        "id": "animal_studies",
        "name": "Animal Studies",
        "description": "Preclinical animal study data supporting probable benefit",
        "weight": 0.25,
        "examples": ["animal model selection rationale", "efficacy endpoints", "safety endpoints"],
    },
    {
        "id": "clinical_experience",
        "name": "Clinical Experience",
        "description": "Any available clinical data from compassionate use or investigations",
        "weight": 0.25,
        "examples": ["compassionate use data", "IDE study results", "case reports"],
    },
    {
        "id": "literature",
        "name": "Published Literature",
        "description": "Published scientific literature supporting probable benefit",
        "weight": 0.15,
        "examples": ["peer-reviewed publications", "systematic reviews", "case series"],
    },
    {
        "id": "alternative_analysis",
        "name": "Alternative Treatment Analysis",
        "description": "Comparison with existing treatments showing unmet need",
        "weight": 0.15,
        "examples": ["treatment gap analysis", "risk comparison with alternatives", "quality of life impact"],
    },
]

# IRB approval statuses
IRB_STATUS_VALUES = [
    "pending_submission",
    "submitted",
    "under_review",
    "approved",
    "conditionally_approved",
    "denied",
    "expired",
    "renewed",
    "suspended",
    "terminated",
]

# Annual distribution report fields per 21 CFR 814.126(b)
ANNUAL_REPORT_FIELDS = [
    "reporting_period_start",
    "reporting_period_end",
    "number_devices_distributed",
    "facilities_distributed_to",
    "adverse_events_summary",
    "device_failures_summary",
    "labeling_changes",
    "manufacturing_changes",
    "profit_status",  # Must be non-profit unless exemption
    "irb_approvals_status",
    "updated_prevalence_data",
]


# ========================================================================
# HDE SUBMISSION OUTLINE GENERATOR
# ========================================================================

class HDESubmissionOutline:
    """Generates structured HDE submission outlines per 21 CFR 814 Subpart H."""

    def __init__(self, device_info: Optional[Dict[str, Any]] = None):
        self.device_info = device_info or {}
        self.sections = HDE_SUBMISSION_SECTIONS.copy()
        self.gaps = []
        self.warnings = []

    def generate(self) -> Dict[str, Any]:
        """Generate a complete HDE submission outline with gap analysis."""
        outline = {
            "title": "Humanitarian Device Exemption (HDE) Submission Outline",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "regulatory_basis": {
                "statute": "Section 520(m) of the FD&C Act",
                "regulation": "21 CFR 814 Subpart H",
                "guidance": "Humanitarian Device Exemption (HDE) Program (2019)",
            },
            "device_info": self._build_device_summary(),
            "sections": self._build_sections(),
            "gaps": self.gaps,
            "warnings": self.warnings,
            "hde_specific_requirements": self._hde_requirements(),
            "disclaimer": (
                "RESEARCH USE ONLY. This outline is for planning purposes. "
                "HDE submissions require review by qualified regulatory professionals."
            ),
        }
        return outline

    def _build_device_summary(self) -> Dict[str, Any]:
        """Build device summary from provided info."""
        summary = {
            "device_name": self.device_info.get("device_name", "[TODO: Enter device name]"),
            "trade_name": self.device_info.get("trade_name", "[TODO: Enter trade name]"),
            "manufacturer": self.device_info.get("manufacturer", "[TODO: Enter manufacturer]"),
            "hud_designation_number": self.device_info.get("hud_designation_number", "[TODO: Enter HUD#]"),
            "disease_condition": self.device_info.get("disease_condition", "[TODO: Enter disease/condition]"),
            "intended_use": self.device_info.get("intended_use", "[TODO: Enter intended use]"),
            "device_class": self.device_info.get("device_class", "III"),
            "product_code": self.device_info.get("product_code", "[TODO: Enter product code]"),
        }

        # Check for missing critical fields
        for field, value in summary.items():
            if isinstance(value, str) and value.startswith("[TODO"):
                self.gaps.append({
                    "section": "Device Info",
                    "field": field,
                    "severity": "HIGH",
                    "message": f"Missing required field: {field}",
                })

        return summary

    def _build_sections(self) -> List[Dict[str, Any]]:
        """Build detailed section entries with status tracking."""
        sections = []
        has_software = self.device_info.get("has_software", False)
        has_biocompat = self.device_info.get("has_biocompat_concern", True)

        for section_def in self.sections:
            # Skip optional sections if not applicable
            if section_def["number"] == "15" and not has_software:
                continue
            if section_def["number"] == "14" and not has_biocompat:
                continue

            section = {
                "number": section_def["number"],
                "title": section_def["title"],
                "description": section_def["description"],
                "required": section_def["required"],
                "cfr_reference": section_def["cfr_reference"],
                "status": "not_started",
                "content_guidance": self._get_content_guidance(section_def["number"]),
                "evidence_needed": self._get_evidence_needed(section_def["number"]),
            }

            if section_def["required"]:
                self.gaps.append({
                    "section": section_def["title"],
                    "field": "content",
                    "severity": "CRITICAL" if section_def["number"] in ["4", "5", "6"] else "HIGH",
                    "message": f"Section {section_def['number']} content not yet prepared",
                })

            sections.append(section)

        return sections

    def _get_content_guidance(self, section_number: str) -> str:
        """Get specific content guidance for each section."""
        guidance_map = {
            "1": "Include cover letter addressed to CDRH, complete FDA Form 3514, table of contents",
            "2": "State intended use precisely; must match HUD designation scope",
            "3": "Include technical drawings, material specifications, principles of operation",
            "4": "Include HUD designation letter from OOPD (Office of Orphan Products Development)",
            "5": "Provide epidemiological data from peer-reviewed sources; CDC/NIH data preferred",
            "6": "Demonstrate probable benefit through available evidence (see Probable Benefit template)",
            "7": "Include all available safety data; bench, animal, clinical; organized by endpoint",
            "8": "Identify all available treatments; explain limitations; justify HDE pathway",
            "9": "Describe manufacturing per 21 CFR 820 (Quality System Regulation)",
            "10": "Must include required HDE labeling statement per 21 CFR 814.104(b)(6)",
            "11": "Document IRB approval status at each planned facility",
            "12": "Include sample informed consent; must mention device has not demonstrated effectiveness",
            "13": "Follow ISO 14971; include risk-benefit determination specific to HDE",
            "14": "ISO 10993-based biocompatibility evaluation per FDA guidance",
            "15": "IEC 62304 software lifecycle documentation; level of concern determination",
            "16": "Summarize any clinical evidence; literature review acceptable",
        }
        return guidance_map.get(section_number, "Consult 21 CFR 814.104 for requirements")

    def _get_evidence_needed(self, section_number: str) -> List[str]:
        """Get list of evidence items needed for each section."""
        evidence_map = {
            "1": ["FDA Form 3514", "Cover letter", "Table of contents", "Applicant information"],
            "2": ["Intended use statement", "Indications for use form"],
            "3": ["Device specifications", "Technical drawings", "Bill of materials"],
            "4": ["HUD designation letter", "OOPD correspondence"],
            "5": ["Prevalence data sources", "Epidemiological studies", "Registry data"],
            "6": ["Bench test reports", "Animal study reports", "Clinical case data", "Literature review"],
            "7": ["Safety test reports", "Biocompatibility data", "Electrical safety data"],
            "8": ["Alternative treatment survey", "Unmet need documentation"],
            "9": ["Manufacturing SOPs", "Quality system documentation", "Sterilization validation"],
            "10": ["Proposed labels", "IFU draft", "HDE required statement"],
            "11": ["IRB approval letters", "IRB protocols", "IRB membership rosters"],
            "12": ["Informed consent template", "Patient information sheet"],
            "13": ["Risk management file", "ISO 14971 report", "FMEA/FTA"],
            "14": ["ISO 10993 test reports", "Material characterization"],
            "15": ["Software requirements spec", "Architecture document", "V&V protocols"],
            "16": ["Literature search protocol", "Appraisal summaries"],
        }
        return evidence_map.get(section_number, [])

    def _hde_requirements(self) -> Dict[str, Any]:
        """Return HDE-specific requirements and notes."""
        return {
            "profit_restriction": (
                "HDEs are generally limited to cost recovery unless the device is "
                "intended for a condition that affects pediatric patients (under 22 years). "
                "Pediatric devices may be sold for profit per Section 520(m)(6)(A)(ii)."
            ),
            "irb_supervision": (
                "Use of an HDE-approved device requires IRB approval at each facility "
                "unless the device is used in an emergency or FDA grants an exemption. "
                "See 21 CFR 814.124."
            ),
            "annual_reporting": (
                "Annual reports are required per 21 CFR 814.126(b). "
                "Reports must include number of devices distributed, adverse events, "
                "facility IRB status, and profit/non-profit statement."
            ),
            "post_approval_requirements": [
                "Annual distribution report (21 CFR 814.126(b))",
                "Adverse event reporting (MDR - 21 CFR 803)",
                "IRB approval maintenance at each facility",
                "Labeling updates as needed",
                "Manufacturing compliance (21 CFR 820)",
            ],
            "hud_designation_first": (
                "HUD designation from OOPD must be obtained BEFORE submitting the HDE. "
                "The HUD request should include disease prevalence documentation."
            ),
        }

    def to_markdown(self) -> str:
        """Export outline as formatted markdown."""
        outline = self.generate()
        lines = [
            f"# {outline['title']}",
            "",
            f"Generated: {outline['generated_at']}",
            "",
            "## Regulatory Basis",
            f"- Statute: {outline['regulatory_basis']['statute']}",
            f"- Regulation: {outline['regulatory_basis']['regulation']}",
            f"- Guidance: {outline['regulatory_basis']['guidance']}",
            "",
            "## Device Information",
        ]

        for key, value in outline["device_info"].items():
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}**: {value}")

        lines.extend(["", "## Submission Sections", ""])

        for section in outline["sections"]:
            req_flag = " (REQUIRED)" if section["required"] else " (if applicable)"
            lines.append(f"### Section {section['number']}: {section['title']}{req_flag}")
            lines.append(f"*CFR Reference: {section['cfr_reference']}*")
            lines.append("")
            lines.append(f"**Description:** {section['description']}")
            lines.append("")
            lines.append(f"**Guidance:** {section['content_guidance']}")
            lines.append("")
            lines.append("**Evidence Needed:**")
            for item in section["evidence_needed"]:
                lines.append(f"- [ ] {item}")
            lines.append("")

        if outline["gaps"]:
            lines.extend(["## Identified Gaps", ""])
            for gap in outline["gaps"]:
                lines.append(f"- **[{gap['severity']}]** {gap['section']}: {gap['message']}")
            lines.append("")

        lines.extend([
            "## HDE-Specific Requirements",
            "",
            f"**Profit Restriction:** {outline['hde_specific_requirements']['profit_restriction']}",
            "",
            f"**IRB Supervision:** {outline['hde_specific_requirements']['irb_supervision']}",
            "",
            f"**Annual Reporting:** {outline['hde_specific_requirements']['annual_reporting']}",
            "",
            "---",
            f"*{outline['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# PREVALENCE VALIDATOR
# ========================================================================

class PrevalenceValidator:
    """
    Validates disease/condition prevalence data for HDE eligibility.

    The HDE pathway requires that the disease or condition affects
    fewer than 8,000 individuals per year in the United States.
    """

    THRESHOLD = HDE_PREVALENCE_THRESHOLD

    # Known rare disease data sources
    ACCEPTED_SOURCES = [
        "NIH/NCATS GARD (Genetic and Rare Diseases Information Center)",
        "CDC WONDER Database",
        "NORD (National Organization for Rare Disorders)",
        "Orphanet",
        "FDA Office of Orphan Products Development (OOPD)",
        "Peer-reviewed epidemiological studies",
        "National disease registries",
        "State health department data",
    ]

    def __init__(self):
        self.validation_results = []

    def validate_prevalence(
        self,
        condition_name: str,
        estimated_prevalence: int,
        data_sources: Optional[List[Dict[str, str]]] = None,
        prevalence_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Validate whether a disease/condition meets HDE prevalence threshold.

        Per 21 CFR 814 Subpart H, HDE is for diseases/conditions affecting
        fewer than 8,000 individuals per year in the United States.

        EDGE CASE: Exactly 8,000 patients is NOT eligible (strict inequality).
        The statute uses "fewer than 8,000" which means strictly less than.
        If your disease affects exactly 8,000 patients, HDE pathway is not
        available -- consider PMA or other pathways.

        EDGE CASE: Prevalence data older than 5 years may trigger FDA requests
        for updated data. Data older than 10 years is strongly discouraged.

        EDGE CASE: Zero or negative prevalence values are technically valid
        for the comparison but indicate data quality issues. Zero prevalence
        trivially satisfies the threshold but FDA will question the clinical
        need for a device with zero affected patients.

        Args:
            condition_name: Name of the disease or condition
            estimated_prevalence: Number of affected patients per year in US
            data_sources: List of dicts with 'name', 'url', 'date' keys
            prevalence_year: Year the prevalence data was collected

        Returns:
            Validation result dict with eligibility determination.
            Key field: 'eligible' is True if < 8,000 (strict inequality
            per regulation), False if >= 8,000.
        """
        current_year = datetime.now(timezone.utc).year
        data_sources = data_sources or []

        result = {
            "condition": condition_name,
            "estimated_prevalence": estimated_prevalence,
            "threshold": self.THRESHOLD,
            "eligible": estimated_prevalence < self.THRESHOLD,
            "margin": self.THRESHOLD - estimated_prevalence,
            "margin_percentage": round(
                ((self.THRESHOLD - estimated_prevalence) / self.THRESHOLD) * 100, 1
            ),
            "data_sources": data_sources,
            "data_quality_score": 0,
            "warnings": [],
            "recommendations": [],
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Quality scoring
        quality_score = 0

        # Source count scoring (max 30 points)
        source_count = len(data_sources)
        if source_count >= 3:
            quality_score += 30
        elif source_count >= 2:
            quality_score += 20
        elif source_count >= 1:
            quality_score += 10
        else:
            result["warnings"].append(
                "No data sources provided. FDA expects documented prevalence from credible sources."
            )
            result["recommendations"].append(
                "Provide at least 2-3 independent prevalence data sources."
            )

        # Data freshness scoring (max 20 points)
        if prevalence_year:
            years_old = current_year - prevalence_year
            if years_old <= 2:
                quality_score += 20
            elif years_old <= 5:
                quality_score += 15
                result["warnings"].append(
                    f"Prevalence data is {years_old} years old. Consider updating."
                )
            elif years_old <= 10:
                quality_score += 5
                result["warnings"].append(
                    f"Prevalence data is {years_old} years old. FDA may request updated data."
                )
            else:
                result["warnings"].append(
                    f"Prevalence data is {years_old} years old. Strongly recommend updating."
                )
                result["recommendations"].append(
                    "Update prevalence data to within the last 5 years."
                )
        else:
            result["warnings"].append("No prevalence year specified.")
            result["recommendations"].append(
                "Document the year of prevalence data collection."
            )

        # Source quality scoring (max 30 points)
        recognized_sources = 0
        for source in data_sources:
            source_name = source.get("name", "")
            for accepted in self.ACCEPTED_SOURCES:
                if any(
                    keyword in source_name.upper()
                    for keyword in accepted.upper().split()[:2]
                ):
                    recognized_sources += 1
                    break

        if recognized_sources >= 2:
            quality_score += 30
        elif recognized_sources >= 1:
            quality_score += 15
        else:
            if data_sources:
                result["recommendations"].append(
                    "Include data from recognized sources: " +
                    ", ".join(self.ACCEPTED_SOURCES[:4])
                )

        # Margin scoring (max 20 points)
        if result["eligible"]:
            if result["margin_percentage"] > 50:
                quality_score += 20
            elif result["margin_percentage"] > 25:
                quality_score += 15
            elif result["margin_percentage"] > 10:
                quality_score += 10
            else:
                quality_score += 5
                result["warnings"].append(
                    f"Prevalence is close to threshold (margin: {result['margin']} patients, "
                    f"{result['margin_percentage']}%). FDA may scrutinize closely."
                )
                result["recommendations"].append(
                    "Prepare additional prevalence documentation to justify eligibility."
                )
        else:
            result["warnings"].append(
                f"INELIGIBLE: Estimated prevalence ({estimated_prevalence:,}) exceeds "
                f"HDE threshold ({self.THRESHOLD:,}). Consider alternative pathway."
            )
            result["recommendations"].append(
                "Consider PMA or 510(k) pathway instead, or refine condition definition."
            )

        result["data_quality_score"] = min(quality_score, 100)

        self.validation_results.append(result)
        return result

    def get_source_recommendations(self, condition_name: str) -> List[Dict[str, str]]:
        """Get recommended prevalence data sources for a given condition."""
        recommendations = []
        for source in self.ACCEPTED_SOURCES:
            recommendations.append({
                "source": source,
                "action": f"Search for '{condition_name}' prevalence data",
                "priority": "HIGH" if "NIH" in source or "CDC" in source else "MEDIUM",
            })
        return recommendations


# ========================================================================
# PROBABLE BENEFIT ANALYZER
# ========================================================================

class ProbableBenefitAnalyzer:
    """
    Generates and evaluates probable benefit analysis for HDE submissions.

    Unlike PMA, HDE does not require demonstration of effectiveness.
    Instead, the applicant must show probable benefit that outweighs
    the risk of injury or illness from device use.
    """

    def __init__(self):
        self.categories = PROBABLE_BENEFIT_CATEGORIES.copy()

    def generate_template(
        self,
        device_name: str,
        condition: str,
        evidence_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a probable benefit analysis template.

        Args:
            device_name: Name of the device
            condition: Disease/condition being treated
            evidence_items: Optional list of evidence items with category and description

        Returns:
            Structured probable benefit template
        """
        evidence_items = evidence_items or []

        template = {
            "title": f"Probable Benefit Analysis: {device_name}",
            "device_name": device_name,
            "condition": condition,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "regulatory_standard": (
                "Probable benefit standard per Section 520(m) of the FD&C Act. "
                "The probable benefit must outweigh the risk of injury or illness "
                "from use of the device, taking into account the probable risks and "
                "benefits of currently available devices or alternative forms of treatment."
            ),
            "evidence_categories": [],
            "risk_benefit_determination": self._build_risk_benefit_template(device_name, condition),
            "overall_score": 0,
            "gaps": [],
            "disclaimer": (
                "RESEARCH USE ONLY. Probable benefit analysis requires review "
                "by qualified clinical and regulatory professionals."
            ),
        }

        # Build evidence category assessments
        total_score = 0
        for category in self.categories:
            cat_evidence = [
                e for e in evidence_items
                if e.get("category") == category["id"]
            ]

            category_entry = {
                "id": category["id"],
                "name": category["name"],
                "description": category["description"],
                "weight": category["weight"],
                "examples": category["examples"],
                "evidence_items": cat_evidence,
                "has_evidence": len(cat_evidence) > 0,
                "strength": self._assess_evidence_strength(cat_evidence),
                "score": 0,
            }

            # Score based on evidence strength
            strength_scores = {
                "strong": 100,
                "moderate": 70,
                "weak": 40,
                "none": 0,
            }
            raw_score = strength_scores.get(category_entry["strength"], 0)
            category_entry["score"] = round(raw_score * category["weight"], 1)
            total_score += category_entry["score"]

            if not cat_evidence:
                template["gaps"].append({
                    "category": category["name"],
                    "severity": "HIGH" if category["weight"] >= 0.20 else "MEDIUM",
                    "message": f"No evidence provided for {category['name']}",
                    "recommendation": f"Prepare {', '.join(category['examples'][:2])}",
                })

            template["evidence_categories"].append(category_entry)

        template["overall_score"] = round(total_score, 1)

        return template

    def _assess_evidence_strength(self, evidence_items: List[Dict[str, Any]]) -> str:
        """Assess strength of evidence items."""
        if not evidence_items:
            return "none"

        # Simple heuristic based on count and quality indicators
        count = len(evidence_items)
        has_published = any(
            e.get("published", False) or e.get("peer_reviewed", False)
            for e in evidence_items
        )
        has_quantitative = any(
            e.get("quantitative", False) or e.get("has_statistics", False)
            for e in evidence_items
        )

        if count >= 3 and (has_published or has_quantitative):
            return "strong"
        elif count >= 2 or has_published:
            return "moderate"
        else:
            return "weak"

    def _build_risk_benefit_template(
        self, device_name: str, condition: str
    ) -> Dict[str, Any]:
        """Build risk-benefit determination template."""
        return {
            "section_title": "Risk-Benefit Determination",
            "description": (
                f"Assessment of whether the probable benefit of {device_name} "
                f"for treatment of {condition} outweighs the risk of injury or illness."
            ),
            "probable_benefits": [
                {"benefit": "[TODO: Describe primary clinical benefit]", "evidence_basis": ""},
                {"benefit": "[TODO: Describe secondary benefit]", "evidence_basis": ""},
            ],
            "known_risks": [
                {"risk": "[TODO: Describe primary risk]", "severity": "", "mitigation": ""},
                {"risk": "[TODO: Describe secondary risk]", "severity": "", "mitigation": ""},
            ],
            "alternative_treatments": [
                {
                    "treatment": "[TODO: Describe alternative]",
                    "limitations": "",
                    "comparison_to_device": "",
                },
            ],
            "determination": "[TODO: State whether probable benefit outweighs risk]",
            "determination_rationale": "[TODO: Provide rationale]",
        }

    def to_markdown(self, template: Dict[str, Any]) -> str:
        """Export probable benefit template as markdown."""
        lines = [
            f"# {template['title']}",
            "",
            f"**Condition:** {template['condition']}",
            f"**Generated:** {template['generated_at']}",
            f"**Overall Evidence Score:** {template['overall_score']}/100",
            "",
            "## Regulatory Standard",
            template["regulatory_standard"],
            "",
            "## Evidence Categories",
            "",
        ]

        for cat in template["evidence_categories"]:
            strength_indicator = {
                "strong": "STRONG",
                "moderate": "MODERATE",
                "weak": "WEAK",
                "none": "NONE",
            }.get(cat["strength"], "UNKNOWN")

            lines.append(f"### {cat['name']} (Weight: {cat['weight']*100:.0f}%)")
            lines.append(f"**Strength:** {strength_indicator} | **Score:** {cat['score']}")
            lines.append(f"*{cat['description']}*")
            lines.append("")

            if cat["evidence_items"]:
                for item in cat["evidence_items"]:
                    lines.append(f"- {item.get('description', 'Evidence item')}")
            else:
                lines.append("- [ ] No evidence provided yet")
                lines.append(f"  - Suggested: {', '.join(cat['examples'])}")
            lines.append("")

        # Risk-benefit section
        rb = template["risk_benefit_determination"]
        lines.extend([
            f"## {rb['section_title']}",
            rb["description"],
            "",
            "### Probable Benefits",
        ])
        for b in rb["probable_benefits"]:
            lines.append(f"1. {b['benefit']}")
        lines.extend(["", "### Known Risks"])
        for r in rb["known_risks"]:
            lines.append(f"1. {r['risk']}")
        lines.extend(["", "### Alternative Treatments"])
        for a in rb["alternative_treatments"]:
            lines.append(f"1. {a['treatment']}")

        lines.extend([
            "",
            f"### Determination: {rb['determination']}",
            f"Rationale: {rb['determination_rationale']}",
            "",
            "## Gaps",
        ])
        for gap in template["gaps"]:
            lines.append(f"- **[{gap['severity']}]** {gap['category']}: {gap['message']}")

        lines.extend([
            "",
            "---",
            f"*{template['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# IRB APPROVAL TRACKER
# ========================================================================

class IRBApprovalTracker:
    """
    Tracks IRB approval status across multiple facilities for HDE devices.

    Per 21 CFR 814.124, an HDE-approved device may only be used at a
    facility after the local IRB has approved its use.
    """

    def __init__(self):
        self.facilities = []

    def add_facility(
        self,
        facility_name: str,
        facility_id: Optional[str] = None,
        irb_name: Optional[str] = None,
        status: str = "pending_submission",
        approval_date: Optional[str] = None,
        expiration_date: Optional[str] = None,
        protocol_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add or update a facility IRB record.

        Args:
            facility_name: Name of the healthcare facility
            facility_id: Facility identifier
            irb_name: Name of the reviewing IRB
            status: One of IRB_STATUS_VALUES
            approval_date: Date of IRB approval (ISO format)
            expiration_date: Date of IRB approval expiration (ISO format)
            protocol_number: IRB protocol number
            notes: Additional notes

        Returns:
            The facility record
        """
        if status not in IRB_STATUS_VALUES:
            raise ValueError(
                f"Invalid status '{status}'. Must be one of: {', '.join(IRB_STATUS_VALUES)}"
            )

        record = {
            "facility_name": facility_name,
            "facility_id": facility_id or f"FAC-{len(self.facilities) + 1:04d}",
            "irb_name": irb_name or "[TODO: Enter IRB name]",
            "status": status,
            "approval_date": approval_date,
            "expiration_date": expiration_date,
            "protocol_number": protocol_number,
            "notes": notes or "",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "is_active": status in ("approved", "conditionally_approved", "renewed"),
            "needs_renewal": False,
        }

        # Check expiration
        if expiration_date:
            try:
                exp_dt = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                days_until_expiry = (exp_dt - now).days

                if days_until_expiry < 0:
                    record["status"] = "expired"
                    record["is_active"] = False
                    record["needs_renewal"] = True
                elif days_until_expiry < 90:
                    record["needs_renewal"] = True
            except (ValueError, TypeError):
                pass

        # Check for duplicate facility
        existing_idx = None
        for i, f in enumerate(self.facilities):
            if f["facility_name"] == facility_name:
                existing_idx = i
                break

        if existing_idx is not None:
            self.facilities[existing_idx] = record
        else:
            self.facilities.append(record)

        return record

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all facility IRB statuses."""
        total = len(self.facilities)
        active = sum(1 for f in self.facilities if f["is_active"])
        pending = sum(1 for f in self.facilities if f["status"] in ("pending_submission", "submitted", "under_review"))
        expired = sum(1 for f in self.facilities if f["status"] == "expired")
        needs_renewal = sum(1 for f in self.facilities if f["needs_renewal"])

        return {
            "total_facilities": total,
            "active_approvals": active,
            "pending_review": pending,
            "expired": expired,
            "needs_renewal": needs_renewal,
            "compliance_rate": round((active / total * 100), 1) if total > 0 else 0,
            "facilities": self.facilities,
            "alerts": self._get_alerts(),
        }

    def _get_alerts(self) -> List[Dict[str, str]]:
        """Generate alerts for IRB issues."""
        alerts = []

        for facility in self.facilities:
            if facility["status"] == "expired":
                alerts.append({
                    "level": "CRITICAL",
                    "facility": facility["facility_name"],
                    "message": "IRB approval has expired. Device use must cease until renewed.",
                })
            elif facility["needs_renewal"]:
                alerts.append({
                    "level": "WARNING",
                    "facility": facility["facility_name"],
                    "message": f"IRB approval expiring soon. Submit renewal promptly.",
                })
            elif facility["status"] == "denied":
                alerts.append({
                    "level": "HIGH",
                    "facility": facility["facility_name"],
                    "message": "IRB approval denied. Device cannot be used at this facility.",
                })
            elif facility["status"] == "suspended":
                alerts.append({
                    "level": "CRITICAL",
                    "facility": facility["facility_name"],
                    "message": "IRB approval suspended. Cease device use pending resolution.",
                })

        return alerts

    def to_markdown(self) -> str:
        """Export IRB tracker as markdown report."""
        summary = self.get_summary()

        lines = [
            "# IRB Approval Tracker - HDE Device",
            "",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Summary",
            f"- Total Facilities: {summary['total_facilities']}",
            f"- Active Approvals: {summary['active_approvals']}",
            f"- Pending Review: {summary['pending_review']}",
            f"- Expired: {summary['expired']}",
            f"- Needs Renewal: {summary['needs_renewal']}",
            f"- Compliance Rate: {summary['compliance_rate']}%",
            "",
        ]

        if summary["alerts"]:
            lines.append("## Alerts")
            for alert in summary["alerts"]:
                lines.append(f"- **[{alert['level']}]** {alert['facility']}: {alert['message']}")
            lines.append("")

        lines.extend(["## Facility Details", ""])
        lines.append("| Facility | IRB | Status | Approval Date | Expiration | Protocol |")
        lines.append("|----------|-----|--------|--------------|------------|----------|")

        for f in self.facilities:
            status_icon = {
                "approved": "APPROVED",
                "conditionally_approved": "CONDITIONAL",
                "expired": "EXPIRED",
                "denied": "DENIED",
                "pending_submission": "PENDING",
                "submitted": "SUBMITTED",
                "under_review": "REVIEWING",
                "renewed": "RENEWED",
                "suspended": "SUSPENDED",
                "terminated": "TERMINATED",
            }.get(f["status"], f["status"])

            lines.append(
                f"| {f['facility_name']} | {f['irb_name']} | {status_icon} | "
                f"{f.get('approval_date', 'N/A')} | {f.get('expiration_date', 'N/A')} | "
                f"{f.get('protocol_number', 'N/A')} |"
            )

        lines.extend([
            "",
            "## Regulatory Requirement",
            "",
            "Per 21 CFR 814.124, use of an HDE-approved device requires IRB approval ",
            "at each facility where the device is used. The IRB must approve the use ",
            "before the device can be used at that facility.",
            "",
            "---",
            "*RESEARCH USE ONLY. IRB compliance tracking requires verification by qualified professionals.*",
        ])

        return "\n".join(lines)


# ========================================================================
# ANNUAL DISTRIBUTION REPORT GENERATOR
# ========================================================================

class AnnualDistributionReport:
    """
    Generates annual distribution reports per 21 CFR 814.126(b).

    HDE holders must submit annual reports to FDA containing:
    - Number of devices distributed
    - Facilities where distributed
    - Summary of adverse events
    - Profit status declaration
    - Updated prevalence data
    """

    def __init__(
        self,
        hde_number: str,
        device_name: str,
        holder_name: str,
    ):
        self.hde_number = hde_number
        self.device_name = device_name
        self.holder_name = holder_name
        self.report_data = {}

    def generate_report(
        self,
        period_start: str,
        period_end: str,
        devices_distributed: int = 0,
        facilities: Optional[List[Dict[str, str]]] = None,
        adverse_events: Optional[List[Dict[str, Any]]] = None,
        device_failures: Optional[List[Dict[str, Any]]] = None,
        labeling_changes: Optional[List[str]] = None,
        manufacturing_changes: Optional[List[str]] = None,
        is_nonprofit: bool = True,
        updated_prevalence: Optional[int] = None,
        irb_tracker: Optional[IRBApprovalTracker] = None,
    ) -> Dict[str, Any]:
        """
        Generate annual distribution report.

        Args:
            period_start: Reporting period start (ISO date)
            period_end: Reporting period end (ISO date)
            devices_distributed: Number of devices distributed during period
            facilities: List of facilities receiving devices
            adverse_events: List of adverse events during period
            device_failures: List of device failures during period
            labeling_changes: List of labeling changes made
            manufacturing_changes: List of manufacturing changes made
            is_nonprofit: Whether distribution is at cost recovery only
            updated_prevalence: Updated prevalence data if available
            irb_tracker: IRB tracker instance for facility status

        Returns:
            Complete annual distribution report
        """
        facilities = facilities or []
        adverse_events = adverse_events or []
        device_failures = device_failures or []
        labeling_changes = labeling_changes or []
        manufacturing_changes = manufacturing_changes or []

        self.report_data = {
            "title": f"Annual Distribution Report - {self.hde_number}",
            "hde_number": self.hde_number,
            "device_name": self.device_name,
            "holder_name": self.holder_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cfr_reference": "21 CFR 814.126(b)",
            "reporting_period": {
                "start": period_start,
                "end": period_end,
            },
            "distribution_summary": {
                "total_devices_distributed": devices_distributed,
                "total_facilities": len(facilities),
                "facilities": facilities,
            },
            "safety_summary": {
                "total_adverse_events": len(adverse_events),
                "adverse_events": adverse_events,
                "total_device_failures": len(device_failures),
                "device_failures": device_failures,
                "mdr_reports_filed": sum(
                    1 for e in adverse_events if e.get("mdr_filed", False)
                ),
            },
            "changes": {
                "labeling_changes": labeling_changes,
                "manufacturing_changes": manufacturing_changes,
                "has_changes": bool(labeling_changes or manufacturing_changes),
            },
            "profit_status": {
                "is_nonprofit": is_nonprofit,
                "declaration": (
                    "Device distributed on a cost-recovery basis only."
                    if is_nonprofit
                    else "Device distributed for profit under pediatric exemption per Section 520(m)(6)(A)(ii)."
                ),
            },
            "prevalence_update": {
                "updated_prevalence": updated_prevalence,
                "still_eligible": (
                    updated_prevalence < HDE_PREVALENCE_THRESHOLD
                    if updated_prevalence is not None
                    else None
                ),
            },
            "irb_status": None,
            "completeness_score": 0,
            "missing_sections": [],
            "disclaimer": (
                "RESEARCH USE ONLY. Annual distribution reports require review "
                "by qualified regulatory professionals before FDA submission."
            ),
        }

        # Add IRB status if tracker provided
        if irb_tracker:
            self.report_data["irb_status"] = irb_tracker.get_summary()

        # Calculate completeness
        self._calculate_completeness()

        return self.report_data

    def _calculate_completeness(self):
        """Calculate report completeness score."""
        checks = [
            ("distribution_data", self.report_data["distribution_summary"]["total_devices_distributed"] >= 0),
            ("facilities_listed", len(self.report_data["distribution_summary"]["facilities"]) > 0),
            ("adverse_events_reviewed", True),  # Reviewed even if zero events
            ("profit_status_declared", True),  # Always set
            ("irb_status_tracked", self.report_data["irb_status"] is not None),
            ("prevalence_updated", self.report_data["prevalence_update"]["updated_prevalence"] is not None),
            ("changes_documented", True),  # Documented even if no changes
        ]

        passed = sum(1 for _, result in checks if result)
        self.report_data["completeness_score"] = round((passed / len(checks)) * 100, 1)

        for name, result in checks:
            if not result:
                self.report_data["missing_sections"].append(name)

    def to_markdown(self) -> str:
        """Export report as markdown."""
        r = self.report_data
        lines = [
            f"# {r['title']}",
            "",
            f"**HDE Number:** {r['hde_number']}",
            f"**Device:** {r['device_name']}",
            f"**Holder:** {r['holder_name']}",
            f"**Reporting Period:** {r['reporting_period']['start']} to {r['reporting_period']['end']}",
            f"**Generated:** {r['generated_at']}",
            f"**CFR Reference:** {r['cfr_reference']}",
            f"**Completeness:** {r['completeness_score']}%",
            "",
            "## Distribution Summary",
            f"- Devices Distributed: {r['distribution_summary']['total_devices_distributed']}",
            f"- Facilities: {r['distribution_summary']['total_facilities']}",
            "",
        ]

        if r["distribution_summary"]["facilities"]:
            lines.append("### Facilities")
            for fac in r["distribution_summary"]["facilities"]:
                lines.append(f"- {fac.get('name', 'Unknown')} ({fac.get('location', 'Unknown')})")
            lines.append("")

        lines.extend([
            "## Safety Summary",
            f"- Total Adverse Events: {r['safety_summary']['total_adverse_events']}",
            f"- Device Failures: {r['safety_summary']['total_device_failures']}",
            f"- MDR Reports Filed: {r['safety_summary']['mdr_reports_filed']}",
            "",
            "## Profit Status",
            r["profit_status"]["declaration"],
            "",
            "## Prevalence Update",
        ])

        if r["prevalence_update"]["updated_prevalence"] is not None:
            prev = r["prevalence_update"]["updated_prevalence"]
            eligible = r["prevalence_update"]["still_eligible"]
            status = "ELIGIBLE" if eligible else "AT RISK - EXCEEDS THRESHOLD"
            lines.append(f"- Updated Prevalence: {prev:,} patients/year ({status})")
        else:
            lines.append("- [TODO: Provide updated prevalence data]")

        lines.extend([
            "",
            "## Changes During Period",
        ])
        if r["changes"]["labeling_changes"]:
            lines.append("### Labeling Changes")
            for change in r["changes"]["labeling_changes"]:
                lines.append(f"- {change}")
        if r["changes"]["manufacturing_changes"]:
            lines.append("### Manufacturing Changes")
            for change in r["changes"]["manufacturing_changes"]:
                lines.append(f"- {change}")
        if not r["changes"]["has_changes"]:
            lines.append("No labeling or manufacturing changes during this period.")

        if r["missing_sections"]:
            lines.extend(["", "## Missing Sections"])
            for section in r["missing_sections"]:
                lines.append(f"- [ ] {section.replace('_', ' ').title()}")

        lines.extend([
            "",
            "---",
            f"*{r['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# CONVENIENCE FUNCTIONS
# ========================================================================

def generate_hde_outline(device_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate an HDE submission outline."""
    generator = HDESubmissionOutline(device_info)
    return generator.generate()


def validate_hde_prevalence(
    condition: str,
    prevalence: int,
    sources: Optional[List[Dict[str, str]]] = None,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Validate disease prevalence for HDE eligibility.

    Per 21 CFR 814 Subpart H, HDE is for diseases/conditions affecting
    fewer than 8,000 individuals per year in the United States.

    EDGE CASE: Exactly 8,000 patients is NOT eligible (strict inequality).
    If your disease affects exactly 8,000 patients, HDE pathway is not
    available -- consider PMA or other pathways.

    Args:
        condition: Name of the disease or condition
        prevalence: Number of affected patients per year in US
        sources: List of dicts with 'name', 'url', 'date' keys
        year: Year the prevalence data was collected

    Returns:
        Validation result dict. Key field: 'eligible' is True if
        prevalence < 8,000 (strict inequality), False if >= 8,000.
    """
    validator = PrevalenceValidator()
    return validator.validate_prevalence(condition, prevalence, sources, year)


def generate_probable_benefit_template(
    device_name: str,
    condition: str,
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generate a probable benefit analysis template."""
    analyzer = ProbableBenefitAnalyzer()
    return analyzer.generate_template(device_name, condition, evidence)
