"""
Test Sprint 6 Features: MRI Safety, Predicate Diversity, eCopy Export

Tests the three critical features added in Sprint 6:
1. MRI Safety Auto-Trigger (Feature 1)
2. Predicate Diversity Scorecard (Feature 2)
3. eCopy Export Command (Feature 3)

Author: Claude Code (Anthropic)
Date: 2026-02-14
"""

import sys
import os
import json
import pytest
from pathlib import Path

# Add lib directory to path
# Package imports configured in conftest.py and pytest.ini

from lib.predicate_diversity import PredicateDiversityAnalyzer, analyze_predicate_diversity
from lib.ecopy_exporter import eCopyExporter


class TestPredicateDiversity:
    """Test predicate diversity analysis module."""

    def test_poor_diversity_single_manufacturer(self):
        """Test poor diversity: single manufacturer (echo chamber)."""
        predicates = [
            {
                "k_number": "K123456",
                "manufacturer": "Boston Scientific",
                "device_name": "Drug-Eluting Balloon",
                "clearance_date": "2022-01-15",
                "product_code": "DQY",
                "decision_description": "paclitaxel-coated balloon catheter",
                "contact_country": "United States",
            },
            {
                "k_number": "K123457",
                "manufacturer": "Boston Scientific",
                "device_name": "Paclitaxel Balloon",
                "clearance_date": "2022-06-10",
                "product_code": "DQY",
                "decision_description": "paclitaxel drug-eluting balloon",
                "contact_country": "United States",
            },
        ]

        analyzer = PredicateDiversityAnalyzer(predicates)
        result = analyzer.analyze()

        assert result["total_score"] < 40, "Should be POOR grade"
        assert result["grade"] == "POOR"
        assert result["manufacturer_score"] == 0, "Single manufacturer = 0 points"
        assert result["unique_manufacturers"] == 1
        assert "CRITICAL" in result["recommendations"][0], "Should recommend different manufacturer"

    def test_excellent_diversity(self):
        """Test excellent diversity: 4 manufacturers, 4 technologies, 6 year span."""
        predicates = [
            {
                "k_number": "K123456",
                "manufacturer": "Boston Scientific",
                "device_name": "Drug-Eluting Balloon",
                "clearance_date": "2018-01-15",
                "product_code": "DQY",
                "decision_description": "paclitaxel drug-eluting balloon catheter",
                "contact_country": "United States",
            },
            {
                "k_number": "K234567",
                "manufacturer": "Medtronic",
                "device_name": "Bare Metal Balloon",
                "clearance_date": "2020-03-20",
                "product_code": "DQY",
                "decision_description": "uncoated bare-metal angioplasty balloon",
                "contact_country": "Ireland",
            },
            {
                "k_number": "K345678",
                "manufacturer": "Abbott",
                "device_name": "Coated Balloon",
                "clearance_date": "2022-06-10",
                "product_code": "DQY",
                "decision_description": "hydrophilic coated balloon catheter",
                "contact_country": "United States",
            },
            {
                "k_number": "K456789",
                "manufacturer": "Cook Medical",
                "device_name": "Sirolimus Balloon",
                "clearance_date": "2024-02-15",
                "product_code": "DQY",
                "decision_description": "sirolimus drug-eluting balloon single-use",
                "contact_country": "United States",
            },
        ]

        analyzer = PredicateDiversityAnalyzer(predicates)
        result = analyzer.analyze()

        assert result["total_score"] >= 80, f"Should be EXCELLENT grade, got {result['total_score']}"
        assert result["grade"] in ["EXCELLENT", "GOOD"]
        assert result["manufacturer_score"] == 30, "4 manufacturers = 30 points"
        assert result["unique_manufacturers"] == 4
        assert result["technology_score"] >= 20, "Should have good technology diversity"
        assert result["clearance_year_span"] == 6, "Should span 6 years (2018-2024)"

    def test_zero_predicates(self):
        """Test edge case: zero predicates."""
        analyzer = PredicateDiversityAnalyzer([])
        result = analyzer.analyze()

        assert result["total_score"] == 0
        assert result["grade"] == "POOR"
        assert "CRITICAL" in result["recommendations"][0]

    def test_technology_detection(self):
        """Test technology keyword detection."""
        predicates = [
            {
                "k_number": "K123456",
                "manufacturer": "Company A",
                "device_name": "AI-Powered CAD System",
                "clearance_date": "2024-01-15",
                "product_code": "QKQ",
                "decision_description": "machine learning neural network for automated image analysis",
                "contact_country": "United States",
            },
            {
                "k_number": "K234567",
                "manufacturer": "Company B",
                "device_name": "Manual Microscope",
                "clearance_date": "2023-06-10",
                "product_code": "QKQ",
                "decision_description": "manual non-powered optical microscope",
                "contact_country": "United States",
            },
        ]

        analyzer = PredicateDiversityAnalyzer(predicates)
        result = analyzer.analyze()

        assert "AI/ML" in result["technology_list"] or "manual" in result["technology_list"]
        assert result["unique_technologies"] >= 2


class TestMRISafetyData:
    """Test MRI safety data structures."""

    def test_implantable_product_codes_load(self):
        """Test that implantable product codes database loads correctly."""
        data_path = Path(__file__).parent.parent / 'data' / 'implantable_product_codes.json'

        assert data_path.exists(), "implantable_product_codes.json should exist"

        with open(data_path) as f:
            data = json.load(f)

        assert "implantable_product_codes" in data
        assert "product_code_details" in data
        assert "material_mri_safety" in data
        assert "mri_field_strengths" in data

        # Check key product codes
        assert "OVE" in data["implantable_product_codes"], "OVE (spine cage) should be implantable"
        assert "GZB" in data["implantable_product_codes"], "GZB (neurostim) should be implantable"

        # Check material data
        assert "Ti-6Al-4V" in data["material_mri_safety"]
        assert data["material_mri_safety"]["Ti-6Al-4V"]["classification"] == "MR_CONDITIONAL"
        assert data["material_mri_safety"]["PEEK"]["classification"] == "MR_SAFE"

    def test_mri_safety_template_exists(self):
        """Test that MRI safety section template exists."""
        template_path = Path(__file__).parent.parent / 'templates' / 'mri_safety_section.md'

        assert template_path.exists(), "mri_safety_section.md template should exist"

        with open(template_path) as f:
            content = f.read()

        # Check key sections present
        assert "Section 19: MRI Safety" in content
        assert "ASTM F2182" in content
        assert "MR Conditional" in content
        assert "RF-Induced Heating" in content
        assert "Magnetically Induced Displacement Force" in content


class TestECopyExporter:
    """Test eCopy exporter module."""

    def test_ecopy_exporter_init(self, tmp_path):
        """Test eCopyExporter initialization."""
        project_path = tmp_path / "test_project"
        project_path.mkdir()

        exporter = eCopyExporter(str(project_path))

        assert exporter.project_path == project_path
        assert exporter.ecopy_path == project_path / "eCopy"
        assert isinstance(exporter.pandoc_available, bool)

    def test_ecopy_sections_structure(self):
        """Test that eCopy sections are properly defined."""
        sections = eCopyExporter.ECOPY_SECTIONS

        assert "01" in sections, "Cover Letter section should exist"
        assert "19" in sections, "MRI Safety section should exist (Sprint 6)"

        assert sections["01"]["name"] == "Cover Letter"
        assert sections["19"]["name"] == "MRI Safety"

        # Check MRI safety draft file mapping
        assert "draft_mri-safety.md" in sections["19"]["draft_files"]

    def test_ecopy_export_empty_project(self, tmp_path):
        """Test eCopy export on empty project (should create structure)."""
        project_path = tmp_path / "empty_project"
        project_path.mkdir()
        drafts_path = project_path / "drafts"
        drafts_path.mkdir()

        exporter = eCopyExporter(str(project_path))
        result = exporter.export()

        assert "ecopy_path" in result
        assert result["sections_created"] == 19, "Should create 19 sections (including MRI Safety)"
        assert result["files_converted"] == 0, "No drafts to convert"
        assert result["total_size_mb"] >= 0

        # Check eCopy directory structure created
        ecopy_path = Path(result["ecopy_path"])
        assert ecopy_path.exists()

        # Check mandatory sections exist
        assert (ecopy_path / "0001-CoverLetter").exists()
        assert (ecopy_path / "0019-MRISafety").exists(), "MRI Safety section should be created"

    def test_ecopy_validation_mandatory_sections(self, tmp_path):
        """Test eCopy validation for mandatory sections."""
        project_path = tmp_path / "validation_project"
        project_path.mkdir()
        drafts_path = project_path / "drafts"
        drafts_path.mkdir()

        exporter = eCopyExporter(str(project_path))
        result = exporter.export()

        validation = result["validation"]

        # Empty project should fail mandatory sections check
        assert validation["mandatory_sections"] == False, "Should fail without draft files"
        assert len(validation["errors"]) > 0, "Should have error messages"


# Integration test scenarios
class TestIntegrationScenarios:
    """Test complete Sprint 6 workflow scenarios."""

    def test_implantable_device_workflow(self):
        """Test complete workflow for implantable device (OVE - spine cage)."""
        # 1. Check product code in implantable database
        data_path = Path(__file__).parent.parent / 'data' / 'implantable_product_codes.json'
        with open(data_path) as f:
            data = json.load(f)

        assert "OVE" in data["implantable_product_codes"]

        product_details = data["product_code_details"]["OVE"]
        assert "Intervertebral Body Fusion Device" in product_details["name"]

        # 2. Verify MRI safety template available
        template_path = Path(__file__).parent.parent / 'templates' / 'mri_safety_section.md'
        assert template_path.exists()

        # 3. Verify eCopy section 19 will be created
        sections = eCopyExporter.ECOPY_SECTIONS
        assert "19" in sections
        assert sections["19"]["name"] == "MRI Safety"

    def test_predicate_diversity_improvement_workflow(self):
        """Test workflow for improving poor predicate diversity."""
        # Start with poor diversity
        poor_predicates = [
            {
                "k_number": "K123456",
                "manufacturer": "Company A",
                "device_name": "Device Type 1",
                "clearance_date": "2023-01-15",
                "product_code": "ABC",
                "decision_description": "technology type 1",
                "contact_country": "United States",
            }
        ]

        analyzer1 = PredicateDiversityAnalyzer(poor_predicates)
        result1 = analyzer1.analyze()

        assert result1["grade"] == "POOR"
        assert "CRITICAL" in result1["recommendations"][0]

        # Add diverse predicates
        improved_predicates = poor_predicates + [
            {
                "k_number": "K234567",
                "manufacturer": "Company B",  # Different manufacturer
                "device_name": "Device Type 2",
                "clearance_date": "2020-06-10",  # Older date for age diversity
                "product_code": "ABC",
                "decision_description": "technology type 2",  # Different technology
                "contact_country": "Germany",  # Different country
            },
            {
                "k_number": "K345678",
                "manufacturer": "Company C",
                "device_name": "Device Type 3",
                "clearance_date": "2024-03-20",  # Recent date
                "product_code": "ABC",
                "decision_description": "technology type 3",
                "contact_country": "United States",
            },
        ]

        analyzer2 = PredicateDiversityAnalyzer(improved_predicates)
        result2 = analyzer2.analyze()

        assert result2["total_score"] > result1["total_score"], "Score should improve"
        assert result2["grade"] in ["EXCELLENT", "GOOD", "FAIR"], "Grade should improve from POOR"
        assert result2["grade"] != "POOR", "Grade should no longer be POOR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
