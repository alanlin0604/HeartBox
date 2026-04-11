# Sentry 快速設定步驟

## 第一步：註冊 Sentry 帳號

1. **前往 Sentry 官網**
   - 網址：https://sentry.io/signup/
   
2. **選擇註冊方式**
   - 推薦使用 GitHub 帳號登入（最快）
   - 或使用 Google 帳號
   - 或使用 Email 註冊

3. **創建組織（Organization）**
   - 組織名稱：`HeartBox` 或 `your-name`
   - 選擇免費方案（Free Plan）
     - 5,000 錯誤事件/月
     - 10,000 性能追蹤/月
     - 完全足夠個人專案使用

---

## 第二步：創建後端專案

1. **點擊 "Create Project"**

2. **選擇平台：Django**
   - 在搜尋框輸入 "django"
   - 點擊 Django 卡片

3. **設定專案名稱**
   - Project name: `heartbox-backend`
   - Set your alert frequency: `Alert me on every new issue`（建議）

4. **創建專案並複製 DSN**
   - 點擊 "Create Project"
   - 頁面會顯示類似這樣的 DSN：
   ```
   https://a1b2c3d4e5f6g7h8i9j0@o123456.ingest.sentry.io/987654
   ```
   - **重要：立即複製這個 DSN！**

---

## 第三步：創建前端專案

1. **再次點擊 "Projects" → "Create Project"**

2. **選擇平台：React**
   - 在搜尋框輸入 "react"
   - 點擊 React 卡片

3. **設定專案名稱**
   - Project name: `heartbox-frontend`
   - Set your alert frequency: `Alert me on every new issue`

4. **創建專案並複製 DSN**
   - 你會得到另一個不同的 DSN
   - 這是前端專用的 DSN

---

## 第四步：設定後端環境變數

### 本地開發環境

1. **編輯 `.env` 檔案**（專案根目錄）

```bash
# 在 HeartBox/.env 中加入或更新：

# Sentry Error Tracking (後端)
SENTRY_DSN=https://你的後端DSN@o123456.ingest.sentry.io/987654
```

2. **測試設定**

```bash
cd backend
python manage.py shell
```

在 Python shell 中執行：
```python
from django.conf import settings
print(settings.SENTRY_DSN)  # 應該顯示你的 DSN

# 測試 Sentry 整合
import sentry_sdk
sentry_sdk.capture_message("測試 Sentry 整合")
print("✓ 測試訊息已發送到 Sentry")
```

3. **檢查 Sentry 控制台**
   - 前往 https://sentry.io
   - 選擇 `heartbox-backend` 專案
   - 在 Issues 頁面應該會看到 "測試 Sentry 整合" 訊息

### 生產環境（Google Cloud Run）

```bash
# 使用 gcloud CLI 更新環境變數
gcloud run services update heartbox-api \
  --region=asia-east1 \
  --update-env-vars SENTRY_DSN=https://你的後端DSN@o123456.ingest.sentry.io/987654
```

或在 Cloud Run 控制台手動設定：
1. 前往 Cloud Run → 選擇 `heartbox-api`
2. 點擊 "EDIT & DEPLOY NEW REVISION"
3. 展開 "Variables & Secrets"
4. 加入環境變數：
   - Name: `SENTRY_DSN`
   - Value: `https://你的後端DSN@...`
5. 點擊 "DEPLOY"

---

## 第五步：設定前端環境變數

### 本地開發環境

前端的 Sentry **只在 production 模式啟用**，所以本地開發時不需要設定。

### 生產環境（Cloudflare Pages）

1. **前往 Cloudflare Dashboard**
   - 登入 https://dash.cloudflare.com
   - Pages → 選擇你的專案

2. **設定環境變數**
   - Settings → Environment variables
   - 點擊 "Add variable"
   - Variable name: `VITE_SENTRY_DSN`
   - Value: `https://你的前端DSN@o123456.ingest.sentry.io/987654`
   - Environment: `Production`（只在生產環境啟用）
   - 點擊 "Save"

3. **重新部署**
   - Deployments → 最新部署 → "Retry deployment"
   - 或推送新的 commit 觸發自動部署

### 本地測試前端 Sentry（可選）

如果想在本地測試前端 Sentry：

1. **創建 `frontend/.env.production.local`**

```bash
# frontend/.env.production.local
VITE_SENTRY_DSN=https://你的前端DSN@o123456.ingest.sentry.io/987654
```

2. **建置並預覽 production 版本**

```bash
cd frontend
npm run build
npm run preview
```

3. **測試錯誤捕獲**

打開瀏覽器控制台（F12），執行：
```javascript
throw new Error("測試 Sentry 前端整合")
```

4. **檢查 Sentry 控制台**
   - 選擇 `heartbox-frontend` 專案
   - 應該會看到錯誤出現

---

## 第六步：驗證設定

### 後端驗證

創建測試 endpoint（可選，測試後請移除）：

```python
# backend/api/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def test_sentry(request):
    """測試 Sentry 錯誤捕獲（測試完請移除）"""
    # 觸發除零錯誤
    result = 1 / 0
    return Response({'status': 'ok'})
```

```python
# backend/moodnotes_pro/urls.py
urlpatterns = [
    # ... 其他 URL patterns
    path('api/test-sentry/', test_sentry, name='test-sentry'),  # 測試用，完成後請移除
]
```

訪問 `http://localhost:8000/api/test-sentry/`，應該會在 Sentry 看到錯誤。

### 前端驗證

在任何頁面的瀏覽器控制台執行：
```javascript
import * as Sentry from '@sentry/react'
Sentry.captureException(new Error('測試前端 Sentry'))
```

---

## 常見問題

### Q1: 找不到 DSN？

**解決方法：**
1. 登入 https://sentry.io
2. 選擇專案（heartbox-backend 或 heartbox-frontend）
3. Settings → Client Keys (DSN)
4. 複製 DSN

### Q2: Sentry 沒有收到錯誤？

**檢查清單：**
1. ✅ 確認 DSN 已正確設定（沒有多餘空格）
2. ✅ 確認環境變數已載入
   ```python
   # Python
   from django.conf import settings
   print(settings.SENTRY_DSN)
   ```
3. ✅ 後端：重啟 Django 服務
4. ✅ 前端：確認是在 production 模式（`npm run build && npm run preview`）
5. ✅ 檢查防火牆/網路是否阻擋 Sentry
6. ✅ 檢查 Sentry quota 是否已用完（unlikely for free plan）

### Q3: 本地開發時想看到錯誤？

**後端：** 預設在所有環境啟用（如果有設定 DSN）

**前端：** 修改 `frontend/src/main.jsx`：

```javascript
// 移除 import.meta.env.PROD 條件（僅用於測試！）
if (SENTRY_DSN) {  // 原本：if (SENTRY_DSN && import.meta.env.PROD)
  Sentry.init({
    // ...
  })
}
```

**重要：測試完請改回來！** 否則開發時會發送大量錯誤到 Sentry。

### Q4: 如何查看 Sentry Dashboard？

1. 登入 https://sentry.io
2. 選擇 Organization → HeartBox
3. 選擇 Project → heartbox-backend 或 heartbox-frontend
4. 主要頁面：
   - **Issues**: 所有錯誤列表
   - **Performance**: API 和頁面效能
   - **Releases**: 版本追蹤（進階功能）
   - **Alerts**: 警報設定

### Q5: 收到太多錯誤通知？

**調整採樣率：**

後端 (`backend/moodnotes_pro/settings.py`)：
```python
sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=0.05,  # 降低至 5%
    # ...
)
```

前端 (`frontend/src/main.jsx`)：
```javascript
Sentry.init({
    dsn: SENTRY_DSN,
    tracesSampleRate: 0.05,  // 降低至 5%
    // ...
})
```

---

## 設定完成檢查清單

- [ ] 已註冊 Sentry 帳號
- [ ] 已創建 heartbox-backend 專案並複製 DSN
- [ ] 已創建 heartbox-frontend 專案並複製 DSN
- [ ] 已在本地 `.env` 設定後端 SENTRY_DSN
- [ ] 已在 Cloud Run 設定後端 SENTRY_DSN
- [ ] 已在 Cloudflare Pages 設定前端 VITE_SENTRY_DSN
- [ ] 已測試後端 Sentry（看到測試錯誤出現在 Dashboard）
- [ ] 已測試前端 Sentry（production 模式）
- [ ] 已移除測試用的 endpoint 和程式碼

---

## 下一步

設定完成後，Sentry 會自動：
- ✅ 捕獲所有未處理的錯誤
- ✅ 追蹤 API 效能（10% 採樣）
- ✅ 記錄錯誤發生時的用戶操作流程
- ✅ 在有新錯誤時發送 Email 通知

建議：
1. 設定 Slack 整合（Settings → Integrations → Slack）
2. 定期檢查 Dashboard（每週一次）
3. 修復高頻錯誤
4. 監控效能趨勢

**恭喜！Sentry 錯誤監控已完成設定！** 🎉
