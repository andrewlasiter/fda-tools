"use client";

/**
 * Root Providers
 * ==============
 * Wraps the application with global context providers:
 *   - AuthProvider      — Supabase session state (FDA-225)
 *   - QueryClientProvider — React Query for API data fetching (FDA-226)
 */

import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/auth-context";

// Instantiate QueryClient once per app (not per render).
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't refetch on window focus in a medical/regulatory tool.
      refetchOnWindowFocus: false,
      // Retry once on failure.
      retry: 1,
      // Cache data for 5 minutes by default.
      staleTime: 5 * 60 * 1000,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
