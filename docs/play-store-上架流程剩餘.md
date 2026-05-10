# Play Store 上架流程 — 剩餘步驟清單

> 文件日期：2026-05-10
> 適用版本：HeartBox versionCode=1, versionName="1.0"
> 所有「✅ 已完成」項目見文末附錄；本主文聚焦「⏳ 還沒做」的事。
>
> **匯出 PDF：** 用 VS Code Markdown preview 右上角「Export PDF」，或瀏覽器打開後 `Ctrl+P` 印成 PDF。

---

## 0. 全景一覽

| 階段 | 項目 | 狀態 | 負責 |
|---|---|---|---|
| Pre-flight | demo 帳號 seed 到 prod DB | ⏳ 還沒做 | 你 |
| Pre-flight | 拍 4 張公開頁截圖 | ⏳ 還沒做 | 你（自動化）|
| Pre-flight | 拍 4 張 auth 頁截圖（×3 語言）| ⏳ 還沒做 | 你（手動）|
| Build | 觸發 GitHub Actions release build | ⏳ 還沒做 | 你 |
| Build | 下載 `.aab` artifact | ⏳ 還沒做 | 你 |
| Console | 身分驗證（已申請）| ⏳ 等 Google 1-15 天 | Google |
| Console | Main store listing × 3 locales | ⏳ 還沒做 | 你（複製貼上）|
| Console | App content（隱私 / Data safety / Health / Rating）| ⏳ 還沒做 | 你 |
| Console | Production release：上傳 AAB | ⏳ 還沒做 | 你 |
| Console | Save → Review → Start rollout | ⏳ 還沒做 | 你 |

預計總時間：**約 3 小時**（不含 Google 身分驗證等待時間）。

---

## 1. Pre-flight：seed demo 帳號到 prod

### 為什麼

Google Play 審查者需要登入測試所有功能。`demo@heartbox.tw` 帳號附 14 天日記、健康資料、AI 對話、活動 streak — 讓審查者看到完整 UX 而不是空 dashboard。

### 怎麼做

```powershell
# 在你的本機 PowerShell:
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\backend

# 設環境變數指向 prod Neon Postgres（從 .env 或 Cloud Run env 拿）
# DATABASE_URL 應該長這樣：postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname
$env:DATABASE_URL = "<從 Cloud Run env 複製，或從 Neon dashboard 取>"
$env:DJANGO_SECRET_KEY = "<隨便填，這個 command 不需要 web stack 啟動>"
$env:ENCRYPTION_KEY = "<從 Cloud Run env 複製，必須跟 prod 一致才能寫入 encrypted journal>"

.\venv\Scripts\python.exe manage.py seed_demo_account
```

預期輸出：
```
Created user demo (demo@heartbox.tw)
  notes: +14 (total 14)
  health: +70 metrics (70 total)
  streak: 14 days
  chat: 1 session, 6 messages

Demo account ready:
  username: demo
  email: demo@heartbox.tw
  password: DemoPass2026
```

### 驗證

打開 https://heartbox.tw/login，用 `demo` / `DemoPass2026` 登入，應該看到 14 天連續日記、dashboard 有趨勢圖。

⚠️ **關鍵：`ENCRYPTION_KEY` 必須跟 prod 用同一個**，否則 seed 出來的日記內容 prod 解不開。

---

## 2. 拍公開頁截圖（自動化）

### 為什麼

Play Store 每個語言要 4-8 張截圖。前 4 張是公開頁面（landing / login / register / privacy），可以用 puppeteer 自動拍。

### 怎麼做

```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\frontend
npm run store:screenshots
```

腳本對 https://heartbox.tw 自動拍：
- `01-landing.png` — 首頁
- `02-login.png` — 登入頁
- `03-register.png` — 註冊頁
- `04-privacy.png` — 隱私政策

每個語言一份，輸出在 `frontend/store-assets/screenshots/{zh-TW,en,ja}/`。

預計時間：**5 分鐘**。

---

## 3. 拍 auth 頁截圖（手動，最花時間）

### 為什麼

Play Store 偏好截圖呈現「實際 app 內容」，所以登入後的核心頁面要拍。Puppeteer 拍不了（要 demo 登入態 + 實機尺寸）。

### 工具

- Android Studio → AVD Manager → 建一個 Pixel 6 或 Pixel 7 模擬器（解析度 **1080×2400**，Play Store 偏好的手機比例）
- 或用實機 Galaxy A52 拍（你已經有）

### 拍法

1. 打開模擬器，安裝 dev build（或直接用瀏覽器訪問 https://heartbox.tw 用手機尺寸）
2. 用 demo 帳號登入：`demo` / `DemoPass2026`
3. 切換 device 語言（**zh-TW → en → ja**），每個語言重拍以下 4 張
4. 手機側邊「電源 + 音量下」拍螢幕，或模擬器點側邊欄相機 icon

### 4 張要拍什麼

| 檔名 | 拍什麼畫面 | 該展示什麼 | 路徑 |
|---|---|---|---|
| `06-journal.png` | 日誌列表 | 14 天 streak（火焰圖示）、彩色標籤、不同心情筆記混排（正向/負向/中性各幾張）| `/notes` |
| `07-dashboard.png` | Dashboard 個人化儀表板 | 情緒趨勢線圖（14 天有資料）、壓力雷達、活動-心情關聯（3 個 tag bar）、習慣打卡 widget | `/dashboard` |
| `08-ai-chat.png` | AI 聊天展開 session | 點開 demo 帳號裡那個「關於工作疲憊」session — 會看到 6 條訊息（user 3 + AI 3），最下方 AI 回覆完整可見 | `/ai-chat` 點該 session |
| `09-health.png` | 健康指標 / 週報 | 步數、心率、HRV、睡眠 4 個 card 都有資料；下方週報摘要文字 | `/health` 或 `/sleep` |

### 存放位置

```
frontend/store-assets/screenshots/
├── zh-TW/
│   ├── 06-journal.png
│   ├── 07-dashboard.png
│   ├── 08-ai-chat.png
│   └── 09-health.png
├── en/
│   ├── (相同 4 張，介面切英文)
└── ja/
    └── (相同 4 張，介面切日文)
```

12 張總共。預計時間：**45-60 分鐘**（換語言、登入、截圖、整理）。

### 截圖品質要求

- **解析度**：1080×2400（Play Store 接受 1080-3840 寬度）
- **格式**：PNG（不要 JPG，避免壓縮 artifact）
- **內容**：真實資料，不要 Lorem ipsum
- **截圖前清空**：通知 panel 收起、status bar 不要太雜（飛航模式可以隱藏訊號）

---

## 4. 觸發 release build → 拿 AAB

### 為什麼

Play Store 從 2021 年 8 月起只接受 `.aab`（Android App Bundle），不收 `.apk`。CI 已經配置好簽章。

### 怎麼做

1. 打開 https://github.com/alanlin0604/HeartBox/actions/workflows/mobile-build.yml
2. 點右上 **「Run workflow」**
3. 設參數：
   - `platform` = **android**
   - `build_type` = **release**
4. 點綠色按鈕 **「Run workflow」**
5. 等 CI 跑完（約 8-12 分鐘），看到綠勾就完成
6. 點進該次 run，最下方 **Artifacts** 區下載 `android-apk` zip
7. 解壓後裡面有：
   - `app-release.aab` ← **上傳這個到 Play Store**
   - `app-release.apk` ← 給你裝實機 QA 用，不上 Store

預計時間：**15 分鐘**（含等待 CI）。

### 簽章已配置

GitHub Secrets 已有 `ANDROID_KEYSTORE_BASE64` / `ANDROID_KEYSTORE_PASSWORD` / `ANDROID_KEY_ALIAS` / `ANDROID_KEY_PASSWORD`，CI 會自動簽。如果 CI 紅了報「keystore not found」，可能是 secret 過期或被誤刪 — 通知我，我幫你找回。

---

## 5. Play Console 表單填寫

### 入口

https://play.google.com/console → 選 HeartBox app

### 5.1 Main store listing（×3 locales）

**Console 路徑**：`Store presence → Main store listing → Manage translations`

每個語言（**繁體中文 / English / 日本語**）都要設定。內容**直接從** [`frontend/store-assets/store-listing.md`](../frontend/store-assets/store-listing.md) 複製：

- App name（≤30 字元）
- Short description（≤80 字元）
- Full description（≤4000 字元）
- App icon → 上傳 `frontend/public/logo-icon.png`（512×512）
- Feature graphic → 上傳 `frontend/store-assets/feature-graphic-{zh,en,ja}.png`（1024×500）
- Phone screenshots → 上傳 §2 + §3 拍的 8 張（4 公開 + 4 auth）

**zh-TW 是 default locale**（其他語言看不到時會 fallback 到這個）。

### 5.2 App content

**Console 路徑**：`App content`，逐個填：

#### Privacy policy
- URL: `https://heartbox.tw/privacy`

#### App access
- 選「**All functionality is available without restrictions**」
- 但在 reviewer note 框貼：`demo@heartbox.tw / DemoPass2026`（即使 app 不要登入也可訪問首頁，給審查者測核心功能）

#### Ads
- **No**

#### Content rating questionnaire
答案（按 [`store-listing.md` 的 §「Content rating」段落](../frontend/store-assets/store-listing.md)）：
- Violence: **None**
- Sexual content: **None**
- Profanity: **None**
- User-generated content: **Yes**（私人日記，不分享）
- Personal info collection: **Yes**（帳號 + 心情 + 選用健康 — 全加密）

提交後等 IARC rating 自動分級（通常即時）。預期分級：**Teen (13+)** with mental health content advisory。

#### Target audience
- **13+**

#### News app
- **No**

#### Data safety
宣告以下類別：
- Health data — 收集，加密傳輸 + 加密儲存，可選用，不分享，可刪除（Settings → Delete Account）
- Personal info（email, username, encrypted journal）— 同上
- App activity（streak, mood）— 同上

#### Health Apps Declaration ⭐ 核心
**Console 路徑**：`App content → Health apps declaration`

直接從 [`store-listing.md` line 226-237](../frontend/store-assets/store-listing.md) 那張表逐欄貼進去：

| 欄位 | 值 |
|---|---|
| Does your app handle health data? | Yes |
| Data types read | Steps, Heart rate, HRV, Active calories burned, Exercise time, Sleep |
| Purpose | (1) Tag exercise/sleep context on journal entries; (2) Display in health dashboard and weekly/monthly reports; (3) Correlate with mood records |
| Shared with third parties? | No |
| Used for AI training? | No |
| Storage | Encrypted, within user account, on Neon PostgreSQL |
| User revocation | Android Health Connect system settings; in-app Settings → Delete Account |
| Privacy policy URL | https://heartbox.tw/privacy#health-data |
| Demo account for review | demo@heartbox.tw / DemoPass2026 |

⚠️ **Data types** 這欄文字必須**逐字符**對齊 Health Connect 的 API enum，不要改寫。

#### Government apps
- **No**

### 5.3 Production release

**Console 路徑**：`Production → Releases → Create new release`

1. 點 **「Upload」** 上傳 §4 拿到的 `app-release.aab`
2. **Release name**：留 versionCode 自動填（會是 `1 (1.0)`）
3. **Release notes**（每個語言一份，≤500 字元）— 可以用：

   **zh-TW:**
   ```
   首次上線。
   - 私密 AI 心情日記（端對端加密）
   - 情緒趨勢、壓力雷達、週報自動產生
   - Health Connect 整合，同步步數、心率、睡眠
   - 呼吸練習 + 引導冥想
   - 諮商師媒合
   ```

   **en-US:**
   ```
   Initial release.
   - Private encrypted AI mood journal
   - Mood trends, stress radar, automatic weekly summaries
   - Health Connect integration: steps, heart rate, sleep
   - Built-in breathing exercises + guided meditation
   - Counselor matching
   ```

   **ja-JP:**
   ```
   初回リリース。
   - 暗号化されたAI気分日記
   - 気分の推移、ストレスレーダー、週次レポート自動生成
   - Health Connect連携（歩数・心拍・睡眠）
   - 呼吸エクササイズ + ガイド付き瞑想
   - カウンセラーマッチング
   ```

4. 點右下 **「Save」** → **「Review release」** → **「Start rollout to Production」**

---

## 6. 提交後

- **身分驗證**：1-15 天，沒辦法加速。Google 會 email 你。
- **政策審查**：通常 24-72 小時。
- **上線**：審查通過 → 自動上架，全球可下載。

### 如果被退回

- 「Health & Fitness 類別誤用」→ 把 Primary category 改 **Lifestyle** 重送
- 「截圖不符政策」→ 通常是 dark UI 太黑或泛 HUD，重拍亮一點的版本
- 「demo 帳號無法登入」→ 確認 §1 seed 完成且 prod DB 真的有 demo user

### 上線後監控

- **Play Console → Crashes & ANRs**：每天看一次，>0.5% 要立刻修
- **Play Console → Vitals**：盯 ANR rate、cold start time
- **Sentry**：新版本上線 24h 內密集看 error rate 變化
- **第一週每天**檢查上面三個面板

---

## 附錄：✅ 已完成（不需要動）

- 後端部署最新版（含 LeaderboardView, cron endpoints, habit reminders）— Cloud Run revision `heartbox-api-00135-lmq` 之後
- Cloud Scheduler `habit-reminders` + `weekly-summaries` 已運行
- `mobile-build.yml` 同時產 `.aab` + `.apk`（commit bd3b1fe）
- `seed_demo_account` 命令存在（`backend/api/management/commands/seed_demo_account.py`）
- `store-listing.md` 三語齊全
- `feature-graphic-{zh,en,ja}.png` 都已生成
- 隱私政策 / 服務條款公開頁可訪問
- Brand color 已統一（橘色+玫瑰色）
- i18n 三語 1471 keys 同步無 missing
- `/habits` /habits 排行榜 等 user-facing bug 已修

---

## 任何卡住通知我

每個步驟卡住把錯誤訊息或截圖貼出來，我幫你 debug。

特別容易卡的點：
- **§1 ENCRYPTION_KEY 不對** → 日記寫了但 prod 解不開（驗證時會看到亂碼）
- **§3 模擬器不會切語言** → Settings → System → Languages → 加 zh-TW 設為主要
- **§4 CI 紅了** → 通常 keystore secret 問題，把 Actions log 貼給我
- **§5.2 Health Apps Declaration 拒絕** → 文字沒對齊 enum，照表逐字貼
