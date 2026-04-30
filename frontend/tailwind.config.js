/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0a0f',
          800: '#0e0e16',
          700: '#12121a',
          600: '#1a1a25',
          500: '#242430',
          400: '#2e2e3d',
        },
        accent: {
          purple: '#7c5cff',
          blue: '#5c9cff',
          green: '#5cffb1',
          pink: '#ff5ca0',
          orange: '#ff9f5c',
          cyan: '#5cdcff',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-purple': '0 0 30px rgba(124, 92, 255, 0.15)',
        'glow-blue': '0 0 30px rgba(92, 156, 255, 0.15)',
        'glow-green': '0 0 30px rgba(92, 255, 177, 0.15)',
        'glow-pink': '0 0 30px rgba(255, 92, 160, 0.15)',
        'float': '0 8px 32px rgba(0, 0, 0, 0.3)',
        'float-lg': '0 16px 48px rgba(0, 0, 0, 0.4)',
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-slow': 'float 8s ease-in-out infinite',
        'pulse-soft': 'pulse-soft 3s ease-in-out infinite',
        'slide-up': 'slide-up 0.5s ease-out',
        'fade-in': 'fade-in 0.4s ease-out',
        'count-up': 'count-up 1s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
