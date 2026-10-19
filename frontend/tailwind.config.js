/** @type {import('tailwindcss').Config} */
// As cores vêm de variáveis CSS (src/index.css) para o tema claro/escuro trocar
// tudo de uma vez. "white" e "slate" também: no tema claro o texto vira escuro.
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        panel: v("panel"),
        tooltip: v("tooltip"),
        border: v("border"),
        accent: v("accent"),
        rupture: v("rupture"),
        muted: v("muted"),
        white: v("fg"),
        slate: {
          200: v("slate-200"),
          300: v("slate-300"),
          400: v("slate-400"),
          500: v("slate-500"),
          600: v("slate-600"),
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "IBM Plex Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
