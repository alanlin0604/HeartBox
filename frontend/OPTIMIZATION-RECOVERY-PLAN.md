# HeartBox 優化恢復計劃

**日期**: 2026-04-11
**狀態**: 網站已回滾並恢復正常

---

## 📋 問題記錄

### 事件時間軸

| 時間 | 事件 | 狀態 |
|------|------|------|
| 20:04 | 推送優化提交 `3ffc86f` | ✅ |
| 20:30 | Cloudflare Pages 部署完成 | ✅ |
| 21:00 | 發現網站空白頁問題 | ❌ |
| 22:04 | 緊急回滾提交 `23f5dd4` | ✅ |
| 22:12 | 網站恢復正常 | ✅ |

### 優化提交包含的變更

1. **核心檔案修改**（可能是問題根源）
   - `src/index.css`: 468 行變更 ⚠️ **高風險**
   - `index.html`: Resource Hints、字型子集化
   - `public/sw.js`: Service Worker v6
   - `vite.config.js`: Brotli、外部依賴

2. **新增元件**
   - `src/components/VirtualList.jsx` (220 行)
   - `src/components/ResponsiveChart.jsx` (180 行)
   - `src/components/OptimizedImage.jsx`
   - `src/components/PageTransition.jsx`
   - `src/utils/haptics.js` (173 行)
   - `src/utils/deepLinking.js` (234 行)
   - `src/hooks/useFormValidation.js` (148 行)

3. **文件與腳本**
   - `scripts/optimize-images.js`
   - `scripts/extract-critical-css.js`
   - `docs/PERFORMANCE-OPTIMIZATION.md` (316 行)
   - `docs/DEEP-LINKING-MARKETING.md` (366 行)
   - `docs/UI-UX-IMPROVEMENTS.md` (1283 行)

4. **圖片優化**
   - 11 張 PNG → WebP

---

## 🔬 問題診斷策略

### Phase 1: 隔離測試（本地）

**目標**: 找出導致空白頁的具體檔案/修改

#### 測試 1: index.css 修改
```bash
# 恢復 index.css 到優化版本
git show 3ffc86f:frontend/src/index.css > src/index.css
npm run dev
# 檢查本地是否正常
```

**預期結果**: 如果本地也空白 → index.css 是問題根源

#### 測試 2: 新增元件
```bash
# 逐一恢復新增的元件
git show 3ffc86f:frontend/src/components/VirtualList.jsx > src/components/VirtualList.jsx
# ... 測試每個元件
```

#### 測試 3: Vite 配置
```bash
# 恢復 vite.config.js
git show 3ffc86f:frontend/vite.config.js > vite.config.js
npm run build
# 檢查建置產物
```

---

### Phase 2: 安全優化重新應用

**原則**: 逐步、可驗證、可回滾

#### 優先級 1: 無風險優化（立即可用）

1. **Brotli 壓縮**
   ```javascript
   // vite.config.js
   plugins: [
     compression({ algorithm: 'gzip' }),
     compression({ algorithm: 'brotliCompress', ext: '.br' }),
   ]
   ```
   - ✅ 不影響功能
   - ✅ 建置時優化
   - ✅ 壓縮率 60-86%

2. **Code Splitting**
   ```javascript
   // vite.config.js
   manualChunks: {
     'vendor-react': ['react', 'react-dom', 'react-router-dom'],
     'vendor-recharts': ['recharts'],
     // ...
   }
   ```
   - ✅ Vite 原生支援
   - ✅ 不修改業務邏輯
   - ✅ 初始載入 -56%

3. **圖片 WebP 轉換**
   ```bash
   npm run optimize:images
   ```
   - ✅ 純資源優化
   - ✅ PNG 保留作為 fallback
   - ✅ 圖片體積 -55%

#### 優先級 2: 低風險優化（需測試）

4. **Resource Hints**
   ```html
   <link rel="dns-prefetch" href="https://fonts.googleapis.com" />
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
   <link rel="prefetch" href="/dashboard" as="document" />
   ```
   - ⚠️ 需要測試
   - ⚠️ 修改 index.html
   - ✅ 網路優化 -100ms

5. **字型子集化**
   ```html
   <link href="...Inter:wght@400;500;600;700&subset=latin,chinese-traditional" />
   ```
   - ⚠️ 需要驗證字型載入
   - ✅ 字型檔案 -40%

#### 優先級 3: 中風險優化（謹慎測試）

6. **Service Worker Stale-While-Revalidate**
   ```javascript
   // 修改 public/sw.js
   const fetchPromise = fetch(request)
     .then(response => {
       caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()))
       return response
     })
   return cached || fetchPromise
   ```
   - ⚠️ 影響快取策略
   - ⚠️ 需要完整測試
   - ✅ 重複訪問 +40%

7. **Critical CSS 內聯**
   ```bash
   npm run build:optimized
   ```
   - ⚠️⚠️ **高風險**（需要充分測試）
   - ⚠️ 修改建置產物
   - ✅ FCP -20%

#### 優先級 4: 暫緩優化（需要重構）

8. **index.css 大規模修改** ⛔
   - ❌ 暫不應用
   - ❌ 需要找出具體問題行
   - ❌ 需要逐行比對測試

9. **新增元件（VirtualList, ResponsiveChart）** ⛔
   - ❌ 暫不應用
   - ❌ 需要單獨測試每個元件
   - ❌ 需要確認依賴關係

---

## 📝 重新應用優化 SOP

### Step 1: 本地測試
```bash
# 1. 應用單一優化
git cherry-pick <specific-commit> --no-commit

# 2. 本地測試
npm run dev
# 手動測試：導航、日記、圖表、設定等

# 3. 建置測試
npm run build
npm run preview
# 確認建置產物正常

# 4. 提交
git commit -m "feat: apply safe optimization - [name]"
```

### Step 2: 漸進式部署
```bash
# 1. 推送到 GitHub
git push origin main

# 2. 等待 Cloudflare Pages 部署（3-5 分鐘）

# 3. 驗證線上版本
# - 無痕模式測試
# - 檢查 Console 無錯誤
# - 測試核心功能

# 4. 監控 24 小時
# - Google Analytics 跳出率
# - 錯誤追蹤（Sentry）
```

### Step 3: 效能驗證
```bash
# 每次優化後執行
npx lighthouse https://heartbox.tw --only-categories=performance
```

**目標指標**:
- Performance Score: ≥90
- FCP: <1.5s
- LCP: <2.5s
- 無 JavaScript 錯誤

---

## 🎯 建議的重新應用順序

### Week 1: 無風險優化
- [x] 回滾到安全版本
- [ ] Day 1: Brotli 壓縮 + Code Splitting
- [ ] Day 2: 圖片 WebP 轉換
- [ ] Day 3: 驗證效能提升

### Week 2: 低風險優化
- [ ] Day 4: Resource Hints (dns-prefetch, preconnect)
- [ ] Day 5: 字型子集化
- [ ] Day 6: Prefetch 可能的下一頁

### Week 3: 謹慎優化
- [ ] Day 7: Service Worker v6（Stale-While-Revalidate）
- [ ] Day 8: 監控並驗證快取策略
- [ ] Day 9: 效能測試與調整

### Week 4: 進階優化（待診斷）
- [ ] 找出 index.css 問題行
- [ ] 單獨測試 VirtualList 元件
- [ ] 單獨測試 ResponsiveChart 元件
- [ ] 評估 Critical CSS 可行性

---

## 🔒 防範措施

### 1. 建立測試環境
```bash
# 使用 Cloudflare Pages Preview Deployments
git checkout -b optimization/safe-bundle
# 推送後會產生預覽 URL
```

### 2. 自動化測試
```yaml
# .github/workflows/test.yml
- name: Lighthouse CI
  run: |
    npm install -g @lhci/cli
    lhci autorun
```

### 3. 回滾流程
```bash
# 緊急回滾（5 分鐘內）
git revert HEAD --no-commit
git commit -m "revert: rollback optimization due to [issue]"
git push origin main
```

---

## 📊 成功指標

### 技術指標
- [ ] Lighthouse Performance Score ≥90
- [ ] FCP <1.5s
- [ ] LCP <2.5s
- [ ] CLS <0.1
- [ ] 無 JavaScript 錯誤

### 業務指標
- [ ] 跳出率未增加
- [ ] 頁面載入時間改善
- [ ] 使用者回報無異常

---

**負責人**: Alan Lin
**更新時間**: 2026-04-11 22:15
**下次檢討**: 2026-04-18
