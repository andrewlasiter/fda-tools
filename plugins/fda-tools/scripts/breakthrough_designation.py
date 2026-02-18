#!/usr/bin/env python3
"""
Breakthrough Device Designation Support -- FDA-43

Templates and tracking for FDA Breakthrough Device Designation requests
per Section 515B of the FD&C Act (21 U.S.C. 360e-3).

A Breakthrough Device designation is intended for devices that provide
more effective treatment or diagnosis of life-threatening or irreversibly
debilitating diseases, and meet one of the following criteria:
    1. Represents breakthrough technology
    2. No approved or cleared alternatives exist
    3. Offers significant advantages over existing alternatives
    4. Device availability is in the best interest of patients

This module provides:
    - Breakthrough designation request template generation
    - Life-threatening condition justification templates
    - Unmet medical need analysis templates
    - Sprint review process tracking
    - Interactive review documentation

Usage:
    from breakthrough_designation import BreakthroughDesignation

    bt = BreakthroughDesignation()
    request = bt.generate_request_template("MyDevice", "cardiology")
    justification = bt.generate_condition_justification("heart_failure")
    analysis = bt.generate_unmet_need_analysis("MyDevice", "DEN200001")
    tracker = bt.create_sprint_review_tracker("MyDevice")

    # CLI usage:
    python3 breakthrough_designation.py --device "MyDevice" --specialty cardiology
    python3 breakthrough_designation.py --device "MyDevice" --condition heart_failure
    python3 breakthrough_designation.py --device "MyDevice" --sprint-tracker
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# Import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------
# Statutory criteria for Breakthrough Device Designation
# ------------------------------------------------------------------

BREAKTHROUGH_CRITERIA = {
    "breakthrough_technology": {
        "label": "Breakthrough Technology",
        "cfr_ref": "Section 515B(a)(1)(A)",
        "description": (
            "The device represents a breakthrough technology for which "
            "no approved or cleared alternatives exist."
        ),
        "evidence_needed": [
            "Description of novel technology mechanism",
            "Patent or IP documentation (optional)",
            "Comparison table showing no existing alternatives",
            "Literature search demonstrating technology gap",
        ],
    },
    "no_alternatives": {
        "label": "No Approved/Cleared Alternatives",
        "cfr_ref": "Section 515B(a)(1)(B)",
        "description": (
            "No approved or cleared alternatives exist for the device."
        ),
        "evidence_needed": [
            "FDA database search results showing no cleared/approved predicates",
            "Clinical literature review showing unmet need",
            "Expert opinion letters (optional)",
            "Professional society position statements (optional)",
        ],
    },
    "significant_advantages": {
        "label": "Significant Advantages Over Existing Alternatives",
        "cfr_ref": "Section 515B(a)(1)(C)",
        "description": (
            "The device offers significant advantages over existing "
            "approved or cleared alternatives, including the potential "
            "to reduce or eliminate the need for hospitalization, "
            "improve patient quality of life, facilitate patients' "
            "ability to manage their own health or reduce healthcare "
            "costs."
        ),
        "evidence_needed": [
            "Side-by-side comparison with existing alternatives",
            "Clinical evidence of superiority (if available)",
            "Patient outcome improvements (quantified)",
            "Cost-effectiveness analysis (optional)",
            "Quality of life impact assessment",
        ],
    },
    "best_interest": {
        "label": "Best Interest of Patients",
        "cfr_ref": "Section 515B(a)(1)(D)",
        "description": (
            "The availability of the device is in the best interest "
            "of patients."
        ),
        "evidence_needed": [
            "Patient population size and demographics",
            "Current treatment pathway limitations",
            "Risk-benefit analysis for target population",
            "Patient advocacy group support (optional)",
            "Epidemiological data on disease burden",
        ],
    },
}


# ------------------------------------------------------------------
# Life-threatening/irreversibly debilitating condition categories
# ------------------------------------------------------------------

CONDITION_CATEGORIES = {
    "cardiovascular": {
        "label": "Cardiovascular Conditions",
        "conditions": [
            "Heart failure (HFrEF/HFpEF)",
            "Acute myocardial infarction",
            "Sudden cardiac death / cardiac arrest",
            "Aortic stenosis / valve disease",
            "Pulmonary hypertension",
            "Peripheral arterial disease (critical limb ischemia)",
        ],
        "mortality_data": "CVD is the leading cause of death globally (17.9M deaths/year, WHO 2024)",
        "regulatory_context": "Cardiovascular devices often qualify for expedited review pathways",
    },
    "oncology": {
        "label": "Oncology Conditions",
        "conditions": [
            "Solid tumors (unresectable/metastatic)",
            "Hematologic malignancies",
            "Brain tumors (glioblastoma)",
            "Pancreatic cancer",
            "Rare cancers with no standard of care",
        ],
        "mortality_data": "Cancer causes ~10M deaths/year globally (WHO 2024)",
        "regulatory_context": "Companion diagnostics and treatment devices frequently qualify",
    },
    "neurological": {
        "label": "Neurological Conditions",
        "conditions": [
            "Stroke (ischemic/hemorrhagic)",
            "Epilepsy (drug-resistant)",
            "Parkinson's disease",
            "Alzheimer's disease",
            "Traumatic brain injury",
            "Spinal cord injury",
        ],
        "mortality_data": "Neurological disorders affect >3B people worldwide (Lancet 2024)",
        "regulatory_context": "Neurostimulation and diagnostic devices may qualify",
    },
    "respiratory": {
        "label": "Respiratory Conditions",
        "conditions": [
            "ARDS (Acute Respiratory Distress Syndrome)",
            "COPD (severe/end-stage)",
            "Pulmonary fibrosis",
            "Lung cancer",
            "Cystic fibrosis",
        ],
        "mortality_data": "Chronic respiratory diseases cause ~4M deaths/year (WHO 2024)",
        "regulatory_context": "Ventilation and monitoring devices may qualify",
    },
    "rare_disease": {
        "label": "Rare Disease Conditions",
        "conditions": [
            "Orphan diseases (<200,000 affected in US)",
            "Ultra-rare diseases (<1,000 affected in US)",
            "Genetic disorders without treatment",
            "Pediatric rare diseases",
        ],
        "mortality_data": "~7,000 rare diseases affect 25-30M Americans (NIH 2024)",
        "regulatory_context": "Humanitarian Device Exemption (HDE) may also apply",
    },
    "infectious_disease": {
        "label": "Infectious Disease Conditions",
        "conditions": [
            "Sepsis / septic shock",
            "Drug-resistant infections (MRSA, CRE)",
            "Emerging infectious diseases",
            "HIV/AIDS complications",
            "Tuberculosis (drug-resistant)",
        ],
        "mortality_data": "Infectious diseases cause ~13M deaths/year (WHO 2024)",
        "regulatory_context": "Diagnostic devices for ID frequently qualify for expedited review",
    },
}


# ------------------------------------------------------------------
# Sprint review milestones for Breakthrough designation
# ------------------------------------------------------------------

SPRINT_REVIEW_MILESTONES = [
    {
        "id": "pre_submission",
        "label": "Pre-Submission Meeting Request",
        "description": "Submit Q-Sub requesting pre-submission meeting to discuss Breakthrough designation",
        "typical_week": 1,
        "deliverables": [
            "Pre-submission meeting request letter",
            "Device description summary",
            "Intended use statement",
            "Preliminary clinical evidence summary",
        ],
    },
    {
        "id": "designation_request",
        "label": "Breakthrough Designation Request Submission",
        "description": "Submit formal Breakthrough Device Designation request to CDRH",
        "typical_week": 4,
        "deliverables": [
            "Completed FDA Form 3913",
            "Device description and intended use",
            "Life-threatening condition justification",
            "Unmet medical need analysis",
            "Preliminary evidence of device benefits",
            "Comparison with existing alternatives",
        ],
    },
    {
        "id": "fda_feedback",
        "label": "FDA Feedback on Designation Request",
        "description": "FDA provides decision on Breakthrough designation (within 60 days)",
        "typical_week": 12,
        "deliverables": [
            "FDA determination letter",
            "Review of any FDA questions or requests",
            "Gap analysis of missing information",
        ],
    },
    {
        "id": "sprint_1_planning",
        "label": "Sprint 1: Development Planning",
        "description": "Initial sprint discussion with FDA review team on development plan",
        "typical_week": 14,
        "deliverables": [
            "Clinical study protocol outline",
            "Non-clinical testing plan",
            "Manufacturing and quality plan",
            "Regulatory strategy document",
        ],
    },
    {
        "id": "sprint_2_nonclinical",
        "label": "Sprint 2: Non-Clinical Data Review",
        "description": "Interactive review of bench testing and non-clinical data",
        "typical_week": 20,
        "deliverables": [
            "Bench test results",
            "Biocompatibility data",
            "Software verification (if applicable)",
            "Electrical safety testing (if applicable)",
        ],
    },
    {
        "id": "sprint_3_clinical",
        "label": "Sprint 3: Clinical Evidence Review",
        "description": "Interactive review of clinical protocol and available clinical data",
        "typical_week": 28,
        "deliverables": [
            "Clinical study protocol (final or near-final)",
            "Interim clinical data (if available)",
            "Risk-benefit analysis",
            "Patient-reported outcomes plan",
        ],
    },
    {
        "id": "sprint_4_presubmission",
        "label": "Sprint 4: Pre-Submission Review",
        "description": "Final pre-submission review before marketing application",
        "typical_week": 40,
        "deliverables": [
            "Complete clinical study report",
            "Updated risk analysis",
            "Labeling draft",
            "Manufacturing documentation",
            "Post-market surveillance plan",
        ],
    },
    {
        "id": "submission",
        "label": "Marketing Application Submission",
        "description": "Submit PMA, De Novo, or 510(k) with Breakthrough designation benefits",
        "typical_week": 48,
        "deliverables": [
            "Complete marketing application",
            "Breakthrough designation reference",
            "All supporting data and documentation",
        ],
    },
    {
        "id": "priority_review",
        "label": "Priority Review Period",
        "description": "FDA prioritized review of marketing application",
        "typical_week": 60,
        "deliverables": [
            "Response to any FDA questions",
            "Additional data requests (if any)",
            "Advisory committee preparation (if required)",
        ],
    },
    {
        "id": "decision",
        "label": "FDA Decision",
        "description": "FDA marketing authorization decision",
        "typical_week": 72,
        "deliverables": [
            "FDA approval/clearance letter",
            "Conditions of approval (if any)",
            "Post-market commitments",
        ],
    },
]


# ------------------------------------------------------------------
# Interactive review documentation templates
# ------------------------------------------------------------------

INTERACTIVE_REVIEW_SECTIONS = {
    "meeting_summary": {
        "label": "Meeting Summary",
        "template_fields": [
            "meeting_date",
            "meeting_type",
            "fda_attendees",
            "sponsor_attendees",
            "topics_discussed",
            "key_agreements",
            "action_items",
            "next_meeting_date",
        ],
    },
    "data_package": {
        "label": "Data Package for Interactive Review",
        "template_fields": [
            "device_description",
            "intended_use",
            "clinical_data_summary",
            "non_clinical_data_summary",
            "risk_analysis_summary",
            "manufacturing_overview",
            "labeling_overview",
        ],
    },
    "fda_feedback_log": {
        "label": "FDA Feedback Log",
        "template_fields": [
            "feedback_date",
            "feedback_source",
            "topic",
            "fda_comment",
            "sponsor_response",
            "resolution_status",
            "impact_on_timeline",
        ],
    },
    "action_item_tracker": {
        "label": "Action Item Tracker",
        "template_fields": [
            "action_item_id",
            "description",
            "assigned_to",
            "due_date",
            "status",
            "completion_date",
            "notes",
        ],
    },
}


# ------------------------------------------------------------------
# BreakthroughDesignation class
# ------------------------------------------------------------------

class BreakthroughDesignation:
    """Breakthrough Device Designation request generator and tracker.

    Generates templates for designation requests, condition justifications,
    unmet medical need analyses, and sprint review process tracking.
    """

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize Breakthrough Designation support.

        Args:
            output_dir: Directory for output files. Defaults to
                        ~/fda-510k-data/breakthrough_designation/
        """
        self.output_dir = output_dir or os.path.expanduser(
            "~/fda-510k-data/breakthrough_designation"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Request template generation
    # ------------------------------------------------------------------

    def generate_request_template(
        self,
        device_name: str,
        specialty: str = "",
        intended_use: str = "",
        criteria: Optional[List[str]] = None,
    ) -> Dict:
        """Generate a Breakthrough Device Designation request template.

        Args:
            device_name: Name of the device.
            specialty: Medical specialty area (e.g., "cardiology").
            intended_use: Device intended use statement.
            criteria: List of breakthrough criteria keys to include.
                      If None, all criteria are included.

        Returns:
            Request template dict with all required sections.
        """
        if criteria is None:
            criteria = list(BREAKTHROUGH_CRITERIA.keys())

        # Build criteria sections
        criteria_sections = []
        for criterion_key in criteria:
            criterion = BREAKTHROUGH_CRITERIA.get(criterion_key)
            if criterion:
                criteria_sections.append({
                    "criterion": criterion_key,
                    "label": criterion["label"],
                    "cfr_ref": criterion["cfr_ref"],
                    "description": criterion["description"],
                    "evidence_needed": criterion["evidence_needed"],
                    "evidence_provided": [],  # To be filled by user
                    "status": "NOT_STARTED",
                })

        template = {
            "document_type": "Breakthrough Device Designation Request",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "regulatory_reference": "Section 515B of the FD&C Act (21 U.S.C. 360e-3)",
            "fda_form": "FDA Form 3913",
            "device_information": {
                "device_name": device_name,
                "trade_name": "",  # To be filled
                "specialty": specialty,
                "intended_use": intended_use,
                "device_description": "",  # To be filled
                "product_code": "",  # To be filled
                "regulation_number": "",  # To be filled
                "device_class": "",  # To be filled
                "submission_type": "",  # PMA, De Novo, or 510(k)
            },
            "applicant_information": {
                "company_name": "",  # To be filled
                "contact_name": "",  # To be filled
                "contact_title": "",  # To be filled
                "contact_email": "",  # To be filled
                "contact_phone": "",  # To be filled
                "address": "",  # To be filled
                "establishment_registration": "",  # To be filled
            },
            "designation_criteria": criteria_sections,
            "life_threatening_justification": {
                "condition": "",  # To be filled
                "is_life_threatening": None,  # True/False
                "is_irreversibly_debilitating": None,  # True/False
                "justification_narrative": "",  # To be filled
                "supporting_references": [],  # To be filled
            },
            "unmet_medical_need": {
                "current_treatment_landscape": "",  # To be filled
                "limitations_of_existing_treatments": "",  # To be filled
                "device_advantages": "",  # To be filled
                "patient_population_size": "",  # To be filled
                "supporting_evidence": [],  # To be filled
            },
            "preliminary_evidence": {
                "bench_testing": [],  # To be filled
                "animal_studies": [],  # To be filled
                "clinical_data": [],  # To be filled
                "literature_references": [],  # To be filled
            },
            "submission_checklist": {
                "fda_form_3913_completed": False,
                "device_description_included": False,
                "intended_use_defined": False,
                "condition_justification_included": False,
                "unmet_need_analysis_included": False,
                "criteria_evidence_included": False,
                "preliminary_data_included": False,
                "comparison_with_alternatives_included": False,
                "cover_letter_included": False,
            },
            "estimated_timeline": {
                "designation_request_target": "",
                "fda_response_expected": "Within 60 calendar days of receipt",
                "notes": (
                    "FDA aims to respond within 60 days. If designated, "
                    "interactive review sprints begin shortly after."
                ),
            },
        }

        return template

    # ------------------------------------------------------------------
    # Life-threatening condition justification
    # ------------------------------------------------------------------

    def generate_condition_justification(
        self,
        condition_category: str,
        specific_condition: str = "",
        custom_conditions: Optional[List[str]] = None,
    ) -> Dict:
        """Generate a life-threatening condition justification template.

        Args:
            condition_category: Category key from CONDITION_CATEGORIES.
            specific_condition: Specific condition within the category.
            custom_conditions: Custom conditions not in predefined list.

        Returns:
            Condition justification template dict.
        """
        category = CONDITION_CATEGORIES.get(condition_category, {})

        conditions = list(category.get("conditions", []))
        if custom_conditions:
            conditions.extend(custom_conditions)

        template = {
            "document_type": "Life-Threatening Condition Justification",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "regulatory_reference": "Section 515B(a)(2) of the FD&C Act",
            "condition_category": {
                "category": condition_category,
                "label": category.get("label", condition_category),
                "conditions_in_scope": conditions,
                "specific_condition": specific_condition,
            },
            "justification_elements": {
                "life_threatening_criteria": {
                    "description": (
                        "A disease or condition is considered life-threatening "
                        "if it is likely to cause death if left untreated, or "
                        "if the use of the device is intended to prevent death."
                    ),
                    "applies": None,  # True/False -- to be filled
                    "narrative": "",  # To be filled
                    "mortality_rate": "",  # To be filled
                    "time_to_mortality": "",  # To be filled
                },
                "irreversibly_debilitating_criteria": {
                    "description": (
                        "A disease or condition is irreversibly debilitating "
                        "if it causes major irreversible morbidity -- a "
                        "substantial disruption of the ability to conduct "
                        "normal life functions."
                    ),
                    "applies": None,  # True/False -- to be filled
                    "narrative": "",  # To be filled
                    "disability_impact": "",  # To be filled
                    "irreversibility_evidence": "",  # To be filled
                },
            },
            "epidemiological_data": {
                "prevalence": "",  # To be filled
                "incidence": "",  # To be filled
                "mortality_data": category.get("mortality_data", ""),
                "disease_burden": "",  # To be filled
                "demographic_distribution": "",  # To be filled
            },
            "current_standard_of_care": {
                "approved_treatments": [],  # To be filled
                "approved_devices": [],  # To be filled
                "treatment_limitations": "",  # To be filled
                "unmet_needs": "",  # To be filled
            },
            "supporting_references": {
                "clinical_guidelines": [],  # To be filled
                "epidemiological_studies": [],  # To be filled
                "regulatory_precedents": [],  # To be filled
                "expert_opinions": [],  # To be filled
            },
            "regulatory_context": category.get("regulatory_context", ""),
        }

        return template

    # ------------------------------------------------------------------
    # Unmet medical need analysis
    # ------------------------------------------------------------------

    def generate_unmet_need_analysis(
        self,
        device_name: str,
        comparison_device: str = "",
        condition: str = "",
    ) -> Dict:
        """Generate an unmet medical need analysis template.

        Args:
            device_name: Name of the proposed device.
            comparison_device: Reference device or treatment for comparison.
            condition: Target condition being addressed.

        Returns:
            Unmet medical need analysis template dict.
        """
        template = {
            "document_type": "Unmet Medical Need Analysis",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "regulatory_reference": "Section 515B of the FD&C Act",
            "device_name": device_name,
            "target_condition": condition,
            "comparison_device": comparison_device,
            "analysis_sections": {
                "current_treatment_landscape": {
                    "description": (
                        "Comprehensive overview of currently available treatments "
                        "and devices for the target condition."
                    ),
                    "approved_devices": [],  # List of cleared/approved devices
                    "approved_drugs": [],  # List of approved drug therapies
                    "surgical_procedures": [],  # Standard surgical approaches
                    "other_interventions": [],  # Other treatment modalities
                },
                "limitations_of_current_options": {
                    "description": (
                        "Detailed analysis of limitations, gaps, and shortcomings "
                        "of existing treatment options."
                    ),
                    "efficacy_limitations": [],  # To be filled
                    "safety_concerns": [],  # To be filled
                    "accessibility_barriers": [],  # To be filled
                    "cost_barriers": [],  # To be filled
                    "patient_burden": [],  # To be filled
                    "healthcare_system_burden": [],  # To be filled
                },
                "proposed_device_advantages": {
                    "description": (
                        "How the proposed device addresses unmet needs and "
                        "offers advantages over existing options."
                    ),
                    "clinical_advantages": [],  # To be filled
                    "safety_improvements": [],  # To be filled
                    "usability_improvements": [],  # To be filled
                    "cost_effectiveness": "",  # To be filled
                    "patient_quality_of_life": "",  # To be filled
                },
                "comparison_matrix": {
                    "description": (
                        "Side-by-side comparison of proposed device vs. "
                        "existing alternatives."
                    ),
                    "comparison_dimensions": [
                        "Efficacy / Performance",
                        "Safety Profile",
                        "Ease of Use",
                        "Patient Comfort",
                        "Recovery Time",
                        "Cost",
                        "Accessibility",
                        "Training Requirements",
                    ],
                    "device_scores": {},  # To be filled: dimension -> score
                    "alternative_scores": {},  # To be filled: dimension -> score
                    "narrative_comparison": "",  # To be filled
                },
                "patient_population_impact": {
                    "description": (
                        "Analysis of impact on target patient population."
                    ),
                    "total_addressable_patients": "",  # To be filled
                    "underserved_populations": [],  # To be filled
                    "geographic_considerations": "",  # To be filled
                    "health_equity_impact": "",  # To be filled
                },
                "evidence_summary": {
                    "description": (
                        "Summary of evidence supporting the unmet need claim."
                    ),
                    "clinical_evidence": [],  # To be filled
                    "real_world_evidence": [],  # To be filled
                    "patient_registry_data": [],  # To be filled
                    "literature_references": [],  # To be filled
                    "expert_consensus": [],  # To be filled
                },
            },
        }

        return template

    # ------------------------------------------------------------------
    # Sprint review process tracker
    # ------------------------------------------------------------------

    def create_sprint_review_tracker(
        self,
        device_name: str,
        start_date: Optional[str] = None,
    ) -> Dict:
        """Create a sprint review process tracker for Breakthrough designation.

        Args:
            device_name: Name of the device.
            start_date: Start date for the tracker (YYYY-MM-DD format).
                        Defaults to today.

        Returns:
            Sprint review tracker dict with milestones and deliverables.
        """
        if start_date:
            try:
                base_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                base_date = datetime.now()
        else:
            base_date = datetime.now()

        milestones = []
        for milestone_def in SPRINT_REVIEW_MILESTONES:
            target_date = base_date + timedelta(weeks=milestone_def["typical_week"])

            milestones.append({
                "milestone_id": milestone_def["id"],
                "label": milestone_def["label"],
                "description": milestone_def["description"],
                "target_date": target_date.strftime("%Y-%m-%d"),
                "actual_date": None,
                "status": "NOT_STARTED",
                "deliverables": [
                    {
                        "item": d,
                        "status": "NOT_STARTED",
                        "completion_date": None,
                        "notes": "",
                    }
                    for d in milestone_def["deliverables"]
                ],
                "fda_feedback": [],
                "notes": "",
            })

        tracker = {
            "document_type": "Breakthrough Device Sprint Review Tracker",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "device_name": device_name,
            "start_date": base_date.strftime("%Y-%m-%d"),
            "estimated_completion": (
                base_date + timedelta(weeks=72)
            ).strftime("%Y-%m-%d"),
            "current_phase": "pre_submission",
            "overall_progress_pct": 0.0,
            "milestones": milestones,
            "interactive_reviews": [],
            "risk_register": [],
            "status_history": [
                {
                    "date": datetime.now(timezone.utc).isoformat(),
                    "status": "INITIATED",
                    "notes": f"Sprint review tracker created for {device_name}",
                },
            ],
        }

        return tracker

    # ------------------------------------------------------------------
    # Interactive review documentation
    # ------------------------------------------------------------------

    def create_interactive_review_record(
        self,
        device_name: str,
        meeting_type: str = "sprint_review",
        meeting_date: Optional[str] = None,
    ) -> Dict:
        """Create an interactive review meeting record template.

        Args:
            device_name: Name of the device.
            meeting_type: Type of meeting (sprint_review, pre_submission, etc.).
            meeting_date: Date of meeting (YYYY-MM-DD). Defaults to today.

        Returns:
            Interactive review record template dict.
        """
        if not meeting_date:
            meeting_date = datetime.now().strftime("%Y-%m-%d")

        record = {
            "document_type": "Interactive Review Record",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "device_name": device_name,
            "meeting_information": {
                "meeting_date": meeting_date,
                "meeting_type": meeting_type,
                "meeting_format": "",  # In-person, virtual, hybrid
                "duration_minutes": None,
                "fda_division": "",
                "fda_branch": "",
            },
            "attendees": {
                "fda_attendees": [],  # List of {"name": "", "title": "", "role": ""}
                "sponsor_attendees": [],  # List of {"name": "", "title": "", "role": ""}
            },
            "agenda": [],  # List of agenda items
            "discussion_summary": {
                "topics_discussed": [],
                "key_agreements": [],
                "open_questions": [],
                "areas_of_concern": [],
            },
            "action_items": [],  # List of {"id": "", "description": "", "assigned_to": "", "due_date": "", "status": ""}
            "data_reviewed": {
                "documents_reviewed": [],
                "test_results_discussed": [],
                "clinical_data_discussed": [],
            },
            "fda_feedback": {
                "positive_feedback": [],
                "concerns_raised": [],
                "recommendations": [],
                "required_actions": [],
            },
            "next_steps": {
                "next_meeting_date": "",
                "deliverables_for_next_meeting": [],
                "timeline_impact": "",
            },
            "notes": "",
        }

        return record

    # ------------------------------------------------------------------
    # Tracker update methods
    # ------------------------------------------------------------------

    def update_milestone_status(
        self,
        tracker: Dict,
        milestone_id: str,
        status: str,
        actual_date: Optional[str] = None,
        notes: str = "",
    ) -> Dict:
        """Update a milestone status in the sprint review tracker.

        Args:
            tracker: Sprint review tracker dict.
            milestone_id: ID of the milestone to update.
            status: New status (NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED, DELAYED).
            actual_date: Actual completion date (YYYY-MM-DD).
            notes: Additional notes.

        Returns:
            Updated tracker dict.
        """
        valid_statuses = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED", "DELAYED"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        for milestone in tracker.get("milestones", []):
            if milestone.get("milestone_id") == milestone_id:
                milestone["status"] = status
                if actual_date:
                    milestone["actual_date"] = actual_date
                if notes:
                    milestone["notes"] = notes
                break

        # Update overall progress
        milestones = tracker.get("milestones", [])
        if milestones:
            completed = sum(1 for m in milestones if m.get("status") == "COMPLETED")
            tracker["overall_progress_pct"] = round(
                completed / len(milestones) * 100, 1
            )

        # Update current phase
        for milestone in milestones:
            if milestone.get("status") != "COMPLETED":
                tracker["current_phase"] = milestone.get("milestone_id", "")
                break

        # Add status history entry
        tracker.setdefault("status_history", []).append({
            "date": datetime.now(timezone.utc).isoformat(),
            "status": f"Milestone '{milestone_id}' updated to {status}",
            "notes": notes,
        })

        return tracker

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_designation_summary(
        self,
        template: Dict,
    ) -> str:
        """Generate a human-readable summary of a designation request.

        Args:
            template: Completed or partially completed request template.

        Returns:
            Formatted text summary.
        """
        lines = []
        lines.append("=" * 70)
        lines.append("BREAKTHROUGH DEVICE DESIGNATION REQUEST SUMMARY")
        lines.append("=" * 70)

        device_info = template.get("device_information", {})
        lines.append(f"Device Name:    {device_info.get('device_name', 'N/A')}")
        lines.append(f"Trade Name:     {device_info.get('trade_name', 'N/A')}")
        lines.append(f"Specialty:      {device_info.get('specialty', 'N/A')}")
        lines.append(f"Intended Use:   {device_info.get('intended_use', 'N/A')}")
        lines.append(f"Submission Type: {device_info.get('submission_type', 'N/A')}")
        lines.append("")

        # Criteria
        criteria = template.get("designation_criteria", [])
        if criteria:
            lines.append("--- Designation Criteria ---")
            for c in criteria:
                lines.append(f"  [{c.get('status', 'N/A')}] {c.get('label', 'N/A')}")
                lines.append(f"    Reference: {c.get('cfr_ref', 'N/A')}")
                evidence = c.get("evidence_provided", [])
                if evidence:
                    for e in evidence:
                        lines.append(f"      - {e}")
                else:
                    lines.append("      (No evidence provided yet)")
            lines.append("")

        # Checklist
        checklist = template.get("submission_checklist", {})
        if checklist:
            lines.append("--- Submission Checklist ---")
            complete = 0
            total = 0
            for item, done in checklist.items():
                total += 1
                if done:
                    complete += 1
                status = "DONE" if done else "TODO"
                label = item.replace("_", " ").title()
                lines.append(f"  [{status}] {label}")
            lines.append(f"  Completion: {complete}/{total}")
            lines.append("")

        lines.append("=" * 70)
        lines.append(f"Generated: {template.get('generated_at', 'N/A')[:10]}")
        lines.append("This template is for planning purposes only.")
        lines.append("Consult with regulatory counsel before FDA submission.")
        lines.append("=" * 70)

        return "\n".join(lines)

    def generate_tracker_summary(
        self,
        tracker: Dict,
    ) -> str:
        """Generate a human-readable summary of the sprint review tracker.

        Args:
            tracker: Sprint review tracker dict.

        Returns:
            Formatted text summary.
        """
        lines = []
        lines.append("=" * 70)
        lines.append("BREAKTHROUGH DEVICE SPRINT REVIEW TRACKER")
        lines.append("=" * 70)
        lines.append(f"Device:           {tracker.get('device_name', 'N/A')}")
        lines.append(f"Start Date:       {tracker.get('start_date', 'N/A')}")
        lines.append(f"Est. Completion:  {tracker.get('estimated_completion', 'N/A')}")
        lines.append(f"Current Phase:    {tracker.get('current_phase', 'N/A')}")
        lines.append(f"Overall Progress: {tracker.get('overall_progress_pct', 0):.1f}%")
        lines.append("")

        milestones = tracker.get("milestones", [])
        if milestones:
            lines.append("--- Milestones ---")
            lines.append(f"  {'#':>3s}  {'Milestone':<40s}  {'Target':10s}  {'Status':12s}")
            lines.append(f"  {'---':>3s}  {'-'*40}  {'----------':10s}  {'-'*12}")
            for i, m in enumerate(milestones, 1):
                lines.append(
                    f"  {i:3d}  {m.get('label', 'N/A'):<40s}  "
                    f"{m.get('target_date', 'N/A'):10s}  "
                    f"{m.get('status', 'N/A'):12s}"
                )
            lines.append("")

        lines.append("=" * 70)
        lines.append(f"Generated: {tracker.get('generated_at', 'N/A')[:10]}")
        lines.append("Sprint reviews are interactive -- maintain open communication with FDA.")
        lines.append("=" * 70)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_template(self, template: Dict, filename: str) -> str:
        """Save a template to the output directory.

        Args:
            template: Template dict to save.
            filename: Output filename (without extension).

        Returns:
            Path to saved file.
        """
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        tmp_path = filepath + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                json.dump(template, f, indent=2, default=str)
            os.replace(tmp_path, filepath)
        except OSError:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
        return filepath

    def load_template(self, filename: str) -> Optional[Dict]:
        """Load a template from the output directory.

        Args:
            filename: Filename (without extension).

        Returns:
            Template dict, or None if not found.
        """
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None


# ------------------------------------------------------------------
# CLI formatting
# ------------------------------------------------------------------

def _format_request_template(template: Dict) -> str:
    """Format request template for CLI output."""
    bt = BreakthroughDesignation()
    return bt.generate_designation_summary(template)


def _format_tracker(tracker: Dict) -> str:
    """Format sprint tracker for CLI output."""
    bt = BreakthroughDesignation()
    return bt.generate_tracker_summary(tracker)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Breakthrough Device Designation Support -- Templates and Tracking"
    )
    parser.add_argument("--device", required=True, help="Device name")
    parser.add_argument("--specialty", default="", help="Medical specialty area")
    parser.add_argument("--intended-use", default="", dest="intended_use",
                        help="Device intended use statement")
    parser.add_argument("--condition", default="",
                        help="Condition category for justification template")
    parser.add_argument("--specific-condition", default="", dest="specific_condition",
                        help="Specific condition within category")
    parser.add_argument("--sprint-tracker", action="store_true", dest="sprint_tracker",
                        help="Generate sprint review tracker")
    parser.add_argument("--start-date", default="", dest="start_date",
                        help="Start date for sprint tracker (YYYY-MM-DD)")
    parser.add_argument("--unmet-need", action="store_true", dest="unmet_need",
                        help="Generate unmet medical need analysis template")
    parser.add_argument("--comparison-device", default="", dest="comparison_device",
                        help="Comparison device for unmet need analysis")
    parser.add_argument("--interactive-review", action="store_true",
                        dest="interactive_review",
                        help="Generate interactive review record template")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    bt = BreakthroughDesignation()

    result = None

    if args.sprint_tracker:
        result = bt.create_sprint_review_tracker(
            args.device,
            start_date=args.start_date or None,
        )
        if not args.json:
            print(_format_tracker(result))
    elif args.condition:
        result = bt.generate_condition_justification(
            args.condition,
            specific_condition=args.specific_condition,
        )
        if not args.json:
            print(json.dumps(result, indent=2, default=str))
    elif args.unmet_need:
        result = bt.generate_unmet_need_analysis(
            args.device,
            comparison_device=args.comparison_device,
            condition=args.condition,
        )
        if not args.json:
            print(json.dumps(result, indent=2, default=str))
    elif args.interactive_review:
        result = bt.create_interactive_review_record(args.device)
        if not args.json:
            print(json.dumps(result, indent=2, default=str))
    else:
        result = bt.generate_request_template(
            args.device,
            specialty=args.specialty,
            intended_use=args.intended_use,
        )
        if not args.json:
            print(_format_request_template(result))

    if args.json and result:
        print(json.dumps(result, indent=2, default=str))

    if args.output and result:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nOutput saved to: {args.output}")


if __name__ == "__main__":
    main()
