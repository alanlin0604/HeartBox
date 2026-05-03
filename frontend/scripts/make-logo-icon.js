// Generate frontend/public/logo-icon.png (heart-only, no "HeartBox" text)
// from frontend/public/logo.png. Run once after logo.png changes:
//   node scripts/make-logo-icon.js
import sharp from 'sharp'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const SRC = join(__dirname, '..', 'public', 'logo.png')
const OUT = join(__dirname, '..', 'public', 'logo-icon.png')

const meta = await sharp(SRC).metadata()
const heartHeight = Math.floor(meta.height * 0.78)

const cropped = await sharp(SRC)
  .extract({ left: 0, top: 0, width: meta.width, height: heartHeight })
  .toBuffer()

await sharp(cropped)
  .trim({ background: { r: 0, g: 0, b: 0, alpha: 0 }, threshold: 10 })
  .toFile(OUT)

console.log(`logo-icon.png written (cropped from ${meta.width}x${meta.height})`)
