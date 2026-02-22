"""
Sprint 28 — Research Hub page assembly + missing panels
Tests: guidance-dendrogram, signal-dashboard, /research/page, /dashboard/page,
       /projects/[id]/page, /documents/[id]/page, /agents/page
Static analysis only — no browser runtime required.
"""
import os
import unittest

# ── Helpers ────────────────────────────────────────────────────────────────

# 3 levels up from tests/ → fda-tools repo root → web/
ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "web")


def comp(rel: str) -> str:
    """Read a file relative to web/."""
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════════
# FDA-291 — GuidanceDendrogram
# ══════════════════════════════════════════════════════════════════════════════

class TestGuidanceDendrogram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = comp("components/research/guidance-dendrogram.tsx")

    def test_use_client(self):       self.assertIn('"use client"', self.src)
    def test_uses_react(self):       self.assertIn("import React", self.src)
    def test_no_d3_import(self):     self.assertNotIn("import * as d3", self.src)
    def test_no_d3_require(self):    self.assertNotIn('require("d3")', self.src)
    def test_svg_based(self):        self.assertIn("<svg", self.src)
    def test_fda_blue(self):         self.assertIn("#005EA2", self.src)
    def test_success_green(self):    self.assertIn("#1A7F4B", self.src)
    def test_warning_amber(self):    self.assertIn("#B45309", self.src)
    def test_critical_red(self):     self.assertIn("#C5191B", self.src)
    def test_regulation_area_type(self): self.assertIn("RegulationArea", self.src)
    def test_guidance_document_type(self): self.assertIn("GuidanceDocument", self.src)
    def test_guidance_cluster_type(self): self.assertIn("GuidanceCluster", self.src)
    def test_props_type_exported(self): self.assertIn("GuidanceDendrogramProps", self.src)
    def test_component_exported(self): self.assertIn("export function GuidanceDendrogram", self.src)
    def test_on_select_document_prop(self): self.assertIn("onSelectDocument", self.src)
    def test_expand_collapse(self): self.assertIn("collapsed", self.src)
    def test_toggle_collapse(self): self.assertIn("toggleCollapse", self.src)
    def test_zoom_state(self):       self.assertIn("zoom", self.src)
    def test_pan_state(self):        self.assertIn("pan", self.src)
    def test_area_filter_state(self): self.assertIn("areaFilter", self.src)
    def test_area_config_exists(self): self.assertIn("AREA_CONFIG", self.src)
    def test_area_general(self):     self.assertIn('"general"', self.src)
    def test_area_devices(self):     self.assertIn('"devices"', self.src)
    def test_area_biologics(self):   self.assertIn('"biologics"', self.src)
    def test_area_drugs(self):       self.assertIn('"drugs"', self.src)
    def test_area_combination(self): self.assertIn('"combination"', self.src)
    def test_tooltip_component(self): self.assertIn("function Tooltip", self.src)
    def test_flat_node_type(self):   self.assertIn("FlatNode", self.src)
    def test_flatten_tree_fn(self):  self.assertIn("flattenTree", self.src)
    def test_applicability_field(self): self.assertIn("applicability", self.src)
    def test_cluster_to_tree_fn(self): self.assertIn("clusterToTree", self.src)
    def test_wheel_zoom(self):       self.assertIn("wheel", self.src)
    def test_mouse_drag(self):       self.assertIn("onMouseDown", self.src)
    def test_cursor_grab(self):      self.assertIn("cursor-grab", self.src)
    def test_aria_label_on_buttons(self): self.assertIn("cursor-pointer", self.src)
    def test_reset_button(self):     self.assertIn("Reset", self.src)
    def test_empty_state(self):      self.assertIn("No guidance documents", self.src)
    def test_cn_utility(self):       self.assertIn("cn(", self.src)
    def test_use_callback(self):     self.assertIn("useCallback", self.src)
    def test_use_effect(self):       self.assertIn("useEffect", self.src)
    def test_use_ref(self):          self.assertIn("useRef", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-292 — SignalDashboard
# ══════════════════════════════════════════════════════════════════════════════

class TestSignalDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = comp("components/research/signal-dashboard.tsx")

    def test_use_client(self):       self.assertIn('"use client"', self.src)
    def test_uses_react(self):       self.assertIn("import React", self.src)
    def test_fda_blue(self):         self.assertIn("#005EA2", self.src)
    def test_critical_red(self):     self.assertIn("#C5191B", self.src)
    def test_warning_amber(self):    self.assertIn("#B45309", self.src)
    def test_success_green(self):    self.assertIn("#1A7F4B", self.src)
    def test_signal_data_point_type(self): self.assertIn("SignalDataPoint", self.src)
    def test_severity_level_type(self): self.assertIn("SeverityLevel", self.src)
    def test_props_type_exported(self): self.assertIn("SignalDashboardProps", self.src)
    def test_component_exported(self): self.assertIn("export function SignalDashboard", self.src)
    def test_cusum_alarm_prop(self): self.assertIn("cusumAlarm", self.src)
    def test_product_codes_prop(self): self.assertIn("productCodes", self.src)
    def test_on_export_prop(self):   self.assertIn("onExport", self.src)
    def test_cusum_chart_fn(self):   self.assertIn("function CusumChart", self.src)
    def test_anomaly_card_fn(self):  self.assertIn("function AnomalyCard", self.src)
    def test_is_anomaly_field(self): self.assertIn("isAnomaly", self.src)
    def test_anomaly_note_field(self): self.assertIn("anomalyNote", self.src)
    def test_window_months_state(self): self.assertIn("windowMonths", self.src)
    def test_selected_codes_state(self): self.assertIn("selectedCodes", self.src)
    def test_svg_chart(self):        self.assertIn("<svg", self.src)
    def test_cusum_alarm_line(self): self.assertIn("alarmY", self.src)
    def test_dashed_alarm_line(self): self.assertIn("strokeDasharray", self.src)
    def test_area_path_fill(self):   self.assertIn("url(#count-grad)", self.src)
    def test_severity_critical(self): self.assertIn('"critical"', self.src)
    def test_severity_serious(self): self.assertIn('"serious"', self.src)
    def test_severity_non_serious(self): self.assertIn('"non_serious"', self.src)
    def test_severity_config_exists(self): self.assertIn("SEVERITY_CONFIG", self.src)
    def test_window_options(self):   self.assertIn("WINDOW_OPTIONS", self.src)
    def test_12mo_window(self):      self.assertIn("12", self.src)
    def test_24mo_window(self):      self.assertIn("24", self.src)
    def test_60mo_window(self):      self.assertIn("60", self.src)
    def test_csv_export(self):       self.assertIn(".csv", self.src)
    def test_url_create_object_url(self): self.assertIn("createObjectURL", self.src)
    def test_monthly_aggregation(self): self.assertIn("monthly", self.src)
    def test_cusum_field(self):      self.assertIn(".cusum", self.src)
    def test_kpi_row(self):          self.assertIn("Total Events", self.src)
    def test_anomalies_count(self):  self.assertIn("Anomalies", self.src)
    def test_severity_breakdown_label(self): self.assertIn("Severity breakdown", self.src)
    def test_empty_state(self):      self.assertIn("No signal data", self.src)
    def test_cn_utility(self):       self.assertIn("cn(", self.src)
    def test_cursor_pointer(self):   self.assertIn("cursor-pointer", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-290 — /research/page.tsx
# ══════════════════════════════════════════════════════════════════════════════

class TestResearchPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = comp("app/research/page.tsx")

    def test_use_client(self):       self.assertIn('"use client"', self.src)
    def test_default_export(self):   self.assertIn("export default function ResearchPage", self.src)
    def test_imports_predicate_selection(self): self.assertIn("predicate-selection", self.src)
    def test_imports_evidence_chain(self): self.assertIn("evidence-chain-viewer", self.src)
    def test_imports_guidance_viewer(self): self.assertIn("guidance-inline-viewer", self.src)
    def test_imports_citation_manager(self): self.assertIn("citation-manager", self.src)
    def test_imports_guidance_dendrogram(self): self.assertIn("guidance-dendrogram", self.src)
    def test_imports_signal_dashboard(self): self.assertIn("signal-dashboard", self.src)
    def test_search_tab(self):       self.assertIn('"search"', self.src)
    def test_predicates_tab(self):   self.assertIn('"predicates"', self.src)
    def test_guidance_tab(self):     self.assertIn('"guidance"', self.src)
    def test_signals_tab(self):      self.assertIn('"signals"', self.src)
    def test_citations_tab(self):    self.assertIn('"citations"', self.src)
    def test_tab_nav_aria(self):     self.assertIn("aria-label", self.src)
    def test_active_tab_state(self): self.assertIn("activeTab", self.src)
    def test_left_tab_rail(self):    self.assertIn("border-r border-border", self.src)
    def test_fda_blue(self):         self.assertIn("#005EA2", self.src)
    def test_demo_predicates(self):  self.assertIn("DEMO_PREDICATES", self.src)
    def test_demo_claims(self):      self.assertIn("DEMO_CLAIMS", self.src)
    def test_demo_clusters(self):    self.assertIn("DEMO_CLUSTERS", self.src)
    def test_demo_signals(self):     self.assertIn("DEMO_SIGNALS", self.src)
    def test_demo_citations(self):   self.assertIn("DEMO_CITATIONS", self.src)
    def test_search_panel_fn(self):  self.assertIn("function SearchPanel", self.src)
    def test_pgvector_mention(self): self.assertIn("pgvector", self.src)
    def test_k_number_in_predicates(self): self.assertIn("kNumber", self.src)
    def test_responsive_collapse(self): self.assertIn("flex-1 overflow-hidden", self.src)
    def test_cn_utility(self):       self.assertIn("cn(", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-294 — /dashboard/page.tsx
# ══════════════════════════════════════════════════════════════════════════════

class TestDashboardPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = comp("app/dashboard/page.tsx")

    def test_use_client(self):       self.assertIn('"use client"', self.src)
    def test_default_export(self):   self.assertIn("export default function DashboardPage", self.src)
    def test_project_status_cards(self): self.assertIn("ProjectCard", self.src)
    def test_agent_feed(self):       self.assertIn("AgentFeedItem", self.src)
    def test_kpi_cards(self):        self.assertIn("KpiCard", self.src)
    def test_sri_sparkline(self):    self.assertIn("SriSparkline", self.src)
    def test_fda_blue(self):         self.assertIn("#005EA2", self.src)
    def test_success_green(self):    self.assertIn("#1A7F4B", self.src)
    def test_warning_amber(self):    self.assertIn("#B45309", self.src)
    def test_critical_red(self):     self.assertIn("#C5191B", self.src)
    def test_project_type(self):     self.assertIn("interface Project", self.src)
    def test_stage_concept(self):    self.assertIn("CONCEPT", self.src)
    def test_stage_cleared(self):    self.assertIn("CLEARED", self.src)
    def test_agent_activity_type(self): self.assertIn("AgentActivity", self.src)
    def test_agent_running_status(self): self.assertIn('"running"', self.src)
    def test_agent_done_status(self): self.assertIn('"done"', self.src)
    def test_agent_error_status(self): self.assertIn('"error"', self.src)
    def test_sri_ring(self):         self.assertIn("SriRing", self.src)
    def test_new_project_btn(self):  self.assertIn("New Project", self.src)
    def test_run_research_btn(self): self.assertIn("Run Research", self.src)
    def test_mission_control_link(self): self.assertIn("Mission control", self.src)
    def test_sri_trend_label(self):  self.assertIn("SRI Trend", self.src)
    def test_status_on_track(self):  self.assertIn("on_track", self.src)
    def test_status_at_risk(self):   self.assertIn("at_risk", self.src)
    def test_status_blocked(self):   self.assertIn("blocked", self.src)
    def test_pulse_animation(self):  self.assertIn("animate-ping", self.src)
    def test_svg_sparkline(self):    self.assertIn("<svg", self.src)
    def test_cn_utility(self):       self.assertIn("cn(", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-293 — /projects/[id]/page.tsx
# ══════════════════════════════════════════════════════════════════════════════

class TestNpdWorkspacePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = comp("app/projects/[id]/page.tsx")

    def test_use_client(self):       self.assertIn('"use client"', self.src)
    def test_default_export(self):   self.assertIn("export default function ProjectWorkspacePage", self.src)
    def test_params_prop(self):      self.assertIn("params: { id: string }", self.src)
    def test_12_stages(self):
        stages = ["CONCEPT","CLASSIFY","PREDICATE","PATHWAY","PRESUB",
                  "TESTING","DRAFTING","REVIEW","SUBMIT","FDA_REVIEW","CLEARED","POST_MARKET"]
        for s in stages:
            self.assertIn(s, self.src)
    def test_stage_type(self):       self.assertIn("interface Stage", self.src)
    def test_stage_status_type(self): self.assertIn("StageStatus", self.src)
    def test_view_mode_type(self):   self.assertIn("ViewMode", self.src)
    def test_wizard_mode(self):      self.assertIn('"wizard"', self.src)
    def test_power_mode(self):       self.assertIn('"power"', self.src)
    def test_hitl_gate_required(self): self.assertIn("gateRequired", self.src)
    def test_ai_assistant_fn(self):  self.assertIn("function AiAssistant", self.src)
    def test_stage_content_fn(self): self.assertIn("function StageContent", self.src)
    def test_ai_open_state(self):    self.assertIn("aiOpen", self.src)
    def test_fda_blue(self):         self.assertIn("#005EA2", self.src)
    def test_hitl_gate_banner(self): self.assertIn("HITL Gate Required", self.src)
    def test_left_sidebar_nav(self): self.assertIn("NPD Pipeline", self.src)
    def test_mode_toggle(self):      self.assertIn("viewMode", self.src)
    def test_research_hub_link(self): self.assertIn("/research", self.src)
    def test_doc_studio_link(self):  self.assertIn("/documents", self.src)
    def test_21_cfr_part11_mention(self): self.assertIn("21 CFR Part 11", self.src)
    def test_aria_label_nav(self):   self.assertIn("aria-label", self.src)
    def test_cn_utility(self):       self.assertIn("cn(", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-295 — /documents/[id]/page.tsx
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentStudioPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = comp("app/documents/[id]/page.tsx")

    def test_use_client(self):       self.assertIn('"use client"', self.src)
    def test_default_export(self):   self.assertIn("export default function DocumentStudioPage", self.src)
    def test_params_prop(self):      self.assertIn("params: { id: string }", self.src)
    def test_imports_document_editor(self): self.assertIn("document-editor", self.src)
    def test_imports_ai_overlay(self): self.assertIn("ai-suggestion-overlay", self.src)
    def test_imports_estar_sections(self): self.assertIn("ESTAR_SECTIONS", self.src)
    def test_section_item_fn(self):  self.assertIn("function SectionItem", self.src)
    def test_demo_suggestions(self): self.assertIn("DEMO_SUGGESTIONS", self.src)
    def test_fda_blue(self):         self.assertIn("#005EA2", self.src)
    def test_success_green(self):    self.assertIn("#1A7F4B", self.src)
    def test_section_navigator(self): self.assertIn("eSTAR section navigator", self.src)
    def test_word_count_state(self): self.assertIn("wordCount", self.src)
    def test_saved_at_state(self):   self.assertIn("savedAt", self.src)
    def test_suggestions_open_state(self): self.assertIn("suggestionsOpen", self.src)
    def test_21_cfr_audit_footer(self): self.assertIn("21 CFR Part 11", self.src)
    def test_export_estar_btn(self): self.assertIn("Export eSTAR", self.src)
    def test_hide_show_ai_btn(self): self.assertIn("Hide AI", self.src)
    def test_active_section_id(self): self.assertIn("activeSectionId", self.src)
    def test_total_complete(self):   self.assertIn("totalComplete", self.src)
    def test_regulatory_category(self): self.assertIn('"regulatory"', self.src)
    def test_completeness_category(self): self.assertIn('"completeness"', self.src)
    def test_aria_label_nav(self):   self.assertIn("aria-label", self.src)
    def test_cn_utility(self):       self.assertIn("cn(", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# FDA-296 — /agents/page.tsx
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = comp("app/agents/page.tsx")

    def test_use_client(self):       self.assertIn('"use client"', self.src)
    def test_default_export(self):   self.assertIn("export default function AgentsPage", self.src)
    def test_imports_agentic_control(self): self.assertIn("agentic-control-panel", self.src)
    def test_imports_diff_viewer(self): self.assertIn("agent-diff-viewer", self.src)
    def test_imports_rate_limit(self): self.assertIn("rate-limit-panel", self.src)
    def test_imports_error_recovery(self): self.assertIn("agent-error-recovery", self.src)
    def test_stat_card_fn(self):     self.assertIn("function StatCard", self.src)
    def test_diff_open_state(self):  self.assertIn("diffOpen", self.src)
    def test_mission_control_heading(self): self.assertIn("Mission control", self.src)
    def test_167_agents(self):       self.assertIn("167 agents", self.src)
    def test_fda_blue(self):         self.assertIn("#005EA2", self.src)
    def test_animate_ping(self):     self.assertIn("animate-ping", self.src)
    def test_running_stat(self):     self.assertIn("Running", self.src)
    def test_queued_stat(self):      self.assertIn("Queued", self.src)
    def test_errors_stat(self):      self.assertIn("Errors", self.src)
    def test_avg_latency_stat(self): self.assertIn("Avg Latency", self.src)
    def test_rate_used_stat(self):   self.assertIn("Rate Used", self.src)
    def test_diff_viewer_drawer(self): self.assertIn("Diff Viewer", self.src)
    def test_right_sidebar_layout(self): self.assertIn("w-[300px]", self.src)
    def test_bottom_drawer(self):    self.assertIn("h-[240px]", self.src)
    def test_cn_utility(self):       self.assertIn("cn(", self.src)
    def test_cursor_pointer(self):   self.assertIn("cursor-pointer", self.src)


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 28 — directory structure
# ══════════════════════════════════════════════════════════════════════════════

class TestSprint28DirectoryStructure(unittest.TestCase):
    def _exists(self, rel: str):
        return os.path.exists(os.path.join(ROOT, rel))

    # New components
    def test_guidance_dendrogram_file(self):
        self.assertTrue(self._exists("components/research/guidance-dendrogram.tsx"))

    def test_signal_dashboard_file(self):
        self.assertTrue(self._exists("components/research/signal-dashboard.tsx"))

    # New pages
    def test_research_page(self):
        self.assertTrue(self._exists("app/research/page.tsx"))

    def test_dashboard_page(self):
        self.assertTrue(self._exists("app/dashboard/page.tsx"))

    def test_projects_page(self):
        self.assertTrue(self._exists("app/projects/[id]/page.tsx"))

    def test_documents_page(self):
        self.assertTrue(self._exists("app/documents/[id]/page.tsx"))

    def test_agents_page(self):
        self.assertTrue(self._exists("app/agents/page.tsx"))

    # Sprint 27 components intact
    def test_predicate_selection_intact(self):
        self.assertTrue(self._exists("components/research/predicate-selection.tsx"))

    def test_evidence_chain_viewer_intact(self):
        self.assertTrue(self._exists("components/research/evidence-chain-viewer.tsx"))

    def test_guidance_inline_viewer_intact(self):
        self.assertTrue(self._exists("components/research/guidance-inline-viewer.tsx"))

    def test_citation_manager_intact(self):
        self.assertTrue(self._exists("components/research/citation-manager.tsx"))

    # Sprint 26 components intact
    def test_document_editor_intact(self):
        self.assertTrue(self._exists("components/editor/document-editor.tsx"))

    def test_ai_suggestion_overlay_intact(self):
        self.assertTrue(self._exists("components/editor/ai-suggestion-overlay.tsx"))

    def test_expert_assignment_interface_intact(self):
        self.assertTrue(self._exists("components/hitl/expert-assignment-interface.tsx"))

    # AI components intact
    def test_agentic_control_panel_intact(self):
        self.assertTrue(self._exists("components/ai/agentic-control-panel.tsx"))

    def test_agent_diff_viewer_intact(self):
        self.assertTrue(self._exists("components/ai/agent-diff-viewer.tsx"))


# ══════════════════════════════════════════════════════════════════════════════
# Cross-page integration checks
# ══════════════════════════════════════════════════════════════════════════════

class TestSprint28Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.research  = comp("app/research/page.tsx")
        cls.dashboard = comp("app/dashboard/page.tsx")
        cls.workspace = comp("app/projects/[id]/page.tsx")
        cls.docstudio = comp("app/documents/[id]/page.tsx")
        cls.agents    = comp("app/agents/page.tsx")
        cls.dendro    = comp("components/research/guidance-dendrogram.tsx")
        cls.signal    = comp("components/research/signal-dashboard.tsx")

    def test_research_page_wires_dendrogram(self):
        self.assertIn("GuidanceDendrogram", self.research)

    def test_research_page_wires_signal_dashboard(self):
        self.assertIn("SignalDashboard", self.research)

    def test_research_page_wires_predicate_selection(self):
        self.assertIn("PredicateSelection", self.research)

    def test_research_page_wires_evidence_chain(self):
        self.assertIn("EvidenceChainViewer", self.research)

    def test_research_page_wires_guidance_viewer(self):
        self.assertIn("GuidanceInlineViewer", self.research)

    def test_research_page_wires_citation_manager(self):
        self.assertIn("CitationManager", self.research)

    def test_workspace_links_to_research(self):
        self.assertIn("/research", self.workspace)

    def test_workspace_links_to_documents(self):
        self.assertIn("/documents", self.workspace)

    def test_dashboard_links_to_agents(self):
        self.assertIn("/agents", self.dashboard)

    def test_dashboard_links_to_projects(self):
        self.assertIn("/projects", self.dashboard)

    def test_doc_studio_wires_document_editor(self):
        self.assertIn("DocumentEditor", self.docstudio)

    def test_doc_studio_wires_ai_overlay(self):
        self.assertIn("AISuggestionOverlay", self.docstudio)

    def test_agents_page_wires_control_panel(self):
        self.assertIn("AgenticControlPanel", self.agents)

    def test_agents_page_wires_diff_viewer(self):
        self.assertIn("AgentDiffViewer", self.agents)

    def test_agents_page_wires_rate_limit_panel(self):
        self.assertIn("RateLimitPanel", self.agents)

    def test_agents_page_wires_error_recovery(self):
        self.assertIn("AgentErrorRecovery", self.agents)

    def test_all_pages_fda_blue(self):
        for name, src in [("research", self.research), ("dashboard", self.dashboard),
                          ("workspace", self.workspace), ("docstudio", self.docstudio),
                          ("agents", self.agents)]:
            with self.subTest(page=name):
                self.assertIn("#005EA2", src)

    def test_all_pages_use_client(self):
        for name, src in [("research", self.research), ("dashboard", self.dashboard),
                          ("workspace", self.workspace), ("docstudio", self.docstudio),
                          ("agents", self.agents)]:
            with self.subTest(page=name):
                self.assertIn('"use client"', src)

    def test_all_pages_default_export(self):
        for name, src in [("research", self.research), ("dashboard", self.dashboard),
                          ("workspace", self.workspace), ("docstudio", self.docstudio),
                          ("agents", self.agents)]:
            with self.subTest(page=name):
                self.assertIn("export default function", src)

    def test_dendrogram_no_d3_dependency(self):
        self.assertNotIn("from 'd3'", self.dendro)
        self.assertNotIn('from "d3"', self.dendro)

    def test_signal_dashboard_csv_export(self):
        self.assertIn("text/csv", self.signal)

    def test_21_cfr_part11_across_pages(self):
        # Both workspace and doc studio reference Part 11 audit
        self.assertIn("21 CFR Part 11", self.workspace)
        self.assertIn("21 CFR Part 11", self.docstudio)


if __name__ == "__main__":
    unittest.main()
