#!/usr/bin/env python3
"""Tests for import_helpers module (FDA-17 / GAP-015)

Tests safe import patterns and error handling.
"""

import sys
import logging
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports

from import_helpers import (  # type: ignore
    ImportResult,
    safe_import,
    try_optional_import,
    safe_import_from,
    conditional_import,
    try_import_with_alternatives,
)


class TestImportResult:
    """Test ImportResult dataclass"""

    def test_success_result(self):
        """Test successful import result"""
        result = ImportResult(success=True, module=sys, error=None, error_type=None)
        assert result.success is True
        assert result.module is sys
        assert result.error is None
        assert result.error_type is None
        assert bool(result) is True

    def test_failure_result(self):
        """Test failed import result"""
        error = ImportError("Module not found")
        result = ImportResult(
            success=False,
            module=None,
            error=error,
            error_type='import'
        )
        assert result.success is False
        assert result.module is None
        assert result.error is error
        assert result.error_type == 'import'
        assert bool(result) is False

    def test_fallback_used(self):
        """Test fallback mechanism"""
        fallback_value = "fallback"
        result = ImportResult(
            success=False,
            module=fallback_value,
            error=ImportError(),
            error_type='import',
            fallback_used=True
        )
        assert result.fallback_used is True
        assert result.module == fallback_value


class TestSafeImport:
    """Test safe_import function"""

    def test_import_stdlib_module(self):
        """Test importing a standard library module"""
        result = safe_import('json')
        assert result.success is True
        assert result.module is not None
        assert result.error is None
        assert hasattr(result.module, 'loads')

    def test_import_specific_attribute(self):
        """Test importing specific class/function from module"""
        result = safe_import('json', 'loads')
        assert result.success is True
        assert callable(result.module)
        assert result.error is None

    def test_import_nonexistent_module(self):
        """Test importing a module that doesn't exist"""
        result = safe_import('nonexistent_module_xyz123')
        assert result.success is False
        assert result.module is None
        assert result.error is not None
        assert result.error_type == 'import'

    def test_import_missing_attribute(self):
        """Test importing attribute that doesn't exist in module"""
        result = safe_import('json', 'nonexistent_function_xyz')
        assert result.success is False
        assert result.error_type == 'attribute'

    def test_fallback_value(self):
        """Test fallback value when import fails"""
        fallback = {'test': 'value'}
        result = safe_import('nonexistent_module', fallback=fallback)
        assert result.success is False
        assert result.module is fallback
        assert result.fallback_used is True

    def test_alternative_names(self):
        """Test trying alternative module names"""
        # Try non-existent first, then real module
        result = safe_import(
            'nonexistent_module',
            alternative_names=['json']
        )
        assert result.success is True
        assert hasattr(result.module, 'loads')

    def test_required_logging_level(self, caplog):
        """Test that required imports log at WARNING level"""
        with caplog.at_level(logging.WARNING):
            result = safe_import('nonexistent_module', required=True)
            assert result.success is False
            # Should have warning-level log messages
            assert any(record.levelno == logging.WARNING for record in caplog.records)

    def test_optional_logging_level(self, caplog):
        """Test that optional imports log at DEBUG level"""
        with caplog.at_level(logging.DEBUG):
            result = safe_import('nonexistent_module', log_level=logging.DEBUG)
            assert result.success is False
            # Should have debug-level log messages
            assert any(record.levelno == logging.DEBUG for record in caplog.records)


class TestTryOptionalImport:
    """Test try_optional_import function"""

    def test_import_available_package(self):
        """Test importing an available optional package"""
        result = try_optional_import('json')
        assert result.success is True
        assert result.module is not None

    def test_import_unavailable_package(self, caplog):
        """Test importing unavailable package with helpful message"""
        with caplog.at_level(logging.DEBUG):
            result = try_optional_import(
                'nonexistent_package',
                package_name='nonexistent-pkg'
            )
            assert result.success is False
            # Should mention pip install
            assert any('pip install' in record.message for record in caplog.records)

    @patch('importlib.metadata.version')
    def test_version_check_satisfied(self, mock_version):
        """Test version check when requirement is satisfied"""
        mock_version.return_value = '2.0.0'
        # Need packaging for version comparison
        try:
            import packaging
            result = try_optional_import('json', min_version='1.0.0')
            assert result.success is True
        except ImportError:
            pytest.skip("packaging not available")

    @patch('importlib.metadata.version')
    def test_version_check_not_satisfied(self, mock_version, caplog):
        """Test version check when requirement not satisfied"""
        mock_version.return_value = '0.9.0'
        try:
            import packaging
            with caplog.at_level(logging.WARNING):
                result = try_optional_import('json', min_version='1.0.0')
                assert result.success is True  # Still imports, just warns
                # Should have warning about version
                assert any('below minimum' in record.message for record in caplog.records)
        except ImportError:
            pytest.skip("packaging not available")


class TestSafeImportFrom:
    """Test safe_import_from function"""

    def test_import_multiple_names(self):
        """Test importing multiple names from module"""
        imports = safe_import_from('json', ['loads', 'dumps'])
        assert imports['loads'] is not None
        assert imports['dumps'] is not None
        assert callable(imports['loads'])
        assert callable(imports['dumps'])

    def test_import_missing_name(self):
        """Test importing non-existent name from module"""
        imports = safe_import_from('json', ['loads', 'nonexistent_xyz'])
        assert imports['loads'] is not None
        assert imports['nonexistent_xyz'] is None

    def test_import_from_missing_module(self):
        """Test importing from non-existent module"""
        imports = safe_import_from('nonexistent_module', ['func1', 'func2'])
        assert imports['func1'] is None
        assert imports['func2'] is None


class TestConditionalImport:
    """Test conditional_import function"""

    def test_condition_met(self):
        """Test import when condition is True"""
        result = conditional_import(lambda: True, 'json')
        assert result.success is True
        assert result.module is not None

    def test_condition_not_met(self):
        """Test skipping import when condition is False"""
        result = conditional_import(lambda: False, 'json')
        assert result.success is False
        assert result.error_type == 'condition_not_met'

    def test_condition_with_attribute(self):
        """Test conditional import with specific attribute"""
        result = conditional_import(lambda: True, 'json', 'loads')
        assert result.success is True
        assert callable(result.module)


class TestTryImportWithAlternatives:
    """Test try_import_with_alternatives function"""

    def test_first_alternative_succeeds(self):
        """Test when first alternative succeeds"""
        result = try_import_with_alternatives('json', 'sys')
        assert result.success is True
        assert hasattr(result.module, 'loads')

    def test_second_alternative_succeeds(self):
        """Test when second alternative succeeds"""
        result = try_import_with_alternatives('nonexistent_xyz', 'json')
        assert result.success is True
        assert hasattr(result.module, 'loads')

    def test_all_alternatives_fail(self):
        """Test when all alternatives fail"""
        result = try_import_with_alternatives('nonexistent_1', 'nonexistent_2')
        assert result.success is False

    def test_no_alternatives_raises(self):
        """Test that calling with no arguments raises ValueError"""
        with pytest.raises(ValueError, match="Must provide at least one"):
            try_import_with_alternatives()


class TestRealWorldPatterns:
    """Test patterns found in actual codebase"""

    def test_pma_intelligence_pattern(self):
        """Test pattern from pma_intelligence.py"""
        # Simulate trying to import optional analytics modules
        result = safe_import('supplement_tracker', 'SupplementTracker')
        # Should fail gracefully (module doesn't exist in test env)
        assert result.success is False or result.module is not None

        # With fallback
        result = safe_import(
            'annual_report_tracker',
            'AnnualReportTracker',
            fallback=None
        )
        if not result.success:
            # Should use fallback
            summary = {"note": "Annual report tracker module not available."}
            assert result.module is None

    def test_scripts_init_pattern(self):
        """Test pattern from scripts/__init__.py"""
        # Try relative import first, then absolute
        result = try_import_with_alternatives(
            'scripts.fda_api_client',
            'fda_api_client'
        )
        # One of these should work in test environment
        # (but we're OK if both fail in isolated test)
        assert isinstance(result, ImportResult)

    def test_batchfetch_optional_deps_pattern(self):
        """Test pattern from batchfetch.py for optional dependencies"""
        # Try importing optional PDF libraries
        pytesseract_result = try_optional_import('pytesseract')
        pdf2image_result = try_optional_import('pdf2image')
        pypdf2_result = try_optional_import('PyPDF2')

        # All should return ImportResult (success depends on installation)
        assert isinstance(pytesseract_result, ImportResult)
        assert isinstance(pdf2image_result, ImportResult)
        assert isinstance(pypdf2_result, ImportResult)


class TestErrorTypeClassification:
    """Test proper classification of error types"""

    def test_import_error_type(self):
        """Test ImportError is classified correctly"""
        result = safe_import('nonexistent_module_xyz')
        assert result.error_type == 'import'
        assert isinstance(result.error, ImportError)

    def test_attribute_error_type(self):
        """Test AttributeError is classified correctly"""
        result = safe_import('json', 'nonexistent_attribute_xyz')
        assert result.error_type == 'attribute'

    @patch('importlib.import_module')
    def test_syntax_error_type(self, mock_import):
        """Test SyntaxError is classified correctly"""
        mock_import.side_effect = SyntaxError("invalid syntax")
        result = safe_import('broken_module')
        assert result.error_type == 'syntax'
        assert isinstance(result.error, SyntaxError)

    @patch('importlib.import_module')
    def test_other_error_type(self, mock_import):
        """Test other exceptions are classified correctly"""
        mock_import.side_effect = ValueError("unexpected error")
        result = safe_import('broken_module')
        assert result.error_type == 'other'
        assert isinstance(result.error, ValueError)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
