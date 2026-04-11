# Cloudflare Pages 環境變數設定 - 詳細導航指南

## 方法一：透過專案設定頁面

### 步驟 1：登入並找到專案

1. **前往 Cloudflare Dashboard**
   - 網址：https://dash.cloudflare.com
   - 登入你的帳號

2. **進入 Pages**
   - 在左側導航欄找到 **"Workers & Pages"**
   - 或直接搜尋 "Pages"
   - 點擊進入

3. **選擇 HeartBox 專案**
   - 在專案列表中找到你的 HeartBox 專案
   - 點擊專案名稱（不是右側的按鈕）

### 步驟 2：找到環境變數設定

進入專案後，你會看到幾個標籤：

**選項 A：如果你看到這些標籤**
- Deployments
- Settings
- Analytics
- etc.

點擊 **"Settings"** 標籤，然後：
- 向下滾動找到 **"Environment variables"** 區塊
- 或在左側子選單中找到 **"Environment variables"**

**選項 B：如果介面不同**
- 尋找 **"⚙️ Settings"** 圖示或按鈕
- 或直接在頁面上方找到 **"Environment variables"** 連結

**選項 C：直接 URL（最快）**
```
https://dash.cloudflare.com/[你的帳號ID]/pages/view/[專案名稱]/settings/environment-variables
```

### 步驟 3：新增環境變數

1. **找到 "Add variable" 或 "Add" 按鈕**
   - 通常在 Environment variables 區塊的右上角
   - 或是在頁面中間的 "Add environment variable" 按鈕

2. **填寫變數資訊**
   ```
   Variable name:  VITE_SENTRY_DSN
   Value:          https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
   ```

3. **選擇環境**
   - ✅ **Production** (勾選)
   - ❌ Preview (不勾選)

4. **儲存**
   - 點擊 "Save" 或 "Add variable" 按鈕

---

## 方法二：透過 Deployments 頁面

如果上面的方法找不到，試試這個：

1. **在專案頁面點擊 "Deployments"**

2. **找到最新的 Production 部署**
   - 找到標記為 "Production" 的部署
   - 點擊該部署（進入部署詳情）

3. **尋找環境變數設定**
   - 在部署詳情頁面中
   - 找到 "Environment variables" 或 "Settings" 區塊
   - 點擊 "Manage variables" 或類似按鈕

---

## 方法三：透過專案設定檔（wrangler.toml）

如果你無法透過 Web UI 設定，可以使用設定檔：

### 1. 安裝 Wrangler CLI

```bash
npm install -g wrangler
```

### 2. 登入 Cloudflare

```bash
wrangler login
```

這會打開瀏覽器讓你授權。

### 3. 設定環境變數

```bash
# 方法 A：互動式設定
wrangler pages secret put VITE_SENTRY_DSN --project-name=heartbox

# 會提示你輸入值，貼上：
# https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
```

或

```bash
# 方法 B：直接設定（一行完成）
echo "https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816" | wrangler pages secret put VITE_SENTRY_DSN --project-name=heartbox
```

### 4. 驗證設定

```bash
wrangler pages secret list --project-name=heartbox
```

應該會顯示 `VITE_SENTRY_DSN`。

---

## 方法四：透過 GitHub Actions 自動設定

如果你的專案是透過 GitHub 自動部署，可以在 GitHub Secrets 中設定：

1. **前往 GitHub 儲存庫**
   - https://github.com/alanlin0604/HeartBox

2. **Settings → Secrets and variables → Actions**

3. **點擊 "New repository secret"**
   ```
   Name:   VITE_SENTRY_DSN
   Value:  https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816
   ```

4. **更新 GitHub Actions workflow**

編輯 `.github/workflows/deploy.yml`（如果存在）：

```yaml
- name: Build
  env:
    VITE_SENTRY_DSN: ${{ secrets.VITE_SENTRY_DSN }}
  run: npm run build
```

---

## 常見介面變化

Cloudflare 的介面可能因帳號類型或時間而異：

### 舊版介面
```
專案頁面
  ├─ Settings (標籤)
  │   └─ Environment variables (區塊)
  └─ ...
```

### 新版介面
```
專案頁面
  ├─ Settings
  │   ├─ General
  │   ├─ Builds & deployments
  │   ├─ Environment variables ← 在這裡！
  │   └─ Functions
  └─ ...
```

### 最新介面（2024+）
```
Workers & Pages
  └─ 選擇專案
      ├─ Overview
      ├─ Deployments
      ├─ Settings
      │   ├─ General
      │   ├─ Environment variables ← 在這裡！
      │   ├─ Builds & deployments
      │   └─ Functions
      └─ Analytics
```

---

## 疑難排解

### 問題 1：完全找不到 Environment variables

**可能原因：**
- 你可能沒有該專案的編輯權限
- 專案可能不是 Pages 專案（而是 Workers）

**解決方法：**
1. 確認你是專案的 Owner 或 Administrator
2. 確認專案類型是 "Pages" 而不是 "Workers"
3. 嘗試使用 Wrangler CLI（方法三）

### 問題 2：看到 "Bindings" 而不是 "Environment variables"

- 這是 Workers 的介面
- 確認你選擇的是 Pages 專案

### 問題 3：設定後沒有生效

**檢查清單：**
- ✅ 變數名稱是 `VITE_SENTRY_DSN`（不是 `SENTRY_DSN`）
- ✅ 環境選擇了 "Production"
- ✅ 已重新部署（推送新 commit 或手動 Retry deployment）
- ✅ 等待 2-3 分鐘讓部署完成

---

## 快速檢查：你的專案部署方式

### 如果是透過 Cloudflare Pages GitHub 整合：

1. GitHub 儲存庫連接到 Cloudflare Pages
2. 每次推送 commit 自動部署
3. **設定位置：** Cloudflare Dashboard → Pages → 專案 → Settings → Environment variables

### 如果是透過 Wrangler CLI 部署：

1. 使用 `wrangler pages publish` 手動部署
2. **設定位置：** 使用 `wrangler pages secret put`

---

## 視覺指引

如果你還是找不到，請告訴我：

1. **你登入 Cloudflare 後看到的主選單有哪些項目？**
   - 例如：Home, Websites, Workers & Pages, etc.

2. **點擊專案後，頁面上方的標籤有哪些？**
   - 例如：Overview, Deployments, Settings, Analytics, etc.

3. **你的專案名稱是什麼？**
   - 我可以提供更精確的 URL

我會根據你的回答提供更準確的指引！

---

## 暫時解決方案：使用 Wrangler CLI

如果 UI 真的找不到，最快的方法是使用 CLI：

```bash
# 1. 安裝 Wrangler
npm install -g wrangler

# 2. 登入
wrangler login

# 3. 設定環境變數（會提示輸入專案名稱）
wrangler pages secret put VITE_SENTRY_DSN

# 輸入值：
# https://c40321f6356ee874a6b4fcf4ebe3a01d@o4511203108847616.ingest.us.sentry.io/4511203130146816

# 4. 驗證
wrangler pages secret list
```

這個方法 100% 有效，而且只需要 2 分鐘！
