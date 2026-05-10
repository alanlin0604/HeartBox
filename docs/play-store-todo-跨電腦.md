# Play Store 上架 — 剩餘待辦（換電腦續做）

> 文件日期：2026-05-10
> 此檔列出**還沒做**的事，已完成的見 [`play-store-上架流程剩餘.md`](play-store-上架流程剩餘.md) 主文。
>
> **跨電腦原則：** 此檔在 OneDrive 內，會自動同步。

---

## ✅ 已完成（不要重做）

- §1 demo 帳號 `demo / DemoPass2026` 已 seed 到 prod（14 天 streak、80 health metrics、AI chat session）
- §2 公開頁 12 張截圖（`frontend/store-assets/screenshots/{zh-TW,en,ja}/01-04.png`）— 在 OneDrive，會跟著同步
- §4 release build 跑完（GitHub Actions run `25619330242`），AAB + APK 產出

## ⚠️ 待辦只剩兩項

- §3 拍 12 張 auth 頁截圖（最花時間，~45-60 分鐘）
- §5 Play Console 表單 + Production rollout（~30 分鐘）

---

## 換到新電腦：開機後第一件事

### 1. 確認 repo 已同步

```powershell
cd $env:USERPROFILE\OneDrive\Desktop\HeartBox
git status
git pull
```

### 2. 拿到 `app-release.aab`（兩種方式擇一）

**方式 A — 從 GitHub 重抓（推薦，不用搬檔案）：**

```powershell
# 需要先 gh auth login 一次
mkdir $env:USERPROFILE\Desktop\HeartBox-release-v1
cd $env:USERPROFILE\Desktop\HeartBox-release-v1
gh run download 25619330242 -R alanlin0604/HeartBox -n android-apk
```

完成後檔案在：
- `Desktop\HeartBox-release-v1\bundle\release\app-release.aab` ← 上傳到 Play Store 用
- `Desktop\HeartBox-release-v1\apk\release\app-release.apk` ← 給實機 QA 用

**方式 B — 從舊電腦複製：**

舊電腦的 `C:\Users\alan9\Desktop\HeartBox-release-v1\` 整個搬到 USB / OneDrive 任意資料夾即可。

⚠️ AAB 不要放進 git repo（`.aab` 應該在 .gitignore 裡，commit 進去會被 GitHub 拒絕推）。

---

## §3 — 拍 12 張 auth 頁截圖

### 環境二選一

| 選項 | 設定 | 適合 |
|---|---|---|
| **A. Chrome DevTools 模擬手機** | 打開 https://heartbox.tw → F12 → Toggle device toolbar → Custom 1080×2400 | 最快，沒有 Health Connect 干擾 |
| **B. Galaxy A52 實機** | 安裝 `app-release.apk`，用瀏覽器路徑或 app 內網頁 | 截圖更貼近真實使用情境 |

⚠️ **Galaxy A52 注意：** Health Connect 還有未解 crash（`memory/project_health_connect_debug_paused.md`），但 §3 走 web mobile view 不會觸發；**不要**走 app 內 Health Connect 同步路徑拍 `09-health.png`。

### 登入

https://heartbox.tw → `demo` / `DemoPass2026`

### 4 張畫面

#### 1️⃣ `06-journal.png` — 心情日誌列表

- **網址：** https://heartbox.tw/notes
- **要拍到：** 火焰圖示 + **14 天** streak、3-4 張不同心情顏色的日記混排、彩色 tag chips
- **避免：** 「新增日記」彈窗、空狀態

#### 2️⃣ `07-dashboard.png` — Dashboard

- **網址：** https://heartbox.tw/dashboard
- **要拍到：** 14 天情緒趨勢線（有起伏）、壓力雷達、活動-心情關聯 3 個 tag bar、習慣打卡 widget
- **避免：** 骨架屏、loading spinner

#### 3️⃣ `08-ai-chat.png` — AI 聊天

- **網址：** https://heartbox.tw/ai-chat
- **操作：** 點開「**關於工作疲憊**」session
- **要拍到：** 6 條訊息（user 3 + AI 3 交錯），最下方 AI 完整回覆可見
- **避免：** 打字中省略號、輸入框擋到內容

#### 4️⃣ `09-health.png` — 健康指標 / 週報

- **網址：** https://heartbox.tw/health（或 `/sleep`）
- **要拍到：** 步數 / 心率 / HRV / 睡眠 4 個 card 都有數字、週報摘要文字
- **避免：** 「請連接 Health Connect」空狀態

### 切語言流程

每張拍 zh-TW / en / ja 三份 = 12 張。

1. 拍完 zh-TW 4 張
2. 右上角 Settings → Language 切 **English** → 重整 → 拍 en 4 張
3. 再切 **日本語** → 重整 → 拍 ja 4 張

（用 app 內 i18n，不必改裝置系統語言）

### 存檔位置（嚴格命名）

```
frontend/store-assets/screenshots/
├── zh-TW/
│   ├── 06-journal.png
│   ├── 07-dashboard.png
│   ├── 08-ai-chat.png
│   └── 09-health.png
├── en/
│   ├── 06-journal.png
│   ├── 07-dashboard.png
│   ├── 08-ai-chat.png
│   └── 09-health.png
└── ja/
    ├── 06-journal.png
    ├── 07-dashboard.png
    ├── 08-ai-chat.png
    └── 09-health.png
```

存好之後 git status 應該看到 12 個新檔案，commit 推上去（這些檔案會跟著 OneDrive 同步，但 commit 進 repo 比較保險）。

### 截圖品質要求

- **解析度**：1080×2400
- **格式**：PNG
- **不要**：JPG、Lorem ipsum 假資料、status bar 通知爆滿
- **建議**：飛航模式拍可隱藏訊號圖示

---

## §5 — Play Console 表單

### 入口
https://play.google.com/console → HeartBox app

### 5.1 Main store listing × 3 locales

`Store presence → Main store listing → Manage translations`

每個語言（zh-TW / en / ja）內容**直接從** [`frontend/store-assets/store-listing.md`](../frontend/store-assets/store-listing.md) 複製：

| 欄位 | 來源 |
|---|---|
| App name (≤30) | store-listing.md 該語言段落 |
| Short description (≤80) | 同上 |
| Full description (≤4000) | 同上 |
| App icon (512×512) | `frontend/public/logo-icon.png` |
| Feature graphic (1024×500) | `frontend/store-assets/feature-graphic-{zh,en,ja}.png` |
| Phone screenshots | §2 + §3 各 4 張 = 8 張 |

zh-TW 是 default locale。

### 5.2 App content（逐項填）

| 項目 | 值 |
|---|---|
| Privacy policy URL | `https://heartbox.tw/privacy` |
| App access | All functionality available; reviewer note 框貼 `demo@heartbox.tw / DemoPass2026` |
| Ads | **No** |
| Content rating | Violence/Sexual/Profanity = None；UGC = Yes（私人日記）；Personal info = Yes（加密）|
| Target audience | **13+** |
| News app | **No** |
| Government apps | **No** |

#### Data safety

宣告以下類別（全部「加密傳輸 + 加密儲存、不分享、可刪除」）：
- Health data — 收集，可選用
- Personal info（email, username, encrypted journal）
- App activity（streak, mood）

#### Health Apps Declaration ⭐ 最易卡關

`App content → Health apps declaration` — 直接從 [`store-listing.md` line 226-237](../frontend/store-assets/store-listing.md) 那張表**逐字符**貼進去（Data types 必須對齊 Health Connect API enum 名稱，不要改寫）：

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

### 5.3 Production release

`Production → Releases → Create new release`

1. **Upload**：上傳 `app-release.aab`（5.9 MB）
2. **Release name**：留空讓 versionCode 自動填（會是 `1 (1.0)`）
3. **Release notes**（每語言一份，≤500 字元）：

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

4. **Save** → **Review release** → **Start rollout to Production**

---

## 提交後

- 身分驗證：1-15 天，等 Google email
- 政策審查：通常 24-72 小時
- 上線後監控：Play Console Crashes & ANRs / Vitals + Sentry，第一週每天看一次

### 常見退回原因

- 「Health & Fitness 類別誤用」→ Primary category 改 **Lifestyle** 重送
- 「截圖不符政策」→ 通常太黑或泛 HUD，重拍亮一點
- 「demo 帳號無法登入」→ 確認 §1 seed 完成（已完成，但若距今超過 30 天可重跑 seed 確保資料新鮮）
- 「Health Apps Declaration 拒絕」→ Data types 文字沒對齊 enum，照表逐字符貼

---

## 完成 checklist（依序勾）

- [ ] §3.1 拍 zh-TW 4 張
- [ ] §3.2 拍 en 4 張
- [ ] §3.3 拍 ja 4 張
- [ ] §3.4 git add + commit + push（讓備份）
- [ ] §5.0 在新電腦下載/取得 `app-release.aab`
- [ ] §5.1 Main store listing × 3 locales
- [ ] §5.2 App content 全部填完（含 Health Apps Declaration）
- [ ] §5.3 上傳 AAB + 三語 release notes
- [ ] §5.4 Save → Review → Start rollout
- [ ] 等 Google 身分驗證 email
- [ ] 上線後第一天看 Crashes & ANRs

卡住任何步驟把錯誤訊息或截圖貼進新電腦的 Claude Code 對話即可續做。
