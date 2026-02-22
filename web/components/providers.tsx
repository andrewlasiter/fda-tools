"use client";

/**
 * Root Providers
 * ==============
 * Wraps the application with all global context providers:
 *   - ThemeProvider    — next-themes dark/light mode
 *   - QueryClientProvider — React Query for API data fetching (FDA-226)
 *   - AuthProvider     — Supabase session state (FDA-225)
 */

import React from "react";
import { ThemeProvider } from "next-themes";
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
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
