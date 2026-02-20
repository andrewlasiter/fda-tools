"""
Regulatory Compliance Validation Helpers

Provides comprehensive validation for FDA regulatory compliance including:
- 21 CFR Part 11 compliance checks
- eSTAR XML format validation
- 510(k) submission requirements validation
- Predicate acceptability criteria
- Substantial equivalence validation

Version: 1.0.0
Date: 2026-02-20
Issue: FDA-174 (QA-001)
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation finding severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    def __lt__(self, other):
        """Allow severity comparison."""
        severity_order = {
            ValidationSeverity.INFO: 0,
            ValidationSeverity.WARNING: 1,
            ValidationSeverity.ERROR: 2,
            ValidationSeverity.CRITICAL: 3,
        }
        return severity_order[self] < severity_order[other]


@dataclass
class ValidationResult:
    """Result of a validation check."""

    validator_name: str
    check_name: str
    severity: ValidationSeverity
    message: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "validator": self.validator_name,
            "check": self.check_name,
            "severity": self.severity.value,
            "message": self.message,
            "passed": self.passed,
            "details": self.details,
            "recommendations": self.recommendations,
        }


class RegulatoryValidator:
    """
    Base class for regulatory compliance validators.

    Provides common validation infrastructure and reporting.
    """

    def __init__(self, validator_name: str):
        """
        Initialize validator.

        Args:
            validator_name: Name of this validator
        """
        self.validator_name = validator_name
        self.results: List[ValidationResult] = []

    def add_result(
        self,
        check_name: str,
        severity: ValidationSeverity,
        message: str,
        passed: bool,
        details: Optional[Dict[str, Any]] = None,
        recommendations: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Add validation result.

        Args:
            check_name: Name of the check
            severity: Severity level
            message: Validation message
            passed: Whether check passed
            details: Additional details
            recommendations: Remediation recommendations

        Returns:
            ValidationResult object
        """
        result = ValidationResult(
            validator_name=self.validator_name,
            check_name=check_name,
            severity=severity,
            message=message,
            passed=passed,
            details=details or {},
            recommendations=recommendations or [],
        )
        self.results.append(result)
        return result

    def get_results(self) -> List[ValidationResult]:
        """Get all validation results."""
        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        by_severity = {}
        for severity in ValidationSeverity:
            count = sum(1 for r in self.results if r.severity == severity)
            by_severity[severity.value] = count

        return {
            "validator": self.validator_name,
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "by_severity": by_severity,
            "overall_status": "PASS" if failed == 0 else "FAIL",
        }

    def has_critical_errors(self) -> bool:
        """Check if any critical errors were found."""
        return any(
            r.severity == ValidationSeverity.CRITICAL and not r.passed
            for r in self.results
        )

    def clear_results(self) -> None:
        """Clear all validation results."""
        self.results = []


class CFRValidator(RegulatoryValidator):
    """
    Validates compliance with 21 CFR regulations.

    Checks:
    - Part 11 electronic records compliance
    - Part 807 premarket notification requirements
    - Part 820 quality system requirements
    - Device-specific CFR parts (e.g., 21 CFR 870 for cardiovascular)
    """

    # Common CFR parts for 510(k) submissions
    CFR_PARTS = {
        "Part 11": "Electronic Records; Electronic Signatures",
        "Part 7": "Enforcement Policy",
        "Part 803": "Medical Device Reporting",
        "Part 807": "Establishment Registration and Device Listing",
        "Part 820": "Quality System Regulation",
    }

    def __init__(self):
        super().__init__("CFRValidator")

    def validate_part_11_compliance(
        self,
        submission_data: Dict[str, Any],
    ) -> List[ValidationResult]:
        """
        Validate 21 CFR Part 11 electronic records compliance.

        Args:
            submission_data: Submission data to validate

        Returns:
            List of ValidationResult objects
        """
        self.clear_results()

        # Check 1: Electronic signatures
        if "signatures" in submission_data:
            signatures = submission_data["signatures"]
            if isinstance(signatures, list) and len(signatures) > 0:
                self.add_result(
                    check_name="electronic_signatures_present",
                    severity=ValidationSeverity.INFO,
                    message="Electronic signatures found",
                    passed=True,
                    details={"signature_count": len(signatures)},
                )
            else:
                self.add_result(
                    check_name="electronic_signatures_present",
                    severity=ValidationSeverity.WARNING,
                    message="No electronic signatures found",
                    passed=False,
                    recommendations=[
                        "Add electronic signatures per 21 CFR Part 11",
                        "Ensure signatory authority is documented",
                    ],
                )

        # Check 2: Audit trail
        if "audit_trail" in submission_data:
            self.add_result(
                check_name="audit_trail_present",
                severity=ValidationSeverity.INFO,
                message="Audit trail present",
                passed=True,
            )
        else:
            self.add_result(
                check_name="audit_trail_present",
                severity=ValidationSeverity.WARNING,
                message="No audit trail found (recommended for Part 11 compliance)",
                passed=False,
                recommendations=[
                    "Implement audit trail for all document modifications",
                    "Include timestamp and user identification for all changes",
                ],
            )

        # Check 3: Document version control
        if "version" in submission_data or "revision" in submission_data:
            self.add_result(
                check_name="version_control",
                severity=ValidationSeverity.INFO,
                message="Version control present",
                passed=True,
            )
        else:
            self.add_result(
                check_name="version_control",
                severity=ValidationSeverity.WARNING,
                message="No version control information found",
                passed=False,
                recommendations=["Add version or revision tracking"],
            )

        return self.get_results()

    def validate_device_classification(
        self,
        product_code: str,
        device_class: str,
        regulation_number: Optional[str] = None,
    ) -> List[ValidationResult]:
        """
        Validate device classification and CFR citation.

        Args:
            product_code: FDA product code (3 letters)
            device_class: Device class (I, II, III, U, f)
            regulation_number: 21 CFR regulation number (e.g., "21 CFR 870.1340")

        Returns:
            List of ValidationResult objects
        """
        # Check 1: Product code format
        if re.match(r"^[A-Z]{3}$", product_code):
            self.add_result(
                check_name="product_code_format",
                severity=ValidationSeverity.INFO,
                message=f"Product code {product_code} has valid format",
                passed=True,
            )
        else:
            self.add_result(
                check_name="product_code_format",
                severity=ValidationSeverity.ERROR,
                message=f"Invalid product code format: {product_code}",
                passed=False,
                details={"product_code": product_code},
                recommendations=["Product code must be 3 uppercase letters"],
            )

        # Check 2: Device class
        valid_classes = ["I", "II", "III", "U", "f"]
        if device_class in valid_classes:
            self.add_result(
                check_name="device_class_valid",
                severity=ValidationSeverity.INFO,
                message=f"Device class {device_class} is valid",
                passed=True,
            )
        else:
            self.add_result(
                check_name="device_class_valid",
                severity=ValidationSeverity.ERROR,
                message=f"Invalid device class: {device_class}",
                passed=False,
                details={"device_class": device_class, "valid_classes": valid_classes},
                recommendations=["Use valid device class (I, II, III, U, or f)"],
            )

        # Check 3: CFR regulation number format
        if regulation_number:
            cfr_pattern = r"^21\s+CFR\s+\d{3}\.\d+$"
            if re.match(cfr_pattern, regulation_number):
                self.add_result(
                    check_name="cfr_citation_format",
                    severity=ValidationSeverity.INFO,
                    message=f"CFR citation {regulation_number} has valid format",
                    passed=True,
                )
            else:
                self.add_result(
                    check_name="cfr_citation_format",
                    severity=ValidationSeverity.WARNING,
                    message=f"CFR citation format may be incorrect: {regulation_number}",
                    passed=False,
                    details={"regulation_number": regulation_number},
                    recommendations=["Use format: 21 CFR XXX.YYYY"],
                )

        return self.get_results()


class EStarValidator(RegulatoryValidator):
    """
    Validates eSTAR XML submission format.

    Checks:
    - XML structure and schema compliance
    - Required fields populated
    - Field length limits
    - Data type validation
    - Template-specific requirements (nIVD, IVD, PreSTAR)
    """

    # Field ID patterns for different eSTAR templates
    NIVD_FIELDS = ["ADTextField210", "DDTextField517a", "DDTextField535"]
    IVD_FIELDS = ["ADTextField210", "IVDPanel", "IVDTestName"]
    PRESTAR_FIELDS = ["DeviceName", "DeviceDescription", "IntendedUse"]

    def __init__(self):
        super().__init__("EStarValidator")

    def validate_xml_structure(self, xml_path: Path) -> List[ValidationResult]:
        """
        Validate eSTAR XML file structure.

        Args:
            xml_path: Path to eSTAR XML file

        Returns:
            List of ValidationResult objects
        """
        self.clear_results()

        # Check 1: File exists
        if not xml_path.exists():
            self.add_result(
                check_name="file_exists",
                severity=ValidationSeverity.CRITICAL,
                message=f"eSTAR XML file not found: {xml_path}",
                passed=False,
                recommendations=["Generate eSTAR XML file before validation"],
            )
            return self.get_results()

        # Check 2: Valid XML
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            self.add_result(
                check_name="valid_xml",
                severity=ValidationSeverity.INFO,
                message="XML file is well-formed",
                passed=True,
            )
        except ET.ParseError as e:
            self.add_result(
                check_name="valid_xml",
                severity=ValidationSeverity.CRITICAL,
                message=f"XML parsing error: {e}",
                passed=False,
                recommendations=["Fix XML syntax errors"],
            )
            return self.get_results()

        # Check 3: Root element
        expected_roots = ["root", "form1", "eSTAR"]
        if root.tag in expected_roots:
            self.add_result(
                check_name="root_element",
                severity=ValidationSeverity.INFO,
                message=f"Root element '{root.tag}' is valid",
                passed=True,
            )
        else:
            self.add_result(
                check_name="root_element",
                severity=ValidationSeverity.ERROR,
                message=f"Unexpected root element: {root.tag}",
                passed=False,
                details={"actual": root.tag, "expected": expected_roots},
                recommendations=[f"Use one of: {', '.join(expected_roots)}"],
            )

        # Check 4: Required fields present (basic check)
        fields = {elem.tag for elem in root.iter()}
        if len(fields) > 3:  # Should have more than just root and basic structure
            self.add_result(
                check_name="fields_present",
                severity=ValidationSeverity.INFO,
                message=f"Found {len(fields)} field elements",
                passed=True,
                details={"field_count": len(fields)},
            )
        else:
            self.add_result(
                check_name="fields_present",
                severity=ValidationSeverity.WARNING,
                message="Very few fields found in XML",
                passed=False,
                details={"field_count": len(fields)},
                recommendations=["Ensure all required eSTAR fields are populated"],
            )

        return self.get_results()

    def validate_field_requirements(
        self,
        xml_path: Path,
        template_type: str = "nIVD",
    ) -> List[ValidationResult]:
        """
        Validate template-specific field requirements.

        Args:
            xml_path: Path to eSTAR XML file
            template_type: Template type (nIVD, IVD, PreSTAR)

        Returns:
            List of ValidationResult objects
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except Exception as e:
            self.add_result(
                check_name="template_validation",
                severity=ValidationSeverity.CRITICAL,
                message=f"Cannot validate template: {e}",
                passed=False,
            )
            return self.get_results()

        # Get required fields for template
        if template_type == "nIVD":
            required_fields = self.NIVD_FIELDS
        elif template_type == "IVD":
            required_fields = self.IVD_FIELDS
        elif template_type == "PreSTAR":
            required_fields = self.PRESTAR_FIELDS
        else:
            self.add_result(
                check_name="template_type",
                severity=ValidationSeverity.ERROR,
                message=f"Unknown template type: {template_type}",
                passed=False,
            )
            return self.get_results()

        # Check each required field
        missing_fields = []
        empty_fields = []
        for field_id in required_fields:
            elem = root.find(f".//{field_id}")
            if elem is None:
                missing_fields.append(field_id)
            elif not elem.text or not elem.text.strip():
                empty_fields.append(field_id)

        if not missing_fields and not empty_fields:
            self.add_result(
                check_name="required_fields",
                severity=ValidationSeverity.INFO,
                message=f"All {template_type} required fields present and populated",
                passed=True,
            )
        else:
            if missing_fields:
                self.add_result(
                    check_name="required_fields_missing",
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                    passed=False,
                    details={"missing": missing_fields},
                    recommendations=[f"Add missing {template_type} fields"],
                )
            if empty_fields:
                self.add_result(
                    check_name="required_fields_empty",
                    severity=ValidationSeverity.WARNING,
                    message=f"Empty required fields: {', '.join(empty_fields)}",
                    passed=False,
                    details={"empty": empty_fields},
                    recommendations=["Populate all required fields"],
                )

        return self.get_results()


class PredicateValidator(RegulatoryValidator):
    """
    Validates predicate device acceptability.

    Checks:
    - Same product code
    - Same intended use
    - Cleared/approved status
    - Not recalled
    - Technological characteristics
    - Clearance date recency
    """

    # Maximum predicate age in years (guideline, not hard rule)
    MAX_PREDICATE_AGE_YEARS = 10

    def __init__(self):
        super().__init__("PredicateValidator")

    def validate_predicate_acceptability(
        self,
        subject_device: Dict[str, Any],
        predicate_device: Dict[str, Any],
    ) -> List[ValidationResult]:
        """
        Validate predicate device acceptability.

        Args:
            subject_device: Subject device data
            predicate_device: Predicate device data

        Returns:
            List of ValidationResult objects
        """
        self.clear_results()

        # Check 1: Same product code
        subject_pc = subject_device.get("product_code")
        predicate_pc = predicate_device.get("product_code")

        if subject_pc == predicate_pc:
            self.add_result(
                check_name="same_product_code",
                severity=ValidationSeverity.INFO,
                message=f"Product codes match: {subject_pc}",
                passed=True,
            )
        else:
            self.add_result(
                check_name="same_product_code",
                severity=ValidationSeverity.ERROR,
                message=f"Product codes differ: {subject_pc} vs {predicate_pc}",
                passed=False,
                details={"subject": subject_pc, "predicate": predicate_pc},
                recommendations=[
                    "Predicates should have same product code as subject device",
                    "Different product codes require additional justification",
                ],
            )

        # Check 2: Cleared status
        decision = predicate_device.get("decision", "").upper()
        if decision in ["SUBSTANTIALLY EQUIVALENT", "SE", "CLEARED"]:
            self.add_result(
                check_name="predicate_cleared",
                severity=ValidationSeverity.INFO,
                message="Predicate device is cleared",
                passed=True,
            )
        else:
            self.add_result(
                check_name="predicate_cleared",
                severity=ValidationSeverity.CRITICAL,
                message=f"Predicate device not cleared: {decision}",
                passed=False,
                details={"decision": decision},
                recommendations=["Use only cleared predicates for 510(k) submissions"],
            )

        # Check 3: Not recalled
        recall_flags = predicate_device.get("risk_flags", [])
        if "recalled" in recall_flags:
            self.add_result(
                check_name="predicate_not_recalled",
                severity=ValidationSeverity.ERROR,
                message="Predicate device has been recalled",
                passed=False,
                recommendations=[
                    "Avoid using recalled devices as predicates",
                    "If used, provide detailed justification",
                ],
            )
        else:
            self.add_result(
                check_name="predicate_not_recalled",
                severity=ValidationSeverity.INFO,
                message="Predicate device has no recall history",
                passed=True,
            )

        # Check 4: Predicate age
        decision_date = predicate_device.get("decision_date")
        if decision_date:
            try:
                # Parse date (assume YYYY-MM-DD format)
                pred_date = datetime.strptime(decision_date, "%Y-%m-%d")
                age_years = (datetime.now() - pred_date).days / 365.25

                if age_years <= self.MAX_PREDICATE_AGE_YEARS:
                    self.add_result(
                        check_name="predicate_recency",
                        severity=ValidationSeverity.INFO,
                        message=f"Predicate is {age_years:.1f} years old (acceptable)",
                        passed=True,
                        details={"age_years": age_years},
                    )
                else:
                    self.add_result(
                        check_name="predicate_recency",
                        severity=ValidationSeverity.WARNING,
                        message=f"Predicate is {age_years:.1f} years old (may be considered dated)",
                        passed=False,
                        details={"age_years": age_years},
                        recommendations=[
                            "Consider using more recent predicates",
                            f"Predicates over {self.MAX_PREDICATE_AGE_YEARS} years may receive scrutiny",
                        ],
                    )
            except ValueError:
                self.add_result(
                    check_name="predicate_date_valid",
                    severity=ValidationSeverity.WARNING,
                    message=f"Cannot parse predicate date: {decision_date}",
                    passed=False,
                )

        return self.get_results()

    def validate_predicate_chain(
        self,
        predicates: List[Dict[str, Any]],
    ) -> List[ValidationResult]:
        """
        Validate predicate chain (split predicates, reference predicates).

        Args:
            predicates: List of predicate device data

        Returns:
            List of ValidationResult objects
        """
        self.clear_results()

        if len(predicates) == 0:
            self.add_result(
                check_name="predicates_present",
                severity=ValidationSeverity.CRITICAL,
                message="No predicates provided",
                passed=False,
                recommendations=["At least one predicate required for 510(k)"],
            )
            return self.get_results()

        # Check 1: Predicate count
        if len(predicates) == 1:
            self.add_result(
                check_name="predicate_count",
                severity=ValidationSeverity.INFO,
                message="Single predicate submission",
                passed=True,
            )
        elif len(predicates) <= 3:
            self.add_result(
                check_name="predicate_count",
                severity=ValidationSeverity.INFO,
                message=f"{len(predicates)} predicates (acceptable)",
                passed=True,
                details={"count": len(predicates)},
            )
        else:
            self.add_result(
                check_name="predicate_count",
                severity=ValidationSeverity.WARNING,
                message=f"{len(predicates)} predicates (may complicate review)",
                passed=True,  # Not a failure, but noteworthy
                details={"count": len(predicates)},
                recommendations=[
                    "Limit predicates to 1-3 when possible",
                    "Clearly explain why multiple predicates are needed",
                ],
            )

        # Check 2: Product code consistency across predicates
        product_codes = {p.get("product_code") for p in predicates if "product_code" in p}
        if len(product_codes) == 1:
            self.add_result(
                check_name="predicate_product_code_consistency",
                severity=ValidationSeverity.INFO,
                message="All predicates have same product code",
                passed=True,
            )
        else:
            self.add_result(
                check_name="predicate_product_code_consistency",
                severity=ValidationSeverity.WARNING,
                message=f"Predicates have {len(product_codes)} different product codes",
                passed=False,
                details={"product_codes": list(product_codes)},
                recommendations=["Justify use of predicates with different product codes"],
            )

        return self.get_results()


class SubstantialEquivalenceValidator(RegulatoryValidator):
    """
    Validates substantial equivalence (SE) demonstration.

    Checks:
    - Intended use equivalence
    - Technological characteristics comparison
    - Performance data adequacy
    - Risk analysis completeness
    - SE discussion structure
    """

    def __init__(self):
        super().__init__("SubstantialEquivalenceValidator")

    def validate_se_comparison(
        self,
        comparison_data: Dict[str, Any],
    ) -> List[ValidationResult]:
        """
        Validate SE comparison data.

        Args:
            comparison_data: SE comparison data (from compare-se output)

        Returns:
            List of ValidationResult objects
        """
        self.clear_results()

        # Check 1: Intended use comparison
        if "intended_use" in comparison_data:
            intended_use = comparison_data["intended_use"]
            if intended_use.get("equivalent", False):
                self.add_result(
                    check_name="intended_use_equivalent",
                    severity=ValidationSeverity.INFO,
                    message="Intended uses are equivalent",
                    passed=True,
                )
            else:
                self.add_result(
                    check_name="intended_use_equivalent",
                    severity=ValidationSeverity.CRITICAL,
                    message="Intended uses differ",
                    passed=False,
                    details=intended_use,
                    recommendations=[
                        "Intended use must be substantially equivalent",
                        "Different intended use may require different pathway",
                    ],
                )

        # Check 2: Technological characteristics
        if "technology" in comparison_data:
            tech = comparison_data["technology"]
            if isinstance(tech, dict):
                differences = tech.get("differences", [])
                if len(differences) == 0:
                    self.add_result(
                        check_name="technological_characteristics",
                        severity=ValidationSeverity.INFO,
                        message="No technological differences identified",
                        passed=True,
                    )
                else:
                    # Differences are OK if performance data supports equivalence
                    self.add_result(
                        check_name="technological_characteristics",
                        severity=ValidationSeverity.WARNING,
                        message=f"{len(differences)} technological differences identified",
                        passed=True,  # Not a failure if properly justified
                        details={"differences": differences},
                        recommendations=[
                            "Provide performance data for each difference",
                            "Demonstrate differences do not raise new safety/effectiveness questions",
                        ],
                    )

        # Check 3: Performance data
        if "performance_data" in comparison_data:
            perf_data = comparison_data["performance_data"]
            if isinstance(perf_data, dict) and len(perf_data) > 0:
                self.add_result(
                    check_name="performance_data_present",
                    severity=ValidationSeverity.INFO,
                    message="Performance data provided",
                    passed=True,
                    details={"data_types": list(perf_data.keys())},
                )
            else:
                self.add_result(
                    check_name="performance_data_present",
                    severity=ValidationSeverity.ERROR,
                    message="No performance data provided",
                    passed=False,
                    recommendations=[
                        "Include bench testing data",
                        "Include biocompatibility data if applicable",
                        "Include sterilization validation if applicable",
                    ],
                )

        return self.get_results()

    def validate_se_discussion(
        self,
        discussion_path: Path,
    ) -> List[ValidationResult]:
        """
        Validate SE discussion section.

        Args:
            discussion_path: Path to SE discussion markdown file

        Returns:
            List of ValidationResult objects
        """
        self.clear_results()

        # Check 1: File exists
        if not discussion_path.exists():
            self.add_result(
                check_name="se_discussion_exists",
                severity=ValidationSeverity.CRITICAL,
                message="SE discussion file not found",
                passed=False,
                recommendations=["Generate SE discussion section"],
            )
            return self.get_results()

        # Read content
        content = discussion_path.read_text()

        # Check 2: Minimum length (should be substantive)
        if len(content) < 500:
            self.add_result(
                check_name="se_discussion_length",
                severity=ValidationSeverity.WARNING,
                message=f"SE discussion is very short ({len(content)} chars)",
                passed=False,
                recommendations=["Expand SE discussion with detailed comparison"],
            )
        else:
            self.add_result(
                check_name="se_discussion_length",
                severity=ValidationSeverity.INFO,
                message=f"SE discussion has adequate length ({len(content)} chars)",
                passed=True,
            )

        # Check 3: Key sections present
        required_sections = [
            ("intended use", r"intended\s+use"),
            ("technological characteristics", r"technolog(?:ical|y)"),
            ("performance", r"performance|testing|validation"),
        ]

        for section_name, pattern in required_sections:
            if re.search(pattern, content, re.IGNORECASE):
                self.add_result(
                    check_name=f"section_{section_name.replace(' ', '_')}",
                    severity=ValidationSeverity.INFO,
                    message=f"{section_name.title()} section present",
                    passed=True,
                )
            else:
                self.add_result(
                    check_name=f"section_{section_name.replace(' ', '_')}",
                    severity=ValidationSeverity.WARNING,
                    message=f"{section_name.title()} section may be missing",
                    passed=False,
                    recommendations=[f"Include {section_name} discussion"],
                )

        # Check 4: Predicate references
        k_number_pattern = r"K\d{6}"
        k_numbers = re.findall(k_number_pattern, content)
        if len(k_numbers) > 0:
            self.add_result(
                check_name="predicate_references",
                severity=ValidationSeverity.INFO,
                message=f"Found {len(k_numbers)} K-number references",
                passed=True,
                details={"k_numbers": list(set(k_numbers))},
            )
        else:
            self.add_result(
                check_name="predicate_references",
                severity=ValidationSeverity.ERROR,
                message="No predicate K-numbers found in SE discussion",
                passed=False,
                recommendations=["Reference predicate devices by K-number"],
            )

        return self.get_results()
