/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#08090d',
        surface: '#0e1016',
        panel: '#13161f',
        border: '#1c2030',
        muted: '#252a3a',
        dim: '#4a5268',
        text: '#c4ccde',
        bright: '#e8edf8',
        accent: '#00c896',
        amber: '#f0a030',
        red: '#e04848',
        green: '#00c896',
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
