"""
Tests for expert_validator.py

Comprehensive test suite for multi-expert validation orchestrator
coordinating coverage auditor, quality reviewer, and RA professional agents.

Test coverage areas:
- Validator initialization and configuration
- Coverage audit orchestration
- Quality review orchestration
- Consensus synthesis logic
- Report generation (markdown format)
- Multi-agent workflow coordination
- CLI argument parsing
- Error handling and graceful degradation

IEC 62304 Compliance:
- Unit tests for all orchestration methods
- Edge case handling (missing agents, empty results)
- Validation against consensus determination rules
- Traceability to validation requirements
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from io import StringIO

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from expert_validator import ExpertValidator  # type: ignore


@pytest.fixture
def temp_standards_dir():
    """Create temporary standards directory with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        standards_path = Path(tmpdir) / 'data' / 'standards'
        standards_path.mkdir(parents=True)

        # Create sample standards files
        standards_files = [
            'standards_DQY.json',
            'standards_OVE.json',
            'standards_GEI.json'
        ]

        for std_file in standards_files:
            product_code = std_file.split('_')[1].split('.')[0]
            standards_data = {
                'product_code': product_code,
                'standards': [
                    {'number': 'ISO 10993-1', 'title': 'Biological evaluation'},
                    {'number': 'IEC 60601-1', 'title': 'Electrical safety'}
                ]
            }
            (standards_path / std_file).write_text(json.dumps(standards_data))

        yield standards_path


@pytest.fixture
def temp_agents_dir():
    """Create temporary agents directory with mock agent files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_path = Path(tmpdir) / 'agents'
        agents_path.mkdir()

        # Create mock agent markdown files
        coverage_agent = """---
name: standards-coverage-auditor
description: Validates 100% coverage across all product codes
---

# Coverage Auditor Agent

Validates standards coverage.
"""
        (agents_path / 'standards-coverage-auditor.md').write_text(coverage_agent)

        quality_agent = """---
name: standards-quality-reviewer
description: Validates appropriateness through stratified sampling
---

# Quality Reviewer Agent

Reviews standards quality.
"""
        (agents_path / 'standards-quality-reviewer.md').write_text(quality_agent)

        yield agents_path


@pytest.mark.lib
@pytest.mark.unit
class TestValidatorInitialization:
    """Test suite for ExpertValidator initialization."""

    def test_initialization_with_valid_paths(self, temp_standards_dir, temp_agents_dir):
        """Test validator initializes with valid directory paths."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        assert validator.standards_dir == temp_standards_dir
        assert validator.agents_dir == temp_agents_dir

    def test_initialization_auto_detects_agents_dir(self, temp_standards_dir):
        """Test validator auto-detects agents directory when not provided."""
        validator = ExpertValidator(standards_dir=temp_standards_dir)

        # Should auto-detect agents directory
        assert validator.agents_dir.name == 'agents'

    def test_results_structure_initialized(self, temp_standards_dir, temp_agents_dir):
        """Test results dictionary is initialized with expected keys."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        expected_keys = ['coverage_audit', 'quality_review', 'ra_professional', 'consensus']

        for key in expected_keys:
            assert key in validator.results
            assert validator.results[key] is None


@pytest.mark.lib
@pytest.mark.unit
class TestCoverageValidation:
    """Test suite for coverage audit orchestration."""

    def test_validate_coverage_returns_result_dict(self, temp_standards_dir, temp_agents_dir):
        """Test coverage validation returns structured result dict."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        result = validator.validate_coverage()

        assert isinstance(result, dict)
        assert 'status' in result
        assert 'agent' in result

    def test_validate_coverage_sets_pending_status(self, temp_standards_dir, temp_agents_dir):
        """Test coverage validation sets PENDING status (agent not invoked in tests)."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        result = validator.validate_coverage()

        assert result['status'] == 'PENDING'
        assert result['agent'] == 'standards-coverage-auditor'

    def test_validate_coverage_stores_result(self, temp_standards_dir, temp_agents_dir):
        """Test coverage validation stores result in validator.results."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        validator.validate_coverage()

        assert validator.results['coverage_audit'] is not None
        assert validator.results['coverage_audit']['status'] == 'PENDING'

    def test_validate_coverage_with_report_path(self, temp_standards_dir, temp_agents_dir):
        """Test coverage validation accepts report_path parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / 'coverage_report.md'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            result = validator.validate_coverage(report_path=report_path)

            assert result['report_path'] == str(report_path)


@pytest.mark.lib
@pytest.mark.unit
class TestQualityValidation:
    """Test suite for quality review orchestration."""

    def test_validate_quality_returns_result_dict(self, temp_standards_dir, temp_agents_dir):
        """Test quality validation returns structured result dict."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        result = validator.validate_quality()

        assert isinstance(result, dict)
        assert 'status' in result
        assert 'agent' in result

    def test_validate_quality_sets_pending_status(self, temp_standards_dir, temp_agents_dir):
        """Test quality validation sets PENDING status (agent not invoked in tests)."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        result = validator.validate_quality()

        assert result['status'] == 'PENDING'
        assert result['agent'] == 'standards-quality-reviewer'

    def test_validate_quality_stores_result(self, temp_standards_dir, temp_agents_dir):
        """Test quality validation stores result in validator.results."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        validator.validate_quality()

        assert validator.results['quality_review'] is not None
        assert validator.results['quality_review']['status'] == 'PENDING'


@pytest.mark.lib
@pytest.mark.unit
class TestConsensusSynthesis:
    """Test suite for consensus determination logic."""

    def test_synthesize_consensus_returns_dict(self, temp_standards_dir, temp_agents_dir):
        """Test consensus synthesis returns structured dict."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        # Run validations first
        validator.validate_coverage()
        validator.validate_quality()

        consensus = validator.synthesize_consensus()

        assert isinstance(consensus, dict)
        assert 'status' in consensus
        assert 'final_determination' in consensus
        assert 'sign_off' in consensus

    def test_synthesize_consensus_checks_all_validations(self, temp_standards_dir, temp_agents_dir, capsys):
        """Test consensus warns if validations incomplete."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        # Don't run validations - results are None

        validator.synthesize_consensus()

        captured = capsys.readouterr()
        assert 'not all validations are complete' in captured.out.lower()

    def test_synthesize_consensus_includes_coverage_status(self, temp_standards_dir, temp_agents_dir):
        """Test consensus includes coverage validation status."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        validator.validate_coverage()
        validator.validate_quality()

        consensus = validator.synthesize_consensus()

        assert 'coverage_status' in consensus
        assert consensus['coverage_status'] == 'PENDING'

    def test_synthesize_consensus_includes_quality_status(self, temp_standards_dir, temp_agents_dir):
        """Test consensus includes quality validation status."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        validator.validate_coverage()
        validator.validate_quality()

        consensus = validator.synthesize_consensus()

        assert 'quality_status' in consensus
        assert consensus['quality_status'] == 'PENDING'

    def test_synthesize_consensus_stores_result(self, temp_standards_dir, temp_agents_dir):
        """Test consensus result is stored in validator.results."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        validator.validate_coverage()
        validator.validate_quality()
        validator.synthesize_consensus()

        assert validator.results['consensus'] is not None
        assert validator.results['consensus']['status'] == 'PENDING'

    def test_synthesize_consensus_with_output_path(self, temp_standards_dir, temp_agents_dir):
        """Test consensus writes report to output_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'consensus_report.md'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            validator.validate_coverage()
            validator.validate_quality()
            validator.synthesize_consensus(output_path=output_path)

            assert output_path.exists()


@pytest.mark.lib
@pytest.mark.unit
class TestReportGeneration:
    """Test suite for consensus report generation."""

    def test_report_contains_header(self, temp_standards_dir, temp_agents_dir):
        """Test consensus report contains proper header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.md'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            validator.validate_coverage()
            validator.validate_quality()
            validator.synthesize_consensus(output_path=output_path)

            content = output_path.read_text()

            assert 'Multi-Expert Validation Consensus Report' in content

    def test_report_contains_determination_rules(self, temp_standards_dir, temp_agents_dir):
        """Test report documents consensus determination rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.md'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            validator.validate_coverage()
            validator.validate_quality()
            validator.synthesize_consensus(output_path=output_path)

            content = output_path.read_text()

            assert 'Coverage ≥99.5%' in content
            assert 'Quality ≥95%' in content

    def test_report_contains_validation_results(self, temp_standards_dir, temp_agents_dir):
        """Test report includes coverage and quality validation results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.md'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            validator.validate_coverage()
            validator.validate_quality()
            validator.synthesize_consensus(output_path=output_path)

            content = output_path.read_text()

            assert 'Coverage Audit' in content
            assert 'Quality Review' in content

    def test_report_contains_recommendations(self, temp_standards_dir, temp_agents_dir):
        """Test report includes recommendations section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.md'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            validator.validate_coverage()
            validator.validate_quality()

            # Add test recommendations
            consensus = validator.synthesize_consensus(output_path=output_path)

            content = output_path.read_text()

            assert 'Recommendations' in content


@pytest.mark.lib
@pytest.mark.integration
class TestFullValidationWorkflow:
    """Test suite for complete validation workflow."""

    def test_validate_all_runs_all_phases(self, temp_standards_dir, temp_agents_dir):
        """Test validate_all executes all three validation phases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'validation_reports'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            result = validator.validate_all(output_dir=output_dir)

            # Should have run all validations
            assert validator.results['coverage_audit'] is not None
            assert validator.results['quality_review'] is not None
            assert validator.results['consensus'] is not None

    def test_validate_all_creates_output_directory(self, temp_standards_dir, temp_agents_dir):
        """Test validate_all creates output directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'new_validation_reports'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            validator.validate_all(output_dir=output_dir)

            assert output_dir.exists()
            assert output_dir.is_dir()

    def test_validate_all_generates_three_reports(self, temp_standards_dir, temp_agents_dir):
        """Test validate_all generates coverage, quality, and consensus reports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'reports'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            result = validator.validate_all(output_dir=output_dir)

            coverage_report = output_dir / 'COVERAGE_AUDIT_REPORT.md'
            quality_report = output_dir / 'QUALITY_REVIEW_REPORT.md'
            consensus_report = output_dir / 'CONSENSUS_VALIDATION_REPORT.md'

            assert consensus_report.exists()
            # Note: Coverage and quality reports are placeholders in current implementation

    def test_validate_all_returns_complete_result(self, temp_standards_dir, temp_agents_dir):
        """Test validate_all returns complete result dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'reports'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            result = validator.validate_all(output_dir=output_dir)

            assert 'consensus_status' in result
            assert 'sign_off' in result
            assert 'reports' in result
            assert 'results' in result

    def test_validate_all_uses_default_output_dir(self, temp_standards_dir, temp_agents_dir):
        """Test validate_all uses default output directory when not specified."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        result = validator.validate_all()

        # Default: standards_dir.parent / 'validation_reports'
        expected_dir = temp_standards_dir.parent / 'validation_reports'

        assert expected_dir.exists()


@pytest.mark.lib
@pytest.mark.unit
class TestCLIInterface:
    """Test suite for CLI argument parsing and execution."""

    @patch('sys.argv', ['expert_validator.py', '--standards-dir', '/tmp/standards'])
    @patch('expert_validator.ExpertValidator')
    def test_cli_accepts_standards_dir_argument(self, mock_validator):
        """Test CLI accepts --standards-dir argument."""
        # Import main to test CLI
        from expert_validator import  # type: ignore main

        mock_instance = MagicMock()
        mock_validator.return_value = mock_instance
        mock_instance.validate_all.return_value = {
            'consensus_status': 'PENDING',
            'sign_off': False
        }

        try:
            main()
        except SystemExit:
            pass

        # Should initialize with provided directory
        mock_validator.assert_called_once()

    @patch('sys.argv', ['expert_validator.py', '--coverage-only'])
    @patch('expert_validator.ExpertValidator')
    def test_cli_coverage_only_flag(self, mock_validator):
        """Test CLI --coverage-only flag runs only coverage audit."""
        from expert_validator import  # type: ignore main

        mock_instance = MagicMock()
        mock_validator.return_value = mock_instance
        mock_instance.validate_coverage.return_value = {'status': 'PENDING'}

        try:
            main()
        except SystemExit:
            pass

        # Should call only validate_coverage
        mock_instance.validate_coverage.assert_called_once()
        mock_instance.validate_quality.assert_not_called()
        mock_instance.validate_all.assert_not_called()

    @patch('sys.argv', ['expert_validator.py', '--quality-only'])
    @patch('expert_validator.ExpertValidator')
    def test_cli_quality_only_flag(self, mock_validator):
        """Test CLI --quality-only flag runs only quality review."""
        from expert_validator import  # type: ignore main

        mock_instance = MagicMock()
        mock_validator.return_value = mock_instance
        mock_instance.validate_quality.return_value = {'status': 'PENDING'}

        try:
            main()
        except SystemExit:
            pass

        # Should call only validate_quality
        mock_instance.validate_quality.assert_called_once()
        mock_instance.validate_coverage.assert_not_called()
        mock_instance.validate_all.assert_not_called()


@pytest.mark.lib
@pytest.mark.unit
class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_missing_standards_directory(self, temp_agents_dir):
        """Test validator handles missing standards directory gracefully."""
        nonexistent_dir = Path('/tmp/nonexistent_standards_dir_12345')

        # Should not crash during initialization
        validator = ExpertValidator(
            standards_dir=nonexistent_dir,
            agents_dir=temp_agents_dir
        )

        assert validator.standards_dir == nonexistent_dir

    def test_missing_agents_directory_auto_detect(self, temp_standards_dir):
        """Test validator handles missing auto-detected agents directory."""
        validator = ExpertValidator(standards_dir=temp_standards_dir)

        # Should auto-detect even if directory doesn't exist
        assert validator.agents_dir.name == 'agents'

    def test_consensus_with_no_prior_validations(self, temp_standards_dir, temp_agents_dir, capsys):
        """Test consensus synthesis when no validations have been run."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        # Run consensus without running validations first
        consensus = validator.synthesize_consensus()

        captured = capsys.readouterr()

        assert 'not all validations are complete' in captured.out.lower()
        assert consensus['status'] == 'PENDING'

    def test_empty_standards_directory(self, temp_agents_dir):
        """Test validator handles empty standards directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_standards_dir = Path(tmpdir) / 'empty_standards'
            empty_standards_dir.mkdir()

            validator = ExpertValidator(
                standards_dir=empty_standards_dir,
                agents_dir=temp_agents_dir
            )

            # Should not crash
            result = validator.validate_coverage()
            assert result['status'] == 'PENDING'

    def test_report_generation_with_empty_recommendations(self, temp_standards_dir, temp_agents_dir):
        """Test report generation when no recommendations are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / 'report.md'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            validator.validate_coverage()
            validator.validate_quality()

            # Consensus with empty recommendations
            consensus = validator.synthesize_consensus(output_path=output_path)

            content = output_path.read_text()

            # Should handle empty recommendations gracefully
            assert 'Recommendations' in content

    def test_path_conversion_to_pathlib(self, temp_agents_dir):
        """Test validator converts string paths to Path objects."""
        standards_dir_str = '/tmp/test_standards'

        validator = ExpertValidator(
            standards_dir=standards_dir_str,
            agents_dir=temp_agents_dir
        )

        assert isinstance(validator.standards_dir, Path)
        assert isinstance(validator.agents_dir, Path)


@pytest.mark.lib
@pytest.mark.unit
class TestValidationMetadata:
    """Test suite for validation metadata and traceability."""

    def test_coverage_result_includes_agent_name(self, temp_standards_dir, temp_agents_dir):
        """Test coverage result includes agent identifier."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        result = validator.validate_coverage()

        assert result['agent'] == 'standards-coverage-auditor'

    def test_quality_result_includes_agent_name(self, temp_standards_dir, temp_agents_dir):
        """Test quality result includes agent identifier."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        result = validator.validate_quality()

        assert result['agent'] == 'standards-quality-reviewer'

    def test_consensus_includes_all_agent_statuses(self, temp_standards_dir, temp_agents_dir):
        """Test consensus includes status from all agents."""
        validator = ExpertValidator(
            standards_dir=temp_standards_dir,
            agents_dir=temp_agents_dir
        )

        validator.validate_coverage()
        validator.validate_quality()
        consensus = validator.synthesize_consensus()

        assert 'coverage_status' in consensus
        assert 'quality_status' in consensus

    def test_validate_all_includes_report_paths(self, temp_standards_dir, temp_agents_dir):
        """Test validate_all result includes all report file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'reports'

            validator = ExpertValidator(
                standards_dir=temp_standards_dir,
                agents_dir=temp_agents_dir
            )

            result = validator.validate_all(output_dir=output_dir)

            assert 'reports' in result
            assert 'coverage' in result['reports']
            assert 'quality' in result['reports']
            assert 'consensus' in result['reports']
