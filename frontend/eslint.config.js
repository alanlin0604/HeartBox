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
    'add-padding.js',
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
    },
  },
])
