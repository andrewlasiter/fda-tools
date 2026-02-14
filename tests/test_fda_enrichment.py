"""
pytest Test Suite for FDA Enrichment Phase 1 & 2
=================================================

Production test suite with assertion-based testing framework.
Tests call actual production code from fda_enrichment.py module.

Version: 2.0.1 (Production Ready)
Date: 2026-02-13

Usage:
    pytest tests/test_fda_enrichment.py -v
    pytest tests/test_fda_enrichment.py::TestPhase1DataIntegrity -v
    pytest tests/test_fda_enrichment.py::TestPhase2Intelligence -v
"""

import pytest
import sys
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / 'plugins' / 'fda-tools' / 'lib'
sys.path.insert(0, str(lib_path))

from fda_enrichment import FDAEnrichment


class TestPhase1DataIntegrity:
    """Test Phase 1: Data Integrity functions"""

    @pytest.fixture
    def enricher(self):
        """Create enrichment instance for testing"""
        return FDAEnrichment(api_version="2.0.1")

    @pytest.fixture
    def perfect_device(self):
        """Perfect device with all fields populated"""
        return {
            'KNUMBER': 'K123456',
            'PRODUCTCODE': 'DQY',
            'DECISIONDATE': '2024-01-15',
            'maude_productcode_5y': 1847,
            'maude_trending': 'stable',
            'maude_recent_6m': 145,
            'maude_scope': 'PRODUCT_CODE',
            'recalls_total': 0,
            'recall_latest_date': '',
            'recall_class': '',
            'recall_status': '',
            'api_validated': 'Yes',
            'decision': 'Substantially Equivalent (SESE)',
            'expedited_review': 'N',
            'statement_or_summary': 'Summary'
        }

    @pytest.fixture
    def incomplete_device(self):
        """Device with missing fields"""
        return {
            'KNUMBER': 'K999999',
            'PRODUCTCODE': 'GEI',
            'DECISIONDATE': '2010-06-20',
            'maude_productcode_5y': 'N/A',
            'maude_trending': 'unknown',
            'recalls_total': 0,
            'api_validated': 'No',
            'decision': 'Unknown',
            'statement_or_summary': 'Unknown'
        }

    def test_quality_score_perfect_device(self, enricher, perfect_device):
        """Test quality score for perfect device (all fields populated)"""
        api_log = [
            {'query': 'MAUDE:DQY', 'success': True},
            {'query': 'Recall:K123456', 'success': True},
            {'query': '510k:K123456', 'success': True}
        ]

        score = enricher.calculate_enrichment_completeness_score(perfect_device, api_log)

        assert isinstance(score, (int, float)), "Score should be numeric"
        assert 0 <= score <= 100, "Score should be 0-100"
        assert score >= 95, f"Perfect device should score >=95, got {score}"

    def test_quality_score_incomplete_device(self, enricher, incomplete_device):
        """Test quality score for device with missing data"""
        api_log = [
            {'query': 'MAUDE:GEI', 'success': False},
            {'query': 'Recall:K999999', 'success': True},
            {'query': '510k:K999999', 'success': False}
        ]

        score = enricher.calculate_enrichment_completeness_score(incomplete_device, api_log)

        assert isinstance(score, (int, float)), "Score should be numeric"
        assert 0 <= score <= 100, "Score should be 0-100"
        assert score < 60, f"Incomplete device should score <60, got {score}"

    def test_maude_data_structure(self, enricher):
        """Test MAUDE data returns correct structure"""
        maude_data = enricher.get_maude_events_by_product_code('DQY')

        assert isinstance(maude_data, dict), "MAUDE data should be dict"
        assert 'maude_productcode_5y' in maude_data, "Should have 5-year count"
        assert 'maude_trending' in maude_data, "Should have trending"
        assert 'maude_scope' in maude_data, "Should have scope declaration"
        assert maude_data['maude_scope'] in ['PRODUCT_CODE', 'UNAVAILABLE'], "Scope should be valid"

    def test_maude_scope_is_product_code(self, enricher):
        """Test MAUDE scope is correctly marked as PRODUCT_CODE"""
        maude_data = enricher.get_maude_events_by_product_code('DQY')

        # Critical test: MAUDE must be marked as product code level
        if maude_data['maude_productcode_5y'] != 'N/A':
            assert maude_data['maude_scope'] == 'PRODUCT_CODE', \
                "MAUDE data MUST be marked as PRODUCT_CODE scope"

    def test_recall_data_structure(self, enricher):
        """Test recall data returns correct structure"""
        recalls = enricher.get_recall_history('K123456')

        assert isinstance(recalls, dict), "Recalls should be dict"
        assert 'recalls_total' in recalls, "Should have total count"
        assert 'recall_latest_date' in recalls, "Should have latest date"
        assert 'recall_class' in recalls, "Should have recall class"
        assert 'recall_status' in recalls, "Should have recall status"

    def test_recall_total_is_numeric(self, enricher):
        """Test recall total is numeric"""
        recalls = enricher.get_recall_history('K123456')

        assert isinstance(recalls['recalls_total'], int), "recalls_total should be integer"
        assert recalls['recalls_total'] >= 0, "recalls_total should be non-negative"

    def test_510k_validation_structure(self, enricher):
        """Test 510(k) validation returns correct structure"""
        validation = enricher.get_510k_validation('K123456')

        assert isinstance(validation, dict), "Validation should be dict"
        assert 'api_validated' in validation, "Should have validation status"
        assert 'decision' in validation, "Should have decision"
        assert 'expedited_review' in validation, "Should have expedited flag"
        assert 'statement_or_summary' in validation, "Should have statement/summary"

    def test_510k_validation_status_values(self, enricher):
        """Test 510(k) validation status has valid values"""
        validation = enricher.get_510k_validation('K123456')

        assert validation['api_validated'] in ['Yes', 'No'], \
            "api_validated should be 'Yes' or 'No'"


class TestPhase2Intelligence:
    """Test Phase 2: Intelligence Layer functions"""

    @pytest.fixture
    def enricher(self):
        """Create enrichment instance for testing"""
        return FDAEnrichment(api_version="2.0.1")

    def test_clinical_detection_positive(self, enricher):
        """Test clinical data detection with positive keywords"""
        validation_data = {'api_validated': 'Yes'}
        decision_desc = "Device approved with clinical study demonstrating safety and effectiveness"

        clinical = enricher.assess_predicate_clinical_history(validation_data, decision_desc)

        assert isinstance(clinical, dict), "Clinical data should be dict"
        assert clinical['predicate_clinical_history'] == 'YES', \
            "Should detect clinical data from keywords"
        assert 'clinical_study_mentioned' in clinical['predicate_clinical_indicators'], \
            "Should flag clinical study indicator"

    def test_clinical_detection_negative(self, enricher):
        """Test clinical data detection with no clinical keywords"""
        validation_data = {'api_validated': 'Yes'}
        decision_desc = "Substantially Equivalent based on bench testing and biocompatibility"

        clinical = enricher.assess_predicate_clinical_history(validation_data, decision_desc)

        assert isinstance(clinical, dict), "Clinical data should be dict"
        assert clinical['predicate_clinical_history'] in ['NO', 'UNKNOWN'], \
            "Should not detect clinical data without keywords"

    def test_clinical_detection_postmarket(self, enricher):
        """Test detection of postmarket surveillance"""
        validation_data = {'api_validated': 'Yes'}
        decision_desc = "SE with postmarket surveillance requirements under 522 order"

        clinical = enricher.assess_predicate_clinical_history(validation_data, decision_desc)

        assert clinical['predicate_clinical_history'] == 'YES', \
            "Should detect postmarket requirements"
        assert clinical['predicate_study_type'] == 'postmarket', \
            "Should identify as postmarket study type"

    def test_clinical_detection_special_controls(self, enricher):
        """Test detection of special controls"""
        validation_data = {'api_validated': 'Yes'}
        decision_desc = "SE subject to special controls per guidance document"

        clinical = enricher.assess_predicate_clinical_history(validation_data, decision_desc)

        assert clinical['special_controls_applicable'] == 'YES', \
            "Should detect special controls"

    def test_predicate_acceptability_no_recalls(self, enricher):
        """Test predicate acceptability with no recalls"""
        recalls_data = {'recalls_total': 0}
        clearance_date = '2022-06-15'

        acceptability = enricher.assess_predicate_acceptability('K123456', recalls_data, clearance_date)

        assert isinstance(acceptability, dict), "Acceptability should be dict"
        assert acceptability['predicate_acceptability'] == 'ACCEPTABLE', \
            "Recent device with no recalls should be ACCEPTABLE"
        assert 'Suitable for primary predicate' in acceptability['predicate_recommendation'], \
            "Should recommend as primary predicate"

    def test_predicate_acceptability_one_recall(self, enricher):
        """Test predicate acceptability with one recall"""
        recalls_data = {'recalls_total': 1}
        clearance_date = '2020-03-10'

        acceptability = enricher.assess_predicate_acceptability('K123456', recalls_data, clearance_date)

        assert acceptability['predicate_acceptability'] == 'REVIEW_REQUIRED', \
            "Device with one recall should require review"
        assert '1 recall(s) on record' in acceptability['predicate_risk_factors'], \
            "Should flag recall in risk factors"

    def test_predicate_acceptability_multiple_recalls(self, enricher):
        """Test predicate acceptability with multiple recalls"""
        recalls_data = {'recalls_total': 3}
        clearance_date = '2018-01-20'

        acceptability = enricher.assess_predicate_acceptability('K123456', recalls_data, clearance_date)

        assert acceptability['predicate_acceptability'] == 'NOT_RECOMMENDED', \
            "Device with 3+ recalls should be NOT_RECOMMENDED"
        assert 'Multiple recalls' in acceptability['acceptability_rationale'], \
            "Should note systematic issues"

    def test_predicate_acceptability_old_clearance(self, enricher):
        """Test predicate acceptability with very old clearance"""
        recalls_data = {'recalls_total': 0}
        clearance_date = '2005-06-15'  # 19+ years old

        acceptability = enricher.assess_predicate_acceptability('K123456', recalls_data, clearance_date)

        assert acceptability['predicate_acceptability'] == 'REVIEW_REQUIRED', \
            "Very old device should require review"
        assert 'Clearance age' in acceptability['predicate_risk_factors'], \
            "Should flag age in risk factors"


class TestEnrichmentWorkflow:
    """Test complete enrichment workflow"""

    @pytest.fixture
    def enricher(self):
        """Create enrichment instance for testing"""
        return FDAEnrichment(api_version="2.0.1")

    @pytest.fixture
    def sample_device(self):
        """Sample device for enrichment"""
        return {
            'KNUMBER': 'K240001',
            'PRODUCTCODE': 'DQY',
            'DECISIONDATE': '2024-01-15',
            'APPLICANT': 'Test Medical Inc.'
        }

    def test_enrich_single_device_structure(self, enricher, sample_device):
        """Test single device enrichment returns complete structure"""
        api_log = []
        enriched = enricher.enrich_single_device(sample_device, api_log)

        # Test Phase 1 fields present
        assert 'maude_productcode_5y' in enriched, "Should have MAUDE data"
        assert 'recalls_total' in enriched, "Should have recalls data"
        assert 'api_validated' in enriched, "Should have validation data"

        # Test Phase 2 fields present
        assert 'predicate_clinical_history' in enriched, "Should have clinical analysis"
        assert 'predicate_acceptability' in enriched, "Should have acceptability assessment"

        # Test quality score added
        assert 'enrichment_completeness_score' in enriched, "Should have quality score"
        assert isinstance(enriched['enrichment_completeness_score'], (int, float)), \
            "Quality score should be numeric"

        # Test metadata added
        assert 'enrichment_timestamp' in enriched, "Should have timestamp"
        assert 'api_version' in enriched, "Should have API version"

    def test_enrich_single_device_api_logging(self, enricher, sample_device):
        """Test single device enrichment logs API calls"""
        api_log = []
        enriched = enricher.enrich_single_device(sample_device, api_log)

        # Should have logged 3 API calls (MAUDE, Recalls, 510k)
        assert len(api_log) >= 3, f"Should log >=3 API calls, got {len(api_log)}"

        # Each log entry should have query and success fields
        for log_entry in api_log:
            assert 'query' in log_entry, "Log entry should have query field"
            assert 'success' in log_entry, "Log entry should have success field"

    def test_enrich_device_batch_structure(self, enricher, sample_device):
        """Test batch enrichment returns correct structure"""
        devices = [sample_device.copy() for _ in range(3)]

        # Make K-numbers unique
        for i, device in enumerate(devices):
            device['KNUMBER'] = f'K24000{i+1}'

        enriched_rows, api_log = enricher.enrich_device_batch(devices)

        # Test return structure
        assert isinstance(enriched_rows, list), "enriched_rows should be list"
        assert isinstance(api_log, list), "api_log should be list"
        assert len(enriched_rows) == 3, "Should enrich all 3 devices"

        # Each device should be enriched
        for enriched in enriched_rows:
            assert 'enrichment_completeness_score' in enriched, \
                "Each device should have quality score"


class TestDataIntegrity:
    """Test data integrity and provenance"""

    @pytest.fixture
    def enricher(self):
        """Create enrichment instance for testing"""
        return FDAEnrichment(api_version="2.0.1")

    def test_maude_scope_always_declared(self, enricher):
        """Test MAUDE scope is ALWAYS declared"""
        for product_code in ['DQY', 'GEI', 'QKQ', 'INVALID']:
            maude_data = enricher.get_maude_events_by_product_code(product_code)

            assert 'maude_scope' in maude_data, \
                f"MAUDE data for {product_code} MUST include scope declaration"
            assert maude_data['maude_scope'] in ['PRODUCT_CODE', 'UNAVAILABLE'], \
                f"MAUDE scope for {product_code} must be valid value"

    def test_quality_score_never_exceeds_100(self, enricher):
        """Test quality score never exceeds 100"""
        # Create overly perfect device
        perfect_device = {
            'KNUMBER': 'K123456',
            'PRODUCTCODE': 'DQY',
            'maude_productcode_5y': 1000,
            'maude_trending': 'stable',
            'recalls_total': 0,
            'api_validated': 'Yes',
            'decision': 'SE',
            'statement_or_summary': 'Summary',
            'maude_scope': 'PRODUCT_CODE'
        }

        perfect_api_log = [
            {'query': 'MAUDE:DQY', 'success': True},
            {'query': 'Recall:K123456', 'success': True},
            {'query': '510k:K123456', 'success': True}
        ]

        score = enricher.calculate_enrichment_completeness_score(perfect_device, perfect_api_log)

        assert score <= 100, f"Quality score should never exceed 100, got {score}"

    def test_quality_score_never_negative(self, enricher):
        """Test quality score never goes negative"""
        # Create worst-case device
        worst_device = {
            'KNUMBER': 'K999999',
            'PRODUCTCODE': 'XXX',
            'maude_productcode_5y': 'N/A',
            'maude_trending': 'unknown',
            'recalls_total': 'N/A',
            'api_validated': 'No',
            'decision': 'Unknown',
            'statement_or_summary': 'Unknown',
            'maude_scope': 'UNAVAILABLE'
        }

        worst_api_log = [
            {'query': 'MAUDE:XXX', 'success': False},
            {'query': 'Recall:K999999', 'success': False},
            {'query': '510k:K999999', 'success': False}
        ]

        score = enricher.calculate_enrichment_completeness_score(worst_device, worst_api_log)

        assert score >= 0, f"Quality score should never be negative, got {score}"


# Test configuration
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
