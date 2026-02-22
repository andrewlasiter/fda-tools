import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React strict mode for better error detection
  reactStrictMode: true,

  // Environment variables exposed to the browser must be prefixed with NEXT_PUBLIC_
  // NEXT_PUBLIC_SUPABASE_URL       — Supabase project URL
  // NEXT_PUBLIC_SUPABASE_ANON_KEY  — Supabase anonymous key (safe to expose)
  // NEXT_PUBLIC_API_URL            — FastAPI bridge server base URL

  // Redirect bare /auth to /auth/login
  async redirects() {
    return [
      {
        source: "/auth",
        destination: "/auth/login",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
