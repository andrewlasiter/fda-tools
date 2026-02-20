#!/usr/bin/env python3
"""
Tests for eSTAR Field Extractor (FDA-120)

Tests field extraction from project files for eSTAR XML population.
"""

import json
import pytest
from pathlib import Path

from fda_tools.lib.estar_field_extractor import (
    EStarFieldExtractor,
    extract_estar_fields,
)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory with test data."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create device_profile.json
    device_profile = {
        "device_name": "Test Device",
        "product_code": "DQY",
        "sterilization_method": "EO",
        "materials": ["Titanium", "Silicone"],
        "shelf_life": "3 years",
        "biocompatibility": "ISO 10993 testing performed",
        "testing_performed": [
            {"test_name": "Biocompatibility Testing"},
            {"test_name": "Sterilization Validation"}
        ]
    }
    with open(project_dir / "device_profile.json", 'w') as f:
        json.dump(device_profile, f)

    # Create review.json
    review_data = {
        "accepted_predicates": [
            {"k_number": "K123456"},
            {"k_number": "K789012"}
        ]
    }
    with open(project_dir / "review.json", 'w') as f:
        json.dump(review_data, f)

    # Create standards_lookup.json
    standards_data = {
        "standards": [
            {"standard_number": "ISO 10993-1", "title": "Biocompatibility"},
            {"standard_number": "ISO 11135", "title": "Sterilization"}
        ]
    }
    with open(project_dir / "standards_lookup.json", 'w') as f:
        json.dump(standards_data, f)

    # Create se_comparison.md
    se_comparison = """# Substantial Equivalence Comparison

| Characteristic | Subject Device | Predicate Device | Assessment |
|---|---|---|---|
| Indications | Same | Same | SE |
| Materials | Titanium | Titanium | SE |
| Sterilization | EO | EO | SE |
"""
    with open(project_dir / "se_comparison.md", 'w') as f:
        f.write(se_comparison)

    # Create drafts directory with sections
    drafts_dir = project_dir / "drafts"
    drafts_dir.mkdir()

    # Sterilization section
    sterilization = """## Sterilization

The device is sterilized using ethylene oxide (EO) gas.
Sterilization validation was performed according to ISO 11135.
"""
    with open(drafts_dir / "12_sterilization.md", 'w') as f:
        f.write(sterilization)

    # Device description
    device_desc = """## Device Description

The device is constructed from medical grade titanium and silicone.
The materials are biocompatible per ISO 10993.
"""
    with open(drafts_dir / "06_device_description.md", 'w') as f:
        f.write(device_desc)

    # Biocompatibility
    biocompat = """## Biocompatibility

The device was evaluated for biocompatibility according to ISO 10993-1.
Testing included cytotoxicity, sensitization, and irritation studies.
All tests passed acceptance criteria.
"""
    with open(drafts_dir / "10_biocompatibility.md", 'w') as f:
        f.write(biocompat)

    # Software (for SaMD devices)
    software = """## Software

The device includes embedded software for control and monitoring.
Software was developed according to IEC 62304.
Cybersecurity controls per FDA guidance.
"""
    with open(drafts_dir / "15_software.md", 'w') as f:
        f.write(software)

    # Test plan
    test_plan = """# Test Plan

## Summary

Testing included biocompatibility, sterilization validation, and performance testing.
All tests were conducted per applicable standards.

## Details
...
"""
    with open(project_dir / "test_plan.md", 'w') as f:
        f.write(test_plan)

    # Shelf life calculation
    calc_dir = project_dir / "calculations"
    calc_dir.mkdir()
    shelf_life_data = {"shelf_life": "3 years", "confidence": "95%"}
    with open(calc_dir / "shelf_life.json", 'w') as f:
        json.dump(shelf_life_data, f)

    return project_dir


@pytest.fixture
def extractor(temp_project_dir):
    """Create extractor instance."""
    return EStarFieldExtractor(str(temp_project_dir))


class TestEStarFieldExtractor:
    """Test suite for eSTAR field extraction."""

    def test_init_creates_extractor(self, temp_project_dir):
        """Test extractor initialization."""
        extractor = EStarFieldExtractor(str(temp_project_dir))
        assert extractor.project_dir == temp_project_dir
        assert extractor._device_profile is None  # Lazy load

    def test_load_device_profile(self, extractor):
        """Test device profile loading."""
        profile = extractor._load_device_profile()
        assert "device_name" in profile
        assert profile["device_name"] == "Test Device"
        assert profile["product_code"] == "DQY"

    def test_load_review_data(self, extractor):
        """Test review data loading."""
        review = extractor._load_review_data()
        assert "accepted_predicates" in review
        assert len(review["accepted_predicates"]) == 2

    def test_load_standards(self, extractor):
        """Test standards loading."""
        standards = extractor._load_standards()
        assert len(standards) == 2
        assert standards[0]["standard_number"] == "ISO 10993-1"

    def test_load_se_comparison(self, extractor):
        """Test SE comparison loading."""
        se_md = extractor._load_se_comparison()
        assert "Substantial Equivalence" in se_md
        assert "Characteristic" in se_md

    def test_read_draft_section(self, extractor):
        """Test draft section reading."""
        content = extractor._read_draft_section("sterilization")
        assert "ethylene oxide" in content.lower()

    def test_get_sterilization_method_from_profile(self, extractor):
        """Test sterilization extraction from device profile."""
        method = extractor.get_sterilization_method()
        assert method == "EO"

    def test_get_sterilization_method_from_draft(self, temp_project_dir):
        """Test sterilization extraction from draft section."""
        # Create extractor without sterilization in profile
        profile_path = temp_project_dir / "device_profile.json"
        with open(profile_path, 'r') as f:
            profile = json.load(f)
        del profile['sterilization_method']
        with open(profile_path, 'w') as f:
            json.dump(profile, f)

        extractor = EStarFieldExtractor(str(temp_project_dir))
        method = extractor.get_sterilization_method()
        assert method == "EO"

    def test_get_materials_from_profile(self, extractor):
        """Test materials extraction from device profile."""
        materials = extractor.get_materials()
        assert "Titanium" in materials
        assert "Silicone" in materials

    def test_get_materials_from_draft(self, temp_project_dir):
        """Test materials extraction from draft section."""
        extractor = EStarFieldExtractor(str(temp_project_dir))
        materials = extractor.get_materials()
        assert len(materials) > 0

    def test_get_shelf_life_from_calculation(self, extractor):
        """Test shelf life extraction from calculation file."""
        shelf_life = extractor.get_shelf_life()
        assert shelf_life == "3 years"

    def test_get_shelf_life_from_profile(self, temp_project_dir):
        """Test shelf life extraction from device profile."""
        # Remove calculation file
        (temp_project_dir / "calculations" / "shelf_life.json").unlink()

        extractor = EStarFieldExtractor(str(temp_project_dir))
        shelf_life = extractor.get_shelf_life()
        assert shelf_life == "3 years"

    def test_get_biocompatibility_summary(self, extractor):
        """Test biocompatibility summary extraction."""
        summary = extractor.get_biocompatibility_summary()
        assert summary is not None
        assert "ISO 10993-1" in summary or "biocompatibility" in summary.lower()

    def test_get_software_description(self, extractor):
        """Test software description extraction."""
        desc = extractor.get_software_description()
        assert desc is not None
        assert "IEC 62304" in desc or "software" in desc.lower()

    def test_get_predicate_comparison(self, extractor):
        """Test predicate comparison table extraction."""
        comparison = extractor.get_predicate_comparison()
        assert len(comparison) >= 3  # At least 3 rows in test data
        assert comparison[0]["characteristic"] == "Indications"
        assert comparison[0]["subject"] == "Same"
        assert comparison[0]["predicate"] == "Same"
        assert comparison[0]["assessment"] == "SE"

    def test_get_standards_compliance(self, extractor):
        """Test standards compliance list extraction."""
        standards = extractor.get_standards_compliance()
        assert len(standards) == 2
        assert standards[0]["number"] == "ISO 10993-1"
        assert standards[0]["status"] == "Compliant"

    def test_get_testing_summary(self, extractor):
        """Test testing summary extraction."""
        summary = extractor.get_testing_summary()
        assert summary is not None
        assert "biocompatibility" in summary.lower() or "testing" in summary.lower()

    def test_get_predicate_k_numbers(self, extractor):
        """Test predicate K-number extraction."""
        k_numbers = extractor.get_predicate_k_numbers()
        assert len(k_numbers) == 2
        assert "K123456" in k_numbers
        assert "K789012" in k_numbers

    def test_extract_all_fields(self, extractor):
        """Test extraction of all fields."""
        fields = extractor.extract_all_fields()

        assert "sterilization_method" in fields
        assert "materials" in fields
        assert "shelf_life" in fields
        assert "biocompatibility_summary" in fields
        assert "software_description" in fields
        assert "predicate_comparison" in fields
        assert "standards_compliance" in fields
        assert "testing_summary" in fields
        assert "predicate_k_numbers" in fields

        # Verify at least some fields are populated
        assert fields["sterilization_method"] is not None
        assert len(fields["materials"]) > 0
        assert fields["shelf_life"] is not None

    def test_get_field_population_score(self, extractor):
        """Test field population scoring."""
        stats = extractor.get_field_population_score()

        assert "total_fields" in stats
        assert "populated_fields" in stats
        assert "population_percentage" in stats
        assert "list_items" in stats
        assert "fields" in stats

        # Should have >50% population with test data
        assert stats["population_percentage"] > 50

    def test_empty_project_handling(self, tmp_path):
        """Test extraction from empty project directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        extractor = EStarFieldExtractor(str(empty_dir))
        fields = extractor.extract_all_fields()

        # Should not crash, just return empty/None values
        assert fields["sterilization_method"] is None
        assert len(fields["materials"]) == 0
        assert fields["shelf_life"] is None

    def test_partial_data_handling(self, temp_project_dir):
        """Test extraction with partial data."""
        # Remove some files
        (temp_project_dir / "review.json").unlink()
        (temp_project_dir / "test_plan.md").unlink()

        extractor = EStarFieldExtractor(str(temp_project_dir))
        fields = extractor.extract_all_fields()

        # Should still extract available data
        assert fields["sterilization_method"] is not None
        assert len(fields["materials"]) > 0

        # Missing data should be empty
        assert len(fields["predicate_k_numbers"]) == 0

    def test_convenience_function(self, temp_project_dir):
        """Test convenience function."""
        fields = extract_estar_fields(str(temp_project_dir))
        assert "sterilization_method" in fields
        assert fields["sterilization_method"] is not None

    def test_lazy_loading(self, extractor):
        """Test lazy loading of data files."""
        # Initially not loaded
        assert extractor._device_profile is None
        assert extractor._review_data is None

        # Load device profile
        extractor._load_device_profile()
        assert extractor._device_profile is not None

        # Second call should use cache
        profile1 = extractor._load_device_profile()
        profile2 = extractor._load_device_profile()
        assert profile1 is profile2  # Same object

    def test_materials_limit(self, temp_project_dir):
        """Test materials list is limited to 10 items."""
        # Create device with many materials
        profile_path = temp_project_dir / "device_profile.json"
        with open(profile_path, 'r') as f:
            profile = json.load(f)

        profile['materials'] = [f"Material{i}" for i in range(20)]
        with open(profile_path, 'w') as f:
            json.dump(profile, f)

        extractor = EStarFieldExtractor(str(temp_project_dir))
        materials = extractor.get_materials()

        assert len(materials) <= 10

    def test_comparison_rows_limit(self, temp_project_dir):
        """Test predicate comparison rows limited to 20."""
        # Create SE comparison with many rows
        se_md = "# SE Comparison\n\n| Characteristic | Subject | Predicate | Assessment |\n|---|---|---|---|\n"
        for i in range(30):
            se_md += f"| Feature{i} | Value{i} | Value{i} | SE |\n"

        with open(temp_project_dir / "se_comparison.md", 'w') as f:
            f.write(se_md)

        extractor = EStarFieldExtractor(str(temp_project_dir))
        comparison = extractor.get_predicate_comparison()

        assert len(comparison) <= 20

    def test_standards_limit(self, temp_project_dir):
        """Test standards list limited to 30 items."""
        # Create standards file with many standards
        standards_data = {
            "standards": [
                {"standard_number": f"ISO {i}", "title": f"Standard {i}"}
                for i in range(50)
            ]
        }
        with open(temp_project_dir / "standards_lookup.json", 'w') as f:
            json.dump(standards_data, f)

        extractor = EStarFieldExtractor(str(temp_project_dir))
        standards = extractor.get_standards_compliance()

        assert len(standards) <= 30
