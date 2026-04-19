# 習慣追蹤器 API 文件

## 概述
習慣追蹤器後端 API 已完整實作，包含習慣管理、打卡記錄和情緒關聯分析功能。

## API 端點

### 1. 習慣 CRUD

#### 獲取習慣列表
```
GET /api/habits/
```

**回應範例：**
```json
[
  {
    "id": 1,
    "name": "每日運動",
    "description": "每天至少運動30分鐘",
    "category": "健康",
    "color": "#22c55e",
    "icon": "dumbbell",
    "target_frequency": "daily",
    "target_count": 1,
    "is_active": true,
    "created_at": "2026-04-19T04:00:00Z",
    "updated_at": "2026-04-19T04:00:00Z",
    "streak": 7,
    "completion_rate": 23.3
  }
]
```

#### 建立習慣
```
POST /api/habits/
```

**請求範例：**
```json
{
  "name": "每日閱讀",
  "description": "每天閱讀30分鐘",
  "category": "學習",
  "color": "#3b82f6",
  "icon": "book",
  "target_frequency": "daily",
  "target_count": 1
}
```

#### 更新習慣
```
PUT /api/habits/{id}/
PATCH /api/habits/{id}/
```

#### 刪除習慣
```
DELETE /api/habits/{id}/
```

### 2. 打卡功能

#### 今日打卡
```
POST /api/habits/{id}/check_in/
```

**請求範例：**
```json
{
  "note": "今天跑步5公里，感覺很棒！"
}
```

**回應範例：**
```json
{
  "id": 1,
  "habit": 1,
  "habit_name": "每日運動",
  "completed_at": "2026-04-19T10:30:00Z",
  "date": "2026-04-19",
  "note": "今天跑步5公里，感覺很棒！"
}
```

**錯誤回應（已打卡）：**
```json
{
  "error": "Already checked in today"
}
```

### 3. 打卡日曆

#### 獲取打卡日曆（最近90天）
```
GET /api/habits/{id}/calendar/
```

**回應範例：**
```json
{
  "habit_id": 1,
  "completed_dates": [
    "2026-04-12",
    "2026-04-13",
    "2026-04-14",
    "2026-04-15",
    "2026-04-16",
    "2026-04-17",
    "2026-04-18",
    "2026-04-19"
  ],
  "start_date": "2026-01-19",
  "end_date": "2026-04-19"
}
```

### 4. 習慣與情緒關聯分析

#### 獲取習慣對情緒的影響分析
```
GET /api/habits/analytics/
```

**回應範例：**
```json
[
  {
    "habit_id": 1,
    "habit_name": "每日運動",
    "avg_mood_when_completed": 0.80,
    "avg_mood_when_not_completed": 0.30,
    "mood_difference": 0.50,
    "completion_days": 7
  },
  {
    "habit_id": 2,
    "habit_name": "閱讀",
    "avg_mood_when_completed": 0.65,
    "avg_mood_when_not_completed": 0.40,
    "mood_difference": 0.25,
    "completion_days": 3
  }
]
```

**說明：**
- `avg_mood_when_completed`: 打卡日的平均情緒分數
- `avg_mood_when_not_completed`: 未打卡日的平均情緒分數
- `mood_difference`: 情緒差異（正值表示習慣對情緒有正面影響）
- `completion_days`: 最近30天內的完成天數
- 結果按 `mood_difference` 絕對值降序排列（影響最大的習慣在前）

## 資料模型

### Habit（習慣）
```python
{
  "id": Integer,
  "user": ForeignKey(User),
  "name": String(max_length=100),
  "description": Text,
  "category": String(max_length=50),
  "color": String(max_length=7),  # Hex color code
  "icon": String(max_length=50),
  "target_frequency": String(choices=['daily', 'weekly', 'custom']),
  "target_count": Integer,  # 每週目標次數（weekly 時使用）
  "is_active": Boolean,
  "created_at": DateTime,
  "updated_at": DateTime
}
```

### HabitLog（打卡記錄）
```python
{
  "id": Integer,
  "habit": ForeignKey(Habit),
  "user": ForeignKey(User),
  "completed_at": DateTime,
  "date": Date,  # 用於查詢統計
  "note": Text
}
```

**約束：**
- `unique_together = [['habit', 'date']]` - 每個習慣每天只能打卡一次

## 計算邏輯

### 1. 連續天數（Streak）
從今天往回查詢，連續有打卡記錄的天數。

```python
def get_streak(habit):
    today = timezone.now().date()
    streak = 0
    check_date = today
    
    while HabitLog.exists(habit, check_date):
        streak += 1
        check_date -= timedelta(days=1)
    
    return streak
```

### 2. 完成率（Completion Rate）
最近30天的打卡天數 ÷ 30 × 100%

```python
def get_completion_rate(habit):
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    completed_days = HabitLog.count(
        habit=habit,
        date__gte=start_date,
        date__lte=end_date
    )
    
    return (completed_days / 30) * 100
```

### 3. 情緒關聯分析
比較「打卡日」和「未打卡日」的平均情緒分數。

```python
def analyze_habit_mood_correlation(user, habit):
    # 獲取最近30天的打卡日期
    completed_dates = HabitLog.dates(habit, days=30)
    
    # 打卡日的平均情緒
    avg_mood_completed = MoodNote.average_sentiment(
        user=user,
        dates__in=completed_dates
    )
    
    # 未打卡日的平均情緒
    avg_mood_not_completed = MoodNote.average_sentiment(
        user=user,
        dates__not_in=completed_dates
    )
    
    return {
        'avg_mood_when_completed': avg_mood_completed,
        'avg_mood_when_not_completed': avg_mood_not_completed,
        'mood_difference': avg_mood_completed - avg_mood_not_completed
    }
```

## 測試結果

✅ Models 已建立（Habit, HabitLog）
✅ Serializers 已實作（HabitSerializer, HabitLogSerializer）
✅ ViewSet 已實作（CRUD + check_in + calendar）
✅ Analytics View 已實作（情緒關聯分析）
✅ URLs 已註冊
✅ Migration 已執行
✅ Django check 通過

### 測試數據
- 連續天數計算：正常（7天連續打卡 → streak = 7）
- 完成率計算：正常（7/30 = 23.3%）
- 情緒關聯分析：正常（打卡日 0.80 vs 未打卡日 0.30，差異 0.50）

## 使用範例

### 1. 建立新習慣
```bash
curl -X POST http://localhost:8000/api/habits/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每日冥想",
    "description": "每天冥想10分鐘",
    "category": "健康",
    "color": "#8b5cf6",
    "icon": "meditation"
  }'
```

### 2. 今日打卡
```bash
curl -X POST http://localhost:8000/api/habits/1/check_in/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "note": "今天冥想感覺很平靜"
  }'
```

### 3. 查看習慣列表（含統計）
```bash
curl -X GET http://localhost:8000/api/habits/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 查看情緒關聯分析
```bash
curl -X GET http://localhost:8000/api/habits/analytics/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 注意事項

1. **每日打卡限制**：每個習慣每天只能打卡一次，重複打卡會返回錯誤
2. **時區處理**：使用 Django 的 `timezone.now()` 確保時區正確
3. **權限控制**：所有端點都需要認證（`IsAuthenticated`）
4. **資料隔離**：用戶只能看到自己的習慣和打卡記錄
5. **效能優化**：
   - 使用 Index 加速查詢（user, is_active, date）
   - unique_together 確保資料一致性

## 下一步建議

### 前端整合
1. 建立習慣列表頁面（顯示 streak 和 completion_rate）
2. 建立打卡日曆視圖（使用 calendar API）
3. 建立習慣詳情頁（顯示統計圖表）
4. 建立情緒關聯分析儀表板

### 功能擴展
1. 支援自定義目標頻率（每週 N 次）
2. 新增習慣標籤系統
3. 新增打卡提醒功能
4. 新增習慣分享功能
5. 新增成就系統（連續打卡 7/30/100 天）

### 通知功能
1. 每日打卡提醒
2. 連續天數里程碑通知
3. 週報總結（本週完成率）
