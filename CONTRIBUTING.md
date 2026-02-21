# Contributing to FDA Tools

## Developer Setup

### Prerequisites

- Python 3.9 or later
- Git
- (Recommended) [uv](https://github.com/astral-sh/uv) or virtualenv

### 1. Clone the repository

```bash
git clone https://github.com/andrewlasiter/fda-tools.git
cd fda-tools
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows PowerShell
```

### 3. Install in editable mode

```bash
pip install -e ".[dev]"
```

This installs the `fda_tools` package in editable mode along with all development
dependencies (pytest, ruff, mypy, etc.). The package is discovered from
`plugins/fda_tools/` as configured in `[tool.setuptools.packages.find]`.

To install with optional dependencies as well:

```bash
pip install -e ".[dev,optional]"
```

### 4. Verify the installation

```bash
python3 plugins/fda_tools/scripts/verify_install.py
```

Expected output:

```
✓ fda_tools.lib.config
✓ fda_tools.lib.cross_process_rate_limiter
✓ fda_tools.lib.rate_limiter (deprecation shim)
✓ fda_tools.scripts.fda_api_client
✓ fda_tools.scripts.data_refresh_orchestrator
✓ fda_tools.scripts.error_handling
✓ CLI entry point: fda-check-version
fda_tools 5.x.x — install OK
```

### 5. Run the test suite

```bash
pytest plugins/fda_tools/tests/ -v --tb=short
```

---

## Package Structure

```
fda-tools/
├── pyproject.toml          # Single source of truth for build + config
├── setup.py                # Backward-compat shim (delegates to pyproject.toml)
├── CONTRIBUTING.md         # This file
├── plugins/
│   └── fda_tools/          # Installed as the `fda_tools` Python package
│       ├── __init__.py
│       ├── lib/            # Core library modules
│       │   ├── config.py
│       │   ├── cross_process_rate_limiter.py
│       │   └── ...
│       ├── scripts/        # CLI scripts and utilities
│       │   ├── fda_api_client.py
│       │   ├── batchfetch.py
│       │   └── ...
│       ├── bridge/         # FastAPI bridge server
│       │   └── server.py
│       └── tests/          # Test suite
│           └── ...
└── docs/                   # Additional documentation
```

### Import convention

All imports use the fully-qualified `fda_tools.*` prefix:

```python
from fda_tools.lib.config import Config
from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter
from fda_tools.scripts.fda_api_client import FDAClient
```

Direct `sys.path.insert()` is not used (removed as part of FDA-199).

---

## CLI Entry Points

After `pip install -e .`, the following commands are available on your `$PATH`:

| Command | Module |
|---------|--------|
| `fda-batchfetch` | `fda_tools.scripts.batchfetch:main` |
| `fda-gap-analysis` | `fda_tools.scripts.gap_analysis:main` |
| `fda-batch-analyze` | `fda_tools.scripts.batch_analyze:main` |
| `fda-batch-seed` | `fda_tools.scripts.batch_seed:main` |
| `fda-backup-project` | `fda_tools.scripts.backup_project:main` |
| `fda-setup-api-key` | `fda_tools.scripts.setup_api_key:main` |
| `fda-migrate-keyring` | `fda_tools.scripts.migrate_to_keyring:main` |
| `fda-auto-standards` | `fda_tools.scripts.auto_generate_device_standards:main` |
| `fda-check-version` | `fda_tools.scripts.check_version:main` |
| `fda-update-manager` | `fda_tools.scripts.update_manager:main` |

---

## Code Quality

### Linting and formatting

```bash
ruff check .            # Lint
ruff format .           # Auto-format
mypy plugins/fda_tools/lib/   # Type-check lib/ modules
```

### Pre-commit hooks

```bash
pre-commit install      # Install hooks (runs on every commit)
pre-commit run --all-files   # Run manually
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FDA_API_KEY` | — | openFDA API key (increases rate limit from 40→240 req/min) |
| `BRIDGE_ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated CORS origins for bridge server |
| `FDA_DATA_DIR` | `~/.fda_tools` | Directory for cached data and rate-limiter state files |

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'fda_tools'`

You need to install the package first:

```bash
pip install -e .
```

### `pip install -e .` fails on externally-managed environment (Debian/Ubuntu)

Create and activate a virtual environment first:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Tests fail with import errors

Ensure you installed with `pip install -e .` (not just `pip install`). The
editable install links `plugins/fda_tools` into `sys.path` so imports resolve
without `sys.path.insert()` hacks.

---

## Contributing Code

### Branch naming

Use the format `<type>/<ticket>-<short-description>`:

```
feat/fda-124-input-validators
fix/gh-77-license-scan
chore/update-deps
```

Common types: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`.

### Commit messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short summary>

[optional body]
[optional footer]
```

Examples:

```
feat(validation): Add email validator to lib/input_validators (FDA-124)
fix(ci): Pin Trivy action to avoid breaking changes
docs: Update CONTRIBUTING with branch naming conventions
```

### Pull request checklist

Before opening a PR, verify:

- [ ] All tests pass: `pytest plugins/fda_tools/tests/ -v`
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`
- [ ] New code is covered by tests
- [ ] No new `sys.path.insert()` calls (use `pip install -e .` instead)
- [ ] Imports use the `fda_tools.*` prefix, not relative paths
- [ ] Sensitive data is not hard-coded (keys, passwords, PII)
- [ ] Related Linear/GitHub issue is referenced in the PR body

### Testing requirements

- All new `lib/` modules require a corresponding `tests/test_<module>.py`
- Minimum coverage for new files: aim for 80 %+ line coverage
- Use `pytest-cov` to check: `pytest --cov=plugins/fda_tools/lib/<module> --cov-report=term-missing`

### Architecture Decision Records

Significant architectural decisions are documented in [`docs/adr/`](docs/adr/).
When your PR introduces a significant new pattern, library choice, or
cross-cutting design change, consider creating an ADR alongside the code.
See [`docs/adr/README.md`](docs/adr/README.md) for the process and template.

### Code review

PRs are reviewed for:

1. Correctness and security (no injection, no path traversal, no hardcoded secrets)
2. Test coverage
3. Import hygiene (`fda_tools.*` prefix, no `sys.path` manipulation)
4. Minimal diff — only changes directly related to the stated purpose
