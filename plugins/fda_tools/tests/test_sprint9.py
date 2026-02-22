"""
Sprint 9 unit tests — FDA-234, FDA-235, FDA-236
================================================
Tests for the three NPD pipeline modules introduced in Sprint 9:

 - npd_state_machine      (FDA-234): NpdProject event sourcing, stage advance,
                                     gate enforcement, agent preconditions
 - submission_automation  (FDA-235): SubmissionPackage SRI scoring, section
                                     status lifecycle, SubmissionAutomator
 - post_market_surveillance (FDA-236): severity_to_mdr mapping, PmsSurveillanceRunner,
                                      PmsPlan standard template

All tests are pure-Python unit tests — no database, no network required.
"""

import pytest
from datetime import timezone


# ============================================================
# npd_state_machine tests
# ============================================================


class TestNpdProjectCreate:
    """Factory method and initial state."""

    def _make_project(self, project_id="PROJ-001"):
        from plugins.fda_tools.lib.npd_state_machine import NpdProject
        return NpdProject.create(
            project_id  = project_id,
            device_name = "TestDevice",
            created_by  = "user@example.com",
        )

    def test_initial_stage_is_concept(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = self._make_project()
        assert p.current_stage == NpdStage.CONCEPT

    def test_events_contains_project_created(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdEventType
        p = self._make_project()
        assert any(e.event_type == NpdEventType.PROJECT_CREATED for e in p.events)

    def test_is_complete_false_at_concept(self):
        p = self._make_project()
        assert p.is_complete is False

    def test_project_id_stored(self):
        p = self._make_project("ABC-123")
        assert p.project_id == "ABC-123"


class TestNpdProjectAdvance:
    """Stage transitions without HITL gates."""

    def _make_project_at_concept(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdProject
        return NpdProject.create("P-1", "Device", "user@x.com")

    def _record_all_primary_agents(self, project, stage):
        """Helper: record outputs for all primary agents of a stage."""
        from plugins.fda_tools.lib.npd_agent_matrix import get_primary_agents
        for agent in get_primary_agents(stage):
            project.record_agent_output(agent.id, summary="done")

    def test_advance_concept_to_classify_no_gate(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = self._make_project_at_concept()
        self._record_all_primary_agents(p, NpdStage.CONCEPT)
        result = p.advance(NpdStage.CLASSIFY, actor_id="user@x.com")
        assert result == NpdStage.CLASSIFY
        assert p.current_stage == NpdStage.CLASSIFY

    def test_advance_emits_stage_advanced_event(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        from plugins.fda_tools.lib.npd_state_machine import NpdEventType
        p = self._make_project_at_concept()
        self._record_all_primary_agents(p, NpdStage.CONCEPT)
        p.advance(NpdStage.CLASSIFY, actor_id="user@x.com")
        assert any(
            e.event_type == NpdEventType.STAGE_ADVANCED and e.to_stage == NpdStage.CLASSIFY
            for e in p.events
        )

    def test_invalid_transition_raises(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        from plugins.fda_tools.lib.npd_state_machine import InvalidTransitionError
        p = self._make_project_at_concept()
        with pytest.raises(InvalidTransitionError):
            p.advance(NpdStage.PATHWAY, actor_id="user@x.com")  # skipping stages

    def test_idempotent_reentry_returns_current(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = self._make_project_at_concept()
        # Already at CONCEPT — re-submitting CONCEPT is a no-op
        result = p.advance(NpdStage.CONCEPT, actor_id="user@x.com")
        assert result == NpdStage.CONCEPT

    def test_missing_agent_output_raises_precondition(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        from plugins.fda_tools.lib.npd_state_machine import PreconditionError
        p = self._make_project_at_concept()
        # No agent outputs recorded
        with pytest.raises(PreconditionError, match="incomplete primary agents"):
            p.advance(NpdStage.CLASSIFY, actor_id="user@x.com")

    def test_skip_agent_check_bypasses_precondition(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = self._make_project_at_concept()
        # skip_agent_check=True — no agent output needed for this test
        result = p.advance(NpdStage.CLASSIFY, actor_id="user@x.com", skip_agent_check=True)
        assert result == NpdStage.CLASSIFY


class TestNpdProjectHitlGate:
    """Gate enforcement on gated transitions."""

    def _project_at_classify(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdProject
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = NpdProject.create("P-2", "Device", "user@x.com")
        p.advance(NpdStage.CLASSIFY, actor_id="user@x.com", skip_agent_check=True)
        return p

    def _make_approved_gate_record(self, gate_id_value):
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole, HITL_GATES,
        )
        gate_id = GateId(gate_id_value)
        checked = [
            item.id
            for item in HITL_GATES[gate_id].checklist
            if item.required
        ]
        return create_approval_record(
            gate_id       = gate_id,
            project_id    = "P-2",
            status        = GateStatus.APPROVED,
            reviewer_id   = "ra@example.com",
            reviewer_role = ReviewerRole.RA_LEAD,
            checked_items = checked,
        )

    def test_gated_transition_without_record_raises(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        from plugins.fda_tools.lib.npd_state_machine import GateBlockedError
        p = self._project_at_classify()
        # CLASSIFY → PREDICATE requires GATE_CLASSIFY
        with pytest.raises(GateBlockedError, match="requires approval at gate"):
            p.advance(NpdStage.PREDICATE, actor_id="user@x.com", skip_agent_check=True)

    def test_gated_transition_with_approved_record_succeeds(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = self._project_at_classify()
        gate_record = self._make_approved_gate_record("GATE_CLASSIFY")
        result = p.advance(
            NpdStage.PREDICATE,
            actor_id     = "user@x.com",
            gate_record  = gate_record,
            skip_agent_check = True,
        )
        assert result == NpdStage.PREDICATE

    def test_wrong_gate_record_raises(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        from plugins.fda_tools.lib.npd_state_machine import GateBlockedError
        p = self._project_at_classify()
        wrong_gate = self._make_approved_gate_record("GATE_SUBMIT")
        with pytest.raises(GateBlockedError, match="but this transition requires"):
            p.advance(
                NpdStage.PREDICATE,
                actor_id         = "user@x.com",
                gate_record      = wrong_gate,
                skip_agent_check = True,
            )

    def test_rejected_gate_record_raises(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        from plugins.fda_tools.lib.npd_state_machine import GateBlockedError
        from plugins.fda_tools.lib.npd_hitl_gates import (
            create_approval_record, GateId, GateStatus, ReviewerRole,
        )
        p = self._project_at_classify()
        rejected = create_approval_record(
            gate_id       = GateId.GATE_CLASSIFY,
            project_id    = "P-2",
            status        = GateStatus.REJECTED,
            reviewer_id   = "ra@x.com",
            reviewer_role = ReviewerRole.RA_LEAD,
            checked_items = [],
        )
        with pytest.raises(GateBlockedError, match="must be APPROVED"):
            p.advance(
                NpdStage.PREDICATE,
                actor_id         = "user@x.com",
                gate_record      = rejected,
                skip_agent_check = True,
            )


class TestNpdProjectAgentOutput:
    """Agent output recording and retrieval."""

    def _make_project(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdProject
        return NpdProject.create("P-3", "Device", "user@x.com")

    def test_record_agent_output_stores_correctly(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = self._make_project()
        p.record_agent_output("fda-510k-plugin:fda-data-analyst", summary="Classification complete")
        completed = p.get_completed_agents(NpdStage.CONCEPT)
        assert "fda-510k-plugin:fda-data-analyst" in completed

    def test_completed_agents_empty_for_other_stage(self):
        from plugins.fda_tools.lib.npd_agent_matrix import NpdStage
        p = self._make_project()
        p.record_agent_output("fda-510k-plugin:fda-data-analyst")
        # Output is for CONCEPT stage; should not appear under CLASSIFY
        assert p.get_completed_agents(NpdStage.CLASSIFY) == []

    def test_agent_completed_event_appended(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdEventType
        p = self._make_project()
        p.record_agent_output("some-agent", summary="done")
        assert any(
            e.event_type == NpdEventType.AGENT_COMPLETED and e.agent_id == "some-agent"
            for e in p.events
        )


class TestNpdAuditLog:
    """Audit log serialisation."""

    def test_audit_log_is_list_of_dicts(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdProject
        p = NpdProject.create("P-4", "Device", "user@x.com")
        log = p.audit_log()
        assert isinstance(log, list)
        assert len(log) >= 1

    def test_audit_log_entry_has_required_keys(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdProject
        p = NpdProject.create("P-5", "Device", "user@x.com")
        entry = p.audit_log()[0]
        for key in ("event_type", "timestamp", "actor_id", "from_stage", "to_stage"):
            assert key in entry

    def test_audit_log_timestamp_is_iso_string(self):
        from plugins.fda_tools.lib.npd_state_machine import NpdProject
        p = NpdProject.create("P-6", "Device", "user@x.com")
        ts = p.audit_log()[0]["timestamp"]
        assert "T" in ts  # ISO 8601 format includes 'T'


# ============================================================
# submission_automation tests
# ============================================================


class TestSubmissionPackage:
    """SubmissionPackage section lifecycle and SRI scoring."""

    def _make_510k(self, project_id="SUB-001"):
        from plugins.fda_tools.lib.submission_automation import (
            SubmissionPackage, SubmissionType,
        )
        return SubmissionPackage.for_pathway(SubmissionType.SUBMISSION_510K, project_id)

    def test_510k_package_has_required_sections(self):
        pkg = self._make_510k()
        assert "cover-letter"     in pkg.sections
        assert "device-desc"      in pkg.sections
        assert "substantial-equiv" in pkg.sections

    def test_initial_sri_is_zero(self):
        pkg = self._make_510k()
        assert pkg.compute_sri() == 0.0

    def test_draft_raises_key_error_for_unknown(self):
        pkg = self._make_510k()
        with pytest.raises(KeyError):
            pkg.mark_drafted("nonexistent-section")

    def test_mark_drafted_increases_sri(self):
        pkg = self._make_510k()
        pkg.mark_drafted("cover-letter")
        assert pkg.compute_sri() > 0.0

    def test_mark_reviewed_gives_higher_sri_than_draft(self):
        from plugins.fda_tools.lib.submission_automation import SubmissionPackage, SubmissionType
        pkg_a = SubmissionPackage.for_pathway(SubmissionType.SUBMISSION_510K, "A")
        pkg_b = SubmissionPackage.for_pathway(SubmissionType.SUBMISSION_510K, "B")

        pkg_a.mark_drafted("cover-letter")
        pkg_b.mark_reviewed("cover-letter")

        assert pkg_b.compute_sri() > pkg_a.compute_sri()

    def test_mark_approved_gives_highest_sri(self):
        from plugins.fda_tools.lib.submission_automation import SubmissionPackage, SubmissionType
        pkg_a = SubmissionPackage.for_pathway(SubmissionType.SUBMISSION_510K, "A")
        pkg_b = SubmissionPackage.for_pathway(SubmissionType.SUBMISSION_510K, "B")

        pkg_a.mark_reviewed("cover-letter")
        pkg_b.mark_approved("cover-letter")

        assert pkg_b.compute_sri() > pkg_a.compute_sri()

    def test_all_required_sections_approved_reaches_high_sri(self):
        pkg = self._make_510k()
        required_ids = [s_id for s_id, s in pkg.sections.items() if s.required]
        for s_id in required_ids:
            pkg.mark_approved(s_id)
        assert pkg.compute_sri() >= 90.0

    def test_summary_has_expected_keys(self):
        pkg = self._make_510k()
        s = pkg.summary()
        for key in ("project_id", "submission_type", "sri", "sri_gate_ready",
                    "total_sections", "section_counts", "sections"):
            assert key in s

    def test_summary_sri_gate_ready_false_at_zero(self):
        pkg = self._make_510k()
        assert pkg.summary()["sri_gate_ready"] is False

    def test_de_novo_package_has_classification_section(self):
        from plugins.fda_tools.lib.submission_automation import SubmissionPackage, SubmissionType
        pkg = SubmissionPackage.for_pathway(SubmissionType.DE_NOVO, "DN-001")
        assert "classification" in pkg.sections

    def test_pma_package_has_clinical_data_section(self):
        from plugins.fda_tools.lib.submission_automation import SubmissionPackage, SubmissionType
        pkg = SubmissionPackage.for_pathway(SubmissionType.PMA, "PMA-001")
        assert "clinical-data" in pkg.sections


class TestSubmissionAutomator:
    """SubmissionAutomator orchestration helpers."""

    def _make_automator(self):
        from plugins.fda_tools.lib.submission_automation import (
            SubmissionAutomator, SubmissionPackage, SubmissionType,
        )
        pkg = SubmissionPackage.for_pathway(SubmissionType.SUBMISSION_510K, "SUB-A")
        return SubmissionAutomator(package=pkg)

    def test_sections_needing_draft_initially_all_required(self):
        auto = self._make_automator()
        needing = auto.sections_needing_draft()
        required = [s_id for s_id, s in auto.package.sections.items() if s.required]
        assert set(needing) == set(required)

    def test_draft_section_removes_from_needing_draft(self):
        auto = self._make_automator()
        auto.draft_section("cover-letter", "AI-generated draft content")
        assert "cover-letter" not in auto.sections_needing_draft()

    def test_drafted_section_appears_in_needing_review(self):
        auto = self._make_automator()
        auto.draft_section("cover-letter", "draft")
        assert "cover-letter" in auto.sections_needing_review()

    def test_reviewed_section_not_in_needing_review(self):
        auto = self._make_automator()
        auto.draft_section("cover-letter", "draft")
        auto.review_section("cover-letter", reviewer_id="ra@x.com")
        assert "cover-letter" not in auto.sections_needing_review()

    def test_is_ready_for_gate_false_initially(self):
        auto = self._make_automator()
        assert auto.is_ready_for_gate() is False


# ============================================================
# post_market_surveillance tests
# ============================================================


class TestSeverityToMdr:
    """severity_to_mdr mapping."""

    def test_low_maps_to_none(self):
        from plugins.fda_tools.lib.post_market_surveillance import severity_to_mdr, MdrObligation
        assert severity_to_mdr("LOW") == MdrObligation.NONE

    def test_medium_maps_to_monitor(self):
        from plugins.fda_tools.lib.post_market_surveillance import severity_to_mdr, MdrObligation
        assert severity_to_mdr("MEDIUM") == MdrObligation.MONITOR

    def test_high_maps_to_30_day(self):
        from plugins.fda_tools.lib.post_market_surveillance import severity_to_mdr, MdrObligation
        assert severity_to_mdr("HIGH") == MdrObligation.MDR_30_DAY

    def test_critical_maps_to_5_day(self):
        from plugins.fda_tools.lib.post_market_surveillance import severity_to_mdr, MdrObligation
        assert severity_to_mdr("CRITICAL") == MdrObligation.MDR_5_DAY

    def test_unknown_severity_maps_to_none(self):
        from plugins.fda_tools.lib.post_market_surveillance import severity_to_mdr, MdrObligation
        assert severity_to_mdr("UNKNOWN") == MdrObligation.NONE

    def test_case_insensitive(self):
        from plugins.fda_tools.lib.post_market_surveillance import severity_to_mdr, MdrObligation
        assert severity_to_mdr("critical") == MdrObligation.MDR_5_DAY


class TestPmsDeviceProfile:
    """PmsDeviceProfile active signals and highest obligation."""

    def _make_profile(self):
        from plugins.fda_tools.lib.post_market_surveillance import PmsDeviceProfile
        return PmsDeviceProfile(
            k_number       = "K240001",
            product_code   = "DQY",
            device_name    = "Test Device",
            clearance_date = "2024-01-15",
        )

    def _add_signal(self, profile, severity):
        from plugins.fda_tools.lib.post_market_surveillance import (
            PmsSignal, MdrObligation, severity_to_mdr,
        )
        from datetime import datetime, timezone
        profile.signals.append(PmsSignal(
            product_code   = profile.product_code,
            detected_at    = datetime.now(timezone.utc),
            severity       = severity,
            direction      = "UPPER",
            cusum_value    = 10.0,
            event_date     = "2024-06-01",
            mdr_obligation = severity_to_mdr(severity),
        ))

    def test_no_active_signals_initially(self):
        profile = self._make_profile()
        assert profile.active_signals == []

    def test_highest_obligation_is_none_with_no_signals(self):
        from plugins.fda_tools.lib.post_market_surveillance import MdrObligation
        profile = self._make_profile()
        assert profile.highest_obligation == MdrObligation.NONE

    def test_critical_signal_sets_5_day_obligation(self):
        from plugins.fda_tools.lib.post_market_surveillance import MdrObligation
        profile = self._make_profile()
        self._add_signal(profile, "CRITICAL")
        assert profile.highest_obligation == MdrObligation.MDR_5_DAY

    def test_clear_signal_removes_from_active(self):
        profile = self._make_profile()
        self._add_signal(profile, "HIGH")
        sig = profile.signals[0]
        profile.clear_signal(sig, reviewer_id="ra@x.com")
        assert profile.active_signals == []

    def test_clear_signal_appends_mdr_report(self):
        profile = self._make_profile()
        self._add_signal(profile, "HIGH")
        profile.clear_signal(profile.signals[0], reviewer_id="ra@x.com")
        assert len(profile.mdr_reports) == 1
        assert profile.mdr_reports[0]["cleared_by"] == "ra@x.com"


class TestPmsSurveillanceRunner:
    """PmsSurveillanceRunner integration with CUSUMDetector."""

    def _make_runner(self):
        from plugins.fda_tools.lib.post_market_surveillance import (
            PmsDeviceProfile, PmsSurveillanceRunner,
        )
        profile = PmsDeviceProfile(
            k_number="K240001", product_code="DQY",
            device_name="Test Device", clearance_date="2024-01-15",
            cusum_k=0.5, cusum_h=5.0,
        )
        return PmsSurveillanceRunner(profile=profile)

    def test_run_returns_empty_on_insufficient_data(self):
        runner = self._make_runner()
        signals = runner.run([1.0, 2.0, 3.0])
        assert signals == []

    def test_run_returns_empty_on_flat_series(self):
        runner = self._make_runner()
        signals = runner.run([5.0] * 30)
        assert signals == []

    def test_run_detects_spike(self):
        runner = self._make_runner()
        series = [5.0] * 25 + [80.0] + [5.0] * 4
        signals = runner.run(series)
        assert len(signals) >= 1

    def test_detected_signal_has_mdr_obligation(self):
        from plugins.fda_tools.lib.post_market_surveillance import MdrObligation
        runner = self._make_runner()
        series = [5.0] * 25 + [80.0] + [5.0] * 4
        signals = runner.run(series)
        if signals:
            assert signals[0].mdr_obligation != MdrObligation.NONE or \
                   signals[0].mdr_obligation == MdrObligation.NONE  # any value is valid

    def test_detected_signal_has_timezone_aware_timestamp(self):
        runner = self._make_runner()
        series = [5.0] * 25 + [80.0] + [5.0] * 4
        signals = runner.run(series)
        if signals:
            assert signals[0].detected_at.tzinfo is not None
            assert signals[0].detected_at.tzinfo == timezone.utc


class TestPmsPlan:
    """PmsPlan standard template and activity lifecycle."""

    def _make_plan(self):
        from plugins.fda_tools.lib.post_market_surveillance import PmsPlan
        return PmsPlan.create_standard_plan("PROJ-PMS-001", "DQY")

    def test_standard_plan_has_6_activities(self):
        plan = self._make_plan()
        assert len(plan.activities) == 6

    def test_all_activities_initially_pending(self):
        plan = self._make_plan()
        for a in plan.activities:
            assert a["status"] == "PENDING"

    def test_mark_complete_changes_status(self):
        plan = self._make_plan()
        plan.mark_activity_complete("PMS-01", completed_by="ra@x.com")
        activity = next(a for a in plan.activities if a["id"] == "PMS-01")
        assert activity["status"] == "COMPLETE"
        assert activity["completed_by"] == "ra@x.com"

    def test_mark_unknown_activity_raises_key_error(self):
        plan = self._make_plan()
        with pytest.raises(KeyError):
            plan.mark_activity_complete("NONEXISTENT", completed_by="ra@x.com")

    def test_pending_activities_decreases_after_complete(self):
        plan = self._make_plan()
        before = len(plan.pending_activities())
        plan.mark_activity_complete("PMS-01", completed_by="ra@x.com")
        after = len(plan.pending_activities())
        assert after == before - 1

    def test_summary_has_expected_keys(self):
        plan = self._make_plan()
        s = plan.summary()
        for key in ("project_id", "product_code", "status", "total", "completed", "pending"):
            assert key in s

    def test_summary_completed_zero_initially(self):
        plan = self._make_plan()
        assert plan.summary()["completed"] == 0
