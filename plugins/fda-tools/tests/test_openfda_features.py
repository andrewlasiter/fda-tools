"""Tests for openFDA API features: wildcard, sort, skip, OR batch, _missing_/_exists_.

Validates that the API reference, commands, and FDAClient all leverage the full
set of openFDA query parameters (sort, skip, search_after, OR batching, wildcards).

These tests do NOT require API access unless marked @pytest.mark.api.
"""

import os
import sys
import pytest

# Add scripts directory to path for import
# Package imports configured in conftest.py and pytest.ini

# Paths to plugin files
PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), "..")
REF_PATH = os.path.join(PLUGIN_ROOT, "skills", "fda-510k-knowledge", "references", "openfda-api.md")
EXTRACT_PATH = os.path.join(PLUGIN_ROOT, "commands", "extract.md")
SAFETY_PATH = os.path.join(PLUGIN_ROOT, "commands", "safety.md")
RESEARCH_PATH = os.path.join(PLUGIN_ROOT, "commands", "research.md")
VALIDATE_PATH = os.path.join(PLUGIN_ROOT, "commands", "validate.md")
MONITOR_PATH = os.path.join(PLUGIN_ROOT, "commands", "monitor.md")
CLIENT_PATH = os.path.join(PLUGIN_ROOT, "scripts", "fda_api_client.py")
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, "commands")


def _read(path):
    with open(path) as f:
        return f.read()


# ──────────────────────────────────────────────
# Reference content tests
# ──────────────────────────────────────────────

class TestReferenceWildcard:
    """Wildcard should be documented as supported, not 'Not supported'."""

    def test_wildcard_documented_as_supported(self):
        content = _read(REF_PATH)
        assert "Not supported" not in content, "Wildcard should not say 'Not supported'"

    def test_wildcard_syntax_shown(self):
        content = _read(REF_PATH)
        assert "field:prefix*" in content or "prefix*" in content


class TestReferenceTemplate:
    """The fda_api() template function should include sort and skip params."""

    def test_template_has_sort_parameter(self):
        content = _read(REF_PATH)
        assert "sort=None" in content

    def test_template_has_skip_parameter(self):
        content = _read(REF_PATH)
        assert "skip=0" in content

    def test_template_passes_sort_to_params(self):
        content = _read(REF_PATH)
        assert 'params["sort"] = sort' in content

    def test_template_passes_skip_to_params(self):
        content = _read(REF_PATH)
        assert 'params["skip"]' in content


class TestReferenceSearchSyntax:
    """Search syntax section should document OR batch, _missing_/_exists_, grouping, sort."""

    def test_has_exists_filter(self):
        content = _read(REF_PATH)
        assert "_exists_" in content

    def test_has_parenthetical_grouping(self):
        content = _read(REF_PATH)
        assert "Parenthetical grouping" in content

    def test_has_or_batch_query(self):
        content = _read(REF_PATH)
        assert "OR batch query" in content

    def test_has_sort_entry(self):
        content = _read(REF_PATH)
        assert "sort=field:asc" in content or "sort=field:desc" in content


class TestReferencePagination:
    """Pagination section should mention search_after for deep paging."""

    def test_has_search_after(self):
        content = _read(REF_PATH)
        assert "search_after" in content

    def test_has_deep_paging_note(self):
        content = _read(REF_PATH)
        assert "Deep paging" in content or "26,000" in content


# ──────────────────────────────────────────────
# Command content tests
# ──────────────────────────────────────────────

class TestExtractBatching:
    """extract.md should use OR batch pattern for safety scan."""

    def test_extract_has_or_batch(self):
        content = _read(EXTRACT_PATH)
        assert "+OR+" in content, "extract.md should use OR batch queries"

    def test_extract_no_individual_loop(self):
        """Should not loop over top_5 with individual API calls."""
        content = _read(EXTRACT_PATH)
        # The old pattern was 'for knumber in top_5:' with individual URL per K
        # New pattern does batch lookup then iterates results
        assert "batch_search" in content or 'batch_search = "+OR+"' in content


class TestSafetyBatching:
    """safety.md should use fda_data_store for API access and batch operations."""

    def test_peer_benchmark_uses_data_store_or_batch(self):
        content = _read(SAFETY_PATH)
        # v5.19.0+ migrated to fda_data_store.py for API access
        assert ("fda_data_store" in content or "+OR+" in content or
                'count_field="device.device_report_product_code.exact"' in content)

    def test_events_by_year_uses_data_store_or_count(self):
        content = _read(SAFETY_PATH)
        # v5.19.0+ uses fda_data_store.py which handles count queries internally
        assert ('count_field="date_received"' in content or
                "fda_data_store" in content), \
            "safety.md should use fda_data_store or count_field for year trend"

    def test_no_year_range_loop(self):
        """Year-by-year loop should be replaced with single count query."""
        content = _read(SAFETY_PATH)
        # Old pattern was 'for year in range(2020, 2027)' with individual calls
        assert "year_totals" in content, "Should aggregate daily buckets into year_totals"

    def test_narrative_fetch_has_sort(self):
        content = _read(SAFETY_PATH)
        assert "date_received:desc" in content, \
            "Narrative fetch should sort by date_received:desc"

    def test_recall_fetch_has_sort(self):
        content = _read(SAFETY_PATH)
        assert "event_date_terminated:desc" in content, \
            "Recent recalls should sort by event_date_terminated:desc"


class TestResearchBatching:
    """research.md should use fda_data_store or OR batch for predicate lookups."""

    def test_research_has_data_store_or_batch(self):
        content = _read(RESEARCH_PATH)
        # v5.19.0+ migrated to fda_data_store.py for API access
        assert ("fda_data_store" in content or "+OR+" in content), \
            "research.md should use fda_data_store or OR batch queries"

    def test_research_batch_or_data_store_pattern(self):
        content = _read(RESEARCH_PATH)
        assert ("batch_search" in content or "fda_data_store" in content), \
            "research.md should use fda_data_store or batch_search pattern"


class TestValidateSort:
    """validate.md --search mode should include sort parameter."""

    def test_validate_has_sort_parameter(self):
        content = _read(VALIDATE_PATH)
        assert "decision_date:desc" in content

    def test_validate_argument_hint_shows_sort(self):
        content = _read(VALIDATE_PATH)
        assert "--sort" in content


class TestMonitorBatching:
    """monitor.md should use OR batch for product code checks."""

    def test_monitor_has_or_batch(self):
        content = _read(MONITOR_PATH)
        assert "+OR+" in content, "monitor.md should use OR batch queries"


# ──────────────────────────────────────────────
# Tier 2 command batching tests (newly batched)
# ──────────────────────────────────────────────

LINEAGE_PATH = os.path.join(COMMANDS_DIR, "lineage.md")
REVIEW_PATH = os.path.join(COMMANDS_DIR, "review.md")
COMPARE_SE_PATH = os.path.join(COMMANDS_DIR, "compare-se.md")
IMPORT_PATH = os.path.join(COMMANDS_DIR, "import.md")
PROPOSE_PATH = os.path.join(COMMANDS_DIR, "propose.md")


class TestLineageBatching:
    """lineage.md should use batch OR queries."""

    def test_lineage_gen0_batch(self):
        content = _read(LINEAGE_PATH)
        assert "batch_search" in content or "+OR+" in content, \
            "lineage.md Gen 0 should use batch OR query"

    def test_lineage_recall_batch(self):
        content = _read(LINEAGE_PATH)
        assert "Batch recall check" in content, \
            "lineage.md Step 3 should batch recall checks"


class TestReviewBatching:
    """review.md should use fda_data_store or batch OR queries."""

    def test_review_product_code_data_store_or_batch(self):
        content = _read(REVIEW_PATH)
        assert ("fda_data_store" in content or "Batch lookup" in content or
                "batch_search" in content), \
            "review.md should use fda_data_store or batch product code lookups"

    def test_review_safety_data_store_or_batch(self):
        content = _read(REVIEW_PATH)
        assert ("fda_data_store" in content or "Batch safety check" in content or
                "Batch recall check" in content), \
            "review.md should use fda_data_store or batch safety checks"

    def test_review_fda_query_has_data_store_or_count(self):
        content = _read(REVIEW_PATH)
        assert ("fda_data_store" in content or "count_field" in content), \
            "review.md should use fda_data_store or count_field parameter"


class TestCompareSEBatching:
    """compare-se.md should use batch OR query for device lookups."""

    def test_compare_se_batch_lookup(self):
        content = _read(COMPARE_SE_PATH)
        assert "Batch lookup" in content or "+OR+" in content, \
            "compare-se.md should batch all device lookups"

    def test_compare_se_all_knumbers(self):
        content = _read(COMPARE_SE_PATH)
        assert "all_knumbers" in content, \
            "compare-se.md should collect all K-numbers for batch"


class TestImportBatching:
    """import.md should use batch OR query for predicate validation."""

    def test_import_predicate_batch(self):
        content = _read(IMPORT_PATH)
        assert "batch" in content.lower() or "+OR+" in content, \
            "import.md should batch predicate validation"


class TestProposeBatching:
    """propose.md should use batch queries for validation and safety."""

    def test_propose_validation_batch(self):
        content = _read(PROPOSE_PATH)
        assert "Batch lookup" in content or "+OR+" in content, \
            "propose.md should batch device validation"

    def test_propose_recall_batch(self):
        content = _read(PROPOSE_PATH)
        assert "Batch recall" in content, \
            "propose.md should batch recall checks"

    def test_propose_death_batch(self):
        content = _read(PROPOSE_PATH)
        assert "Batch MAUDE" in content, \
            "propose.md should batch death event checks"


# ──────────────────────────────────────────────
# API reference: enforcement endpoint & data dictionary
# ──────────────────────────────────────────────

class TestEnforcementDocs:
    """openfda-api.md should document the /device/enforcement endpoint."""

    def test_enforcement_section_exists(self):
        content = _read(REF_PATH)
        assert "/device/enforcement" in content, \
            "API reference should document /device/enforcement endpoint"

    def test_enforcement_classification_documented(self):
        content = _read(REF_PATH)
        # Verify the old error is fixed — classification is NOT only in enforcement
        assert "NOT `/device/recall`" not in content, \
            "The old error claiming classification is only in enforcement should be removed"

    def test_enforcement_classification_both_endpoints(self):
        content = _read(REF_PATH)
        assert "BOTH `/device/recall` AND `/device/enforcement`" in content, \
            "Should document that classification is in both recall and enforcement"


class TestDataDictionary:
    """Data dictionary reference should exist and cover all endpoints."""

    DICT_PATH = os.path.join(
        os.path.dirname(COMMANDS_DIR), "skills", "fda-510k-knowledge",
        "references", "openfda-data-dictionary.md"
    )

    def test_data_dictionary_exists(self):
        assert os.path.isfile(self.DICT_PATH), \
            f"Data dictionary reference should exist at {self.DICT_PATH}"

    def test_data_dictionary_has_key_endpoints(self):
        content = _read(self.DICT_PATH)
        # All 9 openFDA device endpoints should be documented
        for term in ["device/event", "device/recall", "device/510k",
                      "device/classification", "device/registrationlisting",
                      "device/pma", "device/udi"]:
            assert term in content, \
                f"Data dictionary should document {term}"

    def test_data_dictionary_has_endpoint_count(self):
        content = _read(self.DICT_PATH)
        assert "Endpoints: 9" in content, \
            "Data dictionary should document all 9 openFDA device endpoints"


# ──────────────────────────────────────────────
# README data protection section
# ──────────────────────────────────────────────

class TestREADMEDisclaimer:
    """README should have prominent data protection guidance."""

    README_PATH = os.path.join(os.path.dirname(COMMANDS_DIR), "README.md")

    def test_readme_has_confidential_warning(self):
        content = _read(self.README_PATH)
        assert "CONFIDENTIAL DATA WARNING" in content, \
            "README should have a prominent confidential data warning"

    def test_readme_has_protecting_data_section(self):
        content = _read(self.README_PATH)
        assert "Protecting Your Data" in content, \
            "README should have a Protecting Your Data section"

    def test_readme_has_account_type_table(self):
        content = _read(self.README_PATH)
        assert "Team / Enterprise" in content and "Free / Pro / Max" in content, \
            "README should explain training policy by account type"

    def test_readme_links_to_privacy_settings(self):
        content = _read(self.README_PATH)
        assert "claude.ai/settings/data-privacy-controls" in content, \
            "README should link to privacy settings"


# ──────────────────────────────────────────────
# FDAClient tests
# ──────────────────────────────────────────────

class TestFDAClientFeatures:
    """FDAClient should have batch_510k, sort passthrough, and correct version."""

    @pytest.fixture
    def client(self, tmp_path):
        from fda_api_client import FDAClient
        c = FDAClient(cache_dir=str(tmp_path / "cache"))
        c.enabled = False
        return c

    def test_batch_510k_method_exists(self, client):
        assert hasattr(client, "batch_510k"), "FDAClient should have batch_510k method"

    def test_batch_510k_empty_list(self, client):
        result = client.batch_510k([])
        assert result["results"] == []
        assert result["meta"]["results"]["total"] == 0

    def test_search_510k_has_sort_param(self):
        """search_510k should accept sort parameter."""
        from fda_api_client import FDAClient
        import inspect
        sig = inspect.signature(FDAClient.search_510k)
        assert "sort" in sig.parameters

    def test_get_clearances_has_sort_param(self):
        """get_clearances should accept sort parameter."""
        from fda_api_client import FDAClient
        import inspect
        sig = inspect.signature(FDAClient.get_clearances)
        assert "sort" in sig.parameters

    def test_get_clearances_default_sort(self):
        """get_clearances should default to decision_date:desc."""
        from fda_api_client import FDAClient
        import inspect
        sig = inspect.signature(FDAClient.get_clearances)
        default = sig.parameters["sort"].default
        assert default == "decision_date:desc"

    def test_user_agent_version(self):
        from fda_api_client import USER_AGENT
        from version import PLUGIN_VERSION
        assert PLUGIN_VERSION in USER_AGENT, \
            f"USER_AGENT should include plugin version {PLUGIN_VERSION}, got: {USER_AGENT}"


# ──────────────────────────────────────────────
# API tests (require network)
# ──────────────────────────────────────────────

@pytest.mark.api
class TestAPIFeatures:
    """Live API tests — require network access. Run with: pytest -m api"""

    def test_sort_returns_ordered_results(self):
        from fda_api_client import FDAClient
        client = FDAClient()
        result = client.get_clearances("OVE", limit=5, sort="decision_date:desc")
        if result.get("degraded"):
            pytest.skip("API unavailable")
        results = result.get("results", [])
        if len(results) >= 2:
            dates = [r.get("decision_date", "") for r in results]
            assert dates == sorted(dates, reverse=True), \
                f"Results should be sorted desc: {dates}"

    def test_or_batch_returns_multiple(self, tmp_path):
        from fda_api_client import FDAClient
        client = FDAClient(cache_dir=str(tmp_path / "api_test_cache"))
        result = client.batch_510k(["K241335", "K232318"])
        if result.get("degraded"):
            pytest.skip("API unavailable")
        total = result.get("meta", {}).get("results", {}).get("total", 0)
        assert total >= 1, "OR batch should return at least 1 result"

    def test_skip_offsets_results(self, tmp_path):
        """Verify skip parameter returns different results than offset 0."""
        from fda_api_client import FDAClient
        client = FDAClient(cache_dir=str(tmp_path / "skip_cache"))
        # First page
        r1 = client._request("510k", {
            "search": 'product_code:"OVE"',
            "limit": "5",
            "sort": "decision_date:desc"
        })
        if r1.get("degraded"):
            pytest.skip("API unavailable")
        # Second page (skip 5)
        import time
        time.sleep(0.5)
        r2 = client._request("510k", {
            "search": 'product_code:"OVE"',
            "limit": "5",
            "skip": "5",
            "sort": "decision_date:desc"
        })
        if r2.get("degraded"):
            pytest.skip("API unavailable")
        k1 = [r.get("k_number") for r in r1.get("results", [])]
        k2 = [r.get("k_number") for r in r2.get("results", [])]
        # The two pages should not overlap
        assert set(k1).isdisjoint(set(k2)), \
            f"Skip=5 should return different K-numbers: page1={k1}, page2={k2}"

    def test_wildcard_search(self, tmp_path):
        """Verify wildcard prefix search works on the API."""
        from fda_api_client import FDAClient
        client = FDAClient(cache_dir=str(tmp_path / "wildcard_cache"))
        # Search for applicants starting with "MEDTRONIC"
        result = client._request("510k", {
            "search": 'applicant:MEDTRONIC*',
            "limit": "3"
        })
        if result.get("degraded"):
            pytest.skip("API unavailable")
        total = result.get("meta", {}).get("results", {}).get("total", 0)
        assert total > 0, "Wildcard search for MEDTRONIC* should return results"

    @pytest.mark.skip(reason="_missing_ returns 404 on all Device endpoints — documented as unsupported")
    def test_missing_field_filter(self, tmp_path):
        """_missing_ filter is NOT supported on Device API endpoints (returns 404)."""
        pass

    def test_exists_field_filter(self, tmp_path):
        """Verify _exists_ field filter works."""
        from fda_api_client import FDAClient
        client = FDAClient(cache_dir=str(tmp_path / "exists_cache"))
        result = client._request("510k", {
            "search": '_exists_:third_party_flag',
            "limit": "3"
        })
        if result.get("degraded"):
            pytest.skip("API unavailable")
        total = result.get("meta", {}).get("results", {}).get("total", 0)
        assert total > 0, "_exists_:third_party_flag should find records"
        # Verify the field actually exists in returned results
        for r in result.get("results", []):
            assert "third_party_flag" in r, \
                f"Result should have third_party_flag: {r.get('k_number')}"

    def test_count_field_returns_buckets(self, tmp_path):
        """Verify count_field returns aggregated buckets."""
        from fda_api_client import FDAClient
        client = FDAClient(cache_dir=str(tmp_path / "count_cache"))
        result = client._request("510k", {
            "search": 'product_code:"OVE"',
            "count": "decision_code.exact"
        })
        if result.get("degraded"):
            pytest.skip("API unavailable")
        results = result.get("results", [])
        assert len(results) > 0, "Count query should return buckets"
        # Each bucket should have 'term' and 'count'
        for bucket in results:
            assert "term" in bucket, f"Bucket missing 'term': {bucket}"
            assert "count" in bucket, f"Bucket missing 'count': {bucket}"

    def test_enforcement_classification_field(self, tmp_path):
        """Verify /device/enforcement supports classification field."""
        from fda_api_client import FDAClient
        client = FDAClient(cache_dir=str(tmp_path / "enforcement_cache"))
        result = client._request("enforcement", {
            "search": 'classification:"Class I"',
            "limit": "3"
        })
        if result.get("degraded"):
            pytest.skip("API unavailable")
        total = result.get("meta", {}).get("results", {}).get("total", 0)
        assert total > 0, "Enforcement Class I search should return results"
