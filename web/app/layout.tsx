import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

// ── Fonts ──────────────────────────────────────────────────────────────────

/** Inter — body copy */
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

/** Plus Jakarta Sans — headings */
const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
});

// ── Metadata ───────────────────────────────────────────────────────────────

export const metadata: Metadata = {
  title: "FDA Tools — Medical Device Regulatory Platform",
  description:
    "AI-powered regulatory intelligence for medical device new product development",
};

// ── Root layout ────────────────────────────────────────────────────────────

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      // next-themes requires suppressHydrationWarning to avoid
      // mismatch between server (no class) and client (dark/light class).
      suppressHydrationWarning
      className={`${inter.variable} ${plusJakarta.variable}`}
    >
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
