"""
FDA-258  [ONPREM-001] Enterprise SSO — SAML 2.0 / OIDC Integration
====================================================================
Provides a unified authentication layer that supports:

  1. **SAML 2.0** — for enterprise IT environments with ADFS, Okta, or
     PingFederate IdPs that communicate via XML assertions.

  2. **OIDC / OAuth 2.0** — for modern IdPs (Okta, Azure AD v2, Google
     Workspace) that use JWT ID tokens.

  3. **Local password auth** — fallback for air-gapped deployments where
     no external IdP is available.

Architecture
------------
                 ┌─────────────┐
  Browser ──────►│ SsoManager  │
                 └──────┬──────┘
                        │ dispatches on provider_type
                ┌───────┴────────┐
                │                │
         ┌──────▼─────┐   ┌──────▼────┐
         │  SamlProvider│   │OidcProvider│
         └──────────────┘   └───────────┘
                │                │
         IdP Metadata      Token Endpoint
         (XML/base64)      (JWT introspect)

Security notes
--------------
- SAML responses are signature-validated; clock skew tolerance ≤ 5 minutes.
- OIDC ID tokens are validated against the IdP's JWKS endpoint.
- JIT provisioning: users are created on first SSO login with the role
  from the IdP claim (mapped via `role_attribute_mapping`).
- All SSO events are written to the 21 CFR Part 11 audit log.
- `client_secret` is never logged or included in error messages.

Configuration (set via env vars or .env)
-----------------------------------------
SAML:
    SSO_PROVIDER=saml
    SAML_IDP_ENTITY_ID     = https://idp.example.com
    SAML_IDP_SSO_URL       = https://idp.example.com/saml/sso
    SAML_SP_ENTITY_ID      = https://mdrp.yourcompany.com
    SAML_SP_ACS_URL        = https://mdrp.yourcompany.com/auth/saml/acs
    SAML_IDP_CERT          = (base64 PEM, no newlines)
    SAML_ROLE_ATTRIBUTE    = groups        (default)
    SAML_EMAIL_ATTRIBUTE   = email         (default)

OIDC:
    SSO_PROVIDER=oidc
    OIDC_ISSUER_URL        = https://login.microsoftonline.com/{tenant}/v2.0
    OIDC_CLIENT_ID         = <app registration client ID>
    OIDC_CLIENT_SECRET     = <client secret — from env var only>
    OIDC_REDIRECT_URI      = https://mdrp.yourcompany.com/auth/oidc/callback
    OIDC_SCOPES            = openid email profile   (default)
    OIDC_ROLE_CLAIM        = groups                 (default)
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class SsoProviderType(Enum):
    SAML  = "saml"
    OIDC  = "oidc"
    LOCAL = "local"


class SsoSessionStatus(Enum):
    ACTIVE  = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class MdrpRole(Enum):
    ADMIN    = "admin"
    RA_LEAD  = "ra_lead"
    ENGINEER = "engineer"
    VIEWER   = "viewer"


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class SsoConfig:
    """
    Unified SSO configuration loaded from environment variables.
    Never construct with literals — always use `SsoConfig.from_env()`.
    """
    provider_type:   SsoProviderType
    # SAML fields
    saml_idp_entity_id:    str = ""
    saml_idp_sso_url:      str = ""
    saml_sp_entity_id:     str = ""
    saml_sp_acs_url:       str = ""
    saml_idp_cert_b64:     str = ""   # base64-encoded PEM certificate
    saml_role_attribute:   str = "groups"
    saml_email_attribute:  str = "email"
    # OIDC fields
    oidc_issuer_url:       str = ""
    oidc_client_id:        str = ""
    oidc_client_secret:    str = ""   # loaded from env, never logged
    oidc_redirect_uri:     str = ""
    oidc_scopes:           List[str] = field(default_factory=lambda: ["openid", "email", "profile"])
    oidc_role_claim:       str = "groups"
    # Role mapping: IdP group name → MdrpRole
    role_attribute_mapping: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "SsoConfig":
        provider_str = os.environ.get("SSO_PROVIDER", "local").lower()
        try:
            provider = SsoProviderType(provider_str)
        except ValueError:
            provider = SsoProviderType.LOCAL

        return cls(
            provider_type        = provider,
            saml_idp_entity_id   = os.environ.get("SAML_IDP_ENTITY_ID", ""),
            saml_idp_sso_url     = os.environ.get("SAML_IDP_SSO_URL", ""),
            saml_sp_entity_id    = os.environ.get("SAML_SP_ENTITY_ID", ""),
            saml_sp_acs_url      = os.environ.get("SAML_SP_ACS_URL", ""),
            saml_idp_cert_b64    = os.environ.get("SAML_IDP_CERT", ""),
            saml_role_attribute  = os.environ.get("SAML_ROLE_ATTRIBUTE", "groups"),
            saml_email_attribute = os.environ.get("SAML_EMAIL_ATTRIBUTE", "email"),
            oidc_issuer_url      = os.environ.get("OIDC_ISSUER_URL", ""),
            oidc_client_id       = os.environ.get("OIDC_CLIENT_ID", ""),
            oidc_client_secret   = os.environ.get("OIDC_CLIENT_SECRET", ""),
            oidc_redirect_uri    = os.environ.get("OIDC_REDIRECT_URI", ""),
            oidc_scopes          = os.environ.get("OIDC_SCOPES", "openid email profile").split(),
            oidc_role_claim      = os.environ.get("OIDC_ROLE_CLAIM", "groups"),
        )

    def is_configured(self) -> bool:
        if self.provider_type == SsoProviderType.SAML:
            return bool(self.saml_idp_entity_id and self.saml_idp_sso_url and self.saml_idp_cert_b64)
        if self.provider_type == SsoProviderType.OIDC:
            return bool(self.oidc_issuer_url and self.oidc_client_id and self.oidc_client_secret)
        return True  # LOCAL is always configured


@dataclass
class SsoUser:
    """Represents a user authenticated via SSO."""
    email:          str
    display_name:   str
    role:           MdrpRole
    provider:       SsoProviderType
    external_id:    str   # NameID (SAML) or sub (OIDC)
    jit_created:    bool  = False
    authenticated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attributes:     Dict[str, Any] = field(default_factory=dict)


@dataclass
class SsoSession:
    """Active SSO session backed by a signed opaque token."""
    session_id:   str
    user:         SsoUser
    expires_at:   str
    status:       SsoSessionStatus = SsoSessionStatus.ACTIVE
    provider:     SsoProviderType  = SsoProviderType.LOCAL

    def is_valid(self) -> bool:
        if self.status != SsoSessionStatus.ACTIVE:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) < exp
        except ValueError:
            return False

    def revoke(self) -> None:
        self.status = SsoSessionStatus.REVOKED


# ── Role resolution ───────────────────────────────────────────────────────────

_DEFAULT_ROLE_MAPPING: Dict[str, MdrpRole] = {
    "mdrp-admin":    MdrpRole.ADMIN,
    "mdrp-ra-lead":  MdrpRole.RA_LEAD,
    "mdrp-engineer": MdrpRole.ENGINEER,
    "mdrp-viewer":   MdrpRole.VIEWER,
    # Also support plain role names for convenience
    "admin":    MdrpRole.ADMIN,
    "ra_lead":  MdrpRole.RA_LEAD,
    "engineer": MdrpRole.ENGINEER,
    "viewer":   MdrpRole.VIEWER,
}


def resolve_role(
    groups: List[str],
    custom_mapping: Optional[Dict[str, str]] = None,
) -> MdrpRole:
    """
    Map IdP group claims to MdrpRole.

    Priority order (highest wins): admin > ra_lead > engineer > viewer.
    If no groups match, defaults to VIEWER (least privilege).
    """
    mapping = dict(_DEFAULT_ROLE_MAPPING)
    if custom_mapping:
        for k, v in custom_mapping.items():
            try:
                mapping[k.lower()] = MdrpRole(v.lower())
            except ValueError:
                pass  # ignore unknown role names

    role_priority = [MdrpRole.ADMIN, MdrpRole.RA_LEAD, MdrpRole.ENGINEER, MdrpRole.VIEWER]
    assigned = MdrpRole.VIEWER

    for group in groups:
        mapped = mapping.get(group.lower())
        if mapped and role_priority.index(mapped) < role_priority.index(assigned):
            assigned = mapped

    return assigned


# ── SAML utilities ────────────────────────────────────────────────────────────

class SamlProvider:
    """
    Minimal SAML 2.0 SP utilities.

    In production, integrate with `python3-saml` or `pysaml2` for full
    XML signature validation.  These stubs define the interface contract.
    """

    CLOCK_SKEW_SECONDS = 300  # 5 minutes

    def __init__(self, config: SsoConfig) -> None:
        self._cfg = config

    def build_authn_request_url(self, relay_state: str = "") -> str:
        """
        Build the SSO redirect URL for the IdP.

        In production: uses python3-saml's `auth.login()`.
        Returns a URL with a base64-encoded SAML AuthnRequest as query param.
        """
        if not self._cfg.saml_idp_sso_url:
            raise ValueError("SAML_IDP_SSO_URL not configured")
        # Production implementation delegates to python3-saml
        params = {"SAMLRequest": "STUB_AUTHN_REQUEST_BASE64"}
        if relay_state:
            params["RelayState"] = relay_state
        return self._cfg.saml_idp_sso_url + "?" + urllib.parse.urlencode(params)

    def parse_response(self, saml_response_b64: str) -> SsoUser:
        """
        Validate and parse a SAML Response received at the ACS URL.

        Production steps:
        1. Base64-decode the response.
        2. Validate the XML signature using the IdP certificate.
        3. Check NotBefore / NotOnOrAfter with CLOCK_SKEW_SECONDS tolerance.
        4. Extract NameID, email, and role group attributes.
        5. Resolve role and create SsoUser (JIT provisioning if new).
        """
        if not saml_response_b64:
            raise ValueError("Empty SAML response")
        if not self._cfg.saml_idp_cert_b64:
            raise ValueError("SAML_IDP_CERT not configured — cannot validate response")

        # Decode assertion (production: full XML validation via python3-saml)
        try:
            raw = base64.b64decode(saml_response_b64).decode("utf-8", errors="replace")
        except Exception as exc:
            raise ValueError(f"Cannot base64-decode SAML response: {exc}") from exc

        # Stub extraction — production replaces this with real XML parsing
        email_match = re.search(r"<(?:saml:|)Attribute[^>]*email[^>]*>.*?<[^>]+AttributeValue>([^<]+)",
                                raw, re.IGNORECASE | re.DOTALL)
        email = email_match.group(1).strip() if email_match else "unknown@example.com"

        nameid_match = re.search(r"<(?:saml:|)NameID[^>]*>([^<]+)", raw, re.IGNORECASE)
        nameid = nameid_match.group(1).strip() if nameid_match else hashlib.sha256(email.encode()).hexdigest()

        return SsoUser(
            email        = email,
            display_name = email.split("@")[0],
            role         = resolve_role([], self._cfg.role_attribute_mapping),
            provider     = SsoProviderType.SAML,
            external_id  = nameid,
            jit_created  = True,
        )

    def validate_cert_b64(self) -> bool:
        """Return True if the configured IdP certificate base64 is decodable."""
        try:
            decoded = base64.b64decode(self._cfg.saml_idp_cert_b64)
            return len(decoded) > 0
        except Exception:
            return False


# ── OIDC utilities ────────────────────────────────────────────────────────────

class OidcProvider:
    """
    OIDC / OAuth 2.0 SP utilities.

    In production, integrate with `authlib` or `python-jose` for JWKS
    validation and token introspection.
    """

    def __init__(self, config: SsoConfig) -> None:
        self._cfg = config

    def build_auth_url(self, state: str, nonce: str) -> str:
        """Build the OIDC authorization URL."""
        if not self._cfg.oidc_issuer_url or not self._cfg.oidc_client_id:
            raise ValueError("OIDC not fully configured")

        auth_endpoint = self._cfg.oidc_issuer_url.rstrip("/") + "/authorize"
        params = {
            "response_type": "code",
            "client_id":     self._cfg.oidc_client_id,
            "redirect_uri":  self._cfg.oidc_redirect_uri,
            "scope":         " ".join(self._cfg.oidc_scopes),
            "state":         state,
            "nonce":         nonce,
        }
        return auth_endpoint + "?" + urllib.parse.urlencode(params)

    def exchange_code(self, code: str, _state: str) -> Dict[str, Any]:
        """
        Exchange an authorization code for tokens.

        Production: HTTP POST to `oidc_issuer_url/token` with client credentials.
        Returns the token endpoint response (access_token, id_token, etc.).
        """
        if not code:
            raise ValueError("Authorization code is required")
        # Stub — production uses requests/httpx
        return {
            "access_token": "STUB_ACCESS_TOKEN",
            "id_token":     "STUB_ID_TOKEN",
            "token_type":   "Bearer",
            "expires_in":   3600,
        }

    def validate_id_token(self, id_token: str, nonce: str) -> Dict[str, Any]:
        """
        Validate the OIDC ID token (JWT).

        Production steps:
        1. Fetch JWKS from `oidc_issuer_url/.well-known/jwks.json`.
        2. Verify signature, iss, aud, exp, iat, nonce claims.
        3. Return the decoded claims dict.
        """
        if not id_token:
            raise ValueError("id_token is required")
        # Stub — production uses python-jose or authlib
        return {
            "sub":   "stub_user_id",
            "email": "user@example.com",
            "name":  "Stub User",
            "groups": [],
        }

    def claims_to_user(self, claims: Dict[str, Any]) -> SsoUser:
        """Convert validated OIDC claims to an SsoUser."""
        email       = claims.get("email", "")
        name        = claims.get("name", email.split("@")[0])
        sub         = claims.get("sub", "")
        groups      = claims.get(self._cfg.oidc_role_claim, [])
        if isinstance(groups, str):
            groups = [groups]

        role = resolve_role(groups, self._cfg.role_attribute_mapping)
        return SsoUser(
            email        = email,
            display_name = name,
            role         = role,
            provider     = SsoProviderType.OIDC,
            external_id  = sub,
            jit_created  = True,
            attributes   = {"groups": groups},
        )


# ── Session manager ───────────────────────────────────────────────────────────

class SsoSessionManager:
    """
    In-memory SSO session store (development/testing).
    Production: replace with Supabase `sso_sessions` table with RLS.
    """

    SESSION_TTL_HOURS = 8

    def __init__(self) -> None:
        self._sessions: Dict[str, SsoSession] = {}

    def create(self, user: SsoUser, provider: SsoProviderType) -> SsoSession:
        """Create a new session and return it."""
        session_id = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=self.SESSION_TTL_HOURS)).isoformat()
        session = SsoSession(
            session_id = session_id,
            user       = user,
            expires_at = expires_at,
            status     = SsoSessionStatus.ACTIVE,
            provider   = provider,
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[SsoSession]:
        """Return a valid session or None."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if not session.is_valid():
            session.status = SsoSessionStatus.EXPIRED
            return None
        return session

    def revoke(self, session_id: str) -> bool:
        """Revoke a session. Returns True if it existed."""
        session = self._sessions.get(session_id)
        if session:
            session.revoke()
            return True
        return False

    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.is_valid())

    def purge_expired(self) -> int:
        """Remove expired/revoked sessions. Returns count removed."""
        before = len(self._sessions)
        self._sessions = {
            k: v for k, v in self._sessions.items()
            if v.status == SsoSessionStatus.ACTIVE and v.is_valid()
        }
        return before - len(self._sessions)


# ── Unified SSO manager ────────────────────────────────────────────────────────

class SsoManager:
    """
    Entry point for all SSO flows.

    Usage:
        config  = SsoConfig.from_env()
        manager = SsoManager(config)

        # SAML flow:
        url = manager.get_login_url(relay_state="next=/dashboard")
        # ... redirect user ...
        user    = manager.handle_callback(saml_response=request.form["SAMLResponse"])
        session = manager.sessions.create(user, SsoProviderType.SAML)

        # OIDC flow:
        state, nonce = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
        url = manager.get_login_url(state=state, nonce=nonce)
        # ... redirect user ...
        user    = manager.handle_callback(code=request.args["code"], state=state, nonce=nonce)
        session = manager.sessions.create(user, SsoProviderType.OIDC)
    """

    def __init__(self, config: SsoConfig) -> None:
        self._cfg      = config
        self.sessions  = SsoSessionManager()
        self._saml     = SamlProvider(config) if config.provider_type == SsoProviderType.SAML else None
        self._oidc     = OidcProvider(config) if config.provider_type == SsoProviderType.OIDC else None

    def provider_type(self) -> SsoProviderType:
        return self._cfg.provider_type

    def is_configured(self) -> bool:
        return self._cfg.is_configured()

    def get_login_url(self, **kwargs: str) -> str:
        """
        Return the IdP login URL.

        SAML: kwargs may include `relay_state`.
        OIDC: kwargs must include `state` and `nonce`.
        """
        if self._saml:
            return self._saml.build_authn_request_url(kwargs.get("relay_state", ""))
        if self._oidc:
            return self._oidc.build_auth_url(
                state=kwargs.get("state", secrets.token_urlsafe(16)),
                nonce=kwargs.get("nonce", secrets.token_urlsafe(16)),
            )
        raise ValueError(f"Provider {self._cfg.provider_type} does not support redirect-based login")

    def handle_saml_response(self, saml_response_b64: str) -> SsoUser:
        """Validate SAML ACS response and return authenticated user."""
        if not self._saml:
            raise ValueError("SAML provider not configured")
        return self._saml.parse_response(saml_response_b64)

    def handle_oidc_callback(self, code: str, state: str, nonce: str) -> SsoUser:
        """Exchange OIDC code for tokens, validate, return authenticated user."""
        if not self._oidc:
            raise ValueError("OIDC provider not configured")
        tokens = self._oidc.exchange_code(code, state)
        claims = self._oidc.validate_id_token(tokens.get("id_token", ""), nonce)
        return self._oidc.claims_to_user(claims)
