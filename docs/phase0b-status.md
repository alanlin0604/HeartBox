# Phase 0b 狀態報告：OpenAI → 自架 LLM 遷移

**日期**：2026-06-25（最後更新 commit f49e1fd / 9d73639 / 99e7c42 — 三波 max-security 硬化）
**Capstone Defense**：2026-06-30（5 天後）
**生產環境**：Cloud Run `heartbox-api-00183-cm6`（4Gi） + Cloudflare Tunnel `llm.heartbox.tw` → 家裡 GPU `127.0.0.1:8765`

## Max-security 硬化結果（2026-06-25 連續 commits）

`Workflow wf_15244f50-751` 4 phase audit 找到 61 個 finding；以下已 landed：

### 🔒 加密（全部 user-content 欄位現在都 Fernet-encrypt at rest）
- `MoodNote.encrypted_content` ✅（原本就有）
- `MoodNote.ai_feedback` ✅ commit 99e7c42 — 55 rows backfilled
- `AIChatMessage.content` ✅ commit 99e7c42 — 22 rows backfilled
- `WeeklySummary.ai_summary` ✅ commit 99e7c42 — 4 rows backfilled
- `Message.content`（私訊 DM）✅ commit f49e1fd — 3 rows backfilled
- `Notification.message` ✅ commit f49e1fd — **78 rows backfilled**
- `FriendComment.content` ✅ commit f49e1fd — 0 rows (no data yet)
- `PostReport.note` ✅ commit f49e1fd — 1 row backfilled

**總共 163 個歷史 row 從 plaintext 升級到 Fernet AES-128。**
**剩餘明文僅 `MoodNote.search_text`（前 500 字）**為 LIKE search 必要，已記錄在 [defense-qa.md](defense-qa.md)。

### 🔑 Auth 強化（commit 9d73639）
- **CRITICAL** Google OAuth 強制 `email_verified=True` claim + `email__iexact` 匹配（修 pre-emption attack）
- **HIGH** Argon2PasswordHasher 取代 PBKDF2 默認；舊 hash 仍可 verify 並 next-login 升級
- **HIGH** `validate_password()` 接上 4 個 AUTH_PASSWORD_VALIDATORS（之前是 dead config）
- **HIGH** `ACCESS_TOKEN_LIFETIME` 30→15min；`token_version` 在 logout / 2FA disable / refresh 都正確 bump 與 propagate
- **HIGH** TOTPDisable 強制要 password + TOTP code（之前只要 password）
- **HIGH** 2FA partial token 改成 `scope='2fa_pending'` 3-min expiry；`VersionedJWTAuthentication` 拒絕任何 scoped token

### 🛡️ IDOR + push subscription（commit 9d73639）
- **HIGH** `PublicPostViewSet.update/partial_update` 加 IDOR 守門（之前只有 destroy 守）
- **HIGH** `PushSubscription` 改 `(user, endpoint)` composite + 拒絕跨 user 註冊既有 endpoint

### 🌐 Headers / CSP / Sentry（commit f49e1fd）
- **HSTS preload** 2 年 + includeSubDomains
- **CSP** 嚴格 allowlist（GSI Google sign-in + Cloud Run API + WSS）；frame-ancestors `'none'` / base-uri `'self'` / form-action `'self'` / object-src `'none'`
- **COOP** `same-origin-allow-popups` + **CORP** `same-site` (frontend) / `same-origin` (backend)
- **Permissions-Policy** 加 `browsing-topics=()` 阻擋 Topics API
- 後端 CSP middleware 補 emit `base-uri` / `form-action` / `object-src`（settings 早有宣告但 middleware mapping 沒接）
- Sentry `beforeSend` + `beforeBreadcrumb` 用 `scrubUrl()` 清掉 `/notes/<id>` / `/ai-chat/sessions/<id>` / `/share/<token>` 等 PII 路徑；`replaysSessionSampleRate` 降為 0（mental-health app 不錄背景 session，只錄 error）

### ☑️ Headers live 驗證
```
strict-transport-security: max-age=63072000; includeSubDomains; preload  ✓
content-security-policy: default-src 'self'; script-src 'self' ...      ✓
cross-origin-opener-policy: same-origin-allow-popups                     ✓
cross-origin-resource-policy: same-site                                  ✓
permissions-policy: ...interest-cohort=(), browsing-topics=()            ✓
referrer-policy: strict-origin-when-cross-origin                         ✓
x-frame-options: DENY                                                    ✓
```

---

## TL;DR — 結論
**OpenAI 已從 production code 100% 移除。資安端到端健康，defense 可以打。**

| 維度 | 狀態 |
|---|---|
| Production 是否還用 OpenAI / 任何商用 AI | ❌ 完全沒有 — `grep` / CI / pre-deploy 三重防線 |
| AI 推論是否全部在本地 GPU | ✅ TAIDE-LX-7B-Chat + LLaVA-v1.6 + bge-m3 都在你家裡的 GPU 跑 |
| 是否還有資料外流到雲端 AI 服務 | ❌ 沒有 — 全部走 Cloudflare Tunnel 進你家 |
| 是否還有 critical / high 資安問題 | ❌ 沒有 — 唯一中等問題是 llm_server 沒 rate limit（可用性影響，非洩密） |
| Defense 6/30 是否準備好 | ✅ 準備好；最大風險是家裡網路 / GPU 主機在 demo 時掉線 |

---

## 已完成（13 個維度）

### 1. Provider seam（單一收口）
- [backend/api/services/llm/factory.py:34](../backend/api/services/llm/factory.py#L34) `get_llm_provider()` 是 singleton + double-checked locking
- 只接受 `remote_taide`（預設）和 `mock` 兩個 provider；其他值（包含 `openai`）會 raise `LLMProviderError`
- 8 個呼叫點全部走 seam（`ai_engine` × 5 + `ai_chat` + `DailyPromptView` + `WeeklySummaryView`），沒有任何 caller 直接 import `httpx` / `requests` / `openai`

### 2. 自架 chat + vision backend
- [backend/api/services/llm/remote_provider.py:34](../backend/api/services/llm/remote_provider.py#L34) `RemoteTAIDEProvider` 用 httpx 打 `POST {LLM_SERVER_URL}/v1/chat/completions`
- Production URL：`https://llm.heartbox.tw`（Cloudflare Tunnel UUID `6612d45e-3ea1-49c3-91c9-19050dd7b1a4` → `127.0.0.1:8765` 你家 GPU）
- Chat model：[`taide/TAIDE-LX-7B-Chat`](https://huggingface.co/taide/TAIDE-LX-7B-Chat)（4-bit NF4 透過 bitsandbytes）
- Vision model：[`llava-hf/llava-v1.6-mistral-7b-hf`](https://huggingface.co/llava-hf/llava-v1.6-mistral-7b-hf)
- Auth：`X-API-Key`（`hmac.compare_digest` 比對，不會 timing leak）

### 3. Embeddings 也在地化
- [backend/api/services/llm/embeddings.py:49](../backend/api/services/llm/embeddings.py#L49) `BgeM3Embeddings`
- 模型：`BAAI/bge-m3`（Apache 2.0，1024 維），透過 sentence-transformers 本地 in-process 載入
- 取代了原本 OpenAI `text-embedding-ada-002`（1536 維）
- Chroma collection 從 `psychology_kb` 改名 `psychology_kb_bgem3` 避免維度衝突

### 4. 依賴清乾淨
- `requirements.txt`：0 個商用 AI dep（無 `openai` / `langchain-openai` / `tiktoken` / `anthropic` / `google-generativeai` / `cohere` / `replicate`）
- `langchain==0.3.25` 但沒裝 `[openai]` extra，transitive 沒拉進來
- `requirements-llm.txt`：只有 `transformers` / `accelerate` / `bitsandbytes` / `FlagEmbedding` / `fastapi` / `pydantic-settings` / `huggingface_hub` / `uvicorn`
- 前後端 `package.json`：無 `@anthropic-ai/sdk` / `@google/generative-ai` / `openai` / `cohere-ai` / `replicate` / `together-ai`

### 5. CI 防線禁止 OpenAI 回潮
- [.github/workflows/no-openai-check.yml](../.github/workflows/no-openai-check.yml) 在每次 push 阻擋 `import openai` / `langchain_openai` / `OPENAI_(API_KEY|MODEL|ORG)` / `gpt-*` / `text-embedding-*` / `api.openai.com`
- [backend/api/test_llm_factory.py:55](../backend/api/test_llm_factory.py#L55) `test_openai_value_raises` 強制 `LLM_PROVIDER='openai'` 必須丟 error
- [scripts/pre-deploy-check.ps1:27-29](../scripts/pre-deploy-check.ps1#L27-L29) push 前掃 staged diff 找 `OPENAI_API_KEY` / `sk-*` 洩漏

### 6. Output sanitization 收口
- [backend/api/services/llm/sanitize.py](../backend/api/services/llm/sanitize.py) `scrub_llm_output`：
  - NFKC fold
  - 剝 `[INST]` / `<<SYS>>` / `<|im_start|>` / `<|eot_id|>` / `</?s>` / `<image>`
  - 剝 role prefix（含中文「助理：」/「小心：」）
  - 最多 peel 4 次堆疊 prefix
  - 8000 字 hard cap
  - **Prompt-boundary cut**（commit 0749431）：偵測 system prompt 指紋後切掉整個 `日記內容：「...」` 包裝
- 收口在 [remote_provider.py:119-133](../backend/api/services/llm/remote_provider.py#L119-L133)，4 個 public method 一次蓋掉
- 消費端二次清洗：[ai_chat.py:142](../backend/api/services/ai_chat.py#L142) + [ai_engine.py:244 etc.](../backend/api/services/ai_engine.py#L244)
- `detect_system_echo` 標記模型 ≥40 字逐字 echo system prompt 的情況

### 7. Crisis guard 對稱（之前 + 之後 + fallback）
- `ai_chat.generate_ai_response`：BEFORE [inject_preamble L109-111] / AFTER [prepend_hotline L150-151]
- `ai_engine._generate_personalized_feedback`：L229-231 / L246-247
- `ai_engine._generate_rag_feedback`：L294-296 / L311-312
- `ai_engine.analyze_with_images`：L421-423 / L444-445
- `_basic_feedback_with_crisis_guard`（L260-263）涵蓋 personalized fallback / vision fallback / tier-2 local keyword
- HIGH-first severity sweep + per-clause NFKC + `\W_` normalization 攔截 obfuscated `ｋｉｌｌｍｙｓｅｌｆ` / `k.i.l.l.myself`

### 8. 加密：靜態 + 傳輸
- `MoodNote.encrypted_content` 走 Fernet/MultiFernet（[encryption.py](../backend/api/services/encryption.py) + [models.py:78-143](../backend/api/models.py#L78-L143)）支援 key rotation
- `ENCRYPTION_KEY` 在 settings load 時驗證為 32-byte url-safe-b64（[settings.py:230-235](../backend/moodnotes_pro/settings.py#L230-L235)），無效就拒絕啟動
- Plaintext 暫存於 `_raw_content` 並在 save 後清零
- HTTPS end-to-end：browser → Cloud Run → Cloudflare Edge → tunnel；`httpx.Client` 沒有 `verify=False` 任何覆寫

### 9. Prompt-template leak 修復
- [5c430d6](https://github.com/alanlin0604/HeartBox/commit/5c430d6) — engine.py token-slice 取代字串前綴比對；scrub 加到 chokepoint
- [0749431](https://github.com/alanlin0604/HeartBox/commit/0749431) — sanitize 加 boundary cut；前端新 `AIFeedbackText` 元件粗體 numbered headings + 段落間距
- [7a349f5](https://github.com/alanlin0604/HeartBox/commit/7a349f5) — migration 0058 re-scrub 歷史 row（**1 row 已清**：note 952）
- `DailyPromptView` cache key bump 到 v2（[analytics.py:410-414](../backend/api/views/analytics.py#L410-L414)）讓舊污染 cache 失效
- Cache key 含 `request.user.id` + today → 無 cross-user 洩漏

### 10. SSRF + 濫用防禦（llm_server）
- [main.py:121-159](../llm_server/main.py#L121-L159) `_resolve_safe_ips` 拒絕 private/loopback/link-local/reserved/multicast/unspecified（含 GCE metadata `169.254.169.254`）
- [main.py:162-199](../llm_server/main.py#L162-L199) `_verify_peer_ip` 從 httpcore 的 **server_addr** extension 讀（不是 peername），關掉 DNS-rebind TOCTOU；無 extension 時 fail-closed
- `follow_redirects=False` / `max_redirects=0` / 只允許 http(s)
- 每張圖 8MB cap；content-type 必須 `image/*`；PIL `DecompressionBombWarning` 升級成 exception；16MP cap
- 雙層 body cap（[main.py:380-401](../llm_server/main.py#L380-L401)）：拒絕 `Transfer-Encoding: chunked` (411)、拒絕負數/非 int/>100KB CL (400/413)，在 Pydantic 解析前先擋

### 11. Cooperative cancellation + atomic model swap
- [engine.py:209-222](../llm_server/engine.py#L209-L222) `StoppingCriteria` 每 token 檢查 `threading.Event`
- `_await_with_cancel`（L280-348）在 `TimeoutError` 或 client `CancelledError` 時 set event，透過 `asyncio.wait_for(asyncio.shield(fut), _STOP_GRACE_SECONDS)` 等 worker join 才放 `_swap_lock`
- Loader 先建好 `(model, tokenizer, processor)` tuple **才**指派，避免半載入污染 state

### 12. 前端零外流
- [src/api/axios.js:5](../frontend/src/api/axios.js#L5)：前端只跟 `VITE_API_URL`（即 `api.heartbox.tw/api`）講話
- 全前端無 `api.openai.com` / `api.anthropic.com` / `generativelanguage.googleapis.com` / 任何 vendor 的 fetch/axios/XHR

### 13. 三層 graceful degradation 已文件化 + 演練過
- **Tier-1**：`provider.chat_json` (TAIDE) 成功 → 用模型回應
- **Tier-2**：LLM 失敗 → 本地中文 keyword 分析（純離線）
- **Tier-3**：「分析暫時無法使用」banner（[health.py WeeklySummaryView](../backend/api/views/health.py)；[DailyPromptView fallback prompts](../backend/api/views/analytics.py)）
- `ai_chat` 在 `LLMProviderError` 或 provider 未配置時用 `FALLBACK_RESPONSES`

---

## 已關閉項目（commit 4f43145, 2026-06-25）

8 項機械化修法已 deploy：

| 原 Severity | 維度 | Commit 處理方式 |
|---|---|---|
| **MEDIUM** | llm_server rate limiting | ✅ 新 `_rate_limit_middleware`（[main.py](../llm_server/main.py)）— sliding-window per-API-key + burst guard。SHA256 fingerprint key（raw key 永不進記憶體 dump）。預設 60 req/min + burst 10 in 5s。返回 429 + `Retry-After`。skip /health；3 個新測試 |
| LOW | API_KEY 最小長度 | ✅ `create_app()` 拒絕 boot 如 `len(api_key) < 32`；指向 `secrets.token_hex(32)`。新測試 `test_short_api_key_refused_at_startup` |
| LOW | Body-size streamed-bytes 計數 | ✅ `_body_size_limit` 包 `request._receive()` 加 counter；超過上限就 truncate chunk + signal end-of-body 返 413。Defense-in-depth 對抗未來 transport bypass |
| LOW | `log_prompts` dead config flag | ✅ 從 config.py 移除（永遠是 no-op 的 trap） |
| LOW | 註解寫 OpenAI | ✅ notes.py / tasks.py / tests.py 三處改成 LLM roundtrip / LLM provider throttle / LLM provider unconfigured |
| LOW | Archive docs deprecation banner | ✅ `專案全面審查與改進建議.md` + `全面改進建議報告.md` 加 4 行警告 + 指向 `.env.example` + `phase0b-status.md` |
| INFO | `search_text` plaintext caveat | ✅ `docs/defense-qa.md` Q4 加 caveat 段：前 500 字明文 trade-off 因 Fernet ciphertext 不能 LIKE。pre-empt「日記是不是完全加密」的 gotcha |
| INFO | `sanitize._ROLE_NAMES` 含 `小心` 註解 | ✅ 加 7 行 comment 說明 trade-off：catch parrot case at cost of 罕見「小心：注意安全」誤剝（替換為空白所以後文存留） |

## 剩餘待辦（3 個，全部需要你親手做）

| Severity | 維度 | 你要做什麼 |
|---|---|---|
| LOW | `MoodNote.ai_feedback` 沒加密 | 設計決定：要不要 Fernet 包 `ai_feedback`？trade-off：list-view 不需 decrypt vs 防 DB-dump scenario。回 mainline 一句話我就 land migration |
| LOW | 本機 venv 殘留 `openai` 1.78.1 + `langchain-openai` 0.3.18 | 在你工作站跑：`Remove-Item -Recurse -Force backend\venv; python -m venv backend\venv; backend\venv\Scripts\pip install -r requirements.txt`。Cloud Run 不受影響 |
| INFO | 設 `TRANSFORMERS_OFFLINE=1` 在家裡 GPU 主機 | 第一次 boot 成功（HF cache 已熱）後，編輯 `~/.heartbox-llm.env` 加一行 `TRANSFORMERS_OFFLINE=1` 並 restart llm_server。防 HF 主站 outage |

---

## OpenAI 殘留判決（一段）

**Production code 沒有任何 live OpenAI 依賴。** 靜態分析確認非 venv Python source 裡 0 個 `import openai` / `from openai` / `OpenAI(` / `ChatCompletion` / `Embedding.create` / `api.openai.com`；`requirements.txt`、`requirements-llm.txt`、root `package.json`、`frontend/package.json` 都沒有商用 AI SDK；`render.yaml` 無 `OPENAI_API_KEY`。Factory 只接受 `remote_taide` 和 `mock`，舊的 `openai` 字串會丟 error 且有 regression test + CI workflow 雙重把關。剩餘 occurrence 都是良性類別：(a) 註解 / docstring 記錄遷移歷史，(b) wire-format 引用（自架 llm_server 暴露 OpenAI-shape JSON 端點為了重用一個 HTTP client），(c) 防禦性檢查（regression test + pre-deploy secret scanner regex），(d) 本機 venv 殘留（`openai 1.78.1` + `langchain-openai 0.3.18`，不在 requirements 裡也沒被 import，Cloud Run 每次 reinstall 都是乾淨的）。**遷移 production-complete。**

---

## 資安判決（一段）

**端到端資安狀態 defense-ready。** 日記內容用 Fernet（含 MultiFernet rotation）靜態加密，`ENCRYPTION_KEY` 在 boot 驗證為 32-byte url-safe-b64；傳輸用 HTTPS 終結於 Cloudflare Tunnel 內部 `127.0.0.1:8765`，全程無 `verify=False`。**commit 4f43145 後** llm_server 還加上 in-process rate limit（SHA256-fingerprint per-key sliding window + 5s burst guard，預設 60/min + burst 10）+ API_KEY 32 字元最小長度（boot 時拒絕短 key）+ streaming-bytes body counter，與既有 SSRF + body-size cap + chunked-bypass refuse + CORS-on-401 等防禦疊在一起。在 Pydantic parse 前用 `hmac.compare_digest` 比 API key、雙 pass SSRF（httpcore `server_addr` extension 關閉 DNS-rebind TOCTOU）、8MB/16MP 圖片限制 + 中段 abort、cooperative-cancel（StoppingCriteria + thread join + atomic-swap loader）讓 timed-out / 客戶端斷線的 generation 不留 GPU zombie。Django provider seam 在單一 chokepoint 跑 `scrub_llm_output`、消費端再二次清洗、CrisisGuard 在每個 LLM path 和每個 non-LLM fallback path 都對稱跑 BEFORE（preamble inject）+ AFTER（hotline prepend），NFKC + per-clause normalization 抗 obfuscation + HIGH-first severity sweep。Logging 不寫 prompt / reply / system prompt / user content / key 內容——只寫 structured field（provider/op/model/latency_ms/status）+ `removed_chars` 計數。**所有 critical / high / medium 已關閉**；剩 3 個 LOW/INFO 全部要你親手做：`ai_feedback` 是否加密的設計判斷（產品決定）、本機 venv 殘留清理（不影響 prod）、家裡 GPU 設 `TRANSFORMERS_OFFLINE=1`（防 HF 主站 outage）。

---

## Capstone 準備度（2026-06-30）

**準備好。** 遷移 production-complete、prompt-leak 修法（5c430d6 / 0749431 / 7a349f5）已 deploy、migration 0058 已掃過歷史 row、本機 llm_server PID 66980 已 patch、`llm.heartbox.tw` tunnel 健康。Data-sovereignty 論述寫在 [docs/defense-qa.md](defense-qa.md)，runbook 在 [docs/llm-runbook.md](llm-runbook.md)。

**最大殘餘風險是維運不是資安**：Cloud Run 在 demo 時還是要靠你家 GPU 主機透過 Cloudflare Tunnel 通——如果家裡停電或 tunnel flap 在演講中，AI feedback path 會掉到 `_basic_feedback_with_crisis_guard` 那層 canned response（誠實但明顯降級）。Rate limit 已在 commit 4f43145 加上，key 洩漏不再會把 GPU 打爛；**6/29 晚上輪換 key 仍是建議動作**。

### Defense 前要鎖定的事項
1. 確認你家 GPU 主機有 UPS、tunnel 設定 auto-reconnect
2. Demo 前 30 分鐘預熱 chat + vision 模型避免 first-token latency
3. **錄一段成功 end-to-end 寫日記 + AI 回饋的螢幕錄影**當網路降級時的 fallback
4. （Optional）家裡 GPU 主機設 `TRANSFORMERS_OFFLINE=1` 防 HF 主站 outage

---

## Commit 時間軸（最後 5 天）

| Commit | 變更 | 影響 |
|---|---|---|
| 5c430d6 | engine.py token-slice 修 prompt-leak 根因 + scrub at chokepoint | 新輸出永不漏 |
| 8922495 | 11 autofix（dashboard crash / push SSRF / email enum / 等） | 全項目消除 critical/high |
| 0749431 | sanitize boundary cut + AIFeedbackText 前端排版 | 歷史污染清乾淨 + UI 美化 |
| 7a349f5 | migration 0058 re-scrub | 1 row（note 952）已清 |
| ce3df57 | docs/phase0b-status.md | 本份文件初版 |
| **4f43145** | **rate limit + min-length + body counter + 註解/banner/caveat** | **本份文件覆蓋的 8 項全關** |
