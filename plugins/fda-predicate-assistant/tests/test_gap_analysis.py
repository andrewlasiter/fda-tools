#!/usr/bin/env python3
"""
Unit tests for gap_analyzer.py - Phase 4 Feature 1

Tests automated gap detection for:
- Missing device data
- Weak predicates
- Testing gaps
- Confidence scoring
"""

import sys
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta

# Add lib directory to path
lib_path = Path(__file__).parent.parent / 'lib'
sys.path.insert(0, str(lib_path))

from gap_analyzer import (
    GapAnalyzer,
    calculate_gap_analysis_confidence,
    generate_gap_analysis_report,
    write_gap_data_json,
    update_enrichment_metadata
)


class TestGapDetection:
    """Test suite for gap detection functions."""

    def test_detect_missing_device_data_perfect(self):
        """Test 1: Perfect device profile with no missing data."""
        # Create temp project with complete device profile
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Complete device profile
            device_profile = {
                'indications_for_use': 'Treatment of coronary artery disease',
                'intended_use_statement': 'Deliver stent to coronary arteries',
                'technological_characteristics': 'Balloon-expandable cobalt-chromium',
                'device_description': 'Coronary stent system',
                'materials': 'Cobalt-chromium alloy, polymer coating',
                'product_code': 'DQY',
                'regulation_number': '870.3250',
                'device_class': '2',
                'sterilization_method': 'Ethylene oxide',
                'shelf_life': '24 months',
                'intended_user': 'Interventional cardiologists',
                'use_environment': 'Hospital catheterization laboratory'
            }

            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            # Test
            analyzer = GapAnalyzer(str(project_dir))
            gaps = analyzer.detect_missing_device_data()

            # Assert: Should have no HIGH priority gaps
            high_gaps = [g for g in gaps if g.get('priority') == 'HIGH']
            assert len(high_gaps) == 0, "Perfect profile should have no HIGH priority gaps"

    def test_detect_missing_device_data_sparse(self):
        """Test 2: Sparse device profile with multiple missing fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Sparse device profile (only product code)
            device_profile = {
                'product_code': 'DQY',
                'indications_for_use': '',  # Empty string
                'materials': None  # Null value
            }

            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            # Test
            analyzer = GapAnalyzer(str(project_dir))
            gaps = analyzer.detect_missing_device_data()

            # Assert: Should have multiple HIGH priority gaps
            high_gaps = [g for g in gaps if g.get('priority') == 'HIGH']
            assert len(high_gaps) >= 5, "Sparse profile should have ≥5 HIGH priority gaps"

            # Verify specific gaps
            gap_fields = [g.get('field') for g in high_gaps]
            assert 'indications_for_use' in gap_fields
            assert 'materials' in gap_fields
            assert 'technological_characteristics' in gap_fields

    def test_detect_weak_predicates_recalls(self):
        """Test 3: Weak predicate with ≥2 recalls should be HIGH priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create review.json with weak predicate (2+ recalls)
            review_data = {
                'accepted_predicates': [
                    {
                        'k_number': 'K123456',
                        'device_name': 'Example Stent',
                        'recalls_total': 3,  # HIGH priority trigger
                        'decision_date': '2020-05-15'
                    }
                ]
            }

            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            # Create minimal device_profile
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump({'product_code': 'DQY'}, f)

            # Test
            analyzer = GapAnalyzer(str(project_dir))
            weak = analyzer.detect_weak_predicates()

            # Assert: Should flag as HIGH priority
            assert len(weak) == 1
            assert weak[0].get('priority') == 'HIGH'
            assert weak[0].get('k_number') == 'K123456'
            assert '3 recalls' in weak[0].get('reason', '')

    def test_calculate_confidence_high(self):
        """Test 4: High confidence when data is complete and predicates good."""
        # Mock complete gap results
        gap_results = {
            'missing_data': [],  # No missing data
            'weak_predicates': [{
                'k_number': 'K123456',
                'priority': 'LOW',  # No high-priority weak predicates
                'confidence': 90
            }],
            'testing_gaps': [],
            'summary': {
                'total_gaps': 1,
                'high_priority': 0,
                'critical': 0
            }
        }

        # Complete device profile with all HIGH and MEDIUM priority fields
        device_profile = {
            # HIGH priority
            'indications_for_use': 'Complete',
            'intended_use_statement': 'Complete',
            'technological_characteristics': 'Complete',
            'device_description': 'Complete',
            'materials': 'Complete',
            'product_code': 'DQY',
            'regulation_number': '870.3250',
            'device_class': '2',
            # MEDIUM priority
            'sterilization_method': 'EO',
            'shelf_life': '24 months',
            'intended_user': 'Physicians',
            'use_environment': 'Hospital',
            'operating_principle': 'Mechanical',
            'power_source': 'Battery',
            'dimensions': '10x5x2 cm',
            'biocompatibility': 'ISO 10993'
        }

        # Test
        confidence = calculate_gap_analysis_confidence(gap_results, device_profile)

        # Assert: Should be HIGH or MEDIUM confidence (good score)
        assert confidence.get('confidence_level') in ['HIGH', 'MEDIUM']
        assert confidence.get('confidence_score') >= 70

    def test_calculate_confidence_low(self):
        """Test 5: Low confidence when data is sparse and predicates weak."""
        # Mock incomplete gap results
        gap_results = {
            'missing_data': [
                {'priority': 'HIGH', 'confidence': 95},
                {'priority': 'HIGH', 'confidence': 95},
                {'priority': 'HIGH', 'confidence': 95}
            ],
            'weak_predicates': [{
                'k_number': 'K123456',
                'priority': 'HIGH',  # High-priority weak predicate
                'confidence': 90
            }],
            'testing_gaps': [
                {'priority': 'HIGH', 'confidence': 85}
            ],
            'summary': {
                'total_gaps': 5,
                'high_priority': 4,
                'critical': 0
            }
        }

        # Sparse device profile
        device_profile = {
            'product_code': 'DQY'  # Only product code
        }

        # Test
        confidence = calculate_gap_analysis_confidence(gap_results, device_profile)

        # Assert: Should be LOW confidence
        assert confidence.get('confidence_level') == 'LOW'
        assert confidence.get('confidence_score') < 70

    def test_fallback_no_predicates(self):
        """Test 6: Graceful fallback when no predicates in review.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create empty review.json
            with open(project_dir / 'review.json', 'w') as f:
                json.dump({'accepted_predicates': []}, f)

            # Create minimal device_profile
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump({'product_code': 'DQY'}, f)

            # Test
            analyzer = GapAnalyzer(str(project_dir))
            weak = analyzer.detect_weak_predicates()

            # Assert: Should return fallback message
            assert len(weak) == 1
            assert weak[0].get('k_number') == 'N/A'
            assert weak[0].get('priority') == 'HIGH'
            assert 'No accepted predicates' in weak[0].get('reason', '')


class TestReportGeneration:
    """Test suite for report generation functions."""

    def test_generate_report_structure(self):
        """Test that generated report has all required sections."""
        gap_results = {
            'missing_data': [],
            'weak_predicates': [],
            'testing_gaps': [],
            'summary': {'total_gaps': 0, 'high_priority': 0, 'medium_priority': 0,
                       'low_priority': 0, 'critical': 0},
            'timestamp': datetime.now().isoformat()
        }

        confidence = {
            'confidence_score': 95,
            'confidence_level': 'HIGH',
            'interpretation': 'High confidence analysis',
            'contributing_factors': {
                'data_completeness': 40,
                'predicate_quality': 30,
                'gap_clarity': 20,
                'cross_validation': 5
            }
        }

        report = generate_gap_analysis_report(gap_results, confidence, 'Test Project')

        # Assert: Check required sections
        assert '# Automated Gap Analysis Report' in report
        assert 'Executive Summary' in report
        assert 'Missing Device Data' in report
        assert 'Weak Predicate Indicators' in report
        assert 'Testing & Standards Gaps' in report
        assert 'Recommended Actions' in report
        assert 'Human Review Checkpoints' in report
        assert 'Automation Metadata' in report
        assert '⚠️ **AUTOMATION ASSISTS' in report  # Disclaimer

    def test_write_gap_data_json(self):
        """Test JSON data writing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gap_results = {
                'missing_data': [],
                'summary': {'total_gaps': 0}
            }
            confidence = {'confidence_score': 95, 'confidence_level': 'HIGH'}

            json_path = Path(tmpdir) / 'test_gaps.json'
            write_gap_data_json(gap_results, confidence, str(json_path))

            # Assert: File exists and valid JSON
            assert json_path.exists()
            with open(json_path, 'r') as f:
                data = json.load(f)
                assert 'gap_analysis' in data
                assert 'confidence' in data
                assert 'metadata' in data

    def test_update_enrichment_metadata(self):
        """Test enrichment metadata update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gap_results = {
                'timestamp': datetime.now().isoformat(),
                'summary': {'total_gaps': 5, 'high_priority': 2}
            }
            confidence = {
                'confidence_score': 75,
                'confidence_level': 'MEDIUM'
            }

            update_enrichment_metadata(tmpdir, gap_results, confidence)

            # Assert: Metadata file created
            metadata_path = Path(tmpdir) / 'enrichment_metadata.json'
            assert metadata_path.exists()

            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                assert 'gap_analysis' in metadata
                assert metadata['gap_analysis']['confidence_score'] == 75
                assert metadata['gap_analysis']['total_gaps'] == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
