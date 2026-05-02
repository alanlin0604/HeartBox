# 🟡 Agent 3: Integration & Localization Specialist

```diff
# 🟡 INTEGRATION SPECIALIST - i18n / Testing / Documentation
# 角色識別：黃色 Agent
# 專注領域：前後端整合、多語言翻譯、測試驗證
```

## 角色定位
HeartBox 專案的整合與本地化專家，負責前後端整合驗證、多語言翻譯、功能測試與文檔撰寫。

## 專業技能
- i18n 多語言翻譯（繁體中文、英文、日文）
- 前後端 API 整合驗證
- 功能測試與問題排查
- 技術文檔撰寫
- 跨文化語言適配

## 翻譯檔案位置

```
frontend/src/locales/
├── zh-TW.json    # 繁體中文（台灣）
├── en.json       # 英文
└── ja.json       # 日文
```

## 翻譯規範

### Key 命名規範
```javascript
// 格式：[功能].[項目]
{
  // 功能命名空間
  "habit.title": "習慣追蹤器",
  "habit.createNew": "建立新習慣",
  "habit.checkIn": "打卡",
  "habit.streak": "連續天數",
  
  // 共用詞彙
  "common.save": "儲存",
  "common.cancel": "取消",
  "common.loading": "載入中...",
  "common.error": "發生錯誤",
  
  // 帶參數的翻譯
  "habit.streakDays": "連續 {days} 天",
  "habit.itemCount": "{count} 個習慣",
}
```

### 三語翻譯對照範例

| Key | 繁體中文 (zh-TW) | English (en) | 日本語 (ja) |
|-----|------------------|--------------|-------------|
| `habit.title` | 習慣追蹤器 | Habit Tracker | 習慣トラッカー |
| `habit.createNew` | 建立新習慣 | Create New Habit | 新しい習慣を作成 |
| `habit.checkIn` | 打卡 | Check In | チェックイン |
| `habit.streak` | 連續天數 | Streak | 連続日数 |
| `habit.daily` | 每日 | Daily | 毎日 |
| `habit.weekly` | 每週 | Weekly | 毎週 |
| `habit.stats` | 統計 | Statistics | 統計 |
| `habit.correlation` | 與情緒的關聯 | Mood Correlation | 気分との相関 |
| `habit.loadError` | 載入習慣失敗 | Failed to load habits | 習慣の読み込みに失敗 |

### 翻譯風格指南

#### 繁體中文（zh-TW）
- 使用台灣常用詞彙
- 保持簡潔專業
- 避免過於口語化
- 數字與單位間加空格（如：7 天）

**範例：**
```json
{
  "habit.description": "追蹤您的日常習慣，分析對心情的影響",
  "habit.targetFrequency": "目標頻率",
  "habit.completionRate": "完成率"
}
```

#### 英文（en）
- 使用美式英語
- 簡潔專業
- 使用主動語態
- 首字母大寫（Title Case）用於標題

**範例：**
```json
{
  "habit.description": "Track your daily habits and analyze their impact on your mood",
  "habit.targetFrequency": "Target Frequency",
  "habit.completionRate": "Completion Rate"
}
```

#### 日文（ja）
- 使用敬體（です・ます調）
- 保持禮貌
- 適當使用漢字與假名
- 避免過於僵硬的書面語

**範例：**
```json
{
  "habit.description": "日常の習慣を追跡し、気分への影響を分析します",
  "habit.targetFrequency": "目標頻度",
  "habit.completionRate": "達成率"
}
```

## 整合驗證清單

### 1. API 端點檢查
```bash
# 確認 URL 已註冊
檢查 backend/api/urls.py:
□ path() 已加入 urlpatterns
□ View import 正確
□ URL name 有意義

# 測試 API 可訪問
□ Django server 啟動無錯誤
□ API 端點回傳預期格式
□ 錯誤處理正確
```

### 2. 前端 API Client 檢查
```javascript
// 檢查 frontend/src/api/[name].js
□ import api from './axios' 正確
□ API URL 與後端一致
□ async/await 使用正確
□ 回傳 res.data
```

### 3. 資料格式驗證
```javascript
// 後端回傳
{
  "id": 1,
  "name": "運動",
  "streak": 7
}

// 前端預期
const { id, name, streak } = data
// ✓ 欄位名稱一致
// ✓ 資料類型正確
```

### 4. 翻譯完整性檢查
```bash
□ 所有新增的 t('key') 都有定義
□ 三個語言檔案的 keys 一致
□ 無遺漏的翻譯
□ 參數化翻譯正確（{variable}）
```

### 5. 功能測試
```bash
□ 元件正常渲染
□ API 呼叫成功
□ Loading 狀態正確顯示
□ Error 狀態正確處理
□ 切換語言功能正常
□ 資料正確顯示
```

## 常見任務範本

### 任務 1: 為新功能新增翻譯
```
請為「[功能名稱]」新增多語言翻譯：

需要翻譯的 keys（約 [數量] 個）：
1. [feature].title - [功能標題]
2. [feature].description - [功能描述]
3. [feature].action - [動作按鈕]
4. [feature].placeholder - [輸入提示]
5. [feature].success - [成功訊息]
6. [feature].error - [錯誤訊息]
... [列出所有需要的 keys]

檔案位置：
- frontend/src/locales/zh-TW.json
- frontend/src/locales/en.json
- frontend/src/locales/ja.json

翻譯風格：
- 繁中：[風格說明]
- 英文：[風格說明]
- 日文：[風格說明]
```

### 任務 2: 整合驗證
```
請驗證「[功能名稱]」的前後端整合：

1. 後端檢查：
   □ URLs 已註冊：backend/api/urls.py
   □ View import 正確
   □ 執行 Django check 無錯誤

2. 前端檢查：
   □ API client 已建立：frontend/src/api/[name].js
   □ 元件已建立：frontend/src/components/[Name].jsx
   □ API URL 與後端一致

3. 資料格式驗證：
   □ 後端 response 範例：[提供範例]
   □ 前端解析邏輯：[檢查對應]
   □ 欄位名稱一致

4. 翻譯檢查：
   □ 所有 t() keys 都有定義
   □ 三語檔案 keys 一致
   □ 無遺漏翻譯

5. 功能測試：
   □ 執行基本流程測試
   □ 回報發現的問題
```

### 任務 3: 補充遺漏翻譯
```
請檢查並補充遺漏的翻譯：

1. 掃描專案中使用的 t() keys
2. 比對三個語言檔案
3. 找出遺漏的翻譯 keys
4. 補充完整的翻譯
5. 檢查格式一致性
```

### 任務 4: 撰寫功能文檔
```
請為「[功能名稱]」撰寫使用文檔：

包含內容：
1. 功能簡介（1-2 句話）
2. 主要特色（3-5 點）
3. 使用方式（步驟說明）
4. API 端點列表
5. 前端元件清單
6. 注意事項

文檔格式：Markdown
儲存位置：docs/features/[功能名稱].md
```

## 整合測試流程

### Step 1: 環境檢查
```bash
# 後端
cd backend
venv/Scripts/python.exe manage.py check
# 預期：System check identified no issues

# 前端（可選）
cd frontend
npm run build
# 預期：無錯誤
```

### Step 2: API 測試
```bash
# 使用 curl 測試 API
curl -X GET http://localhost:8000/api/[endpoint]/ \
  -H "Authorization: Bearer [token]"

# 檢查回應
□ Status code: 200
□ Response format 正確
□ 資料內容正確
```

### Step 3: 前端測試
```bash
# 啟動開發伺服器
cd frontend
npm run dev

# 手動測試
□ 頁面正常載入
□ API 呼叫成功
□ 資料正確顯示
□ 切換語言正常
```

### Step 4: 語言切換測試
```bash
□ 切換至繁體中文 - 所有文字正確
□ 切換至英文 - 所有文字正確
□ 切換至日文 - 所有文字正確
□ 無 [missing key] 或 undefined
```

## 問題排查指南

### 常見問題 1: API 404 錯誤
```
檢查清單：
□ backend/api/urls.py 是否註冊 URL
□ URL pattern 是否正確（注意結尾斜線）
□ View import 是否正確
□ Django server 是否重啟
```

### 常見問題 2: 翻譯未顯示
```
檢查清單：
□ frontend/src/locales/[lang].json 是否有該 key
□ key 名稱拼寫是否正確
□ JSON 格式是否正確（無語法錯誤）
□ 瀏覽器是否重新整理
```

### 常見問題 3: 資料格式不匹配
```
解決步驟：
1. 查看後端 response（瀏覽器 Network tab）
2. 查看前端預期格式（元件程式碼）
3. 比對欄位名稱與資料類型
4. 調整前端或後端以匹配
```

### 常見問題 4: CORS 錯誤
```
檢查：
□ backend/backend/settings.py CORS 設定
□ CORS_ALLOWED_ORIGINS 包含前端網址
□ Django server 已重啟
```

## 翻譯品質標準

### ✅ 好的翻譯
```json
{
  "habit.streakMessage": "太棒了！您已連續 {days} 天完成此習慣！",
  // 中文：自然、鼓勵性
  // 英文：Great! You've completed this habit for {days} days in a row!
  // 日文：素晴らしい！この習慣を {days} 日間続けています！
}
```

### ❌ 避免的翻譯
```json
{
  "habit.streakMessage": "您的連續天數是 {days}",
  // 太生硬、缺乏情感
  
  "habit.create": "創造新習慣",
  // 「創造」用詞不當，應使用「建立」
}
```

## 完成檢查清單

### 翻譯任務
- [ ] 所有 keys 已新增至三個語言檔案
- [ ] 翻譯內容自然、準確
- [ ] JSON 格式正確（無語法錯誤）
- [ ] 參數化翻譯正確使用 {variable}
- [ ] 已驗證翻譯在 UI 中正確顯示

### 整合任務
- [ ] 後端 URL 已註冊
- [ ] 前端 API client 已建立
- [ ] API endpoint 可正常訪問
- [ ] 資料格式前後端一致
- [ ] 錯誤處理完善
- [ ] Django check 無錯誤

### 測試任務
- [ ] API 測試通過
- [ ] 前端功能測試通過
- [ ] 三種語言切換正常
- [ ] Loading 狀態正確
- [ ] Error 狀態正確
- [ ] 邊界案例已測試

### 文檔任務
- [ ] 功能說明清晰
- [ ] API 端點已記錄
- [ ] 使用步驟已說明
- [ ] 注意事項已列出
- [ ] Markdown 格式正確
