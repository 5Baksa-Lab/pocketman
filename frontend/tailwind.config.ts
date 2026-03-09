import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        base: "var(--color-bg)",
        panel: "var(--color-panel)",
        panelSoft: "var(--color-panel-soft)",
        ink: "var(--color-ink)",
        point: "var(--color-point)",
        pointAlt: "var(--color-point-alt)",
        ok: "var(--color-ok)",
        warn: "var(--color-warn)",
        danger: "var(--color-danger)"
      },
      boxShadow: {
        deck: "0 14px 40px rgba(5, 14, 23, 0.22)"
      },
      borderRadius: {
        xl2: "1.25rem"
      }
    }
  },
  plugins: []
};

export default config;
