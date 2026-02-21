# HeartBox 開發環境設定指南

在新電腦上設定 HeartBox 開發環境的完整步驟。

---

## 前置需求

- **Git**
- **Python 3.12+**
- **Node.js 18+**（含 npm）
- **PostgreSQL**（或使用 Neon 雲端資料庫，本地可用 SQLite 替代）

---

## 1. Clone 專案

```bash
git clone https://github.com/alanlin0604/HeartBox.git
cd HeartBox
```

---

## 2. 設定環境變數

在專案根目錄建立 `.env` 檔（此檔案不會被 git 追蹤）：

```env
# Django
SECRET_KEY=你的django-secret-key
DEBUG=True

# 資料庫（Neon PostgreSQL）
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# 加密金鑰（用於日記內容加密）
# 產生方式：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=你的fernet-key

# OpenAI（AI 分析、聊天功能）
OPENAI_API_KEY=你的openai-api-key

# CORS（本地開發）
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173
```

> **重要：** `.env` 包含密鑰，請從原本的電腦複製過來，或向團隊成員取得。

---

## 3. 後端設定

```bash
# 進入後端目錄
cd backend

# 建立虛擬環境（建議）
python -m venv venv

# 啟用虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 執行資料庫遷移
python manage.py migrate

# （選用）建立管理員帳號
python manage.py createsuperuser

# 啟動開發伺服器
python manage.py runserver
```

後端會在 `http://localhost:8000` 啟動。

---

## 4. 前端設定

```bash
# 進入前端目錄（從專案根目錄）
cd frontend

# 安裝依賴
npm install

# 啟動開發伺服器
npm run dev
```

前端會在 `http://localhost:5173` 啟動。

---

## 5. 驗證

1. 開啟 `http://localhost:5173`
2. 註冊一個新帳號或使用既有帳號登入
3. 確認可以新增日記、查看儀表板等功能

---

## 執行測試

```bash
cd backend
python manage.py test api.tests -v2 --settings=moodnotes_pro.test_settings
```

測試使用 SQLite（不需要 PostgreSQL 連線）。

---

## 專案結構

```
HeartBox/
├── backend/                 # Django 後端
│   ├── api/                 # 主要 App（models, views, serializers）
│   ├── moodnotes_pro/       # Django 專案設定
│   ├── requirements.txt     # Python 依賴
│   └── manage.py
├── frontend/                # Vite + React 前端
│   ├── src/                 # 原始碼
│   ├── public/              # 靜態資源（logo, sw.js, manifest.json）
│   └── package.json
├── docs/                    # 文件
├── Dockerfile               # 後端部署用（Cloud Run）
├── .env                     # 環境變數（不在 git 中）
└── README.md
```

---

## 部署

### 前端（Cloudflare Pages）

```bash
cd frontend
npm run build
npx wrangler pages deploy dist --project-name=heartbox --branch=main
```

### 後端（Google Cloud Run）

```bash
# 從專案根目錄執行（不是 backend/）
gcloud run deploy heartbox-api \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --project heartbox-app
```

> **注意：** 部署必須從專案根目錄執行，因為 Dockerfile 在根目錄。

---

## 常見問題

### Q: 本地不想連 Neon PostgreSQL？
移除 `.env` 中的 `DATABASE_URL`，Django 會自動使用 SQLite。

### Q: ENCRYPTION_KEY 怎麼產生？
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Q: 前端 API 請求失敗？
確認後端已啟動在 `localhost:8000`，且 `.env` 中 `CORS_ALLOWED_ORIGINS` 包含 `http://localhost:5173`。

### Q: AI 功能沒有回應？
確認 `.env` 中的 `OPENAI_API_KEY` 有效且有餘額。AI 功能為選用，缺少 API Key 時會優雅降級（不影響其他功能）。
