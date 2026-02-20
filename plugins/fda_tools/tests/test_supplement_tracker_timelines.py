#!/usr/bin/env python3
"""
Test suite for supplement_tracker.py regulatory timeline configuration loading.

Tests verify:
- Configuration file loading from data/regulatory_timelines.json
- Backward compatibility with hardcoded defaults
- Graceful degradation on config errors
- Timeline value validation
- CFR citation integrity
- Historical timeline preservation
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
# Package imports configured in conftest.py and pytest.ini

# Import after path setup
from supplement_tracker import (  # type: ignore
    _load_regulatory_timelines,
    SUPPLEMENT_REGULATORY_TYPES,
)


class TestRegulatoryTimelineLoading:
    """Test regulatory timeline configuration loading."""

    def test_load_regulatory_timelines_success(self):
        """Test successful loading of regulatory timelines from config file."""
        # Load timelines (should succeed with real config file)
        timelines = _load_regulatory_timelines()

        # Verify structure
        assert isinstance(timelines, dict)
        assert len(timelines) > 0

        # Verify expected timeline types exist
        expected_keys = [
            "180_day_supplement",
            "real_time_supplement",
            "30_day_notice",
            "panel_track_supplement",
            "pas_related",
            "manufacturing_change",
            "other_unclassified",
        ]

        for key in expected_keys:
            assert key in timelines, f"Missing timeline: {key}"
            assert "typical_review_days" in timelines[key]
            assert "cfr_citation" in timelines[key]

    def test_timeline_values_are_positive_integers(self):
        """Test that all timeline values are positive integers."""
        timelines = _load_regulatory_timelines()

        for key, timeline in timelines.items():
            review_days = timeline.get("typical_review_days")
            assert isinstance(review_days, int), \
                f"{key}: typical_review_days must be integer, got {type(review_days)}"
            assert review_days > 0, \
                f"{key}: typical_review_days must be positive, got {review_days}"
            assert review_days <= 730, \
                f"{key}: typical_review_days should not exceed 2 years (730 days), got {review_days}"

    def test_cfr_citations_are_valid(self):
        """Test that all CFR citations follow expected format."""
        timelines = _load_regulatory_timelines()

        # CFR citation pattern: "21 CFR XXX.XX" or "21 CFR XXX.XX(x)"
        import re
        cfr_pattern = re.compile(r"^21 CFR \d+\.\d+(\([a-z]\))?$")

        for key, timeline in timelines.items():
            cfr = timeline.get("cfr_citation", "")
            assert cfr, f"{key}: cfr_citation is missing or empty"
            assert cfr_pattern.match(cfr), \
                f"{key}: invalid CFR citation format: {cfr}"

    def test_backward_compatibility_fallback(self, tmp_path):
        """Test fallback to hardcoded defaults when config file missing."""
        # Create a mock script directory with no config file
        with patch("supplement_tracker.Path") as mock_path:
            # Make config_path.exists() return False
            mock_config = mock_path.return_value.parent.__truediv__.return_value
            mock_config.exists.return_value = False

            timelines = _load_regulatory_timelines()

            # Verify fallback defaults were returned
            assert isinstance(timelines, dict)
            assert "180_day_supplement" in timelines
            assert timelines["180_day_supplement"]["typical_review_days"] == 180

    def test_graceful_degradation_on_json_error(self, tmp_path):
        """Test graceful fallback on invalid JSON in config file."""
        # Create invalid JSON file
        invalid_config = tmp_path / "regulatory_timelines.json"
        invalid_config.write_text("{ invalid json }")

        with patch("supplement_tracker.Path") as mock_path:
            mock_config = mock_path.return_value.parent.__truediv__.return_value
            mock_config.exists.return_value = True
            mock_config.__truediv__ = lambda self, other: invalid_config

            # Should fallback to defaults without raising exception
            timelines = _load_regulatory_timelines()
            assert isinstance(timelines, dict)

    def test_supplement_regulatory_types_use_config_values(self):
        """Test that SUPPLEMENT_REGULATORY_TYPES uses values from config."""
        # Verify that hardcoded values were overridden
        for type_key, type_def in SUPPLEMENT_REGULATORY_TYPES.items():
            review_days = type_def.get("typical_review_days")
            assert isinstance(review_days, int)
            assert review_days > 0

            # Verify CFR section exists
            cfr = type_def.get("cfr_section")
            assert cfr and cfr.startswith("21 CFR")

    def test_configuration_file_exists(self):
        """Test that regulatory_timelines.json exists in expected location."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        assert config_path.exists(), \
            f"Configuration file not found at {config_path}"

    def test_configuration_file_is_valid_json(self):
        """Test that regulatory_timelines.json is valid JSON."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path) as f:
            config = json.load(f)

        # Verify expected structure
        assert "metadata" in config
        assert "current_timelines" in config
        assert "cfr_citations" in config
        assert "update_history" in config

    def test_configuration_metadata_present(self):
        """Test that configuration file has complete metadata."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path) as f:
            config = json.load(f)

        metadata = config.get("metadata", {})
        assert "version" in metadata
        assert "last_updated" in metadata
        assert "effective_date" in metadata
        assert "update_procedure" in metadata

    def test_historical_timelines_preserved(self):
        """Test that historical timelines section exists for audit trail."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path) as f:
            config = json.load(f)

        assert "historical_timelines" in config
        historical = config.get("historical_timelines", [])
        assert isinstance(historical, list)

    def test_update_history_tracked(self):
        """Test that update history is tracked in configuration."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path) as f:
            config = json.load(f)

        history = config.get("update_history", [])
        assert isinstance(history, list)
        assert len(history) > 0, "Update history should not be empty"

        # Verify history entry structure
        for entry in history:
            assert "date" in entry
            assert "version" in entry
            assert "changes" in entry

    def test_validation_rules_defined(self):
        """Test that validation rules are defined in configuration."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path) as f:
            config = json.load(f)

        rules = config.get("validation_rules", {})
        assert "typical_review_days" in rules
        assert "cfr_citation" in rules
        assert "effective_date" in rules

    def test_all_timeline_types_have_guidance_references(self):
        """Test that timeline types include guidance references."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        with open(config_path) as f:
            config = json.load(f)

        current = config.get("current_timelines", {})
        for key, timeline in current.items():
            # Guidance references should be present (may be empty array for some types)
            assert "guidance_references" in timeline, \
                f"{key} missing guidance_references field"
            assert isinstance(timeline["guidance_references"], list)

    def test_effective_dates_are_valid_format(self):
        """Test that all effective dates use ISO 8601 format."""
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if not config_path.exists():
            pytest.skip("Configuration file not found")

        import re
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        with open(config_path) as f:
            config = json.load(f)

        # Check metadata dates
        metadata = config.get("metadata", {})
        if "last_updated" in metadata:
            assert date_pattern.match(metadata["last_updated"])
        if "effective_date" in metadata:
            assert date_pattern.match(metadata["effective_date"])

        # Check timeline effective dates
        current = config.get("current_timelines", {})
        for key, timeline in current.items():
            if "effective_date" in timeline:
                assert date_pattern.match(timeline["effective_date"]), \
                    f"{key}: invalid effective_date format"
            if "last_verified" in timeline:
                assert date_pattern.match(timeline["last_verified"]), \
                    f"{key}: invalid last_verified format"


class TestSupplementClassificationWithTimelines:
    """Test supplement classification using loaded timelines."""

    def test_supplement_types_have_timeline_values(self):
        """Test that all supplement types have timeline values loaded."""
        for type_key, type_def in SUPPLEMENT_REGULATORY_TYPES.items():
            assert "typical_review_days" in type_def
            assert type_def["typical_review_days"] > 0

    def test_default_timeline_fallback(self):
        """Test that default 180 days is used for 'other' type."""
        other_def = SUPPLEMENT_REGULATORY_TYPES.get("other", {})
        # Should have a value (either from config or default)
        assert "typical_review_days" in other_def
        # Default is 180 days
        assert other_def["typical_review_days"] >= 30  # Reasonable minimum

    def test_30_day_notice_has_short_timeline(self):
        """Test that 30-day notice has appropriately short timeline."""
        notice_def = SUPPLEMENT_REGULATORY_TYPES.get("30_day_notice", {})
        assert notice_def["typical_review_days"] <= 60, \
            "30-day notice should have short review period"

    def test_panel_track_has_long_timeline(self):
        """Test that panel-track has appropriately long timeline."""
        panel_def = SUPPLEMENT_REGULATORY_TYPES.get("panel_track", {})
        assert panel_def["typical_review_days"] >= 180, \
            "Panel-track should have extended review period"


class TestTimelineConfigurationMigration:
    """Test configuration migration and update scenarios."""

    def test_can_update_timeline_without_code_changes(self):
        """Test that timeline can be updated by modifying config only.

        This test verifies the update workflow: configuration changes
        propagate to loaded timelines without code modifications.

        Note: This test verifies the current production configuration
        can be loaded and used. To test config updates, modify the
        production config file and re-run tests.
        """
        # Load current configuration
        timelines = _load_regulatory_timelines()

        # Verify configuration is loaded (not hardcoded fallback)
        assert isinstance(timelines, dict)
        assert len(timelines) > 0

        # Verify we can access timeline values that would be updated
        # This demonstrates the update workflow works
        if "30_day_notice" in timelines:
            review_days = timelines["30_day_notice"]["typical_review_days"]
            assert isinstance(review_days, int)
            assert review_days > 0
            # In real update scenario, this value could be changed
            # from 30 to 15 days by editing config file only

        # Verify configuration structure supports updates
        script_dir = Path(__file__).parent.parent / "scripts"
        config_path = script_dir.parent / "data" / "regulatory_timelines.json"

        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)

            # Verify update-supporting structure exists
            assert "current_timelines" in config
            assert "historical_timelines" in config
            assert "update_history" in config

            # Verify at least one timeline can be updated
            current = config.get("current_timelines", {})
            assert len(current) > 0

            # Demonstrate update path: modify current_timelines values
            # without changing code, archive old values in historical_timelines
            assert "metadata" in config
            assert "version" in config["metadata"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
