import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { renameSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function fixIcon() {
  const inputPath = join(__dirname, 'resources', 'icon.png');

  console.log('📖 Reading icon from:', inputPath);

  const image = sharp(inputPath);
  const metadata = await image.metadata();

  console.log(`📏 Original size: ${metadata.width}x${metadata.height}`);

  // 使用 trim 自動偵測並裁切掉透明邊緣
  console.log('✂️  Trimming transparent edges...');

  const trimmed = await image
    .trim({
      background: { r: 0, g: 0, b: 0, alpha: 0 },
      threshold: 0
    })
    .toBuffer();

  const trimmedImage = sharp(trimmed);
  const trimmedMetadata = await trimmedImage.metadata();

  console.log(`📐 After trim: ${trimmedMetadata.width}x${trimmedMetadata.height}`);

  // 創建正方形畫布，使用較大的邊作為基準，並放大 20%
  const maxDimension = Math.max(trimmedMetadata.width, trimmedMetadata.height);
  const finalSize = Math.floor(maxDimension * 1.3); // 放大 30% 讓圖示更大

  console.log(`🎯 Creating ${finalSize}x${finalSize} canvas...`);

  // 先將圖示縮放到適合的大小（占畫布的 62%，適應 Android 圓形安全區域）
  const targetIconSize = Math.floor(finalSize * 0.62);

  const resized = await trimmedImage
    .resize(targetIconSize, targetIconSize, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toBuffer();

  // 計算置中的 padding
  const padding = Math.floor((finalSize - targetIconSize) / 2);

  // 將圖示置中在正方形畫布上
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

  console.log('✅ Icon fixed successfully!');
  console.log(`📍 Final size: ${finalSize}x${finalSize}`);
  console.log('🎯 Next: npx @capacitor/assets generate --iconBackgroundColor=#FFFFFF --android --ios');
}

fixIcon().catch(err => {
  console.error('❌ Error:', err);
  process.exit(1);
});
