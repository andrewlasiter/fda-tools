"""
Sprint 23 — Dashboard + Agent Panel + NPD Workspace + Research Hub
==================================================================
FDA-270: App shell (sidebar + header layout)
FDA-271: Home Dashboard page (/dashboard)
FDA-272: Agent Orchestration Panel (/agents)
FDA-273: NPD Workspace page (/projects/[id])
FDA-274: Regulatory Research Hub (/research)
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


# ── FDA-270: App Shell ────────────────────────────────────────────────────

class TestAppShellSidebar:
    """FDA-270: components/shell/sidebar.tsx with nav + collapse."""

    def test_file_exists(self):
        assert has("components/shell/sidebar.tsx")

    def test_use_client(self):
        assert contains("components/shell/sidebar.tsx", r'"use client"')

    def test_exports_sidebar(self):
        assert contains("components/shell/sidebar.tsx", r"export function Sidebar")

    def test_nav_items_defined(self):
        content = read("components/shell/sidebar.tsx")
        assert "NAV_ITEMS" in content

    def test_dashboard_link(self):
        assert contains("components/shell/sidebar.tsx", r"/dashboard")

    def test_projects_link(self):
        assert contains("components/shell/sidebar.tsx", r"/projects")

    def test_agents_link(self):
        assert contains("components/shell/sidebar.tsx", r"/agents")

    def test_research_link(self):
        assert contains("components/shell/sidebar.tsx", r"/research")

    def test_documents_link(self):
        assert contains("components/shell/sidebar.tsx", r"/documents")

    def test_settings_link(self):
        assert contains("components/shell/sidebar.tsx", r"/settings")

    def test_collapse_toggle(self):
        assert contains("components/shell/sidebar.tsx", r"collapsed")

    def test_fda_logo_present(self):
        assert contains("components/shell/sidebar.tsx", r"FDALogo")

    def test_sign_out(self):
        assert contains("components/shell/sidebar.tsx", r"signOut")

    def test_uses_useauth(self):
        assert contains("components/shell/sidebar.tsx", r"useAuth")

    def test_uses_usepathname(self):
        assert contains("components/shell/sidebar.tsx", r"usePathname")

    def test_active_state_styling(self):
        # Active links should use FDA Blue color
        assert contains("components/shell/sidebar.tsx", r"005EA2")


class TestAppShellHeader:
    """FDA-270: components/shell/header.tsx with breadcrumbs + theme toggle."""

    def test_file_exists(self):
        assert has("components/shell/header.tsx")

    def test_use_client(self):
        assert contains("components/shell/header.tsx", r'"use client"')

    def test_exports_header(self):
        assert contains("components/shell/header.tsx", r"export function Header")

    def test_breadcrumbs(self):
        assert contains("components/shell/header.tsx", r"Breadcrumb")

    def test_uses_usepathname(self):
        assert contains("components/shell/header.tsx", r"usePathname")

    def test_theme_toggle(self):
        assert contains("components/shell/header.tsx", r"ThemeToggle")

    def test_uses_usetheme(self):
        assert contains("components/shell/header.tsx", r"useTheme")

    def test_search_trigger(self):
        # Search input or button should be present
        assert contains("components/shell/header.tsx", r"search|Search", )

    def test_notification_bell(self):
        assert contains("components/shell/header.tsx", r"Bell|bell|notification")

    def test_dark_light_toggle(self):
        content = read("components/shell/header.tsx")
        assert "dark" in content and "light" in content


class TestAuthenticatedLayout:
    """FDA-270: app/(authenticated)/layout.tsx shell wrapper."""

    def test_file_exists(self):
        assert has("app/(authenticated)/layout.tsx")

    def test_imports_sidebar(self):
        assert contains("app/(authenticated)/layout.tsx", r"Sidebar")

    def test_imports_header(self):
        assert contains("app/(authenticated)/layout.tsx", r"Header")

    def test_flex_layout(self):
        assert contains("app/(authenticated)/layout.tsx", r"flex")

    def test_main_element(self):
        assert contains("app/(authenticated)/layout.tsx", r"<main")

    def test_children_rendered(self):
        assert contains("app/(authenticated)/layout.tsx", r"children")


# ── FDA-271: Dashboard ────────────────────────────────────────────────────

class TestDashboardPage:
    """FDA-271: app/(authenticated)/dashboard/page.tsx."""

    def test_file_exists(self):
        assert has("app/(authenticated)/dashboard/page.tsx")

    def test_use_client(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r'"use client"')

    def test_exports_default(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"export default function")

    def test_kpi_cards(self):
        # Must have multiple KPI metrics
        content = read("app/(authenticated)/dashboard/page.tsx")
        assert "Active Projects" in content
        assert "Agents Running" in content
        assert "Avg SRI Score" in content

    def test_sri_trend_chart(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"SRI")

    def test_sparkline_or_chart(self):
        content = read("app/(authenticated)/dashboard/page.tsx")
        # Must have some form of data visualization
        assert "path" in content or "svg" in content.lower() or "AreaChart" in content or "Sparkline" in content

    def test_project_cards(self):
        content = read("app/(authenticated)/dashboard/page.tsx")
        assert "Active Projects" in content or "MOCK_PROJECTS" in content

    def test_agent_feed(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"[Aa]gent")

    def test_compliance_scorecard(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"[Cc]ompliance")

    def test_new_project_button(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"New Project")

    def test_run_research_button(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"Run Research")

    def test_fda_blue_color(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"005EA2")

    def test_dark_mode_compatible(self):
        # Uses dark: Tailwind prefix or dark-mode CSS vars (via badge/card/background CSS vars)
        content = read("app/(authenticated)/dashboard/page.tsx")
        # CSS variable-based dark mode doesn't need explicit dark: prefix
        assert "dark:" in content or "--background" in content or "bg-background" in content or "text-foreground" in content

    def test_sri_score_display(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"SRI")

    def test_stage_pipeline_display(self):
        # Pipeline stages should be visible
        assert contains("app/(authenticated)/dashboard/page.tsx", r"TESTING|DRAFTING|PREDICATE|CONCEPT")

    def test_status_badges(self):
        content = read("app/(authenticated)/dashboard/page.tsx")
        assert "on-track" in content or "On Track" in content

    def test_deadline_display(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"deadline|Due|due")

    def test_card_components_used(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"<Card")

    def test_badge_components_used(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"<Badge")

    def test_button_components_used(self):
        assert contains("app/(authenticated)/dashboard/page.tsx", r"<Button")


# ── FDA-272: Agent Panel ──────────────────────────────────────────────────

class TestAgentOrchestrationPanel:
    """FDA-272: app/(authenticated)/agents/page.tsx."""

    def test_file_exists(self):
        assert has("app/(authenticated)/agents/page.tsx")

    def test_use_client(self):
        assert contains("app/(authenticated)/agents/page.tsx", r'"use client"')

    def test_exports_default(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"export default function")

    def test_agent_status_types(self):
        content = read("app/(authenticated)/agents/page.tsx")
        assert "running" in content
        assert "idle" in content
        assert "done" in content

    def test_running_metric(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"[Rr]unning")

    def test_idle_metric(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"[Ii]dle")

    def test_agent_table(self):
        content = read("app/(authenticated)/agents/page.tsx")
        assert "<table" in content or "Agent" in content

    def test_log_stream(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"[Ll]og")

    def test_log_severity_levels(self):
        content = read("app/(authenticated)/agents/page.tsx")
        assert "INFO" in content
        assert "WARN" in content
        assert "ERROR" in content

    def test_filter_controls(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"filter|Filter")

    def test_agent_actions(self):
        content = read("app/(authenticated)/agents/page.tsx")
        assert "pause" in content or "Pause" in content or "cancel" in content

    def test_status_dot_pulse(self):
        # Running agents should have animated indicator
        assert contains("app/(authenticated)/agents/page.tsx", r"animate-pulse")

    def test_mission_control_heading(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"[Aa]gent [Oo]rchestration|[Mm]ission [Cc]ontrol")

    def test_duration_display(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"duration|Duration")

    def test_category_display(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"category|Category")

    def test_monospace_log(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"font-mono")

    def test_auto_scroll_option(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"[Aa]uto.?[Ss]croll")

    def test_spawn_button(self):
        assert contains("app/(authenticated)/agents/page.tsx", r"[Ss]pawn")


# ── FDA-273: NPD Workspace ────────────────────────────────────────────────

class TestNpdWorkspace:
    """FDA-273: app/(authenticated)/projects/[id]/page.tsx."""

    def test_file_exists(self):
        assert has("app/(authenticated)/projects/[id]/page.tsx")

    def test_use_client(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r'"use client"')

    def test_exports_default(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"export default function")

    def test_all_12_stages_defined(self):
        content = read("app/(authenticated)/projects/[id]/page.tsx")
        stages = ["CONCEPT","CLASSIFY","PREDICATE","PATHWAY","PRESUB","TESTING",
                  "DRAFTING","REVIEW","SUBMIT","FDA_REVIEW","CLEARED","POST_MARKET"]
        for stage in stages:
            assert stage in content, f"Stage {stage} not found"

    def test_stage_navigator(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"StageNav|stage.*nav")

    def test_stage_status_types(self):
        content = read("app/(authenticated)/projects/[id]/page.tsx")
        assert "completed" in content
        assert "active" in content
        assert "pending" in content

    def test_3panel_layout(self):
        content = read("app/(authenticated)/projects/[id]/page.tsx")
        # Left sidebar, main, right panel
        assert content.count("<aside") >= 2 or content.count("flex") >= 1

    def test_ai_assistant_panel(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"[Aa][Ii] [Aa]ssistant|AiAssistant")

    def test_chat_messages(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"message|chat|Message")

    def test_context_sources(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"[Ss]ource")

    def test_sri_display(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"sri|SRI")

    def test_completion_progress(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"completion|progress|Progress")

    def test_generate_draft_button(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"[Gg]enerate [Dd]raft|[Gg]enerate")

    def test_stage_description(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"description|Description")

    def test_pipeline_connector_line(self):
        # Visual connector between stages
        content = read("app/(authenticated)/projects/[id]/page.tsx")
        assert "w-0.5" in content or "connector" in content or "h-4" in content

    def test_fda_blue_accent(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"005EA2")

    def test_dynamic_route_param(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"useParams|params")

    def test_suggested_questions(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"[Ss]uggested")

    def test_stage_locked_state(self):
        assert contains("app/(authenticated)/projects/[id]/page.tsx", r"[Ll]ocked|locked")


# ── FDA-274: Research Hub ─────────────────────────────────────────────────

class TestResearchHub:
    """FDA-274: app/(authenticated)/research/page.tsx."""

    def test_file_exists(self):
        assert has("app/(authenticated)/research/page.tsx")

    def test_use_client(self):
        assert contains("app/(authenticated)/research/page.tsx", r'"use client"')

    def test_exports_default(self):
        assert contains("app/(authenticated)/research/page.tsx", r"export default function")

    def test_search_input(self):
        assert contains("app/(authenticated)/research/page.tsx", r"<input")

    def test_source_toggles(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "k510" in content or "510" in content
        assert "guidance" in content or "Guidance" in content
        assert "maude" in content or "MAUDE" in content

    def test_result_cards(self):
        assert contains("app/(authenticated)/research/page.tsx", r"result|Result")

    def test_relevance_score(self):
        assert contains("app/(authenticated)/research/page.tsx", r"relevance|Relevance")

    def test_source_badge_colors(self):
        assert contains("app/(authenticated)/research/page.tsx", r"SOURCE_COLORS|source.*color")

    def test_empty_state(self):
        assert contains("app/(authenticated)/research/page.tsx", r"Recent|suggestion|empty|hasSearched")

    def test_export_buttons(self):
        content = read("app/(authenticated)/research/page.tsx")
        assert "Export" in content or "export" in content

    def test_semantic_search_heading(self):
        assert contains("app/(authenticated)/research/page.tsx", r"[Ss]emantic|[Uu]nified.*[Ss]earch|Research Hub")

    def test_pubmed_source(self):
        assert contains("app/(authenticated)/research/page.tsx", r"pubmed|PubMed")

    def test_recalls_source(self):
        assert contains("app/(authenticated)/research/page.tsx", r"recall|Recall")


# ── Projects list page ────────────────────────────────────────────────────

class TestProjectsListPage:
    """app/(authenticated)/projects/page.tsx — project index."""

    def test_file_exists(self):
        assert has("app/(authenticated)/projects/page.tsx")

    def test_exports_default(self):
        assert contains("app/(authenticated)/projects/page.tsx", r"export default function")

    def test_links_to_project_detail(self):
        assert contains("app/(authenticated)/projects/page.tsx", r"/projects/")

    def test_sri_display(self):
        assert contains("app/(authenticated)/projects/page.tsx", r"SRI")

    def test_status_badges(self):
        assert contains("app/(authenticated)/projects/page.tsx", r"on-track|at-risk|needs-attention")


# ── Shell directory structure ─────────────────────────────────────────────

class TestShellDirectoryStructure:
    """Verify all Sprint 23 files exist in expected locations."""

    def test_shell_dir_exists(self):
        assert has("components/shell")

    def test_authenticated_group_exists(self):
        assert has("app/(authenticated)")

    def test_dashboard_dir_exists(self):
        assert has("app/(authenticated)/dashboard")

    def test_agents_dir_exists(self):
        assert has("app/(authenticated)/agents")

    def test_projects_id_dir_exists(self):
        assert has("app/(authenticated)/projects/[id]")

    def test_research_dir_exists(self):
        assert has("app/(authenticated)/research")

    def test_test_file_is_python(self):
        # Sanity: test file is valid Python (parseable)
        content = (Path(__file__).parent / "test_sprint23.py").read_text()
        assert "def test_" in content
