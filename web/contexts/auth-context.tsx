"use client";

/**
 * FDA-225 [FE-002] Auth Context
 * ==============================
 * Provides the current Supabase user and session to all Client Components
 * via React context.  Wraps the app in AuthProvider (see components/providers.tsx).
 *
 * Usage:
 *   import { useAuth } from "@/contexts/auth-context"
 *   const { user, session, loading, signOut } = useAuth()
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import type { User, Session } from "@supabase/supabase-js";
import { getSupabaseClient, signOut as _signOut } from "@/lib/supabase";

// ── Types ──────────────────────────────────────────────────────────────────

interface AuthState {
  user:    User    | null;
  session: Session | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  /** Sign out the current user and clear the session. */
  signOut: () => Promise<void>;
  /** True when a valid session is present. */
  isAuthenticated: boolean;
}

// ── Context ────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ── Provider ───────────────────────────────────────────────────────────────

/**
 * Wrap the application tree with AuthProvider to make auth state available
 * to all descendant Client Components.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user:    null,
    session: null,
    loading: true,
  });

  useEffect(() => {
    const supabase = getSupabaseClient();

    // Fetch the initial session on mount.
    supabase.auth.getSession().then(({ data: { session } }) => {
      setState({
        user:    session?.user ?? null,
        session: session,
        loading: false,
      });
    });

    // Subscribe to auth state changes (login, logout, token refresh).
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({
        user:    session?.user ?? null,
        session: session,
        loading: false,
      });
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = useCallback(async () => {
    await _signOut();
  }, []);

  const value: AuthContextValue = {
    ...state,
    isAuthenticated: state.session !== null,
    signOut: handleSignOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ───────────────────────────────────────────────────────────────────

/**
 * Access the auth context.  Must be used inside an AuthProvider.
 *
 * @example
 *   const { user, isAuthenticated, signOut } = useAuth()
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
