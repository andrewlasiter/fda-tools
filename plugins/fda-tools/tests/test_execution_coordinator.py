#!/usr/bin/env python3
"""
Tests for ExecutionCoordinator - Multi-agent workflow orchestration

Tests cover:
1. Execution plan generation (4-phase structure)
2. Result aggregation and deduplication
3. Severity-based sorting
4. Finding grouping by file/type/agent
5. Error handling and partial results
"""

import pytest
from execution_coordinator import (
    ExecutionCoordinator,
    ExecutionPlan,
    PhaseResult,
    Finding,
    AggregatedResults,
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

        assert len(plan.phases) == 4
        assert plan.phases[0].name == "Initial Analysis"
        assert plan.phases[1].name == "Specialist Review"
        assert plan.phases[2].name == "Integration Review"
        assert plan.phases[3].name == "Issue Creation"

    def test_phase_dependencies(self):
        team = ReviewTeam(
            core_agents=[{"name": "agent1", "category": "qa-sec"}],
            language_agents=[],
            domain_agents=[],
            coordination_pattern="peer-to-peer",
            coordinator=None,
            total_agents=1,
        )

        profile = TaskProfile(task_type="code_review")

        plan = self.coordinator.create_execution_plan(team, profile)

        # Phase 2 should depend on Phase 1
        assert 1 in plan.phases[1].dependencies
        # Phase 3 should depend on Phase 2
        assert 2 in plan.phases[2].dependencies
        # Phase 4 should depend on Phase 3
        assert 3 in plan.phases[3].dependencies

    def test_parallel_execution_flags(self):
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

        # Phase 1 and 2 should be parallel
        assert plan.phases[0].parallel is True
        assert plan.phases[1].parallel is True
        # Phase 3 and 4 should be sequential
        assert plan.phases[2].parallel is False
        assert plan.phases[3].parallel is False


class TestResultAggregation:
    """Test result aggregation and deduplication."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_aggregates_findings_from_multiple_agents(self):
        phase_results = [
            PhaseResult(
                phase=1,
                findings=[
                    Finding(
                        type="security",
                        severity="HIGH",
                        description="SQL injection vulnerability",
                        location="api/auth.py:42",
                        agent="security-auditor",
                    )
                ],
                agent_outputs={"security-auditor": "Found 1 issue"},
            ),
            PhaseResult(
                phase=2,
                findings=[
                    Finding(
                        type="code_quality",
                        severity="MEDIUM",
                        description="Complex function needs refactoring",
                        location="api/auth.py:100",
                        agent="code-reviewer",
                    )
                ],
                agent_outputs={"code-reviewer": "Found 1 issue"},
            ),
        ]

        results = self.coordinator._aggregate_results(phase_results)

        assert len(results.findings) == 2

    def test_deduplicates_identical_findings(self):
        phase_results = [
            PhaseResult(
                phase=1,
                findings=[
                    Finding(
                        type="security",
                        severity="HIGH",
                        description="SQL injection",
                        location="api/auth.py:42",
                        agent="agent1",
                    )
                ],
                agent_outputs={},
            ),
            PhaseResult(
                phase=2,
                findings=[
                    Finding(
                        type="security",
                        severity="HIGH",
                        description="SQL injection",
                        location="api/auth.py:42",
                        agent="agent2",
                    )
                ],
                agent_outputs={},
            ),
        ]

        results = self.coordinator._aggregate_results(phase_results)

        # Should deduplicate to 1 finding
        assert len(results.findings) == 1

    def test_severity_counts(self):
        phase_results = [
            PhaseResult(
                phase=1,
                findings=[
                    Finding(type="security", severity="CRITICAL", description="Critical issue", agent="agent1"),
                    Finding(type="security", severity="HIGH", description="High issue 1", agent="agent1"),
                    Finding(type="security", severity="HIGH", description="High issue 2", agent="agent1"),
                    Finding(type="security", severity="MEDIUM", description="Medium issue", agent="agent1"),
                    Finding(type="security", severity="LOW", description="Low issue", agent="agent1"),
                ],
                agent_outputs={},
            )
        ]

        results = self.coordinator._aggregate_results(phase_results)

        assert results.critical_count == 1
        assert results.high_count == 2
        assert results.medium_count == 1
        assert results.low_count == 1


class TestSeverityBasedSorting:
    """Test severity-based sorting of findings."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_sorts_by_severity(self):
        phase_results = [
            PhaseResult(
                phase=1,
                findings=[
                    Finding(type="bug", severity="LOW", description="Low", agent="agent1"),
                    Finding(type="bug", severity="CRITICAL", description="Critical", agent="agent1"),
                    Finding(type="bug", severity="MEDIUM", description="Medium", agent="agent1"),
                    Finding(type="bug", severity="HIGH", description="High", agent="agent1"),
                ],
                agent_outputs={},
            )
        ]

        results = self.coordinator._aggregate_results(phase_results)

        # Should be sorted: CRITICAL, HIGH, MEDIUM, LOW
        assert results.findings[0].severity == "CRITICAL"
        assert results.findings[1].severity == "HIGH"
        assert results.findings[2].severity == "MEDIUM"
        assert results.findings[3].severity == "LOW"


class TestFindingGrouping:
    """Test grouping findings by file, type, and agent."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_groups_by_file(self):
        phase_results = [
            PhaseResult(
                phase=1,
                findings=[
                    Finding(type="bug", severity="HIGH", description="Issue 1", location="api/auth.py:10", agent="agent1"),
                    Finding(type="bug", severity="HIGH", description="Issue 2", location="api/auth.py:20", agent="agent1"),
                    Finding(type="bug", severity="HIGH", description="Issue 3", location="api/db.py:30", agent="agent1"),
                ],
                agent_outputs={},
            )
        ]

        results = self.coordinator._aggregate_results(phase_results)

        # Group by file
        by_file = {}
        for finding in results.findings:
            file = finding.location.split(":")[0] if finding.location else "unknown"
            by_file.setdefault(file, []).append(finding)

        assert len(by_file["api/auth.py"]) == 2
        assert len(by_file["api/db.py"]) == 1

    def test_groups_by_type(self):
        phase_results = [
            PhaseResult(
                phase=1,
                findings=[
                    Finding(type="security", severity="HIGH", description="Issue 1", agent="agent1"),
                    Finding(type="security", severity="HIGH", description="Issue 2", agent="agent1"),
                    Finding(type="testing", severity="MEDIUM", description="Issue 3", agent="agent1"),
                ],
                agent_outputs={},
            )
        ]

        results = self.coordinator._aggregate_results(phase_results)

        # Group by type
        by_type = {}
        for finding in results.findings:
            by_type.setdefault(finding.type, []).append(finding)

        assert len(by_type["security"]) == 2
        assert len(by_type["testing"]) == 1


class TestErrorHandlingAndPartialResults:
    """Test error handling and partial result scenarios."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_handles_empty_phase_results(self):
        phase_results = []

        results = self.coordinator._aggregate_results(phase_results)

        assert len(results.findings) == 0
        assert results.critical_count == 0
        assert results.high_count == 0

    def test_handles_phases_with_no_findings(self):
        phase_results = [
            PhaseResult(phase=1, findings=[], agent_outputs={}),
            PhaseResult(phase=2, findings=[], agent_outputs={}),
        ]

        results = self.coordinator._aggregate_results(phase_results)

        assert len(results.findings) == 0

    def test_handles_partial_results_from_failed_agents(self):
        # Some agents succeeded, others failed
        phase_results = [
            PhaseResult(
                phase=1,
                findings=[
                    Finding(type="security", severity="HIGH", description="Found issue", agent="agent1"),
                ],
                agent_outputs={"agent1": "success"},
            ),
            # Phase 2 failed but we still got results from phase 1
        ]

        results = self.coordinator._aggregate_results(phase_results)

        assert len(results.findings) == 1


class TestExecutionPlanEstimation:
    """Test execution time estimation."""

    def setup_method(self):
        self.coordinator = ExecutionCoordinator()

    def test_estimates_total_hours(self):
        team = ReviewTeam(
            core_agents=[
                {"name": "agent1", "category": "qa-sec"},
                {"name": "agent2", "category": "qa-sec"},
            ],
            language_agents=[{"name": "agent3", "category": "lang"}],
            domain_agents=[],
            coordination_pattern="peer-to-peer",
            coordinator=None,
            total_agents=3,
        )

        profile = TaskProfile(task_type="security_audit")

        plan = self.coordinator.create_execution_plan(team, profile)

        assert plan.total_estimated_hours > 0
        assert isinstance(plan.total_estimated_hours, (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
