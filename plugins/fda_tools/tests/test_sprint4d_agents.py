"""Sprint 4D Tests — Agent Enhancements

Tests for:
- C-08: Predicate legal status verification (review.md, propose.md, lineage.md)
- C-10: Pre-Sub Planner new command orchestration
- H-04: Labeling Reviewer specialist template in review-simulator
- H-05: Q-Sub type differentiation in presub-planner and presub
- M-03: Progress checkpoints in all 7 agents
- M-10: 3-tier guidance trigger reference in review-simulator
- M-12: Commands You Orchestrate table in submission-writer
"""

import os
import re
import pytest

# Paths
PLUGIN_ROOT = os.path.join(os.path.dirname(__file__), '..')
COMMANDS_DIR = os.path.join(PLUGIN_ROOT, 'commands')
AGENTS_DIR = os.path.join(PLUGIN_ROOT, 'agents')


# ===== C-08: Predicate Legal Status Verification =====

class TestPredicateLegalStatusReview:
    """review.md must have enforcement/withdrawal checking."""

    @pytest.fixture
    def review_content(self):
        with open(os.path.join(COMMANDS_DIR, 'review.md')) as f:
            return f.read()

    def test_withdrawn_flag_defined(self, review_content):
        """WITHDRAWN flag must be in risk flags table."""
        assert "WITHDRAWN" in review_content

    def test_enforcement_action_flag_defined(self, review_content):
        """ENFORCEMENT_ACTION flag must be in risk flags table."""
        assert "ENFORCEMENT_ACTION" in review_content

    def test_enforcement_api_query(self, review_content):
        """Must query device/enforcement API endpoint."""
        assert "device/enforcement" in review_content or "enforcement" in review_content

    def test_legal_status_step_exists(self, review_content):
        """Must have a predicate legal status verification step."""
        assert "Predicate Legal Status Verification" in review_content

    def test_legally_unmarketable_warning(self, review_content):
        """Must warn that withdrawn predicates cannot serve as valid predicates."""
        assert "not legally marketed" in review_content.lower() or "legally unmarketable" in review_content.lower()


class TestPredicateLegalStatusPropose:
    """propose.md must have enforcement/withdrawal checking."""

    @pytest.fixture
    def propose_content(self):
        with open(os.path.join(COMMANDS_DIR, 'propose.md')) as f:
            return f.read()

    def test_enforcement_check_present(self, propose_content):
        """propose.md must have enforcement/withdrawal check."""
        assert "enforcement" in propose_content.lower()
        assert "device/enforcement.json" in propose_content

    def test_withdrawn_flag(self, propose_content):
        """propose.md must flag WITHDRAWN predicates."""
        assert "WITHDRAWN" in propose_content

    def test_enforcement_action_flag(self, propose_content):
        """propose.md must flag ENFORCEMENT_ACTION."""
        assert "ENFORCEMENT_ACTION" in propose_content


class TestPredicateLegalStatusLineage:
    """lineage.md must account for withdrawn ancestors."""

    @pytest.fixture
    def lineage_content(self):
        with open(os.path.join(COMMANDS_DIR, 'lineage.md')) as f:
            return f.read()

    def test_withdrawn_in_chain_health(self, lineage_content):
        """Chain health scoring must penalize withdrawn ancestors."""
        assert "withdrawn" in lineage_content.lower()


# ===== C-10: Pre-Sub Planner Command Orchestration =====

class TestPresubPlannerOrchestration:
    """presub-planner.md must orchestrate new v5.8+ commands."""

    @pytest.fixture
    def planner_content(self):
        with open(os.path.join(AGENTS_DIR, 'presub-planner.md')) as f:
            return f.read()

    def test_trials_command_in_table(self, planner_content):
        """/fda:trials must be in Commands You Orchestrate table."""
        assert "/fda:trials" in planner_content

    def test_warnings_command_in_table(self, planner_content):
        """/fda:warnings must be in Commands You Orchestrate table."""
        assert "/fda:warnings" in planner_content

    def test_inspections_command_in_table(self, planner_content):
        """/fda:inspections must be in Commands You Orchestrate table."""
        assert "/fda:inspections" in planner_content

    def test_inspection_step_exists(self, planner_content):
        """Must have inspection history step in workflow."""
        assert "Inspection history" in planner_content

    def test_warning_letter_step_exists(self, planner_content):
        """Must have warning letters step in workflow."""
        assert "Warning letters" in planner_content or "warning letters" in planner_content

    def test_clinical_trials_step_exists(self, planner_content):
        """Must have clinical trials step in workflow."""
        assert "Clinical trials" in planner_content or "clinical trials" in planner_content


# ===== H-04: Labeling Reviewer Specialist Template =====

class TestLabelingReviewerTemplate:
    """review-simulator.md must have expanded Labeling Reviewer template."""

    @pytest.fixture
    def simulator_content(self):
        with open(os.path.join(AGENTS_DIR, 'review-simulator.md')) as f:
            return f.read()

    def test_labeling_reviewer_section_exists(self, simulator_content):
        """Must have Labeling Reviewer Evaluation section."""
        assert "Labeling Reviewer Evaluation" in simulator_content

    def test_cfr_801_reference(self, simulator_content):
        """Must reference 21 CFR 801."""
        assert "21 CFR 801" in simulator_content

    def test_ifu_content_check(self, simulator_content):
        """Must check IFU content completeness."""
        assert "Indications for use" in simulator_content

    def test_format_compliance_section(self, simulator_content):
        """Must have format compliance section."""
        assert "Format Compliance" in simulator_content

    def test_cfr_801_6_reference(self, simulator_content):
        """Must reference 21 CFR 801.6 (adequate directions)."""
        assert "801.6" in simulator_content

    def test_cfr_801_109_reference(self, simulator_content):
        """Must reference 21 CFR 801.109 (prescription device)."""
        assert "801.109" in simulator_content

    def test_udi_label_check(self, simulator_content):
        """Must check UDI presence on label."""
        assert "UDI" in simulator_content or "Unique Device Identifier" in simulator_content

    def test_consistency_checks_in_labeling(self, simulator_content):
        """Must have labeling consistency checks."""
        assert "IFU text identical" in simulator_content or "Consistency Checks" in simulator_content

    def test_scoring_rubric(self, simulator_content):
        """Must have scoring rubric for labeling."""
        assert "labeling items addressed" in simulator_content


# ===== H-05: Q-Sub Type Differentiation =====

class TestQSubTypePresubPlanner:
    """presub-planner.md must differentiate Q-Sub types."""

    @pytest.fixture
    def planner_content(self):
        with open(os.path.join(AGENTS_DIR, 'presub-planner.md')) as f:
            return f.read()

    def test_qsub_type_table(self, planner_content):
        """Must have Q-Sub type recommendation table."""
        assert "Q-Sub" in planner_content
        assert "Formal Meeting" in planner_content

    def test_written_feedback_type(self, planner_content):
        """Must include Written Feedback Only type."""
        assert "Written Feedback Only" in planner_content

    def test_information_type(self, planner_content):
        """Must include Q-Sub Information type."""
        assert "Information" in planner_content

    def test_pre_ide_type(self, planner_content):
        """Must include Pre-IDE type."""
        assert "Pre-IDE" in planner_content

    def test_decision_logic(self, planner_content):
        """Must have decision logic for Q-Sub type selection."""
        assert "Decision Logic" in planner_content


class TestQSubTypePresub:
    """presub.md must support --qsub-type flag."""

    @pytest.fixture
    def presub_content(self):
        with open(os.path.join(COMMANDS_DIR, 'presub.md')) as f:
            return f.read()

    def test_qsub_type_flag(self, presub_content):
        """Must support --qsub-type argument."""
        assert "--qsub-type" in presub_content

    def test_qsub_type_options(self, presub_content):
        """Must list Q-Sub type options."""
        assert "formal" in presub_content
        assert "written" in presub_content

    def test_auto_detect_logic(self, presub_content):
        """Must have Q-Sub type auto-detection logic."""
        assert "auto-detect" in presub_content.lower() or "Determine Q-Sub Type" in presub_content


# ===== M-03: Progress Checkpoints in All Agents =====

class TestProgressCheckpoints:
    """All 7 agents must have Progress Reporting section."""

    AGENTS = [
        'extraction-analyzer.md',
        'submission-writer.md',
        'presub-planner.md',
        'review-simulator.md',
        'research-intelligence.md',
        'submission-assembler.md',
        'data-pipeline-manager.md',
    ]

    @pytest.fixture(params=AGENTS)
    def agent_content(self, request):
        path = os.path.join(AGENTS_DIR, request.param)
        with open(path) as f:
            return f.read(), request.param

    def test_progress_reporting_section(self, agent_content):
        """Each agent must have a Progress Reporting section."""
        content, name = agent_content
        assert "## Progress Reporting" in content, \
            f"Agent {name} missing ## Progress Reporting section"

    def test_checkpoint_format(self, agent_content):
        """Each agent must have numbered checkpoint format."""
        content, name = agent_content
        assert re.search(r'\[1/', content), \
            f"Agent {name} missing numbered checkpoint format [1/N]"


# ===== M-10: 3-Tier Guidance Trigger Reference =====

class TestGuidanceTriggerReference:
    """review-simulator.md must reference 3-tier guidance trigger system."""

    @pytest.fixture
    def simulator_content(self):
        with open(os.path.join(AGENTS_DIR, 'review-simulator.md')) as f:
            return f.read()

    def test_three_tier_reference(self, simulator_content):
        """Must reference 3-tier guidance trigger system."""
        assert "3-tier" in simulator_content

    def test_tier_1_api_flags(self, simulator_content):
        """Must mention Tier 1 API flags."""
        assert "Tier 1" in simulator_content or "API Flags" in simulator_content

    def test_tier_2_keyword_matching(self, simulator_content):
        """Must mention Tier 2 keyword matching."""
        assert "Tier 2" in simulator_content or "Keyword" in simulator_content

    def test_tier_3_heuristics(self, simulator_content):
        """Must mention Tier 3 heuristics."""
        assert "Tier 3" in simulator_content or "Heuristic" in simulator_content

    def test_guidance_lookup_reference(self, simulator_content):
        """Must reference guidance-lookup.md."""
        assert "guidance-lookup.md" in simulator_content


# ===== M-12: Submission Writer Orchestration Table =====

class TestSubmissionWriterOrchestration:
    """submission-writer.md must have Commands You Orchestrate table."""

    @pytest.fixture
    def writer_content(self):
        with open(os.path.join(AGENTS_DIR, 'submission-writer.md')) as f:
            return f.read()

    def test_orchestration_table_exists(self, writer_content):
        """Must have Commands You Orchestrate section."""
        assert "## Commands You Orchestrate" in writer_content

    def test_draft_command_listed(self, writer_content):
        """/fda:draft must be in orchestration table."""
        assert "/fda:draft" in writer_content

    def test_compare_se_listed(self, writer_content):
        """/fda:compare-se must be in orchestration table."""
        assert "/fda:compare-se" in writer_content

    def test_consistency_listed(self, writer_content):
        """/fda:consistency must be in orchestration table."""
        assert "/fda:consistency" in writer_content

    def test_references_section(self, writer_content):
        """Must have References section with key reference files."""
        assert "draft-templates.md" in writer_content
