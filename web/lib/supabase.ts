/**
 * FDA-225 [FE-002] Supabase Auth Integration
 * ============================================
 * Supabase client singletons for browser and server contexts.
 *
 * Environment variables required:
 *   NEXT_PUBLIC_SUPABASE_URL       — Supabase project URL
 *   NEXT_PUBLIC_SUPABASE_ANON_KEY  — Supabase anonymous/public key
 *
 * Usage — browser components:
 *   import { getSupabaseClient } from "@/lib/supabase"
 *   const supabase = getSupabaseClient()
 *
 * Usage — server components / route handlers:
 *   import { createSupabaseServerClient } from "@/lib/supabase-server"
 */

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

// ── Types ──────────────────────────────────────────────────────────────────

export type { User, Session, AuthError } from "@supabase/supabase-js";

/** Auth provider options for OAuth sign-in */
export type OAuthProvider = "google" | "github";

// ── Browser client singleton ───────────────────────────────────────────────

let _browserClient: SupabaseClient | null = null;

/**
 * Returns the Supabase browser client singleton.
 *
 * Safe to call multiple times — returns the same instance.
 * Should only be used in Client Components (files with "use client").
 */
export function getSupabaseClient(): SupabaseClient {
  if (!_browserClient) {
    _browserClient = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
  }
  return _browserClient;
}

// ── Auth helpers ───────────────────────────────────────────────────────────

/**
 * Sign in with magic link (passwordless email).
 * Supabase sends a one-time login URL to the provided email address.
 */
export async function signInWithMagicLink(email: string): Promise<void> {
  const supabase = getSupabaseClient();
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  if (error) throw error;
}

/**
 * Sign in with an OAuth provider (Google or GitHub).
 * Redirects to the provider's authorization page.
 */
export async function signInWithOAuth(provider: OAuthProvider): Promise<void> {
  const supabase = getSupabaseClient();
  const { error } = await supabase.auth.signInWithOAuth({
    provider,
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  if (error) throw error;
}

/**
 * Sign out the current user and clear the local session.
 */
export async function signOut(): Promise<void> {
  const supabase = getSupabaseClient();
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

/**
 * Get the current session access token, or null if not authenticated.
 * Used by the API client to inject the Authorization header.
 */
export async function getAccessToken(): Promise<string | null> {
  const supabase = getSupabaseClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}
