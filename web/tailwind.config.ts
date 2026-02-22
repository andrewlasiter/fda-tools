import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    // Include tremor components
    "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ── MDRP Design Tokens ──────────────────────────────────────────
      colors: {
        // FDA Blue — primary brand color
        primary: {
          DEFAULT: "#005EA2",
          50:  "#E8F1F9",
          100: "#C5D9EF",
          200: "#9EC0E4",
          300: "#77A7D9",
          400: "#5C93D1",
          500: "#005EA2",   // base
          600: "#005492",
          700: "#004780",
          800: "#003A6E",
          900: "#002A52",
          foreground: "#FFFFFF",
        },
        // Status Green — approved / cleared / success
        success: {
          DEFAULT: "#1A7F4B",
          50:  "#E8F5EE",
          100: "#C5E6D3",
          500: "#1A7F4B",
          foreground: "#FFFFFF",
        },
        // Alert Amber — warnings / in-review
        warning: {
          DEFAULT: "#B45309",
          50:  "#FEF3E2",
          100: "#FDDFA8",
          500: "#B45309",
          foreground: "#FFFFFF",
        },
        // Danger Red — critical alerts / failures
        danger: {
          DEFAULT: "#C0152A",
          500: "#C0152A",
          foreground: "#FFFFFF",
        },
        // Dark mode background
        dark: {
          bg:      "#020617", // slate-950
          surface: "#0F172A", // slate-900
          border:  "#1E293B", // slate-800
        },
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        chart: {
          "1": "hsl(var(--chart-1))",
          "2": "hsl(var(--chart-2))",
          "3": "hsl(var(--chart-3))",
          "4": "hsl(var(--chart-4))",
          "5": "hsl(var(--chart-5))",
        },
      },
      fontFamily: {
        // Plus Jakarta Sans for headings
        heading: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
        // Inter for body copy
        body:    ["Inter", "system-ui", "sans-serif"],
        sans:    ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      // NPD pipeline stage colors
      keyframes: {
        "pulse-slow": {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0.5" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-slow": "pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in":    "fade-in 0.15s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
