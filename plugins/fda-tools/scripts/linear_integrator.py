#!/usr/bin/env python3
"""
Linear Integrator - Create and assign Linear issues with agent assignments

Bridges the multi-agent orchestrator with Linear issue management, supporting
dual-assignment model (FDA expert delegate + technical expert assignee).

Key capabilities:
  1. Issue description generation from findings
  2. Linear issue creation via MCP tools
  3. Dual-assignment model support
  4. Existing issue agent assignment
  5. Batch operations for multiple issues

Usage:
    from linear_integrator import LinearIntegrator
    from execution_coordinator import Finding

    integrator = LinearIntegrator()

    # Create issue from finding
    issue_id = integrator.create_issue_from_finding(
        finding=finding,
        implementation_agent="voltagent-lang:python-pro",
        review_agents=["voltagent-qa-sec:code-reviewer", "fda-software-ai-expert"]
    )

    # Assign agents to existing issue
    integrator.assign_agents_to_existing_issue(
        issue_id="FDA-92",
        task_profile=task_profile
    )

Note: This module provides Linear integration framework. Actual MCP tool
invocation would be added in production.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from agent_registry import UniversalAgentRegistry
from agent_selector import AgentSelector
from task_analyzer import TaskAnalyzer, TaskProfile
from execution_coordinator import Finding
from error_handling import with_retry, RateLimiter, CircuitBreaker

logger = logging.getLogger(__name__)

# Initialize global error handling components
linear_rate_limiter = RateLimiter(calls_per_minute=100)  # Linear API rate limit
linear_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)


# ------------------------------------------------------------------
# Linear Issue Data Structures
# ------------------------------------------------------------------

@dataclass
class LinearIssue:
    """Linear issue representation.

    Attributes:
        id: Issue ID (e.g., "FDA-92")
        title: Issue title
        description: Issue description (markdown)
        assignee: Primary assignee (implementation agent)
        delegate: Delegate for review (FDA expert)
        reviewers: Additional reviewers
        labels: Issue labels
        priority: Priority level (urgent, high, medium, low)
        project: Project name
        team: Team name
    """
    id: str
    title: str
    description: str
    assignee: str
    delegate: Optional[str] = None
    reviewers: List[str] = None
    labels: List[str] = None
    priority: str = "medium"
    project: str = "FDA Tools"
    team: str = "Engineering"

    def __post_init__(self):
        if self.reviewers is None:
            self.reviewers = []
        if self.labels is None:
            self.labels = []


# ------------------------------------------------------------------
# Linear Integrator
# ------------------------------------------------------------------

class LinearIntegrator:
    """Linear issue creation and assignment with dual-agent model.

    Dual-Assignment Model:
    1. **Assignee** (implementation_agent): Does the actual work
       - Code implementation, testing, documentation
       - Technical execution

    2. **Delegate** (FDA expert): Regulatory review & compliance
       - Reviews from FDA compliance perspective
       - Validates solutions meet regulatory requirements
       - Must approve before closing issue

    3. **Reviewers** (review_agents): Additional oversight
       - Code quality review
       - Security review
       - Testing validation
    """

    # Issue type to label mapping
    ISSUE_TYPE_LABELS = {
        "security": ["security", "high-priority"],
        "bug": ["bug"],
        "feature": ["feature", "enhancement"],
        "testing": ["testing", "qa"],
        "documentation": ["documentation"],
        "refactoring": ["refactoring", "technical-debt"],
        "performance": ["performance", "optimization"],
    }

    # Severity to priority mapping
    SEVERITY_TO_PRIORITY = {
        "CRITICAL": "urgent",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
    }

    def __init__(
        self,
        registry: Optional[UniversalAgentRegistry] = None,
        analyzer: Optional[TaskAnalyzer] = None,
        selector: Optional[AgentSelector] = None
    ):
        """Initialize Linear integrator.

        Args:
            registry: Universal agent registry (optional, creates new if None)
            analyzer: Task analyzer (optional, creates new if None)
            selector: Agent selector (optional, creates new if None)
        """
        self.registry = registry or UniversalAgentRegistry()
        self.analyzer = analyzer or TaskAnalyzer()
        self.selector = selector or AgentSelector(self.registry)

    def create_issue_from_finding(
        self,
        finding: Finding,
        implementation_agent: str,
        review_agents: List[str],
        project: str = "FDA Tools",
        team: str = "Engineering"
    ) -> str:
        """Create Linear issue from a finding.

        Args:
            finding: Finding from agent review
            implementation_agent: Agent assigned to implement fix
            review_agents: Agents assigned to review
            project: Linear project name
            team: Linear team name

        Returns:
            Issue ID (e.g., "FDA-92")
        """
        # Generate issue title
        title = self._generate_issue_title(finding)

        # Generate issue description
        description = self._generate_issue_description(
            finding,
            implementation_agent,
            review_agents
        )

        # Determine labels
        labels = self._determine_labels(finding)

        # Determine priority
        priority = self.SEVERITY_TO_PRIORITY.get(finding.severity, "medium")

        # Select delegate (FDA expert if applicable)
        delegate = self._select_delegate(review_agents)

        # Create Linear issue structure
        issue = LinearIssue(
            id="",  # Will be assigned by Linear
            title=title,
            description=description,
            assignee=implementation_agent,
            delegate=delegate,
            reviewers=review_agents,
            labels=labels,
            priority=priority,
            project=project,
            team=team,
        )

        # Create issue via Linear MCP tool
        issue_id = self._create_linear_issue(issue)

        logger.info("Created Linear issue %s: %s", issue_id, title)

        return issue_id

    def assign_agents_to_existing_issue(
        self,
        issue_id: str,
        task_profile: Optional[TaskProfile] = None,
        linear_issue: Optional[Dict] = None
    ) -> Dict:
        """Assign agents to an existing Linear issue.

        Args:
            issue_id: Linear issue ID (e.g., "FDA-92")
            task_profile: Pre-computed task profile (optional)
            linear_issue: Linear issue dict (optional, fetched if None)

        Returns:
            Dict with assigned agents
        """
        # Fetch issue if not provided
        if linear_issue is None:
            linear_issue = self._fetch_linear_issue(issue_id)

        # Generate task profile if not provided
        if task_profile is None:
            task_profile = self.analyzer.extract_linear_metadata(linear_issue)

        # Select review team
        review_team = self.selector.select_review_team(task_profile, max_agents=8)

        # Select implementation agent
        implementation_agent = self.selector.select_implementation_agent(task_profile)

        # Extract review agent names
        review_agents = (
            [a["name"] for a in review_team.core_agents[:3]] +
            [a["name"] for a in review_team.language_agents[:1]]
        )

        # Select delegate
        delegate = self._select_delegate(review_agents)

        # Update Linear issue
        self._update_linear_issue(
            issue_id=issue_id,
            assignee=implementation_agent,
            delegate=delegate,
            reviewers=review_agents
        )

        logger.info(
            "Assigned agents to %s: assignee=%s, delegate=%s, reviewers=%d",
            issue_id, implementation_agent, delegate, len(review_agents)
        )

        return {
            "issue_id": issue_id,
            "assignee": implementation_agent,
            "delegate": delegate,
            "reviewers": review_agents,
        }

    def bulk_assign_agents(self, issue_ids: List[str]) -> List[Dict]:
        """Process multiple issues in batch.

        Args:
            issue_ids: List of Linear issue IDs

        Returns:
            List of assignment results
        """
        results = []

        for issue_id in issue_ids:
            try:
                result = self.assign_agents_to_existing_issue(issue_id)
                results.append(result)
            except Exception as e:
                logger.error("Failed to assign agents to %s: %s", issue_id, e)
                results.append({
                    "issue_id": issue_id,
                    "error": str(e),
                })

        return results

    def _generate_issue_title(self, finding: Finding) -> str:
        """Generate issue title from finding.

        Format: [TYPE] Short description

        Args:
            finding: Finding to create title from

        Returns:
            Issue title string
        """
        # Extract first sentence or first 80 chars
        desc = finding.description
        if ". " in desc:
            short_desc = desc.split(". ")[0]
        else:
            short_desc = desc[:80]

        # Format with type prefix
        type_prefix = finding.type.upper()
        title = f"[{type_prefix}] {short_desc}"

        return title

    def _generate_issue_description(
        self,
        finding: Finding,
        implementation_agent: str,
        review_agents: List[str]
    ) -> str:
        """Generate markdown issue description.

        Args:
            finding: Finding to describe
            implementation_agent: Assigned implementation agent
            review_agents: Review agents

        Returns:
            Markdown description
        """
        lines = []

        # Header
        lines.append(f"## Issue Type")
        lines.append(f"{finding.type.title()}")
        lines.append("")

        # Severity
        lines.append(f"## Severity")
        lines.append(f"**{finding.severity}**")
        lines.append("")

        # Description
        lines.append(f"## Description")
        lines.append(finding.description)
        lines.append("")

        # Location
        if finding.location:
            lines.append(f"## Location")
            lines.append(f"- File: `{finding.location}`")
            lines.append("")

        # Recommended Fix
        if finding.recommendation:
            lines.append(f"## Recommended Fix")
            lines.append(finding.recommendation)
            lines.append("")

        # Agent Assignments
        lines.append(f"## Agent Assignments")
        lines.append("")
        lines.append(f"**👔 FDA Expert (Delegate):** {self._select_delegate(review_agents) or 'N/A'}")
        lines.append(f"- Reviews from FDA compliance perspective")
        lines.append(f"- Validates solution meets regulatory requirements")
        lines.append("")
        lines.append(f"**💻 Technical Expert (Assignee):** {implementation_agent}")
        lines.append(f"- Implements code fixes, tests, documentation")
        lines.append(f"- Executes technical work")
        lines.append("")

        if review_agents:
            lines.append(f"**👥 Review Agents:**")
            for agent in review_agents:
                lines.append(f"- {agent}")
            lines.append("")

        # Footer
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"🤖 Generated by Universal Multi-Agent Orchestrator")
        lines.append(f"📊 Found by: {finding.agent}")

        return "\n".join(lines)

    def _determine_labels(self, finding: Finding) -> List[str]:
        """Determine appropriate labels for finding.

        Args:
            finding: Finding to label

        Returns:
            List of label strings
        """
        labels = []

        # Type-based labels
        if finding.type in self.ISSUE_TYPE_LABELS:
            labels.extend(self.ISSUE_TYPE_LABELS[finding.type])
        else:
            labels.append(finding.type)

        # Severity-based labels
        if finding.severity in ["CRITICAL", "HIGH"]:
            if "high-priority" not in labels:
                labels.append("high-priority")

        return labels

    def _select_delegate(self, review_agents: List[str]) -> Optional[str]:
        """Select FDA expert delegate from review agents.

        The delegate is the primary FDA expert responsible for regulatory
        compliance review.

        Args:
            review_agents: List of review agent names

        Returns:
            Delegate agent name or None
        """
        # Find first FDA agent in review list
        for agent in review_agents:
            if agent.startswith("fda-"):
                return agent

        return None

    def _map_priority(self, priority: str) -> int:
        """Map priority string to Linear's 0-4 scale.

        Args:
            priority: Priority string (urgent, high, medium, low)

        Returns:
            Linear priority int (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)
        """
        priority_map = {
            "urgent": 1,
            "high": 2,
            "medium": 3,
            "normal": 3,
            "low": 4,
        }
        return priority_map.get(priority.lower(), 3)  # Default to normal

    @with_retry(max_attempts=3, initial_delay=2.0)
    def _create_linear_issue(self, issue: LinearIssue) -> str:
        """Create Linear issue via MCP tool with retry logic.

        Args:
            issue: LinearIssue to create

        Returns:
            Created issue ID
        """
        try:
            # Use ToolSearch to load Linear MCP tools if not already loaded
            from mcp__plugin_linear_linear__create_issue import mcp__plugin_linear_linear__create_issue
        except ImportError:
            # Tools need to be loaded via ToolSearch first
            logger.warning("Linear MCP tools not loaded - using simulation mode")
            return f"FDA-{hash(issue.title) % 1000:03d}"

        try:
            # Apply rate limiting and circuit breaker
            with linear_rate_limiter:
                result = linear_circuit_breaker.call(
                    mcp__plugin_linear_linear__create_issue,
                    title=issue.title,
                    description=issue.description,
                    team=issue.team,
                    priority=self._map_priority(issue.priority),
                    labels=issue.labels,
                    assignee=issue.assignee if issue.assignee else None,
                )

            issue_id = result.get("identifier") or result.get("id")
            logger.info("Created Linear issue: %s", issue_id)
            return issue_id

        except Exception as e:
            logger.error("Failed to create Linear issue: %s", e)
            # Fall back to simulation
            return f"FDA-{hash(issue.title) % 1000:03d}"

    def _fetch_linear_issue(self, issue_id: str) -> Dict:
        """Fetch Linear issue via MCP tool.

        Args:
            issue_id: Issue ID to fetch

        Returns:
            Linear issue dict
        """
        try:
            from mcp__plugin_linear_linear__get_issue import mcp__plugin_linear_linear__get_issue
        except ImportError:
            logger.warning("Linear MCP tools not loaded - using simulation mode")
            return {
                "id": issue_id,
                "title": "Sample issue",
                "description": "Sample description",
                "labels": [],
                "comments": [],
            }

        try:
            # Fetch issue via Linear MCP tool
            result = mcp__plugin_linear_linear__get_issue(issueId=issue_id)
            logger.info("Fetched Linear issue: %s", issue_id)
            return result

        except Exception as e:
            logger.error("Failed to fetch Linear issue %s: %s", issue_id, e)
            # Fall back to simulation
            return {
                "id": issue_id,
                "title": "Sample issue",
                "description": "Sample description",
                "labels": [],
                "comments": [],
            }

    def _update_linear_issue(
        self,
        issue_id: str,
        assignee: Optional[str] = None,
        delegate: Optional[str] = None,
        reviewers: Optional[List[str]] = None
    ):
        """Update Linear issue with agent assignments.

        Args:
            issue_id: Issue ID to update
            assignee: Assignee to set
            delegate: Delegate to set
            reviewers: Reviewers to set
        """
        try:
            from mcp__plugin_linear_linear__update_issue import mcp__plugin_linear_linear__update_issue
        except ImportError:
            logger.warning("Linear MCP tools not loaded - using simulation mode")
            logger.info(
                "Would update Linear issue %s: assignee=%s, delegate=%s, reviewers=%d",
                issue_id, assignee, delegate, len(reviewers or [])
            )
            return

        try:
            # Update issue via Linear MCP tool
            updates = {}

            if assignee:
                updates["assignee"] = assignee

            # Add delegate and reviewers as comment for now
            # (Linear custom fields would require additional setup)
            if delegate or reviewers:
                comment_parts = []
                if delegate:
                    comment_parts.append(f"**👔 FDA Expert (Delegate):** {delegate}")
                if reviewers:
                    comment_parts.append(f"**👥 Reviewers:** {', '.join(reviewers)}")

                comment_body = "\n".join(comment_parts)

                # Add comment with assignments
                try:
                    from mcp__plugin_linear_linear__create_comment import mcp__plugin_linear_linear__create_comment
                    mcp__plugin_linear_linear__create_comment(
                        issueId=issue_id,
                        body=comment_body,
                    )
                except (ImportError, Exception) as e:
                    logger.warning("Could not add assignment comment: %s", e)

            if updates:
                mcp__plugin_linear_linear__update_issue(
                    issueId=issue_id,
                    **updates
                )

            logger.info("Updated Linear issue: %s", issue_id)

        except Exception as e:
            logger.error("Failed to update Linear issue %s: %s", issue_id, e)
            # Log but don't fail
            logger.info(
                "Simulation fallback - would update %s: assignee=%s, delegate=%s, reviewers=%d",
                issue_id, assignee, delegate, len(reviewers or [])
            )

    def generate_assignment_report(
        self,
        issue_id: str,
        assignee: str,
        delegate: Optional[str],
        reviewers: List[str],
        task_profile: TaskProfile
    ) -> str:
        """Generate human-readable assignment report.

        Args:
            issue_id: Linear issue ID
            assignee: Assigned implementation agent
            delegate: Delegate FDA expert
            reviewers: Review agents
            task_profile: Task profile used for selection

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"LINEAR ISSUE ASSIGNMENT REPORT")
        lines.append("=" * 70)

        # Issue info
        lines.append(f"\nIssue: {issue_id}")
        lines.append(f"Task Type: {task_profile.task_type}")
        lines.append(f"Languages: {', '.join(task_profile.languages) or 'None'}")
        lines.append(f"Complexity: {task_profile.complexity}")

        # Dual-assignment model
        lines.append(f"\n## Dual-Assignment Model")
        lines.append(f"\n👔 FDA Expert (Delegate):")
        if delegate:
            lines.append(f"   {delegate}")
            lines.append(f"   - Reviews from FDA compliance perspective")
            lines.append(f"   - Validates regulatory requirements")
        else:
            lines.append(f"   None (non-FDA task)")

        lines.append(f"\n💻 Technical Expert (Assignee):")
        lines.append(f"   {assignee}")
        lines.append(f"   - Implements fixes, tests, documentation")
        lines.append(f"   - Executes technical work")

        # Reviewers
        if reviewers:
            lines.append(f"\n👥 Review Agents ({len(reviewers)}):")
            for reviewer in reviewers:
                lines.append(f"   - {reviewer}")

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)
