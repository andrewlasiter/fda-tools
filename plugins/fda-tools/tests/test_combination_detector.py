"""
Tests for lib/combination_detector.py (FDA-29: No Tests for lib/ Modules).

Validates combination product detection including drug-device,
device-biologic, and false positive scenarios.

Per 21 CFR Part 3, combination product classification requires
accurate detection of drug and biologic components.
"""

import os
import sys

import pytest

# Ensure lib directory is importable
LIB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "lib"
)
sys.path.insert(0, LIB_DIR)

from combination_detector import CombinationProductDetector


# ============================================================================
# Drug-Device Combination Detection
# ============================================================================


class TestDrugDeviceDetection:
    """Test detection of drug-device combination products."""

    def test_drug_eluting_stent_detected(self):
        device = {
            "device_description": "Drug-eluting coronary stent coated with sirolimus",
            "trade_name": "CardioStent DES",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is True
        assert "drug" in result["combination_type"].lower()

    def test_heparin_coated_catheter_detected(self):
        device = {
            "device_description": "Heparin-coated central venous catheter",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is True

    def test_antibiotic_loaded_bone_cement_detected(self):
        device = {
            "device_description": "Antibiotic-loaded bone cement with gentamicin",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is True
        assert len(result["detected_components"]) >= 1

    def test_paclitaxel_balloon_detected(self):
        device = {
            "device_description": "Paclitaxel-coated peripheral angioplasty balloon",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is True


# ============================================================================
# Device-Biologic Combination Detection
# ============================================================================


class TestDeviceBiologicDetection:
    """Test detection of device-biologic combination products."""

    def test_collagen_scaffold_detected(self):
        device = {
            "device_description": "Collagen-based tissue-engineered scaffold for bone repair",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is True
        assert "biologic" in result["combination_type"].lower()

    def test_decellularized_tissue_detected(self):
        device = {
            "device_description": "Decellularized porcine dermis matrix for wound repair",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is True

    def test_growth_factor_device_detected(self):
        device = {
            "device_description": "Bone graft with bone morphogenetic protein (BMP)",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is True


# ============================================================================
# Non-Combination (False Positive Prevention)
# ============================================================================


class TestNonCombination:
    """Test that non-combination devices are correctly classified."""

    def test_plain_catheter_not_combination(self):
        device = {
            "device_description": "Standard polyurethane central venous catheter",
            "trade_name": "VascuLine Pro",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is False

    def test_orthopedic_screw_not_combination(self):
        device = {
            "device_description": "Titanium pedicle screw for spinal fixation",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is False

    def test_exclusion_keywords_prevent_false_positive(self):
        device = {
            "device_description": "Catheter compatible with drug delivery systems, drug-free version",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is False

    def test_uncoated_device_not_combination(self):
        device = {
            "device_description": "Uncoated stainless steel coronary stent",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is False


# ============================================================================
# Result Structure Validation
# ============================================================================


class TestResultStructure:
    """Test that results contain all required fields."""

    def test_combination_result_has_all_fields(self):
        device = {
            "device_description": "Drug-eluting coronary stent with sirolimus",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()

        required_fields = [
            "is_combination",
            "combination_type",
            "confidence",
            "detected_components",
            "rho_assignment",
            "rho_rationale",
            "consultation_required",
            "regulatory_pathway",
            "recommendations",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

    def test_non_combination_result_has_all_fields(self):
        device = {
            "device_description": "Standard catheter",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()

        assert "is_combination" in result
        assert result["is_combination"] is False

    def test_confidence_is_valid(self):
        device = {
            "device_description": "Drug-coated balloon catheter",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["confidence"] in ("HIGH", "MEDIUM", "LOW")

    def test_rho_assignment_is_valid(self):
        device = {
            "device_description": "Drug-eluting stent with paclitaxel",
        }
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["rho_assignment"] in ("CDRH", "CDER", "CBER", "UNCERTAIN")

    def test_empty_description_returns_no_combination(self):
        device = {"device_description": ""}
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is False

    def test_no_description_key_returns_no_combination(self):
        device = {}
        detector = CombinationProductDetector(device)
        result = detector.detect()
        assert result["is_combination"] is False
