# Dashboard API 端點測試指南

## 已實作的 API 端點

### 1. GET /api/dashboard/layout/
取得用戶儀表板佈局設定（如無設定則回傳預設值）

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/layout/
```

**Response (預設佈局):**
```json
{
  "layout_config": {
    "widgets": [
      {"id": "streak", "x": 0, "y": 0, "w": 4, "h": 2, "enabled": true},
      {"id": "mood_trends", "x": 4, "y": 0, "w": 8, "h": 4, "enabled": true},
      {"id": "on_this_day", "x": 0, "y": 2, "w": 4, "h": 3, "enabled": true},
      {"id": "habit_checkin", "x": 4, "y": 4, "w": 4, "h": 3, "enabled": true},
      {"id": "ai_suggestions", "x": 8, "y": 4, "w": 4, "h": 3, "enabled": true},
      {"id": "sleep_stats", "x": 0, "y": 5, "w": 4, "h": 2, "enabled": false}
    ]
  },
  "updated_at": null
}
```

---

### 2. PUT /api/dashboard/layout/
更新用戶儀表板佈局

**Request:**
```bash
curl -X PUT \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "layout_config": {
      "widgets": [
        {"id": "streak", "x": 0, "y": 0, "w": 6, "h": 2, "enabled": true},
        {"id": "mood_trends", "x": 6, "y": 0, "w": 6, "h": 3, "enabled": true}
      ]
    }
  }' \
  http://localhost:8000/api/dashboard/layout/
```

**Response:**
```json
{
  "layout_config": {
    "widgets": [...]
  },
  "updated_at": "2026-04-19T10:30:00Z"
}
```

---

### 3. POST /api/dashboard/layout/reset/
重置為預設佈局

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/layout/reset/
```

**Response:**
```json
{
  "message": "Dashboard layout reset to default",
  "data": {
    "layout_config": {...},
    "updated_at": "2026-04-19T10:35:00Z"
  }
}
```

---

### 4. GET /api/dashboard/metrics/
取得用戶所有自訂指標

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/metrics/
```

**Response:**
```json
{
  "metrics": [
    {
      "id": 1,
      "metric_type": "daily_entries",
      "target_value": 7.0,
      "current_value": 5.0,
      "progress": 71.4,
      "is_active": true,
      "created_at": "2026-04-15T10:00:00Z",
      "updated_at": "2026-04-19T10:00:00Z"
    }
  ]
}
```

---

### 5. POST /api/dashboard/metrics/
建立新的自訂指標

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_type": "streak_days",
    "target_value": 30.0,
    "is_active": true
  }' \
  http://localhost:8000/api/dashboard/metrics/
```

**Response:**
```json
{
  "id": 2,
  "metric_type": "streak_days",
  "target_value": 30.0,
  "current_value": 15.0,
  "progress": 50.0,
  "is_active": true,
  "created_at": "2026-04-19T10:40:00Z",
  "updated_at": "2026-04-19T10:40:00Z"
}
```

**可用的 metric_type:**
- `daily_entries` - 每週日記筆數
- `avg_mood` - 平均心情分數
- `streak_days` - 連續天數
- `habit_completion` - 習慣完成率
- `sleep_hours` - 平均睡眠時數
- `exercise_minutes` - 平均運動時間

---

### 6. PATCH /api/dashboard/metrics/{id}/
更新指標目標值或啟用狀態

**Request:**
```bash
curl -X PATCH \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "target_value": 10.0,
    "is_active": true
  }' \
  http://localhost:8000/api/dashboard/metrics/1/
```

**Response:**
```json
{
  "id": 1,
  "metric_type": "daily_entries",
  "target_value": 10.0,
  "current_value": 5.0,
  "progress": 50.0,
  "is_active": true,
  "created_at": "2026-04-15T10:00:00Z",
  "updated_at": "2026-04-19T10:45:00Z"
}
```

---

### 7. DELETE /api/dashboard/metrics/{id}/
刪除自訂指標

**Request:**
```bash
curl -X DELETE \
  -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/metrics/1/
```

**Response:** `204 No Content`

---

### 8. GET /api/dashboard/widget-data/{widget_id}/
取得特定 Widget 的資料

#### 8.1 Streak Widget

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/widget-data/streak/
```

**Response:**
```json
{
  "current_streak": 15,
  "longest_streak": 30,
  "total_entries": 245
}
```

#### 8.2 Mood Trends Widget (最近 7 天)

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/widget-data/mood_trends/
```

**Response:**
```json
{
  "dates": ["2026-04-13", "2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17", "2026-04-18", "2026-04-19"],
  "mood_scores": [7.5, 6.2, 8.1, 7.8, null, 8.5, 7.2],
  "avg_mood": 7.6
}
```

#### 8.3 On This Day Widget

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/widget-data/on_this_day/
```

**Response:**
```json
{
  "memories": [
    {
      "id": 123,
      "date": "2025-04-19",
      "year": 2025,
      "preview": "Today was a great day...",
      "sentiment_score": 0.8
    }
  ],
  "count": 1
}
```

#### 8.4 Habit Check-in Widget

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/widget-data/habit_checkin/
```

**Response:**
```json
{
  "habits": [
    {
      "id": 1,
      "name": "Morning Exercise",
      "color": "#8b5cf6",
      "icon": "dumbbell",
      "completed": true,
      "current_streak": 7
    }
  ],
  "completed_count": 3,
  "total_count": 5,
  "completion_rate": 60.0
}
```

#### 8.5 AI Suggestions Widget

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/widget-data/ai_suggestions/
```

**Response:**
```json
{
  "suggestions": [
    {
      "type": "mood",
      "title": "Low mood detected",
      "message": "Your recent entries show lower mood. Consider trying mindfulness exercises.",
      "action": "view_courses"
    }
  ],
  "count": 1
}
```

#### 8.6 Sleep Stats Widget

**Request:**
```bash
curl -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/widget-data/sleep_stats/
```

**Response:**
```json
{
  "dates": ["2026-04-13", "2026-04-14", "2026-04-15", "2026-04-16", "2026-04-17", "2026-04-18", "2026-04-19"],
  "hours": [7.5, 6.8, 8.2, 7.1, 6.5, 8.0, 7.3],
  "quality": [4, 3, 5, 4, 3, 5, 4],
  "avg_hours": 7.3,
  "avg_quality": 4.0,
  "record_count": 7
}
```

**可用的 widget_id:**
- `streak` - 連續記錄統計
- `mood_trends` - 心情趨勢圖
- `on_this_day` - 歷史的今天
- `habit_checkin` - 習慣打卡
- `ai_suggestions` - AI 建議
- `sleep_stats` - 睡眠統計

---

### 9. POST /api/dashboard/metrics/refresh/
重新計算所有啟用指標的當前值

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer {access_token}" \
  http://localhost:8000/api/dashboard/metrics/refresh/
```

**Response:**
```json
{
  "message": "Refreshed 3 metrics",
  "updated_count": 3
}
```

---

## 錯誤回應

### 400 Bad Request - 無效的 widget_id
```json
{
  "error": "Invalid widget_id. Must be one of: streak, mood_trends, on_this_day, habit_checkin, ai_suggestions, sleep_stats"
}
```

### 400 Bad Request - 重複的 metric_type
```json
{
  "error": "You already have a metric of this type"
}
```

### 400 Bad Request - 無效的 layout_config
```json
{
  "layout_config": [
    "Missing 'widgets' key in layout_config"
  ]
}
```

### 404 Not Found - 指標不存在
```json
{
  "error": "Metric not found"
}
```

---

## 測試步驟

1. **登入取得 access_token:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "testpass123"}'
   ```

2. **取得預設佈局:**
   ```bash
   curl -H "Authorization: Bearer {access_token}" \
     http://localhost:8000/api/dashboard/layout/
   ```

3. **建立自訂指標:**
   ```bash
   curl -X POST http://localhost:8000/api/dashboard/metrics/ \
     -H "Authorization: Bearer {access_token}" \
     -H "Content-Type: application/json" \
     -d '{"metric_type": "daily_entries", "target_value": 7.0}'
   ```

4. **取得 widget 資料:**
   ```bash
   curl -H "Authorization: Bearer {access_token}" \
     http://localhost:8000/api/dashboard/widget-data/streak/
   ```

---

## 完成狀態

✅ Model 設計符合需求 (DashboardLayout, UserMetric)
✅ Migration 執行成功 (0041_dashboardlayout_usermetric.py)
✅ Serializer 包含驗證邏輯 (DashboardLayoutSerializer, UserMetricSerializer)
✅ Service 層處理業務邏輯 (dashboard_service.py)
✅ Views 正確呼叫 service (9個 API 端點)
✅ URLs 已註冊 (6個路由)
✅ Django check 通過 (無錯誤)
✅ Admin 介面已註冊 (DashboardLayoutAdmin, UserMetricAdmin)
✅ 功能測試通過

## 架構說明

### Models
- `DashboardLayout`: OneToOne 關聯用戶，儲存 JSONField 佈局配置
- `UserMetric`: ForeignKey 關聯用戶，unique_together 防止重複

### Service Layer
- `get_default_layout()`: 回傳預設佈局
- `get_widget_data(user, widget_id)`: 取得 widget 資料
- `update_metric_current_value(user, metric_type)`: 更新指標當前值

### Views
- `DashboardLayoutView`: GET/PUT 佈局
- `DashboardLayoutResetView`: POST 重置佈局
- `UserMetricListView`: GET/POST 指標列表
- `UserMetricDetailView`: PATCH/DELETE 單一指標
- `DashboardWidgetDataView`: GET widget 資料
- `UserMetricRefreshView`: POST 刷新所有指標

### Widget Data Integration
所有 widget 都整合現有功能的資料：
- Streak → JournalStreak model
- Mood Trends → MoodNote sentiment_score
- Habit Check-in → Habit + HabitLog models
- On This Day → MoodNote 歷史記錄
- AI Suggestions → 基於最近心情和壓力分析
- Sleep Stats → DailySleep model
