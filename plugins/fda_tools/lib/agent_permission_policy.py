"""
FDA-264  [ORCH-011] Agent Permission Policy Engine
====================================================
Pre-flight guardrails that define what each agent type is permitted to do
before the ExecutionCoordinator spawns it.

Design
------
Every agent in the MDRP orchestrator has a named *policy* stored in
``AGENT_POLICY_REGISTRY``.  Before an agent executes an action the caller
must invoke :func:`check_permission` (soft check) or
:func:`enforce_permission` (hard check — raises on denial).

Scopes (smallest-to-largest privilege)
    read      — may read records and data
    suggest   — may propose changes without applying them
    write     — may create or modify records
    sign      — may attach an electronic signature (§11.50)
    approve   — may set a HITL gate to APPROVED
    delete    — may permanently remove records
    deploy    — may trigger production deployments

Usage
-----
    from fda_tools.lib.agent_permission_policy import check_permission, enforce_permission

    # Soft check
    if check_permission("voltagent-lang:python-pro", "write"):
        agent.run(task)

    # Hard check (raises AgentPermissionError on denial)
    enforce_permission("fda-510k-data-analyst", "approve")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Optional

logger = logging.getLogger(__name__)


# ── Scope enum ────────────────────────────────────────────────────────────────

class AgentScope(Enum):
    """Ordered privilege scopes for MDRP agents."""
    READ    = "read"
    SUGGEST = "suggest"
    WRITE   = "write"
    SIGN    = "sign"
    APPROVE = "approve"
    DELETE  = "delete"
    DEPLOY  = "deploy"


# ── Policy dataclass ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPermissionPolicy:
    """
    Immutable permission policy for a single agent.

    Attributes:
        agent_id:           Canonical agent identifier (e.g. "voltagent-lang:python-pro")
        permitted_scopes:   Actions this agent is allowed to perform.
        prohibited_actions: Explicit deny-list (takes precedence over permitted_scopes).
        escalation_trigger: Human-readable description of when this agent must hand off.
    """
    agent_id:           str
    permitted_scopes:   FrozenSet[str]
    prohibited_actions: FrozenSet[str]
    escalation_trigger: str

    def allows(self, action: str) -> bool:
        """Return True iff *action* is permitted and not prohibited."""
        if action in self.prohibited_actions:
            return False
        return action in self.permitted_scopes


# ── Exception ─────────────────────────────────────────────────────────────────

class AgentPermissionError(Exception):
    """Raised by :func:`enforce_permission` when an agent is denied an action."""

    def __init__(self, agent_id: str, action: str, policy: AgentPermissionPolicy) -> None:
        self.agent_id = agent_id
        self.action   = action
        self.policy   = policy
        super().__init__(
            f"Agent '{agent_id}' is not permitted to perform action '{action}'. "
            f"Escalation: {policy.escalation_trigger}"
        )


# ── Public API ────────────────────────────────────────────────────────────────

def check_permission(
    agent_id: str,
    action: str,
    registry: Optional[Dict[str, AgentPermissionPolicy]] = None,
) -> bool:
    """
    Soft permission check — returns False and logs a warning on denial.

    Args:
        agent_id: Canonical agent identifier.
        action:   Scope string to check (e.g. "write", "approve").
        registry: Optional custom registry; defaults to AGENT_POLICY_REGISTRY.

    Returns:
        True if the action is permitted, False otherwise.
    """
    reg = registry if registry is not None else AGENT_POLICY_REGISTRY
    policy = reg.get(agent_id)
    if policy is None:
        logger.warning(
            "No permission policy for agent '%s'; denying action '%s'", agent_id, action
        )
        return False
    if not policy.allows(action):
        logger.warning(
            "Agent '%s' denied action '%s' (permitted=%s, prohibited=%s). %s",
            agent_id, action, policy.permitted_scopes, policy.prohibited_actions,
            policy.escalation_trigger,
        )
        return False
    return True


def enforce_permission(
    agent_id: str,
    action: str,
    registry: Optional[Dict[str, AgentPermissionPolicy]] = None,
) -> None:
    """
    Hard permission check — raises :exc:`AgentPermissionError` on denial.

    Args:
        agent_id: Canonical agent identifier.
        action:   Scope string to check.
        registry: Optional custom registry; defaults to AGENT_POLICY_REGISTRY.

    Raises:
        AgentPermissionError: If the agent is not permitted to perform *action*.
    """
    reg = registry if registry is not None else AGENT_POLICY_REGISTRY
    policy = reg.get(agent_id)
    if policy is None:
        # Create a synthetic deny-all policy for unknown agents
        policy = AgentPermissionPolicy(
            agent_id=agent_id,
            permitted_scopes=frozenset(),
            prohibited_actions=frozenset(),
            escalation_trigger="No policy registered for this agent — register it in AGENT_POLICY_REGISTRY",
        )
    if not policy.allows(action):
        raise AgentPermissionError(agent_id, action, policy)


# ── Registry helpers ──────────────────────────────────────────────────────────

_READ_ONLY   = frozenset({"read", "suggest"})
_STANDARD    = frozenset({"read", "suggest", "write"})
_SENIOR      = frozenset({"read", "suggest", "write", "sign"})
_LEAD        = frozenset({"read", "suggest", "write", "sign", "approve"})

_NO_DELETE         = frozenset({"delete"})
_NO_DEPLOY         = frozenset({"deploy"})
_NO_DELETE_DEPLOY  = frozenset({"delete", "deploy"})

_ESC_RA_LEAD = "Escalate to RA Lead for approval-level actions"
_ESC_ADMIN   = "Escalate to Admin for delete/deploy operations"


def _p(
    agent_id: str,
    scopes: FrozenSet[str],
    prohibited: FrozenSet[str] = frozenset(),
    escalation: str = _ESC_RA_LEAD,
) -> AgentPermissionPolicy:
    return AgentPermissionPolicy(
        agent_id=agent_id,
        permitted_scopes=scopes,
        prohibited_actions=prohibited,
        escalation_trigger=escalation,
    )


# ── Agent Policy Registry ─────────────────────────────────────────────────────

AGENT_POLICY_REGISTRY: Dict[str, AgentPermissionPolicy] = {

    # ── FDA Regulatory ────────────────────────────────────────────────────────
    "fda-quality-expert":              _p("fda-quality-expert",              _STANDARD, _NO_DELETE_DEPLOY),
    "fda-software-ai-expert":          _p("fda-software-ai-expert",          _STANDARD, _NO_DELETE_DEPLOY),
    "fda-clinical-expert":             _p("fda-clinical-expert",             _STANDARD, _NO_DELETE_DEPLOY),
    "fda-510k-data-analyst":           _p("fda-510k-data-analyst",           _READ_ONLY, _NO_DELETE_DEPLOY,
                                          "Escalate to RA Lead for write actions"),
    "fda-regulatory-expert":           _p("fda-regulatory-expert",           _STANDARD, _NO_DELETE_DEPLOY),
    "fda-biocompat-expert":            _p("fda-biocompat-expert",             _STANDARD, _NO_DELETE_DEPLOY),
    "fda-sterility-expert":            _p("fda-sterility-expert",             _STANDARD, _NO_DELETE_DEPLOY),
    "fda-human-factors-expert":        _p("fda-human-factors-expert",        _STANDARD, _NO_DELETE_DEPLOY),
    "fda-cybersecurity-expert":        _p("fda-cybersecurity-expert",        _STANDARD, _NO_DELETE_DEPLOY),

    # ── QA / Security ─────────────────────────────────────────────────────────
    "voltagent-qa-sec:security-auditor":      _p("voltagent-qa-sec:security-auditor",      _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:code-reviewer":         _p("voltagent-qa-sec:code-reviewer",         _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:penetration-tester":    _p("voltagent-qa-sec:penetration-tester",    _READ_ONLY, _NO_DELETE_DEPLOY,
                                                  "Escalate: pen test findings require RA Lead sign-off"),
    "voltagent-qa-sec:qa-expert":             _p("voltagent-qa-sec:qa-expert",             _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:compliance-auditor":    _p("voltagent-qa-sec:compliance-auditor",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:architect-reviewer":    _p("voltagent-qa-sec:architect-reviewer",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:test-automator":        _p("voltagent-qa-sec:test-automator",        _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:debugger":              _p("voltagent-qa-sec:debugger",              _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:performance-engineer":  _p("voltagent-qa-sec:performance-engineer",  _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:chaos-engineer":        _p("voltagent-qa-sec:chaos-engineer",        _STANDARD, _NO_DELETE_DEPLOY,
                                                  "Escalate: chaos experiments require Admin approval in production"),
    "voltagent-qa-sec:error-detective":       _p("voltagent-qa-sec:error-detective",       _READ_ONLY, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:silent-failure-hunter": _p("voltagent-qa-sec:silent-failure-hunter", _READ_ONLY, _NO_DELETE_DEPLOY),
    "voltagent-qa-sec:ad-security-reviewer":  _p("voltagent-qa-sec:ad-security-reviewer",  _READ_ONLY, _NO_DELETE_DEPLOY),

    # ── Languages ─────────────────────────────────────────────────────────────
    "voltagent-lang:python-pro":        _p("voltagent-lang:python-pro",        _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:typescript-pro":    _p("voltagent-lang:typescript-pro",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:javascript-pro":    _p("voltagent-lang:javascript-pro",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:rust-engineer":     _p("voltagent-lang:rust-engineer",     _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:golang-pro":        _p("voltagent-lang:golang-pro",        _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:java-architect":    _p("voltagent-lang:java-architect",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:sql-pro":           _p("voltagent-lang:sql-pro",           _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:swift-expert":      _p("voltagent-lang:swift-expert",      _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:kotlin-specialist": _p("voltagent-lang:kotlin-specialist", _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:nextjs-developer":  _p("voltagent-lang:nextjs-developer",  _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:react-specialist":  _p("voltagent-lang:react-specialist",  _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-lang:vue-expert":        _p("voltagent-lang:vue-expert",        _STANDARD, _NO_DELETE_DEPLOY),

    # ── Infrastructure ────────────────────────────────────────────────────────
    "voltagent-infra:devops-engineer":          _p("voltagent-infra:devops-engineer",          _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:kubernetes-specialist":    _p("voltagent-infra:kubernetes-specialist",    _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:cloud-architect":          _p("voltagent-infra:cloud-architect",          _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:security-engineer":        _p("voltagent-infra:security-engineer",        _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:sre-engineer":             _p("voltagent-infra:sre-engineer",             _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:terraform-engineer":       _p("voltagent-infra:terraform-engineer",       _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:deployment-engineer":      _p("voltagent-infra:deployment-engineer",      _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:database-administrator":   _p("voltagent-infra:database-administrator",   _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:platform-engineer":        _p("voltagent-infra:platform-engineer",        _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:incident-responder":       _p("voltagent-infra:incident-responder",       _SENIOR, _NO_DELETE, _ESC_ADMIN),
    "voltagent-infra:devops-incident-responder":_p("voltagent-infra:devops-incident-responder",_SENIOR, _NO_DELETE, _ESC_ADMIN),

    # ── Data & AI ─────────────────────────────────────────────────────────────
    "voltagent-data-ai:ai-engineer":      _p("voltagent-data-ai:ai-engineer",      _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:data-scientist":   _p("voltagent-data-ai:data-scientist",   _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:ml-engineer":      _p("voltagent-data-ai:ml-engineer",      _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:llm-architect":    _p("voltagent-data-ai:llm-architect",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:data-analyst":     _p("voltagent-data-ai:data-analyst",     _READ_ONLY, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:data-engineer":    _p("voltagent-data-ai:data-engineer",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:mlops-engineer":   _p("voltagent-data-ai:mlops-engineer",   _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:postgres-pro":     _p("voltagent-data-ai:postgres-pro",     _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:prompt-engineer":  _p("voltagent-data-ai:prompt-engineer",  _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-data-ai:nlp-engineer":     _p("voltagent-data-ai:nlp-engineer",     _STANDARD, _NO_DELETE_DEPLOY),

    # ── Core Development ──────────────────────────────────────────────────────
    "voltagent-core-dev:fullstack-developer": _p("voltagent-core-dev:fullstack-developer", _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-core-dev:frontend-developer":  _p("voltagent-core-dev:frontend-developer",  _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-core-dev:backend-developer":   _p("voltagent-core-dev:backend-developer",   _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-core-dev:api-designer":        _p("voltagent-core-dev:api-designer",        _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-core-dev:ui-designer":         _p("voltagent-core-dev:ui-designer",         _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-core-dev:mobile-developer":    _p("voltagent-core-dev:mobile-developer",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-core-dev:websocket-engineer":  _p("voltagent-core-dev:websocket-engineer",  _STANDARD, _NO_DELETE_DEPLOY),

    # ── Meta Coordination ─────────────────────────────────────────────────────
    "voltagent-meta:multi-agent-coordinator": _p("voltagent-meta:multi-agent-coordinator", _LEAD, _NO_DEPLOY,
                                                  "Escalate: coordination above RA Lead scope requires Admin"),
    "voltagent-meta:workflow-orchestrator":   _p("voltagent-meta:workflow-orchestrator",   _LEAD, _NO_DEPLOY,
                                                  "Escalate: workflow decisions above RA Lead scope require Admin"),
    "voltagent-meta:task-distributor":        _p("voltagent-meta:task-distributor",        _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-meta:context-manager":         _p("voltagent-meta:context-manager",         _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-meta:error-coordinator":       _p("voltagent-meta:error-coordinator",       _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-meta:performance-monitor":     _p("voltagent-meta:performance-monitor",     _READ_ONLY, _NO_DELETE_DEPLOY),
    "voltagent-meta:knowledge-synthesizer":   _p("voltagent-meta:knowledge-synthesizer",   _STANDARD, _NO_DELETE_DEPLOY),

    # ── Business ──────────────────────────────────────────────────────────────
    "voltagent-biz:product-manager":     _p("voltagent-biz:product-manager",     _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-biz:technical-writer":    _p("voltagent-biz:technical-writer",    _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-biz:business-analyst":    _p("voltagent-biz:business-analyst",    _READ_ONLY, _NO_DELETE_DEPLOY),
    "voltagent-biz:scrum-master":        _p("voltagent-biz:scrum-master",        _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-biz:project-manager":     _p("voltagent-biz:project-manager",     _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-biz:legal-advisor":       _p("voltagent-biz:legal-advisor",       _READ_ONLY, _NO_DELETE_DEPLOY),
    "voltagent-biz:ux-researcher":       _p("voltagent-biz:ux-researcher",       _READ_ONLY, _NO_DELETE_DEPLOY),

    # ── Plugin agents ─────────────────────────────────────────────────────────
    "feature-dev:code-architect":             _p("feature-dev:code-architect",             _STANDARD, _NO_DELETE_DEPLOY),
    "feature-dev:code-reviewer":              _p("feature-dev:code-reviewer",              _READ_ONLY, _NO_DELETE_DEPLOY),
    "feature-dev:code-explorer":              _p("feature-dev:code-explorer",              _READ_ONLY, _NO_DELETE_DEPLOY),
    "pr-review-toolkit:code-reviewer":        _p("pr-review-toolkit:code-reviewer",        _READ_ONLY, _NO_DELETE_DEPLOY),
    "pr-review-toolkit:type-design-analyzer": _p("pr-review-toolkit:type-design-analyzer", _READ_ONLY, _NO_DELETE_DEPLOY),
    "pr-review-toolkit:pr-test-analyzer":     _p("pr-review-toolkit:pr-test-analyzer",     _READ_ONLY, _NO_DELETE_DEPLOY),
    "code-simplifier:code-simplifier":        _p("code-simplifier:code-simplifier",        _STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-dev-exp:refactoring-specialist":_p("voltagent-dev-exp:refactoring-specialist",_STANDARD, _NO_DELETE_DEPLOY),
    "voltagent-dev-exp:mcp-developer":        _p("voltagent-dev-exp:mcp-developer",        _STANDARD, _NO_DELETE_DEPLOY),
}
