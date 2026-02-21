"""
Security Gateway for FDA Tools Bridge Server (FDA-117)
=======================================================

Implements data classification, LLM routing, access control, and audit
logging for bridge sessions. Enforces the three-tier sensitivity model:

  PUBLIC      - FDA databases, published summaries, cleared device data.
                Safe for any LLM and any messaging channel.
  RESTRICTED  - Derived intelligence, analysis, comparison reports.
                Cloud LLMs allowed with user warnings on messaging channels.
  CONFIDENTIAL - Draft submissions, K-numbers, device specs, company data.
                Only on-premise LLM (Ollama) or file/CLI channel permitted.

Architecture:
  DataClassifier  — Pattern-based classification of commands and content.
  LLMRouter       — Provider selection and channel access control.
  SecurityGateway — Orchestrates classifier + router + audit logging.
  SecurityDecision — Immutable result object returned from evaluate().

Usage:
    gateway = SecurityGateway(audit_log_func=audit_log_entry)
    decision = gateway.evaluate(
        command="draft",
        args="--project my-device --section device-description",
        channel="whatsapp",
        user_id="user-123",
        session_id="session-abc",
    )
    if decision.should_block:
        return error("CONFIDENTIAL data not permitted on whatsapp channel")
    # Proceed with decision.llm_provider
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Classification levels
# ---------------------------------------------------------------------------

class Classification:
    """Constants for data sensitivity tiers."""
    PUBLIC = "PUBLIC"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"

    # Ordering for comparison (higher index = more sensitive)
    _ORDER = [PUBLIC, RESTRICTED, CONFIDENTIAL]

    @classmethod
    def more_sensitive(cls, a: str, b: str) -> str:
        """Return the more sensitive of two classification strings."""
        idx_a = cls._ORDER.index(a) if a in cls._ORDER else 0
        idx_b = cls._ORDER.index(b) if b in cls._ORDER else 0
        return cls._ORDER[max(idx_a, idx_b)]


# ---------------------------------------------------------------------------
# Data Classifier
# ---------------------------------------------------------------------------

# Commands that always access CONFIDENTIAL project data
_CONFIDENTIAL_COMMANDS: frozenset = frozenset(
    {
        "draft",
        "assemble",
        "export",
        "consistency",
        "pre-check",
        "review",
        "import",
        "pipeline",
        "data-pipeline",
        "submission-outline",
        "test-plan",
        "compare-se",
        "traceability",
        "pccp",
        "presub",
    }
)

# Commands that access only PUBLIC FDA data
_PUBLIC_COMMANDS: frozenset = frozenset(
    {
        "research",
        "safety",
        "warnings",
        "trials",
        "guidance",
        "standards",
        "validate",
        "udi",
        "pma-search",
        "pma-compare",
        "pma-intelligence",
        "pma-timeline",
        "predict-review-time",
        "approval-probability",
        "competitive-dashboard",
        "search-predicates",
        "smart-predicates",
        "batchfetch",
        "lineage",
        "pathway",
        "portfolio",
        "status",
        "monitor",
    }
)

# Content patterns indicating CONFIDENTIAL data
_CONFIDENTIAL_CONTENT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bK\d{6}\b"),                      # FDA K-numbers (e.g., K240001)
    re.compile(r"\bP\d{6}\b"),                      # FDA PMA numbers
    re.compile(r"\bP\d{6}/[A-Z]\d{3}\b"),           # PMA supplements
    re.compile(r"device[-_]profile\.json", re.I),   # Project device profile
    re.compile(r"review\.json", re.I),              # Predicate review data
    re.compile(r"draft[-_][\w-]+\.md", re.I),         # Draft section files
    re.compile(r"\b[Cc]ompany\s+[Cc]onfidential\b"),
    re.compile(r"\b[Pp]roprietary\s+[Dd]ata\b"),
    re.compile(r"\b510\(k\)\s+[Ss]ubmission\b"),
    re.compile(r"\b[Ss]ubject\s+[Dd]evice\b"),
]

# Content patterns indicating RESTRICTED data
_RESTRICTED_CONTENT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b[Aa]nalysis\s+[Rr]eport\b"),
    re.compile(r"\b[Cc]ompetitive\s+[Ii]ntelligence\b"),
    re.compile(r"\b[Ss]trategic\s+[Rr]ecommendation\b"),
    re.compile(r"\b[Pp]redicate\s+[Cc]omparison\b"),
    re.compile(r"\b[Gg]ap\s+[Aa]nalysis\b"),
    re.compile(r"\b[Ss]ubmission\s+[Rr]eadiness\b"),
    re.compile(r"intelligence[-_]report\.md", re.I),
    re.compile(r"quality[-_]report\.md", re.I),
]


class DataClassifier:
    """
    Classifies data sensitivity based on command name and content patterns.

    Classification precedence (most restrictive wins):
      1. Command name lookup (CONFIDENTIAL_COMMANDS / PUBLIC_COMMANDS sets)
      2. Content pattern scan (K-numbers, device specs → CONFIDENTIAL etc.)
      3. Default: RESTRICTED for unknown commands without content signals
    """

    def classify_command(self, command: str) -> str:
        """Return classification based on command name alone.

        Args:
            command: FDA command name (e.g., "draft", "research").

        Returns:
            ``Classification.CONFIDENTIAL``, ``RESTRICTED``, or ``PUBLIC``.
        """
        name = command.lower().strip()
        if name in _CONFIDENTIAL_COMMANDS:
            return Classification.CONFIDENTIAL
        if name in _PUBLIC_COMMANDS:
            return Classification.PUBLIC
        return Classification.RESTRICTED  # Unknown commands default to RESTRICTED

    def classify_content(self, content: str) -> str:
        """Return classification based on content pattern analysis.

        Args:
            content: Free-text content (args, context, filenames).

        Returns:
            ``Classification.CONFIDENTIAL``, ``RESTRICTED``, or ``PUBLIC``.
        """
        for pattern in _CONFIDENTIAL_CONTENT_PATTERNS:
            if pattern.search(content):
                return Classification.CONFIDENTIAL
        for pattern in _RESTRICTED_CONTENT_PATTERNS:
            if pattern.search(content):
                return Classification.RESTRICTED
        return Classification.PUBLIC

    def classify(
        self,
        command: str,
        args: str = "",
        context: str = "",
    ) -> str:
        """Classify a request combining command, args, and context.

        Classification can only escalate (PUBLIC → RESTRICTED → CONFIDENTIAL)
        — a CONFIDENTIAL command cannot be downgraded by benign content.

        Args:
            command: FDA command name.
            args: Command arguments string.
            context: Additional request context.

        Returns:
            The most sensitive applicable ``Classification`` level.
        """
        cmd_level = self.classify_command(command)
        combined_text = f"{args} {context}".strip()
        if combined_text:
            content_level = self.classify_content(combined_text)
            return Classification.more_sensitive(cmd_level, content_level)
        return cmd_level


# ---------------------------------------------------------------------------
# LLM Router
# ---------------------------------------------------------------------------

# Channels considered secure (local process or file output)
_SECURE_CHANNELS: frozenset = frozenset({"file", "cli", "local", "terminal"})

# Messaging channels (non-secure, external)
_MESSAGING_CHANNELS: frozenset = frozenset(
    {"whatsapp", "telegram", "slack", "discord", "webhook", "teams", "sms"}
)


class LLMRouter:
    """
    Routes requests to the appropriate LLM provider based on data sensitivity.

    Provider priority by tier:
      PUBLIC      → anthropic → openai → ollama → none
      RESTRICTED  → ollama → anthropic → openai → none
      CONFIDENTIAL → ollama → none   (local-only)
    """

    def get_provider(
        self,
        classification: str,
        available_providers: Optional[List[str]] = None,
    ) -> str:
        """Select LLM provider for the given classification.

        Args:
            classification: One of ``Classification.*`` constants.
            available_providers: Providers known to be available. If ``None``,
                reads environment variables (``ANTHROPIC_API_KEY``, etc.).

        Returns:
            Provider name string or ``"none"`` if no suitable provider found.
        """
        if available_providers is None:
            available_providers = self._detect_available_providers()

        if classification == Classification.CONFIDENTIAL:
            # CONFIDENTIAL: on-premise only
            return "ollama" if "ollama" in available_providers else "none"

        if classification == Classification.RESTRICTED:
            # RESTRICTED: prefer local, then cloud
            for provider in ("ollama", "anthropic", "openai"):
                if provider in available_providers:
                    return provider
            return "none"

        # PUBLIC: prefer cloud for best performance
        for provider in ("anthropic", "openai", "ollama"):
            if provider in available_providers:
                return provider
        return "none"

    def is_channel_allowed(self, classification: str, channel: str) -> bool:
        """Return whether a channel is permitted for the given classification.

        Args:
            classification: Data sensitivity level.
            channel: Request channel identifier.

        Returns:
            ``True`` if the request should be allowed, ``False`` to block.
        """
        if classification in (Classification.PUBLIC, Classification.RESTRICTED):
            return True
        # CONFIDENTIAL: only on secure channels
        return channel in _SECURE_CHANNELS

    def get_warnings(self, classification: str, channel: str) -> List[str]:
        """Return warning messages for the classification/channel combination.

        Args:
            classification: Data sensitivity level.
            channel: Request channel identifier.

        Returns:
            List of warning strings (may be empty).
        """
        warnings: List[str] = []

        if classification == Classification.RESTRICTED and channel in _MESSAGING_CHANNELS:
            warnings.append(
                f"RESTRICTED data on '{channel}' channel. "
                "Verify output does not contain sensitive company information "
                "before sharing with external parties."
            )

        if classification == Classification.CONFIDENTIAL and channel not in _SECURE_CHANNELS:
            warnings.append(
                f"CONFIDENTIAL data blocked on '{channel}' channel. "
                "Use file output or a local terminal for confidential operations."
            )

        return warnings

    @staticmethod
    def _detect_available_providers() -> List[str]:
        """Detect available LLM providers from environment variables."""
        providers: List[str] = []
        if os.getenv("ANTHROPIC_API_KEY"):
            providers.append("anthropic")
        if os.getenv("OPENAI_API_KEY"):
            providers.append("openai")
        providers.append("ollama")  # Always listed (may not be running)
        return providers


# ---------------------------------------------------------------------------
# Security Decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SecurityDecision:
    """Immutable result of a security evaluation.

    Attributes:
        allowed: Whether the request is permitted to proceed.
        classification: Data sensitivity level assigned by ``DataClassifier``.
        llm_provider: Recommended LLM provider from ``LLMRouter``.
        warnings: List of warning strings for the caller to surface to users.
    """

    allowed: bool
    classification: str
    llm_provider: str
    warnings: List[str] = field(default_factory=list)

    @property
    def should_block(self) -> bool:
        """``True`` if the request must be blocked (not ``allowed``)."""
        return not self.allowed


# ---------------------------------------------------------------------------
# Security Gateway
# ---------------------------------------------------------------------------

class SecurityGateway:
    """
    Orchestrates data classification, LLM routing, and access control.

    Each call to :meth:`evaluate` produces a :class:`SecurityDecision`
    that the bridge server uses to allow/block the request and select
    the appropriate LLM provider.

    All classification decisions are audit-logged for compliance.

    Args:
        audit_log_func: Optional callable ``(event_type, data_dict)`` for
            audit logging. Defaults to a no-op if not provided.
    """

    def __init__(
        self,
        audit_log_func: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self.classifier = DataClassifier()
        self.router = LLMRouter()
        self._audit_log: Callable = audit_log_func or (lambda *_a, **_k: None)

    def evaluate(
        self,
        command: str,
        args: str = "",
        channel: str = "file",
        user_id: str = "",
        session_id: str = "",
        context: str = "",
        available_providers: Optional[List[str]] = None,
    ) -> SecurityDecision:
        """Evaluate a command request and return a security decision.

        Steps:
          1. Classify data sensitivity (command + content patterns).
          2. Check channel access permissions.
          3. Select appropriate LLM provider.
          4. Build warning list.
          5. Audit log the decision.

        Args:
            command: FDA command name (e.g., "draft", "research").
            args: Command argument string.
            channel: Output channel (e.g., "file", "whatsapp", "slack").
            user_id: User identifier for audit trail.
            session_id: Session identifier for audit trail.
            context: Additional context string for content classification.
            available_providers: Override provider detection (for testing).

        Returns:
            :class:`SecurityDecision` with ``allowed``, ``classification``,
            ``llm_provider``, and ``warnings``.
        """
        classification = self.classifier.classify(command, args, context)
        allowed = self.router.is_channel_allowed(classification, channel)
        warnings = self.router.get_warnings(classification, channel)
        llm_provider = self.router.get_provider(classification, available_providers)

        self._audit_log(
            "security_decision",
            {
                "command": command,
                "classification": classification,
                "channel": channel,
                "allowed": allowed,
                "llm_provider": llm_provider,
                "warnings_count": len(warnings),
                "user_id": user_id,
                "session_id": session_id,
            },
        )

        return SecurityDecision(
            allowed=allowed,
            classification=classification,
            llm_provider=llm_provider,
            warnings=warnings,
        )
