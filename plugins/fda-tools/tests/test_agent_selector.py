#!/usr/bin/env python3
"""
Tests for AgentSelector - Multi-dimensional team selection

Tests cover:
1. Agent ranking algorithm
2. Weighted scoring (dimension 40%, language 30%, domain 20%, model 10%)
3. Coordination pattern selection
4. Implementation agent selection
5. Team size limits
6. Review team composition
"""

import pytest
from agent_registry import UniversalAgentRegistry
from agent_selector import AgentSelector, ReviewTeam
from task_analyzer import TaskProfile


class TestAgentRanking:
    """Test agent ranking and scoring algorithm."""

    def setup_method(self):
        self.registry = UniversalAgentRegistry()
        self.selector = AgentSelector(self.registry)

    def test_security_dimension_selects_security_agents(self):
        profile = TaskProfile(
            task_type="security_audit",
            languages=["python"],
            review_dimensions={"security": 0.9, "code_quality": 0.5},
        )
        team = self.selector.select_review_team(profile, max_agents=5)

        # Should select security-focused agents
        agent_names = [a["name"] for a in team.core_agents]
        assert any("security" in name.lower() for name in agent_names)

    def test_language_match_prioritized(self):
        profile = TaskProfile(
            task_type="bug_fix",
            languages=["python"],
            review_dimensions={"code_quality": 0.7},
        )
        team = self.selector.select_review_team(profile, max_agents=5)

        # Should include Python specialist
        all_agents = team.core_agents + team.language_agents
        agent_names = [a["name"] for a in all_agents]
        assert any("python" in name.lower() for name in agent_names)

    def test_dimension_scoring_weight(self):
        # High security dimension should rank security agents higher
        profile = TaskProfile(
            task_type="code_review",
            languages=[],
            review_dimensions={"security": 0.9, "testing": 0.3},
        )
        team = self.selector.select_review_team(profile, max_agents=3)

        # First core agent should be security-related
        if team.core_agents:
            first_agent = team.core_agents[0]["name"]
            assert "security" in first_agent.lower() or "qa-sec" in first_agent.lower()


class TestCoordinationPatternSelection:
    """Test coordination pattern recommendation based on team size."""

    def setup_method(self):
        self.registry = UniversalAgentRegistry()
        self.selector = AgentSelector(self.registry)

    def test_peer_to_peer_small_team(self):
        profile = TaskProfile(
            task_type="bug_fix",
            languages=["python"],
            review_dimensions={"code_quality": 0.5},
        )
        team = self.selector.select_review_team(profile, max_agents=3)

        assert team.coordination_pattern == "peer-to-peer"
        assert team.coordinator is None

    def test_master_worker_medium_team(self):
        profile = TaskProfile(
            task_type="security_audit",
            languages=["python", "typescript"],
            review_dimensions={"security": 0.9, "code_quality": 0.8, "testing": 0.7},
        )
        team = self.selector.select_review_team(profile, max_agents=6)

        assert team.coordination_pattern in ["master-worker", "peer-to-peer"]

    def test_hierarchical_large_team(self):
        profile = TaskProfile(
            task_type="security_audit",
            languages=["python", "typescript", "rust"],
            review_dimensions={
                "security": 0.9,
                "code_quality": 0.8,
                "testing": 0.8,
                "documentation": 0.7,
                "performance": 0.7,
            },
        )
        team = self.selector.select_review_team(profile, max_agents=10)

        if team.total_agents >= 7:
            assert team.coordination_pattern == "hierarchical"
            assert team.coordinator is not None
            assert "coordinator" in team.coordinator.lower()


class TestImplementationAgentSelection:
    """Test single best implementer selection for Linear assignment."""

    def setup_method(self):
        self.registry = UniversalAgentRegistry()
        self.selector = AgentSelector(self.registry)

    def test_language_specific_implementer(self):
        profile = TaskProfile(
            task_type="bug_fix",
            languages=["python"],
            review_dimensions={"code_quality": 0.7},
        )
        impl_agent = self.selector.select_implementation_agent(profile)

        assert impl_agent is not None
        assert "python" in impl_agent.lower() or "fullstack" in impl_agent.lower()

    def test_security_fix_implementer(self):
        profile = TaskProfile(
            task_type="security_audit",
            languages=["python"],
            review_dimensions={"security": 0.9},
        )
        impl_agent = self.selector.select_implementation_agent(profile)

        assert impl_agent is not None
        # Should prefer security specialist
        assert "security" in impl_agent.lower() or "python" in impl_agent.lower()

    def test_testing_implementer(self):
        profile = TaskProfile(
            task_type="testing",
            languages=["python"],
            review_dimensions={"testing": 0.9},
        )
        impl_agent = self.selector.select_implementation_agent(profile)

        assert impl_agent is not None
        assert "test" in impl_agent.lower() or "qa" in impl_agent.lower()


class TestTeamSizeLimits:
    """Test team size limiting and agent deduplication."""

    def setup_method(self):
        self.registry = UniversalAgentRegistry()
        self.selector = AgentSelector(self.registry)

    def test_respects_max_agents_limit(self):
        profile = TaskProfile(
            task_type="security_audit",
            languages=["python", "typescript", "rust", "go"],
            review_dimensions={
                "security": 0.9,
                "code_quality": 0.9,
                "testing": 0.9,
                "documentation": 0.9,
                "performance": 0.9,
                "compliance": 0.9,
                "architecture": 0.9,
                "operations": 0.9,
            },
        )
        team = self.selector.select_review_team(profile, max_agents=5)

        assert team.total_agents <= 5

    def test_no_duplicate_agents(self):
        profile = TaskProfile(
            task_type="code_review",
            languages=["python"],
            review_dimensions={"code_quality": 0.8, "testing": 0.7},
        )
        team = self.selector.select_review_team(profile, max_agents=10)

        # Collect all agent names
        all_agents = (
            [a["name"] for a in team.core_agents] +
            [a["name"] for a in team.language_agents] +
            [a["name"] for a in team.domain_agents]
        )

        # Should have no duplicates
        assert len(all_agents) == len(set(all_agents))


class TestReviewTeamComposition:
    """Test review team composition and balance."""

    def setup_method(self):
        self.registry = UniversalAgentRegistry()
        self.selector = AgentSelector(self.registry)

    def test_includes_core_agents(self):
        profile = TaskProfile(
            task_type="security_audit",
            languages=["python"],
            review_dimensions={"security": 0.9},
        )
        team = self.selector.select_review_team(profile, max_agents=5)

        assert len(team.core_agents) > 0

    def test_includes_language_agents_when_detected(self):
        profile = TaskProfile(
            task_type="bug_fix",
            languages=["python", "typescript"],
            review_dimensions={"code_quality": 0.7},
        )
        team = self.selector.select_review_team(profile, max_agents=8)

        assert len(team.language_agents) > 0

    def test_includes_domain_agents_when_detected(self):
        profile = TaskProfile(
            task_type="feature_dev",
            languages=["python"],
            domains=["healthcare", "fda"],
            review_dimensions={"compliance": 0.8, "code_quality": 0.6},
        )
        team = self.selector.select_review_team(profile, max_agents=8)

        # Should include FDA/healthcare domain agents
        if team.domain_agents:
            domain_names = [a["name"] for a in team.domain_agents]
            assert any("fda" in name.lower() or "healthcare" in name.lower() for name in domain_names)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        self.registry = UniversalAgentRegistry()
        self.selector = AgentSelector(self.registry)

    def test_minimal_profile(self):
        profile = TaskProfile(
            task_type="unknown",
            languages=[],
            review_dimensions={},
        )
        team = self.selector.select_review_team(profile, max_agents=3)

        # Should still return a team (fallback to general agents)
        assert team.total_agents > 0

    def test_max_agents_one(self):
        profile = TaskProfile(
            task_type="bug_fix",
            languages=["python"],
            review_dimensions={"code_quality": 0.7},
        )
        team = self.selector.select_review_team(profile, max_agents=1)

        assert team.total_agents == 1
        assert team.coordination_pattern == "peer-to-peer"

    def test_max_agents_zero(self):
        profile = TaskProfile(
            task_type="bug_fix",
            languages=["python"],
            review_dimensions={"code_quality": 0.7},
        )
        team = self.selector.select_review_team(profile, max_agents=0)

        # Should handle gracefully
        assert team.total_agents >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
