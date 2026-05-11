/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Brand palette — dark burgundy #470c1d
        brand: {
          DEFAULT: '#470c1d',
          dark:    '#3a0918',
          light:   '#6b1228',
        },
        // Surface palette — warm cream #f7f4ed
        surface: {
          DEFAULT: '#f7f4ed',
          card:    '#ede9e0',
          border:  '#d4cfc4',
        },
        // Ink — near black #0a0a09
        ink: {
          DEFAULT: '#0a0a09',
        },
      },
    },
  },
  plugins: [],
}
