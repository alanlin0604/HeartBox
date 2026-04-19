# 睡眠分析 API 文件

## 概述

睡眠分析 API 提供以下功能：
1. 睡眠品質評分（0-100分）
2. 睡眠模式識別（早睡早起、晚睡晚起、不規律）
3. 睡眠與情緒/壓力的關聯分析
4. 睡眠問題識別（失眠、睡眠不足、作息不規律、品質差）
5. 個人化睡眠建議
6. 睡眠趨勢與洞察

## API 端點

### 1. GET /api/sleep/analysis/

綜合睡眠分析 - 包含統計、關聯分析、問題識別和建議。

**Query Parameters:**
- `days` (可選): 分析天數，預設 30

**Response:**
```json
{
  "statistics": {
    "avg_sleep_hours": 7.2,
    "avg_quality_score": 78,
    "most_common_pattern": "early_bird",
    "total_records": 28,
    "sleep_debt": 6.0
  },
  "mood_correlation": {
    "sufficient_sleep_avg_mood": 7.5,
    "insufficient_sleep_avg_mood": 5.2,
    "mood_difference": 2.3,
    "correlation": "positive",
    "sample_size": 25
  },
  "stress_correlation": {
    "sufficient_sleep_avg_stress": 3.1,
    "insufficient_sleep_avg_stress": 6.8,
    "stress_difference": 3.7,
    "correlation": "negative",
    "sample_size": 22
  },
  "issues": [
    {
      "type": "insufficient_sleep",
      "severity": "moderate",
      "description": "平均睡眠時間僅 6.2 小時"
    }
  ],
  "recommendations": [
    "嘗試每天固定時間上床睡覺，建立規律作息",
    "避免睡前 2 小時使用電子產品（藍光會影響褪黑激素分泌）"
  ]
}
```

**欄位說明:**

#### statistics
- `avg_sleep_hours`: 平均睡眠時數
- `avg_quality_score`: 平均睡眠品質分數（0-100）
- `most_common_pattern`: 最常見睡眠模式
  - `early_bird`: 早睡早起（平均 bedtime < 23:00, wake_time < 7:00）
  - `night_owl`: 晚睡晚起（平均 bedtime > 00:30, wake_time > 8:00）
  - `regular`: 一般作息
  - `irregular`: 作息不規律（入睡時間標準差 > 2 小時）
- `total_records`: 睡眠記錄數量
- `sleep_debt`: 睡眠債（相對於建議的 7 小時）
  - 正數 = 多睡
  - 負數 = 欠睡

#### mood_correlation
- `sufficient_sleep_avg_mood`: 睡眠充足日（>=7h）的平均情緒（0-10）
- `insufficient_sleep_avg_mood`: 睡眠不足日（<7h）的平均情緒（0-10）
- `mood_difference`: 情緒差異
- `correlation`: 相關性（"positive" / "negative" / "neutral"）
- `sample_size`: 樣本數

#### stress_correlation
- `sufficient_sleep_avg_stress`: 睡眠充足日的平均壓力（0-10）
- `insufficient_sleep_avg_stress`: 睡眠不足日的平均壓力（0-10）
- `stress_difference`: 壓力差異
- `correlation`: 相關性（"negative" 表示睡眠不足時壓力較高）
- `sample_size`: 樣本數

#### issues
睡眠問題列表，每個問題包含：
- `type`: 問題類型
  - `insomnia`: 失眠（連續多日 < 6h）
  - `insufficient_sleep`: 睡眠不足（平均 < 7h）
  - `irregular_schedule`: 作息不規律
  - `poor_quality`: 睡眠品質差（平均品質分數 < 60）
- `severity`: 嚴重程度（"mild" / "moderate" / "severe"）
- `description`: 問題描述

#### recommendations
個人化睡眠建議列表（最多 5 條）

---

### 2. GET /api/sleep/calendar/

睡眠日曆 - 取得特定日期區間的每日睡眠記錄（含分析欄位）。

**Query Parameters:**
- `start_date` (必填): 開始日期，格式 YYYY-MM-DD
- `end_date` (必填): 結束日期，格式 YYYY-MM-DD

**Response:**
```json
{
  "calendar": [
    {
      "id": 123,
      "date": "2026-04-01",
      "sleep_hours": 7.5,
      "sleep_quality": 4,
      "bedtime": "2026-04-01T23:00:00+08:00",
      "wake_time": "2026-04-02T06:30:00+08:00",
      "deep_sleep_minutes": 90,
      "light_sleep_minutes": 240,
      "rem_sleep_minutes": 120,
      "source": "healthkit",
      "quality_score": 85,
      "sleep_pattern": "early_bird",
      "created_at": "2026-04-02T07:00:00+08:00",
      "updated_at": "2026-04-02T07:00:00+08:00"
    },
    ...
  ]
}
```

**欄位說明:**
- 基本欄位與 DailySleep model 相同
- `quality_score`: 計算的睡眠品質分數（0-100）
- `sleep_pattern`: 當日的睡眠模式（基於最近 7 天）

---

### 3. GET /api/sleep/trends/

睡眠趨勢 - 週度聚合資料，用於圖表呈現。

**Query Parameters:**
- `days` (可選): 分析天數，預設 90

**Response:**
```json
{
  "trends": [
    {
      "week_start": "2026-03-31",
      "avg_sleep_hours": 7.3,
      "avg_quality_score": 75,
      "avg_mood": 6.8
    },
    {
      "week_start": "2026-04-07",
      "avg_sleep_hours": 6.8,
      "avg_quality_score": 68,
      "avg_mood": 5.9
    },
    ...
  ]
}
```

**欄位說明:**
- `week_start`: 該週起始日期（週一）
- `avg_sleep_hours`: 該週平均睡眠時數
- `avg_quality_score`: 該週平均品質分數
- `avg_mood`: 該週平均情緒（需有對應的 MoodNote）

**用途:** 
- 繪製睡眠時數趨勢圖
- 繪製睡眠品質趨勢圖
- 繪製睡眠-情緒關聯圖

---

### 4. GET /api/sleep/insights/

睡眠洞察 - 提供有趣的統計發現和個人化洞察。

**Response:**
```json
{
  "insights": [
    "週末平均多睡 1.2 小時（可能平日睡眠不足）",
    "您在睡眠 7-8h 時情緒最佳（平均 7.5/10）",
    "最長連續優質睡眠記錄：5 天",
    "平均深度睡眠佔比 22.3%（建議 20-25%）"
  ]
}
```

**可能的洞察類型:**
1. 週末 vs 平日睡眠差異
2. 最佳睡眠時數（情緒最好的睡眠時數區間）
3. 連續優質睡眠記錄
4. 深度睡眠佔比分析

---

## 睡眠品質評分標準

睡眠品質分數（0-100）由以下因素決定：

### 1. 睡眠時數（40%）
- 7-9 小時：40 分
- 6-7 或 9-10 小時：30 分
- 5-6 或 10-11 小時：20 分
- 其他：10 分

### 2. 深度睡眠比例（30%）
需有 deep/light/rem 資料：
- 20-25%：30 分
- 15-20% 或 25-30%：20 分
- 其他：10 分

### 3. REM 睡眠比例（20%）
- 20-25%：20 分
- 15-20% 或 25-30%：15 分
- 其他：5 分

### 4. 淺睡眠比例（10%）
- ≤50%：10 分
- >50%：5 分

**註:** 若無 deep/light/rem 資料（手動輸入），僅計算睡眠時數（最高 40 分）。

---

## 資料來源

睡眠資料可來自：
- `manual`: 手動輸入
- `healthkit`: Apple Health（iOS）
- `health_connect`: Health Connect（Android）

來自健康平台的資料通常包含完整的睡眠階段資訊（deep/light/rem），可獲得更準確的品質評分。

---

## 建議使用方式

### 儀表板頁面
```javascript
// 取得綜合分析
const response = await fetch('/api/sleep/analysis/?days=30');
const { statistics, issues, recommendations } = await response.json();

// 顯示統計卡片
display(statistics.avg_sleep_hours, statistics.avg_quality_score);

// 顯示問題提醒
if (issues.length > 0) {
  showWarning(issues);
}

// 顯示建議
showRecommendations(recommendations);
```

### 睡眠日曆
```javascript
// 取得本月睡眠記錄
const startDate = '2026-04-01';
const endDate = '2026-04-30';
const response = await fetch(`/api/sleep/calendar/?start_date=${startDate}&end_date=${endDate}`);
const { calendar } = await response.json();

// 渲染日曆熱力圖
renderCalendarHeatmap(calendar.map(day => ({
  date: day.date,
  value: day.quality_score
})));
```

### 睡眠趨勢圖
```javascript
// 取得近 90 天趨勢
const response = await fetch('/api/sleep/trends/?days=90');
const { trends } = await response.json();

// 繪製折線圖
renderLineChart({
  labels: trends.map(w => w.week_start),
  datasets: [
    { label: '睡眠時數', data: trends.map(w => w.avg_sleep_hours) },
    { label: '品質分數', data: trends.map(w => w.avg_quality_score) }
  ]
});
```

### 睡眠洞察卡片
```javascript
// 取得洞察
const response = await fetch('/api/sleep/insights/');
const { insights } = await response.json();

// 隨機顯示一條洞察
showInsightCard(insights[Math.floor(Math.random() * insights.length)]);
```

---

## 測試

執行測試：
```bash
cd backend
venv/Scripts/python.exe test_sleep_analysis.py
```

測試涵蓋：
- 品質分數計算
- 睡眠模式識別
- 睡眠統計
- 問題識別
- 建議生成
- 情緒關聯分析

---

## 注意事項

1. **時區處理**: 所有 datetime 欄位儲存為 UTC，顯示時會轉換為使用者時區（預設 Asia/Taipei）
2. **資料不足**: 若睡眠記錄少於 3 天，某些分析可能回傳 `insufficient_data` 或 `None`
3. **效能**: `/analysis` 端點會進行複雜計算，建議前端快取結果（例如快取 1 小時）
4. **隱私**: 所有 API 端點都需要認證（JWT token）

---

## 未來擴充

可考慮新增的功能：
- 睡眠目標設定與追蹤
- 與運動數據的關聯分析
- 睡眠週期預測（最佳入睡/起床時間建議）
- 睡眠品質與天氣的關聯
- 社交功能（與好友比較睡眠品質）
