"""
End-to-End Test Helper Utilities

Provides comprehensive helper classes and functions for E2E workflow testing:
- WorkflowRunner: Orchestrates complete submission workflows
- DataManager: Manages test data and project files
- Assertions: Domain-specific assertions for FDA submissions
- Stage tracking and validation
- Integration test helpers

Version: 1.0.0
Date: 2026-02-20
Issue: FDA-174 (QA-001)
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
import logging

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """FDA submission workflow stages."""

    INITIALIZATION = "initialization"
    DATA_COLLECTION = "data_collection"
    PREDICATE_SEARCH = "predicate_search"
    PREDICATE_REVIEW = "predicate_review"
    COMPARISON = "comparison"
    DRAFTING = "drafting"
    CONSISTENCY_CHECK = "consistency_check"
    ASSEMBLY = "assembly"
    EXPORT = "export"
    VALIDATION = "validation"

    def __str__(self):
        return self.value


@dataclass
class WorkflowResult:
    """Result of a workflow stage execution."""

    stage: WorkflowStage
    success: bool
    duration: float  # seconds
    artifacts: Dict[str, Path] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Check if stage passed (success and no errors)."""
        return self.success and len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stage": self.stage.value,
            "success": self.success,
            "duration": self.duration,
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
            "metrics": self.metrics,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class E2EWorkflowRunner:
    """
    Orchestrates complete FDA submission workflows for E2E testing.

    Supports:
    - Traditional 510(k)
    - Special 510(k)
    - Abbreviated 510(k)
    - PMA submissions
    - De Novo requests

    Example:
        >>> runner = E2EWorkflowRunner(project_dir, workflow_type="traditional_510k")
        >>> runner.setup_project()
        >>> runner.run_data_collection(product_code="DQY")
        >>> runner.run_predicate_search()
        >>> runner.run_predicate_review()
        >>> results = runner.get_results()
    """

    def __init__(
        self,
        project_dir: Path,
        workflow_type: str = "traditional_510k",
        mock_mode: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize workflow runner.

        Args:
            project_dir: Path to test project directory
            workflow_type: Type of workflow (traditional_510k, special_510k, pma, etc.)
            mock_mode: Use mock APIs instead of real API calls
            config: Optional configuration overrides
        """
        self.project_dir = Path(project_dir)
        self.workflow_type = workflow_type
        self.mock_mode = mock_mode
        self.config = config or {}

        self.results: List[WorkflowResult] = []
        self.current_stage: Optional[WorkflowStage] = None
        self.start_time: Optional[datetime] = None

        # Ensure project directory exists
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Initialize standard project structure
        self._init_project_structure()

    def _init_project_structure(self) -> None:
        """Initialize standard FDA project directory structure."""
        subdirs = [
            "data",
            "drafts",
            "calculations",
            "safety_cache",
            "literature_cache",
        ]
        for subdir in subdirs:
            (self.project_dir / subdir).mkdir(exist_ok=True)

    def setup_project(
        self,
        device_profile: Optional[Dict[str, Any]] = None,
        product_code: Optional[str] = None,
    ) -> WorkflowResult:
        """
        Initialize project with device profile.

        Args:
            device_profile: Device profile data (optional, will generate if not provided)
            product_code: Product code for device (required if device_profile not provided)

        Returns:
            WorkflowResult for initialization stage
        """
        self.current_stage = WorkflowStage.INITIALIZATION
        start = datetime.now(timezone.utc)

        try:
            # Create device profile
            if device_profile is None:
                if product_code is None:
                    raise ValueError("Must provide either device_profile or product_code")
                device_profile = self._generate_device_profile(product_code)

            # Write device profile
            profile_path = self.project_dir / "device_profile.json"
            with open(profile_path, "w") as f:
                json.dump(device_profile, f, indent=2)

            # Create query.json
            query_data = {
                "project": self.project_dir.name,
                "product_code": device_profile.get("product_code"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            query_path = self.project_dir / "query.json"
            with open(query_path, "w") as f:
                json.dump(query_data, f, indent=2)

            duration = (datetime.now(timezone.utc) - start).total_seconds()

            result = WorkflowResult(
                stage=WorkflowStage.INITIALIZATION,
                success=True,
                duration=duration,
                artifacts={
                    "device_profile": profile_path,
                    "query": query_path,
                },
                metrics={
                    "product_code": device_profile.get("product_code"),
                },
            )

            self.results.append(result)
            return result

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            result = WorkflowResult(
                stage=WorkflowStage.INITIALIZATION,
                success=False,
                duration=duration,
                errors=[str(e)],
            )
            self.results.append(result)
            return result

    def _generate_device_profile(self, product_code: str) -> Dict[str, Any]:
        """Generate minimal device profile for testing."""
        return {
            "product_code": product_code,
            "device_name": f"Test Device {product_code}",
            "device_class": "II",
            "regulation_number": "21 CFR 880.XXXX",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def run_data_collection(
        self,
        product_code: str,
        years: Optional[List[int]] = None,
        mock_data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Run data collection stage (batchfetch).

        Args:
            product_code: FDA product code
            years: Years to fetch data for
            mock_data: Mock API response data (if mock_mode=True)

        Returns:
            WorkflowResult for data collection stage
        """
        self.current_stage = WorkflowStage.DATA_COLLECTION
        start = datetime.now(timezone.utc)

        try:
            # In mock mode, use provided mock data
            if self.mock_mode and mock_data:
                clearances = mock_data.get("clearances", [])
            else:
                # Would call real batchfetch here
                clearances = []

            # Write output.csv
            output_path = self.project_dir / "output.csv"
            self._write_clearances_csv(clearances, output_path)

            duration = (datetime.now(timezone.utc) - start).total_seconds()

            result = WorkflowResult(
                stage=WorkflowStage.DATA_COLLECTION,
                success=True,
                duration=duration,
                artifacts={"output_csv": output_path},
                metrics={
                    "clearances_count": len(clearances),
                    "product_code": product_code,
                },
            )

            self.results.append(result)
            return result

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            result = WorkflowResult(
                stage=WorkflowStage.DATA_COLLECTION,
                success=False,
                duration=duration,
                errors=[str(e)],
            )
            self.results.append(result)
            return result

    def _write_clearances_csv(
        self,
        clearances: List[Dict[str, Any]],
        output_path: Path,
    ) -> None:
        """Write clearances to CSV file."""
        import csv

        with open(output_path, "w", newline="") as f:
            if not clearances:
                # Empty CSV with headers
                writer = csv.writer(f)
                writer.writerow(["K-Number", "Product Code", "Document Type"])
                return

            # Write clearances
            writer = csv.DictWriter(f, fieldnames=clearances[0].keys())
            writer.writeheader()
            writer.writerows(clearances)

    def run_predicate_review(
        self,
        review_data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Run predicate review stage.

        Args:
            review_data: Predicate review data (will generate if not provided)

        Returns:
            WorkflowResult for predicate review stage
        """
        self.current_stage = WorkflowStage.PREDICATE_REVIEW
        start = datetime.now(timezone.utc)

        try:
            if review_data is None:
                # Generate minimal review data
                review_data = self._generate_review_data()

            # Write review.json
            review_path = self.project_dir / "review.json"
            with open(review_path, "w") as f:
                json.dump(review_data, f, indent=2)

            # Calculate metrics
            predicates = review_data.get("predicates", {})
            accepted = sum(
                1 for p in predicates.values() if p.get("decision") == "accepted"
            )

            duration = (datetime.now(timezone.utc) - start).total_seconds()

            result = WorkflowResult(
                stage=WorkflowStage.PREDICATE_REVIEW,
                success=True,
                duration=duration,
                artifacts={"review": review_path},
                metrics={
                    "total_predicates": len(predicates),
                    "accepted_predicates": accepted,
                },
            )

            self.results.append(result)
            return result

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            result = WorkflowResult(
                stage=WorkflowStage.PREDICATE_REVIEW,
                success=False,
                duration=duration,
                errors=[str(e)],
            )
            self.results.append(result)
            return result

    def _generate_review_data(self) -> Dict[str, Any]:
        """Generate minimal review data for testing."""
        return {
            "project": self.project_dir.name,
            "product_code": "TEST",
            "predicates": {},
            "summary": {
                "total_evaluated": 0,
                "accepted": 0,
                "rejected": 0,
            },
        }

    def run_drafting(
        self,
        sections: Optional[List[str]] = None,
    ) -> WorkflowResult:
        """
        Run drafting stage.

        Args:
            sections: List of sections to draft (None = all required sections)

        Returns:
            WorkflowResult for drafting stage
        """
        self.current_stage = WorkflowStage.DRAFTING
        start = datetime.now(timezone.utc)

        try:
            if sections is None:
                sections = [
                    "device-description",
                    "se-discussion",
                    "performance-testing",
                ]

            drafts_dir = self.project_dir / "drafts"
            drafts_dir.mkdir(exist_ok=True)

            artifacts = {}
            for section in sections:
                draft_path = drafts_dir / f"{section}.md"
                self._write_draft_section(section, draft_path)
                artifacts[section] = draft_path

            duration = (datetime.now(timezone.utc) - start).total_seconds()

            result = WorkflowResult(
                stage=WorkflowStage.DRAFTING,
                success=True,
                duration=duration,
                artifacts=artifacts,
                metrics={"sections_drafted": len(sections)},
            )

            self.results.append(result)
            return result

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            result = WorkflowResult(
                stage=WorkflowStage.DRAFTING,
                success=False,
                duration=duration,
                errors=[str(e)],
            )
            self.results.append(result)
            return result

    def _write_draft_section(self, section: str, path: Path) -> None:
        """Write minimal draft section for testing."""
        content = f"# {section.replace('-', ' ').title()}\n\n"
        content += f"[DRAFT - Generated for testing]\n\n"
        content += f"This is a test draft section.\n"

        with open(path, "w") as f:
            f.write(content)

    def run_assembly(self) -> WorkflowResult:
        """
        Run assembly stage (combine drafts into submission package).

        Returns:
            WorkflowResult for assembly stage
        """
        self.current_stage = WorkflowStage.ASSEMBLY
        start = datetime.now(timezone.utc)

        try:
            # Create submission package directory
            package_dir = self.project_dir / "submission_package"
            package_dir.mkdir(exist_ok=True)

            # Copy drafts to package
            drafts_dir = self.project_dir / "drafts"
            if drafts_dir.exists():
                for draft in drafts_dir.glob("*.md"):
                    shutil.copy(draft, package_dir / draft.name)

            duration = (datetime.now(timezone.utc) - start).total_seconds()

            result = WorkflowResult(
                stage=WorkflowStage.ASSEMBLY,
                success=True,
                duration=duration,
                artifacts={"package_dir": package_dir},
            )

            self.results.append(result)
            return result

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            result = WorkflowResult(
                stage=WorkflowStage.ASSEMBLY,
                success=False,
                duration=duration,
                errors=[str(e)],
            )
            self.results.append(result)
            return result

    def get_results(self) -> List[WorkflowResult]:
        """Get all workflow stage results."""
        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """Get workflow execution summary."""
        total_duration = sum(r.duration for r in self.results)
        passed = sum(1 for r in self.results if r.passed)

        return {
            "workflow_type": self.workflow_type,
            "total_stages": len(self.results),
            "passed_stages": passed,
            "failed_stages": len(self.results) - passed,
            "total_duration": total_duration,
            "stages": [r.to_dict() for r in self.results],
        }

    def cleanup(self) -> None:
        """Clean up test project directory."""
        if self.project_dir.exists():
            shutil.rmtree(self.project_dir)


class E2EDataManager:
    """
    Manages test data and project files for E2E testing.

    Provides utilities for:
    - Creating realistic test data
    - Managing project files
    - Data validation
    - Fixture generation
    """

    @staticmethod
    def create_device_profile(
        product_code: str,
        device_class: str = "II",
        include_software: bool = False,
        combination_product: bool = False,
    ) -> Dict[str, Any]:
        """
        Create realistic device profile for testing.

        Args:
            product_code: FDA product code
            device_class: Device class (I, II, III)
            include_software: Include software components
            combination_product: Mark as combination product

        Returns:
            Device profile dictionary
        """
        profile = {
            "product_code": product_code,
            "device_class": device_class,
            "device_name": f"Test Device {product_code}",
            "regulation_number": f"21 CFR 8XX.XXXX",
            "intended_use": "Test device for E2E testing",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if include_software:
            profile["software_level"] = "moderate"
            profile["samd"] = True

        if combination_product:
            profile["combination_product"] = True
            profile["primary_mode_of_action"] = "device"

        return profile

    @staticmethod
    def create_predicate_data(
        k_number: str,
        product_code: str,
        decision: str = "accepted",
        confidence_score: int = 85,
    ) -> Dict[str, Any]:
        """
        Create predicate device data for testing.

        Args:
            k_number: K-number (e.g., "K213456")
            product_code: FDA product code
            decision: "accepted" or "rejected"
            confidence_score: Score 0-100

        Returns:
            Predicate data dictionary
        """
        return {
            "device_name": f"Predicate Device {k_number}",
            "applicant": "Test Applicant Inc.",
            "decision_date": "2023-01-15",
            "product_code": product_code,
            "decision": decision,
            "confidence_score": confidence_score,
            "rationale": f"Test predicate {decision} rationale",
            "risk_flags": [] if decision == "accepted" else ["test_flag"],
            "source": "test_data",
        }

    @staticmethod
    def create_review_data(
        product_code: str,
        predicates: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Create predicate review data for testing.

        Args:
            product_code: FDA product code
            predicates: Dictionary of K-number -> predicate data

        Returns:
            Review data dictionary
        """
        if predicates is None:
            predicates = {}

        accepted = sum(1 for p in predicates.values() if p.get("decision") == "accepted")
        rejected = len(predicates) - accepted

        return {
            "project": "test_project",
            "product_code": product_code,
            "predicates": predicates,
            "summary": {
                "total_evaluated": len(predicates),
                "accepted": accepted,
                "rejected": rejected,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }


class E2EAssertions:
    """
    Domain-specific assertions for FDA submission E2E testing.

    Provides high-level assertions that check business logic and
    regulatory compliance rather than implementation details.
    """

    @staticmethod
    def assert_project_structure_valid(project_dir: Path) -> None:
        """
        Assert project has valid FDA submission structure.

        Args:
            project_dir: Path to project directory

        Raises:
            AssertionError: If project structure is invalid
        """
        required_files = ["device_profile.json", "query.json"]
        for filename in required_files:
            filepath = project_dir / filename
            assert filepath.exists(), f"Missing required file: {filename}"

        # Check standard directories exist
        expected_dirs = ["drafts", "data"]
        for dirname in expected_dirs:
            dirpath = project_dir / dirname
            assert dirpath.exists(), f"Missing required directory: {dirname}"
            assert dirpath.is_dir(), f"{dirname} is not a directory"

    @staticmethod
    def assert_device_profile_valid(profile: Dict[str, Any]) -> None:
        """
        Assert device profile has required fields and valid data.

        Args:
            profile: Device profile dictionary

        Raises:
            AssertionError: If device profile is invalid
        """
        required_fields = ["product_code", "device_class", "device_name"]
        for field in required_fields:
            assert field in profile, f"Missing required field: {field}"
            assert profile[field], f"Field {field} is empty"

        # Validate product code format (3 uppercase letters)
        pc = profile["product_code"]
        assert len(pc) == 3, f"Product code must be 3 characters: {pc}"
        assert pc.isalpha(), f"Product code must be alphabetic: {pc}"
        assert pc.isupper(), f"Product code must be uppercase: {pc}"

        # Validate device class
        valid_classes = ["I", "II", "III", "U", "f"]
        dc = profile["device_class"]
        assert dc in valid_classes, f"Invalid device class: {dc}"

    @staticmethod
    def assert_review_data_valid(review: Dict[str, Any]) -> None:
        """
        Assert review data has required fields and consistent counts.

        Args:
            review: Review data dictionary

        Raises:
            AssertionError: If review data is invalid
        """
        required_fields = ["predicates", "summary", "product_code"]
        for field in required_fields:
            assert field in review, f"Missing required field: {field}"

        # Check summary counts match predicates
        predicates = review["predicates"]
        summary = review["summary"]

        accepted = sum(1 for p in predicates.values() if p.get("decision") == "accepted")
        rejected = sum(1 for p in predicates.values() if p.get("decision") == "rejected")

        assert summary["accepted"] == accepted, "Summary accepted count mismatch"
        assert summary["rejected"] == rejected, "Summary rejected count mismatch"
        assert summary["total_evaluated"] == len(predicates), "Summary total count mismatch"

    @staticmethod
    def assert_workflow_completed_successfully(results: List[WorkflowResult]) -> None:
        """
        Assert all workflow stages completed successfully.

        Args:
            results: List of WorkflowResult objects

        Raises:
            AssertionError: If any stage failed
        """
        assert len(results) > 0, "No workflow results found"

        for result in results:
            assert result.success, f"Stage {result.stage} failed: {result.errors}"
            assert len(result.errors) == 0, f"Stage {result.stage} has errors: {result.errors}"

    @staticmethod
    def assert_draft_section_valid(section_path: Path) -> None:
        """
        Assert draft section file is valid.

        Args:
            section_path: Path to draft section markdown file

        Raises:
            AssertionError: If draft section is invalid
        """
        assert section_path.exists(), f"Draft section not found: {section_path}"
        assert section_path.suffix == ".md", f"Draft section must be .md file: {section_path}"

        content = section_path.read_text()
        assert len(content) > 0, f"Draft section is empty: {section_path}"
        assert content.startswith("#"), f"Draft section must start with markdown header: {section_path}"

    @staticmethod
    def assert_clearances_csv_valid(csv_path: Path, min_rows: int = 0) -> None:
        """
        Assert clearances CSV file is valid.

        Args:
            csv_path: Path to output.csv file
            min_rows: Minimum number of data rows required

        Raises:
            AssertionError: If CSV is invalid
        """
        import csv

        assert csv_path.exists(), f"CSV file not found: {csv_path}"

        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) > 0, "CSV file is empty"

        # Check header row exists
        header = rows[0]
        assert len(header) > 0, "CSV header is empty"

        # Check minimum data rows
        data_rows = rows[1:]
        assert len(data_rows) >= min_rows, \
            f"Expected at least {min_rows} data rows, got {len(data_rows)}"


# ---------------------------------------------------------------------------
# Legacy helper stubs for test compatibility
# ---------------------------------------------------------------------------

def verify_file_exists(path: "Path | str") -> bool:
    """Verify a file exists, raising AssertionError if not."""
    p = Path(path)
    assert p.exists(), f"Expected file does not exist: {p}"
    return True


def load_json_safe(path: "Path | str") -> dict:
    """Load JSON from path, returning empty dict on any error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


class E2ETestProject:
    """Minimal test project context manager for legacy e2e tests."""

    def __init__(self, tmp_path: "Path | str", name: str = "test_project"):
        self.project_dir = Path(tmp_path) / name
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def write_file(self, filename: str, content: str) -> Path:
        p = self.project_dir / filename
        p.write_text(content)
        return p

    def write_json(self, filename: str, data: dict) -> Path:
        return self.write_file(filename, json.dumps(data, indent=2))


def compare_json_files(path1: "Path | str", path2: "Path | str") -> bool:
    """Return True if two JSON files have equal content."""
    with open(path1) as f1, open(path2) as f2:
        return json.load(f1) == json.load(f2)


def count_estar_sections(path: "Path | str") -> int:
    """Count top-level sections in an eSTAR XML file."""
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        return len(list(root))
    except Exception:
        return 0


def create_seed_device_profile(
    project_dir: "Path | str",
    product_code: str = "DQY",
    device_name: str = "Test Device",
    **kwargs,
) -> dict:
    """Write a minimal device_profile.json and return the dict."""
    profile = {
        "product_code": product_code,
        "device_name": device_name,
        "indications_for_use": kwargs.get("indications_for_use", ""),
        **kwargs,
    }
    out = Path(project_dir) / "device_profile.json"
    out.write_text(json.dumps(profile, indent=2))
    return profile
