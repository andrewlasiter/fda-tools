#!/usr/bin/env python3
"""Verify that fda_tools is correctly installed and all key imports work.

Run after `pip install -e .` to confirm the editable install succeeded:

    python3 plugins/fda_tools/scripts/verify_install.py

Exit code 0 = all checks passed.
Exit code 1 = one or more checks failed.
"""

import sys
import importlib
import importlib.metadata

CHECKS = [
    ("fda_tools.lib.config", "Config"),
    ("fda_tools.lib.cross_process_rate_limiter", "CrossProcessRateLimiter"),
    ("fda_tools.lib.rate_limiter", "RateLimiter"),       # deprecation shim
    ("fda_tools.scripts.fda_api_client", "FDAClient"),
    ("fda_tools.scripts.data_refresh_orchestrator", "DataRefreshOrchestrator"),
    ("fda_tools.scripts.error_handling", "with_retry"),
]


def main() -> int:
    failed = False

    for module_path, attr in CHECKS:
        try:
            mod = importlib.import_module(module_path)
            assert hasattr(mod, attr), f"{module_path} missing {attr}"
            print(f"✓ {module_path}")
        except Exception as exc:
            print(f"✗ {module_path}: {exc}", file=sys.stderr)
            failed = True

    # Check CLI entry point resolves
    try:
        from fda_tools.scripts.check_version import main as cv_main  # noqa: F401
        print("✓ CLI entry point: fda-check-version")
    except Exception as exc:
        print(f"✗ CLI entry point fda-check-version: {exc}", file=sys.stderr)
        failed = True

    # Print installed version
    try:
        version = importlib.metadata.version("fda-tools")
        print(f"fda_tools {version} — install OK" if not failed else f"fda_tools {version} — install FAILED")
    except importlib.metadata.PackageNotFoundError:
        print("fda_tools — not installed as a package (run: pip install -e .)", file=sys.stderr)
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
