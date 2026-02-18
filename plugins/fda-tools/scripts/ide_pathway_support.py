#!/usr/bin/env python3
"""
IDE Pathway Support (FDA-67) -- Investigational Device Exemption tools
for clinical study planning, SR/NSR determination, ClinicalTrials.gov
integration, informed consent generation, and 21 CFR 812 compliance.

Challenge: No FDA IDE API endpoint exists, so this module provides
offline regulatory intelligence tools.

Features:
  1. IDE submission outline generator
  2. SR vs NSR determination workflow (21 CFR 812.2(b) criteria)
  3. ClinicalTrials.gov integration for IDE studies
  4. Informed consent template generator (21 CFR 50.25)
  5. 21 CFR 812 compliance checklist
  6. IRB submission package generator

Usage:
    from ide_pathway_support import (
        SRNSRDetermination,
        IDESubmissionOutline,
        ClinicalTrialsIntegration,
        InformedConsentGenerator,
        IDEComplianceChecklist,
        IRBPackageGenerator,
    )

    # SR/NSR determination
    sr_nsr = SRNSRDetermination()
    result = sr_nsr.evaluate(
        device_name="Coronary Stent",
        is_implant=True,
        implant_duration_days=365,
        anatomical_site="cardiac",
        failure_severity="death",
    )

    # IDE submission outline
    outline = IDESubmissionOutline()
    ide_package = outline.generate(device_name="Coronary Stent", risk="SR")

    # ClinicalTrials.gov search
    ct = ClinicalTrialsIntegration()
    studies = ct.search_device_studies("coronary stent")

    # Informed consent template
    ic = InformedConsentGenerator()
    consent = ic.generate(device_name="Coronary Stent", study_type="pivotal_rct")

    # 21 CFR 812 compliance checklist
    checklist = IDEComplianceChecklist()
    result = checklist.evaluate(submission_data)

    # CLI:
    python3 ide_pathway_support.py sr-nsr --device "Coronary Stent" --implant --cardiac
    python3 ide_pathway_support.py outline --device "Coronary Stent" --risk SR
    python3 ide_pathway_support.py consent --device "Coronary Stent" --study pivotal_rct
    python3 ide_pathway_support.py checklist --input submission.json
"""

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------
# SR/NSR Criteria per 21 CFR 812.3(m)
# ------------------------------------------------------------------

# Anatomical risk classifications
HIGH_RISK_ANATOMY = {
    "cardiac", "heart", "coronary", "atrial", "ventricular", "aortic",
    "neural", "brain", "spinal", "spine", "cerebral", "intracranial",
    "vascular", "carotid", "aorta", "femoral artery",
    "pulmonary", "lung",
    "hepatic", "liver",
    "renal", "kidney",
    "ocular", "retinal", "intraocular",
}

MODERATE_RISK_ANATOMY = {
    "orthopedic", "bone", "joint", "lumbar", "cervical", "thoracic",
    "dental", "maxillofacial",
    "gastrointestinal", "esophageal", "gastric", "intestinal",
    "urological", "urinary", "bladder", "ureteral",
    "reproductive", "uterine",
    "dermal", "subcutaneous",
    "airway", "tracheal", "bronchial",
    "ear", "cochlear", "tympanic",
}

LOW_RISK_ANATOMY = {
    "external", "surface", "skin", "peripheral", "nasal",
    "oral", "topical", "non-invasive",
}

# Failure severity classifications
FAILURE_SEVERITY = {
    "death": {"score": 100, "level": "critical"},
    "permanent_impairment": {"score": 90, "level": "critical"},
    "serious_injury": {"score": 80, "level": "serious"},
    "hospitalization": {"score": 70, "level": "serious"},
    "surgical_intervention": {"score": 65, "level": "serious"},
    "temporary_impairment": {"score": 40, "level": "moderate"},
    "minor_injury": {"score": 25, "level": "minor"},
    "discomfort": {"score": 15, "level": "minor"},
    "no_harm": {"score": 5, "level": "minimal"},
}


# ------------------------------------------------------------------
# IDE Submission Sections per 21 CFR 812.20
# ------------------------------------------------------------------

IDE_SUBMISSION_SECTIONS = {
    "sr": [
        {
            "section": "1",
            "title": "Cover Letter",
            "cfr_ref": "21 CFR 812.20(a)",
            "description": "Cover letter identifying submission as an IDE application",
            "required": True,
        },
        {
            "section": "2",
            "title": "Table of Contents",
            "cfr_ref": "21 CFR 812.20(b)(1)",
            "description": "Complete table of contents",
            "required": True,
        },
        {
            "section": "3",
            "title": "Name and Address of Sponsor",
            "cfr_ref": "21 CFR 812.20(b)(2)",
            "description": "Full sponsor contact information",
            "required": True,
        },
        {
            "section": "4",
            "title": "Report of Prior Investigations",
            "cfr_ref": "21 CFR 812.20(b)(3) and 812.27",
            "description": "Summary of all prior clinical, animal, and lab studies",
            "required": True,
        },
        {
            "section": "5",
            "title": "Investigational Plan",
            "cfr_ref": "21 CFR 812.20(b)(4) and 812.25",
            "description": "Clinical protocol including objectives, design, endpoints, sample size",
            "required": True,
            "subsections": [
                "Purpose of study",
                "Study protocol (objectives, design, endpoints)",
                "Risk analysis",
                "Device description",
                "Monitoring procedures",
                "Institutional review board (IRB) information",
                "Labeling for investigational device",
                "Informed consent documents",
                "Sale of device during investigation",
            ],
        },
        {
            "section": "6",
            "title": "Device Description",
            "cfr_ref": "21 CFR 812.20(b)(5)",
            "description": "Complete device description including specifications, materials, and manufacturing",
            "required": True,
        },
        {
            "section": "7",
            "title": "Monitoring Procedures",
            "cfr_ref": "21 CFR 812.20(b)(6) and 812.46",
            "description": "Plans for monitoring the study conduct and device performance",
            "required": True,
        },
        {
            "section": "8",
            "title": "Manufacturing Information",
            "cfr_ref": "21 CFR 812.20(b)(7)",
            "description": "Manufacturing, processing, packing, storage, and installation",
            "required": True,
        },
        {
            "section": "9",
            "title": "Investigator Information",
            "cfr_ref": "21 CFR 812.20(b)(8) and 812.43",
            "description": "Names and qualifications of all investigators",
            "required": True,
        },
        {
            "section": "10",
            "title": "IRB Information",
            "cfr_ref": "21 CFR 812.20(b)(9) and 812.66",
            "description": "IRB identification, composition, and approval status",
            "required": True,
        },
        {
            "section": "11",
            "title": "Sale Information",
            "cfr_ref": "21 CFR 812.20(b)(10)",
            "description": "If device is to be sold during investigation, justification required",
            "required": False,
        },
        {
            "section": "12",
            "title": "Environmental Assessment",
            "cfr_ref": "21 CFR 812.20(b)(11) and 21 CFR 25",
            "description": "Environmental impact assessment or categorical exclusion claim",
            "required": True,
        },
        {
            "section": "13",
            "title": "Informed Consent Documents",
            "cfr_ref": "21 CFR 50",
            "description": "Informed consent forms compliant with 21 CFR 50.25",
            "required": True,
        },
        {
            "section": "14",
            "title": "Financial Disclosure",
            "cfr_ref": "21 CFR 54",
            "description": "Financial certification or disclosure for investigators",
            "required": True,
        },
        {
            "section": "15",
            "title": "Labeling",
            "cfr_ref": "21 CFR 812.5",
            "description": "Investigational device labeling (CAUTION: investigational device)",
            "required": True,
        },
    ],
    "nsr": [
        {
            "section": "1",
            "title": "Device Description",
            "cfr_ref": "21 CFR 812.2(b)",
            "description": "Description of the investigational device",
            "required": True,
        },
        {
            "section": "2",
            "title": "SR/NSR Determination Justification",
            "cfr_ref": "21 CFR 812.2(b) and 812.3(m)",
            "description": "Documented rationale for NSR determination",
            "required": True,
        },
        {
            "section": "3",
            "title": "Clinical Protocol",
            "cfr_ref": "21 CFR 812.25",
            "description": "Study protocol (abbreviated version acceptable)",
            "required": True,
        },
        {
            "section": "4",
            "title": "Informed Consent Documents",
            "cfr_ref": "21 CFR 50",
            "description": "Informed consent forms per 21 CFR 50.25",
            "required": True,
        },
        {
            "section": "5",
            "title": "IRB Approval",
            "cfr_ref": "21 CFR 56",
            "description": "IRB review and approval of NSR determination and protocol",
            "required": True,
        },
        {
            "section": "6",
            "title": "Labeling",
            "cfr_ref": "21 CFR 812.5",
            "description": "Investigational device labeling",
            "required": True,
        },
    ],
}


# ------------------------------------------------------------------
# 21 CFR 812 Compliance Requirements
# ------------------------------------------------------------------

COMPLIANCE_REQUIREMENTS = [
    {
        "id": "IDE-01",
        "category": "Sponsor Responsibilities",
        "cfr_ref": "21 CFR 812.40",
        "requirement": "Sponsor shall ensure proper monitoring of the investigation",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-02",
        "category": "Sponsor Responsibilities",
        "cfr_ref": "21 CFR 812.43",
        "requirement": "Sponsor shall select qualified investigators and provide required information",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-03",
        "category": "Sponsor Responsibilities",
        "cfr_ref": "21 CFR 812.45",
        "requirement": "Sponsor shall ensure IRB approval before study initiation at each site",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-04",
        "category": "Sponsor Responsibilities",
        "cfr_ref": "21 CFR 812.46",
        "requirement": "Sponsor shall monitor the investigation and secure compliance",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-05",
        "category": "Investigator Responsibilities",
        "cfr_ref": "21 CFR 812.100",
        "requirement": "Investigator shall conduct investigation according to signed agreement and protocol",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-06",
        "category": "Investigator Responsibilities",
        "cfr_ref": "21 CFR 812.110",
        "requirement": "Investigator shall maintain accurate and complete records",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-07",
        "category": "Informed Consent",
        "cfr_ref": "21 CFR 50.25",
        "requirement": "Informed consent must contain all 9 required elements",
        "priority": "CRITICAL",
        "elements": [
            "Statement that study involves research and expected duration",
            "Description of procedures, identifying experimental ones",
            "Description of reasonably foreseeable risks or discomforts",
            "Description of benefits to subject or others",
            "Disclosure of alternative treatments/procedures",
            "Confidentiality statement",
            "Compensation/medical treatment for injury (>minimal risk)",
            "Contact information for questions",
            "Statement that participation is voluntary",
        ],
    },
    {
        "id": "IDE-08",
        "category": "Informed Consent",
        "cfr_ref": "21 CFR 50.20",
        "requirement": "No informed consent may include exculpatory language",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-09",
        "category": "IRB Requirements",
        "cfr_ref": "21 CFR 56.103",
        "requirement": "IRB must review and approve all research involving human subjects",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-10",
        "category": "IRB Requirements",
        "cfr_ref": "21 CFR 56.109",
        "requirement": "IRB must conduct continuing review at least annually",
        "priority": "HIGH",
    },
    {
        "id": "IDE-11",
        "category": "Reporting",
        "cfr_ref": "21 CFR 812.150(a)",
        "requirement": "Sponsor must submit progress reports every 6 months (or as required)",
        "priority": "HIGH",
    },
    {
        "id": "IDE-12",
        "category": "Reporting",
        "cfr_ref": "21 CFR 812.150(b)",
        "requirement": "Unanticipated adverse device effects must be reported within 10 working days",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-13",
        "category": "Reporting",
        "cfr_ref": "21 CFR 812.150(b)(1)",
        "requirement": "Deaths, serious injuries, and device malfunctions reported to FDA and IRBs",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-14",
        "category": "Labeling",
        "cfr_ref": "21 CFR 812.5",
        "requirement": "Device labeled 'CAUTION - Investigational Device'",
        "priority": "CRITICAL",
    },
    {
        "id": "IDE-15",
        "category": "Record Keeping",
        "cfr_ref": "21 CFR 812.140",
        "requirement": "Sponsors and investigators shall maintain records during study and 2 years after",
        "priority": "HIGH",
    },
    {
        "id": "IDE-16",
        "category": "Changes to IDE",
        "cfr_ref": "21 CFR 812.35",
        "requirement": "Significant changes to IDE require supplemental application before implementation",
        "priority": "HIGH",
    },
    {
        "id": "IDE-17",
        "category": "Financial Disclosure",
        "cfr_ref": "21 CFR 54",
        "requirement": "Financial disclosure information for clinical investigators",
        "priority": "HIGH",
    },
    {
        "id": "IDE-18",
        "category": "Device Accountability",
        "cfr_ref": "21 CFR 812.140(a)(2)",
        "requirement": "Track device shipment, receipt, use, return, and disposition",
        "priority": "HIGH",
    },
]


# ==================================================================
# SR/NSR Determination
# ==================================================================

class SRNSRDetermination:
    """Significant Risk (SR) vs Non-Significant Risk (NSR) determination
    workflow per 21 CFR 812.2(b) and 812.3(m).

    A device is SR if it meets ANY of these criteria:
    1. Presents potential for serious risk to health/safety/welfare
    2. Is intended as an implant and presents potential for serious risk
    3. Is purported to be for use supporting/sustaining human life

    'Serious risk' = risk of death, permanent impairment, or permanent damage.
    """

    SR_THRESHOLD = 60  # Score >= 60 = SR

    def evaluate(
        self,
        device_name: str = "",
        device_description: str = "",
        is_implant: bool = False,
        implant_duration_days: int = 0,
        anatomical_site: str = "",
        body_system: str = "",
        is_life_sustaining: bool = False,
        is_life_supporting: bool = False,
        energy_type: str = "",
        energy_level: str = "",
        invasiveness: str = "",
        failure_severity: str = "",
        patient_population: str = "",
        existing_predicate: str = "",
    ) -> Dict:
        """Evaluate SR/NSR determination for a device.

        Args:
            device_name: Device name.
            device_description: Device description text.
            is_implant: Whether device is an implant.
            implant_duration_days: Duration of implantation (0=not implant).
            anatomical_site: Target anatomy (cardiac, neural, etc.).
            body_system: Body system (cardiovascular, neurological, etc.).
            is_life_sustaining: Whether device sustains human life.
            is_life_supporting: Whether device supports human life.
            energy_type: Type of energy (RF, laser, radiation, etc.).
            energy_level: Energy level (high, moderate, low).
            invasiveness: Invasiveness (surgical, minimally_invasive, non_invasive).
            failure_severity: Worst-case failure outcome.
            patient_population: Target population (general, pediatric, vulnerable).
            existing_predicate: Predicate device K-number if exists.

        Returns:
            SR/NSR determination with score, rationale, and risk factors.
        """
        risk_score = 0
        risk_factors = []
        mitigating_factors = []

        # Factor 1: Implantation (21 CFR 812.3(m)(2))
        if is_implant:
            if implant_duration_days > 365 or implant_duration_days == 0:
                # Permanent implant
                risk_score += 30
                risk_factors.append({
                    "factor": "Permanent implant",
                    "score": 30,
                    "cfr_ref": "21 CFR 812.3(m)(2)",
                    "detail": f"Implant duration: {implant_duration_days} days (permanent)",
                })
            elif implant_duration_days > 30:
                risk_score += 20
                risk_factors.append({
                    "factor": "Extended implant (>30 days)",
                    "score": 20,
                    "cfr_ref": "21 CFR 812.3(m)(2)",
                    "detail": f"Implant duration: {implant_duration_days} days",
                })
            else:
                risk_score += 10
                risk_factors.append({
                    "factor": "Short-term implant (<=30 days)",
                    "score": 10,
                    "cfr_ref": "21 CFR 812.3(m)(2)",
                    "detail": f"Implant duration: {implant_duration_days} days",
                })

        # Factor 2: Life-sustaining/supporting (21 CFR 812.3(m)(3))
        if is_life_sustaining:
            risk_score += 35
            risk_factors.append({
                "factor": "Life-sustaining device",
                "score": 35,
                "cfr_ref": "21 CFR 812.3(m)(3)",
                "detail": "Device sustains human life",
            })
        elif is_life_supporting:
            risk_score += 25
            risk_factors.append({
                "factor": "Life-supporting device",
                "score": 25,
                "cfr_ref": "21 CFR 812.3(m)(3)",
                "detail": "Device supports human life",
            })

        # Factor 3: Anatomical site risk
        site_lower = anatomical_site.lower() if anatomical_site else ""
        system_lower = body_system.lower() if body_system else ""
        combined_anatomy = f"{site_lower} {system_lower}"

        if any(term in combined_anatomy for term in HIGH_RISK_ANATOMY):
            risk_score += 25
            risk_factors.append({
                "factor": "High-risk anatomical site",
                "score": 25,
                "detail": f"Target: {anatomical_site or body_system}",
            })
        elif any(term in combined_anatomy for term in MODERATE_RISK_ANATOMY):
            risk_score += 15
            risk_factors.append({
                "factor": "Moderate-risk anatomical site",
                "score": 15,
                "detail": f"Target: {anatomical_site or body_system}",
            })
        elif any(term in combined_anatomy for term in LOW_RISK_ANATOMY):
            risk_score += 5
            mitigating_factors.append({
                "factor": "Low-risk anatomical site",
                "score": 5,
                "detail": f"Target: {anatomical_site or body_system}",
            })

        # Factor 4: Failure severity
        if failure_severity:
            severity_key = failure_severity.lower().replace(" ", "_").replace("-", "_")
            sev_info = FAILURE_SEVERITY.get(severity_key, {"score": 30, "level": "moderate"})
            severity_score = min(sev_info["score"] // 3, 30)  # Scale to max 30
            risk_score += severity_score
            risk_factors.append({
                "factor": f"Failure severity: {failure_severity}",
                "score": severity_score,
                "detail": f"Worst-case outcome: {failure_severity} ({sev_info['level']})",
            })

        # Factor 5: Energy type
        if energy_type:
            energy_lower = energy_type.lower()
            if any(e in energy_lower for e in ("radiation", "rf ablation", "laser", "high-energy")):
                risk_score += 15
                risk_factors.append({
                    "factor": "High-energy delivery",
                    "score": 15,
                    "detail": f"Energy type: {energy_type}",
                })
            elif any(e in energy_lower for e in ("electrical", "ultrasound", "microwave")):
                risk_score += 8
                risk_factors.append({
                    "factor": "Moderate energy delivery",
                    "score": 8,
                    "detail": f"Energy type: {energy_type}",
                })

        # Factor 6: Invasiveness
        if invasiveness:
            inv_lower = invasiveness.lower()
            if "surgical" in inv_lower or "major" in inv_lower:
                risk_score += 10
                risk_factors.append({
                    "factor": "Surgical invasiveness",
                    "score": 10,
                    "detail": f"Invasiveness: {invasiveness}",
                })
            elif "minimally" in inv_lower:
                risk_score += 5
            elif "non" in inv_lower:
                mitigating_factors.append({
                    "factor": "Non-invasive device",
                    "score": -5,
                    "detail": "Non-invasive approach reduces risk profile",
                })

        # Factor 7: Patient population
        if patient_population:
            pop_lower = patient_population.lower()
            if any(kw in pop_lower for kw in ("pediatric", "neonatal", "pregnant", "vulnerable")):
                risk_score += 10
                risk_factors.append({
                    "factor": "Vulnerable patient population",
                    "score": 10,
                    "detail": f"Population: {patient_population}",
                })

        # Mitigating: existing predicate
        if existing_predicate:
            mitigating_factors.append({
                "factor": "Existing predicate device",
                "score": -5,
                "detail": f"Predicate: {existing_predicate}",
            })

        # Determine SR/NSR
        is_sr = risk_score >= self.SR_THRESHOLD

        # Build justification
        if is_sr:
            determination = "SIGNIFICANT_RISK"
            determination_label = "Significant Risk (SR)"
            regulatory_path = "Full IDE application to FDA required per 21 CFR 812.20"
            fda_review = "30-day FDA review period before study may begin"
        else:
            determination = "NON_SIGNIFICANT_RISK"
            determination_label = "Non-Significant Risk (NSR)"
            regulatory_path = "IRB approval required; no FDA IDE submission needed per 21 CFR 812.2(b)"
            fda_review = "No FDA review required; IRB approval sufficient"

        return {
            "device_name": device_name,
            "determination": determination,
            "determination_label": determination_label,
            "risk_score": risk_score,
            "sr_threshold": self.SR_THRESHOLD,
            "is_significant_risk": is_sr,
            "regulatory_path": regulatory_path,
            "fda_review": fda_review,
            "risk_factors": risk_factors,
            "mitigating_factors": mitigating_factors,
            "total_risk_factors": len(risk_factors),
            "cfr_basis": [
                "21 CFR 812.3(m) - Definition of significant risk device",
                "21 CFR 812.2(b) - Exempted investigations (NSR devices)",
            ],
            "irb_requirements": (
                "IRB must review sponsor's SR/NSR determination. "
                "If IRB disagrees with NSR, sponsor may request FDA determination."
            ),
            "next_steps": self._get_next_steps(is_sr),
            "disclaimer": (
                "This SR/NSR determination is AI-generated guidance. "
                "Final determination must be made by the sponsor with IRB concurrence. "
                "FDA determination is binding if requested."
            ),
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_next_steps(self, is_sr: bool) -> List[str]:
        """Get recommended next steps based on determination."""
        if is_sr:
            return [
                "1. Prepare IDE application per 21 CFR 812.20 (15 sections)",
                "2. Submit IDE to FDA (30-day review clock starts on receipt)",
                "3. Obtain IRB approval at each investigational site",
                "4. Do NOT begin study until FDA approves IDE and all IRBs approve",
                "5. Consider Pre-IDE meeting (Pre-Sub) to discuss protocol with FDA",
                "6. Prepare informed consent per 21 CFR 50.25 (all 9 elements)",
                "7. Ensure device labeled 'CAUTION - Investigational Device'",
            ]
        else:
            return [
                "1. Document NSR determination with written justification",
                "2. Submit NSR determination and protocol to IRB for review",
                "3. Obtain IRB approval before beginning study",
                "4. If IRB disagrees with NSR, consider requesting FDA determination",
                "5. Prepare informed consent per 21 CFR 50.25",
                "6. Maintain study records per 21 CFR 812.140",
                "7. Report unanticipated adverse device effects per 21 CFR 812.150(b)",
            ]


# ==================================================================
# IDE Submission Outline Generator
# ==================================================================

class IDESubmissionOutline:
    """Generate IDE submission outlines per 21 CFR 812.20.

    Produces structured package outlines for both SR (full IDE to FDA)
    and NSR (abbreviated, IRB-only) submissions.
    """

    def generate(
        self,
        device_name: str = "",
        device_description: str = "",
        risk: str = "SR",
        study_type: str = "pivotal",
        num_sites: int = 5,
        num_subjects: int = 100,
        sponsor_name: str = "",
    ) -> Dict:
        """Generate an IDE submission outline.

        Args:
            device_name: Name of the investigational device.
            device_description: Brief device description.
            risk: "SR" or "NSR".
            study_type: "pivotal", "feasibility", or "early_feasibility".
            num_sites: Expected number of sites.
            num_subjects: Expected enrollment.
            sponsor_name: Sponsor name.

        Returns:
            IDE submission outline with sections, checklist, and guidance.
        """
        risk_key = "sr" if risk.upper() == "SR" else "nsr"
        sections = IDE_SUBMISSION_SECTIONS[risk_key]

        # Build checklist
        checklist = []
        for section in sections:
            entry = {
                "section": section["section"],
                "title": section["title"],
                "cfr_ref": section["cfr_ref"],
                "description": section["description"],
                "required": section["required"],
                "status": "NOT_STARTED",
                "notes": "",
            }
            if "subsections" in section:
                entry["subsections"] = section["subsections"]
            checklist.append(entry)

        # Study-specific guidance
        study_guidance = self._get_study_guidance(study_type)

        # Timeline
        if risk_key == "sr":
            timeline = {
                "preparation_weeks": 12 if study_type == "pivotal" else 8,
                "fda_review_days": 30,
                "irb_review_weeks": 4,
                "total_to_first_enrollment_weeks": (
                    16 if study_type == "pivotal" else 12
                ),
                "note": "FDA has 30 calendar days to review SR IDE. Study may begin when IDE is approved.",
            }
        else:
            timeline = {
                "preparation_weeks": 4,
                "fda_review_days": 0,
                "irb_review_weeks": 4,
                "total_to_first_enrollment_weeks": 8,
                "note": "NSR studies require only IRB approval. No FDA submission needed.",
            }

        return {
            "device_name": device_name,
            "device_description": device_description,
            "risk_determination": risk.upper(),
            "study_type": study_type,
            "num_sites": num_sites,
            "num_subjects": num_subjects,
            "sponsor_name": sponsor_name,
            "total_sections": len(checklist),
            "sections": checklist,
            "study_guidance": study_guidance,
            "timeline": timeline,
            "regulatory_references": [
                "21 CFR 812 - Investigational Device Exemptions",
                "21 CFR 50 - Protection of Human Subjects",
                "21 CFR 56 - Institutional Review Boards",
                "21 CFR 54 - Financial Disclosure by Clinical Investigators",
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "This IDE submission outline is AI-generated guidance. "
                "Consult with qualified regulatory professionals before submission."
            ),
        }

    def _get_study_guidance(self, study_type: str) -> Dict:
        """Get study-type-specific guidance."""
        guidance = {
            "pivotal": {
                "description": "Pivotal study to support PMA or De Novo submission",
                "typical_duration_months": 24,
                "typical_sites": "10-30",
                "typical_enrollment": "150-2000+",
                "endpoint_requirements": "Pre-specified primary endpoint with statistical analysis plan",
                "monitoring": "100% source data verification (SDV) recommended",
                "dmc_required": True,
                "note": "Consider Pre-IDE (Pre-Sub) meeting before submission",
            },
            "feasibility": {
                "description": "Feasibility study to assess device performance and refine design",
                "typical_duration_months": 12,
                "typical_sites": "3-10",
                "typical_enrollment": "20-50",
                "endpoint_requirements": "Exploratory endpoints acceptable",
                "monitoring": "Periodic monitoring visits",
                "dmc_required": False,
                "note": "Results may inform pivotal study design",
            },
            "early_feasibility": {
                "description": "Early feasibility study (first-in-human)",
                "typical_duration_months": 6,
                "typical_sites": "1-3",
                "typical_enrollment": "5-15",
                "endpoint_requirements": "Safety-focused with device performance assessment",
                "monitoring": "Enhanced monitoring, possible on-site CRA",
                "dmc_required": True,
                "note": "FDA Early Feasibility Study guidance (2013) applies",
            },
        }
        return guidance.get(study_type, guidance["pivotal"])


# ==================================================================
# ClinicalTrials.gov Integration
# ==================================================================

class ClinicalTrialsIntegration:
    """Search ClinicalTrials.gov for device-related IDE studies.

    Uses the ClinicalTrials.gov v2 API to find relevant device studies
    and extract protocol information.
    """

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def search_device_studies(
        self,
        device_name: str,
        status: str = "",
        max_results: int = 20,
    ) -> Dict:
        """Search ClinicalTrials.gov for device studies.

        Args:
            device_name: Device name or keyword to search.
            status: Optional filter (RECRUITING, COMPLETED, etc.).
            max_results: Maximum results to return.

        Returns:
            Search results with study summaries.
        """
        params = {
            "query.term": f"{device_name} device",
            "query.studyType": "INTERVENTIONAL",
            "pageSize": min(max_results, 100),
            "format": "json",
        }
        if status:
            params["filter.overallStatus"] = status

        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Tools/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            studies = []
            for study in data.get("studies", []):
                protocol = study.get("protocolSection", {})
                ident = protocol.get("identificationModule", {})
                status_mod = protocol.get("statusModule", {})
                design = protocol.get("designModule", {})
                conditions = protocol.get("conditionsModule", {})
                enrollment = design.get("enrollmentInfo", {})

                studies.append({
                    "nct_id": ident.get("nctId", ""),
                    "title": ident.get("briefTitle", ""),
                    "status": status_mod.get("overallStatus", ""),
                    "phase": ", ".join(design.get("phases", [])) if design.get("phases") else "N/A",
                    "study_type": design.get("studyType", ""),
                    "enrollment": enrollment.get("count", 0),
                    "conditions": conditions.get("conditions", []),
                    "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
                    "completion_date": status_mod.get("completionDateStruct", {}).get("date", ""),
                })

            return {
                "query": device_name,
                "total_found": data.get("totalCount", 0),
                "returned": len(studies),
                "studies": studies,
                "search_url": f"https://clinicaltrials.gov/search?term={urllib.parse.quote(device_name)}",
                "searched_at": datetime.now(timezone.utc).isoformat(),
            }

        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            return {
                "query": device_name,
                "total_found": 0,
                "returned": 0,
                "studies": [],
                "error": f"ClinicalTrials.gov API error: {str(e)}",
                "search_url": f"https://clinicaltrials.gov/search?term={urllib.parse.quote(device_name)}",
                "searched_at": datetime.now(timezone.utc).isoformat(),
            }

    def get_study_details(self, nct_id: str) -> Dict:
        """Get detailed information for a specific study.

        Args:
            nct_id: ClinicalTrials.gov NCT ID (e.g., NCT12345678).

        Returns:
            Detailed study information.
        """
        url = f"{self.BASE_URL}/{nct_id}?format=json"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Tools/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            protocol = data.get("protocolSection", {})
            return {
                "nct_id": nct_id,
                "identification": protocol.get("identificationModule", {}),
                "status": protocol.get("statusModule", {}),
                "design": protocol.get("designModule", {}),
                "eligibility": protocol.get("eligibilityModule", {}),
                "outcomes": protocol.get("outcomesModule", {}),
                "contacts": protocol.get("contactsLocationsModule", {}),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }

        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            return {
                "nct_id": nct_id,
                "error": str(e),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }


# ==================================================================
# Informed Consent Template Generator
# ==================================================================

class InformedConsentGenerator:
    """Generate informed consent document templates compliant with
    21 CFR 50.25 requirements.

    Produces structured templates with all 9 required elements and
    device-specific risk descriptions.
    """

    def generate(
        self,
        device_name: str = "",
        device_description: str = "",
        study_type: str = "pivotal",
        study_title: str = "",
        sponsor_name: str = "",
        pi_name: str = "",
        pi_phone: str = "",
        irb_name: str = "",
        irb_phone: str = "",
        is_sr: bool = True,
        device_risks: Optional[List[str]] = None,
        study_duration: str = "",
        num_visits: int = 0,
        alternative_treatments: Optional[List[str]] = None,
    ) -> Dict:
        """Generate an informed consent template.

        Args:
            device_name: Name of investigational device.
            device_description: Brief description.
            study_type: Study type (pivotal, feasibility, etc.).
            study_title: Full study title.
            sponsor_name: Sponsor name.
            pi_name: Principal investigator name.
            pi_phone: PI contact phone.
            irb_name: IRB name.
            irb_phone: IRB contact phone.
            is_sr: Whether device is SR (affects compensation section).
            device_risks: List of device-specific risks.
            study_duration: Expected study duration text.
            num_visits: Number of study visits.
            alternative_treatments: List of alternative treatments.

        Returns:
            Informed consent template with all required elements.
        """
        if not device_risks:
            device_risks = [
                "[DEVICE-SPECIFIC RISK 1 - e.g., device migration]",
                "[DEVICE-SPECIFIC RISK 2 - e.g., infection at implant site]",
                "[DEVICE-SPECIFIC RISK 3 - e.g., device malfunction]",
            ]

        if not alternative_treatments:
            alternative_treatments = [
                "[ALTERNATIVE 1 - e.g., standard surgical procedure]",
                "[ALTERNATIVE 2 - e.g., medical management]",
                "[ALTERNATIVE 3 - e.g., no treatment / watchful waiting]",
            ]

        # Build the 9 required elements per 21 CFR 50.25(a)
        elements = self._build_required_elements(
            device_name, device_description, study_type, study_title,
            sponsor_name, pi_name, pi_phone, irb_name, irb_phone,
            is_sr, device_risks, study_duration, num_visits,
            alternative_treatments,
        )

        # Build additional elements per 21 CFR 50.25(b)
        additional = self._build_additional_elements(
            device_name, study_type, num_visits
        )

        # Generate full template text
        template_text = self._render_template(
            elements, additional, study_title, device_name
        )

        return {
            "device_name": device_name,
            "study_type": study_type,
            "study_title": study_title or "[STUDY TITLE]",
            "is_significant_risk": is_sr,
            "required_elements_count": len(elements),
            "required_elements": elements,
            "additional_elements": additional,
            "template_text": template_text,
            "compliance_checklist": self._get_compliance_checklist(),
            "reading_level_target": "8th grade (Flesch-Kincaid)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "This is a TEMPLATE. Must be customized for specific study, "
                "reviewed by IRB, and approved before use. Not for direct use."
            ),
        }

    def _build_required_elements(
        self, device_name, device_description, study_type, study_title,
        sponsor_name, pi_name, pi_phone, irb_name, irb_phone,
        is_sr, device_risks, study_duration, num_visits, alternatives,
    ) -> List[Dict]:
        """Build the 9 required informed consent elements."""
        return [
            {
                "element_number": 1,
                "cfr_ref": "21 CFR 50.25(a)(1)",
                "title": "Research Statement and Duration",
                "required": True,
                "template_text": (
                    f"You are being asked to take part in a research study. "
                    f"This study involves the use of an investigational "
                    f"(experimental) device called {device_name or '[DEVICE NAME]'}. "
                    f"{device_description or '[BRIEF DEVICE DESCRIPTION]'} "
                    f"Your participation in this study is expected to last "
                    f"{study_duration or '[DURATION, e.g., 24 months]'} "
                    f"and will involve approximately "
                    f"{num_visits or '[NUMBER]'} study visits."
                ),
            },
            {
                "element_number": 2,
                "cfr_ref": "21 CFR 50.25(a)(2)",
                "title": "Description of Procedures",
                "required": True,
                "template_text": (
                    f"If you agree to participate, the following procedures will be performed:\n"
                    f"- Screening: [DESCRIBE screening procedures]\n"
                    f"- Study Procedure: [DESCRIBE the investigational procedure using {device_name or 'the device'}]\n"
                    f"- Follow-up Visits: [DESCRIBE follow-up schedule and assessments]\n\n"
                    f"The experimental part of this study is the use of {device_name or '[DEVICE NAME]'}. "
                    f"[EXPLAIN what makes this experimental vs. standard care]"
                ),
            },
            {
                "element_number": 3,
                "cfr_ref": "21 CFR 50.25(a)(3)",
                "title": "Risks and Discomforts",
                "required": True,
                "template_text": (
                    f"The risks of this study include:\n\n"
                    f"Risks related to {device_name or 'the device'}:\n"
                    + "\n".join(f"- {risk}" for risk in device_risks)
                    + "\n\n"
                    f"Risks related to the study procedure:\n"
                    f"- [PROCEDURE-SPECIFIC RISKS, e.g., bleeding, infection, anesthesia risks]\n\n"
                    f"There may be other risks that are not known at this time."
                ),
            },
            {
                "element_number": 4,
                "cfr_ref": "21 CFR 50.25(a)(4)",
                "title": "Benefits",
                "required": True,
                "template_text": (
                    f"You may or may not benefit from participating in this study. "
                    f"Possible benefits include [DESCRIBE potential benefits, e.g., "
                    f"improvement in symptoms, reduced need for future procedures]. "
                    f"There is no guarantee that you will receive any benefit from "
                    f"participation. The information learned from this study may help "
                    f"others in the future."
                ),
            },
            {
                "element_number": 5,
                "cfr_ref": "21 CFR 50.25(a)(5)",
                "title": "Alternative Treatments",
                "required": True,
                "template_text": (
                    f"Instead of being in this study, you have the following options:\n"
                    + "\n".join(f"- {alt}" for alt in alternatives)
                    + "\n\n"
                    f"Your doctor can explain each of these options to you."
                ),
            },
            {
                "element_number": 6,
                "cfr_ref": "21 CFR 50.25(a)(6)",
                "title": "Confidentiality",
                "required": True,
                "template_text": (
                    f"Your study records will be kept confidential to the extent "
                    f"permitted by law. However, the following parties may review "
                    f"your records:\n"
                    f"- The study sponsor ({sponsor_name or '[SPONSOR NAME]'})\n"
                    f"- The U.S. Food and Drug Administration (FDA)\n"
                    f"- The Institutional Review Board ({irb_name or '[IRB NAME]'})\n"
                    f"- Study monitors and auditors\n\n"
                    f"Your name will not be used in any published reports."
                ),
            },
            {
                "element_number": 7,
                "cfr_ref": "21 CFR 50.25(a)(7)",
                "title": "Compensation for Injury",
                "required": is_sr,
                "template_text": (
                    f"If you are injured as a result of being in this study, "
                    f"[DESCRIBE what medical treatment and/or compensation is available]. "
                    f"[IMPORTANT: Do NOT include exculpatory language such as "
                    f"'you waive your right to sue' - this is prohibited by 21 CFR 50.20]"
                    if is_sr else
                    f"This study involves a non-significant risk device. "
                    f"If you experience any problems related to the study, "
                    f"please contact the study doctor."
                ),
            },
            {
                "element_number": 8,
                "cfr_ref": "21 CFR 50.25(a)(8)",
                "title": "Contact Information",
                "required": True,
                "template_text": (
                    f"If you have questions about this study, contact:\n"
                    f"- Study Doctor: {pi_name or '[PI NAME]'}, "
                    f"Phone: {pi_phone or '[PI PHONE]'}\n\n"
                    f"If you have questions about your rights as a research subject, contact:\n"
                    f"- {irb_name or '[IRB NAME]'}, "
                    f"Phone: {irb_phone or '[IRB PHONE]'}\n\n"
                    f"If you experience a study-related injury, contact:\n"
                    f"- {pi_name or '[PI NAME]'} at {pi_phone or '[PI PHONE]'} "
                    f"(24-hour emergency contact: [EMERGENCY PHONE])"
                ),
            },
            {
                "element_number": 9,
                "cfr_ref": "21 CFR 50.25(a)(9)",
                "title": "Voluntary Participation",
                "required": True,
                "template_text": (
                    f"Your participation in this study is voluntary. You may choose "
                    f"not to participate or you may withdraw at any time without "
                    f"penalty or loss of benefits to which you are otherwise entitled. "
                    f"Your decision will not affect your future medical care."
                ),
            },
        ]

    def _build_additional_elements(
        self, device_name, study_type, num_visits,
    ) -> List[Dict]:
        """Build additional elements per 21 CFR 50.25(b)."""
        return [
            {
                "cfr_ref": "21 CFR 50.25(b)(1)",
                "title": "Pregnancy Risk",
                "template_text": (
                    f"If you are pregnant or become pregnant during this study, "
                    f"the {device_name or 'device'} may pose risks to an unborn "
                    f"baby. [DESCRIBE known or potential risks to fetus]. "
                    f"You should use effective birth control during this study."
                ),
            },
            {
                "cfr_ref": "21 CFR 50.25(b)(2)",
                "title": "Termination by Investigator",
                "template_text": (
                    f"The study doctor may withdraw you from this study without "
                    f"your consent if: [LIST conditions, e.g., health deterioration, "
                    f"non-compliance with protocol, device malfunction, study terminated]."
                ),
            },
            {
                "cfr_ref": "21 CFR 50.25(b)(3)",
                "title": "Additional Costs",
                "template_text": (
                    f"[DESCRIBE any additional costs to the subject, e.g., "
                    f"travel costs, time off work, or state that there are no additional costs]."
                ),
            },
            {
                "cfr_ref": "21 CFR 50.25(b)(5)",
                "title": "New Findings",
                "template_text": (
                    f"During the study, if we learn new information that may affect "
                    f"your willingness to continue participating, we will tell you "
                    f"about these findings."
                ),
            },
            {
                "cfr_ref": "21 CFR 50.25(b)(6)",
                "title": "Number of Subjects",
                "template_text": (
                    f"Approximately [NUMBER] people will participate in this study "
                    f"at approximately [NUMBER] study sites."
                ),
            },
        ]

    def _render_template(
        self, elements, additional, study_title, device_name,
    ) -> str:
        """Render the complete informed consent template as text."""
        lines = [
            "=" * 70,
            "INFORMED CONSENT FORM",
            "[TEMPLATE - MUST BE CUSTOMIZED AND IRB-APPROVED BEFORE USE]",
            "=" * 70,
            "",
            f"Study Title: {study_title or '[FULL STUDY TITLE]'}",
            f"Sponsor: [SPONSOR NAME]",
            f"Principal Investigator: [PI NAME]",
            f"IRB Protocol Number: [PROTOCOL NUMBER]",
            f"IRB Approval Date: [DATE]",
            "",
            "-" * 70,
        ]

        for elem in elements:
            lines.append("")
            lines.append(f"--- {elem['title']} ({elem['cfr_ref']}) ---")
            lines.append(elem["template_text"])

        lines.append("")
        lines.append("-" * 70)
        lines.append("ADDITIONAL INFORMATION")
        lines.append("-" * 70)

        for elem in additional:
            lines.append("")
            lines.append(f"--- {elem['title']} ({elem['cfr_ref']}) ---")
            lines.append(elem["template_text"])

        lines.extend([
            "",
            "=" * 70,
            "SIGNATURE",
            "=" * 70,
            "",
            "I have read this consent form (or it has been read to me).",
            "I have had the opportunity to ask questions and my questions have been answered.",
            "I agree to participate in this research study.",
            "",
            "___________________________________    _______________",
            "Subject Signature                      Date",
            "",
            "___________________________________",
            "Printed Name of Subject",
            "",
            "___________________________________    _______________",
            "Signature of Person Obtaining Consent   Date",
            "",
            "___________________________________",
            "Printed Name of Person Obtaining Consent",
            "",
            "=" * 70,
            "CAUTION: This is a TEMPLATE. Must be customized for specific study,",
            "reviewed by IRB, and approved before use.",
            "=" * 70,
        ])

        return "\n".join(lines)

    def _get_compliance_checklist(self) -> List[Dict]:
        """Get informed consent compliance checklist."""
        return [
            {"item": "All 9 required elements present (21 CFR 50.25(a))", "status": "CHECK"},
            {"item": "No exculpatory language (21 CFR 50.20)", "status": "CHECK"},
            {"item": "Written at 8th-grade reading level", "status": "CHECK"},
            {"item": "Device-specific risks described (not generic)", "status": "CHECK"},
            {"item": "Alternative treatments listed", "status": "CHECK"},
            {"item": "Contact information complete (PI + IRB + emergency)", "status": "CHECK"},
            {"item": "Voluntary participation statement present", "status": "CHECK"},
            {"item": "Compensation for injury described (if SR study)", "status": "CHECK"},
            {"item": "Confidentiality statement includes FDA/IRB access", "status": "CHECK"},
            {"item": "Signature block for subject and person obtaining consent", "status": "CHECK"},
            {"item": "IRB-approved version number and date", "status": "CHECK"},
        ]


# ==================================================================
# 21 CFR 812 Compliance Checklist
# ==================================================================

class IDEComplianceChecklist:
    """21 CFR 812 compliance checklist for IDE submissions.

    Evaluates submission data against all applicable requirements and
    generates a compliance score with deficiency report.
    """

    def __init__(self):
        """Initialize with compliance requirements."""
        self._requirements = COMPLIANCE_REQUIREMENTS

    def evaluate(
        self,
        submission_data: Optional[Dict] = None,
        is_sr: bool = True,
    ) -> Dict:
        """Evaluate compliance against 21 CFR 812 requirements.

        Args:
            submission_data: Dict describing submission status for each
                           requirement (optional).
            is_sr: Whether device is SR (affects requirement applicability).

        Returns:
            Compliance report with scores, deficiencies, and recommendations.
        """
        results = []
        compliant_count = 0
        deficiency_count = 0
        na_count = 0

        for req in self._requirements:
            req_id = req["id"]

            # Check if requirement is applicable
            if not is_sr and req["cfr_ref"].startswith("21 CFR 812.20"):
                status = "NOT_APPLICABLE"
                na_count += 1
            elif submission_data and req_id in submission_data:
                status = submission_data[req_id]
                if status == "COMPLIANT":
                    compliant_count += 1
                elif status == "DEFICIENT":
                    deficiency_count += 1
            else:
                status = "NOT_EVALUATED"

            results.append({
                "id": req_id,
                "category": req["category"],
                "cfr_ref": req["cfr_ref"],
                "requirement": req["requirement"],
                "priority": req["priority"],
                "status": status,
            })

        # Calculate compliance score
        evaluated = compliant_count + deficiency_count
        compliance_score = (
            round(compliant_count / evaluated * 100)
            if evaluated > 0 else 0
        )

        # Identify critical deficiencies
        critical_deficiencies = [
            r for r in results
            if r["status"] == "DEFICIENT" and r["priority"] == "CRITICAL"
        ]

        return {
            "total_requirements": len(results),
            "compliant": compliant_count,
            "deficient": deficiency_count,
            "not_evaluated": len(results) - evaluated - na_count,
            "not_applicable": na_count,
            "compliance_score": compliance_score,
            "is_significant_risk": is_sr,
            "results": results,
            "critical_deficiencies": critical_deficiencies,
            "recommendation": (
                "READY FOR SUBMISSION" if compliance_score >= 95 and not critical_deficiencies
                else "DEFICIENCIES MUST BE RESOLVED" if critical_deficiencies
                else "REVIEW NEEDED"
            ),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_requirements(
        self,
        category: str = "",
        priority: str = "",
    ) -> List[Dict]:
        """Get filtered requirements.

        Args:
            category: Filter by category.
            priority: Filter by priority.

        Returns:
            Filtered requirement list.
        """
        reqs = self._requirements
        if category:
            reqs = [r for r in reqs if r["category"] == category]
        if priority:
            reqs = [r for r in reqs if r["priority"] == priority]
        return reqs

    def get_informed_consent_elements(self) -> List[str]:
        """Get the 9 required informed consent elements from 21 CFR 50.25(a)."""
        for req in self._requirements:
            if req["id"] == "IDE-07":
                return req.get("elements", [])
        return []


# ==================================================================
# IRB Submission Package Generator
# ==================================================================

class IRBPackageGenerator:
    """Generate IRB submission package outlines for IDE studies.

    Creates structured package outlines with required documents for
    initial IRB review, continuing review, and amendments.
    """

    def generate(
        self,
        device_name: str = "",
        study_title: str = "",
        is_sr: bool = True,
        submission_type: str = "initial",
        pi_name: str = "",
        num_subjects: int = 0,
        num_sites: int = 1,
    ) -> Dict:
        """Generate IRB submission package outline.

        Args:
            device_name: Device name.
            study_title: Study title.
            is_sr: Whether SR (affects package requirements).
            submission_type: "initial", "continuing_review", or "amendment".
            pi_name: Principal investigator name.
            num_subjects: Expected enrollment.
            num_sites: Number of sites.

        Returns:
            IRB package outline with required documents and checklist.
        """
        if submission_type == "initial":
            documents = self._initial_review_documents(is_sr)
        elif submission_type == "continuing_review":
            documents = self._continuing_review_documents()
        elif submission_type == "amendment":
            documents = self._amendment_documents()
        else:
            documents = self._initial_review_documents(is_sr)

        checklist = []
        for i, doc in enumerate(documents, 1):
            checklist.append({
                "number": i,
                "document": doc["title"],
                "cfr_ref": doc.get("cfr_ref", ""),
                "required": doc["required"],
                "status": "NOT_STARTED",
                "notes": doc.get("notes", ""),
            })

        return {
            "device_name": device_name,
            "study_title": study_title or "[STUDY TITLE]",
            "submission_type": submission_type,
            "is_significant_risk": is_sr,
            "pi_name": pi_name or "[PI NAME]",
            "num_subjects": num_subjects,
            "num_sites": num_sites,
            "total_documents": len(checklist),
            "documents": checklist,
            "irb_review_timeline": {
                "initial": "4-6 weeks for full board review",
                "expedited": "2-3 weeks (minimal risk studies only)",
                "continuing_review": "4-6 weeks",
                "amendment": "2-4 weeks (depends on significance)",
            },
            "regulatory_references": [
                "21 CFR 56 - Institutional Review Boards",
                "21 CFR 50 - Protection of Human Subjects",
                "21 CFR 812 - Investigational Device Exemptions",
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _initial_review_documents(self, is_sr: bool) -> List[Dict]:
        """Documents required for initial IRB review."""
        docs = [
            {
                "title": "IRB Application Form",
                "cfr_ref": "21 CFR 56.108",
                "required": True,
            },
            {
                "title": "Clinical Protocol",
                "cfr_ref": "21 CFR 812.25",
                "required": True,
            },
            {
                "title": "Informed Consent Form",
                "cfr_ref": "21 CFR 50.25",
                "required": True,
            },
            {
                "title": "Investigator Brochure / Device Description",
                "cfr_ref": "21 CFR 812.20(b)(5)",
                "required": True,
            },
            {
                "title": "SR/NSR Determination Justification",
                "cfr_ref": "21 CFR 812.2(b)",
                "required": True,
            },
            {
                "title": "Investigator CV and Medical License",
                "cfr_ref": "21 CFR 812.43",
                "required": True,
            },
            {
                "title": "Financial Disclosure (Form FDA 3454/3455)",
                "cfr_ref": "21 CFR 54",
                "required": True,
            },
            {
                "title": "Recruitment Materials (ads, flyers)",
                "cfr_ref": "21 CFR 56.111",
                "required": False,
                "notes": "Required if using recruitment materials",
            },
            {
                "title": "Data Safety Monitoring Plan",
                "cfr_ref": "21 CFR 812.46",
                "required": True,
            },
        ]

        if is_sr:
            docs.append({
                "title": "FDA IDE Approval Letter",
                "cfr_ref": "21 CFR 812.20",
                "required": True,
                "notes": "SR devices require FDA IDE approval before study start",
            })

        return docs

    def _continuing_review_documents(self) -> List[Dict]:
        """Documents for continuing (annual) review."""
        return [
            {
                "title": "Continuing Review Application Form",
                "cfr_ref": "21 CFR 56.109(f)",
                "required": True,
            },
            {
                "title": "Progress Report (enrollment, status, safety summary)",
                "cfr_ref": "21 CFR 56.109(f)",
                "required": True,
            },
            {
                "title": "Current Informed Consent Form",
                "cfr_ref": "21 CFR 50.25",
                "required": True,
            },
            {
                "title": "Summary of Adverse Events",
                "cfr_ref": "21 CFR 812.150",
                "required": True,
            },
            {
                "title": "Protocol Deviations Summary",
                "cfr_ref": "21 CFR 812.110",
                "required": True,
            },
            {
                "title": "Current Protocol (with amendments)",
                "cfr_ref": "21 CFR 812.25",
                "required": True,
            },
        ]

    def _amendment_documents(self) -> List[Dict]:
        """Documents for protocol amendment."""
        return [
            {
                "title": "Amendment Application Form",
                "cfr_ref": "21 CFR 56.108",
                "required": True,
            },
            {
                "title": "Summary of Changes (tracked changes)",
                "cfr_ref": "21 CFR 812.35",
                "required": True,
            },
            {
                "title": "Revised Protocol",
                "cfr_ref": "21 CFR 812.25",
                "required": True,
            },
            {
                "title": "Revised Informed Consent (if affected)",
                "cfr_ref": "21 CFR 50.25",
                "required": False,
                "notes": "Required if changes affect subject risk or participation",
            },
            {
                "title": "Justification for Changes",
                "cfr_ref": "21 CFR 812.35",
                "required": True,
            },
        ]


# ==================================================================
# CLI Entry Point
# ==================================================================

def main():
    parser = argparse.ArgumentParser(
        description="IDE Pathway Support Tools (FDA-67)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # sr-nsr command
    sr_p = subparsers.add_parser("sr-nsr", help="SR/NSR determination")
    sr_p.add_argument("--device", required=True, help="Device name")
    sr_p.add_argument("--implant", action="store_true")
    sr_p.add_argument("--duration", type=int, default=0, help="Implant duration (days)")
    sr_p.add_argument("--anatomy", default="", help="Anatomical site")
    sr_p.add_argument("--cardiac", action="store_true")
    sr_p.add_argument("--neural", action="store_true")
    sr_p.add_argument("--life-sustaining", action="store_true")
    sr_p.add_argument("--failure", default="", help="Worst-case failure outcome")
    sr_p.add_argument("--json", action="store_true")

    # outline command
    out_p = subparsers.add_parser("outline", help="Generate IDE outline")
    out_p.add_argument("--device", required=True, help="Device name")
    out_p.add_argument("--risk", default="SR", help="SR or NSR")
    out_p.add_argument("--study-type", default="pivotal", help="Study type")
    out_p.add_argument("--json", action="store_true")

    # consent command
    con_p = subparsers.add_parser("consent", help="Generate informed consent")
    con_p.add_argument("--device", required=True, help="Device name")
    con_p.add_argument("--study", default="pivotal", help="Study type")
    con_p.add_argument("--json", action="store_true")

    # checklist command
    chk_p = subparsers.add_parser("checklist", help="IDE compliance checklist")
    chk_p.add_argument("--sr", action="store_true", default=True)
    chk_p.add_argument("--nsr", action="store_true")
    chk_p.add_argument("--json", action="store_true")

    # search command
    sea_p = subparsers.add_parser("search", help="Search ClinicalTrials.gov")
    sea_p.add_argument("--device", required=True, help="Device keyword")
    sea_p.add_argument("--max", type=int, default=10, help="Max results")
    sea_p.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "sr-nsr":
        anatomy = args.anatomy
        if args.cardiac:
            anatomy = "cardiac"
        elif args.neural:
            anatomy = "neural"
        det = SRNSRDetermination()
        result = det.evaluate(
            device_name=args.device,
            is_implant=args.implant,
            implant_duration_days=args.duration,
            anatomical_site=anatomy,
            is_life_sustaining=args.life_sustaining,
            failure_severity=args.failure,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Device: {result['device_name']}")
            print(f"Determination: {result['determination_label']}")
            print(f"Risk Score: {result['risk_score']}/{result['sr_threshold']} (threshold)")
            print(f"Regulatory Path: {result['regulatory_path']}")
            for step in result["next_steps"]:
                print(f"  {step}")

    elif args.command == "outline":
        gen = IDESubmissionOutline()
        result = gen.generate(
            device_name=args.device,
            risk=args.risk,
            study_type=args.study_type,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"IDE Outline: {result['device_name']} ({result['risk_determination']})")
            print(f"Sections: {result['total_sections']}")
            for s in result["sections"]:
                print(f"  {s['section']}. {s['title']} [{s['cfr_ref']}]")

    elif args.command == "consent":
        gen = InformedConsentGenerator()
        result = gen.generate(
            device_name=args.device,
            study_type=args.study,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(result["template_text"])

    elif args.command == "checklist":
        chk = IDEComplianceChecklist()
        is_sr = not args.nsr
        result = chk.evaluate(is_sr=is_sr)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"IDE Compliance Checklist ({'SR' if is_sr else 'NSR'})")
            print(f"Total Requirements: {result['total_requirements']}")
            for r in result["results"]:
                print(f"  [{r['priority']:8s}] {r['id']}: {r['requirement'][:60]}")

    elif args.command == "search":
        ct = ClinicalTrialsIntegration()
        result = ct.search_device_studies(args.device, max_results=args.max)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"ClinicalTrials.gov Results for '{result['query']}'")
            print(f"Total Found: {result['total_found']}")
            for s in result["studies"]:
                print(f"  {s['nct_id']}: {s['title'][:60]} [{s['status']}]")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
