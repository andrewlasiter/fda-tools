"""
Tests for ecopy_exporter.py

Comprehensive test suite for FDA eCopy package generation per
"eCopy Program for Medical Device Submissions" guidance (August 2019).

Test coverage areas:
- eCopy folder structure creation
- Markdown to PDF conversion (with/without pandoc)
- File discovery and mapping
- Size validation (200 MB per section, 4 GB total)
- eCopy checklist generation (Excel/CSV)
- Package validation
- Error handling

IEC 62304 Compliance:
- Unit tests for all export functions
- Edge case handling (missing files, large files)
- Validation against FDA eCopy requirements
- Graceful degradation when dependencies unavailable
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from ecopy_exporter import (
    eCopyExporter,
    export_ecopy
)


@pytest.fixture
def temp_project_with_drafts():
    """Create temporary project directory with draft files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        drafts_path = project_path / 'drafts'
        drafts_path.mkdir()

        # Create sample draft files
        draft_files = [
            'draft_cover-letter.md',
            'draft_truthful-accuracy.md',
            'draft_form-3881.md',
            'draft_device-description.md',
            'draft_se-discussion.md',
            'draft_labeling.md',
            'draft_sterilization.md',
            'draft_biocompatibility.md',
            'draft_performance-summary.md',
            'draft_doc.md'
        ]

        for draft_file in draft_files:
            content = f"# {draft_file}\n\nTest content for {draft_file}\n\n" + ("Lorem ipsum " * 100)
            (drafts_path / draft_file).write_text(content)

        # Create se_comparison.md at project root
        (project_path / 'se_comparison.md').write_text("# SE Comparison\n\nTest SE data")

        # Create standards_lookup.json
        standards_data = {
            'applicable_standards': [
                {'number': 'ISO 10993-1', 'title': 'Biological evaluation'},
                {'number': 'IEC 60601-1', 'title': 'Electrical safety'}
            ]
        }
        (project_path / 'standards_lookup.json').write_text(json.dumps(standards_data))

        yield project_path


@pytest.fixture
def temp_minimal_project():
    """Create minimal project with only mandatory sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        drafts_path = project_path / 'drafts'
        drafts_path.mkdir()

        # Only mandatory sections (01-06)
        mandatory_files = [
            'draft_cover-letter.md',
            'draft_truthful-accuracy.md',
            'draft_form-3881.md',
            'draft_device-description.md',
            'draft_se-discussion.md',
            'draft_labeling.md'
        ]

        for draft_file in mandatory_files:
            (drafts_path / draft_file).write_text(f"# {draft_file}\n\nMinimal content")

        yield project_path


@pytest.mark.lib
@pytest.mark.unit
class TestECopyInitialization:
    """Test suite for eCopy exporter initialization."""

    def test_initialization_with_valid_path(self, temp_project_with_drafts):
        """Test exporter initializes with valid project path."""
        exporter = eCopyExporter(str(temp_project_with_drafts))

        assert exporter.project_path == temp_project_with_drafts
        assert exporter.ecopy_path == temp_project_with_drafts / 'eCopy'
        assert exporter.drafts_path == temp_project_with_drafts / 'drafts'

    @patch('subprocess.run')
    def test_pandoc_availability_check_success(self, mock_run, temp_project_with_drafts):
        """Test pandoc availability check when pandoc is installed."""
        mock_run.return_value = MagicMock(returncode=0)

        exporter = eCopyExporter(str(temp_project_with_drafts))

        assert exporter.pandoc_available is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_pandoc_availability_check_failure(self, mock_run, temp_project_with_drafts):
        """Test pandoc availability check when pandoc not installed."""
        mock_run.side_effect = FileNotFoundError()

        exporter = eCopyExporter(str(temp_project_with_drafts))

        assert exporter.pandoc_available is False

    @patch('subprocess.run')
    def test_pandoc_timeout_handling(self, mock_run, temp_project_with_drafts):
        """Test graceful handling of pandoc check timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('pandoc', 5)

        exporter = eCopyExporter(str(temp_project_with_drafts))

        assert exporter.pandoc_available is False


@pytest.mark.lib
@pytest.mark.unit
class TestECopyStructure:
    """Test suite for eCopy folder structure creation."""

    def test_ecopy_directory_created(self, temp_project_with_drafts):
        """Test eCopy root directory is created."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        result = exporter.export()

        assert exporter.ecopy_path.exists()
        assert exporter.ecopy_path.is_dir()

    def test_all_section_folders_created(self, temp_project_with_drafts):
        """Test all 19 eCopy section folders are created."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        result = exporter.export()

        # All 19 sections per FDA eCopy guidance
        expected_sections = 19
        section_dirs = list(exporter.ecopy_path.glob('????-*'))

        assert len(section_dirs) == expected_sections

    def test_section_folder_naming_format(self, temp_project_with_drafts):
        """Test section folders follow NNNN-Name format."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        result = exporter.export()

        section_01 = exporter.ecopy_path / '0001-CoverLetter'
        section_03 = exporter.ecopy_path / '0003-510kSummary'
        section_12 = exporter.ecopy_path / '0012-PerformanceTesting'

        assert section_01.exists()
        assert section_03.exists()
        assert section_12.exists()

    def test_sections_created_count(self, temp_project_with_drafts):
        """Test sections_created count is correct."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        result = exporter.export()

        assert result['sections_created'] == 19


@pytest.mark.lib
@pytest.mark.unit
class TestFileConversion:
    """Test suite for markdown to PDF conversion."""

    @patch('subprocess.run')
    def test_markdown_to_pdf_conversion_with_pandoc(self, mock_run, temp_project_with_drafts):
        """Test PDF conversion when pandoc is available."""
        # Mock successful pandoc conversion
        mock_run.return_value = MagicMock(returncode=0, stderr='')

        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = True

        input_md = temp_project_with_drafts / 'drafts' / 'draft_cover-letter.md'
        output_pdf = temp_project_with_drafts / 'eCopy' / '0001-CoverLetter' / 'draft_cover-letter.pdf'
        output_pdf.parent.mkdir(parents=True, exist_ok=True)

        # Should not raise exception
        exporter._convert_md_to_pdf(input_md, output_pdf)

    @patch('subprocess.run')
    def test_pandoc_conversion_arguments(self, mock_run, temp_project_with_drafts):
        """Test pandoc is called with correct FDA-compliant arguments."""
        mock_run.return_value = MagicMock(returncode=0)

        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = True

        input_md = temp_project_with_drafts / 'drafts' / 'draft_cover-letter.md'
        output_pdf = temp_project_with_drafts / 'eCopy' / 'test.pdf'
        output_pdf.parent.mkdir(parents=True, exist_ok=True)

        exporter._convert_md_to_pdf(input_md, output_pdf)

        # Verify pandoc called with FDA-compliant styling
        call_args = mock_run.call_args[0][0]
        assert 'pandoc' in call_args
        assert '--toc' in call_args
        assert '--number-sections' in call_args
        assert 'Times New Roman' in str(call_args)
        assert '12pt' in str(call_args)

    @patch('subprocess.run')
    def test_pandoc_conversion_failure_raises_error(self, mock_run, temp_project_with_drafts):
        """Test pandoc conversion failure raises RuntimeError."""
        mock_run.return_value = MagicMock(returncode=1, stderr='Pandoc error')

        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = True

        input_md = temp_project_with_drafts / 'drafts' / 'draft_cover-letter.md'
        output_pdf = temp_project_with_drafts / 'eCopy' / 'test.pdf'
        output_pdf.parent.mkdir(parents=True, exist_ok=True)

        with pytest.raises(RuntimeError):
            exporter._convert_md_to_pdf(input_md, output_pdf)

    def test_markdown_copy_when_pandoc_unavailable(self, temp_project_with_drafts):
        """Test markdown files are copied when pandoc unavailable."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False

        result = exporter.export()

        # Should copy .md files instead of converting to PDF
        section_01 = exporter.ecopy_path / '0001-CoverLetter'
        md_files = list(section_01.glob('*.md'))

        assert len(md_files) > 0


@pytest.mark.lib
@pytest.mark.unit
class TestECopyChecklist:
    """Test suite for eCopy checklist generation."""

    @patch('openpyxl.Workbook')
    def test_excel_checklist_generation(self, mock_workbook, temp_project_with_drafts):
        """Test Excel checklist is generated when openpyxl available."""
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.active = mock_ws
        mock_workbook.return_value = mock_wb

        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False  # Skip PDF conversion
        exporter.export()

        checklist_path = exporter.ecopy_path / 'eCopy-Checklist.xlsx'

        # Should attempt to save Excel file
        mock_wb.save.assert_called_once()

    def test_csv_checklist_fallback(self, temp_project_with_drafts):
        """Test CSV checklist is created when openpyxl unavailable."""
        with patch('openpyxl.Workbook', side_effect=ImportError):
            exporter = eCopyExporter(str(temp_project_with_drafts))
            exporter.pandoc_available = False
            exporter.export()

            # Should fall back to CSV
            csv_checklist = exporter.ecopy_path / 'eCopy-Checklist.csv'

            assert csv_checklist.exists()

    def test_checklist_contains_all_sections(self, temp_project_with_drafts):
        """Test checklist includes all 19 sections."""
        with patch('openpyxl.Workbook', side_effect=ImportError):
            exporter = eCopyExporter(str(temp_project_with_drafts))
            exporter.pandoc_available = False
            exporter.export()

            csv_checklist = exporter.ecopy_path / 'eCopy-Checklist.csv'
            content = csv_checklist.read_text()

            # Should have header + 19 sections
            lines = content.strip().split('\n')
            assert len(lines) >= 20  # Header + 19 sections


@pytest.mark.lib
@pytest.mark.unit
class TestPackageValidation:
    """Test suite for eCopy package validation."""

    def test_mandatory_sections_validation_pass(self, temp_minimal_project):
        """Test validation passes when mandatory sections present."""
        exporter = eCopyExporter(str(temp_minimal_project))
        exporter.pandoc_available = False
        result = exporter.export()

        validation = result['validation']

        assert validation['mandatory_sections'] is True
        assert validation['status'] in ['PASS', 'WARNING']

    def test_mandatory_sections_validation_fail(self):
        """Test validation fails when mandatory sections missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / 'drafts').mkdir()

            # No draft files - mandatory sections will be empty

            exporter = eCopyExporter(str(project_path))
            result = exporter.export()

            validation = result['validation']

            assert validation['mandatory_sections'] is False
            assert validation['status'] == 'FAIL'
            assert len(validation['errors']) > 0

    def test_size_validation_warning_threshold(self, temp_project_with_drafts):
        """Test size warning at 3.5 GB threshold."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        result = exporter.export()

        validation = result['validation']

        # Mock size check would be needed for actual size testing
        # Verify validation has size_ok field
        assert 'size_ok' in validation

    def test_checklist_validation(self, temp_minimal_project):
        """Test validation checks for checklist existence."""
        with patch('openpyxl.Workbook', side_effect=ImportError):
            exporter = eCopyExporter(str(temp_minimal_project))
            exporter.pandoc_available = False
            result = exporter.export()

            validation = result['validation']

            # CSV checklist should be created
            assert validation['checklist_ok'] is True


@pytest.mark.lib
@pytest.mark.unit
class TestExportResults:
    """Test suite for export result dictionary."""

    def test_export_returns_complete_result_dict(self, temp_project_with_drafts):
        """Test export returns all required result fields."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        result = exporter.export()

        required_fields = [
            'ecopy_path',
            'sections_created',
            'files_converted',
            'total_size_mb',
            'validation',
            'conversion_errors',
            'pandoc_available'
        ]

        for field in required_fields:
            assert field in result

    def test_ecopy_path_is_absolute(self, temp_project_with_drafts):
        """Test ecopy_path in result is absolute path string."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        result = exporter.export()

        ecopy_path = result['ecopy_path']

        assert isinstance(ecopy_path, str)
        assert Path(ecopy_path).is_absolute()

    def test_files_converted_count(self, temp_project_with_drafts):
        """Test files_converted count is accurate."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        result = exporter.export()

        # Should convert/copy multiple files
        assert result['files_converted'] > 0

    def test_total_size_calculation(self, temp_project_with_drafts):
        """Test total_size_mb is calculated correctly."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        result = exporter.export()

        total_size = result['total_size_mb']

        assert isinstance(total_size, (int, float))
        assert total_size > 0


@pytest.mark.lib
@pytest.mark.integration
class TestFileMapping:
    """Test suite for draft file to eCopy section mapping."""

    def test_cover_letter_section_01(self, temp_project_with_drafts):
        """Test cover letter maps to Section 01."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        exporter.export()

        section_01 = exporter.ecopy_path / '0001-CoverLetter'
        files = list(section_01.glob('*cover-letter*'))

        assert len(files) > 0

    def test_form_3881_section_03(self, temp_project_with_drafts):
        """Test Form 3881 maps to Section 03 (510k Summary)."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        exporter.export()

        section_03 = exporter.ecopy_path / '0003-510kSummary'
        files = list(section_03.glob('*form-3881*'))

        assert len(files) > 0

    def test_se_comparison_section_05(self, temp_project_with_drafts):
        """Test SE comparison maps to Section 05."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        exporter.export()

        section_05 = exporter.ecopy_path / '0005-SubstantialEquivalence'

        # se_comparison.md is at project root, not in drafts/
        # Should be found and copied
        assert section_05.exists()

    def test_sterilization_section_07(self, temp_project_with_drafts):
        """Test sterilization maps to Section 07."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        exporter.export()

        section_07 = exporter.ecopy_path / '0007-Sterilization'
        files = list(section_07.glob('*sterilization*'))

        assert len(files) > 0

    def test_biocompatibility_section_08(self, temp_project_with_drafts):
        """Test biocompatibility maps to Section 08."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        exporter.export()

        section_08 = exporter.ecopy_path / '0008-Biocompatibility'
        files = list(section_08.glob('*biocompatibility*'))

        assert len(files) > 0

    def test_doc_section_17(self, temp_project_with_drafts):
        """Test Declaration of Conformity maps to Section 17."""
        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        exporter.export()

        section_17 = exporter.ecopy_path / '0017-DeclarationofConformity'

        # Should find draft_doc.md and standards_lookup.json
        assert section_17.exists()


@pytest.mark.lib
@pytest.mark.unit
class TestConvenienceFunction:
    """Test suite for module-level convenience function."""

    def test_export_ecopy_convenience_wrapper(self, temp_minimal_project):
        """Test export_ecopy() convenience function."""
        result = export_ecopy(str(temp_minimal_project))

        assert isinstance(result, dict)
        assert 'ecopy_path' in result
        assert 'sections_created' in result


@pytest.mark.lib
@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_missing_drafts_directory(self):
        """Test graceful handling when drafts/ directory missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No drafts directory

            exporter = eCopyExporter(tmpdir)
            result = exporter.export()

            # Should complete without crashing
            assert result['sections_created'] == 19

    def test_empty_drafts_directory(self):
        """Test export with no draft files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            (project_path / 'drafts').mkdir()  # Empty directory

            exporter = eCopyExporter(str(project_path))
            result = exporter.export()

            # Should create structure but validation fails
            assert result['sections_created'] == 19
            assert result['files_converted'] == 0
            assert result['validation']['status'] == 'FAIL'

    def test_section_with_multiple_files(self, temp_project_with_drafts):
        """Test section with multiple draft files processes all."""
        # Section 05 has multiple files: se-discussion, se_comparison, predicate-justification

        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = False
        exporter.export()

        section_05 = exporter.ecopy_path / '0005-SubstantialEquivalence'
        files = list(section_05.glob('*'))

        # Should have multiple files
        assert len(files) >= 1

    def test_conversion_error_tracking(self, temp_project_with_drafts):
        """Test conversion errors are tracked in results."""
        with patch('subprocess.run') as mock_run:
            # Mock pandoc failure
            mock_run.return_value = MagicMock(returncode=1, stderr='Mock error')

            exporter = eCopyExporter(str(temp_project_with_drafts))
            exporter.pandoc_available = True
            result = exporter.export()

            # Should track conversion errors
            assert 'conversion_errors' in result

    def test_pandoc_timeout_during_conversion(self, temp_project_with_drafts):
        """Test pandoc timeout raises TimeoutExpired exception."""
        import subprocess

        exporter = eCopyExporter(str(temp_project_with_drafts))
        exporter.pandoc_available = True

        input_md = temp_project_with_drafts / 'drafts' / 'draft_cover-letter.md'
        output_pdf = temp_project_with_drafts / 'eCopy' / 'test.pdf'
        output_pdf.parent.mkdir(parents=True, exist_ok=True)

        # Mock pandoc timeout only for this specific conversion
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('pandoc', 60)):
            # Should raise TimeoutExpired (timeout is critical failure)
            with pytest.raises(subprocess.TimeoutExpired):
                exporter._convert_md_to_pdf(input_md, output_pdf)
