### E2E Testing Infrastructure Guide

Comprehensive guide to the FDA Tools E2E test infrastructure for complete workflow validation.

**Version:** 1.0.0
**Date:** 2026-02-20
**Issue:** FDA-174 (QA-001)
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [E2E Helper Utilities](#e2e-helper-utilities)
5. [Regulatory Validators](#regulatory-validators)
6. [Writing E2E Tests](#writing-e2e-tests)
7. [Test Patterns](#test-patterns)
8. [Integration with CI/CD](#integration-with-cicd)
9. [Performance Guidelines](#performance-guidelines)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The E2E testing infrastructure provides comprehensive tools for validating complete FDA submission workflows from initial device profiling through final submission assembly and export.

### Key Features

- **Workflow Orchestration**: Complete workflow runners for all submission types
- **Regulatory Validation**: FDA compliance checks (21 CFR, eSTAR, SE)
- **Mock Infrastructure**: Comprehensive mocking for APIs and external dependencies
- **Domain Assertions**: High-level assertions for business logic validation
- **Test Data Factories**: Realistic test data generation
- **CI/CD Integration**: Ready for automated testing pipelines

### Supported Workflows

- Traditional 510(k) submissions
- Special 510(k) submissions
- Abbreviated 510(k) submissions
- PMA submissions
- De Novo requests
- HDE submissions
- IDE submissions

---

## Architecture

### Component Structure

```
tests/
├── utils/                           # E2E utilities package
│   ├── __init__.py                 # Package exports
│   ├── e2e_helpers.py              # Workflow runners and assertions
│   └── regulatory_validators.py    # FDA compliance validators
├── e2e/                            # E2E test suite
│   ├── fixtures.py                 # E2E fixtures
│   ├── mocks.py                    # Mock objects
│   ├── test_data.py                # Test data generators
│   └── test_comprehensive_workflows.py
└── test_e2e_utils.py               # Infrastructure tests
```

### Core Components

#### E2E Helpers (`e2e_helpers.py`)

1. **E2EWorkflowRunner**: Orchestrates complete submission workflows
2. **E2EDataManager**: Manages test data and project files
3. **E2EAssertions**: Domain-specific assertions
4. **WorkflowStage**: Enum of workflow stages
5. **WorkflowResult**: Stage execution results

#### Regulatory Validators (`regulatory_validators.py`)

1. **CFRValidator**: 21 CFR compliance validation
2. **EStarValidator**: eSTAR XML format validation
3. **PredicateValidator**: Predicate acceptability validation
4. **SubstantialEquivalenceValidator**: SE demonstration validation
5. **ValidationResult**: Validation findings with severity

---

## Quick Start

### Installation

The E2E infrastructure is included with the FDA Tools plugin. No additional installation required.

### Running E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run fast E2E tests only (<5s each)
pytest -m e2e_fast -v

# Run specific workflow tests
pytest -m e2e_510k -v

# Run with coverage
pytest tests/e2e/ -v --cov=plugins/fda-tools --cov-report=html
```

### Basic Workflow Example

```python
from pathlib import Path
from tests.utils.e2e_helpers import E2EWorkflowRunner

# Create workflow runner
project_dir = Path("/tmp/test_project")
runner = E2EWorkflowRunner(project_dir, workflow_type="traditional_510k")

# Run complete workflow
runner.setup_project(product_code="DQY")
runner.run_data_collection(product_code="DQY")
runner.run_predicate_review()
runner.run_drafting()
runner.run_assembly()

# Get results
summary = runner.get_summary()
print(f"Workflow completed: {summary['passed_stages']}/{summary['total_stages']} stages passed")
```

---

## E2E Helper Utilities

### E2EWorkflowRunner

Orchestrates complete FDA submission workflows with stage tracking and error handling.

#### Initialization

```python
runner = E2EWorkflowRunner(
    project_dir=Path("/tmp/test_project"),
    workflow_type="traditional_510k",  # or "special_510k", "pma", "de_novo"
    mock_mode=True,                    # Use mock APIs
    config={"api_timeout": 30}         # Optional config overrides
)
```

#### Workflow Stages

```python
# Stage 1: Initialize project
result = runner.setup_project(
    device_profile=custom_profile,  # Optional
    product_code="DQY"             # Required if no profile
)

# Stage 2: Data collection (batchfetch)
result = runner.run_data_collection(
    product_code="DQY",
    years=[2023, 2024],
    mock_data={"clearances": [...]}
)

# Stage 3: Predicate review
result = runner.run_predicate_review(
    review_data=custom_review  # Optional, will generate if not provided
)

# Stage 4: Drafting
result = runner.run_drafting(
    sections=["device-description", "se-discussion"]  # Optional
)

# Stage 5: Assembly
result = runner.run_assembly()
```

#### Results and Reporting

```python
# Get all stage results
results = runner.get_results()

# Get summary
summary = runner.get_summary()
# Returns:
# {
#   "workflow_type": "traditional_510k",
#   "total_stages": 5,
#   "passed_stages": 5,
#   "failed_stages": 0,
#   "total_duration": 12.5,
#   "stages": [...]
# }

# Check for failures
for result in results:
    if not result.passed:
        print(f"Stage {result.stage} failed: {result.errors}")

# Cleanup
runner.cleanup()  # Removes test project directory
```

### E2EDataManager

Generates realistic test data for FDA submissions.

#### Device Profiles

```python
from tests.utils.e2e_helpers import E2EDataManager

# Standard Class II device
profile = E2EDataManager.create_device_profile(
    product_code="DQY",
    device_class="II"
)

# SaMD device with software
samd_profile = E2EDataManager.create_device_profile(
    product_code="QKQ",
    include_software=True
)

# Combination product
combo_profile = E2EDataManager.create_device_profile(
    product_code="FRO",
    combination_product=True
)
```

#### Predicate Data

```python
# Accepted predicate
predicate = E2EDataManager.create_predicate_data(
    k_number="K213456",
    product_code="DQY",
    decision="accepted",
    confidence_score=92
)

# Rejected predicate
rejected = E2EDataManager.create_predicate_data(
    k_number="K190987",
    product_code="DQY",
    decision="rejected",
    confidence_score=35
)
```

#### Review Data

```python
predicates = {
    "K213456": E2EDataManager.create_predicate_data("K213456", "DQY", "accepted", 92),
    "K201234": E2EDataManager.create_predicate_data("K201234", "DQY", "accepted", 85),
}

review = E2EDataManager.create_review_data(
    product_code="DQY",
    predicates=predicates
)
```

### E2EAssertions

Domain-specific assertions for FDA submission validation.

#### Project Structure

```python
from tests.utils.e2e_helpers import E2EAssertions

# Assert valid project structure
E2EAssertions.assert_project_structure_valid(project_dir)
# Checks: device_profile.json, query.json, drafts/, data/ exist
```

#### Device Profile

```python
# Assert valid device profile
E2EAssertions.assert_device_profile_valid(profile)
# Checks: product_code format, device_class valid, required fields
```

#### Review Data

```python
# Assert valid review data
E2EAssertions.assert_review_data_valid(review)
# Checks: summary counts match predicates, required fields present
```

#### Workflow Completion

```python
# Assert all stages passed
E2EAssertions.assert_workflow_completed_successfully(results)
# Raises if any stage failed
```

#### Draft Sections

```python
# Assert valid draft section
E2EAssertions.assert_draft_section_valid(section_path)
# Checks: file exists, is markdown, starts with header
```

#### CSV Files

```python
# Assert valid clearances CSV
E2EAssertions.assert_clearances_csv_valid(csv_path, min_rows=10)
# Checks: file exists, has header, minimum data rows
```

---

## Regulatory Validators

### CFRValidator

Validates compliance with 21 CFR regulations.

#### Part 11 Compliance

```python
from tests.utils.regulatory_validators import CFRValidator

validator = CFRValidator()

submission_data = {
    "signatures": [...],
    "audit_trail": [...],
    "version": "1.0"
}

results = validator.validate_part_11_compliance(submission_data)

# Check results
for result in results:
    print(f"{result.check_name}: {result.message}")

# Get summary
summary = validator.get_summary()
# {
#   "validator": "CFRValidator",
#   "total_checks": 3,
#   "passed": 3,
#   "failed": 0,
#   "by_severity": {"info": 3, "warning": 0, ...},
#   "overall_status": "PASS"
# }
```

#### Device Classification

```python
results = validator.validate_device_classification(
    product_code="DQY",
    device_class="II",
    regulation_number="21 CFR 870.1340"
)

# Check for critical errors
if validator.has_critical_errors():
    print("CRITICAL: Classification validation failed")
```

### EStarValidator

Validates eSTAR XML submission format.

#### XML Structure

```python
from tests.utils.regulatory_validators import EStarValidator

validator = EStarValidator()

results = validator.validate_xml_structure(Path("estar.xml"))

# Check for parsing errors
for result in results:
    if result.severity == ValidationSeverity.CRITICAL:
        print(f"CRITICAL: {result.message}")
        for rec in result.recommendations:
            print(f"  - {rec}")
```

#### Template Requirements

```python
results = validator.validate_field_requirements(
    xml_path=Path("estar.xml"),
    template_type="nIVD"  # or "IVD", "PreSTAR"
)
```

### PredicateValidator

Validates predicate device acceptability.

#### Predicate Acceptability

```python
from tests.utils.regulatory_validators import PredicateValidator

validator = PredicateValidator()

subject_device = {"product_code": "DQY", "device_name": "Subject Device"}
predicate_device = {
    "product_code": "DQY",
    "decision": "SUBSTANTIALLY EQUIVALENT",
    "decision_date": "2023-01-15",
    "risk_flags": []
}

results = validator.validate_predicate_acceptability(
    subject_device,
    predicate_device
)

# Check specific validations
for result in results:
    if result.check_name == "same_product_code":
        assert result.passed, "Product codes must match"
```

#### Predicate Chain

```python
predicates = [
    {"product_code": "DQY", "decision": "SE"},
    {"product_code": "DQY", "decision": "SE"},
]

results = validator.validate_predicate_chain(predicates)
```

### SubstantialEquivalenceValidator

Validates SE demonstration.

#### SE Comparison

```python
from tests.utils.regulatory_validators import SubstantialEquivalenceValidator

validator = SubstantialEquivalenceValidator()

comparison_data = {
    "intended_use": {"equivalent": True},
    "technology": {"differences": ["material"]},
    "performance_data": {
        "bench_testing": {...},
        "biocompatibility": {...}
    }
}

results = validator.validate_se_comparison(comparison_data)
```

#### SE Discussion

```python
results = validator.validate_se_discussion(
    Path("drafts/se-discussion.md")
)

# Check for required sections
for result in results:
    if "section_" in result.check_name and not result.passed:
        print(f"Missing section: {result.message}")
```

---

## Writing E2E Tests

### Test Structure Template

```python
import pytest
from pathlib import Path
from tests.utils.e2e_helpers import E2EWorkflowRunner, E2EAssertions
from tests.utils.regulatory_validators import CFRValidator

@pytest.mark.e2e
@pytest.mark.e2e_510k
class TestTraditional510kWorkflow:
    """Test complete Traditional 510(k) workflow."""

    def test_complete_workflow(self, tmp_path):
        """
        Test Traditional 510(k) from device profile to final assembly.

        Workflow stages:
            1. Setup project with device profile
            2. Collect FDA clearance data
            3. Review and select predicates
            4. Draft submission sections
            5. Assemble submission package
            6. Validate regulatory compliance
        """
        # Setup
        project_dir = tmp_path / "traditional_510k"
        runner = E2EWorkflowRunner(
            project_dir,
            workflow_type="traditional_510k",
            mock_mode=True
        )

        # Stage 1: Project setup
        result = runner.setup_project(product_code="DQY")
        assert result.passed
        E2EAssertions.assert_project_structure_valid(project_dir)

        # Stage 2: Data collection
        mock_data = {
            "clearances": [
                {"k_number": "K241001", "product_code": "DQY"},
                {"k_number": "K241002", "product_code": "DQY"},
            ]
        }
        result = runner.run_data_collection("DQY", mock_data=mock_data)
        assert result.passed
        assert result.metrics["clearances_count"] == 2

        # Stage 3: Predicate review
        result = runner.run_predicate_review()
        assert result.passed

        # Stage 4: Drafting
        result = runner.run_drafting()
        assert result.passed

        # Stage 5: Assembly
        result = runner.run_assembly()
        assert result.passed

        # Validation
        E2EAssertions.assert_workflow_completed_successfully(runner.get_results())

        # Regulatory compliance checks
        validator = CFRValidator()
        # ... validation logic

        # Cleanup
        runner.cleanup()
```

### Testing Edge Cases

```python
@pytest.mark.e2e
@pytest.mark.e2e_edge_cases
class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_sparse_data_handling(self, tmp_path):
        """Test workflow with minimal/sparse FDA data."""
        # Test with empty clearances
        # Test with missing predicate summaries
        # Test with incomplete device profiles

    def test_samd_device_workflow(self, tmp_path):
        """Test Software as Medical Device (SaMD) workflow."""
        profile = E2EDataManager.create_device_profile(
            product_code="QKQ",
            include_software=True
        )
        # Test software-specific sections
        # Test cybersecurity validation

    def test_combination_product_workflow(self, tmp_path):
        """Test combination product workflow."""
        profile = E2EDataManager.create_device_profile(
            product_code="FRO",
            combination_product=True
        )
        # Test drug/device combination handling
```

### Testing Error Conditions

```python
@pytest.mark.e2e
class TestErrorHandling:
    """Test error handling and recovery."""

    def test_missing_required_data(self, tmp_path):
        """Test handling of missing required data."""
        runner = E2EWorkflowRunner(tmp_path / "test")

        # Should fail gracefully without product_code
        result = runner.setup_project()
        assert not result.passed
        assert len(result.errors) > 0

    def test_invalid_device_profile(self, tmp_path):
        """Test validation of invalid device profile."""
        profile = {"product_code": "invalid"}  # Missing required fields

        with pytest.raises(AssertionError):
            E2EAssertions.assert_device_profile_valid(profile)
```

---

## Test Patterns

### Pattern 1: Complete Workflow Test

Test entire workflow from start to finish.

```python
def test_complete_510k_workflow(tmp_path):
    runner = E2EWorkflowRunner(tmp_path / "project")
    runner.setup_project(product_code="DQY")
    runner.run_data_collection("DQY", mock_data=mock_data)
    runner.run_predicate_review(review_data)
    runner.run_drafting()
    runner.run_assembly()

    E2EAssertions.assert_workflow_completed_successfully(runner.get_results())
```

### Pattern 2: Stage-Specific Test

Test individual workflow stage in isolation.

```python
def test_predicate_review_stage(tmp_path):
    runner = E2EWorkflowRunner(tmp_path / "project")

    # Setup prerequisites
    runner.setup_project(product_code="DQY")

    # Test specific stage
    review_data = {...}
    result = runner.run_predicate_review(review_data)

    assert result.passed
    assert result.metrics["accepted_predicates"] > 0
```

### Pattern 3: Regulatory Validation Test

Test regulatory compliance validation.

```python
def test_cfr_part_11_compliance():
    validator = CFRValidator()

    submission_data = {
        "signatures": [...],
        "audit_trail": [...],
        "version": "1.0"
    }

    results = validator.validate_part_11_compliance(submission_data)

    assert validator.get_summary()["overall_status"] == "PASS"
    assert not validator.has_critical_errors()
```

### Pattern 4: Data Factory Test

Test data generation and validation.

```python
def test_device_profile_generation():
    profile = E2EDataManager.create_device_profile(
        product_code="DQY",
        device_class="II"
    )

    E2EAssertions.assert_device_profile_valid(profile)
    assert profile["product_code"] == "DQY"
    assert profile["device_class"] == "II"
```

### Pattern 5: Error Recovery Test

Test error handling and recovery mechanisms.

```python
def test_workflow_recovery_from_failure(tmp_path):
    runner = E2EWorkflowRunner(tmp_path / "project")

    # Intentionally cause failure
    result = runner.setup_project()  # Missing product_code
    assert not result.passed

    # Verify error captured
    assert len(result.errors) > 0

    # Verify can recover
    result = runner.setup_project(product_code="DQY")
    assert result.passed
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: E2E Test Suite

on:
  push:
    branches: [master, develop]
  pull_request:
    branches: [master]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist

      - name: Run fast E2E tests
        run: |
          pytest tests/e2e/ -m e2e_fast -v -n auto

      - name: Run full E2E tests
        run: |
          pytest tests/e2e/ -v --cov=plugins/fda-tools --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running fast E2E tests..."
pytest tests/e2e/ -m e2e_fast -q

if [ $? -ne 0 ]; then
    echo "E2E tests failed. Commit aborted."
    exit 1
fi

echo "E2E tests passed."
```

---

## Performance Guidelines

### Target Metrics

- **Fast tests** (`@pytest.mark.e2e_fast`): <5 seconds each
- **Integration tests**: <30 seconds each
- **Full workflow tests**: <60 seconds each
- **Complete suite**: <5 minutes total

### Optimization Tips

1. **Use mock mode**: Set `mock_mode=True` to avoid real API calls
2. **Parallel execution**: Use `pytest-xdist` for parallel test execution
3. **Minimize I/O**: Use in-memory data structures when possible
4. **Cleanup efficiently**: Use context managers and fixtures for cleanup
5. **Cache expensive operations**: Cache test data generation

### Performance Example

```python
@pytest.mark.e2e_fast
def test_fast_workflow(tmp_path):
    """Fast E2E test using minimal data and mock mode."""
    runner = E2EWorkflowRunner(tmp_path / "project", mock_mode=True)

    # Use minimal data
    runner.setup_project(product_code="DQY")
    runner.run_data_collection("DQY", mock_data={"clearances": []})

    # Test only critical paths
    result = runner.run_predicate_review()
    assert result.passed

    # Skip cleanup (pytest tmp_path handles it)
```

---

## Troubleshooting

### Common Issues

#### Issue: "Module not found" errors

**Solution:**
```bash
# Ensure PYTHONPATH includes plugin root
export PYTHONPATH=/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools:$PYTHONPATH

# Or run from plugin root
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
pytest tests/e2e/ -v
```

#### Issue: Tests timeout

**Solution:**
```bash
# Increase timeout
pytest tests/e2e/ -v --timeout=60

# Skip slow tests
pytest tests/e2e/ -v -m "not slow"
```

#### Issue: Import errors for validators

**Solution:**
```python
# Use proper imports
from tests.utils.e2e_helpers import E2EWorkflowRunner
from tests.utils.regulatory_validators import CFRValidator

# NOT:
from tests.e2e_helpers import E2EWorkflowRunner  # Wrong path
```

#### Issue: Fixture data missing

**Solution:**
```bash
# Verify fixture files exist
ls tests/fixtures/

# Check fixture loading in conftest.py
pytest --fixtures tests/e2e/
```

#### Issue: Workflow stages fail silently

**Solution:**
```python
# Always check results
result = runner.run_drafting()
if not result.passed:
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")

# Or use assertions
E2EAssertions.assert_workflow_completed_successfully(runner.get_results())
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use verbose pytest output
pytest tests/e2e/ -vv -s

# Examine workflow results
runner = E2EWorkflowRunner(...)
# ... run workflow ...
for result in runner.get_results():
    print(f"\nStage: {result.stage}")
    print(f"Duration: {result.duration}s")
    print(f"Success: {result.success}")
    print(f"Errors: {result.errors}")
    print(f"Metrics: {result.metrics}")
```

---

## Best Practices

1. **Test complete workflows**: Validate end-to-end processes, not just units
2. **Use domain assertions**: Leverage E2EAssertions for business logic checks
3. **Mock external dependencies**: Use mock_mode to avoid network calls
4. **Generate realistic data**: Use E2EDataManager for test data
5. **Validate regulatory compliance**: Include CFRValidator, EStarValidator checks
6. **Document test purpose**: Clear docstrings explaining what is tested
7. **Keep tests fast**: Mark slow tests appropriately
8. **Clean up resources**: Use context managers and pytest fixtures
9. **Test error conditions**: Include negative test cases
10. **Run tests frequently**: Integrate with CI/CD pipeline

---

## Support and Resources

### Documentation

- `tests/e2e/README.md` - E2E test suite overview
- `tests/utils/e2e_helpers.py` - Helper utilities source code
- `tests/utils/regulatory_validators.py` - Validator source code
- `pytest.ini` - Pytest configuration and markers

### Examples

- `tests/test_e2e_utils.py` - Infrastructure tests and usage examples
- `tests/e2e/test_comprehensive_workflows.py` - Complete workflow tests

### Getting Help

1. Review test output with `-v` flag for verbose logging
2. Check test docstrings for expected behavior
3. Examine source code in `tests/utils/` for implementation details
4. Run with `-s` flag to see print statements and debug output

---

## Version History

**1.0.0** (2026-02-20)
- Initial E2E test infrastructure release
- E2EWorkflowRunner for workflow orchestration
- E2EDataManager for test data generation
- E2EAssertions for domain-specific validation
- CFRValidator, EStarValidator, PredicateValidator, SEValidator
- Comprehensive test coverage
- CI/CD ready
- Production-grade documentation

---

## License

Part of FDA Tools plugin. See LICENSE file for details.
