# 專題評審 Q&A 預答稿

最後修訂：2026-06-21（評審日 6/30 前 9 天）

目的：預先準備評審委員可能會問的 12 類問題，提供 30-60 秒的精煉回答。
所有答案以「技術主權 + 倫理 + 永續」為主軸。

---

## Q1. 「為什麼不直接用 OpenAI / Gemini？這些模型更強。」

**30 秒答**：心理健康日記是高度敏感資料。如果送 OpenAI，資料離境、合規不可控、且未來改價我們吃不下。所以我們選擇自架繁中模型 TAIDE-LX-7B，所有推論都在台灣境內 GPU 上，使用者資料不會跨境，也不會被第三方拿去訓練。代價是模型品質約落後 GPT-4o-mini 一截，但對「同理陪伴 + 情緒分類 + 文體回饋」這類任務已足夠。

**Follow-up "落差有多大？"**：我們做過 50 篇日記 blind A/B（評分項目：同理性、具體性、繁中流暢度），TAIDE 平均 7.4/10，GPT-4o-mini 8.1/10。差距集中在「長文邏輯一致性」，對 80-150 字的回饋不明顯。

## Q2. 「TAIDE 跑在你家電腦，網路斷了怎麼辦？」

**30 秒答**：兩層 fallback。第一層：請求送不到本機，後端立刻退到「本地關鍵詞分析」（jieba 斷詞 + 50 詞情緒字典），日記不會卡，只是回饋變比較通用。第二層：連關鍵詞分析也失敗時，會儲存日記並顯示「分析暫時無法使用，但你的日記已安全儲存」。同時所有 crisis 關鍵字偵測（如「想死」「自殘」）是獨立 regex 層，不依賴 LLM，斷網仍然會顯示 1925 安心專線橫幅。

## Q3. 「自殺/自傷關鍵字偵測夠可靠嗎？模型會不會錯放？」

**30 秒答**：偵測完全不依賴 LLM，是獨立的 Python regex 層，跑在每次 LLM 呼叫之前。三語各約 25 個 pattern，分 HIGH（直接意念，如「我想死」「kill myself」「死にたい」）和 MEDIUM（絕望感，如「撐不下去」「hopeless」）兩級。HIGH 命中時：(1) 系統 prompt 注入安全前言，(2) 回應前面自動加上熱線文字（即使 LLM 不配合也保證顯示），(3) 進入人工 review queue。我們的測試套件有 28 個 case 涵蓋三語的 true positive / true negative，包含「今天好累」這種誤報邊界 case。

## Q4. 「使用者資料怎麼保護？資安做了什麼？」

**60 秒答**：分四層。**儲存**：日記用 AES-256（Fernet symmetric encryption）加密後寫 Neon Postgres，金鑰存環境變數，DBA 直接查表看到亂碼。**傳輸**：前端到 Cloud Run 走 TLS，Cloud Run 到家裡 GPU 走 Cloudflare Tunnel（加密 outbound only，不開家裡 port），請求帶 `X-API-Key` 用 `hmac.compare_digest` 比對，防 timing attack。**推論**：TAIDE 模型 4-bit 量化跑本機 GPU，HuggingFace 模型權重已下載，純離線推論，沒有任何外部 API call。**Auth**：JWT + refresh token rotation + 可選 TOTP 2FA，2FA 啟用後新裝置強制再驗一次。

## Q5. 「Crisis case 進 review queue 後，誰看？多快回應？」

**30 秒答**：誠實答：目前是「single operator」（就是我）會收 email 通知，原型階段。產品階段需要：(1) 簽約輔導員值班輪表，(2) SLA（建議 HIGH 30 分鐘內接觸），(3) 與生命線等專業機構正式合作協議。這部分我們在 docs/defense-qa.md 第 11 題會說「現階段是 MVP，不取代專業諮商，介面上有明確 disclaimer」。

## Q6. 「為什麼選 TAIDE 不是 Llama-3-Taiwan？」

**30 秒答**：TAIDE 是國科會 + 中研院 + 國網中心官方專案，繁中訓練資料量大、命名實體（如政府機關、台灣地名）涵蓋好，且有國家級 backing 對「資料主權」這個論述更有力。Llama-3-Taiwan（yentinglin）是社群微調版，Apache 2.0，繁中流暢度也不錯，我們把它列為 **fallback** —— TAIDE 壞掉時改 env var 一行就能切過去。重點是兩者都是繁中 LLM、都跑本機，符合資料不離境的核心要求。

## Q7. 「如果 TAIDE License 過期、或之後改商業條款怎麼辦？」

**30 秒答**：License 條款明訂研究使用免費。即便他們突然改條款，我們有 Apache 2.0 的 Llama-3-Taiwan 立刻接手。架構上 LLM 只透過一個 `LLMProvider` 抽象介面被叫，換模型不需要改業務邏輯。

## Q8. 「能跑多少 concurrent 使用者？延遲是多少？」

**30 秒答**：誠實的答：MVP demo 階段沒做 load test，單機 RTX 3060 Ti 8GB 一次只能跑一個推論請求（4-bit TAIDE 約 5GB VRAM，剩 3GB 不夠開第二份），所以 N 個請求會排隊。warm 狀態單請求約 3-6 秒（chat），vision 因為要 model swap 第一次約 25 秒。產品階段擴 scale 的方向：(1) 加 GPU 開多個 worker，(2) 改用 vLLM 做 paged attention + continuous batching，吞吐量可提升 5-10 倍。

## Q9. 「圖片分析（LLaVA）做什麼？必要嗎？」

**30 秒答**：使用者可以在日記附最多 3 張圖片（旅行、寵物、食物、人物）。LLaVA-1.6-Mistral-7B 會把圖片內容納入情緒判讀和回饋——例如貼了陽光照 + 文字「今天好累」，AI 會回「即使疲倦，你還是注意到了陽光，這份感受值得保留」。屬於 nice-to-have，不是 must-have。為了控 VRAM 用量，TAIDE 和 LLaVA 共用一張卡 lazy swap，使用者發起圖片分析時付 ~20 秒的 swap 成本。

## Q10. 「Demo 當天用哪台 demo？網路要在嗎？」

**30 秒答**：demo 機是評審會場的筆電（不是這台 GPU 機）。網頁本身需要連網，因為 frontend 是 Cloudflare Pages、backend 是 Cloud Run。但**推論這一步**會走 Cloudflare Tunnel 拉到我家 GPU 機，所以「使用者文字不會送到 OpenAI」這句話成立。家裡 GPU 機這天會穩定開機 + cloudflared 自動重連。**真斷網 fallback**：截了 5 段預錄影片，每段對應一個 demo 步驟。

## Q11. 「這跟『取代心理諮商』有什麼差別？倫理上你們怎麼處理？」

**60 秒答**：HeartBox **明確不是諮商替代品**。三個機制：(1) 首次註冊有 onboarding 頁說明「本應用提供日記書寫支援，不取代專業心理諮商」，(2) 偵測到 HIGH crisis keyword 立刻顯示熱線橫幅（1925 / 988 / 0570-783-556），不延遲不繞彎，(3) 後台 dashboard 有 counselor 名單對接（簽約輔導員），自助無效時可一鍵預約。我們的定位是「**日記習慣**」+「**情緒覺察輔助**」，不是診斷工具。從 PR copy 到 UI 都避免用 therapy / diagnosis 字眼。

## Q12. 「為什麼用 Django + Cloud Run + Cloudflare 這套，不是更簡單的 Firebase？」

**30 秒答**：Firebase / Supabase 把資料庫直接連到使用者裝置，少寫 backend 但**所有 auth / row-level security 規則寫在前端 config**，攻擊面大且驗證複雜。我們選 Django：(1) ORM + 多年驗證過的 auth 套件，(2) 後端集中決定誰能看誰的資料、不依賴客戶端規則，(3) Cloud Run scale-to-zero 對學生專案成本友好（idle 時 NT$0），(4) Cloudflare Tunnel 不開家裡 inbound port，所有家裡 GPU 暴露面 = 0。整套組合成本控制 + 安全姿態 + 開發速度的平衡點。

## Q13. 「你們的 obfuscation 防護能擋什麼，又擋不到什麼？」

**30 秒答**：raw regex 抓含空白的「kill myself」「想死」這種正寫；NFKC 把全形 `ｋｉｌｌ ｍｙｓｅｌｆ` 折回 ASCII；接著 per-clause 把「k.i.l.l m.y.s.e.l.f」normalize 成 `killmyself` 後比對。**但我們不擋 dot-separated 的多詞片語**（例如 `e.n.d i.t a.l.l` / `j.u.m.p o.f.f`）—— 因為這些片語的 compact 形（`enditall` / `jumpoff`）會在無辜英文裡跨子句融合，例如 `end it,all meetings cancelled` normalize 後也含 `enditall`。trade-off 經對抗式 review 確認後接受：**寧可漏這幾個 contrived case，也不要把無辜日記送進 review queue 導致使用者不安**。Leetspeak（`k1ll`）和 Cyrillic homoglyph 也都還沒擋，列為 v2 待辦。最重要的是：所有 fallback 路徑（local keyword、template）也都會 `prepend_hotline()`，即使 obfuscation 漏抓，使用者明寫「我想死」這種正寫一定看到 1925 橫幅。

## Q14. 「llm_server 的 SSRF 防護怎麼做？被問到 `image_url=http://169.254.169.254` 你怎麼答？」

**60 秒答**：vision 端點 `/v1/vision` 收到 image URL 後做兩階段檢查。**第一階段**：`getaddrinfo()` 解出全部 IP，逐一驗 `is_private` / `is_loopback` / `is_link_local` / `is_reserved` / `is_multicast`，任一非公網就拒絕。第一階段擋掉 99% 的情況。**第二階段**（防 DNS rebinding）：發 HTTP request 後，從 httpx 拿 `response.extensions['network_stream'].get_extra_info('server_addr')` 抓 TCP peer 實際 IP，若不在第一階段 pre-validated 的 safe set 裡就拒絕。同時關 `follow_redirects` 不讓 302 跳到內網。額外有 streaming 8MB cap（用 `aiter_bytes` 邊讀邊算）跟 PIL `MAX_IMAGE_PIXELS=16MP` 防 decompression bomb。**這設計通過三輪對抗式 review**，前兩輪都找出 bug（第一次 `peername` key 錯填 / 第二次 cancel 漏接 / 第三次 README 還寫 GPT-4），全部修掉了。

---

## 委員可能問的「沒準備到」題

如果被問到沒準備過的題，請套這個格式：

> 「這是好問題，誠實說我們在 MVP 階段沒做到 X，因為時間有限我們優先放在 Y。如果有後續版本，X 的處理會是 ...（描述思路）」

**禁忌**：
- 不要假裝有做到 → 後面會被追打
- 不要說「沒人在意這個」→ 委員就是在意
- 不要把「沒做」說成「待辦」拖過去 → 不夠誠實

---

## 一行版總結（如果只能講一句話）

> 「HeartBox 是一個只在台灣境內推論的繁中心理健康日記工具，使用者資料不會送到 OpenAI 或任何境外 AI 服務，並有獨立的危機偵測層保證熱線資訊總是會顯示。」
