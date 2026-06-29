# 給 Claude / AI 設計工具的請求

> **使用說明**：把這整份檔案的內容（從下面 `===` 開始）整包複製，貼到 Claude.ai 對話框，按送出。Claude 會看完所有上下文，幫你產出 7 張可直接用在 PPT 的流程圖。

---

===

你好 Claude，我需要你幫我設計幾張**簡單乾淨的流程圖**，要放在我的專題評審 PPT 上。

# 專題簡介

**專題名稱**：HeartBox 心事盒 — AI 心情日記網站

**它是什麼**：
- 一個結合 AI 情緒分析、長期心情統計、個人化洞察的心理日記 App
- 網頁版（heartbox.tw）+ Android App 雙端
- 使用者寫日記 → AI 自動分析情緒 → 長期累積後給予個人化建議

**最大特色**：
- 自架繁中 LLM（TAIDE 模型）做情緒分析，**日記內容從不離開我們的伺服器**（不像 ChatGPT 會把對話上傳）
- 結合天氣資料 + 長期心情規律，給「今日個人化建議」
- 資料庫**欄位加密**（Fernet AES-128），即使 DB 被拖庫也讀不到

**技術棧**：
- 前端：React + Tailwind CSS + Vite
- 後端：Django + DRF on Cloud Run
- 資料庫：Postgres on Neon
- AI 模型：TAIDE-LX-7B（繁中 LLM）+ LLaVA（圖像）+ bge-m3（向量檢索）跑在本機，透過 Cloudflare Tunnel 對外
- 部署：Cloud Run（後端）+ Cloudflare Pages（前端）

# 我要 7 張流程圖

## 設計要求

- **風格**：簡單、乾淨、適合放在 PPT 投影片上
- **不要花俏的設計**，方塊 + 箭頭就好
- **可以彩色但克制**：主色用橘色 (#F97316) 標重點，其他用灰階
- **比例**：每張圖適合放在 16:9 投影片上（橫向長方形 OK）
- **文字**：用繁體中文
- **輸出格式**：給我每張圖的 **Mermaid 程式碼**（我會貼到 mermaid.live 匯出 PNG）

## 圖 1：系統架構總覽（最重要，這張會單獨佔一頁）

**要呈現什麼**：
這個專題的「全貌」— 評審看一眼就知道我做了哪些事。

**圖中要有的元素**：
- 使用者（瀏覽器 / Android App）在最上方
- Cloudflare 邊緣（Pages 前端 CDN + Tunnel）
- Google Cloud Platform（Cloud Run 後端 + Cloud Storage 圖片）
- Neon Postgres 資料庫（加密儲存）
- 本機伺服器（TAIDE + LLaVA + bge-m3 三個 AI 模型）
- Upstash Redis（cache + 任務佇列）

**重點要凸顯**：
- 「跨雲」+「本機 LLM」的混合架構
- 三個 AI 模型自架（不用 OpenAI）
- 資料庫加密

**箭頭方向**：使用者 → 前端 → 後端 → 各個資料源 / AI 服務

---

## 圖 2：使用者主要流程

**呈現**：使用者從註冊到看到分析結果的完整旅程

**步驟（左到右橫向）**：
1. 訪問網站
2. 判斷：有帳號？
3. （沒有）→ 註冊 → Email 驗證
4. （有）→ 登入
5. 寫日記
6. AI 自動分析（橘色強調 — 這是賣點）
7. 儲存 + 加密
8. 看分析結果
9. 累積一段時間後 → 看 Dashboard 長期趨勢
10. 看個人化洞察（橘色強調 — 這也是賣點）

**樣式**：用 flowchart LR（左到右橫排），方便放在投影片上

---

## 圖 3：AI 日記分析流程（sequence diagram）

**呈現**：使用者按下「儲存日記」後，背後發生什麼事

**參與角色（直向 swimlane）**：
- 使用者
- 前端 React
- Django 後端
- Postgres
- TAIDE LLM

**時間順序步驟**：
1. 使用者寫完日記，按儲存
2. 前端 POST 到後端 `/api/notes/`
3. 後端用 Fernet 加密內容
4. 後端存進 Postgres（已加密）
5. 後端立即回應前端 HTTP 201（不等 AI）
6. 前端顯示「已儲存」給使用者
7.（背景非同步）後端把原文送給 TAIDE
8. TAIDE 推理（5-15 秒）→ 回傳 sentiment + stress + 暖心回饋
9. 後端更新 DB（AI 結果也加密）
10. 後端用 WebSocket 推送結果到前端
11. 前端自動補上 AI 分析結果（不用重整頁面）

**重點**：強調「立即回應 → 不阻塞使用者」+「背景處理」

**用 sequenceDiagram 而不是 flowchart**

---

## 圖 4：個人化建議流程

**呈現**：HeartBox 最有特色的功能 — 結合長期統計 + 即時天氣 + LLM 生成的「今日建議」

**步驟（直向）**：
1. 使用者打開日誌頁
2. 取得地理位置（瀏覽器定位）
3. 呼叫 `/api/personal-suggestion/`
4. 後端**並行**收集三類資料：
   - 使用者長期心情規律（從 DB 算 5 個維度）
   - 今天天氣（Open-Meteo API）
   - 今天日期屬性（平日/週末/月段）
5. 組合 prompt 給 TAIDE
6. TAIDE 寫 2-3 句暖心建議
7. 判斷：成功？
   - 是 → Cache 12 小時 → 顯示
   - 否 → 退回固定模板 tips → 顯示

**重點凸顯**：
- 「並行收集」（不是依序）
- LLM 失敗有 fallback（穩定性）
- 12 小時 cache（成本控制）

---

## 圖 5：資料安全 / 加密流程

**呈現**：當使用者寫一篇日記，內容怎麼被加密 + 為什麼還能搜尋

**步驟**：
1. 原文日記
2. 分兩路：
   - 路徑 A：完整內容用 Fernet AES-128 加密 → 存 `encrypted_content` 欄位（DB 看到亂碼）
   - 路徑 B：取前 30%（上限 200 字）→ 存 `search_text` 欄位（明文，給搜尋用）
3. 搜尋查詢時：用 `search_text` 欄位 LIKE 比對 → 回傳結果

**重點**：
- 完整內容**絕對加密**（即使 DB 被偷也讀不到）
- 為了支援搜尋功能，留一小段明文索引（比例化）

**用 flowchart LR**，分兩條路徑清楚呈現

---

## 圖 6：危機關鍵字處理

**呈現**：當使用者寫的內容含自殺/自殘關鍵字時，系統怎麼反應

**步驟**：
1. 使用者寫內容（日記 / AI 對話 / 社群貼文）
2. 後端關鍵字偵測（詞典 + LLM 雙保險）
3. 判斷：含危機字眼？
   - 否 → 正常儲存
   - 是 → 儲存 + 標記 `crisis_detected`
4.（如果是）後端回傳危機 flag + 求助熱線
5. 前端跳出 CrisisBanner：
   - 「你並不孤單」
   - 1995 生命線
   - 113 婦幼專線
6. 同時寫入 AuditLog 追蹤

**重點**：強調這個專題在心理健康議題上的責任感（評審會喜歡看到這個）

**用紅色 / 警示色標示危機分支**

---

## 圖 7：技術棧分層

**呈現**：把整個專題用到的技術，按「前端 / 後端 / AI / 部署」4 層列出來

**4 層直向疊：**

**第 1 層 前端**：
- React 18 + Vite + Tailwind 4 + Tiptap + Recharts
- Capacitor (Android App) + PWA Service Worker

**第 2 層 後端**：
- Django 5 + DRF + Celery + JWT
- Postgres (Neon) + Redis (Upstash) + GCS

**第 3 層 AI**：
- TAIDE-LX-7B（繁中對話）
- LLaVA（圖像理解）
- bge-m3 + ChromaDB（RAG 心理知識檢索）

**第 4 層 部署 / 運維**：
- Cloud Run + Cloudflare Pages + Tunnel
- GitHub Actions CI/CD
- NSSM (Windows Service for LLM)
- Sentry

**樣式**：用簡單的 4 個橫長方形上下堆疊，箭頭表示「上層用下層」

---

# 輸出格式

請給我一份回覆，包含 7 段：

```
## 圖 1：系統架構總覽
（Mermaid 程式碼）

## 圖 2：使用者主要流程
（Mermaid 程式碼）

...（依此類推到圖 7）
```

每個 Mermaid 程式碼用 \`\`\`mermaid 包起來，這樣我可以複製貼到 mermaid.live。

# 額外要求

- **不要解釋每張圖**，直接給 Mermaid 程式碼就好
- **不要設計多餘的圖**，就 7 張
- **如果某張圖某個節點名字太長，可以縮短**，但保留原意
- **顏色用 mermaid 的 style 語法**標重點（主色橘 #F97316）
- 整體簡潔，PPT 螢幕上看得清楚

# 給我額外想要的

第 8 段請告訴我：**這 7 張圖中，如果只能放 3 張在 PPT，你建議放哪 3 張，為什麼？**

謝謝！

===

> **使用說明（再次）**：以上從 `===` 開始的內容就是要貼給 Claude 的完整 prompt。
> 把它整段複製 → 開 Claude.ai → 貼上 → 送出 → 拿到 7 個 mermaid 程式碼 → 一個一個貼到 https://mermaid.live → 下載 PNG → 放進 PPT。
