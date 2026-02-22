"""
Sprint 8 unit tests — FDA-232, FDA-233
=======================================
Tests for the two NPD framework Python modules introduced in Sprint 8:

 - npd_agent_matrix  (FDA-232): NpdStage enum, AgentRole, STAGE_AGENTS matrix, public API
 - npd_hitl_gates    (FDA-233): GateId/Status/Role enums, HitlGate, GateApprovalRecord,
                                create_approval_record() factory and validation

All tests are pure-Python unit tests — no database, no network required.
"""

import pytest
from datetime import timezone


# ── npd_agent_matrix tests ────────────────────────────────────────────────────


class TestNpdStage:
    """Verify the NpdStage enum is complete and well-ordered."""

    def test_all_12_stages_present(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        assert len(NpdStage) == 12

    def test_ordered_list_starts_with_concept(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        ordered = NpdStage.ordered()
        assert ordered[0] == NpdStage.CONCEPT

    def test_ordered_list_ends_with_post_market(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        ordered = NpdStage.ordered()
        assert ordered[-1] == NpdStage.POST_MARKET

    def test_ordered_list_length_matches_enum(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        assert len(NpdStage.ordered()) == len(NpdStage)

    def test_display_name_replaces_underscore(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        assert NpdStage.FDA_REVIEW.display_name == "Fda Review"

    def test_string_value_matches_name(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        assert NpdStage.CLASSIFY.value == "CLASSIFY"


class TestStageAgents:
    """Verify the STAGE_AGENTS matrix covers all stages and agents."""

    def test_every_stage_has_at_least_one_agent(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, STAGE_AGENTS
        for stage in NpdStage:
            assert stage in STAGE_AGENTS, f"Stage {stage.value} missing from STAGE_AGENTS"
            assert len(STAGE_AGENTS[stage]) >= 1, f"Stage {stage.value} has no agents"

    def test_every_stage_has_at_least_one_primary_agent(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, STAGE_AGENTS
        for stage in NpdStage:
            primaries = [a for a in STAGE_AGENTS[stage] if a.is_primary]
            assert len(primaries) >= 1, f"Stage {stage.value} has no primary agent"

    def test_fda_data_analyst_present_in_classify(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, STAGE_AGENTS
        ids = [a.id for a in STAGE_AGENTS[NpdStage.CLASSIFY]]
        assert "fda-510k-plugin:fda-data-analyst" in ids

    def test_agent_ids_non_empty_strings(self):
        from plugins.fda_tools.lib.npd_agent_matrix import STAGE_AGENTS
        for agents in STAGE_AGENTS.values():
            for agent in agents:
                assert agent.id and isinstance(agent.id, str)
                assert agent.name and isinstance(agent.name, str)

    def test_frozen_dataclass_cannot_be_mutated(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, STAGE_AGENTS
        agent = STAGE_AGENTS[NpdStage.CONCEPT][0]
        with pytest.raises((AttributeError, TypeError)):
            agent.name = "Mutated"  # type: ignore[misc]


class TestAgentMatrixPublicApi:
    """Tests for the public query functions."""

    def test_get_agents_for_stage_returns_all(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, STAGE_AGENTS, get_agents_for_stage
        for stage in NpdStage:
            assert get_agents_for_stage(stage) == STAGE_AGENTS[stage]

    def test_get_primary_agents_subset_of_all(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, get_agents_for_stage, get_primary_agents
        for stage in NpdStage:
            primaries = get_primary_agents(stage)
            all_agents = get_agents_for_stage(stage)
            assert set(a.id for a in primaries) <= set(a.id for a in all_agents)

    def test_get_unique_agent_ids_is_frozenset(self):
        from plugins.fda_tools.lib.npd_agent_matrix import get_unique_agent_ids
        ids = get_unique_agent_ids()
        assert isinstance(ids, frozenset)
        assert len(ids) > 0

    def test_unique_agent_ids_contains_fda_analyst(self):
        from plugins.fda_tools.lib.npd_agent_matrix import get_unique_agent_ids
        assert "fda-510k-plugin:fda-data-analyst" in get_unique_agent_ids()

    def test_get_stages_for_agent_fda_analyst(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage, get_stages_for_agent
        stages = get_stages_for_agent("fda-510k-plugin:fda-data-analyst")
        # FDA analyst appears in CLASSIFY, PREDICATE, FDA_REVIEW, POST_MARKET
        assert NpdStage.CLASSIFY    in stages
        assert NpdStage.PREDICATE   in stages
        assert NpdStage.FDA_REVIEW  in stages
        assert NpdStage.POST_MARKET in stages

    def test_get_stages_for_unknown_agent_is_empty(self):
        from plugins.fda_tools.lib.npd_agent_matrix import get_stages_for_agent
        assert get_stages_for_agent("nonexistent:agent") == []

    def test_get_matrix_summary_has_12_entries(self):
        from plugins.fda_tools.lib.npd_agent_matrix import get_matrix_summary
        summary = get_matrix_summary()
        assert len(summary) == 12

    def test_matrix_summary_entry_shape(self):
        from plugins.fda_tools.lib.npd_agent_matrix import get_matrix_summary
        entry = get_matrix_summary()[0]
        assert "stage"          in entry
        assert "display_name"   in entry
        assert "agent_count"    in entry
        assert "primary_agents" in entry
        assert "support_agents" in entry

    def test_matrix_summary_primary_agents_are_dicts(self):
        from plugins.fda_tools.lib.npd_agent_matrix import get_matrix_summary
        for entry in get_matrix_summary():
            for a in entry["primary_agents"]:
                assert "id"          in a
                assert "name"        in a
                assert "description" in a


# ── npd_hitl_gates tests ──────────────────────────────────────────────────────


class TestGateEnums:
    """Verify GateId, GateStatus, and ReviewerRole enums."""

    def test_five_gate_ids(self):
        from plugins.fda_tools.lib.npd_hitl_gates import GateId
        assert len(GateId) == 5

    def test_gate_classify_value(self):
        from plugins.fda_tools.lib.npd_hitl_gates import GateId
        assert GateId.GATE_CLASSIFY.value == "GATE_CLASSIFY"

    def test_gate_display_name_strips_prefix(self):
        from plugins.fda_tools.lib.npd_hitl_gates import GateId
        assert GateId.GATE_CLASSIFY.display_name == "Classify Gate"
        assert GateId.GATE_SUBMIT.display_name   == "Submit Gate"

    def test_four_gate_statuses(self):
        from plugins.fda_tools.lib.npd_hitl_gates import GateStatus
        assert {"PENDING", "APPROVED", "REJECTED", "ESCALATED"} == {s.value for s in GateStatus}

    def test_five_reviewer_roles(self):
        from plugins.fda_tools.lib.npd_hitl_gates import ReviewerRole
        assert len(ReviewerRole) == 5


class TestHitlGateDefinitions:
    """Verify the static gate definitions in HITL_GATES."""

    def test_all_five_gates_present(self):
        from plugins.fda_tools.lib.npd_hitl_gates import HITL_GATES, GateId
        for gate_id in GateId:
            assert gate_id in HITL_GATES

    def test_each_gate_has_checklist(self):
        from plugins.fda_tools.lib.npd_hitl_gates import HITL_GATES
        for gate in HITL_GATES.values():
            assert len(gate.checklist) >= 3, f"Gate {gate.gate_id.value} has fewer than 3 checklist items"

    def test_each_gate_has_required_reviewers(self):
        from plugins.fda_tools.lib.npd_hitl_gates import HITL_GATES
        for gate in HITL_GATES.values():
            assert len(gate.required_reviewers) >= 1

    def test_sla_hours_positive(self):
        from plugins.fda_tools.lib.npd_hitl_gates import HITL_GATES
        for gate in HITL_GATES.values():
            assert gate.sla_hours > 0
            assert gate.escalation_hours > gate.sla_hours

    def test_gate_classify_from_to_stages(self):
        from plugins.fda_tools.lib.npd_hitl_gates import HITL_GATES, GateId
        g = HITL_GATES[GateId.GATE_CLASSIFY]
        assert g.from_stage == "CLASSIFY"
        assert g.to_stage   == "PREDICATE"

    def test_gate_submit_from_to_stages(self):
        from plugins.fda_tools.lib.npd_hitl_gates import HITL_GATES, GateId
        g = HITL_GATES[GateId.GATE_SUBMIT]
        assert g.from_stage == "REVIEW"
        assert g.to_stage   == "SUBMIT"

    def test_get_gate_returns_correct_gate(self):
        from plugins.fda_tools.lib.npd_hitl_gates import get_gate, GateId
        g = get_gate(GateId.GATE_PREDICATE)
        assert g.gate_id == GateId.GATE_PREDICATE

    def test_get_gate_for_transition_found(self):
        from plugins.fda_tools.lib.npd_hitl_gates import get_gate_for_transition, GateId
        g = get_gate_for_transition("CLASSIFY", "PREDICATE")
        assert g is not None
        assert g.gate_id == GateId.GATE_CLASSIFY

    def test_get_gate_for_transition_not_found(self):
        from plugins.fda_tools.lib.npd_hitl_gates import get_gate_for_transition
        assert get_gate_for_transition("CONCEPT", "PREDICATE") is None

    def test_all_gates_in_order_returns_5(self):
        from plugins.fda_tools.lib.npd_hitl_gates import all_gates_in_order, GateId
        gates = all_gates_in_order()
        assert len(gates) == 5
        assert gates[0].gate_id == GateId.GATE_CLASSIFY
        assert gates[-1].gate_id == GateId.GATE_CLEARED


class TestCreateApprovalRecord:
    """Tests for the create_approval_record factory and its validation logic."""

    def _all_required_ids(self, gate_id):
        from plugins.fda_tools.lib.npd_hitl_gates import HITL_GATES
        return [item.id for item in HITL_GATES[gate_id].checklist if item.required]

    def test_approved_with_all_required_items_succeeds(self):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        checked = self._all_required_ids(GateId.GATE_CLASSIFY)
        record = create_approval_record(
            gate_id       = GateId.GATE_CLASSIFY,
            project_id    = "PROJ-001",
            status        = GateStatus.APPROVED,
            reviewer_id   = "ra@example.com",
            reviewer_role = ReviewerRole.RA_LEAD,
            checked_items = checked,
        )
        assert record.status == GateStatus.APPROVED
        assert record.project_id == "PROJ-001"

    def test_approved_with_missing_required_item_raises(self):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        with pytest.raises(ValueError, match="required checklist items not checked"):
            create_approval_record(
                gate_id       = GateId.GATE_CLASSIFY,
                project_id    = "PROJ-001",
                status        = GateStatus.APPROVED,
                reviewer_id   = "ra@example.com",
                reviewer_role = ReviewerRole.RA_LEAD,
                checked_items = [],   # no items checked
            )

    def test_approved_with_override_reason_allows_missing_items(self):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        record = create_approval_record(
            gate_id         = GateId.GATE_CLASSIFY,
            project_id      = "PROJ-002",
            status          = GateStatus.APPROVED,
            reviewer_id     = "ra@example.com",
            reviewer_role   = ReviewerRole.RA_LEAD,
            checked_items   = [],
            override_reason = "Emergency expedited approval — items to be completed post-hoc",
        )
        assert record.status == GateStatus.APPROVED
        assert record.override_reason is not None

    def test_rejected_does_not_validate_checklist(self):
        """REJECTED records should not require any checklist items."""
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        record = create_approval_record(
            gate_id       = GateId.GATE_SUBMIT,
            project_id    = "PROJ-003",
            status        = GateStatus.REJECTED,
            reviewer_id   = "manager@example.com",
            reviewer_role = ReviewerRole.RA_MANAGER,
            checked_items = [],
            comments      = "SRI score below threshold",
        )
        assert record.status == GateStatus.REJECTED

    def test_escalated_does_not_validate_checklist(self):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        record = create_approval_record(
            gate_id       = GateId.GATE_PREDICATE,
            project_id    = "PROJ-004",
            status        = GateStatus.ESCALATED,
            reviewer_id   = "counsel@lawfirm.com",
            reviewer_role = ReviewerRole.REG_COUNSEL,
            checked_items = [],
        )
        assert record.status == GateStatus.ESCALATED

    def test_record_timestamp_is_timezone_aware(self):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        checked = self._all_required_ids(GateId.GATE_PREDICATE)
        record = create_approval_record(
            gate_id       = GateId.GATE_PREDICATE,
            project_id    = "PROJ-005",
            status        = GateStatus.APPROVED,
            reviewer_id   = "engineer@example.com",
            reviewer_role = ReviewerRole.ENGINEER,
            checked_items = checked,
        )
        assert record.timestamp.tzinfo is not None
        assert record.timestamp.tzinfo == timezone.utc

    def test_checked_items_stored_as_list_copy(self):
        """Mutations to the original list must not affect the record."""
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        checked = self._all_required_ids(GateId.GATE_CLEARED)
        record  = create_approval_record(
            gate_id       = GateId.GATE_CLEARED,
            project_id    = "PROJ-006",
            status        = GateStatus.APPROVED,
            reviewer_id   = "qa@example.com",
            reviewer_role = ReviewerRole.QA_LEAD,
            checked_items = checked,
        )
        snapshot = list(record.checked_items)
        checked.clear()
        assert record.checked_items == snapshot

    def test_comments_default_empty_string(self):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        checked = self._all_required_ids(GateId.GATE_PATHWAY)
        record = create_approval_record(
            gate_id       = GateId.GATE_PATHWAY,
            project_id    = "PROJ-007",
            status        = GateStatus.APPROVED,
            reviewer_id   = "ra_manager@example.com",
            reviewer_role = ReviewerRole.RA_MANAGER,
            checked_items = checked,
        )
        assert record.comments == ""

    def test_override_reason_default_none(self):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        checked = self._all_required_ids(GateId.GATE_CLASSIFY)
        record = create_approval_record(
            gate_id       = GateId.GATE_CLASSIFY,
            project_id    = "PROJ-008",
            status        = GateStatus.APPROVED,
            reviewer_id   = "ra@example.com",
            reviewer_role = ReviewerRole.RA_LEAD,
            checked_items = checked,
        )
        assert record.override_reason is None
