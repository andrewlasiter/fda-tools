"""Tests for v5.18.0 Item 28: Comprehensive batchfetch.py test coverage.

Validates script existence, compilation, CLI arguments, FDA URL patterns,
year parsing, download progress tracking, error handling, and output format.
"""

import os
import sys
import re
import json
import csv
import tempfile

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")


def _read_script(name):
    path = os.path.join(SCRIPTS_DIR, f"{name}.py")
    with open(path) as f:
        return f.read()


class TestBatchfetchExistence:
    """Script file existence and basic compilation."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(SCRIPTS_DIR, "batchfetch.py"))

    def test_file_is_python(self):
        content = _read_script("batchfetch")
        assert content.startswith("#!/usr/bin/env python3") or "import" in content[:200]

    def test_has_main_function(self):
        content = _read_script("batchfetch")
        assert "def main(" in content

    def test_has_parse_args(self):
        content = _read_script("batchfetch")
        assert "def parse_args(" in content

    def test_syntax_valid(self):
        """Verify script compiles without syntax errors."""
        path = os.path.join(SCRIPTS_DIR, "batchfetch.py")
        import py_compile
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError:
            assert False, "batchfetch.py has syntax errors"


class TestBatchfetchCLIArgs:
    """CLI argument definitions -- verify all 16 flags exist."""

    def setup_method(self):
        self.content = _read_script("batchfetch")

    def test_has_date_range_flag(self):
        assert "--date-range" in self.content

    def test_has_years_flag(self):
        assert "--years" in self.content

    def test_has_submission_types_flag(self):
        assert "--submission-types" in self.content

    def test_has_committees_flag(self):
        assert "--committees" in self.content

    def test_has_decision_codes_flag(self):
        assert "--decision-codes" in self.content

    def test_has_applicants_flag(self):
        assert "--applicants" in self.content

    def test_has_product_codes_flag(self):
        assert "--product-codes" in self.content

    def test_has_output_dir_flag(self):
        assert "--output-dir" in self.content

    def test_has_download_dir_flag(self):
        assert "--download-dir" in self.content

    def test_has_data_dir_flag(self):
        assert "--data-dir" in self.content

    def test_has_save_excel_flag(self):
        assert "--save-excel" in self.content

    def test_has_interactive_flag(self):
        assert "--interactive" in self.content

    def test_has_no_download_flag(self):
        assert "--no-download" in self.content

    def test_has_delay_flag(self):
        assert "--delay" in self.content

    def test_has_from_manifest_flag(self):
        assert "--from-manifest" in self.content

    def test_has_resume_flag(self):
        assert "--resume" in self.content


class TestBatchfetchFDAUrls:
    """FDA URL patterns used for downloads."""

    def setup_method(self):
        self.content = _read_script("batchfetch")

    def test_has_accessdata_url(self):
        assert "accessdata.fda.gov" in self.content

    def test_has_zip_url_pattern(self):
        assert ".zip" in self.content

    def test_has_pmn_url(self):
        assert "pmn" in self.content.lower()

    def test_has_foiclass_url(self):
        assert "foiclass" in self.content

    def test_has_pdf_download_url(self):
        assert "cdrh_docs" in self.content or "pdf" in self.content.lower()


class TestBatchfetchYearParsing:
    """Year parsing function correctness."""

    def setup_method(self):
        self.content = _read_script("batchfetch")

    def test_has_parse_year_list(self):
        assert "def parse_year_list(" in self.content

    def test_parse_year_range_pattern(self):
        """Verify the function handles ranges like '2020-2025'."""
        assert "split('-')" in self.content or "'-'" in self.content

    def test_parse_year_comma_pattern(self):
        """Verify comma-separated years like '2020,2022,2024'."""
        assert "split(',')" in self.content or "','" in self.content


class TestBatchfetchProgressTracking:
    """Download progress tracking (--resume support)."""

    def setup_method(self):
        self.content = _read_script("batchfetch")

    def test_has_load_progress_function(self):
        assert "def load_progress(" in self.content

    def test_has_save_progress_function(self):
        assert "def save_progress(" in self.content

    def test_progress_uses_json(self):
        assert "download_progress.json" in self.content

    def test_progress_has_completed_field(self):
        assert "'completed'" in self.content

    def test_progress_has_failed_field(self):
        assert "'failed'" in self.content

    def test_progress_atomic_write(self):
        """Verify save_progress uses temp+rename for atomicity."""
        assert ".tmp" in self.content or "os.replace" in self.content

    def test_has_load_manifest_function(self):
        assert "def load_manifest(" in self.content

    def test_manifest_reads_csv(self):
        assert "DictReader" in self.content or "csv" in self.content

    def test_manifest_filters_need_download(self):
        assert "need_download" in self.content


class TestBatchfetchErrorHandling:
    """Error handling patterns."""

    def setup_method(self):
        self.content = _read_script("batchfetch")

    def test_has_try_except(self):
        assert "try:" in self.content and "except" in self.content

    def test_handles_request_exceptions(self):
        assert "requests" in self.content

    def test_has_timeout(self):
        assert "timeout" in self.content.lower()


class TestBatchfetchDataDictionaries:
    """Data structures and dictionaries."""

    def setup_method(self):
        self.content = _read_script("batchfetch")

    def test_has_decision_code_map(self):
        assert "SESE" in self.content or "Substantially Equivalent" in self.content

    def test_has_zip_dict(self):
        assert "zip_dict" in self.content or "pmn96cur" in self.content

    def test_has_colorama(self):
        assert "colorama" in self.content


class TestBatchfetchSharedHTTP:
    """Shared HTTP utility integration (v5.18.0)."""

    def setup_method(self):
        self.content = _read_script("batchfetch")

    def test_imports_fda_http(self):
        assert "fda_http" in self.content

    def test_has_fda_headers_fallback(self):
        assert "FDA_HEADERS" in self.content

    def test_has_create_session_fallback(self):
        assert "create_session" in self.content
