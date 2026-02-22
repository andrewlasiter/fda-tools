"""
Sprint 21 — Supabase Auth + FastAPI REST Client
================================================
Tests verify that all Sprint 21 files exist, export the required symbols,
reference the correct environment variables, and implement the required
acceptance criteria from the Linear issues.

FDA-225 [FE-002]: Supabase Auth integration
FDA-226 [FE-006]: FastAPI → Next.js REST client + TypeScript types

Since these are TypeScript files, tests use file-system checks and regex
pattern matching to validate structure — the same way a CI lint step would.
"""

from __future__ import annotations

import re
from pathlib import Path

# ── Helpers ──────────────────────────────────────────────────────────────────

WEB = Path(__file__).parents[3] / "web"


def read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def has(rel: str) -> bool:
    return (WEB / rel).exists()


def contains(rel: str, pattern: str) -> bool:
    return bool(re.search(pattern, read(rel)))


def contains_all(rel: str, patterns: list[str]) -> bool:
    content = read(rel)
    return all(bool(re.search(p, content)) for p in patterns)


# ── Scaffold files ────────────────────────────────────────────────────────────

class TestScaffoldFiles:
    """FE-001 scaffold: package.json, tsconfig, next.config, layout, globals."""

    def test_package_json_exists(self):
        assert has("package.json")

    def test_package_json_next14(self):
        assert contains("package.json", r'"next":\s*"14\.')

    def test_package_json_supabase_ssr(self):
        assert contains("package.json", r"@supabase/ssr")

    def test_package_json_tanstack_query(self):
        assert contains("package.json", r"@tanstack/react-query")

    def test_package_json_axios(self):
        assert contains("package.json", r'"axios"')

    def test_tsconfig_exists(self):
        assert has("tsconfig.json")

    def test_tsconfig_strict_mode(self):
        assert contains("tsconfig.json", r'"strict":\s*true')

    def test_tsconfig_path_alias(self):
        # @/* maps to ./*
        assert contains("tsconfig.json", r'"@/\*"')

    def test_next_config_exists(self):
        assert has("next.config.ts")

    def test_next_config_documents_env_vars(self):
        assert contains("next.config.ts", r"NEXT_PUBLIC_SUPABASE_URL")
        assert contains("next.config.ts", r"NEXT_PUBLIC_API_URL")

    def test_root_layout_exists(self):
        assert has("app/layout.tsx")

    def test_root_layout_uses_providers(self):
        assert contains("app/layout.tsx", r"Providers")

    def test_globals_css_exists(self):
        assert has("app/globals.css")

    def test_globals_css_fda_blue(self):
        assert contains("app/globals.css", r"--color-fda-blue")


# ── FDA-225: lib/supabase.ts ─────────────────────────────────────────────────

class TestSupabaseClientFile:
    """FDA-225 acceptance: lib/supabase.ts singleton client."""

    def test_file_exists(self):
        assert has("lib/supabase.ts")

    def test_uses_supabase_ssr(self):
        assert contains("lib/supabase.ts", r"@supabase/ssr")

    def test_browser_client_singleton(self):
        # Must export getSupabaseClient function
        assert contains("lib/supabase.ts", r"export function getSupabaseClient")

    def test_env_var_supabase_url(self):
        assert contains("lib/supabase.ts", r"NEXT_PUBLIC_SUPABASE_URL")

    def test_env_var_supabase_anon_key(self):
        assert contains("lib/supabase.ts", r"NEXT_PUBLIC_SUPABASE_ANON_KEY")

    def test_magic_link_export(self):
        assert contains("lib/supabase.ts", r"export.*signInWithMagicLink")

    def test_oauth_export(self):
        assert contains("lib/supabase.ts", r"export.*signInWithOAuth")

    def test_sign_out_export(self):
        assert contains("lib/supabase.ts", r"export.*signOut")

    def test_get_access_token_export(self):
        # Required by api-client.ts for Authorization header injection
        assert contains("lib/supabase.ts", r"export.*getAccessToken")

    def test_oauth_provider_type(self):
        assert contains("lib/supabase.ts", r"OAuthProvider")

    def test_auth_callback_redirect(self):
        # Magic link redirects to /auth/callback
        assert contains("lib/supabase.ts", r"auth/callback")


# ── FDA-225: lib/supabase-server.ts ─────────────────────────────────────────

class TestSupabaseServerFile:
    """FDA-225 acceptance: server-side Supabase client for SSR and middleware."""

    def test_file_exists(self):
        assert has("lib/supabase-server.ts")

    def test_exports_server_client(self):
        assert contains("lib/supabase-server.ts", r"export.*createSupabaseServerClient")

    def test_exports_middleware_client(self):
        assert contains("lib/supabase-server.ts", r"export.*createSupabaseMiddlewareClient")

    def test_uses_cookies_api(self):
        assert contains("lib/supabase-server.ts", r"next/headers")

    def test_exports_get_server_user(self):
        assert contains("lib/supabase-server.ts", r"export.*getServerUser")


# ── FDA-225: middleware.ts ───────────────────────────────────────────────────

class TestMiddlewareFile:
    """FDA-225 acceptance: middleware protecting /dashboard/** routes."""

    def test_file_exists(self):
        assert has("middleware.ts")

    def test_exports_middleware_function(self):
        assert contains("middleware.ts", r"export.*async function middleware")

    def test_protects_dashboard_routes(self):
        assert contains("middleware.ts", r"/dashboard")

    def test_redirects_to_login(self):
        assert contains("middleware.ts", r"/auth/login")

    def test_preserves_next_param(self):
        # Saves the intended destination for post-login redirect
        assert contains("middleware.ts", r'"next"')

    def test_exports_matcher_config(self):
        assert contains("middleware.ts", r"export const config")

    def test_matcher_excludes_static(self):
        assert contains("middleware.ts", r"_next/static")

    def test_session_refresh(self):
        # Middleware must refresh session to keep Supabase tokens alive
        assert contains("middleware.ts", r"getUser|refreshSession|getSession")


# ── FDA-225: auth/login page ─────────────────────────────────────────────────

class TestAuthLoginPage:
    """FDA-225 acceptance: /auth/login page with magic link + OAuth."""

    def test_file_exists(self):
        assert has("app/auth/login/page.tsx")

    def test_use_client_directive(self):
        assert contains("app/auth/login/page.tsx", r'"use client"')

    def test_magic_link_form(self):
        assert contains("app/auth/login/page.tsx", r"signInWithMagicLink")

    def test_oauth_google(self):
        assert contains("app/auth/login/page.tsx", r"google")

    def test_oauth_github(self):
        assert contains("app/auth/login/page.tsx", r"github")

    def test_email_input(self):
        assert contains("app/auth/login/page.tsx", r'type="email"')

    def test_default_export(self):
        assert contains("app/auth/login/page.tsx", r"export default function Login")


# ── FDA-225: auth callback route ─────────────────────────────────────────────

class TestAuthCallbackRoute:
    """FDA-225: /auth/callback route handler exchanges code for session."""

    def test_file_exists(self):
        assert has("app/auth/callback/route.ts")

    def test_exchanges_code_for_session(self):
        assert contains("app/auth/callback/route.ts", r"exchangeCodeForSession")

    def test_handles_next_redirect(self):
        assert contains("app/auth/callback/route.ts", r'"next"')

    def test_error_redirects_to_login(self):
        assert contains("app/auth/callback/route.ts", r"auth/login")


# ── FDA-225: auth context ────────────────────────────────────────────────────

class TestAuthContext:
    """FDA-225 acceptance: auth state in React context."""

    def test_file_exists(self):
        assert has("contexts/auth-context.tsx")

    def test_use_client_directive(self):
        assert contains("contexts/auth-context.tsx", r'"use client"')

    def test_auth_provider_export(self):
        assert contains("contexts/auth-context.tsx", r"export function AuthProvider")

    def test_use_auth_hook_export(self):
        assert contains("contexts/auth-context.tsx", r"export function useAuth")

    def test_session_state(self):
        assert contains("contexts/auth-context.tsx", r"session")

    def test_user_state(self):
        assert contains("contexts/auth-context.tsx", r"user")

    def test_loading_state(self):
        assert contains("contexts/auth-context.tsx", r"loading")

    def test_sign_out_method(self):
        assert contains("contexts/auth-context.tsx", r"signOut")

    def test_is_authenticated_flag(self):
        assert contains("contexts/auth-context.tsx", r"isAuthenticated")

    def test_auth_state_change_subscription(self):
        assert contains("contexts/auth-context.tsx", r"onAuthStateChange")

    def test_unsubscribe_on_unmount(self):
        assert contains("contexts/auth-context.tsx", r"unsubscribe")

    def test_throws_outside_provider(self):
        assert contains("contexts/auth-context.tsx", r"useAuth must be used inside")


# ── FDA-226: lib/api-client.ts ───────────────────────────────────────────────

class TestApiClientFile:
    """FDA-226 acceptance: typed REST client."""

    def test_file_exists(self):
        assert has("lib/api-client.ts")

    def test_base_url_env_var(self):
        assert contains("lib/api-client.ts", r"NEXT_PUBLIC_API_URL")

    def test_api_key_env_var(self):
        assert contains("lib/api-client.ts", r"NEXT_PUBLIC_FDA_API_KEY")

    def test_x_api_key_header(self):
        assert contains("lib/api-client.ts", r"X-API-Key")

    def test_auth_token_injection(self):
        # Supabase access token injected into Authorization header
        assert contains("lib/api-client.ts", r"getAccessToken")
        assert contains("lib/api-client.ts", r"Authorization.*Bearer")

    def test_api_error_type(self):
        assert contains("lib/api-client.ts", r"export interface APIError")

    def test_validation_error_type(self):
        assert contains("lib/api-client.ts", r"export interface ValidationError")

    def test_fda_client_error_union(self):
        assert contains("lib/api-client.ts", r"export type FDAClientError")

    def test_health_response_type(self):
        assert contains("lib/api-client.ts", r"export interface HealthResponse")

    def test_execute_request_type(self):
        assert contains("lib/api-client.ts", r"export interface ExecuteRequest")

    def test_execute_response_type(self):
        assert contains("lib/api-client.ts", r"export interface ExecuteResponse")

    def test_session_info_type(self):
        assert contains("lib/api-client.ts", r"export interface SessionInfo")

    def test_command_info_type(self):
        assert contains("lib/api-client.ts", r"export interface CommandInfo")

    def test_pending_question_type(self):
        assert contains("lib/api-client.ts", r"export interface PendingQuestion")

    def test_audit_integrity_type(self):
        assert contains("lib/api-client.ts", r"export interface AuditIntegrityResponse")


class TestApiClientEndpoints:
    """FDA-226: fdaApi covers all FastAPI bridge endpoints."""

    def test_health_endpoint(self):
        assert contains("lib/api-client.ts", r'"/health"')

    def test_execute_endpoint(self):
        assert contains("lib/api-client.ts", r'"/execute"')

    def test_commands_endpoint(self):
        assert contains("lib/api-client.ts", r'"/commands"')

    def test_tools_endpoint(self):
        assert contains("lib/api-client.ts", r'"/tools"')

    def test_session_post_endpoint(self):
        assert contains("lib/api-client.ts", r'"/session"')

    def test_sessions_list_endpoint(self):
        assert contains("lib/api-client.ts", r'"/sessions"')

    def test_questions_endpoint(self):
        assert contains("lib/api-client.ts", r"questions")

    def test_answer_endpoint(self):
        assert contains("lib/api-client.ts", r"answer")

    def test_audit_endpoint(self):
        assert contains("lib/api-client.ts", r"audit/integrity")


class TestApiClientQueryKeys:
    """FDA-226: query key factory for React Query cache management."""

    def test_query_keys_exported(self):
        assert contains("lib/api-client.ts", r"export const queryKeys")

    def test_health_key(self):
        assert contains("lib/api-client.ts", r'"health"')

    def test_commands_key(self):
        assert contains("lib/api-client.ts", r'"commands"')

    def test_sessions_key(self):
        assert contains("lib/api-client.ts", r'"sessions"')


class TestApiClientReactQueryHooks:
    """FDA-226 acceptance: React Query hooks for key endpoints."""

    def test_use_health_hook(self):
        assert contains("lib/api-client.ts", r"export function useHealth")

    def test_use_commands_hook(self):
        assert contains("lib/api-client.ts", r"export function useCommands")

    def test_use_tools_hook(self):
        assert contains("lib/api-client.ts", r"export function useTools")

    def test_use_sessions_hook(self):
        assert contains("lib/api-client.ts", r"export function useSessions")

    def test_use_session_hook(self):
        assert contains("lib/api-client.ts", r"export function useSession")

    def test_use_execute_mutation(self):
        assert contains("lib/api-client.ts", r"export function useExecute")

    def test_use_answer_question_mutation(self):
        assert contains("lib/api-client.ts", r"export function useAnswerQuestion")

    def test_health_refetch_interval(self):
        # Health should auto-poll (the bridge may restart)
        assert contains("lib/api-client.ts", r"refetchInterval")

    def test_execute_uses_use_mutation(self):
        assert contains("lib/api-client.ts", r"useMutation")


class TestApiClientAxiosConfig:
    """FDA-226: Axios instance configuration."""

    def test_default_base_url(self):
        assert contains("lib/api-client.ts", r"localhost:18790")

    def test_timeout_set(self):
        assert contains("lib/api-client.ts", r"timeout")

    def test_content_type_json(self):
        assert contains("lib/api-client.ts", r"application/json")

    def test_response_interceptor_normalizes_validation_error(self):
        assert contains("lib/api-client.ts", r"422")

    def test_singleton_axios_instance(self):
        # Instance should be created once
        assert contains("lib/api-client.ts", r"_axiosInstance")


# ── Providers component ───────────────────────────────────────────────────────

class TestProvidersComponent:
    """Shared root Providers wraps QueryClientProvider + AuthProvider."""

    def test_file_exists(self):
        assert has("components/providers.tsx")

    def test_query_client_provider(self):
        assert contains("components/providers.tsx", r"QueryClientProvider")

    def test_auth_provider(self):
        assert contains("components/providers.tsx", r"AuthProvider")

    def test_refetch_on_window_focus_disabled(self):
        assert contains("components/providers.tsx", r"refetchOnWindowFocus.*false")


# ── Environment variable checklist ───────────────────────────────────────────

class TestEnvironmentVariables:
    """All required env vars are documented / referenced correctly."""

    def test_supabase_url_is_public(self):
        # Must be NEXT_PUBLIC_ so it's available in the browser
        assert not contains("lib/supabase.ts", r"(?<!NEXT_PUBLIC_)SUPABASE_URL")
        assert contains("lib/supabase.ts", r"NEXT_PUBLIC_SUPABASE_URL")

    def test_supabase_anon_key_is_public(self):
        assert contains("lib/supabase.ts", r"NEXT_PUBLIC_SUPABASE_ANON_KEY")

    def test_api_url_is_public(self):
        assert contains("lib/api-client.ts", r"NEXT_PUBLIC_API_URL")

    def test_no_secret_key_in_client_code(self):
        # SUPABASE_SECRET_KEY must never appear in browser-side code
        assert not contains("lib/supabase.ts", r"SUPABASE_SECRET_KEY")
        assert not contains("lib/api-client.ts", r"SUPABASE_SECRET_KEY")
