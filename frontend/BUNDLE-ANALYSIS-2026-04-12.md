# Bundle 分析報告

**日期**: 2026-04-12  
**總大小**: 1,465 KB (未壓縮) / 418 KB (gzip)

---

## 📊 Bundle 組成分析

### 🔴 大型文件（>100 KB）

| 檔案 | 大小 | Gzip | 類型 | 優先級 |
|------|------|------|------|--------|
| **index-B2QqsPMC.js** | 417.30 KB | 125.96 KB | 主 bundle | 🔴 高 |
| **vendor-recharts-gvNCcIQj.js** | 406.88 KB | 114.17 KB | 圖表庫 | ✅ 已懶載入 |
| **vendor-tiptap-C-bQTWcq.js** | 368.85 KB | 114.75 KB | 編輯器 | ✅ 已懶載入 |

### 🟡 中型文件（20-100 KB）

| 檔案 | 大小 | Gzip | 類型 |
|------|------|------|------|
| **vendor-react-BBQyXNc4.js** | 48.17 KB | 16.70 KB | React 核心 |
| **JournalPage-C6cmLFYJ.js** | 37.42 KB | 10.47 KB | 日記頁面 |
| **vendor-axios-C0Zqfgkc.js** | 36.62 KB | 14.38 KB | HTTP 客戶端 |
| **CounselorListPage-BlVGNjK_.js** | 34.65 KB | 7.46 KB | 諮商師列表 |
| **SettingsPage-B_ExS5Wz.js** | 25.59 KB | 6.82 KB | 設定頁面 |
| **vendor-dompurify-HRjpPm7y.js** | 22.44 KB | 8.42 KB | HTML 淨化 |
| **DashboardPage-BMOZ_dc3.js** | 21.95 KB | 5.46 KB | 儀表板 |

### ✅ 小型文件（< 20 KB）

- 其餘 20+ 個頁面和組件，每個 < 20 KB

---

## 🎯 關鍵發現

### 1. 主 Bundle 過大 (417 KB)

**問題**: 主 bundle 包含了太多初始載入不需要的代碼

**可能原因**:
- 所有路由和頁面組件可能被包含在主 bundle
- Context providers 和 utilities 可能沒有被正確分割
- 可能包含未使用的庫代碼

**優化潛力**: 🔴 高（可減少 50-60%）

---

### 2. 已優化的部分 ✅

**做得好**:
- ✅ Recharts 已懶載入（406 KB）
- ✅ Tiptap 已懶載入（368 KB）
- ✅ 頁面級別的 code splitting（大部分頁面獨立）
- ✅ Vendor chunks 分離良好

---

### 3. 需要進一步優化

#### 3.1 大型頁面組件

| 頁面 | 大小 | 建議 |
|------|------|------|
| JournalPage | 37.42 KB | 分割表單和編輯器組件 |
| CounselorListPage | 34.65 KB | 懶載入諮商師卡片 |
| SettingsPage | 25.59 KB | 分割設定區塊 |

#### 3.2 Vendor 依賴

**Axios (36.62 KB)**:
- 考慮使用更輕量的替代方案（如 ky: ~11 KB）
- 或使用原生 fetch + 封裝層

**DOMPurify (22.44 KB)**:
- 只在需要時載入（Tiptap 編輯器頁面）
- 考慮移到 vendor-tiptap chunk

---

## 🚀 優化建議（按優先級）

### 高優先級

#### 1. 分析主 Bundle 內容
```bash
# 檢查 stats.html 找出主 bundle 中的大型依賴
# 重點關注：
- 未使用的導入
- 可以懶載入的組件
- 重複的依賴
```

#### 2. Route-based Code Splitting
確保所有路由都是懶載入：
```jsx
// ✅ 好 - 懶載入
const JournalPage = lazy(() => import('./pages/JournalPage'))

// ❌ 差 - 靜態導入
import JournalPage from './pages/JournalPage'
```

#### 3. 移除未使用的依賴
```bash
# 使用 depcheck 找出未使用的依賴
npx depcheck
```

#### 4. Tree Shaking 優化
- 確保所有 import 使用 named imports
- 檢查是否有 side effects 阻止 tree shaking

---

### 中優先級

#### 5. 組件級別的懶載入
大型組件應該懶載入：
```jsx
// 模態框、圖表、編輯器等
const Modal = lazy(() => import('./components/Modal'))
```

#### 6. 條件載入第三方庫
```jsx
// 只在需要時載入 DOMPurify
const loadDOMPurify = () => import('dompurify')
```

#### 7. 優化 manualChunks 策略
```js
manualChunks: {
  'vendor-react': ['react', 'react-dom', 'react-router-dom'],
  'vendor-ui': ['framer-motion'], // 分離 UI 庫
  'vendor-utils': ['dompurify', 'axios'], // 工具庫
}
```

---

### 低優先級

#### 8. 考慮替換大型依賴

| 當前依賴 | 大小 | 替代方案 | 新大小 | 節省 |
|---------|------|---------|--------|------|
| axios | 36 KB | ky | 11 KB | -25 KB |
| axios | 36 KB | fetch wrapper | 2 KB | -34 KB |

#### 9. 移除 console.log 和調試代碼
```js
// vite.config.js
build: {
  minify: 'terser',
  terserOptions: {
    compress: {
      drop_console: true,
      drop_debugger: true,
    },
  },
}
```

---

## 📈 預期效果

| 優化項目 | 當前大小 | 目標大小 | 節省 |
|---------|---------|---------|------|
| **主 Bundle** | 417 KB | 250 KB | -167 KB (-40%) |
| **首次載入** | 502 KB | 330 KB | -172 KB (-34%) |
| **Gzip 總計** | 157 KB | 105 KB | -52 KB (-33%) |

**FCP 改善預估**: -0.8 ~ -1.2s  
**LCP 改善預估**: -1.0 ~ -1.5s

---

## 🔍 詳細分析文件

完整的視覺化分析報告：`dist/stats.html`

查看方式：
```bash
# 開啟視覺化報告
start dist/stats.html  # Windows
open dist/stats.html   # Mac
xdg-open dist/stats.html  # Linux
```

---

## 📋 下一步行動

1. [ ] 開啟 stats.html 詳細檢視主 bundle 組成
2. [ ] 實作 route-based code splitting
3. [ ] 執行 depcheck 移除未使用的依賴
4. [ ] 優化大型頁面組件（JournalPage, CounselorListPage）
5. [ ] 考慮替換 axios 為更輕量的方案
6. [ ] 實作組件級別懶載入
7. [ ] 重新建置並驗證效果

---

**生成時間**: 2026-04-12  
**工具**: rollup-plugin-visualizer + Vite 7.3.1
