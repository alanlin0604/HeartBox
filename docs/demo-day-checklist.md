# Defense Day Checklist — 2026-06-30

> 列出當天從起床到報告結束要做的所有事，按順序。每項打勾再做下一個。

---

## 報告前 30 分鐘（暖機 + 最終 smoke）

- [ ] **暖機 API**（喚醒 Cloud Run cold start）
  ```
  curl https://api.heartbox.tw/healthz/
  ```
  期望 `HTTP 200`，第一次可能 8-15 秒，第二次 <1 秒。

- [ ] **暖機 LLM Tunnel**（喚醒 NSSM service）
  ```
  curl https://llm.heartbox.tw/healthz
  ```
  期望 `HTTP 401`（路由活著、需 auth，正常）。

- [ ] **暖機 Personal Suggestion**（讓 TAIDE 預載）
  - 登入任一 test 帳號 → 進日誌頁 → 觀察「今日個人化建議」widget 是否在 20 秒內出現

- [ ] **檢查家裡電腦的 LLM service 還在跑**
  - 開工作管理員 → 看到 `HeartBoxLLM` 服務「執行中」
  - 開瀏覽器 → `http://localhost:8765/healthz` → 應該 200

- [ ] **檢查 cloudflared tunnel 還在跑**
  - 工作管理員看到 `cloudflared` 程序

---

## 4 個示範帳號

| 帳號 | 密碼 | 屬性 | 拿來示範什麼 |
|---|---|---|---|
| `test` | `test` | balanced | 一般使用者，dashboard 完整呈現 |
| `test1` | `test1` | volatile | 起伏大，月份/週末規律明顯 |
| `test2` | `test2` | positive | 正向用戶，趨勢往上 |
| `test3` | `test3` | negative+RAG | 負面內容，焦慮/倦怠主題，可示範 AI 暖心回饋 |

**alan** 是你自己的真實帳號（不要在 demo 前寫新日記，免得 streak 跳掉）。

---

## Demo 黃金路徑（建議 5-7 分鐘）

### Phase 1 — 第一印象（30 秒）

1. 打開 `https://heartbox.tw/` 不要登入
2. 講重點：
   - 「HeartBox 心事盒 — 結合 AI 情緒分析與長期規律觀察的個人心靈日記」
   - 「不會把日記上傳到第三方 AI，所有資料都在我們自己的伺服器」

### Phase 2 — 登入（30 秒）

1. 點「登入」→ 輸入 `test2` / `test2`
2. 講重點：
   - 「我們支援帳號密碼、Google 登入、2FA 兩步驟驗證」
   - 「JWT token 認證，access 15 分鐘失效，refresh 30 天」

### Phase 3 — 日誌頁（1 分鐘）

1. 進入日誌頁
2. **指著「今日個人化建議」**：「這是 LLM 根據使用者長期情緒規律 + 今天台北的天氣，自動生成的一段話。每天 12 小時 cache 一次，不會打爆我們的 LLM」
3. 滾過去看 100 篇日記（test2 是正向使用者）
4. 點任一篇 → 看 AI 回饋
5. 講重點：「每篇日記都有情緒分數 (-1 ~ +1) + 壓力指數 (0~10) + AI 暖心回饋」

### Phase 4 — Dashboard（2 分鐘）

1. 點上方「分析」→「儀表板」
2. 滾過去秀：
   - **心情趨勢**：18 週的折線圖
   - **心情 × 溫度**：散布圖 + 5 段溫度桶
   - **常用標籤**：bar chart
   - **壓力雷達**
   - **個人化洞察**（如果觸發）：「系統偵測到使用者週末心情明顯比平日好」
3. 講重點：
   - 「這些洞察**不是 LLM 算的**，是純統計演算法 — 確定性、可解釋」
   - 「5 個維度：月段、平日週末、月份、天氣、溫度」

### Phase 5 — 切換到 test3 看負向案例（1 分鐘）

1. 登出 → 用 `test3` / `test3` 登入
2. 點任一篇關於焦慮/失眠的日記
3. 講重點：
   - 「同一套 AI 系統，給負向使用者的回饋會更溫柔、更具體」
   - 「日記內容如果觸發危機字眼（自殺/自殘）會自動跳生命線資源 banner」

### Phase 6 — Admin 面板（1 分鐘）

1. 登出 → 用 alan（你的 admin 帳號）登入
2. 點「管理」
3. 秀：
   - **系統總覽**：「目前 280 個使用者，4307 篇日記」
   - **使用者管理**：「能看到全部 280 位的列表」
   - **使用回饋**：「45 則使用者回饋，平均 4.16 星」
   - **稽核日誌**：「敏感操作都有紀錄」
4. 講重點：「管理員權限分層（一般用戶 / 諮商師 / 管理員 / 超級管理員）」

### Phase 7 — 安全性收尾（30 秒）

1. 不用 demo UI，口頭講：
   - 「日記內容用 Fernet AES-128 加密儲存。即使資料庫被偷整個 dump，看到的是亂碼」
   - 「另外為了能搜尋，我們留一小段明文當索引 — **比例化 30%，上限 200 字**」
   - 「2FA / 帳號鎖定 / Rate limit / Audit log / CSP / HSTS 都齊全」

### Phase 8 — Q&A 準備

詳見 [`docs/技術說明.md` §11 FAQ](技術說明.md)。

---

## 緊急情況處理（demo 中如果出狀況）

### 🚨 登入卡住超過 30 秒
- **原因**：Cloud Run cold start + LLM warming up
- **應對**：
  - 跟評審說：「我們是 serverless 架構，閒置時會關機省成本，這幾秒是 server 暖機」
  - 同時開另一個 tab 打 `https://api.heartbox.tw/healthz/` 強制喚醒

### 🚨 日記頁面「今日個人化建議」沒出來
- **原因**：TAIDE LLM 掛掉 / Tunnel 斷線
- **應對**：
  - 系統會自動 fallback 到模板 tips（10 條預寫的暖心建議）
  - 跟評審說：「我們有 3 層 fallback，剛才主 LLM 沒回應，系統用了預備模板」
- **真的炸了**：跳過這個 widget，直接 demo dashboard

### 🚨 Dashboard 空白
- **原因**：analytics endpoint 429/503 / TAIDE 超時
- **應對**：等 3 秒，全域 retry 會自動再打一次
- **不行就 reload**

### 🚨 寫日記按下儲存沒反應
- **原因**：圖片上傳卡 / API timeout
- **應對**：
  - 不要重複按
  - 等 10 秒看會不會出 toast
  - 仍然沒反應 → 換 test 帳號重 demo

### 🚨 整個網站 522 / 524（Cloudflare 錯誤）
- **原因**：Cloud Run 整個掛了
- **應對**：
  - **不要慌，繼續講**
  - 「demo 環境是 serverless，剛才看起來有 instance 在切換」
  - 等 30 秒重整。通常會自己回來。
- **真的不回**：切換到本機跑（如果你有預先 `python manage.py runserver`）

### 🚨 評審問「為什麼系統慢」
- **不要說**「Cloud Run cold start」（聽起來像藉口）
- **要說**「我們選擇 serverless 是為了控制成本，每月不到 NT$500。在生產環境我們會加上 minimum instances=1 來避免冷啟動」

---

## 評審刁問題對應

詳見 [`技術說明.md` §11](技術說明.md)，這裡列重點：

| 問題 | 一句話答案 |
|---|---|
| 為什麼選 TAIDE 不用 ChatGPT？ | 隱私 + 本地化 + 成本可控 |
| 加密金鑰怎麼管？ | Cloud Run 環境變數，從未寫死在 code |
| 如何擴展到 10 萬人？ | Cloud Run auto-scale + Neon serverless DB；LLM 可加 GPU 或暫時 fallback |
| LLM 講錯話怎麼辦？ | 3 層 fallback + 危機字眼自動跳生命線 + 明確標示「不取代專業醫療」 |
| 部署成本？ | 每月 < NT$500，主要用 serverless / free tier |
| 怎麼處理刪除請求？ | 30 天緩衝期 + Celery beat 真硬刪 + GDPR/PDPA 合規 |
| `search_text` 為什麼還是有明文？ | 為了支援搜尋功能，30% 比例上限 200 字，業界 Notion/Evernote 是完全明文 |
| 諮商師媒合怎麼做？ | 諮商師申請 → admin 審核 → 上架 → 用戶預約 + 對話 |

---

## 報告結束後

- [ ] 截圖紀念 demo 畫面
- [ ] 如果評審有給意見，記下來貼到 issues / TODO
- [ ] 不需要立刻刪除 seed users（之後 demo 完再做）

清理 seed users（demo 完之後再做）：
```bash
cd backend
python manage.py seed_demo_test_accounts --reset    # 刪 test/test1/test2/test3
python manage.py seed_demo_population --reset       # 刪 260 個 seed users
python manage.py seed_demo_feedback --reset         # 刪 45 個 feedback
```

---

## 系統當前狀態（截至 2026-06-29 14:00）

```
✅ web (heartbox.tw)         200 ✓
✅ api (api.heartbox.tw)     200 ✓
✅ llm (llm.heartbox.tw)     401 ✓ (alive)
✅ Cloud Run revision        heartbox-api-00195-5nj 100% traffic
✅ Frontend bundle           20260629051215-38aadf6 (latest)
✅ CSP                       全部 directive 正確
✅ IAM                       allUsers public invoker ✓
✅ Django check              0 issues
✅ ESLint                    0 errors
✅ i18n drift                zh/en/ja 全部 1981 keys
✅ Prod DB                   280 users / 4307 notes / 1453 tags / 45 feedback
✅ 4 test accounts           全部 login OK + dashboard 有資料
✅ search_text 比例化         migration 完成 (avg 10.3 字, 30% 比例)
✅ Daily Prompt              工作中 (回 "今天最讓你心跳加速的時刻是哪一段回憶？")
✅ Personal Suggestion       工作中 (LLM 回 639 字段落 + 天氣 + triggers)
```

可以放心 demo。
