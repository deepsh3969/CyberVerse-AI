/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#04070d',
          900: '#070b14',
          850: '#0a101c',
          800: '#0d1424',
          700: '#131c30',
          600: '#1b2740',
        },
        cyber: {
          300: '#7ee7ff',
          400: '#38d6f5',
          500: '#12b6dd',
          600: '#0a8fb0',
        },
        alert: {
          400: '#ff5d7a',
          500: '#ff3b5c',
          600: '#e02348',
        },
        warn: {
          400: '#ffb03a',
          500: '#f5a524',
        },
        ok: {
          400: '#2fd98a',
          500: '#1fbb73',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(56,214,245,0.18), 0 8px 30px -12px rgba(56,214,245,0.35)',
        card: '0 10px 30px -18px rgba(0,0,0,0.9)',
      },
      keyframes: {
        pulseDot: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.45', transform: 'scale(0.82)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        sweep: {
          from: { transform: 'translateX(-100%)' },
          to: { transform: 'translateX(220%)' },
        },
      },
      animation: {
        pulseDot: 'pulseDot 1.6s ease-in-out infinite',
        slideUp: 'slideUp 0.35s ease-out both',
        sweep: 'sweep 2.4s linear infinite',
      },
    },
  },
  plugins: [],
}
