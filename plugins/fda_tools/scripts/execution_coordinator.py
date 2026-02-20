#!/usr/bin/env python3
"""
Execution Coordinator - Multi-agent workflow orchestration

Orchestrates parallel and sequential agent execution with phased workflows,
result aggregation, and error handling.

Key capabilities:
  1. 4-phase execution plan generation
  2. Parallel and sequential agent invocation
  3. Result aggregation and deduplication
  4. Severity-based prioritization
  5. Error handling and retry logic

Usage:
    from execution_coordinator import ExecutionCoordinator
    from agent_selector import ReviewTeam
    from task_analyzer import TaskProfile

    coordinator = ExecutionCoordinator()

    # Create execution plan
    plan = coordinator.create_execution_plan(review_team, task_profile)

    # Execute plan
    results = coordinator.execute_plan(plan)

Note: This is a simulation framework. Actual agent invocation would use
the Task tool in production.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent_selector import ReviewTeam
from task_analyzer import TaskProfile

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Execution Plan Data Structures
# ------------------------------------------------------------------

@dataclass
class ExecutionPhase:
    """Single phase in execution plan.

    Attributes:
        phase: Phase number (1-4)
        name: Phase name
        description: Phase description
        assigned_agents: List of agent names for this phase
        parallel: Whether agents execute in parallel
        dependencies: List of phase numbers that must complete first
        estimated_hours: Estimated execution time
    """
    phase: int
    name: str
    description: str
    assigned_agents: List[str] = field(default_factory=list)
    parallel: bool = False
    dependencies: List[int] = field(default_factory=list)
    estimated_hours: int = 2


@dataclass
class ExecutionPlan:
    """Complete multi-phase execution plan.

    Attributes:
        phases: List of execution phases
        total_estimated_hours: Total execution time
        coordination_pattern: Coordination pattern (peer-to-peer, master-worker, hierarchical)
    """
    phases: List[ExecutionPhase] = field(default_factory=list)
    total_estimated_hours: int = 0
    coordination_pattern: str = "peer-to-peer"


@dataclass
class Finding:
    """Single finding from an agent.

    Attributes:
        agent: Agent name that generated the finding
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
        type: Finding type (security, code_quality, testing, etc.)
        description: Finding description
        location: File and line location
        recommendation: Recommended fix
        phase: Phase number where finding was generated
    """
    agent: str
    severity: str
    type: str
    description: str
    location: str = ""
    recommendation: str = ""
    phase: int = 1


@dataclass
class AggregatedFindings:
    """Aggregated findings from all agents.

    Attributes:
        findings: List of all findings
        critical_count: Number of critical findings
        high_count: Number of high findings
        medium_count: Number of medium findings
        low_count: Number of low findings
        by_file: Findings grouped by file
        by_type: Findings grouped by type
        by_agent: Findings grouped by agent
    """
    findings: List[Finding] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    by_file: Dict[str, List[Finding]] = field(default_factory=dict)
    by_type: Dict[str, List[Finding]] = field(default_factory=dict)
    by_agent: Dict[str, List[Finding]] = field(default_factory=dict)


# ------------------------------------------------------------------
# Execution Coordinator
# ------------------------------------------------------------------

class ExecutionCoordinator:
    """Coordinates multi-agent execution with phased workflow.

    Provides:
    - 4-phase execution plan generation
    - Parallel/sequential agent invocation
    - Result aggregation and deduplication
    - Error handling and retry logic
    """

    # Severity ordering (for sorting)
    SEVERITY_ORDER = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    def __init__(self):
        """Initialize execution coordinator."""
        pass

    def create_execution_plan(
        self,
        review_team: ReviewTeam,
        task_profile: TaskProfile
    ) -> ExecutionPlan:
        """Create 4-phase execution plan for review team.

        Phases:
        1. Initial Analysis (2-3 core agents, parallel)
        2. Specialist Review (language/domain agents, parallel)
        3. Integration (coordinator, sequential)
        4. Issue Creation (orchestrator, sequential)

        Args:
            review_team: Selected review team
            task_profile: Task profile

        Returns:
            ExecutionPlan with phases and dependencies
        """
        phases = []

        # Phase 1: Initial Analysis (core agents)
        core_agent_names = [a["name"] for a in review_team.core_agents[:3]]
        if core_agent_names:
            phases.append(ExecutionPhase(
                phase=1,
                name="Initial Analysis",
                description="Core review agents perform initial assessment",
                assigned_agents=core_agent_names,
                parallel=True,
                dependencies=[],
                estimated_hours=2,
            ))

        # Phase 2: Specialist Review (all remaining agents)
        specialist_agents = (
            [a["name"] for a in review_team.core_agents[3:]] +
            [a["name"] for a in review_team.language_agents] +
            [a["name"] for a in review_team.domain_agents]
        )
        if specialist_agents:
            phases.append(ExecutionPhase(
                phase=2,
                name="Specialist Review",
                description="Domain-specific and language-specific review",
                assigned_agents=specialist_agents,
                parallel=True,
                dependencies=[1] if phases else [],
                estimated_hours=4,
            ))

        # Phase 3: Integration (coordinator if present)
        if review_team.coordinator:
            phases.append(ExecutionPhase(
                phase=3,
                name="Integration Review",
                description="Coordinator aggregates findings and resolves conflicts",
                assigned_agents=[review_team.coordinator],
                parallel=False,
                dependencies=[2] if len(phases) >= 2 else [1],
                estimated_hours=2,
            ))

        # Phase 4: Issue Creation (handled by orchestrator)
        phases.append(ExecutionPhase(
            phase=4,
            name="Issue Creation",
            description="Create Linear issues from findings",
            assigned_agents=[],  # Handled by orchestrator, not agents
            parallel=False,
            dependencies=[3] if len(phases) >= 3 else [2] if len(phases) >= 2 else [1],
            estimated_hours=1,
        ))

        total_hours = sum(p.estimated_hours for p in phases)

        return ExecutionPlan(
            phases=phases,
            total_estimated_hours=total_hours,
            coordination_pattern=review_team.coordination_pattern,
        )

    def execute_plan(self, plan: ExecutionPlan) -> AggregatedFindings:
        """Execute the complete execution plan with error handling.

        This is a simulation. In production, this would invoke agents
        using the Task tool and aggregate real results.

        Args:
            plan: Execution plan to execute

        Returns:
            AggregatedFindings with all findings from all agents
        """
        logger.info("Executing plan with %d phases", len(plan.phases))

        all_findings: List[Finding] = []
        failed_phases = []

        for phase in plan.phases:
            logger.info("Executing phase %d: %s", phase.phase, phase.name)

            try:
                phase_findings = self._execute_phase(phase)
                all_findings.extend(phase_findings)
                logger.info("Phase %d completed: %d findings", phase.phase, len(phase_findings))
            except Exception as e:
                logger.error(
                    "Phase %d (%s) failed: %s - continuing with partial results",
                    phase.phase,
                    phase.name,
                    e,
                    exc_info=True
                )
                failed_phases.append({
                    "phase": phase.phase,
                    "name": phase.name,
                    "error": str(e),
                    "agents": phase.assigned_agents
                })
                # Continue with remaining phases for graceful degradation

        # Aggregate findings with failed phase information
        results = self._aggregate_findings(all_findings)

        # Add warning if some phases failed
        if failed_phases:
            logger.warning(
                "Execution completed with %d failed phases (out of %d total)",
                len(failed_phases),
                len(plan.phases)
            )
            for failed in failed_phases:
                logger.warning("  Failed: Phase %d (%s) - %s", failed["phase"], failed["name"], failed["error"])

        return results

    def _execute_phase(self, phase: ExecutionPhase) -> List[Finding]:
        """Execute a single phase with per-agent error handling.

        In production, this would:
        1. Invoke agents using Task tool
        2. Collect results
        3. Handle errors and retries

        Currently simulates agent execution.

        Args:
            phase: Phase to execute

        Returns:
            List of findings from this phase
        """
        findings = []
        failed_agents = []

        for agent_name in phase.assigned_agents:
            logger.info("  Invoking agent: %s", agent_name)

            try:
                # Simulate agent invocation
                # In production: result = self._invoke_agent(agent_name, phase)
                agent_findings = self._simulate_agent_findings(agent_name, phase.phase)

                findings.extend(agent_findings)
                logger.debug("  Agent %s returned %d findings", agent_name, len(agent_findings))

            except Exception as e:
                logger.error(
                    "  Agent %s failed in phase %d: %s - continuing with other agents",
                    agent_name,
                    phase.phase,
                    e,
                    exc_info=True
                )
                failed_agents.append(agent_name)
                # Continue with next agent for graceful degradation

        # Log summary
        if failed_agents:
            logger.warning(
                "Phase %d completed with %d/%d agents successful (%d findings)",
                phase.phase,
                len(phase.assigned_agents) - len(failed_agents),
                len(phase.assigned_agents),
                len(findings)
            )
        else:
            logger.info(
                "Phase %d completed successfully: all %d agents returned %d findings",
                phase.phase,
                len(phase.assigned_agents),
                len(findings)
            )

        return findings

    def _simulate_agent_findings(self, agent_name: str, phase: int) -> List[Finding]:
        """Simulate agent findings for testing.

        In production, this would be replaced by actual Task tool invocation.

        Args:
            agent_name: Agent name
            phase: Phase number

        Returns:
            List of simulated findings
        """
        # Simulate different findings based on agent type
        findings = []

        if "security" in agent_name.lower():
            findings.append(Finding(
                agent=agent_name,
                severity="HIGH",
                type="security",
                description=f"[{agent_name}] Potential security vulnerability detected",
                location="api/auth.py:42",
                recommendation="Add input validation and sanitization",
                phase=phase,
            ))
        elif "test" in agent_name.lower() or "qa" in agent_name.lower():
            findings.append(Finding(
                agent=agent_name,
                severity="MEDIUM",
                type="testing",
                description=f"[{agent_name}] Insufficient test coverage",
                location="tests/test_auth.py",
                recommendation="Add unit tests for edge cases",
                phase=phase,
            ))
        elif "code-reviewer" in agent_name.lower():
            findings.append(Finding(
                agent=agent_name,
                severity="LOW",
                type="code_quality",
                description=f"[{agent_name}] Code complexity too high",
                location="api/views.py:120",
                recommendation="Refactor function into smaller components",
                phase=phase,
            ))

        return findings

    def _invoke_agent(self, agent_name: str, phase: ExecutionPhase) -> Dict:
        """Invoke an agent using the Task tool.

        This would be the production implementation.

        Args:
            agent_name: Agent to invoke
            phase: Phase context

        Returns:
            Agent result dict
        """
        # Production implementation would use Task tool:
        #
        # from claude_code import Task
        #
        # result = Task(
        #     subagent_type=agent_name,
        #     description=f"{phase.name} - {phase.description}",
        #     prompt=self._generate_agent_prompt(agent_name, phase),
        # )
        #
        # return self._parse_agent_result(result)

        raise NotImplementedError("Production agent invocation not implemented")

    def _aggregate_findings(self, findings: List[Finding]) -> AggregatedFindings:
        """Aggregate and deduplicate findings from all agents.

        Args:
            findings: List of all findings

        Returns:
            AggregatedFindings with counts and groupings
        """
        # Deduplicate similar findings
        deduplicated = self._deduplicate_findings(findings)

        # Sort by severity (CRITICAL > HIGH > MEDIUM > LOW)
        deduplicated.sort(
            key=lambda f: self.SEVERITY_ORDER.get(f.severity, 0),
            reverse=True
        )

        # Count by severity
        critical_count = sum(1 for f in deduplicated if f.severity == "CRITICAL")
        high_count = sum(1 for f in deduplicated if f.severity == "HIGH")
        medium_count = sum(1 for f in deduplicated if f.severity == "MEDIUM")
        low_count = sum(1 for f in deduplicated if f.severity == "LOW")

        # Group by file
        by_file: Dict[str, List[Finding]] = {}
        for finding in deduplicated:
            file = finding.location.split(":")[0] if finding.location else "unknown"
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(finding)

        # Group by type
        by_type: Dict[str, List[Finding]] = {}
        for finding in deduplicated:
            if finding.type not in by_type:
                by_type[finding.type] = []
            by_type[finding.type].append(finding)

        # Group by agent
        by_agent: Dict[str, List[Finding]] = {}
        for finding in deduplicated:
            if finding.agent not in by_agent:
                by_agent[finding.agent] = []
            by_agent[finding.agent].append(finding)

        return AggregatedFindings(
            findings=deduplicated,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            by_file=by_file,
            by_type=by_type,
            by_agent=by_agent,
        )

    def _deduplicate_findings(self, findings: List[Finding]) -> List[Finding]:
        """Remove duplicate findings using similarity scoring.

        Args:
            findings: List of findings (may contain duplicates)

        Returns:
            Deduplicated list
        """
        if not findings:
            return []

        # Simple deduplication: same location + type
        seen = {}
        deduplicated = []

        for finding in findings:
            # Create key from location and type
            key = f"{finding.location}:{finding.type}"

            if key not in seen:
                seen[key] = finding
                deduplicated.append(finding)
            else:
                # Keep the higher severity one
                existing = seen[key]
                if self.SEVERITY_ORDER.get(finding.severity, 0) > \
                   self.SEVERITY_ORDER.get(existing.severity, 0):
                    # Replace with higher severity
                    deduplicated.remove(existing)
                    deduplicated.append(finding)
                    seen[key] = finding

        return deduplicated

    def format_findings_report(self, results: AggregatedFindings) -> str:
        """Format aggregated findings as a human-readable report.

        Args:
            results: Aggregated findings

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("MULTI-AGENT REVIEW FINDINGS REPORT")
        lines.append("=" * 70)

        # Summary
        lines.append(f"\nSummary:")
        lines.append(f"  Total Findings: {len(results.findings)}")
        lines.append(f"  CRITICAL: {results.critical_count}")
        lines.append(f"  HIGH: {results.high_count}")
        lines.append(f"  MEDIUM: {results.medium_count}")
        lines.append(f"  LOW: {results.low_count}")

        # By type
        lines.append(f"\nFindings by Type:")
        for finding_type, type_findings in sorted(results.by_type.items()):
            lines.append(f"  {finding_type:20s}: {len(type_findings)}")

        # By file
        lines.append(f"\nFindings by File:")
        for file, file_findings in sorted(results.by_file.items()):
            lines.append(f"  {file:40s}: {len(file_findings)}")

        # Detailed findings (top 10 by severity)
        lines.append(f"\nTop Findings:")
        for i, finding in enumerate(results.findings[:10], 1):
            lines.append(f"\n  [{i}] {finding.severity} - {finding.type}")
            lines.append(f"      Agent: {finding.agent}")
            lines.append(f"      Location: {finding.location}")
            lines.append(f"      Issue: {finding.description}")
            if finding.recommendation:
                lines.append(f"      Fix: {finding.recommendation}")

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)
