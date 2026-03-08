/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./static/**/*.js",
    "./static/**/*.ts",
    "./static/**/*.jsx",
    "./static/**/*.tsx",
    "./apps/**/*.js",
    "./apps/**/*.ts",
    "./apps/**/*.jsx",
    "./apps/**/*.tsx",
  ],
  darkMode: "class",
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: "1rem",
        sm: "1.5rem",
        lg: "2rem",
        xl: "2.5rem",
      },
      screens: {
        "2xl": "90rem",
      },
    },
    extend: {
      colors: {
        background: "var(--bg)",

        surface: {
          DEFAULT: "var(--surface)",
          soft: "var(--surface-2)",
          muted: "var(--surface-3)",
          strong: "var(--surface-strong)",
          hover: "var(--surface-strong-hover)",
          50: "var(--color-surface-50)",
          100: "var(--color-surface-100)",
          900: "var(--color-surface-900)",
        },

        text: {
          DEFAULT: "var(--text)",
          muted: "var(--muted)",
          soft: "var(--color-text-muted)",
          glass: {
            95: "var(--text-on-glass-95)",
            92: "var(--text-on-glass-92)",
            88: "var(--text-on-glass-88)",
            74: "var(--text-on-glass-74)",
            72: "var(--text-on-glass-72)",
            70: "var(--text-on-glass-70)",
            65: "var(--text-on-glass-65)",
            55: "var(--text-on-glass-55)",
          },
        },

        border: {
          DEFAULT: "var(--border)",
          soft: "var(--stroke-1)",
        },

        ring: {
          DEFAULT: "var(--ring)",
        },

        primary: {
          50: "var(--color-primary-50)",
          100: "var(--color-primary-100)",
          200: "var(--color-primary-200)",
          300: "var(--color-primary-300)",
          400: "var(--color-primary-400)",
          500: "var(--color-primary-500)",
          600: "var(--color-primary-600)",
          700: "var(--color-primary-700)",
          800: "var(--color-primary-800)",
          900: "var(--color-primary-900)",
          DEFAULT: "var(--color-primary-500)",
          hover: "var(--color-primary-600)",
          soft: "var(--color-primary-100)",
        },

        secondary: {
          50: "var(--color-secondary-50)",
          100: "var(--color-secondary-100)",
          200: "var(--color-secondary-200)",
          300: "var(--color-secondary-300)",
          400: "var(--color-secondary-400)",
          500: "var(--color-secondary-500)",
          600: "var(--color-secondary-600)",
          700: "var(--color-secondary-700)",
          800: "var(--color-secondary-800)",
          900: "var(--color-secondary-900)",
          DEFAULT: "var(--color-secondary-500)",
          hover: "var(--color-secondary-600)",
          soft: "var(--color-secondary-100)",
        },

        accent: {
          50: "var(--color-accent-50)",
          100: "var(--color-accent-100)",
          200: "var(--color-accent-200)",
          300: "var(--color-accent-300)",
          400: "var(--color-accent-400)",
          500: "var(--color-accent-500)",
          600: "var(--color-accent-600)",
          700: "var(--color-accent-700)",
          800: "var(--color-accent-800)",
          900: "var(--color-accent-900)",
          DEFAULT: "var(--color-accent-500)",
          hover: "var(--color-accent-600)",
          soft: "var(--color-accent-100)",
        },

        highlight: {
          50: "var(--color-highlight-50)",
          100: "var(--color-highlight-100)",
          200: "var(--color-highlight-200)",
          300: "var(--color-highlight-300)",
          400: "var(--color-highlight-400)",
          500: "var(--color-highlight-500)",
          600: "var(--color-highlight-600)",
          700: "var(--color-highlight-700)",
          800: "var(--color-highlight-800)",
          900: "var(--color-highlight-900)",
          DEFAULT: "var(--color-highlight-500)",
          hover: "var(--color-highlight-600)",
          soft: "var(--color-highlight-100)",
        },

        brand: {
          50: "var(--color-brand-50)",
          100: "var(--color-brand-100)",
          200: "var(--color-brand-200)",
          300: "var(--color-brand-300)",
          400: "var(--color-brand-400)",
          500: "var(--color-brand-500)",
          600: "var(--color-brand-600)",
          700: "var(--color-brand-700)",
          800: "var(--color-brand-800)",
          900: "var(--color-brand-900)",
          DEFAULT: "var(--color-brand-500)",
        },

        solar: {
          50: "var(--color-accent-50)",
          100: "var(--color-accent-100)",
          200: "var(--color-accent-200)",
          300: "var(--color-accent-300)",
          400: "var(--color-accent-400)",
          500: "var(--color-accent-500)",
          600: "var(--color-accent-600)",
          700: "var(--color-accent-700)",
          800: "var(--color-accent-800)",
          900: "var(--color-accent-900)",
        },

        coral: {
          50: "var(--color-highlight-50)",
          100: "var(--color-highlight-100)",
          200: "var(--color-highlight-200)",
          300: "var(--color-highlight-300)",
          400: "var(--color-highlight-400)",
          500: "var(--color-highlight-500)",
          600: "var(--color-highlight-600)",
          700: "var(--color-highlight-700)",
          800: "var(--color-highlight-800)",
          900: "var(--color-highlight-900)",
        },

        overlay: {
          dark: "var(--overlay-dark)",
          soft: "var(--overlay-dark-soft)",
          strong: "var(--overlay-dark-strong)",
        },

        success: {
          bg: "var(--badge-success-bg)",
          border: "var(--badge-success-border)",
          text: "var(--badge-success-text)",
        },

        info: {
          bg: "var(--badge-info-bg)",
          border: "var(--badge-info-border)",
          text: "var(--badge-info-text)",
        },

        warning: {
          bg: "var(--badge-warning-bg)",
          border: "var(--badge-warning-border)",
          text: "var(--badge-warning-text)",
        },

        danger: {
          bg: "var(--badge-danger-bg)",
          border: "var(--badge-danger-border)",
          text: "var(--badge-danger-text)",
        },
      },

      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },

      fontSize: {
        xs: "var(--font-size-xs)",
        sm: "var(--font-size-sm)",
        base: "var(--font-size-base)",
        lg: "var(--font-size-lg)",
        h1: "var(--font-size-h1)",
        h2: "var(--font-size-h2)",
        h3: "var(--font-size-h3)",
      },

      borderRadius: {
        md: "var(--radius-md)",
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-2xl)",
        "3xl": "var(--radius-3xl)",
        full: "var(--radius-full)",
      },

      boxShadow: {
        sm: "var(--shadow-sm)",
        panel: "var(--shadow)",
        md: "var(--shadow-md)",
        glow: "var(--shadow-glass)",
        primary: "var(--primary-shadow)",
      },

      lineHeight: {
        relaxedPlus: "1.75",
      },

      letterSpacing: {
        tightish: "-0.01em",
      },

      backdropBlur: {
        10: "10px",
        12: "12px",
      },

      backgroundImage: {
        "brand-gradient": "var(--primary-grad)",
        "bg-1": "var(--bg-grad-1)",
        "bg-2": "var(--bg-grad-2)",
        "bg-3": "var(--bg-grad-3)",
        "button-primary": "var(--button-primary-bg)",
      },

      maxWidth: {
        "7xl": "var(--container-7xl)",
      },

      screens: {
        xs: "475px",
      },
    },
  },
  plugins: [],
};