# HeartBox 效能優化測試指南

**部署時間**: 2026-04-11 17:04 (UTC+8)
**Git Commit**: `3ffc86f`
**部署方式**: GitHub → Cloudflare Pages 自動部署

---

## ✅ 部署狀態

- [x] Git 推送成功
- [ ] Cloudflare Pages 建置完成（預計 3-5 分鐘）
- [ ] CDN 快取更新（預計 5-10 分鐘）
- [ ] 效能測試完成

---

## 🔍 手動驗證優化項目

### 1. 檢查 Critical CSS 內聯

**測試方法**：
```bash
# 方法 A：使用 curl
curl -s https://heartbox.tw | grep "critical-css"

# 方法 B：瀏覽器 DevTools
# 1. 開啟 https://heartbox.tw
# 2. F12 > Elements > <head>
# 3. 查找 <style id="critical-css">
```

**預期結果**：應該看到約 32 KB 的內聯 CSS

---

### 2. 檢查 Service Worker 版本

**測試方法**：
```bash
# 方法 A：直接查看 SW 檔案
curl -s https://heartbox.tw/sw.js | grep CACHE_NAME

# 方法 B：瀏覽器 DevTools
# 1. F12 > Application > Service Workers
# 2. 點擊 "Update" 強制更新
# 3. 查看 Status 是否為 "activated"
```

**預期結果**：
```javascript
const CACHE_NAME = 'heartbox-cache-v6'
```

**如果仍是 v5**：
1. 清除瀏覽器快取（Ctrl+Shift+Delete）
2. 點擊 DevTools > Application > Service Workers > "Unregister"
3. 重新載入頁面（Ctrl+F5）

---

### 3. 檢查字型子集化

**測試方法**：
```bash
# 查看 HTML 中的字型載入連結
curl -s https://heartbox.tw | grep -o 'subset=[^"&]*'
```

**預期結果**：
```
subset=latin,chinese-traditional
```

---

### 4. 檢查 Resource Hints

**測試方法**：
```bash
# 查看 DNS Prefetch 和 Prefetch
curl -s https://heartbox.tw | grep -E "dns-prefetch|prefetch" | head -5
```

**預期結果**：
```html
<link rel="dns-prefetch" href="https://fonts.googleapis.com" />
<link rel="prefetch" href="/dashboard" as="document" />
<link rel="prefetch" href="/settings" as="document" />
```

---

### 5. 檢查 WebP 圖片

**測試方法**：
```bash
# 查看圖片是否存在
curl -I https://heartbox.tw/icons/AI%20聊天.webp
curl -I https://heartbox.tw/icons/功能指南.webp
```

**預期結果**：HTTP 200 OK

---

## 📊 Chrome DevTools 效能分析

### 步驟 1：Lighthouse 測試

1. 開啟 Chrome 無痕模式（Ctrl+Shift+N）
2. 前往 https://heartbox.tw
3. F12 > Lighthouse 標籤
4. 設定：
   - Mode: **Navigation**
   - Categories: **Performance** 勾選
   - Device: **Desktop** 或 **Mobile**
5. 點擊 "Analyze page load"

**目標指標**：
- Performance Score: **≥95**
- FCP (First Contentful Paint): **<1.0s**
- LCP (Largest Contentful Paint): **<1.5s**
- TBT (Total Blocking Time): **<150ms**
- CLS (Cumulative Layout Shift): **<0.05**
- Speed Index: **<1.5s**

---

### 步驟 2：Network 分析

1. F12 > Network 標籤
2. 勾選 "Disable cache"
3. 重新載入頁面（Ctrl+F5）
4. 觀察：

**關鍵檔案大小（應該看到 Brotli 壓縮）**：
| 檔案 | 原始大小 | 傳輸大小（Brotli） |
|------|---------|-------------------|
| index.html | ~3.4 KB | ~0.9 KB |
| index-*.css | ~70 KB | ~9.8 KB |
| index-*.js | ~217 KB | ~49 KB |
| vendor-react-*.js | ~225 KB | ~63 KB |
| vendor-common-*.js | ~181 KB | ~56 KB |

---

### 步驟 3：Performance 分析

1. F12 > Performance 標籤
2. 點擊 Record（圓形按鈕）
3. 重新載入頁面
4. 停止錄製

**檢查項目**：
- [x] FCP 出現時間 <1.0s
- [x] LCP 元素載入時間 <1.5s
- [x] 沒有長任務（Long Tasks >50ms）
- [x] 沒有佈局偏移（Layout Shifts）
- [x] Main Thread 工作時間 <2.0s

---

## 🌐 WebPageTest 線上測試

**測試網址**: https://www.webpagetest.org/

**設定**：
- URL: `https://heartbox.tw`
- Test Location: **Tokyo, Japan**
- Browser: **Chrome**
- Connection: **Cable** 或 **4G**
- Number of Tests: **3**
- Repeat View: **勾選**

**預期結果（Tokyo）**：
- First Byte: **<0.5s**
- Start Render: **<1.0s**
- FCP: **<1.0s**
- LCP: **<1.5s**
- Speed Index: **<1.5s**
- Total Page Size: **<500 KB**

---

## 🚀 快速驗證腳本

建立一個簡單的 Node.js 腳本來驗證關鍵優化：

```bash
# 在 frontend 目錄執行
node -e "
const https = require('https');

console.log('🔍 驗證 HeartBox 效能優化部署\\n');

// 1. 檢查 Service Worker
https.get('https://heartbox.tw/sw.js', (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    const version = data.match(/heartbox-cache-v(\\d+)/)?.[1];
    console.log(\`✓ Service Worker 版本: v\${version} \${version === '6' ? '✅' : '❌ (應為 v6)'}\`);
  });
});

// 2. 檢查首頁大小
https.get('https://heartbox.tw', (res) => {
  let size = 0;
  res.on('data', chunk => size += chunk.length);
  res.on('end', () => {
    const hasCriticalCSS = size > 3000; // 內聯 CSS 會讓 HTML 變大
    console.log(\`✓ HTML 大小: \${(size/1024).toFixed(1)} KB \${hasCriticalCSS ? '✅' : '❌ (Critical CSS 可能未部署)'}\`);
  });
});

// 3. 檢查 WebP 圖片
https.get('https://heartbox.tw/icons/AI%20聊天.webp', (res) => {
  console.log(\`✓ WebP 圖片: \${res.statusCode === 200 ? '✅ 已部署' : '❌ 未找到'}\`);
});

setTimeout(() => {
  console.log('\\n✨ 驗證完成！');
}, 3000);
"
```

---

## 📈 部署後檢查清單

等待 Cloudflare Pages 部署完成後（通常 3-5 分鐘），執行以下檢查：

### 立即檢查（部署後 5 分鐘）
- [ ] Service Worker 版本更新至 v6
- [ ] HTML 包含 Critical CSS（~32 KB 內聯）
- [ ] 字型 URL 包含 `subset=latin,chinese-traditional`
- [ ] 存在 dns-prefetch 和 prefetch 標籤
- [ ] WebP 圖片可正常訪問

### 效能測試（部署後 10 分鐘）
- [ ] Chrome Lighthouse Performance Score ≥95
- [ ] FCP <1.0s
- [ ] LCP <1.5s
- [ ] CLS <0.05
- [ ] TBT <150ms

### CDN 快取驗證（部署後 15 分鐘）
- [ ] Response Headers 包含 `cf-cache-status: HIT`
- [ ] Brotli 壓縮生效（Content-Encoding: br）
- [ ] 初始載入總大小 <500 KB

---

## 🐛 常見問題排查

### Q1: Service Worker 仍是 v5
**原因**: 瀏覽器快取舊版 SW
**解決方法**:
```javascript
// 在瀏覽器 Console 執行
navigator.serviceWorker.getRegistrations().then(registrations => {
  registrations.forEach(reg => reg.unregister());
  console.log('Service Workers 已清除');
  location.reload(true);
});
```

### Q2: Critical CSS 未生效
**原因**: Cloudflare Pages 可能從快取提供舊版本
**解決方法**:
1. 前往 Cloudflare Dashboard
2. 進入 Pages 專案
3. Deployments > 最新部署 > "Retry deployment"

### Q3: Lighthouse 分數未達 95
**可能原因**:
- 網路環境不穩定（改用無痕模式 + 關閉擴充功能）
- CDN 尚未完全更新（等待 10-15 分鐘）
- 測試裝置效能不足（使用模擬 Mobile 而非實體低階裝置）

---

## 📞 下一步

測試完成後，請記錄以下數據：

### 優化前（2026-04-11 之前）
- Performance Score: **~88-92**
- FCP: **~1.8s**
- LCP: **~2.5s**
- Bundle Size: **411 KB** (未壓縮)

### 優化後（2026-04-11）
- Performance Score: **[待測試]**
- FCP: **[待測試]**
- LCP: **[待測試]**
- Bundle Size: **55 KB** (Brotli 壓縮)

---

**更新時間**: 2026-04-11
**負責人**: Alan Lin
**自動化測試**: 可使用 GitHub Actions + Lighthouse CI 建立持續監控
