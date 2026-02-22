"""
Sprint 27 — Research Hub: Predicates + Evidence + Guidance + Citations Tests
=============================================================================
Validates the four FDA Sprint 27 frontend components:
  FDA-286  [PRED-003]  PredicateSelection
  FDA-287  [PRED-004]  EvidenceChainViewer
  FDA-288  [RH-001]    GuidanceInlineViewer
  FDA-289  [RH-002]    CitationManager

Strategy: static analysis via file reading and pattern checks.
No browser runtime required.
"""

import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "web")


def comp(rel: str) -> str:
    path = os.path.join(ROOT, "components", rel)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Component not found: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def comp_exists(rel: str) -> bool:
    return os.path.exists(os.path.join(ROOT, "components", rel))


# ══════════════════════════════════════════════════════════════════════════════
# FDA-286  PredicateSelection
# ══════════════════════════════════════════════════════════════════════════════

class TestPredicateSelection(unittest.TestCase):
    """FDA-286 [PRED-003] — Predicate search + compare interface."""

    @classmethod
    def setUpClass(cls):
        cls.src = comp("research/predicate-selection.tsx")

    def test_file_exists(self):
        self.assertTrue(comp_exists("research/predicate-selection.tsx"))

    def test_use_client(self):
        self.assertTrue(self.src.strip().startswith('"use client"'))

    def test_uses_react(self):
        self.assertIn("import React", self.src)

    # -- Exports

    def test_exports_predicate_selection(self):
        self.assertIn("export function PredicateSelection", self.src)

    def test_exports_predicate_device_type(self):
        self.assertIn("export interface PredicateDevice", self.src)

    def test_exports_predicate_health_type(self):
        self.assertIn("export interface PredicateHealth", self.src)

    def test_exports_predicate_selection_props(self):
        self.assertIn("export interface PredicateSelectionProps", self.src)

    def test_exports_device_class_type(self):
        self.assertIn("export type DeviceClass", self.src)

    def test_exports_sort_key_type(self):
        self.assertIn("export type SortKey", self.src)

    # -- DeviceClass values

    def test_class_i(self):
        self.assertIn('"I"', self.src)

    def test_class_ii(self):
        self.assertIn('"II"', self.src)

    def test_class_iii(self):
        self.assertIn('"III"', self.src)

    def test_class_u(self):
        self.assertIn('"U"', self.src)

    # -- PredicateDevice fields

    def test_field_k_number(self):
        self.assertIn("kNumber", self.src)

    def test_field_device_name(self):
        self.assertIn("deviceName", self.src)

    def test_field_applicant(self):
        self.assertIn("applicant", self.src)

    def test_field_product_code(self):
        self.assertIn("productCode", self.src)

    def test_field_clearance_year(self):
        self.assertIn("clearanceYear", self.src)

    def test_field_similarity(self):
        self.assertIn("similarity:", self.src)

    def test_field_health(self):
        self.assertIn("health:", self.src)

    # -- PredicateHealth fields

    def test_health_recall_count(self):
        self.assertIn("recallCount", self.src)

    def test_health_ae_count(self):
        self.assertIn("aeCount", self.src)

    def test_health_status(self):
        self.assertIn("\"healthy\"", self.src)
        self.assertIn("\"caution\"", self.src)
        self.assertIn("\"toxic\"", self.src)

    # -- Props

    def test_prop_predicates(self):
        self.assertIn("predicates:", self.src)

    def test_prop_max_comparisons(self):
        self.assertIn("maxComparisons", self.src)

    def test_prop_on_compare(self):
        self.assertIn("onCompare", self.src)

    def test_prop_on_view_details(self):
        self.assertIn("onViewDetails", self.src)

    # -- Features

    def test_search_input(self):
        self.assertIn('type="search"', self.src)

    def test_class_filter_buttons(self):
        self.assertIn("classFilter", self.src)

    def test_sort_key_selector(self):
        self.assertIn("sortKey", self.src)

    def test_year_filter(self):
        self.assertIn("yearFilter", self.src)

    def test_comparison_state(self):
        self.assertIn("comparison", self.src)

    def test_toggle_compare_fn(self):
        self.assertIn("toggleCompare", self.src)

    def test_comparison_tray_subcomponent(self):
        self.assertIn("function ComparisonTray", self.src)

    def test_predicate_card_subcomponent(self):
        self.assertIn("function PredicateCard", self.src)

    def test_similarity_ring_subcomponent(self):
        self.assertIn("function SimilarityRing", self.src)

    def test_swap_comparison(self):
        self.assertIn("swapComparison", self.src)

    def test_sort_by_similarity(self):
        self.assertIn("\"similarity\"", self.src)

    def test_sort_by_year(self):
        self.assertIn("\"year\"", self.src)

    def test_sort_by_ae_count(self):
        self.assertIn("\"ae_count\"", self.src)

    def test_empty_state_message(self):
        self.assertIn("No predicates match", self.src)

    # -- Design tokens

    def test_fda_blue(self):
        self.assertIn("#005EA2", self.src)

    def test_success_green(self):
        self.assertIn("#1A7F4B", self.src)

    def test_critical_red(self):
        self.assertIn("#C5191B", self.src)

    def test_class_config_exists(self):
        self.assertIn("CLASS_CONFIG", self.src)

    def test_health_config_exists(self):
        self.assertIn("HEALTH_CONFIG", self.src)

    # -- Cursor pointer accessibility

    def test_cursor_pointer_on_cards(self):
        self.assertIn("cursor-pointer", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-287  EvidenceChainViewer
# ══════════════════════════════════════════════════════════════════════════════

class TestEvidenceChainViewer(unittest.TestCase):
    """FDA-287 [PRED-004] — SE claim provenance tree viewer."""

    @classmethod
    def setUpClass(cls):
        cls.src = comp("research/evidence-chain-viewer.tsx")

    def test_file_exists(self):
        self.assertTrue(comp_exists("research/evidence-chain-viewer.tsx"))

    def test_use_client(self):
        self.assertTrue(self.src.strip().startswith('"use client"'))

    def test_uses_react(self):
        self.assertIn("import React", self.src)

    # -- Exports

    def test_exports_main_component(self):
        self.assertIn("export function EvidenceChainViewer", self.src)

    def test_exports_evidence_claim(self):
        self.assertIn("export interface EvidenceClaim", self.src)

    def test_exports_evidence_item(self):
        self.assertIn("export interface EvidenceItem", self.src)

    def test_exports_source_document(self):
        self.assertIn("export interface SourceDocument", self.src)

    def test_exports_evidence_type(self):
        self.assertIn("export type EvidenceType", self.src)

    def test_exports_evidence_strength(self):
        self.assertIn("export type EvidenceStrength", self.src)

    def test_exports_document_type(self):
        self.assertIn("export type DocumentType", self.src)

    # -- EvidenceType values

    def test_evidence_type_bench_test(self):
        self.assertIn("\"bench_test\"", self.src)

    def test_evidence_type_clinical(self):
        self.assertIn("\"clinical\"", self.src)

    def test_evidence_type_literature(self):
        self.assertIn("\"literature\"", self.src)

    def test_evidence_type_predicate_data(self):
        self.assertIn("\"predicate_data\"", self.src)

    def test_evidence_type_standard(self):
        self.assertIn("\"standard\"", self.src)

    def test_evidence_type_simulated_use(self):
        self.assertIn("\"simulated_use\"", self.src)

    # -- EvidenceStrength values

    def test_strength_high(self):
        self.assertIn("\"high\"", self.src)

    def test_strength_medium(self):
        self.assertIn("\"medium\"", self.src)

    def test_strength_low(self):
        self.assertIn("\"low\"", self.src)

    # -- EvidenceClaim fields

    def test_claim_text(self):
        self.assertIn("text:", self.src)

    def test_claim_section(self):
        self.assertIn("section:", self.src)

    def test_claim_confidence(self):
        self.assertIn("confidence:", self.src)

    def test_claim_evidence(self):
        self.assertIn("evidence:", self.src)

    # -- EvidenceItem fields

    def test_evidence_quote(self):
        self.assertIn("quote:", self.src)

    def test_evidence_type_field(self):
        self.assertIn("type:", self.src)

    def test_evidence_strength_field(self):
        self.assertIn("strength:", self.src)

    def test_evidence_documents(self):
        self.assertIn("documents:", self.src)

    # -- Sub-components

    def test_claim_node_subcomponent(self):
        self.assertIn("function ClaimNode", self.src)

    def test_evidence_branch_subcomponent(self):
        self.assertIn("function EvidenceBranch", self.src)

    def test_document_leaf_subcomponent(self):
        self.assertIn("function DocumentLeaf", self.src)

    def test_confidence_bar_subcomponent(self):
        self.assertIn("function ConfidenceBar", self.src)

    # -- Features

    def test_strength_filter(self):
        self.assertIn("strengthFilter", self.src)

    def test_expand_collapse(self):
        self.assertIn("expanded", self.src)

    def test_selected_node_tracking(self):
        self.assertIn("selectedId", self.src)

    def test_export_citations_fn(self):
        self.assertIn("handleExport", self.src)

    def test_on_node_click_prop(self):
        self.assertIn("onNodeClick", self.src)

    def test_on_export_prop(self):
        self.assertIn("onExport", self.src)

    def test_empty_state_message(self):
        self.assertIn("No evidence chains", self.src)

    # -- Config maps

    def test_evidence_type_config(self):
        self.assertIn("EVIDENCE_TYPE_CONFIG", self.src)

    def test_strength_config(self):
        self.assertIn("STRENGTH_CONFIG", self.src)

    def test_doc_type_config(self):
        self.assertIn("DOC_TYPE_CONFIG", self.src)

    # -- Design tokens

    def test_fda_blue(self):
        self.assertIn("#005EA2", self.src)

    def test_success_green(self):
        self.assertIn("#1A7F4B", self.src)

    def test_warning_amber(self):
        self.assertIn("#B45309", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-288  GuidanceInlineViewer
# ══════════════════════════════════════════════════════════════════════════════

class TestGuidanceInlineViewer(unittest.TestCase):
    """FDA-288 [RH-001] — In-app PDF viewer with AI highlights."""

    @classmethod
    def setUpClass(cls):
        cls.src = comp("research/guidance-inline-viewer.tsx")

    def test_file_exists(self):
        self.assertTrue(comp_exists("research/guidance-inline-viewer.tsx"))

    def test_use_client(self):
        self.assertTrue(self.src.strip().startswith('"use client"'))

    def test_uses_react(self):
        self.assertIn("import React", self.src)

    # -- Exports

    def test_exports_guidance_inline_viewer(self):
        self.assertIn("export function GuidanceInlineViewer", self.src)

    def test_exports_highlighted_passage(self):
        self.assertIn("export interface HighlightedPassage", self.src)

    def test_exports_related_document(self):
        self.assertIn("export interface RelatedDocument", self.src)

    def test_exports_annotation(self):
        self.assertIn("export interface Annotation", self.src)

    def test_exports_guidance_inline_viewer_props(self):
        self.assertIn("export interface GuidanceInlineViewerProps", self.src)

    def test_exports_document_type(self):
        self.assertIn("export type DocumentType", self.src)

    # -- Props

    def test_prop_title(self):
        self.assertIn("title:", self.src)

    def test_prop_reference(self):
        self.assertIn("reference:", self.src)

    def test_prop_doc_type(self):
        self.assertIn("docType:", self.src)

    def test_prop_pdf_url(self):
        self.assertIn("pdfUrl:", self.src)

    def test_prop_total_pages(self):
        self.assertIn("totalPages:", self.src)

    def test_prop_highlights(self):
        self.assertIn("highlights", self.src)

    def test_prop_related(self):
        self.assertIn("related", self.src)

    def test_prop_annotations(self):
        self.assertIn("annotations", self.src)

    def test_prop_on_cite_copied(self):
        self.assertIn("onCiteCopied", self.src)

    def test_prop_on_annotation_add(self):
        self.assertIn("onAnnotationAdd", self.src)

    def test_prop_on_link_to_section(self):
        self.assertIn("onLinkToSection", self.src)

    def test_prop_on_open_related(self):
        self.assertIn("onOpenRelated", self.src)

    # -- Features

    def test_iframe_pdf_render(self):
        self.assertIn("<iframe", self.src)

    def test_page_navigation(self):
        self.assertIn("currentPage", self.src)
        self.assertIn("totalPages", self.src)

    def test_zoom_control(self):
        self.assertIn("zoom", self.src)
        self.assertIn("ZOOM_LEVELS", self.src)

    def test_tab_navigation(self):
        self.assertIn("activeTab", self.src)
        self.assertIn("\"highlights\"", self.src)
        self.assertIn("\"annotations\"", self.src)
        self.assertIn("\"related\"", self.src)

    def test_passage_citation_copy(self):
        self.assertIn("buildCitation", self.src)
        self.assertIn("clipboard", self.src)

    def test_annotation_form(self):
        self.assertIn("function AnnotationForm", self.src)

    def test_passage_card_subcomponent(self):
        self.assertIn("function PassageCard", self.src)

    def test_go_to_page_fn(self):
        self.assertIn("goToPage", self.src)

    def test_accessibility_aria(self):
        self.assertIn("aria-label", self.src)

    def test_keyboard_nav_prev_next(self):
        self.assertIn("aria-label=\"Previous page\"", self.src)
        self.assertIn("aria-label=\"Next page\"", self.src)

    def test_copied_feedback(self):
        self.assertIn("copied", self.src)

    # -- DocumentType values

    def test_doc_type_guidance(self):
        self.assertIn("\"guidance\"", self.src)

    def test_doc_type_510k(self):
        self.assertIn("\"510k_summary\"", self.src)

    def test_doc_type_standard(self):
        self.assertIn("\"standard\"", self.src)

    def test_doc_type_publication(self):
        self.assertIn("\"publication\"", self.src)

    # -- Design tokens

    def test_fda_blue(self):
        self.assertIn("#005EA2", self.src)

    def test_highlight_amber(self):
        self.assertIn("#B45309", self.src)

    def test_doc_type_config(self):
        self.assertIn("DOC_TYPE_CONFIG", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-289  CitationManager
# ══════════════════════════════════════════════════════════════════════════════

class TestCitationManager(unittest.TestCase):
    """FDA-289 [RH-002] — Per-project citation library."""

    @classmethod
    def setUpClass(cls):
        cls.src = comp("research/citation-manager.tsx")

    def test_file_exists(self):
        self.assertTrue(comp_exists("research/citation-manager.tsx"))

    def test_use_client(self):
        self.assertTrue(self.src.strip().startswith('"use client"'))

    def test_uses_react(self):
        self.assertIn("import React", self.src)

    # -- Exports

    def test_exports_citation_manager(self):
        self.assertIn("export function CitationManager", self.src)

    def test_exports_citation_type(self):
        self.assertIn("export interface Citation", self.src)

    def test_exports_citation_tag_type(self):
        self.assertIn("export type CitationTag", self.src)

    def test_exports_citation_source_type(self):
        self.assertIn("export type CitationSourceType", self.src)

    def test_exports_citation_sort_key(self):
        self.assertIn("export type CitationSortKey", self.src)

    def test_exports_citation_manager_props(self):
        self.assertIn("export interface CitationManagerProps", self.src)

    # -- CitationTag values

    def test_tag_predicate(self):
        self.assertIn("\"predicate\"", self.src)

    def test_tag_standard(self):
        self.assertIn("\"standard\"", self.src)

    def test_tag_safety(self):
        self.assertIn("\"safety\"", self.src)

    def test_tag_clinical(self):
        self.assertIn("\"clinical\"", self.src)

    def test_tag_labeling(self):
        self.assertIn("\"labeling\"", self.src)

    def test_tag_biocompatibility(self):
        self.assertIn("\"biocompatibility\"", self.src)

    def test_tag_software(self):
        self.assertIn("\"software\"", self.src)

    # -- Citation fields

    def test_field_title(self):
        self.assertIn("title:", self.src)

    def test_field_source(self):
        self.assertIn("source:", self.src)

    def test_field_source_type(self):
        self.assertIn("sourceType:", self.src)

    def test_field_relevance(self):
        self.assertIn("relevance:", self.src)

    def test_field_tags(self):
        self.assertIn("tags:", self.src)

    def test_field_note(self):
        self.assertIn("note", self.src)

    def test_field_linked_sections(self):
        self.assertIn("linkedSections:", self.src)

    def test_field_in_submission(self):
        self.assertIn("inSubmission", self.src)

    # -- Props

    def test_prop_citations(self):
        self.assertIn("citations:", self.src)

    def test_prop_submission_sections(self):
        self.assertIn("submissionSections", self.src)

    def test_prop_on_remove(self):
        self.assertIn("onRemove", self.src)

    def test_prop_on_update_note(self):
        self.assertIn("onUpdateNote", self.src)

    def test_prop_on_link_section(self):
        self.assertIn("onLinkSection", self.src)

    def test_prop_on_unlink_section(self):
        self.assertIn("onUnlinkSection", self.src)

    def test_prop_on_export(self):
        self.assertIn("onExport", self.src)

    # -- Features

    def test_nlm_format(self):
        self.assertIn("formatNLM", self.src)

    def test_apa_format(self):
        self.assertIn("formatAPA", self.src)

    def test_export_format_selector(self):
        self.assertIn("exportFmt", self.src)
        self.assertIn("\"nlm\"", self.src)
        self.assertIn("\"apa\"", self.src)

    def test_tag_filter(self):
        self.assertIn("tagFilter", self.src)

    def test_search_query(self):
        self.assertIn("searchQuery", self.src)

    def test_sort_key(self):
        self.assertIn("sortKey", self.src)

    def test_completeness_check(self):
        self.assertIn("missingFromSubmission", self.src)

    def test_link_section_action(self):
        self.assertIn("handleLinkSection", self.src)

    def test_unlink_section_action(self):
        self.assertIn("handleUnlinkSection", self.src)

    def test_citation_card_subcomponent(self):
        self.assertIn("function CitationCard", self.src)

    def test_file_download_export(self):
        self.assertIn("URL.createObjectURL", self.src)

    def test_empty_state_message(self):
        self.assertIn("No citations saved", self.src)

    def test_cited_indicator(self):
        self.assertIn("Cited", self.src)

    # -- Design tokens

    def test_fda_blue(self):
        self.assertIn("#005EA2", self.src)

    def test_success_green(self):
        self.assertIn("#1A7F4B", self.src)

    def test_warning_amber(self):
        self.assertIn("#B45309", self.src)

    def test_tag_config_exists(self):
        self.assertIn("TAG_CONFIG", self.src)

    def test_source_type_config_exists(self):
        self.assertIn("SOURCE_TYPE_CONFIG", self.src)

    # -- Accessibility

    def test_aria_label_on_selects(self):
        self.assertIn("aria-label", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# Directory + cross-component integration
# ══════════════════════════════════════════════════════════════════════════════

class TestSprint27DirectoryStructure(unittest.TestCase):
    """Validates file layout for Sprint 27 deliverables."""

    def test_research_dir_exists(self):
        path = os.path.join(ROOT, "components", "research")
        self.assertTrue(os.path.isdir(path))

    def test_predicate_selection_file(self):
        self.assertTrue(comp_exists("research/predicate-selection.tsx"))

    def test_evidence_chain_viewer_file(self):
        self.assertTrue(comp_exists("research/evidence-chain-viewer.tsx"))

    def test_guidance_inline_viewer_file(self):
        self.assertTrue(comp_exists("research/guidance-inline-viewer.tsx"))

    def test_citation_manager_file(self):
        self.assertTrue(comp_exists("research/citation-manager.tsx"))

    def test_sprint26_editor_components_intact(self):
        for f in [
            "editor/document-editor.tsx",
            "editor/ai-suggestion-overlay.tsx",
            "hitl/expert-assignment-interface.tsx",
        ]:
            with self.subTest(f=f):
                self.assertTrue(comp_exists(f))


class TestSprint27CrossComponent(unittest.TestCase):
    """Cross-component integration checks for Sprint 27."""

    @classmethod
    def setUpClass(cls):
        cls.pred    = comp("research/predicate-selection.tsx")
        cls.evchain = comp("research/evidence-chain-viewer.tsx")
        cls.viewer  = comp("research/guidance-inline-viewer.tsx")
        cls.citmgr  = comp("research/citation-manager.tsx")

    def test_predicate_feeds_into_evidence_via_k_number(self):
        # PredicateDevice has kNumber; EvidenceChain has SourceDocument referencing K-numbers
        self.assertIn("kNumber", self.pred)
        self.assertIn("reference:", self.evchain)

    def test_guidance_viewer_cite_links_to_citation_manager(self):
        # GuidanceInlineViewer has onCiteCopied callback; CitationManager has citation storage
        self.assertIn("onCiteCopied", self.viewer)
        self.assertIn("addedAt:", self.citmgr)

    def test_citation_manager_links_to_submission_sections(self):
        self.assertIn("linkedSections", self.citmgr)
        self.assertIn("submissionSections", self.citmgr)

    def test_guidance_viewer_passage_link_to_section(self):
        self.assertIn("onLinkToSection", self.viewer)

    def test_all_four_have_cn_utility(self):
        for src, name in [
            (self.pred,    "PredicateSelection"),
            (self.evchain, "EvidenceChainViewer"),
            (self.viewer,  "GuidanceInlineViewer"),
            (self.citmgr,  "CitationManager"),
        ]:
            with self.subTest(component=name):
                self.assertIn("cn(", src)

    def test_all_four_have_fda_blue(self):
        for src, name in [
            (self.pred,    "PredicateSelection"),
            (self.evchain, "EvidenceChainViewer"),
            (self.viewer,  "GuidanceInlineViewer"),
            (self.citmgr,  "CitationManager"),
        ]:
            with self.subTest(component=name):
                self.assertIn("#005EA2", src)

    def test_all_four_use_client(self):
        for src, name in [
            (self.pred,    "PredicateSelection"),
            (self.evchain, "EvidenceChainViewer"),
            (self.viewer,  "GuidanceInlineViewer"),
            (self.citmgr,  "CitationManager"),
        ]:
            with self.subTest(component=name):
                self.assertTrue(src.strip().startswith('"use client"'))

    def test_citation_completeness_check_targets_standards(self):
        # CitationManager checks if standard-tagged citations are in submission
        self.assertIn("standard", self.citmgr)
        self.assertIn("inSubmission", self.citmgr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
