# HeartBox 待辦事項清單

**最後更新**: 2026-04-11  
**當前版本**: UI/UX v2.0  
**狀態**: 🟢 生產環境運行中

---

## ✅ 已完成項目 (最近)

### UI/UX 現代化 v2.0 (2026-04-11)
- [x] 建立完整設計系統 (design-tokens.css)
- [x] 創建現代 UI 組件庫 (Button, Card, Input, Modal)
- [x] 重新設計首頁/登入頁
- [x] 優化 Dashboard 頁面
- [x] 安裝 framer-motion
- [x] 效能優化維持 (Recharts/Tiptap 懶載入)
- [x] **修正淺色模式配色** - 使用純白色系
- [x] **降低淺色模式透明度** - 提高文字可讀性

### 效能優化 (2026-04-11)
- [x] Recharts 懶載入 (-406 KB)
- [x] Tiptap 懶載入 (-368 KB)
- [x] Service Worker Stale-While-Revalidate
- [x] WebP 圖片格式
- [x] Inter Variable Font + Latin subset
- [x] Bundle 大小減少 37%

---

## 🔥 高優先級 (立即執行)

### 1. UI/UX 持續改進
- [ ] **測試淺色模式** - 確認文字在所有情況下都清晰
- [ ] **深色模式微調** - 確保深色模式也有良好的對比度
- [ ] **響應式測試** - 手機、平板、桌面各螢幕尺寸
- [ ] **跨瀏覽器測試** - Chrome, Firefox, Safari, Edge

### 2. 無障礙性檢查
- [ ] 運行 Lighthouse 無障礙性審查 (目標 >95 分)
- [ ] 鍵盤導航測試 (Tab, Enter, Esc)
- [ ] 螢幕閱讀器測試 (NVDA/JAWS)
- [ ] 顏色對比度驗證 (所有文字 ≥4.5:1)

### 3. 效能監控
- [ ] Lighthouse 效能測試 (目標維持 70+)
- [ ] Core Web Vitals 監控
- [ ] Bundle 分析 (檢查是否有多餘依賴)

---

## 🎯 中優先級 (本週完成)

### 4. UI 組件完善
- [ ] **整合 framer-motion** - 添加微互動動畫
  - 按鈕點擊動畫
  - 卡片進場動畫
  - 頁面切換過渡
- [ ] **創建更多 UI 組件**
  - Badge (徽章)
  - Tooltip (提示框)
  - Dropdown (下拉選單)
  - Tabs (標籤頁)
  - Alert (警告框)
- [ ] **組件文檔** - 為 UI 組件庫建立使用說明

### 5. 頁面現代化 (剩餘頁面)
- [ ] 註冊頁 (RegisterPage.jsx)
- [ ] 設定頁 (SettingsPage.jsx)
- [ ] 日記詳情頁 (NoteDetailPage.jsx) - 使用新 Card
- [ ] 其他輔助頁面 (PrivacyPage, TermsPage 等)

### 6. 動畫與互動
- [ ] 實作頁面切換動畫
- [ ] 添加載入動畫 (skeleton screens)
- [ ] 優化按鈕 hover/active 狀態
- [ ] 添加成功/錯誤反饋動畫

---

## 📋 低優先級 (有空再做)

### 7. 效能進一步優化
- [ ] **Critical CSS 提取** - 內聯首屏 CSS (-300-500ms FCP)
- [ ] **圖片懶載入** - 非關鍵圖片 lazy loading
- [ ] **字型預載入** - 減少字型載入閃爍
- [ ] **Tree Shaking** - 進一步移除未使用代碼 (-1.7s)
- [ ] **Code Splitting** - 更細粒度的代碼分割

### 8. 設計系統文檔
- [ ] 建立 Storybook 展示組件
- [ ] 撰寫設計指南文檔
- [ ] 創建顏色/字型使用規範
- [ ] 製作 UI 組件使用範例

### 9. 其他改善
- [ ] 添加骨架屏 (Skeleton) 載入狀態
- [ ] 實作無限滾動 (如適用)
- [ ] 添加鍵盤快捷鍵
- [ ] 實作離線模式改善

---

## 🐛 已知問題

### 需要修正
- [ ] Node.js 20 deprecation 警告 (GitHub Actions)
  - 更新 actions/checkout 到支援 Node 24 的版本
  - 更新 actions/setup-node
  - 更新 cloudflare/wrangler-action

### 需要驗證
- [ ] Service Worker 快取策略是否最佳
- [ ] 懶載入組件的 fallback 是否足夠好
- [ ] 淺色/深色模式切換是否流暢

---

## 💡 未來功能想法

### UI/UX 增強
- [ ] 實作主題自訂功能 (讓用戶選擇主色調)
- [ ] 添加更多動畫選項
- [ ] 實作圖示系統 (統一使用 Lucide/Heroicons)
- [ ] 添加更多顏色主題 (藍色、綠色等)

### 技術債務
- [ ] 遷移到 TypeScript (可選)
- [ ] 實作 E2E 測試 (Playwright/Cypress)
- [ ] 設定 Prettier + ESLint 規則
- [ ] 代碼審查與重構

---

## 📊 效能目標

### 當前狀態 (2026-04-11)
- Performance: 70/100
- FCP: 3.3s
- LCP: 6.9s
- TBT: 0ms ✅
- CLS: 0 ✅
- Bundle: 919 KB

### 目標
- Performance: **90+/100**
- FCP: **< 1.8s** (目前 +1.5s)
- LCP: **< 2.5s** (目前 +4.4s)
- TBT: **< 200ms** (已達標 ✅)
- CLS: **< 0.1** (已達標 ✅)
- Bundle: **< 800 KB**

---

## 🚀 快速指令參考

### 開發
```bash
cd frontend
npm run dev          # 啟動開發伺服器
npm run build        # 建置生產版本
npm run preview      # 預覽建置結果
```

### 測試
```bash
npx lighthouse https://heartbox.pages.dev --view
npx lighthouse https://heartbox.pages.dev --only-categories=accessibility
```

### 部署
```bash
git add .
git commit -m "feat: 描述"
git push origin main  # 自動觸發 Cloudflare Pages 部署
```

### 檢查部署
```bash
gh run list --repo alanlin0604/HeartBox --limit 5
gh run view [RUN_ID] --repo alanlin0604/HeartBox
```

---

## 📝 下次對話可用的指令

### 繼續開發
- "繼續實作剩餘的 UI 組件"
- "整合 framer-motion 添加動畫"
- "測試並修正無障礙性問題"
- "優化剩餘頁面的設計"

### 效能優化
- "實作 Critical CSS 提取"
- "添加圖片懶載入"
- "進行 Bundle 分析並優化"
- "運行 Lighthouse 測試並改善"

### 測試與部署
- "測試淺色/深色模式"
- "檢查部署狀態"
- "修正已知問題"
- "部署到生產環境"

---

## 🎯 本週重點 (建議)

**Week 1 (當前週)**:
1. ✅ 完成 UI/UX v2.0 基礎 (已完成)
2. ⏳ 測試並修正淺色模式問題
3. ⏳ 響應式與跨瀏覽器測試
4. ⏳ 無障礙性審查

**Week 2**:
1. 整合 framer-motion 動畫
2. 完善剩餘 UI 組件
3. 現代化剩餘頁面

**Week 3**:
1. 效能進一步優化
2. 建立組件文檔
3. 使用者測試與反饋

---

## 📞 相關文件

- **設計系統**: `frontend/src/styles/design-tokens.css`
- **UI 組件**: `frontend/src/components/ui/`
- **實施總結**: `frontend/UI-UX-MODERNIZATION-SUMMARY.md`
- **部署指南**: `DEPLOYMENT-GUIDE-UI-UX-V2.md`
- **效能報告**: `frontend/PERFORMANCE-REPORT.md`

---

**最後提醒**: 
- 每次修改後記得運行 `npm run build` 測試
- 重要更新前先在本地測試
- 部署前檢查 git status 確認要提交的檔案
- 善用 GitHub Actions 查看建置日誌

**準備好了！下次直接告訴我要做什麼，我會參考這份清單繼續工作。** 🚀
