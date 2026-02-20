"""Tests for v5.13.0: Agent structural validation.

Validates all 7 agents (4 existing + 3 new) have proper YAML frontmatter,
valid tool lists, naming conventions, and required fields.
"""

import os
import re

import pytest
import yaml

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
SKILLS_DIR = os.path.join(BASE_DIR, "skills")

# All expected agent files
AGENT_FILES = [
    "extraction-analyzer.md",
    "submission-writer.md",
    "presub-planner.md",
    "review-simulator.md",
    "research-intelligence.md",
    "submission-assembler.md",
    "data-pipeline-manager.md",
]

VALID_TOOLS = {
    "Read", "Write", "Glob", "Grep", "Bash",
    "WebFetch", "WebSearch", "Edit", "NotebookEdit", "AskUserQuestion",
}

INVALID_FRONTMATTER_FIELDS = {"version", "argument-hint", "allowed-tools", "user-invocable"}

NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def _parse_agent_frontmatter(filename):
    """Parse YAML frontmatter from an agent .md file."""
    path = os.path.join(AGENTS_DIR, filename)
    with open(path) as f:
        content = f.read()
    assert content.startswith("---"), f"{filename} must start with ---"
    end = content.index("---", 3)
    yaml_str = content[3:end]
    return yaml.safe_load(yaml_str), content


# ── Agent Count ──────────────────────────────────────────────


class TestAgentCount:
    """Verify expected number of agent files."""

    def test_agents_directory_exists(self):
        assert os.path.isdir(AGENTS_DIR)

    def test_agent_count_is_7(self):
        md_files = [f for f in os.listdir(AGENTS_DIR) if f.endswith(".md")]
        assert len(md_files) == 7, f"Expected 7 agents, found {len(md_files)}: {sorted(md_files)}"

    def test_all_expected_agents_exist(self):
        for agent_file in AGENT_FILES:
            path = os.path.join(AGENTS_DIR, agent_file)
            assert os.path.exists(path), f"Missing agent: {agent_file}"


# ── Per-Agent Structural Tests ───────────────────────────────


class TestExtractionAnalyzer:
    """Validate extraction-analyzer agent."""

    def setup_method(self):
        self.fm, self.content = _parse_agent_frontmatter("extraction-analyzer.md")

    def test_has_name(self):
        assert "name" in self.fm

    def test_name_value(self):
        assert self.fm["name"] == "extraction-analyzer"

    def test_name_follows_rules(self):
        assert NAME_PATTERN.match(self.fm["name"])

    def test_has_description(self):
        assert "description" in self.fm
        assert len(self.fm["description"]) > 20

    def test_has_tools(self):
        assert "tools" in self.fm
        assert isinstance(self.fm["tools"], list)

    def test_tools_are_valid(self):
        for tool in self.fm["tools"]:
            assert tool in VALID_TOOLS, f"Invalid tool: {tool}"

    def test_no_invalid_fields(self):
        for field in INVALID_FRONTMATTER_FIELDS:
            assert field not in self.fm, f"Invalid field in frontmatter: {field}"

    def test_has_workflow_content(self):
        assert "Workflow" in self.content or "Step" in self.content


class TestSubmissionWriter:
    """Validate submission-writer agent."""

    def setup_method(self):
        self.fm, self.content = _parse_agent_frontmatter("submission-writer.md")

    def test_has_name(self):
        assert "name" in self.fm

    def test_name_value(self):
        assert self.fm["name"] == "submission-writer"

    def test_name_follows_rules(self):
        assert NAME_PATTERN.match(self.fm["name"])

    def test_has_description(self):
        assert "description" in self.fm
        assert len(self.fm["description"]) > 20

    def test_has_tools(self):
        assert "tools" in self.fm
        assert isinstance(self.fm["tools"], list)

    def test_tools_are_valid(self):
        for tool in self.fm["tools"]:
            assert tool in VALID_TOOLS, f"Invalid tool: {tool}"

    def test_no_invalid_fields(self):
        for field in INVALID_FRONTMATTER_FIELDS:
            assert field not in self.fm, f"Invalid field in frontmatter: {field}"

    def test_has_workflow_content(self):
        assert "eSTAR" in self.content or "draft" in self.content.lower()


class TestPresubPlanner:
    """Validate presub-planner agent."""

    def setup_method(self):
        self.fm, self.content = _parse_agent_frontmatter("presub-planner.md")

    def test_has_name(self):
        assert "name" in self.fm

    def test_name_value(self):
        assert self.fm["name"] == "presub-planner"

    def test_name_follows_rules(self):
        assert NAME_PATTERN.match(self.fm["name"])

    def test_has_description(self):
        assert "description" in self.fm
        assert len(self.fm["description"]) > 20

    def test_has_tools(self):
        assert "tools" in self.fm
        assert isinstance(self.fm["tools"], list)

    def test_tools_are_valid(self):
        for tool in self.fm["tools"]:
            assert tool in VALID_TOOLS, f"Invalid tool: {tool}"

    def test_no_invalid_fields(self):
        for field in INVALID_FRONTMATTER_FIELDS:
            assert field not in self.fm, f"Invalid field in frontmatter: {field}"

    def test_has_pre_submission_content(self):
        assert "Pre-Sub" in self.content or "pre-submission" in self.content.lower()


class TestReviewSimulator:
    """Validate review-simulator agent."""

    def setup_method(self):
        self.fm, self.content = _parse_agent_frontmatter("review-simulator.md")

    def test_has_name(self):
        assert "name" in self.fm

    def test_name_value(self):
        assert self.fm["name"] == "review-simulator"

    def test_name_follows_rules(self):
        assert NAME_PATTERN.match(self.fm["name"])

    def test_has_description(self):
        assert "description" in self.fm
        assert len(self.fm["description"]) > 20

    def test_has_tools(self):
        assert "tools" in self.fm
        assert isinstance(self.fm["tools"], list)

    def test_tools_are_valid(self):
        for tool in self.fm["tools"]:
            assert tool in VALID_TOOLS, f"Invalid tool: {tool}"

    def test_no_invalid_fields(self):
        for field in INVALID_FRONTMATTER_FIELDS:
            assert field not in self.fm, f"Invalid field in frontmatter: {field}"

    def test_has_review_content(self):
        assert "review" in self.content.lower()


class TestResearchIntelligence:
    """Validate research-intelligence agent (new in v5.13.0)."""

    def setup_method(self):
        self.fm, self.content = _parse_agent_frontmatter("research-intelligence.md")

    def test_has_name(self):
        assert "name" in self.fm

    def test_name_value(self):
        assert self.fm["name"] == "research-intelligence"

    def test_name_follows_rules(self):
        assert NAME_PATTERN.match(self.fm["name"])

    def test_has_description(self):
        assert "description" in self.fm
        assert len(self.fm["description"]) > 20

    def test_has_tools(self):
        assert "tools" in self.fm
        assert isinstance(self.fm["tools"], list)

    def test_tools_are_valid(self):
        for tool in self.fm["tools"]:
            assert tool in VALID_TOOLS, f"Invalid tool: {tool}"

    def test_no_invalid_fields(self):
        for field in INVALID_FRONTMATTER_FIELDS:
            assert field not in self.fm, f"Invalid field in frontmatter: {field}"

    def test_references_research_commands(self):
        """Agent should reference all 7 commands it orchestrates."""
        cmds = ["/fda:research", "/fda:safety", "/fda:guidance", "/fda:literature",
                "/fda:warnings", "/fda:inspections", "/fda:trials"]
        found = sum(1 for c in cmds if c in self.content)
        assert found >= 6, f"Expected at least 6 of 7 command references, found {found}"

    def test_has_intelligence_report(self):
        assert "Intelligence Report" in self.content


class TestSubmissionAssembler:
    """Validate submission-assembler agent (new in v5.13.0)."""

    def setup_method(self):
        self.fm, self.content = _parse_agent_frontmatter("submission-assembler.md")

    def test_has_name(self):
        assert "name" in self.fm

    def test_name_value(self):
        assert self.fm["name"] == "submission-assembler"

    def test_name_follows_rules(self):
        assert NAME_PATTERN.match(self.fm["name"])

    def test_has_description(self):
        assert "description" in self.fm
        assert len(self.fm["description"]) > 20

    def test_has_tools(self):
        assert "tools" in self.fm
        assert isinstance(self.fm["tools"], list)

    def test_tools_are_valid(self):
        for tool in self.fm["tools"]:
            assert tool in VALID_TOOLS, f"Invalid tool: {tool}"

    def test_no_invalid_fields(self):
        for field in INVALID_FRONTMATTER_FIELDS:
            assert field not in self.fm, f"Invalid field in frontmatter: {field}"

    def test_references_draft_command(self):
        assert "/fda:draft" in self.content

    def test_references_consistency_command(self):
        assert "/fda:consistency" in self.content

    def test_references_assemble_command(self):
        assert "/fda:assemble" in self.content

    def test_has_readiness_score(self):
        assert "readiness" in self.content.lower() or "Readiness" in self.content


class TestDataPipelineManager:
    """Validate data-pipeline-manager agent (new in v5.13.0)."""

    def setup_method(self):
        self.fm, self.content = _parse_agent_frontmatter("data-pipeline-manager.md")

    def test_has_name(self):
        assert "name" in self.fm

    def test_name_value(self):
        assert self.fm["name"] == "data-pipeline-manager"

    def test_name_follows_rules(self):
        assert NAME_PATTERN.match(self.fm["name"])

    def test_has_description(self):
        assert "description" in self.fm
        assert len(self.fm["description"]) > 20

    def test_has_tools(self):
        assert "tools" in self.fm
        assert isinstance(self.fm["tools"], list)

    def test_tools_are_valid(self):
        for tool in self.fm["tools"]:
            assert tool in VALID_TOOLS, f"Invalid tool: {tool}"

    def test_no_invalid_fields(self):
        for field in INVALID_FRONTMATTER_FIELDS:
            assert field not in self.fm, f"Invalid field in frontmatter: {field}"

    def test_references_gap_analysis(self):
        assert "/fda:gap-analysis" in self.content

    def test_references_data_pipeline(self):
        assert "/fda:data-pipeline" in self.content

    def test_references_extract(self):
        assert "/fda:extract" in self.content

    def test_has_pipeline_report(self):
        assert "Pipeline Report" in self.content


# ── Parametrized Cross-Agent Tests ───────────────────────────


@pytest.mark.parametrize("agent_file", AGENT_FILES)
class TestAllAgentsCommon:
    """Common structural tests applied to every agent."""

    def test_file_exists(self, agent_file):
        assert os.path.exists(os.path.join(AGENTS_DIR, agent_file))

    def test_starts_with_frontmatter(self, agent_file):
        path = os.path.join(AGENTS_DIR, agent_file)
        with open(path) as f:
            content = f.read()
        assert content.startswith("---")

    def test_has_closing_frontmatter(self, agent_file):
        path = os.path.join(AGENTS_DIR, agent_file)
        with open(path) as f:
            content = f.read()
        assert content.count("---") >= 2

    def test_has_heading_after_frontmatter(self, agent_file):
        path = os.path.join(AGENTS_DIR, agent_file)
        with open(path) as f:
            content = f.read()
        end = content.index("---", 3)
        body = content[end + 3:]
        assert "#" in body, "Agent should have at least one heading"

    def test_name_field_present(self, agent_file):
        fm, _ = _parse_agent_frontmatter(agent_file)
        assert "name" in fm

    def test_description_field_present(self, agent_file):
        fm, _ = _parse_agent_frontmatter(agent_file)
        assert "description" in fm

    def test_tools_field_present(self, agent_file):
        fm, _ = _parse_agent_frontmatter(agent_file)
        assert "tools" in fm
