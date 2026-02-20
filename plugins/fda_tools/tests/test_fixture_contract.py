"""Quarterly API contract tests for fixture staleness detection (FDA-56).

These tests fetch ONE real response from each openFDA endpoint and validate
that the response structure matches the fields used in test fixtures.  If the
API changes its schema, these tests will fail while offline fixture-based
tests continue to pass -- alerting the team to update fixtures.

Run quarterly:
    pytest -m api_contract -v

Skip in CI or offline runs:
    pytest -m "not api_contract"

When a test fails:
    1. Read the assertion message to identify the missing/renamed field.
    2. Check https://open.fda.gov/apis/device/ for the updated schema.
    3. Update the fixture file(s) in tests/fixtures/ to match.
    4. Bump ``api_schema_version`` in each fixture's ``_fixture_meta``.
    5. Re-run ``pytest -m api_contract`` to confirm the fix.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

# Mark every test in this module with both 'api' and 'api_contract'
pytestmark = [pytest.mark.api, pytest.mark.api_contract]

BASE_URL = "https://api.fda.gov/device"
HEADERS = {"User-Agent": "Mozilla/5.0 (FDA-Plugin-FixtureContract/1.0)"}
TIMEOUT = 15

FIXTURES_DIR = Path(__file__).parent.resolve() / "fixtures"

# --------------------------------------------------------------------------
# The canonical field sets that our fixtures depend on.
# If the API removes or renames any of these, fixtures are stale.
# --------------------------------------------------------------------------

CLEARANCE_510K_REQUIRED_FIELDS = {
    "k_number",
    "device_name",
    "applicant",
    "decision_date",
    "product_code",
}

CLEARANCE_510K_OPTIONAL_FIELDS = {
    "decision_code",
    "clearance_type",
    "date_received",
    "statement_or_summary",
    "review_advisory_committee",
}

RECALL_REQUIRED_FIELDS = {
    "product_code",
}

RECALL_COMMON_FIELDS = {
    "res_event_number",
    "event_type",
    "reason_for_recall",
}

META_REQUIRED_STRUCTURE = {"meta", "results"}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _api_get(endpoint: str, search: str, limit: int = 1) -> dict:
    """Make a single openFDA API request and return parsed JSON."""
    params = {"search": search, "limit": str(limit)}
    url = f"{BASE_URL}/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        pytest.skip(f"API returned HTTP {exc.code} -- skipping contract test")
    except urllib.error.URLError:
        pytest.skip("Network unavailable -- skipping contract test")


def _load_fixture_raw(filename: str) -> dict:
    """Load a fixture file including _fixture_meta."""
    path = FIXTURES_DIR / filename
    with open(path) as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Contract Tests -- 510(k) clearances
# --------------------------------------------------------------------------

class TestClearanceFixtureContract:
    """Validate that the live 510(k) API response matches fixture structure."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1.5)

    def test_live_clearance_has_required_fields(self):
        """Fetch one real 510(k) clearance and verify required fields exist."""
        data = _api_get("510k", 'product_code:"DQY"', limit=1)
        result = data["results"][0]

        missing = CLEARANCE_510K_REQUIRED_FIELDS - set(result.keys())
        assert not missing, (
            f"openFDA /device/510k response is missing fields that our "
            f"fixtures depend on: {missing}. Update fixtures and bump "
            f"api_schema_version."
        )

    def test_live_clearance_meta_structure(self):
        """Verify meta.results.total structure still exists."""
        data = _api_get("510k", 'product_code:"DQY"', limit=1)

        assert "meta" in data, "Response missing 'meta' key"
        assert "results" in data["meta"], "meta missing 'results' key"
        assert "total" in data["meta"]["results"], "meta.results missing 'total' key"
        assert isinstance(data["meta"]["results"]["total"], int), (
            "meta.results.total is not an integer"
        )

    def test_fixture_clearance_fields_match_live_api(self):
        """Cross-check fixture clearance fields against live API response."""
        data = _api_get("510k", 'product_code:"DQY"', limit=1)
        live_fields = set(data["results"][0].keys())

        fixture = _load_fixture_raw("sample_api_responses.json")
        fixture_result = fixture["clearances_dqy_5_items"]["results"][0]
        fixture_fields = set(fixture_result.keys())

        # Every field in our fixture should exist in the live response
        stale_fields = fixture_fields - live_fields
        assert not stale_fields, (
            f"Fixture contains fields not found in live API: {stale_fields}. "
            f"The API may have renamed or removed them."
        )


# --------------------------------------------------------------------------
# Contract Tests -- Recalls
# --------------------------------------------------------------------------

class TestRecallFixtureContract:
    """Validate that the live recall API response matches fixture structure."""

    @pytest.fixture(autouse=True)
    def _rate_limit(self):
        yield
        time.sleep(1.5)

    def test_live_recall_has_product_code(self):
        """Fetch one real recall and verify product_code field exists."""
        data = _api_get("recall", 'product_code:"KGN"', limit=1)
        result = data["results"][0]

        assert "product_code" in result, (
            "openFDA /device/recall response missing 'product_code' field"
        )

    def test_live_recall_meta_structure(self):
        """Verify recall endpoint meta structure."""
        data = _api_get("recall", 'product_code:"KGN"', limit=1)

        assert "meta" in data
        assert "results" in data["meta"]
        assert "total" in data["meta"]["results"]


# --------------------------------------------------------------------------
# Fixture Metadata Validation
# --------------------------------------------------------------------------

class TestFixtureMetadata:
    """Validate that all fixtures have proper _fixture_meta tracking (FDA-56)."""

    FIXTURE_FILES = [
        "sample_api_responses.json",
        "sample_fingerprints.json",
        "sample_section_data.json",
        "sample_review.json",
    ]

    @pytest.mark.parametrize("fixture_file", FIXTURE_FILES)
    def test_fixture_has_meta(self, fixture_file):
        """Every fixture file must have _fixture_meta with required keys."""
        data = _load_fixture_raw(fixture_file)

        assert "_fixture_meta" in data, (
            f"{fixture_file} missing _fixture_meta key. "
            f"Add api_schema_version tracking per FDA-56."
        )

        meta = data["_fixture_meta"]
        required_keys = {"api_schema_version", "created_at", "last_validated"}
        missing = required_keys - set(meta.keys())
        assert not missing, (
            f"{fixture_file} _fixture_meta missing keys: {missing}"
        )

    @pytest.mark.parametrize("fixture_file", FIXTURE_FILES)
    def test_fixture_schema_version_is_semver(self, fixture_file):
        """api_schema_version must follow semver format (X.Y.Z)."""
        import re

        data = _load_fixture_raw(fixture_file)
        meta = data.get("_fixture_meta", {})
        version = meta.get("api_schema_version", "")

        assert re.match(r"^\d+\.\d+\.\d+$", version), (
            f"{fixture_file} api_schema_version '{version}' is not valid semver"
        )
