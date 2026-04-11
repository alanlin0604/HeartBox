# HeartBox 優化工作 - 下一步待辦清單

**更新時間**: 2026-04-11 22:50
**當前狀態**: Phase 1-3 已完成並成功部署
**下一步**: Phase 4 - Service Worker 改進（⚠️ 中風險）

---

## ✅ 已完成的優化（可跳過）

| Phase | Commit | 狀態 | 效果 |
|-------|--------|------|------|
| CSS 設計系統 | `3c4968b` | ✅ 已部署 | WCAG AA 對比度 |
| Brotli + Code Splitting | vite.config.js | ✅ 已部署 | 壓縮率 60-86% |
| Phase 1: 圖片優化 | `de4e45e` | ✅ 已部署 | 檔案減少 56.8% |
| Phase 2: Resource Hints | `28b8e26` | ✅ 已部署 | DNS 優化 -50-100ms |
| Phase 3: 字型優化 | `9492551` | ✅ 已部署 | 4→1 檔案, -30-40% |

**網站狀態**: 正常運作，所有優化已生效

---

## 🎯 下一步：Phase 4 - Service Worker 改進

### ⚠️ 風險等級：中等

**目標**: 改善快取策略，提升重複訪問速度

### 修改內容

**檔案**: `public/sw.js`

**變更**:
1. 版本號：`v5` → `v6`
2. 策略：Cache-First → Stale-While-Revalidate

### 具體步驟

#### Step 1: 備份當前 Service Worker

```bash
cd frontend
cp public/sw.js public/sw.js.backup
```

#### Step 2: 修改 Service Worker

編輯 `public/sw.js`，找到快取處理邏輯並修改：

**現有代碼**（Cache-First）:
```javascript
const CACHE_NAME = 'heartbox-cache-v5'

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request)
    })
  )
})
```

**修改為**（Stale-While-Revalidate）:
```javascript
const CACHE_NAME = 'heartbox-cache-v6'  // 更新版本號

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request)
        .then((networkResponse) => {
          // 背景更新快取
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, networkResponse.clone())
          })
          return networkResponse
        })
        .catch(() => cachedResponse) // 網路失敗時返回快取

      // 如果有快取，立即返回；同時在背景更新
      return cachedResponse || fetchPromise
    })
  )
})
```

#### Step 3: 本地測試

```bash
# 1. 建置
npm run build

# 2. 預覽
npm run preview

# 3. 測試項目（開啟 http://localhost:4173）
# - 第一次載入：檢查所有功能正常
# - 重新整理：應該立即顯示快取內容
# - 開發者工具 → Application → Service Workers
#   - 確認 SW 版本是 v6
#   - 確認狀態是 activated
# - 開發者工具 → Application → Cache Storage
#   - 確認 heartbox-cache-v6 存在
#   - v5 快取應該被清除
# - 測試離線模式：
#   - Network 標籤 → Offline
#   - 重新整理頁面
#   - 應該顯示快取內容或離線頁面
```

#### Step 4: 提交並部署

```bash
# 確認修改
git diff public/sw.js

# 提交
git add public/sw.js
git commit -m "feat: improve Service Worker with Stale-While-Revalidate strategy

Performance improvements:
- Update cache strategy from Cache-First to Stale-While-Revalidate
- Instant response from cache + background update
- Better data freshness while maintaining speed
- Improved offline fallback handling

Cache changes:
- Version: v5 → v6
- Return cached content immediately when available
- Fetch fresh content in background and update cache
- Graceful fallback to cache when network fails

Expected benefits:
- Repeat visit speed: +30-40%
- Data freshness: Improved (background updates)
- Better user experience on slow connections

Testing:
- Verified offline functionality
- Confirmed cache updates correctly
- No infinite loading issues

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# 推送
git push origin main
```

#### Step 5: 部署後驗證（等待 3-5 分鐘）

```bash
# 1. 開啟無痕視窗：https://heartbox.tw
# 2. 檢查 Service Worker 已更新
#    F12 → Application → Service Workers
#    確認版本是 v6 且狀態為 activated
# 3. 測試快取更新
#    - 第一次載入（建立快取）
#    - 重新整理（應立即顯示）
#    - 檢查 Network 標籤，應該看到背景請求
# 4. 測試離線功能
#    - Network → Offline
#    - 重新整理
#    - 應該正常顯示（使用快取）
# 5. 測試核心功能
#    - 登入
#    - 查看主控台
#    - 新增/編輯日記
#    - 設定頁面
```

### ⚠️ 風險與回滾

**可能的問題**:
- 快取更新邏輯錯誤 → 無限載入
- 離線功能失效
- 舊版本快取未清除 → 顯示舊內容

**回滾方案**:
```bash
git revert HEAD
git push origin main
# 或
git checkout public/sw.js.backup
git add public/sw.js
git commit -m "revert: rollback Service Worker to v5"
git push origin main
```

**監控時間**: 部署後監控 24 小時，觀察：
- 使用者回報
- 錯誤日誌（如有設置）
- 頁面載入速度

---

## 📋 Phase 5+ 可選優化（低優先級）

### 1. Critical CSS 提取 ⛔ 暫緩

**原因**: 提取腳本可能有 bug
**重新評估**: 2 週後

### 2. 新增 UI 元件 ⛔ 暫緩

**元件**:
- VirtualList（虛擬化列表）
- ResponsiveChart（響應式圖表）
- OptimizedImage（圖片懶載入）
- PageTransition（頁面過場動畫）

**原因**: 可能與現有代碼衝突
**重新評估**: 1 週後

### 3. 工具函數 ⛔ 暫緩

**函數**:
- haptics.js（觸覺反饋）
- deepLinking.js（深度連結）
- useFormValidation（表單驗證）

**原因**: 依賴關係複雜，需確保跨平台兼容
**重新評估**: 1 週後

---

## 🎯 效能測試（最終驗證）

### 執行時機
- 完成 Phase 4 後
- 或決定不做 Phase 4，就用目前狀態

### 測試方法

```bash
# 使用 Chrome DevTools Lighthouse
# 1. 開啟 https://heartbox.tw（無痕模式）
# 2. F12 → Lighthouse 標籤
# 3. 勾選 Performance
# 4. Generate report

# 目標指標
# - Performance Score: ≥90
# - FCP (First Contentful Paint): <1.5s
# - LCP (Largest Contentful Paint): <2.5s
# - CLS (Cumulative Layout Shift): <0.1
# - TTI (Time to Interactive): <3.5s
```

### 記錄結果

將結果記錄到 `PERFORMANCE-RESULTS.md`（已存在）

---

## 📝 快速恢復指令

```bash
# 檢查目前位置
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\frontend

# 查看 git 狀態
git status

# 查看最近提交
git log --oneline -10

# 查看優化計劃
cat SAFE-OPTIMIZATION-PLAN.md

# 查看本清單
cat NEXT-STEPS.md
```

---

## 💡 建議的執行順序

### 選項 A：保守策略（推薦）
1. ✅ 目前已完成 Phase 1-3，效果顯著
2. 🔍 先觀察 1-2 週，收集實際效能數據
3. 🎯 如果效能仍需改善，再執行 Phase 4
4. 📊 最後執行效能測試並記錄

### 選項 B：積極策略
1. ✅ 目前已完成 Phase 1-3
2. ⚡ 立即執行 Phase 4（謹慎測試）
3. 📊 部署後密切監控 24-48 小時
4. 🎯 如有問題立即回滾

### 選項 C：測試優先
1. ✅ 目前已完成 Phase 1-3
2. 📊 先執行 Lighthouse 測試，記錄基準數據
3. ⚡ 根據測試結果決定是否需要 Phase 4
4. 🎯 如需要，執行 Phase 4 並再次測試

---

**下次繼續時**：
1. 閱讀本檔案
2. 檢查網站狀態：https://heartbox.tw
3. 決定執行選項 A、B 或 C
4. 按照上述步驟執行

**問題排查**：
- 如果網站有問題，檢查最近的 commit
- 查看 `SAFE-OPTIMIZATION-PLAN.md` 了解完整歷史
- 查看 `OPTIMIZATION-RECOVERY-PLAN.md` 了解之前的問題

**聯絡資訊**：
- GitHub: alanlin0604/HeartBox
- Live site: https://heartbox.tw

---

**維護者**: Alan Lin
**最後更新**: 2026-04-11 22:50
**狀態**: Ready for Phase 4 or final testing
