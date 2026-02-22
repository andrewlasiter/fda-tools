/**
 * Supabase browser client singleton for Next.js.
 *
 * Reads from:
 *   NEXT_PUBLIC_SUPABASE_URL       — public project URL
 *   NEXT_PUBLIC_SUPABASE_ANON_KEY  — public anon key (safe to expose in browser)
 *
 * The service-role key (SUPABASE_SECRET_KEY) is NEVER used here —
 * it stays server-side only (see the Python SupabaseClient).
 */

import { createBrowserClient } from "@supabase/ssr";

let client: ReturnType<typeof createBrowserClient> | null = null;

export function getSupabaseClient() {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !key) {
    throw new Error(
      "Missing Supabase env vars. Set NEXT_PUBLIC_SUPABASE_URL and " +
      "NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local"
    );
  }

  client = createBrowserClient(url, key);
  return client;
}
