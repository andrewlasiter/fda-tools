"""
Shared pytest fixtures for FDA Tools Quick Wins test suite.

Provides reusable fixtures for temporary project directories, sample
fingerprints, mock API responses, section data, and mock FDA clients.
All fixtures operate offline without network access.

Path resolution strategy (FDA-55):
    This conftest.py resolves paths relative to its own filesystem location
    so that tests work regardless of CWD, pytest-xdist parallelism, or IDE
    test runner invocation.  The primary mechanism is pytest.ini's
    ``pythonpath = . scripts lib tests`` setting; the sys.path fallback
    below exists only to support edge-case environments where pytest.ini
    is not honoured (e.g. bare ``python -m pytest`` from an unexpected
    directory).
"""

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Portable path resolution (FDA-55)
# ---------------------------------------------------------------------------
# Resolve directories relative to *this file*, not relative to CWD.
# This makes the test suite work from any working directory and with
# pytest-xdist (which may spawn workers with a different CWD).

TESTS_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_DIR.parent.resolve()           # plugins/fda-tools
FIXTURES_DIR = TESTS_DIR / "fixtures"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LIB_DIR = PROJECT_ROOT / "lib"

# Ensure all package roots are on sys.path (idempotent).
# Order: PROJECT_ROOT first so that ``import scripts.xxx`` and
# ``import lib.xxx`` both work; then the individual dirs so that bare
# ``import xxx`` also resolves for legacy test files.
for _dir in (PROJECT_ROOT, SCRIPTS_DIR, LIB_DIR, TESTS_DIR):
    _dir_str = str(_dir)
    if _dir_str not in sys.path:
        sys.path.insert(0, _dir_str)

# Import from tests package (using proper package import)
from tests.mocks.mock_fda_client import MockFDAClient


def _load_fixture(filename):
    """Load a JSON fixture file from the fixtures directory.

    Automatically strips the ``_fixture_meta`` key (FDA-56) so that test
    code sees only the payload data.
    """
    filepath = FIXTURES_DIR / filename
    with open(filepath) as f:
        data = json.load(f)
    # Strip fixture metadata (FDA-56) so tests see only payload data
    if isinstance(data, dict):
        data.pop("_fixture_meta", None)
    return data


# ---------------------------------------------------------------------------
# Fixture Data Loaders
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_fingerprints():
    """Load sample fingerprint data for DQY, OVE, and GEI product codes.

    Returns:
        Dict mapping product code to fingerprint dict.
    """
    return _load_fixture("sample_fingerprints.json")


@pytest.fixture
def sample_api_responses():
    """Load sample FDA API response data for various scenarios.

    Contains clearance responses, recall responses, and error responses
    keyed by descriptive scenario names.

    Returns:
        Dict mapping scenario name to API response dict.
    """
    return _load_fixture("sample_api_responses.json")


@pytest.fixture
def sample_section_data():
    """Load sample section data for similarity and trend tests.

    Contains 8 devices across product codes DQY (5 devices) and OVE (3 devices)
    with clinical_testing and biocompatibility sections spanning 2024.

    Returns:
        Dict mapping K-number to device data dict.
    """
    return _load_fixture("sample_section_data.json")


# ---------------------------------------------------------------------------
# Temporary Project Directory
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Create a temporary project directory with a minimal data_manifest.json.

    The manifest contains a single product code (DQY) and no fingerprints,
    simulating a project where batchfetch has been run but no change
    detection has occurred yet.

    Yields:
        str: Absolute path to the temporary project directory.
    """
    manifest = {
        "project": "test_project",
        "product_codes": ["DQY"],
        "queries": {},
    }
    manifest_path = tmp_path / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    yield str(tmp_path)


@pytest.fixture
def tmp_project_dir_with_fingerprint(tmp_path, sample_fingerprints):
    """Create a temporary project directory with an existing DQY fingerprint.

    Useful for tests that need to detect changes against an existing baseline.

    Yields:
        str: Absolute path to the temporary project directory.
    """
    manifest = {
        "project": "test_project",
        "product_codes": ["DQY"],
        "queries": {},
        "fingerprints": {
            "DQY": sample_fingerprints["DQY"],
        },
    }
    manifest_path = tmp_path / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    yield str(tmp_path)


@pytest.fixture
def tmp_project_dir_empty_manifest(tmp_path):
    """Create a temporary project directory with an empty manifest.

    Simulates a project with no product codes and no fingerprints.

    Yields:
        str: Absolute path to the temporary project directory.
    """
    manifest = {}
    manifest_path = tmp_path / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    yield str(tmp_path)


@pytest.fixture
def tmp_project_dir_multi_codes(tmp_path, sample_fingerprints):
    """Create a temporary project with multiple product codes and fingerprints.

    Yields:
        str: Absolute path to the temporary project directory.
    """
    manifest = {
        "project": "test_multi",
        "product_codes": ["DQY", "OVE", "GEI"],
        "queries": {},
        "fingerprints": sample_fingerprints,
    }
    manifest_path = tmp_path / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    yield str(tmp_path)


# ---------------------------------------------------------------------------
# Mock FDA Client Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_fda_client_with_new_clearances(sample_api_responses):
    """Create a MockFDAClient that returns 2 new + 3 existing clearances for DQY.

    The response includes K261001 and K261002 (new) plus K241001-K241003 (existing
    in sample fingerprint). Recall count stays at 3.
    """
    client = MockFDAClient()
    resp = sample_api_responses["clearances_dqy_5_items"]
    client.set_clearances("DQY", meta_total=resp["meta"]["results"]["total"],
                          results=resp["results"])
    client.set_recalls("DQY", meta_total=3)
    return client


@pytest.fixture
def mock_fda_client_stable(sample_api_responses):
    """Create a MockFDAClient that returns exactly the known clearances and recalls.

    No new clearances, no new recalls. Matches the DQY fingerprint baseline.
    """
    client = MockFDAClient()
    # Return only the 2 known items (matching known_k_numbers subset)
    resp = sample_api_responses["clearances_stable_2_items"]
    client.set_clearances("DQY", meta_total=resp["meta"]["results"]["total"],
                          results=resp["results"])
    client.set_recalls("DQY", meta_total=1)
    return client


@pytest.fixture
def mock_fda_client_error():
    """Create a MockFDAClient that returns API errors for all product codes."""
    return MockFDAClient(default_error=True)


@pytest.fixture
def mock_fda_client_3_new_items(sample_api_responses):
    """Create a MockFDAClient that returns 3 clearances for empty-known-list scenario.

    All 3 clearances should be detected as new since the known list is empty.
    """
    client = MockFDAClient()
    resp = sample_api_responses["clearances_3_new_items"]
    client.set_clearances("DQY", meta_total=resp["meta"]["results"]["total"],
                          results=resp["results"])
    client.set_recalls("DQY", meta_total=0)
    return client


@pytest.fixture
def mock_fda_client_with_recalls(sample_api_responses):
    """Create a MockFDAClient with increased recall count (from 2 to 4) for DQY.

    Returns stable clearances but recall count has increased from 2 to 4,
    simulating 2 new recalls detected.
    """
    client = MockFDAClient()
    resp = sample_api_responses["clearances_stable_2_items"]
    client.set_clearances("DQY", meta_total=resp["meta"]["results"]["total"],
                          results=resp["results"])
    client.set_recalls("DQY", meta_total=4)  # Increased from baseline of 2
    return client


# ---------------------------------------------------------------------------
# Portable Path Fixtures (FDA-55)
# ---------------------------------------------------------------------------
# These fixtures provide absolute paths resolved from this file's location,
# making tests CWD-independent and compatible with pytest-xdist and IDEs.


@pytest.fixture
def plugin_root():
    """Return the absolute path to the plugin root (plugins/fda-tools/).

    Use this instead of computing paths from os.getcwd().
    """
    return PROJECT_ROOT


@pytest.fixture
def scripts_dir():
    """Return the absolute path to the scripts directory."""
    return SCRIPTS_DIR


@pytest.fixture
def lib_dir():
    """Return the absolute path to the lib directory."""
    return LIB_DIR


@pytest.fixture
def fixtures_dir():
    """Return the absolute path to the test fixtures directory."""
    return FIXTURES_DIR
