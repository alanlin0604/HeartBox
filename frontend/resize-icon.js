import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { renameSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function resizeIcon() {
  const inputPath = join(__dirname, 'resources', 'icon.png');
  const outputPath = inputPath;

  console.log('Reading icon from:', inputPath);

  // 讀取原始圖片
  const image = sharp(inputPath);
  const metadata = await image.metadata();

  console.log(`Original size: ${metadata.width}x${metadata.height}`);

  // 不縮小，保持原始大小（Capacitor Assets 會自動處理）
  const newSize = metadata.width;
  const padding = 0;

  console.log(`Resizing to ${newSize}x${newSize} with ${padding}px padding`);

  // 縮小圖示並添加透明邊距
  await sharp(inputPath)
    .resize(newSize, newSize, {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .extend({
      top: padding,
      bottom: padding,
      left: padding,
      right: padding,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .toFile(outputPath + '.tmp');

  // 替換原檔案
  renameSync(outputPath + '.tmp', outputPath);

  console.log('✅ Icon resized successfully!');
  console.log('📍 New icon saved to:', outputPath);
  console.log('🎯 Now run: npx @capacitor/assets generate --iconBackgroundColor=#7c3aed --android --ios');
}

resizeIcon().catch(err => {
  console.error('❌ Error:', err);
  process.exit(1);
});
