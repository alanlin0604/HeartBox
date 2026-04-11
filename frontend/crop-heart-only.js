import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { renameSync, copyFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function cropHeartOnly() {
  const inputPath = join(__dirname, 'resources', 'icon.png');
  const backupPath = join(__dirname, 'public', 'logo.png');

  console.log('📖 Reading original logo...');
  copyFileSync(backupPath, inputPath);

  const image = sharp(inputPath);
  const metadata = await image.metadata();

  console.log(`📏 Original size: ${metadata.width}x${metadata.height}`);

  // 裁切掉底部的 "HeartBox" 文字，只保留心形部分（大約上方 78%）
  const heartHeight = Math.floor(metadata.height * 0.78);

  console.log(`✂️  Cropping to heart only (top ${heartHeight}px)...`);

  const cropped = await image
    .extract({
      left: 0,
      top: 0,
      width: metadata.width,
      height: heartHeight
    })
    .toBuffer();

  // 對裁切後的圖片做 trim，移除多餘透明區域
  console.log('🔍 Trimming transparent edges...');

  const trimmed = await sharp(cropped)
    .trim({
      background: { r: 0, g: 0, b: 0, alpha: 0 },
      threshold: 10
    })
    .toBuffer();

  const trimmedImage = sharp(trimmed);
  const trimmedMeta = await trimmedImage.metadata();

  console.log(`📐 Trimmed size: ${trimmedMeta.width}x${trimmedMeta.height}`);

  // 創建正方形畫布，60% 填充（確保完全不超出圓形安全區域）
  const maxDim = Math.max(trimmedMeta.width, trimmedMeta.height);
  const finalSize = Math.ceil(maxDim / 0.60);
  const iconSize = Math.floor(finalSize * 0.60);

  console.log(`🎯 Canvas: ${finalSize}x${finalSize}, Icon: ${iconSize}x${iconSize}`);

  // 縮放並置中
  const resized = await trimmedImage
    .resize(iconSize, iconSize, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toBuffer();

  const basePadding = Math.floor((finalSize - iconSize) / 2);
  const topPadding = basePadding + 15;  // 增加上方 padding，讓圖示下移
  const bottomPadding = finalSize - iconSize - topPadding;
  const sidePadding = basePadding;

  console.log(`📦 Adding padding (top: ${topPadding}px, bottom: ${bottomPadding}px, sides: ${sidePadding}px)`);

  await sharp(resized)
    .extend({
      top: topPadding,
      bottom: bottomPadding,
      left: sidePadding,
      right: sidePadding,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toFile(inputPath + '.tmp');

  renameSync(inputPath + '.tmp', inputPath);

  console.log('✅ Heart icon created (no text)!');
  console.log(`📍 Final: ${finalSize}x${finalSize}`);
}

cropHeartOnly().catch(err => {
  console.error('❌ Error:', err);
  process.exit(1);
});
