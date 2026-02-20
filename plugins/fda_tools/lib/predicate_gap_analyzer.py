#!/usr/bin/env python3
"""
Predicate Gap Analyzer - Focused module for predicate-related gap detection.

Extracted from gap_analyzer.py as part of FDA-116 refactoring.
Handles missing device data and weak predicate detection.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PredicateGapAnalyzer:
    """
    Analyzes gaps related to predicates and device data.

    Responsibilities:
    1. Missing/incomplete device data fields
    2. Weak predicates (recalls, age, SE differences)
    """

    # Priority field definitions
    HIGH_PRIORITY_FIELDS = [
        'indications_for_use',
        'intended_use_statement',
        'technological_characteristics',
        'device_description',
        'materials',
        'product_code',
        'regulation_number',
        'device_class'
    ]

    MEDIUM_PRIORITY_FIELDS = [
        'sterilization_method',
        'shelf_life',
        'intended_user',
        'use_environment',
        'operating_principle',
        'power_source',
        'dimensions',
        'biocompatibility'
    ]

    LOW_PRIORITY_FIELDS = [
        'accessories',
        'compatible_equipment',
        'packaging',
        'labeling_claims',
        'storage_conditions'
    ]

    # Thresholds for weak predicate detection
    RECALL_THRESHOLD_HIGH = 2  # ≥2 recalls → HIGH priority
    CLEARANCE_AGE_THRESHOLD_MEDIUM = 15  # >15 years → MEDIUM flag
    SE_DIFFERENCE_THRESHOLD = 5  # ≥5 differences → MEDIUM weak predicate

    def __init__(self, project_dir: str):
        """Initialize analyzer with project data."""
        self.project_dir = Path(project_dir)
        self.device_profile = self._load_device_profile()
        self.review_data = self._load_review_data()

    def _load_device_profile(self) -> Dict[str, Any]:
        """Load device_profile.json from project directory."""
        profile_path = self.project_dir / 'device_profile.json'
        if not profile_path.exists():
            return {}
        with open(profile_path, 'r') as f:
            return json.load(f)

    def _load_review_data(self) -> Dict[str, Any]:
        """Load review.json from project directory."""
        review_path = self.project_dir / 'review.json'
        if not review_path.exists():
            return {'accepted_predicates': [], 'rejected_predicates': []}
        with open(review_path, 'r') as f:
            return json.load(f)

    def detect_missing_device_data(self) -> List[Dict[str, Any]]:
        """
        Detect missing or incomplete device data fields.

        Returns:
            List of gap dicts with fields: field, priority, reason, confidence
        """
        gaps = []

        if not self.device_profile:
            return [{
                'field': 'device_profile.json',
                'priority': 'CRITICAL',
                'reason': 'Device profile file missing - cannot analyze gaps',
                'confidence': 100,
                'category': 'missing_data'
            }]

        # Check HIGH priority fields
        for field in self.HIGH_PRIORITY_FIELDS:
            value = self.device_profile.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                gaps.append({
                    'field': field,
                    'priority': 'HIGH',
                    'reason': f'Required field "{field}" is empty or missing',
                    'confidence': 95,
                    'category': 'missing_data',
                    'remediation': f'Obtain {field} from device specifications or manufacturer'
                })

        # Check MEDIUM priority fields
        for field in self.MEDIUM_PRIORITY_FIELDS:
            value = self.device_profile.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                gaps.append({
                    'field': field,
                    'priority': 'MEDIUM',
                    'reason': f'Recommended field "{field}" is empty',
                    'confidence': 85,
                    'category': 'missing_data',
                    'remediation': f'Provide {field} information for complete submission'
                })

        # Check LOW priority fields
        for field in self.LOW_PRIORITY_FIELDS:
            value = self.device_profile.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                gaps.append({
                    'field': field,
                    'priority': 'LOW',
                    'reason': f'Optional field "{field}" is empty',
                    'confidence': 70,
                    'category': 'missing_data',
                    'remediation': f'Consider adding {field} if applicable to your device'
                })

        return gaps

    def detect_weak_predicates(self) -> List[Dict[str, Any]]:
        """
        Identify weak predicates based on recall history, age, and SE differences.

        Returns:
            List of weak predicate gap dicts
        """
        gaps = []

        if not self.review_data:
            return gaps

        accepted_predicates = self.review_data.get('accepted_predicates', [])

        for predicate in accepted_predicates:
            k_number = predicate.get('k_number', 'Unknown')

            # Check recall count
            recall_count = predicate.get('recall_count', 0)
            if recall_count >= self.RECALL_THRESHOLD_HIGH:
                gaps.append({
                    'predicate': k_number,
                    'priority': 'HIGH',
                    'reason': f'Predicate has {recall_count} recalls (threshold: {self.RECALL_THRESHOLD_HIGH})',
                    'confidence': 90,
                    'category': 'weak_predicate',
                    'remediation': 'Consider selecting a predicate with better safety record'
                })

            # Check clearance age
            decision_date = predicate.get('decision_date', '')
            if decision_date:
                try:
                    decision_year = int(decision_date[:4])
                    current_year = datetime.now().year
                    age = current_year - decision_year

                    if age > self.CLEARANCE_AGE_THRESHOLD_MEDIUM:
                        gaps.append({
                            'predicate': k_number,
                            'priority': 'MEDIUM',
                            'reason': f'Predicate is {age} years old (threshold: {self.CLEARANCE_AGE_THRESHOLD_MEDIUM} years)',
                            'confidence': 75,
                            'category': 'weak_predicate',
                            'remediation': 'Consider more recent predicate if available'
                        })
                except (ValueError, TypeError):
                    pass

            # Check SE differences
            se_differences = predicate.get('se_differences_count', 0)
            if se_differences >= self.SE_DIFFERENCE_THRESHOLD:
                gaps.append({
                    'predicate': k_number,
                    'priority': 'MEDIUM',
                    'reason': f'Predicate has {se_differences} SE differences (threshold: {self.SE_DIFFERENCE_THRESHOLD})',
                    'confidence': 80,
                    'category': 'weak_predicate',
                    'remediation': 'Ensure all SE differences are adequately addressed in comparison table'
                })

        return gaps
