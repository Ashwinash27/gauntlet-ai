/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Void Backgrounds
        void: {
          deep: '#05070a',
          base: '#0a0e14',
          elevated: '#0f1419',
          surface: '#161b22',
        },
        // Neon Accents
        neon: {
          cyan: '#00f0ff',
          magenta: '#ff00ff',
          electric: '#4d9fff',
        },
        // Status Colors
        status: {
          safe: '#00ff9f',
          danger: '#ff3366',
          warning: '#ffaa00',
        },
        // Layer Colors
        layer: {
          1: '#bf7af0',  // Purple - rules
          2: '#ff6bb3',  // Pink - embeddings
          3: '#ffb347',  // Orange - LLM judge
        },
        // Legacy support
        bg: {
          primary: '#0a0e14',
          secondary: '#0f1419',
          tertiary: '#161b22',
          elevated: '#1c2128',
        },
        text: {
          primary: '#e6edf3',
          secondary: '#8b949e',
          tertiary: '#6e7681',
        },
        safe: '#00ff9f',
        danger: '#ff3366',
        warning: '#ffaa00',
        accent: '#00f0ff',
      },
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        sans: ['JetBrains Mono', 'Consolas', 'monospace'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'neon-cyan': '0 0 20px rgba(0, 240, 255, 0.5), 0 0 40px rgba(0, 240, 255, 0.2)',
        'neon-cyan-lg': '0 0 30px rgba(0, 240, 255, 0.6), 0 0 60px rgba(0, 240, 255, 0.3)',
        'neon-magenta': '0 0 20px rgba(255, 0, 255, 0.5), 0 0 40px rgba(255, 0, 255, 0.2)',
        'neon-magenta-lg': '0 0 30px rgba(255, 0, 255, 0.6), 0 0 60px rgba(255, 0, 255, 0.3)',
        'neon-safe': '0 0 20px rgba(0, 255, 159, 0.5), 0 0 40px rgba(0, 255, 159, 0.2)',
        'neon-danger': '0 0 20px rgba(255, 51, 102, 0.5), 0 0 40px rgba(255, 51, 102, 0.2)',
        'neon-warning': '0 0 20px rgba(255, 170, 0, 0.5), 0 0 40px rgba(255, 170, 0, 0.2)',
        'neon-layer-1': '0 0 20px rgba(191, 122, 240, 0.5), 0 0 40px rgba(191, 122, 240, 0.2)',
        'neon-layer-2': '0 0 20px rgba(255, 107, 179, 0.5), 0 0 40px rgba(255, 107, 179, 0.2)',
        'neon-layer-3': '0 0 20px rgba(255, 179, 71, 0.5), 0 0 40px rgba(255, 179, 71, 0.2)',
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'border-scan': 'border-scan 3s linear infinite',
        'flicker': 'flicker 0.15s infinite',
        'typing-cursor': 'typing-cursor 1s step-end infinite',
        'scan-line': 'scan-line 8s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'shake': 'shake 0.5s ease-in-out',
        'chromatic': 'chromatic 0.3s ease-in-out',
        'data-stream': 'data-stream 1.5s linear infinite',
        'count-up': 'count-up 0.5s ease-out forwards',
        'slide-up': 'slide-up 0.5s ease-out',
        'slide-in-left': 'slide-in-left 0.4s ease-out',
        'fade-in': 'fade-in 0.5s ease-out',
        'scale-in': 'scale-in 0.3s ease-out',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'border-scan': {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '200% 0%' },
        },
        'flicker': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
        'typing-cursor': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'shake': {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
        },
        'chromatic': {
          '0%': { textShadow: '2px 0 #ff00ff, -2px 0 #00f0ff' },
          '50%': { textShadow: '-2px 0 #ff00ff, 2px 0 #00f0ff' },
          '100%': { textShadow: '0 0 transparent' },
        },
        'data-stream': {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '100% 100%' },
        },
        'count-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-left': {
          '0%': { opacity: '0', transform: 'translateX(-20px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      backgroundImage: {
        'grid-pattern': `linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px),
                         linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px)`,
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
        'neon-border': 'linear-gradient(90deg, #00f0ff, #ff00ff, #00f0ff)',
      },
      backgroundSize: {
        'grid': '50px 50px',
      },
    },
  },
  plugins: [],
}
