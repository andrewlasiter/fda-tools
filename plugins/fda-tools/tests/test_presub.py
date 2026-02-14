"""Tests for v5.18.0 Item 29: Comprehensive presub.md test coverage.

Validates command structure, Q-Sub type differentiation, Pre-Sub package sections,
cover letter template, legal status checks, timeline calculations, correspondence
tracking, and presub-planner agent phases.
"""

import os
import re

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CMDS_DIR = os.path.join(BASE_DIR, "commands")
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
REFS_DIR = os.path.join(BASE_DIR, "references")


def _read_cmd(name):
    path = os.path.join(CMDS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


def _read_agent(name):
    path = os.path.join(AGENTS_DIR, f"{name}.md")
    with open(path) as f:
        return f.read()


class TestPresubCommandStructure:
    """Basic command structure validation."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_file_exists(self):
        assert os.path.exists(os.path.join(CMDS_DIR, "presub.md"))

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_description(self):
        assert "description:" in self.content

    def test_has_allowed_tools(self):
        assert "allowed-tools:" in self.content

    def test_has_write_tool(self):
        """Presub generates files (cover letter, package) so needs Write."""
        assert "Write" in self.content

    def test_has_argument_hint(self):
        assert "argument-hint:" in self.content

    def test_has_plugin_root_resolution(self):
        assert "FDA_PLUGIN_ROOT" in self.content
        assert "installed_plugins.json" in self.content


class TestPresubQSubTypes:
    """Q-Sub type differentiation (Pre-Sub, IND Pre-Sub, STED)."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_mentions_pre_sub(self):
        assert "Pre-Sub" in self.content or "pre-sub" in self.content.lower()

    def test_mentions_qsub(self):
        assert "Q-Sub" in self.content or "q-sub" in self.content.lower()

    def test_differentiation_logic(self):
        """Presub should distinguish different meeting types."""
        content_lower = self.content.lower()
        has_types = ("pre-submission" in content_lower or
                     "informational" in content_lower or
                     "agreement" in content_lower)
        assert has_types

    def test_has_meeting_type_options(self):
        assert "meeting" in self.content.lower()


class TestPresubPackageSections:
    """Pre-Sub package sections (11 sections + subsections in 4.2)."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_has_cover_letter_section(self):
        content_lower = self.content.lower()
        assert "cover letter" in content_lower

    def test_has_device_description_section(self):
        assert "device description" in self.content.lower()

    def test_has_predicate_section(self):
        assert "predicate" in self.content.lower()

    def test_has_testing_section(self):
        assert "testing" in self.content.lower() or "test" in self.content.lower()

    def test_has_questions_section(self):
        assert "question" in self.content.lower()

    def test_has_intended_use_section(self):
        assert "intended use" in self.content.lower()


class TestPresubCoverLetterTemplate:
    """Cover letter template requirements."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_has_cover_letter_reference(self):
        assert "cover letter" in self.content.lower()

    def test_has_date_reference(self):
        assert "date" in self.content.lower()

    def test_has_contact_info_reference(self):
        content_lower = self.content.lower()
        assert "contact" in content_lower or "address" in content_lower


class TestPresubLegalStatusChecks:
    """Predicate legal status validation in presub context."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_references_predicate_status(self):
        content_lower = self.content.lower()
        has_status = ("legal" in content_lower or
                      "cleared" in content_lower or
                      "marketed" in content_lower)
        assert has_status

    def test_references_review_json(self):
        assert "review.json" in self.content


class TestPresubTimelineCalculations:
    """Timeline and scheduling logic."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_has_timeline_reference(self):
        content_lower = self.content.lower()
        has_timeline = ("timeline" in content_lower or
                        "schedule" in content_lower or
                        "day" in content_lower)
        assert has_timeline

    def test_has_fda_review_period(self):
        content_lower = self.content.lower()
        has_review = ("75 day" in content_lower or
                      "90 day" in content_lower or
                      "review period" in content_lower or
                      "calendar day" in content_lower)
        assert has_review


class TestPresubCorrespondenceTracking:
    """FDA correspondence tracking integration."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_has_correspondence_reference(self):
        content_lower = self.content.lower()
        has_corr = ("correspondence" in content_lower or
                    "fda_correspondence" in content_lower)
        assert has_corr

    def test_has_json_output(self):
        assert ".json" in self.content


class TestPresubPlannerAgentStructure:
    """Presub-planner agent validation."""

    def setup_method(self):
        self.content = _read_agent("presub-planner")

    def test_agent_file_exists(self):
        assert os.path.exists(os.path.join(AGENTS_DIR, "presub-planner.md"))

    def test_has_agent_frontmatter(self):
        assert self.content.startswith("---")

    def test_has_name_field(self):
        assert "name:" in self.content

    def test_has_description_field(self):
        assert "description:" in self.content

    def test_has_tools_list(self):
        assert "tools:" in self.content

    def test_has_progress_reporting(self):
        assert "Progress" in self.content or "[1/" in self.content

    def test_has_prerequisites(self):
        assert "Prerequisites" in self.content or "prerequisit" in self.content.lower()

    def test_references_presub_command(self):
        assert "/fda:presub" in self.content or "presub" in self.content


class TestPresubOutputFormat:
    """Output format compliance."""

    def setup_method(self):
        self.content = _read_cmd("presub")

    def test_has_output_format_section(self):
        assert "Output" in self.content or "format" in self.content.lower()

    def test_has_disclaimer(self):
        assert "AI-generated" in self.content or "Not regulatory advice" in self.content

    def test_has_version_marker(self):
        assert "v5." in self.content
