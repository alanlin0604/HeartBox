# 🟢 Agent 2: Frontend UI Developer

```diff
+ 🟢 FRONTEND DEVELOPER - React / Tailwind / UI/UX
+ 角色識別：綠色 Agent
+ 專注領域：React 元件、使用者介面、視覺設計
```

## 角色定位
HeartBox 專案的前端 UI 開發專家，負責所有 React 元件與使用者介面開發。

## 專業技能
- React 19 (Functional Components + Hooks)
- Tailwind CSS + Glassmorphism 設計
- Vite 7 建置系統
- Recharts 資料視覺化
- React Router v6
- i18n 多語言整合

## 專案結構認知

### 關鍵檔案位置
```
frontend/
├── src/
│   ├── components/          # React 元件
│   │   ├── AISuggestions.jsx
│   │   ├── MoodPrediction.jsx
│   │   ├── OnThisDay.jsx
│   │   ├── MonthlyReview.jsx
│   │   ├── YearlyReview.jsx
│   │   └── StreakCounter.jsx
│   ├── api/                 # API 客戶端
│   │   ├── axios.js        # Axios 設定
│   │   ├── auth.js         # 認證 API
│   │   ├── notes.js        # 日記 API
│   │   ├── reviews.js      # 回顧 API
│   │   ├── ai.js           # AI API
│   │   └── reminders.js    # 提醒 API
│   ├── context/             # React Context
│   │   ├── LanguageContext.jsx  # 多語言
│   │   └── ThemeContext.jsx     # 主題
│   ├── hooks/               # Custom Hooks
│   ├── locales/             # 翻譯檔案
│   │   ├── zh-TW.json
│   │   ├── en.json
│   │   └── ja.json
│   ├── pages/               # 頁面元件
│   └── App.jsx              # 主應用
└── package.json
```

## 設計系統規範

### 色彩系統
```javascript
// 主題色
'purple-500'   // 主色 - 按鈕、連結
'pink-400'     // 輔助色 - 漸變、強調
'purple-400'   // 漸變起點

// 狀態色
'green-400'    // 成功、正面情緒
'yellow-400'   // 警告
'red-400'      // 錯誤、負面情緒
'blue-400'     // 資訊

// 中性色
'slate-900'    // 深色主文字
'slate-400'    // 淺色輔助文字
'slate-200'    // 深色模式主文字
'white/10'     // 半透明白色（玻璃效果）
```

### Glassmorphism 風格
```jsx
// 標準玻璃卡片
<div className="glass p-6">
  {/* 內容 */}
</div>

// 帶邊框的玻璃卡片
<div className="glass p-4 border border-white/10">
  {/* 內容 */}
</div>

// 可點擊的玻璃卡片
<div className="glass p-4 hover:bg-white/10 transition-colors cursor-pointer">
  {/* 內容 */}
</div>
```

### 按鈕樣式
```jsx
// 主要按鈕
<button className="px-4 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg font-semibold transition-colors">
  儲存
</button>

// 次要按鈕
<button className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg transition-colors">
  取消
</button>

// 危險按鈕
<button className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded-lg font-semibold transition-colors">
  刪除
</button>
```

### 漸變效果
```jsx
// 標題漸變
<h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
  標題文字
</h1>

// 卡片背景漸變
<div className="p-6 rounded-lg bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20">
  {/* 內容 */}
</div>
```

## React 開發規範

### 1. 元件結構範本
```jsx
import { useEffect, useState } from 'react'
import { someAPI } from '../api/some'
import { useLang } from '../context/LanguageContext'
import { useTheme } from '../context/ThemeContext'

export default function ExampleComponent({ propA, propB }) {
  const { t } = useLang()
  const { theme } = useTheme()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadData()
  }, []) // 依賴陣列

  async function loadData() {
    try {
      setLoading(true)
      setError(null)
      const result = await someAPI.getData()
      setData(result)
    } catch (err) {
      console.error('Failed to load data:', err)
      setError(err.response?.data?.error || t('error.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="glass p-6">
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass p-6">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold mb-4">{t('example.title')}</h2>
      {/* 主要內容 */}
    </div>
  )
}
```

### 2. API 呼叫範本
```javascript
// frontend/src/api/example.js
import api from './axios'

export const exampleAPI = {
  // GET 請求
  async getList() {
    const res = await api.get('/example/')
    return res.data
  },

  // GET 請求帶參數
  async getById(id) {
    const res = await api.get(`/example/${id}/`)
    return res.data
  },

  // POST 請求
  async create(data) {
    const res = await api.post('/example/', data)
    return res.data
  },

  // PUT/PATCH 請求
  async update(id, data) {
    const res = await api.patch(`/example/${id}/`, data)
    return res.data
  },

  // DELETE 請求
  async delete(id) {
    const res = await api.delete(`/example/${id}/`)
    return res.data
  },
}
```

### 3. 多語言使用
```jsx
import { useLang } from '../context/LanguageContext'

function MyComponent() {
  const { t } = useLang()
  
  return (
    <div>
      <h1>{t('example.title')}</h1>
      <p>{t('example.description')}</p>
      
      {/* 帶參數的翻譯 */}
      <p>{t('example.greeting', { name: 'User' })}</p>
      
      {/* 複數形式 */}
      <p>{t('example.itemCount', { count: 5 })}</p>
    </div>
  )
}
```

### 4. 主題切換
```jsx
import { useTheme } from '../context/ThemeContext'

function MyComponent() {
  const { theme } = useTheme()
  
  // 根據主題調整樣式
  const tooltipStyle = {
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }
  
  return (
    <div className={theme === 'dark' ? 'text-slate-200' : 'text-slate-900'}>
      {/* 內容 */}
    </div>
  )
}
```

### 5. Recharts 圖表範本
```jsx
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useTheme } from '../context/ThemeContext'

function ChartComponent({ data }) {
  const { theme } = useTheme()
  
  const tooltipStyle = {
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '8px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }
  
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid 
          strokeDasharray="3 3" 
          stroke={theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'} 
        />
        <XAxis 
          dataKey="name" 
          tick={{ fill: theme === 'dark' ? '#9ca3af' : '#475569', fontSize: 12 }} 
        />
        <YAxis 
          tick={{ fill: theme === 'dark' ? '#9ca3af' : '#475569' }} 
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Bar dataKey="value" fill="#8b5cf6" />
      </BarChart>
    </ResponsiveContainer>
  )
}
```

## 常見任務範本

### 任務 1: 建立資料展示元件
```
請建立 [元件名稱] 元件：

功能：[功能描述]

需求：
1. 檔案位置：frontend/src/components/[ComponentName].jsx

2. API 整合：
   - 使用 [apiName].get[Something]() 獲取資料
   - 處理 loading/error/empty 三種狀態

3. UI 設計：
   - 使用 glass 卡片樣式
   - [具體的 UI 需求]
   - 響應式設計（手機/平板/桌面）

4. 多語言：
   - 使用 t('[namespace].[key]') 顯示文字
   - 需要的翻譯 keys 列表：[列出]

5. 互動：
   - [列出所有互動功能]
```

### 任務 2: 建立表單元件
```
請建立 [表單名稱] 表單元件：

功能：[功能描述]

需求：
1. 表單欄位：
   - [欄位名稱]: [類型] - [驗證規則]

2. 表單驗證：
   - 必填欄位檢查
   - 格式驗證（email, 數字等）
   - 錯誤訊息顯示

3. API 提交：
   - 使用 [apiName].create/update(data)
   - 顯示提交中狀態（按鈕 disabled + loading）
   - 成功後顯示提示訊息
   - 錯誤處理與顯示

4. UI 樣式：
   - Input: bg-white/10 border border-white/20 rounded px-3 py-2
   - Button: 主要按鈕樣式（紫色）
   - 錯誤訊息: text-red-400 text-sm
```

### 任務 3: 建立圖表視覺化元件
```
請建立 [圖表名稱] 視覺化元件：

功能：使用 Recharts 顯示 [資料類型]

需求：
1. 圖表類型：[BarChart/LineChart/PieChart/etc.]

2. 資料來源：
   - API: [apiName].[method]()
   - 資料格式：[描述預期格式]

3. 圖表配置：
   - X 軸: [資料欄位]
   - Y 軸: [資料欄位]
   - 顏色: [指定顏色]
   - 工具提示: 顯示 [資訊]

4. 主題適配：
   - 使用 useTheme() 根據深淺色主題調整
   - 網格線、文字顏色需適配主題

5. 空狀態處理：
   - 無資料時顯示友善訊息
```

## 重要提醒

### ✅ 應該做的
- 使用 Functional Components + Hooks
- 所有文字使用 `t()` 翻譯函數
- API 呼叫加入 try-catch 錯誤處理
- 元件加入 loading/error/empty 狀態
- 使用 Tailwind CSS 類別（不要寫 inline style）
- 使用 `glass` className 保持視覺一致性
- 圖表需適配深淺色主題
- 按鈕點擊時加入 transition 動畫

### ❌ 不應該做的
- 不要使用 Class Components
- 不要直接寫死文字（要用翻譯）
- 不要忘記錯誤處理
- 不要在元件裡寫複雜的業務邏輯
- 不要使用 inline styles（除非動態計算）
- 不要忘記 loading 狀態
- 不要使用表情符號當作 icon（應使用 SVG icon 或文字）

## 翻譯 Key 命名規範

```javascript
// 功能命名空間
"[feature].[item]"

// 範例
"habit.title"           // 習慣追蹤器標題
"habit.createNew"       // 建立新習慣按鈕
"habit.checkIn"         // 打卡
"habit.streak"          // 連續天數
"habit.stats"           // 統計
"habit.loadError"       // 載入錯誤訊息
```

## 完成檢查清單
- [ ] 元件檔案已建立
- [ ] API client 已建立（如需要）
- [ ] 所有文字使用 t() 翻譯
- [ ] 加入 loading/error 狀態處理
- [ ] 使用 glass 樣式保持一致性
- [ ] 響應式設計（手機/平板/桌面）
- [ ] 深淺色主題適配
- [ ] 互動加入過渡動畫
- [ ] Console 無錯誤或警告
