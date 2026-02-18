#!/usr/bin/env python3
"""
Agent Selector - Multi-dimensional agent team selection

Intelligently selects optimal agent teams based on task profiles,
combining dimension matching, language expertise, domain knowledge,
and model tier optimization.

Key capabilities:
  1. Multi-dimensional agent selection (8 review dimensions)
  2. Language-specific agent matching
  3. Domain expertise selection
  4. Coordination pattern recommendation
  5. Team size optimization
  6. Ranking by relevance score

Usage:
    from agent_selector import AgentSelector
    from agent_registry import UniversalAgentRegistry
    from task_analyzer import TaskProfile

    registry = UniversalAgentRegistry()
    selector = AgentSelector(registry)

    # Select review team
    team = selector.select_review_team(task_profile, max_agents=10)

    # Select implementation agent
    impl_agent = selector.select_implementation_agent(task_profile)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent_registry import UniversalAgentRegistry
from task_analyzer import TaskProfile

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Agent Team Data Structures
# ------------------------------------------------------------------

@dataclass
class ReviewTeam:
    """Agent team assembled for comprehensive review.

    Attributes:
        core_agents: Agents selected by review dimension match
        language_agents: Language-specific agents
        domain_agents: Domain-specific agents
        coordinator: Optional coordinator agent for teams > 6
        coordination_pattern: Recommended pattern (peer-to-peer, master-worker, hierarchical)
        total_agents: Total team size
        estimated_hours: Estimated total review time
    """
    core_agents: List[Dict] = field(default_factory=list)
    language_agents: List[Dict] = field(default_factory=list)
    domain_agents: List[Dict] = field(default_factory=list)
    coordinator: Optional[str] = None
    coordination_pattern: str = "peer-to-peer"
    total_agents: int = 0
    estimated_hours: int = 0


# ------------------------------------------------------------------
# Agent Selector
# ------------------------------------------------------------------

class AgentSelector:
    """Intelligent agent selection using task profile and agent capabilities.

    Selects optimal agent teams based on:
    - Review dimension importance (40% weight)
    - Language matching (30% weight)
    - Domain matching (20% weight)
    - Model tier (10% weight)
    """

    # Ranking weights
    DIMENSION_WEIGHT = 0.40
    LANGUAGE_WEIGHT = 0.30
    DOMAIN_WEIGHT = 0.20
    MODEL_WEIGHT = 0.10

    # Model tier scores
    MODEL_SCORES = {
        "opus": 10,
        "sonnet": 7,
        "haiku": 4,
    }

    # Dimension importance threshold (only select agents for dimensions > this)
    DIMENSION_THRESHOLD = 0.3

    # Estimated hours per agent by model tier
    HOURS_PER_AGENT = {
        "opus": 3,
        "sonnet": 2,
        "haiku": 1,
    }

    def __init__(self, registry: UniversalAgentRegistry):
        """Initialize agent selector.

        Args:
            registry: Universal agent registry instance
        """
        self.registry = registry

    def select_review_team(
        self,
        task_profile: TaskProfile,
        max_agents: int = 10
    ) -> ReviewTeam:
        """Select optimal agent team for comprehensive review.

        Selection algorithm:
        1. For each review dimension with score > 0.3:
           - Select 1-2 specialist agents
        2. Add language-specific agents if detected
        3. Add domain-specific agents if detected
        4. Add meta-coordinator if team size > 6
        5. Rank by relevance score
        6. Limit to max_agents

        Args:
            task_profile: Task profile from TaskAnalyzer
            max_agents: Maximum team size

        Returns:
            ReviewTeam with selected agents and coordination pattern
        """
        # Step 1: Select core agents by review dimension
        core_agents = self._select_dimension_agents(task_profile, max_per_dimension=2)

        # Step 2: Select language-specific agents
        language_agents = self._select_language_agents(task_profile, max_per_language=1)

        # Step 3: Select domain-specific agents
        domain_agents = self._select_domain_agents(task_profile, max_per_domain=1)

        # Step 4: Combine and deduplicate
        all_agents = self._deduplicate_agents(
            core_agents + language_agents + domain_agents
        )

        # Step 5: Rank and limit to max_agents
        ranked_agents = self._rank_agents(all_agents, task_profile)[:max_agents]

        # Step 6: Categorize agents
        core = [a for a in ranked_agents if a["selection_reason"] == "dimension"]
        lang = [a for a in ranked_agents if a["selection_reason"] == "language"]
        domain = [a for a in ranked_agents if a["selection_reason"] == "domain"]

        # Step 7: Add coordinator if needed
        coordinator = None
        if len(ranked_agents) > 6:
            coordinator = "voltagent-meta:multi-agent-coordinator"

        # Step 8: Determine coordination pattern
        team_size = len(ranked_agents) + (1 if coordinator else 0)
        coordination_pattern = self._recommend_coordination_pattern(team_size)

        # Step 9: Estimate hours
        estimated_hours = self._estimate_review_hours(ranked_agents, coordinator)

        return ReviewTeam(
            core_agents=core,
            language_agents=lang,
            domain_agents=domain,
            coordinator=coordinator,
            coordination_pattern=coordination_pattern,
            total_agents=team_size,
            estimated_hours=estimated_hours,
        )

    def select_implementation_agent(self, task_profile: TaskProfile) -> str:
        """Select single best implementation agent for Linear assignment.

        Selection logic:
        - If language detected: language-specific agent (python-pro, typescript-pro, etc.)
        - If refactoring: refactoring-specialist
        - If security fix: security-auditor
        - If test writing: test-automator
        - Fallback: fullstack-developer or code-reviewer

        Args:
            task_profile: Task profile from TaskAnalyzer

        Returns:
            Agent name string
        """
        # Priority 1: Language-specific agents
        if task_profile.languages:
            primary_lang = task_profile.languages[0]
            lang_agents = self.registry.find_agents_by_language(primary_lang)

            # Prefer language specialists from "lang" category
            lang_specialists = [
                a for a in lang_agents
                if a.get("category") == "lang"
            ]
            if lang_specialists:
                return lang_specialists[0]["name"]

        # Priority 2: Task-type specific agents
        task_type = task_profile.task_type

        if task_type == "refactoring":
            return "voltagent-dev-exp:refactoring-specialist"
        elif task_type == "security_audit":
            return "voltagent-qa-sec:security-auditor"
        elif task_type == "testing":
            return "voltagent-qa-sec:test-automator"
        elif task_type == "documentation":
            return "voltagent-biz:technical-writer"
        elif task_type == "deployment":
            return "voltagent-infra:devops-engineer"

        # Priority 3: Review dimension specialists
        if task_profile.review_dimensions:
            top_dimension = max(
                task_profile.review_dimensions.items(),
                key=lambda x: x[1]
            )[0]

            dimension_agents = self.registry.find_agents_by_review_dimension(top_dimension)
            if dimension_agents:
                return dimension_agents[0]["name"]

        # Fallback: Generalist agents
        return "voltagent-core-dev:fullstack-developer"

    def _select_dimension_agents(
        self,
        task_profile: TaskProfile,
        max_per_dimension: int = 2
    ) -> List[Dict]:
        """Select agents based on review dimension importance.

        Args:
            task_profile: Task profile
            max_per_dimension: Max agents per dimension

        Returns:
            List of selected agent dicts with selection_reason added
        """
        selected = []

        for dimension, score in task_profile.review_dimensions.items():
            if score <= self.DIMENSION_THRESHOLD:
                continue  # Skip low-importance dimensions

            # Get agents for this dimension
            agents = self.registry.find_agents_by_review_dimension(dimension)

            # Select top agents
            for agent in agents[:max_per_dimension]:
                selected.append({
                    **agent,
                    "selection_reason": "dimension",
                    "matched_dimension": dimension,
                    "dimension_score": score,
                })

        return selected

    def _select_language_agents(
        self,
        task_profile: TaskProfile,
        max_per_language: int = 1
    ) -> List[Dict]:
        """Select language-specific agents.

        Args:
            task_profile: Task profile
            max_per_language: Max agents per language

        Returns:
            List of selected agent dicts
        """
        selected = []

        for language in task_profile.languages:
            agents = self.registry.find_agents_by_language(language)

            # Prefer agents from "lang" category
            lang_specialists = [a for a in agents if a.get("category") == "lang"]
            candidates = lang_specialists if lang_specialists else agents

            for agent in candidates[:max_per_language]:
                selected.append({
                    **agent,
                    "selection_reason": "language",
                    "matched_language": language,
                })

        return selected

    def _select_domain_agents(
        self,
        task_profile: TaskProfile,
        max_per_domain: int = 1
    ) -> List[Dict]:
        """Select domain-specific agents.

        Args:
            task_profile: Task profile
            max_per_domain: Max agents per domain

        Returns:
            List of selected agent dicts
        """
        selected = []

        # Domain-to-agent mapping
        domain_map = {
            "healthcare": ["fda-quality-expert", "fda-software-ai-expert"],
            "fintech": ["voltagent-domains:fintech-engineer"],
            "blockchain": ["voltagent-domains:blockchain-developer"],
            "api": ["voltagent-core-dev:api-designer"],
        }

        for domain in task_profile.domains:
            # Try direct mapping first
            if domain in domain_map:
                for agent_name in domain_map[domain][:max_per_domain]:
                    agent = self.registry.get_universal_agent(agent_name)
                    if agent:
                        selected.append({
                            **agent,
                            "selection_reason": "domain",
                            "matched_domain": domain,
                        })
            else:
                # Try searching by domain keyword
                results = self.registry.search_universal_agents(
                    query=domain,
                    category="domains"
                )
                for agent in results[:max_per_domain]:
                    selected.append({
                        **agent,
                        "selection_reason": "domain",
                        "matched_domain": domain,
                    })

        return selected

    def _deduplicate_agents(self, agents: List[Dict]) -> List[Dict]:
        """Remove duplicate agents, keeping highest-scored version.

        Args:
            agents: List of agent dicts (may have duplicates)

        Returns:
            Deduplicated list
        """
        seen = {}
        for agent in agents:
            name = agent["name"]
            if name not in seen:
                seen[name] = agent
            else:
                # Keep the one with higher dimension_score if available
                existing_score = seen[name].get("dimension_score", 0)
                new_score = agent.get("dimension_score", 0)
                if new_score > existing_score:
                    seen[name] = agent

        return list(seen.values())

    def _rank_agents(
        self,
        agents: List[Dict],
        task_profile: TaskProfile
    ) -> List[Dict]:
        """Rank agents by relevance score.

        Scoring formula:
        - Dimension match: 40%
        - Language match: 30%
        - Domain match: 20%
        - Model tier: 10%

        Args:
            agents: List of agent dicts
            task_profile: Task profile

        Returns:
            Sorted list of agents (highest score first)
        """
        scored_agents = []

        for agent in agents:
            # Dimension score (0-40 points)
            dimension_score = agent.get("dimension_score", 0) * 40

            # Language score (0-30 points)
            language_score = 0
            if agent.get("matched_language") in task_profile.languages:
                language_score = 30

            # Domain score (0-20 points)
            domain_score = 0
            if agent.get("matched_domain") in task_profile.domains:
                domain_score = 20

            # Model tier score (0-10 points)
            model = agent.get("model", "haiku")
            model_score = self.MODEL_SCORES.get(model, 0)

            # Total score
            total_score = dimension_score + language_score + domain_score + model_score

            scored_agents.append({
                **agent,
                "_relevance_score": total_score,
            })

        # Sort by score (descending)
        scored_agents.sort(key=lambda a: a["_relevance_score"], reverse=True)

        # Remove temporary scoring field
        for agent in scored_agents:
            agent.pop("_relevance_score", None)

        return scored_agents

    def _recommend_coordination_pattern(self, team_size: int) -> str:
        """Recommend coordination pattern based on team size.

        Patterns:
        - peer-to-peer: Team size ≤ 3 (direct coordination)
        - master-worker: Team size 4-6 (lead coordinator)
        - hierarchical: Team size ≥ 7 (coordinator + sub-teams)

        Args:
            team_size: Total team size including coordinator

        Returns:
            Coordination pattern string
        """
        if team_size <= 3:
            return "peer-to-peer"
        elif team_size <= 6:
            return "master-worker"
        else:
            return "hierarchical"

    def _estimate_review_hours(
        self,
        agents: List[Dict],
        coordinator: Optional[str]
    ) -> int:
        """Estimate total review hours for team.

        Args:
            agents: List of selected agents
            coordinator: Optional coordinator agent name

        Returns:
            Estimated hours
        """
        total_hours = 0

        # Agent hours
        for agent in agents:
            model = agent.get("model", "sonnet")
            hours = self.HOURS_PER_AGENT.get(model, 2)
            total_hours += hours

        # Coordinator overhead
        if coordinator:
            total_hours += 2

        return total_hours

    def explain_selection(
        self,
        team: ReviewTeam,
        task_profile: TaskProfile
    ) -> str:
        """Generate human-readable explanation of team selection.

        Args:
            team: Selected review team
            task_profile: Task profile used for selection

        Returns:
            Formatted explanation string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("AGENT TEAM SELECTION EXPLANATION")
        lines.append("=" * 70)

        # Task summary
        lines.append(f"\nTask Type: {task_profile.task_type}")
        lines.append(f"Languages: {', '.join(task_profile.languages) or 'None'}")
        lines.append(f"Frameworks: {', '.join(task_profile.frameworks) or 'None'}")
        lines.append(f"Domains: {', '.join(task_profile.domains) or 'None'}")
        lines.append(f"Complexity: {task_profile.complexity}")

        # Review dimensions
        lines.append(f"\nReview Dimensions:")
        for dim, score in sorted(
            task_profile.review_dimensions.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"  {dim:20s}: {score:.2f}")

        # Selected team
        lines.append(f"\nSelected Team ({team.total_agents} agents):")

        if team.core_agents:
            lines.append(f"\n  Core Agents ({len(team.core_agents)}):")
            for agent in team.core_agents:
                dim = agent.get("matched_dimension", "N/A")
                lines.append(f"    - {agent['name']} (dimension: {dim})")

        if team.language_agents:
            lines.append(f"\n  Language Agents ({len(team.language_agents)}):")
            for agent in team.language_agents:
                lang = agent.get("matched_language", "N/A")
                lines.append(f"    - {agent['name']} (language: {lang})")

        if team.domain_agents:
            lines.append(f"\n  Domain Agents ({len(team.domain_agents)}):")
            for agent in team.domain_agents:
                domain = agent.get("matched_domain", "N/A")
                lines.append(f"    - {agent['name']} (domain: {domain})")

        if team.coordinator:
            lines.append(f"\n  Coordinator:")
            lines.append(f"    - {team.coordinator}")

        # Coordination
        lines.append(f"\nCoordination Pattern: {team.coordination_pattern}")
        lines.append(f"Estimated Hours: {team.estimated_hours}")

        lines.append("=" * 70)

        return "\n".join(lines)
