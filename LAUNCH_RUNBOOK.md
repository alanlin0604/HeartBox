# HeartBox 上架 Runbook

> 一頁完整流程。從「準備好上架」到「按下提交」的所有指令。
> 假設 `heartbox.tw` 自訂域名已設定（沒設先看附錄 D）。

---

## 階段 A：素材生成（~2 小時，可離線做）

### A1. Backend deploy（先做，因為 prod 還跑舊 prediction schema）

```powershell
cd c:\Users\alan9\OneDrive\Desktop\HeartBox
.\deploy-backend.ps1
```

verify：開 https://heartbox-api-598139488748.asia-east1.run.app/api/health/ 應該 200。
若 fail，查 `gcloud run services logs read heartbox-api --region=asia-east1 --limit=50`。

### A2. Demo 帳號 seed 到 prod

```powershell
# Cloud Run 一次性 job — 等同把 manage.py 命令 run 在 prod DB 上
gcloud run jobs deploy seed-demo `
  --image=asia-east1-docker.pkg.dev/heartbox-app/cloud-run-source-deploy/heartbox-api:latest `
  --command=python --args=manage.py,seed_demo_account `
  --region=asia-east1 `
  --set-env-vars=DJANGO_SETTINGS_MODULE=moodnotes_pro.settings,...
gcloud run jobs execute seed-demo --region=asia-east1 --wait
```

或更簡單：本機跑 + 連 prod DB（如果你的 .env 裡有 `DATABASE_URL` 指 prod）：

```powershell
cd backend
python manage.py seed_demo_account
```

verify：去 https://heartbox.tw/login → 用 `demo@heartbox.tw / DemoPass2026` 登入 → 應看到 14 篇日記。

### A3. 截圖

**Public pages**（4 張 × 3 語 = 12 張）：

```powershell
cd frontend
npm run store:screenshots
```

**Authenticated pages**（5 張 × 3 語 = 15 張）：

```powershell
# 對 prod 拍
$env:TARGET="https://heartbox.tw"
$env:DEMO_USER="demo@heartbox.tw"
$env:DEMO_PASS="DemoPass2026"
npm run store:screenshots:authed

# 或對本地 preview 拍（無需 deploy backend）：
npm run build
npm run preview &  # 起 http://localhost:4173
$env:TARGET="http://localhost:4173"
npm run store:screenshots:authed
```

verify：`frontend/store-assets/screenshots/{zh-TW,en,ja}/` 各有 9 張 PNG。
若哪張 timing 不對，調 `capture-screenshots-authed.js` 內該頁的 `wait` 參數重跑。

### A4. Build Release AAB

到 GitHub Actions：
1. 開 https://github.com/alanlin0604/HeartBox/actions/workflows/mobile-build.yml
2. 「Run workflow」→ `platform=android` + `build_type=release` → 等 ~15 分鐘
3. 點進 run → 底部 Artifacts → 下載 `android-apk`
4. 解開，內有 `*.aab` (Play Store 上傳用) 與 `*.apk` (你 sideload 測試用)

---

## 階段 B：Smoke Test（~15 分鐘）

把 release `.apk` 裝到 Galaxy A52，逐項測：

| 路徑 | 預期 |
|---|---|
| 新使用者註冊 | email verify 信收得到 |
| 登入 demo 帳號 | 14 篇日記都看得到 |
| 寫一篇日記 | < 1 秒回應；3-10 秒後 AI 分析跳出 |
| 設定 → 健康 → 連結 HC | 跳 HC 權限頁、勾全部、允許 → 綠燈「已連結」 |
| /dashboard | 圖表全部 render；情緒預測 header/箭頭 反映實際 trend |
| /community | 「好友動態」/「公開動態」分區正確 |
| /ai-chat | 發訊息可收到 AI 回覆 |
| 通知 bell | 設定 → 偏好設定 → 推播開啟 → 寫日記後收到 achievement 通知 |

任一項紅 → fix 完再進階段 C。

---

## 階段 C：Play Console 填表（~45 分鐘）

開 https://play.google.com/console → HeartBox app → 照下面順序：

### C1. Main store listing × 3 語 (Store presence)

每語照 [store-listing.md §1-3](frontend/store-assets/store-listing.md) 貼：

| 欄位 | 來源 |
|---|---|
| App name (≤30) | `store-listing.md` 的 `App name` 區塊 |
| Short description (≤80) | `Short description` 區塊 |
| Full description (≤4000) | `Full description` 區塊 |
| App icon (512×512) | `frontend/public/logo-icon.png` |
| Feature graphic (1024×500) | `frontend/store-assets/feature-graphic-{zh,en,ja}.png` |

### C2. Screenshots × 3 語

每語上傳 `frontend/store-assets/screenshots/{zh-TW,en,ja}/0[1-9]-*.png` 共 9 張。
（Play 接 4-8 張，這裡多備 1 張供換）

### C3. App content (App content menu)

- Privacy policy URL: `https://heartbox.tw/privacy`
- App access: "All functionality available" + 把 `demo@heartbox.tw / DemoPass2026` 貼進 reviewer note
- Ads: No
- Content rating: 走 IARC questionnaire → 通常即時拿到 PEGI 3 / ESRB E / 適合所有年齡
- Target audience: 13+
- Data safety: Health data + Personal info + App activity，加密、可刪、不分享
- **Health Apps Declaration**: 重要，要照 [store-listing.md 的 Health declaration 區塊](frontend/store-assets/store-listing.md) 逐字貼

### C4. Production release

- Production → Releases → Create release
- Upload AAB（從 A4 拿的）
- Release notes ≤500 字：
  > 「v1.0 首發。心情日記＋AI 分析＋情緒預測＋健康整合（Health Connect）。  
  > 端到端加密日記、PHQ-9/GAD-7 量表、感恩日記模板、社群動態（好友優先）。」
- Save → Review → **Start rollout to Production**

---

## 階段 D：送審後（被動等待）

- Identity verification：1-15 天，通常 2-3 天
- Health-app 人工審核：1-7 天額外
- **被拒主要原因**：Health Apps Declaration 漏寫、敏感權限說明不足、demo 帳號登入失敗。Google 信件會寫明，修完點「Send for review」即可

監看：https://play.google.com/console → 左側 Inbox / Notifications

---

## 附錄 A：哪些 commit 還沒 deploy？

跑這指令對照：

```powershell
cd c:\Users\alan9\OneDrive\Desktop\HeartBox
git log --oneline origin/main ^$(git log -1 --format=%H -- deploy-backend.ps1) 2>$null
```

> 若有結果 → 提示哪些 backend 改動還未 push 進 prod。  
> 過去幾輪 prediction schema 改動就是這個 case，frontend 加了 reverse mapping 兜，但 deploy 後可清掉那個 patch。

## 附錄 B：CI 失敗時

GitHub Actions Mobile Build 紅 → 通常兩個原因：
1. **「Verify HC patch applied」step 紅**：`patch-package` 沒跑 → 看 [docs/health-connect-debug-progress.md](docs/health-connect-debug-progress.md) Lesson 1
2. **「Verify Kotlin stdlib version」step 紅**：報出 resolved version → 看 [docs/health-connect-debug-progress.md](docs/health-connect-debug-progress.md) Lesson 2

## 附錄 C：Cloud Scheduler cron

兩個 cron job 必須跑（不跑使用者收不到習慣提醒、週報）：

```bash
SVC_URL=https://heartbox-api-598139488748.asia-east1.run.app
SECRET="<同 CRON_SECRET env var>"

gcloud scheduler jobs create http habit-reminders \
  --schedule="*/15 * * * *" --time-zone="Asia/Taipei" \
  --uri="$SVC_URL/api/internal/cron/habit-reminders/" --http-method=POST \
  --headers="X-Cron-Secret=$SECRET" --location=asia-east1

gcloud scheduler jobs create http weekly-summaries \
  --schedule="0 6 * * 1" --time-zone="Asia/Taipei" \
  --uri="$SVC_URL/api/internal/cron/weekly-summaries/" --http-method=POST \
  --headers="X-Cron-Secret=$SECRET" --location=asia-east1
```

跑一次就好；之後 Cloud Scheduler 持續觸發。

## 附錄 D：heartbox.tw 自訂域名

如果還沒設：

1. Cloudflare Pages → heartbox（你的 project name）→ Custom domains → Set up a custom domain → 填 `heartbox.tw`
2. 在 DNS provider（GoDaddy/Namecheap）把 CNAME 指到 `heartbox.pages.dev`
3. Cloud Run 後端也要對應：
   ```bash
   gcloud run services update heartbox-api \
     --region=asia-east1 \
     --update-env-vars="CORS_ALLOWED_ORIGINS=https://heartbox.tw,CSRF_TRUSTED_ORIGINS=https://heartbox.tw,FRONTEND_URL=https://heartbox.tw,DJANGO_ALLOWED_HOSTS=heartbox-api-598139488748.asia-east1.run.app"
   ```
4. 等 DNS 生效（~30 分鐘到 24 小時）

---

## 預估總時間

| 階段 | 時間 |
|---|---|
| A 素材生成 | 2 小時 |
| B Smoke test | 15 分 |
| C Play Console 填表 | 45 分 |
| D 等審查 | 1-7 天（被動） |
| **總人工** | **3-4 小時** |
| 加審查週期 | **2-10 天** |

