#!/usr/bin/env node
import sharp from 'sharp'
import { readdir, stat } from 'fs/promises'
import { join } from 'path'
import { fileURLToPath } from 'url'
import { dirname } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const ICONS_DIR = join(__dirname, '../public/icons')

async function optimizeImages() {
  console.log('🔍 開始圖片優化...\n')

  try {
    const files = await readdir(ICONS_DIR)
    const pngFiles = files.filter(f =>
      f.endsWith('.png') &&
      !f.includes('icon-192') &&
      !f.includes('icon-512')
    )

    console.log(`找到 ${pngFiles.length} 張 PNG 圖片需要優化\n`)

    let totalOriginalSize = 0
    let totalWebPSize = 0

    for (const file of pngFiles) {
      const inputPath = join(ICONS_DIR, file)
      const name = file.replace('.png', '')
      const webpPath = join(ICONS_DIR, `${name}.webp`)

      try {
        // 獲取原始檔案大小
        const originalStats = await stat(inputPath)
        const originalSize = originalStats.size

        // 轉換為 WebP
        const info = await sharp(inputPath)
          .webp({ quality: 85, effort: 6 })
          .toFile(webpPath)

        const reduction = ((1 - info.size / originalSize) * 100).toFixed(1)
        totalOriginalSize += originalSize
        totalWebPSize += info.size

        console.log(`✓ ${file}`)
        console.log(`  ${(originalSize/1024).toFixed(1)} KB → ${(info.size/1024).toFixed(1)} KB (-${reduction}%)`)
      } catch (err) {
        console.error(`✗ ${file}: ${err.message}`)
      }
    }

    const totalReduction = ((1 - totalWebPSize / totalOriginalSize) * 100).toFixed(1)

    console.log('\n✨ 圖片優化完成!')
    console.log(`\n📊 總計:`)
    console.log(`  原始大小: ${(totalOriginalSize/1024).toFixed(1)} KB`)
    console.log(`  WebP 大小: ${(totalWebPSize/1024).toFixed(1)} KB`)
    console.log(`  總體減少: ${totalReduction}%`)
  } catch (err) {
    console.error('❌ 錯誤:', err.message)
    process.exit(1)
  }
}

optimizeImages()
