#!/usr/bin/env python3
"""
Test suite for FDA Regulatory Expert Agent Registry (FDA-73).

Tests cover:
  - AgentRegistry (discovery, listing, search, capabilities, team assembly)
  - AgentTeamCoordinator (review plans, task matrices, coordination patterns)
  - YAML/frontmatter parsing (with and without PyYAML)
  - Constants validation (capability categories, device maps, pathway maps)
  - Edge cases (empty directories, missing files, invalid config)

Minimum 35 tests required for this module.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure scripts directory is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from agent_registry import (
    AgentRegistry,
    AgentTeamCoordinator,
    CAPABILITY_CATEGORIES,
    DEVICE_AGENT_MAP,
    PATHWAY_AGENT_MAP,
    SKILLS_DIR,
    _parse_frontmatter,
    _parse_yaml_file,
)


# ==================================================================
# Test Fixtures
# ==================================================================

@pytest.fixture
def registry():
    """Create a registry pointing to the real skills directory."""
    return AgentRegistry()


@pytest.fixture
def empty_registry(tmp_path):
    """Create a registry pointing to an empty directory."""
    return AgentRegistry(skills_dir=tmp_path)


@pytest.fixture
def mock_skills_dir(tmp_path):
    """Create a mock skills directory with test agents."""
    # Agent 1: Complete agent with SKILL.md and agent.yaml
    agent1_dir = tmp_path / "fda-test-expert"
    agent1_dir.mkdir()
    (agent1_dir / "SKILL.md").write_text(
        "---\n"
        "name: fda-test-expert\n"
        "description: Test expert agent for unit testing with biocompatibility and 510(k) knowledge and ISO 14971 risk management expertise.\n"
        "---\n\n"
        "# FDA Test Expert\n\n"
        "## Overview\n\n"
        "This agent provides test support for FDA regulatory workflows.\n\n"
        "## Capabilities\n\n"
        "- Biocompatibility testing per ISO 10993\n"
        "- Risk management per ISO 14971\n"
        "- 510(k) submission support\n"
        "- Quality systems compliance\n\n"
        + "## Detailed Knowledge\n\n" + ("Additional content. " * 100) + "\n"
    )
    (agent1_dir / "agent.yaml").write_text(
        "name: fda-test-expert\n"
        "model: sonnet\n"
        "description: Test expert agent\n"
    )
    refs_dir = agent1_dir / "references"
    refs_dir.mkdir()
    (refs_dir / "ref1.md").write_text("Reference 1")

    # Agent 2: Minimal agent with only SKILL.md
    agent2_dir = tmp_path / "fda-minimal-support"
    agent2_dir.mkdir()
    (agent2_dir / "SKILL.md").write_text(
        "---\n"
        "name: fda-minimal-support\n"
        "description: Minimal support agent.\n"
        "---\n\n"
        "# Minimal Support\n\n"
        "Basic agent.\n"
    )

    # Agent 3: Short SKILL.md, has yaml
    agent3_dir = tmp_path / "fda-short-skill"
    agent3_dir.mkdir()
    (agent3_dir / "SKILL.md").write_text(
        "---\nname: fda-short-skill\ndescription: Short.\n---\n\n# Short\nBrief.\n"
    )
    (agent3_dir / "agent.yaml").write_text("name: fda-short-skill\n")

    # Non-agent directory (no SKILL.md)
    non_agent = tmp_path / "not-an-agent"
    non_agent.mkdir()
    (non_agent / "README.md").write_text("Not an agent")

    # Hidden directory (should be skipped)
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "SKILL.md").write_text("---\nname: hidden\n---\n")

    return tmp_path


@pytest.fixture
def mock_registry(mock_skills_dir):
    """Create a registry with mock skills directory."""
    return AgentRegistry(skills_dir=mock_skills_dir)


@pytest.fixture
def coordinator(registry):
    """Create a team coordinator with real registry."""
    return AgentTeamCoordinator(registry=registry)


@pytest.fixture
def mock_coordinator(mock_registry):
    """Create a team coordinator with mock registry."""
    return AgentTeamCoordinator(registry=mock_registry)


# ==================================================================
# Frontmatter and YAML Parsing Tests
# ==================================================================

class TestParsing:
    """Tests for YAML and frontmatter parsing."""

    def test_parse_frontmatter_basic(self):
        """Should parse basic YAML frontmatter."""
        content = "---\nname: test-agent\ndescription: A test agent\n---\n\n# Content"
        result = _parse_frontmatter(content)
        assert result["name"] == "test-agent"
        assert result["description"] == "A test agent"

    def test_parse_frontmatter_no_frontmatter(self):
        """Content without frontmatter should return empty dict."""
        result = _parse_frontmatter("# Just a heading\n\nSome content")
        assert result == {}

    def test_parse_frontmatter_empty_content(self):
        """Empty content should return empty dict."""
        result = _parse_frontmatter("")
        assert result == {}

    def test_parse_yaml_file_nonexistent(self, tmp_path):
        """Non-existent file should return empty dict."""
        result = _parse_yaml_file(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_parse_yaml_file_valid(self, tmp_path):
        """Valid YAML file should parse correctly."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("name: test\nmodel: sonnet\n")
        result = _parse_yaml_file(yaml_file)
        assert result["name"] == "test"


# ==================================================================
# AgentRegistry Discovery Tests
# ==================================================================

class TestAgentRegistryDiscovery:
    """Tests for agent discovery and loading."""

    def test_discovers_agents_from_real_skills(self, registry):
        """Registry should discover agents from real skills directory."""
        agents = registry.list_agents()
        assert len(agents) > 0

    def test_discovers_mock_agents(self, mock_registry):
        """Registry should discover agents from mock skills directory."""
        agents = mock_registry.list_agents()
        assert len(agents) == 3  # test-expert, minimal-support, short-skill

    def test_skips_non_agent_directories(self, mock_registry):
        """Should skip directories without SKILL.md."""
        agents = mock_registry.list_agents()
        names = [a["name"] for a in agents]
        assert "not-an-agent" not in names

    def test_skips_hidden_directories(self, mock_registry):
        """Should skip hidden directories."""
        agents = mock_registry.list_agents()
        names = [a["name"] for a in agents]
        assert "hidden" not in names

    def test_empty_skills_dir_returns_empty_list(self, empty_registry):
        """Empty skills directory should return empty list."""
        agents = empty_registry.list_agents()
        assert len(agents) == 0

    def test_lazy_loading(self, mock_registry):
        """Registry should not load until first access."""
        assert mock_registry._loaded is False
        mock_registry.list_agents()
        assert mock_registry._loaded is True


# ==================================================================
# AgentRegistry API Tests
# ==================================================================

class TestAgentRegistryAPI:
    """Tests for AgentRegistry public API methods."""

    def test_list_agents_returns_sorted(self, mock_registry):
        """list_agents should return agents sorted by name."""
        agents = mock_registry.list_agents()
        names = [a["name"] for a in agents]
        assert names == sorted(names)

    def test_list_agents_filter_by_type(self, mock_registry):
        """list_agents should filter by agent type."""
        experts = mock_registry.list_agents(agent_type="expert")
        for agent in experts:
            assert agent["type"] == "expert"

    def test_get_agent_by_name(self, mock_registry):
        """get_agent should return agent by exact name."""
        agent = mock_registry.get_agent("fda-test-expert")
        assert agent is not None
        assert agent["name"] == "fda-test-expert"

    def test_get_agent_not_found(self, mock_registry):
        """get_agent should return None for non-existent agent."""
        agent = mock_registry.get_agent("non-existent-agent")
        assert agent is None

    def test_agent_has_required_fields(self, mock_registry):
        """Agent dict should have all required fields."""
        agent = mock_registry.get_agent("fda-test-expert")
        required = [
            "name", "directory", "description", "type",
            "has_skill_md", "has_agent_yaml", "has_references",
            "reference_count", "skill_lines", "skill_words",
            "capabilities", "yaml_config", "frontmatter",
        ]
        for field in required:
            assert field in agent, f"Missing field: {field}"

    def test_agent_type_detection_expert(self, mock_registry):
        """Agent with 'expert' in name should be type 'expert'."""
        agent = mock_registry.get_agent("fda-test-expert")
        assert agent["type"] == "expert"

    def test_agent_type_detection_support(self, mock_registry):
        """Agent with 'support' in name should be type 'support'."""
        agent = mock_registry.get_agent("fda-minimal-support")
        assert agent["type"] == "support"

    def test_agent_references_detected(self, mock_registry):
        """Agent with references directory should report references."""
        agent = mock_registry.get_agent("fda-test-expert")
        assert agent["has_references"] is True
        assert agent["reference_count"] == 1

    def test_agent_yaml_detected(self, mock_registry):
        """Agent with agent.yaml should report it."""
        agent = mock_registry.get_agent("fda-test-expert")
        assert agent["has_agent_yaml"] is True

    def test_agent_without_yaml_detected(self, mock_registry):
        """Agent without agent.yaml should report it."""
        agent = mock_registry.get_agent("fda-minimal-support")
        assert agent["has_agent_yaml"] is False


# ==================================================================
# Agent Search Tests
# ==================================================================

class TestAgentSearch:
    """Tests for agent search functionality."""

    def test_search_by_name(self, mock_registry):
        """Search by name should find matching agents."""
        results = mock_registry.search_agents("test")
        assert len(results) >= 1
        assert results[0]["name"] == "fda-test-expert"

    def test_search_by_description(self, mock_registry):
        """Search by description keyword should find matching agents."""
        results = mock_registry.search_agents("unit testing")
        assert len(results) >= 1

    def test_search_no_results(self, mock_registry):
        """Search with no matches should return empty list."""
        results = mock_registry.search_agents("xyznonexistent")
        assert len(results) == 0

    def test_search_results_sorted_by_relevance(self, mock_registry):
        """Search results should be sorted by relevance score."""
        # Name match scores higher than description match
        results = mock_registry.search_agents("expert")
        if len(results) > 1:
            # First result should have name match (higher score)
            assert "expert" in results[0]["name"].lower()

    def test_find_by_capability(self, mock_registry):
        """find_agents_by_capability should find agents with matching capability."""
        results = mock_registry.find_agents_by_capability("ISO 10993")
        assert len(results) >= 1


# ==================================================================
# Team Assembly Tests
# ==================================================================

class TestTeamAssembly:
    """Tests for team assembly functionality."""

    def test_assemble_generic_team(self, registry):
        """Should assemble a team for generic device type."""
        team = registry.assemble_team(device_type="generic")
        assert "team_size" in team
        assert "core_agents" in team
        assert "specialty_agents" in team
        assert "unavailable_agents" in team
        assert "coordination_pattern" in team

    def test_assemble_samd_team(self, registry):
        """SaMD team should include software expert."""
        team = registry.assemble_team(device_type="SaMD")
        all_names = [a["name"] for a in team["core_agents"] + team["specialty_agents"]]
        # fda-software-ai-expert should be in the team if it exists in skills
        # (it may be in unavailable if not found)
        found = "fda-software-ai-expert" in all_names or "fda-software-ai-expert" in team["unavailable_agents"]
        assert found

    def test_assemble_with_pathway(self, registry):
        """Pathway-specific agents should be included."""
        team = registry.assemble_team(
            device_type="generic",
            submission_pathway="PMA",
        )
        all_names = (
            [a["name"] for a in team["core_agents"] + team["specialty_agents"]]
            + team["unavailable_agents"]
        )
        # PMA pathway should include clinical expert
        assert "fda-clinical-expert" in all_names

    def test_assemble_class_iii_includes_clinical(self, registry):
        """Class III should include clinical and postmarket experts."""
        team = registry.assemble_team(device_class="III")
        all_names = (
            [a["name"] for a in team["core_agents"] + team["specialty_agents"]]
            + team["unavailable_agents"]
        )
        assert "fda-clinical-expert" in all_names
        assert "fda-postmarket-expert" in all_names

    def test_team_no_duplicates(self, registry):
        """Team should not have duplicate agent names."""
        team = registry.assemble_team(
            device_type="SaMD",
            submission_pathway="510k",
            device_class="II",
        )
        all_names = (
            [a["name"] for a in team["core_agents"]]
            + [a["name"] for a in team["specialty_agents"]]
            + team["unavailable_agents"]
        )
        assert len(all_names) == len(set(all_names))

    def test_coordination_pattern_small_team(self, mock_registry):
        """Small team should get peer-to-peer pattern."""
        team = mock_registry.assemble_team(device_type="generic")
        if team["team_size"] <= 3:
            assert team["coordination_pattern"]["pattern"] == "peer-to-peer"

    def test_team_with_additional_capabilities(self, registry):
        """Additional capabilities should pull in more agents."""
        team_basic = registry.assemble_team(device_type="generic")
        team_extra = registry.assemble_team(
            device_type="generic",
            additional_capabilities=["cybersecurity"],
        )
        # Team with extra capabilities should have same or more agents
        assert team_extra["team_size"] >= team_basic["team_size"]


# ==================================================================
# Agent Validation Tests
# ==================================================================

class TestAgentValidation:
    """Tests for agent validation functionality."""

    def test_validate_all_returns_report(self, mock_registry):
        """validate_all should return a validation report."""
        report = mock_registry.validate_all_agents()
        assert "total_agents" in report
        assert "overall_score" in report
        assert "agents" in report
        assert "summary" in report

    def test_validate_complete_agent(self, mock_registry):
        """Complete agent should score higher than minimal agent."""
        report = mock_registry.validate_all_agents()
        agent_scores = {a["name"]: a["score"] for a in report["agents"]}
        assert agent_scores["fda-test-expert"] > agent_scores["fda-minimal-support"]

    def test_validate_agent_statuses(self, mock_registry):
        """Agents should be classified as COMPLETE, PARTIAL, or MINIMAL."""
        report = mock_registry.validate_all_agents()
        valid_statuses = {"COMPLETE", "PARTIAL", "MINIMAL"}
        for agent in report["agents"]:
            assert agent["status"] in valid_statuses

    def test_validate_summary_counts(self, mock_registry):
        """Summary should correctly count status categories."""
        report = mock_registry.validate_all_agents()
        summary = report["summary"]
        total = summary["fully_complete"] + summary["partial"] + summary["minimal"]
        assert total == report["total_agents"]

    def test_validate_issues_for_minimal_agent(self, mock_registry):
        """Minimal agent should have validation issues."""
        report = mock_registry.validate_all_agents()
        minimal = [a for a in report["agents"] if a["name"] == "fda-minimal-support"][0]
        assert len(minimal["issues"]) > 0
        assert any("agent.yaml" in issue for issue in minimal["issues"])


# ==================================================================
# Statistics Tests
# ==================================================================

class TestStatistics:
    """Tests for registry statistics."""

    def test_statistics_structure(self, mock_registry):
        """Statistics should have expected structure."""
        stats = mock_registry.get_statistics()
        required = [
            "total_agents", "agent_types", "agents_with_yaml",
            "agents_with_references", "total_skill_lines",
            "total_reference_files", "avg_skill_lines",
        ]
        for field in required:
            assert field in stats, f"Missing field: {field}"

    def test_statistics_counts(self, mock_registry):
        """Statistics counts should match actual data."""
        stats = mock_registry.get_statistics()
        assert stats["total_agents"] == 3
        assert stats["agents_with_yaml"] == 2  # test-expert and short-skill
        assert stats["agents_with_references"] == 1  # only test-expert

    def test_statistics_agent_types(self, mock_registry):
        """Agent type counts should be correct."""
        stats = mock_registry.get_statistics()
        types = stats["agent_types"]
        assert types.get("expert", 0) >= 1
        assert types.get("support", 0) >= 1


# ==================================================================
# AgentTeamCoordinator Tests
# ==================================================================

class TestAgentTeamCoordinator:
    """Tests for team coordination functionality."""

    def test_create_review_plan_structure(self, coordinator):
        """Review plan should have expected structure."""
        plan = coordinator.create_review_plan(
            device_name="Test Device",
            device_type="generic",
            submission_pathway="510k",
        )
        assert "device_name" in plan
        assert "team" in plan
        assert "phases" in plan
        assert "total_estimated_hours" in plan
        assert plan["device_name"] == "Test Device"

    def test_review_plan_has_4_phases(self, coordinator):
        """Review plan should have 4 phases."""
        plan = coordinator.create_review_plan(device_name="Test")
        assert len(plan["phases"]) == 4

    def test_phase_1_is_initial_assessment(self, coordinator):
        """Phase 1 should be Initial Assessment."""
        plan = coordinator.create_review_plan(device_name="Test")
        assert plan["phases"][0]["phase"] == 1
        assert plan["phases"][0]["name"] == "Initial Assessment"
        assert plan["phases"][0]["dependencies"] == []

    def test_phase_2_depends_on_phase_1(self, coordinator):
        """Phase 2 should depend on Phase 1."""
        plan = coordinator.create_review_plan(device_name="Test")
        assert 1 in plan["phases"][1]["dependencies"]

    def test_phase_4_depends_on_phases_2_and_3(self, coordinator):
        """Phase 4 should depend on Phases 2 and 3."""
        plan = coordinator.create_review_plan(device_name="Test")
        phase4 = plan["phases"][3]
        assert 2 in phase4["dependencies"]
        assert 3 in phase4["dependencies"]

    def test_total_hours_positive(self, coordinator):
        """Total estimated hours should be positive."""
        plan = coordinator.create_review_plan(device_name="Test")
        assert plan["total_estimated_hours"] > 0

    def test_task_matrix_generation(self, coordinator):
        """Task matrix should generate tasks from review plan."""
        plan = coordinator.create_review_plan(device_name="Test")
        tasks = coordinator.get_agent_task_matrix(plan)
        assert len(tasks) > 0
        for task in tasks:
            assert "phase" in task
            assert "agent" in task
            assert "description" in task

    def test_task_matrix_estimated_hours(self, coordinator):
        """Task matrix should distribute hours per agent."""
        plan = coordinator.create_review_plan(device_name="Test")
        tasks = coordinator.get_agent_task_matrix(plan)
        for task in tasks:
            assert task["estimated_hours"] > 0


# ==================================================================
# Constants Validation Tests
# ==================================================================

class TestConstants:
    """Validate data constants and configuration."""

    def test_capability_categories_populated(self):
        """All capability categories should have items."""
        for category, items in CAPABILITY_CATEGORIES.items():
            assert len(items) > 0, f"Empty category: {category}"

    def test_device_agent_map_has_generic(self):
        """Device agent map should have a 'generic' fallback."""
        assert "generic" in DEVICE_AGENT_MAP
        assert len(DEVICE_AGENT_MAP["generic"]) > 0

    def test_device_agent_map_all_populated(self):
        """All device types should have recommended agents."""
        for device_type, agents in DEVICE_AGENT_MAP.items():
            assert len(agents) >= 2, f"{device_type} needs more agents"

    def test_pathway_agent_map_has_510k(self):
        """Pathway map should have 510k."""
        assert "510k" in PATHWAY_AGENT_MAP
        assert len(PATHWAY_AGENT_MAP["510k"]) > 0

    def test_pathway_agent_map_has_pma(self):
        """Pathway map should have PMA."""
        assert "PMA" in PATHWAY_AGENT_MAP
        assert len(PATHWAY_AGENT_MAP["PMA"]) > 0

    def test_pathway_agent_map_has_de_novo(self):
        """Pathway map should have De Novo."""
        assert "De Novo" in PATHWAY_AGENT_MAP

    def test_pathway_agent_map_has_ide(self):
        """Pathway map should have IDE."""
        assert "IDE" in PATHWAY_AGENT_MAP

    def test_skills_dir_path_correct(self):
        """SKILLS_DIR should point to a skills directory."""
        assert "skills" in str(SKILLS_DIR)

    def test_real_skills_dir_exists(self):
        """Real skills directory should exist on disk."""
        assert SKILLS_DIR.exists(), f"Skills dir not found: {SKILLS_DIR}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
