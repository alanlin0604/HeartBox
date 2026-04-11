# Sentry 錯誤監控設定指南

## 概述

Sentry 是一個強大的錯誤監控和性能追蹤平台，可以幫助我們：
- 即時捕獲前端和後端的錯誤
- 追蹤錯誤的堆疊資訊和用戶操作流程
- 監控應用程式性能（API 回應時間、頁面載入速度等）
- 設定錯誤通知警報

## 1. 註冊 Sentry 帳號

1. 前往 [sentry.io](https://sentry.io/signup/)
2. 使用 GitHub 或 Google 帳號註冊（推薦使用專案相關的帳號）
3. 創建新的組織（Organization）

## 2. 創建專案

### 後端專案（Django）

1. 在 Sentry 控制台點擊「Create Project」
2. 選擇平台：**Django**
3. 設定警報頻率：建議選擇「Alert me on every new issue」
4. 專案名稱：`heartbox-backend`
5. 創建完成後，Sentry 會顯示 DSN（Data Source Name）
6. 複製 DSN，格式類似：
   ```
   https://examplePublicKey@o0.ingest.sentry.io/0
   ```

### 前端專案（React）

1. 再次點擊「Create Project」
2. 選擇平台：**React**
3. 設定警報頻率：建議選擇「Alert me on every new issue」
4. 專案名稱：`heartbox-frontend`
5. 複製前端專案的 DSN

## 3. 配置環境變數

### 後端配置

在專案根目錄的 `.env` 檔案中加入：

```bash
# Sentry Error Tracking
SENTRY_DSN=https://your-backend-dsn@o0.ingest.sentry.io/0
```

### 前端配置

在 `frontend/.env.production` 檔案中加入：

```bash
# Sentry Error Tracking (production only)
VITE_SENTRY_DSN=https://your-frontend-dsn@o0.ingest.sentry.io/0
```

**注意：**
- 前端的 Sentry 只在 **production 模式** 下啟用（避免開發時的錯誤干擾）
- 後端的 Sentry 在設定 DSN 後即啟用

## 4. 部署配置

### Cloudflare Pages（前端）

在 Cloudflare Pages 的環境變數設定中加入：
- 變數名稱：`VITE_SENTRY_DSN`
- 變數值：前端 Sentry DSN

### Google Cloud Run（後端）

使用 `gcloud` CLI 更新環境變數：

```bash
gcloud run services update heartbox-api \
  --region=asia-east1 \
  --update-env-vars SENTRY_DSN=https://your-backend-dsn@o0.ingest.sentry.io/0
```

或在 Cloud Run 控制台手動設定環境變數。

## 5. 測試配置

### 測試後端 Sentry

創建一個測試 view 來觸發錯誤：

```python
# backend/api/views.py（測試用，正式環境請移除）
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def sentry_debug(request):
    division_by_zero = 1 / 0
    return Response({'status': 'ok'})
```

訪問該 endpoint 後，應該會在 Sentry 控制台看到錯誤。

### 測試前端 Sentry

在瀏覽器控制台執行：

```javascript
// 只在 production build 中有效
throw new Error("Sentry 測試錯誤")
```

或在程式碼中手動觸發：

```javascript
import * as Sentry from '@sentry/react'

// 測試錯誤捕獲
Sentry.captureException(new Error('測試 Sentry 整合'))
```

## 6. Sentry 功能說明

### 後端配置（已完成）

在 `backend/moodnotes_pro/settings.py` 中的配置：

```python
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,      # 追蹤 10% 的交易（性能監控）
        profiles_sample_rate=0.1,    # 效能分析採樣率
        send_default_pii=False,      # 不發送個人識別資訊（GDPR 合規）
    )
```

### 前端配置（已完成）

在 `frontend/src/main.jsx` 中的配置：

```javascript
Sentry.init({
  dsn: SENTRY_DSN,
  environment: import.meta.env.MODE,
  integrations: [
    Sentry.browserTracingIntegration(),  // 頁面載入和導航追蹤
    Sentry.replayIntegration({           // 錯誤時的用戶操作重播
      maskAllText: true,                 // 遮蔽所有文字（隱私保護）
      blockAllMedia: true,               // 不記錄媒體內容
    }),
  ],
  tracesSampleRate: 0.1,                 // 追蹤 10% 的交易
  replaysSessionSampleRate: 0.1,         // 記錄 10% 的正常會話
  replaysOnErrorSampleRate: 1.0,         // 錯誤發生時 100% 記錄重播
})
```

## 7. Sentry 控制台使用

### 查看錯誤

1. 登入 [sentry.io](https://sentry.io)
2. 選擇專案（heartbox-backend 或 heartbox-frontend）
3. 在 Issues 頁面查看所有錯誤
4. 點擊錯誤可查看：
   - 錯誤堆疊（Stack Trace）
   - 發生時間和頻率
   - 受影響的用戶數量
   - 環境資訊（瀏覽器、作業系統等）
   - 用戶操作流程（Breadcrumbs）

### 設定警報

1. 前往 **Alerts** → **Create Alert**
2. 選擇條件（例如：「當新錯誤發生時」）
3. 設定通知方式：
   - Email
   - Slack（推薦）
   - Discord
   - Webhook

### 效能監控

1. 前往 **Performance** 頁面
2. 查看：
   - API endpoint 回應時間
   - 頁面載入速度
   - 慢查詢（Slow Queries）
   - 交易追蹤（Transaction Traces）

## 8. 隱私和安全考量

### 資料隱私

我們的配置已經考慮隱私保護：

1. **後端**：
   - `send_default_pii=False`：不發送個人識別資訊
   - Sentry 不會記錄用戶的加密筆記內容

2. **前端**：
   - `maskAllText: true`：所有文字都會被遮蔽
   - `blockAllMedia: true`：不記錄圖片和影片
   - 只在錯誤發生時記錄操作流程

### 資料保留

Sentry 免費方案：
- 錯誤事件保留 **30 天**
- 效能事件保留 **30 天**
- 每月 **5,000** 個錯誤事件
- 每月 **10,000** 個效能追蹤事件

如果超過額度，考慮升級到付費方案或調整採樣率。

## 9. 成本估算

### 免費方案

- 5,000 錯誤/月
- 10,000 追蹤/月
- 1 位開發者
- 適合初期使用

### Team 方案（USD 26/月）

- 50,000 錯誤/月
- 100,000 追蹤/月
- 無限開發者
- Email 支援

### Business 方案（USD 80/月）

- 100,000 錯誤/月
- 500,000 追蹤/月
- 優先支援
- 更長的資料保留期

**建議：**先使用免費方案，等流量增加後再升級。

## 10. 最佳實踐

### 錯誤處理

在程式碼中手動捕獲特定錯誤：

```python
# 後端
import sentry_sdk

try:
    # 可能出錯的操作
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)
    # 處理錯誤
```

```javascript
// 前端
import * as Sentry from '@sentry/react'

try {
  // 可能出錯的操作
  riskyOperation()
} catch (error) {
  Sentry.captureException(error)
  // 處理錯誤
}
```

### 自訂上下文

添加額外的錯誤上下文：

```python
# 後端
sentry_sdk.set_user({"id": user.id, "username": user.username})
sentry_sdk.set_tag("feature", "mood_note_export")
sentry_sdk.set_context("export_info", {"format": "pdf", "count": 100})
```

```javascript
// 前端
Sentry.setUser({ id: user.id, username: user.username })
Sentry.setTag('feature', 'mood_note_create')
Sentry.setContext('note_info', { type: 'daily', mood: 'happy' })
```

### 忽略特定錯誤

有些錯誤不需要追蹤（例如網路中斷）：

```python
# backend/moodnotes_pro/settings.py
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        ignore_errors=[
            'ConnectionError',
            'Timeout',
        ],
        # ... 其他配置
    )
```

## 11. 疑難排解

### 問題：Sentry 沒有收到錯誤

**檢查：**
1. 確認 DSN 是否正確設定
2. 確認環境變數是否已載入（`echo $SENTRY_DSN`）
3. 檢查 Sentry SDK 是否已安裝
4. 前端：確認是否在 production 模式（`npm run build && npm run preview`）

### 問題：收到太多錯誤

**解決：**
1. 降低採樣率：`traces_sample_rate=0.05`
2. 設定錯誤過濾規則
3. 修復高頻錯誤

### 問題：超過免費額度

**解決：**
1. 降低採樣率
2. 設定錯誤過濾規則（忽略不重要的錯誤）
3. 升級到付費方案

## 12. 下一步

1. **立即執行：**
   - 註冊 Sentry 帳號
   - 創建兩個專案（backend、frontend）
   - 設定環境變數
   - 測試錯誤捕獲

2. **設定警報：**
   - 設定 Slack 或 Email 通知
   - 設定錯誤閾值警報

3. **定期檢查：**
   - 每週檢查 Sentry 控制台
   - 修復高頻錯誤
   - 監控效能趨勢

## 相關資源

- [Sentry 官方文件](https://docs.sentry.io/)
- [Django 整合指南](https://docs.sentry.io/platforms/python/guides/django/)
- [React 整合指南](https://docs.sentry.io/platforms/javascript/guides/react/)
- [效能監控最佳實踐](https://docs.sentry.io/product/performance/best-practices/)
