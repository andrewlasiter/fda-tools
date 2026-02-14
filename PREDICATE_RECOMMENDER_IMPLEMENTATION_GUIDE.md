# Predicate Recommender - Technical Implementation Guide

**Version:** 1.0
**Date:** 2026-02-13
**Estimated Implementation Time:** 10 hours
**Status:** Ready for Development

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install scikit-learn>=1.0.0 numpy>=1.21.0

# Verify installation
python3 -c "from sklearn.feature_extraction.text import TfidfVectorizer; print('OK')"
```

### Basic Usage

```python
from lib.predicate_recommender import PredicateRecommender
import json

# Initialize recommender
recommender = PredicateRecommender()

# Load subject device
subject_device = json.load(open('device_profile.json'))

# Load enriched predicates (from batchfetch --enrich)
enriched_predicates = recommender.load_csv('510k_download_enriched.csv')

# Generate recommendations
recommendations = recommender.recommend_predicates(
    subject_device=subject_device,
    candidate_pool=enriched_predicates,
    top_n=5
)

# Export results
recommender.export_markdown(recommendations, 'predicate_recommendations.md')
recommender.export_json(recommendations, 'predicate_recommendations.json')

print(f"Top predicate: {recommendations['recommendations'][0]['predicate']['KNUMBER']}")
print(f"Score: {recommendations['recommendations'][0]['final_score']}/100")
```

---

## File Structure

```
plugins/fda-predicate-assistant/
├── lib/
│   ├── fda_enrichment.py          # Existing (Phase 1-3)
│   ├── disclaimers.py             # Existing (Phase 1-3)
│   └── predicate_recommender.py   # NEW (Phase 4)
├── commands/
│   └── batchfetch.md              # UPDATE (add --recommend-predicates)
├── tests/
│   ├── test_fda_enrichment.py     # Existing
│   └── test_predicate_recommender.py  # NEW (Phase 4)
└── docs/
    ├── SMART_PREDICATE_RECOMMENDATIONS_ML_DESIGN.md  # Design document
    └── PREDICATE_RECOMMENDER_USER_GUIDE.md           # User documentation
```

---

## Core Module: predicate_recommender.py

### Class Architecture

```python
"""
Predicate Recommender - Automated predicate selection for FDA 510(k) submissions.

This module implements a hybrid similarity scoring algorithm combining:
- Text similarity (TF-IDF cosine similarity on intended use + device description)
- Discrete feature matching (sterilization, materials, dimensions, standards)
- Risk scoring (recalls, MAUDE events, clinical data requirements, age)

Version: 1.0.0
Date: 2026-02-13
"""

from typing import Dict, List, Tuple, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
import csv
import re
from datetime import datetime


class PredicateRecommender:
    """
    Automated predicate recommendation engine for FDA 510(k) submissions.

    Usage:
        recommender = PredicateRecommender()
        recommendations = recommender.recommend_predicates(subject_device, candidate_pool)
        recommender.export_markdown(recommendations, 'output.md')

    Algorithm:
        Stage 1: Candidate Filtering (product code, MAUDE outliers, recalls, age)
        Stage 2: Similarity Scoring (TF-IDF text + discrete features)
        Stage 3: Risk Adjustment (recall history, MAUDE classification, clinical data)

    Attributes:
        similarity_weights (dict): Weights for text vs feature similarity
        ranking_weights (dict): Weights for similarity vs risk in final score
        vectorizer (TfidfVectorizer): Text vectorization model
    """

    def __init__(
        self,
        similarity_weights: Optional[Dict[str, float]] = None,
        ranking_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize recommender with configurable weights.

        Args:
            similarity_weights: {'text': 0.6, 'features': 0.4} - default
            ranking_weights: {'similarity': 0.7, 'risk': 0.3} - default
        """
        self.similarity_weights = similarity_weights or {'text': 0.6, 'features': 0.4}
        self.ranking_weights = ranking_weights or {'similarity': 0.7, 'risk': 0.3}
        self.vectorizer = None

        # Material keyword dictionary (expand as needed)
        self.material_keywords = {
            'peek', 'titanium', 'stainless steel', 'nitinol', 'cobalt chromium',
            'polyethylene', 'polypropylene', 'silicone', 'latex', 'polyurethane',
            'ptfe', 'eptfe', 'dacron', 'nylon', 'polycarbonate', 'pvc',
            'ceramic', 'zirconia', 'alumina', 'carbon fiber', 'tungsten'
        }

        # Standards keyword patterns
        self.standards_patterns = [
            r'ISO\s+\d+(-\d+)*',
            r'IEC\s+\d+(-\d+)*',
            r'ASTM\s+[A-Z]\d+',
            r'AAMI\s+[A-Z]+\d+'
        ]

    # ========================================================================
    # STAGE 1: CANDIDATE FILTERING
    # ========================================================================

    def filter_candidates(
        self,
        subject_device: Dict[str, Any],
        all_predicates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply mandatory filters to reduce candidate pool.

        Filters:
        1. Product code exact match (mandatory)
        2. Remove EXTREME_OUTLIER MAUDE classification
        3. Remove NOT_RECOMMENDED acceptability (≥2 recalls)
        4. Remove devices > 15 years old
        5. Remove non-API-validated devices

        Args:
            subject_device: Device profile dict from device_profile.json
            all_predicates: Full enriched predicate pool from batchfetch

        Returns:
            Filtered candidate list (typically 50-300 devices)

        Example:
            candidates = recommender.filter_candidates(subject_device, all_predicates)
            # Input: 2000 devices → Output: 287 devices
        """
        subject_product_code = subject_device.get('product_code', '')
        current_year = datetime.now().year

        candidates = []

        for predicate in all_predicates:
            # Filter 1: Product code EXACT MATCH
            if predicate.get('PRODUCTCODE', '') != subject_product_code:
                continue

            # Filter 2: Remove EXTREME OUTLIERS
            if predicate.get('maude_classification') == 'EXTREME_OUTLIER':
                continue

            # Filter 3: Remove NOT_RECOMMENDED
            if predicate.get('predicate_acceptability') == 'NOT_RECOMMENDED':
                continue

            # Filter 4: Age limit (15 years)
            try:
                clearance_date = predicate.get('DECISIONDATE', '')
                clearance_year = int(clearance_date[:4])
                age_years = current_year - clearance_year
                if age_years > 15:
                    continue
            except (ValueError, IndexError):
                continue  # Skip if date parsing fails

            # Filter 5: API validation
            if predicate.get('api_validated') != 'Yes':
                continue

            candidates.append(predicate)

        return candidates

    # ========================================================================
    # STAGE 2: SIMILARITY SCORING
    # ========================================================================

    def calculate_text_similarity(
        self,
        subject_text: str,
        predicate_texts: List[str]
    ) -> np.ndarray:
        """
        Calculate TF-IDF cosine similarity between subject and predicates.

        Args:
            subject_text: Combined text from subject device (intended use + description)
            predicate_texts: List of combined texts from predicates

        Returns:
            Array of similarity scores (0.0-1.0) for each predicate

        Example:
            subject = "Device indicated for coronary artery catheterization..."
            predicates = ["Catheter for coronary use...", "Orthopedic implant..."]
            scores = recommender.calculate_text_similarity(subject, predicates)
            # Returns: [0.89, 0.12]
        """
        corpus = [subject_text] + predicate_texts

        self.vectorizer = TfidfVectorizer(
            max_features=200,        # Limit vocabulary to top 200 terms
            ngram_range=(1, 2),      # Unigrams + bigrams
            stop_words='english',    # Remove "the", "and", etc.
            min_df=1,                # Keep rare terms (small corpus)
            lowercase=True,
            strip_accents='unicode'
        )

        try:
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            subject_vector = tfidf_matrix[0:1]
            predicate_vectors = tfidf_matrix[1:]

            similarities = cosine_similarity(subject_vector, predicate_vectors)[0]
            return similarities

        except Exception as e:
            # Fallback: return zeros if vectorization fails
            print(f"Warning: Text similarity failed ({e}). Using zeros.")
            return np.zeros(len(predicate_texts))

    def extract_sterilization(self, predicate: Dict[str, Any]) -> str:
        """
        Extract sterilization method from predicate text.

        Args:
            predicate: Enriched predicate dict

        Returns:
            Sterilization method string ('ethylene_oxide', 'radiation', 'steam', 'non_sterile', '')

        Example:
            method = recommender.extract_sterilization(predicate)
            # "Device is sterilized via ethylene oxide..." → 'ethylene_oxide'
        """
        decision_text = predicate.get('decision_description', '').lower()
        summary_text = predicate.get('statement_or_summary', '').lower()
        combined = decision_text + ' ' + summary_text

        # Priority order: specific to general
        if 'ethylene oxide' in combined or ' eo ' in combined or 'eto' in combined:
            return 'ethylene_oxide'
        elif 'gamma' in combined or 'e-beam' in combined or 'radiation' in combined:
            return 'radiation'
        elif 'steam' in combined or 'autoclave' in combined:
            return 'steam'
        elif 'non-sterile' in combined or 'nonsterile' in combined or 'not sterile' in combined:
            return 'non_sterile'

        return ''

    def extract_materials(self, predicate: Dict[str, Any]) -> set:
        """
        Extract materials from predicate text using keyword matching.

        Args:
            predicate: Enriched predicate dict

        Returns:
            Set of material names found in text

        Example:
            materials = recommender.extract_materials(predicate)
            # "Device made of titanium and PEEK..." → {'titanium', 'peek'}
        """
        decision_text = predicate.get('decision_description', '').lower()
        summary_text = predicate.get('statement_or_summary', '').lower()
        combined = decision_text + ' ' + summary_text

        found_materials = set()
        for material in self.material_keywords:
            if material in combined:
                found_materials.add(material)

        return found_materials

    def extract_standards(self, predicate: Dict[str, Any]) -> set:
        """
        Extract ISO/IEC/ASTM standards from predicate text.

        Args:
            predicate: Enriched predicate dict

        Returns:
            Set of standards found (e.g., {'ISO 10993-1', 'ISO 11135'})

        Example:
            standards = recommender.extract_standards(predicate)
            # "Testing per ISO 10993-1 and ISO 11135..." → {'ISO 10993-1', 'ISO 11135'}
        """
        decision_text = predicate.get('decision_description', '')
        summary_text = predicate.get('statement_or_summary', '')
        combined = decision_text + ' ' + summary_text

        found_standards = set()
        for pattern in self.standards_patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            for match in matches:
                found_standards.add(match.upper())

        return found_standards

    def sterilization_compatible(self, method1: str, method2: str) -> bool:
        """
        Check if two sterilization methods are compatible (partial credit).

        Args:
            method1: First sterilization method
            method2: Second sterilization method

        Returns:
            True if methods are compatible (both terminal sterilization)

        Example:
            compatible = recommender.sterilization_compatible('ethylene_oxide', 'radiation')
            # Returns: True (both are terminal sterilization methods)
        """
        terminal_methods = {'ethylene_oxide', 'radiation', 'steam'}
        return method1 in terminal_methods and method2 in terminal_methods

    def calculate_feature_similarity(
        self,
        subject_device: Dict[str, Any],
        predicate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate discrete feature similarity score.

        Features:
        - Sterilization method (15 points)
        - Materials overlap (10 points)
        - Standards overlap (5 points)
        - Dimensions/sizes (10 points) - TODO

        Args:
            subject_device: Device profile dict
            predicate: Enriched predicate dict

        Returns:
            Dict with feature_similarity_score (0-100) and breakdown

        Example:
            result = recommender.calculate_feature_similarity(subject_device, predicate)
            # Returns: {
            #   'feature_similarity_score': 28.5,
            #   'sterilization_score': 15.0,
            #   'materials_score': 8.5,
            #   'standards_score': 5.0,
            #   'dimensions_score': 0.0
            # }
        """
        score = 0.0
        breakdown = {}

        # 1. Sterilization Method (15 points)
        subject_sterilization = subject_device.get('sterilization_method', '').lower()
        predicate_sterilization = self.extract_sterilization(predicate)

        if subject_sterilization and predicate_sterilization:
            if subject_sterilization == predicate_sterilization:
                sterilization_score = 15.0
            elif self.sterilization_compatible(subject_sterilization, predicate_sterilization):
                sterilization_score = 7.5  # Partial credit
            else:
                sterilization_score = 0.0
        else:
            sterilization_score = 0.0

        score += sterilization_score
        breakdown['sterilization_score'] = sterilization_score
        breakdown['sterilization_match'] = predicate_sterilization if sterilization_score > 0 else 'none'

        # 2. Materials Overlap (10 points) - Jaccard similarity
        subject_materials = set([m.lower() for m in subject_device.get('materials', [])])
        predicate_materials = self.extract_materials(predicate)

        if subject_materials and predicate_materials:
            overlap = len(subject_materials & predicate_materials)
            total = len(subject_materials | predicate_materials)
            jaccard = overlap / total if total > 0 else 0
            materials_score = jaccard * 10.0
        else:
            materials_score = 0.0
            jaccard = 0.0

        score += materials_score
        breakdown['materials_score'] = materials_score
        breakdown['materials_overlap'] = f"{len(subject_materials & predicate_materials)}/{len(subject_materials | predicate_materials)}" if subject_materials or predicate_materials else 'none'

        # 3. Standards Overlap (5 points)
        subject_standards = set(subject_device.get('standards_referenced', []))
        predicate_standards = self.extract_standards(predicate)

        if subject_standards and predicate_standards:
            overlap = len(subject_standards & predicate_standards)
            total = len(subject_standards)
            overlap_ratio = overlap / total if total > 0 else 0
            standards_score = overlap_ratio * 5.0
        else:
            standards_score = 0.0

        score += standards_score
        breakdown['standards_score'] = standards_score
        breakdown['standards_overlap'] = f"{len(subject_standards & predicate_standards)}/{len(subject_standards)}" if subject_standards else 'none'

        # 4. Dimensions/Sizes (10 points) - TODO: Implement size extraction
        dimensions_score = 0.0
        breakdown['dimensions_score'] = dimensions_score
        breakdown['dimensions_match'] = 'not_implemented'

        breakdown['feature_similarity_score'] = round(score, 2)
        return breakdown

    def calculate_similarity_score(
        self,
        subject_device: Dict[str, Any],
        predicate: Dict[str, Any],
        text_similarity: float
    ) -> Dict[str, Any]:
        """
        Calculate combined similarity score (text + features).

        Args:
            subject_device: Device profile dict
            predicate: Enriched predicate dict
            text_similarity: Pre-calculated text similarity (0.0-1.0)

        Returns:
            Dict with similarity_score (0-100) and breakdown

        Example:
            result = recommender.calculate_similarity_score(subject, predicate, 0.89)
            # Returns: {'similarity_score': 85.3, 'text_score': 89.0, 'feature_score': 28.5, ...}
        """
        text_score = text_similarity * 100  # Convert to 0-100 scale

        feature_result = self.calculate_feature_similarity(subject_device, predicate)
        feature_score = feature_result['feature_similarity_score']

        # Weighted combination (60% text + 40% features)
        combined_score = (text_score * self.similarity_weights['text']) + \
                        (feature_score * self.similarity_weights['features'])

        return {
            'similarity_score': round(combined_score, 2),
            'text_score': round(text_score, 2),
            'feature_score': round(feature_score, 2),
            **feature_result  # Include feature breakdown
        }

    # ========================================================================
    # STAGE 3: RISK SCORING
    # ========================================================================

    def calculate_risk_score(self, predicate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate regulatory risk score (0-100, higher is better).

        Risk factors (penalties):
        - Recalls: -15 pts per recall (max -30)
        - MAUDE CONCERNING: -15 pts
        - MAUDE EXTREME_OUTLIER: -25 pts
        - Clinical data required: -20 pts (YES), -10 pts (PROBABLE)
        - Age > 10 years: -2 pts per year over 10 (max -15)
        - Special controls: -10 pts

        Bonuses:
        - Age ≤ 2 years: +10 pts
        - Age 3-5 years: +5 pts
        - MAUDE EXCELLENT: +10 pts
        - MAUDE GOOD: +5 pts
        - No clinical data: +5 pts
        - No recalls: +5 pts

        Args:
            predicate: Enriched predicate dict

        Returns:
            Dict with risk_score (0-100) and penalty/bonus breakdown

        Example:
            result = recommender.calculate_risk_score(predicate)
            # Returns: {
            #   'risk_score': 75.0,
            #   'penalties': ['1 recall (-15 pts)', '12 years old (-4 pts)'],
            #   'bonuses': ['MAUDE GOOD (+5 pts)', 'No clinical data (+5 pts)']
            # }
        """
        risk_score = 100.0
        penalties = []
        bonuses = []

        # ===== PENALTIES =====

        # 1. Recall History (-30 points max)
        recalls_total = predicate.get('recalls_total', 0)
        if isinstance(recalls_total, int):
            if recalls_total == 1:
                risk_score -= 15
                penalties.append('1 recall (-15 pts)')
            elif recalls_total >= 2:
                risk_score -= 30
                penalties.append(f'{recalls_total} recalls (-30 pts)')

        # 2. MAUDE Classification (-25 points max)
        maude_class = predicate.get('maude_classification', '')
        if maude_class == 'CONCERNING':
            risk_score -= 15
            penalties.append('MAUDE CONCERNING (-15 pts)')
        elif maude_class == 'EXTREME_OUTLIER':
            risk_score -= 25
            penalties.append('MAUDE EXTREME_OUTLIER (-25 pts)')

        # 3. Clinical Data Requirements (-20 points max)
        clinical_history = predicate.get('predicate_clinical_history', 'NO')
        if clinical_history == 'YES':
            risk_score -= 20
            penalties.append('Clinical data required (-20 pts)')
        elif clinical_history == 'PROBABLE':
            risk_score -= 10
            penalties.append('Probable clinical data (-10 pts)')

        # 4. Clearance Age (-15 points max)
        try:
            clearance_year = int(predicate.get('DECISIONDATE', '2025')[:4])
            age_years = datetime.now().year - clearance_year
            if age_years > 10:
                penalty = min((age_years - 10) * 2, 15)
                risk_score -= penalty
                penalties.append(f'{age_years} years old (-{penalty:.0f} pts)')
        except (ValueError, IndexError):
            age_years = 0

        # 5. Special Controls (-10 points)
        if predicate.get('special_controls_applicable') == 'YES':
            risk_score -= 10
            penalties.append('Special controls (-10 pts)')

        # ===== BONUSES =====

        # 1. Recent Clearance (+10 points max)
        if age_years <= 2:
            bonus = 10
            risk_score += bonus
            bonuses.append(f'Recent clearance ({age_years}y, +{bonus} pts)')
        elif age_years <= 5:
            bonus = 5
            risk_score += bonus
            bonuses.append(f'Recent clearance ({age_years}y, +{bonus} pts)')

        # 2. Excellent MAUDE Profile (+10 points)
        if maude_class == 'EXCELLENT':
            bonus = 10
            risk_score += bonus
            bonuses.append('MAUDE EXCELLENT (+10 pts)')
        elif maude_class == 'GOOD':
            bonus = 5
            risk_score += bonus
            bonuses.append('MAUDE GOOD (+5 pts)')

        # 3. No Clinical Data (+5 points)
        if clinical_history == 'NO':
            bonus = 5
            risk_score += bonus
            bonuses.append('No clinical data (+5 pts)')

        # 4. No Recalls Ever (+5 points)
        if recalls_total == 0:
            bonus = 5
            risk_score += bonus
            bonuses.append('No recalls (+5 pts)')

        # Clamp to 0-100 range
        risk_score = max(0, min(100, risk_score))

        return {
            'risk_score': round(risk_score, 2),
            'penalties': penalties,
            'bonuses': bonuses,
            'recalls_total': recalls_total,
            'maude_classification': maude_class,
            'clinical_data_required': clinical_history,
            'age_years': age_years,
            'predicate_acceptability': predicate.get('predicate_acceptability', 'UNKNOWN')
        }

    # ========================================================================
    # FINAL RANKING
    # ========================================================================

    def calculate_final_score(
        self,
        similarity_score: float,
        risk_score: float
    ) -> float:
        """
        Calculate final recommendation score.

        Formula: (similarity * 0.7) + (risk * 0.3)

        Rationale:
        - Similarity dominates (70%) - device must be technologically similar
        - Risk is tie-breaker (30%) - among similar devices, choose safer one

        Args:
            similarity_score: Similarity score (0-100)
            risk_score: Risk score (0-100)

        Returns:
            Final score (0-100)

        Example:
            final = recommender.calculate_final_score(85.3, 75.0)
            # Returns: 82.21 = (85.3 * 0.7) + (75.0 * 0.3)
        """
        final = (similarity_score * self.ranking_weights['similarity']) + \
                (risk_score * self.ranking_weights['risk'])
        return round(final, 2)

    # ========================================================================
    # MAIN RECOMMENDATION PIPELINE
    # ========================================================================

    def recommend_predicates(
        self,
        subject_device: Dict[str, Any],
        candidate_pool: List[Dict[str, Any]],
        top_n: int = 5
    ) -> Dict[str, Any]:
        """
        Generate top-N predicate recommendations.

        Pipeline:
        1. Filter candidates (product code, MAUDE, recalls, age)
        2. Calculate text similarity (TF-IDF batch processing)
        3. Calculate feature similarity (sterilization, materials, standards)
        4. Calculate risk scores (recalls, MAUDE, clinical data, age)
        5. Combine scores and rank
        6. Return top N with detailed breakdown

        Args:
            subject_device: Device profile dict from device_profile.json
            candidate_pool: List of enriched predicate dicts from batchfetch
            top_n: Number of recommendations to return (default: 5)

        Returns:
            Dict with recommendations, search summary, and metadata

        Example:
            recommendations = recommender.recommend_predicates(subject, predicates, top_n=5)
            print(recommendations['recommendations'][0]['final_score'])  # 87.4
        """
        start_time = datetime.now()

        # ===== STAGE 1: FILTER CANDIDATES =====
        candidates = self.filter_candidates(subject_device, candidate_pool)

        if len(candidates) == 0:
            return {
                'subject_device': subject_device,
                'recommendations': [],
                'search_summary': {
                    'total_searched': len(candidate_pool),
                    'after_filtering': 0,
                    'scored_candidates': 0,
                    'recommendation_count': 0,
                    'error': 'No candidates passed filtering criteria'
                },
                'generation_time_seconds': (datetime.now() - start_time).total_seconds()
            }

        # ===== STAGE 2: TEXT SIMILARITY (BATCH PROCESSING) =====

        # Prepare subject text
        subject_text = ' '.join([
            subject_device.get('intended_use', ''),
            subject_device.get('device_description', ''),
            subject_device.get('indications_for_use', '')
        ])

        # Prepare predicate texts
        predicate_texts = []
        for pred in candidates:
            pred_text = ' '.join([
                pred.get('DEVICENAME', ''),
                pred.get('decision_description', ''),
                pred.get('statement_or_summary', '')
            ])
            predicate_texts.append(pred_text)

        # Batch TF-IDF calculation
        text_similarities = self.calculate_text_similarity(subject_text, predicate_texts)

        # ===== STAGE 3: SCORE ALL CANDIDATES =====

        scored_candidates = []

        for i, predicate in enumerate(candidates):
            # Similarity score (text + features)
            similarity_result = self.calculate_similarity_score(
                subject_device,
                predicate,
                text_similarities[i]
            )

            # Risk score
            risk_result = self.calculate_risk_score(predicate)

            # Final score
            final_score = self.calculate_final_score(
                similarity_result['similarity_score'],
                risk_result['risk_score']
            )

            scored_candidates.append({
                'rank': 0,  # Will be set after sorting
                'k_number': predicate.get('KNUMBER', ''),
                'device_name': predicate.get('DEVICENAME', ''),
                'applicant': predicate.get('APPLICANT', ''),
                'clearance_date': predicate.get('DECISIONDATE', ''),
                'final_score': final_score,
                'similarity_breakdown': similarity_result,
                'risk_breakdown': risk_result,
                'predicate': predicate  # Include full predicate data
            })

        # ===== STAGE 4: RANK AND SELECT TOP N =====

        ranked = sorted(scored_candidates, key=lambda x: x['final_score'], reverse=True)

        # Assign ranks
        for i, candidate in enumerate(ranked):
            candidate['rank'] = i + 1

        top_recommendations = ranked[:top_n]

        # ===== RETURN RESULTS =====

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            'subject_device': {
                'product_code': subject_device.get('product_code', ''),
                'device_name': subject_device.get('device_name', ''),
                'intended_use_snippet': subject_device.get('intended_use', '')[:150] + '...'
            },
            'recommendations': top_recommendations,
            'search_summary': {
                'total_predicates_searched': len(candidate_pool),
                'after_filtering': len(candidates),
                'scored_candidates': len(scored_candidates),
                'recommendation_count': len(top_recommendations)
            },
            'generation_time_seconds': round(duration, 2),
            'algorithm_version': '1.0.0',
            'generated_at': end_time.isoformat()
        }

    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================

    def load_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Load enriched CSV file into list of dicts.

        Args:
            csv_path: Path to 510k_download_enriched.csv

        Returns:
            List of predicate dicts

        Example:
            predicates = recommender.load_csv('510k_download_enriched.csv')
        """
        predicates = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                if 'recalls_total' in row:
                    try:
                        row['recalls_total'] = int(row['recalls_total'])
                    except ValueError:
                        row['recalls_total'] = 0

                predicates.append(row)
        return predicates

    def export_json(self, recommendations: Dict[str, Any], output_path: str):
        """
        Export recommendations to JSON file.

        Args:
            recommendations: Output from recommend_predicates()
            output_path: Path to output JSON file

        Example:
            recommender.export_json(recommendations, 'predicate_recommendations.json')
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, indent=2)

        print(f"✓ JSON export saved: {output_path}")

    def export_markdown(self, recommendations: Dict[str, Any], output_path: str):
        """
        Export recommendations to Markdown report.

        Args:
            recommendations: Output from recommend_predicates()
            output_path: Path to output .md file

        Example:
            recommender.export_markdown(recommendations, 'predicate_recommendations.md')
        """
        md_lines = []

        # Header
        md_lines.append("# Smart Predicate Recommendations\n")
        md_lines.append(f"**Subject Device:** {recommendations['subject_device']['device_name']} ({recommendations['subject_device']['product_code']})\n")
        md_lines.append(f"**Generated:** {recommendations['generated_at']}\n")
        md_lines.append(f"**Candidates Analyzed:** {recommendations['search_summary']['scored_candidates']} devices\n")
        md_lines.append(f"**Processing Time:** {recommendations['generation_time_seconds']} seconds\n")
        md_lines.append("\n---\n")

        # Top Recommendations
        md_lines.append("## Top 5 Recommended Predicates\n")

        for rec in recommendations['recommendations']:
            rank = rec['rank']
            k_number = rec['k_number']
            device_name = rec['device_name']
            applicant = rec['applicant']
            clearance_date = rec['clearance_date']
            final_score = rec['final_score']

            sim = rec['similarity_breakdown']
            risk = rec['risk_breakdown']

            # Recommendation level
            if rank == 1:
                rec_level = "⭐ PRIMARY PREDICATE"
            elif rank <= 3:
                rec_level = "⭐ SECONDARY PREDICATE"
            else:
                rec_level = "ALTERNATIVE"

            md_lines.append(f"\n### {rank}. {k_number} - {device_name} (Score: {final_score}/100)\n")
            md_lines.append(f"**Applicant:** {applicant}\n")
            md_lines.append(f"**Clearance:** {clearance_date}\n")
            md_lines.append(f"**Recommendation:** {rec_level}\n\n")

            md_lines.append("**Why this predicate:**\n")
            md_lines.append(f"- Technological similarity: {sim['similarity_score']:.1f}%\n")
            md_lines.append(f"  - Text similarity: {sim['text_score']:.1f}%\n")
            md_lines.append(f"  - Feature similarity: {sim['feature_score']:.1f}%\n")
            md_lines.append(f"- Risk score: {risk['risk_score']:.1f}/100\n")

            if risk['bonuses']:
                md_lines.append(f"- Bonuses: {'; '.join(risk['bonuses'])}\n")
            if risk['penalties']:
                md_lines.append(f"- Penalties: {'; '.join(risk['penalties'])}\n")

            md_lines.append("\n**Similarity Details:**\n")
            md_lines.append(f"- Sterilization: {sim.get('sterilization_match', 'unknown')}\n")
            md_lines.append(f"- Materials overlap: {sim.get('materials_overlap', 'unknown')}\n")
            md_lines.append(f"- Standards overlap: {sim.get('standards_overlap', 'unknown')}\n")

            md_lines.append("\n**Risk Assessment:**\n")
            md_lines.append(f"- Recalls: {risk['recalls_total']}\n")
            md_lines.append(f"- MAUDE classification: {risk['maude_classification']}\n")
            md_lines.append(f"- Clinical data required: {risk['clinical_data_required']}\n")
            md_lines.append(f"- Age: {risk['age_years']} years\n")
            md_lines.append(f"- Acceptability: {risk['predicate_acceptability']}\n")

            md_lines.append("\n---\n")

        # Search Summary
        md_lines.append("\n## Search Summary\n")
        summary = recommendations['search_summary']
        md_lines.append(f"- **Total devices in product code:** {summary['total_predicates_searched']:,}\n")
        md_lines.append(f"- **After mandatory filtering:** {summary['after_filtering']} candidates\n")
        md_lines.append(f"- **Scored candidates:** {summary['scored_candidates']}\n")
        md_lines.append(f"- **Top recommendations:** {summary['recommendation_count']}\n")

        # Disclaimer
        md_lines.append("\n---\n")
        md_lines.append("\n## Disclaimer\n")
        md_lines.append("This recommendation is generated by automated analysis of FDA public data. ")
        md_lines.append("Final predicate selection must be reviewed and approved by qualified Regulatory Affairs professionals. ")
        md_lines.append("Verify all cited information against current FDA databases before submission.\n")

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(md_lines)

        print(f"✓ Markdown report saved: {output_path}")


# ========================================================================
# COMMAND-LINE INTERFACE (OPTIONAL)
# ========================================================================

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python3 predicate_recommender.py <device_profile.json> <enriched_csv> [top_n]")
        sys.exit(1)

    device_profile_path = sys.argv[1]
    enriched_csv_path = sys.argv[2]
    top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    # Load inputs
    with open(device_profile_path, 'r') as f:
        subject_device = json.load(f)

    recommender = PredicateRecommender()
    predicates = recommender.load_csv(enriched_csv_path)

    # Generate recommendations
    print(f"Analyzing {len(predicates)} predicates for {subject_device.get('device_name', 'Unknown Device')}...")

    recommendations = recommender.recommend_predicates(subject_device, predicates, top_n)

    # Export results
    output_dir = '.'
    recommender.export_json(recommendations, f'{output_dir}/predicate_recommendations.json')
    recommender.export_markdown(recommendations, f'{output_dir}/predicate_recommendations.md')

    # Print summary
    print(f"\n✓ Analysis complete in {recommendations['generation_time_seconds']} seconds")
    print(f"✓ Top recommendation: {recommendations['recommendations'][0]['k_number']} (score: {recommendations['recommendations'][0]['final_score']}/100)")
```

---

## Testing Strategy

### Test File: test_predicate_recommender.py

```python
"""
Unit tests for PredicateRecommender.

Run with: pytest tests/test_predicate_recommender.py -v
"""

import pytest
from lib.predicate_recommender import PredicateRecommender
import json


class TestCandidateFiltering:
    """Test Stage 1: Candidate Filtering"""

    def test_product_code_filter(self):
        """Test that only matching product codes pass through."""
        recommender = PredicateRecommender()

        subject = {'product_code': 'DQY'}
        predicates = [
            {'PRODUCTCODE': 'DQY', 'api_validated': 'Yes', 'DECISIONDATE': '2024-01-01'},
            {'PRODUCTCODE': 'OVE', 'api_validated': 'Yes', 'DECISIONDATE': '2024-01-01'},
            {'PRODUCTCODE': 'DQY', 'api_validated': 'Yes', 'DECISIONDATE': '2024-01-01'}
        ]

        filtered = recommender.filter_candidates(subject, predicates)

        assert len(filtered) == 2
        assert all(p['PRODUCTCODE'] == 'DQY' for p in filtered)

    def test_extreme_outlier_filter(self):
        """Test that EXTREME_OUTLIER MAUDE devices are excluded."""
        recommender = PredicateRecommender()

        subject = {'product_code': 'DQY'}
        predicates = [
            {'PRODUCTCODE': 'DQY', 'maude_classification': 'EXCELLENT', 'api_validated': 'Yes', 'DECISIONDATE': '2024-01-01'},
            {'PRODUCTCODE': 'DQY', 'maude_classification': 'EXTREME_OUTLIER', 'api_validated': 'Yes', 'DECISIONDATE': '2024-01-01'}
        ]

        filtered = recommender.filter_candidates(subject, predicates)

        assert len(filtered) == 1
        assert filtered[0]['maude_classification'] == 'EXCELLENT'

    def test_not_recommended_filter(self):
        """Test that NOT_RECOMMENDED predicates are excluded."""
        recommender = PredicateRecommender()

        subject = {'product_code': 'DQY'}
        predicates = [
            {'PRODUCTCODE': 'DQY', 'predicate_acceptability': 'ACCEPTABLE', 'api_validated': 'Yes', 'DECISIONDATE': '2024-01-01'},
            {'PRODUCTCODE': 'DQY', 'predicate_acceptability': 'NOT_RECOMMENDED', 'api_validated': 'Yes', 'DECISIONDATE': '2024-01-01'}
        ]

        filtered = recommender.filter_candidates(subject, predicates)

        assert len(filtered) == 1
        assert filtered[0]['predicate_acceptability'] == 'ACCEPTABLE'

    def test_age_filter(self):
        """Test that devices > 15 years old are excluded."""
        recommender = PredicateRecommender()

        subject = {'product_code': 'DQY'}
        predicates = [
            {'PRODUCTCODE': 'DQY', 'DECISIONDATE': '2024-01-01', 'api_validated': 'Yes'},
            {'PRODUCTCODE': 'DQY', 'DECISIONDATE': '2000-01-01', 'api_validated': 'Yes'}  # 26 years old
        ]

        filtered = recommender.filter_candidates(subject, predicates)

        assert len(filtered) == 1
        assert '2024' in filtered[0]['DECISIONDATE']


class TestTextSimilarity:
    """Test Stage 2a: Text Similarity"""

    def test_identical_text(self):
        """Test that identical text returns similarity ~1.0."""
        recommender = PredicateRecommender()

        subject_text = "Device indicated for coronary artery catheterization in patients with heart disease"
        predicate_texts = [subject_text]

        similarities = recommender.calculate_text_similarity(subject_text, predicate_texts)

        assert similarities[0] > 0.95  # Should be very high

    def test_similar_text(self):
        """Test that similar text returns high similarity."""
        recommender = PredicateRecommender()

        subject_text = "Catheter for coronary artery procedures in cardiac patients"
        predicate_texts = [
            "Device for coronary catheterization in heart disease patients",
            "Orthopedic implant for spinal fusion surgery"
        ]

        similarities = recommender.calculate_text_similarity(subject_text, predicate_texts)

        assert similarities[0] > 0.5  # Similar text
        assert similarities[1] < 0.3  # Dissimilar text (ortho vs cardio)

    def test_empty_text(self):
        """Test graceful handling of empty text."""
        recommender = PredicateRecommender()

        subject_text = ""
        predicate_texts = ["Device description here"]

        similarities = recommender.calculate_text_similarity(subject_text, predicate_texts)

        assert len(similarities) == 1
        assert similarities[0] >= 0  # Should not crash


class TestFeatureSimilarity:
    """Test Stage 2b: Feature Similarity"""

    def test_sterilization_exact_match(self):
        """Test exact sterilization method match."""
        recommender = PredicateRecommender()

        subject = {'sterilization_method': 'ethylene_oxide'}
        predicate = {'decision_description': 'Device is sterilized via ethylene oxide'}

        result = recommender.calculate_feature_similarity(subject, predicate)

        assert result['sterilization_score'] == 15.0

    def test_materials_overlap(self):
        """Test materials Jaccard similarity."""
        recommender = PredicateRecommender()

        subject = {'materials': ['titanium', 'PEEK']}
        predicate = {'decision_description': 'Device made of titanium and PEEK'}

        result = recommender.calculate_feature_similarity(subject, predicate)

        assert result['materials_score'] == 10.0  # Perfect overlap

    def test_standards_overlap(self):
        """Test standards extraction and overlap."""
        recommender = PredicateRecommender()

        subject = {'standards_referenced': ['ISO 10993-1', 'ISO 11135']}
        predicate = {'decision_description': 'Tested per ISO 10993-1 and ISO 11135'}

        result = recommender.calculate_feature_similarity(subject, predicate)

        assert result['standards_score'] == 5.0  # Perfect overlap


class TestRiskScoring:
    """Test Stage 3: Risk Scoring"""

    def test_no_recalls_bonus(self):
        """Test bonus for zero recalls."""
        recommender = PredicateRecommender()

        predicate = {
            'recalls_total': 0,
            'maude_classification': 'GOOD',
            'predicate_clinical_history': 'NO',
            'DECISIONDATE': '2024-01-01'
        }

        result = recommender.calculate_risk_score(predicate)

        assert 'No recalls (+5 pts)' in result['bonuses']
        assert result['risk_score'] > 100  # Bonuses should push above base

    def test_recalls_penalty(self):
        """Test penalty for recalls."""
        recommender = PredicateRecommender()

        predicate = {
            'recalls_total': 2,
            'maude_classification': 'AVERAGE',
            'predicate_clinical_history': 'NO',
            'DECISIONDATE': '2024-01-01'
        }

        result = recommender.calculate_risk_score(predicate)

        assert '2 recalls (-30 pts)' in result['penalties']
        assert result['risk_score'] < 100

    def test_clinical_data_penalty(self):
        """Test penalty for clinical data requirements."""
        recommender = PredicateRecommender()

        predicate = {
            'recalls_total': 0,
            'maude_classification': 'GOOD',
            'predicate_clinical_history': 'YES',
            'DECISIONDATE': '2024-01-01'
        }

        result = recommender.calculate_risk_score(predicate)

        assert 'Clinical data required (-20 pts)' in result['penalties']


class TestEndToEnd:
    """Test full recommendation pipeline."""

    def test_recommendation_pipeline(self):
        """Test complete recommendation workflow."""
        recommender = PredicateRecommender()

        subject_device = {
            'product_code': 'DQY',
            'device_name': 'Test Catheter',
            'intended_use': 'Device for coronary artery catheterization',
            'device_description': 'Sterile catheter with radiopaque markers',
            'sterilization_method': 'ethylene_oxide',
            'materials': ['titanium'],
            'standards_referenced': ['ISO 10993-1']
        }

        predicates = [
            {
                'KNUMBER': 'K123456',
                'PRODUCTCODE': 'DQY',
                'DEVICENAME': 'Similar Catheter',
                'APPLICANT': 'Test Corp',
                'DECISIONDATE': '2024-01-01',
                'decision_description': 'Catheter for coronary use, sterilized via ethylene oxide',
                'statement_or_summary': 'Made of titanium per ISO 10993-1',
                'api_validated': 'Yes',
                'recalls_total': 0,
                'maude_classification': 'EXCELLENT',
                'predicate_clinical_history': 'NO',
                'predicate_acceptability': 'ACCEPTABLE'
            },
            {
                'KNUMBER': 'K999999',
                'PRODUCTCODE': 'DQY',
                'DEVICENAME': 'Different Device',
                'APPLICANT': 'Other Corp',
                'DECISIONDATE': '2010-01-01',
                'decision_description': 'Surgical instrument',
                'statement_or_summary': '',
                'api_validated': 'Yes',
                'recalls_total': 2,
                'maude_classification': 'CONCERNING',
                'predicate_clinical_history': 'YES',
                'predicate_acceptability': 'REVIEW_REQUIRED'
            }
        ]

        recommendations = recommender.recommend_predicates(subject_device, predicates, top_n=2)

        # Assertions
        assert len(recommendations['recommendations']) == 1  # Only 1 passes filters (other fails age/recalls)
        assert recommendations['recommendations'][0]['k_number'] == 'K123456'
        assert recommendations['recommendations'][0]['final_score'] > 70  # Should be high score
        assert recommendations['search_summary']['total_predicates_searched'] == 2
```

---

## Integration with Batchfetch

### Update: commands/batchfetch.md

Add new argument parsing section:

```markdown
## Parse Arguments

From `$ARGUMENTS`, extract:

...existing args...

- `--recommend-predicates` — Generate smart predicate recommendations (requires --enrich)
- `--subject-device PATH` — Path to device_profile.json for recommendation
```

Add new step at end of enrichment workflow:

```markdown
## Step 7: Smart Predicate Recommendations (Optional)

If `--recommend-predicates` flag is set:

```python
if '--recommend-predicates' in arguments:
    if '--subject-device' not in arguments:
        error("--recommend-predicates requires --subject-device PATH")

    from lib.predicate_recommender import PredicateRecommender
    import json

    # Load subject device
    subject_device_path = arguments['--subject-device']
    with open(subject_device_path, 'r') as f:
        subject_device = json.load(f)

    # Initialize recommender
    recommender = PredicateRecommender()

    # Load enriched CSV
    enriched_csv = os.path.join(PROJECT_DIR, '510k_download_enriched.csv')
    predicates = recommender.load_csv(enriched_csv)

    # Generate recommendations
    print("\n🤖 Generating smart predicate recommendations...")
    recommendations = recommender.recommend_predicates(subject_device, predicates, top_n=5)

    # Export results
    recommender.export_json(
        recommendations,
        os.path.join(PROJECT_DIR, 'predicate_recommendations.json')
    )
    recommender.export_markdown(
        recommendations,
        os.path.join(PROJECT_DIR, 'predicate_recommendations.md')
    )

    print(f"\n✓ Recommendations saved:")
    print(f"  - {PROJECT_DIR}/predicate_recommendations.json")
    print(f"  - {PROJECT_DIR}/predicate_recommendations.md")
    print(f"\n🏆 Top recommendation: {recommendations['recommendations'][0]['k_number']}")
    print(f"    Score: {recommendations['recommendations'][0]['final_score']}/100")
```
```

---

## Performance Benchmarks

### Expected Performance (MacBook Pro, M1, 16 GB RAM)

| Candidate Pool Size | Filtering | TF-IDF | Scoring | Total |
|---------------------|-----------|--------|---------|-------|
| 50 devices          | 0.1s      | 0.2s   | 0.1s    | 0.4s  |
| 200 devices         | 0.3s      | 0.8s   | 0.4s    | 1.5s  |
| 500 devices         | 0.7s      | 2.1s   | 1.0s    | 3.8s  |
| 1000 devices        | 1.4s      | 5.2s   | 2.1s    | 8.7s  |

### Memory Usage

| Pool Size | TF-IDF Vectors | Total Memory |
|-----------|----------------|--------------|
| 50        | 0.5 MB         | 2 MB         |
| 200       | 2.0 MB         | 5 MB         |
| 500       | 5.0 MB         | 12 MB        |
| 1000      | 10.0 MB        | 22 MB        |

---

## Deployment Checklist

- [ ] Install dependencies: `pip install scikit-learn numpy`
- [ ] Create `lib/predicate_recommender.py`
- [ ] Create `tests/test_predicate_recommender.py`
- [ ] Update `commands/batchfetch.md` with --recommend-predicates
- [ ] Run tests: `pytest tests/test_predicate_recommender.py -v`
- [ ] Test on Round 1/Round 2 device archetypes
- [ ] Manual validation: RA professional reviews 10 test cases
- [ ] Update user documentation
- [ ] Add to release announcement

---

## Future Optimization Ideas

1. **Caching TF-IDF Vectors:** Pre-compute vectors for predicate pool, reuse across queries
2. **Parallel Processing:** Use multiprocessing.Pool for similarity calculations
3. **Early Stopping:** Skip similarity calculation if risk score disqualifies
4. **Incremental Vectorization:** Add new predicates to existing TF-IDF model
5. **GPU Acceleration:** Use cuML for TF-IDF on large pools (1000+ devices)

---

**Document Version:** 1.0
**Ready for Implementation:** Yes
**Estimated Completion:** 10 hours
**Dependencies:** scikit-learn, numpy
**Testing Coverage Target:** 80% (pytest)
