import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

// Brand tokens are mirrored from school_erp_designed/jaikalki-school-erp-design.html
// so the React UI ships pixel-faithful with the approved mockup.
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        // Mockup palette
        saffron: {
          DEFAULT: "#E85D2E",
          dark: "#C44419",
          darker: "#8C2F0E",
          light: "#FF7A4D",
          lighter: "#FFB394",
          pale: "#FEE5DA",
        },
        teal: {
          DEFAULT: "#0F766E",
          dark: "#115E59",
          darker: "#0A3D38",
          light: "#2C9489",
          lighter: "#99D4CC",
          pale: "#D1F0EC",
        },
        marigold: {
          DEFAULT: "#FFB800",
          bright: "#FFC72E",
          light: "#FFD659",
          pale: "#FFF3D6",
          dark: "#C28800",
        },
        indigo: {
          DEFAULT: "#2E1A6B",
          dark: "#1F1248",
          light: "#4C32A0",
          pale: "#DCD5F2",
        },
        ivory: "#FFF9F0",
        "mint-cream": "#F0F9F4",
        "warm-white": "#FFFCF7",
        // Semantic shortcuts the shadcn primitives expect
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
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
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      fontFamily: {
        display: ['"Fraunces"', "serif"],
        body: ['"DM Sans"', "system-ui", "sans-serif"],
        hindi: ['"Noto Sans Devanagari"', '"DM Sans"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 4px)",
        sm: "calc(var(--radius) - 8px)",
      },
    },
  },
  plugins: [animate],
} satisfies Config;
