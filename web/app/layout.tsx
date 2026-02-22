import type { Metadata, Viewport } from "next";
import { ThemeProvider } from "@/components/layout/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "MDRP — Medical Device Regulatory Platform",
    template: "%s | MDRP",
  },
  description:
    "End-to-end medical device regulatory platform: 510(k) submissions, predicate research, AI-assisted drafting, and post-market surveillance.",
  keywords: ["FDA", "510k", "medical device", "regulatory", "RA", "submissions"],
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFFFFF" },
    { media: "(prefers-color-scheme: dark)",  color: "#020617" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
