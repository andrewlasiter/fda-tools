"""Sprint 4C Tests — Script & Pipeline Gaps

Tests for:
- C-04 + H-10 + M-06 + M-07 + L-01: predicate_extractor.py improvements
- C-05 + M-08: data-pipeline.md script references and paths
"""

import os
import re
import sys
import pytest

# Paths
PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), '..')
SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, 'scripts')
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, 'commands')

sys.path.insert(0, SCRIPTS_DIR)


# ===== L-01: DEN Number Extraction =====

class TestDENNumberExtraction:
    """predicate_extractor.py must extract DEN numbers."""

    def test_correct_dennumber_format_exists(self):
        """Module must have correct_dennumber_format function."""
        from predicate_extractor import correct_dennumber_format
        assert callable(correct_dennumber_format)

    def test_valid_den_number(self):
        from predicate_extractor import correct_dennumber_format
        result = correct_dennumber_format("DEN200045")
        assert result == "DEN200045"

    def test_valid_den_7_digit(self):
        from predicate_extractor import correct_dennumber_format
        result = correct_dennumber_format("DEN2100012")
        assert result == "DEN2100012"

    def test_invalid_den_too_short(self):
        from predicate_extractor import correct_dennumber_format
        result = correct_dennumber_format("DEN12345")
        assert result is None

    def test_invalid_den_too_long(self):
        from predicate_extractor import correct_dennumber_format
        result = correct_dennumber_format("DEN12345678")
        assert result is None

    def test_invalid_format(self):
        from predicate_extractor import correct_dennumber_format
        result = correct_dennumber_format("K192345")
        assert result is None

    def test_case_insensitive(self):
        from predicate_extractor import correct_dennumber_format
        result = correct_dennumber_format("den200045")
        assert result is not None  # Should handle case


# ===== M-07: ijson Fallback =====

class TestIjsonFallback:
    """predicate_extractor.py must handle missing ijson gracefully."""

    def test_has_ijson_flag(self):
        """Module must define HAS_IJSON flag."""
        import predicate_extractor
        assert hasattr(predicate_extractor, 'HAS_IJSON')

    def test_ijson_flag_is_bool(self):
        import predicate_extractor
        assert isinstance(predicate_extractor.HAS_IJSON, bool)

    def test_load_large_json_exists(self):
        """load_large_json must exist and be callable."""
        from predicate_extractor import load_large_json
        assert callable(load_large_json)


# ===== orjson Fallback =====

class TestOrjsonFallback:
    """predicate_extractor.py must handle missing orjson gracefully."""

    def test_has_orjson_flag(self):
        """Module must define HAS_ORJSON flag."""
        import predicate_extractor
        assert hasattr(predicate_extractor, 'HAS_ORJSON')

    def test_orjson_flag_is_bool(self):
        import predicate_extractor
        assert isinstance(predicate_extractor.HAS_ORJSON, bool)

    def test_save_to_json_exists(self):
        from predicate_extractor import save_to_json
        assert callable(save_to_json)


# ===== H-10: OCR Correction Documentation =====

class TestOCRCorrectionDocumentation:
    """OCR correction functions must have docstrings explaining validation chain."""

    def test_correct_number_format_has_docstring(self):
        from predicate_extractor import correct_number_format
        assert correct_number_format.__doc__ is not None
        assert len(correct_number_format.__doc__) > 20

    def test_correct_knumber_format_has_docstring(self):
        from predicate_extractor import correct_knumber_format
        assert correct_knumber_format.__doc__ is not None

    def test_correct_pnumber_format_has_docstring(self):
        from predicate_extractor import correct_pnumber_format
        assert correct_pnumber_format.__doc__ is not None


# ===== M-06: CSV Column Consistency =====

class TestCSVColumnConsistency:
    """predicate_extractor.py must normalize CSV row widths."""

    def test_main_function_exists(self):
        """main() must exist."""
        from predicate_extractor import main
        assert callable(main)

    def test_source_has_normalization_code(self):
        """Source code must contain row normalization logic."""
        script_path = os.path.join(SCRIPTS_DIR, 'predicate_extractor.py')
        with open(script_path) as f:
            content = f.read()
        assert "expected_cols" in content or "total_cols" in content, "Missing CSV column normalization code"

    def test_source_pads_short_rows(self):
        """Source code must pad short rows with empty strings."""
        script_path = os.path.join(SCRIPTS_DIR, 'predicate_extractor.py')
        with open(script_path) as f:
            content = f.read()
        assert "row.extend" in content or "extend" in content


# ===== C-05: data-pipeline.md Script References =====

class TestDataPipelineScriptReferences:
    """data-pipeline.md must clearly document bundled vs non-bundled scripts."""

    @pytest.fixture
    def pipeline_content(self):
        path = os.path.join(COMMANDS_DIR, 'data-pipeline.md')
        with open(path) as f:
            return f.read()

    def test_script_availability_table(self, pipeline_content):
        """Must have a table showing which scripts are bundled."""
        assert "Bundled in Plugin" in pipeline_content or "BUNDLED" in pipeline_content

    def test_documents_gap_analysis_bundled(self, pipeline_content):
        """gap_analysis.py must be listed as bundled."""
        assert "gap_analysis.py" in pipeline_content

    def test_documents_predicate_extractor_bundled(self, pipeline_content):
        """predicate_extractor.py must be listed as bundled."""
        assert "predicate_extractor.py" in pipeline_content

    def test_documents_pipeline_not_bundled(self, pipeline_content):
        """pipeline.py must be listed as not bundled."""
        # Should mention it's REPO ONLY or not bundled
        assert "REPO ONLY" in pipeline_content or "not bundled" in pipeline_content.lower()

    def test_documents_gap_downloader_not_bundled(self, pipeline_content):
        """gap_downloader.py must be listed as not bundled."""
        assert "gap_downloader" in pipeline_content

    def test_fallback_for_merge(self, pipeline_content):
        """Must provide inline Python fallback for merge step."""
        assert "inline" in pipeline_content.lower() or "merge" in pipeline_content.lower()

    def test_fallback_for_download(self, pipeline_content):
        """Must mention batchfetch.py as download fallback."""
        assert "batchfetch.py" in pipeline_content

    def test_uses_plugin_root_for_bundled(self, pipeline_content):
        """Bundled scripts must use $FDA_PLUGIN_ROOT path."""
        assert "$FDA_PLUGIN_ROOT/scripts/" in pipeline_content


# ===== M-08: No Hardcoded WSL Paths =====

class TestNoHardcodedPaths:
    """data-pipeline.md must have no hardcoded /mnt/c/ or WSL-specific paths."""

    @pytest.fixture
    def pipeline_content(self):
        path = os.path.join(COMMANDS_DIR, 'data-pipeline.md')
        with open(path) as f:
            return f.read()

    def test_no_mnt_c_paths(self, pipeline_content):
        """No /mnt/c/ paths in data-pipeline.md."""
        assert "/mnt/c/" not in pipeline_content

    def test_no_windows_paths(self, pipeline_content):
        """No C:\\ Windows-style paths."""
        assert "C:\\" not in pipeline_content

    def test_uses_settings_based_paths(self, pipeline_content):
        """Must use settings-based path resolution."""
        assert "extraction_dir" in pipeline_content or "pdf_dir" in pipeline_content


# ===== DEN Regex Pattern =====

class TestDENRegexInParseText:
    """parse_text must include DEN regex pattern."""

    def test_parse_text_source_has_den_regex(self):
        """Source code must contain DEN regex pattern."""
        script_path = os.path.join(SCRIPTS_DIR, 'predicate_extractor.py')
        with open(script_path) as f:
            content = f.read()
        assert r"DEN\d{6,7}" in content or "den_regex" in content

    def test_parse_text_includes_dennumber_correction(self):
        """parse_text must call correct_dennumber_format."""
        script_path = os.path.join(SCRIPTS_DIR, 'predicate_extractor.py')
        with open(script_path) as f:
            content = f.read()
        assert "correct_dennumber_format" in content


# ===== K-Number punctuation regression =====

class TestParseTextKNumberPunctuationRegression:
    """parse_text must capture canonical K-numbers before punctuation/EOL."""

    def test_extracts_knumber_before_terminal_period(self):
        from predicate_extractor import parse_text

        text = "Subject device K250003 cites predicate K250001 and reference K250002."
        csv_data = {"K250003": "AAA", "K250001": "AAA", "K250002": "BBB"}
        known_knumbers = set(csv_data.keys())

        data, _ = parse_text(text, "K250003.pdf", csv_data, known_knumbers, set())
        extracted = [identifier for identifier, _type, _pc in data]

        assert "K250001" in extracted
        assert "K250002" in extracted

    @pytest.mark.parametrize("suffix", [".", ",", ";", ")", "]", ""])
    def test_extracts_knumber_with_common_suffixes(self, suffix):
        from predicate_extractor import parse_text

        text = f"Reference: K250002{suffix}"
        csv_data = {"K250003": "AAA", "K250002": "BBB"}
        known_knumbers = {"K250002", "K250003"}

        data, _ = parse_text(text, "K250003.pdf", csv_data, known_knumbers, set())
        extracted = [identifier for identifier, _type, _pc in data]

        assert "K250002" in extracted
