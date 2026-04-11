import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { renameSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function addPadding() {
  const inputPath = join(__dirname, 'resources', 'icon.png');

  console.log('📖 Reading icon from:', inputPath);

  const image = sharp(inputPath);
  const metadata = await image.metadata();

  console.log(`📏 Original size: ${metadata.width}x${metadata.height}`);

  // 縮小到 65% 並加上透明 padding（確保符合圓形安全區域）
  const originalSize = Math.max(metadata.width, metadata.height);
  const iconSize = Math.floor(originalSize * 0.65);
  const finalSize = originalSize;

  console.log(`🔍 Resizing icon to ${iconSize}x${iconSize} (65%)`);
  console.log(`📐 Final canvas: ${finalSize}x${finalSize}`);

  // 先縮放圖示
  const resized = await image
    .resize(iconSize, iconSize, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toBuffer();

  // 計算 padding
  const padding = Math.floor((finalSize - iconSize) / 2);

  console.log(`📦 Adding ${padding}px padding on each side`);

  // 加上透明 padding
  await sharp(resized)
    .extend({
      top: padding,
      bottom: padding,
      left: padding,
      right: padding,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toFile(inputPath + '.tmp');

  // 替換原檔案
  renameSync(inputPath + '.tmp', inputPath);

  console.log('✅ Padding added successfully!');
  console.log('🎯 Icon is now 65% with safe zone padding');
}

addPadding().catch(err => {
  console.error('❌ Error:', err);
  process.exit(1);
});
