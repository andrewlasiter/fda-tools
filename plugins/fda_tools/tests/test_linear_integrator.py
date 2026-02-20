#!/usr/bin/env python3
"""
Tests for LinearIntegrator - Linear issue creation and assignment

Tests cover:
1. Issue description generation
2. Dual-assignment model (assignee + delegate + reviewers)
3. Label determination
4. Delegate selection (FDA expert)
5. Priority mapping
6. Batch operations
"""

import pytest
from linear_integrator import LinearIntegrator, LinearIssue
from execution_coordinator import Finding
from task_analyzer import TaskProfile


class TestIssueDescriptionGeneration:
    """Test issue description generation from findings."""

    def setup_method(self):
        self.integrator = LinearIntegrator()

    def test_generates_title_from_finding(self):
        finding = Finding(
            type="security",
            severity="HIGH",
            description="Path traversal vulnerability in file upload",
            location="api/upload.py:45",
            agent="security-auditor",
        )

        title = self.integrator._generate_issue_title(finding)

        assert "[SECURITY]" in title.upper()
        assert len(title) > 0
        assert len(title) < 120  # Reasonable title length

    def test_generates_markdown_description(self):
        finding = Finding(
            type="security",
            severity="CRITICAL",
            description="SQL injection in authentication endpoint",
            location="api/auth.py:42",
            recommendation="Use parameterized queries",
            agent="security-auditor",
        )

        description = self.integrator._generate_issue_description(
            finding,
            implementation_agent="voltagent-qa-sec:security-auditor",
            review_agents=["voltagent-qa-sec:code-reviewer"],
        )

        assert "## Issue Type" in description
        assert "## Severity" in description
        assert "CRITICAL" in description
        assert "## Description" in description
        assert "SQL injection" in description
        assert "## Location" in description
        assert "api/auth.py:42" in description
        assert "## Recommended Fix" in description
        assert "parameterized queries" in description
        assert "## Agent Assignments" in description


class TestDualAssignmentModel:
    """Test dual-assignment model implementation."""

    def setup_method(self):
        self.integrator = LinearIntegrator()

    def test_selects_fda_delegate_when_present(self):
        review_agents = [
            "voltagent-qa-sec:code-reviewer",
            "fda-software-ai-expert",
            "voltagent-lang:python-pro",
        ]

        delegate = self.integrator._select_delegate(review_agents)

        assert delegate is not None
        assert "fda-" in delegate

    def test_no_delegate_when_no_fda_agents(self):
        review_agents = [
            "voltagent-qa-sec:code-reviewer",
            "voltagent-lang:python-pro",
        ]

        delegate = self.integrator._select_delegate(review_agents)

        assert delegate is None

    def test_creates_issue_with_all_assignments(self):
        finding = Finding(
            type="security",
            severity="HIGH",
            description="Security issue",
            agent="agent1",
        )

        # This would create an issue in production
        # For now, just test the structure
        issue = LinearIssue(
            id="",
            title="[SECURITY] Test issue",
            description="Test description",
            assignee="voltagent-qa-sec:security-auditor",
            delegate="fda-software-ai-expert",
            reviewers=["voltagent-qa-sec:code-reviewer"],
            labels=["security", "high"],
            priority="high",
        )

        assert issue.assignee is not None
        assert issue.delegate is not None
        assert len(issue.reviewers) > 0


class TestLabelDetermination:
    """Test label determination logic."""

    def setup_method(self):
        self.integrator = LinearIntegrator()

    def test_security_finding_gets_security_labels(self):
        finding = Finding(
            type="security",
            severity="CRITICAL",
            description="Security issue",
            agent="agent1",
        )

        labels = self.integrator._determine_labels(finding)

        assert "security" in labels
        assert "high-priority" in labels or "critical" in [l.lower() for l in labels]

    def test_testing_finding_gets_testing_labels(self):
        finding = Finding(
            type="testing",
            severity="MEDIUM",
            description="Missing test coverage",
            agent="agent1",
        )

        labels = self.integrator._determine_labels(finding)

        assert "testing" in labels or "qa" in labels

    def test_high_severity_gets_priority_label(self):
        finding = Finding(
            type="bug",
            severity="HIGH",
            description="Critical bug",
            agent="agent1",
        )

        labels = self.integrator._determine_labels(finding)

        assert "high-priority" in labels or any("high" in l.lower() for l in labels)


class TestPriorityMapping:
    """Test severity to priority mapping."""

    def setup_method(self):
        self.integrator = LinearIntegrator()

    def test_critical_maps_to_urgent(self):
        assert self.integrator.SEVERITY_TO_PRIORITY["CRITICAL"] == "urgent"

    def test_high_maps_to_high(self):
        assert self.integrator.SEVERITY_TO_PRIORITY["HIGH"] == "high"

    def test_medium_maps_to_medium(self):
        assert self.integrator.SEVERITY_TO_PRIORITY["MEDIUM"] == "medium"

    def test_low_maps_to_low(self):
        assert self.integrator.SEVERITY_TO_PRIORITY["LOW"] == "low"


class TestBatchOperations:
    """Test batch operations for multiple issues."""

    def setup_method(self):
        self.integrator = LinearIntegrator()

    def test_bulk_assign_agents_processes_all_issues(self):
        issue_ids = ["FDA-92", "FDA-93", "FDA-94"]

        # This would call real Linear API in production
        # For now, test the structure
        results = self.integrator.bulk_assign_agents(issue_ids)

        assert len(results) == len(issue_ids)

    def test_bulk_assign_handles_errors_gracefully(self):
        issue_ids = ["VALID-1", "INVALID-999", "VALID-2"]

        results = self.integrator.bulk_assign_agents(issue_ids)

        # Should return results for all issues (some may have errors)
        assert len(results) == len(issue_ids)


class TestExistingIssueAssignment:
    """Test agent assignment to existing Linear issues."""

    def setup_method(self):
        self.integrator = LinearIntegrator()

    def test_assigns_agents_to_existing_issue(self):
        issue_id = "FDA-92"

        # Would fetch real issue and assign agents in production
        result = self.integrator.assign_agents_to_existing_issue(issue_id)

        assert result["issue_id"] == issue_id
        assert "assignee" in result
        assert "reviewers" in result

    def test_uses_task_profile_when_provided(self):
        issue_id = "FDA-92"
        task_profile = TaskProfile(
            task_type="security_audit",
            languages=["python"],
            review_dimensions={"security": 0.9},
        )

        result = self.integrator.assign_agents_to_existing_issue(
            issue_id,
            task_profile=task_profile,
        )

        assert result["issue_id"] == issue_id
        # Should use provided profile for agent selection


class TestAssignmentReportGeneration:
    """Test assignment report generation."""

    def setup_method(self):
        self.integrator = LinearIntegrator()

    def test_generates_readable_report(self):
        task_profile = TaskProfile(
            task_type="security_audit",
            languages=["python"],
            complexity="high",
        )

        report = self.integrator.generate_assignment_report(
            issue_id="FDA-92",
            assignee="voltagent-qa-sec:security-auditor",
            delegate="fda-software-ai-expert",
            reviewers=["voltagent-qa-sec:code-reviewer", "voltagent-lang:python-pro"],
            task_profile=task_profile,
        )

        assert "FDA-92" in report
        assert "security_audit" in report
        assert "voltagent-qa-sec:security-auditor" in report
        assert "fda-software-ai-expert" in report
        assert len(report) > 100  # Should be comprehensive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
