"""
Sprint 12 tests — FDA-258, FDA-259
===================================
Covers:
  FDA-258 [ONPREM-001] Enterprise SSO (SAML 2.0 / OIDC)
  FDA-259 [ONPREM-002] Air-gapped LLM support (Ollama)
"""

from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta, timezone


# ═════════════════════════════════════════════════════════════════════════════
# FDA-258 — SSO Config
# ═════════════════════════════════════════════════════════════════════════════

class TestSsoConfig:

    def test_from_env_defaults_to_local(self, monkeypatch):
        for k in ["SSO_PROVIDER", "SAML_IDP_ENTITY_ID", "OIDC_ISSUER_URL"]:
            monkeypatch.delenv(k, raising=False)
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig, SsoProviderType
        cfg = SsoConfig.from_env()
        assert cfg.provider_type == SsoProviderType.LOCAL

    def test_from_env_saml_provider(self, monkeypatch):
        monkeypatch.setenv("SSO_PROVIDER", "saml")
        monkeypatch.setenv("SAML_IDP_ENTITY_ID", "https://idp.example.com")
        monkeypatch.setenv("SAML_IDP_SSO_URL", "https://idp.example.com/sso")
        monkeypatch.setenv("SAML_IDP_CERT", base64.b64encode(b"CERT_DATA").decode())
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig, SsoProviderType
        cfg = SsoConfig.from_env()
        assert cfg.provider_type == SsoProviderType.SAML
        assert cfg.is_configured()

    def test_from_env_oidc_provider(self, monkeypatch):
        monkeypatch.setenv("SSO_PROVIDER", "oidc")
        monkeypatch.setenv("OIDC_ISSUER_URL", "https://login.microsoftonline.com/tenant/v2.0")
        monkeypatch.setenv("OIDC_CLIENT_ID", "app-client-id")
        monkeypatch.setenv("OIDC_CLIENT_SECRET", "super-secret")
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig, SsoProviderType
        cfg = SsoConfig.from_env()
        assert cfg.provider_type == SsoProviderType.OIDC
        assert cfg.is_configured()

    def test_saml_not_configured_without_cert(self, monkeypatch):
        monkeypatch.setenv("SSO_PROVIDER", "saml")
        monkeypatch.setenv("SAML_IDP_ENTITY_ID", "https://idp.example.com")
        monkeypatch.delenv("SAML_IDP_CERT", raising=False)
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig
        cfg = SsoConfig.from_env()
        assert not cfg.is_configured()

    def test_local_is_always_configured(self, monkeypatch):
        monkeypatch.setenv("SSO_PROVIDER", "local")
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig
        cfg = SsoConfig.from_env()
        assert cfg.is_configured()

    def test_unknown_provider_defaults_to_local(self, monkeypatch):
        monkeypatch.setenv("SSO_PROVIDER", "unknown_provider")
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig, SsoProviderType
        cfg = SsoConfig.from_env()
        assert cfg.provider_type == SsoProviderType.LOCAL


# ═════════════════════════════════════════════════════════════════════════════
# FDA-258 — Role resolution
# ═════════════════════════════════════════════════════════════════════════════

class TestRoleResolution:

    def test_admin_group_maps_to_admin(self):
        from plugins.fda_tools.lib.enterprise_sso import resolve_role, MdrpRole
        assert resolve_role(["mdrp-admin"]) == MdrpRole.ADMIN

    def test_ra_lead_group_maps_correctly(self):
        from plugins.fda_tools.lib.enterprise_sso import resolve_role, MdrpRole
        assert resolve_role(["mdrp-ra-lead"]) == MdrpRole.RA_LEAD

    def test_admin_wins_over_engineer(self):
        from plugins.fda_tools.lib.enterprise_sso import resolve_role, MdrpRole
        assert resolve_role(["mdrp-engineer", "mdrp-admin"]) == MdrpRole.ADMIN

    def test_empty_groups_defaults_to_viewer(self):
        from plugins.fda_tools.lib.enterprise_sso import resolve_role, MdrpRole
        assert resolve_role([]) == MdrpRole.VIEWER

    def test_custom_mapping_applied(self):
        from plugins.fda_tools.lib.enterprise_sso import resolve_role, MdrpRole
        result = resolve_role(["ACME-RA-TEAM"], custom_mapping={"acme-ra-team": "ra_lead"})
        assert result == MdrpRole.RA_LEAD

    def test_unknown_groups_default_to_viewer(self):
        from plugins.fda_tools.lib.enterprise_sso import resolve_role, MdrpRole
        assert resolve_role(["some-other-group"]) == MdrpRole.VIEWER

    def test_plain_role_names_work(self):
        from plugins.fda_tools.lib.enterprise_sso import resolve_role, MdrpRole
        assert resolve_role(["admin"]) == MdrpRole.ADMIN
        assert resolve_role(["engineer"]) == MdrpRole.ENGINEER


# ═════════════════════════════════════════════════════════════════════════════
# FDA-258 — SAML Provider
# ═════════════════════════════════════════════════════════════════════════════

class TestSamlProvider:

    def _saml_cfg(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig, SsoProviderType
        return SsoConfig(
            provider_type       = SsoProviderType.SAML,
            saml_idp_entity_id  = "https://idp.example.com",
            saml_idp_sso_url    = "https://idp.example.com/sso",
            saml_sp_entity_id   = "https://mdrp.example.com",
            saml_sp_acs_url     = "https://mdrp.example.com/auth/saml/acs",
            saml_idp_cert_b64   = base64.b64encode(b"MOCK_CERT_PEM").decode(),
        )

    def test_build_authn_request_url_contains_idp(self):
        from plugins.fda_tools.lib.enterprise_sso import SamlProvider
        provider = SamlProvider(self._saml_cfg())
        url = provider.build_authn_request_url()
        assert "idp.example.com" in url
        assert "SAMLRequest" in url

    def test_build_authn_request_url_includes_relay_state(self):
        from plugins.fda_tools.lib.enterprise_sso import SamlProvider
        provider = SamlProvider(self._saml_cfg())
        url = provider.build_authn_request_url(relay_state="/dashboard")
        assert "RelayState" in url

    def test_parse_response_requires_cert(self):
        import pytest
        from plugins.fda_tools.lib.enterprise_sso import SamlProvider, SsoConfig, SsoProviderType
        cfg = SsoConfig(provider_type=SsoProviderType.SAML)  # no cert
        provider = SamlProvider(cfg)
        with pytest.raises(ValueError, match="SAML_IDP_CERT"):
            provider.parse_response(base64.b64encode(b"<saml>fake</saml>").decode())

    def test_validate_cert_b64_valid(self):
        from plugins.fda_tools.lib.enterprise_sso import SamlProvider
        provider = SamlProvider(self._saml_cfg())
        assert provider.validate_cert_b64() is True

    def test_validate_cert_b64_invalid(self):
        from plugins.fda_tools.lib.enterprise_sso import SamlProvider, SsoConfig, SsoProviderType
        cfg = SsoConfig(
            provider_type=SsoProviderType.SAML,
            saml_idp_cert_b64="!!!not_base64!!!"
        )
        provider = SamlProvider(cfg)
        assert provider.validate_cert_b64() is False


# ═════════════════════════════════════════════════════════════════════════════
# FDA-258 — OIDC Provider
# ═════════════════════════════════════════════════════════════════════════════

class TestOidcProvider:

    def _oidc_cfg(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoConfig, SsoProviderType
        return SsoConfig(
            provider_type       = SsoProviderType.OIDC,
            oidc_issuer_url     = "https://login.microsoftonline.com/tenant/v2.0",
            oidc_client_id      = "client-abc123",
            oidc_client_secret  = "secret-xyz",
            oidc_redirect_uri   = "https://mdrp.example.com/auth/oidc/callback",
            oidc_scopes         = ["openid", "email", "profile"],
        )

    def test_build_auth_url_contains_client_id(self):
        from plugins.fda_tools.lib.enterprise_sso import OidcProvider
        provider = OidcProvider(self._oidc_cfg())
        url = provider.build_auth_url(state="random_state", nonce="random_nonce")
        assert "client-abc123" in url
        assert "state=random_state" in url
        assert "openid" in url

    def test_build_auth_url_requires_issuer(self):
        import pytest
        from plugins.fda_tools.lib.enterprise_sso import OidcProvider, SsoConfig, SsoProviderType
        cfg = SsoConfig(provider_type=SsoProviderType.OIDC)
        provider = OidcProvider(cfg)
        with pytest.raises(ValueError, match="not fully configured"):
            provider.build_auth_url(state="s", nonce="n")

    def test_exchange_code_stub_returns_tokens(self):
        from plugins.fda_tools.lib.enterprise_sso import OidcProvider
        provider = OidcProvider(self._oidc_cfg())
        tokens = provider.exchange_code(code="auth_code", _state="state")
        assert "access_token" in tokens
        assert "id_token" in tokens

    def test_claims_to_user_maps_role(self):
        from plugins.fda_tools.lib.enterprise_sso import OidcProvider, MdrpRole
        provider = OidcProvider(self._oidc_cfg())
        claims = {
            "sub":    "user-123",
            "email":  "alice@example.com",
            "name":   "Alice",
            "groups": ["mdrp-ra-lead"],
        }
        user = provider.claims_to_user(claims)
        assert user.email == "alice@example.com"
        assert user.role  == MdrpRole.RA_LEAD

    def test_claims_to_user_string_group(self):
        from plugins.fda_tools.lib.enterprise_sso import OidcProvider, MdrpRole
        provider = OidcProvider(self._oidc_cfg())
        claims = {"sub": "u", "email": "b@x.com", "groups": "mdrp-admin"}
        user = provider.claims_to_user(claims)
        assert user.role == MdrpRole.ADMIN


# ═════════════════════════════════════════════════════════════════════════════
# FDA-258 — Session Manager
# ═════════════════════════════════════════════════════════════════════════════

class TestSsoSessionManager:

    def _make_user(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoUser, SsoProviderType, MdrpRole
        return SsoUser(
            email="alice@example.com",
            display_name="Alice",
            role=MdrpRole.RA_LEAD,
            provider=SsoProviderType.OIDC,
            external_id="alice-sub-123",
        )

    def test_create_returns_session(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoSessionManager, SsoProviderType
        mgr     = SsoSessionManager()
        session = mgr.create(self._make_user(), SsoProviderType.OIDC)
        assert session.is_valid()
        assert len(session.session_id) > 0

    def test_get_valid_session(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoSessionManager, SsoProviderType
        mgr     = SsoSessionManager()
        created = mgr.create(self._make_user(), SsoProviderType.OIDC)
        fetched = mgr.get(created.session_id)
        assert fetched is not None
        assert fetched.session_id == created.session_id

    def test_get_unknown_session_returns_none(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoSessionManager
        mgr = SsoSessionManager()
        assert mgr.get("nonexistent_id") is None

    def test_revoke_session(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoSessionManager, SsoProviderType
        mgr     = SsoSessionManager()
        created = mgr.create(self._make_user(), SsoProviderType.OIDC)
        assert mgr.revoke(created.session_id) is True
        assert mgr.get(created.session_id) is None

    def test_active_count(self):
        from plugins.fda_tools.lib.enterprise_sso import SsoSessionManager, SsoProviderType
        mgr = SsoSessionManager()
        mgr.create(self._make_user(), SsoProviderType.OIDC)
        mgr.create(self._make_user(), SsoProviderType.OIDC)
        assert mgr.active_count() == 2

    def test_purge_expired(self):
        from plugins.fda_tools.lib.enterprise_sso import (
            SsoSessionManager, SsoSession, SsoSessionStatus, SsoProviderType,
        )
        mgr = SsoSessionManager()
        s   = mgr.create(self._make_user(), SsoProviderType.OIDC)
        # Manually expire the session
        s.expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        removed = mgr.purge_expired()
        assert removed >= 1


# ═════════════════════════════════════════════════════════════════════════════
# FDA-259 — LLM Config
# ═════════════════════════════════════════════════════════════════════════════

class TestLlmConfig:

    def test_from_env_defaults_to_anthropic(self, monkeypatch):
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        from plugins.fda_tools.lib.local_llm import LlmConfig, LlmProvider
        cfg = LlmConfig.from_env()
        assert cfg.provider == LlmProvider.ANTHROPIC

    def test_from_env_ollama(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.setenv("OLLAMA_MODEL", "mistral")
        from plugins.fda_tools.lib.local_llm import LlmConfig, LlmProvider
        cfg = LlmConfig.from_env()
        assert cfg.provider == LlmProvider.OLLAMA
        assert cfg.ollama_model == "mistral"
        assert cfg.is_air_gapped() is True

    def test_from_env_stub(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "stub")
        from plugins.fda_tools.lib.local_llm import LlmConfig, LlmProvider
        cfg = LlmConfig.from_env()
        assert cfg.provider == LlmProvider.STUB

    def test_unknown_provider_defaults_to_anthropic(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "gpt-99")
        from plugins.fda_tools.lib.local_llm import LlmConfig, LlmProvider
        cfg = LlmConfig.from_env()
        assert cfg.provider == LlmProvider.ANTHROPIC

    def test_air_gapped_flag(self):
        from plugins.fda_tools.lib.local_llm import LlmConfig, LlmProvider
        cfg = LlmConfig(provider=LlmProvider.OLLAMA)
        assert cfg.is_air_gapped() is True
        cfg2 = LlmConfig(provider=LlmProvider.ANTHROPIC)
        assert cfg2.is_air_gapped() is False


# ═════════════════════════════════════════════════════════════════════════════
# FDA-259 — Prompt normalisation
# ═════════════════════════════════════════════════════════════════════════════

class TestPromptNormalisation:

    def test_strips_xml_tags(self):
        from plugins.fda_tools.lib.local_llm import _normalise_prompt
        result = _normalise_prompt("<system>Summarise this.</system>")
        assert "<system>" not in result
        assert "Summarise this." in result

    def test_collapses_excess_whitespace(self):
        from plugins.fda_tools.lib.local_llm import _normalise_prompt
        result = _normalise_prompt("A\n\n\n\n\nB")
        assert "\n\n\n" not in result

    def test_truncates_long_prompts(self):
        from plugins.fda_tools.lib.local_llm import _normalise_prompt
        long_prompt = "x" * 40_000
        result = _normalise_prompt(long_prompt)
        assert len(result) <= 32_100  # 32000 + truncation message
        assert "truncated" in result

    def test_short_prompt_not_truncated(self):
        from plugins.fda_tools.lib.local_llm import _normalise_prompt
        result = _normalise_prompt("Short prompt.")
        assert "truncated" not in result
        assert result == "Short prompt."


# ═════════════════════════════════════════════════════════════════════════════
# FDA-259 — Stub LLM client
# ═════════════════════════════════════════════════════════════════════════════

class TestStubLlmClient:

    def test_complete_returns_response(self):
        from plugins.fda_tools.lib.local_llm import StubLlmClient, LlmProvider
        client = StubLlmClient()
        resp = client.complete("Summarise this section.")
        assert "STUB_RESPONSE" in resp.content
        assert resp.provider == LlmProvider.STUB

    def test_chat_returns_response(self):
        from plugins.fda_tools.lib.local_llm import StubLlmClient, LlmMessage, LlmRole
        client = StubLlmClient()
        messages = [LlmMessage(role=LlmRole.USER, content="Hello")]
        resp = client.chat(messages)
        assert "STUB_RESPONSE" in resp.content

    def test_complete_records_token_counts(self):
        from plugins.fda_tools.lib.local_llm import StubLlmClient
        client = StubLlmClient()
        resp = client.complete("This is a five word prompt here")
        assert resp.prompt_tokens > 0
        assert resp.output_tokens > 0


# ═════════════════════════════════════════════════════════════════════════════
# FDA-259 — Unified LlmClient with stub backend
# ═════════════════════════════════════════════════════════════════════════════

class TestLlmClientStubBackend:

    def _stub_client(self):
        from plugins.fda_tools.lib.local_llm import LlmClient, LlmConfig, LlmProvider
        return LlmClient(LlmConfig(provider=LlmProvider.STUB))

    def test_provider_returns_stub(self):
        from plugins.fda_tools.lib.local_llm import LlmProvider
        assert self._stub_client().provider() == LlmProvider.STUB

    def test_is_not_air_gapped(self):
        # Stub is not air-gapped (it's a testing backend, not Ollama)
        assert self._stub_client().is_air_gapped() is False

    def test_complete_via_stub_backend(self):
        client = self._stub_client()
        resp = client.complete("Test prompt")
        assert resp.content == "STUB_RESPONSE: This is a test response from the stub LLM client."

    def test_chat_via_stub_backend(self):
        from plugins.fda_tools.lib.local_llm import LlmMessage, LlmRole
        client = self._stub_client()
        resp = client.chat([LlmMessage(LlmRole.USER, "Hello")])
        assert "STUB_RESPONSE" in resp.content

    def test_llm_response_str(self):
        client = self._stub_client()
        resp = client.complete("x")
        assert str(resp) == resp.content


# ═════════════════════════════════════════════════════════════════════════════
# FDA-259 — Confidentiality guard
# ═════════════════════════════════════════════════════════════════════════════

class TestConfidentialityGuard:

    def test_confidential_to_cloud_blocked(self):
        import pytest
        from plugins.fda_tools.lib.local_llm import ConfidentialityGuard, LlmProvider
        guard = ConfidentialityGuard(allow_on_confidential=False)
        with pytest.raises(PermissionError, match="CONFIDENTIAL"):
            guard.check("CONFIDENTIAL", LlmProvider.ANTHROPIC)

    def test_confidential_to_ollama_allowed(self):
        from plugins.fda_tools.lib.local_llm import ConfidentialityGuard, LlmProvider
        guard = ConfidentialityGuard(allow_on_confidential=False)
        guard.check("CONFIDENTIAL", LlmProvider.OLLAMA)  # must not raise

    def test_non_confidential_to_cloud_allowed(self):
        from plugins.fda_tools.lib.local_llm import ConfidentialityGuard, LlmProvider
        guard = ConfidentialityGuard(allow_on_confidential=False)
        guard.check("PUBLIC", LlmProvider.ANTHROPIC)  # must not raise

    def test_explicit_allow_bypasses_guard(self):
        from plugins.fda_tools.lib.local_llm import ConfidentialityGuard, LlmProvider
        guard = ConfidentialityGuard(allow_on_confidential=True)
        guard.check("CONFIDENTIAL", LlmProvider.ANTHROPIC)  # must not raise

    def test_case_insensitive_classification(self):
        import pytest
        from plugins.fda_tools.lib.local_llm import ConfidentialityGuard, LlmProvider
        guard = ConfidentialityGuard(allow_on_confidential=False)
        with pytest.raises(PermissionError):
            guard.check("confidential", LlmProvider.ANTHROPIC)


# ═════════════════════════════════════════════════════════════════════════════
# FDA-259 — Ollama client (unit tests without network)
# ═════════════════════════════════════════════════════════════════════════════

class TestOllamaClientUnit:
    """
    Unit tests for OllamaClient that do NOT require a running Ollama server.
    Network calls are monkey-patched.
    """

    def _cfg(self):
        from plugins.fda_tools.lib.local_llm import LlmConfig, LlmProvider
        return LlmConfig(
            provider       = LlmProvider.OLLAMA,
            ollama_base_url = "http://localhost:11434",
            ollama_model   = "llama3",
            max_tokens     = 512,
            temperature    = 0.1,
        )

    def test_complete_uses_generate_endpoint(self, monkeypatch):
        import json as _json
        from plugins.fda_tools.lib.local_llm import OllamaClient

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = _json.loads(req.data.decode())
            import io
            return io.BytesIO(_json.dumps({
                "response": "Test response text",
                "done": True,
                "prompt_eval_count": 5,
                "eval_count": 3,
            }).encode())

        import urllib.request as _ureq
        monkeypatch.setattr(_ureq, "urlopen", fake_urlopen)

        client = OllamaClient(self._cfg())
        resp = client.complete("Describe this device.")
        assert resp.content == "Test response text"
        assert "/api/generate" in captured["url"]
        assert captured["body"]["model"] == "llama3"

    def test_chat_uses_chat_endpoint(self, monkeypatch):
        import json as _json
        from plugins.fda_tools.lib.local_llm import OllamaClient, LlmMessage, LlmRole

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            import io
            return io.BytesIO(_json.dumps({
                "message": {"role": "assistant", "content": "Chat reply"},
                "done": True,
                "prompt_eval_count": 10,
                "eval_count": 5,
            }).encode())

        import urllib.request as _ureq
        monkeypatch.setattr(_ureq, "urlopen", fake_urlopen)

        client = OllamaClient(self._cfg())
        msgs  = [LlmMessage(LlmRole.USER, "Hello")]
        resp  = client.chat(msgs)
        assert resp.content == "Chat reply"
        assert "/api/chat" in captured["url"]

    def test_connection_error_on_unreachable(self, monkeypatch):
        import urllib.error
        import urllib.request as _ureq
        from plugins.fda_tools.lib.local_llm import OllamaClient

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(_ureq, "urlopen", fake_urlopen)

        client = OllamaClient(self._cfg())
        import pytest
        with pytest.raises(ConnectionError, match="Ollama"):
            client.complete("test")

    def test_list_models_parses_tags_response(self, monkeypatch):
        import json as _json
        import urllib.request as _ureq
        from plugins.fda_tools.lib.local_llm import OllamaClient

        def fake_urlopen(url, timeout=None):
            import io
            return io.BytesIO(_json.dumps({
                "models": [{"name": "llama3:latest"}, {"name": "mistral:latest"}]
            }).encode())

        monkeypatch.setattr(_ureq, "urlopen", fake_urlopen)

        client = OllamaClient(self._cfg())
        models = client.list_models()
        assert "llama3:latest" in models
        assert "mistral:latest" in models
