import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { renameSync, copyFileSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function recenterIcon() {
  const inputPath = join(__dirname, 'resources', 'icon.png');
  const backupPath = join(__dirname, 'public', 'logo.png');

  console.log('📖 Restoring original icon...');

  // 從備份還原原始圖片
  copyFileSync(backupPath, inputPath);

  const image = sharp(inputPath);
  const metadata = await image.metadata();

  console.log(`📏 Original size: ${metadata.width}x${metadata.height}`);

  // 使用 trim 找出實際內容範圍
  console.log('✂️  Trimming to find actual content bounds...');

  const trimmed = await image
    .trim({
      background: { r: 0, g: 0, b: 0, alpha: 0 },
      threshold: 10
    })
    .toBuffer();

  const trimmedImage = sharp(trimmed);
  const trimmedMeta = await trimmedImage.metadata();

  console.log(`📐 Trimmed size: ${trimmedMeta.width}x${trimmedMeta.height}`);

  // 創建正方形畫布
  const canvasSize = Math.max(trimmedMeta.width, trimmedMeta.height);

  // 縮小到 65% 以符合圓形安全區域
  const finalCanvasSize = Math.ceil(canvasSize / 0.65);
  const iconSize = Math.floor(finalCanvasSize * 0.65);

  console.log(`🎯 Target canvas: ${finalCanvasSize}x${finalCanvasSize}`);
  console.log(`📦 Icon size: ${iconSize}x${iconSize} (65%)`);

  // 先將內容縮放到目標大小
  const resized = await trimmedImage
    .resize(iconSize, iconSize, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toBuffer();

  // 計算完全置中的 padding
  const padding = Math.floor((finalCanvasSize - iconSize) / 2);

  console.log(`📍 Adding ${padding}px padding on all sides for perfect centering`);

  // 加上完全相等的 padding 以確保置中
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

  console.log('✅ Icon perfectly centered!');
  console.log(`📍 Final size: ${finalCanvasSize}x${finalCanvasSize}`);
}

recenterIcon().catch(err => {
  console.error('❌ Error:', err);
  process.exit(1);
});
