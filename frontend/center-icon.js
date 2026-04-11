import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function centerIcon() {
  const inputPath = join(__dirname, 'resources', 'icon.png');

  console.log('📖 Reading icon from:', inputPath);

  // 讀取圖片
  const image = sharp(inputPath);
  const metadata = await image.metadata();

  console.log(`📏 Original size: ${metadata.width}x${metadata.height}`);

  // 裁切掉下方的文字部分（保留上方約 80% 的心形部分）
  const heartHeight = Math.floor(metadata.height * 0.75);
  const heartWidth = metadata.width;

  console.log('✂️  Cropping to heart only...');

  // 裁切心形部分
  const croppedBuffer = await image
    .extract({
      left: 0,
      top: 0,
      width: heartWidth,
      height: heartHeight
    })
    .toBuffer();

  // 將心形置中在正方形畫布上（不縮小）
  const size = Math.max(heartWidth, heartHeight);

  console.log(`📐 Creating ${size}x${size} centered canvas...`);

  // 計算置中所需的 padding
  const verticalPadding = Math.floor((size - heartHeight) / 2);
  const horizontalPadding = Math.floor((size - heartWidth) / 2);

  await sharp(croppedBuffer)
    .extend({
      top: verticalPadding,
      bottom: size - heartHeight - verticalPadding,
      left: horizontalPadding,
      right: size - heartWidth - horizontalPadding,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toFile(inputPath + '.tmp');

  // 替換原檔案
  const { renameSync } = await import('fs');
  renameSync(inputPath + '.tmp', inputPath);

  console.log('✅ Icon centered successfully!');
  console.log('📍 Saved to:', inputPath);
  console.log('🎯 Next: npx @capacitor/assets generate --iconBackgroundColor=#FFFFFF --android --ios');
}

centerIcon().catch(err => {
  console.error('❌ Error:', err);
  process.exit(1);
});
