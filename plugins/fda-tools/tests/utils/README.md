# E2E Test Utilities - Quick Reference

**Version:** 1.0.0
**Issue:** FDA-174 (QA-001)
**Status:** Production Ready

## Overview

Comprehensive E2E test infrastructure for FDA Tools plugin providing workflow orchestration, regulatory validation, and test data generation.

## Quick Start

```python
from tests.utils import (
    E2EWorkflowRunner, E2EDataManager, E2EAssertions,
    CFRValidator, PredicateValidator, SubstantialEquivalenceValidator
)

# Run complete workflow
runner = E2EWorkflowRunner("/tmp/test", workflow_type="traditional_510k")
runner.setup_project(product_code="DQY")
runner.run_data_collection("DQY", mock_data={...})
runner.run_predicate_review()
runner.run_drafting()
runner.run_assembly()

# Validate results
E2EAssertions.assert_workflow_completed_successfully(runner.get_results())
```

## Modules

### `e2e_helpers.py`

**E2EWorkflowRunner** - Orchestrate complete workflows
```python
runner = E2EWorkflowRunner(project_dir, workflow_type="traditional_510k")
runner.setup_project(product_code="DQY")
runner.run_data_collection("DQY")
runner.run_predicate_review()
runner.run_drafting()
runner.run_assembly()
summary = runner.get_summary()
```

**E2EDataManager** - Generate test data
```python
profile = E2EDataManager.create_device_profile("DQY", "II")
predicate = E2EDataManager.create_predicate_data("K213456", "DQY", "accepted", 92)
review = E2EDataManager.create_review_data("DQY", predicates)
```

**E2EAssertions** - Domain-specific assertions
```python
E2EAssertions.assert_project_structure_valid(project_dir)
E2EAssertions.assert_device_profile_valid(profile)
E2EAssertions.assert_review_data_valid(review)
E2EAssertions.assert_workflow_completed_successfully(results)
```

### `regulatory_validators.py`

**CFRValidator** - 21 CFR compliance
```python
validator = CFRValidator()
results = validator.validate_part_11_compliance(submission_data)
results = validator.validate_device_classification("DQY", "II", "21 CFR 870.1340")
```

**EStarValidator** - eSTAR XML validation
```python
validator = EStarValidator()
results = validator.validate_xml_structure(Path("estar.xml"))
results = validator.validate_field_requirements(Path("estar.xml"), "nIVD")
```

**PredicateValidator** - Predicate acceptability
```python
validator = PredicateValidator()
results = validator.validate_predicate_acceptability(subject, predicate)
results = validator.validate_predicate_chain(predicates)
```

**SubstantialEquivalenceValidator** - SE validation
```python
validator = SubstantialEquivalenceValidator()
results = validator.validate_se_comparison(comparison_data)
results = validator.validate_se_discussion(Path("se-discussion.md"))
```

## Test Execution

```bash
# Run infrastructure tests
pytest tests/test_e2e_utils.py -v

# Run with coverage
pytest tests/test_e2e_utils.py --cov=tests/utils --cov-report=term-missing

# Run fast E2E tests
pytest -m e2e_fast -v

# Run all E2E tests
pytest tests/e2e/ -v
```

## Workflow Stages

1. INITIALIZATION - Project setup
2. DATA_COLLECTION - FDA data fetch
3. PREDICATE_SEARCH - Search predicates
4. PREDICATE_REVIEW - Review and select
5. COMPARISON - SE comparison
6. DRAFTING - Draft sections
7. CONSISTENCY_CHECK - Validate consistency
8. ASSEMBLY - Package assembly
9. EXPORT - eSTAR export
10. VALIDATION - Final validation

## Validation Severities

- **INFO** - Informational (passed)
- **WARNING** - Should address
- **ERROR** - Must fix
- **CRITICAL** - Blocking issue

## Common Patterns

### Pattern 1: Complete Workflow
```python
runner = E2EWorkflowRunner(tmp_path / "project")
runner.setup_project(product_code="DQY")
runner.run_data_collection("DQY", mock_data=data)
runner.run_predicate_review(review_data)
runner.run_drafting()
runner.run_assembly()
E2EAssertions.assert_workflow_completed_successfully(runner.get_results())
```

### Pattern 2: Regulatory Validation
```python
cfr = CFRValidator()
results = cfr.validate_device_classification("DQY", "II", "21 CFR 870.1340")
assert cfr.get_summary()["overall_status"] == "PASS"
```

### Pattern 3: Test Data Generation
```python
profile = E2EDataManager.create_device_profile("DQY", "II", include_software=True)
E2EAssertions.assert_device_profile_valid(profile)
```

## Documentation

- **Comprehensive Guide**: `/docs/E2E_TESTING_GUIDE.md`
- **Implementation Summary**: `/FDA-174_IMPLEMENTATION_SUMMARY.md`
- **E2E Test Suite**: `/tests/e2e/README.md`

## Support

- Review source code in `tests/utils/`
- Check test examples in `tests/test_e2e_utils.py`
- See E2E test suite in `tests/e2e/`

## Statistics

- **39 tests** - 100% passing
- **650 lines** - e2e_helpers.py
- **800 lines** - regulatory_validators.py
- **<1 second** - Full test execution
- **4 validators** - Regulatory compliance
- **10 workflow stages** - Complete coverage
