"""
Predicate Diversity Analyzer for FDA 510(k) Submissions

This module analyzes predicate device diversity to identify "echo chamber" risk
where all predicates are too similar (same manufacturer, same technology, narrow
time range). FDA may question SE arguments that rely on a non-diverse predicate set.

Sprint 6 Feature 2: Predicate Diversity Scorecard (91.3 → 92.8 expert rating)

Author: Claude Code (Anthropic)
Date: 2026-02-14
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import Counter
import re


class PredicateDiversityAnalyzer:
    """
    Analyze predicate device set for diversity across 5 dimensions:
    1. Manufacturer diversity (0-30 points)
    2. Technology diversity (0-30 points)
    3. Age diversity (0-25 points)
    4. Regulatory pathway diversity (0-10 points)
    5. Geographic diversity (0-10 points)

    Total score: 0-100 points
    Grading: 80-100 EXCELLENT, 60-79 GOOD, 40-59 FAIR, 0-39 POOR
    """

    def __init__(self, predicates: List[Dict[str, Any]]):
        """
        Initialize analyzer with predicate device list.

        Args:
            predicates: List of predicate device dicts with keys:
                - k_number (str): K-number (e.g., "K123456")
                - manufacturer (str): Manufacturer name
                - device_name (str): Trade name
                - clearance_date (str): Clearance date (YYYY-MM-DD)
                - product_code (str): Product code
                - decision_description (str): Device description
                - review_panel (str): Review panel (optional)
                - contact_country (str): Country (optional)
        """
        self.predicates = predicates
        self.num_predicates = len(predicates)

    def analyze(self) -> Dict[str, Any]:
        """
        Perform full diversity analysis and return scorecard.

        Returns:
            Dict with keys:
                - total_score (int): 0-100 total diversity score
                - manufacturer_score (int): 0-30 manufacturer diversity
                - technology_score (int): 0-30 technology diversity
                - age_score (int): 0-25 age diversity
                - pathway_score (int): 0-10 pathway diversity
                - geographic_score (int): 0-10 geographic diversity
                - grade (str): EXCELLENT/GOOD/FAIR/POOR
                - recommendations (List[str]): Actionable improvements
                - unique_manufacturers (int): Count of unique manufacturers
                - unique_technologies (int): Count of unique technologies
                - clearance_year_span (int): Years from oldest to newest
                - most_recent_year (int): Most recent clearance year
        """
        if self.num_predicates == 0:
            return self._empty_result()

        # Calculate dimension scores
        manufacturer_score, manufacturer_data = self._score_manufacturer_diversity()
        technology_score, technology_data = self._score_technology_diversity()
        age_score, age_data = self._score_age_diversity()
        pathway_score, pathway_data = self._score_pathway_diversity()
        geographic_score, geographic_data = self._score_geographic_diversity()

        # Total score
        total_score = (
            manufacturer_score
            + technology_score
            + age_score
            + pathway_score
            + geographic_score
        )

        # Grade
        grade = self._get_grade(total_score)

        # Recommendations
        recommendations = self._get_recommendations(
            manufacturer_score,
            technology_score,
            age_score,
            pathway_score,
            geographic_score,
            manufacturer_data,
            technology_data,
            age_data,
        )

        return {
            "total_score": total_score,
            "manufacturer_score": manufacturer_score,
            "technology_score": technology_score,
            "age_score": age_score,
            "pathway_score": pathway_score,
            "geographic_score": geographic_score,
            "grade": grade,
            "recommendations": recommendations,
            "unique_manufacturers": manufacturer_data["unique_count"],
            "manufacturer_list": manufacturer_data["unique_list"],
            "unique_technologies": technology_data["unique_count"],
            "technology_list": technology_data["unique_list"],
            "clearance_year_span": age_data["year_span"],
            "most_recent_year": age_data["most_recent_year"],
            "oldest_year": age_data["oldest_year"],
            "pathway_diversity": pathway_data["unique_count"],
            "country_diversity": geographic_data["unique_count"],
        }

    def _score_manufacturer_diversity(self) -> tuple[int, Dict[str, Any]]:
        """
        Score manufacturer diversity (0-30 points).

        Scoring:
        - 1 manufacturer: 0 points (echo chamber risk)
        - 2 manufacturers: 10 points
        - 3 manufacturers: 20 points
        - 4+ manufacturers: 30 points

        Returns:
            (score, metadata_dict)
        """
        manufacturers = [
            p.get("manufacturer", "Unknown").strip()
            for p in self.predicates
            if p.get("manufacturer")
        ]
        unique_manufacturers = list(set(manufacturers))
        unique_count = len(unique_manufacturers)

        if unique_count == 1:
            score = 0
        elif unique_count == 2:
            score = 10
        elif unique_count == 3:
            score = 20
        else:  # 4+
            score = 30

        return score, {
            "unique_count": unique_count,
            "unique_list": sorted(unique_manufacturers),
            "distribution": Counter(manufacturers),
        }

    def _score_technology_diversity(self) -> tuple[int, Dict[str, Any]]:
        """
        Score technology diversity (0-30 points).

        Extract technology keywords from decision_description:
        - Drug-eluting, bare metal, bioresorbable (for stents)
        - Single-use, reusable
        - Powered, manual
        - Different materials, coatings, mechanisms

        Scoring:
        - 1 technology type: 0 points
        - 2 technology types: 10 points
        - 3 technology types: 20 points
        - 4+ technology types: 30 points

        Returns:
            (score, metadata_dict)
        """
        technology_keywords = {
            "drug-eluting": ["drug-eluting", "drug eluting", "paclitaxel", "sirolimus", "everolimus"],
            "bare-metal": ["bare metal", "bare-metal", "uncoated"],
            "bioresorbable": ["bioresorbable", "bioabsorbable", "resorbable", "absorbable"],
            "coated": ["coated", "coating", "hydrophilic"],
            "powered": ["powered", "electric", "electronic", "battery"],
            "manual": ["manual", "non-powered", "passive"],
            "reusable": ["reusable", "reprocessing", "re-use"],
            "single-use": ["single-use", "disposable", "single use"],
            "wireless": ["wireless", "bluetooth", "wi-fi", "telemetry"],
            "implantable": ["implantable", "implant", "permanent"],
            "temporary": ["temporary", "transient", "removable"],
            "robotic": ["robotic", "robot-assisted", "automated"],
            "AI/ML": ["machine learning", "artificial intelligence", "ai-powered", "neural network"],
        }

        detected_technologies = set()

        for predicate in self.predicates:
            description = predicate.get("decision_description", "").lower()
            device_name = predicate.get("device_name", "").lower()
            combined_text = f"{description} {device_name}"

            for tech_name, keywords in technology_keywords.items():
                if any(keyword in combined_text for keyword in keywords):
                    detected_technologies.add(tech_name)

        unique_count = len(detected_technologies)

        if unique_count == 1:
            score = 0
        elif unique_count == 2:
            score = 10
        elif unique_count == 3:
            score = 20
        else:  # 4+
            score = 30

        return score, {
            "unique_count": unique_count,
            "unique_list": sorted(detected_technologies) if detected_technologies else ["generic"],
        }

    def _score_age_diversity(self) -> tuple[int, Dict[str, Any]]:
        """
        Score age diversity (0-25 points).

        Base scoring (0-15 points):
        - <2 year span: 0 points (too narrow)
        - 2-3 year span: 5 points
        - 4-5 year span: 10 points
        - 6+ year span: 15 points

        Bonus for recent predicates (+10 points):
        - Most recent predicate within last 2 years: +10 points
        - Most recent predicate 2-4 years old: +5 points
        - Most recent predicate >4 years old: +0 points

        Total: 0-25 points

        Returns:
            (score, metadata_dict)
        """
        clearance_years = []
        current_year = datetime.now().year

        for predicate in self.predicates:
            date_str = predicate.get("clearance_date", "")
            if date_str:
                # Try parsing YYYY-MM-DD
                match = re.match(r"(\d{4})-\d{2}-\d{2}", date_str)
                if match:
                    clearance_years.append(int(match.group(1)))
                else:
                    # Try parsing YYYY
                    match = re.match(r"(\d{4})", date_str)
                    if match:
                        clearance_years.append(int(match.group(1)))

        if not clearance_years:
            return 0, {
                "year_span": 0,
                "most_recent_year": None,
                "oldest_year": None,
                "years_since_most_recent": None,
            }

        oldest_year = min(clearance_years)
        most_recent_year = max(clearance_years)
        year_span = most_recent_year - oldest_year
        years_since_most_recent = current_year - most_recent_year

        # Base score for year span
        if year_span < 2:
            base_score = 0
        elif year_span <= 3:
            base_score = 5
        elif year_span <= 5:
            base_score = 10
        else:  # 6+
            base_score = 15

        # Bonus for recent predicates
        if years_since_most_recent <= 2:
            recency_bonus = 10
        elif years_since_most_recent <= 4:
            recency_bonus = 5
        else:
            recency_bonus = 0

        total_score = base_score + recency_bonus

        return total_score, {
            "year_span": year_span,
            "most_recent_year": most_recent_year,
            "oldest_year": oldest_year,
            "years_since_most_recent": years_since_most_recent,
            "clearance_years": sorted(clearance_years),
        }

    def _score_pathway_diversity(self) -> tuple[int, Dict[str, Any]]:
        """
        Score regulatory pathway diversity (0-10 points).

        Pathways:
        - Traditional 510(k)
        - Special 510(k)
        - Abbreviated 510(k)
        - De Novo

        Scoring:
        - 1 pathway: 0 points
        - 2+ pathways: 10 points (bonus for including Special or De Novo)

        Returns:
            (score, metadata_dict)
        """
        pathways = set()

        for predicate in self.predicates:
            decision_desc = predicate.get("decision_description", "").lower()
            k_number = predicate.get("k_number", "")

            # Heuristic pathway detection
            if "special 510(k)" in decision_desc or "special" in decision_desc:
                pathways.add("Special 510(k)")
            elif "abbreviated" in decision_desc:
                pathways.add("Abbreviated 510(k)")
            elif k_number.startswith("DEN"):
                pathways.add("De Novo")
            else:
                pathways.add("Traditional 510(k)")

        unique_count = len(pathways)

        if unique_count >= 2:
            score = 10
        else:
            score = 0

        return score, {"unique_count": unique_count, "pathways": sorted(pathways)}

    def _score_geographic_diversity(self) -> tuple[int, Dict[str, Any]]:
        """
        Score geographic diversity (0-10 points).

        Countries of manufacturers:
        - 1 country: 0 points
        - 2+ countries: 10 points

        Returns:
            (score, metadata_dict)
        """
        countries = [
            p.get("contact_country", "Unknown").strip()
            for p in self.predicates
            if p.get("contact_country")
        ]

        if not countries:
            # Default to US if no country data
            countries = ["United States"]

        unique_countries = set(countries)
        unique_count = len(unique_countries)

        if unique_count >= 2:
            score = 10
        else:
            score = 0

        return score, {
            "unique_count": unique_count,
            "countries": sorted(unique_countries),
        }

    def _get_grade(self, total_score: int) -> str:
        """
        Convert total score to letter grade.

        Args:
            total_score: 0-100 total diversity score

        Returns:
            EXCELLENT (80-100), GOOD (60-79), FAIR (40-59), POOR (0-39)
        """
        if total_score >= 80:
            return "EXCELLENT"
        elif total_score >= 60:
            return "GOOD"
        elif total_score >= 40:
            return "FAIR"
        else:
            return "POOR"

    def _get_recommendations(
        self,
        manufacturer_score: int,
        technology_score: int,
        age_score: int,
        pathway_score: int,
        geographic_score: int,
        manufacturer_data: Dict[str, Any],
        technology_data: Dict[str, Any],
        age_data: Dict[str, Any],
    ) -> List[str]:
        """
        Generate actionable recommendations to improve diversity.

        Args:
            Dimension scores and metadata

        Returns:
            List of recommendation strings (prioritized)
        """
        recommendations = []

        # CRITICAL: Manufacturer diversity (worth 30 points)
        if manufacturer_score == 0:
            recommendations.append(
                "CRITICAL: Add predicate from different manufacturer (avoid echo chamber risk)"
            )
            # Suggest alternative manufacturers
            current_manufacturer = manufacturer_data["unique_list"][0]
            recommendations.append(
                f"  → Current manufacturer: {current_manufacturer}"
            )
            recommendations.append(
                "  → Search for predicates from competing manufacturers (Boston Scientific, Medtronic, Abbott, etc.)"
            )
        elif manufacturer_score == 10:
            recommendations.append(
                "MAJOR: Add third manufacturer to strengthen predicate diversity"
            )

        # CRITICAL: Technology diversity (worth 30 points)
        if technology_score == 0:
            recommendations.append(
                "CRITICAL: Add predicate with different technology approach"
            )
            current_tech = (
                technology_data["unique_list"][0]
                if technology_data["unique_list"]
                else "generic"
            )
            recommendations.append(f"  → Current technology: {current_tech}")
            recommendations.append(
                "  → Consider predicates with different materials, coatings, or mechanisms"
            )
        elif technology_score == 10:
            recommendations.append(
                "MAJOR: Add predicates demonstrating broader technology range"
            )

        # MAJOR: Age diversity (worth 25 points)
        if age_score < 10:
            year_span = age_data.get("year_span", 0)
            most_recent_year = age_data.get("most_recent_year")
            recommendations.append(
                f"MAJOR: Expand clearance date range (current span: {year_span} years)"
            )
            if most_recent_year:
                recommendations.append(
                    f"  → Include predicates spanning wider time range (5+ years recommended)"
                )
                recommendations.append(
                    f"  → Most recent: {most_recent_year}, consider adding older predicates for historical context"
                )
        elif age_score < 20:
            years_since_recent = age_data.get("years_since_most_recent", 0)
            if years_since_recent > 2:
                recommendations.append(
                    f"SUGGESTED: Include more recent predicates (most recent: {years_since_recent} years ago)"
                )

        # MINOR: Pathway diversity (worth 10 points)
        if pathway_score == 0:
            recommendations.append(
                "SUGGESTED: Consider including Special 510(k) or De Novo predicates for pathway diversity"
            )

        # MINOR: Geographic diversity (worth 10 points)
        if geographic_score == 0:
            recommendations.append(
                "SUGGESTED: Consider international predicates for geographic diversity"
            )

        # If no recommendations (excellent diversity)
        if not recommendations:
            recommendations.append(
                "Excellent predicate diversity - no improvements needed"
            )

        return recommendations

    def _empty_result(self) -> Dict[str, Any]:
        """
        Return empty result for zero predicates.

        Returns:
            Dict with zero scores
        """
        return {
            "total_score": 0,
            "manufacturer_score": 0,
            "technology_score": 0,
            "age_score": 0,
            "pathway_score": 0,
            "geographic_score": 0,
            "grade": "POOR",
            "recommendations": ["CRITICAL: No predicates found - add at least 1-3 predicates"],
            "unique_manufacturers": 0,
            "manufacturer_list": [],
            "unique_technologies": 0,
            "technology_list": [],
            "clearance_year_span": 0,
            "most_recent_year": None,
            "oldest_year": None,
            "pathway_diversity": 0,
            "country_diversity": 0,
        }


def analyze_predicate_diversity(predicates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to analyze predicate diversity.

    Args:
        predicates: List of predicate device dicts

    Returns:
        Diversity analysis scorecard dict
    """
    analyzer = PredicateDiversityAnalyzer(predicates)
    return analyzer.analyze()
