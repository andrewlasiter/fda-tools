"""
Sprint 22 — Complete Next.js 14 + shadcn/ui + Tremor Scaffold
==============================================================
Tests verify that FDA-221 (version assertion fix) and FDA-222 (Next.js
scaffold completion) acceptance criteria are fully met.

FDA-221: Fix test_accessgudid.py version assertion (5.22.0 → 5.36.0)
FDA-222: Next.js 14 + shadcn/ui + Tremor + dark mode + fonts
"""

from __future__ import annotations

import json
import re
from pathlib import Path

WEB = Path(__file__).parents[3] / "web"
TESTS = Path(__file__).parent

# ── Helpers ──────────────────────────────────────────────────────────────────

def read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def has(rel: str) -> bool:
    return (WEB / rel).exists()


def contains(rel: str, pattern: str) -> bool:
    return bool(re.search(pattern, read(rel)))


# ── FDA-221: Version assertion fix ───────────────────────────────────────────

class TestVersionAssertionFix:
    """FDA-221: test_accessgudid.py must assert version == 5.36.0."""

    def test_stale_5_22_0_removed(self):
        content = (TESTS / "test_accessgudid.py").read_text()
        assert "5.22.0" not in content, "Stale 5.22.0 assertion still present"

    def test_current_5_36_0_asserted(self):
        content = (TESTS / "test_accessgudid.py").read_text()
        assert "5.36.0" in content

    def test_test_method_name_updated(self):
        content = (TESTS / "test_accessgudid.py").read_text()
        # Old stale method name should be gone
        assert "test_version_is_5_9_0" not in content

    def test_plugin_json_is_5_36_0(self):
        # parents: tests -> fda_tools -> plugins -> fda-tools
        plugin_json = Path(__file__).parents[1] / ".claude-plugin" / "plugin.json"
        data = json.loads(plugin_json.read_text())
        assert data["version"] == "5.36.0"


# ── FDA-222: Package.json completeness ───────────────────────────────────────

class TestPackageJsonComplete:
    """FDA-222: package.json has all required dependencies."""

    def _pkg(self):
        return json.loads(read("package.json"))

    def test_next_14(self):
        assert "14." in self._pkg()["dependencies"]["next"]

    def test_tailwindcss(self):
        assert "tailwindcss" in self._pkg()["devDependencies"]

    def test_autoprefixer(self):
        assert "autoprefixer" in self._pkg()["devDependencies"]

    def test_postcss(self):
        assert "postcss" in self._pkg()["devDependencies"]

    def test_next_themes(self):
        assert "next-themes" in self._pkg()["dependencies"]

    def test_tremor(self):
        assert "@tremor/react" in self._pkg()["dependencies"]

    def test_radix_slot(self):
        assert "@radix-ui/react-slot" in self._pkg()["dependencies"]

    def test_class_variance_authority(self):
        assert "class-variance-authority" in self._pkg()["dependencies"]

    def test_clsx(self):
        assert "clsx" in self._pkg()["dependencies"]

    def test_tailwind_merge(self):
        assert "tailwind-merge" in self._pkg()["dependencies"]

    def test_lucide_react(self):
        assert "lucide-react" in self._pkg()["dependencies"]

    def test_type_check_script(self):
        assert "type-check" in self._pkg()["scripts"]

    def test_dev_script(self):
        assert "dev" in self._pkg()["scripts"]


# ── FDA-222: Tailwind config ──────────────────────────────────────────────────

class TestTailwindConfig:
    """FDA-222: tailwind.config.ts with FDA tokens and dark mode."""

    def test_file_exists(self):
        assert has("tailwind.config.ts")

    def test_dark_mode_class(self):
        assert contains("tailwind.config.ts", r"darkMode.*class")

    def test_content_includes_app(self):
        assert contains("tailwind.config.ts", r"app/\*\*/\*")

    def test_content_includes_components(self):
        assert contains("tailwind.config.ts", r"components/\*\*/\*")

    def test_fda_blue_color(self):
        assert contains("tailwind.config.ts", r"005EA2")

    def test_semantic_primary_token(self):
        assert contains("tailwind.config.ts", r"primary")

    def test_border_radius_variable(self):
        assert contains("tailwind.config.ts", r"--radius")

    def test_heading_font_variable(self):
        assert contains("tailwind.config.ts", r"--font-heading")

    def test_sans_font_variable(self):
        assert contains("tailwind.config.ts", r"--font-sans")

    def test_tremor_content_included(self):
        # Tremor components must be included in content scan
        assert contains("tailwind.config.ts", r"@tremor")


# ── FDA-222: PostCSS config ───────────────────────────────────────────────────

class TestPostcssConfig:
    """FDA-222: postcss.config.js with tailwindcss + autoprefixer plugins."""

    def test_file_exists(self):
        assert has("postcss.config.js")

    def test_tailwindcss_plugin(self):
        assert contains("postcss.config.js", r"tailwindcss")

    def test_autoprefixer_plugin(self):
        assert contains("postcss.config.js", r"autoprefixer")


# ── FDA-222: globals.css ──────────────────────────────────────────────────────

class TestGlobalsCss:
    """FDA-222: globals.css with Tailwind directives and shadcn/ui CSS vars."""

    def test_tailwind_base(self):
        assert contains("app/globals.css", r"@tailwind base")

    def test_tailwind_components(self):
        assert contains("app/globals.css", r"@tailwind components")

    def test_tailwind_utilities(self):
        assert contains("app/globals.css", r"@tailwind utilities")

    def test_shadcn_background_var(self):
        assert contains("app/globals.css", r"--background")

    def test_shadcn_primary_var(self):
        assert contains("app/globals.css", r"--primary")

    def test_dark_mode_block(self):
        assert contains("app/globals.css", r"\.dark\s*\{")

    def test_fda_blue_token(self):
        assert contains("app/globals.css", r"--color-fda-blue")

    def test_border_radius_var(self):
        assert contains("app/globals.css", r"--radius")


# ── FDA-222: Root layout with fonts ──────────────────────────────────────────

class TestRootLayout:
    """FDA-222: layout.tsx loads Plus Jakarta Sans + Inter and wraps Providers."""

    def test_plus_jakarta_import(self):
        assert contains("app/layout.tsx", r"Plus_Jakarta_Sans")

    def test_inter_import(self):
        assert contains("app/layout.tsx", r"Inter")

    def test_font_variable_heading(self):
        assert contains("app/layout.tsx", r"--font-heading")

    def test_font_variable_sans(self):
        assert contains("app/layout.tsx", r"--font-sans")

    def test_suppress_hydration_warning(self):
        assert contains("app/layout.tsx", r"suppressHydrationWarning")

    def test_providers_wrap(self):
        assert contains("app/layout.tsx", r"Providers")

    def test_metadata_export(self):
        assert contains("app/layout.tsx", r"export const metadata")


# ── FDA-222: Root page redirect ───────────────────────────────────────────────

class TestRootPage:
    """FDA-222: / redirects to /dashboard."""

    def test_file_exists(self):
        assert has("app/page.tsx")

    def test_redirects_to_dashboard(self):
        assert contains("app/page.tsx", r"/dashboard")

    def test_uses_redirect(self):
        assert contains("app/page.tsx", r"redirect")


# ── FDA-222: Providers with dark mode ────────────────────────────────────────

class TestProvidersWithDarkMode:
    """FDA-222: Providers wraps ThemeProvider from next-themes."""

    def test_theme_provider_import(self):
        assert contains("components/providers.tsx", r"ThemeProvider")

    def test_next_themes_import(self):
        assert contains("components/providers.tsx", r"next-themes")

    def test_attribute_class(self):
        assert contains("components/providers.tsx", r'attribute="class"')

    def test_default_theme_system(self):
        assert contains("components/providers.tsx", r"defaultTheme")

    def test_enable_system(self):
        assert contains("components/providers.tsx", r"enableSystem")


# ── FDA-222: shadcn/ui Button ─────────────────────────────────────────────────

class TestButtonComponent:
    """FDA-222: components/ui/button.tsx with variants."""

    def test_file_exists(self):
        assert has("components/ui/button.tsx")

    def test_uses_cva(self):
        assert contains("components/ui/button.tsx", r"cva")

    def test_uses_slot(self):
        assert contains("components/ui/button.tsx", r"Slot")

    def test_variant_default(self):
        assert contains("components/ui/button.tsx", r"default")

    def test_variant_destructive(self):
        assert contains("components/ui/button.tsx", r"destructive")

    def test_variant_outline(self):
        assert contains("components/ui/button.tsx", r"outline")

    def test_variant_ghost(self):
        assert contains("components/ui/button.tsx", r"ghost")

    def test_size_sm(self):
        assert contains("components/ui/button.tsx", r"\bsm\b")

    def test_size_lg(self):
        assert contains("components/ui/button.tsx", r"\blg\b")

    def test_size_icon(self):
        assert contains("components/ui/button.tsx", r"\bicon\b")

    def test_exports_button(self):
        assert contains("components/ui/button.tsx", r"export.*Button")

    def test_exports_button_variants(self):
        assert contains("components/ui/button.tsx", r"export.*buttonVariants")

    def test_as_child_prop(self):
        assert contains("components/ui/button.tsx", r"asChild")

    def test_forward_ref(self):
        assert contains("components/ui/button.tsx", r"forwardRef")


# ── FDA-222: shadcn/ui Card ───────────────────────────────────────────────────

class TestCardComponent:
    """FDA-222: components/ui/card.tsx with sub-components."""

    def test_file_exists(self):
        assert has("components/ui/card.tsx")

    def test_exports_card(self):
        content = read("components/ui/card.tsx")
        assert "export" in content and re.search(r"\bCard\b", content)

    def test_exports_card_header(self):
        assert contains("components/ui/card.tsx", r"CardHeader")

    def test_exports_card_title(self):
        assert contains("components/ui/card.tsx", r"CardTitle")

    def test_exports_card_description(self):
        assert contains("components/ui/card.tsx", r"CardDescription")

    def test_exports_card_content(self):
        assert contains("components/ui/card.tsx", r"CardContent")

    def test_exports_card_footer(self):
        assert contains("components/ui/card.tsx", r"CardFooter")

    def test_uses_cn(self):
        assert contains("components/ui/card.tsx", r"\bcn\b")

    def test_uses_forward_ref(self):
        assert contains("components/ui/card.tsx", r"forwardRef")

    def test_border_and_shadow(self):
        assert contains("components/ui/card.tsx", r"shadow-sm")


# ── FDA-222: shadcn/ui Badge ──────────────────────────────────────────────────

class TestBadgeComponent:
    """FDA-222: components/ui/badge.tsx with variants including success/warning."""

    def test_file_exists(self):
        assert has("components/ui/badge.tsx")

    def test_exports_badge(self):
        assert contains("components/ui/badge.tsx", r"export.*\bBadge\b")

    def test_exports_badge_variants(self):
        assert contains("components/ui/badge.tsx", r"export.*badgeVariants")

    def test_uses_cva(self):
        assert contains("components/ui/badge.tsx", r"cva")

    def test_variant_default(self):
        assert contains("components/ui/badge.tsx", r"default")

    def test_variant_secondary(self):
        assert contains("components/ui/badge.tsx", r"secondary")

    def test_variant_destructive(self):
        assert contains("components/ui/badge.tsx", r"destructive")

    def test_variant_success(self):
        # FDA-specific: regulatory status indicators need success/warning
        assert contains("components/ui/badge.tsx", r"success")

    def test_variant_warning(self):
        assert contains("components/ui/badge.tsx", r"warning")


# ── FDA-222: shadcn/ui Input ──────────────────────────────────────────────────

class TestInputComponent:
    """FDA-222: components/ui/input.tsx."""

    def test_file_exists(self):
        assert has("components/ui/input.tsx")

    def test_exports_input(self):
        assert contains("components/ui/input.tsx", r"export.*\bInput\b")

    def test_forward_ref(self):
        assert contains("components/ui/input.tsx", r"forwardRef")

    def test_uses_cn(self):
        assert contains("components/ui/input.tsx", r"\bcn\b")

    def test_ring_focus_styles(self):
        assert contains("components/ui/input.tsx", r"focus-visible:ring")

    def test_disabled_styles(self):
        assert contains("components/ui/input.tsx", r"disabled:")
