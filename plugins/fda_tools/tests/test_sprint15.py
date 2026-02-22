"""
Tests for FDA-269  [ORCH-016] Multi-Repo Support
=================================================
Covers RepoConfig, RepoRegistry, CrossRepoDependency, CrossRepoDepGraph,
MultiRepoOrchestrator, and TaskRoute from lib/multi_repo_orchestrator.py.
"""

from __future__ import annotations

import json
import pytest

from fda_tools.lib.multi_repo_orchestrator import (
    CrossRepoDependency,
    CrossRepoDepGraph,
    DependencyCycleError,
    MultiRepoOrchestrator,
    RepoConfig,
    RepoNotFound,
    RepoRegistry,
    TaskRoute,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_repo(repo_id: str, language: str = "python", tags=(), hints=()) -> RepoConfig:
    return RepoConfig(
        repo_id          = repo_id,
        name             = f"Repo {repo_id}",
        url              = f"https://github.com/org/{repo_id}",
        primary_language = language,
        domain_tags      = frozenset(tags),
        agent_hints      = tuple(hints),
    )


def _make_dep(src: str, tgt: str, dep_type: str = "api") -> CrossRepoDependency:
    return CrossRepoDependency(source_repo=src, target_repo=tgt, dependency_type=dep_type)


# ═══════════════════════════════════════════════════════════════════════════════
# RepoConfig
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepoConfig:

    def test_frozen_prevents_mutation(self) -> None:
        repo = _make_repo("fda-tools")
        with pytest.raises((AttributeError, TypeError)):
            repo.repo_id = "other"  # type: ignore[misc]

    def test_default_domain_tags_is_frozenset(self) -> None:
        repo = _make_repo("fda-tools")
        assert isinstance(repo.domain_tags, frozenset)

    def test_default_agent_hints_is_tuple(self) -> None:
        repo = _make_repo("fda-tools")
        assert isinstance(repo.agent_hints, tuple)

    def test_to_dict_round_trip(self) -> None:
        repo = RepoConfig(
            repo_id          = "mdrp-web",
            name             = "MDRP Web",
            url              = "https://github.com/org/mdrp-web",
            primary_language = "typescript",
            domain_tags      = frozenset({"frontend", "nextjs"}),
            agent_hints      = ("nextjs-developer", "typescript-pro"),
        )
        restored = RepoConfig.from_dict(repo.to_dict())
        assert restored.repo_id          == repo.repo_id
        assert restored.primary_language == repo.primary_language
        assert restored.domain_tags      == repo.domain_tags
        assert restored.agent_hints      == repo.agent_hints

    def test_to_dict_domain_tags_sorted(self) -> None:
        repo = _make_repo("x", tags=("zebra", "apple", "mango"))
        d = repo.to_dict()
        assert d["domain_tags"] == sorted(d["domain_tags"])

    def test_from_dict_missing_optional_keys(self) -> None:
        data = {"repo_id": "x", "name": "X", "url": "u", "primary_language": "go"}
        repo = RepoConfig.from_dict(data)
        assert repo.domain_tags  == frozenset()
        assert repo.agent_hints  == ()


# ═══════════════════════════════════════════════════════════════════════════════
# RepoRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepoRegistry:

    def test_add_and_get(self) -> None:
        reg = RepoRegistry()
        repo = _make_repo("fda-tools")
        reg.add(repo)
        assert reg.get("fda-tools") is repo

    def test_get_missing_raises_repo_not_found(self) -> None:
        reg = RepoRegistry()
        with pytest.raises(RepoNotFound):
            reg.get("unknown")

    def test_remove_decrements_count(self) -> None:
        reg = RepoRegistry()
        reg.add(_make_repo("a"))
        reg.add(_make_repo("b"))
        reg.remove("a")
        assert reg.count() == 1

    def test_remove_missing_raises(self) -> None:
        reg = RepoRegistry()
        with pytest.raises(RepoNotFound):
            reg.remove("ghost")

    def test_add_overwrites_existing(self) -> None:
        reg = RepoRegistry()
        reg.add(_make_repo("fda-tools", language="python"))
        reg.add(_make_repo("fda-tools", language="rust"))
        assert reg.get("fda-tools").primary_language == "rust"

    def test_list_repos_sorted_by_repo_id(self) -> None:
        reg = RepoRegistry()
        for rid in ("z-repo", "a-repo", "m-repo"):
            reg.add(_make_repo(rid))
        ids = [r.repo_id for r in reg.list_repos()]
        assert ids == sorted(ids)

    def test_find_by_language(self) -> None:
        reg = RepoRegistry()
        reg.add(_make_repo("py-a", language="python"))
        reg.add(_make_repo("py-b", language="python"))
        reg.add(_make_repo("ts-c", language="typescript"))
        result = reg.find_by_language("python")
        assert len(result) == 2

    def test_find_by_language_case_insensitive(self) -> None:
        reg = RepoRegistry()
        reg.add(_make_repo("r1", language="Python"))
        assert len(reg.find_by_language("python")) == 1

    def test_find_by_domain_tag(self) -> None:
        reg = RepoRegistry()
        reg.add(_make_repo("fda-tools", tags=("fda", "regulatory")))
        reg.add(_make_repo("mdrp-web",  tags=("frontend", "regulatory")))
        reg.add(_make_repo("ml-svc",    tags=("ml",)))
        result = reg.find_by_domain_tag("regulatory")
        assert {r.repo_id for r in result} == {"fda-tools", "mdrp-web"}

    def test_to_json_from_json_round_trip(self) -> None:
        reg = RepoRegistry()
        reg.add(RepoConfig(
            repo_id="fda", name="FDA", url="u", primary_language="python",
            domain_tags=frozenset({"fda"}), agent_hints=("python-pro",),
        ))
        reg.add(_make_repo("web"))
        restored = RepoRegistry.from_json(reg.to_json())
        assert restored.repo_ids() == reg.repo_ids()
        assert restored.get("fda").domain_tags == frozenset({"fda"})

    def test_to_json_produces_valid_json(self) -> None:
        reg = RepoRegistry()
        reg.add(_make_repo("r"))
        json.loads(reg.to_json())  # must not raise


# ═══════════════════════════════════════════════════════════════════════════════
# CrossRepoDependency
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossRepoDependency:

    def test_valid_dependency_types(self) -> None:
        for dep_type in ("api", "library", "data", "deploy", "test"):
            dep = _make_dep("a", "b", dep_type)
            assert dep.dependency_type == dep_type

    def test_invalid_dependency_type_raises(self) -> None:
        with pytest.raises(ValueError, match="dependency_type"):
            CrossRepoDependency(source_repo="a", target_repo="b", dependency_type="unknown")

    def test_self_dependency_raises(self) -> None:
        with pytest.raises(ValueError):
            CrossRepoDependency(source_repo="a", target_repo="a", dependency_type="api")

    def test_frozen(self) -> None:
        dep = _make_dep("a", "b")
        with pytest.raises((AttributeError, TypeError)):
            dep.source_repo = "x"  # type: ignore[misc]

    def test_description_defaults_empty(self) -> None:
        dep = _make_dep("a", "b")
        assert dep.description == ""

    def test_description_stored(self) -> None:
        dep = CrossRepoDependency("a", "b", "api", "Frontend calls backend API")
        assert "Frontend" in dep.description


# ═══════════════════════════════════════════════════════════════════════════════
# CrossRepoDepGraph
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossRepoDepGraph:

    def _three_node_graph(self) -> CrossRepoDepGraph:
        """web → api → db"""
        g = CrossRepoDepGraph()
        g.add_dependency(_make_dep("web", "api"))
        g.add_dependency(_make_dep("api", "db"))
        return g

    def test_add_dependency_increments_edge_count(self) -> None:
        g = CrossRepoDepGraph()
        g.add_dependency(_make_dep("a", "b"))
        assert g.edge_count() == 1

    def test_node_count_after_adding_edges(self) -> None:
        g = self._three_node_graph()
        assert g.node_count() == 3

    def test_dependencies_of_direct(self) -> None:
        g = self._three_node_graph()
        assert g.dependencies_of("web") == ["api"]
        assert g.dependencies_of("api") == ["db"]
        assert g.dependencies_of("db")  == []

    def test_dependents_of(self) -> None:
        g = self._three_node_graph()
        assert g.dependents_of("api") == ["web"]
        assert g.dependents_of("db")  == ["api"]

    def test_all_dependencies_transitive(self) -> None:
        g = self._three_node_graph()
        result = g.all_dependencies_of("web")
        assert "api" in result
        assert "db"  in result

    def test_topological_order_deps_first(self) -> None:
        g = self._three_node_graph()
        order = g.topological_order()
        assert order.index("db")  < order.index("api")
        assert order.index("api") < order.index("web")

    def test_cycle_detection_raises(self) -> None:
        g = CrossRepoDepGraph()
        g.add_dependency(_make_dep("a", "b"))
        g.add_dependency(_make_dep("b", "c"))
        with pytest.raises(DependencyCycleError):
            g.add_dependency(_make_dep("c", "a"))  # would close a→b→c→a

    def test_impact_analysis_transitive(self) -> None:
        g = self._three_node_graph()
        # Changing "db" affects "api" and "web"
        affected = g.impact_analysis("db")
        assert "api" in affected
        assert "web" in affected

    def test_impact_analysis_leaf_node_empty(self) -> None:
        g = self._three_node_graph()
        # Changing "web" (no dependents) has zero impact
        assert g.impact_analysis("web") == []

    def test_dependency_chain_starts_with_repo(self) -> None:
        g = self._three_node_graph()
        chain = g.dependency_chain("web")
        assert chain[0] == "web"
        assert "api" in chain
        assert "db"  in chain

    def test_all_edges_iteration(self) -> None:
        g = self._three_node_graph()
        edges = list(g.all_edges())
        assert len(edges) == 2

    def test_diamond_dependency_topological_sort(self) -> None:
        """A → B, A → C, B → D, C → D  (diamond — D must come first)"""
        g = CrossRepoDepGraph()
        g.add_dependency(_make_dep("A", "B"))
        g.add_dependency(_make_dep("A", "C"))
        g.add_dependency(_make_dep("B", "D"))
        g.add_dependency(_make_dep("C", "D"))
        order = g.topological_order()
        assert order.index("D") < order.index("B")
        assert order.index("D") < order.index("C")
        assert order.index("B") < order.index("A")
        assert order.index("C") < order.index("A")


# ═══════════════════════════════════════════════════════════════════════════════
# MultiRepoOrchestrator  +  TaskRoute
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiRepoOrchestrator:

    def _make_registry(self) -> RepoRegistry:
        reg = RepoRegistry()
        reg.add(RepoConfig(
            repo_id          = "fda-tools",
            name             = "FDA Tools Plugin",
            url              = "u",
            primary_language = "python",
            domain_tags      = frozenset({"fda", "regulatory", "510k"}),
            agent_hints      = ("voltagent-lang:python-pro",),
        ))
        reg.add(RepoConfig(
            repo_id          = "mdrp-web",
            name             = "MDRP Web Frontend",
            url              = "u",
            primary_language = "typescript",
            domain_tags      = frozenset({"frontend", "nextjs", "react"}),
            agent_hints      = ("voltagent-lang:nextjs-developer",),
        ))
        reg.add(RepoConfig(
            repo_id          = "ml-service",
            name             = "ML Service",
            url              = "u",
            primary_language = "python",
            domain_tags      = frozenset({"ml", "embeddings", "vector"}),
            agent_hints      = ("voltagent-data-ai:ai-engineer",),
        ))
        return reg

    def _make_graph(self) -> CrossRepoDepGraph:
        g = CrossRepoDepGraph()
        # web depends on fda-tools (API calls)
        g.add_dependency(CrossRepoDependency("mdrp-web", "fda-tools", "api", "Web frontend calls FastAPI backend"))
        # fda-tools depends on ml-service (embeddings)
        g.add_dependency(CrossRepoDependency("fda-tools", "ml-service", "api", "Calls embedding API"))
        return g

    def test_route_task_returns_task_route(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry())
        route = orch.route_task("Fix 510k predicate search bug", keywords=["510k", "predicate"])
        assert isinstance(route, TaskRoute)

    def test_route_task_primary_repo_is_string(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry())
        route = orch.route_task("Fix 510k predicate search bug", keywords=["510k", "fda"])
        assert isinstance(route.primary_repo, str)
        assert route.primary_repo == "fda-tools"

    def test_route_task_frontend_keywords(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry())
        route = orch.route_task("Update Next.js dashboard layout", keywords=["nextjs", "frontend"])
        assert route.primary_repo == "mdrp-web"

    def test_route_task_ml_keywords(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry())
        route = orch.route_task("Optimize embeddings pipeline", keywords=["embeddings", "ml"])
        assert route.primary_repo == "ml-service"

    def test_route_task_dependency_chain_populated(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry(), dep_graph=self._make_graph())
        route = orch.route_task("Fix 510k search", keywords=["510k"])
        # fda-tools depends on ml-service via the graph
        assert "ml-service" in route.dependency_chain

    def test_route_task_supporting_repos(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry(), dep_graph=self._make_graph())
        route = orch.route_task("Fix 510k search", keywords=["510k"])
        assert isinstance(route.supporting_repos, tuple)

    def test_route_task_agent_hints_non_empty(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry())
        route = orch.route_task("Fix 510k predicate", keywords=["510k", "fda"])
        assert len(route.agent_hints) > 0

    def test_route_task_agent_hints_no_duplicates(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry(), dep_graph=self._make_graph())
        route = orch.route_task("Fix 510k search", keywords=["510k"])
        assert len(route.agent_hints) == len(set(route.agent_hints))

    def test_route_task_routing_reason_non_empty(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry())
        route = orch.route_task("anything")
        assert len(route.routing_reason) > 0

    def test_route_task_empty_registry_raises(self) -> None:
        orch = MultiRepoOrchestrator(registry=RepoRegistry())
        with pytest.raises(RepoNotFound):
            orch.route_task("anything")

    def test_route_task_no_keywords_still_routes(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry())
        route = orch.route_task("update the fda regulatory pipeline")
        assert isinstance(route.primary_repo, str)

    def test_affected_repos_uses_impact_analysis(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry(), dep_graph=self._make_graph())
        # Changing ml-service affects fda-tools → affects mdrp-web
        affected = orch.affected_repos("ml-service")
        assert "fda-tools" in affected
        assert "mdrp-web"  in affected

    def test_execution_order_deps_first(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry(), dep_graph=self._make_graph())
        order = orch.execution_order()
        # ml-service must come before fda-tools; fda-tools before mdrp-web
        assert order.index("ml-service") < order.index("fda-tools")
        assert order.index("fda-tools")  < order.index("mdrp-web")

    def test_dependency_chain_is_tuple(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry(), dep_graph=self._make_graph())
        route = orch.route_task("510k fix", keywords=["510k"])
        assert isinstance(route.dependency_chain, tuple)

    def test_supporting_repos_is_tuple(self) -> None:
        orch = MultiRepoOrchestrator(registry=self._make_registry(), dep_graph=self._make_graph())
        route = orch.route_task("510k fix", keywords=["510k"])
        assert isinstance(route.supporting_repos, tuple)
