# 🚀 Cloudflare Pages Sentry 快速設定

## 方法一：使用 Wrangler CLI（推薦，最簡單）

### 步驟 1：登入 Cloudflare

在終端機執行：
```bash
wrangler login
```

- 這會打開瀏覽器
- 點擊 "Allow" 授權 Wrangler 訪問你的 Cloudflare 帳號
- 看到 "You have granted authorization to Wrangler!" 後關閉瀏覽器
- 回到終端機，應該顯示 "Successfully logged in"

### 步驟 2：設定環境變數

執行以下命令：
```bash
wrangler pages secret put VITE_SENTRY_DSN --project-name=heartbox
```

**當提示 "Enter a secret value:" 時，貼上：**
```
https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
```

按 Enter 確認。

**注意：** 如果提示專案名稱不對，請先查詢你的專案名稱：
```bash
wrangler pages project list
```

然後使用正確的專案名稱重新執行命令。

### 步驟 3：驗證設定

```bash
wrangler pages secret list --project-name=heartbox
```

應該會看到 `VITE_SENTRY_DSN` 出現在列表中。

### 步驟 4：觸發重新部署

推送一個新的 commit 或在 Cloudflare Dashboard 手動重新部署：

```bash
# 方法 A：推送空 commit 觸發部署
git commit --allow-empty -m "chore: trigger redeployment for Sentry config"
git push

# 方法 B：或在 Cloudflare Dashboard 手動 Retry deployment
```

---

## 方法二：透過 Cloudflare Dashboard（如果你找到的話）

### 新版 Cloudflare 介面路徑：

1. **登入 Cloudflare**
   - https://dash.cloudflare.com

2. **進入 Workers & Pages**
   - 左側選單 → **Workers & Pages**

3. **選擇你的專案**
   - 在專案列表中點擊專案名稱

4. **設定環境變數**
   - 點擊 **Settings** 標籤
   - 找到 **Environment variables** 區塊（向下滾動）
   - 點擊 **Add variable**
   - 填寫：
     ```
     Variable name:  VITE_SENTRY_DSN
     Value:          https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
     Environment:    Production (勾選)
     ```
   - 點擊 **Save**

5. **重新部署**
   - Deployments → 最新部署 → Retry deployment

---

## 驗證 Sentry 是否生效

部署完成後（約 2-3 分鐘）：

1. **前往你的生產環境網站**
2. **打開瀏覽器 Console (F12)**
3. **執行測試：**
   ```javascript
   throw new Error("測試 Cloudflare Pages Sentry 整合")
   ```
4. **檢查 Sentry Dashboard**
   - 前往 https://sentry.io
   - 選擇 `heartbox-frontend` 專案
   - 應該會看到錯誤！

---

## 完成！ 🎉

設定完成後：
- ✅ 前端錯誤會自動發送到 Sentry
- ✅ 包含用戶操作重播
- ✅ 效能監控（頁面載入速度等）
- ✅ Email 通知新錯誤

**你的前端 Sentry DSN：**
```
https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
```

有問題隨時問我！
