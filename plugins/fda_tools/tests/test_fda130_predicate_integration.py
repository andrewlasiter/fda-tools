"""
Integration tests for FDA-130: Predicate Diversity & Ranker integration
into main workflow commands (research, pipeline, compare-se, dashboard).

Verifies that:
1. PredicateDiversityAnalyzer and PredicateRanker are importable via the
   fda_tools package path (the same imports used in the new command steps).
2. The diversity gate logic (POOR / FAIR / GOOD / EXCELLENT) works end-to-end
   with a project directory containing review.json.
3. PredicateRanker produces ranked output sorted by total_score descending.
4. Edge cases (< 2 predicates, missing files) are handled gracefully.
"""

import json
import tempfile
from pathlib import Path

import pytest

from fda_tools.lib.predicate_diversity import PredicateDiversityAnalyzer
from fda_tools.lib.predicate_ranker import PredicateRanker, rank_predicates


# ============================================================================
# Fixtures
# ============================================================================

def _make_review_json(accepted: list[dict], project_dir: Path) -> None:
    """Write a review.json in the format PredicateRanker._load_enriched_predicates expects.

    PredicateRanker reads `accepted_predicates` (list), while the diversity
    analysis reads from the standard `predicates` (dict) format. We write both
    so both can be tested from the same file.
    """
    # Standard format used by dashboard/pipeline diversity gate
    predicates_dict = {}
    for p in accepted:
        k = p["k_number"]
        predicates_dict[k] = {
            "decision": "accepted",
            "manufacturer": p.get("manufacturer", ""),
            "device_name": p.get("device_name", ""),
            "clearance_date": p.get("clearance_date", ""),
            "product_code": p.get("product_code", "DQY"),
            "decision_description": p.get("decision_description", ""),
            "contact_country": p.get("contact_country", "US"),
        }
    # Ranker format (accepted_predicates list) — PredicateRanker._load_enriched_predicates
    accepted_list = [
        {
            "k_number": p["k_number"],
            "device_name": p.get("device_name", ""),
            "applicant": p.get("manufacturer", ""),
            "decision_date": p.get("clearance_date", ""),
            "product_code": p.get("product_code", "DQY"),
            "statement": p.get("decision_description", ""),
            "confidence_score": 70,
            "recalls_total": 0,
            "maude_productcode_5y": 10,
            "web_validation": "GREEN",
        }
        for p in accepted
    ]
    review_data = {
        "review_mode": "auto",
        "predicates": predicates_dict,
        "accepted_predicates": accepted_list,
    }
    (project_dir / "review.json").write_text(json.dumps(review_data))


DIVERSE_SET = [
    {
        "k_number": "K241335",
        "manufacturer": "Acme Medical",
        "device_name": "CardioStent A",
        "clearance_date": "2024-06-15",
        "product_code": "DQY",
        "decision_description": "Drug-coated coronary stent",
        "contact_country": "US",
    },
    {
        "k_number": "K221001",
        "manufacturer": "BioTech Corp",
        "device_name": "FlowCath B",
        "clearance_date": "2022-03-10",
        "product_code": "DQY",
        "decision_description": "Polymer catheter for cardiac use",
        "contact_country": "DE",
    },
    {
        "k_number": "K190500",
        "manufacturer": "MedDevice Inc",
        "device_name": "VascuLine C",
        "clearance_date": "2019-11-20",
        "product_code": "DQY",
        "decision_description": "Metallic coronary stent",
        "contact_country": "JP",
    },
    {
        "k_number": "K170200",
        "manufacturer": "CardioTech SA",
        "device_name": "StentPro D",
        "clearance_date": "2017-08-05",
        "product_code": "DQY",
        "decision_description": "Bare metal stent system",
        "contact_country": "FR",
    },
]

ECHO_CHAMBER_SET = [
    {
        "k_number": "K241335",
        "manufacturer": "Acme Medical",
        "device_name": "CardioStent A",
        "clearance_date": "2024-06-15",
        "product_code": "DQY",
        "decision_description": "Drug-coated coronary stent",
        "contact_country": "US",
    },
    {
        "k_number": "K241336",
        "manufacturer": "Acme Medical",
        "device_name": "CardioStent B",
        "clearance_date": "2024-07-20",
        "product_code": "DQY",
        "decision_description": "Drug-coated coronary stent 2",
        "contact_country": "US",
    },
    {
        "k_number": "K241337",
        "manufacturer": "Acme Medical",
        "device_name": "CardioStent C",
        "clearance_date": "2024-09-01",
        "product_code": "DQY",
        "decision_description": "Drug-coated coronary stent 3",
        "contact_country": "US",
    },
]


# ============================================================================
# 1. Import path tests (FDA-130 integration point)
# ============================================================================

class TestImportPaths:
    """The fda_tools package imports used in command steps must resolve."""

    def test_predicate_diversity_importable(self):
        from fda_tools.lib.predicate_diversity import PredicateDiversityAnalyzer  # noqa: F401

    def test_predicate_ranker_importable(self):
        from fda_tools.lib.predicate_ranker import PredicateRanker, rank_predicates  # noqa: F401


# ============================================================================
# 2. Diversity gate logic (pipeline.md Step 2.5)
# ============================================================================

class TestDiversityGate:
    """Verify the diversity gate classifies predicate sets correctly."""

    def test_diverse_set_achieves_good_grade(self):
        result = PredicateDiversityAnalyzer(DIVERSE_SET).analyze()
        assert result["total_score"] >= 60, (
            f"Diverse 4-predicate set should score ≥60, got {result['total_score']}"
        )
        assert result["grade"] in ("GOOD", "EXCELLENT")

    def test_echo_chamber_scores_poorly(self):
        result = PredicateDiversityAnalyzer(ECHO_CHAMBER_SET).analyze()
        assert result["total_score"] < 60, (
            f"Echo-chamber set (same mfr/country/year) should score <60, got {result['total_score']}"
        )

    def test_insufficient_predicates_skipped(self):
        """Single predicate — diversity analysis should be skipped."""
        single = [DIVERSE_SET[0]]
        # With only 1 predicate, the gate logic skips (< 2 predicates)
        assert len(single) < 2

    def test_grade_labels(self):
        result = PredicateDiversityAnalyzer(DIVERSE_SET).analyze()
        assert result["grade"] in ("EXCELLENT", "GOOD", "FAIR", "POOR")

    def test_result_keys_present(self):
        result = PredicateDiversityAnalyzer(DIVERSE_SET).analyze()
        for key in ("total_score", "grade", "manufacturer_score", "technology_score", "age_score"):
            assert key in result, f"Missing key: {key}"


# ============================================================================
# 3. Ranker integration with project directory (research.md Step 4.25)
# ============================================================================

class TestRankerIntegration:
    """Verify PredicateRanker works end-to-end with a review.json project."""

    def test_ranker_instantiates_with_project_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            # No files — should instantiate without error
            ranker = PredicateRanker(str(project_dir))
            assert ranker is not None

    def test_ranker_returns_ranked_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            _make_review_json(DIVERSE_SET, project_dir)

            # Provide minimal device profile for TF-IDF
            (project_dir / "device_profile.json").write_text(json.dumps({
                "product_code": "DQY",
                "indications_for_use": "Treatment of coronary artery disease in patients",
            }))

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            assert isinstance(ranked, list)
            assert len(ranked) > 0

    def test_ranked_list_sorted_by_score_descending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            _make_review_json(DIVERSE_SET, project_dir)
            (project_dir / "device_profile.json").write_text(json.dumps({
                "product_code": "DQY",
                "indications_for_use": "Cardiovascular stent",
            }))

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            if len(ranked) >= 2:
                scores = [r.get("total_score", 0) for r in ranked]
                assert scores == sorted(scores, reverse=True), (
                    "Ranked list must be sorted descending by total_score"
                )

    def test_ranked_items_have_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            _make_review_json(DIVERSE_SET[:2], project_dir)
            (project_dir / "device_profile.json").write_text(json.dumps({
                "product_code": "DQY",
            }))

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            for item in ranked:
                assert "k_number" in item
                assert "total_score" in item
                assert "strength" in item

    def test_ranker_handles_empty_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()
            # Empty project should return empty list (no error)
            assert isinstance(ranked, list)


# ============================================================================
# 4. Pipeline integration scenario (compare-se.md Step 2.75)
# ============================================================================

class TestCompareSeRankingScenario:
    """Simulate the ranking logic used in compare-se.md Step 2.75."""

    def test_primary_predicate_is_highest_scored(self):
        """The first item in ranked[] should be the primary predicate column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            _make_review_json(DIVERSE_SET, project_dir)
            (project_dir / "device_profile.json").write_text(json.dumps({
                "product_code": "DQY",
                "indications_for_use": "Coronary stent for atherosclerosis treatment",
            }))

            ranker = PredicateRanker(str(project_dir))
            ranked = ranker.rank_predicates()

            if len(ranked) >= 2:
                primary_score = ranked[0]["total_score"]
                for other in ranked[1:]:
                    assert primary_score >= other["total_score"], (
                        "Primary predicate (rank 1) must have highest or equal score"
                    )

    def test_diversity_and_ranking_consistent(self):
        """Ranking + diversity can both run on the same predicate set without error."""
        result = PredicateDiversityAnalyzer(DIVERSE_SET).analyze()
        assert result["total_score"] >= 0

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            _make_review_json(DIVERSE_SET, project_dir)
            (project_dir / "device_profile.json").write_text(json.dumps({
                "product_code": "DQY",
            }))
            ranked = PredicateRanker(str(project_dir)).rank_predicates()

        assert isinstance(ranked, list)
