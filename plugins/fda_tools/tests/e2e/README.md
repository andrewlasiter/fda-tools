# End-to-End Test Suite

Comprehensive E2E testing infrastructure for FDA Tools plugin validating complete workflows from data collection through final submission assembly.

**Version:** 1.0.0  
**Date:** 2026-02-20  
**Issue:** FDA-186 (QA-001)

## Overview

This E2E test suite validates:
- Complete 510(k) submission workflows (Traditional, Special, Abbreviated)
- PMA submission workflows
- De Novo submission workflows
- Multi-agent orchestration
- API integration and error handling
- Configuration and authentication
- Data pipeline integrity
- Report generation workflows

## Test Coverage

### Total Test Scenarios: 16+

1. **Complete 510(k) Workflows** (3 scenarios)
   - Traditional 510(k) complete workflow
   - Special 510(k) workflow with software (SaMD)
   - Abbreviated 510(k) workflow with consensus standards

2. **Configuration and Authentication** (3 scenarios)
   - Configuration loading and validation
   - Custom configuration overrides
   - Nested value retrieval with dot notation

3. **API Integration and Error Handling** (4 scenarios)
   - API rate limiting enforcement
   - Retry on transient errors
   - Graceful degradation in error mode
   - API response validation

4. **Data Pipeline Integrity** (2 scenarios)
   - Data flow from device profile to review stage
   - Pipeline integrity validation

5. **Edge Cases and Special Scenarios** (4 scenarios)
   - Sparse data handling
   - SaMD device workflow
   - Combination product workflow
   - Class U device workflow

## Directory Structure

```
tests/e2e/
├── __init__.py              # Package initialization
├── README.md                # This file
├── fixtures.py              # Shared test fixtures
├── mocks.py                 # Mock objects for external dependencies
├── test_data.py             # Test data generators
└── test_comprehensive_workflows.py  # Main E2E test suite
```

## Test Execution

### Run All E2E Tests

```bash
# From plugin root directory
pytest tests/e2e/ -v

# With markers
pytest -m e2e -v

# Fast tests only (<5s each)
pytest -m e2e_fast -v
```

### Run Specific Test Categories

```bash
# 510(k) workflow tests only
pytest -m e2e_510k -v

# Security and authentication tests
pytest -m e2e_security -v

# Integration tests (may require real APIs)
pytest -m e2e_integration -v

# Edge case tests
pytest -m e2e_edge_cases -v

# Data collection tests
pytest -m e2e_data_collection -v
```

### Run Specific Test Classes

```bash
# Complete 510(k) workflows
pytest tests/e2e/test_comprehensive_workflows.py::TestComplete510kWorkflows -v

# Configuration and auth
pytest tests/e2e/test_comprehensive_workflows.py::TestConfigurationAndAuth -v

# API integration
pytest tests/e2e/test_comprehensive_workflows.py::TestAPIIntegrationAndErrors -v

# Data pipeline
pytest tests/e2e/test_comprehensive_workflows.py::TestDataPipelineIntegrity -v

# Edge cases
pytest tests/e2e/test_comprehensive_workflows.py::TestEdgeCasesAndSpecialScenarios -v
```

### Run Individual Tests

```bash
# Specific test method
pytest tests/e2e/test_comprehensive_workflows.py::TestComplete510kWorkflows::test_traditional_510k_complete_workflow -v

# With output capture disabled (see print statements)
pytest tests/e2e/test_comprehensive_workflows.py::TestComplete510kWorkflows::test_traditional_510k_complete_workflow -v -s
```

## Pytest Markers

The following pytest markers are used for test organization:

- `@pytest.mark.e2e` - All E2E tests
- `@pytest.mark.e2e_510k` - Traditional 510(k) submission tests (P0)
- `@pytest.mark.e2e_pma` - PMA submission tests (P0)
- `@pytest.mark.e2e_special` - Special 510(k) submission tests (P1)
- `@pytest.mark.e2e_denovo` - De Novo submission tests (P1)
- `@pytest.mark.e2e_abbreviated` - Abbreviated 510(k) submission tests (P2)
- `@pytest.mark.e2e_security` - Security and authentication tests
- `@pytest.mark.e2e_data_collection` - Data collection stage tests
- `@pytest.mark.e2e_integration` - Integration tests requiring real API calls
- `@pytest.mark.e2e_edge_cases` - Edge case tests (SaMD, combination, sparse, Class U)
- `@pytest.mark.e2e_fast` - Fast E2E tests (<5s each)
- `@pytest.mark.slow` - Tests that may take >30 seconds

## Test Fixtures

### Project Environment Fixtures

- `e2e_project` - Empty temporary project directory
- `e2e_project_with_device_profile` - Project with device_profile.json
- `e2e_project_complete` - Fully populated project with all files

### Sample Data Fixtures

- `sample_device_data` - Sample device profile
- `sample_predicate_data` - Sample predicate device data
- `sample_review_data` - Sample review data
- `sample_standards_data` - Sample standards data
- `test_k_numbers` - List of test K-numbers
- `mock_api_response` - Mock API response generator

## Mock Objects

### MockFDAAPIClient

Mock FDA openFDA API client for testing without network calls.

```python
from tests.e2e.mocks import MockFDAAPIClient

client = MockFDAAPIClient(
    response_data={"DQY": {...}},
    error_mode=False,
    rate_limit_mode=False,
    delay_seconds=0.0
)

response = client.query_devices(product_code="DQY")
```

### MockConfigManager

Mock configuration manager for testing without file I/O.

```python
from tests.e2e.mocks import MockConfigManager

config_manager = MockConfigManager({
    "api": {"rate_limit": 120}
})

config = config_manager.load_config()
rate_limit = config_manager.get("api.rate_limit")
```

### MockRateLimiter

Mock rate limiter for testing rate limiting logic.

```python
from tests.e2e.mocks import MockRateLimiter

limiter = MockRateLimiter(rate_limit=60, enforce=True)
limiter.acquire()  # Succeeds
# After 60 requests in 1 minute...
limiter.acquire()  # Raises exception
```

## Test Data Generation

### Device Profile Generation

```python
from tests.e2e.test_data import generate_device_profile

# Standard Class II device
profile = generate_device_profile(
    product_code="DQY",
    device_class="II",
    device_type="cardiovascular"
)

# SaMD device with software
samd_profile = generate_device_profile(
    product_code="QKQ",
    include_software=True
)

# Combination product
combo_profile = generate_device_profile(
    product_code="FRO",
    combination_product=True
)
```

### Workflow Data Generation

```python
from tests.e2e.test_data import generate_510k_workflow_data

# Traditional 510(k) workflow data
data = generate_510k_workflow_data("traditional")
# Returns: device_profile, predicates, fda_clearances, fda_recalls

# Special 510(k) with software
special_data = generate_510k_workflow_data("special")
```

### Edge Case Data Generation

```python
from tests.e2e.test_data import generate_edge_case_data

# Sparse data scenario
sparse = generate_edge_case_data("sparse_data")

# SaMD scenario
samd = generate_edge_case_data("samd")

# Combination product scenario
combo = generate_edge_case_data("combination")

# Class U scenario
class_u = generate_edge_case_data("class_u")
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v --cov=plugins/fda-tools --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### Local Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running E2E fast tests..."
pytest tests/e2e/ -m e2e_fast -v

if [ $? -ne 0 ]; then
    echo "E2E tests failed. Commit aborted."
    exit 1
fi
```

## Writing New E2E Tests

### Template for New Test

```python
import pytest
from tests.e2e.fixtures import E2ETestProject
from tests.e2e.mocks import create_mock_fda_client
from tests.e2e.test_data import generate_device_profile

@pytest.mark.e2e
@pytest.mark.e2e_fast
class TestNewFeature:
    """Test new feature end-to-end."""
    
    def test_new_feature_workflow(self):
        """Test new feature complete workflow.
        
        Workflow stages:
            1. Setup
            2. Execution
            3. Validation
        """
        with E2ETestProject("test_new_feature") as project_dir:
            # Setup phase
            device_profile = generate_device_profile()
            # ... write files
            
            # Execution phase
            # ... run operations
            
            # Validation phase
            assert (project_dir / "output.json").exists()
```

### Best Practices

1. **Use fixtures** - Leverage existing fixtures for common setup
2. **Mock external APIs** - Use mock objects to avoid network calls
3. **Test complete workflows** - Validate entire process, not just units
4. **Assert meaningful outcomes** - Check business logic, not implementation details
5. **Keep tests fast** - Use `@pytest.mark.e2e_fast` for <5s tests
6. **Document test purpose** - Clear docstrings explaining what is tested
7. **Clean up resources** - Use context managers for temp files/dirs
8. **Test edge cases** - Include error conditions and boundary cases

## Performance Targets

- **Fast tests** (`e2e_fast`): <5 seconds each
- **Integration tests**: <30 seconds each
- **Full suite execution**: <5 minutes
- **Parallel execution**: Supported via pytest-xdist

## Troubleshooting

### Tests Fail with "Module not found"

```bash
# Ensure PYTHONPATH includes plugin root
export PYTHONPATH=/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools:$PYTHONPATH

# Or run from plugin root directory
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
pytest tests/e2e/ -v
```

### Tests Timeout

```bash
# Increase timeout for slow tests
pytest tests/e2e/ -v --timeout=60

# Skip slow tests
pytest tests/e2e/ -v -m "not slow"
```

### Mock Data Issues

```bash
# Verify mock data files exist
ls tests/fixtures/

# Regenerate test data if needed
python -c "from tests.e2e.test_data import generate_510k_workflow_data; print(generate_510k_workflow_data('traditional'))"
```

## Support

For issues or questions:
- Review test output with `-v` flag for verbose logging
- Check test docstrings for expected behavior
- Examine fixture code in `fixtures.py` for setup details
- Review mock implementations in `mocks.py` for API behavior

## Version History

- **1.0.0** (2026-02-20) - Initial E2E test infrastructure
  - 15+ test scenarios implemented
  - Complete mock infrastructure
  - Test data generators
  - CI/CD ready
