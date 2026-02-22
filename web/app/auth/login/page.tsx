"use client";

/**
 * FDA-225 [FE-002] Login Page
 * ============================
 * Supports two authentication methods:
 *   1. Magic link — passwordless email (Supabase OTP)
 *   2. OAuth    — Google and GitHub
 */

import React, { useState } from "react";
import { signInWithMagicLink, signInWithOAuth } from "@/lib/supabase";

// ── Sub-components ─────────────────────────────────────────────────────────

function StatusMessage({
  type,
  message,
}: {
  type: "success" | "error";
  message: string;
}) {
  const base = "rounded-md px-4 py-3 text-sm font-medium";
  const styles =
    type === "success"
      ? `${base} bg-green-50 text-green-800 border border-green-200`
      : `${base} bg-red-50 text-red-800 border border-red-200`;
  return <div className={styles}>{message}</div>;
}

// ── Main component ─────────────────────────────────────────────────────────

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [oauthLoading, setOAuthLoading] = useState<string | null>(null);
  const [status, setStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  async function handleMagicLink(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setStatus(null);
    try {
      await signInWithMagicLink(email.trim());
      setStatus({
        type: "success",
        message: "Check your inbox — a login link is on its way.",
      });
      setEmail("");
    } catch {
      setStatus({
        type: "error",
        message: "Unable to send magic link. Please try again.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleOAuth(provider: "google" | "github") {
    setOAuthLoading(provider);
    setStatus(null);
    try {
      await signInWithOAuth(provider);
      // Redirect handled by Supabase — no need to update state.
    } catch {
      setStatus({
        type: "error",
        message: `Unable to sign in with ${provider}. Please try again.`,
      });
      setOAuthLoading(null);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--color-bg-subtle)] px-4">
      <div className="w-full max-w-md space-y-6 rounded-xl border border-[var(--color-border)] bg-white p-8 shadow-sm">

        {/* Header */}
        <div className="text-center">
          <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--color-fda-blue)]">
            <span className="text-lg font-bold text-white">F</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-text)]">
            Sign in to FDA Tools
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-subtle)]">
            Medical Device Regulatory Platform
          </p>
        </div>

        {/* Status message */}
        {status && <StatusMessage type={status.type} message={status.message} />}

        {/* Magic link form */}
        <form onSubmit={handleMagicLink} className="space-y-3">
          <label
            htmlFor="email"
            className="block text-sm font-medium text-[var(--color-text)]"
          >
            Email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            className="w-full rounded-md border border-[var(--color-border)] px-3 py-2 text-sm
                       focus:border-[var(--color-fda-blue)] focus:outline-none focus:ring-1
                       focus:ring-[var(--color-fda-blue)]"
          />
          <button
            type="submit"
            disabled={submitting || !email.trim()}
            className="w-full rounded-md bg-[var(--color-fda-blue)] px-4 py-2 text-sm
                       font-semibold text-white transition-colors
                       hover:bg-[var(--color-fda-blue-dk)] disabled:opacity-50"
          >
            {submitting ? "Sending…" : "Send magic link"}
          </button>
        </form>

        {/* Divider */}
        <div className="relative flex items-center">
          <div className="flex-1 border-t border-[var(--color-border)]" />
          <span className="mx-3 text-xs text-[var(--color-text-subtle)]">or</span>
          <div className="flex-1 border-t border-[var(--color-border)]" />
        </div>

        {/* OAuth buttons */}
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => handleOAuth("google")}
            disabled={oauthLoading !== null}
            className="flex w-full items-center justify-center gap-2 rounded-md border
                       border-[var(--color-border)] px-4 py-2 text-sm font-medium
                       text-[var(--color-text)] transition-colors hover:bg-[var(--color-bg-subtle)]
                       disabled:opacity-50"
          >
            {oauthLoading === "google" ? "Redirecting…" : "Continue with Google"}
          </button>
          <button
            type="button"
            onClick={() => handleOAuth("github")}
            disabled={oauthLoading !== null}
            className="flex w-full items-center justify-center gap-2 rounded-md border
                       border-[var(--color-border)] px-4 py-2 text-sm font-medium
                       text-[var(--color-text)] transition-colors hover:bg-[var(--color-bg-subtle)]
                       disabled:opacity-50"
          >
            {oauthLoading === "github" ? "Redirecting…" : "Continue with GitHub"}
          </button>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-[var(--color-text-subtle)]">
          By signing in you agree to our Terms of Service.
          <br />
          Your data is protected under 21 CFR Part 11 audit controls.
        </p>
      </div>
    </main>
  );
}
