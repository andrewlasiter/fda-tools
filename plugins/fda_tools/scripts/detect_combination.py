#!/usr/bin/env python3
"""
Combination Product Detection CLI (FDA-125)
============================================

Reads a project's device_profile.json, runs CombinationProductDetector,
and prints the result as JSON.  Called by the draft.md workflow to
determine whether a device is a combination product before generating
sections.

Usage:
    python3 -m fda_tools.scripts.detect_combination --project-dir PATH
    python3 -m fda_tools.scripts.detect_combination --device-description TEXT

Output (stdout):
    JSON object with keys:
      - is_combination (bool)
      - combination_type (str | null)
      - confidence (str)
      - detected_components (list[str])
      - rho_assignment (str)
      - rho_rationale (str)
      - consultation_required (str | null)
      - regulatory_pathway (str)
      - recommendations (list[str])
      - class_u (bool)           — True if Class U device
      - class_u_rationale (str)  — explanation for Class U status

Exit codes:
    0 — detection ran successfully
    1 — project directory / device profile not found or unreadable
    2 — bad arguments
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fda_tools.lib.combination_detector import CombinationProductDetector

# ---------------------------------------------------------------------------
# Class U detection helpers
# ---------------------------------------------------------------------------

# Regulation numbers that indicate a Class U (unclassified) device when a
# full classification number is absent or the code is explicitly Class U.
_CLASS_U_PATTERNS = (
    re.compile(r"\bclass\s+u\b", re.IGNORECASE),
    re.compile(r"\bunclassified\b", re.IGNORECASE),
    re.compile(r"\bclass u\b", re.IGNORECASE),
)


def _detect_class_u(device_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``{"class_u": bool, "class_u_rationale": str}`` from profile fields."""
    # 1. Explicit device_class field
    device_class = str(device_profile.get("device_class", "")).strip().upper()
    if device_class == "U":
        return {
            "class_u": True,
            "class_u_rationale": "device_class field is 'U' (unclassified device).",
        }

    # 2. Scan device_class / regulation_number free text for Class U keywords
    fields_to_scan = [
        device_profile.get("device_class", ""),
        device_profile.get("regulation_number", ""),
        device_profile.get("device_description", ""),
    ]
    combined = " ".join(str(f) for f in fields_to_scan if f)
    for pattern in _CLASS_U_PATTERNS:
        if pattern.search(combined):
            return {
                "class_u": True,
                "class_u_rationale": (
                    f"Matched pattern '{pattern.pattern}' in device data. "
                    "Class U (unclassified) devices require special regulatory pathway handling."
                ),
            }

    return {"class_u": False, "class_u_rationale": ""}


# ---------------------------------------------------------------------------
# Detection entry points
# ---------------------------------------------------------------------------


def detect_from_profile(device_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Run combination product detection on a *device_profile* dict.

    Args:
        device_profile: Parsed ``device_profile.json`` content.

    Returns:
        Detection result dict (combination fields + class_u fields).
    """
    device_data = {
        "device_description": device_profile.get("device_description", ""),
        "trade_name": device_profile.get("trade_name", ""),
        "intended_use": device_profile.get("intended_use", ""),
    }

    detector = CombinationProductDetector(device_data)
    result = detector.detect()

    # Merge Class U detection
    class_u_info = _detect_class_u(device_profile)
    result.update(class_u_info)

    return result


def detect_from_text(
    device_description: str,
    trade_name: str = "",
    intended_use: str = "",
    device_class: str = "",
) -> Dict[str, Any]:
    """Run combination product detection from raw text fields.

    Args:
        device_description: Free-text device description.
        trade_name: Optional device trade name.
        intended_use: Optional intended use statement.
        device_class: Optional device class letter (e.g. ``"II"``, ``"U"``).

    Returns:
        Detection result dict (combination fields + class_u fields).
    """
    device_data = {
        "device_description": device_description,
        "trade_name": trade_name,
        "intended_use": intended_use,
    }

    detector = CombinationProductDetector(device_data)
    result = detector.detect()

    # Class U from the explicitly-provided device_class
    mock_profile = {
        "device_class": device_class,
        "device_description": device_description,
    }
    class_u_info = _detect_class_u(mock_profile)
    result.update(class_u_info)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_project(project_dir: str) -> Optional[Dict[str, Any]]:
    """Load device_profile.json from *project_dir*."""
    profile_path = Path(project_dir) / "device_profile.json"
    if not profile_path.exists():
        return None
    try:
        return json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="detect_combination",
        description="Detect whether a device is a combination product (FDA-125).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--project-dir",
        metavar="PATH",
        help="Path to project directory containing device_profile.json.",
    )
    group.add_argument(
        "--device-description",
        metavar="TEXT",
        help="Device description text (use instead of --project-dir for quick checks).",
    )
    parser.add_argument(
        "--trade-name",
        default="",
        help="Device trade name (used with --device-description).",
    )
    parser.add_argument(
        "--intended-use",
        default="",
        help="Intended use statement (used with --device-description).",
    )
    parser.add_argument(
        "--device-class",
        default="",
        help="Device class letter, e.g. 'II' or 'U' (used with --device-description).",
    )

    args = parser.parse_args(argv)

    if args.project_dir:
        profile = _load_project(args.project_dir)
        if profile is None:
            print(
                json.dumps({"error": f"device_profile.json not found or unreadable in {args.project_dir}"}),
                file=sys.stderr,
            )
            return 1
        result = detect_from_profile(profile)
    else:
        result = detect_from_text(
            device_description=args.device_description,
            trade_name=args.trade_name,
            intended_use=args.intended_use,
            device_class=args.device_class,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
