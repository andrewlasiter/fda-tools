#!/usr/bin/env python3
"""
FDA Regulatory Expert Agent Registry (FDA-73) -- Framework for managing,
discovering, and coordinating the FDA regulatory expert agent team.

Provides:
  1. Agent registration and discovery
  2. Capability-based agent selection
  3. Agent team assembly for device reviews
  4. Skill validation and completeness checking
  5. Agent coordination patterns

The registry discovers agents from the skills/ directory structure:
    skills/
        fda-{specialty}-expert/
            SKILL.md      -- Agent skill definition (required)
            agent.yaml    -- Agent configuration (required)
            references/   -- Reference materials (optional)

Usage:
    from agent_registry import AgentRegistry

    registry = AgentRegistry()
    agents = registry.list_agents()
    agent = registry.get_agent("fda-software-ai-expert")
    team = registry.assemble_team(device_type="SaMD", device_class="II")
    validation = registry.validate_all_agents()

    # CLI:
    python3 agent_registry.py list
    python3 agent_registry.py info fda-clinical-expert
    python3 agent_registry.py team --device-type SaMD --class II
    python3 agent_registry.py validate
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

# Try to import yaml; fall back to basic parsing if unavailable
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ------------------------------------------------------------------
# Agent Registry Constants
# ------------------------------------------------------------------

# Skills directory relative to this script
SKILLS_DIR = Path(__file__).parent.parent / "skills"

# Required files for a valid agent
REQUIRED_FILES = ["SKILL.md"]
RECOMMENDED_FILES = ["agent.yaml"]

# Agent capability categories
CAPABILITY_CATEGORIES = {
    "regulatory_pathway": [
        "510(k)", "PMA", "De Novo", "HDE", "IDE",
        "Breakthrough Device", "Pre-Sub",
    ],
    "device_specialty": [
        "cardiovascular", "orthopedic", "neurological", "ophthalmic",
        "dental", "radiology", "IVD", "SaMD", "combination_product",
    ],
    "functional_area": [
        "quality_systems", "biocompatibility", "sterilization",
        "software_validation", "clinical_evidence", "postmarket",
        "regulatory_strategy", "risk_management", "human_factors",
        "cybersecurity", "international",
    ],
    "regulatory_framework": [
        "21 CFR 820", "21 CFR 812", "21 CFR 814", "21 CFR 803",
        "ISO 13485", "ISO 14971", "IEC 62304", "ISO 10993",
        "IEC 60601", "IEC 62366",
    ],
}

# Device type to recommended agents mapping
DEVICE_AGENT_MAP = {
    "SaMD": [
        "fda-software-ai-expert",
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "cardiovascular": [
        "fda-cardiovascular-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-sterilization-expert",
        "fda-quality-expert",
    ],
    "orthopedic": [
        "fda-orthopedic-expert",
        "fda-biocompatibility-expert",
        "fda-sterilization-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "IVD": [
        "fda-ivd-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
        "fda-regulatory-strategy-expert",
    ],
    "combination_product": [
        "fda-combination-product-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
        "fda-regulatory-strategy-expert",
    ],
    "neurological": [
        "fda-neurology-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-software-ai-expert",
        "fda-quality-expert",
    ],
    "ophthalmic": [
        "fda-ophthalmic-expert",
        "fda-biocompatibility-expert",
        "fda-clinical-expert",
        "fda-sterilization-expert",
    ],
    "radiology": [
        "fda-radiology-expert",
        "fda-software-ai-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "generic": [
        "fda-regulatory-strategy-expert",
        "fda-quality-expert",
        "fda-clinical-expert",
        "fda-postmarket-expert",
    ],
}

# Submission pathway to required agents
PATHWAY_AGENT_MAP = {
    "510k": [
        "fda-regulatory-strategy-expert",
        "fda-quality-expert",
    ],
    "PMA": [
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
        "fda-postmarket-expert",
    ],
    "De Novo": [
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
        "fda-quality-expert",
    ],
    "IDE": [
        "fda-clinical-expert",
        "fda-regulatory-strategy-expert",
    ],
    "HDE": [
        "fda-regulatory-strategy-expert",
        "fda-clinical-expert",
    ],
}


# ------------------------------------------------------------------
# YAML Frontmatter Parser (fallback when PyYAML not available)
# ------------------------------------------------------------------

def _parse_frontmatter(content: str) -> Dict:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}

    end_idx = content.index("---", 3) if "---" in content[3:] else -1
    if end_idx < 0:
        return {}

    yaml_text = content[3:end_idx + 3].strip()

    if HAS_YAML:
        try:
            return yaml.safe_load(yaml_text) or {}  # type: ignore
        except yaml.YAMLError:  # type: ignore
            pass

    # Fallback: basic key-value parsing
    result = {}
    for line in yaml_text.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _parse_yaml_file(path: Path) -> Dict:
    """Parse a YAML file."""
    try:
        content = path.read_text(encoding="utf-8")
        if HAS_YAML:
            return yaml.safe_load(content) or {}  # type: ignore  # type: ignore
        # Fallback: basic parsing
        result = {}
        for line in content.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith("#") and not line.startswith("-"):
                key, _, value = line.partition(":")
                result[key.strip()] = value.strip()
        return result
    except (OSError, ValueError):
        return {}


# ==================================================================
# Agent Registry
# ==================================================================

class AgentRegistry:
    """Registry for discovering, managing, and coordinating FDA
    regulatory expert agents.

    Scans the skills/ directory for agent definitions and provides
    capability-based selection and team assembly.
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        """Initialize the agent registry.

        Args:
            skills_dir: Path to skills directory. Defaults to
                       project skills/ directory.
        """
        self._skills_dir = skills_dir or SKILLS_DIR
        self._agents: Dict[str, Dict] = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Lazy-load agent definitions on first access."""
        if not self._loaded:
            self._scan_agents()
            self._loaded = True

    def _scan_agents(self):
        """Scan skills directory for agent definitions."""
        if not self._skills_dir.exists():
            return

        for agent_dir in sorted(self._skills_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            if agent_dir.name.startswith("."):
                continue

            skill_path = agent_dir / "SKILL.md"
            if not skill_path.exists():
                continue

            agent = self._load_agent(agent_dir)
            if agent:
                self._agents[agent["name"]] = agent

    def _load_agent(self, agent_dir: Path) -> Optional[Dict]:
        """Load a single agent definition from its directory.

        Args:
            agent_dir: Path to agent directory.

        Returns:
            Agent definition dict or None if invalid.
        """
        skill_path = agent_dir / "SKILL.md"
        yaml_path = agent_dir / "agent.yaml"

        try:
            skill_content = skill_path.read_text(encoding="utf-8")
        except OSError:
            return None

        # Parse frontmatter
        frontmatter = _parse_frontmatter(skill_content)
        name = frontmatter.get("name", agent_dir.name)
        description = frontmatter.get("description", "")

        # Parse agent.yaml if exists
        yaml_config = {}
        if yaml_path.exists():
            yaml_config = _parse_yaml_file(yaml_path)

        # Check for references directory
        refs_dir = agent_dir / "references"
        has_references = refs_dir.is_dir() and any(refs_dir.iterdir()) if refs_dir.exists() else False
        ref_count = len(list(refs_dir.iterdir())) if has_references else 0

        # Extract capabilities from description and skill content
        capabilities = self._extract_capabilities(description, skill_content)

        # Determine agent type
        agent_type = self._determine_agent_type(name)

        # Measure content size
        skill_lines = len(skill_content.split("\n"))
        skill_words = len(skill_content.split())

        return {
            "name": name,
            "directory": str(agent_dir),
            "description": description,
            "type": agent_type,
            "has_skill_md": True,
            "has_agent_yaml": yaml_path.exists(),
            "has_references": has_references,
            "reference_count": ref_count,
            "skill_lines": skill_lines,
            "skill_words": skill_words,
            "capabilities": capabilities,
            "yaml_config": yaml_config,
            "frontmatter": frontmatter,
        }

    def _extract_capabilities(self, description: str, content: str) -> List[str]:
        """Extract capability tags from description and content."""
        caps = set()
        combined = (description + " " + content[:2000]).lower()

        # Check all capability categories
        for category, keywords in CAPABILITY_CATEGORIES.items():
            for kw in keywords:
                if kw.lower() in combined:
                    caps.add(kw)

        return sorted(caps)

    def _determine_agent_type(self, name: str) -> str:
        """Determine agent type from naming convention."""
        if "expert" in name:
            return "expert"
        elif "support" in name:
            return "support"
        elif "integration" in name:
            return "integration"
        elif "knowledge" in name:
            return "knowledge"
        elif "smoke" in name or "test" in name:
            return "testing"
        else:
            return "skill"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_agents(self, agent_type: str = "") -> List[Dict]:
        """List all registered agents.

        Args:
            agent_type: Optional filter by type (expert, support, etc.).

        Returns:
            List of agent summary dicts.
        """
        self._ensure_loaded()
        agents = list(self._agents.values())
        if agent_type:
            agents = [a for a in agents if a["type"] == agent_type]
        return sorted(agents, key=lambda a: a["name"])

    def get_agent(self, name: str) -> Optional[Dict]:
        """Get a specific agent by name.

        Args:
            name: Agent name (e.g., 'fda-software-ai-expert').

        Returns:
            Agent definition dict or None.
        """
        self._ensure_loaded()
        return self._agents.get(name)

    def search_agents(self, query: str) -> List[Dict]:
        """Search agents by keyword in name or description.

        Args:
            query: Search query string.

        Returns:
            Matching agents sorted by relevance.
        """
        self._ensure_loaded()
        query_lower = query.lower()
        results = []
        for agent in self._agents.values():
            score = 0
            if query_lower in agent["name"].lower():
                score += 10
            if query_lower in agent["description"].lower():
                score += 5
            if any(query_lower in cap.lower() for cap in agent["capabilities"]):
                score += 3
            if score > 0:
                results.append((score, agent))

        results.sort(key=lambda x: x[0], reverse=True)
        return [agent for _, agent in results]

    def find_agents_by_capability(self, capability: str) -> List[Dict]:
        """Find agents with a specific capability.

        Args:
            capability: Capability keyword (e.g., 'ISO 10993', 'cybersecurity').

        Returns:
            Matching agents.
        """
        self._ensure_loaded()
        cap_lower = capability.lower()
        return [
            agent for agent in self._agents.values()
            if any(cap_lower in cap.lower() for cap in agent["capabilities"])
        ]

    def assemble_team(
        self,
        device_type: str = "generic",
        submission_pathway: str = "",
        device_class: str = "",
        additional_capabilities: Optional[List[str]] = None,
    ) -> Dict:
        """Assemble an expert team for a device review.

        Args:
            device_type: Device type (SaMD, cardiovascular, etc.).
            submission_pathway: Pathway (510k, PMA, De Novo, IDE, HDE).
            device_class: Device class (I, II, III).
            additional_capabilities: Extra capabilities needed.

        Returns:
            Team assembly with core, specialty, and support agents.
        """
        self._ensure_loaded()

        # Get recommended agents for device type
        device_agents = DEVICE_AGENT_MAP.get(device_type, DEVICE_AGENT_MAP["generic"])

        # Add pathway-specific agents
        pathway_agents = PATHWAY_AGENT_MAP.get(submission_pathway, [])

        # Combine and deduplicate
        all_agent_names: List[str] = []
        seen: Set[str] = set()
        for name in device_agents + pathway_agents:
            if name not in seen:
                all_agent_names.append(name)
                seen.add(name)

        # Add agents for additional capabilities
        if additional_capabilities:
            for cap in additional_capabilities:
                cap_agents = self.find_agents_by_capability(cap)
                for agent in cap_agents:
                    if agent["name"] not in seen:
                        all_agent_names.append(agent["name"])
                        seen.add(agent["name"])

        # Class III always needs clinical expert and postmarket
        if device_class == "III":
            for name in ["fda-clinical-expert", "fda-postmarket-expert"]:
                if name not in seen:
                    all_agent_names.append(name)
                    seen.add(name)

        # Resolve agent objects
        core_agents = []
        specialty_agents = []
        unavailable = []

        for name in all_agent_names:
            agent = self._agents.get(name)
            if agent:
                if agent["type"] == "expert":
                    if name in device_agents[:2]:
                        core_agents.append(agent)
                    else:
                        specialty_agents.append(agent)
                else:
                    specialty_agents.append(agent)
            else:
                unavailable.append(name)

        return {
            "device_type": device_type,
            "submission_pathway": submission_pathway,
            "device_class": device_class,
            "team_size": len(core_agents) + len(specialty_agents),
            "core_agents": [
                {"name": a["name"], "type": a["type"], "role": "core"}
                for a in core_agents
            ],
            "specialty_agents": [
                {"name": a["name"], "type": a["type"], "role": "specialty"}
                for a in specialty_agents
            ],
            "unavailable_agents": unavailable,
            "coordination_pattern": self._recommend_pattern(
                len(core_agents) + len(specialty_agents)
            ),
        }

    def _recommend_pattern(self, team_size: int) -> Dict:
        """Recommend coordination pattern based on team size."""
        if team_size <= 3:
            return {
                "pattern": "peer-to-peer",
                "description": "Small team, direct coordination between agents",
                "overhead": "low",
            }
        elif team_size <= 6:
            return {
                "pattern": "master-worker",
                "description": "Lead reviewer coordinates specialist agents",
                "overhead": "medium",
            }
        else:
            return {
                "pattern": "hierarchical",
                "description": "Lead reviewer with sub-team leads for each domain",
                "overhead": "medium-high",
            }

    def validate_all_agents(self) -> Dict:
        """Validate all registered agents for completeness.

        Returns:
            Validation report with pass/fail for each agent and overall score.
        """
        self._ensure_loaded()

        results = []
        total_score = 0
        max_score = 0

        for name, agent in sorted(self._agents.items()):
            validation = self._validate_agent(agent)
            results.append(validation)
            total_score += validation["score"]
            max_score += validation["max_score"]

        overall_score = round(total_score / max_score * 100) if max_score > 0 else 0

        return {
            "total_agents": len(results),
            "overall_score": overall_score,
            "agents": results,
            "summary": {
                "fully_complete": sum(1 for r in results if r["status"] == "COMPLETE"),
                "partial": sum(1 for r in results if r["status"] == "PARTIAL"),
                "minimal": sum(1 for r in results if r["status"] == "MINIMAL"),
            },
        }

    def _validate_agent(self, agent: Dict) -> Dict:
        """Validate a single agent definition."""
        issues = []
        score = 0
        max_score = 100

        # SKILL.md exists (required)
        if agent["has_skill_md"]:
            score += 20
        else:
            issues.append("CRITICAL: Missing SKILL.md")

        # agent.yaml exists (recommended)
        if agent["has_agent_yaml"]:
            score += 15
        else:
            issues.append("WARNING: Missing agent.yaml")

        # Description exists and is meaningful
        if agent["description"] and len(agent["description"]) > 50:
            score += 15
        elif agent["description"]:
            score += 8
            issues.append("MINOR: Description too short (<50 chars)")
        else:
            issues.append("WARNING: No description")

        # SKILL.md content depth
        if agent["skill_lines"] >= 200:
            score += 20
        elif agent["skill_lines"] >= 100:
            score += 12
            issues.append("MINOR: SKILL.md could be more comprehensive")
        elif agent["skill_lines"] >= 50:
            score += 6
            issues.append("WARNING: SKILL.md is minimal")
        else:
            issues.append("WARNING: SKILL.md is very short")

        # References exist
        if agent["has_references"]:
            score += 10
        else:
            # Not all agents need references
            score += 5

        # Capabilities extracted
        if len(agent["capabilities"]) >= 5:
            score += 10
        elif len(agent["capabilities"]) >= 2:
            score += 5
        else:
            issues.append("MINOR: Few capabilities detected")

        # Frontmatter complete
        fm = agent["frontmatter"]
        if "name" in fm and "description" in fm:
            score += 10
        elif "name" in fm:
            score += 5
            issues.append("MINOR: Frontmatter missing description")
        else:
            issues.append("WARNING: Frontmatter incomplete")

        status = "COMPLETE" if score >= 80 else "PARTIAL" if score >= 50 else "MINIMAL"

        return {
            "name": agent["name"],
            "type": agent["type"],
            "score": score,
            "max_score": max_score,
            "status": status,
            "issues": issues,
        }

    def get_statistics(self) -> Dict:
        """Get registry statistics.

        Returns:
            Statistics about registered agents.
        """
        self._ensure_loaded()

        types = {}
        total_lines = 0
        total_refs = 0
        with_yaml = 0
        with_refs = 0

        for agent in self._agents.values():
            t = agent["type"]
            types[t] = types.get(t, 0) + 1
            total_lines += agent["skill_lines"]
            total_refs += agent["reference_count"]
            if agent["has_agent_yaml"]:
                with_yaml += 1
            if agent["has_references"]:
                with_refs += 1

        return {
            "total_agents": len(self._agents),
            "agent_types": types,
            "agents_with_yaml": with_yaml,
            "agents_with_references": with_refs,
            "total_skill_lines": total_lines,
            "total_reference_files": total_refs,
            "avg_skill_lines": round(total_lines / max(len(self._agents), 1)),
        }


# ==================================================================
# Agent Team Coordinator
# ==================================================================

class AgentTeamCoordinator:
    """Coordinates multi-agent review workflows.

    Provides patterns for assembling and coordinating expert agent teams
    for device reviews, including task assignment, dependency management,
    and result aggregation.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """Initialize with an agent registry.

        Args:
            registry: Agent registry instance.
        """
        self.registry = registry or AgentRegistry()

    def create_review_plan(
        self,
        device_name: str,
        device_type: str = "generic",
        submission_pathway: str = "510k",
        device_class: str = "II",
    ) -> Dict:
        """Create a multi-agent review plan.

        Args:
            device_name: Device name.
            device_type: Device type category.
            submission_pathway: Regulatory pathway.
            device_class: FDA device class.

        Returns:
            Review plan with phases, tasks, and agent assignments.
        """
        # Assemble team
        team = self.registry.assemble_team(
            device_type=device_type,
            submission_pathway=submission_pathway,
            device_class=device_class,
        )

        # Define review phases
        phases = [
            {
                "phase": 1,
                "name": "Initial Assessment",
                "description": "Device classification, pathway verification, initial risk assessment",
                "assigned_agents": [
                    a["name"] for a in team["core_agents"][:2]
                ],
                "dependencies": [],
                "estimated_hours": 4,
            },
            {
                "phase": 2,
                "name": "Specialist Review",
                "description": "Domain-specific technical review (biocompatibility, software, clinical, etc.)",
                "assigned_agents": [
                    a["name"] for a in team["specialty_agents"]
                ],
                "dependencies": [1],
                "estimated_hours": 8,
                "parallel": True,
            },
            {
                "phase": 3,
                "name": "Quality & Compliance",
                "description": "QMS compliance, design control, and documentation review",
                "assigned_agents": [
                    a["name"] for a in team["core_agents"]
                    if "quality" in a["name"]
                ] or [team["core_agents"][0]["name"]] if team["core_agents"] else [],
                "dependencies": [1],
                "estimated_hours": 4,
            },
            {
                "phase": 4,
                "name": "Integration & Deficiency Report",
                "description": "Aggregate findings, resolve conflicts, generate unified report",
                "assigned_agents": [
                    a["name"] for a in team["core_agents"][:1]
                ],
                "dependencies": [2, 3],
                "estimated_hours": 4,
            },
        ]

        total_hours = sum(p["estimated_hours"] for p in phases)

        return {
            "device_name": device_name,
            "device_type": device_type,
            "submission_pathway": submission_pathway,
            "device_class": device_class,
            "team": team,
            "phases": phases,
            "total_estimated_hours": total_hours,
            "coordination_pattern": team["coordination_pattern"],
        }

    def get_agent_task_matrix(self, review_plan: Dict) -> List[Dict]:
        """Generate a task assignment matrix from a review plan.

        Args:
            review_plan: Review plan from create_review_plan().

        Returns:
            List of task assignments.
        """
        tasks = []
        for phase in review_plan.get("phases", []):
            for agent_name in phase.get("assigned_agents", []):
                tasks.append({
                    "phase": phase["phase"],
                    "phase_name": phase["name"],
                    "agent": agent_name,
                    "description": phase["description"],
                    "dependencies": phase.get("dependencies", []),
                    "parallel": phase.get("parallel", False),
                    "estimated_hours": (
                        phase["estimated_hours"] / max(len(phase["assigned_agents"]), 1)
                    ),
                })
        return tasks


# ==================================================================
# CLI Entry Point
# ==================================================================

def main():
    parser = argparse.ArgumentParser(
        description="FDA Regulatory Expert Agent Registry (FDA-73)"
    )
    subparsers = parser.add_subparsers(dest="command")

    # list command
    list_p = subparsers.add_parser("list", help="List all agents")
    list_p.add_argument("--type", default="", help="Filter by type")
    list_p.add_argument("--json", action="store_true")

    # info command
    info_p = subparsers.add_parser("info", help="Show agent details")
    info_p.add_argument("name", help="Agent name")
    info_p.add_argument("--json", action="store_true")

    # team command
    team_p = subparsers.add_parser("team", help="Assemble review team")
    team_p.add_argument("--device-type", default="generic", help="Device type")
    team_p.add_argument("--pathway", default="510k", help="Submission pathway")
    team_p.add_argument("--class", dest="device_class", default="II", help="Device class")
    team_p.add_argument("--json", action="store_true")

    # validate command
    val_p = subparsers.add_parser("validate", help="Validate all agents")
    val_p.add_argument("--json", action="store_true")

    # stats command
    stats_p = subparsers.add_parser("stats", help="Registry statistics")
    stats_p.add_argument("--json", action="store_true")

    # search command
    search_p = subparsers.add_parser("search", help="Search agents")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--json", action="store_true")

    args = parser.parse_args()
    registry = AgentRegistry()

    if args.command == "list":
        agents = registry.list_agents(agent_type=args.type)
        if args.json:
            print(json.dumps([{
                "name": a["name"], "type": a["type"],
                "description": a["description"][:100],
            } for a in agents], indent=2))
        else:
            print(f"Registered Agents: {len(agents)}")
            for a in agents:
                yaml_mark = "Y" if a["has_agent_yaml"] else "N"
                refs_mark = "Y" if a["has_references"] else "N"
                print(f"  [{a['type']:10s}] {a['name']:40s} yaml:{yaml_mark} refs:{refs_mark} lines:{a['skill_lines']}")

    elif args.command == "info":
        agent = registry.get_agent(args.name)
        if agent:
            if args.json:
                # Remove non-serializable content
                safe = {k: v for k, v in agent.items() if k != "yaml_config" or isinstance(v, (str, int, float, bool, list, dict, type(None)))}
                print(json.dumps(safe, indent=2, default=str))
            else:
                print(f"Agent: {agent['name']}")
                print(f"Type: {agent['type']}")
                print(f"Description: {agent['description'][:200]}")
                print(f"SKILL.md: {agent['skill_lines']} lines, {agent['skill_words']} words")
                print(f"agent.yaml: {'Yes' if agent['has_agent_yaml'] else 'No'}")
                print(f"References: {agent['reference_count']} files")
                print(f"Capabilities: {', '.join(agent['capabilities'][:10])}")
        else:
            print(f"Agent not found: {args.name}")

    elif args.command == "team":
        team = registry.assemble_team(
            device_type=args.device_type,
            submission_pathway=args.pathway,
            device_class=args.device_class,
        )
        if args.json:
            print(json.dumps(team, indent=2))
        else:
            print(f"Team for {args.device_type} ({args.pathway}, Class {args.device_class}):")
            print(f"Team size: {team['team_size']}")
            print(f"Core agents:")
            for a in team["core_agents"]:
                print(f"  - {a['name']}")
            print(f"Specialty agents:")
            for a in team["specialty_agents"]:
                print(f"  - {a['name']}")
            if team["unavailable_agents"]:
                print(f"Unavailable:")
                for name in team["unavailable_agents"]:
                    print(f"  - {name}")
            pattern = team["coordination_pattern"]
            print(f"Coordination: {pattern['pattern']} ({pattern['description']})")

    elif args.command == "validate":
        report = registry.validate_all_agents()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Agent Validation Report")
            print(f"Overall Score: {report['overall_score']}%")
            print(f"Total Agents: {report['total_agents']}")
            summary = report["summary"]
            print(f"  Complete: {summary['fully_complete']}")
            print(f"  Partial: {summary['partial']}")
            print(f"  Minimal: {summary['minimal']}")
            print()
            for agent in report["agents"]:
                status_char = "+" if agent["status"] == "COMPLETE" else "~" if agent["status"] == "PARTIAL" else "-"
                print(f"  [{status_char}] {agent['name']:40s} {agent['score']}/{agent['max_score']} {agent['status']}")
                for issue in agent["issues"]:
                    print(f"      {issue}")

    elif args.command == "stats":
        stats = registry.get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"Registry Statistics:")
            print(f"  Total Agents: {stats['total_agents']}")
            print(f"  With YAML: {stats['agents_with_yaml']}")
            print(f"  With References: {stats['agents_with_references']}")
            print(f"  Total SKILL.md Lines: {stats['total_skill_lines']}")
            print(f"  Avg Lines per Agent: {stats['avg_skill_lines']}")
            print(f"  Agent Types:")
            for t, count in stats["agent_types"].items():
                print(f"    {t}: {count}")

    elif args.command == "search":
        results = registry.search_agents(args.query)
        if args.json:
            print(json.dumps([{
                "name": a["name"], "type": a["type"],
            } for a in results], indent=2))
        else:
            print(f"Search results for '{args.query}': {len(results)} found")
            for a in results:
                print(f"  {a['name']} ({a['type']})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
