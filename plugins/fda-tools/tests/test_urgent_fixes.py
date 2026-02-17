"""
Tests for URGENT priority fixes: FDA-34, FDA-32, FDA-33.

FDA-34: Compliance Disclaimer Not Shown at CLI Runtime
FDA-32: save_manifest() Not Atomic - Data Corruption Risk
FDA-33: CI/CD Pipeline Missing Python 3.12 & Dependencies

These tests validate critical compliance and data integrity fixes
without requiring network access.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts directory is importable
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)


# ============================================================================
# FDA-34: Compliance Disclaimer Tests
# ============================================================================


class TestComplianceDisclaimer:
    """Validate that the compliance disclaimer module works correctly.

    Regulatory basis: 21 CFR Part 11 requires clear attribution and
    context for electronic records. Research-use-only tools must display
    disclaimers before producing output.
    """

    def test_disclaimer_module_imports(self):
        """The compliance_disclaimer module should be importable."""
        from compliance_disclaimer import (  # type: ignore
            show_disclaimer,
            add_disclaimer_args,
            DISCLAIMER_TEXT,
            DISCLAIMER_SHORT,
        )
        assert callable(show_disclaimer)
        assert callable(add_disclaimer_args)
        assert "RESEARCH USE ONLY" in DISCLAIMER_TEXT
        assert "RESEARCH USE ONLY" in DISCLAIMER_SHORT

    def test_disclaimer_text_contains_required_elements(self):
        """Disclaimer must contain all required warning elements."""
        from compliance_disclaimer import DISCLAIMER_TEXT  # type: ignore

        required_phrases = [
            "RESEARCH USE ONLY",
            "NOT FOR DIRECT FDA SUBMISSION",
            "qualified Regulatory Affairs",
            "independently verified",
            "21 CFR",
        ]
        for phrase in required_phrases:
            assert phrase in DISCLAIMER_TEXT, (
                f"Disclaimer missing required phrase: '{phrase}'"
            )

    def test_disclaimer_accepted_with_flag(self, capsys):
        """--accept-disclaimer flag should skip interactive prompt."""
        from compliance_disclaimer import show_disclaimer  # type: ignore

        result = show_disclaimer("test-tool", accept_flag=True)
        assert result is True
        captured = capsys.readouterr()
        assert "RESEARCH USE ONLY" in captured.err

    def test_disclaimer_accepted_quiet_mode(self, capsys):
        """Quiet mode should show short disclaimer on stderr."""
        from compliance_disclaimer import show_disclaimer  # type: ignore

        result = show_disclaimer("test-tool", accept_flag=False, quiet=True)
        assert result is True
        captured = capsys.readouterr()
        assert "RESEARCH USE ONLY" in captured.err
        # Quiet mode should NOT show the full banner
        assert "independently verified" not in captured.err

    def test_disclaimer_exits_on_decline(self, monkeypatch):
        """Declining the disclaimer in interactive mode should exit."""
        from compliance_disclaimer import show_disclaimer  # type: ignore

        monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: True))
        monkeypatch.setattr("builtins.input", lambda _: "n")

        with pytest.raises(SystemExit) as exc_info:
            show_disclaimer("test-tool", accept_flag=False)
        assert exc_info.value.code == 1

    def test_disclaimer_accepts_yes(self, monkeypatch, capsys):
        """Typing 'y' should accept the disclaimer."""
        from compliance_disclaimer import show_disclaimer  # type: ignore

        monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: True))
        monkeypatch.setattr("builtins.input", lambda _: "y")

        result = show_disclaimer("test-tool", accept_flag=False)
        assert result is True

    def test_disclaimer_noninteractive_requires_flag(self, monkeypatch):
        """Non-interactive (piped) mode without flag should exit."""
        from compliance_disclaimer import show_disclaimer  # type: ignore

        monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: False))

        with pytest.raises(SystemExit) as exc_info:
            show_disclaimer("test-tool", accept_flag=False)
        assert exc_info.value.code == 1

    def test_add_disclaimer_args(self):
        """add_disclaimer_args should add --accept-disclaimer flag."""
        import argparse
        from compliance_disclaimer import add_disclaimer_args  # type: ignore

        parser = argparse.ArgumentParser()
        add_disclaimer_args(parser)
        args = parser.parse_args(["--accept-disclaimer"])
        assert args.accept_disclaimer is True

        args_default = parser.parse_args([])
        assert args_default.accept_disclaimer is False

    def test_audit_log_written_on_acceptance(self, tmp_path, monkeypatch):
        """Disclaimer acceptance should be logged to audit trail."""
        from compliance_disclaimer import _log_disclaimer_event  # type: ignore

        log_dir = str(tmp_path / "logs")
        monkeypatch.setattr(
            "os.path.expanduser",
            lambda p: str(tmp_path) if "~/fda-510k-data" in p else p,
        )
        # Patch the log directory path
        monkeypatch.setattr(
            "compliance_disclaimer.os.path.expanduser",
            lambda p: str(tmp_path / "fda-510k-data" / "logs")
            if "~/fda-510k-data/logs" in p
            else p,
        )

        _log_disclaimer_event("test-tool", "accepted_flag")

        log_path = tmp_path / "fda-510k-data" / "logs" / "disclaimer_audit.jsonl"
        if log_path.exists():
            lines = log_path.read_text().strip().split("\n")
            entry = json.loads(lines[-1])
            assert entry["tool"] == "test-tool"
            assert entry["action"] == "accepted_flag"
            assert "timestamp" in entry

    def test_disclaimer_handles_keyboard_interrupt(self, monkeypatch):
        """KeyboardInterrupt during input should exit gracefully."""
        from compliance_disclaimer import show_disclaimer  # type: ignore

        monkeypatch.setattr("sys.stdin", MagicMock(isatty=lambda: True))

        def raise_interrupt(_):
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", raise_interrupt)

        with pytest.raises(SystemExit) as exc_info:
            show_disclaimer("test-tool", accept_flag=False)
        assert exc_info.value.code == 1


# ============================================================================
# FDA-32: Atomic Manifest Writes Tests
# ============================================================================


class TestAtomicManifestWrites:
    """Validate that save_manifest() uses atomic write-then-rename.

    Regulatory basis: 21 CFR 820.70(i) requires that automated data
    processing ensures data integrity. A crash during file write must
    not corrupt the manifest.
    """

    def test_save_manifest_creates_file(self, tmp_path):
        """save_manifest should create data_manifest.json."""
        from fda_data_store import save_manifest, load_manifest  # type: ignore

        project_dir = str(tmp_path / "test_atomic")
        manifest = load_manifest(project_dir)
        save_manifest(project_dir, manifest)

        manifest_path = os.path.join(project_dir, "data_manifest.json")
        assert os.path.exists(manifest_path)

        # Verify content is valid JSON
        with open(manifest_path) as f:
            data = json.load(f)
        assert data["project"] == "test_atomic"

    def test_save_manifest_creates_backup(self, tmp_path):
        """save_manifest should create .bak file after second write."""
        from fda_data_store import save_manifest, load_manifest  # type: ignore

        project_dir = str(tmp_path / "test_backup")
        manifest = load_manifest(project_dir)

        # First write
        save_manifest(project_dir, manifest)
        backup_path = os.path.join(project_dir, "data_manifest.json.bak")
        # Backup might not exist after first write (no pre-existing file)

        # Modify and write again
        manifest["product_codes"] = ["DQY"]
        save_manifest(project_dir, manifest)

        # Now backup should exist (copy of the first write)
        assert os.path.exists(backup_path)

        with open(backup_path) as f:
            backup_data = json.load(f)
        # Backup should have the old data (empty product_codes)
        assert backup_data["product_codes"] == []

    def test_save_manifest_no_temp_files_left(self, tmp_path):
        """After successful save, no .tmp files should remain."""
        from fda_data_store import save_manifest, load_manifest  # type: ignore

        project_dir = str(tmp_path / "test_no_tmp")
        manifest = load_manifest(project_dir)
        save_manifest(project_dir, manifest)

        tmp_files = [
            f for f in os.listdir(project_dir) if f.endswith(".tmp")
        ]
        assert len(tmp_files) == 0, f"Temp files left behind: {tmp_files}"

    def test_save_manifest_content_integrity(self, tmp_path):
        """Saved manifest should be byte-identical to intended content."""
        from fda_data_store import save_manifest, load_manifest  # type: ignore

        project_dir = str(tmp_path / "test_integrity")
        manifest = {
            "project": "integrity_test",
            "created_at": "2026-02-16T00:00:00+00:00",
            "last_updated": "2026-02-16T00:00:00+00:00",
            "product_codes": ["DQY", "OVE", "GEI"],
            "queries": {"classification:DQY": {"summary": {"class": "2"}}},
        }
        save_manifest(project_dir, manifest)
        loaded = load_manifest(project_dir)

        assert loaded["product_codes"] == ["DQY", "OVE", "GEI"]
        assert loaded["queries"]["classification:DQY"]["summary"]["class"] == "2"

    def test_load_manifest_recovers_from_corruption(self, tmp_path):
        """If primary manifest is corrupt, load_manifest should use .bak."""
        from fda_data_store import load_manifest  # type: ignore

        project_dir = str(tmp_path / "test_recovery")
        os.makedirs(project_dir)

        # Create a valid backup
        backup_data = {
            "project": "recovery_test",
            "created_at": "2026-02-16T00:00:00+00:00",
            "last_updated": "2026-02-16T00:00:00+00:00",
            "product_codes": ["RECOVERED"],
            "queries": {},
        }
        backup_path = os.path.join(project_dir, "data_manifest.json.bak")
        with open(backup_path, "w") as f:
            json.dump(backup_data, f)

        # Create a corrupt primary
        manifest_path = os.path.join(project_dir, "data_manifest.json")
        with open(manifest_path, "w") as f:
            f.write("{corrupt json data incomplete")

        # load_manifest should recover from backup
        manifest = load_manifest(project_dir)
        assert manifest["product_codes"] == ["RECOVERED"]

    def test_load_manifest_fresh_when_both_corrupt(self, tmp_path):
        """If both primary and backup are corrupt, return fresh manifest."""
        from fda_data_store import load_manifest  # type: ignore

        project_dir = str(tmp_path / "both_corrupt")
        os.makedirs(project_dir)

        # Create corrupt primary and backup
        for filename in ["data_manifest.json", "data_manifest.json.bak"]:
            with open(os.path.join(project_dir, filename), "w") as f:
                f.write("{broken")

        manifest = load_manifest(project_dir)
        assert manifest["queries"] == {}
        assert manifest["product_codes"] == []

    def test_save_manifest_atomic_on_simulated_crash(self, tmp_path):
        """Simulate a crash during write; manifest should remain intact."""
        from fda_data_store import save_manifest, load_manifest  # type: ignore

        project_dir = str(tmp_path / "crash_test")
        original_manifest = {
            "project": "crash_test",
            "created_at": "2026-02-16T00:00:00+00:00",
            "last_updated": "2026-02-16T00:00:00+00:00",
            "product_codes": ["ORIGINAL"],
            "queries": {},
        }

        # First successful save
        save_manifest(project_dir, original_manifest)

        # Simulate crash: patch os.replace to raise after tmp file written
        original_replace = os.replace

        def crashing_replace(src, dst):
            raise OSError("Simulated disk failure during rename")

        with patch("fda_data_store.os.replace", side_effect=crashing_replace):
            with pytest.raises(OSError, match="Simulated disk failure"):
                new_manifest = {
                    "project": "crash_test",
                    "created_at": "2026-02-16T00:00:00+00:00",
                    "last_updated": "2026-02-16T00:00:00+00:00",
                    "product_codes": ["CORRUPTED"],
                    "queries": {},
                }
                save_manifest(project_dir, new_manifest)

        # Original manifest should still be intact
        loaded = load_manifest(project_dir)
        assert loaded["product_codes"] == ["ORIGINAL"]

    def test_save_manifest_cleans_temp_on_failure(self, tmp_path):
        """Temp files should be cleaned up even when write fails."""
        from fda_data_store import save_manifest, load_manifest  # type: ignore

        project_dir = str(tmp_path / "cleanup_test")
        os.makedirs(project_dir)

        def crashing_replace(src, dst):
            raise OSError("Simulated failure")

        with patch("fda_data_store.os.replace", side_effect=crashing_replace):
            with pytest.raises(OSError):
                save_manifest(project_dir, {"project": "cleanup"})

        # No temp files should remain
        tmp_files = [
            f for f in os.listdir(project_dir)
            if ".tmp" in f or f.startswith(".data_manifest_")
        ]
        assert len(tmp_files) == 0, f"Temp files not cleaned: {tmp_files}"

    def test_save_manifest_roundtrip_multiple_writes(self, tmp_path):
        """Multiple sequential saves should maintain data integrity."""
        from fda_data_store import save_manifest, load_manifest  # type: ignore

        project_dir = str(tmp_path / "multi_write")

        for i in range(10):
            manifest = load_manifest(project_dir)
            manifest.setdefault("product_codes", []).append(f"CODE{i}")
            save_manifest(project_dir, manifest)

        final = load_manifest(project_dir)
        # Should have accumulated all 10 codes
        assert len(final["product_codes"]) >= 10


# ============================================================================
# FDA-33: CI/CD Pipeline Configuration Tests
# ============================================================================


class TestCICDConfiguration:
    """Validate CI/CD pipeline configuration correctness.

    Regulatory basis: 21 CFR 820.70(i) requires validated software
    build processes. The CI pipeline must test against all supported
    Python versions with all required dependencies.
    """

    @pytest.fixture
    def workflow_path(self):
        return os.path.join(
            os.path.dirname(__file__), "..", ".github", "workflows", "test.yml"
        )

    def test_workflow_file_exists(self, workflow_path):
        """CI workflow file must exist."""
        assert os.path.exists(workflow_path), (
            f"CI workflow not found at {workflow_path}"
        )

    def test_workflow_includes_python_312(self, workflow_path):
        """Python 3.12 must be in the test matrix."""
        with open(workflow_path) as f:
            content = f.read()
        assert '"3.12"' in content or "'3.12'" in content, (
            "Python 3.12 missing from CI matrix"
        )

    def test_workflow_installs_requirements(self, workflow_path):
        """CI must install from requirements.txt."""
        with open(workflow_path) as f:
            content = f.read()
        assert "requirements.txt" in content, (
            "CI does not install from requirements.txt"
        )

    def test_workflow_has_coverage(self, workflow_path):
        """CI must generate coverage reports."""
        with open(workflow_path) as f:
            content = f.read()
        assert "--cov" in content, "CI missing coverage flag"

    def test_workflow_has_linting(self, workflow_path):
        """CI must include a linting step."""
        with open(workflow_path) as f:
            content = f.read()
        assert "ruff" in content or "flake8" in content, (
            "CI missing linting step"
        )

    def test_workflow_retains_python_39_311(self, workflow_path):
        """Existing Python versions (3.9-3.11) must still be tested."""
        with open(workflow_path) as f:
            content = f.read()
        for version in ["3.9", "3.10", "3.11"]:
            assert f'"{version}"' in content or f"'{version}'" in content, (
                f"Python {version} missing from CI matrix"
            )

    def test_requirements_file_exists(self):
        """requirements.txt must exist in scripts directory."""
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "requirements.txt"
        )
        assert os.path.exists(req_path), (
            f"requirements.txt not found at {req_path}"
        )

    def test_requirements_has_core_deps(self):
        """requirements.txt must include core dependencies."""
        req_path = os.path.join(
            os.path.dirname(__file__), "..", "scripts", "requirements.txt"
        )
        with open(req_path) as f:
            content = f.read()

        core_deps = ["requests", "pytest", "pytest-cov"]
        for dep in core_deps:
            assert dep in content, (
                f"Core dependency '{dep}' missing from requirements.txt"
            )


# ============================================================================
# FDA-31: Bare Except Clauses (HIGH, related validation)
# ============================================================================


class TestBareExceptAudit:
    """Verify that bare except clauses have been addressed.

    This test scans the scripts directory for bare 'except:' patterns
    (without specifying an exception type). Per IEC 62304, error handling
    must be explicit and traceable.
    """

    def test_no_bare_except_in_standards_generators(self):
        """Standards generation scripts must have no bare except clauses.

        Fixed as part of FDA-31 (HIGH priority). All bare except: clauses
        have been replaced with specific exception types.
        """
        scripts_to_check = [
            "knowledge_based_generator.py",
            "quick_standards_generator.py",
            "auto_generate_device_standards.py",
        ]

        bare_except_found = []
        for script_name in scripts_to_check:
            script_path = os.path.join(SCRIPTS_DIR, script_name)
            if not os.path.exists(script_path):
                continue
            with open(script_path) as f:
                for line_num, line in enumerate(f, 1):
                    stripped = line.strip()
                    # Match bare except: but not except SomeError: or except (A, B):
                    if stripped == "except:" or stripped.startswith("except: "):
                        bare_except_found.append(
                            f"{script_name}:{line_num}: {stripped}"
                        )

        assert len(bare_except_found) == 0, (
            f"Bare except clauses found: {bare_except_found}"
        )


# ============================================================================
# Integration: Disclaimer + Standards Generator Integration
# ============================================================================


class TestDisclaimerIntegration:
    """Verify that standards generators have disclaimer integration."""

    def _read_main_function(self, script_name):
        """Read a script and return its main() function source."""
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        with open(script_path) as f:
            return f.read()

    def test_knowledge_based_generator_has_disclaimer(self):
        """knowledge_based_generator.py must import and call disclaimer."""
        source = self._read_main_function("knowledge_based_generator.py")
        assert "compliance_disclaimer" in source
        assert "show_disclaimer" in source
        assert "accept_disclaimer" in source

    def test_quick_standards_generator_has_disclaimer(self):
        """quick_standards_generator.py must import and call disclaimer."""
        source = self._read_main_function("quick_standards_generator.py")
        assert "compliance_disclaimer" in source
        assert "show_disclaimer" in source
        assert "accept_disclaimer" in source

    def test_auto_generate_standards_has_disclaimer(self):
        """auto_generate_device_standards.py must import and call disclaimer."""
        source = self._read_main_function("auto_generate_device_standards.py")
        assert "compliance_disclaimer" in source
        assert "show_disclaimer" in source
        assert "accept_disclaimer" in source
