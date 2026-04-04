/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#080c12',
        surface: '#0d1117',
        'surface-2': '#161b22',
        border: '#21262d',
        'border-hover': '#3d444d',
        primary: {
          50:  '#e0f7ff',
          100: '#b3ecff',
          200: '#6dd8f7',
          300: '#38c8ef',
          400: '#17b8e8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        accent: {
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
        },
        node: {
          dim:   'rgba(14, 165, 233, 0.15)',
          glow:  '#0ea5e9',
          pulse: 'rgba(14, 165, 233, 0.4)',
        },
        success: '#22c55e',
        warning: '#f59e0b',
        error:   '#ef4444',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow':      'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'node-ping':       'node-ping 3s ease-in-out infinite',
        'fade-up':         'fade-up 0.4s ease-out both',
        'slide-in-left':   'slide-in-left 0.35s cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-in-right':  'slide-in-right 0.35s cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-out-left':  'slide-out-left 0.3s ease-in both',
        'slide-out-right': 'slide-out-right 0.3s ease-in both',
        'shimmer':         'shimmer 2s linear infinite',
        'glow-pulse':      'glow-pulse 3s ease-in-out infinite',
        'stream-flow':     'stream-flow 2s linear infinite',
        'draw':            'draw 1.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        'node-ping': {
          '0%, 100%': { transform: 'scale(1)',   opacity: '0.5' },
          '50%':      { transform: 'scale(1.4)', opacity: '1'   },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to:   { opacity: '1', transform: 'translateY(0)'    },
        },
        'slide-in-left': {
          from: { opacity: '0', transform: 'translateX(-24px)' },
          to:   { opacity: '1', transform: 'translateX(0)'     },
        },
        'slide-in-right': {
          from: { opacity: '0', transform: 'translateX(24px)' },
          to:   { opacity: '1', transform: 'translateX(0)'    },
        },
        'slide-out-left': {
          from: { opacity: '1', transform: 'translateX(0)'      },
          to:   { opacity: '0', transform: 'translateX(-24px)'  },
        },
        'slide-out-right': {
          from: { opacity: '1', transform: 'translateX(0)'     },
          to:   { opacity: '0', transform: 'translateX(24px)'  },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200%  0' },
        },
        'glow-pulse': {
          '0%, 100%': { opacity: '0.4', filter: 'blur(60px)' },
          '50%':      { opacity: '0.7', filter: 'blur(80px)' },
        },
        'stream-flow': {
          '0%': { strokeDashoffset: '20' },
          '100%': { strokeDashoffset: '0' },
        },
        'draw': {
          '0%': { strokeDashoffset: '1000' },
          '100%': { strokeDashoffset: '0' },
        },
      },
      boxShadow: {
        'glow-sm': '0 0 12px rgba(14, 165, 233, 0.25)',
        'glow-md': '0 0 24px rgba(14, 165, 233, 0.35)',
        'glow-lg': '0 0 48px rgba(14, 165, 233, 0.2)',
        'card':    '0 1px 1px rgba(0,0,0,0.4), 0 4px 8px rgba(0,0,0,0.3), 0 16px 32px rgba(0,0,0,0.25)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
