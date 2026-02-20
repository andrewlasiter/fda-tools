"""
Functional test suite for FDA Tools skills directory (FDA-54).

Validates that all skill definitions in the skills/ directory have:
    1. Valid SKILL.md files with proper YAML frontmatter
    2. Required frontmatter fields (name, description)
    3. Consistent naming between directory and frontmatter
    4. Valid content structure (Overview, Workflow/Quick Start, Guardrails)
    5. Existing smoke test script is syntactically valid

This test file requires no network access and runs entirely offline.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_DIR.parent.resolve()  # plugins/fda-tools
SKILLS_DIR = PROJECT_ROOT / "skills"

# The 5 skills explicitly listed in the issue
EXPECTED_CORE_SKILLS = [
    "fda-predicate-assessment",
    "fda-510k-knowledge",
    "fda-safety-signal-triage",
    "fda-plugin-e2e-smoke",
    "fda-510k-submission-outline",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_yaml_frontmatter(content: str) -> Tuple[Optional[Dict], str]:
    """Parse YAML frontmatter from markdown content.

    Expects content starting with '---' and ending with '---'.

    Returns:
        Tuple of (frontmatter_dict, body) or (None, content) if no frontmatter.
    """
    if not content.startswith("---"):
        return None, content

    # Find closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return None, content

    frontmatter_text = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    # Simple YAML key: value parser (no nested structures needed)
    result = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()

    return result, body


def _discover_all_skills() -> List[str]:
    """Discover all skill directories under skills/.

    Returns:
        List of skill directory names.
    """
    if not SKILLS_DIR.exists():
        return []

    return sorted([
        d.name for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    ])


# ---------------------------------------------------------------------------
# Test: All expected core skills exist
# ---------------------------------------------------------------------------


class TestSkillsExistence:
    """Verify the expected 5 core skills are present."""

    def test_skills_directory_exists(self):
        """The skills/ directory must exist."""
        assert SKILLS_DIR.exists(), f"Skills directory not found at {SKILLS_DIR}"

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_core_skill_directory_exists(self, skill_name):
        """Each core skill must have its own directory."""
        skill_dir = SKILLS_DIR / skill_name
        assert skill_dir.exists(), (
            f"Expected skill directory not found: {skill_dir}"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_core_skill_has_skill_md(self, skill_name):
        """Each core skill must have a SKILL.md file."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        assert skill_md.exists(), (
            f"SKILL.md not found for skill '{skill_name}': {skill_md}"
        )


# ---------------------------------------------------------------------------
# Test: SKILL.md frontmatter validation
# ---------------------------------------------------------------------------


class TestSkillFrontmatter:
    """Validate YAML frontmatter in all SKILL.md files."""

    @pytest.fixture(autouse=True)
    def _load_skills(self):
        """Load all discovered skills."""
        self.all_skills = _discover_all_skills()
        assert len(self.all_skills) >= 5, (
            f"Expected at least 5 skills, found {len(self.all_skills)}"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_frontmatter_exists(self, skill_name):
        """SKILL.md must begin with YAML frontmatter (--- delimiters)."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        assert content.startswith("---"), (
            f"SKILL.md for '{skill_name}' does not start with YAML frontmatter '---'"
        )
        # Must have closing ---
        end_idx = content.find("---", 3)
        assert end_idx > 3, (
            f"SKILL.md for '{skill_name}' has no closing '---' for frontmatter"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_frontmatter_has_name(self, skill_name):
        """Frontmatter must include a 'name' field."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        fm, _ = _parse_yaml_frontmatter(content)
        assert fm is not None, f"Could not parse frontmatter for '{skill_name}'"
        assert "name" in fm, (
            f"Frontmatter for '{skill_name}' missing required 'name' field"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_frontmatter_has_description(self, skill_name):
        """Frontmatter must include a 'description' field."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        fm, _ = _parse_yaml_frontmatter(content)
        assert fm is not None, f"Could not parse frontmatter for '{skill_name}'"
        assert "description" in fm, (
            f"Frontmatter for '{skill_name}' missing required 'description' field"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_frontmatter_name_matches_directory(self, skill_name):
        """The 'name' field in frontmatter must match the directory name."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        fm, _ = _parse_yaml_frontmatter(content)
        assert fm is not None
        assert fm["name"] == skill_name, (
            f"Frontmatter name '{fm['name']}' does not match "
            f"directory name '{skill_name}'"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_description_not_empty(self, skill_name):
        """The description field must not be empty."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        fm, _ = _parse_yaml_frontmatter(content)
        assert fm is not None
        desc = fm.get("description", "")
        assert len(desc) > 10, (
            f"Description for '{skill_name}' is too short ({len(desc)} chars)"
        )


# ---------------------------------------------------------------------------
# Test: SKILL.md content structure validation
# ---------------------------------------------------------------------------


class TestSkillContentStructure:
    """Validate the content structure of SKILL.md files."""

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_has_overview_section(self, skill_name):
        """SKILL.md should contain an Overview section."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        assert re.search(r"^##\s+Overview", content, re.MULTILINE), (
            f"SKILL.md for '{skill_name}' missing '## Overview' section"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_has_guardrails_section(self, skill_name):
        """SKILL.md should contain a Guardrails section."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        assert re.search(r"^##\s+Guardrails", content, re.MULTILINE), (
            f"SKILL.md for '{skill_name}' missing '## Guardrails' section"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_has_workflow_or_quickstart(self, skill_name):
        """SKILL.md should contain a Workflow or Quick Start section."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        has_workflow = bool(re.search(r"^##\s+Workflow", content, re.MULTILINE))
        has_quickstart = bool(re.search(r"^##\s+Quick\s*Start", content, re.MULTILINE))
        has_when = bool(re.search(r"^##\s+When\s+To\s+Use", content, re.MULTILINE))
        assert has_workflow or has_quickstart or has_when, (
            f"SKILL.md for '{skill_name}' missing Workflow, Quick Start, "
            f"or When To Use section"
        )

    @pytest.mark.parametrize("skill_name", EXPECTED_CORE_SKILLS)
    def test_content_minimum_length(self, skill_name):
        """SKILL.md should have substantial content (> 200 chars body)."""
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        _, body = _parse_yaml_frontmatter(content)
        assert len(body) > 200, (
            f"SKILL.md body for '{skill_name}' is too short "
            f"({len(body)} chars, expected > 200)"
        )


# ---------------------------------------------------------------------------
# Test: All discovered skills load correctly
# ---------------------------------------------------------------------------


class TestAllSkillsLoadCorrectly:
    """Validate that ALL discovered skills (not just core 5) have valid structure."""

    def test_all_discovered_skills_have_valid_frontmatter(self):
        """Every SKILL.md in skills/ must have valid frontmatter with name and description."""
        all_skills = _discover_all_skills()
        failures = []

        for skill_name in all_skills:
            skill_md = SKILLS_DIR / skill_name / "SKILL.md"
            try:
                content = skill_md.read_text(encoding="utf-8")
                fm, _ = _parse_yaml_frontmatter(content)
                if fm is None:
                    failures.append(f"{skill_name}: No frontmatter found")
                    continue
                if "name" not in fm:
                    failures.append(f"{skill_name}: Missing 'name' in frontmatter")
                if "description" not in fm:
                    failures.append(f"{skill_name}: Missing 'description' in frontmatter")
            except Exception as e:
                failures.append(f"{skill_name}: Error reading SKILL.md: {e}")

        assert not failures, (
            f"Skills with invalid frontmatter:\n" +
            "\n".join(f"  - {f}" for f in failures)
        )

    def test_all_skills_count(self):
        """We should have at least 5 skill definitions."""
        all_skills = _discover_all_skills()
        assert len(all_skills) >= 5, (
            f"Expected at least 5 skills, discovered {len(all_skills)}: "
            f"{', '.join(all_skills)}"
        )

    def test_no_duplicate_skill_names(self):
        """No two skills should have the same 'name' in frontmatter."""
        all_skills = _discover_all_skills()
        names = {}

        for skill_name in all_skills:
            skill_md = SKILLS_DIR / skill_name / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")
            fm, _ = _parse_yaml_frontmatter(content)
            if fm and "name" in fm:
                fm_name = fm["name"]
                if fm_name in names:
                    pytest.fail(
                        f"Duplicate skill name '{fm_name}' in directories "
                        f"'{names[fm_name]}' and '{skill_name}'"
                    )
                names[fm_name] = skill_name


# ---------------------------------------------------------------------------
# Test: Smoke test script validation
# ---------------------------------------------------------------------------


class TestSmokeTestScript:
    """Validate the E2E smoke test script for fda-plugin-e2e-smoke."""

    SMOKE_SCRIPT = (
        SKILLS_DIR / "fda-plugin-e2e-smoke" / "scripts" / "run_smoke.sh"
    )

    def test_smoke_script_exists(self):
        """The run_smoke.sh script must exist."""
        assert self.SMOKE_SCRIPT.exists(), (
            f"Smoke test script not found: {self.SMOKE_SCRIPT}"
        )

    def test_smoke_script_has_shebang(self):
        """The script must have a proper shebang line."""
        content = self.SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert content.startswith("#!/"), (
            f"Smoke script missing shebang line"
        )

    def test_smoke_script_has_set_euo_pipefail(self):
        """The script should use 'set -euo pipefail' for safety."""
        content = self.SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "set -euo pipefail" in content, (
            "Smoke script should include 'set -euo pipefail'"
        )

    def test_smoke_script_is_executable_or_bash_callable(self):
        """The script should be runnable via bash."""
        # Check it can be parsed by bash without syntax errors
        result = subprocess.run(
            ["bash", "-n", str(self.SMOKE_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"Bash syntax check failed for smoke script:\n{result.stderr}"
        )

    def test_smoke_script_validates_outputs(self):
        """The script should include validation steps (SMOKE_STATUS/SMOKE_VALIDATION)."""
        content = self.SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "SMOKE_STATUS:PASS" in content or "SMOKE_VALIDATION:PASS" in content, (
            "Smoke script should contain pass/fail status markers"
        )

    def test_smoke_script_handles_cleanup(self):
        """The script should support a --cleanup flag."""
        content = self.SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "--cleanup" in content, (
            "Smoke script should support --cleanup flag"
        )

    def test_smoke_script_runs_gap_analysis(self):
        """The script should invoke gap_analysis.py."""
        content = self.SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "gap_analysis.py" in content, (
            "Smoke script should run gap_analysis.py"
        )

    def test_smoke_script_runs_predicate_extractor(self):
        """The script should invoke predicate_extractor.py."""
        content = self.SMOKE_SCRIPT.read_text(encoding="utf-8")
        assert "predicate_extractor.py" in content, (
            "Smoke script should run predicate_extractor.py"
        )


# ---------------------------------------------------------------------------
# Test: Skills functional loading simulation
# ---------------------------------------------------------------------------


class TestSkillsFunctionalLoading:
    """Simulate loading all skills as a plugin system would.

    Verifies that each skill can be discovered, parsed, and its metadata
    extracted without errors -- the functional equivalent of
    'all 5 skills load correctly'.
    """

    def test_load_all_core_skills(self):
        """Load all 5 core skills and verify metadata extraction."""
        loaded = {}

        for skill_name in EXPECTED_CORE_SKILLS:
            skill_md = SKILLS_DIR / skill_name / "SKILL.md"
            assert skill_md.exists(), f"Missing: {skill_md}"

            content = skill_md.read_text(encoding="utf-8")
            fm, body = _parse_yaml_frontmatter(content)

            assert fm is not None, f"No frontmatter in {skill_name}"
            assert "name" in fm, f"No name in {skill_name}"
            assert "description" in fm, f"No description in {skill_name}"

            loaded[skill_name] = {
                "name": fm["name"],
                "description": fm["description"],
                "body_length": len(body),
                "has_overview": bool(re.search(r"^##\s+Overview", body, re.MULTILINE)),
                "has_guardrails": bool(re.search(r"^##\s+Guardrails", body, re.MULTILINE)),
            }

        assert len(loaded) == 5, (
            f"Expected 5 loaded skills, got {len(loaded)}"
        )

        # Verify each loaded skill has valid metadata
        for skill_name, meta in loaded.items():
            assert meta["name"] == skill_name
            assert len(meta["description"]) > 10
            assert meta["body_length"] > 100
            assert meta["has_overview"], f"{skill_name} missing overview"
            assert meta["has_guardrails"], f"{skill_name} missing guardrails"

    def test_load_all_discovered_skills(self):
        """Load every discovered skill and extract metadata without errors."""
        all_skills = _discover_all_skills()
        loaded_count = 0
        errors = []

        for skill_name in all_skills:
            skill_md = SKILLS_DIR / skill_name / "SKILL.md"
            try:
                content = skill_md.read_text(encoding="utf-8")
                fm, body = _parse_yaml_frontmatter(content)
                if fm is None:
                    errors.append(f"{skill_name}: frontmatter parse failed")
                    continue
                if not fm.get("name"):
                    errors.append(f"{skill_name}: empty name")
                    continue
                if not fm.get("description"):
                    errors.append(f"{skill_name}: empty description")
                    continue
                loaded_count += 1
            except Exception as e:
                errors.append(f"{skill_name}: {e}")

        assert not errors, (
            f"Failed to load {len(errors)} skill(s):\n" +
            "\n".join(f"  - {e}" for e in errors)
        )
        assert loaded_count >= 5, (
            f"Expected at least 5 loadable skills, got {loaded_count}"
        )
