# Lighthouse 測試報告

**測試日期**: 2026-04-12  
**測試網址**: https://heartbox.pages.dev/  
**Lighthouse 版本**: 13.1.0

---

## 📊 總體分數

| 類別 | 分數 | 狀態 | 目標 |
|------|------|------|------|
| **效能 (Performance)** | 60/100 | 🟡 需改進 | 90+ |
| **無障礙性 (Accessibility)** | 78/100 | 🟡 需改進 | 95+ |
| **最佳實踐 (Best Practices)** | 96/100 | 🟢 良好 | 90+ |
| **SEO** | 91/100 | 🟢 良好 | 90+ |

---

## ⚡ 核心 Web 指標 (Core Web Vitals)

| 指標 | 數值 | 狀態 | 目標 |
|------|------|------|------|
| **FCP** (First Contentful Paint) | 3.9s | 🔴 差 | < 1.8s |
| **LCP** (Largest Contentful Paint) | 5.5s | 🔴 差 | < 2.5s |
| **TBT** (Total Blocking Time) | 410ms | 🟡 中等 | < 200ms |
| **CLS** (Cumulative Layout Shift) | 0 | 🟢 優秀 | < 0.1 |
| **Speed Index** | 3.9s | 🟡 中等 | < 3.4s |

### 📈 與上次比較 (2026-04-11)

| 指標 | 之前 | 現在 | 變化 |
|------|------|------|------|
| Performance | 70 | 60 | ⬇️ -10 |
| FCP | 3.3s | 3.9s | ⬇️ +0.6s |
| LCP | 6.9s | 5.5s | ⬆️ -1.4s |
| TBT | 0ms | 410ms | ⬇️ +410ms |

**⚠️ 警告**: 頁面載入超時，部分結果可能不完整。

---

## 🚨 無障礙性問題 (優先修正)

### 1. ❌ 按鈕缺少可存取名稱
**問題**: 螢幕閱讀器會將按鈕唸成「button」，使用者無法理解功能  
**影響**: 🔴 高  
**修正方法**:
- 為所有按鈕添加 `aria-label` 屬性
- 確保按鈕內有可見文字或 icon + aria-label 組合
- 檢查所有 `<button>` 和 icon-only 按鈕

### 2. ❌ 文字與背景對比度不足
**問題**: 某些文字的對比度低於 4.5:1，視力較弱的使用者難以閱讀  
**影響**: 🔴 高  
**修正方法**:
- 檢查淺色模式中所有文字的對比度
- 特別注意灰色文字（次要文字）
- 使用對比度檢查工具驗證

### 3. ❌ 禁用縮放功能
**問題**: `<meta name="viewport">` 設定了 `user-scalable="no"` 或 `maximum-scale < 5`  
**影響**: 🟡 中  
**修正方法**:
- 移除 `user-scalable="no"`
- 設定 `maximum-scale=5` 或更高
- 允許使用者放大頁面

---

## ⚡ 效能問題

### 主要瓶頸
1. **FCP 過慢 (3.9s)**
   - 問題: 首次內容繪製時間過長
   - 目標: 需減少 2.1s (降至 1.8s)
   
2. **LCP 過慢 (5.5s)**
   - 問題: 最大內容繪製時間過長
   - 目標: 需減少 3.0s (降至 2.5s)
   - 改善: 相比之前已改善 1.4s ✅

3. **TBT 過高 (410ms)**
   - 問題: 總阻塞時間增加，JavaScript 執行時間過長
   - 目標: 需減少 210ms (降至 200ms)
   - 警告: 相比之前增加了 410ms ⚠️

### 可能的原因
- API 請求逾時 (dashboard 載入時 2 個 API 未完成)
- JavaScript bundle 執行時間過長
- 首屏資源載入順序需優化

---

## ✅ 做得好的部分

### 最佳實踐 (96/100)
- ✅ 使用 HTTPS
- ✅ 沒有主控台錯誤
- ✅ 正確的 DOCTYPE 和字元集
- ✅ 未濫用權限請求

### SEO (91/100)
- ✅ Meta description 存在
- ✅ HTTP 狀態碼正常
- ✅ 連結可爬取
- ✅ robots.txt 有效

### CLS (0)
- ✅ 完全沒有版面偏移
- ✅ 視覺穩定性極佳

---

## 🎯 立即行動項目

### 高優先級 (本日完成)
- [ ] **修正無障礙性問題**
  - [ ] 為所有按鈕添加 aria-label
  - [ ] 修正文字對比度問題
  - [ ] 允許頁面縮放

### 中優先級 (本週完成)
- [ ] **優化 FCP/LCP**
  - [ ] 分析首屏渲染路徑
  - [ ] 優化關鍵資源載入順序
  - [ ] 考慮 Critical CSS 內聯

- [ ] **降低 TBT**
  - [ ] 分析 JavaScript 執行時間
  - [ ] 檢查是否有阻塞主執行緒的操作
  - [ ] 考慮代碼分割優化

### 低優先級 (有空再做)
- [ ] 進一步優化 bundle 大小
- [ ] 添加資源預載入提示

---

## 📝 下一步建議

1. **立即修正無障礙性問題** - 這些是相對容易修正的，可以大幅提升 A11y 分數
2. **調查 TBT 增加原因** - 找出為何相比之前增加了 410ms
3. **優化首屏載入** - 專注於改善 FCP/LCP
4. **重新測試** - 修正後再次運行 Lighthouse

---

## 🔧 快速修正指令

```bash
# 查看詳細的 HTML 報告
npx lighthouse https://heartbox.pages.dev --view

# 只測試無障礙性
npx lighthouse https://heartbox.pages.dev --only-categories=accessibility --view

# 只測試效能
npx lighthouse https://heartbox.pages.dev --only-categories=performance --view
```

---

**報告生成時間**: 2026-04-12  
**下次測試**: 修正後
