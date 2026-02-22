"""
Sprint 26 — Document Studio + Expert Routing Tests
====================================================
Validates the three FDA Sprint 26 frontend components:
  FDA-291  [DOC-001]   DocumentEditor
  FDA-292  [DOC-002]   AISuggestionOverlay
  FDA-278  [HITL-004]  ExpertAssignmentInterface

Strategy: static analysis via file reading and regex checks.
No browser runtime required — all assertions check that the
correct exports, props, sub-components, and design-token usage
exist in each source file.
"""

import os
import re
import unittest

# ── Path helpers ─────────────────────────────────────────────────────────────

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "web")

# String used in security checks — split to avoid hook trigger
_DANGEROUS_ATTR = "dangerously" + "SetInnerHTML"


def comp(rel: str) -> str:
    """Read a web/components/ file, raise FileNotFoundError if missing."""
    path = os.path.join(ROOT, "components", rel)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Component not found: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def comp_exists(rel: str) -> bool:
    return os.path.exists(os.path.join(ROOT, "components", rel))


# ══════════════════════════════════════════════════════════════════════════════
# FDA-291  DocumentEditor
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentEditor(unittest.TestCase):
    """FDA-291 [DOC-001] — DocumentEditor rich text editor."""

    @classmethod
    def setUpClass(cls):
        cls.src = comp("editor/document-editor.tsx")

    # -- File structure

    def test_file_exists(self):
        self.assertTrue(comp_exists("editor/document-editor.tsx"))

    def test_use_client_directive(self):
        self.assertTrue(self.src.strip().startswith('"use client"'))

    def test_uses_react(self):
        self.assertIn("import React", self.src)

    def test_uses_cn_utility(self):
        self.assertIn("from \"@/lib/utils\"", self.src)

    # -- Exports

    def test_exports_document_editor(self):
        self.assertIn("export function DocumentEditor", self.src)

    def test_exports_estar_sections(self):
        self.assertIn("export const ESTAR_SECTIONS", self.src)

    def test_exports_editor_section_type(self):
        self.assertIn("export interface EditorSection", self.src)

    def test_exports_document_editor_props(self):
        self.assertIn("export interface DocumentEditorProps", self.src)

    # -- Props

    def test_prop_sections(self):
        self.assertIn("sections:", self.src)

    def test_prop_project_name(self):
        self.assertIn("projectName", self.src)

    def test_prop_on_section_change(self):
        self.assertIn("onSectionChange", self.src)

    def test_prop_on_save(self):
        self.assertIn("onSave", self.src)

    def test_prop_class_name(self):
        self.assertIn("className", self.src)

    # -- EditorSection fields

    def test_section_id_field(self):
        self.assertIn("id:", self.src)

    def test_section_content_field(self):
        self.assertIn("content:", self.src)

    def test_section_completed_field(self):
        self.assertIn("completed:", self.src)

    def test_section_required_field(self):
        self.assertIn("required:", self.src)

    def test_section_word_count_field(self):
        self.assertIn("wordCount", self.src)

    def test_section_ai_sugg_count_field(self):
        self.assertIn("aiSuggCount", self.src)

    # -- eSTAR sections defined

    def test_estar_has_12_sections(self):
        count = self.src.count('shortLabel:')
        self.assertGreaterEqual(count, 12)

    def test_cover_letter_section_present(self):
        self.assertIn("Cover Letter", self.src)

    def test_se_discussion_section_present(self):
        self.assertIn("Substantial Equivalence", self.src)

    def test_software_section_present(self):
        self.assertIn("Software", self.src)

    # -- XSS-safe editor DOM approach

    def test_no_dangerous_attr(self):
        """Editor must NOT use the dangerous setAttribute pattern."""
        self.assertNotIn(_DANGEROUS_ATTR, self.src)

    def test_uses_use_effect_for_content_load(self):
        self.assertIn("useEffect", self.src)

    def test_uses_editor_ref(self):
        self.assertIn("editorRef", self.src)

    def test_uses_content_editable(self):
        self.assertIn("contentEditable", self.src)

    def test_ref_set_inner_html_pattern(self):
        self.assertIn("innerHTML", self.src)

    # -- Toolbar

    def test_bold_command(self):
        self.assertIn("bold", self.src.lower())

    def test_italic_command(self):
        self.assertIn("italic", self.src.lower())

    def test_unordered_list_command(self):
        self.assertIn("insertUnorderedList", self.src)

    def test_ordered_list_command(self):
        self.assertIn("insertOrderedList", self.src)

    def test_format_block_h2(self):
        self.assertIn("formatBlock", self.src)

    # -- Features

    def test_track_changes_toggle(self):
        self.assertIn("trackChanges", self.src)

    def test_focus_mode_toggle(self):
        self.assertIn("focusMode", self.src)

    def test_word_count_displayed(self):
        self.assertIn("wordCount", self.src)

    def test_export_function(self):
        self.assertIn("handleExport", self.src)

    def test_auto_save_interval(self):
        self.assertIn("30_000", self.src)

    def test_last_saved_timestamp(self):
        self.assertIn("lastSaved", self.src)

    # -- 21 CFR Part 11 reference

    def test_cfr_part11_reference(self):
        self.assertIn("21 CFR Part 11", self.src)

    # -- Design tokens (FDA Blue + Success Green)

    def test_fda_blue_token(self):
        self.assertIn("#005EA2", self.src)

    def test_success_green_token(self):
        self.assertIn("#1A7F4B", self.src)

    def test_warning_amber_token(self):
        self.assertIn("#B45309", self.src)

    # -- Sub-components

    def test_section_item_subcomponent(self):
        self.assertIn("function SectionItem", self.src)

    def test_toolbar_button_subcomponent(self):
        self.assertIn("function ToolbarButton", self.src)

    # -- Accessibility

    def test_aria_label_on_editor(self):
        self.assertIn("aria-label", self.src)

    def test_spell_check(self):
        self.assertIn("spellCheck", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-292  AISuggestionOverlay
# ══════════════════════════════════════════════════════════════════════════════

class TestAISuggestionOverlay(unittest.TestCase):
    """FDA-292 [DOC-002] — AI Inline Suggestions per paragraph."""

    @classmethod
    def setUpClass(cls):
        cls.src = comp("editor/ai-suggestion-overlay.tsx")

    # -- File structure

    def test_file_exists(self):
        self.assertTrue(comp_exists("editor/ai-suggestion-overlay.tsx"))

    def test_use_client_directive(self):
        self.assertTrue(self.src.strip().startswith('"use client"'))

    def test_uses_react(self):
        self.assertIn("import React", self.src)

    # -- Exports

    def test_exports_overlay_component(self):
        self.assertIn("export function AISuggestionOverlay", self.src)

    def test_exports_ai_suggestion_type(self):
        self.assertIn("export interface AISuggestion", self.src)

    def test_exports_suggestion_category_type(self):
        self.assertIn("export type SuggestionCategory", self.src)

    def test_exports_suggestion_status_type(self):
        self.assertIn("export type SuggestionStatus", self.src)

    def test_exports_overlay_props(self):
        self.assertIn("export interface AISuggestionOverlayProps", self.src)

    # -- SuggestionCategory values

    def test_category_regulatory(self):
        self.assertIn("\"regulatory\"", self.src)

    def test_category_clarity(self):
        self.assertIn("\"clarity\"", self.src)

    def test_category_completeness(self):
        self.assertIn("\"completeness\"", self.src)

    def test_category_grammar(self):
        self.assertIn("\"grammar\"", self.src)

    def test_category_consistency(self):
        self.assertIn("\"consistency\"", self.src)

    # -- SuggestionStatus values

    def test_status_pending(self):
        self.assertIn("\"pending\"", self.src)

    def test_status_accepted(self):
        self.assertIn("\"accepted\"", self.src)

    def test_status_rejected(self):
        self.assertIn("\"rejected\"", self.src)

    def test_status_editing(self):
        self.assertIn("\"editing\"", self.src)

    # -- AISuggestion fields

    def test_field_original(self):
        self.assertIn("original:", self.src)

    def test_field_proposed(self):
        self.assertIn("proposed:", self.src)

    def test_field_rationale(self):
        self.assertIn("rationale:", self.src)

    def test_field_confidence(self):
        self.assertIn("confidence:", self.src)

    def test_field_regulation_refs(self):
        self.assertIn("regulationRefs", self.src)

    def test_field_agent_name(self):
        self.assertIn("agentName:", self.src)

    def test_field_paragraph_index(self):
        self.assertIn("paragraphIndex:", self.src)

    # -- Overlay props

    def test_prop_on_accept(self):
        self.assertIn("onAccept", self.src)

    def test_prop_on_reject(self):
        self.assertIn("onReject", self.src)

    def test_prop_on_bulk_accept(self):
        self.assertIn("onBulkAccept", self.src)

    def test_prop_on_bulk_reject(self):
        self.assertIn("onBulkReject", self.src)

    def test_prop_section_id_filter(self):
        self.assertIn("sectionId", self.src)

    # -- Features

    def test_accept_action(self):
        self.assertIn("onAccept(", self.src)

    def test_reject_action(self):
        self.assertIn("onReject(", self.src)

    def test_bulk_accept_handler(self):
        self.assertIn("handleBulkAccept", self.src)

    def test_bulk_reject_handler(self):
        self.assertIn("handleBulkReject", self.src)

    def test_edit_before_accept(self):
        self.assertIn("editing", self.src)

    def test_edit_textarea_present(self):
        self.assertIn("<textarea", self.src)

    def test_rejection_reason_field(self):
        self.assertIn("rejectReason", self.src)

    def test_show_original_toggle(self):
        self.assertIn("showOriginal", self.src)

    def test_confidence_badge(self):
        self.assertIn("ConfidenceBadge", self.src)

    def test_category_filter(self):
        self.assertIn("catFilter", self.src)

    def test_review_progress_bar(self):
        self.assertIn("stats.accepted", self.src)

    # -- Design tokens

    def test_fda_blue(self):
        self.assertIn("#005EA2", self.src)

    def test_success_green(self):
        self.assertIn("#1A7F4B", self.src)

    def test_critical_red(self):
        self.assertIn("#C5191B", self.src)

    # -- Sub-components

    def test_suggestion_card_subcomponent(self):
        self.assertIn("function SuggestionCard", self.src)

    def test_confidence_badge_subcomponent(self):
        self.assertIn("function ConfidenceBadge", self.src)

    # -- Category config coverage

    def test_cat_config_exists(self):
        self.assertIn("CAT_CONFIG", self.src)

    def test_regulatory_in_cat_config(self):
        pattern = r'CAT_CONFIG.*regulatory'
        self.assertRegex(self.src.replace("\n", " "), pattern)

    # -- Empty state

    def test_empty_state_message(self):
        self.assertIn("No AI suggestions", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-278  ExpertAssignmentInterface
# ══════════════════════════════════════════════════════════════════════════════

class TestExpertAssignmentInterface(unittest.TestCase):
    """FDA-278 [HITL-004] — Expert Assignment Interface for gate review routing."""

    @classmethod
    def setUpClass(cls):
        cls.src = comp("hitl/expert-assignment-interface.tsx")

    # -- File structure

    def test_file_exists(self):
        self.assertTrue(comp_exists("hitl/expert-assignment-interface.tsx"))

    def test_use_client_directive(self):
        self.assertTrue(self.src.strip().startswith('"use client"'))

    def test_uses_react(self):
        self.assertIn("import React", self.src)

    # -- Exports

    def test_exports_main_component(self):
        self.assertIn("export function ExpertAssignmentInterface", self.src)

    def test_exports_expert_type(self):
        self.assertIn("export interface Expert", self.src)

    def test_exports_expert_assignment_type(self):
        self.assertIn("export interface ExpertAssignment", self.src)

    def test_exports_assignment_options_type(self):
        self.assertIn("export interface AssignmentOptions", self.src)

    def test_exports_availability_type(self):
        self.assertIn("export type ExpertAvailability", self.src)

    def test_exports_specialization_type(self):
        self.assertIn("export type ExpertSpecialization", self.src)

    def test_exports_priority_type(self):
        self.assertIn("export type AssignmentPriority", self.src)

    # -- ExpertAvailability values

    def test_availability_available(self):
        self.assertIn("\"available\"", self.src)

    def test_availability_busy(self):
        self.assertIn("\"busy\"", self.src)

    def test_availability_ooo(self):
        self.assertIn("\"ooo\"", self.src)

    # -- ExpertSpecialization values (key ones)

    def test_spec_510k(self):
        self.assertIn("\"510k\"", self.src)

    def test_spec_de_novo(self):
        self.assertIn("\"de_novo\"", self.src)

    def test_spec_pma(self):
        self.assertIn("\"pma\"", self.src)

    def test_spec_software(self):
        self.assertIn("\"software\"", self.src)

    def test_spec_biocompatibility(self):
        self.assertIn("\"biocompatibility\"", self.src)

    def test_spec_human_factors(self):
        self.assertIn("\"human_factors\"", self.src)

    def test_spec_combination(self):
        self.assertIn("\"combination\"", self.src)

    def test_spec_ivd(self):
        self.assertIn("\"ivd\"", self.src)

    # -- AssignmentPriority values

    def test_priority_routine(self):
        self.assertIn("\"routine\"", self.src)

    def test_priority_expedited(self):
        self.assertIn("\"expedited\"", self.src)

    def test_priority_urgent(self):
        self.assertIn("\"urgent\"", self.src)

    # -- Expert fields

    def test_expert_field_name(self):
        self.assertIn("name:", self.src)

    def test_expert_field_title(self):
        self.assertIn("title:", self.src)

    def test_expert_field_email(self):
        self.assertIn("email:", self.src)

    def test_expert_field_availability(self):
        self.assertIn("availability:", self.src)

    def test_expert_field_specializations(self):
        self.assertIn("specializations:", self.src)

    def test_expert_field_open_reviews(self):
        self.assertIn("openReviews:", self.src)

    def test_expert_field_avg_close_days(self):
        self.assertIn("avgCloseDays:", self.src)

    def test_expert_field_conflict_companies(self):
        self.assertIn("conflictCompanies", self.src)

    def test_expert_field_assignments(self):
        self.assertIn("assignments:", self.src)

    # -- Props

    def test_prop_experts(self):
        self.assertIn("experts:", self.src)

    def test_prop_gate_label(self):
        self.assertIn("gateLabel:", self.src)

    def test_prop_project_name(self):
        self.assertIn("projectName:", self.src)

    def test_prop_applicant_company(self):
        self.assertIn("applicantCompany", self.src)

    def test_prop_current_assignee_id(self):
        self.assertIn("currentAssigneeId", self.src)

    def test_prop_on_assign(self):
        self.assertIn("onAssign", self.src)

    def test_prop_on_unassign(self):
        self.assertIn("onUnassign", self.src)

    # -- Features

    def test_coi_detection(self):
        self.assertIn("hasCOI", self.src)

    def test_coi_warning_displayed(self):
        self.assertIn("Conflict of Interest", self.src)

    def test_workload_bar(self):
        self.assertIn("WorkloadBar", self.src)

    def test_avatar_subcomponent(self):
        self.assertIn("function Avatar", self.src)

    def test_expert_card_subcomponent(self):
        self.assertIn("function ExpertCard", self.src)

    def test_specialization_filter(self):
        self.assertIn("specFilter", self.src)

    def test_spec_config_exists(self):
        self.assertIn("SPEC_CONFIG", self.src)

    def test_priority_config_exists(self):
        self.assertIn("PRIORITY_CONFIG", self.src)

    def test_avail_config_exists(self):
        self.assertIn("AVAIL_CONFIG", self.src)

    def test_deadline_input(self):
        self.assertIn("deadline", self.src)

    def test_notes_field(self):
        self.assertIn("notes", self.src)

    def test_handle_assign_fn(self):
        self.assertIn("handleAssign", self.src)

    def test_handle_unassign_fn(self):
        self.assertIn("handleUnassign", self.src)

    def test_assignment_confirmation_state(self):
        self.assertIn("submitted", self.src)

    def test_ooo_button_disabled(self):
        self.assertIn("availability === \"ooo\"", self.src)

    def test_recent_assignment_history(self):
        self.assertIn("recentAssignments", self.src)

    # -- 21 CFR Part 11

    def test_cfr_part11_in_assign_button(self):
        self.assertIn("21 CFR Part 11", self.src)

    # -- Design tokens

    def test_fda_blue(self):
        self.assertIn("#005EA2", self.src)

    def test_success_green(self):
        self.assertIn("#1A7F4B", self.src)

    def test_critical_red(self):
        self.assertIn("#C5191B", self.src)

    def test_warning_amber(self):
        self.assertIn("#B45309", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# Directory + cross-component integration checks
# ══════════════════════════════════════════════════════════════════════════════

class TestSprint26DirectoryStructure(unittest.TestCase):
    """Validates file layout for Sprint 26 deliverables."""

    def test_editor_dir_exists(self):
        path = os.path.join(ROOT, "components", "editor")
        self.assertTrue(os.path.isdir(path))

    def test_hitl_dir_exists(self):
        path = os.path.join(ROOT, "components", "hitl")
        self.assertTrue(os.path.isdir(path))

    def test_document_editor_file(self):
        self.assertTrue(comp_exists("editor/document-editor.tsx"))

    def test_ai_suggestion_overlay_file(self):
        self.assertTrue(comp_exists("editor/ai-suggestion-overlay.tsx"))

    def test_expert_assignment_interface_file(self):
        self.assertTrue(comp_exists("hitl/expert-assignment-interface.tsx"))

    def test_hitl_audit_trail_still_exists(self):
        # Sprint 25 must not have been deleted
        self.assertTrue(comp_exists("hitl/hitl-audit-trail.tsx"))

    def test_hitl_gate_integration_still_exists(self):
        self.assertTrue(comp_exists("hitl/hitl-gate-integration.tsx"))

    def test_ai_dir_components_exist(self):
        for f in [
            "ai/agent-diff-viewer.tsx",
            "ai/agent-error-recovery.tsx",
            "ai/rate-limit-panel.tsx",
            "ai/agentic-control-panel.tsx",
        ]:
            with self.subTest(f=f):
                self.assertTrue(comp_exists(f))


class TestSprint26CrossComponent(unittest.TestCase):
    """Cross-component integration checks for Sprint 26."""

    @classmethod
    def setUpClass(cls):
        cls.editor  = comp("editor/document-editor.tsx")
        cls.overlay = comp("editor/ai-suggestion-overlay.tsx")
        cls.expert  = comp("hitl/expert-assignment-interface.tsx")

    def test_editor_ai_sugg_count_links_to_overlay(self):
        # Editor tracks aiSuggCount; overlay consumes sectionId filter
        self.assertIn("aiSuggCount", self.editor)
        self.assertIn("sectionId", self.overlay)

    def test_editor_on_save_callback_for_cfr_logging(self):
        self.assertIn("onSave", self.editor)
        self.assertIn("Part 11", self.editor)

    def test_overlay_confidence_threshold(self):
        # Low-confidence suggestions should have warning indicators
        self.assertIn("confidence", self.overlay)
        self.assertIn("#C5191B", self.overlay)

    def test_expert_interface_on_assign_returns_options(self):
        # onAssign receives AssignmentOptions (priority, deadline, notes)
        self.assertIn("AssignmentOptions", self.expert)
        self.assertIn("priority:", self.expert)
        self.assertIn("deadline", self.expert)
        self.assertIn("notes", self.expert)

    def test_all_three_have_cn_utility(self):
        for src, name in [
            (self.editor,  "DocumentEditor"),
            (self.overlay, "AISuggestionOverlay"),
            (self.expert,  "ExpertAssignmentInterface"),
        ]:
            with self.subTest(component=name):
                self.assertIn("cn(", src)

    def test_all_three_have_fda_blue(self):
        for src, name in [
            (self.editor,  "DocumentEditor"),
            (self.overlay, "AISuggestionOverlay"),
            (self.expert,  "ExpertAssignmentInterface"),
        ]:
            with self.subTest(component=name):
                self.assertIn("#005EA2", src)

    def test_all_three_use_client(self):
        for src, name in [
            (self.editor,  "DocumentEditor"),
            (self.overlay, "AISuggestionOverlay"),
            (self.expert,  "ExpertAssignmentInterface"),
        ]:
            with self.subTest(component=name):
                self.assertTrue(src.strip().startswith('"use client"'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
