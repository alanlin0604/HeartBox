# HeartBox 文檔索引

## 📱 Android 開發

### 🚀 立即開始
- **[Android開發與優化清單](./Android開發與優化清單.md)** ⭐ 完整的 Android 建置與優化藍圖（30 個任務）
- **[行動裝置APP建置指南](./行動裝置APP建置指南.md)** - Capacitor APP 建置流程
- **[健康資訊連動快速指南](./健康資訊連動快速指南.md)** - HealthKit 與 Health Connect 整合

### 💰 成本
- Android: $25 USD（一次性，Google Play Console）
- iOS: $99 USD/年（Apple Developer Program，選填）

---

## 🏗️ 系統架構

### 核心文檔
- **[system-architecture.md](./system-architecture.md)** - 系統整體架構
- **[system-components.md](./system-components.md)** - 系統元件說明
- **[feature-modules.md](./feature-modules.md)** - 功能模組列表

### 設定指南
- **[setup-guide.md](./setup-guide.md)** - 專案設定指南
- **[MCP服務器配置指南](./MCP服務器配置指南.md)** - MCP (Model Context Protocol) 配置

---

## 🔧 開發工具

### 監控與除錯
- **[Sentry錯誤監控設定指南](./Sentry錯誤監控設定指南.md)** - Sentry 錯誤追蹤設定

### 安全性
- **[安全審查報告](./安全審查報告.md)** - 安全審查與建議

---

## 🎨 UI/UX

- **[UI-UX-進階優化報告](./UI-UX-進階優化報告.md)** - UI/UX 優化建議與最佳實踐

---

## 📚 API 文檔

存放於 `api/` 子目錄：

- **[好友系統API文件](./api/好友系統API文件.md)** - 好友系統完整 API 說明
- **[好友系統API速查表](./api/好友系統API速查表.md)** - 好友系統 API 快速參考

---

## 🗄️ 維護與備份

- **[版本備份與還原指南](./版本備份與還原指南.md)** - Git 版本控制與備份策略

---

## 📦 歸檔文件

已完成或暫時不需要的文件存放於 `archive/` 子目錄（15 個文件）：

### 已完成的專案報告
- 功能完成總結報告_2026-04-19.md
- 部署報告-2026-04-18.md
- 健康整合待辦清單.md（已被 Android開發與優化清單 取代）

### Agent 開發指南（專案已完成）
- AGENT_1_Backend_Developer.md
- AGENT_2_Frontend_Developer.md
- AGENT_3_Integration_Specialist.md
- AGENT使用指南.md

### 暫時不需要的文件
- 全面改進建議報告.md（已整合到新清單）
- 專案全面審查與改進建議.md
- Cloudflare_Pages_詳細導航指南.md
- 資料庫備份策略指南.md
- 付費方案與金流規劃.md
- subscription-plan.md
- feature-overview.md
- pwa-installation.md

---

## 🎯 快速導航

### 新手入門
1. 閱讀 [system-architecture.md](./system-architecture.md) 了解系統架構
2. 跟隨 [setup-guide.md](./setup-guide.md) 設定開發環境
3. 查看 [feature-modules.md](./feature-modules.md) 了解功能模組

### Android 開發
1. 查看 **[Android開發與優化清單](./Android開發與優化清單.md)** 📱
2. 按照步驟執行任務 1-12（建置與上架）
3. 預算：$25 USD（Google Play Console）

### 健康資料整合
1. 閱讀 [健康資訊連動快速指南](./健康資訊連動快速指南.md)
2. 安裝 `@capgo/capacitor-health` 插件
3. 配置 AndroidManifest.xml 權限

### 部署與監控
1. 前端：自動部署到 Cloudflare Pages（GitHub Actions）
2. 後端：手動部署到 Google Cloud Run（目前有問題待解決）
3. 錯誤監控：參考 [Sentry錯誤監控設定指南](./Sentry錯誤監控設定指南.md)

---

## 📊 文檔統計

| 類別 | 數量 |
|------|------|
| 核心文檔 | 12 個 |
| API 文檔 | 2 個 |
| 歸檔文件 | 15 個 |
| **總計** | **29 個** |

---

## 🔄 最後更新

- **日期：** 2026-05-02
- **版本：** 1.0
- **狀態：** 已整理並分類

---

## 💡 貢獻指南

如需新增文檔：
1. 核心文檔放在 `docs/` 根目錄
2. API 文檔放在 `docs/api/`
3. 已完成或不常用的文檔移至 `docs/archive/`
4. 更新本 README.md 索引
