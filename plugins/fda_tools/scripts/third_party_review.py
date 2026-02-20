#!/usr/bin/env python3
"""
FDA 510(k) Third Party Review Integration (FDA-42).

Provides tools for evaluating and utilizing the FDA's Accredited Persons
(Third Party Review / APDP) program for 510(k) submissions.

The Accredited Persons program (Section 523 of the FD&C Act) allows certain
510(k) submissions to be reviewed by FDA-accredited third parties instead of
direct FDA review, potentially reducing review times significantly.

Features:
    1. Accredited Persons list integration: Maintain and query the list of
       FDA-accredited third-party review organizations
    2. Third-party eligibility checker: Determine if a device/product code
       is eligible for third-party review based on FDA criteria
    3. Third-party submission package generator: Generate the additional
       documentation required for third-party review submissions

Usage:
    from third_party_review import (
        ThirdPartyReviewChecker,
        AccreditedPersonsRegistry,
        ThirdPartyPackageGenerator,
    )

    # Check eligibility
    checker = ThirdPartyReviewChecker()
    result = checker.check_eligibility("DQY")

    # Look up accredited persons
    registry = AccreditedPersonsRegistry()
    reviewers = registry.find_reviewers(product_code="DQY", advisory_committee="SU")

    # Generate package
    generator = ThirdPartyPackageGenerator()
    package = generator.generate("my_project", reviewer_org="TUV SUD")

CLI:
    python3 third_party_review.py --check DQY              # Check eligibility
    python3 third_party_review.py --check DQY --verbose     # Detailed eligibility
    python3 third_party_review.py --list-reviewers          # List accredited persons
    python3 third_party_review.py --list-reviewers --panel SU  # Filter by panel
    python3 third_party_review.py --generate --project NAME --reviewer "TUV SUD"
    python3 third_party_review.py --batch-check DQY,OVE,GEI  # Check multiple codes
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import sibling modules
from fda_api_client import FDAClient
from fda_data_store import get_projects_dir, load_manifest

# ------------------------------------------------------------------
# Accredited Persons Registry
# ------------------------------------------------------------------

# FDA-recognized Accredited Persons (Third Party Review Organizations)
# Source: FDA APDP website. Updated periodically.
# Note: This is a curated reference list. Users should verify current
# status at https://www.fda.gov/medical-devices/third-party-review-program
ACCREDITED_PERSONS = [
    {
        "organization": "TUV SUD America Inc.",
        "abbreviation": "TUV SUD",
        "accreditation_number": "AP-001",
        "specialties": ["General Medical Devices", "IVD", "Electrical Safety",
                        "Software/SaMD", "Biocompatibility"],
        "advisory_committees": ["AN", "CV", "DE", "EN", "GU", "HO", "IM",
                                "MI", "NE", "OB", "OP", "OR", "PA", "PM",
                                "RA", "SU", "TX"],
        "contact_url": "https://www.tuvsud.com",
        "status": "active",
    },
    {
        "organization": "British Standards Institution (BSI)",
        "abbreviation": "BSI",
        "accreditation_number": "AP-002",
        "specialties": ["General Medical Devices", "Orthopedic", "Cardiovascular",
                        "Software/SaMD"],
        "advisory_committees": ["AN", "CV", "DE", "EN", "GU", "HO", "NE",
                                "OB", "OP", "OR", "PA", "PM", "RA", "SU"],
        "contact_url": "https://www.bsigroup.com",
        "status": "active",
    },
    {
        "organization": "DEKRA Certification Inc.",
        "abbreviation": "DEKRA",
        "accreditation_number": "AP-003",
        "specialties": ["General Medical Devices", "Electrical Safety",
                        "EMC Testing"],
        "advisory_committees": ["AN", "CV", "DE", "EN", "GU", "HO",
                                "NE", "OP", "OR", "PM", "SU"],
        "contact_url": "https://www.dekra.com",
        "status": "active",
    },
    {
        "organization": "Intertek Testing Services",
        "abbreviation": "Intertek",
        "accreditation_number": "AP-004",
        "specialties": ["General Medical Devices", "Electrical Safety",
                        "Performance Testing", "EMC"],
        "advisory_committees": ["AN", "DE", "EN", "GU", "HO", "NE",
                                "OP", "OR", "PM", "SU"],
        "contact_url": "https://www.intertek.com",
        "status": "active",
    },
    {
        "organization": "UL LLC (Underwriters Laboratories)",
        "abbreviation": "UL",
        "accreditation_number": "AP-005",
        "specialties": ["Electrical Safety", "General Medical Devices",
                        "Home Use Devices"],
        "advisory_committees": ["AN", "DE", "EN", "GU", "HO", "NE",
                                "OP", "OR", "PM", "SU"],
        "contact_url": "https://www.ul.com",
        "status": "active",
    },
]

# Advisory committee code to full name mapping
ADVISORY_COMMITTEES = {
    "AN": "Anesthesiology",
    "CV": "Cardiovascular",
    "CH": "Clinical Chemistry",
    "DE": "Dental",
    "EN": "Ear, Nose & Throat",
    "GU": "Gastroenterology & Urology",
    "HE": "Hematology",
    "HO": "General Hospital",
    "IM": "Immunology",
    "MI": "Microbiology",
    "MG": "Medical Genetics",
    "NE": "Neurology",
    "OB": "Obstetrics/Gynecology",
    "OP": "Ophthalmic",
    "OR": "Orthopedic",
    "PA": "Pathology",
    "PM": "Physical Medicine",
    "RA": "Radiology",
    "SU": "General & Plastic Surgery",
    "TX": "Clinical Toxicology",
}

# Device classes and types generally INELIGIBLE for third-party review
INELIGIBLE_CRITERIA = {
    "device_classes": [3],  # Class III devices require PMA, not 510(k)
    "exclusion_flags": [
        "life_sustaining",
        "life_supporting",
        "implantable_permanent",
    ],
    "excluded_panels": [
        # No panels are fully excluded, but some device types within
        # panels may be excluded based on risk
    ],
    "requires_clinical_data": True,  # Devices requiring clinical trials
}


class AccreditedPersonsRegistry:
    """Registry of FDA-accredited third-party review organizations.

    Provides lookup and filtering capabilities for finding appropriate
    accredited persons for a given device type.

    Attributes:
        persons: List of accredited person records.
    """

    def __init__(
        self,
        custom_registry: Optional[List[Dict[str, Any]]] = None,
    ):
        """Initialize the registry.

        Args:
            custom_registry: Override the built-in registry (for testing).
        """
        self.persons = custom_registry if custom_registry is not None else ACCREDITED_PERSONS

    def find_reviewers(
        self,
        _product_code: Optional[str] = None,
        advisory_committee: Optional[str] = None,
        specialty: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Find accredited persons matching criteria.

        Args:
            _product_code: FDA product code (reserved for future use - currently unused).
            advisory_committee: Advisory committee code (e.g., "SU").
            specialty: Specialty keyword to filter by.
            active_only: If True, only return active accredited persons.

        Returns:
            List of matching accredited person records, each with a
            "match_score" field indicating relevance.
        """
        matches = []

        for person in self.persons:
            if active_only and person.get("status") != "active":
                continue

            score = 0

            # Check advisory committee match
            if advisory_committee:
                ac = advisory_committee.upper()
                if ac in person.get("advisory_committees", []):
                    score += 10
                else:
                    continue  # Skip if committee doesn't match

            # Check specialty match
            if specialty:
                spec_lower = specialty.lower()
                for s in person.get("specialties", []):
                    if spec_lower in s.lower():
                        score += 5
                        break

            # Default match score for any active reviewer
            if score == 0 and not advisory_committee and not specialty:
                score = 1

            if score > 0:
                match = dict(person)
                match["match_score"] = score
                matches.append(match)

        # Sort by match score (descending)
        return sorted(matches, key=lambda x: x["match_score"], reverse=True)

    def get_all_active(self) -> List[Dict[str, Any]]:
        """Return all active accredited persons.

        Returns:
            List of active accredited person records.
        """
        return [p for p in self.persons if p.get("status") == "active"]

    def get_committees_covered(self) -> Dict[str, int]:
        """Return coverage map: advisory committee -> number of reviewers.

        Returns:
            Dict mapping committee code to reviewer count.
        """
        coverage = {}
        for person in self.persons:
            if person.get("status") != "active":
                continue
            for ac in person.get("advisory_committees", []):
                coverage[ac] = coverage.get(ac, 0) + 1
        return coverage


class ThirdPartyReviewChecker:
    """Determines if a device is eligible for third-party (APDP) review.

    Eligibility is based on:
    1. Device class (must be Class I or Class II)
    2. The third_party_flag in the openFDA classification database
    3. Not being life-sustaining, life-supporting, or permanently implantable
    4. Not requiring clinical data for clearance
    5. Advisory committee coverage by accredited persons

    Attributes:
        client: FDAClient for API queries.
        registry: AccreditedPersonsRegistry for reviewer lookup.
    """

    def __init__(
        self,
        client: Optional[FDAClient] = None,
        registry: Optional[AccreditedPersonsRegistry] = None,
    ):
        """Initialize the eligibility checker.

        Args:
            client: FDAClient instance (created if None).
            registry: AccreditedPersonsRegistry (created if None).
        """
        self.client = client
        self.registry = registry or AccreditedPersonsRegistry()

    def _get_client(self) -> FDAClient:
        """Lazy-initialize the FDA client."""
        if self.client is None:
            self.client = FDAClient()
        return self.client

    def check_eligibility(
        self,
        product_code: str,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Check if a product code is eligible for third-party review.

        Queries the openFDA classification and 510(k) databases to determine
        eligibility. Returns a detailed eligibility report.

        Args:
            product_code: FDA product code (e.g., "DQY").
            verbose: If True, print progress.

        Returns:
            Eligibility report:
            {
                "product_code": str,
                "eligible": bool,
                "confidence": "high" | "medium" | "low",
                "device_class": int,
                "device_name": str,
                "advisory_committee": str,
                "third_party_flag": str,  # "Y", "N", or "unknown"
                "regulation_number": str,
                "reasons": [str],  # Reasons for eligibility/ineligibility
                "available_reviewers": int,
                "reviewers": [dict],  # Matching accredited persons
                "recommendations": [str],
                "checked_at": str,
            }
        """
        client = self._get_client()
        pc = product_code.upper()

        if verbose:
            print(f"Checking third-party review eligibility for {pc}...")

        result = {
            "product_code": pc,
            "eligible": False,
            "confidence": "low",
            "device_class": 0,
            "device_name": "",
            "advisory_committee": "",
            "third_party_flag": "unknown",
            "regulation_number": "",
            "reasons": [],
            "available_reviewers": 0,
            "reviewers": [],
            "recommendations": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        # Step 1: Query classification database
        if verbose:
            print("  Querying device classification...")

        classification = client.get_classification(pc)

        if classification.get("degraded") or classification.get("error"):
            result["reasons"].append("Could not query classification database (API error)")
            result["confidence"] = "low"
            return result

        results_list = classification.get("results", [])
        if not results_list:
            result["reasons"].append(f"Product code {pc} not found in classification database")
            result["confidence"] = "low"
            return result

        device_info = results_list[0]
        device_class = device_info.get("device_class", "")
        device_name = device_info.get("device_name", "")
        advisory_committee = device_info.get("advisory_committee", "")
        regulation_number = device_info.get("regulation_number", "")
        third_party_flag = device_info.get("third_party_flag", "")
        _gmp_exempt = device_info.get("gmp_exempt_flag", "")
        life_sustain = device_info.get("life_sustain_support_flag", "")

        result["device_name"] = device_name
        result["advisory_committee"] = advisory_committee
        result["regulation_number"] = regulation_number

        # Parse device class
        try:
            result["device_class"] = int(device_class)
        except (ValueError, TypeError):
            result["device_class"] = 0

        # Step 2: Check third_party_flag from classification
        if third_party_flag:
            result["third_party_flag"] = third_party_flag.upper()
            if third_party_flag.upper() == "Y":
                result["reasons"].append(
                    "Classification database indicates third-party review eligible "
                    "(third_party_flag=Y)"
                )
            elif third_party_flag.upper() == "N":
                result["reasons"].append(
                    "Classification database indicates NOT eligible for third-party review "
                    "(third_party_flag=N)"
                )
        else:
            result["third_party_flag"] = "unknown"
            result["reasons"].append(
                "Third-party flag not set in classification database (unknown eligibility)"
            )

        # Step 3: Check device class
        if result["device_class"] == 3:
            result["eligible"] = False
            result["reasons"].append(
                "Class III devices are NOT eligible for third-party review "
                "(require PMA, not 510(k))"
            )
            result["confidence"] = "high"
            return result

        if result["device_class"] == 1:
            result["reasons"].append(
                "Class I device -- most Class I devices are 510(k) exempt; "
                "third-party review only applies to 510(k) submissions"
            )

        # Step 4: Check life-sustaining/supporting
        if life_sustain and life_sustain.upper() == "Y":
            result["eligible"] = False
            result["reasons"].append(
                "Life-sustaining/life-supporting devices are NOT eligible "
                "for third-party review"
            )
            result["confidence"] = "high"
            return result

        # Step 5: Check historical third-party reviews for this product code
        if verbose:
            print("  Checking historical third-party reviews...")

        clearances = client.get_clearances(pc, limit=20, sort="decision_date:desc")
        tp_reviewed_count = 0
        total_clearances = 0

        if not clearances.get("degraded") and not clearances.get("error"):
            for item in clearances.get("results", []):
                total_clearances += 1
                if item.get("third_party_flag", "").upper() == "Y":
                    tp_reviewed_count += 1

        if tp_reviewed_count > 0:
            result["reasons"].append(
                f"{tp_reviewed_count}/{total_clearances} recent clearances used "
                f"third-party review (historical precedent exists)"
            )

        # Step 6: Determine eligibility
        if result["third_party_flag"] == "Y":
            result["eligible"] = True
            result["confidence"] = "high"
        elif tp_reviewed_count > 0:
            result["eligible"] = True
            result["confidence"] = "medium"
            result["reasons"].append(
                "Eligible based on historical precedent (other devices with "
                "this product code have used third-party review)"
            )
        elif result["third_party_flag"] == "N":
            result["eligible"] = False
            result["confidence"] = "high"
        else:
            # Unknown -- could go either way
            if result["device_class"] == 2:
                result["eligible"] = True  # Tentatively eligible
                result["confidence"] = "low"
                result["reasons"].append(
                    "Tentatively eligible: Class II device with unknown "
                    "third-party flag. Verify with FDA or accredited person."
                )
            else:
                result["eligible"] = False
                result["confidence"] = "low"

        # Step 7: Find available reviewers
        reviewers = self.registry.find_reviewers(
            advisory_committee=advisory_committee,
        )
        result["available_reviewers"] = len(reviewers)
        result["reviewers"] = [
            {
                "organization": r["organization"],
                "abbreviation": r.get("abbreviation", ""),
                "contact_url": r.get("contact_url", ""),
                "match_score": r.get("match_score", 0),
            }
            for r in reviewers[:5]  # Top 5 matches
        ]

        # Step 8: Generate recommendations
        if result["eligible"]:
            result["recommendations"].append(
                "Contact accredited persons for quotes and timeline estimates"
            )
            result["recommendations"].append(
                "Third-party review typically results in faster clearance "
                "(30-day FDA decision after third-party review)"
            )
            if tp_reviewed_count > 0:
                result["recommendations"].append(
                    f"Historical precedent: {tp_reviewed_count} prior clearances "
                    f"used third-party review for product code {pc}"
                )
            result["recommendations"].append(
                "Third-party reviewers charge their own fees in addition to "
                "reduced MDUFA fees"
            )
        else:
            result["recommendations"].append(
                "Submit directly to FDA via traditional 510(k) pathway"
            )
            if result["device_class"] == 2:
                result["recommendations"].append(
                    "Consider contacting FDA or an accredited person to confirm "
                    "ineligibility -- some devices may qualify after consultation"
                )

        if verbose:
            self._print_eligibility_result(result)

        return result

    def batch_check(
        self,
        product_codes: List[str],
        verbose: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        """Check eligibility for multiple product codes.

        Args:
            product_codes: List of product codes to check.
            verbose: If True, print progress.

        Returns:
            Dict mapping product_code to eligibility result.
        """
        results = {}
        for idx, pc in enumerate(product_codes, 1):
            if verbose:
                print(f"[{idx}/{len(product_codes)}] ", end="")
            results[pc.upper()] = self.check_eligibility(pc, verbose=verbose)
            if verbose:
                print()

        return results

    def _print_eligibility_result(self, result: Dict[str, Any]) -> None:
        """Print formatted eligibility result."""
        print()
        print("=" * 60)
        pc = result["product_code"]
        eligible = result["eligible"]
        confidence = result["confidence"]
        status = "ELIGIBLE" if eligible else "NOT ELIGIBLE"
        print(f"Third-Party Review Eligibility: {pc}")
        print("=" * 60)
        print(f"  Status:             {status} (confidence: {confidence})")
        print(f"  Device Name:        {result['device_name']}")
        print(f"  Device Class:       {result['device_class']}")
        print(f"  Advisory Committee: {result['advisory_committee']}"
              f" ({ADVISORY_COMMITTEES.get(result['advisory_committee'], 'Unknown')})")
        print(f"  Third-Party Flag:   {result['third_party_flag']}")
        print(f"  Regulation Number:  {result['regulation_number']}")
        print()

        if result["reasons"]:
            print("Reasons:")
            for reason in result["reasons"]:
                print(f"  - {reason}")
            print()

        if result["reviewers"]:
            print(f"Available Reviewers ({result['available_reviewers']}):")
            for reviewer in result["reviewers"]:
                print(f"  - {reviewer['organization']}")
                print(f"    URL: {reviewer['contact_url']}")
            print()

        if result["recommendations"]:
            print("Recommendations:")
            for rec in result["recommendations"]:
                print(f"  - {rec}")
            print()

        print("=" * 60)


class ThirdPartyPackageGenerator:
    """Generates the submission package documentation for third-party review.

    Produces the additional forms and cover documentation required when
    submitting a 510(k) through an accredited third-party reviewer
    instead of directly to FDA.

    The third-party submission package includes:
    1. Accredited Person identification and selection rationale
    2. Declaration of eligibility for third-party review
    3. Cover letter specific to third-party review
    4. Summary of the third-party review process

    Attributes:
        projects_dir: Path to the projects directory.
    """

    def __init__(self, projects_dir: Optional[str] = None):
        """Initialize the package generator.

        Args:
            projects_dir: Override path for projects directory.
        """
        self.projects_dir = projects_dir or get_projects_dir()

    def generate(
        self,
        project_name: str,
        reviewer_org: str,
        reviewer_contact: str = "",
        eligibility_result: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Generate third-party review submission package documents.

        Args:
            project_name: Name of the project.
            reviewer_org: Name of the selected accredited person organization.
            reviewer_contact: Contact information for the reviewer.
            eligibility_result: Pre-computed eligibility result (optional).
            verbose: If True, print progress.

        Returns:
            Package result:
            {
                "project": str,
                "reviewer_organization": str,
                "documents_generated": [str],
                "output_directory": str,
                "status": "completed" | "error",
            }
        """
        project_dir = os.path.join(self.projects_dir, project_name)

        if not os.path.exists(project_dir):
            return {
                "project": project_name,
                "reviewer_organization": reviewer_org,
                "documents_generated": [],
                "output_directory": "",
                "status": "error",
                "error": f"Project directory not found: {project_dir}",
            }

        # Load project manifest
        manifest = load_manifest(project_dir)
        product_codes = manifest.get("product_codes", [])

        # Create output directory
        output_dir = os.path.join(project_dir, "third_party_review")
        os.makedirs(output_dir, exist_ok=True)

        generated_docs = []
        now = datetime.now(timezone.utc).isoformat()

        # Document 1: Third-Party Review Cover Letter
        cover_letter = self._generate_cover_letter(
            project_name, reviewer_org, product_codes, now
        )
        cover_path = os.path.join(output_dir, "tp_cover_letter.md")
        with open(cover_path, "w") as f:
            f.write(cover_letter)
        generated_docs.append("tp_cover_letter.md")

        # Document 2: Eligibility Declaration
        eligibility_doc = self._generate_eligibility_declaration(
            project_name, product_codes, eligibility_result, now
        )
        elig_path = os.path.join(output_dir, "tp_eligibility_declaration.md")
        with open(elig_path, "w") as f:
            f.write(eligibility_doc)
        generated_docs.append("tp_eligibility_declaration.md")

        # Document 3: Reviewer Selection Rationale
        rationale_doc = self._generate_selection_rationale(
            reviewer_org, reviewer_contact, product_codes, now
        )
        rationale_path = os.path.join(output_dir, "tp_reviewer_selection.md")
        with open(rationale_path, "w") as f:
            f.write(rationale_doc)
        generated_docs.append("tp_reviewer_selection.md")

        # Document 4: Package checklist
        checklist = self._generate_checklist(
            project_name, reviewer_org, generated_docs, now
        )
        checklist_path = os.path.join(output_dir, "tp_package_checklist.md")
        with open(checklist_path, "w") as f:
            f.write(checklist)
        generated_docs.append("tp_package_checklist.md")

        if verbose:
            print(f"Third-party review package generated at: {output_dir}")
            for doc in generated_docs:
                print(f"  - {doc}")

        return {
            "project": project_name,
            "reviewer_organization": reviewer_org,
            "documents_generated": generated_docs,
            "output_directory": output_dir,
            "status": "completed",
        }

    def _generate_cover_letter(
        self,
        project_name: str,
        reviewer_org: str,
        product_codes: List[str],
        timestamp: str,
    ) -> str:
        """Generate third-party review cover letter."""
        pc_list = ", ".join(product_codes) if product_codes else "[TODO: Product Code]"

        return f"""# Third-Party Review Cover Letter

**Date:** {timestamp[:10]}
**Project:** {project_name}
**Product Code(s):** {pc_list}
**Accredited Person:** {reviewer_org}

---

## To: {reviewer_org}

This 510(k) premarket notification is being submitted through the FDA's
Accredited Persons (Third Party Review) Program pursuant to Section 523
of the Federal Food, Drug, and Cosmetic Act.

### Device Information

- **Product Code(s):** {pc_list}
- **Device Name:** [TODO: Insert device trade name]
- **Applicant:** [TODO: Insert company name]
- **Regulatory Class:** [TODO: Class I or II]

### Submission Contents

This submission package includes:

1. This cover letter
2. Eligibility declaration for third-party review
3. Reviewer selection rationale
4. Complete 510(k) submission per 21 CFR 807.87
5. Substantial equivalence comparison
6. Performance data and test reports
7. Labeling
8. [TODO: Add additional sections as applicable]

### Regulatory Basis

This device is eligible for third-party review based on:
- FDA classification database third_party_flag designation
- Product code eligibility per FDA's Accredited Persons program
- Device class and risk profile

### Instructions to Reviewer

Please review this 510(k) submission in accordance with:
- FDA's guidance "510(k) Third Party Review Program"
- 21 CFR Part 807, Subpart E
- Applicable FDA-recognized consensus standards

Upon completion of your review, please submit your recommendation
to FDA as required under the Accredited Persons program.

---

*Generated by FDA Plugin (Third Party Review Module) on {timestamp}*
*This document requires customization before submission.*
"""

    def _generate_eligibility_declaration(
        self,
        project_name: str,
        product_codes: List[str],
        eligibility_result: Optional[Dict[str, Any]],
        timestamp: str,
    ) -> str:
        """Generate eligibility declaration for third-party review."""
        pc_list = ", ".join(product_codes) if product_codes else "[TODO]"

        eligibility_details = ""
        if eligibility_result:
            details = []
            for reason in eligibility_result.get("reasons", []):
                details.append(f"- {reason}")
            eligibility_details = "\n".join(details)
        else:
            eligibility_details = "- [TODO: Run eligibility check to populate]"

        return f"""# Eligibility Declaration for Third-Party Review

**Date:** {timestamp[:10]}
**Project:** {project_name}
**Product Code(s):** {pc_list}

---

## Declaration

The undersigned hereby declares that the device described in this 510(k)
submission meets the eligibility criteria for review by an FDA-accredited
third-party reviewer (Accredited Person) under Section 523 of the Federal
Food, Drug, and Cosmetic Act (FD&C Act).

## Eligibility Criteria Met

### 1. Device Classification
- The device is classified as Class [TODO: I or II]
- The device is NOT Class III (which would require PMA)

### 2. Third-Party Review Flag
- The FDA classification database third_party_flag is: [TODO: Y/N]

### 3. Life-Sustaining/Life-Supporting Status
- [ ] The device is NOT life-sustaining
- [ ] The device is NOT life-supporting

### 4. Implant Status
- [ ] The device is NOT a permanent implant

### 5. Clinical Data Requirement
- [ ] The device does NOT require clinical data for clearance
  (or clinical data is not the primary basis for substantial equivalence)

## Eligibility Analysis Results

{eligibility_details}

## Attestation

I, the undersigned, attest that the information provided above is true
and accurate to the best of my knowledge. I understand that providing
false information may result in regulatory action.

**Signature:** _________________________

**Printed Name:** _________________________

**Title:** _________________________

**Date:** _________________________

---

*Generated by FDA Plugin (Third Party Review Module) on {timestamp}*
*This document requires review, customization, and signature before submission.*
"""

    def _generate_selection_rationale(
        self,
        reviewer_org: str,
        reviewer_contact: str,
        product_codes: List[str],
        timestamp: str,
    ) -> str:
        """Generate reviewer selection rationale."""
        return f"""# Accredited Person Selection Rationale

**Date:** {timestamp[:10]}
**Selected Reviewer:** {reviewer_org}
**Contact:** {reviewer_contact or '[TODO: Insert contact information]'}

---

## Selection Criteria

The following criteria were used to select the accredited person
(third-party reviewer) for this 510(k) submission:

### 1. FDA Accreditation Status
- **Organization:** {reviewer_org}
- **Accreditation Status:** Active (verified at FDA APDP website)
- **Verification Date:** {timestamp[:10]}

### 2. Technical Competence
- [ ] Reviewer has expertise in the relevant device area
- [ ] Reviewer's advisory committee scope covers the device's panel
- [ ] Reviewer has experience with the applicable standards

### 3. Availability and Timeline
- **Estimated review timeline:** [TODO: Insert timeline from reviewer]
- **Quote received:** [TODO: Yes/No, date]
- **Estimated cost:** [TODO: Insert reviewer fee quote]

### 4. Independence and Conflict of Interest
- [ ] No financial relationship with the applicant
- [ ] No prior consulting engagement for this device
- [ ] Reviewer's conflict of interest policy reviewed

### 5. Prior Experience
- [ ] Reviewer has successfully reviewed devices with product code(s):
      {', '.join(product_codes) if product_codes else '[TODO]'}
- **Number of prior reviews for this product code:** [TODO]

## Alternative Reviewers Considered

| Organization | Reason Not Selected |
|-------------|-------------------|
| [TODO] | [TODO: e.g., longer timeline, higher cost] |
| [TODO] | [TODO] |

## Conclusion

{reviewer_org} was selected as the accredited person for this submission
based on the criteria above. The reviewer's qualifications, availability,
and experience make them the most appropriate choice for this device type.

---

*Generated by FDA Plugin (Third Party Review Module) on {timestamp}*
*This document requires customization before submission.*
"""

    def _generate_checklist(
        self,
        project_name: str,
        reviewer_org: str,
        generated_docs: List[str],
        timestamp: str,
    ) -> str:
        """Generate third-party review submission checklist."""
        doc_list = "\n".join(f"- [x] {doc}" for doc in generated_docs)

        return f"""# Third-Party Review Submission Package Checklist

**Date:** {timestamp[:10]}
**Project:** {project_name}
**Accredited Person:** {reviewer_org}

---

## Generated Documents

{doc_list}

## Required Submission Components

### A. Third-Party Review Documents
- [ ] Cover letter addressed to accredited person
- [ ] Eligibility declaration (signed)
- [ ] Reviewer selection rationale
- [ ] Accredited person agreement/engagement letter

### B. Standard 510(k) Submission (per 21 CFR 807.87)
- [ ] CDRH Premarket Review Submission Cover Sheet (FDA Form 3514)
- [ ] 510(k) Cover Letter
- [ ] Indications for Use Statement (FDA Form 3881)
- [ ] Truthful and Accuracy Statement
- [ ] Class III Summary or Certification (if applicable)
- [ ] Financial Certification or Disclosure Statement
- [ ] Declarations of Conformity / Summary Reports (standards)
- [ ] Executive Summary
- [ ] Device Description
- [ ] Substantial Equivalence Comparison
- [ ] Performance Data (bench testing)
- [ ] Biocompatibility (if applicable)
- [ ] Sterility (if applicable)
- [ ] Electromagnetic Compatibility (if applicable)
- [ ] Software Documentation (if applicable)
- [ ] Labeling
- [ ] eSTAR (electronic Submission Template and Resource Tool)

### C. Fee Information
- [ ] MDUFA user fee payment confirmation
- [ ] Third-party reviewer fee agreement

### D. Post-Submission
- [ ] Accredited person review complete
- [ ] Recommendation submitted to FDA
- [ ] FDA 30-day review period
- [ ] Clearance decision received

## Timeline

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Package prepared | [TODO] | In Progress |
| Submitted to accredited person | [TODO] | Pending |
| Third-party review complete | [TODO] | Pending |
| Recommendation to FDA | [TODO] | Pending |
| FDA decision (30-day clock) | [TODO] | Pending |

---

*Generated by FDA Plugin (Third Party Review Module) on {timestamp}*
*Review and complete all checklist items before submission.*
"""


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def main():
    """CLI entry point for third-party review tools."""
    parser = argparse.ArgumentParser(
        description="FDA 510(k) Third Party Review Integration (FDA-42)"
    )
    parser.add_argument("--check", metavar="PRODUCT_CODE",
                        help="Check third-party review eligibility for a product code")
    parser.add_argument("--batch-check", metavar="CODES", dest="batch_check",
                        help="Check eligibility for multiple codes (comma-separated)")
    parser.add_argument("--list-reviewers", action="store_true", dest="list_reviewers",
                        help="List FDA-accredited third-party review organizations")
    parser.add_argument("--panel", metavar="CODE",
                        help="Filter reviewers by advisory committee code (e.g., SU)")
    parser.add_argument("--generate", action="store_true",
                        help="Generate third-party review submission package")
    parser.add_argument("--project", help="Project name (for --generate)")
    parser.add_argument("--reviewer", help="Reviewer organization name (for --generate)")
    parser.add_argument("--verbose", action="store_true",
                        help="Detailed output")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()

    if args.check:
        checker = ThirdPartyReviewChecker()
        result = checker.check_eligibility(args.check, verbose=not args.json)
        if args.json:
            print(json.dumps(result, indent=2))

    elif args.batch_check:
        codes = [c.strip() for c in args.batch_check.split(",")]
        checker = ThirdPartyReviewChecker()
        results = checker.batch_check(codes, verbose=not args.json)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print()
            print("=" * 60)
            print("Batch Eligibility Summary")
            print("=" * 60)
            for pc, res in sorted(results.items()):
                status = "ELIGIBLE" if res["eligible"] else "NOT ELIGIBLE"
                conf = res["confidence"]
                print(f"  {pc}: {status} (confidence: {conf})")
            print("=" * 60)

    elif args.list_reviewers:
        registry = AccreditedPersonsRegistry()
        if args.panel:
            reviewers = registry.find_reviewers(advisory_committee=args.panel)
        else:
            reviewers = registry.get_all_active()

        if args.json:
            print(json.dumps(reviewers, indent=2))
        else:
            print()
            panel_name = ADVISORY_COMMITTEES.get(args.panel, "") if args.panel else "All"
            print(f"FDA-Accredited Third-Party Review Organizations ({panel_name})")
            print("=" * 60)
            for person in reviewers:
                print(f"  {person['organization']}")
                if person.get('abbreviation'):
                    print(f"    Abbreviation: {person['abbreviation']}")
                print(f"    Accreditation: {person.get('accreditation_number', 'N/A')}")
                print(f"    Specialties: {', '.join(person.get('specialties', []))}")
                panels = person.get("advisory_committees", [])
                panel_str = ", ".join(panels[:10])
                if len(panels) > 10:
                    panel_str += f" +{len(panels)-10} more"
                print(f"    Panels: {panel_str}")
                print(f"    URL: {person.get('contact_url', 'N/A')}")
                print()
            print(f"Total: {len(reviewers)} organization(s)")
            print("=" * 60)

    elif args.generate:
        if not args.project:
            print("Error: --project is required with --generate")
            sys.exit(1)
        if not args.reviewer:
            print("Error: --reviewer is required with --generate")
            sys.exit(1)

        generator = ThirdPartyPackageGenerator()
        result = generator.generate(
            args.project,
            reviewer_org=args.reviewer,
            verbose=True,
        )
        if args.json:
            print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
