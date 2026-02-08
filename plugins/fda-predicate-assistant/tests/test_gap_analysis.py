"""Tests for v5.6.0/v5.7.0 features: gap analysis command, data pipeline command,
bundled gap_analysis.py script.

Validates command files, script integrity, CLI flags, and cross-references.
"""

import csv
import json
import os
import subprocess
import sys
import tempfile

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
PLUGIN_JSON = os.path.join(BASE_DIR, ".claude-plugin", "plugin.json")


# ── Command File Existence ──────────────────────────────────


class TestGapAnalysisCommandExists:
    """Test gap-analysis.md command file."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "gap-analysis.md")
        with open(path) as f:
            self.content = f.read()

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "gap-analysis.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content

    def test_mentions_3_way_cross_reference(self):
        assert "PMN" in self.content
        assert "CSV" in self.content
        assert "PDF" in self.content

    def test_has_years_flag(self):
        assert "--years" in self.content

    def test_has_product_codes_flag(self):
        assert "--product-codes" in self.content

    def test_has_prefixes_flag(self):
        assert "--prefixes" in self.content

    def test_has_baseline_flag(self):
        assert "--baseline" in self.content

    def test_has_output_format(self):
        assert "Gap Analysis" in self.content
        assert "NEXT STEPS" in self.content

    def test_has_pmn_file_search(self):
        assert "pmn96cur.txt" in self.content
        assert "pmnlstmn.txt" in self.content


class TestDataPipelineCommandExists:
    """Test data-pipeline.md command file."""

    def setup_method(self):
        path = os.path.join(CMDS_DIR, "data-pipeline.md")
        with open(path) as f:
            self.content = f.read()

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "data-pipeline.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_subcommands(self):
        assert "status" in self.content
        assert "analyze" in self.content
        assert "download" in self.content
        assert "extract" in self.content
        assert "merge" in self.content

    def test_distinguishes_from_regulatory_pipeline(self):
        assert "NOT the regulatory submission pipeline" in self.content

    def test_has_pipeline_py_reference(self):
        assert "pipeline.py" in self.content

    def test_has_download_510k_path(self):
        assert "download/510k" in self.content

    def test_has_incremental_flag(self):
        assert "--incremental" in self.content

    def test_has_dry_run_flag(self):
        assert "--dry-run" in self.content


# ── Bundled Script Integrity ────────────────────────────────


class TestGapAnalysisScript:
    """Test gap_analysis.py bundled script."""

    def test_script_exists(self):
        assert os.path.exists(os.path.join(SCRIPTS_DIR, "gap_analysis.py"))

    def test_script_is_executable_python(self):
        path = os.path.join(SCRIPTS_DIR, "gap_analysis.py")
        result = subprocess.run(
            [sys.executable, path, "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "gap" in result.stdout.lower() or "missing" in result.stdout.lower()

    def test_has_argparse_flags(self):
        path = os.path.join(SCRIPTS_DIR, "gap_analysis.py")
        result = subprocess.run(
            [sys.executable, path, "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert "--years" in result.stdout
        assert "--prefixes" in result.stdout
        assert "--product-codes" in result.stdout
        assert "--baseline" in result.stdout
        assert "--pdf-dir" in result.stdout
        assert "--output" in result.stdout
        assert "--pmn-files" in result.stdout

    def test_no_hardcoded_prefixes_in_main(self):
        """Ensure the script doesn't use hardcoded TARGET_PREFIXES."""
        path = os.path.join(SCRIPTS_DIR, "gap_analysis.py")
        with open(path) as f:
            content = f.read()
        # Should NOT have a global TARGET_PREFIXES constant
        assert "TARGET_PREFIXES" not in content

    def test_has_parse_years_function(self):
        path = os.path.join(SCRIPTS_DIR, "gap_analysis.py")
        with open(path) as f:
            content = f.read()
        assert "def parse_years" in content

    def test_has_prefixes_from_years_function(self):
        path = os.path.join(SCRIPTS_DIR, "gap_analysis.py")
        with open(path) as f:
            content = f.read()
        assert "def prefixes_from_years" in content


class TestGapAnalysisLogic:
    """Test gap_analysis.py core logic with synthetic data."""

    def test_year_range_parsing(self):
        """Test parse_years handles ranges and lists."""
        path = os.path.join(SCRIPTS_DIR, "gap_analysis.py")
        result = subprocess.run(
            [sys.executable, "-c", f"""
import sys; sys.path.insert(0, '{os.path.dirname(path)}')
from gap_analysis import parse_years
assert parse_years('2024') == {{2024}}
assert parse_years('2024,2025') == {{2024, 2025}}
assert parse_years('2020-2023') == {{2020, 2021, 2022, 2023}}
assert parse_years('2020-2022,2025') == {{2020, 2021, 2022, 2025}}
print('ALL_PASSED')
"""],
            capture_output=True, text=True, timeout=10
        )
        assert "ALL_PASSED" in result.stdout, result.stderr

    def test_prefixes_from_years(self):
        """Test year-to-prefix derivation."""
        path = os.path.join(SCRIPTS_DIR, "gap_analysis.py")
        result = subprocess.run(
            [sys.executable, "-c", f"""
import sys; sys.path.insert(0, '{os.path.dirname(path)}')
from gap_analysis import prefixes_from_years
p = prefixes_from_years({{2024, 2025}})
assert 'K24' in p
assert 'K25' in p
assert 'DEN' in p
assert 'K23' not in p
print('ALL_PASSED')
"""],
            capture_output=True, text=True, timeout=10
        )
        assert "ALL_PASSED" in result.stdout, result.stderr

    def test_manifest_output_format(self):
        """Test that the script produces valid CSV manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal PMN file
            pmn_path = os.path.join(tmpdir, "pmn_test.txt")
            with open(pmn_path, "w") as f:
                f.write("KNUMBER|APPLICANT|STREET1|STREET2|CITY|STATE|COUNTRY_CODE|ZIP|DATEPANEL|DESSION_DATE|DATERECEIVED|DECISION|REVIEWCODE|ESSION_CODE|PRODUCTCODE|STATEORSUMM|CLASSADVISE|ESSION_CODE2|TYPE|THIRDPARTY|EXPEDITEDREVIEW|DEVICENAME\n")
                f.write("K250001|TEST CORP|123 St||City|CA|US|90210|01/15/2025|02/15/2025|01/01/2025|SESE|RC001|SE|KGN|Cleared|N|SE|Traditional|N|N|Test Device\n")
                f.write("K250002|OTHER INC|456 Ave||Town|NY|US|10001|02/01/2025|03/01/2025|02/01/2025|SESE|RC002|SE|DXY|Cleared|N|SE|Special|N|N|Other Device\n")

            # Create empty baseline CSV
            baseline = os.path.join(tmpdir, "baseline.csv")
            with open(baseline, "w") as f:
                f.write("KNUMBER,TYPE\nK250001,Predicate\n")

            output = os.path.join(tmpdir, "manifest.csv")
            script = os.path.join(SCRIPTS_DIR, "gap_analysis.py")

            result = subprocess.run(
                [sys.executable, script,
                 "--years", "2025",
                 "--pmn-files", pmn_path,
                 "--baseline", baseline,
                 "--pdf-dir", tmpdir,
                 "--output", output],
                capture_output=True, text=True, timeout=30
            )
            assert result.returncode == 0, result.stderr

            # Verify manifest exists and has correct structure
            assert os.path.exists(output)
            with open(output) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # K250001 should be skipped (in baseline), K250002 should be in manifest
            knumbers = {r["KNUMBER"] for r in rows}
            assert "K250001" not in knumbers, "K250001 should be skipped (in baseline)"
            assert "K250002" in knumbers, "K250002 should be in manifest"

            # Check required columns
            assert "STATUS" in rows[0]
            assert "DOWNLOAD_URL" in rows[0]
            assert rows[0]["STATUS"] == "need_download"

    def test_product_code_filter(self):
        """Test --product-codes filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pmn_path = os.path.join(tmpdir, "pmn_test.txt")
            with open(pmn_path, "w") as f:
                f.write("KNUMBER|APPLICANT|STREET1|STREET2|CITY|STATE|COUNTRY_CODE|ZIP|DATEPANEL|DESSION_DATE|DATERECEIVED|DECISION|REVIEWCODE|ESSION_CODE|PRODUCTCODE|STATEORSUMM|CLASSADVISE|ESSION_CODE2|TYPE|THIRDPARTY|EXPEDITEDREVIEW|DEVICENAME\n")
                f.write("K250001|TEST CORP|123 St||City|CA|US|90210|01/15/2025|02/15/2025|01/01/2025|SESE|RC001|SE|KGN|Cleared|N|SE|Traditional|N|N|Test Device\n")
                f.write("K250002|OTHER INC|456 Ave||Town|NY|US|10001|02/01/2025|03/01/2025|02/01/2025|SESE|RC002|SE|DXY|Cleared|N|SE|Special|N|N|Other Device\n")

            baseline = os.path.join(tmpdir, "baseline.csv")
            with open(baseline, "w") as f:
                f.write("KNUMBER\n")

            output = os.path.join(tmpdir, "manifest.csv")
            script = os.path.join(SCRIPTS_DIR, "gap_analysis.py")

            result = subprocess.run(
                [sys.executable, script,
                 "--years", "2025",
                 "--product-codes", "KGN",
                 "--pmn-files", pmn_path,
                 "--baseline", baseline,
                 "--pdf-dir", tmpdir,
                 "--output", output],
                capture_output=True, text=True, timeout=30
            )
            assert result.returncode == 0

            with open(output) as f:
                rows = list(csv.DictReader(f))

            # Only KGN should be in output, not DXY
            codes = {r["PRODUCTCODE"] for r in rows}
            assert "KGN" in codes
            assert "DXY" not in codes


# ── Plugin Metadata ─────────────────────────────────────────


class TestPluginVersionAndCounts:
    """Test plugin.json reflects v5.7.0 with 35 commands."""

    def test_version_is_5_8_0(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert data["version"] == "5.8.0"

    def test_description_mentions_36_commands(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "36 commands" in data["description"]

    def test_description_mentions_gap_analysis(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "gap analysis" in data["description"]

    def test_description_mentions_data_pipeline(self):
        with open(PLUGIN_JSON) as f:
            data = json.load(f)
        assert "data maintenance pipeline" in data["description"]

    def test_command_count_is_36(self):
        """Verify 36 .md files in commands directory."""
        cmd_files = [f for f in os.listdir(CMDS_DIR) if f.endswith(".md")]
        assert len(cmd_files) == 36, f"Expected 36 commands, found {len(cmd_files)}: {sorted(cmd_files)}"
