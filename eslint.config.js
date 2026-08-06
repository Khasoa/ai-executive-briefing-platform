import js from "@eslint/js"
import globals from "globals"
import react from "eslint-plugin-react"
import reactHooks from "eslint-plugin-react-hooks"
import reactRefresh from "eslint-plugin-react-refresh"
import { defineConfig, globalIgnores } from "eslint/config"

export default defineConfig([
  globalIgnores(["dist", "backend", "node_modules"]),
  {
    files: ["**/*.{js,jsx}"],
    extends: [
      js.configs.recommended,
      react.configs.flat.recommended,
      react.configs.flat["jsx-runtime"],
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      // Allow constant re-exports from UI primitive modules (e.g. buttonVariants).
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      // Component names and similar PascalCase bindings often look unused to the core rule.
      "no-unused-vars": ["error", { varsIgnorePattern: "^[A-Z_]" }],
      // Standard fetch-on-mount pattern in useApiQuery; not a cascading-render bug.
      "react-hooks/set-state-in-effect": "off",
      // PropTypes are not used in this JavaScript codebase.
      "react/prop-types": "off",
    },
  },
])
