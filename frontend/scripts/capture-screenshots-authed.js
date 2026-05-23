// Capture Play Store screenshots from authenticated pages (Journal,
// Dashboard, AI Chat, Health/Sleep Analysis, Community). Companion to
// capture-screenshots.js, which only covers the public marketing pages.
//
// Why a separate script?
//   - Public pages don't need auth/data, so the original script can run
//     against the live prod site (https://heartbox.tw) and looks
//     authentic regardless of who's logged in.
//   - Authed pages need real-looking journal/sleep/chat content; the
//     `seed_demo_account` management command populates demo@heartbox.tw
//     with 14 days of realistic zh-TW journal data. Default target is
//     the local dev server so we don't have to seed production.
//
// Setup (one-time):
//   cd backend && python manage.py seed_demo_account     # seeds demo user
//   cd frontend && npm run build && npm run preview &    # or `npm run dev`
//
// Run (using local preview as the target):
//   TARGET=http://localhost:4173 \
//     DEMO_USER=demo@heartbox.tw DEMO_PASS=DemoPass2026 \
//     node scripts/capture-screenshots-authed.js
//
// Run against production (assuming demo seed is up):
//   TARGET=https://heartbox.tw \
//     DEMO_USER=demo@heartbox.tw DEMO_PASS=DemoPass2026 \
//     node scripts/capture-screenshots-authed.js
//
// Output: frontend/store-assets/screenshots/{lang}/{05..09}-*.png
// Filenames intentionally start at 05 so they sort after the 01-04 set
// produced by capture-screenshots.js.
import puppeteer from 'puppeteer-core'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { mkdirSync, existsSync, statSync } from 'fs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const OUT_BASE = join(__dirname, '..', 'store-assets', 'screenshots')

const TARGET = (process.env.TARGET || 'http://localhost:4173').replace(/\/$/, '')
const VIEWPORT = { width: 1080, height: 2400, deviceScaleFactor: 1 }
const LANGS = ['zh-TW', 'en', 'ja']

const DEMO_USER = process.env.DEMO_USER || 'demo@heartbox.tw'
const DEMO_PASS = process.env.DEMO_PASS || 'DemoPass2026'

// Auth-required pages to capture. `wait` is a per-page extra delay (ms)
// after networkidle2 so charts have time to finish animating in.
const PAGES = [
  { name: '05-journal',    path: '/',                wait: 2000 },
  { name: '06-dashboard',  path: '/dashboard',       wait: 3500 }, // recharts animations
  { name: '07-ai-chat',    path: '/ai-chat',         wait: 2000 },
  { name: '08-sleep',      path: '/sleep-analysis',  wait: 3500 }, // sleep trend chart
  { name: '09-community',  path: '/community',       wait: 2000 },
]

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
console.log(`Demo user: ${DEMO_USER}`)

const browser = await puppeteer.launch({
  executablePath,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})

// Per-locale: open a fresh context (no shared cookies between languages),
// log in, then walk through the page list. We can't reuse the page across
// languages because LanguageContext reads from localStorage on init —
// switching `language` mid-session would need a full reload anyway, so
// it's simpler to redo login per locale.
try {
  for (const lang of LANGS) {
    console.log(`\n=== Locale: ${lang} ===`)
    const dir = join(OUT_BASE, lang)
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true })

    const context = await browser.createBrowserContext()
    const page = await context.newPage()
    await page.setViewport(VIEWPORT)
    await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }])
    await page.evaluateOnNewDocument((l) => {
      try {
        localStorage.setItem('language', l)
        localStorage.setItem('theme', 'light')
        localStorage.setItem('theme_manual', '1')
        // Mark onboarding done so the modal doesn't cover the screenshots.
        localStorage.setItem('heartbox_onboarding_skipped', '1')
      } catch { /* ignore */ }
    }, lang)

    // ---- Login ----
    try {
      await page.goto(`${TARGET}/login`, { waitUntil: 'networkidle2', timeout: 30_000 })

      // Robust to label/placeholder localisation: select by input type.
      await page.waitForSelector('input[type="text"], input[name="username"], input[name="email"]', { timeout: 10_000 })
      const userInput = await page.$('input[name="username"]')
        || await page.$('input[name="email"]')
        || await page.$('input[type="text"]')
      await userInput.click({ clickCount: 3 })
      await userInput.type(DEMO_USER)

      const passInput = await page.$('input[type="password"]')
      await passInput.click({ clickCount: 3 })
      await passInput.type(DEMO_PASS)

      await Promise.all([
        page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 20_000 }),
        page.click('button[type="submit"]'),
      ])
      console.log(`  ✓ login ok`)
    } catch (err) {
      console.warn(`  ✗ login failed for ${lang}: ${err.message}`)
      await page.close()
      await context.close()
      continue
    }

    // ---- Per-page capture ----
    for (const p of PAGES) {
      try {
        await page.goto(TARGET + p.path, { waitUntil: 'networkidle2', timeout: 30_000 })
        // Give charts / WebSocket / lazy chunks time to settle. The
        // dashboard's MoodPrediction + recharts animation is the slowest.
        await new Promise((r) => setTimeout(r, p.wait))
        // Scroll back to top — some pages restore scroll position on
        // re-entry and the screenshot would miss the header.
        await page.evaluate(() => window.scrollTo(0, 0))
        await new Promise((r) => setTimeout(r, 200))
        const out = join(dir, `${p.name}.png`)
        await page.screenshot({ path: out, fullPage: false })
        console.log(`  ✓ ${lang}/${p.name}.png`)
      } catch (err) {
        console.warn(`  ✗ ${lang}/${p.name}: ${err.message}`)
      }
    }

    await page.close()
    await context.close()
  }
} finally {
  await browser.close()
}

console.log('\nDone. Output: frontend/store-assets/screenshots/{zh-TW,en,ja}/05-09-*.png')
console.log('If any frame looks wrong, re-run with TARGET=http://localhost:4173 and tweak the wait values.')
