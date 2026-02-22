"""
FDA-232  [NPD-001] AI Agent Needs Matrix for Autonomous NPD
============================================================
Maps each of the 12 NPD stages to the AI agents required to advance
through it.  The matrix is consumed by:
 - The NPD state machine (FDA-234) when deciding which agents to spawn
 - The Agent Orchestration Panel (FDA-243) to populate agent slots
 - HITL gate logic (FDA-233) to know which outputs require human review

Stage definitions (aligned with the 12-stage NPD pipeline):
  CONCEPT       → Initial device concept exploration
  CLASSIFY      → Device classification (class I/II/III, product code)
  PREDICATE     → Predicate device search and selection
  PATHWAY       → Regulatory submission pathway determination
  PRESUB        → Pre-submission (Q-Sub / Pre-IDE) preparation
  TESTING       → Performance, biocompatibility, sterility testing
  DRAFTING      → 510(k) submission document drafting
  REVIEW        → Internal consistency review
  SUBMIT        → Submission assembly and eCopy/eSTAR finalization
  FDA_REVIEW    → FDA review monitoring / response management
  CLEARED       → Post-clearance commercialization
  POST_MARKET   → Post-market surveillance

AgentRole values correspond to Claude Code subagent_type identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List


# ── Stage enum ────────────────────────────────────────────────────────────────


class NpdStage(str, Enum):
    CONCEPT       = "CONCEPT"
    CLASSIFY      = "CLASSIFY"
    PREDICATE     = "PREDICATE"
    PATHWAY       = "PATHWAY"
    PRESUB        = "PRESUB"
    TESTING       = "TESTING"
    DRAFTING      = "DRAFTING"
    REVIEW        = "REVIEW"
    SUBMIT        = "SUBMIT"
    FDA_REVIEW    = "FDA_REVIEW"
    CLEARED       = "CLEARED"
    POST_MARKET   = "POST_MARKET"

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()

    @classmethod
    def ordered(cls) -> List["NpdStage"]:
        return [
            cls.CONCEPT, cls.CLASSIFY, cls.PREDICATE, cls.PATHWAY,
            cls.PRESUB,  cls.TESTING,  cls.DRAFTING,  cls.REVIEW,
            cls.SUBMIT,  cls.FDA_REVIEW, cls.CLEARED,  cls.POST_MARKET,
        ]


# ── Agent role definitions ────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentRole:
    """Descriptor for an AI agent role within the NPD workflow."""
    id:          str   # matches subagent_type in Claude Code Task calls
    name:        str   # human-readable display name
    description: str   # what the agent does at this stage
    is_primary:  bool  = True   # False = supporting role only


# ── Stage agent matrix ────────────────────────────────────────────────────────


#: Maps each NPD stage to a list of AgentRole objects.
#: Primary agents are required; supporting agents are optional accelerators.
STAGE_AGENTS: Dict[NpdStage, List[AgentRole]] = {

    NpdStage.CONCEPT: [
        AgentRole(
            id="voltagent-research:research-analyst",
            name="Research Analyst",
            description="Literature review: gather scientific evidence, competitive landscape, "
                        "clinical need documentation",
        ),
        AgentRole(
            id="voltagent-biz:product-manager",
            name="Product Manager",
            description="Define device concept, clinical indication, user needs, and "
                        "intended patient population",
        ),
        AgentRole(
            id="voltagent-research:market-researcher",
            name="Market Researcher",
            description="Assess market size, competitor products, and unmet clinical needs",
            is_primary=False,
        ),
    ],

    NpdStage.CLASSIFY: [
        AgentRole(
            id="fda-510k-plugin:fda-data-analyst",
            name="FDA Data Analyst",
            description="Classify the device using FDA product code database; determine "
                        "device class (I/II/III) and applicable regulations (21 CFR Part X)",
        ),
        AgentRole(
            id="voltagent-qa-sec:compliance-auditor",
            name="Compliance Auditor",
            description="Cross-validate classification against De Novo and exempt-device "
                        "databases; flag classification edge cases",
            is_primary=False,
        ),
    ],

    NpdStage.PREDICATE: [
        AgentRole(
            id="fda-510k-plugin:fda-data-analyst",
            name="FDA Data Analyst",
            description="Search 510(k) clearance database for predicate devices; rank by "
                        "SE similarity score, review time, and clearance recency",
        ),
        AgentRole(
            id="voltagent-research:research-analyst",
            name="Research Analyst",
            description="Extract predicate device specifications from 510(k) summaries; "
                        "build SE comparison table",
        ),
        AgentRole(
            id="voltagent-data-ai:data-scientist",
            name="Data Scientist",
            description="Run predicate chain validation; check recall / MAUDE history "
                        "on candidate predicates",
            is_primary=False,
        ),
    ],

    NpdStage.PATHWAY: [
        AgentRole(
            id="voltagent-biz:product-manager",
            name="Product Manager",
            description="Evaluate 510(k) vs De Novo vs PMA pathway; factor in device class, "
                        "predicate availability, and development timeline",
        ),
        AgentRole(
            id="voltagent-qa-sec:compliance-auditor",
            name="Compliance Auditor",
            description="Review applicable special controls, guidance documents, and "
                        "QSR / QMS obligations per pathway",
        ),
    ],

    NpdStage.PRESUB: [
        AgentRole(
            id="voltagent-biz:technical-writer",
            name="Technical Writer",
            description="Draft Pre-Submission (Q-Sub) letter including proposed testing "
                        "protocols and key regulatory questions",
        ),
        AgentRole(
            id="voltagent-qa-sec:qa-expert",
            name="QA Expert",
            description="Review Pre-Sub draft for completeness; cross-reference guidance "
                        "expectations for the device class",
        ),
    ],

    NpdStage.TESTING: [
        AgentRole(
            id="voltagent-data-ai:data-scientist",
            name="Data Scientist",
            description="Define testing protocols (bench, animal, clinical); calculate "
                        "sample sizes, statistical acceptance criteria",
        ),
        AgentRole(
            id="voltagent-qa-sec:test-automator",
            name="Test Automator",
            description="Build automated data collection pipelines for in-vitro test "
                        "results; validate measurement system analysis",
        ),
        AgentRole(
            id="voltagent-research:research-analyst",
            name="Research Analyst",
            description="Literature search for predicate device test data; identify "
                        "applicable ISO/ASTM/IEC standards",
            is_primary=False,
        ),
    ],

    NpdStage.DRAFTING: [
        AgentRole(
            id="voltagent-biz:technical-writer",
            name="Technical Writer",
            description="Draft all 510(k) sections: Intended Use, Device Description, "
                        "SE Summary, Performance Testing, Biocompatibility, Labeling",
        ),
        AgentRole(
            id="voltagent-data-ai:llm-architect",
            name="LLM Architect",
            description="Generate AI inline suggestions for each submission section; "
                        "apply compliance and clarity improvements",
        ),
        AgentRole(
            id="voltagent-qa-sec:code-reviewer",
            name="Code / Content Reviewer",
            description="Check cross-section consistency, specification alignment, "
                        "and regulatory citation accuracy",
            is_primary=False,
        ),
    ],

    NpdStage.REVIEW: [
        AgentRole(
            id="voltagent-qa-sec:qa-expert",
            name="QA Expert",
            description="Internal RTA (Refuse-to-Accept) simulation; score submission "
                        "readiness using SRI metrics",
        ),
        AgentRole(
            id="voltagent-qa-sec:compliance-auditor",
            name="Compliance Auditor",
            description="Audit submission for 21 CFR Part 820 / ISO 13485 QMS references, "
                        "labeling requirements, and standards declarations",
        ),
        AgentRole(
            id="voltagent-biz:technical-writer",
            name="Technical Writer",
            description="Revise sections based on review findings; update version history "
                        "and change log",
            is_primary=False,
        ),
    ],

    NpdStage.SUBMIT: [
        AgentRole(
            id="voltagent-biz:technical-writer",
            name="Technical Writer",
            description="Assemble final submission package: eCopy cover letter, "
                        "eSTAR XML, Form 3514, all supporting exhibits",
        ),
        AgentRole(
            id="voltagent-infra:devops-engineer",
            name="DevOps Engineer",
            description="Manage eCopy encryption, CDRH portal upload, submission "
                        "tracking number retrieval",
            is_primary=False,
        ),
    ],

    NpdStage.FDA_REVIEW: [
        AgentRole(
            id="fda-510k-plugin:fda-data-analyst",
            name="FDA Data Analyst",
            description="Monitor FDA CDRH submission tracker; alert on status changes, "
                        "AI / IRD letters, and meeting requests",
        ),
        AgentRole(
            id="voltagent-biz:technical-writer",
            name="Technical Writer",
            description="Draft responses to FDA AI (Additional Information) requests "
                        "within required 180-day window",
            is_primary=False,
        ),
    ],

    NpdStage.CLEARED: [
        AgentRole(
            id="voltagent-biz:product-manager",
            name="Product Manager",
            description="Plan commercialization: launch readiness, reimbursement coding "
                        "(CPT/ICD), and market access strategy",
        ),
        AgentRole(
            id="voltagent-qa-sec:compliance-auditor",
            name="Compliance Auditor",
            description="Establish post-market Quality System obligations: MDR reporting, "
                        "recall procedures, corrective action (CAPA) process",
        ),
    ],

    NpdStage.POST_MARKET: [
        AgentRole(
            id="fda-510k-plugin:fda-data-analyst",
            name="FDA Data Analyst",
            description="Continuous MAUDE surveillance: CUSUM spike detection, signal "
                        "correlation analysis, recall watch",
        ),
        AgentRole(
            id="voltagent-infra:sre-engineer",
            name="SRE Engineer",
            description="Monitor post-market digital health / SaMD performance SLOs; "
                        "alert on anomaly patterns requiring regulatory reporting",
            is_primary=False,
        ),
        AgentRole(
            id="voltagent-data-ai:data-scientist",
            name="Data Scientist",
            description="Analyze real-world evidence (RWE) and clinical data for "
                        "PMA supplement / De Novo reclassification triggers",
            is_primary=False,
        ),
    ],
}


# ── Public API ────────────────────────────────────────────────────────────────


def get_agents_for_stage(stage: NpdStage) -> List[AgentRole]:
    """Return all agent roles (primary + supporting) for a given NPD stage."""
    return STAGE_AGENTS.get(stage, [])


def get_primary_agents(stage: NpdStage) -> List[AgentRole]:
    """Return only primary (required) agents for the stage."""
    return [a for a in get_agents_for_stage(stage) if a.is_primary]


def get_unique_agent_ids() -> FrozenSet[str]:
    """Return all unique agent IDs referenced across the entire matrix."""
    return frozenset(
        agent.id
        for agents in STAGE_AGENTS.values()
        for agent in agents
    )


def get_stages_for_agent(agent_id: str) -> List[NpdStage]:
    """Return all stages where the given agent is involved."""
    return [
        stage for stage, agents in STAGE_AGENTS.items()
        if any(a.id == agent_id for a in agents)
    ]


def get_matrix_summary() -> List[dict]:
    """
    Return a serialisable summary of the full agent-stage matrix.

    Suitable for the Agent Orchestration Panel API endpoint.
    """
    return [
        {
            "stage":          stage.value,
            "display_name":   stage.display_name,
            "agent_count":    len(agents),
            "primary_agents": [
                {"id": a.id, "name": a.name, "description": a.description}
                for a in agents if a.is_primary
            ],
            "support_agents": [
                {"id": a.id, "name": a.name, "description": a.description}
                for a in agents if not a.is_primary
            ],
        }
        for stage, agents in STAGE_AGENTS.items()
    ]
