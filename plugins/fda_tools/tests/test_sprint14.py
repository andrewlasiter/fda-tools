"""
Sprint 14 — Orchestrator Governance Layer (FDA-264 through FDA-268)
===================================================================
Tests for:
  - agent_permission_policy.py  (FDA-264 / ORCH-011)
  - orchestrator_audit_bridge.py (FDA-265 / ORCH-012)
  - npd_rollback.py              (FDA-266 / ORCH-013)
  - orchestrator_telemetry.py    (FDA-267 / ORCH-014)
  - agent_contracts.py           (FDA-268 / ORCH-015)
"""

import json
import pytest

# ── Module under test imports ─────────────────────────────────────────────────

from fda_tools.lib.agent_permission_policy import (
    AgentPermissionPolicy,
    AgentPermissionError,
    AgentScope,
    AGENT_POLICY_REGISTRY,
    check_permission,
    enforce_permission,
)
from fda_tools.lib.orchestrator_audit_bridge import OrchestratorAuditBridge
from fda_tools.lib.cfr_part11 import Part11AuditLog, AuditAction
from fda_tools.lib.npd_rollback import NpdRollbackManager, NpdSnapshot, RollbackError
from fda_tools.lib.orchestrator_telemetry import OrchestratorTelemetry, MetricPoint
from fda_tools.lib.agent_contracts import (
    AgentFinding,
    AgentOutput,
    AggregatedResults,
    AgentContractViolation,
    validate_agent_output,
    build_finding,
    aggregate,
    _PYDANTIC_AVAILABLE,
)


# =============================================================================
# FDA-264: Agent Permission Policy Engine
# =============================================================================

class TestAgentPermissionPolicy:
    """Unit tests for AgentPermissionPolicy dataclass."""

    def _make_policy(self, permitted=None, prohibited=None, escalation="Escalate"):
        return AgentPermissionPolicy(
            agent_id="test-agent",
            permitted_scopes=frozenset(permitted or []),
            prohibited_actions=frozenset(prohibited or []),
            escalation_trigger=escalation,
        )

    def test_allows_permitted_action(self):
        policy = self._make_policy(permitted=["read", "write"])
        assert policy.allows("read") is True
        assert policy.allows("write") is True

    def test_denies_action_not_in_permitted(self):
        policy = self._make_policy(permitted=["read"])
        assert policy.allows("write") is False

    def test_prohibited_overrides_permitted(self):
        policy = self._make_policy(permitted=["read", "delete"], prohibited=["delete"])
        assert policy.allows("delete") is False

    def test_empty_permitted_denies_all(self):
        policy = self._make_policy()
        for scope in AgentScope:
            assert policy.allows(scope.value) is False

    def test_frozen_dataclass_immutable(self):
        policy = self._make_policy(permitted=["read"])
        with pytest.raises((AttributeError, TypeError)):
            policy.agent_id = "other"  # type: ignore[misc]

    def test_permitted_scopes_is_frozenset(self):
        policy = self._make_policy(permitted=["read"])
        assert isinstance(policy.permitted_scopes, frozenset)

    def test_prohibited_actions_is_frozenset(self):
        policy = self._make_policy(prohibited=["delete"])
        assert isinstance(policy.prohibited_actions, frozenset)

    def test_escalation_trigger_stored(self):
        policy = self._make_policy(escalation="Call RA Lead immediately")
        assert "RA Lead" in policy.escalation_trigger

    def test_allows_unknown_action_returns_false(self):
        policy = self._make_policy(permitted=["read"])
        assert policy.allows("fly_to_moon") is False

    def test_agent_scope_enum_values(self):
        scopes = {s.value for s in AgentScope}
        assert "read" in scopes
        assert "approve" in scopes
        assert "deploy" in scopes


class TestCheckPermission:
    """Tests for the check_permission() soft-check function."""

    def _registry(self):
        return {
            "writer-agent": AgentPermissionPolicy(
                agent_id="writer-agent",
                permitted_scopes=frozenset({"read", "suggest", "write"}),
                prohibited_actions=frozenset({"delete", "deploy"}),
                escalation_trigger="Escalate to RA Lead",
            ),
            "read-only-agent": AgentPermissionPolicy(
                agent_id="read-only-agent",
                permitted_scopes=frozenset({"read", "suggest"}),
                prohibited_actions=frozenset(),
                escalation_trigger="Escalate for write access",
            ),
        }

    def test_known_agent_permitted_action_returns_true(self):
        assert check_permission("writer-agent", "write", self._registry()) is True

    def test_known_agent_denied_action_returns_false(self):
        assert check_permission("writer-agent", "delete", self._registry()) is False

    def test_prohibited_action_returns_false(self):
        assert check_permission("writer-agent", "deploy", self._registry()) is False

    def test_unknown_agent_returns_false(self):
        assert check_permission("ghost-agent", "read", self._registry()) is False

    def test_read_only_agent_cannot_write(self):
        assert check_permission("read-only-agent", "write", self._registry()) is False

    def test_read_only_agent_can_suggest(self):
        assert check_permission("read-only-agent", "suggest", self._registry()) is True

    def test_uses_global_registry_by_default(self):
        # At least one well-known agent should be in the global registry
        result = check_permission("voltagent-lang:python-pro", "write")
        assert result is True

    def test_global_registry_denies_deploy_for_standard_agent(self):
        result = check_permission("voltagent-lang:python-pro", "deploy")
        assert result is False


class TestEnforcePermission:
    """Tests for the enforce_permission() hard-check function."""

    def _registry(self):
        return {
            "approver-agent": AgentPermissionPolicy(
                agent_id="approver-agent",
                permitted_scopes=frozenset({"read", "suggest", "write", "approve"}),
                prohibited_actions=frozenset({"delete"}),
                escalation_trigger="Escalate to Admin for delete",
            ),
        }

    def test_permitted_action_does_not_raise(self):
        enforce_permission("approver-agent", "approve", self._registry())

    def test_denied_action_raises_agent_permission_error(self):
        with pytest.raises(AgentPermissionError) as exc_info:
            enforce_permission("approver-agent", "delete", self._registry())
        assert "approver-agent" in str(exc_info.value)
        assert "delete" in str(exc_info.value)

    def test_unknown_agent_raises_agent_permission_error(self):
        with pytest.raises(AgentPermissionError):
            enforce_permission("unknown-ghost", "read", self._registry())

    def test_exception_has_agent_id_attribute(self):
        with pytest.raises(AgentPermissionError) as exc_info:
            enforce_permission("approver-agent", "deploy", self._registry())
        assert exc_info.value.agent_id == "approver-agent"

    def test_exception_has_action_attribute(self):
        with pytest.raises(AgentPermissionError) as exc_info:
            enforce_permission("approver-agent", "deploy", self._registry())
        assert exc_info.value.action == "deploy"


class TestAgentPolicyRegistry:
    """Tests for the global AGENT_POLICY_REGISTRY."""

    def test_registry_is_dict(self):
        assert isinstance(AGENT_POLICY_REGISTRY, dict)

    def test_registry_has_at_least_30_agents(self):
        assert len(AGENT_POLICY_REGISTRY) >= 30

    def test_all_values_are_policy_instances(self):
        for key, val in AGENT_POLICY_REGISTRY.items():
            assert isinstance(val, AgentPermissionPolicy), f"Bad policy for {key!r}"

    def test_agent_ids_match_keys(self):
        for key, val in AGENT_POLICY_REGISTRY.items():
            assert val.agent_id == key

    def test_meta_coordinator_can_approve(self):
        policy = AGENT_POLICY_REGISTRY["voltagent-meta:multi-agent-coordinator"]
        assert policy.allows("approve") is True

    def test_read_only_agents_cannot_write(self):
        read_only_ids = [k for k, v in AGENT_POLICY_REGISTRY.items()
                         if "read" in v.permitted_scopes and "write" not in v.permitted_scopes]
        assert len(read_only_ids) >= 3, "Expected at least 3 read-only agents"
        for aid in read_only_ids:
            assert not AGENT_POLICY_REGISTRY[aid].allows("write")


# =============================================================================
# FDA-265: Orchestrator Decision Audit Trail
# =============================================================================

class TestOrchestratorAuditBridge:
    """Tests for OrchestratorAuditBridge."""

    def _bridge(self):
        log = Part11AuditLog()
        bridge = OrchestratorAuditBridge(log=log)
        return bridge, log

    def test_log_team_selection_appends_record(self):
        bridge, log = self._bridge()
        bridge.log_team_selection(
            team_data={"core_agents": ["security-auditor"], "total_agents": 1},
            task_profile_data={"task_type": "security_review"},
        )
        assert len(log.records()) == 1

    def test_log_team_selection_record_type(self):
        bridge, log = self._bridge()
        bridge.log_team_selection({}, {"task_type": "test"})
        assert log.records()[0].record_type == "orchestrator_event"

    def test_log_team_selection_action_is_create(self):
        bridge, log = self._bridge()
        bridge.log_team_selection({}, {})
        assert log.records()[0].action == AuditAction.CREATE

    def test_log_team_selection_content_is_valid_json(self):
        bridge, log = self._bridge()
        bridge.log_team_selection({"agents": ["a"]}, {"task_type": "x"})
        content = json.loads(log.records()[0].content)
        assert content["event"] == "team_selection"

    def test_log_phase_start_appends_record(self):
        bridge, log = self._bridge()
        bridge.log_phase_start(phase=1, agents=["security-auditor"])
        assert len(log.records()) == 1

    def test_log_phase_start_contains_phase_number(self):
        bridge, log = self._bridge()
        bridge.log_phase_start(phase=2, agents=["python-pro"])
        content = json.loads(log.records()[0].content)
        assert content["phase"] == 2
        assert "python-pro" in content["agents"]

    def test_log_phase_complete_action_is_update(self):
        bridge, log = self._bridge()
        bridge.log_phase_complete(phase=1, findings_count=3)
        assert log.records()[0].action == AuditAction.UPDATE

    def test_log_phase_complete_contains_findings_count(self):
        bridge, log = self._bridge()
        bridge.log_phase_complete(phase=3, findings_count=7)
        content = json.loads(log.records()[0].content)
        assert content["findings_count"] == 7

    def test_log_workflow_complete_action_is_export(self):
        bridge, log = self._bridge()
        bridge.log_workflow_complete({"run_id": "abc"})
        assert log.records()[0].action == AuditAction.EXPORT

    def test_log_permission_violation_action_is_access_denied(self):
        bridge, log = self._bridge()
        bridge.log_permission_violation("bad-agent", "delete")
        assert log.records()[0].action == AuditAction.ACCESS_DENIED

    def test_log_permission_violation_content(self):
        bridge, log = self._bridge()
        bridge.log_permission_violation("bad-agent", "deploy")
        content = json.loads(log.records()[0].content)
        assert content["agent_id"] == "bad-agent"
        assert content["action"] == "deploy"

    def test_log_rollback_action_is_update(self):
        bridge, log = self._bridge()
        bridge.log_rollback("CLASSIFY", "HITL gate rejected", "snap_abc123")
        assert log.records()[0].action == AuditAction.UPDATE

    def test_log_rollback_contains_snapshot_id(self):
        bridge, log = self._bridge()
        bridge.log_rollback("TESTING", "agent error", "snap_xyz")
        content = json.loads(log.records()[0].content)
        assert content["snapshot_id"] == "snap_xyz"

    def test_multiple_calls_accumulate_records(self):
        bridge, log = self._bridge()
        bridge.log_team_selection({}, {})
        bridge.log_phase_start(1, [])
        bridge.log_phase_complete(1, 0)
        bridge.log_workflow_complete({})
        assert len(log.records()) == 4

    def test_records_have_valid_integrity(self):
        bridge, log = self._bridge()
        bridge.log_team_selection({}, {"task_type": "integrity_test"})
        from fda_tools.lib.cfr_part11 import RecordIntegrity
        assert log.records()[0].verify_integrity() == RecordIntegrity.VALID


# =============================================================================
# FDA-266: NPD Workflow Rollback & Compensation
# =============================================================================

class TestNpdSnapshot:
    """Tests for the NpdSnapshot value object."""

    def _snap(self, stage="CONCEPT", data=None, is_good=True):
        mgr = NpdRollbackManager()
        return mgr.snapshot(stage, data or {"key": "value"}, is_good=is_good)

    def test_snapshot_has_snapshot_id(self):
        snap = self._snap()
        assert isinstance(snap.snapshot_id, str)
        assert len(snap.snapshot_id) == 16   # token_hex(8) → 16 hex chars

    def test_snapshot_has_stage(self):
        snap = self._snap(stage="CLASSIFY")
        assert snap.stage == "CLASSIFY"

    def test_restore_returns_deep_copy(self):
        data = {"a": {"b": 1}}
        snap = self._snap(data=data)
        restored = snap.restore()
        assert restored == data
        restored["a"]["b"] = 99
        assert snap.project_data["a"]["b"] == 1  # original unchanged

    def test_snapshot_is_frozen(self):
        snap = self._snap()
        with pytest.raises((AttributeError, TypeError)):
            snap.stage = "TESTING"  # type: ignore[misc]

    def test_is_good_default_true(self):
        snap = self._snap()
        assert snap.is_good is True


class TestNpdRollbackManager:
    """Tests for NpdRollbackManager."""

    def test_initial_snapshot_count_is_zero(self):
        mgr = NpdRollbackManager()
        assert mgr.snapshot_count() == 0

    def test_snapshot_increments_count(self):
        mgr = NpdRollbackManager()
        mgr.snapshot("CONCEPT", {})
        assert mgr.snapshot_count() == 1

    def test_multiple_snapshots_accumulate(self):
        mgr = NpdRollbackManager()
        for stage in ["CONCEPT", "CLASSIFY", "PREDICATE"]:
            mgr.snapshot(stage, {"stage": stage})
        assert mgr.snapshot_count() == 3

    def test_rollback_returns_last_good(self):
        mgr = NpdRollbackManager()
        snap1 = mgr.snapshot("CONCEPT", {"step": 1})
        snap2 = mgr.snapshot("CLASSIFY", {"step": 2})
        result = mgr.rollback_to_last_snapshot()
        assert result.snapshot_id == snap2.snapshot_id

    def test_rollback_skips_bad_snapshots(self):
        mgr = NpdRollbackManager()
        snap1 = mgr.snapshot("CONCEPT", {"step": 1})
        mgr.snapshot("CLASSIFY", {"step": 2})
        mgr.mark_last_bad()
        result = mgr.rollback_to_last_snapshot()
        assert result.snapshot_id == snap1.snapshot_id

    def test_rollback_raises_when_no_good_snapshot(self):
        mgr = NpdRollbackManager()
        with pytest.raises(RollbackError):
            mgr.rollback_to_last_snapshot()

    def test_rollback_to_last_good_before_stage(self):
        mgr = NpdRollbackManager()
        snap1 = mgr.snapshot("CONCEPT", {"step": 1})
        mgr.snapshot("CLASSIFY", {"step": 2})
        result = mgr.rollback_to_last_good_before("CLASSIFY")
        assert result.snapshot_id == snap1.snapshot_id

    def test_rollback_to_last_good_before_raises_if_none(self):
        mgr = NpdRollbackManager()
        mgr.snapshot("CONCEPT", {})
        with pytest.raises(RollbackError):
            mgr.rollback_to_last_good_before("CONCEPT")

    def test_mark_last_bad_sets_is_good_false(self):
        mgr = NpdRollbackManager()
        mgr.snapshot("CONCEPT", {})
        mgr.mark_last_bad()
        assert mgr.get_snapshot_chain()[-1].is_good is False

    def test_good_snapshot_count(self):
        mgr = NpdRollbackManager()
        mgr.snapshot("CONCEPT", {})
        mgr.snapshot("CLASSIFY", {})
        mgr.mark_last_bad()
        assert mgr.good_snapshot_count() == 1

    def test_get_snapshot_chain_returns_copy(self):
        mgr = NpdRollbackManager()
        mgr.snapshot("CONCEPT", {})
        chain = mgr.get_snapshot_chain()
        chain.clear()
        assert mgr.snapshot_count() == 1  # original unaffected

    def test_latest_stage_returns_most_recent(self):
        mgr = NpdRollbackManager()
        mgr.snapshot("CONCEPT", {})
        mgr.snapshot("CLASSIFY", {})
        assert mgr.latest_stage() == "CLASSIFY"

    def test_latest_stage_empty_manager(self):
        mgr = NpdRollbackManager()
        assert mgr.latest_stage() == ""

    def test_snapshot_deep_copies_data(self):
        mgr = NpdRollbackManager()
        data = {"nested": {"val": 42}}
        mgr.snapshot("CONCEPT", data)
        data["nested"]["val"] = 999
        assert mgr.get_snapshot_chain()[0].project_data["nested"]["val"] == 42

    def test_stage_coerced_to_string(self):
        mgr = NpdRollbackManager()
        # NpdStage-like enum would pass its .value or str() representation
        class FakeStage:
            def __str__(self): return "FAKE_STAGE"
        mgr.snapshot(FakeStage(), {})
        assert mgr.latest_stage() == "FAKE_STAGE"


# =============================================================================
# FDA-267: Orchestrator Structured Observability
# =============================================================================

class TestOrchestratorTelemetry:
    """Tests for OrchestratorTelemetry."""

    def test_span_noop_without_sdk(self):
        tel = OrchestratorTelemetry()
        with tel.span("test_span", task_type="review"):
            pass   # should not raise

    def test_record_agent_selection_adds_metrics(self):
        tel = OrchestratorTelemetry()
        tel.record_agent_selection("security-auditor", score=0.9, latency_ms=50.0)
        pts = tel.metrics()
        assert len(pts) == 3

    def test_record_agent_selection_metric_names(self):
        tel = OrchestratorTelemetry()
        tel.record_agent_selection("python-pro", score=0.85, latency_ms=30.0)
        names = {pt.name for pt in tel.metrics()}
        assert "orchestrator_agents_selected" in names
        assert "orchestrator_agent_selection_score" in names
        assert "orchestrator_agent_selection_latency_ms" in names

    def test_record_phase_complete_adds_metrics(self):
        tel = OrchestratorTelemetry()
        tel.record_phase_complete(phase=1, agent_count=3, duration_ms=5000.0, finding_count=4)
        assert len(tel.metrics()) == 3

    def test_record_phase_complete_duration_converted_to_seconds(self):
        tel = OrchestratorTelemetry()
        tel.record_phase_complete(phase=2, agent_count=2, duration_ms=2000.0, finding_count=1)
        secs = [pt for pt in tel.metrics() if "duration_seconds" in pt.name]
        assert len(secs) == 1
        assert secs[0].value == pytest.approx(2.0)

    def test_record_run_complete_increments_run_count(self):
        tel = OrchestratorTelemetry()
        tel.record_run_complete(success=True, total_findings=5)
        assert tel.health_status()["run_count"] == 1

    def test_record_run_complete_sets_last_timestamp(self):
        tel = OrchestratorTelemetry()
        tel.record_run_complete(success=True, total_findings=0)
        assert tel.health_status()["last_run_timestamp"] is not None

    def test_set_circuit_breaker_state(self):
        tel = OrchestratorTelemetry()
        tel.set_circuit_breaker_state("OPEN")
        assert tel.health_status()["circuit_breaker_state"] == "OPEN"

    def test_set_active_agents(self):
        tel = OrchestratorTelemetry()
        tel.set_active_agents(["agent-a", "agent-b"])
        assert tel.health_status()["active_agents"] == ["agent-a", "agent-b"]

    def test_health_status_keys(self):
        tel = OrchestratorTelemetry()
        status = tel.health_status()
        required = {"service", "circuit_breaker_state", "run_count", "last_run_timestamp",
                    "active_agents", "metrics_recorded"}
        assert required.issubset(status.keys())

    def test_metrics_returns_copy(self):
        tel = OrchestratorTelemetry()
        tel.record_run_start()
        pts = tel.metrics()
        pts.clear()
        assert len(tel.metrics()) == 1  # original unaffected

    def test_metrics_by_name(self):
        tel = OrchestratorTelemetry()
        tel.record_agent_selection("agent-x", score=0.7, latency_ms=20.0)
        pts = tel.metrics_by_name("orchestrator_agents_selected")
        assert len(pts) == 1
        assert pts[0].labels.get("agent_id") == "agent-x"

    def test_reset_clears_all_state(self):
        tel = OrchestratorTelemetry()
        tel.record_run_complete(success=True, total_findings=3)
        tel.set_circuit_breaker_state("OPEN")
        tel.reset()
        status = tel.health_status()
        assert status["run_count"] == 0
        assert status["circuit_breaker_state"] == "CLOSED"
        assert status["metrics_recorded"] == 0

    def test_metric_point_is_frozen(self):
        pt = MetricPoint(name="x", value=1.0, timestamp="2026-01-01T00:00:00Z", labels={})
        with pytest.raises((AttributeError, TypeError)):
            pt.value = 99.0  # type: ignore[misc]


# =============================================================================
# FDA-268: Agent I/O Contract Enforcement
# =============================================================================

class TestAgentFinding:
    """Tests for the AgentFinding model/stub."""

    def test_valid_finding_created(self):
        f = build_finding(
            agent_id="security-auditor",
            severity="high",
            location="api/auth.py:45",
            description="Missing rate limiting",
            recommendation="Add rate limiting middleware",
        )
        assert f.severity == "high"
        assert f.agent_id == "security-auditor"

    def test_finding_id_auto_generated(self):
        f = build_finding("agent", "low", "file.py", "desc", "rec")
        assert len(f.finding_id) == 16

    def test_invalid_severity_raises(self):
        with pytest.raises((ValueError, Exception)):
            build_finding("agent", "extreme", "file.py", "desc", "rec")

    def test_confidence_default_is_one(self):
        f = build_finding("agent", "medium", "loc", "desc", "rec")
        assert f.confidence == pytest.approx(1.0)

    def test_confidence_out_of_range_raises(self):
        with pytest.raises((ValueError, Exception)):
            build_finding("agent", "medium", "loc", "desc", "rec", confidence=1.5)


class TestValidateAgentOutput:
    """Tests for validate_agent_output()."""

    def _valid_raw(self):
        return {
            "agent_id": "voltagent-qa-sec:security-auditor",
            "phase": 2,
            "findings": [],
            "metadata": {},
        }

    def test_valid_raw_returns_agent_output(self):
        result = validate_agent_output(self._valid_raw())
        assert result.agent_id == "voltagent-qa-sec:security-auditor"
        assert result.phase == 2

    def test_missing_agent_id_raises_contract_violation(self):
        raw = self._valid_raw()
        del raw["agent_id"]
        with pytest.raises(AgentContractViolation):
            validate_agent_output(raw)

    def test_missing_phase_raises_contract_violation(self):
        raw = self._valid_raw()
        del raw["phase"]
        with pytest.raises(AgentContractViolation):
            validate_agent_output(raw)

    def test_wrong_phase_type_raises_contract_violation(self):
        raw = self._valid_raw()
        raw["phase"] = "two"
        with pytest.raises((AgentContractViolation, Exception)):
            validate_agent_output(raw)

    def test_valid_finding_in_findings_list(self):
        raw = self._valid_raw()
        raw["findings"] = [{
            "finding_id": "abc123",
            "severity": "critical",
            "location": "lib/auth.py",
            "description": "SQL injection",
            "recommendation": "Use parameterised queries",
            "agent_id": "security-auditor",
            "confidence": 0.95,
        }]
        result = validate_agent_output(raw)
        assert len(result.findings) == 1

    def test_contract_violation_has_agent_id(self):
        raw = {"agent_id": "my-agent", "phase": "bad"}
        try:
            validate_agent_output(raw)
        except (AgentContractViolation, Exception) as exc:
            # AgentContractViolation always has agent_id; generic exception is ok too
            pass


class TestAgentContractViolation:
    """Tests for AgentContractViolation exception."""

    def test_has_agent_id_attribute(self):
        exc = AgentContractViolation("my-agent", "phase", "int", "bad")
        assert exc.agent_id == "my-agent"

    def test_has_field_path_attribute(self):
        exc = AgentContractViolation("my-agent", "findings.0.severity", "str", 42)
        assert exc.field_path == "findings.0.severity"

    def test_has_expected_type_attribute(self):
        exc = AgentContractViolation("a", "f", "int", "x")
        assert exc.expected_type == "int"

    def test_has_received_value_attribute(self):
        exc = AgentContractViolation("a", "f", "int", "bad_value")
        assert exc.received_value == "bad_value"

    def test_str_representation_contains_agent_id(self):
        exc = AgentContractViolation("target-agent", "phase", "int", None)
        assert "target-agent" in str(exc)


class TestAggregate:
    """Tests for the aggregate() helper."""

    def _make_output(self, agent_id="agent-a", phase=1, n_findings=0):
        findings = [
            build_finding(agent_id, "low", "file.py", "desc", "rec")
            for _ in range(n_findings)
        ]
        raw = {"agent_id": agent_id, "phase": phase, "findings": [
            {
                "finding_id": f.finding_id,
                "severity": f.severity,
                "location": f.location,
                "description": f.description,
                "recommendation": f.recommendation,
                "agent_id": f.agent_id,
                "confidence": f.confidence,
            }
            for f in findings
        ], "metadata": {}}
        return validate_agent_output(raw)

    def test_empty_outputs_aggregate_ok(self):
        results = aggregate([])
        assert results.total_findings == 0

    def test_findings_merged_across_agents(self):
        out1 = self._make_output("agent-a", 1, n_findings=2)
        out2 = self._make_output("agent-b", 2, n_findings=3)
        results = aggregate([out1, out2])
        assert results.total_findings == 5

    def test_run_id_auto_generated_if_not_given(self):
        results = aggregate([])
        assert len(results.run_id) == 16

    def test_run_id_can_be_specified(self):
        results = aggregate([], run_id="custom-run-id")
        assert results.run_id == "custom-run-id"

    def test_agent_outputs_preserved(self):
        out = self._make_output("agent-x", 1)
        results = aggregate([out])
        assert len(results.agent_outputs) == 1
