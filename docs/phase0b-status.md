# Phase 0b 狀態報告：OpenAI → 自架 LLM 遷移

**日期**：2026-06-25
**Capstone Defense**：2026-06-30（5 天後）
**生產環境**：Cloud Run `heartbox-api-00180-nnj`（4Gi） + Cloudflare Tunnel `llm.heartbox.tw` → 家裡 GPU `127.0.0.1:8765`

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

## 仍待處理（11 個，全部 LOW / INFO，1 個 MEDIUM）

| Severity | 維度 | Owner | 為什麼還沒做 |
|---|---|---|---|
| **MEDIUM** | llm_server rate limiting | assistant-can-do | 沒有 slowapi / token-bucket / per-IP throttle。被洩漏的 API key 可以對 tunnel 持續打到 GPU 耗盡，到金鑰輪換為止。**可用性問題，不是洩密**。`_swap_lock` 天然序列化 (~1 req/5-15s) + Cloudflare edge throttle 已經算自然防禦。建議用 slowapi sliding-window keyed by `X-API-Key`，這樣可以發多把 key 分別 revoke。 |
| LOW | API_KEY 最小長度 / 熵 | assistant-can-do | [config.py:34](../llm_server/config.py#L34) 只檢查非空；理論上 `API_KEY=x` 也會 boot 並接受 1-char key。加 Pydantic `Field(min_length=32)` 或 startup assertion 就好。 |
| LOW | Body-size middleware streaming-bytes 強制 | assistant-can-do | [main.py:387-398](../llm_server/main.py#L387-L398) 信任 `Content-Length`。Uvicorn/Starlette 在 transport 層強制 declared CL 所以實際安全，但 defense-in-depth 應該 wrap `await request.body()` 進 counting reader。 |
| LOW | `log_prompts` dead config flag | assistant-can-do | [config.py:52](../llm_server/config.py#L52) parse 進 Settings 但 main.py / engine.py grep 都找不到使用。資安角度算好（任何 path 都不會 log prompt），但 dead flag 誤導 operator。 |
| LOW | `MoodNote.ai_feedback` 沒加密 | **user-must-do** | [models.py:95](../backend/api/models.py#L95) `ai_feedback` 是 plaintext `TextField`。系統 prompt 禁止 verbatim echo + `scrub_llm_output` 切 boundary，但推論出來的情緒 + paraphrase 還是 plaintext。如果 threat model 加 DB-dump 場景才要 Fernet 包，**需要 product owner 決定**（list-view 不需要 decrypt 是 trade-off；retroactive 加密要 data migration 而且打掉 LIKE search）。 |
| LOW | 註解還寫 OpenAI | assistant-can-do | [notes.py:273,278](../backend/api/views/notes.py#L273) 還寫「5-15s OpenAI roundtrip」「failed OpenAI call」。[tasks.py:16](../backend/api/tasks.py#L16) 還寫「OpenAI throttle」。[tests.py:1518](../backend/api/tests.py#L1518) docstring 還提「OpenAI key is missing」。純文件 drift，實際呼叫已走本地 TAIDE seam。改成「LLM roundtrip / LLM throttle / LLM provider unconfigured」。 |
| LOW | 本機 venv 殘留 `openai` 1.78.1 + `langchain-openai` 0.3.18 | **user-must-do** | `backend/venv/Lib/site-packages` 裡有殘留。**`requirements.txt` 沒釘**，**沒被任何非 venv source import**，Cloud Run 每次都 reinstall 所以 deploy 0 影響。純本機磁碟衛生問題。在你的工作站跑 `rm -rf backend/venv && python -m venv backend/venv && pip install -r requirements.txt` 即可。 |
| LOW | Archive docs 還提 OpenAI | assistant-can-do | `docs/archive/專案全面審查與改進建議.md:71` 還列 `OPENAI_API_KEY`。`docs/archive/全面改進建議報告.md:291` 還寫「AI: OpenAI GPT-4, LangChain, ChromaDB」。在 `/docs/archive/` 下可接受，但加一行 deprecation banner 避免被 defense panel grep 到舊版。 |
| INFO | `search_text` plaintext 預覽要文件化 | assistant-can-do | [models.py:96,133](../backend/api/models.py#L96) `search_text` 存 `strip_tags(raw)[:500]` plaintext 給 LIKE search。設計可接受但要在 `docs/defense-qa.md` 寫清楚——「AES-256 加密日記」claim 要 qualify「除了前 500 字明文預覽以外」。若 panel 問「日記是不是完全加密」runbook 要先答到避免 gotcha。 |
| INFO | `sanitize._ROLE_NAMES` 含 bot 名字 | assistant-can-do | `小心` 是 AI persona name 但也是中文「小心、注意」動詞。理論上 `小心：你應該休息一下` 會被剝。替換成空白所以後面文字會留下。Cosmetic — 加 comment 註明 trade-off 即可。 |
| INFO | huggingface.co cold-cache load path | **user-must-do** | llm_server 沒設 `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE`。如果 HF_HOME cache 被清光，下次載入會去 huggingface.co。**不是日記資料外流**（只是模型權重），但是維運顧慮。Mitigation：透過 [backend/download_models.py](../backend/download_models.py) 預熱，然後設 `TRANSFORMERS_OFFLINE=1`。 |

---

## OpenAI 殘留判決（一段）

**Production code 沒有任何 live OpenAI 依賴。** 靜態分析確認非 venv Python source 裡 0 個 `import openai` / `from openai` / `OpenAI(` / `ChatCompletion` / `Embedding.create` / `api.openai.com`；`requirements.txt`、`requirements-llm.txt`、root `package.json`、`frontend/package.json` 都沒有商用 AI SDK；`render.yaml` 無 `OPENAI_API_KEY`。Factory 只接受 `remote_taide` 和 `mock`，舊的 `openai` 字串會丟 error 且有 regression test + CI workflow 雙重把關。剩餘 occurrence 都是良性類別：(a) 註解 / docstring 記錄遷移歷史，(b) wire-format 引用（自架 llm_server 暴露 OpenAI-shape JSON 端點為了重用一個 HTTP client），(c) 防禦性檢查（regression test + pre-deploy secret scanner regex），(d) 本機 venv 殘留（`openai 1.78.1` + `langchain-openai 0.3.18`，不在 requirements 裡也沒被 import，Cloud Run 每次 reinstall 都是乾淨的）。**遷移 production-complete。**

---

## 資安判決（一段）

**端到端資安狀態為 defense 窗口可接受。** 日記內容用 Fernet（含 MultiFernet rotation）靜態加密，`ENCRYPTION_KEY` 在 boot 驗證為 32-byte url-safe-b64；傳輸用 HTTPS 終結於 Cloudflare Tunnel 內部 `127.0.0.1:8765`，全程無 `verify=False`。llm_server 在 Pydantic parse 前先用 `hmac.compare_digest` 比 API key、雙 pass SSRF 防禦（用對的 httpcore `server_addr` extension 關閉 DNS-rebind TOCTOU window）、8MB/16MP 圖片限制 + 中段 abort、雙層 body-size 強制（拒絕 chunked-encoding 繞道）、嚴格 CORS allowlist 無 wildcard 且 credentials disabled、docs surface 關閉（無 swagger fingerprint）、cooperative-cancel 完整（StoppingCriteria + thread join + atomic-swap loader）讓 timed-out / 客戶端斷線的 generation 不會留 GPU-holding zombie 在 `_swap_lock` 後面。Django provider seam 在單一 chokepoint 跑 `scrub_llm_output`、消費端再二次清洗、CrisisGuard 在每個 LLM path 和每個 non-LLM fallback path 都對稱跑 BEFORE（preamble inject）+ AFTER（hotline prepend），NFKC + per-clause normalization 抗 obfuscation + HIGH-first severity sweep。Logging 不寫 prompt / reply / system prompt / user content / key 內容——只寫 structured field（provider/op/model/latency_ms/status）+ `removed_chars` 計數。兩個實質 gap 是 llm_server 沒 in-process rate limit（MEDIUM，可用性問題，被 GPU 序列化 + Cloudflare edge throttle 自然緩解）+ API_KEY 沒最小長度檢查（LOW，operator hygiene）；其餘都是 cosmetic 用詞 drift、dead config flag、或已 document 的設計 trade-off（ai_feedback plaintext、search_text plaintext 預覽）。

---

## Capstone 準備度（2026-06-30）

**準備好。** 遷移 production-complete、prompt-leak 修法（5c430d6 / 0749431 / 7a349f5）已 deploy、migration 0058 已掃過歷史 row、本機 llm_server PID 66980 已 patch、`llm.heartbox.tw` tunnel 健康。Data-sovereignty 論述寫在 [docs/defense-qa.md](defense-qa.md)，runbook 在 [docs/llm-runbook.md](llm-runbook.md)。

**最大殘餘風險是維運不是資安**：Cloud Run 在 demo 時還是要靠你家 GPU 主機透過 Cloudflare Tunnel 通——如果家裡停電或 tunnel flap 在演講中，AI feedback path 會掉到 `_basic_feedback_with_crisis_guard` 那層 canned response（誠實但明顯降級）。次要風險是 llm_server 沒 rate limit；只要 `LLM_SERVER_API_KEY` 在 8 天內不洩漏就沒事，**6/29 晚上輪換 key 是標準衛生動作**。

### Defense 前要鎖定的事項
1. 確認你家 GPU 主機有 UPS、tunnel 設定 auto-reconnect
2. Demo 前 30 分鐘預熱 chat + vision 模型避免 first-token latency
3. **錄一段成功 end-to-end 寫日記 + AI 回饋的螢幕錄影**當網路降級時的 fallback
4. （Optional）freeze 前 land llm_server slowapi rate-limit patch（若你願意再改一輪 code）

---

## 我可以接下來幫你做的（如果你想繼續）

按優先序：

1. **llm_server slowapi rate limit**（MEDIUM）— 防禦 key 洩漏後的 GPU 耗盡
2. **API_KEY min-length validator**（LOW）— 一行 Pydantic field
3. **註解 / docstring 改 OpenAI → LLM**（LOW）— 純文字 drift
4. **Archive docs 加 deprecation banner**（LOW）— 防 defense panel grep 到舊版
5. **`docs/defense-qa.md` 補一段 `search_text` 預覽明文的 caveat**（INFO）

需要哪幾個就跟我說。本機 venv 清理 + `TRANSFORMERS_OFFLINE` 設定要你自己在工作站做（我沒辦法摸你的 PowerShell）。
