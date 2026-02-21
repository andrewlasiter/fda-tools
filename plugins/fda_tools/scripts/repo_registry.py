#!/usr/bin/env python3
"""
RepoRegistry — Multi-repository configuration store for the Universal Orchestrator.

Implements FDA-215 (ORCH-011) — Phase 11 of the Universal Multi-Agent Orchestrator.

Provides:

1. ``RepoConfig`` — configuration record for a single repository (name, path,
   Linear team, primary flag).
2. ``RepoRegistry`` — JSON-backed registry of known repos with CRUD operations,
   cross-repo import detection, and dependency graph building.
3. ``CrossRepoImportDetector`` — scans Python source for imports/calls that
   reference files or packages owned by other registered repos, enabling
   cross-repo scope expansion for reviews.

Storage format (``~/.fda_tools/repo_registry.json``):

.. code-block:: json

   {
     "repos": [
       {
         "name": "fda-tools",
         "path": "~/projects/fda-tools",
         "team": "FDA tools",
         "primary": true
       },
       {
         "name": "fda-submission-writer",
         "path": "~/projects/fda-submission-writer",
         "team": "FDA Submission",
         "primary": false
       }
     ]
   }

Usage::

    from fda_tools.scripts.repo_registry import RepoRegistry

    registry = RepoRegistry()
    registry.register("fda-submission-writer",
                       path="~/projects/fda-submission-writer",
                       team="FDA Submission")

    # Detect cross-repo dependencies in a file
    deps = registry.detect_cross_repo_imports("api/auth.py")

    # Expand task scope to include dependent repos
    repos = registry.resolve_repos_for_task(
        task="Security audit",
        files=["api/auth.py"],
        requested_repos=["fda-tools", "fda-submission-writer"],
    )
"""

import json
import logging
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known FDA ecosystem repos with their Linear team names.
# Pre-registered so users get a usable registry out-of-the-box.
# ---------------------------------------------------------------------------

DEFAULT_REPOS: List[Dict] = [
    {
        "name": "fda-tools",
        "path": "~/fda-tools",
        "team": "FDA tools",
        "primary": True,
    },
    {
        "name": "fda-510k-data",
        "path": "~/fda-510k-data",
        "team": "FDA tools",
        "primary": False,
    },
    {
        "name": "fda-submission-writer",
        "path": "~/fda-submission-writer",
        "team": "FDA Submission",
        "primary": False,
    },
    {
        "name": "openclaw-skill",
        "path": "~/openclaw-skill",
        "team": "FDA tools",
        "primary": False,
    },
]


# ---------------------------------------------------------------------------
# RepoConfig
# ---------------------------------------------------------------------------


@dataclass
class RepoConfig:
    """Configuration record for a single repository.

    Attributes:
        name: Short repository name (must be unique in the registry).
        path: Filesystem path (``~`` is expanded at query time).
        team: Linear team name where issues for this repo are filed.
        primary: When True, this is the main repo; orchestrator defaults to
            it when no ``--repos`` flag is given.
    """

    name: str
    path: str
    team: str
    primary: bool = False

    @property
    def resolved_path(self) -> Path:
        """Return the fully-resolved ``Path`` (expands ``~``)."""
        return Path(self.path).expanduser().resolve()

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for JSON storage)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RepoConfig":
        """Deserialise from a plain dict (unknown keys ignored)."""
        known = {"name", "path", "team", "primary"}
        return cls(**{k: v for k, v in data.items() if k in known})


# ---------------------------------------------------------------------------
# CrossRepoDependency
# ---------------------------------------------------------------------------


@dataclass
class CrossRepoDependency:
    """A detected dependency from one repo to another.

    Attributes:
        source_repo: Repository that contains the importing file.
        source_file: Path of the file containing the import.
        target_repo: Repository that owns the imported symbol/file.
        import_pattern: The raw import line or API call that was matched.
    """

    source_repo: str
    source_file: str
    target_repo: str
    import_pattern: str

    def __str__(self) -> str:
        """Return a one-line description."""
        return (
            f"{self.source_repo}/{self.source_file}"
            f" → {self.target_repo} (via '{self.import_pattern}')"
        )


# ---------------------------------------------------------------------------
# CrossRepoImportDetector
# ---------------------------------------------------------------------------


class CrossRepoImportDetector:
    """Scan Python source files for cross-repo imports and API references.

    Heuristic approach: looks for ``import`` / ``from … import`` statements
    that reference package names matching known repo names (with hyphens
    replaced by underscores) or string literals that look like paths inside
    registered repos.

    Args:
        registry: The ``RepoRegistry`` to resolve repo names from.
    """

    def __init__(self, registry: "RepoRegistry") -> None:
        """Initialise the detector with a repo registry."""
        self._registry = registry
        # Pre-compile patterns for each registered repo.
        self._patterns: Dict[str, re.Pattern] = {
            repo.name: self._build_pattern(repo)
            for repo in registry.list_repos()
        }

    @staticmethod
    def _build_pattern(repo: RepoConfig) -> re.Pattern:
        """Build a regex matching import references to *repo*."""
        pkg_name = repo.name.replace("-", "_")
        # Matches: import fda_tools, from fda_tools import, from fda_tools.sub import,
        # "fda-tools/", 'fda_tools'
        return re.compile(
            rf"(?:import\s+{re.escape(pkg_name)}"
            rf"|from\s+{re.escape(pkg_name)}(?:\s|\.)"
            rf"|['\"](?:[^'\"]*?/)?{re.escape(repo.name)}(?:/[^'\"]*)?['\"])",
            re.IGNORECASE,
        )

    def detect(
        self,
        file_path: str,
        source_repo: str,
    ) -> List[CrossRepoDependency]:
        """Return cross-repo dependencies found in *file_path*.

        Reads the file from disk, scans each line, and returns a dependency
        for each repo (other than *source_repo*) that is referenced.

        Args:
            file_path: Path to a Python source file.
            source_repo: Name of the repo that owns *file_path*.

        Returns:
            List of ``CrossRepoDependency`` instances (may be empty).
        """
        path = Path(file_path).expanduser()
        if not path.exists():
            logger.debug("detect: file not found %s", path)
            return []

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("detect: could not read %s: %s", path, exc)
            return []

        deps: List[CrossRepoDependency] = []
        for repo_name, pattern in self._patterns.items():
            if repo_name == source_repo:
                continue
            for line in text.splitlines():
                m = pattern.search(line)
                if m:
                    deps.append(CrossRepoDependency(
                        source_repo=source_repo,
                        source_file=str(file_path),
                        target_repo=repo_name,
                        import_pattern=m.group(0).strip(),
                    ))
                    break  # one match per target repo per file is enough
        return deps


# ---------------------------------------------------------------------------
# RepoRegistry
# ---------------------------------------------------------------------------


class RepoRegistry:
    """Multi-repository configuration store.

    Loads repo definitions from ``~/.fda_tools/repo_registry.json`` (or a
    custom path) and provides helpers used by the orchestrator to:

    - resolve repo configs from user-supplied names
    - detect cross-repo imports in source files
    - build a dependency graph for scope expansion

    The store is populated with ``DEFAULT_REPOS`` on first use if the file
    does not exist.

    Args:
        store_path: Path to the JSON registry file.  Defaults to
            ``~/.fda_tools/repo_registry.json``.
    """

    def __init__(self, store_path: Optional[Path] = None) -> None:
        """Initialise the registry and load/create the store."""
        self.store_path = store_path or (
            Path.home() / ".fda_tools" / "repo_registry.json"
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._repos: Dict[str, RepoConfig] = self._load()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        path: str,
        team: str,
        primary: bool = False,
    ) -> RepoConfig:
        """Add or replace a repo in the registry.

        Args:
            name: Unique short name (e.g. ``"fda-submission-writer"``).
            path: Filesystem path (``~`` supported).
            team: Linear team name for issues filed against this repo.
            primary: Mark as primary repo (only one primary allowed; any
                existing primary is not changed — caller must unset it first).

        Returns:
            The newly created or replaced ``RepoConfig``.
        """
        cfg = RepoConfig(name=name, path=path, team=team, primary=primary)
        self._repos[name] = cfg
        self._save()
        logger.debug("Registered repo: %s → %s (team: %s)", name, path, team)
        return cfg

    def unregister(self, name: str) -> bool:
        """Remove *name* from the registry.

        Returns:
            True if the repo was present and removed; False if not found.
        """
        if name in self._repos:
            del self._repos[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[RepoConfig]:
        """Return the ``RepoConfig`` for *name*, or None if not registered."""
        return self._repos.get(name)

    def list_repos(self) -> List[RepoConfig]:
        """Return all registered repos (sorted by name)."""
        return sorted(self._repos.values(), key=lambda r: (not r.primary, r.name))

    def primary(self) -> Optional[RepoConfig]:
        """Return the primary repo, or None if none is marked primary."""
        for repo in self._repos.values():
            if repo.primary:
                return repo
        return None

    # ------------------------------------------------------------------
    # Multi-repo scope resolution
    # ------------------------------------------------------------------

    def resolve_repos(self, names: List[str]) -> List[RepoConfig]:
        """Return ``RepoConfig`` objects for each name in *names*.

        Unknown names are logged as warnings and omitted.

        Args:
            names: List of repo short-names to resolve.

        Returns:
            Resolved ``RepoConfig`` list (same order as *names*, minus
            any unknown entries).
        """
        result: List[RepoConfig] = []
        for name in names:
            cfg = self._repos.get(name)
            if cfg:
                result.append(cfg)
            else:
                logger.warning("RepoRegistry: unknown repo '%s' — skipped.", name)
        return result

    def detect_cross_repo_imports(
        self,
        file_path: str,
        source_repo: Optional[str] = None,
    ) -> List[CrossRepoDependency]:
        """Detect cross-repo dependencies in *file_path*.

        If *source_repo* is omitted the primary repo is used.

        Args:
            file_path: Path to the source file to scan.
            source_repo: Owning repo name.

        Returns:
            List of ``CrossRepoDependency`` instances.
        """
        if source_repo is None:
            primary = self.primary()
            source_repo = primary.name if primary else ""

        detector = CrossRepoImportDetector(self)
        return detector.detect(file_path, source_repo)

    def build_dependency_graph(
        self,
        files: List[str],
        source_repo: str,
    ) -> Dict[str, Set[str]]:
        """Return a ``{source_repo: {target_repos}}`` dependency mapping.

        Scans all *files* for cross-repo imports and returns the aggregate
        set of repos that each file's repo depends on.

        Args:
            files: Source files to scan.
            source_repo: Owning repo of all *files*.

        Returns:
            Dict mapping repo names to the set of repos they depend on.
        """
        graph: Dict[str, Set[str]] = {source_repo: set()}
        detector = CrossRepoImportDetector(self)
        for f in files:
            for dep in detector.detect(f, source_repo):
                graph.setdefault(dep.source_repo, set()).add(dep.target_repo)
        return graph

    def format_registry(self) -> str:
        """Return a markdown table of registered repos."""
        repos = self.list_repos()
        if not repos:
            return "*No repos registered.*\n"
        lines = [
            "## Registered Repositories\n",
            "| Name | Path | Team | Primary |",
            "|------|------|------|---------|",
        ]
        for r in repos:
            primary_flag = "✓" if r.primary else ""
            lines.append(f"| `{r.name}` | `{r.path}` | {r.team} | {primary_flag} |")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, RepoConfig]:
        """Load repos from disk; seed with defaults on first use."""
        if not self.store_path.exists():
            logger.debug("RepoRegistry: seeding defaults at %s", self.store_path)
            defaults = {r["name"]: RepoConfig.from_dict(r) for r in DEFAULT_REPOS}
            self._repos = defaults
            self._save()
            return defaults

        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            repos_list: List[dict] = data.get("repos", [])
            return {r["name"]: RepoConfig.from_dict(r) for r in repos_list if "name" in r}
        except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
            logger.warning(
                "RepoRegistry: could not load %s (%s); using defaults.", self.store_path, exc
            )
            return {r["name"]: RepoConfig.from_dict(r) for r in DEFAULT_REPOS}

    def _save(self) -> None:
        """Atomically write registry to disk."""
        payload = {"repos": [r.to_dict() for r in self._repos.values()]}
        tmp = self.store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.store_path)
