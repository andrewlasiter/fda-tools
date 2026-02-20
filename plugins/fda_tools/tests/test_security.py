#!/usr/bin/env python3
"""
Security test suite for FDA-83, FDA-84, and FDA-85.

Tests:
  FDA-83: Path traversal prevention in agent_registry.py
  FDA-84: API key redaction in logging and console output
  FDA-85: Safe YAML parsing with schema validation

Run with:
    python3 -m pytest tests/test_security.py -v
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure scripts directory is on path
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")

from agent_registry import (  # noqa: E402
    AgentRegistry,
    _parse_yaml_file,
    _validate_yaml_schema,
    ALLOWED_AGENT_YAML_KEYS,
)
from setup_api_key import (  # noqa: E402
    APIKeyRedactor,
    mask_api_key,
    install_api_key_redactor,
)


# ==================================================================
# FDA-83: Path Traversal Prevention Tests
# ==================================================================

class TestFDA83PathTraversal:
    """Verify that path traversal attacks are blocked in agent_registry."""

    def setup_method(self):
        """Create temporary directory structures for testing."""
        self.tmpdir = tempfile.mkdtemp()
        self.skills_dir = Path(self.tmpdir) / "skills"
        self.skills_dir.mkdir()

        # Create a valid agent
        valid_agent = self.skills_dir / "fda-test-agent"
        valid_agent.mkdir()
        (valid_agent / "SKILL.md").write_text(
            "---\nname: fda-test-agent\ndescription: A test agent for security testing\n---\n"
            "## Overview\nTest agent.\n"
        )

    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_valid_agent_is_loaded(self):
        """Normal agents within the skills directory are loaded."""
        registry = AgentRegistry(skills_dir=self.skills_dir)
        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "fda-test-agent"

    def test_symlink_outside_base_is_blocked(self):
        """Symlinks pointing outside the skills directory are rejected."""
        # Create a directory outside the skills dir
        outside_dir = Path(self.tmpdir) / "outside"
        outside_dir.mkdir()
        (outside_dir / "SKILL.md").write_text(
            "---\nname: evil-agent\ndescription: Malicious agent via symlink\n---\n"
            "## Overview\nEvil.\n"
        )

        # Create a symlink inside skills/ that points outside
        symlink_path = self.skills_dir / "evil-symlink"
        try:
            symlink_path.symlink_to(outside_dir)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        registry = AgentRegistry(skills_dir=self.skills_dir)
        agents = registry.list_agents()

        # The symlinked agent should be blocked
        agent_names = [a["name"] for a in agents]
        assert "evil-agent" not in agent_names

    def test_dotdot_in_path_does_not_escape(self):
        """Directory names with '..' components cannot escape the base."""
        # This tests the _validate_path_within_base method directly
        registry = AgentRegistry(skills_dir=self.skills_dir)

        base = self.skills_dir.resolve()
        # Construct a path that tries to escape via ..
        malicious_path = self.skills_dir / ".." / ".." / "etc" / "passwd"

        result = registry._validate_path_within_base(malicious_path, base)
        assert result is False, "Path with ../../../etc/passwd should be blocked"

    def test_etc_passwd_traversal_blocked(self):
        """Classic path traversal attack vectors are blocked."""
        registry = AgentRegistry(skills_dir=self.skills_dir)
        base = self.skills_dir.resolve()

        attack_paths = [
            self.skills_dir / ".." / ".." / ".." / "etc" / "passwd",
            self.skills_dir / "legitimate-agent" / ".." / ".." / ".." / "etc" / "shadow",
            self.skills_dir / "." / ".." / ".." / "root" / ".ssh" / "id_rsa",
        ]

        for attack_path in attack_paths:
            result = registry._validate_path_within_base(attack_path, base)
            assert result is False, f"Path traversal should be blocked: {attack_path}"

    def test_valid_path_within_base_passes(self):
        """Legitimate paths within the base directory pass validation."""
        registry = AgentRegistry(skills_dir=self.skills_dir)
        base = self.skills_dir.resolve()

        valid_agent = self.skills_dir / "fda-test-agent" / "SKILL.md"
        result = registry._validate_path_within_base(valid_agent, base)
        assert result is True

    def test_path_traversal_logged_as_warning(self, caplog):
        """Path traversal attempts are logged with WARNING level."""
        registry = AgentRegistry(skills_dir=self.skills_dir)
        base = self.skills_dir.resolve()
        malicious = self.skills_dir / ".." / ".." / "etc" / "passwd"

        with caplog.at_level(logging.WARNING):
            registry._validate_path_within_base(malicious, base)

        assert any("Path traversal attempt blocked" in r.message for r in caplog.records)

    def test_nonexistent_skills_dir_handled(self):
        """Non-existent skills directory is handled gracefully."""
        fake_dir = Path(self.tmpdir) / "nonexistent"
        registry = AgentRegistry(skills_dir=fake_dir)
        agents = registry.list_agents()
        assert len(agents) == 0


# ==================================================================
# FDA-84: API Key Redaction Tests
# ==================================================================

class TestFDA84APIKeyRedaction:
    """Verify that API keys are never exposed in logs or console output."""

    def test_mask_api_key_normal(self):
        """Normal-length API keys are masked showing first and last 4 chars."""
        key = "abcdefghijklmnopqrstuvwxyz"
        masked = mask_api_key(key)
        assert masked == "abcd...wxyz"
        assert key not in masked

    def test_mask_api_key_short(self):
        """Short keys (< 8 chars) are fully redacted."""
        assert mask_api_key("abc") == "REDACTED"
        assert mask_api_key("") == "REDACTED"
        assert mask_api_key(None) == "REDACTED"

    def test_mask_api_key_exact_8(self):
        """8-char keys show first 4 and last 4 (which overlap is fine)."""
        key = "12345678"
        masked = mask_api_key(key)
        assert masked == "1234...5678"

    def test_redactor_filters_log_messages(self):
        """APIKeyRedactor strips key-like strings from log messages."""
        redactor = APIKeyRedactor()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="API key is abcdefghijklmnopqrstuvwxyz1234 and that is secret",
            args=None, exc_info=None,
        )

        redactor.filter(record)

        # The full key should not appear in the filtered message
        assert "abcdefghijklmnopqrstuvwxyz1234" not in record.msg
        # But the masked version should
        assert "abcd" in record.msg
        assert "1234" in record.msg

    def test_redactor_filters_log_args_tuple(self):
        """APIKeyRedactor redacts keys in log record args (tuple form)."""
        redactor = APIKeyRedactor()

        key = "SuperSecretAPIKey1234567890XYZ"
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Key: %s", args=(key,), exc_info=None,
        )

        redactor.filter(record)

        # The arg should be redacted
        assert key not in str(record.args)

    def test_redactor_filters_log_args_dict(self):
        """APIKeyRedactor redacts keys in log record args (dict form)."""
        redactor = APIKeyRedactor()

        key = "SuperSecretAPIKey1234567890XYZ"
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Data: %(api_key)s", args={"api_key": key}, exc_info=None,
        )

        redactor.filter(record)

        assert key not in str(record.args)

    def test_redactor_does_not_suppress_records(self):
        """APIKeyRedactor never suppresses log records (always returns True)."""
        redactor = APIKeyRedactor()

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Normal message without keys", args=None, exc_info=None,
        )

        result = redactor.filter(record)
        assert result is True

    def test_install_redactor_is_idempotent(self):
        """install_api_key_redactor can be called multiple times safely."""
        initial_filter_count = len(logging.root.filters)

        install_api_key_redactor()
        count_after_first = len(logging.root.filters)

        install_api_key_redactor()
        count_after_second = len(logging.root.filters)

        # Should not add duplicate filters
        assert count_after_second == count_after_first

    def test_no_full_key_in_setup_export_output(self):
        """The export OPENFDA_API_KEY line should not show the full key."""
        # We test the mask_api_key function that is used in the print statement
        test_key = "aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0u"
        masked = mask_api_key(test_key)
        assert test_key not in masked
        assert len(masked) < len(test_key)


# ==================================================================
# FDA-85: Safe YAML Parsing Tests
# ==================================================================

class TestFDA85SafeYAML:
    """Verify that YAML parsing uses safe_load and validates schemas."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_safe_load_is_used(self):
        """Verify yaml.safe_load is used (not yaml.load) in agent_registry."""
        import agent_registry
        source = Path(agent_registry.__file__).read_text()

        # Should NOT have yaml.load( without safe_
        import re
        unsafe_calls = re.findall(r'yaml\.load\(', source)
        assert len(unsafe_calls) == 0, f"Found unsafe yaml.load() calls: {unsafe_calls}"

        # Should have yaml.safe_load
        safe_calls = re.findall(r'yaml\.safe_load\(', source)
        assert len(safe_calls) >= 2, "Expected at least 2 yaml.safe_load calls"

    def test_malicious_yaml_python_object_blocked(self):
        """Malicious YAML with !!python/object is blocked by safe_load."""
        # This YAML payload uses a !!python/object/apply directive
        # that yaml.safe_load will reject (ConstructorError)
        yaml_content = "!!python/object/apply:builtins.print\nargs: ['blocked']\n"
        yaml_path = Path(self.tmpdir) / "malicious.yaml"
        yaml_path.write_text(yaml_content)

        # safe_load should raise an exception or return empty dict
        result = _parse_yaml_file(yaml_path)
        # Should not have executed anything; result should be safe
        assert isinstance(result, dict)

    def test_malicious_yaml_eval_blocked(self):
        """YAML !!python/object/apply with eval-like construct is blocked."""
        yaml_content = "!!python/object/new:builtins.eval\nargs: ['1+1']\n"
        yaml_path = Path(self.tmpdir) / "malicious2.yaml"
        yaml_path.write_text(yaml_content)

        result = _parse_yaml_file(yaml_path)
        assert isinstance(result, dict)

    def test_valid_yaml_parsed_correctly(self):
        """Valid agent YAML is parsed correctly."""
        yaml_content = (
            "name: fda-test-expert\n"
            "description: Test expert agent\n"
            "model: opus\n"
            "tools:\n"
            "  - Read\n"
            "  - Grep\n"
        )
        yaml_path = Path(self.tmpdir) / "valid.yaml"
        yaml_path.write_text(yaml_content)

        result = _parse_yaml_file(yaml_path)
        assert result["name"] == "fda-test-expert"
        assert result["description"] == "Test expert agent"
        assert result["model"] == "opus"

    def test_unknown_keys_filtered(self):
        """Unknown top-level keys are filtered from parsed YAML."""
        data = {
            "name": "test-agent",
            "description": "Valid field",
            "evil_command": "dangerous payload",
            "__proto__": {"polluted": True},
        }
        result = _validate_yaml_schema(data, source="test")
        assert "name" in result
        assert "description" in result
        assert "evil_command" not in result
        assert "__proto__" not in result

    def test_allowed_keys_whitelist_completeness(self):
        """The allowed keys whitelist covers standard agent.yaml fields."""
        required_keys = {"name", "description", "model", "tools"}
        assert required_keys.issubset(ALLOWED_AGENT_YAML_KEYS)

    def test_schema_validation_with_non_dict(self):
        """Non-dict YAML results return empty dict."""
        result = _validate_yaml_schema("just a string", source="test")
        assert result == {}

        result = _validate_yaml_schema(42, source="test")
        assert result == {}

    def test_schema_validation_logs_unknown_keys(self, caplog):
        """Unknown keys in YAML trigger a warning log."""
        data = {"name": "test", "malicious_key": "value"}
        with caplog.at_level(logging.WARNING):
            _validate_yaml_schema(data, source="test.yaml")
        assert any("rejecting unknown keys" in r.message for r in caplog.records)

    def test_empty_yaml_file(self):
        """Empty YAML files return empty dict without error."""
        yaml_path = Path(self.tmpdir) / "empty.yaml"
        yaml_path.write_text("")

        result = _parse_yaml_file(yaml_path)
        assert result == {}

    def test_yaml_with_only_allowed_keys(self):
        """YAML with only allowed keys passes validation unchanged."""
        data = {
            "name": "test-agent",
            "description": "A test agent",
            "model": "opus",
            "tools": ["Read", "Grep"],
            "expertise": ["510(k)"],
        }
        result = _validate_yaml_schema(data, source="test")
        assert result == data


# ==================================================================
# Integration: Combined Security Tests
# ==================================================================

class TestSecurityIntegration:
    """Integration tests combining multiple security features."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.skills_dir = Path(self.tmpdir) / "skills"
        self.skills_dir.mkdir()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_agent_with_malicious_yaml_is_safe(self):
        """An agent with a malicious agent.yaml is loaded safely."""
        agent_dir = self.skills_dir / "fda-safe-agent"
        agent_dir.mkdir()
        (agent_dir / "SKILL.md").write_text(
            "---\nname: fda-safe-agent\ndescription: Agent with dangerous YAML config\n---\n"
            "## Overview\nSafe agent.\n"
        )
        # Write YAML with unknown/suspicious keys
        (agent_dir / "agent.yaml").write_text(
            "name: fda-safe-agent\n"
            "description: Normal agent\n"
            "shell_command: dangerous payload\n"
            "exec_directive: another payload\n"
        )

        registry = AgentRegistry(skills_dir=self.skills_dir)
        agents = registry.list_agents()
        assert len(agents) == 1

        # The malicious keys should have been filtered out
        agent = agents[0]
        yaml_config = agent["yaml_config"]
        assert "shell_command" not in yaml_config
        assert "exec_directive" not in yaml_config

    def test_full_security_scan_on_real_skills(self):
        """Run security validation against the actual skills directory."""
        real_skills = Path(__file__).parent.parent / "skills"
        if not real_skills.exists():
            pytest.skip("Skills directory not found")

        registry = AgentRegistry(skills_dir=real_skills)
        agents = registry.list_agents()

        # All agents should load without path traversal warnings
        for agent in agents:
            agent_path = Path(agent["directory"])
            assert real_skills.resolve() in agent_path.resolve().parents or \
                agent_path.resolve() == real_skills.resolve(), \
                f"Agent {agent['name']} path escapes skills directory"
