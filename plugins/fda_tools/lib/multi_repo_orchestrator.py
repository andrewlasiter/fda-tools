"""
FDA-269  [ORCH-016] Multi-Repo Support — Cross-Repository Orchestration
=========================================================================
Phase 11 from ORCHESTRATOR_ARCHITECTURE.md.

Extends the Universal Multi-Agent Orchestrator beyond a single plugin to
support orchestration across multiple repositories with cross-repo
dependency analysis, impact estimation, and task routing.

Design
------
``RepoConfig``           — immutable description of one repository.
``RepoRegistry``         — add / get / list repos; JSON-serialisable.
``CrossRepoDependency``  — directed edge in the dependency graph.
``CrossRepoDepGraph``    — DAG: cycle detection, topological sort,
                           reachability, and impact analysis.
``MultiRepoOrchestrator``— top-level facade; routes tasks to the most
                           appropriate repo(s) and resolves cross-repo
                           dependencies via the DAG.
``TaskRoute``            — result of routing a task.

Usage
-----
    registry = RepoRegistry()
    registry.add(RepoConfig(
        repo_id="fda-tools",
        name="FDA Tools Plugin",
        url="https://github.com/andrewlasiter/fda-tools",
        primary_language="python",
        domain_tags=frozenset({"fda", "regulatory", "510k"}),
        agent_hints=("voltagent-lang:python-pro",),
    ))
    registry.add(RepoConfig(
        repo_id="mdrp-web",
        name="MDRP Web Frontend",
        url="https://github.com/andrewlasiter/mdrp-web",
        primary_language="typescript",
        domain_tags=frozenset({"frontend", "react", "nextjs"}),
        agent_hints=("voltagent-lang:nextjs-developer",),
    ))

    graph = CrossRepoDepGraph()
    graph.add_dependency(CrossRepoDependency(
        source_repo="mdrp-web",
        target_repo="fda-tools",
        dependency_type="api",
        description="Web frontend calls FDA Tools FastAPI backend",
    ))

    orch = MultiRepoOrchestrator(registry=registry, dep_graph=graph)
    route = orch.route_task(
        task="Add rate limiting to the 510(k) search endpoint",
        keywords=["rate limiting", "510k", "search"],
    )
    # route.primary_repo → "fda-tools"
    # route.dependency_chain → ["fda-tools", "mdrp-web"]
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Tuple


# ── Exceptions ────────────────────────────────────────────────────────────────

class RepoNotFound(KeyError):
    """Raised when a repo_id is not in the registry."""


class DependencyCycleError(ValueError):
    """Raised when adding a dependency would create a cycle in the DAG."""


# ── RepoConfig ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RepoConfig:
    """
    Immutable description of a single repository.

    Attributes:
        repo_id:          Short unique identifier (e.g. ``"fda-tools"``).
        name:             Human-readable display name.
        url:              Remote URL (GitHub, GitLab, etc.).
        primary_language: Dominant programming language (e.g. ``"python"``).
        domain_tags:      Frozenset of domain labels used for task routing
                          (e.g. ``frozenset({"fda", "regulatory", "510k"})``).
        agent_hints:      Tuple of agent IDs well-suited to this repo's stack.
    """
    repo_id:          str
    name:             str
    url:              str
    primary_language: str
    domain_tags:      FrozenSet[str]     = field(default_factory=frozenset)
    agent_hints:      Tuple[str, ...]    = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "repo_id":          self.repo_id,
            "name":             self.name,
            "url":              self.url,
            "primary_language": self.primary_language,
            "domain_tags":      sorted(self.domain_tags),
            "agent_hints":      list(self.agent_hints),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepoConfig":
        """Deserialize from a dict produced by ``to_dict()``."""
        return cls(
            repo_id          = data["repo_id"],
            name             = data["name"],
            url              = data["url"],
            primary_language = data["primary_language"],
            domain_tags      = frozenset(data.get("domain_tags", [])),
            agent_hints      = tuple(data.get("agent_hints", [])),
        )


# ── RepoRegistry ──────────────────────────────────────────────────────────────

class RepoRegistry:
    """
    Mutable store for :class:`RepoConfig` objects.

    Supports JSON serialisation so configs can be persisted and reloaded
    without a live database connection.
    """

    def __init__(self) -> None:
        self._repos: Dict[str, RepoConfig] = {}

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(self, repo: RepoConfig) -> None:
        """Register a repository.  Overwrites an existing entry with the same id."""
        self._repos[repo.repo_id] = repo

    def remove(self, repo_id: str) -> None:
        """Remove a repository by id.

        Raises:
            RepoNotFound: If repo_id is not registered.
        """
        if repo_id not in self._repos:
            raise RepoNotFound(repo_id)
        del self._repos[repo_id]

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, repo_id: str) -> RepoConfig:
        """Return the :class:`RepoConfig` for *repo_id*.

        Raises:
            RepoNotFound: If not registered.
        """
        try:
            return self._repos[repo_id]
        except KeyError:
            raise RepoNotFound(repo_id)

    def list_repos(self) -> List[RepoConfig]:
        """Return all registered repos sorted by repo_id."""
        return sorted(self._repos.values(), key=lambda r: r.repo_id)

    def repo_ids(self) -> List[str]:
        """Return sorted list of all registered repo IDs."""
        return sorted(self._repos)

    def count(self) -> int:
        """Number of registered repositories."""
        return len(self._repos)

    def find_by_language(self, language: str) -> List[RepoConfig]:
        """Return repos whose primary_language matches (case-insensitive)."""
        lang = language.lower()
        return [r for r in self._repos.values() if r.primary_language.lower() == lang]

    def find_by_domain_tag(self, tag: str) -> List[RepoConfig]:
        """Return repos that include *tag* in their domain_tags."""
        return [r for r in self._repos.values() if tag in r.domain_tags]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_json(self) -> str:
        """Serialize the entire registry to a JSON string."""
        return json.dumps(
            [r.to_dict() for r in self.list_repos()],
            indent=2,
        )

    @classmethod
    def from_json(cls, data: str) -> "RepoRegistry":
        """Restore a :class:`RepoRegistry` from JSON produced by ``to_json()``."""
        registry = cls()
        for item in json.loads(data):
            registry.add(RepoConfig.from_dict(item))
        return registry


# ── CrossRepoDependency ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class CrossRepoDependency:
    """
    A directed dependency edge in the cross-repo DAG.

    ``source_repo`` depends on ``target_repo``
    (i.e. source *needs* target to exist / run first).

    Attributes:
        source_repo:     Repo that has the dependency.
        target_repo:     Repo being depended upon.
        dependency_type: Nature of the link — one of
                         ``"api"``, ``"library"``, ``"data"``, ``"deploy"``, ``"test"``.
        description:     Human-readable description of the dependency.
    """
    source_repo:     str
    target_repo:     str
    dependency_type: str
    description:     str = ""

    _VALID_TYPES = frozenset({"api", "library", "data", "deploy", "test"})

    def __post_init__(self) -> None:
        if self.dependency_type not in self._VALID_TYPES:
            raise ValueError(
                f"dependency_type must be one of {sorted(self._VALID_TYPES)}, "
                f"got '{self.dependency_type}'"
            )
        if self.source_repo == self.target_repo:
            raise ValueError("source_repo and target_repo must be different")


# ── CrossRepoDepGraph ─────────────────────────────────────────────────────────

class CrossRepoDepGraph:
    """
    Directed acyclic graph (DAG) of cross-repository dependencies.

    Edges are ``CrossRepoDependency`` objects: ``source → target`` means
    *source* depends on *target*.  The graph rejects cycles.

    Key operations
    --------------
    - ``add_dependency(dep)``        — add edge; raises :class:`DependencyCycleError` if it creates a cycle.
    - ``dependencies_of(repo_id)``   — repos that *repo_id* directly depends on.
    - ``dependents_of(repo_id)``     — repos that directly depend on *repo_id*.
    - ``topological_order()``        — all repos in dependency-safe execution order.
    - ``impact_analysis(repo_id)``   — all repos transitively affected by a change in *repo_id*.
    - ``dependency_chain(repo_id)``  — linear chain from *repo_id* to all its transitive deps.
    """

    def __init__(self) -> None:
        # adjacency: source → set of targets
        self._edges: Dict[str, List[CrossRepoDependency]] = {}

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_dependency(self, dep: CrossRepoDependency) -> None:
        """Add a dependency edge.

        Raises:
            DependencyCycleError: If adding this edge would create a cycle.
        """
        # Ensure both nodes exist in the adjacency list
        for node in (dep.source_repo, dep.target_repo):
            if node not in self._edges:
                self._edges[node] = []

        # Check would-be cycle BEFORE adding
        if self._would_create_cycle(dep.source_repo, dep.target_repo):
            raise DependencyCycleError(
                f"Adding '{dep.source_repo}' → '{dep.target_repo}' would create a cycle"
            )
        self._edges[dep.source_repo].append(dep)

    # ── Cycle detection ───────────────────────────────────────────────────────

    def _would_create_cycle(self, new_source: str, new_target: str) -> bool:
        """Return True if adding source→target would create a cycle."""
        # A cycle exists if new_target can already reach new_source
        visited: set = set()

        def dfs(node: str) -> bool:
            if node == new_source:
                return True
            if node in visited:
                return False
            visited.add(node)
            for dep in self._edges.get(node, []):
                if dfs(dep.target_repo):
                    return True
            return False

        return dfs(new_target)

    # ── Queries ───────────────────────────────────────────────────────────────

    def dependencies_of(self, repo_id: str) -> List[str]:
        """Direct dependencies (targets) of *repo_id*."""
        return [d.target_repo for d in self._edges.get(repo_id, [])]

    def dependents_of(self, repo_id: str) -> List[str]:
        """Repos that directly depend on *repo_id* (reverse edges)."""
        return [
            src
            for src, deps in self._edges.items()
            if any(d.target_repo == repo_id for d in deps)
        ]

    def all_dependencies_of(self, repo_id: str) -> List[str]:
        """All transitive dependencies of *repo_id* (BFS)."""
        visited: List[str] = []
        queue = list(self.dependencies_of(repo_id))
        seen = set(queue)
        while queue:
            node = queue.pop(0)
            visited.append(node)
            for dep in self.dependencies_of(node):
                if dep not in seen:
                    seen.add(dep)
                    queue.append(dep)
        return visited

    def impact_analysis(self, repo_id: str) -> List[str]:
        """All repos transitively affected by a change in *repo_id* (reverse BFS)."""
        result: List[str] = []
        queue = list(self.dependents_of(repo_id))
        seen = set(queue)
        while queue:
            node = queue.pop(0)
            result.append(node)
            for dep in self.dependents_of(node):
                if dep not in seen:
                    seen.add(dep)
                    queue.append(dep)
        return result

    def dependency_chain(self, repo_id: str) -> List[str]:
        """
        Return a linear list starting with *repo_id* followed by all transitive
        dependencies in breadth-first order.
        """
        return [repo_id] + self.all_dependencies_of(repo_id)

    def topological_order(self) -> List[str]:
        """
        Return all known repo_ids in topological order (dependencies first).

        Uses Kahn's algorithm (in-degree reduction).

        Raises:
            DependencyCycleError: If a cycle exists (should not happen if
                                  ``add_dependency`` is always used).
        """
        # Build in-degree map
        in_degree: Dict[str, int] = {node: 0 for node in self._edges}
        for deps in self._edges.values():
            for dep in deps:
                in_degree[dep.target_repo] = in_degree.get(dep.target_repo, 0) + 1
                if dep.target_repo not in in_degree:
                    in_degree[dep.target_repo] = 0

        # Start from nodes with in-degree 0
        queue = sorted(k for k, v in in_degree.items() if v == 0)
        result: List[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dep in self._edges.get(node, []):
                in_degree[dep.target_repo] -= 1
                if in_degree[dep.target_repo] == 0:
                    queue.append(dep.target_repo)
                    queue.sort()

        if len(result) != len(in_degree):
            raise DependencyCycleError("Cycle detected during topological sort")
        # Kahn's produces sources-first (dependents before dependencies).
        # Reverse for execution order (dependencies first, dependents last).
        return list(reversed(result))

    def edge_count(self) -> int:
        """Total number of dependency edges."""
        return sum(len(deps) for deps in self._edges.values())

    def node_count(self) -> int:
        """Total number of known repo nodes."""
        return len(self._edges)

    def all_edges(self) -> Iterator[CrossRepoDependency]:
        """Iterate over all dependency edges."""
        for deps in self._edges.values():
            yield from deps


# ── TaskRoute ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TaskRoute:
    """
    Result of routing a task through the :class:`MultiRepoOrchestrator`.

    Attributes:
        primary_repo:      The repo best suited to own this task.
        supporting_repos:  Other repos involved via cross-repo dependencies.
        dependency_chain:  Full ordered chain from primary to its transitive deps.
        agent_hints:       Aggregated agent suggestions from all involved repos.
        routing_reason:    Human-readable explanation of why this routing was chosen.
        keyword_matches:   Which keywords matched which repos (for debugging).
    """
    primary_repo:     str
    supporting_repos: Tuple[str, ...]
    dependency_chain: Tuple[str, ...]
    agent_hints:      Tuple[str, ...]
    routing_reason:   str
    keyword_matches:  Tuple[Tuple[str, str], ...]  = field(default_factory=tuple)


# ── MultiRepoOrchestrator ─────────────────────────────────────────────────────

class MultiRepoOrchestrator:
    """
    Top-level facade that routes tasks to appropriate repo(s) and resolves
    cross-repo dependencies using the :class:`CrossRepoDepGraph`.

    Routing algorithm
    -----------------
    1. Score every registered repo against the task description + keywords:

       - +2 for each keyword that appears in a domain tag
       - +1 for each keyword that appears in repo name / primary_language
       - +1 for each keyword that matches an agent_hint fragment

    2. The highest-scoring repo becomes ``primary_repo``.

    3. Cross-repo dependencies of ``primary_repo`` are resolved from the graph
       to populate ``supporting_repos`` and ``dependency_chain``.

    4. Agent hints from primary + supporting repos are deduplicated and returned
       in the ``TaskRoute``.
    """

    def __init__(
        self,
        registry:  RepoRegistry,
        dep_graph: Optional[CrossRepoDepGraph] = None,
    ) -> None:
        self.registry  = registry
        self.dep_graph = dep_graph or CrossRepoDepGraph()

    # ── Routing ───────────────────────────────────────────────────────────────

    def route_task(
        self,
        task:     str,
        keywords: Optional[List[str]] = None,
    ) -> TaskRoute:
        """
        Route a task to the most relevant repo(s).

        Args:
            task:     Natural-language task description.
            keywords: Optional list of keywords to boost scoring.

        Returns:
            A :class:`TaskRoute` describing the recommended repo(s) and agents.

        Raises:
            RepoNotFound: If the registry is empty (no repos registered).
        """
        if self.registry.count() == 0:
            raise RepoNotFound("No repositories registered in the registry")

        all_keywords = list(keywords or []) + task.lower().split()
        normalised   = [k.lower().strip(".,;:!?") for k in all_keywords]

        scores: Dict[str, int]                    = {}
        matches: Dict[str, List[Tuple[str, str]]] = {}

        for repo in self.registry.list_repos():
            score = 0
            repo_matches: List[Tuple[str, str]] = []

            for kw in normalised:
                if not kw:
                    continue
                for tag in repo.domain_tags:
                    if kw in tag or tag in kw:
                        score += 2
                        repo_matches.append((kw, f"domain_tag:{tag}"))
                if kw in repo.name.lower() or kw in repo.primary_language.lower():
                    score += 1
                    repo_matches.append((kw, f"repo_name_or_language"))
                for hint in repo.agent_hints:
                    if kw in hint.lower():
                        score += 1
                        repo_matches.append((kw, f"agent_hint:{hint}"))

            scores[repo.repo_id]  = score
            matches[repo.repo_id] = repo_matches

        # Pick highest-scoring repo (alphabetical tiebreak for determinism)
        primary_id = max(scores, key=lambda rid: (scores[rid], rid))

        # Resolve cross-repo chain
        chain         = self.dep_graph.dependency_chain(primary_id)
        supporting    = tuple(r for r in chain[1:] if self.registry._repos.get(r))

        # Aggregate agent hints from all involved repos
        seen_hints:   List[str] = []
        hint_set:     set       = set()
        involved_ids = [primary_id] + list(supporting)
        for rid in involved_ids:
            repo = self.registry._repos.get(rid)
            if repo:
                for h in repo.agent_hints:
                    if h not in hint_set:
                        hint_set.add(h)
                        seen_hints.append(h)

        reason = (
            f"Routed to '{primary_id}' (score={scores[primary_id]}) "
            f"based on {len(matches[primary_id])} keyword match(es). "
            f"Cross-repo chain: {' → '.join(chain)}."
        )

        flat_matches = tuple(
            (kw, ctx)
            for rid in scores
            for kw, ctx in matches[rid]
        )

        return TaskRoute(
            primary_repo     = primary_id,
            supporting_repos = supporting,
            dependency_chain = tuple(chain),
            agent_hints      = tuple(seen_hints),
            routing_reason   = reason,
            keyword_matches  = flat_matches,
        )

    # ── Convenience ───────────────────────────────────────────────────────────

    def affected_repos(self, changed_repo_id: str) -> List[str]:
        """
        Return repo IDs that should be re-tested / re-reviewed when
        *changed_repo_id* changes (via impact analysis on the dep graph).
        """
        return self.dep_graph.impact_analysis(changed_repo_id)

    def execution_order(self) -> List[str]:
        """
        Return all registered repo IDs in safe execution order
        (dependencies before dependents).
        """
        topo = self.dep_graph.topological_order()
        registered = set(self.registry.repo_ids())
        # Topo order first, then any registered repos not in the graph
        in_graph  = [r for r in topo if r in registered]
        not_graph = sorted(r for r in registered if r not in topo)
        return in_graph + not_graph
