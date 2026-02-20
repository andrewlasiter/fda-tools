#!/usr/bin/env python3
"""setup.py for fda-tools package.

Backward compatibility shim for older build tools that don't support PEP 517/518.
Modern installations should use pyproject.toml directly via:
    pip install -e .
    pip install .

This file is required for:
- pip < 19.0
- conda builds
- Some legacy CI/CD systems
"""

from setuptools import setup

# All configuration is in pyproject.toml per PEP 517/518
# This setup.py exists only for backward compatibility
setup()
