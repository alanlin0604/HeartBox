# HeartBox 系統開發元件總覽

*Last updated: 2026-02-20*

---

## 一、前端（Frontend）

**技術棧：** Vite + React 19 + Tailwind CSS v4 + Recharts + TipTap Editor

### 頁面元件（20 個）

| 頁面 | 檔案 | 功能描述 |
|------|------|----------|
| 登入 | `LoginPage.jsx` | JWT 登入、記住我、語言切換 |
| 註冊 | `RegisterPage.jsx` | 帳號註冊、密碼強度驗證 |
| 忘記密碼 | `ForgotPasswordPage.jsx` | 密碼重設 Email 發送 |
| 重設密碼 | `ResetPasswordPage.jsx` | Token 驗證 + 密碼重設 |
| 日記主頁 | `JournalPage.jsx` | 筆記列表、搜尋、篩選、批次操作、垃圾桶 |
| 筆記詳情 | `NoteDetailPage.jsx` | 單篇筆記檢視/編輯、情緒分析、分享、釘選 |
| 儀表板 | `DashboardPage.jsx` | 情緒趨勢、壓力雷達、日曆熱圖、年度像素、課程推薦 |
| 週報 | `WeeklySummaryPage.jsx` | AI 生成的每週情緒摘要 |
| 諮商師列表 | `CounselorListPage.jsx` | 瀏覽諮商師、申請成為諮商師、排程管理 |
| 即時聊天 | `ChatPage.jsx` | 與諮商師即時通訊、報價功能 |
| AI 聊天 | `AIChatPage.jsx` | 多會話 AI 助手、歷史對話管理 |
| 心理文章 | `PsychoContentPage.jsx` | 教育文章瀏覽（Markdown 渲染） |
| 課程詳情 | `CourseDetailPage.jsx` | 線上課程內容與進度 |
| 課堂頁面 | `LessonPage.jsx` | 單堂課程內容 + 完成追蹤 |
| 呼吸練習 | `BreathingPage.jsx` | 引導式呼吸（4-7-8、方盒呼吸、深呼吸） |
| 自我評估 | `AssessmentsPage.jsx` | PHQ-9、GAD-7 量表 + 分數圖表 |
| 設定 | `SettingsPage.jsx` | 個人資料、主題/語言、密碼、匯出、刪除帳號 |
| 成就 | `AchievementsPage.jsx` | 成就徽章系統（6 大類 30 項） |
| 管理後台 | `AdminPage.jsx` | 用戶統計、用戶管理、諮商師審核、回饋檢視 |
| 功能導覽 | `GuidePage.jsx` | 功能介紹頁面 |
| 隱私政策 | `PrivacyPage.jsx` | 隱私權條款 |
| 服務條款 | `TermsPage.jsx` | 使用條款 |
| 報告公開頁 | `TherapistReportPublicPage.jsx` | Token 驗證的公開治療報告 |
| 404 | `NotFoundPage.jsx` | 找不到頁面 |

### UI 元件（22 個）

| 類別 | 元件 | 功能 |
|------|------|------|
| **佈局** | `Layout.jsx` | 主框架：導覽列、路由預載、主題/語言切換 |
| | `NotificationBell.jsx` | 通知下拉選單 + WebSocket 即時推播 |
| **編輯器** | `NoteForm.jsx` | TipTap 富文本編輯器（天氣、活動標籤、心情） |
| | `EditorToolbar.jsx` | 格式工具列（粗體、斜體、列表、程式碼） |
| **搜尋** | `SearchFilterPanel.jsx` | 進階搜尋/篩選（情緒、壓力、日期、標籤） |
| | `HighlightText.jsx` | 搜尋關鍵字高亮 |
| **卡片** | `NoteCard.jsx` | 筆記列表項目（摘要、情緒徽章、標籤） |
| | `MoodBadge.jsx` | 情緒顏色標示（正面/中性/負面） |
| **圖表** | `MoodCalendar.jsx` | 日曆熱圖（每日情緒色彩） |
| | `StressRadarChart.jsx` | 壓力雷達圖（Recharts） |
| | `YearInPixels.jsx` | GitHub 風格年度情緒格 |
| **互動** | `ConfirmModal.jsx` | 確認對話框（鍵盤捕獲、Esc 關閉） |
| | `AlertBanner.jsx` | 高/中嚴重性警報橫幅 |
| | `EmptyState.jsx` | 空狀態 UI |
| | `ErrorBoundary.jsx` | 錯誤邊界 + 回報後端 |
| **功能** | `ExportPDFButton.jsx` | 匯出 PDF/CSV（日期範圍選擇） |
| | `ShareNoteButton.jsx` | 分享筆記給諮商師 |
| | `FeedbackWidget.jsx` | 星級評分 + 文字回饋 |
| | `BookingPanel.jsx` | 諮商預約 UI（日期/時段/價格） |
| | `ScheduleManager.jsx` | 諮商師排班管理 |
| | `PasswordField.jsx` | 密碼輸入（強度指示器） |
| **載入** | `LoadingSpinner.jsx` | 載入指示器 |
| | `SkeletonCard.jsx` / `Skeleton.jsx` | 骨架屏載入動畫 |

### Context 狀態管理（4 個）

| Context | 功能 |
|---------|------|
| `AuthContext.jsx` | 認證狀態、登入/登出、Token 管理 |
| `ThemeContext.jsx` | 深色/淺色主題、系統偏好偵測 |
| `LanguageContext.jsx` | 多語言支援（zh-TW、en、ja）、動態翻譯 |
| `ToastContext.jsx` | Toast 通知系統（成功/錯誤/資訊）、全域 API 錯誤監聽 |

### API 整合層（15 個模組）

| 模組 | 功能 |
|------|------|
| `axios.js` | Axios 實例、Bearer Token 注入、401 自動刷新、請求去重 |
| `auth.js` | 登入、註冊、個人資料、密碼重設、帳號刪除 |
| `notes.js` | 筆記 CRUD + 快取、搜尋、批次刪除、垃圾桶、分享、附件 |
| `analytics.js` | 儀表板分析數據 + 快取 |
| `cache.js` | 客戶端 TTL 快取、前綴清除 |
| `notifications.js` | 通知查詢、已讀標記 |
| `aiChat.js` | AI 聊天 Session/Message CRUD |
| `counselors.js` | 諮商師列表、申請、對話、訊息 |
| `schedule.js` | 時段管理、可用時段查詢、預約 |
| `wellness.js` | 年度像素、每日提示、自評量表、週報、課程、文章 |
| `breathe.js` | 呼吸練習紀錄 |
| `achievements.js` | 成就查詢 + 快取 |
| `alerts.js` | 情緒警報查詢 |
| `feedback.js` | 用戶回饋提交 |
| `admin.js` | 管理後台統計、用戶管理、諮商師審核 |

### 工具函式（3 個）

| 檔案 | 功能 |
|------|------|
| `locales.js` | 日期格式、時區映射、語言選項 |
| `tokenStorage.js` | JWT 儲存（localStorage/sessionStorage）、記住我 |
| `passwordStrength.js` | 密碼強度評估（弱/中/強） |

### 前端依賴

| 套件 | 版本 | 用途 |
|------|------|------|
| React | 19.2.0 | UI 框架 |
| React Router DOM | 7.13.0 | 路由 |
| Tailwind CSS | 4.1.18 | 樣式框架 |
| TipTap | 3.19.0 | 富文本編輯器 |
| Recharts | 3.7.0 | 圖表視覺化 |
| Axios | 1.13.5 | HTTP 客戶端 |
| DOMPurify | 3.3.1 | HTML 消毒 |
| Vite | — | 構建工具 |
| Vitest | — | 測試框架 |

---

## 二、後端（Backend）

**技術棧：** Django 5.2.1 + DRF + SimpleJWT + Channels (WebSocket) + Daphne ASGI

### Views（55+ 個 API 端點）

| 類別 | View | 端點 | 功能 |
|------|------|------|------|
| **認證 (8)** | `RegisterView` | `POST /auth/register/` | 用戶註冊 |
| | `LoginView` | `POST /auth/login/` | JWT 登入（含版本號） |
| | `RefreshView` | `POST /auth/refresh/` | Token 刷新 |
| | `ProfileView` | `GET/PATCH /auth/profile/` | 個人資料 + 改密碼 |
| | `ForgotPasswordView` | `POST /auth/password/forgot/` | 忘記密碼 |
| | `ResetPasswordView` | `POST /auth/password/reset/` | 重設密碼 |
| | `LogoutOtherDevicesView` | `POST /auth/logout-other-devices/` | 登出其他裝置 |
| | `DeleteAccountView` | `POST /auth/delete-account/` | 刪除帳號 |
| **筆記 (7)** | `MoodNoteViewSet` | `/notes/` | CRUD + toggle_pin, batch_delete, trash, restore, permanent_delete, reanalyze |
| **分析 (6)** | `AnalyticsView` | `GET /analytics/` | 情緒趨勢、壓力、相關性（快取 5min） |
| | `CalendarView` | `GET /analytics/calendar/` | 月曆熱圖（快取 5min） |
| | `YearPixelsView` | `GET /analytics/year-pixels/` | 年度像素（快取 1h） |
| | `AlertsView` | `GET /alerts/` | 情緒警報偵測 |
| | `DailyPromptView` | `GET /daily-prompt/` | AI 每日寫作提示 |
| | `ExportPDFView` | `GET /auth/export/` | PDF/JSON 匯出 |
| **成就 (2)** | `AchievementsView` | `GET /achievements/` | 30 項成就 + 進度 |
| | `AchievementCheckView` | `POST /achievements/check/` | 觸發成就檢查 |
| **諮商師 (4)** | `CounselorApplyView` | `POST /counselors/apply/` | 申請諮商師 |
| | `CounselorMyProfileView` | `GET/PATCH /counselors/me/` | 自身檔案管理 |
| | `CounselorListView` | `GET /counselors/` | 瀏覽已審核諮商師 |
| | `AdminCounselorActionView` | `POST /admin/counselors/<id>/action/` | 審核（批准/拒絕） |
| **即時通訊 (5)** | `ConversationListView` | `GET /conversations/` | 對話列表（含最後訊息） |
| | `ConversationCreateView` | `POST /conversations/create/` | 建立對話 |
| | `ConversationDeleteView` | `DELETE /conversations/<id>/` | 刪除對話 |
| | `MessageListView` | `GET/POST /conversations/<id>/messages/` | 訊息收發 |
| | `QuoteActionView` | `POST .../messages/<id>/quote-action/` | 報價接受/拒絕 |
| **預約 (5)** | `TimeSlotListView` | `GET/POST /schedule/` | 時段 CRUD |
| | `AvailableSlotsView` | `GET /counselors/<id>/available/` | 查詢可用時段 |
| | `BookingListView` | `GET /bookings/` | 預約列表 |
| | `BookingCreateView` | `POST /bookings/create/` | 建立預約（行級鎖防衝突） |
| | `BookingActionView` | `POST /bookings/<id>/action/` | 確認/取消/完成 |
| **分享 (2)** | `ShareNoteView` | `POST /notes/<id>/share/` | 分享筆記給諮商師 |
| | `SharedNotesReceivedView` | `GET /shared-notes/` | 收到的分享筆記 |
| **附件 (1)** | `NoteAttachmentUploadView` | `POST /notes/<id>/attachments/` | 上傳圖片（10MB，magic number 驗證） |
| **通知 (2)** | `NotificationListView` | `GET /notifications/` | 通知列表 |
| | `NotificationReadView` | `POST /notifications/read/` | 標記已讀 |
| **AI 聊天 (3)** | `AIChatSessionListCreateView` | `GET/POST /ai-chat/sessions/` | Session 列表/建立 |
| | `AIChatSessionDetailView` | `GET/PATCH/DELETE /ai-chat/sessions/<id>/` | 詳情（分頁 50 則） |
| | `AIChatSendMessageView` | `POST .../sessions/<id>/messages/` | 發訊 + AI 回覆 |
| **評估 (1)** | `SelfAssessmentListCreateView` | `GET/POST /assessments/` | PHQ-9 / GAD-7 量表 |
| **報告 (4)** | `WeeklySummaryView` | `GET /weekly-summary/` | AI 週報生成 |
| | `WeeklySummaryListView` | `GET /weekly-summary/list/` | 週報列表 |
| | `TherapistReportCreateView` | `POST /reports/` | 生成可分享治療報告 |
| | `TherapistReportPublicView` | `GET /reports/public/<token>/` | 公開報告（Token 驗證） |
| **教育 (5)** | `PsychoArticleListView` | `GET /articles/` | 文章列表 |
| | `PsychoArticleDetailView` | `GET /articles/<id>/` | 文章詳情 + 自動追蹤 |
| | `CourseListView` | `GET /courses/` | 課程列表 + 進度 |
| | `CourseDetailView` | `GET /courses/<id>/` | 課程詳情 + 課堂 |
| | `LessonCompleteView` | `POST /lessons/<id>/complete/` | 標記課堂完成 |
| **管理 (4)** | `AdminStatsView` | `GET /admin/stats/` | 用戶/筆記統計 |
| | `AdminUserListView` | `GET /admin/users/` | 用戶列表 |
| | `AdminUserDetailView` | `PATCH /admin/users/<id>/` | 編輯用戶 |
| | `AdminFeedbackListView` | `GET /admin/feedback/` | 回饋列表 |
| **匯出 (2)** | `ExportDataView` | `GET /auth/export/` | JSON 全量匯出 |
| | `ExportCSVView` | `GET /auth/export/csv/` | CSV 匯出 |

### Serializers（27 個）

| 類別 | Serializer | 功能 |
|------|------------|------|
| **認證** | `UserRegistrationSerializer` | 註冊驗證（密碼 min 8 字元） |
| | `UserProfileSerializer` | 用戶資料 + 諮商師狀態 |
| | `AdminUserSerializer` | 管理員用戶檢視 |
| **筆記** | `MoodNoteSerializer` | 完整筆記（加密/解密） |
| | `MoodNoteListSerializer` | 輕量列表（100 字元摘要） |
| **諮商師** | `CounselorProfileSerializer` | 諮商師檔案 |
| | `CounselorListSerializer` | 公開列表（含頭像） |
| | `AdminCounselorSerializer` | 管理員檢視 |
| **通訊** | `MessageSerializer` | 訊息（含發送者頭像） |
| | `ConversationSerializer` | 對話（含最後訊息、未讀數） |
| | `NotificationSerializer` | 通知 |
| **預約** | `TimeSlotSerializer` | 時段 CRUD |
| | `BookingSerializer` | 預約（含用戶/諮商師名稱） |
| **附件** | `NoteAttachmentSerializer` | 檔案元資料 |
| **分享** | `SharedNoteSerializer` | 分享筆記（含摘要、作者） |
| **AI** | `AIChatMessageSerializer` | AI 訊息（含情緒/壓力） |
| | `AIChatSessionSerializer` | AI 會話（含訊息數、最後預覽） |
| **健康** | `SelfAssessmentSerializer` | 評估驗證（phq9=9 題, gad7=7 題） |
| | `WellnessSessionSerializer` | 運動紀錄 |
| | `UserAchievementSerializer` | 成就解鎖 |
| **報告** | `WeeklySummarySerializer` | 週報 |
| | `TherapistReportSerializer` | 治療報告（含分享 URL） |
| | `TherapistReportPublicSerializer` | 公開報告 |
| **教育** | `PsychoArticleSerializer` | 文章（三語） |
| | `CourseLessonSerializer` | 課堂（含完成狀態） |
| | `CourseListSerializer` | 課程列表（含課堂/完成數） |
| | `CourseDetailSerializer` | 課程詳情（含完整課堂列表） |

### 服務層（10 個模組）

| 服務 | 功能 |
|------|------|
| `encryption.py` | Fernet AES-256 加密/解密 + 金鑰輪替（MultiFernet） |
| `ai_engine.py` | 三級降級 AI 分析：OpenAI → 本地中文關鍵字 → 模板回覆；RAG 回饋（ChromaDB + LangChain） |
| `ai_chat.py` | AI 聊天回覆生成（20 則歷史上下文）、本地情緒分析、危機偵測、三語系統提示 |
| `analytics.py` | 情緒趨勢、天氣相關性、日曆資料、年度像素、標籤分析、睡眠-情緒相關、感恩統計 |
| `search.py` | 多條件筆記搜尋（日期、情緒、壓力、標籤、關鍵字） |
| `achievements.py` | 30 項成就系統、批次聚合進度計算、自動解鎖 |
| `pdf_export.py` | ReportLab PDF 生成 |
| `alerts.py` | 情緒警報偵測（連續低分模式） |
| `audit.py` | 稽核日誌（10+ 動作類型）、IP 擷取（支援 X-Forwarded-For） |

### 中介軟體 & WebSocket

| 元件 | 功能 |
|------|------|
| `authentication.py` | VersionedJWTAuthentication — Token 版本比對，防重播攻擊 |
| `middleware.py` → `ContentSecurityPolicyMiddleware` | CSP / Referrer-Policy / Permissions-Policy 安全標頭 |
| `middleware.py` → `JWTAuthMiddleware` | WebSocket JWT 認證（query string 或首條訊息） |
| `consumers.py` → `ChatConsumer` | 即時聊天（行級鎖、報價訊息、通知推播） |
| `consumers.py` → `NotificationConsumer` | 通知頻道（接收用推播） |

### 速率限制（11 個 Throttle）

| Throttle | 限制 |
|----------|------|
| LoginRateThrottle | 10 次/小時 |
| RegisterRateThrottle | 5 次/小時 |
| PasswordResetRateThrottle | 5 次/小時 |
| RefreshTokenThrottle | 30 次/小時 |
| NoteCreateThrottle | 30 次/小時 |
| UploadThrottle | 50 次/小時 |
| ExportThrottle | 5 次/小時 |
| BookingThrottle | 20 次/小時 |
| MessageThrottle | 60 次/小時 |
| AIChatThrottle | 30 次/小時 |
| DeleteAccountThrottle | 5 次/小時 |

### 後端依賴

| 套件 | 版本 | 用途 |
|------|------|------|
| Django | 5.2.1 | Web 框架 |
| DRF | 3.16.0 | REST API |
| SimpleJWT | 5.5.0 | JWT 認證 |
| Channels + Daphne | 4.2.0 | WebSocket + ASGI |
| OpenAI | 1.78.1 | GPT-4o AI 分析 |
| LangChain | 0.3.25 | RAG 框架 |
| ChromaDB | 1.0.20 | 向量資料庫 |
| Jieba | 0.42.1 | 中文分詞 |
| Pandas | 2.2.3 | 數據分析 |
| SciPy | 1.15.3 | 統計計算 |
| ReportLab | 4.4.0 | PDF 生成 |
| Cryptography | 44.0.3 | Fernet 加密 |
| Psycopg2 | 2.9.10 | PostgreSQL 驅動 |
| Whitenoise | 6.8.2 | 靜態檔案 |
| Sentry SDK | 2.19.2 | 錯誤追蹤 |
| Pillow | 11.1.0 | 圖片處理 |
| django-cors-headers | 4.7.0 | CORS |
| django-storages | 1.14.4 | GCS 儲存 |

---

## 三、資料庫（Database）

**引擎：** Neon PostgreSQL（生產）/ SQLite（測試/開發回退）

### 資料表（22 張）

| # | Model | 用途 | 關鍵欄位 | 關聯 |
|---|-------|------|----------|------|
| 1 | **CustomUser** | 用戶帳號 | bio, avatar, token_version | 系統核心，被 15+ 表 FK |
| 2 | **MoodNote** | 加密日記 | encrypted_content, sentiment_score, stress_index, ai_feedback, search_text, is_pinned, is_deleted, metadata(JSON) | FK→User |
| 3 | **CounselorProfile** | 諮商師檔案 | license_number(unique), display_name, specialty, hourly_rate, currency, status | O2O→User |
| 4 | **Conversation** | 聊天對話 | user, counselor | FK→User×2, unique_together |
| 5 | **Message** | 對話訊息 | content, message_type(text/quote), metadata, is_read | FK→Conversation, FK→User |
| 6 | **Notification** | 系統通知 | type(message/booking/share/system), title, message, data(JSON), is_read | FK→User |
| 7 | **NoteAttachment** | 筆記附件 | file, file_type(image/audio), original_name | FK→MoodNote |
| 8 | **TimeSlot** | 諮商師時段 | day_of_week(0-6), start_time, end_time, is_active | FK→User |
| 9 | **Booking** | 諮商預約 | date, start_time, end_time, status, price | FK→User×2 |
| 10 | **Feedback** | 用戶回饋 | rating(1-5), content | FK→User |
| 11 | **SharedNote** | 分享筆記 | is_anonymous, shared_at | FK→MoodNote, FK→User, unique_together |
| 12 | **AIChatSession** | AI 聊天會話 | title, is_active, is_pinned | FK→User |
| 13 | **AIChatMessage** | AI 聊天訊息 | role(user/assistant), content, sentiment_score, stress_index | FK→AIChatSession |
| 14 | **UserAchievement** | 用戶成就 | achievement_id, unlocked_at | FK→User, unique_together |
| 15 | **AuditLog** | 稽核日誌 | action(10+類型), target_type, target_id, ip_address, details(JSON) | FK→User(nullable) |
| 16 | **SelfAssessment** | 自我評估 | assessment_type(phq9/gad7), responses(JSON), total_score | FK→User |
| 17 | **WeeklySummary** | 每週摘要 | week_start, mood_avg, stress_avg, note_count, top_activities(JSON), ai_summary | FK→User, unique_together |
| 18 | **TherapistReport** | 治療報告 | token(UUID), title, period_start/end, report_data(JSON), expires_at | FK→User |
| 19 | **PsychoArticle** | 心理文章 | title/content ×3 語言, category, reading_time, source, lesson_order | FK→Course(nullable) |
| 20 | **WellnessSession** | 呼吸/冥想紀錄 | session_type, exercise_name, duration_seconds | FK→User |
| 21 | **Course** | 教育課程 | title/description ×3 語言, category, icon_emoji, order | 被 PsychoArticle FK |
| 22 | **UserLessonProgress** | 課堂進度 | started_at, completed_at | FK→User, FK→PsychoArticle, unique_together |

### 資料庫索引（17 個自訂索引）

| 索引 | 涵蓋欄位 |
|------|----------|
| `moodnote_user_created` | user, created_at |
| `moodnote_user_sentiment` | user, sentiment_score |
| `moodnote_user_search` | user, search_text |
| `moodnote_user_deleted` | user, is_deleted |
| `conv_updated_at` | updated_at |
| `message_conv_read` | conversation, is_read |
| `message_sender_created` | sender, created_at |
| `notif_user_read` | user, is_read, created_at |
| `timeslot_counselor_day` | counselor, day_of_week, is_active |
| `booking_counselor_date` | counselor, date, status |
| `sharednote_user_date` | shared_with, shared_at |
| `aichat_user_pin_upd` | user, is_pinned, updated_at |
| `aichatmsg_session_created` | session, created_at |
| `assess_user_type_date` | user, assessment_type, created_at |
| `wellness_user_completed` | user, completed_at |
| `audit_user_created` | user, created_at |
| `audit_action_created` | action, created_at |

### 資料遷移（29 個，含 5 個種子資料）

| 遷移 | 類型 | 內容 |
|------|------|------|
| `0019_seed_psycho_articles` | Seed | 8 篇三語心理文章 |
| `0021_seed_article_sources` | Seed | 學術來源引用 |
| `0025_add_credible_articles` | Seed | 8 篇額外文章（WHO、APA 來源） |
| `0027_seed_courses` | Seed | 4 門課程 + 16 堂課映射 |
| `0028_seed_breathing_course` | Seed | 呼吸課程 |

### ER 關聯圖（核心）

```
CustomUser ─┬─< MoodNote ──< NoteAttachment
            │              └──< SharedNote
            ├── CounselorProfile (1:1)
            ├─< Conversation ──< Message
            ├─< Notification
            ├─< TimeSlot
            ├─< Booking
            ├─< AIChatSession ──< AIChatMessage
            ├─< UserAchievement
            ├─< AuditLog
            ├─< SelfAssessment
            ├─< WeeklySummary
            ├─< TherapistReport
            ├─< WellnessSession
            ├─< UserLessonProgress ──> PsychoArticle ──> Course
            └─< Feedback
```

---

## 四、部署架構

| 層級 | 服務 | 說明 |
|------|------|------|
| **前端** | Cloudflare Pages | Vite 靜態建置、CDN 全球分發 |
| **後端** | Google Cloud Run | Daphne ASGI、自動擴縮、asia-east1 |
| **資料庫** | Neon PostgreSQL | Serverless Postgres、自動擴縮 |
| **儲存** | Google Cloud Storage | 附件圖片儲存 |
| **AI** | OpenAI API | GPT-4o-mini 情緒分析 + 聊天 |
| **向量庫** | ChromaDB | RAG 知識庫（LangChain 整合） |
| **監控** | Sentry | 錯誤追蹤 + 效能監控 |

---

## 五、統計總覽

| 項目 | 數量 |
|------|------|
| 前端頁面 | 24 |
| 前端 UI 元件 | 22 |
| Context Provider | 4 |
| API 整合模組 | 15 |
| 後端 API 端點 | 55+ |
| Serializer | 27 |
| 服務模組 | 10 |
| 速率限制 | 11 |
| 資料表 | 22 |
| 資料庫索引 | 17 |
| 資料遷移 | 29 |
| 後端測試 | 113 |
