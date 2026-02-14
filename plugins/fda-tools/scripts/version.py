#!/usr/bin/env python3
"""Central plugin version source of truth."""

import json
from pathlib import Path


def get_plugin_version(default="0.0.0"):
    """Read plugin version from .claude-plugin/plugin.json."""
    plugin_json = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        with plugin_json.open("r", encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except Exception:
        pass
    return default


PLUGIN_VERSION = get_plugin_version()
