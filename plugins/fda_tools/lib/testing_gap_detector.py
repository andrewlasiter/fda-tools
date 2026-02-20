#!/usr/bin/env python3
"""
Testing Gap Detector - Focused module for test coverage gap detection.

Extracted from gap_analyzer.py as part of FDA-116 refactoring.
Identifies missing test evidence based on device type and standards.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class TestingGapDetector:
    """
    Analyzes gaps in test coverage for 510(k) submissions.

    Identifies expected tests not declared based on:
    - Device type and classification
    - Applicable standards
    - Sterilization method
    - Biocompatibility requirements
    """

    # Common test categories by device type
    COMMON_TESTS = {
        'sterile': ['bioburden', 'sterility', 'pyrogen'],
        'implantable': ['biocompatibility', 'bioburden', 'corrosion'],
        'electrical': ['electrical_safety', 'EMC'],
        'software': ['software_validation', 'cybersecurity'],
    }

    def __init__(self, project_dir: str):
        """Initialize detector with project data."""
        self.project_dir = Path(project_dir)
        self.device_profile = self._load_device_profile()
        self.standards_lookup = self._load_standards_lookup()

    def _load_device_profile(self) -> Dict[str, Any]:
        """Load device_profile.json from project directory."""
        profile_path = self.project_dir / 'device_profile.json'
        if not profile_path.exists():
            return {}
        with open(profile_path, 'r') as f:
            return json.load(f)

    def _load_standards_lookup(self) -> List[Dict[str, Any]]:
        """Load standards_lookup.json from project directory."""
        standards_path = self.project_dir / 'standards_lookup.json'
        if not standards_path.exists():
            return []
        with open(standards_path, 'r') as f:
            data = json.load(f)
            return data.get('standards', [])

    def detect_testing_gaps(self) -> List[Dict[str, Any]]:
        """
        Identify missing test evidence based on device characteristics.

        Returns:
            List of testing gap dicts
        """
        gaps = []

        if not self.device_profile:
            return gaps

        # Check sterilization-related tests
        sterilization = self.device_profile.get('sterilization_method', '').lower()
        if sterilization and 'sterile' in sterilization:
            declared_tests = self.device_profile.get('testing_performed', [])
            if isinstance(declared_tests, list):
                declared_test_names = [t.get('test_name', '').lower() for t in declared_tests]

                for required_test in self.COMMON_TESTS['sterile']:
                    if not any(required_test in test_name for test_name in declared_test_names):
                        gaps.append({
                            'test': required_test,
                            'priority': 'HIGH',
                            'reason': f'Sterile device missing {required_test} test declaration',
                            'confidence': 85,
                            'category': 'testing_gap',
                            'remediation': f'Declare {required_test} testing or explain why not applicable'
                        })

        # Check biocompatibility tests for body-contacting devices
        biocompat = self.device_profile.get('biocompatibility', '').lower()
        if biocompat and ('yes' in biocompat or 'required' in biocompat):
            declared_tests = self.device_profile.get('testing_performed', [])
            if isinstance(declared_tests, list):
                declared_test_names = [t.get('test_name', '').lower() for t in declared_tests]

                if not any('biocompat' in test_name or 'iso 10993' in test_name for test_name in declared_test_names):
                    gaps.append({
                        'test': 'biocompatibility',
                        'priority': 'HIGH',
                        'reason': 'Device requires biocompatibility testing but not declared',
                        'confidence': 90,
                        'category': 'testing_gap',
                        'remediation': 'Declare ISO 10993 biocompatibility testing'
                    })

        # Check electrical safety for powered devices
        power_source = self.device_profile.get('power_source', '').lower()
        if power_source and ('electric' in power_source or 'battery' in power_source or 'ac' in power_source):
            declared_tests = self.device_profile.get('testing_performed', [])
            if isinstance(declared_tests, list):
                declared_test_names = [t.get('test_name', '').lower() for t in declared_tests]

                if not any('electrical' in test_name or 'iec 60601' in test_name for test_name in declared_test_names):
                    gaps.append({
                        'test': 'electrical_safety',
                        'priority': 'HIGH',
                        'reason': 'Powered device missing electrical safety test declaration',
                        'confidence': 95,
                        'category': 'testing_gap',
                        'remediation': 'Declare IEC 60601 electrical safety testing'
                    })

        # Check standards-based testing requirements
        for standard in self.standards_lookup:
            standard_number = standard.get('standard_number', '')
            if 'ISO 10993' in standard_number:  # Biocompatibility
                declared_tests = self.device_profile.get('testing_performed', [])
                if isinstance(declared_tests, list):
                    declared_test_names = [t.get('test_name', '').lower() for t in declared_tests]
                    if not any('10993' in test_name for test_name in declared_test_names):
                        gaps.append({
                            'test': 'ISO 10993',
                            'priority': 'MEDIUM',
                            'reason': f'Applicable standard {standard_number} not reflected in declared testing',
                            'confidence': 75,
                            'category': 'testing_gap',
                            'remediation': f'Verify {standard_number} testing is declared or explain inapplicability'
                        })

        return gaps
