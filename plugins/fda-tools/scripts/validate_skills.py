#!/usr/bin/env python3
"""
FDA Skills Validation Script (FDA-54).

Standalone script that validates all skill definitions in the skills/ directory.
Can be run from CI or manually to verify skill integrity.

Usage:
    python3 scripts/validate_skills.py
    python3 scripts/validate_skills.py --verbose
    python3 scripts/validate_skills.py --json

Exit codes:
    0 - All skills valid
    1 - One or more validation failures
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def parse_yaml_frontmatter(content: str) -> Tuple[Optional[Dict[str, str]], str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None, content
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return None, content

    frontmatter_text = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    result: Dict[str, str] = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()

    return result, body


def validate_skill(skill_dir: Path, verbose: bool = False) -> Dict[str, Any]:
    """Validate a single skill directory.

    Returns:
        Dict with 'valid' (bool), 'errors' (list), 'warnings' (list), 'name' (str).
    """
    errors: List[str] = []
    warnings: List[str] = []
    skill_name = skill_dir.name

    # Check SKILL.md exists
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return {
            "valid": False,
            "name": skill_name,
            "errors": ["SKILL.md not found"],
            "warnings": [],
        }

    # Read and parse
    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "valid": False,
            "name": skill_name,
            "errors": [f"Cannot read SKILL.md: {e}"],
            "warnings": [],
        }

    # Frontmatter validation
    fm, body = parse_yaml_frontmatter(content)

    if fm is None:
        errors.append("No YAML frontmatter found (must start with '---')")
    else:
        if "name" not in fm:
            errors.append("Missing required 'name' field in frontmatter")
        elif fm["name"] != skill_name:
            errors.append(
                f"Frontmatter name '{fm['name']}' does not match "
                f"directory name '{skill_name}'"
            )

        if "description" not in fm:
            errors.append("Missing required 'description' field in frontmatter")
        elif len(fm.get("description", "")) < 10:
            warnings.append("Description is very short (< 10 chars)")

    # Content structure validation
    if not re.search(r"^##\s+Overview", body, re.MULTILINE):
        warnings.append("Missing '## Overview' section")

    if not re.search(r"^##\s+Guardrails", body, re.MULTILINE):
        warnings.append("Missing '## Guardrails' section")

    has_workflow = bool(re.search(r"^##\s+Workflow", body, re.MULTILINE))
    has_quickstart = bool(re.search(r"^##\s+Quick\s*Start", body, re.MULTILINE))
    has_when = bool(re.search(r"^##\s+When\s+To\s+Use", body, re.MULTILINE))
    if not (has_workflow or has_quickstart or has_when):
        warnings.append("Missing Workflow, Quick Start, or When To Use section")

    if len(body) < 200:
        warnings.append(f"Body content is short ({len(body)} chars)")

    return {
        "valid": len(errors) == 0,
        "name": skill_name,
        "frontmatter_name": fm.get("name", "") if fm else "",
        "description_length": len(fm.get("description", "")) if fm else 0,
        "body_length": len(body),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate FDA skill definitions in skills/ directory"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed output")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--skills-dir", type=str, default=None,
                        help="Override skills directory path")
    args = parser.parse_args()

    # Resolve skills directory
    if args.skills_dir:
        skills_dir = Path(args.skills_dir).resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        skills_dir = script_dir.parent / "skills"

    if not skills_dir.exists():
        print(f"ERROR: Skills directory not found: {skills_dir}", file=sys.stderr)
        return 1

    # Discover skills
    skill_dirs = sorted([
        d for d in skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    ])

    if not skill_dirs:
        print(f"ERROR: No skills found in {skills_dir}", file=sys.stderr)
        return 1

    # Validate each skill
    results: List[Dict[str, Any]] = []
    total_errors = 0
    total_warnings = 0

    for skill_dir in skill_dirs:
        result = validate_skill(skill_dir, verbose=args.verbose)
        results.append(result)
        total_errors += len(result["errors"])
        total_warnings += len(result["warnings"])

    # Output
    if args.json:
        output = {
            "total_skills": len(results),
            "valid_skills": sum(1 for r in results if r["valid"]),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "results": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"FDA Skills Validation")
        print(f"{'=' * 60}")
        print(f"Skills directory: {skills_dir}")
        print(f"Skills found: {len(results)}")
        print()

        for r in results:
            status = "PASS" if r["valid"] else "FAIL"
            marker = "[+]" if r["valid"] else "[X]"
            print(f"  {marker} {r['name']}: {status}")

            if args.verbose or not r["valid"]:
                for err in r["errors"]:
                    print(f"      ERROR: {err}")
            if args.verbose:
                for warn in r["warnings"]:
                    print(f"      WARN:  {warn}")

        print()
        valid_count = sum(1 for r in results if r["valid"])
        print(f"Result: {valid_count}/{len(results)} skills valid, "
              f"{total_errors} error(s), {total_warnings} warning(s)")

        if total_errors > 0:
            print("\nFAILED: Fix errors above before merging.")
        else:
            print("\nPASSED: All skills validated successfully.")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
