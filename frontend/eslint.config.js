import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores([
    'dist',
    'android',
    'ios',
    '*.config.js',
    // One-off Node CLI utilities for icon prep — not part of the app bundle,
    // run with `node <file>.js`. Don't lint with browser globals.
    'add-padding.js',
    'center-icon.js',
    'crop-heart-only.js',
    'fix-icon.js',
    'recenter-icon.js',
    'resize-icon.js',
    'scripts/**',
  ]),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    plugins: { react },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      // Mark JSX-referenced identifiers as used so motion.div, AnimatePresence etc.
      // don't trip no-unused-vars. We deliberately don't pull in the rest of
      // eslint-plugin-react — just this single rule.
      'react/jsx-uses-vars': 'error',
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
      // Prevent console.log in production code, but allow warn/error for debugging
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      // React 19's stricter "no setState during effect body" rule fires on the
      // standard load → setState pattern (`useEffect(() => { fetch().then(setData) }, [])`).
      // We rely on that pattern across ~14 widgets/pages and the alternatives
      // (suspense, useReducer with thunk-like dispatch) would be a much larger
      // refactor. Keep the rule visible as a warning so genuine new mistakes
      // still surface, but don't fail the build on existing usage.
      'react-hooks/set-state-in-effect': 'warn',
    },
  },
])
