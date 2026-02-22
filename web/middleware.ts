/**
 * FDA-225 [FE-002] + QA-306 [A07] Route Protection Middleware
 * ============================================================
 * Runs on every request at the Edge runtime.
 * Refreshes the Supabase session and redirects unauthenticated users
 * away from all protected routes in the MDRP application.
 *
 * Protected paths:    /dashboard/**, /agents/**, /research/**,
 *                     /documents/**, /projects/**
 * Public paths:       /auth/**, / (root), /public/**
 *
 * OWASP A07 (2021): Authentication Failures — fixed to cover all routes.
 */

import { NextResponse, type NextRequest } from "next/server";
import { createSupabaseMiddlewareClient } from "@/lib/supabase-server";

/** Paths that do NOT require authentication. */
const PUBLIC_PATHS = ["/auth", "/auth/login", "/auth/callback", "/"];

/** All protected path prefixes (any path not in PUBLIC_PATHS requires auth). */
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/agents",
  "/research",
  "/documents",
  "/projects",
];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
}

function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Build a base response — middleware must return a response to continue.
  const response = NextResponse.next({
    request: { headers: request.headers },
  });

  // Only run auth check on protected routes.
  if (!isProtectedPath(pathname)) {
    return response;
  }

  const { supabase, response: supabaseResponse } =
    createSupabaseMiddlewareClient(request, response);

  // Refresh session — required by @supabase/ssr to keep tokens alive.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user && !isPublicPath(pathname)) {
    // Redirect to login, preserving the intended destination.
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/auth/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return supabaseResponse;
}

export const config = {
  // Run middleware on all routes except static assets and Next.js internals.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
