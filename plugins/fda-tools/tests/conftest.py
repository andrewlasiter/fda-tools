"""
Shared pytest fixtures for FDA Tools Quick Wins test suite.

Provides reusable fixtures for temporary project directories, sample
fingerprints, mock API responses, section data, and mock FDA clients.
All fixtures operate offline without network access.
"""

import json
import os
import sys

import pytest

# Ensure scripts directory is importable
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

# Ensure tests directory is importable (for mocks)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)

from mocks.mock_fda_client import MockFDAClient

# Path to fixture data files
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")


def _load_fixture(filename):
    """Load a JSON fixture file from the fixtures directory."""
    filepath = os.path.join(FIXTURES_DIR, filename)
    with open(filepath) as f:
        return json.load(f)


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
    """Create a MockFDAClient with increased recall count for DQY.

    Returns recall total of 4 (up from fingerprint baseline of 3).
    """
    client = MockFDAClient()
    resp = sample_api_responses["clearances_stable_2_items"]
    client.set_clearances("DQY", meta_total=resp["meta"]["results"]["total"],
                          results=resp["results"])
    client.set_recalls("DQY", meta_total=4)
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
