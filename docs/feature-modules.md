# HeartBox 功能模組總覽

*Last updated: 2026-02-20*

---

## 模組分類總覽

| # | 大類 | 模組數 | 說明 |
|---|------|--------|------|
| 1 | 用戶認證與帳號管理 | 6 | 註冊、登入、密碼、多裝置、資料匯出、帳號刪除 |
| 2 | 日記與筆記系統 | 8 | CRUD、加密、附件、搜尋、垃圾桶、批次操作、每日提示 |
| 3 | AI 智能分析與聊天 | 4 | 情緒分析、AI 回饋、多輪對話、圖像辨識 |
| 4 | 數據分析與視覺化 | 8 | 趨勢圖、日曆熱圖、年度像素、天氣/活動/睡眠相關性、警報 |
| 5 | 諮商師平台 | 6 | 申請審核、檔案管理、排班、預約、報價 |
| 6 | 即時通訊與通知 | 5 | 對話管理、訊息收發、WebSocket、通知系統、筆記分享 |
| 7 | 心理健康工具 | 4 | PHQ-9、GAD-7、呼吸練習、冥想計時器 |
| 8 | 教育學習系統 | 4 | 心理文章、結構化課程、進度追蹤、課程完成 |
| 9 | 週報與治療報告 | 3 | AI 週報、治療師報告、PDF 匯出 |
| 10 | 成就與遊戲化 | 2 | 30 項成就徽章、自動解鎖通知 |
| 11 | 管理後台 | 4 | 系統統計、用戶管理、諮商師審核、回饋管理 |
| 12 | 安全與合規 | 4 | AES-256 加密、稽核日誌、速率限制、GDPR 合規 |
| 13 | 國際化與個人化 | 4 | 三語支援、主題切換、語言偏好、本地化工具 |

**合計：62 個功能模組**

---

## 一、用戶認證與帳號管理（6 個模組）

### 1.1 用戶註冊
- **說明**：帳號建立，密碼強度驗證（最少 8 字元）
- **前端**：`RegisterPage.jsx`、`PasswordField.jsx`（強度指示器）
- **後端**：`RegisterView` → `UserRegistrationSerializer`
- **API**：`POST /api/auth/register/`
- **限流**：5 次/小時

### 1.2 登入與 Token 管理
- **說明**：JWT 登入（含 Token 版本號），支援「記住我」，自動刷新
- **前端**：`LoginPage.jsx`、`AuthContext.jsx`、`tokenStorage.js`
- **後端**：`LoginView`（VersionedTokenObtainPairSerializer）、`RefreshView`
- **API**：`POST /api/auth/login/`、`POST /api/auth/refresh/`
- **限流**：登入 10 次/小時、刷新 30 次/小時
- **安全**：Token 版本比對防重播攻擊

### 1.3 密碼管理
- **說明**：忘記密碼（Email 重設）、修改密碼（需驗證舊密碼）
- **前端**：`ForgotPasswordPage.jsx`、`ResetPasswordPage.jsx`、`SettingsPage.jsx`
- **後端**：`ForgotPasswordView`（1 秒延遲防時間攻擊）、`ResetPasswordView`、`ProfileView`
- **API**：`POST /api/auth/password/forgot/`、`POST /api/auth/password/reset/`
- **限流**：5 次/小時

### 1.4 多裝置會話管理
- **說明**：一鍵登出所有其他裝置，Token 版本輪替使舊 Token 失效
- **前端**：`SettingsPage.jsx`
- **後端**：`LogoutOtherDevicesView`（遞增 `token_version`）
- **API**：`POST /api/auth/logout-other-devices/`

### 1.5 個人資料管理
- **說明**：更新暱稱、Email、個人簡介、頭像
- **前端**：`SettingsPage.jsx`
- **後端**：`ProfileView` → `UserProfileSerializer`
- **API**：`GET/PATCH /api/auth/profile/`

### 1.6 資料匯出與帳號刪除（GDPR）
- **說明**：全量 JSON/CSV 匯出（最多 5000 筆）、密碼確認後永久刪除帳號
- **前端**：`SettingsPage.jsx`
- **後端**：`ExportDataView`、`ExportCSVView`、`DeleteAccountView`（atomic transaction）
- **API**：`GET /api/auth/export/`、`GET /api/auth/export/csv/`、`POST /api/auth/delete-account/`
- **限流**：匯出 5 次/小時、刪除 5 次/小時

---

## 二、日記與筆記系統（8 個模組）

### 2.1 筆記 CRUD
- **說明**：建立、閱讀、編輯、刪除心情日記，支援富文本（TipTap）
- **前端**：`JournalPage.jsx`、`NoteDetailPage.jsx`、`NoteForm.jsx`、`EditorToolbar.jsx`
- **後端**：`MoodNoteViewSet`（list / create / retrieve / update / destroy）
- **API**：`GET/POST /api/notes/`、`GET/PATCH/DELETE /api/notes/{id}/`
- **加密**：內容以 Fernet AES-256 加密儲存，`search_text` 存明文前 500 字供搜尋
- **Metadata**：天氣、溫度、地點、活動標籤（JSON）

### 2.2 筆記釘選
- **說明**：將重要筆記置頂顯示
- **前端**：`NoteCard.jsx`（釘選圖示）
- **後端**：`MoodNoteViewSet.toggle_pin`
- **API**：`POST /api/notes/{id}/toggle_pin/`

### 2.3 圖片附件
- **說明**：上傳圖片至筆記（單檔 10MB，每用戶上限 500 張）
- **前端**：`NoteForm.jsx`（拖放上傳）
- **後端**：`NoteAttachmentUploadView`（Magic Number 驗證防 MIME 偽造）
- **API**：`POST /api/notes/{id}/attachments/`
- **限流**：50 次/小時

### 2.4 進階搜尋與篩選
- **說明**：全文搜尋 + 多維度篩選（情緒、壓力、日期、標籤）
- **前端**：`SearchFilterPanel.jsx`（受控輸入 + 防抖）、`HighlightText.jsx`
- **後端**：`services/search.py` → `search_notes()`
- **API**：`GET /api/notes/?search=...&sentiment_min=...&sentiment_max=...&stress_min=...&stress_max=...&date_from=...&date_to=...&tag=...`
- **搜尋歷史**：前端 localStorage 記錄最近 10 筆

### 2.5 垃圾桶與軟刪除
- **說明**：刪除筆記進入垃圾桶（軟刪除），可還原或永久刪除
- **前端**：`JournalPage.jsx`（垃圾桶分頁）
- **後端**：`MoodNoteViewSet.trash` / `restore` / `permanent_delete`
- **API**：`GET /api/notes/trash/`、`POST /api/notes/{id}/restore/`、`DELETE /api/notes/{id}/permanent-delete/`
- **上限**：垃圾桶最多顯示 200 筆

### 2.6 批次刪除
- **說明**：一次刪除最多 50 筆筆記
- **前端**：`JournalPage.jsx`（多選模式）
- **後端**：`MoodNoteViewSet.batch_delete`
- **API**：`POST /api/notes/batch_delete/`

### 2.7 每日寫作提示
- **說明**：根據近 7 天情緒趨勢，AI 生成個人化寫作提示（三語）；無 API Key 時使用預設模板
- **前端**：`JournalPage.jsx`（提示卡片）
- **後端**：`DailyPromptView`（快取 24 小時）
- **API**：`GET /api/daily-prompt/`

### 2.8 圖像感知 AI 重新分析
- **說明**：使用 GPT-4o Vision 結合附件圖片重新分析筆記情緒
- **前端**：`NoteDetailPage.jsx`（重新分析按鈕）
- **後端**：`MoodNoteViewSet.reanalyze` → `ai_engine.analyze_with_images()`
- **API**：`POST /api/notes/{id}/reanalyze/`

---

## 三、AI 智能分析與聊天（4 個模組）

### 3.1 自動情緒與壓力分析
- **說明**：筆記建立/更新時自動分析：情緒分數（-1.0 ~ 1.0）、壓力指數（0 ~ 10）、AI 回饋文字
- **後端**：`MoodNoteViewSet._run_ai_analysis()` → `ai_engine.analyze()`
- **三級降級策略**：
  1. OpenAI GPT-4o-mini（JSON 結構化輸出）
  2. 本地中文關鍵字匹配（Jieba 分詞）
  3. 基礎模板回覆
- **RAG 強化**：情緒分數 < -0.4 時啟用 ChromaDB + LangChain 知識庫回饋

### 3.2 AI 回饋生成
- **說明**：依據情緒分數提供差異化回饋
- **後端**：`services/ai_engine.py`
- **策略**：
  - 負面情緒（< -0.4）：RAG 知識庫回饋（專業心理學建議）
  - 其他情緒：OpenAI 個人化回饋 → 本地回饋 → 模板回饋

### 3.3 多輪 AI 對話
- **說明**：多會話制 AI 聊天助手，支援會話管理（建立、釘選、重命名、刪除）
- **前端**：`AIChatPage.jsx`
- **後端**：`AIChatSessionListCreateView`、`AIChatSessionDetailView`、`AIChatSendMessageView`
- **API**：
  - `GET/POST /api/ai-chat/sessions/`
  - `GET/PATCH/DELETE /api/ai-chat/sessions/{id}/`
  - `POST /api/ai-chat/sessions/{id}/messages/`
- **特色**：
  - 20 則歷史上下文送入 AI
  - 首條訊息自動生成會話標題
  - 使用者訊息即時情緒分析
  - 危機偵測（含各地心理諮詢熱線）
  - 三語系統提示（zh-TW / en / ja）
  - 分頁載入（每頁 50 則）
- **限流**：30 次/小時

### 3.4 對話情緒追蹤
- **說明**：每則使用者訊息即時計算情緒分數與壓力指數
- **後端**：`services/ai_chat.py` → `analyze_user_message()`
- **儲存**：`AIChatMessage.sentiment_score`、`AIChatMessage.stress_index`

---

## 四、數據分析與視覺化（8 個模組）

### 4.1 情緒趨勢圖
- **說明**：每日/每週/每月情緒趨勢折線圖，含寫作連續天數統計
- **前端**：`DashboardPage.jsx`（Recharts 折線圖）
- **後端**：`AnalyticsView` → `services/analytics.py` → `get_mood_trends()`
- **API**：`GET /api/analytics/?period=week&lookback_days=30`
- **快取**：5 分鐘

### 4.2 壓力雷達圖
- **說明**：多維度壓力視覺化（按標籤分類）
- **前端**：`DashboardPage.jsx`、`StressRadarChart.jsx`（Recharts Radar）
- **後端**：`services/analytics.py` → `get_stress_by_tag()`

### 4.3 日曆熱圖
- **說明**：月曆格式顯示每日情緒色彩
- **前端**：`DashboardPage.jsx`、`MoodCalendar.jsx`
- **後端**：`CalendarView` → `get_calendar_data()`
- **API**：`GET /api/analytics/calendar/?year=2026&month=2`
- **快取**：5 分鐘

### 4.4 年度像素圖
- **說明**：GitHub 風格年度活動格，依情緒分數著色
- **前端**：`DashboardPage.jsx`、`YearInPixels.jsx`
- **後端**：`YearPixelsView` → `get_year_pixels()`
- **API**：`GET /api/analytics/year-pixels/?year=2026`
- **快取**：1 小時

### 4.5 天氣-情緒相關性
- **說明**：Pearson 相關係數分析天氣條件對情緒的影響
- **後端**：`services/analytics.py` → `get_mood_weather_correlation()`
- **依賴**：SciPy（統計計算）

### 4.6 活動-情緒相關性
- **說明**：分析哪些活動標籤與正面情緒最相關
- **後端**：`services/analytics.py` → `get_activity_mood_correlation()`

### 4.7 睡眠-情緒相關性
- **說明**：分析睡眠品質（metadata）對隔日情緒的影響
- **後端**：`services/analytics.py` → `get_sleep_mood_correlation()`

### 4.8 情緒警報
- **說明**：偵測連續負面情緒模式，發出高/中嚴重性警報
- **前端**：`JournalPage.jsx`、`AlertBanner.jsx`
- **後端**：`AlertsView` → `services/alerts.py` → `check_mood_alerts()`
- **API**：`GET /api/alerts/`

---

## 五、諮商師平台（6 個模組）

### 5.1 諮商師申請與審核
- **說明**：用戶提交執照號碼、專長、自我介紹申請成為諮商師；管理員審核
- **前端**：`CounselorListPage.jsx`（申請表單分頁）
- **後端**：`CounselorApplyView`、`AdminCounselorActionView`（approve / reject）
- **API**：`POST /api/counselors/apply/`、`POST /api/admin/counselors/{id}/action/`
- **狀態流程**：pending → approved / rejected

### 5.2 諮商師檔案管理
- **說明**：已審核諮商師更新個人檔案、費率、顯示名稱
- **前端**：`CounselorListPage.jsx`（個人檔案分頁）
- **後端**：`CounselorMyProfileView`
- **API**：`GET/PATCH /api/counselors/me/`
- **欄位**：display_name、specialty、introduction、hourly_rate、currency

### 5.3 諮商師目錄
- **說明**：瀏覽已審核的諮商師列表（排除自己）
- **前端**：`CounselorListPage.jsx`（瀏覽分頁）
- **後端**：`CounselorListView`
- **API**：`GET /api/counselors/`

### 5.4 排班管理
- **說明**：諮商師設定每週可用時段（星期幾 + 開始/結束時間）
- **前端**：`ScheduleManager.jsx`
- **後端**：`TimeSlotListView`
- **API**：`GET/POST/DELETE /api/schedule/`

### 5.5 預約系統
- **說明**：查詢可用時段 → 建立預約 → 確認/取消/完成
- **前端**：`BookingPanel.jsx`
- **後端**：`AvailableSlotsView`、`BookingCreateView`（行級鎖防衝突）、`BookingActionView`
- **API**：
  - `GET /api/counselors/{id}/available/?date=YYYY-MM-DD`
  - `POST /api/bookings/create/`
  - `GET /api/bookings/`
  - `POST /api/bookings/{id}/action/`（confirm / cancel / complete）
- **狀態流程**：pending → confirmed → completed（或 cancelled）
- **安全**：`select_for_update()` 行級鎖防止重複預約
- **限流**：20 次/小時
- **自動**：預約自動帶入諮商師費率

### 5.6 報價訊息
- **說明**：諮商師在對話中發送服務報價（描述、價格、幣別），用戶可接受/拒絕
- **前端**：`ChatPage.jsx`（報價卡片 UI）
- **後端**：`MessageListView`（message_type='quote'）、`QuoteActionView`
- **API**：`POST /api/conversations/{id}/messages/{msg_id}/quote-action/`
- **權限**：僅已審核諮商師可發送報價

---

## 六、即時通訊與通知（5 個模組）

### 6.1 對話管理
- **說明**：與諮商師建立一對一對話（每對唯一），列表、刪除
- **前端**：`ChatPage.jsx`
- **後端**：`ConversationListView`、`ConversationCreateView`、`ConversationDeleteView`
- **API**：`GET /api/conversations/`、`POST /api/conversations/create/`、`DELETE /api/conversations/{id}/`
- **最佳化**：annotation 預載最後訊息、未讀數、select_related 諮商師檔案

### 6.2 即時訊息收發
- **說明**：文字訊息收發，支援已讀追蹤、HTML 標籤過濾
- **前端**：`ChatPage.jsx`
- **後端**：`MessageListView`
- **API**：`GET/POST /api/conversations/{id}/messages/`
- **限制**：單則上限 5000 字元
- **限流**：60 次/小時

### 6.3 WebSocket 即時推播
- **說明**：Django Channels 雙向 WebSocket 通訊
- **後端**：
  - `ChatConsumer`（`ws/chat/{conv_id}/`）— 即時聊天
  - `NotificationConsumer`（`ws/notifications/`）— 通知推播
- **特色**：
  - 首條訊息 JWT 認證（避免 Token 放 URL）
  - 心跳檢測（30 秒 ping/pong）
  - 群組廣播（per-conversation / per-user）

### 6.4 通知系統
- **說明**：系統通知（訊息、預約、分享、系統事件），支援已讀標記
- **前端**：`NotificationBell.jsx`（下拉選單 + 未讀數）
- **後端**：`NotificationListView`、`NotificationReadView`
- **API**：`GET /api/notifications/`、`POST /api/notifications/read/`
- **類型**：message / booking / share / system
- **分頁**：每頁 50 筆

### 6.5 筆記分享
- **說明**：將筆記分享給諮商師（可匿名），諮商師端查看收到的分享
- **前端**：`ShareNoteButton.jsx`
- **後端**：`ShareNoteView`、`SharedNotesReceivedView`
- **API**：`POST /api/notes/{id}/share/`、`GET /api/shared-notes/`
- **防重複**：unique_together (note, shared_with)
- **自動通知**：分享時自動推播通知給諮商師

---

## 七、心理健康工具（4 個模組）

### 7.1 PHQ-9 憂鬱症篩檢
- **說明**：9 題患者健康問卷（每題 0-3 分，總分 0-27）
- **前端**：`AssessmentsPage.jsx`（互動式問卷 + 歷史折線圖）
- **後端**：`SelfAssessmentListCreateView`（type=phq9，驗證 9 題 × 0-3 分）
- **API**：`GET/POST /api/assessments/?type=phq9`
- **嚴重度分級**：極輕（≤4）/ 輕度（≤9）/ 中度（≤14）/ 中重度（≤19）/ 重度（>19）

### 7.2 GAD-7 焦慮症篩檢
- **說明**：7 題廣泛性焦慮量表（每題 0-3 分，總分 0-21）
- **前端**：`AssessmentsPage.jsx`
- **後端**：`SelfAssessmentListCreateView`（type=gad7，驗證 7 題 × 0-3 分）
- **API**：`GET/POST /api/assessments/?type=gad7`
- **嚴重度分級**：極輕（≤4）/ 輕度（≤9）/ 中度（≤14）/ 重度（>14）

### 7.3 呼吸練習
- **說明**：引導式呼吸運動，含視覺化呼吸圈動畫
- **前端**：`BreathingPage.jsx`（呼吸分頁）
- **運動類型**：
  - 4-7-8 呼吸法（吸 4 秒、屏 7 秒、呼 8 秒）
  - 方盒呼吸（吸 4 秒、屏 4 秒、呼 4 秒、屏 4 秒）
  - 深呼吸（吸 5 秒、屏 2 秒、呼 5 秒）
- **紀錄**：完成後寫入 `WellnessSession`
- **API**：`POST /api/wellness-sessions/`

### 7.4 冥想計時器
- **說明**：可選時長（1 / 3 / 5 / 10 / 15 分鐘），含環境白噪音（Web Audio API）
- **前端**：`BreathingPage.jsx`（冥想分頁）
- **紀錄**：完成後寫入 `WellnessSession`（session_type='meditation'）

---

## 八、教育學習系統（4 個模組）

### 8.1 心理教育文章
- **說明**：5 大類專業文章（CBT、正念、情緒、壓力、睡眠），三語支援
- **前端**：`PsychoContentPage.jsx`、`LessonPage.jsx`
- **後端**：`PsychoArticleListView`、`PsychoArticleDetailView`
- **API**：`GET /api/articles/`、`GET /api/articles/{id}/`
- **種子資料**：16 篇預建文章（WHO、APA、NICE 等學術來源）
- **自動追蹤**：瀏覽文章時自動建立 `UserLessonProgress`

### 8.2 結構化課程
- **說明**：4 門課程，每門含 3-5 堂課，支援三語標題與描述
- **前端**：`PsychoContentPage.jsx`（課程分頁）、`CourseDetailPage.jsx`
- **後端**：`CourseListView`（含 annotation 課堂數）、`CourseDetailView`
- **API**：`GET /api/courses/`、`GET /api/courses/{id}/`
- **課程列表**：
  - CBT 認知行為基礎（🧠）— 3 堂
  - 壓力紓解工具箱（🌿）— 5 堂
  - 情緒智慧（❤️）— 4 堂
  - 正念與身心健康（🧘）— 4 堂

### 8.3 課堂進度追蹤
- **說明**：記錄每堂課的開始與完成狀態
- **後端**：`UserLessonProgress`（unique_together: user + article）
- **API**：`POST /api/lessons/{id}/complete/`

### 8.4 學習進度視覺化
- **說明**：儀表板顯示已開始課程數、已完成課堂數、整體進度百分比
- **前端**：`DashboardPage.jsx`（課程推薦卡片）
- **後端**：`CourseListSerializer`（`_lesson_count` annotation + `completed_ids` context）

---

## 九、週報與治療報告（3 個模組）

### 9.1 AI 每週摘要
- **說明**：自動生成每週情緒/壓力平均、熱門活動、AI 洞察文字
- **前端**：`WeeklySummaryPage.jsx`
- **後端**：`WeeklySummaryView`（OpenAI 生成 → 快取）、`WeeklySummaryListView`
- **API**：`GET /api/weekly-summary/?week_start=YYYY-MM-DD`、`GET /api/weekly-summary/list/`
- **資料**：mood_avg、stress_avg、note_count、top_activities（JSON）、ai_summary

### 9.2 治療師報告
- **說明**：生成可分享的治療報告（情緒趨勢快照 + 評估資料），透過 UUID Token 公開連結分享
- **前端**：`WeeklySummaryPage.jsx`（生成按鈕）、`TherapistReportPublicPage.jsx`（公開頁）
- **後端**：`TherapistReportCreateView`、`TherapistReportPublicView`（匿名存取 + AnonRateThrottle）
- **API**：`POST /api/reports/`、`GET /api/reports/list/`、`GET /api/reports/public/{token}/`
- **有效期**：30 天自動過期

### 9.3 PDF / CSV 匯出
- **說明**：將筆記匯出為 PDF（含情緒、壓力、標籤）或 CSV 格式
- **前端**：`ExportPDFButton.jsx`（日期範圍選擇）
- **後端**：`ExportPDFView`（ReportLab）、`ExportCSVView`
- **API**：`GET /api/auth/export/`、`GET /api/auth/export/csv/`
- **限流**：5 次/小時
- **語言**：支援 zh-TW / en / ja

---

## 十、成就與遊戲化（2 個模組）

### 10.1 成就系統（30 項）
- **說明**：6 大類成就徽章，依使用行為自動計算進度

| 類別 | 成就 | 解鎖條件 |
|------|------|----------|
| **寫作** | first_note | 寫下第 1 篇日記 |
| | notes_10 / notes_50 / notes_100 / notes_200 | 累計 10/50/100/200 篇 |
| | long_writer | 單篇超過 500 字 |
| **持續** | streak_3 / streak_7 / streak_30 | 連續寫作 3/7/30 天 |
| **情緒** | mood_explorer | 記錄多種情緒 |
| | positive_streak | 連續正面情緒 |
| | mood_improver | 情緒好轉趨勢 |
| | self_aware | 使用進階分析 |
| **社交** | first_share | 首次分享筆記 |
| | first_booking | 首次預約諮商 |
| | first_ai_chat / ai_chat_10 | AI 對話次數 |
| **探索** | night_owl | 深夜寫作（0-5 點） |
| | early_bird | 早起寫作（5-7 點） |
| | pin_master | 釘選 5 篇筆記 |
| **健康** | 呼吸/冥想/課程相關 | 完成健康活動 |

- **前端**：`AchievementsPage.jsx`（分類過濾 + 進度條）
- **後端**：`services/achievements.py`（批次聚合查詢）、`AchievementsView`
- **API**：`GET /api/achievements/`、`POST /api/achievements/check/`

### 10.2 自動解鎖通知
- **說明**：建立筆記時自動檢查成就，透過 Response Header 通知前端
- **後端**：`MoodNoteViewSet.perform_create` → `check_achievements()`
- **通知方式**：`X-New-Achievements` Header（逗號分隔的成就 ID）
- **容錯**：成就檢查失敗不影響筆記建立

---

## 十一、管理後台（4 個模組）

### 11.1 系統統計儀表板
- **說明**：總用戶數、今日新增、活躍用戶、總筆記數、待審諮商師數
- **前端**：`AdminPage.jsx`（統計卡片）
- **後端**：`AdminStatsView`（合併聚合查詢）
- **API**：`GET /api/admin/stats/`
- **權限**：僅 `is_staff=True`

### 11.2 用戶管理
- **說明**：搜尋用戶（帳號/Email）、編輯用戶資料、管理管理員權限
- **前端**：`AdminPage.jsx`（用戶列表分頁）
- **後端**：`AdminUserListView`、`AdminUserDetailView`（防止自我降級）
- **API**：`GET /api/admin/users/`、`PATCH /api/admin/users/{id}/`

### 11.3 諮商師審核
- **說明**：檢視待審核諮商師申請，批准或拒絕
- **前端**：`AdminPage.jsx`（諮商師分頁）
- **後端**：`AdminCounselorListView`、`AdminCounselorActionView`
- **API**：`GET /api/admin/counselors/?status=pending`、`POST /api/admin/counselors/{id}/action/`

### 11.4 回饋管理
- **說明**：用戶提交 1-5 星回饋，管理員查看所有回饋
- **前端**：`FeedbackWidget.jsx`（提交）、`AdminPage.jsx`（列表）
- **後端**：`FeedbackCreateView`、`AdminFeedbackListView`
- **API**：`POST /api/feedback/`、`GET /api/admin/feedback/`

---

## 十二、安全與合規（4 個模組）

### 12.1 AES-256 內容加密
- **說明**：所有日記內容以 Fernet（AES-CBC + HMAC-SHA256）加密儲存
- **後端**：`services/encryption.py`（EncryptionService 單例）
- **特色**：
  - MultiFernet 金鑰輪替支援
  - `search_text` 儲存明文前 500 字元供搜尋（不加密）
  - `content_preview` 讀取 `search_text` 前 100 字元（避免解密開銷）

### 12.2 稽核日誌
- **說明**：記錄所有安全相關操作，含 IP 位址與詳細資訊
- **後端**：`services/audit.py` → `log_action()`、`AuditLog` Model
- **追蹤動作**：login、password_change、password_reset、note_create / update / delete / restore / permanent_delete、account_delete、export_data
- **索引**：user + created_at、action + created_at

### 12.3 速率限制
- **說明**：11 個端點級 Throttle 防止濫用
- **後端**：`throttles.py`

| 端點 | 限制 |
|------|------|
| 登入 | 10 次/小時 |
| 註冊 | 5 次/小時 |
| 密碼重設 | 5 次/小時 |
| Token 刷新 | 30 次/小時 |
| 筆記建立 | 30 次/小時 |
| 上傳 | 50 次/小時 |
| 匯出 | 5 次/小時 |
| 預約 | 20 次/小時 |
| 訊息 | 60 次/小時 |
| AI 聊天 | 30 次/小時 |
| 刪除帳號 | 5 次/小時 |
| 匿名存取 | 100 次/小時 |

### 12.4 安全標頭與防護
- **說明**：CSP、HSTS、CSRF、CORS、Referrer-Policy、Permissions-Policy
- **後端**：`middleware.py` → `ContentSecurityPolicyMiddleware`
- **其他**：
  - 密碼重設 1 秒延遲（防時間攻擊）
  - Magic Number 檔案驗證（防 MIME 偽造）
  - Token 版本化（防重播攻擊）
  - 附件上傳 `select_for_update()` 配額鎖

---

## 十三、國際化與個人化（4 個模組）

### 13.1 三語支援
- **說明**：繁體中文（zh-TW）、英文（en）、日文（ja）完整支援
- **前端**：`LanguageContext.jsx`（動態翻譯函式 `t()`）
- **後端**：Model 三語欄位（title_zh / title_en / title_ja）、Accept-Language 偵測
- **涵蓋範圍**：UI 文字、AI 回覆、文章內容、課程名稱、每日提示

### 13.2 主題切換
- **說明**：深色/淺色模式切換，偵測系統偏好，localStorage 持久化
- **前端**：`ThemeContext.jsx`
- **UI 風格**：Glassmorphism（毛玻璃效果）

### 13.3 語言偏好
- **說明**：用戶可隨時切換語言，前端即時生效
- **前端**：`Layout.jsx`（語言選單）、`LoginPage.jsx`（登入前選擇）
- **共用**：`utils/locales.js` → `LANG_OPTIONS`

### 13.4 日期與時區本地化
- **說明**：依語言自動選擇日期格式與時區
- **前端**：`utils/locales.js` → `LOCALE_MAP`、`TZ_MAP`

---

## 附錄：模組依賴關係圖

```
用戶認證 ──────────────────────────────────────────────────┐
    │                                                      │
    ├── 日記系統 ──┬── AI 分析 ──── 數據分析               │
    │              │                  │                     │
    │              ├── 圖片附件       ├── 情緒警報          │
    │              │                  │                     │
    │              ├── 搜尋篩選       ├── 年度像素          │
    │              │                  │                     │
    │              └── 垃圾桶         └── 日曆熱圖          │
    │                                                      │
    ├── 諮商師平台 ──┬── 排班管理                          │
    │                ├── 預約系統                           │
    │                └── 報價訊息 ── 即時通訊 ── WebSocket  │
    │                                    │                 │
    │                                    └── 通知系統      │
    │                                                      │
    ├── 心理健康工具 ──┬── PHQ-9 / GAD-7                   │
    │                  └── 呼吸 / 冥想                     │
    │                                                      │
    ├── 教育學習 ──┬── 文章                                │
    │              └── 課程 ── 進度追蹤                    │
    │                                                      │
    ├── 週報與報告 ──┬── AI 週報                           │
    │                ├── 治療師報告                         │
    │                └── PDF/CSV 匯出                      │
    │                                                      │
    ├── 成就系統 ←─── 筆記/社交/健康活動觸發               │
    │                                                      │
    ├── 管理後台 ──── 用戶管理 / 諮商師審核 / 回饋         │
    │                                                      │
    └── 安全合規 ──── 加密 / 稽核 / 限流 / 安全標頭 ──────┘
```

---

## 統計

| 項目 | 數量 |
|------|------|
| 功能大類 | 13 |
| 功能模組 | 62 |
| API 端點 | 55+ |
| 前端頁面 | 24 |
| 前端元件 | 22 |
| 後端服務 | 10 |
| 資料表 | 22 |
| 速率限制 | 12 |
| 支援語言 | 3（zh-TW / en / ja） |
