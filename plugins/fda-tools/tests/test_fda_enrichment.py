"""
Comprehensive tests for fda_enrichment.py module.

Tests all enrichment functions across Phase 1 (Data Integrity), Phase 2
(Intelligence Layer), and Phase 3 (Advanced Analytics).

Test Coverage:
    - get_device_specific_cfr function
    - FDAEnrichment class initialization
    - Phase 1: Data integrity (MAUDE, recalls, validation, quality scoring)
    - Phase 2: Intelligence (clinical detection, predicate acceptability)
    - Phase 3: Advanced analytics (MAUDE peer comparison)
    - API query handling and rate limiting
    - Batch enrichment
    - Error handling and graceful degradation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from lib.fda_enrichment import (
    get_device_specific_cfr,
    FDAEnrichment,
    PRODUCT_CODE_CFR_PARTS,
)
from datetime import datetime, timezone, timedelta


class TestDeviceSpecificCFR:
    """Test get_device_specific_cfr function."""

    def test_get_cfr_for_known_product_code(self):
        """Should return CFR citation for known product code."""
        result = get_device_specific_cfr('DQY')
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0].startswith('21 CFR')

    def test_get_cfr_for_cardiovascular_device(self):
        """Should return cardiovascular CFR for DQY."""
        result = get_device_specific_cfr('DQY')
        assert result == ('21 CFR 870.1340', 'Percutaneous Catheter')

    def test_get_cfr_for_orthopedic_device(self):
        """Should return orthopedic CFR for OVE."""
        result = get_device_specific_cfr('OVE')
        assert result == ('21 CFR 888.3080', 'Intervertebral Body Fusion Device')

    def test_get_cfr_for_unknown_product_code(self):
        """Should return None for unknown product code."""
        result = get_device_specific_cfr('UNKNOWN')
        assert result is None

    def test_get_cfr_for_empty_string(self):
        """Should return None for empty string."""
        result = get_device_specific_cfr('')
        assert result is None

    def test_product_code_cfr_parts_has_multiple_categories(self):
        """PRODUCT_CODE_CFR_PARTS should cover multiple device categories."""
        # Check for devices from different CFR parts
        assert any('870' in cfr for cfr, _ in PRODUCT_CODE_CFR_PARTS.values())  # Cardiovascular
        assert any('888' in cfr for cfr, _ in PRODUCT_CODE_CFR_PARTS.values())  # Orthopedic
        assert any('878' in cfr for cfr, _ in PRODUCT_CODE_CFR_PARTS.values())  # General Surgery


class TestFDAEnrichmentInitialization:
    """Test FDAEnrichment class initialization."""

    def test_init_without_api_key(self):
        """Should initialize with default parameters."""
        enricher = FDAEnrichment()
        assert enricher.api_key is None
        assert enricher.api_version == "3.0.0"
        assert enricher.base_url == "https://api.fda.gov/device"

    def test_init_with_api_key(self):
        """Should store provided API key."""
        enricher = FDAEnrichment(api_key="test_key_123")
        assert enricher.api_key == "test_key_123"

    def test_init_with_custom_version(self):
        """Should use custom API version."""
        enricher = FDAEnrichment(api_version="2.0.1")
        assert enricher.api_version == "2.0.1"

    def test_init_sets_timestamp(self):
        """Should set enrichment timestamp on initialization."""
        enricher = FDAEnrichment()
        assert hasattr(enricher, 'enrichment_timestamp')
        assert isinstance(enricher.enrichment_timestamp, str)
        assert 'T' in enricher.enrichment_timestamp
        assert 'Z' in enricher.enrichment_timestamp


class TestAPIQuery:
    """Test api_query method."""

    @patch('lib.fda_enrichment.urlopen')
    @patch('lib.fda_enrichment.time.sleep')
    def test_api_query_successful(self, mock_sleep, mock_urlopen):
        """Should successfully query API and parse JSON response."""
        mock_response = Mock()
        mock_response.read.return_value = b'{"results": [{"k_number": "K123456"}]}'
        mock_urlopen.return_value = mock_response

        enricher = FDAEnrichment()
        result = enricher.api_query('510k', {'search': 'k_number:"K123456"'})

        assert result is not None
        assert 'results' in result
        assert result['results'][0]['k_number'] == 'K123456'
        mock_sleep.assert_called_once_with(0.25)  # Rate limiting

    @patch('lib.fda_enrichment.urlopen')
    def test_api_query_includes_api_key_when_provided(self, mock_urlopen):
        """Should add api_key to query params if provided."""
        mock_response = Mock()
        mock_response.read.return_value = b'{"results": []}'
        mock_urlopen.return_value = mock_response

        enricher = FDAEnrichment(api_key="test_key")
        enricher.api_query('510k', {'search': 'product_code:"DQY"'})

        # Check that API key is in the URL
        call_args = mock_urlopen.call_args[0][0]
        assert 'api_key=test_key' in call_args.full_url

    @patch('lib.fda_enrichment.urlopen')
    def test_api_query_handles_404_error(self, mock_urlopen):
        """Should return None for 404 errors."""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(None, 404, 'Not Found', None, None)

        enricher = FDAEnrichment()
        result = enricher.api_query('510k', {'search': 'k_number:"NOTFOUND"'})

        assert result is None

    @patch('lib.fda_enrichment.urlopen')
    def test_api_query_handles_network_errors(self, mock_urlopen):
        """Should return None for network errors."""
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError('Network error')

        enricher = FDAEnrichment()
        result = enricher.api_query('510k', {'search': 'test'})

        assert result is None

    @patch('lib.fda_enrichment.urlopen')
    def test_api_query_sets_user_agent(self, mock_urlopen):
        """Should set User-Agent header in API requests."""
        mock_response = Mock()
        mock_response.read.return_value = b'{"results": []}'
        mock_urlopen.return_value = mock_response

        enricher = FDAEnrichment()
        enricher.api_query('510k', {'search': 'test'})

        request = mock_urlopen.call_args[0][0]
        assert request.headers.get('User-agent') == 'FDA-Predicate-Assistant/2.0'


class TestMAUDEEvents:
    """Test get_maude_events_by_product_code method."""

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_events_successful(self, mock_api_query):
        """Should calculate MAUDE events and trending correctly."""
        # Mock 60 months of data with stable trend
        mock_results = [{'count': 30}] * 60  # 1800 total events, stable trend
        mock_api_query.return_value = {'results': mock_results}

        enricher = FDAEnrichment()
        result = enricher.get_maude_events_by_product_code('DQY')

        assert result['maude_productcode_5y'] == 1800
        assert result['maude_trending'] == 'stable'
        assert result['maude_recent_6m'] == 180
        assert result['maude_scope'] == 'PRODUCT_CODE'

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_events_increasing_trend(self, mock_api_query):
        """Should detect increasing trend when recent > previous * 1.2."""
        # Recent 6 months: 50/month, Previous 6 months: 30/month
        mock_results = [{'count': 50}] * 6 + [{'count': 30}] * 54
        mock_api_query.return_value = {'results': mock_results}

        enricher = FDAEnrichment()
        result = enricher.get_maude_events_by_product_code('DQY')

        assert result['maude_trending'] == 'increasing'
        assert result['maude_recent_6m'] == 300

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_events_decreasing_trend(self, mock_api_query):
        """Should detect decreasing trend when recent < previous * 0.8."""
        # Recent 6 months: 15/month, Previous 6 months: 30/month
        mock_results = [{'count': 15}] * 6 + [{'count': 30}] * 54
        mock_api_query.return_value = {'results': mock_results}

        enricher = FDAEnrichment()
        result = enricher.get_maude_events_by_product_code('DQY')

        assert result['maude_trending'] == 'decreasing'

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_events_zero_previous(self, mock_api_query):
        """Should handle zero events in previous period gracefully."""
        mock_results = [{'count': 10}] * 6 + [{'count': 0}] * 54
        mock_api_query.return_value = {'results': mock_results}

        enricher = FDAEnrichment()
        result = enricher.get_maude_events_by_product_code('DQY')

        assert result['maude_trending'] == 'stable'  # Defaults to stable when prev == 0

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_events_api_error(self, mock_api_query):
        """Should return dict with N/A values on API error."""
        mock_api_query.return_value = None

        enricher = FDAEnrichment()
        result = enricher.get_maude_events_by_product_code('DQY')

        assert result['maude_productcode_5y'] == 'N/A'
        assert result['maude_trending'] == 'unknown'
        assert result['maude_recent_6m'] == 'N/A'
        assert result['maude_scope'] == 'UNAVAILABLE'


class TestRecallHistory:
    """Test get_recall_history method."""

    @patch.object(FDAEnrichment, 'api_query')
    def test_recall_history_no_recalls(self, mock_api_query):
        """Should return zero recalls when none found."""
        mock_api_query.return_value = None

        enricher = FDAEnrichment()
        result = enricher.get_recall_history('K123456')

        assert result['recalls_total'] == 0
        assert result['recall_latest_date'] == ''
        assert result['recall_class'] == ''
        assert result['recall_status'] == ''

    @patch.object(FDAEnrichment, 'api_query')
    def test_recall_history_class_i_recall(self, mock_api_query):
        """Should return recall data for Class I recalls."""
        mock_api_query.return_value = {
            'results': [{
                'classification': 'Class I',
                'recall_number': 'Z-1234-2024',
                'product_description': 'Test Device',
                'recall_initiation_date': '2024-01-15',
                'status': 'Ongoing'
            }]
        }

        enricher = FDAEnrichment()
        result = enricher.get_recall_history('K123456')

        assert result['recalls_total'] == 1
        assert result['recall_latest_date'] == '2024-01-15'
        assert result['recall_class'] == 'Class I'
        assert result['recall_status'] == 'Ongoing'

    @patch.object(FDAEnrichment, 'api_query')
    def test_recall_history_class_ii_recall(self, mock_api_query):
        """Should return recall data for Class II recalls."""
        mock_api_query.return_value = {
            'results': [{
                'classification': 'Class II',
                'recall_number': 'Z-1234-2024',
                'product_description': 'Test Device',
                'recall_initiation_date': '2024-02-20',
                'status': 'Completed'
            }]
        }

        enricher = FDAEnrichment()
        result = enricher.get_recall_history('K123456')

        assert result['recalls_total'] == 1
        assert result['recall_latest_date'] == '2024-02-20'
        assert result['recall_class'] == 'Class II'

    @patch.object(FDAEnrichment, 'api_query')
    def test_recall_history_multiple_recalls(self, mock_api_query):
        """Should count multiple recalls correctly."""
        mock_api_query.return_value = {
            'results': [
                {'classification': 'Class II', 'recall_number': 'Z-1234-2024', 'product_description': 'Device 1', 'recall_initiation_date': '2024-03-01', 'status': 'Ongoing'},
                {'classification': 'Class III', 'recall_number': 'Z-5678-2024', 'product_description': 'Device 2', 'recall_initiation_date': '2024-02-15', 'status': 'Completed'}
            ]
        }

        enricher = FDAEnrichment()
        result = enricher.get_recall_history('K123456')

        assert result['recalls_total'] == 2
        assert result['recall_latest_date'] == '2024-03-01'  # Latest date from first result


class Test510kValidation:
    """Test get_510k_validation method."""

    @patch.object(FDAEnrichment, 'api_query')
    def test_510k_validation_successful(self, mock_api_query):
        """Should validate 510(k) and return clearance data."""
        mock_api_query.return_value = {
            'results': [{
                'k_number': 'K123456',
                'decision_description': 'Substantially Equivalent',
                'clearance_date': '2024-01-15',
                'expedited_review_flag': 'N',
                'statement_or_summary': 'Summary'
            }]
        }

        enricher = FDAEnrichment()
        result = enricher.get_510k_validation('K123456')

        assert result['api_validated'] == 'Yes'
        assert result['decision'] == 'Substantially Equivalent'
        assert result['expedited_review'] == 'N'
        assert result['statement_or_summary'] == 'Summary'

    @patch.object(FDAEnrichment, 'api_query')
    def test_510k_validation_not_found(self, mock_api_query):
        """Should return NOT_FOUND for invalid K-number."""
        mock_api_query.return_value = None

        enricher = FDAEnrichment()
        result = enricher.get_510k_validation('K999999')

        assert result['api_validated'] == 'No'
        assert result['decision'] == 'Unknown'
        assert result['expedited_review'] == 'Unknown'
        assert result['statement_or_summary'] == 'Unknown'


class TestEnrichmentCompletenessScore:
    """Test calculate_enrichment_completeness_score method."""

    def test_completeness_score_all_fields_populated(self):
        """Should return 100 when all enrichment fields are populated."""
        row = {
            'KNUMBER': 'K123456',
            'maude_productcode_5y': 1847,
            'maude_trending': 'stable',
            'recalls_total': 0,
            'api_validated': 'Yes',
            'decision': 'Substantially Equivalent',
            'statement_or_summary': 'Summary',
            'maude_scope': 'PRODUCT_CODE'
        }
        api_log = [
            {'query': 'MAUDE:K123456', 'success': True},
            {'query': 'Recall:K123456', 'success': True},
            {'query': '510k:K123456', 'success': True}
        ]

        enricher = FDAEnrichment()
        score = enricher.calculate_enrichment_completeness_score(row, api_log)

        assert score == 100.0

    def test_completeness_score_missing_maude_data(self):
        """Should reduce score when MAUDE data is missing."""
        row = {
            'KNUMBER': 'K123456',
            'maude_productcode_5y': 'N/A',
            'maude_trending': 'unknown',
            'recalls_total': 0,
            'api_validated': 'Yes',
            'decision': 'Unknown',
            'statement_or_summary': 'Unknown',
            'maude_scope': 'UNAVAILABLE'
        }
        api_log = [{'query': 'MAUDE:K123456', 'success': False}]

        enricher = FDAEnrichment()
        score = enricher.calculate_enrichment_completeness_score(row, api_log)

        assert score < 100.0

    def test_completeness_score_api_failures(self):
        """Should reduce score for API failures."""
        row = {
            'KNUMBER': 'K123456',
            'maude_productcode_5y': 1847,
            'maude_trending': 'stable',
            'recalls_total': 0,
            'api_validated': 'No',
            'decision': 'Unknown',
            'statement_or_summary': 'Unknown',
            'maude_scope': 'PRODUCT_CODE'
        }
        api_log = [
            {'query': 'MAUDE:K123456', 'success': True},
            {'query': 'Recall:K123456', 'success': False},
            {'query': '510k:K123456', 'success': False}
        ]

        enricher = FDAEnrichment()
        score = enricher.calculate_enrichment_completeness_score(row, api_log)

        assert score < 80.0


class TestClinicalHistoryAssessment:
    """Test assess_predicate_clinical_history method (Phase 2)."""

    def test_clinical_likely_yes_for_clinical_keywords(self):
        """Should detect YES for clinical trial keywords in decision description."""
        validation_data = {'decision': 'Clinical data from a randomized controlled trial'}

        enricher = FDAEnrichment()
        result = enricher.assess_predicate_clinical_history(validation_data, validation_data['decision'])

        assert result['predicate_clinical_history'] == 'YES'
        assert result['predicate_study_type'] == 'premarket'
        assert 'clinical_study_mentioned' in result['predicate_clinical_indicators']

    def test_clinical_likely_probable_for_study_keywords(self):
        """Should detect clinical history for postmarket study keywords."""
        validation_data = {'decision': 'Subject to postmarket surveillance requirements'}

        enricher = FDAEnrichment()
        result = enricher.assess_predicate_clinical_history(validation_data, validation_data['decision'])

        assert result['predicate_clinical_history'] == 'YES'
        assert result['predicate_study_type'] == 'postmarket'
        assert 'postmarket_study_required' in result['predicate_clinical_indicators']

    def test_clinical_likely_no_for_benign_text(self):
        """Should detect UNKNOWN for text without clinical indicators."""
        validation_data = {'decision': 'Substantially equivalent based on technological comparison'}

        enricher = FDAEnrichment()
        result = enricher.assess_predicate_clinical_history(validation_data, validation_data['decision'])

        assert result['predicate_clinical_history'] == 'UNKNOWN'
        assert result['predicate_study_type'] == 'none'
        assert result['predicate_clinical_indicators'] == 'none'


class TestPredicateAcceptability:
    """Test assess_predicate_acceptability method (Phase 2)."""

    def test_predicate_acceptable_no_recalls_recent_clearance(self):
        """Should mark predicate ACCEPTABLE if no recalls and recent clearance."""
        recalls_data = {'recalls_total': 0, 'recall_latest_date': '', 'recall_class': '', 'recall_status': ''}
        clearance_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        enricher = FDAEnrichment()
        result = enricher.assess_predicate_acceptability('K123456', recalls_data, clearance_date)

        assert result['predicate_acceptability'] == 'ACCEPTABLE'
        assert result['predicate_recommendation'] == 'Suitable for primary predicate citation'

    def test_predicate_caution_for_class_ii_recall(self):
        """Should mark predicate REVIEW_REQUIRED for Class II recalls."""
        recalls_data = {'recalls_total': 1, 'recall_latest_date': '2024-01-15', 'recall_class': 'Class II', 'recall_status': 'Ongoing'}
        clearance_date = '2023-01-15'

        enricher = FDAEnrichment()
        result = enricher.assess_predicate_acceptability('K123456', recalls_data, clearance_date)

        assert result['predicate_acceptability'] == 'REVIEW_REQUIRED'
        assert '1 recall(s) on record' in result['predicate_risk_factors']

    def test_predicate_toxic_for_class_i_recall(self):
        """Should mark predicate REVIEW_REQUIRED for Class I recalls."""
        recalls_data = {'recalls_total': 1, 'recall_latest_date': '2024-01-15', 'recall_class': 'Class I', 'recall_status': 'Ongoing'}
        clearance_date = '2023-01-15'

        enricher = FDAEnrichment()
        result = enricher.assess_predicate_acceptability('K123456', recalls_data, clearance_date)

        assert result['predicate_acceptability'] == 'REVIEW_REQUIRED'
        assert '1 recall(s) on record' in result['predicate_risk_factors']


class TestMAUDEPeerComparison:
    """Test analyze_maude_peer_comparison method (Phase 3)."""

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_peer_comparison_calculates_percentile(self, mock_api_query):
        """Should calculate device's percentile in product code distribution."""
        # Mock peer data with 10 devices - need enough data for statistics
        mock_api_query.return_value = {
            'results': [
                {'k_number': f'K{i:06d}', 'product_code': 'DQY', 'device_name': f'Device{i}'}
                for i in range(15)  # Need at least 10 for cohort, 15 to ensure stats work
            ]
        }

        enricher = FDAEnrichment()
        # The analyze_maude_peer_comparison method calls get_maude_events_by_product_code internally
        # We need to mock multiple returns for each peer device
        with patch.object(enricher, 'get_maude_events_by_product_code') as mock_maude:
            # Return varying MAUDE counts for peers (need at least 5 non-zero)
            mock_maude.side_effect = [
                {'maude_productcode_5y': 50},
                {'maude_productcode_5y': 75},
                {'maude_productcode_5y': 100},
                {'maude_productcode_5y': 125},
                {'maude_productcode_5y': 150},
                {'maude_productcode_5y': 175},
                {'maude_productcode_5y': 200},
                {'maude_productcode_5y': 225},
                {'maude_productcode_5y': 250},
                {'maude_productcode_5y': 275},
                {'maude_productcode_5y': 300},
                {'maude_productcode_5y': 325},
                {'maude_productcode_5y': 350},
                {'maude_productcode_5y': 375},
                {'maude_productcode_5y': 400},
            ]

            result = enricher.analyze_maude_peer_comparison('DQY', 150, device_name='Test Device')

            assert 'device_percentile' in result
            assert 'peer_cohort_size' in result
            assert result['peer_cohort_size'] >= 10

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_peer_comparison_handles_no_peers(self, mock_api_query):
        """Should handle case where no peer devices are found."""
        mock_api_query.return_value = None

        enricher = FDAEnrichment()
        result = enricher.analyze_maude_peer_comparison('UNKNOWN', 100, device_name='Test')

        assert result['peer_cohort_size'] == 0
        assert result['maude_classification'] == 'INSUFFICIENT_DATA'


class TestEnrichSingleDevice:
    """Test enrich_single_device method (integration)."""

    @patch.object(FDAEnrichment, 'api_query')
    def test_enrich_single_device_complete_enrichment(self, mock_api_query):
        """Should enrich device with all available data."""
        # Mock successful API responses
        mock_api_query.side_effect = [
            # MAUDE events
            {'results': [{'count': 30}] * 60},
            # Recalls
            None,
            # 510(k) validation
            {'results': [{'k_number': 'K123456', 'decision_description': 'SE', 'clearance_date': '2024-01-15', 'expedited_review_flag': 'N', 'statement_or_summary': 'Summary'}]},
            # MAUDE peer comparison - return None to trigger default response
            None
        ]

        enricher = FDAEnrichment()
        device_row = {
            'KNUMBER': 'K123456',
            'PRODUCTCODE': 'DQY',
            'APPLICANT': 'Test Corp',
            'DECISIONDATE': '2024-01-15',
            'DEVICENAME': 'Test Device'
        }
        api_log = []

        result = enricher.enrich_single_device(device_row, api_log)

        assert 'maude_productcode_5y' in result
        assert 'recalls_total' in result
        assert 'api_validated' in result
        assert 'predicate_clinical_history' in result
        assert 'predicate_acceptability' in result
        assert len(api_log) > 0


class TestEnrichDeviceBatch:
    """Test enrich_device_batch method."""

    @patch.object(FDAEnrichment, 'enrich_single_device')
    def test_enrich_device_batch_processes_all_devices(self, mock_enrich_single):
        """Should process all devices in batch."""
        mock_enrich_single.return_value = {'KNUMBER': 'K123456', 'maude_productcode_5y': 1847}

        enricher = FDAEnrichment()
        devices = [
            {'KNUMBER': 'K123456', 'PRODUCTCODE': 'DQY'},
            {'KNUMBER': 'K123457', 'PRODUCTCODE': 'DQY'},
            {'KNUMBER': 'K123458', 'PRODUCTCODE': 'GEI'}
        ]

        enriched_devices, api_log = enricher.enrich_device_batch(devices)

        assert len(enriched_devices) == 3
        assert mock_enrich_single.call_count == 3

    @patch.object(FDAEnrichment, 'enrich_single_device')
    def test_enrich_device_batch_handles_errors_gracefully(self, mock_enrich_single):
        """Should raise exception if a device fails (no error handling in batch processor)."""
        mock_enrich_single.side_effect = [
            {'KNUMBER': 'K123456', 'maude_productcode_5y': 1847},
            Exception('API error'),
            {'KNUMBER': 'K123458', 'maude_productcode_5y': 542}
        ]

        enricher = FDAEnrichment()
        devices = [
            {'KNUMBER': 'K123456', 'PRODUCTCODE': 'DQY'},
            {'KNUMBER': 'K123457', 'PRODUCTCODE': 'DQY'},
            {'KNUMBER': 'K123458', 'PRODUCTCODE': 'GEI'}
        ]

        # Production code does NOT handle exceptions in batch processing - it lets them propagate
        with pytest.raises(Exception, match='API error'):
            enricher.enrich_device_batch(devices)


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @patch('lib.fda_enrichment.urlopen')
    def test_handles_malformed_json_response(self, mock_urlopen):
        """Should handle malformed JSON responses gracefully."""
        mock_response = Mock()
        mock_response.read.return_value = b'not valid json'
        mock_urlopen.return_value = mock_response

        enricher = FDAEnrichment()
        result = enricher.api_query('510k', {'search': 'test'})

        assert result is None

    @patch.object(FDAEnrichment, 'api_query')
    def test_maude_events_handles_missing_results_key(self, mock_api_query):
        """Should handle API response without 'results' key."""
        mock_api_query.return_value = {'error': 'No results found'}

        enricher = FDAEnrichment()
        result = enricher.get_maude_events_by_product_code('DQY')

        assert result['maude_productcode_5y'] == 'N/A'
        assert result['maude_trending'] == 'unknown'
        assert result['maude_scope'] == 'UNAVAILABLE'

    @patch.object(FDAEnrichment, 'api_query')
    def test_enrich_single_device_handles_missing_product_code(self, mock_api_query):
        """Should handle device row without product_code gracefully."""
        # Mock API responses
        mock_api_query.side_effect = [
            {'results': [{'count': 0}] * 60},  # MAUDE
            None,  # Recalls
            None,  # 510k validation
            None   # MAUDE peer comparison
        ]

        enricher = FDAEnrichment()
        device_row = {'KNUMBER': 'K123456', 'DECISIONDATE': '2024-01-15'}  # Missing PRODUCTCODE
        api_log = []

        result = enricher.enrich_single_device(device_row, api_log)

        # Should still return a dict (graceful degradation)
        assert isinstance(result, dict)
        assert 'KNUMBER' in result
