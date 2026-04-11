#!/usr/bin/env node
import sharp from 'sharp'
import { readdir } from 'fs/promises'
import { join, parse } from 'path'

const ICONS_DIR = new URL('../public/icons', import.meta.url).pathname.slice(1) // Remove leading slash on Windows

async function optimizeImages() {
  const files = await readdir(ICONS_DIR)
  const pngFiles = files.filter(f => f.endsWith('.png') && !f.includes('icon-192') && !f.includes('icon-512'))

  console.log(`Found ${pngFiles.length} PNG files to optimize\n`)

  for (const file of pngFiles) {
    const inputPath = join(ICONS_DIR, file)
    const { name } = parse(file)
    const webpPath = join(ICONS_DIR, `${name}.webp`)

    try {
      const info = await sharp(inputPath)
        .webp({ quality: 85, effort: 6 })
        .toFile(webpPath)

      const originalSize = (await sharp(inputPath).metadata()).size
      const reduction = ((1 - info.size / originalSize) * 100).toFixed(1)

      console.log(`✓ ${file} → ${name}.webp (-${reduction}%)`)
    } catch (err) {
      console.error(`✗ ${file}: ${err.message}`)
    }
  }

  console.log('\n✨ Image optimization complete!')
}

optimizeImages().catch(console.error)
