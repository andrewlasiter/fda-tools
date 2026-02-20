# E2E Testing Quick Start Guide

**Fast reference for running FDA Tools E2E tests**

## Quick Commands

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Fast tests only (<5s each)
pytest -m e2e_fast -v

# Run by category
pytest -m e2e_510k -v          # 510(k) workflows
pytest -m e2e_security -v      # Security/auth
pytest -m e2e_edge_cases -v    # Edge cases

# Using execution script
./scripts/run_e2e_tests.sh --fast
./scripts/run_e2e_tests.sh --coverage
./scripts/run_e2e_tests.sh --510k --verbose
```

## Test Organization

| Marker | Tests | Purpose |
|--------|-------|---------|
| `e2e_fast` | 17 | Fast tests (<5s) |
| `e2e_510k` | 3 | 510(k) workflows |
| `e2e_security` | 3 | Auth/config |
| `e2e_api` | 4 | API integration |
| `e2e_pipeline` | 2 | Data pipeline |
| `e2e_edge_cases` | 4 | Edge cases |

## Files Created

```
tests/e2e/
├── __init__.py                         # Package init
├── README.md                           # Full documentation
├── fixtures.py                         # Test fixtures (379 lines)
├── mocks.py                           # Mock objects (486 lines)
├── test_data.py                       # Data generators (482 lines)
└── test_comprehensive_workflows.py    # Test suite (637 lines)

scripts/
└── run_e2e_tests.sh                   # Execution script (181 lines)

docs/
├── FDA-186_E2E_TEST_INFRASTRUCTURE.md # Implementation doc (554 lines)
└── E2E_QUICK_START.md                 # This file
```

## Test Results

```
17 tests, 100% pass rate, 0.31s execution time
```

## Common Patterns

### Using Fixtures
```python
def test_example(e2e_project, sample_device_data):
    device_path = e2e_project / "device_profile.json"
    with open(device_path, 'w') as f:
        json.dump(sample_device_data, f, indent=2)
```

### Using Mocks
```python
from tests.e2e.mocks import create_mock_fda_client

client = create_mock_fda_client("DQY", result_count=10)
response = client.query_devices(product_code="DQY")
```

### Generating Data
```python
from tests.e2e.test_data import generate_510k_workflow_data

data = generate_510k_workflow_data("traditional")
# Returns: device_profile, predicates, clearances, recalls
```

## Troubleshooting

**Import errors:**
```bash
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools
pytest tests/e2e/ -v
```

**See full output:**
```bash
pytest tests/e2e/ -v -s
```

**Debug single test:**
```bash
pytest tests/e2e/test_comprehensive_workflows.py::TestClass::test_method -v -s
```

## Next Steps

1. Read full docs: `tests/e2e/README.md`
2. Review implementation: `docs/FDA-186_E2E_TEST_INFRASTRUCTURE.md`
3. Add new tests following existing patterns
4. Run tests before commits: `./scripts/run_e2e_tests.sh --fast`

