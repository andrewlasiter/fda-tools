#!/usr/bin/env python3
"""
Integration tests for UniversalOrchestrator - End-to-end workflows

Tests cover:
1. End-to-end review workflow
2. Agent assignment workflow
3. Batch processing
4. Error handling
5. CLI integration
"""

import json
import pytest
import subprocess
from pathlib import Path

# Integration tests - test the full workflow
class TestEndToEndReviewWorkflow:
    """Test complete review workflow from task to findings."""

    def test_review_workflow_basic(self):
        """Test basic review workflow with simple task."""
        # This would run the full orchestrator in production
        # For now, test that the components integrate correctly

        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        # Simple security review task
        task = "Fix SQL injection in authentication endpoint"
        files = ["api/auth.py"]

        result = orchestrator.review(task, files, max_agents=5)

        # Verify structure
        assert "profile" in result
        assert "team" in result
        assert "plan" in result
        assert "results" in result

        # Verify profile was generated
        assert result["profile"].task_type in ["security_audit", "bug_fix"]
        assert len(result["profile"].languages) > 0

        # Verify team was selected
        assert result["team"].total_agents > 0
        assert result["team"].total_agents <= 5

        # Verify plan was created
        assert len(result["plan"].phases) == 4

        # Verify results were aggregated
        assert hasattr(result["results"], "findings")

    def test_review_workflow_complex(self):
        """Test review workflow with complex multi-language task."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        task = "Comprehensive security audit of authentication system"
        files = ["api/auth.py", "frontend/Login.tsx", "tests/test_auth.py"]

        result = orchestrator.review(task, files, max_agents=10)

        # Should detect multiple languages
        assert len(result["profile"].languages) >= 2

        # Should select larger team
        assert result["team"].total_agents > 3

        # Should have coordinator for large team
        if result["team"].total_agents >= 7:
            assert result["team"].coordinator is not None


class TestAgentAssignmentWorkflow:
    """Test agent assignment to Linear issues."""

    def test_assign_workflow_auto(self):
        """Test auto-assignment workflow."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        # Would fetch real Linear issue in production
        result = orchestrator.assign("FDA-92", auto=True)

        assert "issue_id" in result
        assert "assignee" in result
        assert "reviewers" in result
        assert result["issue_id"] == "FDA-92"

    def test_assign_workflow_manual(self):
        """Test manual assignment with task description."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        task_description = "Fix security vulnerability in payment processing"

        result = orchestrator.assign(
            "FDA-93",
            auto=False,
            task_description=task_description,
        )

        assert result["issue_id"] == "FDA-93"
        assert result["assignee"] is not None


class TestBatchProcessing:
    """Test batch processing of multiple issues."""

    def test_batch_workflow(self):
        """Test batch assignment workflow."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        issue_ids = ["FDA-92", "FDA-93", "FDA-94"]

        results = orchestrator.batch(issue_ids)

        assert len(results) == len(issue_ids)

        # All should have basic structure
        for result in results:
            assert "issue_id" in result

    def test_batch_handles_errors(self):
        """Test batch processing with some invalid issues."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        issue_ids = ["FDA-92", "INVALID-999", "FDA-93"]

        results = orchestrator.batch(issue_ids)

        # Should still process all issues
        assert len(results) == len(issue_ids)

        # Some may have errors
        errors = [r for r in results if "error" in r]
        successes = [r for r in results if "error" not in r]

        # At least some should succeed
        assert len(successes) > 0


class TestFullExecutionWorkflow:
    """Test full workflow: review + create Linear issues."""

    def test_execute_workflow(self):
        """Test complete execution workflow."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        task = "Security audit of API endpoints"
        files = ["api/users.py", "api/auth.py"]

        result = orchestrator.execute(
            task,
            files,
            create_linear=False,  # Don't actually create issues in tests
            max_agents=8,
        )

        # Should have review results
        assert "profile" in result
        assert "team" in result
        assert "plan" in result
        assert "results" in result

        # Should have empty created_issues when create_linear=False
        assert "created_issues" in result

    def test_execute_workflow_with_linear_creation(self):
        """Test execution workflow with Linear issue creation."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        task = "Fix critical security vulnerability"
        files = ["api/auth.py"]

        result = orchestrator.execute(
            task,
            files,
            create_linear=True,
            max_agents=5,
        )

        # Should have created_issues list
        assert "created_issues" in result
        assert isinstance(result["created_issues"], list)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_empty_task_description(self):
        """Test handling of empty task description."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        result = orchestrator.review("", ["file.py"], max_agents=3)

        # Should handle gracefully
        assert "profile" in result

    def test_no_files(self):
        """Test handling of no files."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        result = orchestrator.review("Review task", [], max_agents=3)

        # Should handle gracefully
        assert "profile" in result

    def test_max_agents_zero(self):
        """Test handling of max_agents=0."""
        from universal_orchestrator import UniversalOrchestrator

        orchestrator = UniversalOrchestrator()

        result = orchestrator.review("Task", ["file.py"], max_agents=0)

        # Should handle gracefully or use minimum agents
        assert "team" in result


class TestCLIIntegration:
    """Test CLI integration (requires actual script execution)."""

    @pytest.mark.slow
    def test_cli_review_command(self):
        """Test CLI review command."""
        script_path = Path(__file__).parent.parent / "scripts" / "universal_orchestrator.py"

        if not script_path.exists():
            pytest.skip("Script not found")

        result = subprocess.run(
            [
                "python3",
                str(script_path),
                "review",
                "--task", "Test security review",
                "--files", "test.py",
                "--max-agents", "3",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        # Should output valid JSON
        try:
            output = json.loads(result.stdout)
            assert "task_type" in output or "team_size" in output
        except json.JSONDecodeError:
            pytest.fail("Invalid JSON output")

    @pytest.mark.slow
    def test_cli_assign_command(self):
        """Test CLI assign command."""
        script_path = Path(__file__).parent.parent / "scripts" / "universal_orchestrator.py"

        if not script_path.exists():
            pytest.skip("Script not found")

        result = subprocess.run(
            [
                "python3",
                str(script_path),
                "assign",
                "--issue-id", "FDA-92",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0


class TestComponentIntegration:
    """Test integration between all orchestrator components."""

    def test_analyzer_to_selector_integration(self):
        """Test TaskAnalyzer -> AgentSelector integration."""
        from task_analyzer import TaskAnalyzer
        from agent_selector import AgentSelector
        from agent_registry import UniversalAgentRegistry

        analyzer = TaskAnalyzer()
        registry = UniversalAgentRegistry()
        selector = AgentSelector(registry)

        # Analyze task
        profile = analyzer.analyze_task(
            "Security audit of Python API",
            {"files": ["api/auth.py"]},
        )

        # Select team based on profile
        team = selector.select_review_team(profile, max_agents=5)

        # Verify integration
        assert team.total_agents > 0
        assert len(team.core_agents) > 0

    def test_selector_to_coordinator_integration(self):
        """Test AgentSelector -> ExecutionCoordinator integration."""
        from agent_selector import AgentSelector, ReviewTeam
        from execution_coordinator import ExecutionCoordinator
        from agent_registry import UniversalAgentRegistry
        from task_analyzer import TaskProfile

        registry = UniversalAgentRegistry()
        selector = AgentSelector(registry)
        coordinator = ExecutionCoordinator()

        # Create profile and select team
        profile = TaskProfile(
            task_type="security_audit",
            languages=["python"],
            review_dimensions={"security": 0.9},
        )
        team = selector.select_review_team(profile, max_agents=5)

        # Create execution plan
        plan = coordinator.create_execution_plan(team, profile)

        # Verify integration
        assert len(plan.phases) == 4
        assert plan.total_estimated_hours > 0

    def test_coordinator_to_linear_integration(self):
        """Test ExecutionCoordinator -> LinearIntegrator integration."""
        from execution_coordinator import ExecutionCoordinator, Finding
        from linear_integrator import LinearIntegrator

        coordinator = ExecutionCoordinator()
        integrator = LinearIntegrator()

        # Create finding
        finding = Finding(
            type="security",
            severity="HIGH",
            description="SQL injection vulnerability",
            location="api/auth.py:42",
            agent="security-auditor",
        )

        # Create Linear issue from finding
        issue_id = integrator.create_issue_from_finding(
            finding,
            implementation_agent="voltagent-qa-sec:security-auditor",
            review_agents=["voltagent-qa-sec:code-reviewer"],
        )

        # Verify integration
        assert issue_id is not None
        assert len(issue_id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
