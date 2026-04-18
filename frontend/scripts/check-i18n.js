#!/usr/bin/env node
/**
 * i18n Completeness Checker
 * Validates that all translation files have the same keys
 * and reports missing or extra translations
 */

import { readFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const LOCALES_DIR = join(__dirname, '../src/locales')
const LOCALES = ['zh-TW', 'en', 'ja']
const BASE_LOCALE = 'zh-TW' // Reference locale

function loadLocale(locale) {
  try {
    const path = join(LOCALES_DIR, `${locale}.json`)
    const content = readFileSync(path, 'utf-8')
    return JSON.parse(content)
  } catch (error) {
    console.error(`❌ Failed to load ${locale}.json:`, error.message)
    process.exit(1)
  }
}

function getAllKeys(obj) {
  // For flat structure with dot-separated keys
  return Object.keys(obj)
}

function checkCompleteness() {
  console.log('🔍 Checking i18n completeness...\n')

  // Load all locales
  const locales = {}
  for (const locale of LOCALES) {
    locales[locale] = loadLocale(locale)
  }

  // Get all keys from base locale
  const baseKeys = new Set(getAllKeys(locales[BASE_LOCALE]))
  console.log(`📋 Base locale (${BASE_LOCALE}): ${baseKeys.size} keys\n`)

  let hasErrors = false

  // Check each locale against base
  for (const locale of LOCALES) {
    if (locale === BASE_LOCALE) continue

    const localeKeys = new Set(getAllKeys(locales[locale]))
    const missing = [...baseKeys].filter(k => !localeKeys.has(k))
    const extra = [...localeKeys].filter(k => !baseKeys.has(k))

    console.log(`🌐 ${locale}.json (${localeKeys.size} keys)`)

    if (missing.length > 0) {
      hasErrors = true
      console.log(`  ❌ Missing ${missing.length} keys:`)
      missing.slice(0, 10).forEach(key => console.log(`     - ${key}`))
      if (missing.length > 10) {
        console.log(`     ... and ${missing.length - 10} more`)
      }
    }

    if (extra.length > 0) {
      hasErrors = true
      console.log(`  ⚠️  Extra ${extra.length} keys:`)
      extra.slice(0, 10).forEach(key => console.log(`     - ${key}`))
      if (extra.length > 10) {
        console.log(`     ... and ${extra.length - 10} more`)
      }
    }

    if (missing.length === 0 && extra.length === 0) {
      console.log('  ✅ Complete')
    }

    console.log('')
  }

  // Check for empty values
  console.log('🔍 Checking for empty values...\n')

  for (const locale of LOCALES) {
    const emptyKeys = Object.entries(locales[locale])
      .filter(([key, value]) => value === '' || value === null || value === undefined)
      .map(([key]) => key)

    if (emptyKeys.length > 0) {
      hasErrors = true
      console.log(`⚠️  ${locale}.json has ${emptyKeys.length} empty values:`)
      emptyKeys.slice(0, 5).forEach(key => console.log(`   - ${key}`))
      if (emptyKeys.length > 5) {
        console.log(`   ... and ${emptyKeys.length - 5} more`)
      }
      console.log('')
    }
  }

  if (hasErrors) {
    console.log('❌ i18n completeness check failed\n')
    process.exit(1)
  } else {
    console.log('✅ All translations are complete!\n')
  }
}

checkCompleteness()
