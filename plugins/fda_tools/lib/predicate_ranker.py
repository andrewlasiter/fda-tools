#!/usr/bin/env python3
"""
Predicate Ranker Module for FDA 510(k) Submissions

Smart predicate recommendations using FDA-compliant confidence scoring.
Leverages existing confidence-scoring.md algorithm with TF-IDF enhancements.

Part of Phase 4: Automation Features
"""

import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fda_tools.lib.post_market_surveillance import _maude_safety_score

logger = logging.getLogger(__name__)


class PredicateRanker:
    """
    Smart predicate ranking using FDA-compliant confidence scoring.

    Leverages the existing confidence-scoring.md system (5 base components +
    extended scoring + binary gates + risk flags) and adds TF-IDF text similarity
    for enhanced IFU/technology matching.
    """

    def __init__(self, project_dir: str):
        """
        Initialize predicate ranker for a specific project.

        Args:
            project_dir: Path to project directory
        """
        self.project_dir = Path(project_dir)
        self.device_profile = self._load_device_profile()
        self.enriched_predicates = self._load_enriched_predicates()

    def _load_device_profile(self) -> Dict[str, Any]:
        """Load subject device profile."""
        profile_path = self.project_dir / 'device_profile.json'
        if not profile_path.exists():
            return {}

        with open(profile_path, 'r') as f:
            return json.load(f)

    def _load_enriched_predicates(self) -> List[Dict[str, Any]]:
        """Load enriched predicates from CSV or review.json."""
        # Try review.json first (accepted predicates)
        review_path = self.project_dir / 'review.json'
        if review_path.exists():
            with open(review_path, 'r') as f:
                review_data = json.load(f)
                return review_data.get('accepted_predicates', [])

        # Fallback: Load from enriched CSV
        csv_path = self.project_dir / '510k_download_enriched.csv'
        if csv_path.exists():
            import csv
            predicates = []
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    predicates.append(row)
            return predicates

        return []

    def calculate_text_similarity(self, text1: str, text2: str) -> Dict[str, float]:
        """
        Calculate text similarity using TF-IDF and keyword overlap.

        Args:
            text1: Subject device text (IFU or tech characteristics)
            text2: Predicate device text

        Returns:
            Dict with tfidf_similarity and keyword_overlap scores
        """
        if not text1 or not text2:
            return {'tfidf_similarity': 0.0, 'keyword_overlap': 0.0}

        # Normalize text
        text1_norm = text1.lower().strip()
        text2_norm = text2.lower().strip()

        # Extract keywords (simple approach - split on non-alphanumeric)
        words1 = set(re.findall(r'\b[a-z]{3,}\b', text1_norm))
        words2 = set(re.findall(r'\b[a-z]{3,}\b', text2_norm))

        # Remove common stopwords
        stopwords = {'the', 'and', 'for', 'with', 'that', 'this', 'from',
                    'are', 'was', 'were', 'been', 'have', 'has', 'had',
                    'but', 'not', 'can', 'will', 'use', 'used', 'device'}
        words1 = words1 - stopwords
        words2 = words2 - stopwords

        # Keyword overlap (Jaccard similarity)
        if not words1 or not words2:
            keyword_overlap = 0.0
        else:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            keyword_overlap = intersection / union if union > 0 else 0.0

        # Simple TF-IDF approximation using word frequency
        # (Full TF-IDF would require sklearn, using simplified version)
        all_words = list(words1 | words2)

        # Build term frequency vectors
        tf1 = Counter(re.findall(r'\b[a-z]{3,}\b', text1_norm))
        tf2 = Counter(re.findall(r'\b[a-z]{3,}\b', text2_norm))

        # Calculate cosine similarity
        dot_product = sum(tf1.get(word, 0) * tf2.get(word, 0) for word in all_words)
        magnitude1 = sum(count ** 2 for count in tf1.values()) ** 0.5
        magnitude2 = sum(count ** 2 for count in tf2.values()) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            tfidf_similarity = 0.0
        else:
            tfidf_similarity = dot_product / (magnitude1 * magnitude2)

        return {
            'tfidf_similarity': round(tfidf_similarity, 3),
            'keyword_overlap': round(keyword_overlap, 3)
        }

    def rank_predicates(self,
                       top_n: int = 10,
                       min_confidence: int = 40) -> List[Dict[str, Any]]:
        """
        Rank predicates using existing confidence scoring + TF-IDF enhancement.

        Uses the FDA-compliant confidence-scoring.md system:
        - Base scoring (100 pts): section context, citation frequency, product code,
          recency, regulatory history
        - Extended scoring (+20 pts): chain depth, SE table, applicant, IFU overlap
        - Binary gates: web validation, FDA criteria compliance
        - Risk flags: recalls, MAUDE, enforcement

        Adds TF-IDF similarity as additional IFU overlap metric.

        Args:
            top_n: Number of top predicates to return
            min_confidence: Minimum confidence score threshold

        Returns:
            List of ranked predicates with scores and recommendations
        """
        if not self.enriched_predicates:
            return []

        ranked = []

        # Get subject device text for similarity
        subject_ifu = self.device_profile.get('indications_for_use', '')
        subject_tech = self.device_profile.get('technological_characteristics', '')
        subject_product_code = self.device_profile.get('product_code', '')

        for predicate in self.enriched_predicates:
            # Use existing confidence score if available
            base_score = predicate.get('confidence_score', 0)

            # If no confidence score, estimate based on available data
            if not base_score:
                base_score = self._estimate_confidence_score(predicate, subject_product_code)

            # Skip if below minimum threshold
            if base_score < min_confidence:
                continue

            # Calculate TF-IDF similarity for IFU
            predicate_ifu = predicate.get('statement', '') or predicate.get('indications_for_use', '')
            ifu_similarity = self.calculate_text_similarity(subject_ifu, predicate_ifu)

            # Calculate TF-IDF similarity for technology
            predicate_tech = predicate.get('technological_characteristics', '')
            tech_similarity = self.calculate_text_similarity(subject_tech, predicate_tech)

            # Enhanced IFU overlap score (replaces +5 bonus with data-driven score)
            ifu_bonus = min(int(ifu_similarity['tfidf_similarity'] * 5), 5)

            # Tech similarity bonus (not in original system, but valuable)
            tech_bonus = min(int(tech_similarity['tfidf_similarity'] * 3), 3)

            # Total score = base + IFU bonus + tech bonus
            total_score = base_score + ifu_bonus + tech_bonus

            # Extract risk flags
            risk_flags = self._extract_risk_flags(predicate)

            # Determine strength level
            strength = self._classify_strength(total_score, risk_flags)

            ranked.append({
                'k_number': predicate.get('k_number', 'Unknown'),
                'device_name': predicate.get('device_name', 'Unknown'),
                'applicant': predicate.get('applicant', 'Unknown'),
                'decision_date': predicate.get('decision_date', 'Unknown'),
                'product_code': predicate.get('product_code', 'Unknown'),
                'base_score': base_score,
                'ifu_similarity': ifu_similarity['tfidf_similarity'],
                'tech_similarity': tech_similarity['tfidf_similarity'],
                'ifu_bonus': ifu_bonus,
                'tech_bonus': tech_bonus,
                'total_score': total_score,
                'strength': strength,
                'risk_flags': risk_flags,
                'recommendation': self._generate_recommendation(strength, risk_flags)
            })

        # Sort by total score (descending)
        ranked.sort(key=lambda x: x['total_score'], reverse=True)

        return ranked[:top_n]

    def _estimate_confidence_score(self, predicate: Dict[str, Any],
                                   subject_product_code: str) -> int:
        """
        Estimate confidence score when not pre-calculated.

        Uses simplified version of confidence-scoring.md algorithm.
        """
        score = 0

        # Product code match (15 pts)
        pred_code = predicate.get('product_code', '')
        if pred_code == subject_product_code:
            score += 15
        elif pred_code and subject_product_code:
            # Partial credit for same panel (would need panel lookup)
            score += 5

        # Recency (15 pts)
        decision_date = predicate.get('decision_date', '')
        if decision_date:
            try:
                if '-' in decision_date:
                    clearance_date = datetime.strptime(decision_date, '%Y-%m-%d')
                else:
                    clearance_date = datetime.strptime(decision_date, '%Y%m%d')

                age_years = (datetime.now() - clearance_date).days / 365.25

                if age_years < 5:
                    score += 15
                elif age_years < 10:
                    score += 10
                elif age_years < 15:
                    score += 5
                else:
                    score += 2
            except (ValueError, TypeError):
                score += 5  # Unknown date

        # Clean regulatory history (10 pts) — recall component
        recalls = predicate.get('recalls_total', 0)
        if isinstance(recalls, int):
            if recalls == 0:
                score += 10
            elif recalls == 1:
                score += 5
            # else: 0 points

        # MAUDE safety component (10 pts) — granular score based on annual event rate (FDA-119)
        maude_5y = predicate.get('maude_productcode_5y', 0)
        if isinstance(maude_5y, (int, float)):
            events_per_year = maude_5y / 5.0
            score += _maude_safety_score(events_per_year)

        # Section context (40 pts) - assume moderate if no data
        score += 25  # Conservative estimate

        # Citation frequency (20 pts) - assume minimal
        score += 5  # Conservative estimate

        return score

    def _extract_risk_flags(self, predicate: Dict[str, Any]) -> List[str]:
        """Extract risk flags from predicate data."""
        flags = []

        # Recalls
        recalls = predicate.get('recalls_total', 0)
        if isinstance(recalls, int) and recalls > 0:
            flags.append(f'RECALLED ({recalls} recall{"s" if recalls > 1 else ""})')

        # High MAUDE — flag when product code averages >10 events/year (FDA-119)
        maude_5y = predicate.get('maude_productcode_5y', 0)
        if isinstance(maude_5y, (int, float)):
            events_per_year = maude_5y / 5.0
            if events_per_year > 10:
                flags.append(f'HIGH_MAUDE ({maude_5y} events / 5y, {events_per_year:.0f}/yr)')

        # Old predicate
        decision_date = predicate.get('decision_date', '')
        if decision_date:
            try:
                if '-' in decision_date:
                    clearance_date = datetime.strptime(decision_date, '%Y-%m-%d')
                else:
                    clearance_date = datetime.strptime(decision_date, '%Y%m%d')

                age_years = (datetime.now() - clearance_date).days / 365.25
                if age_years > 15:
                    flags.append(f'OLD ({int(age_years)} years)')
            except (ValueError, TypeError) as e:
                logger.warning("Could not parse decision_date for risk flag extraction: %s", e)

        # Web validation flags (if present)
        web_val = predicate.get('web_validation', '')
        if web_val == 'RED':
            flags.append('WEB_VALIDATION_RED')
        elif web_val == 'YELLOW':
            flags.append('WEB_VALIDATION_YELLOW')

        return flags

    def _classify_strength(self, total_score: int, risk_flags: List[str]) -> str:
        """Classify predicate strength based on score and flags."""
        # Check for critical flags that override score
        if 'WEB_VALIDATION_RED' in risk_flags:
            return 'REJECT'

        # Score-based classification (confidence-scoring.md thresholds)
        if total_score >= 85:
            return 'STRONG'
        elif total_score >= 70:
            return 'GOOD'
        elif total_score >= 55:
            return 'MODERATE'
        elif total_score >= 40:
            return 'WEAK'
        else:
            return 'POOR'

    def _generate_recommendation(self, strength: str,
                                 risk_flags: List[str]) -> str:
        """Generate human-readable recommendation."""
        if strength == 'STRONG':
            rec = 'Excellent predicate - recommend as primary'
        elif strength == 'GOOD':
            rec = 'Solid predicate - safe to use'
        elif strength == 'MODERATE':
            rec = 'Viable predicate - review concerns before accepting'
        elif strength == 'WEAK':
            rec = 'Marginal predicate - consider alternatives'
        else:
            rec = 'Low confidence - do not use as predicate'

        # Add flag warnings
        if 'RECALLED' in ' '.join(risk_flags):
            rec += ' ⚠️ Note: Recall history'
        if 'WEB_VALIDATION_RED' in risk_flags:
            rec = 'DO NOT USE - Critical regulatory issues'

        return rec


def rank_predicates(project_dir: str, top_n: int = 10) -> List[Dict[str, Any]]:
    """Convenience function for ranking predicates."""
    ranker = PredicateRanker(project_dir)
    return ranker.rank_predicates(top_n=top_n)


def generate_smart_recommendations_report(ranked_predicates: List[Dict[str, Any]],
                                         project_name: str = 'Unknown') -> str:
    """
    Generate markdown report with smart predicate recommendations.

    Args:
        ranked_predicates: List of ranked predicates from rank_predicates()
        project_name: Project name for report header

    Returns:
        Markdown-formatted report
    """
    report = []

    # Header
    report.append('# Smart Predicate Recommendations Report')
    report.append(f'**Project:** {project_name}')
    report.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    report.append(f'**Automation Version:** Phase 4B - Predicate Ranker v1.0')
    report.append('')
    report.append('---')
    report.append('')

    # Disclaimer
    report.append('⚠️ **AUTOMATION ASSISTS, DOES NOT REPLACE RA JUDGMENT**')
    report.append('')
    report.append('This automation provides data-driven predicate ranking based on:')
    report.append('- FDA-compliant confidence scoring (confidence-scoring.md)')
    report.append('- TF-IDF text similarity (IFU and technology matching)')
    report.append('- Regulatory history and risk flags')
    report.append('')
    report.append('**YOU (RA professional) are responsible for:**')
    report.append('- Reviewing actual 510(k) summaries for Rank 1-3 predicates')
    report.append('- Validating that indications match YOUR device')
    report.append('- Determining substantial equivalence')
    report.append('- Final predicate selection decisions')
    report.append('')
    report.append('All recommendations must be independently verified')
    report.append('by qualified Regulatory Affairs professionals.')
    report.append('')
    report.append('---')
    report.append('')

    # Executive Summary
    report.append('## Executive Summary')
    report.append('')
    report.append(f'**Total Predicates Analyzed:** {len(ranked_predicates)}')

    strong_count = len([p for p in ranked_predicates if p['strength'] == 'STRONG'])
    good_count = len([p for p in ranked_predicates if p['strength'] == 'GOOD'])
    moderate_count = len([p for p in ranked_predicates if p['strength'] == 'MODERATE'])

    report.append(f'- STRONG (85-120 pts): {strong_count}')
    report.append(f'- GOOD (70-84 pts): {good_count}')
    report.append(f'- MODERATE (55-69 pts): {moderate_count}')
    report.append('')

    if strong_count > 0:
        report.append(f'✅ **{strong_count} high-confidence predicate{"s" if strong_count > 1 else ""} identified**')
    elif good_count > 0:
        report.append(f'✓ **{good_count} good predicate{"s" if good_count > 1 else ""} available**')
    else:
        report.append('⚠️ **No strong predicates identified - manual research recommended**')

    report.append('')
    report.append('---')
    report.append('')

    # Top 10 Ranked Predicates
    report.append('## Top Ranked Predicates')
    report.append('')

    for i, pred in enumerate(ranked_predicates, 1):
        # Rank header with score
        icon = {
            'STRONG': '⭐',
            'GOOD': '✓',
            'MODERATE': '○',
            'WEAK': '△',
            'POOR': '✗',
            'REJECT': '✗'
        }.get(pred['strength'], '•')

        report.append(f'### {icon} Rank {i}: {pred["k_number"]} ({pred["strength"]} - {pred["total_score"]} pts)')
        report.append('')
        report.append(f'**Device:** {pred["device_name"]}')
        report.append(f'**Applicant:** {pred["applicant"]}')
        report.append(f'**Clearance Date:** {pred["decision_date"]}')
        report.append(f'**Product Code:** {pred["product_code"]}')
        report.append('')

        # Score breakdown
        report.append('**Score Breakdown:**')
        report.append(f'- Base Confidence Score: {pred["base_score"]}/100')
        report.append(f'- IFU Similarity Bonus: +{pred["ifu_bonus"]} ({pred["ifu_similarity"]:.1%} match)')
        report.append(f'- Technology Similarity Bonus: +{pred["tech_bonus"]} ({pred["tech_similarity"]:.1%} match)')
        report.append(f'- **Total Score:** {pred["total_score"]}/108')
        report.append('')

        # Risk flags
        if pred['risk_flags']:
            report.append('**Risk Flags:**')
            for flag in pred['risk_flags']:
                report.append(f'- ⚠️ {flag}')
            report.append('')

        # Recommendation
        report.append(f'**Recommendation:** {pred["recommendation"]}')
        report.append('')
        report.append('---')
        report.append('')

    # Human Review Checkpoints
    report.append('## Human Review Checkpoints')
    report.append('')
    report.append('Before finalizing predicate selection, RA professional must:')
    report.append('')
    report.append('- [ ] I have reviewed actual 510(k) summaries for Rank 1-3 predicates')
    report.append('- [ ] I have verified indications match my device')
    report.append('- [ ] I have compared technological characteristics in detail')
    report.append('- [ ] I have reviewed risk flags and assessed relevance')
    report.append('- [ ] I have validated these recommendations are current')
    report.append('')

    # Metadata
    report.append('---')
    report.append('')
    report.append('## Methodology')
    report.append('')
    report.append('**Scoring Algorithm:**')
    report.append('- Base: FDA-compliant confidence scoring (confidence-scoring.md)')
    report.append('  - Section context (40 pts), Citation frequency (20 pts),')
    report.append('  - Product code match (15 pts), Recency (15 pts),')
    report.append('  - Regulatory history (10 pts)')
    report.append('- Enhancement: TF-IDF text similarity')
    report.append('  - IFU matching (0-5 bonus pts)')
    report.append('  - Technology matching (0-3 bonus pts)')
    report.append('- Risk flags: Independent assessment (RECALLED, HIGH_MAUDE, OLD)')
    report.append('')
    report.append('**Strength Thresholds:**')
    report.append('- STRONG: 85-120 pts (excellent predicates)')
    report.append('- GOOD: 70-84 pts (solid predicates)')
    report.append('- MODERATE: 55-69 pts (viable with review)')
    report.append('- WEAK: 40-54 pts (marginal)')
    report.append('- POOR/REJECT: 0-39 pts (do not use)')
    report.append('')
    report.append('**Valid Until:** 30 days from generation - Re-run before submission')
    report.append('')

    # Footer
    report.append('---')
    report.append('')
    report.append('*Generated by FDA Predicate Assistant - Phase 4B Automation*')
    report.append('')

    return '\n'.join(report)
