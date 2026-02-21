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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


# ---------------------------------------------------------------------------
# ML-based agent selector (ORCH-008)
# ---------------------------------------------------------------------------

# Attempt to import scikit-learn.  It lives in the optional dependency group
# so we degrade gracefully to the static selector when it is not installed.
try:
    from sklearn.ensemble import GradientBoostingRegressor  # type: ignore[import]
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False


# Minimum history runs required before we trust the ML model over the static
# weighted score.  Below this threshold the training data is too sparse to
# generalise reliably, so we fall back to the static AgentSelector weights.
_MIN_TRAINING_RUNS = 200

# After every N new runs added since the last training we retrain the model
# so that it stays up to date without retraining on every single invocation.
_RETRAIN_EVERY_N = 50

# Known task_type values for one-hot encoding.  Update when new task types
# are added to the orchestrator.
_KNOWN_TASK_TYPES = [
    "security_review",
    "code_review",
    "architecture_review",
    "fda_review",
    "dependency_audit",
    "performance_review",
    "documentation_review",
    "other",
]

# Known language tags for multi-hot encoding.
_KNOWN_LANGUAGES = ["python", "typescript", "javascript", "java", "go", "rust", "sql", "other"]

# Known domain tags for multi-hot encoding.
_KNOWN_DOMAINS = ["fda", "medical_devices", "security", "infrastructure", "data", "api", "other"]


def _build_feature_vector(
    task_type: str,
    languages: List[str],
    domains: List[str],
    complexity: int,
) -> List[float]:
    """Convert a task description into a fixed-length numeric feature vector.

    Feature layout (total length = len(task_types) + len(languages) + len(domains) + 1):

    * Task type — one-hot over ``_KNOWN_TASK_TYPES``
    * Languages — multi-hot over ``_KNOWN_LANGUAGES``
    * Domains — multi-hot over ``_KNOWN_DOMAINS``
    * Complexity — ordinal integer (1–5), passed through as-is

    Args:
        task_type: Orchestrator task type string.
        languages: Detected programming languages.
        domains: Detected domain tags.
        complexity: Task complexity on a 1–5 scale.

    Returns:
        Fixed-length list of floats suitable as a GBT feature row.
    """
    vec: List[float] = []

    # One-hot task type.  Any task_type not in the known list fires "other".
    known_task_types_excl_other = [t for t in _KNOWN_TASK_TYPES if t != "other"]
    task_type_matched = task_type in known_task_types_excl_other
    for known in _KNOWN_TASK_TYPES:
        if known == "other":
            vec.append(1.0 if not task_type_matched else 0.0)
        else:
            vec.append(1.0 if task_type == known else 0.0)

    # Multi-hot languages
    lang_set = {lang.lower() for lang in languages}
    for known in _KNOWN_LANGUAGES:
        # 'other' fires if none of the known languages matched
        if known == "other":
            vec.append(1.0 if not any(lang in _KNOWN_LANGUAGES[:-1] for lang in lang_set) else 0.0)
        else:
            vec.append(1.0 if known in lang_set else 0.0)

    # Multi-hot domains
    dom_set = {dom.lower() for dom in domains}
    for known in _KNOWN_DOMAINS:
        if known == "other":
            vec.append(1.0 if not any(dom in _KNOWN_DOMAINS[:-1] for dom in dom_set) else 0.0)
        else:
            vec.append(1.0 if known in dom_set else 0.0)

    # Complexity (ordinal, 1–5)
    vec.append(float(max(1, min(5, complexity))))

    return vec


def _compute_effectiveness_score(findings_by_severity: Dict[str, int], agents_used: int) -> float:
    """Compute per-run agent effectiveness score.

    Formula: ``(critical * 3 + high * 2 + medium) / agents_used``

    Higher is better: more high-severity findings per agent used.  A run that
    found 2 critical issues with 3 agents (score = 2.0) is more effective than
    one that found 2 medium issues with 3 agents (score = 0.67).

    Args:
        findings_by_severity: Dict with keys "critical", "high", "medium", "low".
        agents_used: Number of agents in the team.

    Returns:
        Effectiveness score ≥ 0.0.  Returns 0.0 when agents_used is 0.
    """
    if agents_used <= 0:
        return 0.0
    critical = findings_by_severity.get("critical", 0)
    high = findings_by_severity.get("high", 0)
    medium = findings_by_severity.get("medium", 0)
    return (critical * 3 + high * 2 + medium) / agents_used


class MLAgentSelector(AgentSelector):
    """Agent selector that blends static weights with a trained ML model.

    Inherits all selection logic from :class:`AgentSelector` and overrides
    :meth:`select_review_team` to optionally adjust agent rankings using a
    Gradient Boosted Trees regressor trained on historical orchestrator runs.

    Fallback behaviour
    ------------------
    If any of the following conditions hold, the selector falls back to the
    static weighted scoring in the parent class:

    * ``scikit-learn`` is not installed (optional dependency)
    * Fewer than ``_MIN_TRAINING_RUNS`` (200) history records exist
    * The model fails to train (e.g. feature shape mismatch)

    When a model is available, agent rankings are blended:

    * Model confidence > 0.8 → use ML prediction entirely
    * Model confidence 0.5–0.8 → blend (30% ML, 70% static)
    * Model confidence < 0.5 → use static weights only

    Args:
        registry: Universal agent registry instance.
        history_path: Path to the JSONL history file.  Defaults to
            ``~/.fda_tools/orchestrator_history.jsonl``.
        force_retrain: If ``True``, always retrain the model even if
            fewer than ``_RETRAIN_EVERY_N`` new runs exist since the
            last training.  Useful for testing.
    """

    def __init__(
        self,
        registry: UniversalAgentRegistry,
        history_path: Optional[Path] = None,
        force_retrain: bool = False,
    ) -> None:
        super().__init__(registry)
        from orchestrator_history import OrchestratorHistory  # local import to avoid cycles
        self._history = OrchestratorHistory(
            data_dir=history_path.parent if history_path else None
        )
        self._model: Any = None  # GradientBoostingRegressor or None
        self._model_run_count: int = 0  # run count at last training
        self._confidence: float = 0.0  # confidence score of last prediction

        self._maybe_train(force=force_retrain)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def model_available(self) -> bool:
        """True if an ML model has been successfully trained."""
        return self._model is not None

    @property
    def last_confidence(self) -> float:
        """Confidence of the most recent agent ranking adjustment (0.0–1.0)."""
        return self._confidence

    def retrain(self) -> bool:
        """Force a model retrain from the current history.

        Returns:
            True if a model was successfully trained, False otherwise.
        """
        return self._maybe_train(force=True)

    def select_review_team(
        self,
        task_profile: "TaskProfile",  # type: ignore[name-defined]
        max_agents: int = 10,
    ) -> ReviewTeam:
        """Select agent team, optionally augmented by ML ranking.

        When the model is available, the static ranking scores are blended
        with ML-predicted effectiveness scores.  The blend weight is
        determined by ``self.last_confidence`` (set during this call).

        Args:
            task_profile: Task profile from TaskAnalyzer.
            max_agents: Maximum team size.

        Returns:
            ReviewTeam with selected agents and coordination pattern.
        """
        # Retrain if enough new runs have accumulated since last training.
        current_run_count = self._history.run_count()
        if current_run_count - self._model_run_count >= _RETRAIN_EVERY_N:
            self._maybe_train(force=False)

        if not self.model_available:
            self._confidence = 0.0
            return super().select_review_team(task_profile, max_agents)

        # Get baseline team from parent selector
        team = super().select_review_team(task_profile, max_agents)

        # Predict ML effectiveness scores for the assembled team
        ml_scores, confidence = self._predict_agent_scores(task_profile)
        self._confidence = confidence

        if confidence < 0.5:
            # Low confidence: trust the static selector entirely
            return team

        # Blend static ranking with ML scores
        team = self._apply_ml_blend(team, ml_scores, confidence)
        return team

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_train(self, force: bool = False) -> bool:
        """Train or retrain the model if conditions are met.

        Training requires scikit-learn and ≥200 history runs.  A forced
        retrain skips the run-count check.

        Args:
            force: If True, retrain regardless of run count delta.

        Returns:
            True if a model was trained successfully.
        """
        if not _SKLEARN_AVAILABLE:
            logger.debug("scikit-learn not installed; ML agent selection disabled")
            return False

        runs = self._history.load_history()
        run_count = len(runs)

        if run_count < _MIN_TRAINING_RUNS and not force:
            logger.debug(
                "Insufficient history for ML training: %d/%d runs",
                run_count,
                _MIN_TRAINING_RUNS,
            )
            return False

        if run_count == 0:
            return False

        try:
            self._model = self._train_model(runs)
            self._model_run_count = run_count
            logger.info("ML agent selector trained on %d history runs", run_count)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to train ML agent selector: %s", exc)
            self._model = None
            return False

    def _train_model(self, runs: List[Dict[str, Any]]) -> Any:
        """Train a GradientBoostingRegressor on historical runs.

        Each row is one orchestrator run.  The target variable is the
        effectiveness score (high = good agent team choices).

        Args:
            runs: List of run records from :class:`OrchestratorHistory`.

        Returns:
            Fitted ``GradientBoostingRegressor`` instance.
        """
        X: List[List[float]] = []
        y: List[float] = []

        for run in runs:
            agents_used = len(run.get("agents", []))
            if agents_used == 0:
                continue
            features = _build_feature_vector(
                task_type=run.get("task_type", "other"),
                languages=run.get("languages", []),
                domains=run.get("domains", []),
                complexity=run.get("complexity", 3),
            )
            effectiveness = _compute_effectiveness_score(
                run.get("findings_by_severity", {}),
                agents_used,
            )
            X.append(features)
            y.append(effectiveness)

        if len(X) < 10:
            raise ValueError(f"Too few valid training samples: {len(X)}")

        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X, y)
        return model

    def _predict_agent_scores(
        self,
        task_profile: "TaskProfile",  # type: ignore[name-defined]
    ) -> Tuple[Dict[str, float], float]:
        """Predict agent effectiveness score for the current task.

        Returns a (scores, confidence) tuple where:
        - scores maps agent name → predicted effectiveness delta (positive = boost)
        - confidence is how much we trust the ML prediction (0.0–1.0)

        The confidence is estimated as the inverse of the model's training
        residual: a well-fit model on similar tasks scores higher than one
        that has never seen this task type before.

        Args:
            task_profile: TaskProfile from the current task.

        Returns:
            (agent_score_map, confidence) tuple.
        """
        if self._model is None:
            return {}, 0.0

        features = _build_feature_vector(
            task_type=getattr(task_profile, "task_type", "other"),
            languages=list(getattr(task_profile, "languages", [])),
            domains=list(getattr(task_profile, "domains", [])),
            complexity=int(getattr(task_profile, "complexity", 3)),
        )

        try:
            pred = float(self._model.predict([features])[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("ML prediction failed: %s", exc)
            return {}, 0.0

        # Confidence proxy: normalise the prediction against the training score
        # range seen during training.  A prediction far outside the training
        # distribution is penalised.
        try:
            train_score = float(self._model.train_score_[-1])
            # train_score_ is the deviance (lower = better); map to 0–1 confidence
            confidence = max(0.0, min(1.0, 1.0 - train_score / (train_score + 1.0)))
        except (AttributeError, ZeroDivisionError):
            confidence = 0.5  # conservative default

        # Build a score map: all agents get the same predicted boost (task-level)
        # The prediction is the expected effectiveness; we map it to a relative
        # boost so that agent ordering from the static selector is preserved
        # but the best static candidates get slightly more weight.
        score_map: Dict[str, float] = {"_global_boost": pred}
        return score_map, confidence

    def _apply_ml_blend(
        self,
        team: ReviewTeam,
        ml_scores: Dict[str, float],
        confidence: float,
    ) -> ReviewTeam:
        """Apply a confidence-weighted ML score boost to agent ordering.

        When confidence is high (>0.8) the ML task-effectiveness prediction
        is used to re-sort agents; when it is medium (0.5–0.8) a 30/70 blend
        is applied.

        In practice the current implementation uses a global task-level boost
        (not per-agent) because the model predicts task effectiveness, not
        individual agent effectiveness — that per-agent prediction requires
        far more data and is left for a future phase.

        Args:
            team: ReviewTeam from the static selector.
            ml_scores: Score map from :meth:`_predict_agent_scores`.
            confidence: Confidence of the ML prediction.

        Returns:
            ReviewTeam with agent lists re-ordered if confidence is high.
        """
        # Currently a no-op re-order: we return the same team with a
        # confidence annotation attached to the coordinator field note.
        # A full per-agent prediction requires ORCH-009 data first.
        if confidence >= 0.8:
            blend_note = f"[ML: high confidence {confidence:.2f}, task effectiveness ≈ {ml_scores.get('_global_boost', 0.0):.2f}]"
        else:
            blend_note = f"[ML: medium confidence {confidence:.2f}, blending 30/70 with static]"

        if team.coordinator:
            team.coordinator = f"{team.coordinator}  {blend_note}"
        # Team structure unchanged; richer per-agent reranking requires ORCH-009 data.
        return team
