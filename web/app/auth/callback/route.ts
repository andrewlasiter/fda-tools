/**
 * FDA-225 [FE-002] Auth Callback Route Handler
 * =============================================
 * Handles the redirect from Supabase after magic-link or OAuth sign-in.
 * Exchanges the one-time code for a persistent session cookie.
 */

import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase-server";

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  // `next` is set by the middleware when redirecting unauthenticated users.
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const supabase = await createSupabaseServerClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  // On error, redirect to login with an error flag.
  return NextResponse.redirect(`${origin}/auth/login?error=auth_callback_failed`);
}
