import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./pages/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}', './app/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        primary: '#D6A84B', secondary: '#196AA5', accent: '#5BC5FF', danger: '#B7373F',
        background: '#090B0D', surface: '#171C22', border: '#8D642C',
        'stone-light': '#20262D', 'gold-bright': '#FFD76A', bronze: '#A87934',
        'text-main': '#F5EDD8', muted: '#ADA794', 'war-red': '#D94B38',
      },
      fontFamily: { sans: ['Inter', 'sans-serif'], display: ['Cinzel', 'serif'], mono: ['JetBrains Mono', 'monospace'] },
      boxShadow: {
        gold: '0 0 28px rgba(214,168,75,.22)', blue: '0 0 30px rgba(42,138,194,.2)',
        insetGold: 'inset 0 0 22px rgba(214,168,75,.07)',
      },
      animation: { drift: 'drift 16s ease-in-out infinite', shimmer: 'shimmer 2.8s ease-in-out infinite', 'archive-pulse': 'archive-pulse 1.4s ease-in-out infinite' },
    },
  },
  plugins: [],
}

export default config
