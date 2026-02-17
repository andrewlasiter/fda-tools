#!/usr/bin/env python3
"""
Gap Analyzer Module for FDA 510(k) Submissions

Automated gap analysis to identify missing data, weak predicates, testing gaps,
and standards gaps in 510(k) submission projects.

Part of Phase 4: Automation Features
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class GapAnalyzer:
    """
    Automated gap analysis for 510(k) submission projects.

    Identifies four categories of gaps:
    1. Missing Device Data - Critical fields empty or incomplete
    2. Weak Predicates - Predicates with recalls, age, or SE differences
    3. Testing Gaps - Expected tests not declared
    4. Standards Gaps - Applicable standards not referenced

    Returns prioritized gap lists with confidence scoring.
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
        """
        Initialize gap analyzer for a specific project.

        Args:
            project_dir: Path to project directory containing device_profile.json, etc.
        """
        self.project_dir = Path(project_dir)
        self.device_profile = self._load_device_profile()
        self.review_data = self._load_review_data()
        self.se_comparison = self._load_se_comparison()
        self.standards_lookup = self._load_standards_lookup()

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

    def _load_se_comparison(self) -> str:
        """Load se_comparison.md from project directory."""
        se_path = self.project_dir / 'se_comparison.md'
        if not se_path.exists():
            return ''

        with open(se_path, 'r') as f:
            return f.read()

    def _load_standards_lookup(self) -> List[Dict[str, Any]]:
        """Load standards_lookup.json from project directory."""
        standards_path = self.project_dir / 'standards_lookup.json'
        if not standards_path.exists():
            return []

        with open(standards_path, 'r') as f:
            data = json.load(f)
            # Handle both list and dict formats
            if isinstance(data, dict):
                return data.get('standards', [])
            return data

    def detect_missing_device_data(self) -> List[Dict[str, Any]]:
        """
        Detect missing or incomplete device data fields.

        Scans device_profile.json for empty/null critical fields and assigns
        priority based on criticality for 510(k) submission.

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

        Analyzes accepted predicates for:
        - Recall count (≥2 recalls → HIGH priority concern)
        - Clearance age (>15 years → MEDIUM concern)
        - SE differences (≥5 differences → MEDIUM concern)

        Returns:
            List of weak predicate dicts with K-number, reason, priority
        """
        weak_predicates = []

        if not self.review_data or not self.review_data.get('accepted_predicates'):
            return [{
                'k_number': 'N/A',
                'priority': 'HIGH',
                'reason': 'No accepted predicates found in review.json',
                'confidence': 100,
                'category': 'weak_predicate',
                'remediation': 'Run /fda:propose or /fda:research to identify predicates'
            }]

        accepted = self.review_data.get('accepted_predicates', [])

        for predicate in accepted:
            k_number = predicate.get('k_number', 'Unknown')
            issues = []
            max_priority = 'LOW'

            # Check recall count
            recalls_total = predicate.get('recalls_total', 0)
            if isinstance(recalls_total, int) and recalls_total >= self.RECALL_THRESHOLD_HIGH:
                issues.append(f'{recalls_total} recalls on record')
                max_priority = 'HIGH'

            # Check clearance age
            decision_date = predicate.get('decision_date')
            if decision_date:
                try:
                    # Parse date (format: YYYY-MM-DD or YYYYMMDD)
                    if '-' in decision_date:
                        clearance_date = datetime.strptime(decision_date, '%Y-%m-%d')
                    else:
                        clearance_date = datetime.strptime(decision_date, '%Y%m%d')

                    age_years = (datetime.now() - clearance_date).days / 365.25

                    if age_years > self.CLEARANCE_AGE_THRESHOLD_MEDIUM:
                        issues.append(f'{int(age_years)} years old (>{self.CLEARANCE_AGE_THRESHOLD_MEDIUM} years)')
                        if max_priority == 'LOW':
                            max_priority = 'MEDIUM'
                except (ValueError, TypeError) as e:
                    logger.warning("Could not parse clearance date for weak predicate detection: %s", e)

            # Check SE differences (from se_comparison.md)
            if self.se_comparison and k_number in self.se_comparison:
                # Count rows with "Different" in SE comparison
                diff_count = self.se_comparison.count('Different')
                if diff_count >= self.SE_DIFFERENCE_THRESHOLD:
                    issues.append(f'{diff_count} SE differences identified')
                    if max_priority == 'LOW':
                        max_priority = 'MEDIUM'

            # If any issues found, add to weak predicates
            if issues:
                weak_predicates.append({
                    'k_number': k_number,
                    'device_name': predicate.get('device_name', 'Unknown'),
                    'priority': max_priority,
                    'reason': '; '.join(issues),
                    'confidence': 90 if max_priority == 'HIGH' else 80,
                    'category': 'weak_predicate',
                    'remediation': 'Consider alternative predicates or justify selection in SE discussion'
                })

        return weak_predicates

    def detect_testing_gaps(self) -> List[Dict[str, Any]]:
        """
        Identify missing tests by comparing expected tests to declared tests.

        Compares standards_lookup.json (expected) against extracted sections
        from predicates to identify testing gaps.

        Returns:
            List of testing gap dicts with standard, test_type, priority
        """
        testing_gaps = []

        if not self.standards_lookup:
            return [{
                'standard': 'N/A',
                'priority': 'MEDIUM',
                'reason': 'No standards lookup data available',
                'confidence': 70,
                'category': 'testing_gap',
                'remediation': 'Run /fda:standards to identify applicable standards'
            }]

        # Get expected standards from lookup
        expected_standards = set()
        for standard in self.standards_lookup:
            std_number = standard.get('standard_number') or standard.get('recognition_number')
            if std_number:
                expected_standards.add(std_number)

        # Get declared standards from device profile
        declared_standards = set()
        device_standards = self.device_profile.get('standards', [])
        if isinstance(device_standards, list):
            for std in device_standards:
                if isinstance(std, str):
                    declared_standards.add(std)
                elif isinstance(std, dict):
                    declared_standards.add(std.get('standard_number', ''))

        # Find missing standards
        missing_standards = expected_standards - declared_standards

        for std in missing_standards:
            # Find full standard info
            std_info = next((s for s in self.standards_lookup
                           if (s.get('standard_number') == std or
                               s.get('recognition_number') == std)), None)

            if std_info:
                testing_gaps.append({
                    'standard': std,
                    'title': std_info.get('title', 'Unknown'),
                    'priority': 'HIGH',  # Missing expected standard is HIGH priority
                    'reason': f'Standard {std} expected for this product code but not declared',
                    'confidence': 85,
                    'category': 'testing_gap',
                    'remediation': f'Perform testing to {std} or justify why not applicable'
                })

        return testing_gaps

    def detect_standards_gaps(self) -> List[Dict[str, Any]]:
        """
        Query FDA Recognized Standards and compare to declared standards.

        Note: This function provides a framework for standards gap detection.
        Full implementation would query FDA Recognition Database or use
        web scraping. Current implementation uses standards_lookup.json.

        Returns:
            List of standards gap dicts
        """
        # This is a placeholder that uses testing_gaps logic
        # In full implementation, this would query FDA Recognition Database
        # and cross-reference with device profile

        # For now, defer to detect_testing_gaps()
        return []  # Avoid duplication with testing_gaps

    def analyze_all_gaps(self) -> Dict[str, Any]:
        """
        Run all gap detection functions and aggregate results.

        Returns:
            Dict with gap categories, counts, priorities, and overall confidence
        """
        results = {
            'missing_data': self.detect_missing_device_data(),
            'weak_predicates': self.detect_weak_predicates(),
            'testing_gaps': self.detect_testing_gaps(),
            'standards_gaps': self.detect_standards_gaps(),
            'timestamp': datetime.now().isoformat(),
            'project_dir': str(self.project_dir)
        }

        # Calculate summary statistics
        all_gaps = (results['missing_data'] + results['weak_predicates'] +
                   results['testing_gaps'] + results['standards_gaps'])

        results['summary'] = {
            'total_gaps': len(all_gaps),
            'high_priority': len([g for g in all_gaps if g.get('priority') == 'HIGH']),
            'medium_priority': len([g for g in all_gaps if g.get('priority') == 'MEDIUM']),
            'low_priority': len([g for g in all_gaps if g.get('priority') == 'LOW']),
            'critical': len([g for g in all_gaps if g.get('priority') == 'CRITICAL'])
        }

        return results


def detect_missing_device_data(project_dir: str) -> List[Dict[str, Any]]:
    """Convenience function for detecting missing device data."""
    analyzer = GapAnalyzer(project_dir)
    return analyzer.detect_missing_device_data()


def detect_weak_predicates(project_dir: str) -> List[Dict[str, Any]]:
    """Convenience function for detecting weak predicates."""
    analyzer = GapAnalyzer(project_dir)
    return analyzer.detect_weak_predicates()


def detect_testing_gaps(project_dir: str) -> List[Dict[str, Any]]:
    """Convenience function for detecting testing gaps."""
    analyzer = GapAnalyzer(project_dir)
    return analyzer.detect_testing_gaps()


def analyze_all_gaps(project_dir: str) -> Dict[str, Any]:
    """Convenience function for full gap analysis."""
    analyzer = GapAnalyzer(project_dir)
    return analyzer.analyze_all_gaps()


def calculate_gap_analysis_confidence(gap_results: Dict[str, Any],
                                     device_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate confidence score for gap analysis results.

    Confidence based on:
    - Data completeness (40%): How complete is device_profile.json
    - Predicate quality (30%): Recall history, age of accepted predicates
    - Gap clarity (20%): How definitive are the gaps detected
    - Cross-validation (10%): Agreement between detection methods

    Args:
        gap_results: Results from analyze_all_gaps()
        device_profile: Device profile dict

    Returns:
        Dict with confidence_score (0-100), confidence_level (HIGH/MEDIUM/LOW),
        and contributing factors
    """
    scores = {}

    # Factor 1: Data Completeness (40 points max)
    total_fields = (len(GapAnalyzer.HIGH_PRIORITY_FIELDS) +
                   len(GapAnalyzer.MEDIUM_PRIORITY_FIELDS) +
                   len(GapAnalyzer.LOW_PRIORITY_FIELDS))

    filled_fields = 0
    for field_list in [GapAnalyzer.HIGH_PRIORITY_FIELDS,
                      GapAnalyzer.MEDIUM_PRIORITY_FIELDS,
                      GapAnalyzer.LOW_PRIORITY_FIELDS]:
        for field in field_list:
            value = device_profile.get(field)
            if value and (not isinstance(value, str) or value.strip()):
                filled_fields += 1

    completeness_score = int((filled_fields / total_fields) * 40) if total_fields > 0 else 0
    scores['data_completeness'] = completeness_score

    # Factor 2: Predicate Quality (30 points max)
    weak_predicates = gap_results.get('weak_predicates', [])
    high_priority_weak = len([p for p in weak_predicates if p.get('priority') == 'HIGH'])

    if not weak_predicates or (len(weak_predicates) == 1 and
                               weak_predicates[0].get('k_number') == 'N/A'):
        # No predicates analyzed
        predicate_score = 15  # Neutral score
    elif high_priority_weak == 0:
        # All predicates good quality
        predicate_score = 30
    elif high_priority_weak == len(weak_predicates):
        # All predicates weak
        predicate_score = 5
    else:
        # Mix of weak and good predicates
        weak_ratio = high_priority_weak / len(weak_predicates)
        predicate_score = int(30 * (1 - weak_ratio))

    scores['predicate_quality'] = predicate_score

    # Factor 3: Gap Clarity (20 points max)
    all_gaps = (gap_results.get('missing_data', []) +
               gap_results.get('weak_predicates', []) +
               gap_results.get('testing_gaps', []))

    if not all_gaps:
        # No gaps is GOOD
        clarity_score = 20
    else:
        # Average confidence of detected gaps
        avg_confidence = sum(g.get('confidence', 70) for g in all_gaps) / len(all_gaps)
        clarity_score = int((avg_confidence / 100) * 20)

    scores['gap_clarity'] = clarity_score

    # Factor 4: Cross-validation (10 points max)
    # If multiple gap types detected, cross-validation is higher
    gap_types_detected = sum([
        1 if gap_results.get('missing_data') else 0,
        1 if gap_results.get('weak_predicates') else 0,
        1 if gap_results.get('testing_gaps') else 0
    ])

    cross_val_score = min(gap_types_detected * 3, 10)
    scores['cross_validation'] = cross_val_score

    # Total confidence score
    total_score = sum(scores.values())

    # Confidence level classification
    if total_score >= 90:
        confidence_level = 'HIGH'
    elif total_score >= 70:
        confidence_level = 'MEDIUM'
    else:
        confidence_level = 'LOW'

    return {
        'confidence_score': total_score,
        'confidence_level': confidence_level,
        'contributing_factors': scores,
        'interpretation': _interpret_confidence(confidence_level, total_score)
    }


def _interpret_confidence(level: str, score: int) -> str:
    """Generate human-readable confidence interpretation."""
    if level == 'HIGH':
        return (f'High confidence ({score}/100) - Gap analysis is comprehensive and reliable. '
               f'Data completeness and predicate quality are good.')
    elif level == 'MEDIUM':
        return (f'Medium confidence ({score}/100) - Gap analysis is generally reliable but '
               f'some data may be incomplete. Validate HIGH priority gaps manually.')
    else:
        return (f'Low confidence ({score}/100) - Gap analysis may be incomplete due to missing '
               f'data or lack of predicates. MANUAL REVIEW REQUIRED.')


def generate_gap_analysis_report(gap_results: Dict[str, Any],
                                confidence: Dict[str, Any],
                                project_name: str = 'Unknown') -> str:
    """
    Generate comprehensive markdown gap analysis report.

    Includes:
    - Executive summary with confidence
    - Gaps organized by category (4 sections)
    - Recommended actions (priority-ordered)
    - Automation metadata
    - Human review checkpoints

    Args:
        gap_results: Results from analyze_all_gaps()
        confidence: Results from calculate_gap_analysis_confidence()
        project_name: Name of project for report header

    Returns:
        Markdown-formatted report string
    """
    report = []

    # Header
    report.append('# Automated Gap Analysis Report')
    report.append(f'**Project:** {project_name}')
    report.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    report.append(f'**Automation Version:** Phase 4 - Gap Analyzer v1.0')
    report.append('')
    report.append('---')
    report.append('')

    # Disclaimer
    report.append('⚠️ **AUTOMATION ASSISTS, DOES NOT REPLACE RA JUDGMENT**')
    report.append('')
    report.append('This automation provides data-driven gap identification for:')
    report.append('- Missing device data')
    report.append('- Weak predicate indicators')
    report.append('- Testing and standards gaps')
    report.append('')
    report.append('**YOU (RA professional) are responsible for:**')
    report.append('- Validating all HIGH priority gaps')
    report.append('- Determining gap criticality for YOUR device')
    report.append('- Final regulatory decisions')
    report.append('')
    report.append('All automated findings must be independently verified')
    report.append('by qualified Regulatory Affairs professionals.')
    report.append('')
    report.append('---')
    report.append('')

    # Executive Summary
    summary = gap_results.get('summary', {})
    conf_score = confidence.get('confidence_score', 0)
    conf_level = confidence.get('confidence_level', 'UNKNOWN')

    report.append('## Executive Summary')
    report.append('')
    report.append(f'**Total Gaps Identified:** {summary.get("total_gaps", 0)}')
    report.append(f'- CRITICAL (blocking): {summary.get("critical", 0)}')
    report.append(f'- HIGH priority (blocking): {summary.get("high_priority", 0)}')
    report.append(f'- MEDIUM priority (recommended): {summary.get("medium_priority", 0)}')
    report.append(f'- LOW priority (optional): {summary.get("low_priority", 0)}')
    report.append('')
    report.append(f'**Automation Confidence:** {conf_score}% ({conf_level})')
    report.append(f'- {confidence.get("interpretation", "No interpretation available")}')
    report.append('')

    # Gap Categories

    # 1. Missing Device Data
    report.append('---')
    report.append('')
    report.append('## 1. Missing Device Data')
    report.append('')
    missing_data = gap_results.get('missing_data', [])

    if not missing_data:
        report.append('✅ **No missing device data detected** - Device profile appears complete')
        report.append('')
    else:
        # Group by priority
        critical = [g for g in missing_data if g.get('priority') == 'CRITICAL']
        high = [g for g in missing_data if g.get('priority') == 'HIGH']
        medium = [g for g in missing_data if g.get('priority') == 'MEDIUM']
        low = [g for g in missing_data if g.get('priority') == 'LOW']

        for priority_group, gaps, icon in [
            ('CRITICAL', critical, '🔴'),
            ('HIGH', high, '🟠'),
            ('MEDIUM', medium, '🟡'),
            ('LOW', low, '⚪')
        ]:
            if gaps:
                report.append(f'### {icon} {priority_group} Priority ({len(gaps)} gaps)')
                report.append('')
                for gap in gaps:
                    report.append(f'**{gap.get("field")}**')
                    report.append(f'- Reason: {gap.get("reason")}')
                    report.append(f'- Remediation: {gap.get("remediation", "Review and complete")}')
                    report.append(f'- Confidence: {gap.get("confidence", 0)}%')
                    report.append('')

    # 2. Weak Predicates
    report.append('---')
    report.append('')
    report.append('## 2. Weak Predicate Indicators')
    report.append('')
    weak_preds = gap_results.get('weak_predicates', [])

    if not weak_preds or (len(weak_preds) == 1 and weak_preds[0].get('k_number') == 'N/A'):
        report.append('⚠️ **No predicates analyzed** - Run predicate selection first')
        report.append('')
    elif all(g.get('priority') == 'LOW' for g in weak_preds if g.get('k_number') != 'N/A'):
        report.append('✅ **All accepted predicates appear strong** - No major concerns detected')
        report.append('')
    else:
        for priority in ['HIGH', 'MEDIUM']:
            priority_preds = [p for p in weak_preds if p.get('priority') == priority]
            if priority_preds:
                icon = '🔴' if priority == 'HIGH' else '🟡'
                report.append(f'### {icon} {priority} Priority ({len(priority_preds)} predicates)')
                report.append('')
                for pred in priority_preds:
                    report.append(f'**{pred.get("k_number")}** - {pred.get("device_name", "Unknown")}')
                    report.append(f'- Concerns: {pred.get("reason")}')
                    report.append(f'- Remediation: {pred.get("remediation", "Review and justify or select alternative")}')
                    report.append(f'- Confidence: {pred.get("confidence", 0)}%')
                    report.append('')

    # 3. Testing Gaps
    report.append('---')
    report.append('')
    report.append('## 3. Testing & Standards Gaps')
    report.append('')
    testing_gaps = gap_results.get('testing_gaps', [])

    if not testing_gaps:
        report.append('✅ **No testing gaps detected** - Declared standards align with expectations')
        report.append('')
    else:
        report.append(f'**{len(testing_gaps)} standards expected but not declared**')
        report.append('')
        for gap in testing_gaps:
            report.append(f'**{gap.get("standard")}**')
            report.append(f'- Title: {gap.get("title", "Unknown")}')
            report.append(f'- Reason: {gap.get("reason")}')
            report.append(f'- Remediation: {gap.get("remediation", "Perform testing or justify N/A")}')
            report.append(f'- Confidence: {gap.get("confidence", 0)}%')
            report.append('')

    # Recommended Actions (Priority-ordered)
    report.append('---')
    report.append('')
    report.append('## Recommended Actions (Priority Order)')
    report.append('')

    all_gaps = missing_data + weak_preds + testing_gaps
    # Sort by priority: CRITICAL > HIGH > MEDIUM > LOW
    priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
    sorted_gaps = sorted(all_gaps,
                        key=lambda g: (priority_order.get(g.get('priority', 'LOW'), 4),
                                     -g.get('confidence', 0)))

    critical_high = [g for g in sorted_gaps if g.get('priority') in ['CRITICAL', 'HIGH']]

    if not critical_high:
        report.append('✅ **No critical or high-priority gaps** - Project data appears complete')
        report.append('')
    else:
        for i, gap in enumerate(critical_high, 1):
            priority_icon = '🔴' if gap.get('priority') == 'CRITICAL' else '🟠'
            field_or_knum = gap.get('field') or gap.get('k_number') or gap.get('standard', 'Unknown')
            report.append(f'{i}. {priority_icon} **[{gap.get("priority")}]** {field_or_knum}')
            report.append(f'   - {gap.get("remediation", gap.get("reason", "Review and address"))}')
            report.append('')

    # Human Review Checkpoints
    report.append('---')
    report.append('')
    report.append('## Human Review Checkpoints')
    report.append('')
    report.append('Before proceeding with submission, RA professional must confirm:')
    report.append('')
    report.append('- [ ] All CRITICAL gaps have been addressed')
    report.append('- [ ] All HIGH priority gaps have been reviewed and resolved')
    report.append('- [ ] MEDIUM priority gaps have been evaluated for applicability')
    report.append('- [ ] Weak predicate indicators have been investigated')
    report.append('- [ ] This gap analysis reflects current project state')
    report.append('')

    # Metadata
    report.append('---')
    report.append('')
    report.append('## Automation Metadata')
    report.append('')
    report.append('**Gap Analysis Details:**')
    report.append(f'- Timestamp: {gap_results.get("timestamp", "Unknown")}')
    report.append(f'- Project Directory: {gap_results.get("project_dir", "Unknown")}')
    report.append(f'- Confidence Score: {conf_score}/100 ({conf_level})')
    report.append(f'- Contributing Factors:')
    for factor, score in confidence.get('contributing_factors', {}).items():
        report.append(f'  - {factor}: {score} points')
    report.append('')
    report.append('**Data Sources:**')
    report.append('- device_profile.json (device specifications)')
    report.append('- review.json (accepted predicates)')
    report.append('- se_comparison.md (SE analysis)')
    report.append('- standards_lookup.json (applicable standards)')
    report.append('')
    report.append('**Valid Until:** 7 days from generation - Re-run before submission')
    report.append('')

    # Footer
    report.append('---')
    report.append('')
    report.append('*Generated by FDA Predicate Assistant - Phase 4 Automation*')
    report.append('')

    return '\n'.join(report)


def write_gap_data_json(gap_results: Dict[str, Any],
                       confidence: Dict[str, Any],
                       output_path: str) -> None:
    """
    Write machine-readable JSON with gap analysis results.

    Args:
        gap_results: Results from analyze_all_gaps()
        confidence: Results from calculate_gap_analysis_confidence()
        output_path: Path to write JSON file
    """
    output_data = {
        'gap_analysis': gap_results,
        'confidence': confidence,
        'metadata': {
            'version': 'Phase 4 - Gap Analyzer v1.0',
            'generated_at': datetime.now().isoformat(),
            'format': 'FDA Gap Analysis JSON v1.0'
        }
    }

    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)


def update_enrichment_metadata(project_dir: str,
                              gap_results: Dict[str, Any],
                              confidence: Dict[str, Any]) -> None:
    """
    Append gap analysis results to enrichment_metadata.json.

    Args:
        project_dir: Project directory path
        gap_results: Results from analyze_all_gaps()
        confidence: Results from calculate_gap_analysis_confidence()
    """
    metadata_path = Path(project_dir) / 'enrichment_metadata.json'

    # Load existing metadata or create new
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}

    # Append gap analysis section
    metadata['gap_analysis'] = {
        'timestamp': gap_results.get('timestamp'),
        'confidence_score': confidence.get('confidence_score'),
        'confidence_level': confidence.get('confidence_level'),
        'total_gaps': gap_results.get('summary', {}).get('total_gaps', 0),
        'high_priority_gaps': gap_results.get('summary', {}).get('high_priority', 0),
        'human_review_required': confidence.get('confidence_level') == 'LOW'
    }

    # Write back
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
