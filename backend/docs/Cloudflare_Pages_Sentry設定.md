# Cloudflare Pages 前端 Sentry 設定

## 快速設定步驟

### 方法一：Cloudflare Dashboard（推薦）

1. **登入 Cloudflare Dashboard**
   - 前往 https://dash.cloudflare.com
   - 登入你的帳號

2. **選擇 HeartBox 專案**
   - 左側選單 → Pages
   - 點擊 HeartBox 專案

3. **設定環境變數**
   - 點擊 "Settings" 標籤
   - 找到 "Environment variables" 區塊
   - 點擊 "Add variable" 或 "Edit variables"

4. **加入 VITE_SENTRY_DSN**
   ```
   Variable name:  VITE_SENTRY_DSN
   Value:          https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
   Environment:    Production (只勾選 Production)
   ```

5. **儲存**
   - 點擊 "Save" 按鈕

6. **重新部署**
   - 回到 "Deployments" 標籤
   - 找到最新的部署
   - 點擊 "···" → "Retry deployment"
   - 或直接推送新的 commit 到 main 分支觸發自動部署

### 方法二：使用 Wrangler CLI

如果你有安裝 Wrangler CLI：

```bash
# 安裝 Wrangler（如果還沒安裝）
npm install -g wrangler

# 登入 Cloudflare
wrangler login

# 設定環境變數
wrangler pages secret put VITE_SENTRY_DSN

# 輸入值：
# https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
```

---

## 驗證設定

### 1. 檢查環境變數是否已設定

部署完成後，檢查 build logs：
- Cloudflare Pages → Deployments → 點擊最新部署
- 查看 "Build logs"
- 應該不會看到任何 VITE_SENTRY_DSN 相關的錯誤

### 2. 測試前端 Sentry

1. **前往生產環境網站**
   - https://your-heartbox-app.pages.dev

2. **打開瀏覽器開發者工具** (F12)

3. **在 Console 執行**
   ```javascript
   throw new Error("測試前端 Sentry 整合")
   ```

4. **檢查 Sentry Dashboard**
   - 前往 https://sentry.io
   - 選擇 `heartbox-frontend` 專案
   - 應該會看到錯誤出現！

---

## 注意事項

### ⚠️ 重要

1. **只在 Production 環境設定**
   - 不要在 Preview 環境設定（否則開發時的錯誤也會被發送）
   - Cloudflare Pages 的 Preview 部署不應該發送錯誤到 Sentry

2. **環境變數名稱必須是 `VITE_SENTRY_DSN`**
   - Vite 只會暴露 `VITE_` 開頭的環境變數
   - 不是 `SENTRY_DSN`，而是 `VITE_SENTRY_DSN`

3. **重新部署才會生效**
   - 設定環境變數後必須重新部署
   - 現有的部署不會自動更新

### ✅ 確認設定成功

檢查清單：
- [ ] 已在 Cloudflare Pages 設定 `VITE_SENTRY_DSN` 環境變數
- [ ] 環境設定為 "Production"（不包含 Preview）
- [ ] 已重新部署應用程式
- [ ] 在生產環境測試錯誤捕獲（throw new Error）
- [ ] 在 Sentry Dashboard 看到測試錯誤

---

## 疑難排解

### 問題：Sentry 沒有收到前端錯誤

**檢查：**

1. **確認環境變數名稱正確**
   ```
   ✅ VITE_SENTRY_DSN
   ❌ SENTRY_DSN
   ```

2. **確認只在 Production 環境**
   - Preview 部署不應該啟用 Sentry

3. **確認已重新部署**
   - 設定後需要觸發新的部署

4. **檢查瀏覽器 Console**
   - 是否有 Sentry 相關的錯誤訊息
   - F12 → Console

5. **檢查 Network 請求**
   - F12 → Network
   - 搜尋 "sentry.io"
   - 應該會看到發送到 Sentry 的請求

### 問題：本地開發想測試 Sentry

創建 `frontend/.env.production.local`：
```bash
VITE_SENTRY_DSN=https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
```

然後執行：
```bash
npm run build
npm run preview
```

**注意：** 測試完請刪除 `.env.production.local`，避免開發時發送錯誤！

---

## 完成！

設定完成後，前端錯誤將自動發送到 Sentry：
- ✅ 未處理的 JavaScript 錯誤
- ✅ React 元件錯誤
- ✅ API 請求失敗（自動捕獲）
- ✅ 用戶操作重播（錯誤發生時）

Sentry Dashboard: https://sentry.io/organizations/heartbox-awmq/issues/
