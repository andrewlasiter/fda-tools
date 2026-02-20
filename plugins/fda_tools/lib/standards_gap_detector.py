#!/usr/bin/env python3
"""
Standards Gap Detector - Focused module for standards compliance gap detection.

Extracted from gap_analyzer.py as part of FDA-116 refactoring.
Identifies applicable standards not referenced in submission.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class StandardsGapDetector:
    """
    Analyzes gaps in standards compliance for 510(k) submissions.

    Identifies applicable FDA-recognized consensus standards that are
    not referenced in the submission documents.
    """

    def __init__(self, project_dir: str):
        """Initialize detector with project data."""
        self.project_dir = Path(project_dir)
        self.standards_lookup = self._load_standards_lookup()
        self.device_profile = self._load_device_profile()

    def _load_standards_lookup(self) -> List[Dict[str, Any]]:
        """Load standards_lookup.json from project directory."""
        standards_path = self.project_dir / 'standards_lookup.json'
        if not standards_path.exists():
            return []
        with open(standards_path, 'r') as f:
            data = json.load(f)
            return data.get('standards', [])

    def _load_device_profile(self) -> Dict[str, Any]:
        """Load device_profile.json from project directory."""
        profile_path = self.project_dir / 'device_profile.json'
        if not profile_path.exists():
            return {}
        with open(profile_path, 'r') as f:
            return json.load(f)

    def detect_standards_gaps(self) -> List[Dict[str, Any]]:
        """
        Identify applicable standards not referenced in submission.

        Returns:
            List of standards gap dicts
        """
        gaps = []

        if not self.standards_lookup:
            return gaps

        # Get declared standards from device profile
        declared_standards = self.device_profile.get('standards_compliance', [])
        if isinstance(declared_standards, list):
            declared_numbers = [s.get('standard_number', '') for s in declared_standards]
        else:
            declared_numbers = []

        # Check each applicable standard
        for standard in self.standards_lookup:
            standard_number = standard.get('standard_number', '')
            standard_title = standard.get('title', 'Unknown')
            applicability = standard.get('applicability', 'Unknown')

            # Skip if already declared
            if any(standard_number in declared for declared in declared_numbers):
                continue

            # Flag as gap
            priority = 'MEDIUM'
            confidence = 75

            # Higher priority for critical standards
            if any(keyword in standard_title.lower() for keyword in ['biocompatibility', 'sterility', 'electrical']):
                priority = 'HIGH'
                confidence = 85

            gaps.append({
                'standard': standard_number,
                'title': standard_title,
                'priority': priority,
                'reason': f'Applicable standard {standard_number} not referenced in submission',
                'confidence': confidence,
                'category': 'standards_gap',
                'applicability': applicability,
                'remediation': f'Declare compliance with {standard_number} or explain why not applicable'
            })

        return gaps
