# 💻 電腦重灌後恢復工作指南

## 🤖 自動化建置（推薦）

重灌後只需 3 步驟，Claude 會自動幫你完成所有設定：

### 步驟 1：安裝基礎工具
```powershell
# 在 PowerShell (系統管理員) 執行
winget install Git.Git
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
winget install Microsoft.VisualStudioCode
winget install GitHub.cli
```

### 步驟 2：Clone 專案
```powershell
cd C:\Users\alan9\OneDrive\Desktop
git clone https://github.com/alanlin0604/HeartBox.git
cd HeartBox
```

### 步驟 3：開啟 Claude Code 並說
```
幫我建置 HeartBox 開發環境
```

**Claude 會自動執行：**
- ✅ 設定 Git 使用者資訊
- ✅ 安裝前端依賴 (npm install)
- ✅ 建立後端虛擬環境
- ✅ 安裝後端依賴 (pip install)
- ✅ 檢查環境變數檔案
- ✅ 執行資料庫遷移

**接著說：**
```
幫我建立環境變數檔案
```

Claude 會建立 `backend/.env` 和 `frontend/.env`，然後你只需填入敏感資訊（API keys）。

**最後說：**
```
啟動開發環境
```

就完成了！🎉

---

## ✅ 已完成：所有變更已 Push

**最新 4 個 commits 已推送到 GitHub：**
1. `4d21d96` - docs: add computer reinstallation recovery guide
2. `fc8e4c3` - docs: reorganize and clean up documentation structure
3. `158b9c7` - docs: add comprehensive Android development and optimization roadmap
4. `bf49702` - chore: remove HEALTHCHECK from Dockerfile for Cloud Run compatibility

**確認網址：** https://github.com/alanlin0604/HeartBox

---

## 🔧 手動恢復步驟（進階使用者）

> 💡 建議使用上方的自動化建置方式，以下為手動步驟參考

### 1️⃣ 安裝必要軟體（Windows）

#### Git
```powershell
winget install Git.Git
```

#### Node.js (20.x LTS)
```powershell
winget install OpenJS.NodeJS.LTS
```

#### Python 3.12
```powershell
winget install Python.Python.3.12
```

#### VS Code
```powershell
winget install Microsoft.VisualStudioCode
```

#### GitHub CLI (gh)
```powershell
winget install GitHub.cli
```

#### Google Cloud SDK
下載並安裝：https://cloud.google.com/sdk/docs/install

---

### 2️⃣ Clone 專案

```bash
cd C:\Users\alan9\OneDrive\Desktop
git clone https://github.com/alanlin0604/HeartBox.git
cd HeartBox
```

---

### 3️⃣ 設定 Git

```bash
git config --global user.name "alam930604"
git config --global user.email "alan930604@gmail.com"
```

---

### 4️⃣ 安裝專案依賴

#### 前端
```bash
cd frontend
npm install
```

#### 後端
```bash
cd ../backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

### 5️⃣ 設定環境變數

#### 後端 `.env`
在 `backend/` 目錄建立 `.env` 檔案：

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/heartbox

# OpenAI
OPENAI_API_KEY=your-openai-key

# Email (GoDaddy SMTP)
EMAIL_HOST=smtpout.secureserver.net
EMAIL_PORT=465
EMAIL_HOST_USER=support@heartbox.tw
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_USE_SSL=True

# Sentry (選填)
SENTRY_DSN=your-sentry-dsn
```

#### 前端 `.env`
在 `frontend/` 目錄建立 `.env` 檔案：

```env
VITE_API_URL=http://localhost:8000
VITE_SENTRY_DSN=your-sentry-dsn
```

---

### 6️⃣ 啟動開發環境

#### 終端機 1：後端
```bash
cd backend
venv\Scripts\activate
python manage.py migrate
python manage.py runserver
```

#### 終端機 2：前端
```bash
cd frontend
npm run dev
```

**開啟瀏覽器：** http://localhost:5173

---

### 7️⃣ Google Cloud 認證

```bash
gcloud auth login
gcloud config set project heartbox-app
gcloud config set run/region asia-east1
```

---

## 📋 當前專案狀態

### ✅ 已完成
- ✅ 6 大核心功能已實作（習慣追蹤、儀表板、好友系統、睡眠分析、社群、匯入）
- ✅ 前端已部署到 Cloudflare Pages
- ✅ CI/CD 管道正常運作
- ✅ 文檔已整理（12 個核心文件 + 2 個 API 文件）
- ✅ Android 開發清單已建立（30 個任務）

### ⚠️ 待處理
- ❌ 後端部署問題（Cloud Run "Container import failed"）
- ⏳ Android APP 建置（尚未開始）
- ⏳ 健康資料整合（插件已選定，待安裝）

---

## 🚀 下一步行動

重灌後繼續工作的建議順序：

### 方案 A：Android 開發（推薦）
1. 參考 `docs/Android開發與優化清單.md`
2. 從任務 1 開始：安裝健康資料插件
3. 預算：$25 USD（Google Play Console）

### 方案 B：解決後端部署
1. 聯繫 Google Cloud 支援
2. 或等待平台問題修復
3. 目前後端仍在運行（舊版本）

### 方案 C：本地開發優化
1. 實作背景健康資料同步
2. 新增健康異常偵測
3. 優化前端效能

---

## 📞 重要連結

### GitHub
- **專案：** https://github.com/alanlin0604/HeartBox
- **帳號：** alanlin0604

### 部署
- **前端：** https://heartbox-frontend.pages.dev
- **後端：** https://heartbox-api-598139488748.asia-east1.run.app

### Cloud Services
- **GCP 專案：** heartbox-app
- **GCP 帳號：** alan930604@gmail.com
- **Cloudflare：** 使用 GitHub Actions 自動部署

### 文檔
- **核心文檔：** `docs/README.md`
- **Android 清單：** `docs/Android開發與優化清單.md`
- **系統架構：** `docs/system-architecture.md`

---

## 🔐 需要的憑證/金鑰（請備份）

### 必須備份
- [ ] Django `DJANGO_SECRET_KEY`
- [ ] `OPENAI_API_KEY`
- [ ] Email 密碼 (`EMAIL_HOST_PASSWORD`)
- [ ] Google Cloud 服務帳號金鑰
- [ ] GitHub Personal Access Token（如果有）

### Android 開發（未來需要）
- [ ] Android Keystore 檔案
- [ ] Keystore 密碼
- [ ] Google Play Console 帳號

### 選填
- [ ] Sentry DSN
- [ ] Cloudflare API Token

---

## 📱 聯絡資訊

- **Email：** alan930604@gmail.com
- **GitHub：** alanlin0604
- **專案名稱：** HeartBox

---

## ⚡ 快速檢查清單

重灌後確認以下項目：

```bash
# 檢查工具版本
git --version          # Git 2.x+
node --version         # Node 20.x+
npm --version          # npm 10.x+
python --version       # Python 3.12.x
gh --version           # GitHub CLI 2.x+
gcloud --version       # Google Cloud SDK

# 檢查專案
cd HeartBox
git status             # 應該是 clean
git log -1             # 最新 commit: fc8e4c3

# 前端測試
cd frontend
npm test               # 應該通過 74 個測試

# 後端測試
cd ../backend
python manage.py check # 應該 0 issues
```

---

## 💡 提示

1. **OneDrive 同步：** 如果使用 OneDrive，確保 `HeartBox/` 資料夾已同步
2. **環境變數：** 重新建立 `.env` 檔案（不會同步到 Git）
3. **node_modules：** 需要重新 `npm install`
4. **Python venv：** 需要重新建立虛擬環境
5. **Git 認證：** 第一次 push 時需要輸入 GitHub 帳號密碼或 token

---

**建立日期：** 2026-05-02  
**最後 Push：** fc8e4c3  
**狀態：** ✅ 所有變更已備份到 GitHub

**重灌後只需 clone 專案，安裝依賴，即可繼續開發！** 🚀
