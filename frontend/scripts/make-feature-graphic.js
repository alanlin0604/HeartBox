// Generate Play Store feature graphic (1024x500) from logo + brand colors.
// Output: frontend/store-assets/feature-graphic-{lang}.png
// Usage: node scripts/make-feature-graphic.js
import sharp from 'sharp'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { mkdirSync, existsSync } from 'fs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const OUT_DIR = join(ROOT, 'store-assets')
const LOGO = join(ROOT, 'public', 'logo-icon.png')

if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true })

const W = 1024
const H = 500

// Brand gradient (matching index.css --bg-gradient-* tokens)
function gradientSvg() {
  return `
<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1a1440"/>
      <stop offset="50%" stop-color="#3b1d6b"/>
      <stop offset="100%" stop-color="#7c3aed"/>
    </linearGradient>
    <radialGradient id="glow" cx="20%" cy="50%" r="40%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#g)"/>
  <rect width="${W}" height="${H}" fill="url(#glow)"/>
</svg>`
}

// Text overlay. Uses system CJK fonts (Microsoft JhengHei on Windows,
// Noto Sans CJK elsewhere). Font fallbacks in font-family handle both.
function textSvg({ title, subtitle, tagline }) {
  const fontStack = '"Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC", "Hiragino Sans", "Yu Gothic", sans-serif'
  return `
<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title { font: 700 64px ${fontStack}; fill: #ffffff; }
    .subtitle { font: 600 36px ${fontStack}; fill: #e9d5ff; }
    .tagline { font: 400 22px ${fontStack}; fill: #d8b4fe; }
  </style>
  <text x="380" y="200" class="title">${title}</text>
  <text x="380" y="260" class="subtitle">${subtitle}</text>
  <text x="380" y="320" class="tagline">${tagline}</text>
</svg>`
}

const VARIANTS = [
  {
    lang: 'zh',
    title: 'HeartBox',
    subtitle: '心事盒',
    tagline: '私密 AI 心情日記 · 加密保護',
  },
  {
    lang: 'en',
    title: 'HeartBox',
    subtitle: 'Your Private Mood Journal',
    tagline: 'AI-powered · End-to-end encrypted',
  },
  {
    lang: 'ja',
    title: 'HeartBox',
    subtitle: '心の箱',
    tagline: 'AI気分日記 · 暗号化保護',
  },
]

const logoBuf = await sharp(LOGO)
  .resize(280, 280, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
  .png()
  .toBuffer()

for (const v of VARIANTS) {
  const out = join(OUT_DIR, `feature-graphic-${v.lang}.png`)
  await sharp(Buffer.from(gradientSvg()))
    .composite([
      { input: logoBuf, left: 70, top: 110 },
      { input: Buffer.from(textSvg(v)), left: 0, top: 0 },
    ])
    .png()
    .toFile(out)
  console.log(`wrote ${out}`)
}
