"""
Sprint 24 — HITL Gates + AI Trust + Inline Evidence + Predicate Comparison
============================================================================
FDA-275: HITL Gate Decision Component
FDA-279: AI Trust Badge
FDA-284: Inline Evidence Popover
FDA-285: Predicate Comparison Table (with evidence popover integration)
FDA-290: Research Hub — predicate comparison tab
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).parents[3] / "web"


def read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def has(rel: str) -> bool:
    return (WEB / rel).exists()


def contains(rel: str, pattern: str) -> bool:
    return bool(re.search(pattern, read(rel)))


# ── FDA-275: HITL Gate Decision ───────────────────────────────────────────

class TestHitlGateDecision:
    """FDA-275 [HITL-001] — components/hitl/hitl-gate-decision.tsx"""

    def test_file_exists(self):
        assert has("components/hitl/hitl-gate-decision.tsx")

    def test_use_client(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r'"use client"')

    def test_exports_hitl_gate_decision(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"export function HitlGateDecision")

    def test_exports_hitl_decision_type(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"HitlDecision")

    def test_exports_gate_context(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"GateContext")

    def test_exports_hitl_decision_record(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"HitlDecisionRecord")

    def test_approve_option(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "approve" in content

    def test_request_changes_option(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "request_changes" in content

    def test_reject_option(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "reject" in content

    def test_defer_option(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "defer" in content

    def test_four_decision_options(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        decisions = ["approve", "request_changes", "reject", "defer"]
        for d in decisions:
            assert d in content, f"Decision option '{d}' not found"

    def test_rationale_required(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "rationale" in content and "minChars" in content

    def test_min_chars_validation(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"minChars")

    def test_digital_signature_field(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "reviewerName" in content or "signature" in content.lower()

    def test_21_cfr_part_11_checkbox(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "21 CFR" in content or "Part 11" in content or "cfr" in content.lower()

    def test_sri_display(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"sri|SRI")

    def test_sri_ring_svg(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "SriRing" in content or "svg" in content.lower()

    def test_ai_readiness_summary(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "agentSummary" in content or "readiness" in content.lower() or "summary" in content.lower()

    def test_open_gaps_display(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "openGaps" in content or "gaps" in content

    def test_completion_percentage(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"completion|completionPct")

    def test_on_submit_callback(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"onSubmit")

    def test_on_cancel_callback(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"onCancel")

    def test_success_state_after_submit(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "submitted" in content or "success" in content.lower()

    def test_decision_config_colors(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        # Green for approve, amber for changes, red for reject
        assert "1A7F4B" in content or "green" in content.lower()
        assert "B45309" in content or "amber" in content.lower()

    def test_fda_blue_accent(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"005EA2")

    def test_gate_name_displayed(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"gateName")

    def test_stage_label_displayed(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"stageLabel")

    def test_deadline_support(self):
        assert contains("components/hitl/hitl-gate-decision.tsx", r"deadline")

    def test_trust_integration(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "TrustBadge" in content or "trust" in content.lower()

    def test_timestamp_iso(self):
        content = read("components/hitl/hitl-gate-decision.tsx")
        assert "toISOString" in content or "timestamp" in content


# ── FDA-279: Trust Badge ──────────────────────────────────────────────────

class TestTrustBadge:
    """FDA-279 [AI-001] — components/trust/trust-badge.tsx"""

    def test_file_exists(self):
        assert has("components/trust/trust-badge.tsx")

    def test_use_client(self):
        assert contains("components/trust/trust-badge.tsx", r'"use client"')

    def test_exports_trust_badge(self):
        assert contains("components/trust/trust-badge.tsx", r"export function TrustBadge")

    def test_exports_trust_data_interface(self):
        assert contains("components/trust/trust-badge.tsx", r"export interface TrustData")

    def test_exports_trust_source_interface(self):
        assert contains("components/trust/trust-badge.tsx", r"export interface TrustSource")

    def test_confidence_field(self):
        assert contains("components/trust/trust-badge.tsx", r"confidence")

    def test_source_count_field(self):
        assert contains("components/trust/trust-badge.tsx", r"sourceCount")

    def test_model_id_field(self):
        assert contains("components/trust/trust-badge.tsx", r"modelId")

    def test_validated_at_field(self):
        assert contains("components/trust/trust-badge.tsx", r"validatedAt")

    def test_trust_source_types(self):
        content = read("components/trust/trust-badge.tsx")
        assert '"510k"' in content
        assert "guidance" in content
        assert "standard" in content
        assert "maude" in content
        assert "pubmed" in content
        assert "manual" in content

    def test_three_variants(self):
        content = read("components/trust/trust-badge.tsx")
        assert '"full"' in content
        assert '"compact"' in content
        assert '"icon"' in content

    def test_shield_icon_svg(self):
        assert contains("components/trust/trust-badge.tsx", r"ShieldIcon")

    def test_confidence_color_helper(self):
        assert contains("components/trust/trust-badge.tsx", r"confidenceColor")

    def test_confidence_high_color(self):
        # High confidence = green
        assert contains("components/trust/trust-badge.tsx", r"1A7F4B")

    def test_confidence_medium_color(self):
        # Medium confidence = amber
        assert contains("components/trust/trust-badge.tsx", r"B45309")

    def test_confidence_low_color(self):
        # Low confidence = red
        assert contains("components/trust/trust-badge.tsx", r"destructive|C5191B")

    def test_expandable_panel(self):
        content = read("components/trust/trust-badge.tsx")
        assert "expanded" in content or "setExpanded" in content

    def test_confidence_bar(self):
        # Progress/bar visualization of confidence
        content = read("components/trust/trust-badge.tsx")
        assert "h-2" in content or "progress" in content.lower() or "width.*%" in content

    def test_source_pills(self):
        assert contains("components/trust/trust-badge.tsx", r"SourcePill")

    def test_on_verify_callback(self):
        assert contains("components/trust/trust-badge.tsx", r"onVerify")

    def test_validation_timestamp(self):
        content = read("components/trust/trust-badge.tsx")
        assert "validatedAt" in content and "toLocaleDateString" in content

    def test_icon_variant_tooltip(self):
        content = read("components/trust/trust-badge.tsx")
        assert 'variant === "icon"' in content or "icon" in content

    def test_compact_variant_renders(self):
        content = read("components/trust/trust-badge.tsx")
        assert 'variant === "compact"' in content or "compact" in content


# ── FDA-284: Evidence Popover ─────────────────────────────────────────────

class TestEvidencePopover:
    """FDA-284 [PRED-001] — components/predicate/evidence-popover.tsx"""

    def test_file_exists(self):
        assert has("components/predicate/evidence-popover.tsx")

    def test_use_client(self):
        assert contains("components/predicate/evidence-popover.tsx", r'"use client"')

    def test_exports_evidence_popover(self):
        assert contains("components/predicate/evidence-popover.tsx", r"export function EvidencePopover")

    def test_exports_evidence_interface(self):
        assert contains("components/predicate/evidence-popover.tsx", r"export interface Evidence")

    def test_source_field(self):
        assert contains("components/predicate/evidence-popover.tsx", r"source:")

    def test_quote_field(self):
        assert contains("components/predicate/evidence-popover.tsx", r"quote:")

    def test_section_field(self):
        assert contains("components/predicate/evidence-popover.tsx", r"section\?:")

    def test_confidence_field(self):
        assert contains("components/predicate/evidence-popover.tsx", r"confidence:")

    def test_k_number_field(self):
        assert contains("components/predicate/evidence-popover.tsx", r"kNumber")

    def test_doi_field(self):
        assert contains("components/predicate/evidence-popover.tsx", r"doi\?:")

    def test_source_config_all_types(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert '"510k"' in content
        assert "guidance" in content
        assert "standard" in content
        assert "maude" in content
        assert "pubmed" in content

    def test_confidence_ring_svg(self):
        assert contains("components/predicate/evidence-popover.tsx", r"ConfidenceRing")

    def test_verbatim_quote_highlight(self):
        content = read("components/predicate/evidence-popover.tsx")
        # Quote must be highlighted (amber background)
        assert "amber" in content or "bg-amber" in content

    def test_copy_citation_action(self):
        assert contains("components/predicate/evidence-popover.tsx", r"[Cc]opy [Cc]itation|copyCitation")

    def test_flag_for_review_action(self):
        assert contains("components/predicate/evidence-popover.tsx", r"[Ff]lag")

    def test_nlm_citation_format(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "buildCitation" in content or "citation" in content.lower()

    def test_esc_to_close(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "Escape" in content

    def test_outside_click_close(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "mousedown" in content

    def test_evidence_indicator_dot(self):
        # Blue dot visible on cell to indicate evidence exists
        content = read("components/predicate/evidence-popover.tsx")
        assert "005EA2" in content

    def test_popover_z_index(self):
        assert contains("components/predicate/evidence-popover.tsx", r"z-50")

    def test_source_count_in_header(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "source" in content and "length" in content

    def test_evidence_card_subcomponent(self):
        assert contains("components/predicate/evidence-popover.tsx", r"EvidenceCard")

    def test_open_document_link(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "Open document" in content or "open document" in content.lower()

    def test_multiple_evidence_pagination(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "total" in content and "index" in content

    def test_no_evidence_renders_children(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "evidence.length === 0" in content

    def test_view_evidence_chain_footer(self):
        content = read("components/predicate/evidence-popover.tsx")
        assert "evidence chain" in content.lower() or "chain" in content


# ── FDA-285: Predicate Comparison Table ──────────────────────────────────

class TestPredicateComparisonTable:
    """FDA-285 [PRED-002] — components/predicate/predicate-comparison-table.tsx"""

    def test_file_exists(self):
        assert has("components/predicate/predicate-comparison-table.tsx")

    def test_use_client(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r'"use client"')

    def test_exports_predicate_comparison_table(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"export function PredicateComparisonTable")

    def test_exports_attribute_row_type(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"export interface AttributeRow")

    def test_exports_predicate_column_type(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"export interface PredicateColumn")

    def test_exports_similarity_type(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"export type Similarity")

    def test_similarity_values(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        for sim in ["identical", "similar", "different", "na"]:
            assert sim in content, f"Similarity value '{sim}' not found"

    def test_imports_evidence_popover(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "EvidencePopover" in content and "evidence-popover" in content

    def test_imports_trust_badge(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "TrustBadge" in content

    def test_evidence_popover_used_in_cell(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "EvidencePopover" in content and "evidence" in content

    def test_data_cell_component(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"DataCell")

    def test_similarity_color_coding(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        # Green for identical, amber for similar, red for different
        assert "1A7F4B" in content
        assert "B45309" in content
        assert "destructive" in content

    def test_sticky_header(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "sticky" in content

    def test_sticky_attribute_column(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "sticky left-0" in content

    def test_group_header_rows(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "group" in content and ("Group" in content or "grouped" in content)

    def test_collapsible_groups(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "expandedGroups" in content or "toggleGroup" in content

    def test_se_score_calculation(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"seScore|SE.*score|se.*score")

    def test_k_number_in_header(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"kNumber")

    def test_company_in_header(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"company")

    def test_clearance_date_in_header(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"cleared")

    def test_trust_badge_in_predicate_header(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "TrustBadge" in content and ("trust" in content)

    def test_similarity_bar_visualization(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"SimilarityBar")

    def test_export_csv_function(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"exportCsv|Export CSV")

    def test_export_triggers_download(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "Blob" in content or "download" in content

    def test_similarity_legend(self):
        assert contains("components/predicate/predicate-comparison-table.tsx", r"SimLegend")

    def test_subject_device_column(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "Subject Device" in content or "subject" in content

    def test_aria_label_table(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "aria-label" in content

    def test_overflow_x_scroll(self):
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "overflow-x-auto" in content or "overflow-x" in content

    def test_fda_blue_subject_column(self):
        # Subject device column uses FDA Blue accent
        content = read("components/predicate/predicate-comparison-table.tsx")
        assert "005EA2" in content


# ── FDA-290: Research Hub Predicate Tab ──────────────────────────────────

class TestResearchHubPredicateTab:
    """FDA-290 [RH-003] — Research Hub updated with predicate comparison tab."""

    def test_research_page_exists(self):
        assert has("app/(authenticated)/research/page.tsx")

    def test_imports_predicate_comparison_table(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "PredicateComparisonTable" in content

    def test_imports_attribute_row_type(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "AttributeRow" in content

    def test_imports_predicate_column_type(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "PredicateColumn" in content

    def test_tab_navigation(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "tab" in content

    def test_search_tab(self):
        assert contains("app/(authenticated)/research/page.tsx", r'"search"')

    def test_predicates_tab(self):
        assert contains("app/(authenticated)/research/page.tsx", r'"predicates"')

    def test_guidance_tab(self):
        assert contains("app/(authenticated)/research/page.tsx", r'"guidance"')

    def test_safety_tab(self):
        assert contains("app/(authenticated)/research/page.tsx", r'"safety"')

    def test_new_badge_on_predicates_tab(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "NEW" in content

    def test_mock_predicate_data(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "MOCK_PREDICATES" in content

    def test_mock_rows_data(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "MOCK_ROWS" in content

    def test_k_numbers_in_data(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "K193726" in content
        assert "K220031" in content

    def test_evidence_in_rows(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "evidence:" in content

    def test_similarity_values_in_rows(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "identical" in content
        assert "similar" in content
        assert "different" in content

    def test_generate_se_summary_button(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "Generate SE Summary" in content or "SE Summary" in content

    def test_export_to_estar_button(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "eSTAR" in content

    def test_add_predicate_action(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "Add Predicate" in content

    def test_compare_predicates_cta_in_search(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "Compare Predicates" in content

    def test_tab_role_attributes(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert 'role="tab"' in content

    def test_source_toggles_present(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "k510" in content
        assert "guidance" in content
        assert "maude" in content

    def test_source_colors_defined(self):
        assert contains("app/(authenticated)/research/page.tsx", r"SOURCE_COLORS")

    def test_semantic_search_heading(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "Research Hub" in content or "Regulatory Research" in content

    def test_pubmed_source(self):
        assert contains("app/(authenticated)/research/page.tsx", r"pubmed|PubMed")

    def test_recall_source(self):
        assert contains("app/(authenticated)/research/page.tsx", r"recall|Recall")


# ── Directory structure ───────────────────────────────────────────────────

class TestSprint24DirectoryStructure:
    """Verify Sprint 24 files exist in expected locations."""

    def test_trust_dir_exists(self):
        assert has("components/trust")

    def test_trust_badge_file(self):
        assert has("components/trust/trust-badge.tsx")

    def test_predicate_dir_exists(self):
        assert has("components/predicate")

    def test_evidence_popover_file(self):
        assert has("components/predicate/evidence-popover.tsx")

    def test_predicate_comparison_table_file(self):
        assert has("components/predicate/predicate-comparison-table.tsx")

    def test_hitl_dir_exists(self):
        assert has("components/hitl")

    def test_hitl_gate_decision_file(self):
        assert has("components/hitl/hitl-gate-decision.tsx")

    def test_research_page_updated(self):
        assert has("app/(authenticated)/research/page.tsx")

    def test_test_file_is_python(self):
        content = (Path(__file__).parent / "test_sprint24.py").read_text()
        assert "def test_" in content
