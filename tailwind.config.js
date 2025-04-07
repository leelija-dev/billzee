/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.js",
    "./static/**/*.css",
    "./static/**/*.html",
    "./node_modules/flowbite/**/*.js"
  ],
  safelist: [
    "text-3xl", "bg-primary", "text-center", "py-4", "px-6", "rounded", "font-bold", "hover:bg-blue-700"
  ],
  theme: {
    extend: {
      colors: {
        primary: "#18cb96",
        primarydark: "#108f6a",
        secondary: "#3B82F6",
        success: "#059669",
        danger: "#DC2626",
        warning: "#D97706",
        info: "#2563EB",
      },
      spacing: {
        '72': '18rem',
        '84': '21rem',
        '96': '24rem',
      },
      maxWidth: {
        '8xl': '88rem',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '2rem',
      },
    },
  },
  plugins: [
    require('flowbite/plugin')
  ],
  darkMode: 'class',
}
