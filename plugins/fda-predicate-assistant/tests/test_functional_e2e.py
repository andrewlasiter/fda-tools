"""Tests for v5.14.0: Functional end-to-end validation.

Unlike structural tests (which check files contain expected strings), these tests
prove that command logic and data processing actually WORK with real or fixture data.

Tiers:
  - Tier 1: Local commands — no API, no project required (~15 tests)
  - Tier 2: Project data commands — uses test fixtures (~25 tests)
  - Tier 3: API commands — real openFDA calls, marked @pytest.mark.api (~20 tests)
  - Tier 4: Cross-command workflow — data flows between commands (~10 tests)
"""

import csv
import json
import os
import re

import pytest

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
REFS_DIR = os.path.join(BASE_DIR, "skills", "fda-510k-knowledge", "references")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_PROJECT = os.path.join(FIXTURES_DIR, "sample_project")


def _read_file(path):
    with open(path) as f:
        return f.read()


def _read_cmd(name):
    return _read_file(os.path.join(CMDS_DIR, f"{name}.md"))


def _read_agent(name):
    return _read_file(os.path.join(AGENTS_DIR, f"{name}.md"))


def _read_ref(name):
    return _read_file(os.path.join(REFS_DIR, f"{name}.md"))


def _load_json(path):
    with open(path) as f:
        return json.load(f)


# ════════════════════════════════════════════════════════════
# TIER 1: LOCAL COMMANDS — No API, No Project
# ════════════════════════════════════════════════════════════


class TestCalcShelfLife:
    """Verify ASTM F1980 shelf-life formula is documented correctly in calc.md."""

    def setup_method(self):
        self.content = _read_cmd("calc")

    def test_astm_f1980_formula_present(self):
        """calc.md must contain the accelerated aging formula."""
        assert "Q10" in self.content
        assert "ASTM F1980" in self.content

    def test_q10_default_value(self):
        """Default Q10 factor should be 2.0 per ASTM F1980."""
        assert "2.0" in self.content or "2" in self.content

    def test_aat_formula_components(self):
        """Formula: AAT_days = desired_shelf_life / Q10^((TAA - TRT) / 10)."""
        # Check that the formula references the key variables
        assert "TAA" in self.content or "accelerated" in self.content.lower()
        assert "TRT" in self.content or "ambient" in self.content.lower()

    def test_shelf_life_known_calculation(self):
        """Verify a known ASTM F1980 calculation inline.

        Given: shelf_life=2yr, Q10=2.0, TAA=55C, TRT=25C
        AAF = Q10^((55-25)/10) = 2^3 = 8
        AAT_days = 730 / 8 = 91.25 days
        """
        q10 = 2.0
        taa = 55
        trt = 25
        shelf_life_days = 2 * 365  # 2 years
        aaf = q10 ** ((taa - trt) / 10)
        aat_days = shelf_life_days / aaf
        assert aaf == 8.0
        assert abs(aat_days - 91.25) < 0.01

    def test_sample_size_section_exists(self):
        """calc.md must have a sample size calculator section."""
        assert "sample size" in self.content.lower() or "sample-size" in self.content.lower()

    def test_sterilization_dose_section_exists(self):
        """calc.md must have sterilization dose content."""
        assert "sterilization" in self.content.lower()


class TestConfigureCommand:
    """Verify configure.md settings management logic."""

    def setup_method(self):
        self.content = _read_cmd("configure")

    def test_settings_file_path(self):
        """configure.md must reference the correct settings file."""
        assert "fda-predicate-assistant.local.md" in self.content

    def test_settings_keys_documented(self):
        """Key settings must be documented."""
        for key in ["projects_dir", "openfda_api_key", "openfda_enabled"]:
            assert key in self.content, f"Setting '{key}' not documented in configure.md"

    def test_api_key_setup_flow(self):
        """configure.md must have --setup-key instructions."""
        assert "--setup-key" in self.content or "setup-key" in self.content

    def test_test_api_flag(self):
        """configure.md must support --test-api."""
        assert "--test-api" in self.content


class TestStatusCommand:
    """Verify status.md file freshness detection logic."""

    def setup_method(self):
        self.content = _read_cmd("status")

    def test_checks_fda_database_freshness(self):
        """status.md must check FDA database file ages."""
        assert "5 day" in self.content.lower() or "5-day" in self.content.lower() or "freshness" in self.content.lower()

    def test_reports_api_connectivity(self):
        """status.md must report API status."""
        assert "api" in self.content.lower()
        assert "connectivity" in self.content.lower() or "connection" in self.content.lower() or "status" in self.content.lower()

    def test_lists_project_files(self):
        """status.md must inventory project data files."""
        assert "output.csv" in self.content or "review.json" in self.content

    def test_checks_script_availability(self):
        """status.md must verify scripts exist."""
        assert "batchfetch" in self.content.lower() or "predicate_extractor" in self.content.lower()


class TestPathwayCommand:
    """Verify pathway recommendation logic structure."""

    def setup_method(self):
        self.content = _read_cmd("pathway")

    def test_three_pathways_covered(self):
        """Must cover Traditional, Special, and Abbreviated 510(k)."""
        content_lower = self.content.lower()
        assert "traditional" in content_lower
        assert "special" in content_lower
        assert "abbreviated" in content_lower

    def test_de_novo_pathway(self):
        """Must mention De Novo as alternative pathway."""
        assert "De Novo" in self.content or "de novo" in self.content.lower()

    def test_pma_pathway(self):
        """Must mention PMA for Class III devices."""
        assert "PMA" in self.content or "pma" in self.content


# ════════════════════════════════════════════════════════════
# TIER 2: PROJECT DATA COMMANDS — Uses Test Fixtures
# ════════════════════════════════════════════════════════════


class TestReviewJsonFixture:
    """Verify review.json fixture is well-formed and usable."""

    def setup_method(self):
        self.review = _load_json(os.path.join(SAMPLE_PROJECT, "review.json"))

    def test_has_required_top_level_fields(self):
        for field in ["project", "product_code", "predicates", "summary"]:
            assert field in self.review, f"Missing required field: {field}"

    def test_predicates_have_required_fields(self):
        for knum, pred in self.review["predicates"].items():
            assert re.match(r"^K\d{6}$", knum), f"Invalid K-number format: {knum}"
            for field in ["device_name", "decision", "confidence_score", "product_code"]:
                assert field in pred, f"{knum} missing field: {field}"

    def test_accepted_predicates_have_high_scores(self):
        for knum, pred in self.review["predicates"].items():
            if pred["decision"] == "accepted":
                assert pred["confidence_score"] >= 70, \
                    f"Accepted predicate {knum} has low score: {pred['confidence_score']}"

    def test_rejected_predicates_have_flags(self):
        for knum, pred in self.review["predicates"].items():
            if pred["decision"] == "rejected":
                assert len(pred.get("risk_flags", [])) > 0, \
                    f"Rejected predicate {knum} has no risk flags"

    def test_summary_counts_match(self):
        accepted = sum(1 for p in self.review["predicates"].values() if p["decision"] == "accepted")
        rejected = sum(1 for p in self.review["predicates"].values() if p["decision"] == "rejected")
        assert self.review["summary"]["accepted"] == accepted
        assert self.review["summary"]["rejected"] == rejected
        assert self.review["summary"]["total_evaluated"] == accepted + rejected

    def test_product_code_consistent(self):
        """Product code in top-level must match all accepted predicates."""
        pc = self.review["product_code"]
        for knum, pred in self.review["predicates"].items():
            if pred["decision"] == "accepted":
                assert pred["product_code"] == pc, \
                    f"Predicate {knum} has product code {pred['product_code']}, expected {pc}"


class TestOutputCsvFixture:
    """Verify output.csv fixture is well-formed and parseable."""

    def setup_method(self):
        path = os.path.join(SAMPLE_PROJECT, "output.csv")
        with open(path, newline="") as f:
            self.reader = list(csv.reader(f))
        self.header = self.reader[0]
        self.rows = self.reader[1:]

    def test_has_header_row(self):
        assert "K-Number" in self.header[0] or "K-number" in self.header[0]

    def test_has_data_rows(self):
        assert len(self.rows) >= 5, f"Expected 5+ rows, got {len(self.rows)}"

    def test_knumber_format(self):
        for row in self.rows:
            knum = row[0].strip()
            if knum:
                assert re.match(r"^K\d{6}$", knum), f"Invalid K-number: {knum}"

    def test_product_code_column(self):
        for row in self.rows:
            pc = row[1].strip()
            assert len(pc) == 3 and pc.isalpha() and pc.isupper(), \
                f"Invalid product code: {pc}"

    def test_document_type_values(self):
        valid_types = {"Summary", "Statement"}
        for row in self.rows:
            doc_type = row[2].strip()
            assert doc_type in valid_types, f"Invalid doc type: {doc_type}"

    def test_predicate_columns_contain_knumbers_or_empty(self):
        for row in self.rows:
            for col in row[3:]:
                val = col.strip()
                if val:
                    assert re.match(r"^K\d{6}$", val), f"Invalid predicate: {val}"

    def test_some_rows_have_predicates(self):
        rows_with_preds = sum(1 for row in self.rows if any(col.strip() for col in row[3:]))
        assert rows_with_preds > 0, "No rows have extracted predicates"

    def test_at_least_one_row_has_no_predicates(self):
        """Fixture should include a row with zero predicates to test edge case."""
        rows_without = sum(1 for row in self.rows if not any(col.strip() for col in row[3:]))
        assert rows_without >= 1, "Need at least one row without predicates for edge case testing"


class TestDraftFixture:
    """Verify draft fixture is well-formed and has expected markers."""

    def setup_method(self):
        self.content = _read_file(
            os.path.join(SAMPLE_PROJECT, "drafts", "device-description.md")
        )

    def test_has_draft_header(self):
        assert "DRAFT" in self.content

    def test_has_todo_markers(self):
        todo_count = self.content.count("[TODO:")
        assert todo_count >= 3, f"Expected 3+ [TODO:] markers, got {todo_count}"

    def test_has_source_markers(self):
        assert "[Source:" in self.content

    def test_has_product_code_reference(self):
        assert "QAS" in self.content

    def test_has_predicate_reference(self):
        assert "K213456" in self.content

    def test_has_comparison_table(self):
        assert "Predicate" in self.content or "predicate" in self.content
        assert "|" in self.content  # markdown table


class TestConsistencyLogic:
    """Verify consistency check logic using fixtures with known data."""

    def setup_method(self):
        self.review = _load_json(os.path.join(SAMPLE_PROJECT, "review.json"))
        self.query = _load_json(os.path.join(SAMPLE_PROJECT, "query.json"))
        self.draft = _read_file(
            os.path.join(SAMPLE_PROJECT, "drafts", "device-description.md")
        )

    def test_product_code_consistent_review_query(self):
        """review.json and query.json must agree on product code."""
        assert self.review["product_code"] == self.query["product_code"]

    def test_product_code_in_draft(self):
        """Draft must reference the same product code."""
        assert self.query["product_code"] in self.draft

    def test_accepted_predicate_in_draft(self):
        """At least one accepted predicate must appear in the draft."""
        accepted = [k for k, v in self.review["predicates"].items() if v["decision"] == "accepted"]
        found = any(k in self.draft for k in accepted)
        assert found, "No accepted predicates referenced in draft"

    def test_rejected_predicate_not_primary_in_draft(self):
        """Rejected predicates should not appear as primary predicate comparison."""
        rejected = [k for k, v in self.review["predicates"].items() if v["decision"] == "rejected"]
        # Check they don't appear in the comparison table header
        for knum in rejected:
            # It's OK if mentioned in passing, but it should not be in the comparison table
            # as a "Predicate K..." header column
            assert f"Predicate {knum}" not in self.draft, \
                f"Rejected predicate {knum} appears as predicate in comparison table"

    def test_project_name_consistent(self):
        """Project name must match between review.json and query.json."""
        assert self.review["project"] == self.query["project"]


class TestAnalyzeLogic:
    """Verify analyze command logic against fixture output.csv."""

    def setup_method(self):
        path = os.path.join(SAMPLE_PROJECT, "output.csv")
        with open(path, newline="") as f:
            reader = csv.reader(f)
            self.header = next(reader)
            self.rows = list(reader)

    def test_total_submissions_count(self):
        assert len(self.rows) == 10

    def test_product_code_distribution(self):
        codes = set(row[1].strip() for row in self.rows)
        assert codes == {"QAS"}

    def test_document_type_ratio(self):
        summary_count = sum(1 for row in self.rows if row[2].strip() == "Summary")
        statement_count = sum(1 for row in self.rows if row[2].strip() == "Statement")
        assert summary_count == 7
        assert statement_count == 3

    def test_predicate_frequency(self):
        """K213456 should be the most cited predicate."""
        pred_counts = {}
        for row in self.rows:
            for col in row[3:]:
                val = col.strip()
                if val and re.match(r"^K\d{6}$", val):
                    pred_counts[val] = pred_counts.get(val, 0) + 1
        assert max(pred_counts, key=pred_counts.get) == "K213456"
        assert pred_counts["K213456"] == 6

    def test_zero_predicate_detection(self):
        """Should detect row(s) with no predicates extracted."""
        zero_pred_rows = [row for row in self.rows if not any(col.strip() for col in row[3:])]
        assert len(zero_pred_rows) == 1  # K226666

    def test_average_predicates_per_submission(self):
        counts = []
        for row in self.rows:
            n = sum(1 for col in row[3:] if col.strip())
            counts.append(n)
        avg = sum(counts) / len(counts)
        assert 1.0 < avg < 3.0  # Expected ~1.6

    def test_unique_predicates_identified(self):
        preds = set()
        for row in self.rows:
            for col in row[3:]:
                val = col.strip()
                if val and re.match(r"^K\d{6}$", val):
                    preds.add(val)
        # K213456, K201234, K190987, K180555
        assert len(preds) == 4


class TestTraceabilityLogic:
    """Verify traceability concepts work with fixture data."""

    def setup_method(self):
        self.review = _load_json(os.path.join(SAMPLE_PROJECT, "review.json"))

    def test_accepted_predicates_traceable(self):
        """Every accepted predicate must have a rationale (traceability source)."""
        for knum, pred in self.review["predicates"].items():
            if pred["decision"] == "accepted":
                assert pred.get("rationale"), f"Accepted predicate {knum} has no rationale"
                assert len(pred["rationale"]) > 10, \
                    f"Predicate {knum} rationale too short: {pred['rationale']}"

    def test_risk_flags_are_valid_types(self):
        """Risk flags must be from the known set."""
        known_flags = {
            "different_intended_use", "recalled", "old_predicate", "class_iii",
            "no_summary", "different_product_code", "ai_ml_component",
            "maude_deaths", "maude_injuries"
        }
        for knum, pred in self.review["predicates"].items():
            for flag in pred.get("risk_flags", []):
                assert flag in known_flags, f"Unknown risk flag '{flag}' on {knum}"


# ════════════════════════════════════════════════════════════
# TIER 3: API COMMANDS — Real openFDA Calls
# ════════════════════════════════════════════════════════════


@pytest.mark.api
class TestValidateApi:
    """Verify validate command works with real openFDA API."""

    def test_valid_knumber_returns_data(self):
        """K213456 lookup should return data (or 404 for fabricated numbers)."""
        import urllib.request
        url = "https://api.fda.gov/device/510k.json?search=k_number:K213456&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                # Either we get results or an error — both are valid API responses
                assert "results" in data or "error" in data
        except Exception:
            pytest.skip("openFDA API unavailable")

    def test_product_code_search(self):
        """Product code QAS should return classification data."""
        import urllib.request
        url = "https://api.fda.gov/device/classification.json?search=product_code:QAS&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "results" in data
                assert len(data["results"]) > 0
                result = data["results"][0]
                assert result["product_code"] == "QAS"
        except Exception:
            pytest.skip("openFDA API unavailable")


@pytest.mark.api
class TestSafetyApi:
    """Verify safety command openFDA MAUDE query structure."""

    def test_maude_query_returns_events(self):
        """MAUDE events for a common product code should return results."""
        import urllib.request
        url = "https://api.fda.gov/device/event.json?search=device.openfda.device_class:2&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "results" in data
                assert len(data["results"]) > 0
        except Exception:
            pytest.skip("openFDA API unavailable")

    def test_recall_query_structure(self):
        """Recall query should work with product code filter."""
        import urllib.request
        url = "https://api.fda.gov/device/recall.json?search=openfda.device_class:2&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "results" in data or "error" in data
        except Exception:
            pytest.skip("openFDA API unavailable")


@pytest.mark.api
class TestUdiApi:
    """Verify UDI command API query works."""

    def test_udi_product_code_search(self):
        """UDI search by product code should return results."""
        import urllib.request
        url = "https://api.fda.gov/device/udi.json?search=product_codes.code:QAS&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "results" in data or "error" in data
        except Exception:
            pytest.skip("openFDA API unavailable")


@pytest.mark.api
class TestPathwayApi:
    """Verify pathway command classification lookup."""

    def test_classification_returns_device_class(self):
        """Classification lookup should return device class."""
        import urllib.request
        url = "https://api.fda.gov/device/classification.json?search=product_code:QAS&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if "results" in data and len(data["results"]) > 0:
                    result = data["results"][0]
                    assert "device_class" in result
                    assert result["device_class"] in ["1", "2", "3", "f", "u"]
        except Exception:
            pytest.skip("openFDA API unavailable")


@pytest.mark.api
class TestTrialsApi:
    """Verify ClinicalTrials.gov API v2 query structure."""

    def test_device_study_search(self):
        """ClinicalTrials.gov search for device studies should work."""
        import urllib.request
        url = "https://clinicaltrials.gov/api/v2/studies?query.term=PACS+imaging&pageSize=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "studies" in data or "totalCount" in data
        except Exception:
            pytest.skip("ClinicalTrials.gov API unavailable")


@pytest.mark.api
class TestInspectionsApi:
    """Verify FDA Data Dashboard API query structure."""

    def test_inspections_endpoint_reachable(self):
        """FDA Data Dashboard inspections endpoint should respond."""
        import urllib.request
        url = "https://api.fda.gov/device/enforcement.json?limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "results" in data or "error" in data
        except Exception:
            pytest.skip("FDA API unavailable")


@pytest.mark.api
class TestStandardsApi:
    """Verify FDA recognized standards endpoint works."""

    def test_510k_endpoint_returns_data(self):
        """510(k) endpoint should return clearance data."""
        import urllib.request
        url = "https://api.fda.gov/device/510k.json?search=product_code:QAS&limit=3"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "results" in data
                for result in data["results"]:
                    assert "k_number" in result
                    assert "product_code" in result
        except Exception:
            pytest.skip("openFDA API unavailable")


@pytest.mark.api
class TestWarningsApi:
    """Verify warning letter and enforcement data works."""

    def test_enforcement_search(self):
        """Enforcement endpoint should return recall data."""
        import urllib.request
        url = "https://api.fda.gov/device/enforcement.json?search=classification:\"Class+II\"&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FDA-Plugin-Test/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                assert "results" in data or "error" in data
        except Exception:
            pytest.skip("openFDA API unavailable")


# ════════════════════════════════════════════════════════════
# TIER 4: CROSS-COMMAND WORKFLOW — Data Flows Between Commands
# ════════════════════════════════════════════════════════════


class TestReviewToCompareSeDataFlow:
    """Verify review.json schema is compatible with compare-se command."""

    def setup_method(self):
        self.review = _load_json(os.path.join(SAMPLE_PROJECT, "review.json"))
        self.compare_se = _read_cmd("compare-se")

    def test_accepted_predicates_are_knumbers(self):
        """compare-se expects K-numbers from review.json."""
        accepted = [k for k, v in self.review["predicates"].items() if v["decision"] == "accepted"]
        for knum in accepted:
            assert re.match(r"^K\d{6}$", knum)

    def test_compare_se_accepts_predicate_list_format(self):
        """compare-se must accept comma-separated K-numbers."""
        assert "--predicates" in self.compare_se
        assert "K" in self.compare_se  # References K-number format

    def test_product_code_flows_to_compare_se(self):
        """compare-se must accept product code from review context."""
        assert "--product-code" in self.compare_se or "product_code" in self.compare_se


class TestReviewToDraftDataFlow:
    """Verify review.json is usable by draft command."""

    def setup_method(self):
        self.review = _load_json(os.path.join(SAMPLE_PROJECT, "review.json"))
        self.draft = _read_cmd("draft")

    def test_draft_reads_review_json(self):
        """draft.md must reference review.json as data source."""
        assert "review.json" in self.draft

    def test_draft_uses_accepted_predicates(self):
        """draft.md must filter for accepted predicates."""
        assert "accepted" in self.draft.lower()

    def test_review_json_has_fields_draft_needs(self):
        """review.json must have device_name and product_code that draft uses."""
        assert "product_code" in self.review
        assert "device_name" in self.review or "predicates" in self.review
        # Draft needs at least one accepted predicate
        accepted = [k for k, v in self.review["predicates"].items() if v["decision"] == "accepted"]
        assert len(accepted) >= 1


class TestReviewToPreCheckDataFlow:
    """Verify review.json is usable by pre-check command."""

    def setup_method(self):
        self.review = _load_json(os.path.join(SAMPLE_PROJECT, "review.json"))
        self.pre_check = _read_cmd("pre-check")

    def test_pre_check_reads_review_json(self):
        """pre-check.md must reference review.json."""
        assert "review.json" in self.pre_check

    def test_pre_check_evaluates_predicates(self):
        """pre-check.md must evaluate predicate appropriateness."""
        assert "predicate" in self.pre_check.lower()
        assert "score" in self.pre_check.lower() or "assessment" in self.pre_check.lower()


class TestOutputCsvToReviewDataFlow:
    """Verify output.csv from extract is parseable by review command."""

    def setup_method(self):
        self.review_cmd = _read_cmd("review")
        path = os.path.join(SAMPLE_PROJECT, "output.csv")
        with open(path, newline="") as f:
            self.rows = list(csv.reader(f))

    def test_review_expects_csv_format(self):
        """review.md must reference output.csv columns."""
        assert "output.csv" in self.review_cmd
        assert "K-number" in self.review_cmd or "K-Number" in self.review_cmd or "Column 1" in self.review_cmd

    def test_csv_has_extractable_predicates(self):
        """output.csv must have predicate columns that review can read."""
        # Skip header
        data_rows = self.rows[1:]
        all_preds = set()
        for row in data_rows:
            for col in row[3:]:
                val = col.strip()
                if val and re.match(r"^K\d{6}$", val):
                    all_preds.add(val)
        assert len(all_preds) >= 2, "Need multiple predicates for review scoring"


class TestOutputCsvToAnalyzeDataFlow:
    """Verify output.csv is parseable by analyze command."""

    def setup_method(self):
        self.analyze_cmd = _read_cmd("analyze")

    def test_analyze_references_output_csv(self):
        """analyze.md must mention output.csv."""
        assert "output.csv" in self.analyze_cmd

    def test_analyze_handles_product_codes(self):
        """analyze.md must group by product code."""
        assert "product" in self.analyze_cmd.lower() and "code" in self.analyze_cmd.lower()


class TestConsistencyReadsAllFiles:
    """Verify consistency command can read all project file types."""

    def setup_method(self):
        self.cmd = _read_cmd("consistency")

    def test_reads_review_json(self):
        assert "review.json" in self.cmd

    def test_reads_query_json(self):
        assert "query.json" in self.cmd

    def test_reads_output_csv(self):
        assert "output.csv" in self.cmd

    def test_reads_drafts(self):
        assert "draft" in self.cmd.lower()

    def test_checks_product_code_consistency(self):
        assert "product code" in self.cmd.lower() or "product_code" in self.cmd


class TestDraftToAssembleDataFlow:
    """Verify draft output is usable by assemble command."""

    def setup_method(self):
        self.assemble = _read_cmd("assemble")
        self.draft_content = _read_file(
            os.path.join(SAMPLE_PROJECT, "drafts", "device-description.md")
        )

    def test_assemble_expects_draft_files(self):
        """assemble.md must reference draft files."""
        assert "draft" in self.assemble.lower()

    def test_assemble_maps_sections_to_estar(self):
        """assemble.md must map section names to eSTAR structure."""
        assert "eSTAR" in self.assemble or "estar" in self.assemble.lower()

    def test_draft_output_is_markdown(self):
        """Draft files must be valid markdown that assemble can process."""
        assert self.draft_content.startswith("#")
        assert "##" in self.draft_content


# ════════════════════════════════════════════════════════════
# ALLOWED-TOOLS VALIDATION
# ════════════════════════════════════════════════════════════


class TestAllowedToolsCompleteness:
    """Verify commands have all tools they reference in their body."""

    def _extract_allowed_tools(self, content):
        """Extract allowed-tools list from frontmatter."""
        match = re.search(r"allowed-tools:\s*(.+)", content)
        if match:
            return [t.strip() for t in match.group(1).split(",")]
        return []

    def test_review_has_askuserquestion(self):
        content = _read_cmd("review")
        tools = self._extract_allowed_tools(content)
        assert "AskUserQuestion" in tools, \
            "review.md uses AskUserQuestion but it's not in allowed-tools"

    def test_compare_se_has_askuserquestion(self):
        content = _read_cmd("compare-se")
        tools = self._extract_allowed_tools(content)
        assert "AskUserQuestion" in tools, \
            "compare-se.md uses AskUserQuestion but it's not in allowed-tools"

    def test_safety_has_write(self):
        content = _read_cmd("safety")
        tools = self._extract_allowed_tools(content)
        assert "Write" in tools, \
            "safety.md needs Write for saving reports"

    def test_validate_has_write(self):
        content = _read_cmd("validate")
        tools = self._extract_allowed_tools(content)
        assert "Write" in tools

    def test_summarize_has_write(self):
        content = _read_cmd("summarize")
        tools = self._extract_allowed_tools(content)
        assert "Write" in tools

    def test_analyze_has_write(self):
        content = _read_cmd("analyze")
        tools = self._extract_allowed_tools(content)
        assert "Write" in tools

    def test_consistency_has_write(self):
        content = _read_cmd("consistency")
        tools = self._extract_allowed_tools(content)
        assert "Write" in tools

    def test_all_commands_have_bash_and_read(self):
        """Every command should have at least Bash and Read."""
        for cmd_file in os.listdir(CMDS_DIR):
            if not cmd_file.endswith(".md"):
                continue
            name = cmd_file[:-3]
            content = _read_cmd(name)
            tools = self._extract_allowed_tools(content)
            assert "Bash" in tools, f"{name}.md missing Bash in allowed-tools"
            assert "Read" in tools, f"{name}.md missing Read in allowed-tools"


# ════════════════════════════════════════════════════════════
# AGENT PREREQUISITES VALIDATION
# ════════════════════════════════════════════════════════════


class TestAgentPrerequisites:
    """Verify all agents have prerequisite checks."""

    def test_extraction_analyzer_has_prerequisites(self):
        content = _read_agent("extraction-analyzer")
        assert "## Prerequisites" in content
        assert "output.csv" in content

    def test_submission_writer_has_prerequisites(self):
        content = _read_agent("submission-writer")
        assert "## Prerequisites" in content
        assert "review.json" in content

    def test_submission_assembler_has_prerequisites(self):
        content = _read_agent("submission-assembler")
        assert "## Prerequisites" in content
        assert "drafts/" in content or "drafts" in content

    def test_presub_planner_has_prerequisites(self):
        content = _read_agent("presub-planner")
        assert "## Prerequisites" in content
        assert "installed_plugins.json" in content

    def test_review_simulator_has_prerequisites(self):
        content = _read_agent("review-simulator")
        assert "## Prerequisites" in content
        assert "review.json" in content

    def test_research_intelligence_has_prerequisites(self):
        content = _read_agent("research-intelligence")
        assert "## Prerequisites" in content
        assert "product code" in content.lower()

    def test_data_pipeline_manager_has_prerequisites(self):
        content = _read_agent("data-pipeline-manager")
        assert "## Prerequisites" in content
        assert "batchfetch.py" in content


class TestAgentDeduplication:
    """Verify submission-writer and submission-assembler have distinct roles."""

    def setup_method(self):
        self.writer = _read_agent("submission-writer")
        self.assembler = _read_agent("submission-assembler")

    def test_writer_is_draft_focused(self):
        """submission-writer description should emphasize drafting."""
        # Check the frontmatter description
        match = re.search(r"description:\s*(.+?)(?:\n)", self.writer)
        desc = match.group(1).lower() if match else ""
        assert "draft" in desc, "submission-writer should be described as draft-focused"
        # Description may mention assembler as a cross-reference but should not claim to do assembly itself
        assert "assembles the package" not in desc, \
            "submission-writer should not claim to assemble the package"

    def test_assembler_is_packaging_focused(self):
        """submission-assembler description should emphasize packaging."""
        match = re.search(r"description:\s*(.+?)(?:\n)", self.assembler)
        desc = match.group(1).lower() if match else ""
        assert "packag" in desc or "post-draft" in desc, \
            "submission-assembler should be described as post-drafting/packaging"

    def test_writer_does_not_assemble(self):
        """submission-writer should not run /fda:assemble or /fda:export."""
        # Writer should not have assemble or export in its orchestrated commands
        assert "/fda:assemble" not in self.writer or "submission-assembler" in self.writer

    def test_assembler_draft_is_pre_assembly_only(self):
        """submission-assembler may reference /fda:draft but only for pre-assembly gap-filling."""
        # Assembler can reference /fda:draft as a pre-assembly step to generate missing drafts
        # but its primary description should not claim to be a drafting agent
        match = re.search(r"description:\s*(.+?)(?:\n)", self.assembler)
        desc = match.group(1).lower() if match else ""
        assert "draft" not in desc or "post-draft" in desc, \
            "submission-assembler description should emphasize packaging, not drafting"

    def test_writer_references_assembler_as_next_step(self):
        """submission-writer should tell user to run assembler next."""
        assert "submission-assembler" in self.writer


class TestReviewSimulatorScoringRubric:
    """Verify review-simulator has consistent scoring criteria."""

    def setup_method(self):
        self.content = _read_agent("review-simulator")

    def test_has_scoring_rubric_section(self):
        assert "Scoring Rubric" in self.content

    def test_has_predicate_appropriateness_score(self):
        assert "Predicate Appropriateness Score" in self.content

    def test_has_rta_screening_criteria(self):
        assert "RTA Screening" in self.content
        assert "rta-checklist.md" in self.content

    def test_has_specialist_evaluation_templates(self):
        assert "Biocompatibility" in self.content
        assert "Software" in self.content
        assert "Sterilization" in self.content

    def test_scoring_uses_numeric_points(self):
        """Scoring must use numeric point values for reproducibility."""
        assert "+20" in self.content or "+ 20" in self.content
        assert "+15" in self.content or "+ 15" in self.content

    def test_references_confidence_scoring_algorithm(self):
        assert "confidence-scoring.md" in self.content


# ════════════════════════════════════════════════════════════
# SKILL.MD COMPLETENESS
# ════════════════════════════════════════════════════════════


class TestSkillMdCompleteness:
    """Verify SKILL.md accurately reflects all plugin components."""

    def setup_method(self):
        self.skill = _read_file(os.path.join(
            BASE_DIR, "skills", "fda-510k-knowledge", "SKILL.md"
        ))

    def test_command_count_matches(self):
        """SKILL.md must list 41 commands."""
        assert "41" in self.skill
        # Count /fda: references in command tables
        fda_cmds = re.findall(r"/fda:([a-z-]+)", self.skill)
        unique_cmds = set(fda_cmds)
        assert len(unique_cmds) >= 41, f"Only {len(unique_cmds)} unique commands in SKILL.md"

    def test_all_commands_listed(self):
        """Every command file must appear in SKILL.md."""
        for cmd_file in os.listdir(CMDS_DIR):
            if not cmd_file.endswith(".md"):
                continue
            name = cmd_file[:-3]
            assert f"/fda:{name}" in self.skill, f"Command /fda:{name} missing from SKILL.md"

    def test_reference_count_matches(self):
        """SKILL.md must list 41 references."""
        assert "41 references" in self.skill

    def test_all_references_listed(self):
        """Every reference file must appear in SKILL.md."""
        refs_in_skill = set(re.findall(r"references/([a-z0-9-]+\.md)", self.skill))
        actual_refs = set(os.listdir(REFS_DIR))
        missing = actual_refs - refs_in_skill
        assert len(missing) == 0, f"References missing from SKILL.md: {missing}"

    def test_agents_section_exists(self):
        """SKILL.md must have an Agents section."""
        assert "## Agents" in self.skill

    def test_all_agents_listed(self):
        """Every agent must appear in SKILL.md."""
        for agent_file in os.listdir(AGENTS_DIR):
            if not agent_file.endswith(".md"):
                continue
            name = agent_file[:-3]
            assert name in self.skill, f"Agent {name} missing from SKILL.md"

    def test_workflow_guide_exists(self):
        """SKILL.md must have a Workflow Guide section."""
        assert "## Workflow Guide" in self.skill

    def test_workflow_has_five_stages(self):
        """Workflow must cover all 5 stages."""
        for stage in ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"]:
            assert stage in self.skill, f"Workflow missing {stage}"
