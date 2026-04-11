# HeartBox Deep Linking 行銷活用指南

深度連結（Deep Linking）讓您能夠直接將使用者導向 APP 內的特定頁面，大幅提升行銷轉換率和使用者體驗。

---

## 📱 支援的 Deep Link 格式

### 1. Custom URL Scheme
```
heartbox://路徑?參數=值
```
**用途**：在 APP 已安裝時直接開啟
**範例**：`heartbox://notes/123`

### 2. Universal Links (推薦)
```
https://heartbox.tw/路徑?參數=值
```
**用途**：APP 未安裝時開啟網頁，已安裝時開啟 APP
**範例**：`https://heartbox.tw/dashboard?tab=health`

---

## 🎯 行銷活用場景

### 1. 社群媒體貼文

#### Facebook / Instagram 廣告
```html
<!-- CTA 按鈕連結 -->
https://heartbox.tw/assessments?utm_source=facebook&utm_campaign=mental_health_2024

<!-- 貼文內容範例 -->
想了解自己的心理健康狀態嗎？
立即進行專業評估 👇
https://heartbox.tw/assessments
```

#### Twitter / X
```
壓力大到睡不著？試試 HeartBox 的呼吸冥想功能 🧘‍♀️

https://heartbox.tw/breathe?source=twitter

#心理健康 #冥想 #減壓
```

#### LINE 官方帳號
```
🎁 新用戶專屬優惠！
立即體驗 AI 心理諮詢聊天機器人

👉 https://heartbox.tw/ai-chat?promo=line_welcome
```

---

### 2. Email 行銷

#### 歡迎信
```html
<h2>歡迎加入 HeartBox！</h2>
<p>開始記錄您的第一篇心情日記：</p>
<a href="https://heartbox.tw/?action=new_note&utm_source=welcome_email"
   style="background: #7c3aed; color: white; padding: 12px 24px; border-radius: 8px;">
  立即開始寫日記
</a>
```

#### 每週心情報告提醒
```html
<h2>您的本週心情分析已準備好！</h2>
<a href="https://heartbox.tw/weekly-summary?utm_source=email&utm_campaign=weekly_report">
  查看我的心情週報 →
</a>
```

#### 未完成評估提醒
```html
<p>還記得上次開始的心理健康評估嗎？</p>
<a href="https://heartbox.tw/assessments?resume=true&id=ABC123">
  繼續完成評估
</a>
```

---

### 3. 推播通知 (Push Notifications)

#### 每日提醒
```javascript
// 推播內容
{
  title: "☀️ 早安！記錄今天的心情",
  body: "花 2 分鐘寫下今天的感受",
  data: {
    deepLink: "heartbox://?action=new_note",
    utm_source: "push_notification",
    utm_campaign: "daily_reminder"
  }
}
```

#### 好友互動通知
```javascript
{
  title: "💬 Amy 回覆了您的日記",
  body: "「我也有類似的感受！」",
  data: {
    deepLink: "heartbox://notes/456?highlight=comment",
  }
}
```

#### 成就解鎖
```javascript
{
  title: "🏆 恭喜！達成新成就",
  body: "連續記錄 7 天心情",
  data: {
    deepLink: "heartbox://achievements?new=7day_streak",
  }
}
```

---

### 4. QR Code 應用

#### 活動海報 QR Code
```
活動：心理健康工作坊
掃描 QR Code 立即預約諮商師

QR Code 內容：
https://heartbox.tw/counselors?event=workshop_2024&utm_source=poster
```

#### 產品包裝 QR Code
```
HeartBox Premium 會員卡

QR Code 內容：
https://heartbox.tw/pricing?promo=premium_card&discount=20
```

---

### 5. 部落格 / SEO 內容

#### 文章內嵌連結
```markdown
研究顯示，每天寫日記可以有效減壓。
[立即開始使用 HeartBox 記錄心情](https://heartbox.tw/?utm_source=blog&utm_content=journaling_benefits)

想了解自己的壓力來源？
[進行免費心理健康評估](https://heartbox.tw/assessments?utm_source=blog&utm_content=stress_assessment)
```

---

### 6. 合作夥伴整合

#### 心理諮商診所網站
```html
<!-- 推薦工具 -->
<div class="partner-tools">
  <h3>診間建議工具</h3>
  <p>HeartBox 幫助您在諮商期間追蹤心情變化</p>
  <a href="https://heartbox.tw/counselors?partner=clinic_abc">
    查看合作諮商師
  </a>
</div>
```

#### 企業 EAP 計畫
```
員工心理健康支持計畫

專屬連結：
https://heartbox.tw/pricing?corporate=company_xyz&seats=50
```

---

## 🔗 常用 Deep Link 路徑

| 功能 | Deep Link | 用途 |
|------|-----------|------|
| **首頁（新增日記）** | `heartbox://` 或 `/?action=new_note` | 引導寫日記 |
| **心情儀表板** | `heartbox://dashboard` | 查看分析 |
| **特定日記** | `heartbox://notes/{id}` | 分享日記 |
| **心理評估** | `heartbox://assessments` | 進行評估 |
| **AI 聊天** | `heartbox://ai-chat` | AI 諮詢 |
| **呼吸冥想** | `heartbox://breathe` | 減壓冥想 |
| **諮商師列表** | `heartbox://counselors` | 尋找專業協助 |
| **成就系統** | `heartbox://achievements` | 查看成就 |
| **設定頁（健康）** | `heartbox://settings?tab=health` | 健康數據設定 |
| **每週報告** | `heartbox://weekly-summary` | 週報分析 |
| **學習中心** | `heartbox://learn` | 心理知識 |

---

## 📊 UTM 參數追蹤

### 標準 UTM 結構
```
https://heartbox.tw/路徑?
  utm_source=來源&
  utm_medium=媒介&
  utm_campaign=活動名稱&
  utm_content=內容&
  utm_term=關鍵字
```

### 實際範例

#### Google Ads
```
https://heartbox.tw/assessments?
  utm_source=google&
  utm_medium=cpc&
  utm_campaign=mental_health_assessment_2024&
  utm_content=ad_variant_a&
  utm_term=心理健康評估
```

#### Facebook Ads
```
https://heartbox.tw/pricing?
  utm_source=facebook&
  utm_medium=paid_social&
  utm_campaign=premium_q1_2024&
  utm_content=video_ad
```

#### Instagram Story
```
https://heartbox.tw/breathe?
  utm_source=instagram&
  utm_medium=story&
  utm_campaign=meditation_week
```

#### Email Newsletter
```
https://heartbox.tw/weekly-summary?
  utm_source=newsletter&
  utm_medium=email&
  utm_campaign=weekly_digest&
  utm_content=cta_button
```

---

## 💡 最佳實踐

### 1. 短網址服務
使用 Bitly 或自建短網址服務縮短連結：
```
原始：https://heartbox.tw/assessments?utm_source=instagram&utm_campaign=...
短網址：https://hb.tw/assess
```

### 2. 動態參數
根據使用者資料動態生成連結：
```javascript
const userId = user.id
const deepLink = `https://heartbox.tw/dashboard?user=${userId}&welcome=true`
```

### 3. A/B Testing
使用不同連結測試轉換率：
```
版本 A：https://heartbox.tw/assessments?variant=a
版本 B：https://heartbox.tw/assessments?variant=b
```

### 4. 分享功能整合
```javascript
import { shareDeepLink } from '@/utils/deepLinking'

await shareDeepLink({
  title: '我的心情週報',
  text: '這週的心情分析很有趣！',
  path: '/weekly-summary',
  params: { shared_by: user.id }
})
```

---

## 🎨 Call-to-Action 按鈕設計

### 高轉換率 CTA 文案
- ✅ **立即開始記錄心情** (具體行動)
- ✅ **查看我的心情分析** (個人化)
- ✅ **免費進行心理評估** (免費 + 價值)
- ✅ **2 分鐘了解壓力來源** (時間承諾)
- ❌ 點擊這裡 (不具體)
- ❌ 了解更多 (太模糊)

### 按鈕顏色建議
- **主要 CTA**：HeartBox 紫色 `#7c3aed`
- **次要 CTA**：深灰或白色邊框
- **警示 CTA**：琥珀色 `#f59e0b`

---

## 📈 成效追蹤

### Google Analytics 事件追蹤
```javascript
// 當使用者透過 Deep Link 進入時記錄
gtag('event', 'deep_link_open', {
  source: utm_source,
  campaign: utm_campaign,
  path: window.location.pathname
})
```

### 內部分析
記錄每個 Deep Link 的：
- 點擊次數
- 轉換率（安裝 → 開啟）
- 留存率（7 天、30 天）
- 特定功能使用率

---

## 🔒 安全考量

### 1. 參數驗證
```javascript
// 驗證 Deep Link 參數
if (params.promo) {
  // 檢查促銷碼是否有效
  const isValid = await validatePromoCode(params.promo)
}
```

### 2. 敏感資料保護
❌ **不要**在 Deep Link 中包含：
- 使用者密碼
- 個人識別資訊（身分證號）
- 敏感醫療資料

✅ **可以**包含：
- 公開的內容 ID
- 促銷代碼
- UTM 追蹤參數
- Session token (短期有效)

---

## 📞 技術支援

如需協助設定 Deep Linking 或有任何問題，請聯繫：
- Email: support@heartbox.tw
- GitHub: [HeartBox Deep Linking Docs](https://github.com/heartbox/docs)

---

**更新日期**：2026-04-11
**版本**：1.0
