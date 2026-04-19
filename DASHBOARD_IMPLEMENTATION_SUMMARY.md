# 個人化儀表板後端 API 實作摘要

## 📋 實作概述

已成功實作完整的個人化儀表板後端 API，包含：
- 2 個新的 Django Models
- 2 個 Serializers
- 1 個 Service 模組 (12 個函數)
- 5 個 Views (9 個 API 端點)
- 6 個 URL 路由
- 2 個 Admin 介面

---

## 🗂️ 檔案變更清單

### 新增檔案
1. **`backend/api/services/dashboard_service.py`** (423 行)
   - 完整的 dashboard 業務邏輯
   - 12 個服務函數處理不同 widget 資料

2. **`backend/api/migrations/0041_dashboardlayout_usermetric.py`**
   - 資料庫遷移檔

3. **`test_dashboard_endpoints.md`**
   - API 端點測試文件

### 修改檔案
1. **`backend/api/models.py`**
   - 新增 `DashboardLayout` model (17 行)
   - 新增 `UserMetric` model (26 行)

2. **`backend/api/serializers.py`**
   - 新增 `DashboardLayoutSerializer` (34 行)
   - 新增 `UserMetricSerializer` (20 行)
   - 更新 imports

3. **`backend/api/views.py`**
   - 新增 5 個 View classes (約 180 行)
   - 更新 imports

4. **`backend/api/urls.py`**
   - 新增 6 個 URL patterns
   - 更新 imports

5. **`backend/api/admin.py`**
   - 新增 `DashboardLayoutAdmin`
   - 新增 `UserMetricAdmin`
   - 更新 imports

---

## 📊 Model 設計

### 1. DashboardLayout
```python
class DashboardLayout(models.Model):
    user = models.OneToOneField(...)  # 一對一關聯
    layout_config = models.JSONField(default=dict)  # 彈性佈局儲存
    updated_at = models.DateTimeField(auto_now=True)
```

**特點:**
- OneToOne 關係，每個用戶一個佈局
- JSONField 儲存 widgets 陣列
- 自動記錄更新時間

### 2. UserMetric
```python
class UserMetric(models.Model):
    user = models.ForeignKey(...)
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPE_CHOICES)
    target_value = models.FloatField()
    current_value = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
```

**特點:**
- unique_together 防止重複 metric_type
- 6 種預定義 metric_type
- 自動計算 current_value

**支援的 Metric Types:**
1. `daily_entries` - 每週日記筆數
2. `avg_mood` - 平均心情分數 (0-10)
3. `streak_days` - 連續記錄天數
4. `habit_completion` - 習慣完成率 (%)
5. `sleep_hours` - 平均睡眠時數
6. `exercise_minutes` - 平均運動分鐘數

---

## 🔧 Service Layer 設計

### 核心函數

#### 1. `get_default_layout()`
回傳預設的 6 個 widget 配置。

#### 2. `get_widget_data(user, widget_id)`
根據 widget_id 分發到對應的資料處理函數。

**支援的 Widgets:**
- `streak` - 連續記錄統計
- `mood_trends` - 最近 7 天心情趨勢
- `on_this_day` - 歷史的今天 (最多 5 筆)
- `habit_checkin` - 今日習慣打卡狀態
- `ai_suggestions` - AI 智能建議 (最多 3 條)
- `sleep_stats` - 最近 7 天睡眠統計

#### 3. `update_metric_current_value(user, metric_type)`
根據 metric_type 計算最新的 current_value。

### Widget 資料處理函數

#### `_get_streak_data(user)`
- 來源: `JournalStreak` model
- 回傳: current_streak, longest_streak, total_entries

#### `_get_mood_trends_data(user)`
- 來源: `MoodNote` model (sentiment_score)
- 回傳: 7 天的日期、心情分數、平均值
- 轉換: sentiment (-1~1) → mood (0~10)

#### `_get_on_this_day_data(user)`
- 來源: `MoodNote` model (歷史同一天)
- 回傳: 最多 5 筆歷史記錄
- 排除: 當年的記錄

#### `_get_habit_checkin_data(user)`
- 來源: `Habit` + `HabitLog` models
- 回傳: 所有啟用習慣的今日完成狀態
- 計算: 完成數、總數、完成率、各習慣 streak

#### `_get_ai_suggestions_data(user)`
- 來源: 分析最近 7 天的心情和壓力
- 回傳: 最多 3 條建議
- 類型: mood (低落)、stress (高壓)、streak (中斷)

#### `_get_sleep_stats_data(user)`
- 來源: `DailySleep` model
- 回傳: 7 天的日期、睡眠時數、品質、平均值

### Metric 計算函數

每個 metric_type 都有對應的計算函數：
- `_calculate_daily_entries()` - 最近 7 天筆數
- `_calculate_avg_mood()` - 最近 7 天平均心情 (0-10)
- `_calculate_streak_days()` - 當前連續天數
- `_calculate_habit_completion()` - 最近 7 天完成率
- `_calculate_sleep_hours()` - 最近 7 天平均睡眠
- `_calculate_exercise_minutes()` - 最近 7 天平均運動

---

## 🌐 API 端點設計

### 1. Dashboard Layout APIs

#### GET `/api/dashboard/layout/`
- 取得用戶佈局（無設定則回傳預設）
- 自動使用 OneToOne 關聯

#### PUT `/api/dashboard/layout/`
- 更新/建立佈局
- 包含 JSON 結構驗證

#### POST `/api/dashboard/layout/reset/`
- 重置為預設佈局
- 使用 `update_or_create`

### 2. User Metrics APIs

#### GET `/api/dashboard/metrics/`
- 列出所有自訂指標
- 包含計算後的 progress

#### POST `/api/dashboard/metrics/`
- 建立新指標
- 自動計算初始 current_value
- 處理 unique_together 錯誤

#### PATCH `/api/dashboard/metrics/{id}/`
- 更新 target_value 或 is_active
- 自動重新計算 current_value
- 驗證用戶所有權

#### DELETE `/api/dashboard/metrics/{id}/`
- 刪除指標
- 驗證用戶所有權

### 3. Widget Data API

#### GET `/api/dashboard/widget-data/{widget_id}/`
- 動態回傳不同 widget 的資料
- 驗證 widget_id 有效性
- 錯誤處理與日誌記錄

### 4. Metrics Refresh API

#### POST `/api/dashboard/metrics/refresh/`
- 批次更新所有啟用指標的 current_value
- 回傳更新數量
- 個別錯誤不影響其他指標

---

## ✅ 驗證與測試

### Django Checks
```bash
System check identified no issues (0 silenced).
```

### Migration
```bash
Migrations for 'api':
  api\migrations\0041_dashboardlayout_usermetric.py
    + Create model DashboardLayout
    + Create model UserMetric
```

### 功能測試
已透過 Django shell 驗證：
- ✅ 建立/更新 DashboardLayout
- ✅ 建立/更新 UserMetric
- ✅ get_default_layout() 正常運作
- ✅ get_widget_data() 所有 6 個 widgets
- ✅ update_metric_current_value() 計算正確

---

## 🎯 Serializer 驗證邏輯

### DashboardLayoutSerializer
```python
def validate_layout_config(self, value):
    # 檢查必要欄位: widgets
    # 驗證每個 widget 包含: id, x, y, w, h, enabled
    # 驗證資料型別: id (str), enabled (bool), 位置/大小 (number)
```

### UserMetricSerializer
```python
def validate_target_value(self, value):
    # target_value 必須 > 0
    
def get_progress(self, obj):
    # 計算進度百分比 (current/target * 100)
```

---

## 🔒 權限與安全

### 所有端點
- `permission_classes = [permissions.IsAuthenticated]`
- 需要有效的 JWT token

### 資料隔離
- 所有查詢自動過濾 `user=request.user`
- PATCH/DELETE 驗證資源所有權
- unique_together 防止資料衝突

---

## 📈 效能考量

### 查詢優化
- 使用 `.aggregate()` 減少資料庫查詢
- Widget data 預先計算並快取 (future enhancement)
- 批次更新 metrics (refresh endpoint)

### 索引
```python
# DashboardLayout
models.Index(fields=['user'])

# UserMetric
models.Index(fields=['user', 'is_active'])
unique_together = [['user', 'metric_type']]
```

---

## 🎨 Admin 介面

### DashboardLayoutAdmin
- 顯示: user, updated_at
- 搜尋: username
- 唯讀: updated_at

### UserMetricAdmin
- 顯示: user, metric_type, target_value, current_value, is_active
- 篩選: metric_type, is_active
- 搜尋: username
- 唯讀: created_at, updated_at

---

## 🚀 部署注意事項

### Migration
執行以下指令：
```bash
python manage.py migrate
```

### 靜態檔案
無新增靜態檔案需求。

### 環境變數
無需新增環境變數。

### 資料庫
- 新增 2 個資料表
- 新增 3 個索引
- 支援 PostgreSQL JSON 查詢

---

## 📝 未來優化建議

### 1. 快取機制
```python
# 在 get_widget_data 中加入快取
@cache.cache_page(60 * 5)  # 5 分鐘
def get_widget_data(user, widget_id):
    ...
```

### 2. 背景任務
```python
# 定期更新所有用戶的 metrics
@celery.task
def refresh_all_metrics():
    for user in User.objects.filter(is_active=True):
        for metric in user.custom_metrics.filter(is_active=True):
            update_metric_current_value(user, metric.metric_type)
```

### 3. WebSocket 即時更新
```python
# 當有新日記/習慣記錄時，即時推送更新
async def notify_dashboard_update(user_id, widget_id):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'dashboard_{user_id}',
        {'type': 'widget_update', 'widget_id': widget_id}
    )
```

### 4. Widget 擴充性
```python
# 支援用戶自訂 widget
class CustomWidget(models.Model):
    user = models.ForeignKey(...)
    widget_type = models.CharField(...)
    config = models.JSONField()
    data_source = models.CharField(...)
```

---

## 📚 相關文件

- API 測試文件: `test_dashboard_endpoints.md`
- Model 設計: `backend/api/models.py` (L963-1020)
- Service 邏輯: `backend/api/services/dashboard_service.py`
- URL 配置: `backend/api/urls.py` (L231-236)

---

## ✨ 完成檢核

- ✅ Model 設計符合需求
- ✅ Migration 執行成功
- ✅ Serializer 包含驗證邏輯
- ✅ Service 層處理業務邏輯
- ✅ Views 正確呼叫 service
- ✅ URLs 已註冊
- ✅ Django check 通過
- ✅ Admin 介面完整
- ✅ 功能測試通過
- ✅ 文件完整

---

**實作完成時間:** 2026-04-19
**總程式碼行數:** ~700 行
**測試狀態:** ✅ 通過
