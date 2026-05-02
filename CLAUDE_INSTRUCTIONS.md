# 🤖 Claude 自動化指令指南

當你重灌電腦後，只需要告訴 Claude 這些簡單的指令，我會自動幫你完成所有設定。

## 📋 快速指令清單

### 1️⃣ 環境建置
```
幫我建置 HeartBox 開發環境
```
**Claude 會自動：**
- 設定 Git 使用者資訊 (alam930604, alan930604@gmail.com)
- 安裝前端依賴 (npm install)
- 建立 Python 虛擬環境
- 安裝後端依賴 (pip install -r requirements.txt)
- 檢查環境變數檔案

---

### 2️⃣ 建立環境變數
```
幫我建立環境變數檔案
```
**Claude 會建立：**
- `backend/.env` - 包含 Django、資料庫、OpenAI、Email 設定
- `frontend/.env` - 包含 Vite API URL、Sentry DSN

⚠️ **你需要手動填入的敏感資訊：**
- `DJANGO_SECRET_KEY` - Django 金鑰
- `OPENAI_API_KEY` - OpenAI API 金鑰
- `EMAIL_HOST_PASSWORD` - Email 密碼
- `DATABASE_URL` - 資料庫連線字串（選填）

---

### 3️⃣ 啟動開發環境
```
啟動開發環境
```
**Claude 會：**
- 開啟終端機 1：啟動後端 (Django + Daphne)
- 開啟終端機 2：啟動前端 (Vite dev server)
- 自動執行資料庫遷移

---

### 4️⃣ 部署到生產環境
```
部署前端到 Cloudflare Pages
```
或
```
部署後端到 Google Cloud Run
```

---

### 5️⃣ 檢查系統狀態
```
檢查專案健康狀況
```
**Claude 會檢查：**
- Git 狀態
- 依賴版本
- 測試執行結果
- 環境變數完整性

---

### 6️⃣ Android 開發
```
開始 Android 開發
```
**Claude 會：**
- 參考 `docs/Android開發與優化清單.md`
- 從任務 1 開始執行：安裝健康資料插件
- 逐步完成 30 個任務

---

## 🔑 需要備份的敏感資訊

重灌前請備份這些資訊（不要存在 Git 中）：

### 必須
- [ ] `DJANGO_SECRET_KEY` - Django 金鑰
- [ ] `OPENAI_API_KEY` - OpenAI API 金鑰
- [ ] `EMAIL_HOST_PASSWORD` - support@heartbox.tw 的密碼

### 選填
- [ ] `DATABASE_URL` - PostgreSQL 連線字串（如果使用雲端資料庫）
- [ ] `SENTRY_DSN` - Sentry 錯誤監控（選填）
- [ ] Google Cloud 服務帳號金鑰 JSON 檔案

---

## 💡 進階指令

### 修復部署問題
```
修復 Cloud Run 部署失敗問題
```

### 執行測試
```
執行所有測試
```

### 建立新功能
```
根據 Android開發與優化清單，執行下一個任務
```

### 查看文檔
```
顯示專案文檔結構
```

---

## 📚 相關文檔

- **完整恢復指南：** [RESTORE.md](./RESTORE.md)
- **Android 開發清單：** [docs/Android開發與優化清單.md](./docs/Android開發與優化清單.md)
- **文檔索引：** [docs/README.md](./docs/README.md)
- **系統架構：** [docs/system-architecture.md](./docs/system-architecture.md)

---

## 🎯 使用原則

1. **簡單明確**：用自然語言說出你要做什麼
2. **信任 Claude**：我會檢查所有步驟並提醒你需要注意的事項
3. **確認變更**：重要操作（如部署、刪除）我會先詢問確認
4. **隨時提問**：不確定時隨時問我「這個步驟會做什麼？」

---

**重灌後第一句話就說：**
```
幫我建置 HeartBox 開發環境
```

我會自動完成所有設定！🚀
