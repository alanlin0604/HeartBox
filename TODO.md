# HeartBox 待辦清單

**最後更新：** 2026-05-16
**當前階段：** Pre-launch（Play Store 上架準備）
**生產環境：** https://heartbox.pages.dev （Cloudflare Pages）+ Cloud Run asia-east1
**功能完成度：** 91%（10 / 11，詳見 [PENDING_FEATURES.md](PENDING_FEATURES.md)）

---

## 🚀 上架阻擋（必須先解）

### 1. Health Connect 自動同步 — 唯一未完功能（D2）
- 現況：`SleepAnalysisPage` / 報告全綠，但依賴使用者手動輸入睡眠資料
- Blocker：Galaxy A52 上 capgo Health Connect plugin native crash
- 追蹤：[docs/health-connect-debug-progress.md](docs/health-connect-debug-progress.md)
- 不阻擋 web 上架，但會被 Play Store reviewer 質問 health data section

### 2. Play Store 商店資產最後確認
- [x] 三語商店描述（諮商師段落已 2026-05-16 移除）
- [ ] 截圖 06-09 重新拍：移除諮商師移除後的最新 UI 截圖
- [ ] Feature graphic（1024×500）三語版本
- [ ] AAB build：GitHub Actions → Mobile Build → release artifact
- 流程：[frontend/store-assets/store-listing.md](frontend/store-assets/store-listing.md)

### 3. 諮商師功能反向恢復計畫（功能準備好時）
- 全 codebase 已用 `// hidden pre-launch — re-enable with /counselors` 標記
- 反向開啟步驟：
  1. [frontend/src/App.jsx](frontend/src/App.jsx) `/counselors` Navigate → 改回 LazyRoute
  2. [frontend/src/components/Layout.jsx](frontend/src/components/Layout.jsx) 社群 dropdown + flat list 加回 counselor link
  3. [frontend/src/pages/NoteDetailPage.jsx](frontend/src/pages/NoteDetailPage.jsx) 還原 ShareNoteButton
  4. [frontend/src/pages/AssessmentsPage.jsx](frontend/src/pages/AssessmentsPage.jsx) 還原 share-to-counselor
  5. [frontend/src/pages/LandingPage.jsx](frontend/src/pages/LandingPage.jsx) 加回 featureCounselor
  6. [frontend/src/pages/ChatPage.jsx](frontend/src/pages/ChatPage.jsx) navigate('/') → '/counselors'
  7. [frontend/src/pages/AdminPage.jsx](frontend/src/pages/AdminPage.jsx) Counselors tab `hidden: true` → `false`
  8. [backend/api/services/achievements.py](backend/api/services/achievements.py) 4 個成就的 `hidden: True` 移除
  9. [frontend/store-assets/store-listing.md](frontend/store-assets/store-listing.md) 諮商師段落還原

---

## 🟡 上架後馬上處理（不阻擋發版但 P1）

### 4. 失效成就 + 文案清理
- [ ] 後端 `Message.objects.filter(sender=user)` 計算範圍 — 現在只算 Conversation message，但若未來改用同一張表給朋友聊天，achievement counter 會錯
- [ ] Locale `counselor.*` keys（三語 70+ keys）若決定永久移除，現在開始下檔

### 5. 文件對齊現況
- [ ] [QA_CHECKLIST.md](QA_CHECKLIST.md) — 諮商師相關項已 2026-05-16 註解
- [ ] [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) — smoke check 已 2026-05-16 更新
- [ ] `HeartBox_全面檢查報告.md`（2026-02-19）— 舊資訊
- [ ] `重灌前最終確認報告.md`（2026-05-02）— 已過時，建議歸檔
- [ ] [docs/system-components.md](docs/system-components.md) — 仍列 `ShareNoteButton.jsx` 為 active

### 6. Lint warning 清掉
- 現況：5 errors（icon 腳本 `process` 未定義，獨立檔不影響 app）+ 93 warnings
- 主要 warnings 類型：
  - `react-hooks/set-state-in-effect`（~60 處）
  - `react-hooks/exhaustive-deps`（~25 處）
- 都是 hint，不影響功能；但有些可能是真實 race condition

---

## 🟢 後續發展（無時間壓力）

### 7. 諮商師功能正式上線準備（等業務面）
- [ ] 至少 1 位真實諮商師簽約並通過審核（pending → approved）
- [ ] Stripe / 綠界等金流串接（PricingTab 後端已有 SubscriptionPlan model）
- [ ] 諮商師訓練文件 / 規範 / 服務協議
- [ ] 隱私政策更新（諮商師可看到日記分享、評估資料）

### 8. 技術債
- [ ] backend `views.py` 已拆 9 模組，但 [backend/api/views.py](backend/api/views.py) 仍有遺留
- [ ] [frontend/src/pages/CounselorListPage.jsx](frontend/src/pages/CounselorListPage.jsx)（1240 行）+ `pages/counselor/*` 9 個 tab — 已斷 routing，dead code 可刪可留
- [ ] 評估是否需要 TypeScript migration（現為 JSX）
- [ ] E2E 測試（Playwright）— 目前只有 78 個 unit test

### 9. 效能進階優化
- 現況：Bundle 已大幅優化（Recharts/Tiptap lazy）；Cloud Run 已 min-instances=1
- 可動：
  - [ ] Critical CSS 提取（-300-500ms FCP）
  - [ ] 圖片 LCP candidate 加 `fetchpriority="high"`
  - [ ] Web Vitals 監控接入 Sentry

### 10. 內容 / UX
- [ ] 心理教育文章 8 → 20+ 篇（目前是 seed data）
- [ ] 引導式冥想腳本擴充
- [ ] 感恩日記模板（已有，可補更多變體）

---

## ✅ 最近完成（2026-05）

- **2026-05-16** 諮商師 UI 全面隱藏（route + nav + share + landing + admin + achievement）
- **2026-05-16** Play Store 商店描述移除諮商師段落（三語）
- **2026-05-16** QA + Deployment checklist 對齊
- **2026-05-15** launch-prep: compliance / crisis safety / retention / data rights / marketing（commit `ae5c6b1`）
- **2026-05-14** i18n hard fixes：ConfirmDialog / Alert / FeedbackToast 漏中文
- **2026-05-13** perf：achievements + counselors 頁面 cache
- **2026-05-12** security：first-message-only WS auth + audit logging

---

## 📁 重要檔案速查

| 用途 | 檔案 |
|---|---|
| 功能完成度 | [PENDING_FEATURES.md](PENDING_FEATURES.md) |
| 上架流程 | [frontend/store-assets/store-listing.md](frontend/store-assets/store-listing.md) |
| Deploy checklist | [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) |
| QA checklist | [QA_CHECKLIST.md](QA_CHECKLIST.md) |
| 系統架構 | [docs/system-architecture.md](docs/system-architecture.md) |
| 元件清單 | [docs/system-components.md](docs/system-components.md) |
| 功能模組 | [docs/feature-modules.md](docs/feature-modules.md) |
| API 速查 | [docs/api/好友系統API速查表.md](docs/api/好友系統API速查表.md) |
| CLAUDE 指南 | [CLAUDE.md](CLAUDE.md) |

---

## 🛠 常用指令

### 開發
```powershell
cd frontend
npm run dev                              # vite dev server
npm run build                            # production build
npm run lint                             # eslint check
npm run test                             # vitest

cd ../backend
python manage.py runserver
python manage.py test api.tests
```

### 部署
```powershell
# 後端（Cloud Run, asia-east1）
./deploy-backend.ps1

# 前端（Cloudflare Pages 自動部署）
git push origin main
```

### 環境檢查
```powershell
gh run list --repo alanlin0604/HeartBox --limit 5
gh run view <RUN_ID>
```
