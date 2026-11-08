/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#121212',
        card: '#18181b',
        surface: '#18181b',
        'surface-hover': '#222226',
        border: '#27272a',
        'border-subtle': '#27272a',
        text: '#f4f4f5',
        'text-muted': '#a1a1aa',
        accent: {
          blue: '#3b82f6',
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#f43f5e',
        },
      },
    },
  },
  plugins: [],
};
