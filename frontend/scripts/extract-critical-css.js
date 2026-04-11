#!/usr/bin/env node
/**
 * Extract Critical CSS for Above-the-Fold Content
 *
 * Usage: node scripts/extract-critical-css.js
 *
 * This script extracts critical CSS needed for above-the-fold rendering
 * and inlines it in index.html for faster First Contentful Paint.
 */

import { readFile, writeFile } from 'fs/promises'
import { join } from 'path'

const DIST_DIR = 'dist'
const INDEX_PATH = join(DIST_DIR, 'index.html')

// Critical selectors that should be inlined (above-the-fold styles)
const CRITICAL_SELECTORS = [
  // CSS Custom Properties
  ':root',

  // Base elements
  'html', 'body', '#root',

  // Layout
  '.layout', 'nav', 'header',

  // Loading states
  '.loading-spinner', '.skeleton',

  // Hero/above-fold components
  '.btn-primary', '.btn-secondary',
  '.glass-card', '.surface-elevated',

  // Typography base
  'h1', 'h2', 'h3', 'p',

  // Utility classes (commonly used)
  '.sr-only', '.text-center', '.flex', '.grid',
]

async function extractCriticalCSS() {
  try {
    // Read built index.html
    const htmlContent = await readFile(INDEX_PATH, 'utf-8')

    // Find CSS file reference
    const cssMatch = htmlContent.match(/<link rel="stylesheet"[^>]*href="([^"]+\.css)"/)
    if (!cssMatch) {
      console.warn('⚠ No CSS file found in index.html')
      return
    }

    const cssPath = join(DIST_DIR, cssMatch[1])
    const fullCSS = await readFile(cssPath, 'utf-8')

    // Extract rules matching critical selectors
    // This is a simplified approach - for production, use a proper CSS parser
    const criticalRules = []
    const ruleRegex = /([^{}]+)\{([^{}]*)\}/g
    let match

    while ((match = ruleRegex.exec(fullCSS)) !== null) {
      const selector = match[1].trim()
      const isCritical = CRITICAL_SELECTORS.some(critical =>
        selector.includes(critical) || selector.startsWith(critical)
      )

      if (isCritical) {
        criticalRules.push(`${selector}{${match[2]}}`)
      }
    }

    const criticalCSS = criticalRules.join('\n')

    // Inline critical CSS in <head>
    const updatedHTML = htmlContent.replace(
      '<title>',
      `<style id="critical-css">${criticalCSS}</style>\n    <title>`
    )

    await writeFile(INDEX_PATH, updatedHTML, 'utf-8')

    const savings = ((criticalCSS.length / fullCSS.length) * 100).toFixed(1)
    console.log(`✓ Critical CSS extracted (${savings}% of total CSS)`)
    console.log(`  Inlined: ${(criticalCSS.length / 1024).toFixed(1)} KB`)
    console.log(`  Total CSS: ${(fullCSS.length / 1024).toFixed(1)} KB`)
  } catch (err) {
    console.error('✗ Failed to extract critical CSS:', err.message)
  }
}

extractCriticalCSS().catch(console.error)
