#!/usr/bin/env python3
"""
FDA De Novo Classification Request Support Module
==================================================

Provides core functionality for De Novo classification requests including:
- De Novo submission outline generator (21 CFR 860.260)
- Special controls proposal template
- Risk assessment framework for novel devices
- Benefit-risk analysis tool
- De Novo vs 510(k) decision tree
- Predicate search documentation

Regulatory basis:
- 21 CFR 860.260 (De Novo Classification Process)
- Section 513(f)(2) of the FD&C Act
- FDA Guidance: "De Novo Classification Process (Evaluation of Automatic Class III Designation)" (2021)
- FDA Guidance: "Acceptance Review for De Novo Classification Requests" (2023)

DISCLAIMER: This tool is for RESEARCH USE ONLY. De Novo submissions require
review by qualified regulatory professionals. Do not submit to FDA
without independent professional verification.

Version: 1.0.0
Date: 2026-02-17
"""

from typing import Any, Dict, List, Optional


# ========================================================================
# CONSTANTS
# ========================================================================

# De Novo submission sections per FDA guidance
DE_NOVO_SUBMISSION_SECTIONS = [
    {
        "number": "1",
        "title": "Administrative Information",
        "description": "Cover letter, TOC, applicant info, device name, establishment registration",
        "required": True,
        "cfr_reference": "21 CFR 860.260",
        "acceptance_criteria": "Complete administrative package with all required forms",
    },
    {
        "number": "2",
        "title": "Device Description",
        "description": "Complete technical description including principles of operation, specifications, materials, components",
        "required": True,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Sufficient detail to understand device technology and function",
    },
    {
        "number": "3",
        "title": "Intended Use / Indications for Use",
        "description": "Precise statement of intended use and specific indications for use",
        "required": True,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Clear, specific IFU statement consistent with evidence",
    },
    {
        "number": "4",
        "title": "Classification Recommendation",
        "description": "Recommended classification (Class I or II) with rationale, proposed product code, regulation number",
        "required": True,
        "cfr_reference": "Section 513(f)(2) FD&C Act",
        "acceptance_criteria": "Clear classification recommendation with regulatory justification",
    },
    {
        "number": "5",
        "title": "Predicate Search and Classification Assessment",
        "description": "Documentation of predicate search, explanation of why no predicate exists or why SE cannot be established",
        "required": True,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Thorough predicate search documented with clear rationale",
    },
    {
        "number": "6",
        "title": "Risks and Mitigations",
        "description": "Comprehensive risk identification and mitigation strategy for each identified risk",
        "required": True,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Complete risk-mitigation table with all identified risks addressed",
    },
    {
        "number": "7",
        "title": "Proposed Special Controls",
        "description": "Specific special controls proposal that, combined with general controls, provide reasonable assurance of safety and effectiveness",
        "required": True,
        "cfr_reference": "Section 513(a)(1)(B) FD&C Act",
        "acceptance_criteria": "Specific, enforceable special controls addressing all identified risks",
    },
    {
        "number": "8",
        "title": "Performance Testing - Non-Clinical",
        "description": "Bench testing, biocompatibility, electrical safety, EMC, sterility validation, etc.",
        "required": True,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Testing protocols and results for all relevant performance characteristics",
    },
    {
        "number": "9",
        "title": "Performance Testing - Clinical",
        "description": "Clinical study results, if applicable, supporting safety and effectiveness",
        "required": False,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Clinical evidence supporting intended use (if required)",
    },
    {
        "number": "10",
        "title": "Benefit-Risk Assessment",
        "description": "Structured benefit-risk analysis demonstrating favorable benefit-risk profile",
        "required": True,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Comprehensive benefit-risk analysis with clear favorable determination",
    },
    {
        "number": "11",
        "title": "Labeling",
        "description": "Proposed labeling including instructions for use, warnings, contraindications",
        "required": True,
        "cfr_reference": "21 CFR 860.260(a)",
        "acceptance_criteria": "Complete proposed labeling consistent with intended use",
    },
    {
        "number": "12",
        "title": "Software Documentation",
        "description": "Software level of concern, SRS, architecture, V&V, cybersecurity (if applicable)",
        "required": False,
        "cfr_reference": "IEC 62304, FDA Cybersecurity Guidance",
        "acceptance_criteria": "Complete software documentation per level of concern",
    },
    {
        "number": "13",
        "title": "Biocompatibility",
        "description": "Biocompatibility evaluation per ISO 10993 (if applicable)",
        "required": False,
        "cfr_reference": "ISO 10993-1",
        "acceptance_criteria": "Complete biocompatibility evaluation appropriate to device contact",
    },
    {
        "number": "14",
        "title": "Electrical Safety and EMC",
        "description": "Electrical safety (IEC 60601-1) and EMC (IEC 60601-1-2) testing (if applicable)",
        "required": False,
        "cfr_reference": "IEC 60601-1, IEC 60601-1-2",
        "acceptance_criteria": "Complete electrical safety and EMC test reports",
    },
    {
        "number": "15",
        "title": "Human Factors / Usability",
        "description": "Human factors engineering evaluation and usability study results",
        "required": False,
        "cfr_reference": "IEC 62366-1, FDA HFE Guidance",
        "acceptance_criteria": "HFE evaluation with critical task analysis and validation results",
    },
    {
        "number": "16",
        "title": "Sterilization Validation",
        "description": "Sterilization validation and shelf-life testing (if applicable)",
        "required": False,
        "cfr_reference": "ISO 11135, ISO 11137, ISO 11607",
        "acceptance_criteria": "Complete sterilization validation with sterility assurance",
    },
]

# Risk categories for De Novo devices
RISK_CATEGORIES = {
    "device_related": {
        "name": "Device-Related Risks",
        "description": "Risks arising from the device design, materials, and operation",
        "subcategories": [
            "mechanical_failure",
            "material_biocompatibility",
            "electrical_hazard",
            "software_malfunction",
            "sterility_failure",
            "shelf_life_degradation",
            "electromagnetic_interference",
        ],
    },
    "use_related": {
        "name": "Use-Related Risks",
        "description": "Risks arising from user interaction with the device",
        "subcategories": [
            "use_error",
            "misuse",
            "training_inadequacy",
            "labeling_confusion",
            "incorrect_patient_selection",
        ],
    },
    "clinical": {
        "name": "Clinical Risks",
        "description": "Risks to patient health from device use",
        "subcategories": [
            "adverse_tissue_reaction",
            "infection",
            "treatment_failure",
            "delayed_diagnosis",
            "unnecessary_treatment",
        ],
    },
    "indirect": {
        "name": "Indirect Risks",
        "description": "Risks from consequences of device output or results",
        "subcategories": [
            "false_positive_result",
            "false_negative_result",
            "delayed_treatment",
            "incorrect_treatment_decision",
        ],
    },
}

# Special controls categories
SPECIAL_CONTROLS_CATEGORIES = [
    {
        "id": "performance_standards",
        "name": "Performance Standards",
        "description": "Mandatory performance criteria and testing standards",
        "examples": [
            "Consensus standards (ISO, IEC, ASTM)",
            "Performance benchmarks and acceptance criteria",
            "Specific test methodologies",
        ],
    },
    {
        "id": "postmarket_surveillance",
        "name": "Postmarket Surveillance",
        "description": "Requirements for monitoring device performance after marketing",
        "examples": [
            "Clinical follow-up studies (522 studies)",
            "Registry participation requirements",
            "Periodic reporting requirements",
        ],
    },
    {
        "id": "patient_registries",
        "name": "Patient Registries",
        "description": "Requirements for maintaining patient/device registries",
        "examples": [
            "Mandatory patient tracking",
            "Long-term outcome data collection",
            "Adverse event monitoring through registry",
        ],
    },
    {
        "id": "labeling_requirements",
        "name": "Special Labeling Requirements",
        "description": "Specific labeling content, warnings, or restrictions",
        "examples": [
            "Specific warning statements",
            "Restriction to prescription use",
            "Training requirements in labeling",
            "Patient information leaflet requirements",
        ],
    },
    {
        "id": "premarket_testing",
        "name": "Premarket Testing Requirements",
        "description": "Required testing that must be performed before marketing",
        "examples": [
            "Specific performance testing protocols",
            "Clinical data requirements",
            "Biocompatibility testing per FDA guidance",
        ],
    },
    {
        "id": "design_restrictions",
        "name": "Design Restrictions",
        "description": "Constraints on device design, materials, or configuration",
        "examples": [
            "Material restrictions",
            "Maximum/minimum device parameters",
            "Required safety features",
        ],
    },
]

# Decision tree factors for De Novo vs 510(k)
DECISION_FACTORS = {
    "predicate_exists": {
        "question": "Does a legally marketed predicate device exist?",
        "weight": 0.35,
        "510k_if": True,
        "de_novo_if": False,
    },
    "same_intended_use": {
        "question": "Is the intended use the same as an existing cleared/approved device?",
        "weight": 0.20,
        "510k_if": True,
        "de_novo_if": False,
    },
    "novel_technology": {
        "question": "Does the device use novel technology not present in marketed devices?",
        "weight": 0.15,
        "510k_if": False,
        "de_novo_if": True,
    },
    "different_questions_of_safety": {
        "question": "Does the device raise different questions of safety/effectiveness vs predicates?",
        "weight": 0.15,
        "510k_if": False,
        "de_novo_if": True,
    },
    "low_to_moderate_risk": {
        "question": "Is the device low-to-moderate risk (not requiring PMA-level evidence)?",
        "weight": 0.10,
        "510k_if": True,
        "de_novo_if": True,
    },
    "general_special_controls_sufficient": {
        "question": "Can general and special controls provide reasonable assurance of safety and effectiveness?",
        "weight": 0.05,
        "510k_if": True,
        "de_novo_if": True,
    },
}


# ========================================================================
# DE NOVO SUBMISSION OUTLINE GENERATOR
# ========================================================================

class DeNovoSubmissionOutline:
    """Generates structured De Novo submission outlines per 21 CFR 860.260."""

    def __init__(self, device_info: Optional[Dict[str, Any]] = None):
        self.device_info = device_info or {}
        self.sections = DE_NOVO_SUBMISSION_SECTIONS.copy()
        self.gaps = []
        self.warnings = []

    def generate(self) -> Dict[str, Any]:
        """Generate a complete De Novo submission outline with gap analysis."""
        outline = {
            "title": "De Novo Classification Request Outline",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "regulatory_basis": {
                "statute": "Section 513(f)(2) of the FD&C Act",
                "regulation": "21 CFR 860.260",
                "guidance": "De Novo Classification Process (Evaluation of Automatic Class III Designation) (2021)",
                "acceptance_guidance": "Acceptance Review for De Novo Classification Requests (2023)",
            },
            "device_info": self._build_device_summary(),
            "classification_recommendation": self._build_classification_recommendation(),
            "sections": self._build_sections(),
            "gaps": self.gaps,
            "warnings": self.warnings,
            "de_novo_specific_notes": self._de_novo_notes(),
            "user_fee_info": {
                "de_novo_fee_fy2025": 130682,
                "small_business_waiver": "Available for qualifying small businesses",
                "fee_exemption": "First De Novo from a small business may be exempt",
            },
            "timeline_estimate": {
                "fda_review_goal": "150 review days (MDUFA performance goal)",
                "typical_total": "12-18 months from submission to decision",
                "refuse_to_accept_review": "15 business days",
                "substantive_review": "150 review days",
            },
            "disclaimer": (
                "RESEARCH USE ONLY. This outline is for planning purposes. "
                "De Novo submissions require review by qualified regulatory professionals."
            ),
        }
        return outline

    def _build_device_summary(self) -> Dict[str, Any]:
        """Build device summary from provided info."""
        summary = {
            "device_name": self.device_info.get("device_name", "[TODO: Enter device name]"),
            "trade_name": self.device_info.get("trade_name", "[TODO: Enter trade name]"),
            "manufacturer": self.device_info.get("manufacturer", "[TODO: Enter manufacturer]"),
            "intended_use": self.device_info.get("intended_use", "[TODO: Enter intended use]"),
            "indications_for_use": self.device_info.get("indications_for_use", "[TODO: Enter IFU]"),
            "technology_description": self.device_info.get("technology_description", "[TODO: Describe technology]"),
            "proposed_class": self.device_info.get("proposed_class", "II"),
            "proposed_product_code": self.device_info.get("proposed_product_code", "[TODO: Propose product code]"),
            "proposed_regulation_number": self.device_info.get("proposed_regulation_number", "[TODO: Propose reg number]"),
            "review_panel": self.device_info.get("review_panel", "[TODO: Identify review panel]"),
        }

        for field, value in summary.items():
            if isinstance(value, str) and value.startswith("[TODO"):
                self.gaps.append({
                    "section": "Device Info",
                    "field": field,
                    "severity": "HIGH",
                    "message": f"Missing required field: {field}",
                })

        return summary

    def _build_classification_recommendation(self) -> Dict[str, Any]:
        """Build classification recommendation section."""
        proposed_class = self.device_info.get("proposed_class", "II")

        return {
            "proposed_class": proposed_class,
            "rationale": self.device_info.get(
                "classification_rationale",
                "[TODO: Explain why general controls (Class I) or general + special controls (Class II) are sufficient]"
            ),
            "class_i_considerations": (
                "Class I: General controls alone are sufficient to provide reasonable "
                "assurance of safety and effectiveness. Typically for lowest-risk devices."
            ),
            "class_ii_considerations": (
                "Class II: General controls alone are insufficient, but special controls "
                "can provide reasonable assurance. Most De Novo devices are classified as Class II."
            ),
            "note": (
                "Class III (PMA) is not appropriate for De Novo; if the device requires "
                "PMA-level evidence, De Novo is not the correct pathway."
            ),
        }

    def _build_sections(self) -> List[Dict[str, Any]]:
        """Build detailed section entries with status tracking."""
        sections = []
        has_software = self.device_info.get("has_software", False)
        has_biocompat = self.device_info.get("has_biocompat_concern", True)
        is_electrical = self.device_info.get("is_electrical", False)
        is_sterile = self.device_info.get("is_sterile", False)

        for section_def in self.sections:
            # Skip non-applicable optional sections
            if section_def["number"] == "12" and not has_software:
                continue
            if section_def["number"] == "13" and not has_biocompat:
                continue
            if section_def["number"] == "14" and not is_electrical:
                continue
            if section_def["number"] == "16" and not is_sterile:
                continue

            section = {
                "number": section_def["number"],
                "title": section_def["title"],
                "description": section_def["description"],
                "required": section_def["required"],
                "cfr_reference": section_def["cfr_reference"],
                "acceptance_criteria": section_def["acceptance_criteria"],
                "status": "not_started",
                "content_guidance": self._get_content_guidance(section_def["number"]),
            }

            if section_def["required"]:
                self.gaps.append({
                    "section": section_def["title"],
                    "field": "content",
                    "severity": "CRITICAL" if section_def["number"] in ["5", "6", "7", "10"] else "HIGH",
                    "message": f"Section {section_def['number']} content not yet prepared",
                })

            sections.append(section)

        return sections

    def _get_content_guidance(self, section_number: str) -> str:
        """Get specific content guidance for each section."""
        guidance_map = {
            "1": "Include cover letter, FDA Form 3514, Table of Contents, applicant info, establishment registration number",
            "2": "Describe device technology, materials, principles of operation, key specifications. Include diagrams/photos.",
            "3": "State intended use precisely. IFU must be specific enough for classification yet broad enough for commercial use.",
            "4": "Recommend Class I or II with rationale. Propose product code and 21 CFR regulation number.",
            "5": "Document thorough predicate search in FDA 510(k) database, PMA database, De Novo database. Explain why SE is not possible.",
            "6": "Identify ALL risks per ISO 14971. Map each risk to a mitigation strategy. Use risk-mitigation table format.",
            "7": "Propose specific, enforceable special controls for each identified risk. Map risks to controls.",
            "8": "Include all relevant bench testing: performance, biocompatibility, electrical safety, EMC, sterility, shelf life.",
            "9": "Include clinical study protocol, results, and analysis if clinical data is part of the submission.",
            "10": "Structured benefit-risk analysis showing favorable benefit-risk profile. Address each identified risk.",
            "11": "Proposed labeling consistent with intended use, including adequate directions for use and warnings.",
            "12": "Software documentation per IEC 62304 level of concern. Include cybersecurity assessment.",
            "13": "ISO 10993-1 biocompatibility evaluation based on device contact type and duration.",
            "14": "IEC 60601-1 electrical safety and IEC 60601-1-2 EMC testing as applicable.",
            "15": "IEC 62366-1 HFE evaluation. Critical task analysis and summative usability evaluation.",
            "16": "Sterilization validation per applicable ISO standards. Shelf-life and packaging validation.",
        }
        return guidance_map.get(section_number, "Consult 21 CFR 860.260 for requirements")

    def _de_novo_notes(self) -> Dict[str, Any]:
        """Return De Novo-specific notes and considerations."""
        return {
            "key_differences_from_510k": [
                "No predicate device comparison required (no SE determination)",
                "Must propose special controls instead of comparing to predicate",
                "Classification recommendation is part of the submission",
                "Creates a new device classification upon granting",
                "Granted De Novo becomes predicate for future 510(k) submissions",
            ],
            "common_de_novo_pitfalls": [
                "Insufficient predicate search documentation",
                "Special controls that are too vague or unenforceable",
                "Risk assessment that misses key hazards",
                "Proposed classification (Class I vs II) not justified",
                "Benefit-risk analysis not sufficiently structured",
                "Intended use too broad for available evidence",
            ],
            "pre_submission_recommendations": [
                "Strongly recommended: Pre-Submission (Q-Sub) meeting with FDA",
                "Discuss: Intended use scope, special controls proposal, testing strategy",
                "Discuss: Need for clinical data, appropriate endpoints",
                "Discuss: Proposed classification and product code",
            ],
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

        lines.extend([
            "",
            "## Classification Recommendation",
            f"- **Proposed Class:** {outline['classification_recommendation']['proposed_class']}",
            f"- **Rationale:** {outline['classification_recommendation']['rationale']}",
            "",
            "## Submission Sections",
            "",
        ])

        for section in outline["sections"]:
            req_flag = " (REQUIRED)" if section["required"] else " (if applicable)"
            lines.append(f"### Section {section['number']}: {section['title']}{req_flag}")
            lines.append(f"*CFR Reference: {section['cfr_reference']}*")
            lines.append(f"*Acceptance Criteria: {section['acceptance_criteria']}*")
            lines.append("")
            lines.append(f"**Guidance:** {section['content_guidance']}")
            lines.append("")

        if outline["gaps"]:
            lines.extend(["## Identified Gaps", ""])
            for gap in outline["gaps"]:
                lines.append(f"- **[{gap['severity']}]** {gap['section']}: {gap['message']}")
            lines.append("")

        lines.extend([
            "## Timeline & Fees",
            f"- User Fee (FY2025): ${outline['user_fee_info']['de_novo_fee_fy2025']:,}",
            f"- FDA Review Goal: {outline['timeline_estimate']['fda_review_goal']}",
            f"- Typical Total: {outline['timeline_estimate']['typical_total']}",
            "",
            "---",
            f"*{outline['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# SPECIAL CONTROLS PROPOSAL TEMPLATE
# ========================================================================

class SpecialControlsProposal:
    """
    Generates special controls proposal templates for De Novo requests.

    Special controls, together with general controls, must provide
    reasonable assurance of safety and effectiveness for Class II devices.
    """

    def __init__(self):
        self.categories = SPECIAL_CONTROLS_CATEGORIES.copy()

    def generate(
        self,
        device_name: str,
        risks: Optional[List[Dict[str, Any]]] = None,
        proposed_controls: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a special controls proposal.

        Args:
            device_name: Name of the device
            risks: List of identified risks with id, description, severity, category
            proposed_controls: List of proposed controls with id, description, category, linked_risks

        Returns:
            Special controls proposal template
        """
        risks = risks or []
        proposed_controls = proposed_controls or []

        template = {
            "title": f"Special Controls Proposal: {device_name}",
            "device_name": device_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "regulatory_basis": "Section 513(a)(1)(B) of the FD&C Act",
            "controls_categories": [],
            "risk_control_matrix": [],
            "unmitigated_risks": [],
            "general_controls_reference": self._general_controls_checklist(),
            "completeness_score": 0,
            "disclaimer": (
                "RESEARCH USE ONLY. Special controls proposals require review "
                "by qualified regulatory professionals."
            ),
        }

        # Build category entries
        for category in self.categories:
            cat_controls = [
                c for c in proposed_controls
                if c.get("category") == category["id"]
            ]
            template["controls_categories"].append({
                "id": category["id"],
                "name": category["name"],
                "description": category["description"],
                "examples": category["examples"],
                "proposed_controls": cat_controls,
                "has_controls": len(cat_controls) > 0,
            })

        # Build risk-control matrix
        linked_risk_ids = set()
        for control in proposed_controls:
            for risk_id in control.get("linked_risks", []):
                linked_risk_ids.add(risk_id)
                matching_risk = next(
                    (r for r in risks if r.get("id") == risk_id), None
                )
                template["risk_control_matrix"].append({
                    "risk_id": risk_id,
                    "risk_description": matching_risk.get("description", "Unknown") if matching_risk else "Unknown",
                    "risk_severity": matching_risk.get("severity", "Unknown") if matching_risk else "Unknown",
                    "control_id": control.get("id", ""),
                    "control_description": control.get("description", ""),
                    "control_category": control.get("category", ""),
                })

        # Find unmitigated risks
        for risk in risks:
            if risk.get("id") not in linked_risk_ids:
                template["unmitigated_risks"].append({
                    "risk_id": risk.get("id"),
                    "description": risk.get("description"),
                    "severity": risk.get("severity"),
                    "message": "No special control proposed for this risk",
                })

        # Completeness scoring
        total_risks = len(risks)
        mitigated_risks = len(linked_risk_ids)
        template["completeness_score"] = round(
            (mitigated_risks / total_risks * 100) if total_risks > 0 else 0, 1
        )

        return template

    def _general_controls_checklist(self) -> List[Dict[str, str]]:
        """General controls that apply to ALL devices."""
        return [
            {"control": "Establishment Registration", "cfr": "21 CFR 807"},
            {"control": "Device Listing", "cfr": "21 CFR 807"},
            {"control": "Good Manufacturing Practices (QSR)", "cfr": "21 CFR 820"},
            {"control": "Labeling Requirements", "cfr": "21 CFR 801"},
            {"control": "Medical Device Reporting (MDR)", "cfr": "21 CFR 803"},
            {"control": "Premarket Notification (if applicable)", "cfr": "21 CFR 807 Subpart E"},
            {"control": "Banned Devices", "cfr": "21 CFR 895"},
            {"control": "Notification/Repair/Replace/Refund", "cfr": "21 CFR 810"},
            {"control": "Records and Reports", "cfr": "21 CFR 820.180-198"},
            {"control": "Unique Device Identification (UDI)", "cfr": "21 CFR 830"},
        ]

    def to_markdown(self, template: Dict[str, Any]) -> str:
        """Export proposal as markdown."""
        lines = [
            f"# {template['title']}",
            "",
            f"**Generated:** {template['generated_at']}",
            f"**Regulatory Basis:** {template['regulatory_basis']}",
            f"**Completeness:** {template['completeness_score']}% of risks addressed",
            "",
            "## Proposed Special Controls by Category",
            "",
        ]

        for cat in template["controls_categories"]:
            lines.append(f"### {cat['name']}")
            lines.append(f"*{cat['description']}*")
            lines.append("")
            if cat["proposed_controls"]:
                for ctrl in cat["proposed_controls"]:
                    lines.append(f"- **{ctrl.get('id', 'SC-X')}:** {ctrl.get('description', '')}")
            else:
                lines.append("- [ ] No controls proposed in this category yet")
                lines.append(f"  - Examples: {', '.join(cat['examples'])}")
            lines.append("")

        lines.extend(["## Risk-Control Traceability Matrix", ""])
        if template["risk_control_matrix"]:
            lines.append("| Risk ID | Risk Description | Severity | Control ID | Control Description |")
            lines.append("|---------|-----------------|----------|------------|-------------------|")
            for entry in template["risk_control_matrix"]:
                lines.append(
                    f"| {entry['risk_id']} | {entry['risk_description'][:50]} | "
                    f"{entry['risk_severity']} | {entry['control_id']} | "
                    f"{entry['control_description'][:50]} |"
                )
        else:
            lines.append("*No risk-control mappings defined yet.*")

        if template["unmitigated_risks"]:
            lines.extend(["", "## UNMITIGATED RISKS (Action Required)", ""])
            for risk in template["unmitigated_risks"]:
                lines.append(f"- **[{risk['severity']}]** {risk['risk_id']}: {risk['description']}")

        lines.extend([
            "",
            "## General Controls Reference",
            "",
        ])
        for gc in template["general_controls_reference"]:
            lines.append(f"- {gc['control']} ({gc['cfr']})")

        lines.extend([
            "",
            "---",
            f"*{template['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# RISK ASSESSMENT FRAMEWORK
# ========================================================================

class DeNovoRiskAssessment:
    """
    Risk assessment framework for De Novo classification requests.

    Implements ISO 14971-aligned risk analysis with De Novo-specific
    considerations including risk-mitigation mapping for special controls.
    """

    # Severity scale
    SEVERITY_SCALE = {
        1: {"label": "Negligible", "description": "Inconvenience or temporary discomfort"},
        2: {"label": "Minor", "description": "Temporary injury, no medical intervention"},
        3: {"label": "Moderate", "description": "Injury requiring medical intervention"},
        4: {"label": "Major", "description": "Serious injury, hospitalization, permanent impairment"},
        5: {"label": "Critical", "description": "Life-threatening or death"},
    }

    # Probability scale
    PROBABILITY_SCALE = {
        1: {"label": "Rare", "description": "< 1 in 100,000"},
        2: {"label": "Unlikely", "description": "1 in 10,000 to 1 in 100,000"},
        3: {"label": "Possible", "description": "1 in 1,000 to 1 in 10,000"},
        4: {"label": "Likely", "description": "1 in 100 to 1 in 1,000"},
        5: {"label": "Very Likely", "description": "> 1 in 100"},
    }

    # Detectability scale
    DETECTABILITY_SCALE = {
        1: {"label": "Very High", "description": "Almost certain to be detected before harm"},
        2: {"label": "High", "description": "High chance of detection"},
        3: {"label": "Moderate", "description": "May or may not be detected"},
        4: {"label": "Low", "description": "Unlikely to be detected"},
        5: {"label": "Very Low", "description": "Almost impossible to detect"},
    }

    def __init__(self):
        self.risks = []
        self.risk_categories = RISK_CATEGORIES.copy()

    def add_risk(
        self,
        risk_id: str,
        description: str,
        category: str,
        subcategory: Optional[str] = None,
        severity: int = 3,
        probability: int = 3,
        detectability: int = 3,
        existing_mitigations: Optional[List[str]] = None,
        proposed_mitigations: Optional[List[str]] = None,
        residual_severity: Optional[int] = None,
        residual_probability: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Add a risk to the assessment.

        Args:
            risk_id: Unique risk identifier (e.g., "R-001")
            description: Description of the risk/hazard
            category: Risk category from RISK_CATEGORIES
            subcategory: Optional subcategory
            severity: Severity score (1-5)
            probability: Probability score (1-5)
            detectability: Detectability score (1-5)
            existing_mitigations: Current mitigation measures
            proposed_mitigations: Proposed additional mitigations
            residual_severity: Post-mitigation severity
            residual_probability: Post-mitigation probability

        Returns:
            Risk entry with RPN calculation
        """
        severity = max(1, min(5, severity))
        probability = max(1, min(5, probability))
        detectability = max(1, min(5, detectability))

        rpn = severity * probability * detectability
        residual_rpn = None

        if residual_severity is not None and residual_probability is not None:
            residual_rpn = residual_severity * residual_probability * detectability

        risk_entry = {
            "risk_id": risk_id,
            "description": description,
            "category": category,
            "subcategory": subcategory,
            "severity": {
                "score": severity,
                "label": self.SEVERITY_SCALE.get(severity, {}).get("label", "Unknown"),
            },
            "probability": {
                "score": probability,
                "label": self.PROBABILITY_SCALE.get(probability, {}).get("label", "Unknown"),
            },
            "detectability": {
                "score": detectability,
                "label": self.DETECTABILITY_SCALE.get(detectability, {}).get("label", "Unknown"),
            },
            "rpn": rpn,
            "risk_level": self._classify_risk_level(rpn),
            "existing_mitigations": existing_mitigations or [],
            "proposed_mitigations": proposed_mitigations or [],
            "residual_risk": {
                "severity": residual_severity,
                "probability": residual_probability,
                "rpn": residual_rpn,
                "level": self._classify_risk_level(residual_rpn) if residual_rpn else None,
            },
            "acceptable": self._is_acceptable(rpn, residual_rpn),
        }

        self.risks.append(risk_entry)
        return risk_entry

    def _classify_risk_level(self, rpn: int) -> str:
        """Classify risk level based on RPN."""
        if rpn <= 10:
            return "LOW"
        elif rpn <= 30:
            return "MODERATE"
        elif rpn <= 60:
            return "HIGH"
        else:
            return "CRITICAL"

    def _is_acceptable(self, rpn: int, residual_rpn: Optional[int]) -> bool:
        """Determine if risk is acceptable (with mitigations if provided)."""
        effective_rpn = residual_rpn if residual_rpn is not None else rpn
        return effective_rpn <= 30

    def get_assessment_summary(self) -> Dict[str, Any]:
        """Get summary of the complete risk assessment."""
        total = len(self.risks)
        acceptable = sum(1 for r in self.risks if r["acceptable"])
        critical = sum(1 for r in self.risks if r["risk_level"] == "CRITICAL")
        high = sum(1 for r in self.risks if r["risk_level"] == "HIGH")

        by_category = {}
        for risk in self.risks:
            cat = risk["category"]
            if cat not in by_category:
                by_category[cat] = {"count": 0, "max_rpn": 0}
            by_category[cat]["count"] += 1
            by_category[cat]["max_rpn"] = max(by_category[cat]["max_rpn"], risk["rpn"])

        return {
            "total_risks": total,
            "acceptable_risks": acceptable,
            "unacceptable_risks": total - acceptable,
            "critical_risks": critical,
            "high_risks": high,
            "acceptance_rate": round((acceptable / total * 100), 1) if total > 0 else 0,
            "average_rpn": round(sum(r["rpn"] for r in self.risks) / total, 1) if total > 0 else 0,
            "max_rpn": max((r["rpn"] for r in self.risks), default=0),
            "by_category": by_category,
            "risks": self.risks,
        }

    def to_markdown(self) -> str:
        """Export risk assessment as markdown."""
        summary = self.get_assessment_summary()
        lines = [
            "# De Novo Risk Assessment",
            "",
            f"**Total Risks:** {summary['total_risks']}",
            f"**Acceptable:** {summary['acceptable_risks']}",
            f"**Unacceptable:** {summary['unacceptable_risks']}",
            f"**Acceptance Rate:** {summary['acceptance_rate']}%",
            f"**Average RPN:** {summary['average_rpn']}",
            "",
            "## Risk Matrix",
            "",
            "| Risk ID | Description | Sev | Prob | Det | RPN | Level | Acceptable |",
            "|---------|------------|-----|------|-----|-----|-------|-----------|",
        ]

        for risk in sorted(self.risks, key=lambda r: r["rpn"], reverse=True):
            acc = "YES" if risk["acceptable"] else "NO",
            lines.append(
                f"| {risk['risk_id']} | {risk['description'][:40]} | "
                f"{risk['severity']['score']} | {risk['probability']['score']} | "
                f"{risk['detectability']['score']} | {risk['rpn']} | "
                f"{risk['risk_level']} | {acc[0] if isinstance(acc, tuple) else acc} |"
            )

        lines.extend([
            "",
            "---",
            "*RESEARCH USE ONLY. Risk assessments require review by qualified professionals.*",
        ])

        return "\n".join(lines)


# ========================================================================
# BENEFIT-RISK ANALYSIS TOOL
# ========================================================================

class BenefitRiskAnalysis:
    """
    Structured benefit-risk analysis for De Novo classification requests.

    Implements a systematic framework for evaluating whether a device's
    benefits outweigh its risks for the proposed intended use.
    """

    def __init__(self, device_name: str, intended_use: str):
        self.device_name = device_name
        self.intended_use = intended_use
        self.benefits = []
        self.risks = []

    def add_benefit(
        self,
        benefit_id: str,
        description: str,
        magnitude: int = 3,
        probability: int = 3,
        evidence_type: str = "bench",
        evidence_summary: str = "",
    ) -> Dict[str, Any]:
        """Add a benefit with magnitude and probability scoring (1-5)."""
        magnitude = max(1, min(5, magnitude))
        probability = max(1, min(5, probability))

        entry = {
            "benefit_id": benefit_id,
            "description": description,
            "magnitude": magnitude,
            "probability": probability,
            "benefit_score": magnitude * probability,
            "evidence_type": evidence_type,
            "evidence_summary": evidence_summary,
        }
        self.benefits.append(entry)
        return entry

    def add_risk(
        self,
        risk_id: str,
        description: str,
        severity: int = 3,
        probability: int = 3,
        mitigation: str = "",
        residual_severity: Optional[int] = None,
        residual_probability: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add a risk with severity and probability scoring (1-5)."""
        severity = max(1, min(5, severity))
        probability = max(1, min(5, probability))

        risk_score = severity * probability
        residual_score = None
        if residual_severity is not None and residual_probability is not None:
            residual_score = residual_severity * residual_probability

        entry = {
            "risk_id": risk_id,
            "description": description,
            "severity": severity,
            "probability": probability,
            "risk_score": risk_score,
            "mitigation": mitigation,
            "residual_severity": residual_severity,
            "residual_probability": residual_probability,
            "residual_score": residual_score,
        }
        self.risks.append(entry)
        return entry

    def analyze(self) -> Dict[str, Any]:
        """Perform benefit-risk analysis and generate determination."""
        total_benefit = sum(b["benefit_score"] for b in self.benefits)
        total_risk = sum(r["risk_score"] for r in self.risks)
        total_residual_risk = sum(
            r["residual_score"] for r in self.risks
            if r["residual_score"] is not None
        )
        unmitigated_risk_count = sum(
            1 for r in self.risks if r["residual_score"] is None
        )

        # Use residual risk if all risks have mitigations
        effective_risk = total_residual_risk if unmitigated_risk_count == 0 and self.risks else total_risk

        # Benefit-risk ratio
        br_ratio = round(total_benefit / effective_risk, 2) if effective_risk > 0 else float("inf")

        # Determination
        if br_ratio >= 2.0:
            determination = "FAVORABLE"
            confidence = "HIGH"
        elif br_ratio >= 1.5:
            determination = "FAVORABLE"
            confidence = "MODERATE"
        elif br_ratio >= 1.0:
            determination = "FAVORABLE"
            confidence = "LOW"
        else:
            determination = "UNFAVORABLE"
            confidence = "N/A"

        return {
            "title": f"Benefit-Risk Analysis: {self.device_name}",
            "device_name": self.device_name,
            "intended_use": self.intended_use,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "benefits": self.benefits,
            "risks": self.risks,
            "summary": {
                "total_benefits_assessed": len(self.benefits),
                "total_risks_assessed": len(self.risks),
                "total_benefit_score": total_benefit,
                "total_risk_score": total_risk,
                "total_residual_risk_score": total_residual_risk,
                "effective_risk_score": effective_risk,
                "benefit_risk_ratio": br_ratio,
                "determination": determination,
                "confidence": confidence,
            },
            "determination_statement": (
                f"The benefit-risk profile of {self.device_name} for {self.intended_use} "
                f"is {determination} with {confidence} confidence "
                f"(B/R ratio: {br_ratio})."
            ),
            "disclaimer": (
                "RESEARCH USE ONLY. Benefit-risk analyses require review "
                "by qualified clinical and regulatory professionals."
            ),
        }


# ========================================================================
# DE NOVO vs 510(k) DECISION TREE
# ========================================================================

class PathwayDecisionTree:
    """
    Decision tree to determine whether De Novo or 510(k) is more appropriate.

    Evaluates multiple factors and provides a scored recommendation
    with rationale for each pathway.
    """

    def __init__(self):
        self.factors = DECISION_FACTORS.copy()

    def evaluate(
        self,
        answers: Dict[str, bool],
        device_context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate pathway recommendation based on decision factor answers.

        Args:
            answers: Dict mapping factor_id to True/False answer
            device_context: Optional context about the device

        Returns:
            Pathway recommendation with scores and rationale
        """
        device_context = device_context or {}

        score_510k = 0
        score_de_novo = 0
        factor_analysis = []

        for factor_id, factor_def in self.factors.items():
            answer = answers.get(factor_id)

            if answer is None:
                factor_analysis.append({
                    "factor": factor_id,
                    "question": factor_def["question"],
                    "answer": "NOT PROVIDED",
                    "impact": "Cannot score this factor",
                })
                continue

            weight = factor_def["weight"]

            if answer == factor_def["510k_if"]:
                score_510k += weight
                favors = "510(k)"
            else:
                favors = "Neither specifically"

            if answer == factor_def["de_novo_if"]:
                score_de_novo += weight
                favors = "De Novo" if favors == "Neither specifically" else "Both"

            factor_analysis.append({
                "factor": factor_id,
                "question": factor_def["question"],
                "answer": "Yes" if answer else "No",
                "weight": weight,
                "favors": favors,
            })

        # Normalize scores
        max_possible = sum(f["weight"] for f in self.factors.values())
        norm_510k = round((score_510k / max_possible * 100) if max_possible > 0 else 0, 1)
        norm_de_novo = round((score_de_novo / max_possible * 100) if max_possible > 0 else 0, 1)

        # Recommendation
        if norm_510k > norm_de_novo + 15:
            recommendation = "510(k)"
            confidence = "HIGH" if norm_510k > 70 else "MODERATE"
        elif norm_de_novo > norm_510k + 15:
            recommendation = "De Novo"
            confidence = "HIGH" if norm_de_novo > 70 else "MODERATE"
        else:
            recommendation = "Further analysis needed"
            confidence = "LOW"

        return {
            "title": "Regulatory Pathway Decision Analysis",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "device_context": device_context,
            "scores": {
                "510k_score": norm_510k,
                "de_novo_score": norm_de_novo,
            },
            "recommendation": recommendation,
            "confidence": confidence,
            "factor_analysis": factor_analysis,
            "next_steps": self._get_next_steps(recommendation),
            "disclaimer": (
                "RESEARCH USE ONLY. Regulatory pathway decisions require "
                "consultation with qualified regulatory professionals."
            ),
        }

    def _get_next_steps(self, recommendation: str) -> List[str]:
        """Get recommended next steps based on pathway recommendation."""
        if recommendation == "510(k)":
            return [
                "Identify and document predicate device(s)",
                "Prepare substantial equivalence comparison",
                "Conduct predicate search using FDA databases",
                "Consider Pre-Submission meeting with FDA to confirm approach",
            ]
        elif recommendation == "De Novo":
            return [
                "Document thorough predicate search showing no suitable predicates",
                "Develop proposed special controls",
                "Prepare risk assessment and benefit-risk analysis",
                "Strongly recommended: Pre-Submission meeting with FDA",
                "Propose classification (Class I or II) with rationale",
            ]
        else:
            return [
                "Conduct more thorough predicate search",
                "Consult with regulatory professional",
                "Consider Pre-Submission meeting with FDA for pathway guidance",
                "Evaluate whether device raises new questions of safety/effectiveness",
            ]


# ========================================================================
# PREDICATE SEARCH DOCUMENTATION
# ========================================================================

class PredicateSearchDocumentation:
    """
    Documents the predicate search process for De Novo submissions.

    A De Novo request must demonstrate that no suitable predicate exists,
    or that substantial equivalence cannot be established.
    """

    def __init__(self, device_name: str):
        self.device_name = device_name
        self.search_strategies = []
        self.databases_searched = []
        self.candidates_evaluated = []
        self.conclusion = ""

    def add_search_strategy(
        self,
        database: str,
        search_terms: List[str],
        date_range: Optional[str] = None,
        results_count: int = 0,
        search_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a documented search strategy."""
        strategy = {
            "database": database,
            "search_terms": search_terms,
            "date_range": date_range or "All available years",
            "results_count": results_count,
            "search_date": search_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        self.search_strategies.append(strategy)

        if database not in self.databases_searched:
            self.databases_searched.append(database)

        return strategy

    def add_candidate_evaluation(
        self,
        device_name: str,
        k_number: Optional[str] = None,
        product_code: Optional[str] = None,
        intended_use: str = "",
        technology: str = "",
        se_possible: bool = False,
        rejection_reason: str = "",
    ) -> Dict[str, Any]:
        """Add evaluation of a potential predicate candidate."""
        candidate = {
            "device_name": device_name,
            "k_number": k_number,
            "product_code": product_code,
            "intended_use": intended_use,
            "technology": technology,
            "se_possible": se_possible,
            "rejection_reason": rejection_reason,
        }
        self.candidates_evaluated.append(candidate)
        return candidate

    def generate_documentation(self) -> Dict[str, Any]:
        """Generate complete predicate search documentation."""
        all_rejected = all(
            not c["se_possible"] for c in self.candidates_evaluated
        )

        doc = {
            "title": f"Predicate Search Documentation: {self.device_name}",
            "device_name": self.device_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "databases_searched": self.databases_searched,
            "search_strategies": self.search_strategies,
            "candidates_evaluated": self.candidates_evaluated,
            "total_candidates": len(self.candidates_evaluated),
            "suitable_predicates_found": sum(
                1 for c in self.candidates_evaluated if c["se_possible"]
            ),
            "conclusion": (
                "No suitable predicate device was identified. De Novo classification "
                "request is appropriate."
                if all_rejected
                else "Potential predicate(s) identified. 510(k) may be more appropriate."
            ),
            "supports_de_novo": all_rejected,
            "recommended_databases": [
                "FDA 510(k) Premarket Notification Database",
                "FDA PMA Database",
                "FDA De Novo Database",
                "FDA Product Classification Database",
                "AccessGUDID",
            ],
            "disclaimer": (
                "RESEARCH USE ONLY. Predicate search documentation requires "
                "review by qualified regulatory professionals."
            ),
        }

        return doc

    def to_markdown(self) -> str:
        """Export documentation as markdown."""
        doc = self.generate_documentation()
        lines = [
            f"# {doc['title']}",
            "",
            f"**Generated:** {doc['generated_at']}",
            f"**Databases Searched:** {len(doc['databases_searched'])}",
            f"**Candidates Evaluated:** {doc['total_candidates']}",
            f"**Suitable Predicates Found:** {doc['suitable_predicates_found']}",
            "",
            "## Search Strategies",
            "",
        ]

        for i, strategy in enumerate(doc["search_strategies"], 1):
            lines.append(f"### Search {i}: {strategy['database']}")
            lines.append(f"- **Terms:** {', '.join(strategy['search_terms'])}")
            lines.append(f"- **Date Range:** {strategy['date_range']}")
            lines.append(f"- **Results:** {strategy['results_count']}")
            lines.append(f"- **Search Date:** {strategy['search_date']}")
            lines.append("")

        lines.extend(["## Candidate Evaluations", ""])
        if doc["candidates_evaluated"]:
            lines.append("| Device | K-Number | Product Code | SE Possible | Rejection Reason |")
            lines.append("|--------|----------|-------------|-------------|------------------|")
            for c in doc["candidates_evaluated"]:
                se = "Yes" if c["se_possible"] else "No"
                lines.append(
                    f"| {c['device_name']} | {c.get('k_number', 'N/A')} | "
                    f"{c.get('product_code', 'N/A')} | {se} | "
                    f"{c['rejection_reason'][:60]} |"
                )
        else:
            lines.append("*No candidates evaluated yet.*")

        lines.extend([
            "",
            "## Conclusion",
            doc["conclusion"],
            "",
            f"**Supports De Novo:** {'Yes' if doc['supports_de_novo'] else 'No'}",
            "",
            "---",
            f"*{doc['disclaimer']}*",
        ])

        return "\n".join(lines)


# ========================================================================
# CONVENIENCE FUNCTIONS
# ========================================================================

def generate_de_novo_outline(
    device_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a De Novo submission outline."""
    generator = DeNovoSubmissionOutline(device_info)
    return generator.generate()


def generate_special_controls(
    device_name: str,
    risks: Optional[List[Dict[str, Any]]] = None,
    controls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generate a special controls proposal."""
    proposal = SpecialControlsProposal()
    return proposal.generate(device_name, risks, controls)


def evaluate_pathway(
    answers: Dict[str, bool],
    device_context: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Evaluate De Novo vs 510(k) pathway recommendation."""
    tree = PathwayDecisionTree()
    return tree.evaluate(answers, device_context)


def perform_benefit_risk_analysis(
    device_name: str,
    intended_use: str,
) -> BenefitRiskAnalysis:
    """Create a benefit-risk analysis instance for populating."""
    return BenefitRiskAnalysis(device_name, intended_use)
