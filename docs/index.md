# FDA Tools

AI-powered FDA regulatory assistant with 74 commands for 510(k) predicate search,
substantial equivalence analysis, submission drafting, and regulatory intelligence.

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Quick Start](docs/QUICK_START.md) | Get started in 5 minutes |
| [Installation](docs/INSTALLATION.md) | Full setup instructions |
| [API Reference](api/index.md) | Auto-generated Python module docs |
| [Examples](../examples/) | Worked 510(k) examples (catheter, SaMD, combo product) |
| [ADRs](docs/adr/README.md) | Architecture Decision Records |
| [Contributing](CONTRIBUTING.md) | Developer guide |

## Key Modules

### For command integrations

```python
from fda_tools.lib.config import Config
from fda_tools.lib.input_validators import validate_k_number, validate_product_code
from fda_tools.scripts.fda_api_client import FDAClient
```

### For analytics

```python
from fda_tools.lib.feature_analytics import FeatureAnalytics
from fda_tools.lib.fda_enrichment import enrich_device_record
from fda_tools.lib.predicate_ranker import PredicateRanker
```

### For security

```python
from fda_tools.lib.auth import AuthManager
from fda_tools.lib.rbac import require_role, Role
from fda_tools.lib.path_validator import OutputPathValidator
```

## Package Structure

```
fda_tools/
├── lib/        ← Stable importable library (stdlib-only, see ADR-005)
├── scripts/    ← CLI scripts and utilities
├── bridge/     ← FastAPI bridge server
└── tests/      ← Test suite
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development guide.
