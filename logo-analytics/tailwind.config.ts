import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        canvas:     '#080808',
        panel:      '#0E0E0E',
        'panel-hover': '#141414',
        wire:       '#222222',
        'wire-s':   '#2E2E2E',
        ink:        '#F0F0F0',
        dim:        '#787878',
        ghost:      '#383838',
        spark:      '#C5F000',
        'spark-bg': 'rgba(197,240,0,0.07)',
      },
      fontFamily: {
        mono: ['"SF Mono"', '"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'monospace'],
      },
      keyframes: {
        'fade-in': { from: { opacity: '0', transform: 'translateY(6px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'bar-fill': { from: { width: '0%' }, to: { width: 'var(--target-w)' } },
      },
      animation: {
        'fade-in': 'fade-in 0.35s ease forwards',
      },
    },
  },
  plugins: [],
}

export default config
