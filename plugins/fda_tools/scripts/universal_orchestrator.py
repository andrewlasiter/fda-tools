#!/usr/bin/env python3
"""
Universal Multi-Agent Orchestrator - Main CLI Entry Point

Unified command-line interface for the Universal Multi-Agent Orchestrator System.
Provides 4 main workflows for JIT agent assignment and comprehensive code review.

Commands:
  review    - Comprehensive code review with multi-agent team
  assign    - Assign agents to existing Linear issue
  batch     - Process multiple Linear issues in batch
  execute   - Full workflow: review + create Linear issues

Usage:
    # Comprehensive code review
    python3 universal_orchestrator.py review \
        --task "Fix authentication vulnerability" \
        --files api/auth.py \
        --max-agents 10

    # Assign agents to Linear issue
    python3 universal_orchestrator.py assign \
        --issue-id FDA-92 \
        --auto

    # Batch process Linear issues
    python3 universal_orchestrator.py batch \
        --issue-ids FDA-92,FDA-93,FDA-94

    # Full workflow (review + create issues)
    python3 universal_orchestrator.py execute \
        --task "Security audit of bridge server" \
        --files bridge/server.py \
        --create-linear \
        --max-agents 12

    # Continuous monitoring
    python3 universal_orchestrator.py watch \\
        --issue-ids FDA-83,FDA-96,FDA-97 \\
        --poll-interval 300
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Import orchestrator components
from agent_registry import UniversalAgentRegistry
from task_analyzer import TaskAnalyzer
from agent_selector import AgentSelector
from execution_coordinator import ExecutionCoordinator
from linear_integrator import LinearIntegrator
from linear_issue_watcher import LinearIssueWatcher
from agent_performance_tracker import AgentPerformanceTracker
from repo_registry import RepoRegistry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UniversalOrchestrator:
    """Main orchestrator class integrating all components.

    Provides 4 main workflows:
    1. review: Comprehensive code review
    2. assign: Assign agents to Linear issue
    3. batch: Process multiple Linear issues
    4. execute: Full workflow (review + create issues)
    """

    def __init__(self):
        """Initialize orchestrator with all components."""
        logger.info("Initializing Universal Multi-Agent Orchestrator...")

        self.registry = UniversalAgentRegistry()
        self.analyzer = TaskAnalyzer()
        self.selector = AgentSelector(self.registry)
        self.coordinator = ExecutionCoordinator()
        self.linear = LinearIntegrator(self.registry, self.analyzer, self.selector)

        logger.info("✓ Orchestrator initialized with 167 agents")

    def review(
        self,
        task: str,
        files: List[str],
        max_agents: int = 10,
        context: Optional[dict] = None
    ) -> dict:
        """Comprehensive code review workflow.

        Steps:
        1. Analyze task to generate profile
        2. Select optimal agent team
        3. Create execution plan
        4. Execute review (simulated)
        5. Return aggregated findings

        Args:
            task: Task description
            files: List of file paths
            max_agents: Maximum team size
            context: Optional additional context

        Returns:
            Dict with profile, team, plan, and results
        """
        logger.info("=" * 70)
        logger.info("COMPREHENSIVE CODE REVIEW")
        logger.info("=" * 70)

        # Step 1: Analyze task
        logger.info("\n1. Analyzing task...")
        task_context = context or {}
        task_context["files"] = files
        profile = self.analyzer.analyze_task(task, task_context)

        logger.info("   Task type: %s", profile.task_type)
        logger.info("   Languages: %s", ", ".join(profile.languages) or "None")
        logger.info("   Complexity: %s", profile.complexity)

        # Step 2: Select team
        logger.info("\n2. Selecting agent team...")
        team = self.selector.select_review_team(profile, max_agents)

        logger.info("   Team size: %d agents", team.total_agents)
        logger.info("   Core agents: %d", len(team.core_agents))
        logger.info("   Language agents: %d", len(team.language_agents))
        logger.info("   Domain agents: %d", len(team.domain_agents))
        if team.coordinator:
            logger.info("   Coordinator: %s", team.coordinator)

        # Step 3: Create execution plan
        logger.info("\n3. Creating execution plan...")
        plan = self.coordinator.create_execution_plan(team, profile)

        logger.info("   Phases: %d", len(plan.phases))
        logger.info("   Estimated hours: %d", plan.total_estimated_hours)
        logger.info("   Coordination: %s", plan.coordination_pattern)

        # Step 4: Execute review
        logger.info("\n4. Executing multi-agent review...")
        results = self.coordinator.execute_plan(plan)

        logger.info("   Total findings: %d", len(results.findings))
        logger.info("   CRITICAL: %d", results.critical_count)
        logger.info("   HIGH: %d", results.high_count)
        logger.info("   MEDIUM: %d", results.medium_count)
        logger.info("   LOW: %d", results.low_count)

        logger.info("\n" + "=" * 70)

        return {
            "profile": profile,
            "team": team,
            "plan": plan,
            "results": results,
        }

    def assign(
        self,
        issue_id: str,
        auto: bool = True,
        task_description: Optional[str] = None
    ) -> dict:
        """Assign agents to existing Linear issue.

        Args:
            issue_id: Linear issue ID (e.g., "FDA-92")
            auto: Auto-select agents based on issue content
            task_description: Manual task description (if not auto)

        Returns:
            Dict with assignment details
        """
        logger.info("=" * 70)
        logger.info("ASSIGN AGENTS TO LINEAR ISSUE")
        logger.info("=" * 70)

        logger.info("\nIssue: %s", issue_id)

        if auto:
            # Fetch issue and auto-analyze
            logger.info("Mode: Auto-assignment")
            result = self.linear.assign_agents_to_existing_issue(issue_id)
        else:
            # Manual task description
            logger.info("Mode: Manual assignment")
            if not task_description:
                raise ValueError("task_description required when auto=False")

            profile = self.analyzer.analyze_task(task_description)
            result = self.linear.assign_agents_to_existing_issue(
                issue_id,
                task_profile=profile
            )

        logger.info("\nAssigned agents:")
        logger.info("  Assignee: %s", result["assignee"])
        logger.info("  Delegate: %s", result["delegate"] or "None")
        logger.info("  Reviewers: %d", len(result["reviewers"]))
        for reviewer in result["reviewers"]:
            logger.info("    - %s", reviewer)

        logger.info("\n" + "=" * 70)

        return result

    def batch(
        self,
        issue_ids: List[str]
    ) -> List[dict]:
        """Process multiple Linear issues in batch.

        Args:
            issue_ids: List of Linear issue IDs

        Returns:
            List of assignment results
        """
        logger.info("=" * 70)
        logger.info("BATCH PROCESS LINEAR ISSUES")
        logger.info("=" * 70)

        logger.info("\nProcessing %d issues...", len(issue_ids))

        results = self.linear.bulk_assign_agents(issue_ids)

        success_count = sum(1 for r in results if "error" not in r)
        error_count = len(results) - success_count

        logger.info("\nResults:")
        logger.info("  Success: %d", success_count)
        logger.info("  Errors: %d", error_count)

        for result in results:
            if "error" in result:
                logger.error("  %s: ERROR - %s", result["issue_id"], result["error"])
            else:
                logger.info("  %s: ✓ Assigned to %s", result["issue_id"], result["assignee"])

        logger.info("\n" + "=" * 70)

        return results

    def execute(
        self,
        task: str,
        files: List[str],
        create_linear: bool = False,
        max_agents: int = 10
    ) -> dict:
        """Full workflow: review + create Linear issues.

        Args:
            task: Task description
            files: List of file paths
            create_linear: Whether to create Linear issues from findings
            max_agents: Maximum team size

        Returns:
            Dict with review results and created issues
        """
        logger.info("=" * 70)
        logger.info("FULL ORCHESTRATION WORKFLOW")
        logger.info("=" * 70)

        # Step 1: Comprehensive review
        review_result = self.review(task, files, max_agents)

        created_issues = []

        # Step 2: Create Linear issues if requested
        if create_linear:
            logger.info("\n5. Creating Linear issues from findings...")

            profile = review_result["profile"]
            results = review_result["results"]

            # Select implementation agent
            impl_agent = self.selector.select_implementation_agent(profile)

            # Select review agents
            team = review_result["team"]
            review_agents = (
                [a["name"] for a in team.core_agents[:3]] +
                [a["name"] for a in team.language_agents[:1]]
            )

            # Create issue for each finding
            for finding in results.findings[:10]:  # Limit to top 10
                issue_id = self.linear.create_issue_from_finding(
                    finding,
                    impl_agent,
                    review_agents
                )
                created_issues.append(issue_id)

            logger.info("   Created %d Linear issues", len(created_issues))

        logger.info("\n" + "=" * 70)

        return {
            **review_result,
            "created_issues": created_issues,
        }

    def watch(
        self,
        issue_ids: List[str],
        poll_interval: int = 300,
        auto_rereview: bool = True,
    ) -> None:
        """Daemon mode: monitor Linear issues and re-trigger review on substantial changes.

        Polls *issue_ids* every *poll_interval* seconds.  When a substantial
        change is detected (PR linked, "fixed" comment, code change mentioned)
        the orchestrator optionally posts a re-review comment on the original
        issue.

        Runs until SIGINT (Ctrl-C) or SIGTERM is received.

        Args:
            issue_ids: Linear identifiers to monitor (e.g. ``["FDA-83"]``).
            poll_interval: Seconds between poll cycles (default 300).
            auto_rereview: When True, post re-review comment for substantial
                updates automatically.
        """
        logger.info("=" * 70)
        logger.info("CONTINUOUS MONITORING MODE")
        logger.info("=" * 70)
        logger.info("\nWatching %d issues (interval=%ds, auto-rereview=%s)",
                    len(issue_ids), poll_interval, auto_rereview)

        watcher = LinearIssueWatcher(poll_interval_seconds=poll_interval)

        for update in watcher.watch(issue_ids):
            if update.is_substantial:
                logger.info("Substantial update on %s: %s", update.issue_id, update.substance_reason)
                if auto_rereview:
                    comment = watcher.post_rereview_comment(update)
                    logger.info("Re-review comment posted (%d chars)", len(comment))
            else:
                logger.debug("Informational update on %s — no action", update.issue_id)

    def report_agents(
        self,
        top_n: int = 20,
        strict: bool = False,
    ) -> str:
        """Print and return an agent performance ranking table.

        Loads performance data from the default store
        (``~/.fda_tools/agent_performance.json``) and renders a markdown
        table sorted by effectiveness score.

        Args:
            top_n: Maximum rows to include in the table (default 20).
            strict: When True, low-performing agents are excluded from the
                report and flagged prominently.

        Returns:
            Markdown-formatted report string.
        """
        logger.info("=" * 70)
        logger.info("AGENT PERFORMANCE REPORT")
        logger.info("=" * 70)

        tracker = AgentPerformanceTracker()
        report = tracker.format_report(top_n=top_n, include_low_performers=not strict)

        low = tracker.get_low_performers()
        if low:
            logger.warning("%d low-performing agent(s) flagged.", len(low))
            for rec in low:
                logger.warning(
                    "  ⚠ %s  score=%.3f  runs=%d",
                    rec.agent_name, rec.effectiveness_score, rec.total_runs,
                )

        logger.info("\n" + "=" * 70)
        print(report)
        return report

    def list_repos(self) -> str:
        """Display and return the multi-repo registry table.

        Loads the registry from ``~/.fda_tools/repo_registry.json`` and
        prints a markdown-formatted table of all registered repositories.

        Returns:
            Markdown table string.
        """
        logger.info("=" * 70)
        logger.info("REGISTERED REPOSITORIES")
        logger.info("=" * 70)

        registry = RepoRegistry()
        table = registry.format_registry()
        print(table)
        return table

    def multi_repo_execute(
        self,
        task: str,
        files: List[str],
        repo_names: List[str],
        create_linear: bool = False,
        max_agents: int = 10,
    ) -> dict:
        """Full workflow across multiple repositories.

        Resolves each repo from the registry, detects cross-repo imports in
        *files*, expands the file list to include dependent repos' files
        (heuristic), runs a standard ``execute()`` review, and annotates the
        returned result with multi-repo metadata.

        Args:
            task: Task description.
            files: Source files for the review.
            repo_names: Comma-separated or list of repo short-names.
            create_linear: Whether to create Linear issues from findings.
            max_agents: Maximum team size.

        Returns:
            Dict with review results plus ``multi_repo_metadata``.
        """
        logger.info("=" * 70)
        logger.info("MULTI-REPO ORCHESTRATION WORKFLOW")
        logger.info("=" * 70)

        registry = RepoRegistry()
        repos = registry.resolve_repos(repo_names)

        if not repos:
            logger.warning("No valid repos resolved from: %s", repo_names)
            repos_info = []
        else:
            repos_info = [{"name": r.name, "team": r.team, "path": r.path} for r in repos]
            logger.info("Resolved %d repos: %s", len(repos), [r.name for r in repos])

        # Detect cross-repo dependencies in provided files.
        cross_deps = []
        primary_repo = repos[0].name if repos else ""
        for f in files:
            for dep in registry.detect_cross_repo_imports(f, primary_repo):
                cross_deps.append(str(dep))
                logger.info("  Cross-repo dep: %s", dep)

        if cross_deps:
            logger.info("%d cross-repo import(s) detected.", len(cross_deps))

        # Run the standard execute workflow.
        result = self.execute(task, files, create_linear=create_linear, max_agents=max_agents)

        result["multi_repo_metadata"] = {
            "repos": repos_info,
            "cross_repo_dependencies": cross_deps,
            "dependency_count": len(cross_deps),
        }

        logger.info("\n" + "=" * 70)
        return result


# ==================================================================
# CLI Entry Point
# ==================================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Universal Multi-Agent Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # review command
    review_parser = subparsers.add_parser("review", help="Comprehensive code review")
    review_parser.add_argument("--task", required=True, help="Task description")
    review_parser.add_argument("--files", required=True, help="Comma-separated file paths")
    review_parser.add_argument("--max-agents", type=int, default=10, help="Maximum team size")
    review_parser.add_argument("--json", action="store_true", help="Output JSON")

    # assign command
    assign_parser = subparsers.add_parser("assign", help="Assign agents to Linear issue")
    assign_parser.add_argument("--issue-id", required=True, help="Linear issue ID (e.g., FDA-92)")
    assign_parser.add_argument("--auto", action="store_true", default=True, help="Auto-select agents")
    assign_parser.add_argument("--task", help="Manual task description (if not auto)")
    assign_parser.add_argument("--json", action="store_true", help="Output JSON")

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Batch process Linear issues")
    batch_parser.add_argument("--issue-ids", required=True, help="Comma-separated issue IDs")
    batch_parser.add_argument("--json", action="store_true", help="Output JSON")

    # execute command
    execute_parser = subparsers.add_parser("execute", help="Full workflow")
    execute_parser.add_argument("--task", required=True, help="Task description")
    execute_parser.add_argument("--files", required=True, help="Comma-separated file paths")
    execute_parser.add_argument("--create-linear", action="store_true", help="Create Linear issues")
    execute_parser.add_argument("--max-agents", type=int, default=10, help="Maximum team size")
    execute_parser.add_argument(
        "--repos",
        default="",
        metavar="REPO,...",
        help="Comma-separated repo names for multi-repo orchestration (FDA-215)",
    )
    execute_parser.add_argument("--json", action="store_true", help="Output JSON")

    # list-repos command (FDA-215 / ORCH-011)
    subparsers.add_parser(
        "list-repos",
        help="Show all registered repositories in the multi-repo registry",
    )

    # report-agents command (FDA-214 / ORCH-010)
    report_parser = subparsers.add_parser(
        "report-agents",
        help="Show agent performance ranking table",
    )
    report_parser.add_argument(
        "--top",
        type=int,
        default=20,
        metavar="N",
        help="Number of top agents to show (default: 20)",
    )
    report_parser.add_argument(
        "--strict",
        action="store_true",
        help="Exclude low-performing agents from output",
    )
    report_parser.add_argument("--json", action="store_true", help="Output JSON")

    # watch command (FDA-213 / ORCH-009)
    watch_parser = subparsers.add_parser(
        "watch",
        help="Daemon: monitor Linear issues and re-trigger review on substantial updates",
    )
    watch_parser.add_argument(
        "--issue-ids",
        required=True,
        help="Comma-separated Linear issue IDs to monitor (e.g. FDA-83,FDA-96)",
    )
    watch_parser.add_argument(
        "--poll-interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Seconds between poll cycles (default: 300)",
    )
    watch_parser.add_argument(
        "--no-auto-rereview",
        action="store_true",
        help="Log substantial updates but do not post re-review comments",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize orchestrator
    orchestrator = UniversalOrchestrator()

    # Execute command
    try:
        if args.command == "review":
            files = args.files.split(",")
            result = orchestrator.review(args.task, files, args.max_agents)

            if args.json:
                # Convert dataclasses to dicts for JSON
                print(json.dumps({
                    "task_type": result["profile"].task_type,
                    "team_size": result["team"].total_agents,
                    "findings": len(result["results"].findings),
                }, indent=2))

        elif args.command == "assign":
            result = orchestrator.assign(
                args.issue_id,
                auto=args.auto,
                task_description=args.task
            )

            if args.json:
                print(json.dumps(result, indent=2))

        elif args.command == "batch":
            issue_ids = args.issue_ids.split(",")
            results = orchestrator.batch(issue_ids)

            if args.json:
                print(json.dumps(results, indent=2))

        elif args.command == "execute":
            files = args.files.split(",")
            repo_names = [r for r in args.repos.split(",") if r] if args.repos else []

            if repo_names:
                # Multi-repo execution (FDA-215)
                result = orchestrator.multi_repo_execute(
                    args.task,
                    files,
                    repo_names=repo_names,
                    create_linear=args.create_linear,
                    max_agents=args.max_agents,
                )
            else:
                result = orchestrator.execute(
                    args.task,
                    files,
                    create_linear=args.create_linear,
                    max_agents=args.max_agents,
                )

            if args.json:
                out = {
                    "task_type": result["profile"].task_type,
                    "team_size": result["team"].total_agents,
                    "findings": len(result["results"].findings),
                    "created_issues": result["created_issues"],
                }
                if "multi_repo_metadata" in result:
                    out["multi_repo_metadata"] = result["multi_repo_metadata"]
                print(json.dumps(out, indent=2))

        elif args.command == "list-repos":
            orchestrator.list_repos()

        elif args.command == "report-agents":
            orchestrator.report_agents(top_n=args.top, strict=args.strict)
            if args.json:
                # Emit raw records as JSON for machine consumption.
                from agent_performance_tracker import AgentPerformanceTracker
                tracker = AgentPerformanceTracker()
                ranked = tracker.rank_agents(include_low_performers=not args.strict)
                print(json.dumps(
                    [r.to_dict() for r in ranked[:args.top]],
                    indent=2,
                ))

        elif args.command == "watch":
            issue_ids = args.issue_ids.split(",")
            orchestrator.watch(
                issue_ids,
                poll_interval=args.poll_interval,
                auto_rereview=not args.no_auto_rereview,
            )

        return 0

    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
