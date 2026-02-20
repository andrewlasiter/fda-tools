#!/usr/bin/env python3
"""
Tests for ExecutionCoordinator - Multi-agent workflow orchestration

Tests cover:
1. Execution plan generation (4-phase structure)
2. Result aggregation and deduplication
3. Severity-based sorting
4. Finding grouping by file/type/agent
5. Simulated agent execution
"""

import pytest
from execution_coordinator import (
    ExecutionCoordinator,
    ExecutionPlan,
    ExecutionPhase,
    Finding,
    AggregatedFindings,
)
from agent_selector import ReviewTeam
from task_analyzer import TaskProfile


class TestExecutionPlanGeneration:
    """Test execution plan creation with 4-phase structure."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_creates_four_phases(self):
        team = ReviewTeam(
            core_agents=[
                {"name": "voltagent-qa-sec:code-reviewer", "category": "qa-sec"},
                {"name": "voltagent-qa-sec:security-auditor", "category": "qa-sec"},
            ],
            language_agents=[{"name": "voltagent-lang:python-pro", "category": "lang"}],
            domain_agents=[],
            coordination_pattern="peer-to-peer",
            coordinator=None,
            total_agents=3,
        )

        profile = TaskProfile(
            task_type="security_audit",
            languages=["python"],
            review_dimensions={"security": 0.9},
        )

        plan = self.coordinator.create_execution_plan(team, profile)

        # Should have 4 phases (Initial Analysis, Specialist Review, Issue Creation)
        # Note: No Phase 3 (Integration) because coordinator is None
        assert len(plan.phases) >= 3
        assert len(plan.phases) <= 4

    def test_phase_one_has_core_agents(self):
        team = ReviewTeam(
            core_agents=[
                {"name": "agent1", "category": "qa-sec"},
                {"name": "agent2", "category": "qa-sec"},
            ],
            language_agents=[],
            domain_agents=[],
            coordination_pattern="peer-to-peer",
            coordinator=None,
            total_agents=2,
        )

        profile = TaskProfile(task_type="code_review")

        plan = self.coordinator.create_execution_plan(team, profile)

        # Phase 1 should have core agents
        phase1 = plan.phases[0]
        assert phase1.phase == 1
        assert phase1.name == "Initial Analysis"
        assert len(phase1.assigned_agents) > 0
        assert phase1.parallel is True

    def test_includes_coordinator_when_present(self):
        team = ReviewTeam(
            core_agents=[{"name": f"agent{i}", "category": "qa-sec"} for i in range(7)],
            language_agents=[],
            domain_agents=[],
            coordination_pattern="master-worker",
            coordinator="voltagent-meta:multi-agent-coordinator",
            total_agents=7,
        )

        profile = TaskProfile(task_type="security_audit")

        plan = self.coordinator.create_execution_plan(team, profile)

        # Should have Phase 3 (Integration) with coordinator
        assert len(plan.phases) == 4
        phase3 = plan.phases[2]
        assert phase3.name == "Integration Review"
        assert phase3.assigned_agents == ["voltagent-meta:multi-agent-coordinator"]
        assert phase3.parallel is False

    def test_sets_proper_dependencies(self):
        team = ReviewTeam(
            core_agents=[{"name": "agent1", "category": "qa-sec"}],
            language_agents=[{"name": "agent2", "category": "lang"}],
            domain_agents=[],
            coordination_pattern="peer-to-peer",
            coordinator=None,
            total_agents=2,
        )

        profile = TaskProfile(task_type="code_review")

        plan = self.coordinator.create_execution_plan(team, profile)

        # Phase 2 should depend on Phase 1
        if len(plan.phases) >= 2:
            assert 1 in plan.phases[1].dependencies

        # Last phase (Issue Creation) should have dependencies
        assert len(plan.phases[-1].dependencies) > 0

    def test_parallel_and_sequential_execution(self):
        team = ReviewTeam(
            core_agents=[{"name": "agent1", "category": "qa-sec"}],
            language_agents=[{"name": "agent2", "category": "lang"}],
            domain_agents=[],
            coordination_pattern="peer-to-peer",
            coordinator=None,
            total_agents=2,
        )

        profile = TaskProfile(task_type="security_audit")

        plan = self.coordinator.create_execution_plan(team, profile)

        # Phase 1 and 2 should be parallel
        assert plan.phases[0].parallel is True
        if len(plan.phases) >= 2:
            assert plan.phases[1].parallel is True

        # Issue creation phase should be sequential
        assert plan.phases[-1].parallel is False


class TestResultAggregation:
    """Test result aggregation and deduplication."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_aggregates_findings_from_multiple_agents(self):
        findings = [
            Finding(
                type="security",
                severity="HIGH",
                description="SQL injection vulnerability",
                location="api/auth.py:42",
                agent="security-auditor",
            ),
            Finding(
                type="code_quality",
                severity="MEDIUM",
                description="Complex function needs refactoring",
                location="api/auth.py:100",
                agent="code-reviewer",
            ),
        ]

        results = self.coordinator._aggregate_findings(findings)

        assert len(results.findings) == 2

    def test_deduplicates_identical_findings(self):
        findings = [
            Finding(
                type="security",
                severity="HIGH",
                description="SQL injection",
                location="api/auth.py:42",
                agent="agent1",
            ),
            Finding(
                type="security",
                severity="HIGH",
                description="SQL injection",
                location="api/auth.py:42",
                agent="agent2",
            ),
        ]

        results = self.coordinator._aggregate_findings(findings)

        # Should deduplicate to 1 finding (same location + type)
        assert len(results.findings) == 1

    def test_keeps_higher_severity_when_deduplicating(self):
        findings = [
            Finding(
                type="security",
                severity="MEDIUM",
                description="Issue",
                location="api/auth.py:42",
                agent="agent1",
            ),
            Finding(
                type="security",
                severity="HIGH",
                description="Issue",
                location="api/auth.py:42",
                agent="agent2",
            ),
        ]

        results = self.coordinator._aggregate_findings(findings)

        # Should keep the HIGH severity one
        assert len(results.findings) == 1
        assert results.findings[0].severity == "HIGH"

    def test_severity_counts(self):
        findings = [
            Finding(type="security", severity="CRITICAL", description="Critical issue", location="file.py:0", agent="agent1"),
            Finding(type="security", severity="HIGH", description="High issue 1", location="file.py:1", agent="agent1"),
            Finding(type="security", severity="HIGH", description="High issue 2", location="file.py:2", agent="agent1"),
            Finding(type="security", severity="MEDIUM", description="Medium issue", location="file.py:3", agent="agent1"),
            Finding(type="security", severity="LOW", description="Low issue", location="file.py:4", agent="agent1"),
        ]

        results = self.coordinator._aggregate_findings(findings)

        # All have different locations, so no deduplication
        assert results.critical_count == 1
        assert results.high_count == 2
        assert results.medium_count == 1
        assert results.low_count == 1

    def test_severity_sorting(self):
        findings = [
            Finding(type="security", severity="LOW", description="Low", location="file.py:1", agent="agent1"),
            Finding(type="security", severity="CRITICAL", description="Critical", location="file.py:2", agent="agent1"),
            Finding(type="security", severity="MEDIUM", description="Medium", location="file.py:3", agent="agent1"),
            Finding(type="security", severity="HIGH", description="High", location="file.py:4", agent="agent1"),
        ]

        results = self.coordinator._aggregate_findings(findings)

        # Should be sorted CRITICAL > HIGH > MEDIUM > LOW
        assert results.findings[0].severity == "CRITICAL"
        assert results.findings[1].severity == "HIGH"
        assert results.findings[2].severity == "MEDIUM"
        assert results.findings[3].severity == "LOW"

    def test_groups_by_file(self):
        findings = [
            Finding(type="security", severity="HIGH", description="Issue 1", location="api/auth.py:10", agent="agent1"),
            Finding(type="security", severity="HIGH", description="Issue 2", location="api/auth.py:20", agent="agent1"),
            Finding(type="security", severity="HIGH", description="Issue 3", location="api/views.py:30", agent="agent1"),
        ]

        results = self.coordinator._aggregate_findings(findings)

        assert "api/auth.py" in results.by_file
        assert "api/views.py" in results.by_file
        assert len(results.by_file["api/auth.py"]) == 2
        assert len(results.by_file["api/views.py"]) == 1

    def test_groups_by_type(self):
        findings = [
            Finding(type="security", severity="HIGH", description="Issue 1", location="file.py:1", agent="agent1"),
            Finding(type="security", severity="HIGH", description="Issue 2", location="file.py:2", agent="agent1"),
            Finding(type="testing", severity="MEDIUM", description="Issue 3", location="file.py:3", agent="agent1"),
        ]

        results = self.coordinator._aggregate_findings(findings)

        assert "security" in results.by_type
        assert "testing" in results.by_type
        assert len(results.by_type["security"]) == 2
        assert len(results.by_type["testing"]) == 1

    def test_groups_by_agent(self):
        findings = [
            Finding(type="security", severity="HIGH", description="Issue 1", location="file.py:1", agent="security-auditor"),
            Finding(type="security", severity="HIGH", description="Issue 2", location="file.py:2", agent="security-auditor"),
            Finding(type="code_quality", severity="MEDIUM", description="Issue 3", location="file.py:3", agent="code-reviewer"),
        ]

        results = self.coordinator._aggregate_findings(findings)

        assert "security-auditor" in results.by_agent
        assert "code-reviewer" in results.by_agent
        assert len(results.by_agent["security-auditor"]) == 2
        assert len(results.by_agent["code-reviewer"]) == 1


class TestExecutePlan:
    """Test execution plan execution."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_executes_plan_and_returns_results(self):
        team = ReviewTeam(
            core_agents=[
                {"name": "voltagent-qa-sec:security-auditor", "category": "qa-sec"},
            ],
            language_agents=[],
            domain_agents=[],
            coordination_pattern="peer-to-peer",
            coordinator=None,
            total_agents=1,
        )

        profile = TaskProfile(task_type="security_audit")
        plan = self.coordinator.create_execution_plan(team, profile)

        results = self.coordinator.execute_plan(plan)

        # Should return AggregatedFindings
        assert isinstance(results, AggregatedFindings)
        assert isinstance(results.findings, list)

    def test_simulates_security_agent_findings(self):
        findings = self.coordinator._simulate_agent_findings("voltagent-qa-sec:security-auditor", 1)

        assert len(findings) > 0
        assert findings[0].type == "security"
        assert findings[0].severity == "HIGH"

    def test_simulates_testing_agent_findings(self):
        findings = self.coordinator._simulate_agent_findings("voltagent-qa-sec:test-automator", 1)

        assert len(findings) > 0
        assert findings[0].type == "testing"

    def test_simulates_code_reviewer_findings(self):
        # The actual implementation checks for "code-reviewer" in the lowercase agent name
        findings = self.coordinator._simulate_agent_findings("code-reviewer", 1)

        assert len(findings) > 0
        assert findings[0].type == "code_quality"


class TestFormatFindingsReport:
    """Test findings report formatting."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_formats_report(self):
        findings = [
            Finding(
                type="security",
                severity="CRITICAL",
                description="SQL injection vulnerability",
                location="api/auth.py:42",
                recommendation="Use parameterized queries",
                agent="security-auditor",
            ),
            Finding(
                type="testing",
                severity="MEDIUM",
                description="Missing test coverage",
                location="tests/test_auth.py",
                agent="test-automator",
            ),
        ]

        results = self.coordinator._aggregate_findings(findings)
        report = self.coordinator.format_findings_report(results)

        # Should contain key sections
        assert "MULTI-AGENT REVIEW FINDINGS REPORT" in report
        assert "Summary:" in report
        assert "Total Findings: 2" in report
        assert "CRITICAL: 1" in report
        assert "MEDIUM: 1" in report
        assert "Findings by Type:" in report
        assert "Findings by File:" in report
        assert "Top Findings:" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
