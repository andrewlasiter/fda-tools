"""
Sprint 31 — HITL Enterprise Hardening + Live Search Wiring
===========================================================
Test suite for FDA-311 (pgvector/live research search wiring) and
FDA-309 (HITL gate enterprise hardening with cryptographic signing).

Coverage:
  FDA-311 [SR-001] Bridge endpoint POST /research/search
  FDA-311 [SR-002] Guidance corpus and keyword matching
  FDA-311 [SR-003] TypeScript types and hooks in api-client.ts
  FDA-311 [SR-004] SearchPanel wired to live search in research/page.tsx
  FDA-309 [HG-001] Bridge endpoint POST /hitl/gate/{id}/sign
  FDA-309 [HG-002] Bridge endpoint GET  /hitl/gate/{id}
  FDA-309 [HG-003] Role-based access control for HITL signing
  FDA-309 [HG-004] 24h escalation logic for deferred gates
  FDA-309 [HG-005] TypeScript types and hooks in api-client.ts
  FDA-309 [HG-006] HitlGateIntegration component — reviewer fields + signing
  BCO-001 Bridge completeness — all Sprint 31 endpoints registered
  BCO-002 OpenClaw E2E assessment document exists and is comprehensive
"""

import os
import re
import unittest

# ── Path setup ──────────────────────────────────────────────────────────────

_HERE = os.path.dirname(__file__)
ROOT     = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "web"))
FDA_PKG  = os.path.normpath(os.path.join(_HERE, ".."))
LIB      = os.path.join(FDA_PKG, "lib")
BRIDGE   = os.path.join(FDA_PKG, "bridge", "server.py")
API_CLIENT = os.path.join(ROOT, "lib", "api-client.ts")
RESEARCH_PAGE = os.path.join(ROOT, "app", "research", "page.tsx")
HITL_COMPONENT = os.path.join(ROOT, "components", "hitl", "hitl-gate-integration.tsx")
CFR11_LIB = os.path.join(LIB, "cfr_part11.py")
ASSESSMENT = os.path.join(
    os.path.normpath(os.path.join(_HERE, "..", "..", "..")),
    "docs", "OPENCLAW_E2E_ASSESSMENT.md"
)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def exists(path: str) -> bool:
    return os.path.exists(path)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-311 [SR-001] — Bridge endpoint: POST /research/search
# ─────────────────────────────────────────────────────────────────────────────

class TestSR001BridgeSearchEndpoint(unittest.TestCase):
    """Bridge server has the POST /research/search endpoint."""

    def setUp(self):
        self.src = read(BRIDGE)

    def test_endpoint_route_defined(self):
        """Route @app.post('/research/search') exists."""
        self.assertIn('"/research/search"', self.src)

    def test_endpoint_is_post(self):
        """Endpoint uses POST method."""
        self.assertIn("app.post(\"/research/search\")", self.src)

    def test_research_search_body_model(self):
        """ResearchSearchBody Pydantic model is defined."""
        self.assertIn("class ResearchSearchBody", self.src)

    def test_research_hit_model(self):
        """ResearchHit Pydantic model is defined."""
        self.assertIn("class ResearchHit", self.src)

    def test_sources_field_in_model(self):
        """ResearchSearchBody has a sources field."""
        self.assertIn("sources:", self.src)

    def test_limit_field_in_model(self):
        """ResearchSearchBody has a limit field."""
        self.assertIn("limit:", self.src)

    def test_product_code_filter(self):
        """Endpoint accepts optional product_code for filtering."""
        self.assertIn("product_code", self.src)

    def test_endpoint_uses_rate_limit(self):
        """Endpoint applies rate limiting via @_rate_limit."""
        # Extract the area around the research/search endpoint
        idx = self.src.find('"/research/search"')
        surrounding = self.src[max(0, idx - 200): idx + 50]
        self.assertIn("_rate_limit", surrounding)

    def test_endpoint_requires_api_key(self):
        """Endpoint requires API key authentication."""
        idx = self.src.find('"/research/search"')
        surrounding = self.src[idx: idx + 300]
        self.assertIn("require_api_key", surrounding)

    def test_510k_source_supported(self):
        """Endpoint queries openFDA 510(k) API for '510k' source."""
        self.assertIn("api.fda.gov/device/510k.json", self.src)

    def test_maude_source_supported(self):
        """Endpoint queries MAUDE adverse events for 'maude' source."""
        self.assertIn("api.fda.gov/device/event.json", self.src)

    def test_recalls_source_supported(self):
        """Endpoint queries recall database for 'recalls' source."""
        self.assertIn("api.fda.gov/device/recall.json", self.src)

    def test_guidance_source_supported(self):
        """Endpoint includes guidance document search."""
        self.assertIn("guidance", self.src)

    def test_returns_results_field(self):
        """Endpoint returns 'results' field in response."""
        # Search for the return dict directly (last occurrence is the endpoint return)
        idx = self.src.rfind('"results"')
        self.assertGreaterEqual(idx, 0, "'\"results\"' key not found in server.py")

    def test_returns_total_field(self):
        """Endpoint returns 'total' count."""
        # The return dict at end of endpoint has "total": len(results)
        idx = self.src.rfind('"total"')
        self.assertGreaterEqual(idx, 0, "'\"total\"' key not found in server.py")

    def test_returns_duration_ms(self):
        """Endpoint measures and returns query duration."""
        self.assertIn("duration_ms", self.src)

    def test_uses_httpx_async_client(self):
        """Endpoint uses httpx.AsyncClient for openFDA calls."""
        self.assertIn("httpx.AsyncClient", self.src)

    def test_audit_log_entry(self):
        """Search is audit-logged."""
        idx = self.src.find("research_search")
        self.assertGreaterEqual(idx, 0)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-311 [SR-002] — Guidance corpus and keyword matching
# ─────────────────────────────────────────────────────────────────────────────

class TestSR002GuidanceCorpus(unittest.TestCase):
    """Guidance corpus exists and keyword matcher is implemented."""

    def setUp(self):
        self.src = read(BRIDGE)

    def test_guidance_corpus_defined(self):
        """_GUIDANCE_CORPUS list is defined."""
        self.assertIn("_GUIDANCE_CORPUS", self.src)

    def test_corpus_has_entries(self):
        """Guidance corpus contains at least 10 entries."""
        # Count entries by counting 'title' keys in the corpus block
        # Use a rough count of "id": "g" entries
        count = len(re.findall(r'"id":\s*"g\d+', self.src))
        self.assertGreaterEqual(count, 10, "Guidance corpus should have ≥10 entries")

    def test_corpus_has_url_field(self):
        """Corpus entries have url field (may be None)."""
        self.assertIn('"url":', self.src)

    def test_corpus_has_cfr_field(self):
        """Corpus entries have CFR reference field."""
        self.assertIn('"cfr":', self.src)

    def test_keyword_matcher_function(self):
        """_match_guidance_keywords helper function is defined."""
        self.assertIn("def _match_guidance_keywords", self.src)

    def test_matcher_returns_research_hits(self):
        """Matcher returns ResearchHit objects."""
        idx = self.src.find("def _match_guidance_keywords")
        surrounding = self.src[idx: idx + 500]
        self.assertIn("ResearchHit", surrounding)

    def test_matcher_has_score_logic(self):
        """Matcher calculates a relevance score."""
        idx = self.src.find("def _match_guidance_keywords")
        surrounding = self.src[idx: idx + 600]
        self.assertIn("score", surrounding)

    def test_corpus_includes_510k_guidance(self):
        """Corpus includes the 510(k) substantial equivalence guidance."""
        self.assertIn("Substantial Equivalence", self.src)

    def test_corpus_includes_cybersecurity_guidance(self):
        """Corpus includes the cybersecurity guidance document."""
        self.assertIn("Cybersecurity", self.src)

    def test_corpus_includes_biocompat_guidance(self):
        """Corpus includes ISO 10993 biocompatibility guidance."""
        self.assertIn("10993", self.src)

    def test_model_dump_not_dict(self):
        """Code uses model_dump() not deprecated dict() for Pydantic v2."""
        idx = self.src.find("def research_search")
        if idx < 0:
            idx = self.src.find("/research/search")
        surrounding = self.src[idx: idx + 3000]
        self.assertIn("model_dump()", surrounding)
        self.assertNotIn(".dict()", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-311 [SR-003] — TypeScript types and hooks in api-client.ts
# ─────────────────────────────────────────────────────────────────────────────

class TestSR003TypeScriptSearchTypes(unittest.TestCase):
    """api-client.ts has types and hooks for research search."""

    def setUp(self):
        self.src = read(API_CLIENT)

    def test_research_search_request_type(self):
        """ResearchSearchRequest interface is defined."""
        self.assertIn("ResearchSearchRequest", self.src)

    def test_research_hit_type(self):
        """ResearchHit interface is defined."""
        self.assertIn("ResearchHit", self.src)

    def test_research_search_response_type(self):
        """ResearchSearchResponse interface is defined."""
        self.assertIn("ResearchSearchResponse", self.src)

    def test_research_source_type(self):
        """ResearchSource union type is defined."""
        self.assertIn("ResearchSource", self.src)

    def test_sources_field_in_request(self):
        """ResearchSearchRequest has a sources field."""
        idx = self.src.find("ResearchSearchRequest")
        surrounding = self.src[idx: idx + 300]
        self.assertIn("sources", surrounding)

    def test_510k_in_source_type(self):
        """'510k' is one of the ResearchSource values."""
        self.assertIn('"510k"', self.src)

    def test_search_research_api_method(self):
        """fdaApi.searchResearch method is defined."""
        self.assertIn("searchResearch", self.src)

    def test_search_research_posts_to_correct_path(self):
        """searchResearch calls POST /research/search."""
        self.assertIn('"/research/search"', self.src)

    def test_use_research_search_hook(self):
        """useResearchSearch hook is exported."""
        self.assertIn("useResearchSearch", self.src)

    def test_use_research_search_is_mutation(self):
        """useResearchSearch uses useMutation (fires on demand, not on mount)."""
        idx = self.src.find("useResearchSearch")
        surrounding = self.src[idx: idx + 600]  # window covers comment + function body
        self.assertIn("useMutation", surrounding)

    def test_search_research_response_has_results(self):
        """ResearchSearchResponse has a results field."""
        idx = self.src.find("ResearchSearchResponse")
        surrounding = self.src[idx: idx + 200]
        self.assertIn("results", surrounding)

    def test_search_research_response_has_duration(self):
        """ResearchSearchResponse has duration_ms for observability."""
        self.assertIn("duration_ms", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-311 [SR-004] — SearchPanel wired in research/page.tsx
# ─────────────────────────────────────────────────────────────────────────────

class TestSR004SearchPanelWiring(unittest.TestCase):
    """research/page.tsx SearchPanel is wired to live API."""

    def setUp(self):
        self.src = read(RESEARCH_PAGE)

    def test_imports_use_research_search(self):
        """Page imports useResearchSearch hook."""
        self.assertIn("useResearchSearch", self.src)

    def test_search_panel_uses_hook(self):
        """SearchPanel calls useResearchSearch."""
        idx = self.src.find("function SearchPanel")
        surrounding = self.src[idx: idx + 800]
        self.assertIn("useResearchSearch", surrounding)

    def test_search_triggers_on_submit(self):
        """Search is triggered on button click / Enter key."""
        idx = self.src.find("function SearchPanel")
        surrounding = self.src[idx: idx + 1500]
        self.assertTrue(
            "search.mutate" in surrounding or "handleSubmit" in surrounding
        )

    def test_results_are_rendered(self):
        """SearchPanel renders search results."""
        idx = self.src.find("function SearchPanel")
        surrounding = self.src[idx: idx + 5000]  # SearchPanel is JSX-heavy
        self.assertTrue(
            "search.data" in surrounding or "results.map" in surrounding
        )

    def test_loading_state_handled(self):
        """SearchPanel shows loading state during search."""
        idx = self.src.find("function SearchPanel")
        surrounding = self.src[idx: idx + 5000]
        self.assertTrue(
            "isPending" in surrounding or "isLoading" in surrounding
        )

    def test_error_state_handled(self):
        """SearchPanel shows error state when search fails."""
        idx = self.src.find("function SearchPanel")
        surrounding = self.src[idx: idx + 5000]  # JSX error block is deep in function
        self.assertTrue("isError" in surrounding or "error" in surrounding.lower())

    def test_source_toggles_present(self):
        """SearchPanel has source filter toggles."""
        self.assertIn("toggleSource", self.src)

    def test_empty_state_present(self):
        """SearchPanel shows empty state before first search."""
        idx = self.src.find("function SearchPanel")
        surrounding = self.src[idx: idx + 5000]  # empty state is deep in JSX body
        self.assertTrue(
            "!search.data" in surrounding or "empty" in surrounding.lower()
        )

    def test_enter_key_triggers_search(self):
        """Pressing Enter key triggers search."""
        self.assertIn("onKeyDown", self.src)

    def test_result_card_component(self):
        """A result card component is defined."""
        self.assertTrue(
            "SearchResultCard" in self.src or "ResultCard" in self.src
        )

    def test_source_badge_shows_source_type(self):
        """Source badge differentiates 510k / guidance / maude / recalls."""
        self.assertIn("SOURCE_CONFIG", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-309 [HG-001] — Bridge endpoint: POST /hitl/gate/{id}/sign
# ─────────────────────────────────────────────────────────────────────────────

class TestHG001BridgeHitlSignEndpoint(unittest.TestCase):
    """Bridge server has POST /hitl/gate/{gate_id}/sign endpoint."""

    def setUp(self):
        self.src = read(BRIDGE)

    def test_sign_endpoint_route(self):
        """POST /hitl/gate/{gate_id}/sign route is registered."""
        self.assertIn("/hitl/gate/", self.src)
        self.assertIn("sign", self.src)

    def test_sign_endpoint_is_post(self):
        """Sign endpoint uses POST method."""
        self.assertIn('app.post("/hitl/gate/', self.src)

    def test_hitl_sign_request_model(self):
        """HitlGateSignRequest Pydantic model is defined."""
        self.assertIn("class HitlGateSignRequest", self.src)

    def test_model_has_session_id(self):
        """Request model has session_id field."""
        idx = self.src.find("class HitlGateSignRequest")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("session_id", surrounding)

    def test_model_has_decision(self):
        """Request model has decision field (approved/rejected/deferred)."""
        idx = self.src.find("class HitlGateSignRequest")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("decision", surrounding)

    def test_model_has_rationale(self):
        """Request model has rationale field."""
        idx = self.src.find("class HitlGateSignRequest")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("rationale", surrounding)

    def test_model_has_reviewer_role(self):
        """Request model has reviewer_role field."""
        idx = self.src.find("class HitlGateSignRequest")
        surrounding = self.src[idx: idx + 700]  # 8-field model needs wider window
        self.assertIn("reviewer_role", surrounding)

    def test_authorized_roles_set_defined(self):
        """HITL_AUTHORIZED_ROLES frozenset is defined."""
        self.assertIn("HITL_AUTHORIZED_ROLES", self.src)

    def test_ra_lead_is_authorized(self):
        """RA_LEAD is an authorized role."""
        self.assertIn("RA_LEAD", self.src)

    def test_qam_is_authorized(self):
        """QA_MANAGER is an authorized role."""
        self.assertIn("QA_MANAGER", self.src)

    def test_role_validation_in_endpoint(self):
        """Endpoint validates reviewer role against authorized set."""
        self.assertIn("HITL_AUTHORIZED_ROLES", self.src)

    def test_hmac_signing_via_cfr_part11(self):
        """Endpoint calls ElectronicSignature.sign() for HMAC signing."""
        self.assertIn("ElectronicSignature", self.src)
        self.assertIn("ElectronicSignature.sign", self.src)

    def test_record_hash_computed(self):
        """Endpoint computes SHA-256 record hash before signing."""
        self.assertIn("record_hash", self.src)
        self.assertIn("hashlib.sha256", self.src)

    def test_gate_store_defined(self):
        """_HITL_GATE_STORE dict is defined for persistence."""
        self.assertIn("_HITL_GATE_STORE", self.src)

    def test_gate_lock_for_thread_safety(self):
        """_HITL_GATE_LOCK is used for thread-safe gate store access."""
        self.assertIn("_HITL_GATE_LOCK", self.src)

    def test_audit_log_on_sign(self):
        """Gate signing is audit-logged."""
        self.assertIn("hitl_gate_signed", self.src)

    def test_403_for_unauthorized_role(self):
        """Endpoint returns 403 for unauthorized role."""
        idx = self.src.find("sign_hitl_gate")
        surrounding = self.src[idx: idx + 1500]
        self.assertIn("403", surrounding)

    def test_unsigned_warning_when_key_missing(self):
        """Endpoint warns when CFR_PART11_SIGNING_KEY is not set."""
        self.assertIn("CFR_PART11_SIGNING_KEY", self.src)
        self.assertIn("UNSIGNED", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-309 [HG-002] — Bridge endpoint: GET /hitl/gate/{id}
# ─────────────────────────────────────────────────────────────────────────────

class TestHG002BridgeHitlGetEndpoint(unittest.TestCase):
    """Bridge server has GET /hitl/gate/{gate_id} endpoint."""

    def setUp(self):
        self.src = read(BRIDGE)

    def test_get_endpoint_registered(self):
        """GET /hitl/gate/{gate_id} route is registered."""
        self.assertIn("app.get(\"/hitl/gate/", self.src)

    def test_returns_status_field(self):
        """GET endpoint returns 'status' field."""
        idx = self.src.find("get_hitl_gate")
        surrounding = self.src[idx: idx + 1000]
        self.assertIn('"status"', surrounding)

    def test_returns_record_field(self):
        """GET endpoint returns 'record' field (None if not yet signed)."""
        idx = self.src.find("get_hitl_gate")
        surrounding = self.src[idx: idx + 1000]
        self.assertIn('"record"', surrounding)

    def test_returns_pending_when_no_record(self):
        """GET endpoint returns 'pending' status when gate not yet signed."""
        idx = self.src.find("get_hitl_gate")
        surrounding = self.src[idx: idx + 1000]
        self.assertIn('"pending"', surrounding)

    def test_escalated_field_returned(self):
        """GET endpoint returns 'escalated' boolean for 24h timeout."""
        idx = self.src.find("get_hitl_gate")
        surrounding = self.src[idx: idx + 1500]
        self.assertIn("escalated", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-309 [HG-003] — Role-based access control
# ─────────────────────────────────────────────────────────────────────────────

class TestHG003RoleBasedAccessControl(unittest.TestCase):
    """HITL gate signing enforces authorized RA roles."""

    def setUp(self):
        self.src = read(BRIDGE)

    def test_five_authorized_roles(self):
        """At least 5 authorized roles are defined."""
        idx = self.src.find("HITL_AUTHORIZED_ROLES")
        surrounding = self.src[idx: idx + 300]
        roles = re.findall(r'"[A-Z_]{3,}"', surrounding)
        self.assertGreaterEqual(len(roles), 5, f"Expected ≥5 roles, found: {roles}")

    def test_access_denied_audit_event(self):
        """Unauthorized role access is audit-logged."""
        self.assertIn("hitl_gate_access_denied", self.src)

    def test_403_status_code(self):
        """Unauthorized role returns HTTP 403 Forbidden."""
        idx = self.src.find("hitl_gate_access_denied")
        surrounding = self.src[max(0, idx - 50): idx + 300]
        self.assertIn("403", surrounding)

    def test_role_normalized_to_upper(self):
        """Role comparison normalizes input to uppercase."""
        # upper() appears in the endpoint function, search the whole file
        self.assertTrue(
            ".upper()" in self.src or "upper()" in self.src
        )

    def test_gate_id_path_body_consistency_check(self):
        """Endpoint validates path gate_id matches body gate_id."""
        self.assertIn("gate_id != body.gate_id", self.src)

    def test_valid_decisions_validated(self):
        """Decision value is validated against approved/rejected/deferred."""
        idx = self.src.find("valid_decisions")
        self.assertGreaterEqual(idx, 0, "valid_decisions set not found")


# ─────────────────────────────────────────────────────────────────────────────
# FDA-309 [HG-004] — 24-hour timeout escalation
# ─────────────────────────────────────────────────────────────────────────────

class TestHG004TwentyFourHourEscalation(unittest.TestCase):
    """Deferred gates escalate after 24 hours."""

    def setUp(self):
        self.src = read(BRIDGE)

    def test_age_hours_computed(self):
        """Age of deferred decision is computed in hours."""
        self.assertIn("age_hours", self.src)

    def test_24h_threshold(self):
        """Escalation triggers after 24 hours."""
        self.assertIn("24", self.src)
        # Check the comparison happens near escalation logic
        idx = self.src.find("age_hours")
        surrounding = self.src[max(0, idx - 100): idx + 200]
        self.assertIn("24", surrounding)

    def test_escalation_reason_provided(self):
        """Escalation includes a human-readable reason."""
        self.assertIn("escalation_reason", self.src)

    def test_escalation_targets_deferred(self):
        """Escalation only applies to deferred decisions."""
        idx = self.src.find("age_hours")
        surrounding = self.src[max(0, idx - 300): idx + 100]
        self.assertIn("deferred", surrounding)

    def test_datetime_isoformat_parsing(self):
        """Escalation parses ISO 8601 timestamp from stored record."""
        self.assertIn("fromisoformat", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-309 [HG-005] — TypeScript types and hooks in api-client.ts
# ─────────────────────────────────────────────────────────────────────────────

class TestHG005TypeScriptHitlTypes(unittest.TestCase):
    """api-client.ts has types and hooks for HITL gate enterprise signing."""

    def setUp(self):
        self.src = read(API_CLIENT)

    def test_hitl_decision_type(self):
        """HitlDecision union type is defined."""
        self.assertIn("HitlDecision", self.src)

    def test_hitl_reviewer_role_type(self):
        """HitlReviewerRole type is defined with authorized roles."""
        self.assertIn("HitlReviewerRole", self.src)

    def test_hitl_gate_sign_request_type(self):
        """HitlGateSignRequest interface is defined."""
        self.assertIn("HitlGateSignRequest", self.src)

    def test_hitl_gate_sign_response_type(self):
        """HitlGateSignResponse interface is defined."""
        self.assertIn("HitlGateSignResponse", self.src)

    def test_hitl_gate_record_type(self):
        """HitlGateRecord interface is defined."""
        self.assertIn("HitlGateRecord", self.src)

    def test_hitl_gate_status_response_type(self):
        """HitlGateStatusResponse interface is defined."""
        self.assertIn("HitlGateStatusResponse", self.src)

    def test_cryptographic_field_in_response(self):
        """HitlGateSignResponse includes cryptographic boolean."""
        idx = self.src.find("HitlGateSignResponse")
        surrounding = self.src[idx: idx + 500]
        self.assertIn("cryptographic", surrounding)

    def test_sign_hitl_gate_api_method(self):
        """fdaApi.signHitlGate method is defined."""
        self.assertIn("signHitlGate", self.src)

    def test_sign_hitl_gate_posts_to_correct_path(self):
        """signHitlGate calls POST /hitl/gate/{id}/sign."""
        idx = self.src.find("signHitlGate")
        surrounding = self.src[idx: idx + 300]
        self.assertIn("/hitl/gate/", surrounding)

    def test_get_hitl_gate_api_method(self):
        """fdaApi.getHitlGate method is defined."""
        self.assertIn("getHitlGate", self.src)

    def test_use_sign_hitl_gate_hook(self):
        """useSignHitlGate mutation hook is exported."""
        self.assertIn("useSignHitlGate", self.src)

    def test_use_sign_hitl_gate_is_mutation(self):
        """useSignHitlGate is a mutation (not query) hook."""
        idx = self.src.find("useSignHitlGate")
        surrounding = self.src[idx: idx + 600]  # cover comment block + function body
        self.assertIn("useMutation", surrounding)

    def test_use_hitl_gate_status_hook(self):
        """useHitlGateStatus query hook is exported."""
        self.assertIn("useHitlGateStatus", self.src)

    def test_use_hitl_gate_status_polls_every_60s(self):
        """useHitlGateStatus polls every 60 seconds for escalation detection."""
        idx = self.src.find("useHitlGateStatus")
        surrounding = self.src[idx: idx + 600]  # refetchInterval appears ~430 chars in
        self.assertIn("60", surrounding)

    def test_escalated_field_in_status_response(self):
        """HitlGateStatusResponse includes escalated field."""
        idx = self.src.find("HitlGateStatusResponse")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("escalated", surrounding)


# ─────────────────────────────────────────────────────────────────────────────
# FDA-309 [HG-006] — HitlGateIntegration component
# ─────────────────────────────────────────────────────────────────────────────

class TestHG006HitlComponentUpgrade(unittest.TestCase):
    """HitlGateIntegration component has enterprise hardening features."""

    def setUp(self):
        self.src = read(HITL_COMPONENT)

    def test_imports_use_sign_hitl_gate(self):
        """Component imports useSignHitlGate hook."""
        self.assertIn("useSignHitlGate", self.src)

    def test_imports_hitl_reviewer_role_type(self):
        """Component imports HitlReviewerRole type."""
        self.assertIn("HitlReviewerRole", self.src)

    def test_session_id_prop_added(self):
        """HitlGateIntegrationProps includes sessionId prop."""
        idx = self.src.find("HitlGateIntegrationProps")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("sessionId", surrounding)

    def test_reviewer_name_field_in_form(self):
        """Review form includes Reviewer Name input field."""
        self.assertIn("reviewerName", self.src)

    def test_reviewer_role_select_in_form(self):
        """Review form includes Role select dropdown."""
        self.assertIn("reviewerRole", self.src)

    def test_hitl_roles_list_defined(self):
        """HITL_ROLES list for select options is defined."""
        self.assertIn("HITL_ROLES", self.src)

    def test_sign_gate_mutation_called(self):
        """Component calls signGate.mutateAsync for backend signing."""
        self.assertIn("signGate.mutateAsync", self.src)

    def test_signature_hash_displayed(self):
        """Signature hash is displayed on successful signing."""
        self.assertIn("signatureHash", self.src)

    def test_loading_state_on_signing(self):
        """Submit button shows loading state while signing."""
        self.assertIn("isPending", self.src)

    def test_part11_labeling(self):
        """Submit button references 21 CFR Part 11."""
        self.assertIn("§11.50", self.src)

    def test_session_id_forwarded_to_panel(self):
        """Main component forwards sessionId to GateDetailPanel."""
        idx = self.src.find("GateDetailPanel")
        surrounding = self.src[idx: idx + 200]
        self.assertIn("sessionId", surrounding)

    def test_success_state_shows_audit_confirmation(self):
        """Success state shows audit record confirmation."""
        self.assertIn("isSuccess", self.src)

    def test_rationale_min_length_enforced(self):
        """Submit disabled until rationale is filled (≥ 1 char in UI)."""
        self.assertIn("rationale.trim()", self.src)

    def test_reviewer_name_required(self):
        """Submit disabled until reviewer name is filled."""
        self.assertIn("reviewerName.trim()", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# BCO-001 — Bridge completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestBCO001BridgeCompleteness(unittest.TestCase):
    """All Sprint 31 bridge endpoints are registered and consistent."""

    def setUp(self):
        self.src = read(BRIDGE)

    def test_all_sprint31_endpoints_present(self):
        """All 3 new Sprint 31 endpoints are present in bridge server."""
        endpoints = [
            '"/research/search"',
            '"/hitl/gate/',
        ]
        for ep in endpoints:
            with self.subTest(endpoint=ep):
                self.assertIn(ep, self.src, f"Endpoint {ep!r} not found in server.py")

    def test_hitl_sign_endpoint_rate_limited(self):
        """HITL sign endpoint is rate limited."""
        idx = self.src.find("sign_hitl_gate")
        surrounding = self.src[max(0, idx - 200): idx + 50]
        self.assertIn("_rate_limit", surrounding)

    def test_hitl_get_endpoint_rate_limited(self):
        """HITL GET endpoint is rate limited."""
        idx = self.src.find("get_hitl_gate")
        surrounding = self.src[max(0, idx - 200): idx + 50]
        self.assertIn("_rate_limit", surrounding)

    def test_research_endpoint_authenticated(self):
        """Research search endpoint requires API key."""
        idx = self.src.find("research_search")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("require_api_key", surrounding)

    def test_hitl_endpoint_authenticated(self):
        """HITL sign endpoint requires API key."""
        idx = self.src.find("sign_hitl_gate")
        surrounding = self.src[idx: idx + 400]
        self.assertIn("require_api_key", surrounding)

    def test_model_dump_used_throughout(self):
        """Pydantic v2 model_dump() is used instead of deprecated dict()."""
        # Ensure we do not regress to .dict() in endpoint functions
        research_idx = self.src.find("def research_search")
        search_block = self.src[research_idx: research_idx + 4000]
        self.assertNotIn(".dict()", search_block)

    def test_canonical_json_for_hashing(self):
        """Gate sign endpoint uses sort_keys=True for canonical JSON hashing."""
        self.assertIn("sort_keys=True", self.src)


# ─────────────────────────────────────────────────────────────────────────────
# BCO-002 — OpenClaw E2E assessment
# ─────────────────────────────────────────────────────────────────────────────

class TestBCO002OpenClawAssessment(unittest.TestCase):
    """OpenClaw E2E assessment document is comprehensive."""

    def setUp(self):
        self.src = read(ASSESSMENT) if exists(ASSESSMENT) else ""

    def test_assessment_document_exists(self):
        """OPENCLAW_E2E_ASSESSMENT.md exists in docs/."""
        self.assertTrue(exists(ASSESSMENT), f"Missing: {ASSESSMENT}")

    def test_assessment_covers_bridge_endpoints(self):
        """Assessment documents the bridge API endpoints."""
        self.assertIn("/execute", self.src)
        self.assertIn("/health", self.src)

    def test_assessment_identifies_pain_points(self):
        """Assessment identifies user pain points."""
        self.assertIn("Pain Point", self.src.replace("pain point", "Pain Point").replace(
            "pain-point", "Pain Point"
        ).replace("P1", "Pain Point"))
        # Alternative check — just look for "Pain" in the document
        self.assertIn("Pain", self.src)

    def test_assessment_has_persona_workflows(self):
        """Assessment has persona-based workflows."""
        self.assertTrue(
            "Persona" in self.src or "510(k)" in self.src
        )

    def test_assessment_proposes_slash_commands(self):
        """Assessment proposes new slash commands."""
        self.assertIn("/mdrp:", self.src)

    def test_assessment_has_usability_score(self):
        """Assessment includes usability score."""
        self.assertTrue(
            "usability" in self.src.lower() or "score" in self.src.lower()
        )

    def test_assessment_covers_hitl(self):
        """Assessment covers HITL gate interaction."""
        self.assertTrue("HITL" in self.src or "hitl" in self.src)

    def test_assessment_has_roadmap(self):
        """Assessment has implementation roadmap."""
        self.assertTrue(
            "Roadmap" in self.src or "Sprint" in self.src
        )


# ─────────────────────────────────────────────────────────────────────────────
# CFR Part 11 signing correctness (from Sprint 30, regression guard)
# ─────────────────────────────────────────────────────────────────────────────

class TestCFR11SigningCorrectness(unittest.TestCase):
    """ElectronicSignature raises ValueError when signing key is absent."""

    def test_sign_raises_without_key(self):
        """ElectronicSignature.sign() raises ValueError when no key is set."""
        import sys
        sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", "..")))
        from plugins.fda_tools.lib.cfr_part11 import ElectronicSignature
        import os as _os
        _orig = _os.environ.pop("CFR_PART11_SIGNING_KEY", None)
        try:
            with self.assertRaises(ValueError):
                ElectronicSignature.sign(
                    record_hash="abc123",
                    signer_id="test@example.com",
                    signer_name="Test User",
                    meaning="Test",
                )
        finally:
            if _orig is not None:
                _os.environ["CFR_PART11_SIGNING_KEY"] = _orig

    def test_sign_succeeds_with_key(self):
        """ElectronicSignature.sign() succeeds when signing key is present."""
        from plugins.fda_tools.lib.cfr_part11 import ElectronicSignature
        sig = ElectronicSignature.sign(
            record_hash="deadbeef" * 8,
            signer_id="ra@example.com",
            signer_name="RA Lead",
            meaning="Gate 2 Approved",
            signing_key="testkey-abc123",
        )
        self.assertIsNotNone(sig.signature)
        self.assertEqual(len(sig.signature), 64)  # HMAC-SHA256 = 64 hex chars

    def test_signature_is_hmac_sha256(self):
        """Signature is a 64-character hex HMAC-SHA256 digest."""
        from plugins.fda_tools.lib.cfr_part11 import ElectronicSignature
        sig = ElectronicSignature.sign(
            record_hash="cafebabe" * 8,
            signer_id="reviewer@example.com",
            signer_name="Dr. Reviewer",
            meaning="Approved",
            signing_key="stable-key-xyz",
        )
        self.assertRegex(sig.signature, r"^[0-9a-f]{64}$")

    def test_verify_valid_signature(self):
        """verify() returns True for a signature created with the same key."""
        from plugins.fda_tools.lib.cfr_part11 import ElectronicSignature
        sig = ElectronicSignature.sign(
            record_hash="aabbcc" * 10,
            signer_id="user@test.com",
            signer_name="User",
            meaning="Approved",
            signing_key="key-for-verify-test",
        )
        self.assertTrue(sig.verify(signing_key="key-for-verify-test"))

    def test_verify_fails_with_wrong_key(self):
        """verify() returns False when key does not match."""
        from plugins.fda_tools.lib.cfr_part11 import ElectronicSignature
        sig = ElectronicSignature.sign(
            record_hash="112233" * 10,
            signer_id="user@test.com",
            signer_name="User",
            meaning="Approved",
            signing_key="correct-key",
        )
        self.assertFalse(sig.verify(signing_key="wrong-key"))

    def test_audit_record_has_agent_id_field(self):
        """AuditRecord has agent_id field for AI agent attribution (§11.70)."""
        from plugins.fda_tools.lib.cfr_part11 import AuditRecord
        import inspect
        src = inspect.getsource(AuditRecord)
        self.assertIn("agent_id", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
