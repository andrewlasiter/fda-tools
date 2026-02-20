"""
Phase 3 Unit Tests - MAUDE Peer Comparison
===========================================

Tests for analyze_maude_peer_comparison() method in fda_enrichment.py

Test Coverage:
1. Sufficient cohort (≥10 devices) - normal case
2. Insufficient cohort (<10 devices) - edge case
3. EXTREME_OUTLIER classification (>90th percentile)
4. EXCELLENT classification (zero events)
5. Error handling (API failure, malformed data)
6. Statistical calculations (percentiles, median)
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent.parent / 'plugins' / 'fda-tools' / 'lib'
sys.path.insert(0, str(lib_path))

from fda_enrichment import FDAEnrichment


class TestPhase3MAUDEPeerComparison(unittest.TestCase):
    """Test suite for Phase 3 MAUDE Peer Comparison feature"""

    def setUp(self):
        """Initialize enricher for each test"""
        self.enricher = FDAEnrichment(api_key=None, api_version="3.0.0")

    def test_sufficient_cohort_normal_case(self):
        """Test 1: Normal case with sufficient peer cohort (≥10 devices)"""

        # Mock API responses
        with patch.object(self.enricher, 'api_query') as mock_api:
            # Mock 510k API response with 15 peer devices
            mock_api.return_value = {
                'results': [
                    {'k_number': f'K24000{i}', 'device_name': f'Device {i}', 'product_code': 'DQY'}
                    for i in range(15)
                ]
            }

            # Mock get_maude_events_by_product_code to return varying counts
            with patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_maude:
                # Return counts: [5, 8, 10, 12, 15, 18, 20, 22, 25, 30, 35, 40, 45, 50, 100]
                # This creates a distribution where median ≈ 22, P75 ≈ 37.5, P90 ≈ 47.5
                maude_counts = [5, 8, 10, 12, 15, 18, 20, 22, 25, 30, 35, 40, 45, 50, 100]
                mock_maude.side_effect = [{'maude_productcode_5y': count} for count in maude_counts]

                # Test device with 25 events (should be AVERAGE, around 60th percentile)
                result = self.enricher.analyze_maude_peer_comparison('DQY', 25, 'Test Device')

                # Assertions
                self.assertEqual(result['peer_cohort_size'], 15, "Should analyze 15 peer devices")
                self.assertIsInstance(result['peer_median_events'], (int, float), "Median should be a number")
                self.assertGreater(result['peer_median_events'], 0, "Median should be positive")
                self.assertIsInstance(result['device_percentile'], (int, float), "Percentile should be numeric")
                self.assertIn(result['maude_classification'],
                             ['EXCELLENT', 'GOOD', 'AVERAGE', 'CONCERNING', 'EXTREME_OUTLIER'],
                             "Classification should be one of the valid values")
                self.assertIsInstance(result['peer_comparison_note'], str, "Note should be a string")
                self.assertGreater(len(result['peer_comparison_note']), 10, "Note should be descriptive")

    def test_insufficient_cohort(self):
        """Test 2: Insufficient cohort (<10 devices) returns INSUFFICIENT_DATA"""

        with patch.object(self.enricher, 'api_query') as mock_api:
            # Mock 510k API response with only 5 peer devices (too few)
            mock_api.return_value = {
                'results': [
                    {'k_number': f'K24000{i}', 'device_name': f'Device {i}', 'product_code': 'ABC'}
                    for i in range(5)
                ]
            }

            result = self.enricher.analyze_maude_peer_comparison('ABC', 10, 'Test Device')

            # Assertions
            self.assertEqual(result['peer_cohort_size'], 5, "Should report actual cohort size")
            self.assertEqual(result['peer_median_events'], 'N/A', "Median should be N/A for small cohort")
            self.assertEqual(result['peer_75th_percentile'], 'N/A', "P75 should be N/A")
            self.assertEqual(result['peer_90th_percentile'], 'N/A', "P90 should be N/A")
            self.assertEqual(result['device_percentile'], 'N/A', "Percentile should be N/A")
            self.assertEqual(result['maude_classification'], 'INSUFFICIENT_DATA',
                           "Classification should be INSUFFICIENT_DATA")
            self.assertIn('too small', result['peer_comparison_note'].lower(),
                         "Note should mention cohort is too small")

    def test_extreme_outlier_classification(self):
        """Test 3: Device with >90th percentile gets EXTREME_OUTLIER classification"""

        with patch.object(self.enricher, 'api_query') as mock_api:
            # Mock 510k API with 20 peers
            mock_api.return_value = {
                'results': [
                    {'k_number': f'K24000{i}', 'device_name': f'Device {i}', 'product_code': 'DQY'}
                    for i in range(20)
                ]
            }

            with patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_maude:
                # Create distribution where most devices have 5-25 events
                # but test device has 100 events (extreme outlier)
                maude_counts = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25]
                mock_maude.side_effect = [{'maude_productcode_5y': count} for count in maude_counts]

                # Test device with 100 events (far above P90)
                result = self.enricher.analyze_maude_peer_comparison('DQY', 100, 'Outlier Device')

                # Assertions
                self.assertEqual(result['maude_classification'], 'EXTREME_OUTLIER',
                               "Device with 100 events should be EXTREME_OUTLIER")
                self.assertGreaterEqual(result['device_percentile'], 90,
                                       "Percentile should be ≥90 for extreme outlier")
                self.assertIn('DO NOT USE', result['peer_comparison_note'],
                            "Note should warn against using as predicate")
                self.assertIn('90th percentile', result['peer_comparison_note'].lower(),
                            "Note should mention 90th percentile")

    def test_excellent_classification_zero_events(self):
        """Test 4: Device with zero events gets EXCELLENT classification"""

        with patch.object(self.enricher, 'api_query') as mock_api:
            # Mock 510k API with 15 peers
            mock_api.return_value = {
                'results': [
                    {'k_number': f'K24000{i}', 'device_name': f'Device {i}', 'product_code': 'DQY'}
                    for i in range(15)
                ]
            }

            with patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_maude:
                # Peers have various event counts
                maude_counts = [2, 3, 5, 7, 8, 10, 12, 15, 18, 20, 22, 25, 30, 35, 40]
                mock_maude.side_effect = [{'maude_productcode_5y': count} for count in maude_counts]

                # Test device with 0 events (best possible)
                result = self.enricher.analyze_maude_peer_comparison('DQY', 0, 'Perfect Device')

                # Assertions
                self.assertEqual(result['maude_classification'], 'EXCELLENT',
                               "Device with 0 events should be EXCELLENT")
                self.assertEqual(result['device_percentile'], 0,
                               "Percentile should be 0 for zero events")
                self.assertIn('Zero adverse events', result['peer_comparison_note'],
                            "Note should mention zero events")
                self.assertIn('best possible', result['peer_comparison_note'].lower(),
                            "Note should say this is best outcome")

    def test_api_failure_error_handling(self):
        """Test 5: Graceful error handling when API fails"""

        with patch.object(self.enricher, 'api_query') as mock_api:
            # Mock API failure (returns None)
            mock_api.return_value = None

            result = self.enricher.analyze_maude_peer_comparison('DQY', 10, 'Test Device')

            # Assertions - should return default values, not crash
            self.assertEqual(result['peer_cohort_size'], 0, "Cohort size should be 0 on API failure")
            self.assertEqual(result['maude_classification'], 'INSUFFICIENT_DATA',
                           "Classification should be INSUFFICIENT_DATA on failure")
            self.assertIsInstance(result['peer_comparison_note'], str,
                                "Should return error message in note")

    def test_statistical_calculations_accuracy(self):
        """Test 6: Verify statistical calculations (median, percentiles) are accurate"""

        with patch.object(self.enricher, 'api_query') as mock_api:
            # Mock 510k API with 20 peers
            mock_api.return_value = {
                'results': [
                    {'k_number': f'K24000{i}', 'device_name': f'Device {i}', 'product_code': 'DQY'}
                    for i in range(20)
                ]
            }

            with patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_maude:
                # Create known distribution: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                #                             110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
                # Median should be 105 (average of 100 and 110)
                # P75 should be 152.5 (between 150 and 160)
                # P90 should be 181 (between 180 and 190)
                maude_counts = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                               110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
                mock_maude.side_effect = [{'maude_productcode_5y': count} for count in maude_counts]

                # Test device with 105 events (exactly at median)
                result = self.enricher.analyze_maude_peer_comparison('DQY', 105, 'Median Device')

                # Assertions
                self.assertEqual(result['peer_cohort_size'], 20, "Should analyze all 20 peers")

                # Median should be close to 105 (exact middle of distribution)
                self.assertAlmostEqual(result['peer_median_events'], 105, delta=5,
                                      msg="Median should be approximately 105")

                # P75 should be around 152.5
                self.assertAlmostEqual(result['peer_75th_percentile'], 152.5, delta=10,
                                      msg="75th percentile should be approximately 152.5")

                # P90 should be around 181
                self.assertAlmostEqual(result['peer_90th_percentile'], 181, delta=10,
                                      msg="90th percentile should be approximately 181")

                # Device at median should be around 50th percentile
                self.assertGreaterEqual(result['device_percentile'], 40,
                                       "Device at median should be ≥40th percentile")
                self.assertLessEqual(result['device_percentile'], 60,
                                    "Device at median should be ≤60th percentile")

                # Classification should be GOOD or AVERAGE (near median)
                self.assertIn(result['maude_classification'], ['GOOD', 'AVERAGE'],
                             "Device at median should be GOOD or AVERAGE")

    def test_good_classification_below_median(self):
        """Test 7: Device below median but above 25th percentile gets GOOD classification"""

        with patch.object(self.enricher, 'api_query') as mock_api:
            # Mock 510k API with 20 peers
            mock_api.return_value = {
                'results': [
                    {'k_number': f'K24000{i}', 'device_name': f'Device {i}', 'product_code': 'DQY'}
                    for i in range(20)
                ]
            }

            with patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_maude:
                # Distribution: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, ...]
                # P25 ≈ 52.5, Median ≈ 105
                maude_counts = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                               110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
                mock_maude.side_effect = [{'maude_productcode_5y': count} for count in maude_counts]

                # Test device with 70 events (between P25 and median, should be GOOD)
                result = self.enricher.analyze_maude_peer_comparison('DQY', 70, 'Good Device')

                # Assertions
                self.assertIn(result['maude_classification'], ['EXCELLENT', 'GOOD'],
                             "Device below median should be EXCELLENT or GOOD")
                self.assertLess(result['device_percentile'], 50,
                               "Device below median should have percentile <50")
                self.assertIn('below median', result['peer_comparison_note'].lower(),
                            "Note should mention below median")


class TestPhase3Integration(unittest.TestCase):
    """Integration tests for Phase 3 in full enrichment workflow"""

    def setUp(self):
        """Initialize enricher for each test"""
        self.enricher = FDAEnrichment(api_key=None, api_version="3.0.0")

    def test_phase3_columns_in_enriched_output(self):
        """Test 8: Verify all 7 Phase 3 columns are present in enriched output"""

        # Mock all API calls
        with patch.object(self.enricher, 'api_query') as mock_api, \
             patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_maude, \
             patch.object(self.enricher, 'get_recall_history') as mock_recalls, \
             patch.object(self.enricher, 'get_510k_validation') as mock_validation:

            # Mock MAUDE data
            mock_maude.return_value = {
                'maude_productcode_5y': 25,
                'maude_scope': 'PRODUCT_CODE'
            }

            # Mock recalls data
            mock_recalls.return_value = {
                'recalls_total': 0,
                'recall_latest_date': '',
                'recall_class': '',
                'recall_status': ''
            }

            # Mock 510k validation
            mock_validation.return_value = {
                'api_validated': 'Yes',
                'decision': 'substantially equivalent'
            }

            # Mock peer query (sufficient cohort)
            mock_api.return_value = {
                'results': [
                    {'k_number': f'K24000{i}', 'device_name': f'Device {i}', 'product_code': 'DQY'}
                    for i in range(15)
                ]
            }

            # Mock peer MAUDE counts
            with patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_peer_maude:
                maude_counts = [5, 8, 10, 12, 15, 18, 20, 22, 25, 30, 35, 40, 45, 50, 100]
                mock_peer_maude.side_effect = [
                    {'maude_productcode_5y': 25, 'maude_scope': 'PRODUCT_CODE'}  # Original device
                ] + [{'maude_productcode_5y': count} for count in maude_counts]  # Peers

            # Create test device
            device_row = {
                'KNUMBER': 'K240001',
                'PRODUCTCODE': 'DQY',
                'DEVICENAME': 'Test Catheter',
                'DECISIONDATE': '20240101'
            }

            api_log = []
            enriched = self.enricher.enrich_single_device(device_row, api_log)

            # Verify all 7 Phase 3 columns are present
            phase3_columns = [
                'peer_cohort_size',
                'peer_median_events',
                'peer_75th_percentile',
                'peer_90th_percentile',
                'device_percentile',
                'maude_classification',
                'peer_comparison_note'
            ]

            for column in phase3_columns:
                self.assertIn(column, enriched, f"Phase 3 column '{column}' should be in enriched output")
                self.assertIsNotNone(enriched[column], f"Phase 3 column '{column}' should not be None")

    def test_no_maude_data_handling(self):
        """Test 9: Verify proper handling when device has no MAUDE data"""

        with patch.object(self.enricher, 'api_query') as mock_api, \
             patch.object(self.enricher, 'get_maude_events_by_product_code') as mock_maude, \
             patch.object(self.enricher, 'get_recall_history') as mock_recalls, \
             patch.object(self.enricher, 'get_510k_validation') as mock_validation:

            # Mock MAUDE data as unavailable
            mock_maude.return_value = {
                'maude_productcode_5y': 0,
                'maude_scope': 'UNAVAILABLE'
            }

            mock_recalls.return_value = {'recalls_total': 0, 'recall_latest_date': '', 'recall_class': '', 'recall_status': ''}
            mock_validation.return_value = {'api_validated': 'Yes', 'decision': 'substantially equivalent'}

            device_row = {
                'KNUMBER': 'K240001',
                'PRODUCTCODE': 'XYZ',
                'DEVICENAME': 'Test Device',
                'DECISIONDATE': '20240101'
            }

            api_log = []
            enriched = self.enricher.enrich_single_device(device_row, api_log)

            # Verify NO_MAUDE_DATA classification
            self.assertEqual(enriched['maude_classification'], 'NO_MAUDE_DATA',
                           "Should classify as NO_MAUDE_DATA when MAUDE unavailable")
            self.assertEqual(enriched['peer_cohort_size'], 0,
                           "Cohort size should be 0 when no MAUDE data")
            self.assertIn('No MAUDE data', enriched['peer_comparison_note'],
                         "Note should explain no MAUDE data available")


if __name__ == '__main__':
    unittest.main()
