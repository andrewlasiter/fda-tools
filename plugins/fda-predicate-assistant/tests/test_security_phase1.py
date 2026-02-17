"""
Phase 1 Security Foundation - Unit Tests

Tests for security_gateway.py and audit_logger.py modules.

Run with: python3 -m pytest tests/test_security_phase1.py -v
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

import pytest

# Import modules to test
from security_gateway import (
    SecurityGateway,
    DataClassification,
    LLMProvider,
    get_security_gateway
)
from audit_logger import AuditLogger, AuditEvent, get_audit_logger


class TestSecurityGateway:
    """Test suite for SecurityGateway class"""

    @pytest.fixture
    def temp_config(self):
        """Create temporary security config for testing"""
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / 'security.toml'

        # Write minimal test config
        config_content = """
[security]
version = "1.0.0"
immutable = true

[data_classification]
public_patterns = ["*/openFDA/*", "*/MAUDE/*"]
confidential_patterns = ["*/projects/*", "*/submissions/*"]

[llm_providers]
local_preferred = true
require_local_for_confidential = true

[llm_providers.ollama]
enabled = true
endpoint = "http://localhost:11434"
models = ["llama2", "mistral"]

[llm_providers.anthropic]
enabled = true
endpoint = "https://api.anthropic.com"
models = ["claude-opus-4.6"]

[communication]
public_channels = ["whatsapp", "telegram", "slack", "file"]
restricted_channels = ["file", "webhook"]
confidential_channels = ["file"]

[audit]
log_path = "~/.claude/fda-tools.audit.jsonl"
retention_days = 2555
"""
        config_path.write_text(config_content)

        # Make immutable
        os.chmod(config_path, 0o444)

        yield str(config_path)

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_load_policy(self, temp_config):
        """Test loading security policy from config"""
        gateway = SecurityGateway(temp_config)

        assert gateway.policy.local_preferred is True
        assert gateway.policy.require_local_for_confidential is True
        assert "llama2" in gateway.policy.ollama_models
        assert "file" in gateway.policy.confidential_channels

    def test_immutable_config(self, temp_config):
        """Test that config file is immutable (read-only)"""
        gateway = SecurityGateway(temp_config)

        # Verify file mode is 444
        stat_info = Path(temp_config).stat()
        mode = stat_info.st_mode & 0o777
        assert mode == 0o444

    def test_classify_public_data(self, temp_config):
        """Test classification of PUBLIC data"""
        gateway = SecurityGateway(temp_config)

        file_paths = [
            "/data/openFDA/device_510k.json",
            "/cache/MAUDE/events.json"
        ]

        classification = gateway.classify_data(file_paths, "validate")
        assert classification == DataClassification.PUBLIC

    def test_classify_confidential_data(self, temp_config):
        """Test classification of CONFIDENTIAL data"""
        gateway = SecurityGateway(temp_config)

        file_paths = [
            "/fda-510k-data/projects/ABC001/device_profile.json",
            "/home/user/submissions/draft.md"
        ]

        classification = gateway.classify_data(file_paths, "draft")
        assert classification == DataClassification.CONFIDENTIAL

    def test_classify_restricted_command(self, temp_config):
        """Test classification of RESTRICTED commands"""
        gateway = SecurityGateway(temp_config)

        # Commands that generate derived intelligence are RESTRICTED
        file_paths = ["/data/openFDA/predicates.json"]

        classification = gateway.classify_data(file_paths, "analyze")
        assert classification == DataClassification.RESTRICTED

    def test_pattern_matching(self, temp_config):
        """Test glob pattern matching"""
        gateway = SecurityGateway(temp_config)

        # Test single wildcard
        assert gateway._match_pattern(
            "/data/openFDA/devices.json",
            "*/openFDA/*"
        )

        # Test recursive wildcard
        assert gateway._match_pattern(
            "/data/projects/ABC/submissions/draft.md",
            "*/projects/*"
        )

    def test_channel_validation_confidential(self, temp_config):
        """Test channel validation for CONFIDENTIAL data"""
        gateway = SecurityGateway(temp_config)

        # File channel should be allowed
        allowed, warnings = gateway.validate_channel(
            DataClassification.CONFIDENTIAL,
            "file"
        )
        assert allowed is True
        assert len(warnings) == 0

        # WhatsApp should be blocked
        allowed, warnings = gateway.validate_channel(
            DataClassification.CONFIDENTIAL,
            "whatsapp"
        )
        assert allowed is False
        assert len(warnings) > 0

    def test_channel_validation_public(self, temp_config):
        """Test channel validation for PUBLIC data"""
        gateway = SecurityGateway(temp_config)

        # All channels should be allowed for PUBLIC data
        for channel in ["whatsapp", "telegram", "slack", "file"]:
            allowed, warnings = gateway.validate_channel(
                DataClassification.PUBLIC,
                channel
            )
            assert allowed is True

    def test_security_evaluation(self, temp_config):
        """Test complete security evaluation"""
        gateway = SecurityGateway(temp_config)

        # Test PUBLIC data with allowed channel
        decision = gateway.evaluate(
            command="validate",
            file_paths=["/data/openFDA/device.json"],
            channel="whatsapp",
            user_id="test_user",
            session_id="test_session"
        )

        assert decision.classification == DataClassification.PUBLIC
        assert decision.channel_allowed is True
        assert len(decision.errors) == 0

    def test_confidential_data_blocking(self, temp_config):
        """Test that CONFIDENTIAL data blocks unsafe channels"""
        gateway = SecurityGateway(temp_config)

        decision = gateway.evaluate(
            command="draft",
            file_paths=["/projects/ABC/device_profile.json"],
            channel="whatsapp",
            user_id="test_user",
            session_id="test_session"
        )

        assert decision.classification == DataClassification.CONFIDENTIAL
        assert decision.allowed is False
        assert len(decision.errors) > 0


class TestAuditLogger:
    """Test suite for AuditLogger class"""

    @pytest.fixture
    def temp_log(self):
        """Create temporary audit log for testing"""
        temp_dir = tempfile.mkdtemp()
        log_path = Path(temp_dir) / 'audit.jsonl'

        yield str(log_path)

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_log_event(self, temp_log):
        """Test logging audit event"""
        logger = AuditLogger(temp_log)

        event = logger.log_event(
            event_type="execute",
            user_id="test_user",
            session_id="test_session",
            command="validate",
            classification="PUBLIC",
            llm_provider="anthropic",
            channel="file",
            allowed=True,
            success=True,
            duration_ms=1234
        )

        assert event.event_type == "execute"
        assert event.user_id == "test_user"
        assert event.command == "validate"
        assert event.allowed is True
        assert event.event_hash is not None

    def test_log_persistence(self, temp_log):
        """Test that events are persisted to file"""
        logger = AuditLogger(temp_log)

        logger.log_event(
            event_type="execute",
            user_id="user1",
            session_id="session1",
            command="research",
            classification="PUBLIC",
            llm_provider="ollama",
            channel="file",
            allowed=True
        )

        # Read log file
        with open(temp_log, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 1

        event = json.loads(lines[0])
        assert event['user_id'] == "user1"
        assert event['command'] == "research"

    def test_chain_integrity(self, temp_log):
        """Test event chain integrity (previous hash linking)"""
        logger = AuditLogger(temp_log)

        # Log first event
        event1 = logger.log_event(
            event_type="execute",
            user_id="user1",
            session_id="session1",
            command="research",
            classification="PUBLIC",
            llm_provider="ollama",
            channel="file",
            allowed=True
        )

        # Log second event
        event2 = logger.log_event(
            event_type="execute",
            user_id="user1",
            session_id="session1",
            command="analyze",
            classification="RESTRICTED",
            llm_provider="ollama",
            channel="file",
            allowed=True
        )

        # Second event should reference first event's hash
        assert event2.prev_event_hash == event1.event_hash

    def test_verify_integrity(self, temp_log):
        """Test audit log integrity verification"""
        logger = AuditLogger(temp_log)

        # Log some events
        for i in range(5):
            logger.log_event(
                event_type="execute",
                user_id=f"user{i}",
                session_id="session1",
                command="validate",
                classification="PUBLIC",
                llm_provider="ollama",
                channel="file",
                allowed=True
            )

        # Verify integrity
        results = logger.verify_integrity()

        assert results['valid'] is True
        assert results['total_events'] == 5
        assert results['verified_events'] == 5
        assert len(results['broken_chains']) == 0
        assert len(results['invalid_hashes']) == 0

    def test_query_events(self, temp_log):
        """Test querying audit events with filters"""
        logger = AuditLogger(temp_log)

        # Log events with different users
        logger.log_event(
            event_type="execute",
            user_id="alice",
            session_id="session1",
            command="research",
            classification="PUBLIC",
            llm_provider="ollama",
            channel="file",
            allowed=True
        )

        logger.log_event(
            event_type="execute",
            user_id="bob",
            session_id="session2",
            command="draft",
            classification="CONFIDENTIAL",
            llm_provider="ollama",
            channel="file",
            allowed=True
        )

        logger.log_event(
            event_type="execute",
            user_id="alice",
            session_id="session3",
            command="analyze",
            classification="RESTRICTED",
            llm_provider="ollama",
            channel="file",
            allowed=True
        )

        # Query Alice's events
        alice_events = logger.get_events(user_id="alice")
        assert len(alice_events) == 2
        assert all(e.user_id == "alice" for e in alice_events)

        # Query CONFIDENTIAL events
        confidential_events = logger.get_events(classification="CONFIDENTIAL")
        assert len(confidential_events) == 1
        assert confidential_events[0].command == "draft"

    def test_security_violation_logging(self, temp_log):
        """Test logging security violations"""
        logger = AuditLogger(temp_log)

        event = logger.log_event(
            event_type="security_violation",
            user_id="malicious_user",
            session_id="session1",
            command="draft",
            classification="CONFIDENTIAL",
            llm_provider="none",
            channel="whatsapp",
            allowed=False,
            violations=["CONFIDENTIAL data cannot use whatsapp channel"]
        )

        assert event.event_type == "security_violation"
        assert event.allowed is False
        assert len(event.violations) > 0


class TestIntegration:
    """Integration tests for security gateway + audit logger"""

    @pytest.fixture
    def temp_env(self):
        """Create temporary environment for integration testing"""
        temp_dir = tempfile.mkdtemp()

        config_path = Path(temp_dir) / 'security.toml'
        log_path = Path(temp_dir) / 'audit.jsonl'

        # Write config
        config_content = """
[security]
version = "1.0.0"
immutable = true

[data_classification]
public_patterns = ["*/openFDA/*"]
confidential_patterns = ["*/projects/*"]

[llm_providers]
local_preferred = true
require_local_for_confidential = true

[llm_providers.ollama]
enabled = true
endpoint = "http://localhost:11434"
models = ["llama2"]

[llm_providers.anthropic]
enabled = true
endpoint = "https://api.anthropic.com"
models = ["claude-opus-4.6"]

[communication]
public_channels = ["whatsapp", "file"]
restricted_channels = ["file"]
confidential_channels = ["file"]

[audit]
log_path = "{log_path}"
retention_days = 2555
""".format(log_path=log_path)

        config_path.write_text(config_content)
        os.chmod(config_path, 0o444)

        yield {
            'config_path': str(config_path),
            'log_path': str(log_path),
            'temp_dir': temp_dir
        }

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_full_evaluation_with_audit(self, temp_env):
        """Test complete evaluation with audit logging"""
        gateway = SecurityGateway(temp_env['config_path'])
        logger = AuditLogger(temp_env['log_path'])

        # Evaluate command
        decision = gateway.evaluate(
            command="research",
            file_paths=["/data/openFDA/predicates.json"],
            channel="file",
            user_id="test_user",
            session_id="test_session"
        )

        # Log audit event
        event = logger.log_event(
            event_type="execute",
            user_id=decision.audit_metadata['user_id'],
            session_id=decision.audit_metadata['session_id'],
            command=decision.audit_metadata['command'],
            classification=decision.classification.value,
            llm_provider=decision.llm_provider.value,
            channel=decision.audit_metadata['channel'],
            allowed=decision.allowed,
            warnings=decision.warnings
        )

        # Verify decision
        assert decision.allowed is True

        # Verify audit log
        events = logger.get_events(user_id="test_user")
        assert len(events) == 1
        assert events[0].command == "research"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
