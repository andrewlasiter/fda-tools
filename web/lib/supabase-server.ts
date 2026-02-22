/**
 * FDA-225 [FE-002] Supabase Server Client
 * ========================================
 * Server-side Supabase client for Next.js 14 Server Components,
 * Route Handlers, and middleware.  Uses @supabase/ssr cookie utilities
 * so session tokens are stored in HTTP-only cookies rather than localStorage.
 *
 * Usage — Server Components / Route Handlers:
 *   import { createSupabaseServerClient } from "@/lib/supabase-server"
 *   const supabase = await createSupabaseServerClient()
 *
 * Usage — Middleware (Edge runtime):
 *   import { createSupabaseMiddlewareClient } from "@/lib/supabase-server"
 */

import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";
import type { NextRequest, NextResponse } from "next/server";

// ── Server Component / Route Handler client ────────────────────────────────

/**
 * Creates a Supabase client for use in Server Components and Route Handlers.
 * Reads and writes session cookies via next/headers.
 */
export async function createSupabaseServerClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        },
      },
    }
  );
}

// ── Middleware client (Edge runtime) ───────────────────────────────────────

/**
 * Creates a Supabase client for use in Next.js middleware.
 * Reads from `request.cookies` and writes to `response.cookies`.
 *
 * @returns Object with `supabase` client and updated `response`.
 */
export function createSupabaseMiddlewareClient(
  request: NextRequest,
  response: NextResponse
) {
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(
          cookiesToSet: { name: string; value: string; options: CookieOptions }[]
        ) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );
  return { supabase, response };
}

// ── Auth helpers (server-side) ─────────────────────────────────────────────

/**
 * Get the current user from the server-side session.
 * Returns null if not authenticated.
 */
export async function getServerUser() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
}
