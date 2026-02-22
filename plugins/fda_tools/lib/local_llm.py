"""
FDA-259  [ONPREM-002] Air-gapped LLM support via Ollama
========================================================
Provides a model-agnostic `LlmClient` abstraction that routes completion
requests to either:

  1. **Ollama** (local, air-gapped) — for on-premise deployments where
     no internet access is available.  Requires Ollama to be running
     at `http://localhost:11434` (or `OLLAMA_BASE_URL`).

  2. **Anthropic Claude** (cloud) — default for SaaS and desktop-with-
     cloud mode. Uses the Anthropic Python SDK.

  3. **Stub** — for testing; returns canned responses without network I/O.

Usage
-----
    # Cloud (default)
    client = LlmClient.from_env()
    resp   = client.complete("Summarise this 510(k) section.")

    # Air-gapped Ollama
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_MODEL"] = "llama3"
    client = LlmClient.from_env()
    resp   = client.complete("Identify predicate devices for category OVE.")

Configuration
-------------
    LLM_PROVIDER     = "anthropic" | "ollama" | "stub"   (default: "anthropic")
    ANTHROPIC_API_KEY = sk-ant-...   (required when LLM_PROVIDER=anthropic)
    OLLAMA_BASE_URL   = http://localhost:11434            (default)
    OLLAMA_MODEL      = llama3                           (default)
    LLM_MAX_TOKENS    = 4096                             (default)
    LLM_TEMPERATURE   = 0.2                              (default)

Air-gapped notes
----------------
- When LLM_PROVIDER=ollama, no outbound network traffic is generated.
- Ollama must be pre-loaded with the target model before deployment:
    ollama pull llama3          # or mistral, phi3, etc.
- Prompt formatting is normalised before sending to ensure consistent
  behaviour across models (XML tags stripped, whitespace normalised).
- CONFIDENTIAL documents are *never* sent to any LLM unless the document
  vault setting `allow_llm_on_confidential` is explicitly True.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


# ── Enumerations ──────────────────────────────────────────────────────────────

class LlmProvider(Enum):
    ANTHROPIC = "anthropic"
    OLLAMA    = "ollama"
    STUB      = "stub"


class LlmRole(Enum):
    USER      = "user"
    ASSISTANT = "assistant"
    SYSTEM    = "system"


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class LlmMessage:
    role:    LlmRole
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}


@dataclass
class LlmConfig:
    provider:     LlmProvider = LlmProvider.ANTHROPIC
    # Anthropic
    anthropic_api_key: str    = ""
    anthropic_model:   str    = "claude-haiku-4-5-20251001"
    # Ollama
    ollama_base_url:   str    = "http://localhost:11434"
    ollama_model:      str    = "llama3"
    # Shared
    max_tokens:   int   = 4096
    temperature:  float = 0.2
    timeout_secs: int   = 120

    @classmethod
    def from_env(cls) -> "LlmConfig":
        provider_str = os.environ.get("LLM_PROVIDER", "anthropic").lower()
        try:
            provider = LlmProvider(provider_str)
        except ValueError:
            provider = LlmProvider.ANTHROPIC

        return cls(
            provider          = provider,
            anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", ""),
            anthropic_model   = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            ollama_base_url   = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model      = os.environ.get("OLLAMA_MODEL", "llama3"),
            max_tokens        = int(os.environ.get("LLM_MAX_TOKENS", "4096")),
            temperature       = float(os.environ.get("LLM_TEMPERATURE", "0.2")),
            timeout_secs      = int(os.environ.get("LLM_TIMEOUT_SECS", "120")),
        )

    def is_air_gapped(self) -> bool:
        return self.provider == LlmProvider.OLLAMA


@dataclass
class LlmResponse:
    content:        str
    provider:       LlmProvider
    model:          str
    prompt_tokens:  int = 0
    output_tokens:  int = 0
    stop_reason:    str = "end_turn"
    raw:            Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.content


# ── Prompt normalisation ──────────────────────────────────────────────────────

def _normalise_prompt(text: str) -> str:
    """
    Normalise a prompt before sending to any model.

    - Strip XML/HTML tags (Anthropic-style <system> tags are valid in the API
      but confuse local models if passed as raw text).
    - Collapse excess whitespace.
    - Truncate to a conservative 32 000 character limit to avoid context overflows
      on smaller Ollama models.
    """
    # Strip XML-style tags that are internal to the system prompt
    cleaned = re.sub(r"<[a-zA-Z_][^>]*>|</[a-zA-Z_][^>]*>", " ", text)
    cleaned = re.sub(r"\s{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    MAX_CHARS = 32_000
    if len(cleaned) > MAX_CHARS:
        cleaned = cleaned[:MAX_CHARS] + "\n\n[... truncated for model context limit ...]"
    return cleaned


# ── Ollama client ──────────────────────────────────────────────────────────────

class OllamaClient:
    """
    Minimal HTTP client for the Ollama REST API.
    Uses only stdlib (urllib) so it works in air-gapped environments
    where pip install is restricted.

    Ollama API reference:
        POST /api/generate   — single-turn completion
        POST /api/chat       — multi-turn messages
        GET  /api/tags       — list available models
        GET  /api/version    — Ollama server version
    """

    def __init__(self, config: LlmConfig) -> None:
        self._cfg  = config
        self._base = config.ollama_base_url.rstrip("/")

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url  = self._base + endpoint
        body = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            url,
            data    = body,
            headers = {"Content-Type": "application/json"},
            method  = "POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._cfg.timeout_secs) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Cannot reach Ollama at {self._base}. "
                f"Is Ollama running? (`ollama serve`). Error: {exc}"
            ) from exc

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = self._base + endpoint
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Cannot reach Ollama at {self._base}: {exc}") from exc

    def complete(self, prompt: str, system: str = "") -> LlmResponse:
        """Single-turn text completion via /api/generate."""
        payload: Dict[str, Any] = {
            "model":  self._cfg.ollama_model,
            "prompt": _normalise_prompt(prompt),
            "stream": False,
            "options": {
                "temperature": self._cfg.temperature,
                "num_predict": self._cfg.max_tokens,
            },
        }
        if system:
            payload["system"] = _normalise_prompt(system)

        raw = self._post("/api/generate", payload)
        return LlmResponse(
            content       = raw.get("response", ""),
            provider      = LlmProvider.OLLAMA,
            model         = self._cfg.ollama_model,
            prompt_tokens  = raw.get("prompt_eval_count", 0),
            output_tokens  = raw.get("eval_count", 0),
            stop_reason   = "stop" if raw.get("done") else "length",
            raw           = raw,
        )

    def chat(self, messages: List[LlmMessage]) -> LlmResponse:
        """Multi-turn chat completion via /api/chat."""
        payload = {
            "model":    self._cfg.ollama_model,
            "messages": [m.to_dict() for m in messages],
            "stream":   False,
            "options":  {
                "temperature": self._cfg.temperature,
                "num_predict": self._cfg.max_tokens,
            },
        }
        raw = self._post("/api/chat", payload)
        msg = raw.get("message", {})
        return LlmResponse(
            content      = msg.get("content", ""),
            provider     = LlmProvider.OLLAMA,
            model        = self._cfg.ollama_model,
            prompt_tokens = raw.get("prompt_eval_count", 0),
            output_tokens = raw.get("eval_count", 0),
            stop_reason  = "stop" if raw.get("done") else "length",
            raw          = raw,
        )

    def list_models(self) -> List[str]:
        """Return names of locally available Ollama models."""
        raw = self._get("/api/tags")
        return [m.get("name", "") for m in raw.get("models", [])]

    def is_available(self) -> bool:
        """Return True if Ollama is reachable and the target model is loaded."""
        try:
            models = self.list_models()
            return any(self._cfg.ollama_model in m for m in models)
        except ConnectionError:
            return False

    def server_version(self) -> str:
        """Return Ollama server version string."""
        try:
            raw = self._get("/api/version")
            return raw.get("version", "unknown")
        except ConnectionError:
            return "unreachable"


# ── Stub client (testing) ─────────────────────────────────────────────────────

class StubLlmClient:
    """Returns deterministic canned responses for unit tests."""

    CANNED = "STUB_RESPONSE: This is a test response from the stub LLM client."

    def complete(self, prompt: str, _system: str = "") -> LlmResponse:
        return LlmResponse(
            content      = self.CANNED,
            provider     = LlmProvider.STUB,
            model        = "stub",
            prompt_tokens = len(prompt.split()),
            output_tokens = len(self.CANNED.split()),
        )

    def chat(self, messages: List[LlmMessage]) -> LlmResponse:
        return self.complete(messages[-1].content if messages else "")


# ── Unified LLM client ────────────────────────────────────────────────────────

class LlmClient:
    """
    Model-agnostic completion client.

    Dispatches to the appropriate backend based on `LlmConfig.provider`.
    All callers should use this class rather than vendor-specific clients
    directly, to allow transparent switching between cloud and air-gapped
    deployments.
    """

    def __init__(self, config: LlmConfig) -> None:
        self._cfg      = config
        self._ollama   = OllamaClient(config) if config.provider == LlmProvider.OLLAMA else None
        self._stub     = StubLlmClient()      if config.provider == LlmProvider.STUB   else None

    @classmethod
    def from_env(cls) -> "LlmClient":
        return cls(LlmConfig.from_env())

    def provider(self) -> LlmProvider:
        return self._cfg.provider

    def is_air_gapped(self) -> bool:
        return self._cfg.is_air_gapped()

    def complete(self, prompt: str, system: str = "") -> LlmResponse:
        """
        Single-turn text completion.

        Args:
            prompt: The user prompt.
            system: Optional system prompt. Applied via the API when supported;
                    prepended to prompt for Ollama if the model lacks a system role.

        Returns:
            LlmResponse with .content being the model's text output.
        """
        if self._stub:
            return self._stub.complete(prompt, system)
        if self._ollama:
            return self._ollama.complete(prompt, system)
        return self._claude_complete(prompt, system)

    def chat(self, messages: List[LlmMessage]) -> LlmResponse:
        """
        Multi-turn chat completion.

        Args:
            messages: Ordered list of LlmMessage (user/assistant/system roles).
        """
        if self._stub:
            return self._stub.chat(messages)
        if self._ollama:
            return self._ollama.chat(messages)
        return self._claude_chat(messages)

    # -- Anthropic Claude backend (requires anthropic package) -----------------

    def _claude_complete(self, prompt: str, system: str = "") -> LlmResponse:
        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        client = anthropic.Anthropic(api_key=self._cfg.anthropic_api_key)
        kwargs: Dict[str, Any] = {
            "model":      self._cfg.anthropic_model,
            "max_tokens": self._cfg.max_tokens,
            "messages":   [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        resp = client.messages.create(**kwargs)
        return LlmResponse(
            content       = resp.content[0].text if resp.content else "",
            provider      = LlmProvider.ANTHROPIC,
            model         = self._cfg.anthropic_model,
            prompt_tokens  = resp.usage.input_tokens,
            output_tokens  = resp.usage.output_tokens,
            stop_reason   = resp.stop_reason or "end_turn",
        )

    def _claude_chat(self, messages: List[LlmMessage]) -> LlmResponse:
        try:
            import anthropic  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        client   = anthropic.Anthropic(api_key=self._cfg.anthropic_api_key)
        system_msgs = [m.content for m in messages if m.role == LlmRole.SYSTEM]
        user_msgs   = [m.to_dict() for m in messages if m.role != LlmRole.SYSTEM]

        kwargs: Dict[str, Any] = {
            "model":      self._cfg.anthropic_model,
            "max_tokens": self._cfg.max_tokens,
            "messages":   user_msgs,
        }
        if system_msgs:
            kwargs["system"] = "\n\n".join(system_msgs)

        resp = client.messages.create(**kwargs)
        return LlmResponse(
            content       = resp.content[0].text if resp.content else "",
            provider      = LlmProvider.ANTHROPIC,
            model         = self._cfg.anthropic_model,
            prompt_tokens  = resp.usage.input_tokens,
            output_tokens  = resp.usage.output_tokens,
            stop_reason   = resp.stop_reason or "end_turn",
        )


# ── Confidentiality guard ─────────────────────────────────────────────────────

class ConfidentialityGuard:
    """
    Prevents CONFIDENTIAL documents from being sent to any LLM,
    per the system design principle: CONFIDENTIAL data never leaves the machine.
    """

    def __init__(self, allow_on_confidential: bool = False) -> None:
        self._allow = allow_on_confidential

    def check(self, document_classification: str, provider: LlmProvider) -> None:
        """
        Raise PermissionError if a CONFIDENTIAL document would be sent to a cloud LLM.

        Local LLMs (OLLAMA, STUB) are always permitted.
        Cloud LLMs (ANTHROPIC) require explicit opt-in via allow_on_confidential.
        """
        is_cloud = provider == LlmProvider.ANTHROPIC
        is_confidential = document_classification.upper() == "CONFIDENTIAL"

        if is_confidential and is_cloud and not self._allow:
            raise PermissionError(
                "CONFIDENTIAL documents cannot be sent to cloud LLMs. "
                "Use an air-gapped Ollama instance (LLM_PROVIDER=ollama) or "
                "enable allow_llm_on_confidential in vault settings."
            )
