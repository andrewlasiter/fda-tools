"""
Unit Tests for SecurityGateway (FDA-117)
=========================================

Validates the three-tier data classification and access control system
implemented in fda_tools.bridge.security_gateway:

  - DataClassifier: command-name lookup + content pattern matching
  - LLMRouter: provider selection and channel access control
  - SecurityGateway: end-to-end evaluate() + audit logging
  - SecurityDecision: immutable result object

Classification tiers:
  PUBLIC       — public FDA data, safe anywhere
  RESTRICTED   — derived intelligence, messaging channel warnings
  CONFIDENTIAL — draft submissions, K-numbers, blocked on messaging channels

Test count: 34
Target: pytest plugins/fda_tools/tests/test_fda117_security_gateway.py -v
"""

import pytest
from unittest.mock import MagicMock, call

from fda_tools.bridge.security_gateway import (
    Classification,
    DataClassifier,
    LLMRouter,
    SecurityDecision,
    SecurityGateway,
    _CONFIDENTIAL_COMMANDS,
    _PUBLIC_COMMANDS,
    _SECURE_CHANNELS,
    _MESSAGING_CHANNELS,
)


# ---------------------------------------------------------------------------
# TestClassificationConstants
# ---------------------------------------------------------------------------

class TestClassificationConstants:
    """Verify constant sets are populated as expected."""

    def test_confidential_commands_contains_draft(self):
        assert "draft" in _CONFIDENTIAL_COMMANDS

    def test_confidential_commands_contains_assemble(self):
        assert "assemble" in _CONFIDENTIAL_COMMANDS

    def test_public_commands_contains_research(self):
        assert "research" in _PUBLIC_COMMANDS

    def test_public_commands_contains_batchfetch(self):
        assert "batchfetch" in _PUBLIC_COMMANDS

    def test_secure_channels_contains_file(self):
        assert "file" in _SECURE_CHANNELS

    def test_messaging_channels_contains_whatsapp(self):
        assert "whatsapp" in _MESSAGING_CHANNELS

    def test_classification_more_sensitive(self):
        assert Classification.more_sensitive("PUBLIC", "CONFIDENTIAL") == "CONFIDENTIAL"
        assert Classification.more_sensitive("RESTRICTED", "PUBLIC") == "RESTRICTED"
        assert Classification.more_sensitive("PUBLIC", "PUBLIC") == "PUBLIC"


# ---------------------------------------------------------------------------
# TestDataClassifier
# ---------------------------------------------------------------------------

class TestDataClassifier:
    """Tests for DataClassifier.classify_command(), classify_content(), classify()."""

    @pytest.fixture(autouse=True)
    def classifier(self):
        self.clf = DataClassifier()

    # --- classify_command ---

    def test_draft_command_is_confidential(self):
        assert self.clf.classify_command("draft") == Classification.CONFIDENTIAL

    def test_assemble_command_is_confidential(self):
        assert self.clf.classify_command("assemble") == Classification.CONFIDENTIAL

    def test_pre_check_command_is_confidential(self):
        assert self.clf.classify_command("pre-check") == Classification.CONFIDENTIAL

    def test_research_command_is_public(self):
        assert self.clf.classify_command("research") == Classification.PUBLIC

    def test_batchfetch_command_is_public(self):
        assert self.clf.classify_command("batchfetch") == Classification.PUBLIC

    def test_validate_command_is_public(self):
        assert self.clf.classify_command("validate") == Classification.PUBLIC

    def test_unknown_command_defaults_to_restricted(self):
        assert self.clf.classify_command("frobnicate") == Classification.RESTRICTED

    # --- classify_content ---

    def test_k_number_in_content_is_confidential(self):
        assert self.clf.classify_content("K240001") == Classification.CONFIDENTIAL

    def test_pma_number_in_content_is_confidential(self):
        assert self.clf.classify_content("PMA P123456") == Classification.CONFIDENTIAL

    def test_device_profile_json_is_confidential(self):
        assert self.clf.classify_content("device_profile.json loaded") == Classification.CONFIDENTIAL

    def test_draft_filename_is_confidential(self):
        assert self.clf.classify_content("draft_cover-letter.md") == Classification.CONFIDENTIAL

    def test_review_json_is_confidential(self):
        assert self.clf.classify_content("review.json data") == Classification.CONFIDENTIAL

    def test_analysis_report_is_restricted(self):
        assert self.clf.classify_content("Gap Analysis Report") == Classification.RESTRICTED

    def test_plain_text_is_public(self):
        assert self.clf.classify_content("list devices in product code DQY") == Classification.PUBLIC

    # --- classify (combined) ---

    def test_public_command_with_confidential_content_escalates(self):
        """PUBLIC command + K-number in args → CONFIDENTIAL."""
        result = self.clf.classify("research", args="K240001 K230002")
        assert result == Classification.CONFIDENTIAL

    def test_confidential_command_with_public_content_stays_confidential(self):
        """CONFIDENTIAL command + benign args cannot be downgraded."""
        result = self.clf.classify("draft", args="--section device-description")
        assert result == Classification.CONFIDENTIAL

    def test_unknown_command_with_analysis_content_is_restricted(self):
        result = self.clf.classify("unknown-cmd", context="Gap Analysis Report")
        assert result == Classification.RESTRICTED

    def test_public_command_with_public_content_stays_public(self):
        result = self.clf.classify("research", args="--topic biocompatibility")
        assert result == Classification.PUBLIC


# ---------------------------------------------------------------------------
# TestLLMRouter
# ---------------------------------------------------------------------------

class TestLLMRouter:
    """Tests for LLMRouter.get_provider(), is_channel_allowed(), get_warnings()."""

    @pytest.fixture(autouse=True)
    def router(self):
        self.router = LLMRouter()

    # --- get_provider ---

    def test_public_prefers_anthropic(self):
        result = self.router.get_provider(Classification.PUBLIC, ["anthropic", "ollama"])
        assert result == "anthropic"

    def test_confidential_requires_ollama(self):
        result = self.router.get_provider(Classification.CONFIDENTIAL, ["anthropic", "openai", "ollama"])
        assert result == "ollama"

    def test_confidential_without_ollama_returns_none(self):
        result = self.router.get_provider(Classification.CONFIDENTIAL, ["anthropic", "openai"])
        assert result == "none"

    def test_restricted_prefers_ollama(self):
        result = self.router.get_provider(Classification.RESTRICTED, ["anthropic", "ollama"])
        assert result == "ollama"

    def test_no_providers_returns_none(self):
        result = self.router.get_provider(Classification.PUBLIC, [])
        assert result == "none"

    # --- is_channel_allowed ---

    def test_public_on_whatsapp_is_allowed(self):
        assert self.router.is_channel_allowed(Classification.PUBLIC, "whatsapp") is True

    def test_restricted_on_telegram_is_allowed(self):
        assert self.router.is_channel_allowed(Classification.RESTRICTED, "telegram") is True

    def test_confidential_on_whatsapp_is_blocked(self):
        assert self.router.is_channel_allowed(Classification.CONFIDENTIAL, "whatsapp") is False

    def test_confidential_on_file_is_allowed(self):
        assert self.router.is_channel_allowed(Classification.CONFIDENTIAL, "file") is True

    def test_confidential_on_cli_is_allowed(self):
        assert self.router.is_channel_allowed(Classification.CONFIDENTIAL, "cli") is True

    # --- get_warnings ---

    def test_restricted_on_slack_produces_warning(self):
        warnings = self.router.get_warnings(Classification.RESTRICTED, "slack")
        assert len(warnings) == 1
        assert "RESTRICTED" in warnings[0]

    def test_public_on_slack_no_warning(self):
        warnings = self.router.get_warnings(Classification.PUBLIC, "slack")
        assert warnings == []

    def test_confidential_on_discord_produces_block_warning(self):
        warnings = self.router.get_warnings(Classification.CONFIDENTIAL, "discord")
        assert len(warnings) == 1
        assert "CONFIDENTIAL" in warnings[0]

    def test_confidential_on_file_no_warning(self):
        warnings = self.router.get_warnings(Classification.CONFIDENTIAL, "file")
        assert warnings == []


# ---------------------------------------------------------------------------
# TestSecurityGateway
# ---------------------------------------------------------------------------

class TestSecurityGateway:
    """Tests for SecurityGateway.evaluate() and audit logging."""

    @pytest.fixture(autouse=True)
    def gateway(self):
        self.audit_calls = []
        self.gw = SecurityGateway(
            audit_log_func=lambda event, data: self.audit_calls.append((event, data))
        )

    def test_evaluate_public_command_on_file_is_allowed(self):
        decision = self.gw.evaluate("research", channel="file")
        assert decision.allowed is True
        assert decision.classification == Classification.PUBLIC

    def test_evaluate_confidential_on_whatsapp_is_blocked(self):
        decision = self.gw.evaluate("draft", channel="whatsapp")
        assert decision.allowed is False
        assert decision.should_block is True

    def test_evaluate_confidential_on_file_is_allowed(self):
        decision = self.gw.evaluate("draft", channel="file")
        assert decision.allowed is True

    def test_evaluate_returns_correct_classification(self):
        decision = self.gw.evaluate("assemble", channel="file")
        assert decision.classification == Classification.CONFIDENTIAL

    def test_evaluate_returns_llm_provider(self):
        decision = self.gw.evaluate(
            "research", channel="file",
            available_providers=["anthropic"]
        )
        assert decision.llm_provider == "anthropic"

    def test_evaluate_confidential_no_ollama_provider_is_none(self):
        decision = self.gw.evaluate(
            "draft", channel="file",
            available_providers=["anthropic", "openai"]
        )
        assert decision.llm_provider == "none"

    def test_evaluate_calls_audit_log(self):
        self.gw.evaluate("research", channel="file", user_id="u1", session_id="s1")
        assert len(self.audit_calls) == 1
        event, data = self.audit_calls[0]
        assert event == "security_decision"
        assert data["command"] == "research"
        assert data["user_id"] == "u1"

    def test_evaluate_audit_log_includes_classification(self):
        self.gw.evaluate("draft", channel="file")
        _, data = self.audit_calls[0]
        assert data["classification"] == Classification.CONFIDENTIAL

    def test_evaluate_restricted_on_messaging_has_warning(self):
        decision = self.gw.evaluate("unknown-cmd", channel="slack")
        assert len(decision.warnings) >= 1
        assert any("RESTRICTED" in w for w in decision.warnings)

    def test_security_decision_is_frozen(self):
        """SecurityDecision is a frozen dataclass — mutating raises."""
        decision = self.gw.evaluate("research", channel="file")
        with pytest.raises(Exception):
            decision.allowed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestSecurityDecision
# ---------------------------------------------------------------------------

class TestSecurityDecision:
    """Tests for SecurityDecision dataclass."""

    def test_should_block_true_when_not_allowed(self):
        d = SecurityDecision(allowed=False, classification="CONFIDENTIAL", llm_provider="none")
        assert d.should_block is True

    def test_should_block_false_when_allowed(self):
        d = SecurityDecision(allowed=True, classification="PUBLIC", llm_provider="anthropic")
        assert d.should_block is False

    def test_default_warnings_is_empty_list(self):
        d = SecurityDecision(allowed=True, classification="PUBLIC", llm_provider="anthropic")
        assert d.warnings == []
