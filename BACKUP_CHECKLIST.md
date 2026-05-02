# 🔐 重灌前備份檢查清單

**檢查時間：** 2026-05-02  
**專案：** HeartBox  
**GitHub：** https://github.com/alanlin0604/HeartBox

---

## ✅ 已備份到 GitHub 的內容

### 程式碼 (100% 完整)
- ✅ 前端程式碼 (`frontend/`)
- ✅ 後端程式碼 (`backend/`)
- ✅ Docker 配置 (`Dockerfile`)
- ✅ CI/CD 配置 (`.github/workflows/`)
- ✅ 依賴清單 (`package.json`, `requirements.txt`)
- ✅ Capacitor 配置 (`capacitor.config.json`)

### 文檔 (100% 完整)
- ✅ 13 個核心文檔
- ✅ 2 個 API 文檔
- ✅ 15 個歸檔文檔
- ✅ RESTORE.md (恢復指南)
- ✅ CLAUDE_INSTRUCTIONS.md (Claude 指令指南)
- ✅ setup.ps1 (自動化腳本)

### Git 狀態
- ✅ 本地與遠端同步 (origin/main)
- ✅ 無未提交的變更
- ✅ 最新 commit: `215accf`
- ✅ 總共 5 個最新 commits 已推送

---

## ⚠️ 需要手動備份的內容

### 🔑 敏感資訊（最重要！）

#### 必須備份
⚠️ **檢測結果：** `.env` 檔案和系統環境變數均不存在  
📍 **可能位置：**
- Google Cloud Run 的環境變數設定
- 本地開發時使用預設值
- 需要重新取得 API keys

建議在重灌前備份以下資訊：

- [ ] **Django Secret Key** - 用於加密和簽名
  - 來源：重新生成或從 Cloud Run 環境變數匯出
  - 變數名：`DJANGO_SECRET_KEY`
  - 生成方式：`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  
- [ ] **OpenAI API Key** - AI 功能必需
  - 來源：OpenAI Dashboard (https://platform.openai.com/api-keys)
  - 變數名：`OPENAI_API_KEY`
  - ⚠️ 如果遺失需要重新生成
  
- [ ] **Email 密碼** - GoDaddy SMTP
  - 帳號：`support@heartbox.tw`
  - 來源：GoDaddy Email 管理介面
  - 變數名：`EMAIL_HOST_PASSWORD`

#### 雲端服務憑證
- [x] **Google Cloud 認證** ✅
  - 狀態：已登入 (alan930604@gmail.com)
  - 專案：`heartbox-app`
  - 重灌後需要：`gcloud auth login`
  
- [x] **GitHub 認證** ✅
  - 狀態：已登入 (alanlin0604)
  - Token 範圍：gist, read:org, repo
  - 重灌後需要：`gh auth login`

#### 選填
- [ ] **Sentry DSN** - 錯誤監控（選填）
- [ ] **Cloudflare API Token** - 自動部署（可重新生成）

---

## 📋 重灌後恢復檢查

### 步驟 1：安裝工具
```powershell
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

### 步驟 3：告訴 Claude
```
幫我建置 HeartBox 開發環境
```

### 步驟 4：建立環境變數
```
幫我建立環境變數檔案
```
然後填入備份的敏感資訊。

---

## 🔍 驗證方法

重灌後執行以下檢查：

### Git 驗證
```bash
git status          # 應該顯示 clean
git log -1          # 應該是 215accf
git remote -v       # 應該指向 alanlin0604/HeartBox
```

### 工具版本
```bash
git --version       # Git 2.x+
node --version      # Node 20.x+
python --version    # Python 3.12.x
gh --version        # GitHub CLI 2.x+
```

### 專案完整性
```bash
cd frontend && npm install    # 應該成功
cd ../backend && python -m venv venv && venv\Scripts\activate && pip install -r ../requirements.txt  # 應該成功
```

### 測試執行
```bash
cd frontend && npm test       # 應該通過 74 個測試
```

---

## 📞 帳號資訊

### GitHub
- **帳號：** alanlin0604
- **Email：** alan930604@gmail.com
- **倉庫：** https://github.com/alanlin0604/HeartBox

### Google Cloud
- **帳號：** alan930604@gmail.com
- **專案 ID：** heartbox-app
- **區域：** asia-east1

### 部署網址
- **前端：** https://heartbox-frontend.pages.dev
- **後端：** https://heartbox-api-598139488748.asia-east1.run.app

---

## ⚡ 快速恢復命令

重灌後在 PowerShell 執行：

```powershell
# 1. 安裝工具（一次性）
winget install Git.Git OpenJS.NodeJS.LTS Python.Python.3.12 Microsoft.VisualStudioCode GitHub.cli

# 2. Clone 專案
cd C:\Users\alan9\OneDrive\Desktop
git clone https://github.com/alanlin0604/HeartBox.git
cd HeartBox

# 3. 開啟 VS Code
code .

# 4. 開啟 Claude Code，說：
# "幫我建置 HeartBox 開發環境"
```

---

## 💡 重要提醒

### ✅ 可以安心重灌
- 所有程式碼已安全備份到 GitHub
- 所有文檔已完整提交
- 自動化腳本已建立
- 恢復指南已完成

### ⚠️ 必須手動處理
- `.env` 檔案不在 Git 中（安全考量）
- 需要重新填入 API keys 和密碼
- Google Cloud 和 GitHub 需要重新登入

### 🔐 敏感資訊處理
1. **備份位置建議：**
   - 密碼管理器（1Password, Bitwarden）
   - 加密的 USB 隨身碟
   - OneDrive 加密資料夾

2. **不要：**
   - ❌ 不要將 .env 提交到 Git
   - ❌ 不要將金鑰存成純文字檔
   - ❌ 不要存在未加密的雲端硬碟

---

## ✨ 預期結果

重灌後，你應該能夠：

1. ✅ Clone 專案成功
2. ✅ 告訴 Claude「幫我建置環境」
3. ✅ 5 分鐘內完成所有依賴安裝
4. ✅ 填入環境變數後立即啟動開發
5. ✅ 執行測試全部通過
6. ✅ 前後端正常運行

**重灌後的開發體驗應該和現在一模一樣！** 🎉

---

**建立時間：** 2026-05-02  
**檢查人：** Claude Sonnet 4.5  
**狀態：** ✅ 備份完整，可以重灌
