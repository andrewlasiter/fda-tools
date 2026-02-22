import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Strict mode catches subtle React bugs in development
  reactStrictMode: true,

  // Backend API URL — set NEXT_PUBLIC_API_URL in .env.local
  env: {
    NEXT_PUBLIC_APP_NAME: "MDRP",
    NEXT_PUBLIC_APP_VERSION: "1.0.0",
  },

  // Allow images from Supabase storage
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.supabase.co",
        pathname: "/storage/v1/object/public/**",
      },
    ],
  },

  // Transpile tremor for Next.js
  transpilePackages: ["@tremor/react"],
};

export default nextConfig;
