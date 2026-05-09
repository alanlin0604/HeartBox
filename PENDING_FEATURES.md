# HeartBox 功能完成度

> 紀錄所有功能的實際完成狀態。每次完成新東西就更新一次。

**最後更新：** 2026-05-09
**完成度：** 10 / 11 (91%)

---

## ✅ 已完成 (10)

### Tier A — 日記增強

- **A1. 標籤系統** — 自訂標籤、過濾、標籤雲
- **A2. 日記提醒** — 每日提醒、連續天數、`JournalStreak` model
- **A3. 日記回顧** — 一年前今天、月/年度回顧

### Tier B — AI

- **B1. AI 日記建議** — 寫作提示、情緒洞察
- **B2. 情緒預測** — 趨勢、壓力預警

### Tier C — 社交

- **C1. 匿名分享社群** — `PublicPost` / `PostReaction` / `PostReport` model；3 種反應；
  `PostReport` 8 種理由 + 自動隱藏門檻（3 個獨立檢舉）；admin 審核 endpoint；
  關鍵字內容過濾；反應通知（保持匿名）。
  Files: `backend/api/community_views.py`, `backend/api/services/content_moderation.py`,
  `frontend/src/pages/CommunityPage.jsx`.
- **C2. 好友系統** — `Friendship` / `FriendRequest` / `SharedNote` / `FriendComment` model；
  搜尋 / 邀請 / 接受 / 拒絕 / 移除；分享日記給好友；好友動態 feed；streak 排行榜
  （Tab 頁面：好友 / 排行榜 / 共享日記 / 動態）。
  Files: `backend/api/friends_views.py`, `backend/api/services/friends_service.py`,
  `frontend/src/pages/FriendsPage.jsx`, `frontend/src/components/friends/*.jsx`.

### Tier D — 健康分析

- **D1. 習慣追蹤器** — `Habit` / `HabitLog` model；CRUD + 每日打卡（idempotent，可 undo）；
  打卡備註；90 天熱力圖；習慣與心情關聯分析（`HabitAnalyticsView`）。
  Files: `backend/api/views/health.py` (HabitViewSet), `frontend/src/components/HabitCard.jsx`.

### Tier E — 個人化

- **E1. 個人化儀表板** — `DashboardLayout` / `UserMetric` model；可拖拽 widget；
  目前 widget：streak / mood trends / on-this-day / habit check-in / AI suggestions / sleep stats。
  Files: `frontend/src/pages/PersonalDashboardPage.jsx`, `frontend/src/components/dashboard/widgets/*.jsx`.
- **E2. 數據匯入** — CSV / JSON / Day One / Journey 格式；欄位 mapping UI（後端真套用）；
  > 500 行走 Celery `import_notes_task` 背景處理（無 broker 自動 fallback 到 daemon thread）；
  `ImportJob` model + 進度輪詢 endpoint；前端進度條。
  Files: `backend/api/services/import_service.py`, `backend/api/tasks.py`,
  `frontend/src/pages/DataImportPage.jsx`.

---

## 🔴 還未做 (1)

### D2. 睡眠深度分析

**現況：** Backend 95% 完整 — `SleepAnalysisView` / `SleepCalendarView` / `SleepTrendsView` /
`SleepInsightsView` 都有真實計算邏輯（`backend/api/services/sleep_analysis.py`，
品質分數、模式辨識、改善建議），前端 `SleepAnalysisPage` 渲染圖表都正常。

**缺：** Apple Health / Health Connect 自動同步 — `HealthSyncView` 是 stub，
依賴使用者手動輸入睡眠資料。

**Blocker：** 整合工作卡在 paused 的 Health Connect crash 調查
（[`docs/health-connect-debug-progress.md`](docs/health-connect-debug-progress.md)）。
等 capgo plugin 在 Galaxy A52 上的 native crash 解了再動。

---

## 加值修復（spec 沒列、做了）

- LoginPage 預熱 + 「正在喚醒伺服器」提示（Cloud Run cold-start UX）
- 登入合併 user payload 省 1 趟 `/profile/` roundtrip
- views.py 3820 行 → 9 個主題模組（auth / notes / analytics / health / counselor /
  messaging / wellness / admin / dashboard）
- CounselorListPage 1240 行 → 9 個 tab 元件
- drf_spectacular schema 78 errors → 0 errors
- Brand 全面換色：紫 → terracotta orange + crimson rose（heart-on-treasure-box logo）
- 版本徽章（每頁右下角小字 `v{時間}-{git-sha}`）
- demo 帳號 seed 指令（Play Store 審查者用）
