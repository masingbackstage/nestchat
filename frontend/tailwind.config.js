/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{svelte,js,ts}'],
  theme: {
    extend: {
      colors: {
        surface: {
          950: '#090b13',
          900: '#101425',
          850: '#151b30',
          800: '#1b2440',
        },
        panel: {
          soft: 'rgba(24, 30, 51, 0.72)',
          muted: 'rgba(19, 25, 44, 0.76)',
          strong: 'rgba(15, 19, 35, 0.86)',
        },
        accent: {
          500: '#ec5b13',
          400: '#f27b3d',
          300: '#fb9e6d',
        },
        muted: {
          100: '#d8dbea',
          200: '#b7bfd5',
          300: '#98a2c2',
          400: '#7b86ab',
          500: '#5f6b92',
        },
        glass: {
          border: 'rgba(255,255,255,0.12)',
          highlight: 'rgba(255,255,255,0.2)',
        },
      },
      boxShadow: {
        glow: '0 0 60px -20px rgba(236,91,19,0.35)',
        panel: '0 18px 60px rgba(2, 6, 24, 0.45)',
      },
      borderRadius: {
        panel: '1.5rem',
        pill: '9999px',
      },
    },
  },
  plugins: [],
};
