/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eef6ff",
          100: "#d9eaff",
          200: "#bcd8ff",
          300: "#8ec2ff",
          400: "#5aa6ff",
          500: "#2f8cff",   // Primary
          600: "#1e6fe0",
          700: "#1858b8",
          800: "#154892",
          900: "#123c77",   // Deep exploration blue
        },

        solar: {
          50:  "#fffbea",
          100: "#fff3c4",
          200: "#ffe588",
          300: "#ffd24d",
          400: "#ffc107",
          500: "#f5b301",   // Golden accent
          600: "#d89b00",
          700: "#b37f00",
          800: "#8c6300",
          900: "#664800",
        },

        coral: {
          50:  "#fff1f0",
          100: "#ffe0dd",
          200: "#ffc2bb",
          300: "#ff9a8f",
          400: "#ff6d5e",
          500: "#ff4d3a",   // CTA color
          600: "#e63c2a",
          700: "#c32f20",
          800: "#9f2419",
          900: "#7d1a12",
        },

        surface: {
          50:  "#f8fafc",
          100: "#eef2f7",
          200: "#e2e8f0",
          800: "#0b1220",
          900: "#070b15",   // darker, more global
        },
      },

      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },

      screens: { xs: "475px" },
    },
  },
  plugins: [],
};
