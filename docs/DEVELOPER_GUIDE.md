# Developer Guide

This guide explains how to extend FDA Tools — adding slash commands, library modules,
CLI scripts, and tests. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first for setup instructions.

---

## How to Add a New Slash Command

Slash commands live in `plugins/fda_tools/commands/`. Each command is a markdown file
with YAML frontmatter that Claude reads when the user invokes `/fda-tools:<command>`.

### 1. Create the command file

```bash
touch plugins/fda_tools/commands/my-command.md
```

### 2. Write the frontmatter

```markdown
---
description: "One-line description shown in /fda-tools:help"
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, WebFetch
argument-hint: "[--project PROJECT] [--output FORMAT]"
---
```

**`allowed-tools`** controls which Claude tools the command can invoke. Use the minimal
set needed. Never list tools your command doesn't use.

**`argument-hint`** is shown as autocomplete hint text. Use `[]` for optional args and
`<>` for required ones.

### 3. Write the command body

The body is a natural-language instruction set for Claude:

```markdown
## My Command

Given `<description of what the user provides>`, perform the following steps:

**Step 1 — Load project data**
Read `~/.fda_tools/projects/{project}/device_profile.json`. If not found,
output an error: "Project not found: {project}" and stop.

**Step 2 — Do the thing**
...

**Output**
Write results to `{project}/output/my-report.md`.
```

### 4. Register in plugin.json (optional)

If you want the command listed in the plugin manifest, add it to
`plugins/fda_tools/.claude-plugin/plugin.json`:

```json
{
  "commands": ["my-command"]
}
```

### Command conventions

- Keep each step numbered and explicit — Claude executes them in order
- Reference project data files by full `~/.fda_tools/projects/` path
- Always validate inputs before operating on them
- Add a clear "Output" section specifying what files are written
- Short aliases go in a separate `<letter>.md` file (see `b.md` for an example)

---

## How to Add a New `lib/` Module

`lib/` modules form the core of FDA Tools. They are subject to strict constraints
(see [ADR-005](adr/ADR-005-stdlib-only-lib-modules.md)):

> **stdlib-only:** `lib/` modules may only import from Python's standard library
> and other `fda_tools.lib.*` modules. No third-party imports.

This ensures `lib/` is importable in any environment without pip dependencies.

### 1. Create the module

```bash
touch plugins/fda_tools/lib/my_module.py
```

### 2. Write the module

```python
"""My module — brief description.

Longer description of what this module does and why.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fda_tools.lib.config import Config
from fda_tools.lib.logger import get_logger

logger = get_logger(__name__)


class MyHelper:
    """One-line description.

    Args:
        data_dir: Path to the project data directory.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def do_something(self, value: str) -> dict[str, Any]:
        """Describe what this method does.

        Args:
            value: What value is.

        Returns:
            A dict with ...

        Raises:
            ValueError: If value is invalid.
        """
        if not value:
            raise ValueError("value must not be empty")
        # implementation
        return {"result": value}
```

### 3. Add an `__init__.py` export (optional)

For commonly-used classes, add a re-export in `plugins/fda_tools/lib/__init__.py`:

```python
from fda_tools.lib.my_module import MyHelper
```

### 4. Create a MkDocs stub page

```bash
cat > docs/api/lib/my_module.md << 'EOF'
# My Module

::: fda_tools.lib.my_module
EOF
```

Then add it to `mkdocs.yml` under the appropriate nav group.

### 5. Write tests

Create `plugins/fda_tools/tests/test_my_module.py`. See the
[Testing Guide](#testing-guide) below.

---

## How to Add a New CLI Script

CLI scripts live in `plugins/fda_tools/scripts/`. They are richer than `lib/` modules
and may use third-party imports.

### 1. Create the script

```bash
touch plugins/fda_tools/scripts/my_script.py
```

### 2. Follow the script template

```python
#!/usr/bin/env python3
"""my_script — brief description.

Usage:
    fda-my-command [OPTIONS]

Options:
    --project PROJECT   Project name under ~/.fda_tools/projects/
    --output FORMAT     Output format: json|csv|markdown (default: markdown)
    --help              Show this message
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fda_tools.lib.config import Config
from fda_tools.lib.logger import get_logger
from fda_tools.scripts.fda_api_client import FDAClient

logger = get_logger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Brief description of the script.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument(
        "--output", choices=["json", "csv", "markdown"], default="markdown"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for fda-my-command."""
    args = parse_args(argv)
    cfg = Config()

    project_dir = cfg.projects_dir / args.project
    if not project_dir.exists():
        logger.error("Project not found: %s", args.project)
        return 1

    # ... implementation ...
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 3. Register the entry point

Add the entry point to `pyproject.toml`:

```toml
[project.scripts]
fda-my-command = "fda_tools.scripts.my_script:main"
```

Then reinstall: `pip install -e .`

### 4. Add shell completion

Add flag completion to `tools/completions/fda-tools.bash` and `fda-tools.zsh`.
See the existing entries for `fda-batchfetch` as a reference.

---

## How to Add a New Agent

Agents live in `plugins/fda_tools/agents/` and are autonomous Claude prompts that run
multi-step workflows.

### 1. Create the agent file

```bash
touch plugins/fda_tools/agents/my-agent.md
```

### 2. Write the frontmatter

```markdown
---
description: >
  One-paragraph description of what the agent does. Include when to use it
  and what it produces.
allowed-tools: Bash, Read, Glob, Grep, Write, Task, WebFetch
argument-hint: "<project> [--focus AREA]"
---
```

### 3. Write the agent body

Agents should specify:

- **Trigger conditions** — when the agent runs, what inputs it expects
- **Phase breakdown** — numbered phases with clear goals
- **Error handling** — what to do if a phase fails
- **Output** — what files or reports are produced

---

## Testing Guide

### Running tests

```bash
# Full test suite
pytest plugins/fda_tools/tests/ -v --tb=short

# Single file
pytest plugins/fda_tools/tests/test_my_module.py -v

# Skip slow API tests
pytest plugins/fda_tools/tests/ -v -m "not slow"

# With coverage
pytest plugins/fda_tools/tests/ --cov=plugins/fda_tools/lib/my_module --cov-report=term-missing
```

### Writing tests for a `lib/` module

```python
# plugins/fda_tools/tests/test_my_module.py

import pytest
from fda_tools.lib.my_module import MyHelper


class TestMyHelper:
    def test_do_something_returns_dict(self):
        helper = MyHelper(data_dir=None)
        result = helper.do_something("hello")
        assert result == {"result": "hello"}

    def test_do_something_raises_on_empty(self):
        helper = MyHelper(data_dir=None)
        with pytest.raises(ValueError, match="must not be empty"):
            helper.do_something("")
```

### Writing tests for a CLI script

```python
# plugins/fda_tools/tests/test_my_script.py

import pytest
from unittest.mock import patch, MagicMock
from fda_tools.scripts.my_script import parse_args, main


class TestParseArgs:
    def test_required_project(self):
        args = parse_args(["--project", "my-project"])
        assert args.project == "my-project"

    def test_default_output(self):
        args = parse_args(["--project", "x"])
        assert args.output == "markdown"


class TestMain:
    def test_missing_project_returns_1(self, tmp_path):
        with patch("fda_tools.scripts.my_script.Config") as mock_cfg:
            mock_cfg.return_value.projects_dir = tmp_path
            result = main(["--project", "nonexistent"])
        assert result == 1
```

### Test markers

Use pytest markers to categorize tests:

```python
@pytest.mark.slow         # Makes real API calls — skip in CI with -m "not slow"
@pytest.mark.api          # Requires FDA_API_KEY environment variable
@pytest.mark.api_contract # Quarterly contract tests — validate fixtures against live API
```

---

## Code Style Guide

### Imports

```python
# Standard library first
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Optional

# Third-party (scripts only, not lib/)
import requests

# First-party
from fda_tools.lib.config import Config
from fda_tools.lib.logger import get_logger
```

### Docstrings

Use Google-style docstrings (enforced by `ruff D` rules):

```python
def calculate_sei(subject_specs: dict, predicate_specs: dict) -> float:
    """Calculate the Substantial Equivalence Index.

    Computes a weighted similarity score across technological characteristics,
    performance parameters, and intended use alignment.

    Args:
        subject_specs: Dict of subject device specifications.
        predicate_specs: Dict of predicate device specifications.

    Returns:
        SEI score in the range [0.0, 1.0].

    Raises:
        ValueError: If either spec dict is empty.

    Note:
        Per 21 CFR 807.87(f), substantial equivalence requires same intended
        use and same or different technological characteristics that do not
        raise new safety questions.
    """
```

### Regulatory comments

When implementing logic derived from FDA regulations, cite the relevant CFR section:

```python
# Per 21 CFR 807.87(e): predicate must have cleared under 510(k) or be
# a preamendments device. De Novo grants (21 CFR 860.257) also qualify.
if device.decision_code not in {"SESE", "SESK", "DENG"}:
    raise InvalidPredicateError(f"Decision code {device.decision_code!r} is not a valid predicate")
```

### Error handling

Use `user_errors.py` for user-facing errors; Python built-ins for programmer errors:

```python
from fda_tools.lib.user_errors import UserFacingError

# User-facing: shown with a friendly message
raise UserFacingError(
    "Project 'my-project' not found. Run `/fda-tools:init my-project` first."
)

# Programmer error: use built-in ValueError / RuntimeError
raise ValueError(f"Unexpected device_type: {device_type!r}")
```

---

## Adding an Architecture Decision Record

When your PR introduces a significant new pattern:

1. Copy `docs/adr/template.md` to `docs/adr/ADR-XXX-short-title.md`
2. Fill in the context, decision, and consequences
3. Link it from `docs/adr/README.md`
4. Reference it from your PR body

See [`docs/adr/README.md`](adr/README.md) for the full ADR process.

---

## Release Process

1. Update `version` in `pyproject.toml` and badge in `README.md`
2. Update `CHANGELOG.md` with the new version section
3. Create a PR titled `chore: Release vX.Y.Z`
4. After merge, create a GitHub release with the changelog entry as release notes
