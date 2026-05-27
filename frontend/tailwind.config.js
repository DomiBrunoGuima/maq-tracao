/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1117",
        surface: "#1a1d27",
        border: "#2a2d3e",
        accent: "#00d4ff",
        rupture: "#ff6b35",
        muted: "#64748b",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "IBM Plex Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
