// Capture Play Store screenshots from the production frontend.
//
// Captures public marketing pages at 1080x2400 (modern phone aspect, Play
// Store accepts 1080-3840 wide and 9:16 ~ 16:9). For each of the three
// locales, the script presets localStorage so the page renders in that
// language and forces light mode (Play Store screenshots tend to look
// brighter / more inviting in light theme).
//
// Authenticated pages (Journal, Dashboard, AI chat, Health, Weekly
// summary) need real data and are easier to capture from the running
// emulator — manual screenshots there will look more authentic anyway.
//
// Setup:
//   cd frontend
//   npm install        # picks up puppeteer-core devDep
//
// Run:
//   # Against the live site (recommended — real data, real network):
//   node scripts/capture-screenshots.js
//
//   # Against a local preview (fully offline):
//   npm run build && npm run preview &
//   TARGET=http://localhost:4173 node scripts/capture-screenshots.js
//
// Output: frontend/store-assets/screenshots/{lang}/{page}.png
import puppeteer from 'puppeteer-core'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { mkdirSync, existsSync, statSync } from 'fs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUT_BASE = join(__dirname, '..', 'store-assets', 'screenshots')

const TARGET = process.env.TARGET || 'https://heartbox.tw'
const VIEWPORT = { width: 1080, height: 2400, deviceScaleFactor: 1 }

const LANGS = ['zh-TW', 'en', 'ja']
// Pages that don't require backend data or auth. /pricing was dropped
// because it depends on a backend round-trip for plan data — when that
// hangs, the screenshot captures only the LoadingSpinner.
const PAGES = [
  { name: '01-landing', path: '/' },
  { name: '02-login', path: '/login' },
  { name: '03-register', path: '/register' },
  { name: '04-privacy', path: '/privacy' },
]

// Find Chrome on Windows. Adjust if your install path differs.
function findChrome() {
  const candidates = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
  ].filter(Boolean)
  for (const p of candidates) {
    try { if (statSync(p).isFile()) return p } catch { /* skip */ }
  }
  throw new Error('Chrome not found. Set CHROME env var to chrome.exe path.')
}

const executablePath = process.env.CHROME || findChrome()
console.log(`Chrome: ${executablePath}`)
console.log(`Target: ${TARGET}`)

const browser = await puppeteer.launch({
  executablePath,
  headless: 'new',
  args: ['--lang=zh-TW', '--no-sandbox', '--disable-dev-shm-usage'],
})

try {
  for (const lang of LANGS) {
    const dir = join(OUT_BASE, lang)
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true })

    for (const p of PAGES) {
      const page = await browser.newPage()
      await page.setViewport(VIEWPORT)

      // Preset language + force light mode before navigation so first
      // paint is already in target locale and theme. theme_manual prevents
      // ThemeContext from auto-switching back to OS preference.
      await page.evaluateOnNewDocument((l) => {
        try {
          localStorage.setItem('language', l)
          localStorage.setItem('theme', 'light')
          localStorage.setItem('theme_manual', '1')
        } catch { /* ignore */ }
      }, lang)
      // Also tell Chrome itself to report a light color scheme so any
      // CSS that bypasses ThemeContext (e.g. media queries) goes light too.
      await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }])

      const url = TARGET.replace(/\/$/, '') + p.path
      try {
        await page.goto(url, { waitUntil: 'networkidle2', timeout: 30_000 })
        // Let lazy fonts and animations settle
        await new Promise((r) => setTimeout(r, 1500))
        const out = join(dir, `${p.name}.png`)
        await page.screenshot({ path: out, fullPage: false })
        console.log(`  ✓ ${lang}/${p.name}.png`)
      } catch (err) {
        console.warn(`  ✗ ${lang}/${p.name}: ${err.message}`)
      } finally {
        await page.close()
      }
    }
  }
} finally {
  await browser.close()
}

console.log('Done. Authed pages (Journal/Dashboard/AI/Health) — capture manually from the emulator.')
