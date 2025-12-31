/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        primary: '#00d4ff',
        warning: '#ffc107',
        danger: '#ff6b6b',
        success: '#22c55e',  // Updated to match Tailwind green-500
        oracle: '#a855f7',   // Oracle purple accent
      },
      fontFamily: {
        mono: ['Courier New', 'monospace'],
      },
      animation: {
        'glow': 'glow 2s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        glow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(34, 197, 94, 0.4)' },
          '50%': { boxShadow: '0 0 30px 10px rgba(34, 197, 94, 0.15)' },
        },
      },
    },
  },
  plugins: [],
}

