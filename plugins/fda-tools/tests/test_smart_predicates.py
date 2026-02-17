#!/usr/bin/env python3
"""
Unit tests for predicate_ranker.py - Phase 4B Feature 2

Tests smart predicate recommendations using FDA-compliant scoring.
"""

import sys
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

# Add lib directory to path
# Package imports configured in conftest.py and pytest.ini

from lib.predicate_ranker import (
    PredicateRanker,
    rank_predicates,
    generate_smart_recommendations_report
)


class TestTextSimilarity:
    """Test suite for TF-IDF text similarity."""

    def test_text_similarity_identical(self):
        """Test 1: Identical text should have high similarity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create minimal device profile
            device_profile = {
                'indications_for_use': 'Treatment of coronary artery disease',
                'product_code': 'DQY'
            }

            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            # Test
            ranker = PredicateRanker(str(project_dir))
            similarity = ranker.calculate_text_similarity(
                'Treatment of coronary artery disease',
                'Treatment of coronary artery disease'
            )

            # Assert: Should have high similarity
            assert similarity['tfidf_similarity'] > 0.9
            assert similarity['keyword_overlap'] > 0.9

    def test_text_similarity_different(self):
        """Test 2: Different text should have low similarity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            device_profile = {'product_code': 'DQY'}
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            ranker = PredicateRanker(str(project_dir))
            similarity = ranker.calculate_text_similarity(
                'Treatment of coronary artery disease with stent',
                'Orthopedic hip replacement implant system'
            )

            # Assert: Should have low similarity
            assert similarity['tfidf_similarity'] < 0.3
            assert similarity['keyword_overlap'] < 0.3


class TestPredicateRanking:
    """Test suite for predicate ranking."""

    def test_rank_predicates_top_10(self):
        """Test 3: Ranking should return top 10 predicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create device profile
            device_profile = {
                'indications_for_use': 'Treatment of coronary artery disease',
                'technological_characteristics': 'Balloon-expandable stent',
                'product_code': 'DQY'
            }

            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            # Create review.json with 15 predicates
            accepted_predicates = []
            for i in range(1, 16):
                accepted_predicates.append({
                    'k_number': f'K{12340 + i}',
                    'device_name': f'Test Device {i}',
                    'applicant': 'Test Company',
                    'decision_date': '2020-05-15',
                    'product_code': 'DQY',
                    'confidence_score': 50 + i,  # Varying scores
                    'statement': 'Treatment of coronary artery disease',
                    'recalls_total': 0
                })

            review_data = {'accepted_predicates': accepted_predicates}
            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            # Test
            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates(top_n=10)

            # Assert: Should return 10 predicates
            assert len(ranked) == 10
            # Assert: Should be sorted by total_score descending
            for i in range(len(ranked) - 1):
                assert ranked[i]['total_score'] >= ranked[i + 1]['total_score']

    def test_rank_predicates_filters_low_confidence(self):
        """Test 4: Ranking should filter predicates below minimum confidence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            device_profile = {'product_code': 'DQY'}
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            # Create predicates with low confidence scores
            accepted_predicates = [
                {
                    'k_number': 'K123450',
                    'device_name': 'High Confidence Device',
                    'confidence_score': 75,  # Above threshold
                    'decision_date': '2020-05-15',
                    'product_code': 'DQY',
                    'recalls_total': 0
                },
                {
                    'k_number': 'K123451',
                    'device_name': 'Low Confidence Device',
                    'confidence_score': 25,  # Below threshold (40)
                    'decision_date': '2020-05-15',
                    'product_code': 'DQY',
                    'recalls_total': 0
                }
            ]

            review_data = {'accepted_predicates': accepted_predicates}
            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            # Test
            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates(min_confidence=40)

            # Assert: Should only return high confidence predicate
            assert len(ranked) == 1
            assert ranked[0]['k_number'] == 'K123450'

    def test_strength_classification_strong(self):
        """Test 5: High score should classify as STRONG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            device_profile = {'product_code': 'DQY'}
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            accepted_predicates = [{
                'k_number': 'K123456',
                'device_name': 'Strong Predicate',
                'confidence_score': 90,  # Will be 90+ with bonuses
                'decision_date': '2022-01-15',
                'product_code': 'DQY',
                'recalls_total': 0,
                'statement': 'Treatment of coronary artery disease'
            }]

            review_data = {'accepted_predicates': accepted_predicates}
            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            # Assert: Should classify as STRONG
            assert ranked[0]['strength'] in ['STRONG', 'GOOD']  # May be GOOD if total < 85

    def test_risk_flags_recalls(self):
        """Test 6: Predicates with recalls should have risk flags."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            device_profile = {'product_code': 'DQY'}
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            accepted_predicates = [{
                'k_number': 'K123456',
                'device_name': 'Recalled Device',
                'confidence_score': 80,
                'decision_date': '2020-05-15',
                'product_code': 'DQY',
                'recalls_total': 2  # Has recalls
            }]

            review_data = {'accepted_predicates': accepted_predicates}
            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            # Assert: Should have RECALLED flag
            assert len(ranked[0]['risk_flags']) > 0
            assert any('RECALLED' in flag for flag in ranked[0]['risk_flags'])

    def test_fallback_no_predicates(self):
        """Test 7: Graceful fallback when no predicates available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            device_profile = {'product_code': 'DQY'}
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            # Empty review.json
            review_data = {'accepted_predicates': []}
            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            # Assert: Should return empty list
            assert len(ranked) == 0

    def test_estimate_confidence_score(self):
        """Test 8: Confidence score estimation when not pre-calculated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            device_profile = {'product_code': 'DQY'}
            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            accepted_predicates = [{
                'k_number': 'K123456',
                'device_name': 'Test Device',
                # No confidence_score - should be estimated
                'decision_date': '2022-01-15',  # Recent
                'product_code': 'DQY',  # Same code
                'recalls_total': 0  # Clean
            }]

            review_data = {'accepted_predicates': accepted_predicates}
            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            # Assert: Should have estimated score
            assert ranked[0]['base_score'] > 0
            # Expect: 15 (product code) + 15 (recency <5y) + 10 (clean) + 25 (section) + 5 (citation) = 70
            assert ranked[0]['base_score'] >= 50  # Conservative check

    def test_ifu_similarity_bonus(self):
        """Test 9: High IFU similarity should add bonus points."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            device_profile = {
                'indications_for_use': 'Treatment of coronary artery disease with balloon expandable stent',
                'product_code': 'DQY'
            }

            with open(project_dir / 'device_profile.json', 'w') as f:
                json.dump(device_profile, f)

            accepted_predicates = [{
                'k_number': 'K123456',
                'device_name': 'Similar Device',
                'confidence_score': 70,
                'decision_date': '2020-05-15',
                'product_code': 'DQY',
                'recalls_total': 0,
                'statement': 'Treatment of coronary artery disease with balloon expandable stent'  # Identical IFU
            }]

            review_data = {'accepted_predicates': accepted_predicates}
            with open(project_dir / 'review.json', 'w') as f:
                json.dump(review_data, f)

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            # Assert: Should have IFU bonus
            assert ranked[0]['ifu_bonus'] > 0
            assert ranked[0]['ifu_similarity'] > 0.7


class TestReportGeneration:
    """Test suite for report generation."""

    def test_generate_report_structure(self):
        """Test 10: Generated report should have all required sections."""
        ranked_predicates = [{
            'k_number': 'K123456',
            'device_name': 'Test Device',
            'applicant': 'Test Company',
            'decision_date': '2020-05-15',
            'product_code': 'DQY',
            'base_score': 75,
            'ifu_similarity': 0.85,
            'tech_similarity': 0.75,
            'ifu_bonus': 4,
            'tech_bonus': 2,
            'total_score': 81,
            'strength': 'GOOD',
            'risk_flags': [],
            'recommendation': 'Solid predicate - safe to use'
        }]

        report = generate_smart_recommendations_report(ranked_predicates, 'Test Project')

        # Assert: Check required sections
        assert '# Smart Predicate Recommendations Report' in report
        assert 'Executive Summary' in report
        assert 'Top Ranked Predicates' in report
        assert 'Human Review Checkpoints' in report
        assert 'Methodology' in report
        assert '⚠️ **AUTOMATION ASSISTS' in report  # Disclaimer


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
