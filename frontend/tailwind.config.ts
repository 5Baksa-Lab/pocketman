import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
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
        danger: "var(--color-danger)",
        pk: {
          red: "#ee1515",
          yellow: "#ffcb05",
          blue: "#31a7d7",
          dark: "#212121",
          screen: "#98cb98",
          border: "#333333"
        }
      },
      boxShadow: {
        deck: "0 14px 40px rgba(5, 14, 23, 0.22)",
        retro: "6px 6px 0px 0px rgba(0,0,0,1)",
        "retro-sm": "4px 4px 0px 0px rgba(0,0,0,1)"
      },
      borderRadius: {
        xl2: "1.25rem"
      },
      keyframes: {
        // PokemonCard — sprite bounce (davidkpiano design, 2s loop)
        "bounce-head": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" }
        },
        // Plaza sprite — idle breathing
        "idle-breath": {
          "0%, 100%": { transform: "scale(1.0)" },
          "50%": { transform: "scale(1.03)" }
        },
        // Plaza sprite — 2-frame bounce while moving
        "sprite-bounce": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" }
        },
        // Login mobile — grass sway
        "grass-sway": {
          "0%, 100%": { transform: "rotate(-3deg)" },
          "50%": { transform: "rotate(3deg)" }
        },
        // Pokemon Parade — sprite sheet step (simeydotme design)
        "poke-walk": {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "-576px 0" }
        },
        // Pokemon Parade — horizontal movement
        "poke-move": {
          "0%": { transform: "translateX(110vw)" },
          "100%": { transform: "translateX(-110px)" }
        },
        // General entrance fade
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" }
        },
        // Login card slide up
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        // Result page card reveal
        "card-reveal": {
          "0%": { opacity: "0", transform: "scale(0.92) translateY(16px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" }
        },
        // Login page — pokemon eyes look left/right
        "eyes-look": {
          "0%, 100%": { transform: "translateX(0)" },
          "30%": { transform: "translateX(-2px)" },
          "70%": { transform: "translateX(2px)" }
        },
        // Login page — pokemon eye blink
        "eye-blink": {
          "0%, 90%, 100%": { transform: "scaleY(1)" },
          "95%": { transform: "scaleY(0.08)" }
        },
        // Login page mobile — cloud drift
        "cloud-move": {
          "0%": { transform: "translateX(0)" },
          "50%": { transform: "translateX(12px)" },
          "100%": { transform: "translateX(0)" }
        },
        // Login page mobile — Pidgey fly
        "pidgey-fly": {
          "0%, 100%": { transform: "translateY(0) rotate(-4deg)" },
          "50%": { transform: "translateY(-8px) rotate(4deg)" }
        },
        // Login page mobile — Pikachu tail wag
        "pikachu-tail": {
          "0%, 100%": { transform: "rotate(-10deg)" },
          "50%": { transform: "rotate(10deg)" }
        }
      },
      animation: {
        "bounce-head": "bounce-head 2s ease-in-out infinite",
        "idle-breath": "idle-breath 2s ease-in-out infinite",
        "sprite-bounce": "sprite-bounce 0.4s ease-in-out infinite",
        "grass-sway": "grass-sway 2s ease-in-out infinite",
        "poke-walk": "poke-walk 0.6s steps(6) infinite",
        "poke-move": "poke-move 6s linear infinite",
        "fade-in": "fade-in 0.4s ease-out forwards",
        "slide-up": "slide-up 0.5s ease-out forwards",
        "card-reveal": "card-reveal 0.6s ease-out forwards",
        "eyes-look": "eyes-look 3s ease-in-out infinite",
        "eye-blink": "eye-blink 4s ease-in-out infinite",
        "cloud-move": "cloud-move 5s ease-in-out infinite",
        "pidgey-fly": "pidgey-fly 2s ease-in-out infinite",
        "pikachu-tail": "pikachu-tail 0.6s ease-in-out infinite"
      }
    }
  },
  plugins: []
};

export default config;
