# Test fixtures package for FDA Tools Quick Wins test suite.
#
# Fixture Staleness Prevention (FDA-56)
# ======================================
#
# Every fixture JSON file contains a ``_fixture_meta`` block with:
#
#   - ``api_schema_version``: Semver tracking the openFDA API schema this
#     fixture was last validated against.  Bump this when fields change.
#   - ``created_at``: Date the fixture was first created.
#   - ``last_validated``: Date of the most recent validation against the
#     live openFDA API.
#   - ``source``: Which API endpoint(s) the fixture models.
#   - ``update_procedure``: Brief instructions for updating.
#
# Quarterly Validation
# --------------------
# Run the API contract tests to check fixtures against the live API::
#
#     pytest -m api_contract -v
#
# These tests fetch ONE real response per endpoint and verify that the
# fields used in fixtures still exist.  If a test fails:
#
#   1. Read the assertion message to find the missing/renamed field.
#   2. Check https://open.fda.gov/apis/device/ for the updated schema.
#   3. Update the affected fixture file(s) in this directory.
#   4. Bump ``api_schema_version`` in ``_fixture_meta``.
#   5. Update ``last_validated`` to today's date.
#   6. Re-run ``pytest -m api_contract`` to confirm.
#
# The ``_fixture_meta`` key is automatically stripped by conftest.py's
# ``_load_fixture()`` helper, so test code never sees it.
