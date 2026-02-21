"""Tests for multi-repo orchestration support (FDA-215 / ORCH-011).

Coverage:
- RepoConfig: resolved_path, serialisation round-trip
- RepoRegistry: register/unregister/get/list_repos/primary, resolve_repos,
  persistence (save/load/corrupt), default seeding, format_registry
- CrossRepoImportDetector.detect(): matches imports, skips source repo,
  handles missing files
- RepoRegistry.detect_cross_repo_imports(): delegates to detector
- RepoRegistry.build_dependency_graph(): correct edge set
"""

import json
import textwrap
from pathlib import Path

import pytest

from fda_tools.scripts.repo_registry import (
    DEFAULT_REPOS,
    CrossRepoDependency,
    CrossRepoImportDetector,
    RepoConfig,
    RepoRegistry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(tmp_path: Path) -> RepoRegistry:
    """Return a fresh, empty (no-default) registry backed by tmp_path."""
    store = tmp_path / "repo_registry.json"
    # Seed with an empty repos list so we control the contents.
    store.write_text(json.dumps({"repos": []}), encoding="utf-8")
    return RepoRegistry(store_path=store)


def _write_py(path: Path, content: str) -> Path:
    """Write a Python source file and return its Path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# RepoConfig
# ---------------------------------------------------------------------------


class TestRepoConfig:
    """Tests for the RepoConfig dataclass."""

    def test_resolved_path_expands_tilde(self):
        cfg = RepoConfig(name="r", path="~/projects/r", team="T")
        resolved = cfg.resolved_path
        assert "~" not in str(resolved)
        assert resolved.is_absolute()

    def test_serialisation_round_trip(self):
        cfg = RepoConfig(name="fda-tools", path="~/fda-tools", team="FDA tools", primary=True)
        d = cfg.to_dict()
        cfg2 = RepoConfig.from_dict(d)
        assert cfg2.name == cfg.name
        assert cfg2.path == cfg.path
        assert cfg2.team == cfg.team
        assert cfg2.primary == cfg.primary

    def test_from_dict_ignores_unknown_keys(self):
        d = {"name": "x", "path": "/p", "team": "T", "primary": False, "unknown": "y"}
        cfg = RepoConfig.from_dict(d)
        assert cfg.name == "x"

    def test_primary_defaults_to_false(self):
        cfg = RepoConfig.from_dict({"name": "x", "path": "/p", "team": "T"})
        assert not cfg.primary


# ---------------------------------------------------------------------------
# RepoRegistry CRUD
# ---------------------------------------------------------------------------


class TestRepoRegistryCRUD:
    """Tests for register / unregister / get / list_repos / primary."""

    def test_register_adds_repo(self, tmp_path):
        reg = _make_registry(tmp_path)
        cfg = reg.register("my-repo", path="~/my-repo", team="My Team")
        assert reg.get("my-repo") is cfg

    def test_register_replaces_existing(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("r", path="~/old", team="T")
        reg.register("r", path="~/new", team="T2")
        assert reg.get("r").path == "~/new"

    def test_unregister_removes_repo(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("r", path="~/r", team="T")
        result = reg.unregister("r")
        assert result is True
        assert reg.get("r") is None

    def test_unregister_unknown_returns_false(self, tmp_path):
        reg = _make_registry(tmp_path)
        assert reg.unregister("nonexistent") is False

    def test_list_repos_sorted_primary_first(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("b-repo", path="~/b", team="T")
        reg.register("a-primary", path="~/a", team="T", primary=True)
        listed = reg.list_repos()
        assert listed[0].name == "a-primary"

    def test_primary_returns_primary_repo(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("secondary", path="~/s", team="T", primary=False)
        reg.register("main", path="~/m", team="T", primary=True)
        assert reg.primary().name == "main"

    def test_primary_returns_none_when_no_primary(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("r", path="~/r", team="T", primary=False)
        assert reg.primary() is None


# ---------------------------------------------------------------------------
# RepoRegistry resolve_repos
# ---------------------------------------------------------------------------


class TestResolveRepos:
    """Tests for resolve_repos() name → config mapping."""

    def test_known_names_resolved(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("fda-tools", path="~/t", team="T")
        reg.register("fda-writer", path="~/w", team="W")
        resolved = reg.resolve_repos(["fda-tools", "fda-writer"])
        assert [r.name for r in resolved] == ["fda-tools", "fda-writer"]

    def test_unknown_names_skipped(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("fda-tools", path="~/t", team="T")
        resolved = reg.resolve_repos(["fda-tools", "unknown-repo"])
        assert len(resolved) == 1
        assert resolved[0].name == "fda-tools"

    def test_empty_list_returns_empty(self, tmp_path):
        reg = _make_registry(tmp_path)
        assert reg.resolve_repos([]) == []


# ---------------------------------------------------------------------------
# CrossRepoImportDetector
# ---------------------------------------------------------------------------


class TestCrossRepoImportDetector:
    """Tests for cross-repo import detection."""

    def _make_reg_with_two_repos(self, tmp_path: Path) -> RepoRegistry:
        reg = _make_registry(tmp_path)
        reg.register("fda-tools", path=str(tmp_path / "fda-tools"), team="T", primary=True)
        reg.register("fda-writer", path=str(tmp_path / "fda-writer"), team="W")
        return reg

    def test_detects_from_import(self, tmp_path):
        reg = self._make_reg_with_two_repos(tmp_path)
        src = _write_py(
            tmp_path / "auth.py",
            """
            from fda_writer.templates import TemplateEngine
            import os
            """,
        )
        deps = reg.detect_cross_repo_imports(str(src), source_repo="fda-tools")
        assert any(d.target_repo == "fda-writer" for d in deps)

    def test_detects_string_path_reference(self, tmp_path):
        reg = self._make_reg_with_two_repos(tmp_path)
        src = _write_py(
            tmp_path / "config.py",
            """
            BASE = "~/fda-writer/templates"
            """,
        )
        deps = reg.detect_cross_repo_imports(str(src), source_repo="fda-tools")
        assert any(d.target_repo == "fda-writer" for d in deps)

    def test_skips_self_references(self, tmp_path):
        reg = self._make_reg_with_two_repos(tmp_path)
        src = _write_py(
            tmp_path / "self_ref.py",
            """
            from fda_tools.lib.config import Config
            """,
        )
        deps = reg.detect_cross_repo_imports(str(src), source_repo="fda-tools")
        # Should NOT report a dep from fda-tools → fda-tools
        assert not any(d.target_repo == "fda-tools" for d in deps)

    def test_no_deps_when_no_cross_imports(self, tmp_path):
        reg = self._make_reg_with_two_repos(tmp_path)
        src = _write_py(
            tmp_path / "clean.py",
            """
            import os
            import json
            """,
        )
        deps = reg.detect_cross_repo_imports(str(src), source_repo="fda-tools")
        assert deps == []

    def test_missing_file_returns_empty(self, tmp_path):
        reg = self._make_reg_with_two_repos(tmp_path)
        deps = reg.detect_cross_repo_imports(
            str(tmp_path / "does_not_exist.py"),
            source_repo="fda-tools",
        )
        assert deps == []

    def test_dependency_has_correct_fields(self, tmp_path):
        reg = self._make_reg_with_two_repos(tmp_path)
        src = _write_py(
            tmp_path / "caller.py",
            """
            import fda_writer
            """,
        )
        deps = reg.detect_cross_repo_imports(str(src), source_repo="fda-tools")
        dep = next((d for d in deps if d.target_repo == "fda-writer"), None)
        assert dep is not None
        assert dep.source_repo == "fda-tools"
        assert "caller.py" in dep.source_file
        assert dep.import_pattern  # non-empty string


# ---------------------------------------------------------------------------
# build_dependency_graph
# ---------------------------------------------------------------------------


class TestBuildDependencyGraph:
    """Tests for the dependency graph builder."""

    def test_graph_contains_cross_repo_edges(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("fda-tools", path=str(tmp_path / "fda-tools"), team="T", primary=True)
        reg.register("fda-writer", path=str(tmp_path / "fda-writer"), team="W")

        src1 = _write_py(tmp_path / "a.py", "import fda_writer\n")
        src2 = _write_py(tmp_path / "b.py", "import os\n")

        graph = reg.build_dependency_graph([str(src1), str(src2)], source_repo="fda-tools")
        assert "fda-writer" in graph.get("fda-tools", set())

    def test_graph_empty_when_no_cross_imports(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("fda-tools", path=str(tmp_path), team="T", primary=True)

        src = _write_py(tmp_path / "clean.py", "import os\n")
        graph = reg.build_dependency_graph([str(src)], source_repo="fda-tools")
        assert graph.get("fda-tools", set()) == set()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestRepoRegistryPersistence:
    """Tests for save/load round-trip and error handling."""

    def test_registered_repos_survive_reload(self, tmp_path):
        store = tmp_path / "reg.json"
        r1 = RepoRegistry(store_path=store)
        r1.register("fda-tools", path="~/t", team="T", primary=True)

        r2 = RepoRegistry(store_path=store)
        assert r2.get("fda-tools") is not None
        assert r2.get("fda-tools").primary is True

    def test_corrupt_file_uses_defaults(self, tmp_path):
        store = tmp_path / "reg.json"
        store.write_text("not json", encoding="utf-8")
        reg = RepoRegistry(store_path=store)
        # Should fall back to DEFAULT_REPOS
        assert reg.get(DEFAULT_REPOS[0]["name"]) is not None

    def test_new_store_seeded_with_defaults(self, tmp_path):
        store = tmp_path / "new_reg.json"
        assert not store.exists()
        reg = RepoRegistry(store_path=store)
        # Defaults should be seeded
        assert store.exists()
        for default in DEFAULT_REPOS:
            assert reg.get(default["name"]) is not None

    def test_atomic_write_no_tmp_leftover(self, tmp_path):
        store = tmp_path / "reg.json"
        reg = RepoRegistry(store_path=store)
        reg.register("r", path="~/r", team="T")
        assert not (store.with_suffix(".tmp")).exists()


# ---------------------------------------------------------------------------
# format_registry
# ---------------------------------------------------------------------------


class TestFormatRegistry:
    """Tests for the markdown registry table."""

    def test_empty_registry_returns_placeholder(self, tmp_path):
        reg = _make_registry(tmp_path)
        out = reg.format_registry()
        assert "No repos registered" in out

    def test_table_contains_registered_name(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("my-repo", path="~/m", team="My Team")
        out = reg.format_registry()
        assert "my-repo" in out

    def test_table_has_header_columns(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("r", path="~/r", team="T")
        out = reg.format_registry()
        assert "Name" in out
        assert "Team" in out
        assert "Primary" in out

    def test_primary_repo_marked(self, tmp_path):
        reg = _make_registry(tmp_path)
        reg.register("main", path="~/main", team="T", primary=True)
        out = reg.format_registry()
        assert "✓" in out
