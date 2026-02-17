"""
Security Gateway - Immutable Security Enforcement for FDA Tools

This module provides mandatory pre-execution security checks for all FDA commands.
It enforces:
1. 3-tier data classification (PUBLIC/RESTRICTED/CONFIDENTIAL)
2. LLM provider routing based on data sensitivity
3. Communication protocol whitelist enforcement
4. Audit logging (append-only)

CRITICAL: Security policies are IMMUTABLE and cannot be modified by agents.
Configuration is read from ~/.claude/fda-tools.security.toml (file mode 444).

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import sys
import re
import toml
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class DataClassification(str, Enum):
    """Data sensitivity classification levels"""
    PUBLIC = "PUBLIC"           # FDA databases, safe for any LLM
    RESTRICTED = "RESTRICTED"   # Derived intelligence, warnings required
    CONFIDENTIAL = "CONFIDENTIAL"  # Company documents, local LLM ONLY


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"           # Local LLM (Llama 2, Mistral, etc.)
    ANTHROPIC = "anthropic"     # Claude (cloud)
    OPENAI = "openai"           # GPT (cloud)
    NONE = "none"               # No provider available


@dataclass
class SecurityPolicy:
    """Immutable security policy loaded from config"""
    public_patterns: List[str]
    confidential_patterns: List[str]
    local_preferred: bool
    require_local_for_confidential: bool
    ollama_endpoint: str
    ollama_models: List[str]
    anthropic_endpoint: str
    anthropic_models: List[str]
    public_channels: List[str]
    restricted_channels: List[str]
    confidential_channels: List[str]
    audit_log_path: str
    audit_retention_days: int


@dataclass
class SecurityDecision:
    """Result of security evaluation"""
    allowed: bool
    classification: DataClassification
    llm_provider: LLMProvider
    channel_allowed: bool
    warnings: List[str]
    errors: List[str]
    audit_metadata: Dict


class SecurityGateway:
    """
    Mandatory security gateway for all FDA command execution.

    This class enforces immutable security policies that cannot be
    modified by agents or users during execution.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize security gateway.

        Args:
            config_path: Path to security config (default: ~/.claude/fda-tools.security.toml)
        """
        if config_path is None:
            config_path = os.path.expanduser("~/.claude/fda-tools.security.toml")

        self.config_path = Path(config_path)
        self.policy = self._load_policy()
        self._verify_immutable()

    def _load_policy(self) -> SecurityPolicy:
        """
        Load security policy from TOML config.

        Returns:
            SecurityPolicy object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Security config not found: {self.config_path}\n"
                f"Run: cp {self.config_path}.template {self.config_path}"
            )

        try:
            config = toml.load(self.config_path)
        except Exception as e:
            raise ValueError(f"Invalid security config: {e}")

        # Validate required sections
        required = ['security', 'data_classification', 'llm_providers', 'communication', 'audit']
        for section in required:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")

        # Extract policy
        dc = config['data_classification']
        llm = config['llm_providers']
        comm = config['communication']
        audit = config['audit']

        return SecurityPolicy(
            public_patterns=dc.get('public_patterns', []),
            confidential_patterns=dc.get('confidential_patterns', []),
            local_preferred=llm.get('local_preferred', True),
            require_local_for_confidential=llm.get('require_local_for_confidential', True),
            ollama_endpoint=llm.get('ollama', {}).get('endpoint', 'http://localhost:11434'),
            ollama_models=llm.get('ollama', {}).get('models', []),
            anthropic_endpoint=llm.get('anthropic', {}).get('endpoint', 'https://api.anthropic.com'),
            anthropic_models=llm.get('anthropic', {}).get('models', []),
            public_channels=comm.get('public_channels', []),
            restricted_channels=comm.get('restricted_channels', []),
            confidential_channels=comm.get('confidential_channels', []),
            audit_log_path=os.path.expanduser(audit.get('log_path', '~/.claude/fda-tools.audit.jsonl')),
            audit_retention_days=audit.get('retention_days', 2555)
        )

    def _verify_immutable(self):
        """
        Verify config file is read-only (immutable).

        Raises:
            PermissionError: If file is writable
        """
        stat_info = self.config_path.stat()
        mode = stat_info.st_mode & 0o777

        # Should be 444 (read-only for all)
        if mode != 0o444:
            raise PermissionError(
                f"Security config is not immutable: {self.config_path}\n"
                f"Current mode: {oct(mode)}, expected: 0o444\n"
                f"Run: chmod 444 {self.config_path}"
            )

    def classify_data(self, file_paths: List[str], command: str) -> DataClassification:
        """
        Classify data sensitivity based on file paths and command.

        Args:
            file_paths: List of file paths being accessed
            command: FDA command being executed

        Returns:
            DataClassification (PUBLIC, RESTRICTED, or CONFIDENTIAL)
        """
        # Check for CONFIDENTIAL patterns first (highest sensitivity)
        for path in file_paths:
            for pattern in self.policy.confidential_patterns:
                if self._match_pattern(path, pattern):
                    return DataClassification.CONFIDENTIAL

        # Check for PUBLIC patterns
        has_public = False
        for path in file_paths:
            for pattern in self.policy.public_patterns:
                if self._match_pattern(path, pattern):
                    has_public = True
                    break

        # Commands that generate derived intelligence are RESTRICTED
        restricted_commands = [
            'analyze', 'compare-se', 'consistency', 'pre-check',
            'review-simulator', 'draft', 'assemble'
        ]

        # If command is restricted, classification is at least RESTRICTED
        if command in restricted_commands:
            return DataClassification.RESTRICTED

        # If all paths are PUBLIC and command is not restricted, then PUBLIC
        if has_public:
            return DataClassification.PUBLIC

        # Default to RESTRICTED for safety
        return DataClassification.RESTRICTED

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """
        Match file path against glob-like pattern.

        Args:
            path: File path to check
            pattern: Pattern with wildcards (*, **)

        Returns:
            True if path matches pattern
        """
        import fnmatch

        # Normalize paths
        path = path.replace('\\', '/')
        pattern = pattern.replace('\\', '/')

        # Handle ** (recursive wildcard)
        if '**' in pattern:
            # Convert ** to match any number of directories
            # Pattern: */projects/** -> any path containing /projects/
            pattern_parts = pattern.split('**')
            if len(pattern_parts) == 2:
                before, after = pattern_parts
                before = before.rstrip('/')
                after = after.lstrip('/')

                # Check if path contains the before part and after part
                if before and not fnmatch.fnmatch(path, f'{before}*'):
                    return False
                if after and not fnmatch.fnmatch(path, f'*{after}'):
                    return False
                return True

        # Use fnmatch for simple patterns with *
        # For patterns like */openFDA/*, we need to match anywhere in path
        if pattern.startswith('*/'):
            # Pattern like */openFDA/* should match /data/openFDA/file.json
            pattern_suffix = pattern[2:]  # Remove leading */
            # Check if pattern matches anywhere in the path
            return fnmatch.fnmatch(path, f'*/{pattern_suffix}')
        else:
            return fnmatch.fnmatch(path, pattern)

    def detect_llm_providers(self) -> List[LLMProvider]:
        """
        Detect available LLM providers via health checks.

        Returns:
            List of available LLMProvider values
        """
        available = []

        # Check Ollama (local)
        try:
            response = requests.get(
                f"{self.policy.ollama_endpoint}/api/tags",
                timeout=2
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                if any(m['name'].startswith(model) for m in models for model in self.policy.ollama_models):
                    available.append(LLMProvider.OLLAMA)
        except Exception as e:
            # Expected: Ollama may not be running
            print(f"Info: Ollama provider detection failed: {e}", file=sys.stderr)

        # Check Anthropic (cloud) - just check if API key exists
        if os.environ.get('ANTHROPIC_API_KEY'):
            available.append(LLMProvider.ANTHROPIC)

        # Check OpenAI (cloud) - just check if API key exists
        if os.environ.get('OPENAI_API_KEY'):
            available.append(LLMProvider.OPENAI)

        return available

    def select_llm_provider(
        self,
        classification: DataClassification,
        available_providers: List[LLMProvider]
    ) -> Tuple[LLMProvider, List[str]]:
        """
        Select LLM provider based on data classification and availability.

        Args:
            classification: Data sensitivity level
            available_providers: List of available providers

        Returns:
            Tuple of (selected_provider, warnings)

        Raises:
            ValueError: If no suitable provider available for CONFIDENTIAL data
        """
        warnings = []

        # CONFIDENTIAL: Local LLM ONLY
        if classification == DataClassification.CONFIDENTIAL:
            if LLMProvider.OLLAMA in available_providers:
                return LLMProvider.OLLAMA, warnings
            else:
                raise ValueError(
                    "CONFIDENTIAL data requires local LLM (Ollama) but none available.\n"
                    f"Start Ollama: ollama serve\n"
                    f"Pull model: ollama pull {self.policy.ollama_models[0] if self.policy.ollama_models else 'llama2'}"
                )

        # RESTRICTED: Prefer local, warn if cloud
        if classification == DataClassification.RESTRICTED:
            if self.policy.local_preferred and LLMProvider.OLLAMA in available_providers:
                return LLMProvider.OLLAMA, warnings

            # Fall back to cloud with warning
            if LLMProvider.ANTHROPIC in available_providers:
                warnings.append(
                    "⚠️ RESTRICTED data using cloud LLM (Anthropic Claude). "
                    "For maximum privacy, install Ollama for local processing."
                )
                return LLMProvider.ANTHROPIC, warnings

            if LLMProvider.OPENAI in available_providers:
                warnings.append(
                    "⚠️ RESTRICTED data using cloud LLM (OpenAI GPT). "
                    "For maximum privacy, install Ollama for local processing."
                )
                return LLMProvider.OPENAI, warnings

            if LLMProvider.OLLAMA in available_providers:
                return LLMProvider.OLLAMA, warnings

            raise ValueError("No LLM provider available for RESTRICTED data")

        # PUBLIC: Any available LLM
        if available_providers:
            # Prefer cloud for PUBLIC data (faster, better quality)
            if LLMProvider.ANTHROPIC in available_providers:
                return LLMProvider.ANTHROPIC, warnings
            if LLMProvider.OPENAI in available_providers:
                return LLMProvider.OPENAI, warnings
            if LLMProvider.OLLAMA in available_providers:
                return LLMProvider.OLLAMA, warnings

        raise ValueError("No LLM provider available")

    def validate_channel(
        self,
        classification: DataClassification,
        channel: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate if channel is allowed for data classification.

        Args:
            classification: Data sensitivity level
            channel: Output channel (whatsapp, telegram, slack, discord, webhook, file)

        Returns:
            Tuple of (allowed, warnings)
        """
        warnings = []

        if classification == DataClassification.CONFIDENTIAL:
            if channel not in self.policy.confidential_channels:
                return False, [
                    f"❌ CONFIDENTIAL data cannot use '{channel}' channel. "
                    f"Allowed: {', '.join(self.policy.confidential_channels)}"
                ]

        elif classification == DataClassification.RESTRICTED:
            if channel not in self.policy.restricted_channels:
                warnings.append(
                    f"⚠️ RESTRICTED data on '{channel}' channel. "
                    f"Recommended: {', '.join(self.policy.restricted_channels)}"
                )

        return True, warnings

    def evaluate(
        self,
        command: str,
        file_paths: List[str],
        channel: str,
        user_id: str,
        session_id: str
    ) -> SecurityDecision:
        """
        Perform complete security evaluation for command execution.

        Args:
            command: FDA command to execute
            file_paths: File paths being accessed
            channel: Output channel
            user_id: User identifier
            session_id: Session identifier

        Returns:
            SecurityDecision with full evaluation results
        """
        warnings = []
        errors = []

        # Step 1: Classify data
        classification = self.classify_data(file_paths, command)

        # Step 2: Detect available LLM providers
        available_providers = self.detect_llm_providers()

        # Step 3: Select LLM provider
        try:
            llm_provider, provider_warnings = self.select_llm_provider(
                classification, available_providers
            )
            warnings.extend(provider_warnings)
        except ValueError as e:
            errors.append(str(e))
            llm_provider = LLMProvider.NONE

        # Step 4: Validate channel
        channel_allowed, channel_warnings = self.validate_channel(classification, channel)
        warnings.extend(channel_warnings)

        if not channel_allowed:
            errors.extend(channel_warnings)

        # Step 5: Final decision
        allowed = len(errors) == 0

        # Step 6: Audit metadata
        audit_metadata = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'session_id': session_id,
            'command': command,
            'classification': classification.value,
            'llm_provider': llm_provider.value,
            'channel': channel,
            'allowed': allowed,
            'file_paths': file_paths,
            'warnings_count': len(warnings),
            'errors_count': len(errors)
        }

        return SecurityDecision(
            allowed=allowed,
            classification=classification,
            llm_provider=llm_provider,
            channel_allowed=channel_allowed,
            warnings=warnings,
            errors=errors,
            audit_metadata=audit_metadata
        )

    def get_config_hash(self) -> str:
        """
        Get SHA256 hash of current security config.

        Returns:
            Hex digest of config file
        """
        with open(self.config_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()


# Global singleton instance
_gateway_instance: Optional[SecurityGateway] = None


def get_security_gateway(config_path: Optional[str] = None) -> SecurityGateway:
    """
    Get global SecurityGateway instance (singleton pattern).

    Args:
        config_path: Optional path to security config

    Returns:
        SecurityGateway instance
    """
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = SecurityGateway(config_path)
    return _gateway_instance
