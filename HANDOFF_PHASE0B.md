# HeartBox Phase 0b LLM Migration — Handoff (2026-06-22)

## 大架構

正在做 **OpenAI → 自架繁中 LLM (TAIDE + LLaVA + bge-m3)** 大遷移，目標 6/30 大學專題評審。

- Phase 0b 設計 workflow `wt5pb0krw` 已完成（28 個檔案的設計藍圖）
- 我已寫好 28 個檔案 + 4 個 refactor + 跑過 143 tests（3 fail 全 pre-existing booking 不是 LLM regression）
- Adversarial review workflow `wrpzx3q94` 完成 — **找出 33 個 confirmed bugs（17 HIGH + 16 MEDIUM）**

## 仍跑著的 Background Tasks（重要）

新 session 可能拿不到這些 task ID，請先確認：

| Task ID | 內容 | 預估完成 |
|---|---|---|
| python -m download_models.py | TAIDE 下載中（~14GB, 1/11 files when paused） | 約 15-20 分 |

Check 用：
```powershell
tail -20 C:\Users\alan9\OneDrive\Desktop\HeartBox\backend\download_models.log
```

如果 TAIDE 顯示 `[OK] done`，下載完成 ✅。

## 已完成（不要重做）

### 寫好的 28 個新檔 / refactor 過的檔案

- `backend/api/services/llm/__init__.py` `base.py` `factory.py` `mock_provider.py` `remote_provider.py` — provider seam
- `backend/api/services/llm/crisis_guard.py` + `backend/api/test_crisis_guard.py`（28 tests 都過）
- `backend/api/services/llm/embeddings.py` — BGE-M3 LangChain adapter
- `backend/api/services/ai_engine.py` — refactor 過用 provider seam
- `backend/api/services/ai_chat.py` — refactor 過用 provider seam
- `backend/api/management/commands/load_knowledge_base.py` — 改用 bge-m3 + `psychology_kb_bgem3` collection
- `backend/api/views/__init__.py` — `_get_openai_client` → `_get_llm_provider_or_none`
- `backend/api/views/analytics.py` `health.py` — 移除 hardcoded `'gpt-4o-mini'`
- `backend/moodnotes_pro/settings.py` — 移除 OPENAI_*, 加 LLM_*, CHROMA_COLLECTION_NAME
- `requirements.txt` — 移除 `openai` `langchain-openai`, 加 `sentence-transformers` `httpx`
- `llm_server/` (7 files) — `__init__.py` `__main__.py` `config.py` `engine.py` `main.py` `start.bat` `README.md`
- `.github/workflows/no-openai-check.yml` — CI guard
- `docs/llm-runbook.md` `docs/defense-qa.md` `docs/demo-rehearsal.md`
- `backend/download_models.py` `backend/check_env.py` `requirements-llm.txt`

### Batch 1 部分修好（已 apply）

- ✅ `settings.py` — `LLM_SERVER_URL` 預設改空字串、`LLM_TIMEOUT_S` 用 `or '30'` handle 空字串
- ✅ `remote_provider.py` — `is_configured()` 要求 URL AND api_key 都有
- ✅ `mock_provider.py` — `is_configured()` 改讀 `settings.LLM_MOCK_CONFIGURED`（預設 True）
- ✅ `backend/api/tests.py` — 3 個 `@override_settings(OPENAI_API_KEY='')` → `(LLM_PROVIDER='mock', LLM_MOCK_CONFIGURED=False)`
- ✅ `AIChatTests.setUp/tearDown` 加 `reset_llm_provider_cache()`
- ✅ `AISentimentTests` 加 class-level `@override_settings` + reset

## 未完成（請繼續做）

### 🔴 Batch 1 剩餘：CI no-openai-check 還會 fail

[bug #2] CI guard 跑下去會找到 12 個違規在 8 個檔案，會擋 PR merge：

1. `backend/api/tests.py:855,887,904` — 已修（OPENAI_API_KEY 字串已換掉）
2. `backend/api/services/llm/base.py:83` — docstring 含 `gpt-4o-mini did.`
3. `backend/api/services/llm/remote_provider.py:194` — comment 含 `at JSON than gpt-4o-mini`
4. `render.yaml:23` — `- key: OPENAI_API_KEY`
5. `RESTORE.md:153,269` `BACKUP_CHECKLIST.md:58` `CLAUDE_INSTRUCTIONS.md:30,87` `DEPLOYMENT_CHECKLIST.md:13` — docs 提到 OPENAI_API_KEY
6. `backend/.env.render.example` — 含 `OPENAI_API_KEY=` + `OPENAI_MODEL=gpt-4o-mini`

**建議修法**：
- base.py / remote_provider.py 改掉 `gpt-4o-mini` 字串成 `small models`
- 刪除 render.yaml 的 OPENAI_API_KEY 那一行
- 改 docs/.md 的 OPENAI 提及成 LLM_SERVER_URL/LLM_SERVER_API_KEY
- `.env.render.example` 把 OPENAI_* 兩行刪掉、加 LLM_* 行

### 🟠 Batch 2：Crisis guard 安全 gap（3 個 HIGH bug）

修 `backend/api/services/llm/crisis_guard.py` 和 `backend/api/services/crisis_detector.py`：

**[bug #14]** `\bwant(?:ing|s|ed)?\s+to\s+die\b` 漏掉 — 加到 `crisis_detector._CRISIS_PATTERNS`，補英文 high pattern 也要加 `\b(?:overdose|jump\s+off)\b`。同時補測試 case「I want to die」「wanting to die」進 `test_crisis_guard.py`。

**[bug #13]** Obfuscation bypass — 加 normalize pass：
```python
# crisis_guard.py 加 helper
_NORMALIZE = re.compile(r'[\W_]+')
def _normalized(text):
    return _NORMALIZE.sub('', text.lower())
# detect() 先對 raw text 跑 HIGH/MEDIUM scan，再對 _normalized(text) 跑 HIGH scan（補抓 k.i.l.l 之類）
```

**[bug #12]** Locale guess 亂跑 — 改成 count-based：
```python
@staticmethod
def _guess_locale(text):
    h = len(_HIRAGANA_KATAKANA.findall(text))
    c = len(_CJK.findall(text))
    a = len(_ASCII_ALPHA.findall(text))
    if h > max(c, a): return 'ja'
    if a > max(h, c): return 'en'
    if c > 0: return 'zh-TW'
    return 'zh-TW'
```

### 🟠 Batch 3：llm_server 安全強化（6 個 HIGH bug）

修 `llm_server/engine.py` 和 `llm_server/main.py`：

**[bug #3]** `load_taide` / `load_llava` 沒 try/except — partial state poisoning。包 try，失敗時保留舊 model 不要先 release。

**[bug #4]** `asyncio.wait_for` 不 cancel HF generate — 改用 `TextIteratorStreamer + StoppingCriteria(check Event)`，或最少：timeout 不要釋放 `_swap_lock` 直到 worker thread 真的 join。

**[bug #5]** Auth 排在 body parse 後 — 改 ASGI middleware 在 body parse 前驗 `X-API-Key`。

**[bug #6]** Body-size 中介層 bypass — 改 `request.stream()` 累積 bytes 超過 cap 就 413，並擋 `Transfer-Encoding: chunked`。

**[bug #7]** PIL decompress bomb — 加：
```python
import warnings
warnings.simplefilter('error', Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = 4096 * 4096
# 檢查 img.size：if w*h > MAX_PIXELS: reject
```

**[bug #8]** SSRF — `_fetch_images` 解析 host → `socket.getaddrinfo` → reject `is_private/is_loopback/is_link_local/is_reserved/is_multicast`。停 `follow_redirects` 或每跳重驗。

### 🟠 Batch 4：ai_engine 邊角 case（2 個 HIGH + 1 個用到的 fix）

**[bug #9]** `analyze_with_images` 傳 `/media/xxx.jpg`（FileField.url 是 relative path）給遠端 LLaVA — LLaVA 永遠 404。修法：在 `views/notes.py` 用 `request.build_absolute_uri(att.file.url)` 或在 worker 把檔案讀成 `data:` URI 傳。

**[bug #10]** Tier-1 feedback 失敗會掉 HIGH-crisis hotline — `_generate_personalized_feedback` except 內呼叫 `_generate_basic_feedback` 沒帶 crisis hotline。修法：在 except 內先 detect 再 `prepend_hotline`。

**[bug #15]** `remote_provider.py:107` 拆 response 沒擋 `None.get(...)` 會 raise `AttributeError`，違反「所有錯誤包 LLMProviderError」契約。修法：加 `AttributeError, TypeError` 到 `except (ValueError, KeyError, AttributeError, TypeError)`。

### MEDIUM 16 個

跑這個指令可拿全部細節：
```bash
PYTHONIOENCODING=utf-8 python -c "import json,sys; sys.stdout.reconfigure(encoding='utf-8'); d=json.load(open(r'C:\Users\alan9\AppData\Local\Temp\claude\c--Users-alan9-OneDrive-Desktop-HeartBox\fa1b1d96-512d-493d-aada-d494cac3ce3e\tasks\wrpzx3q94.output', encoding='utf-8')); [print(f\"## {b['severity']}|{b['dimension']}: {b['title']}\\n{b['detail'][:800]}\\nFIX: {b.get('suggested_fix','')[:400]}\\n\") for b in d['result']['confirmed_bugs'] if b['severity']=='MEDIUM']"
```

主要 MEDIUM 主題：
- `parse_json_tolerant` 用 greedy regex（不是 docstring 說的 "first balanced object"）
- `_CRISIS_PATTERNS` 裡 `r'自殺'` 重複出現
- `except (LLMProviderError, Exception)` 等同 `except Exception`
- `/v1/switch_model` 釋放 lock 後別人 generate 中可以再 swap（race）
- `/health` 不需 auth 卻洩漏 model 名稱
- Tokenizer `truncation=False` 可被 prompt bomb DoS
- `_build_chat_prompt` 默默丟掉 chat path 的 image content blocks
- bge-m3 lazy load → 第一個 deploy 後請求等 5-30s
- Cached retriever 不會在 `load_knowledge_base --reset` 後失效
- Demo step 3:30 提到 `/about/architecture` 但 route 不存在
- Runbook + README + factory.py 對 `LLM_PROVIDER=openai` 是否支援講法不一致
- `.env.render.example` 還寫著 OPENAI_API_KEY / gpt-4o-mini

### 其他要做的

- **跑 143 tests** 確認 Batch 1 fixes 沒 break 既有測試：
  ```powershell
  cd C:\Users\alan9\OneDrive\Desktop\HeartBox\backend
  ./venv/Scripts/python.exe manage.py test api --keepdb --noinput
  ```
- **TAIDE 下載完成後**：寫 smoke test 驗證模型真的能跑（測試腳本可以是這樣的 PowerShell）：
  ```powershell
  # 用 transformers 直接 load TAIDE 跑一句話
  ./venv/Scripts/python.exe -c "
  from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
  import torch
  tok = AutoTokenizer.from_pretrained('taide/TAIDE-LX-7B-Chat')
  m = AutoModelForCausalLM.from_pretrained('taide/TAIDE-LX-7B-Chat',
      quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16),
      device_map='auto')
  inp = tok('哈囉，今天心情很差', return_tensors='pt').to(m.device)
  out = m.generate(**inp, max_new_tokens=50)
  print(tok.decode(out[0], skip_special_tokens=True))
  "
  ```
- **啟動 FastAPI server smoke test**：
  ```powershell
  # 創 ~/.heartbox-llm.env 含 API_KEY=<隨機>
  python -c "import secrets; print(secrets.token_hex(32))" > %USERPROFILE%\.heartbox-llm-key.txt
  # 編輯 ~/.heartbox-llm.env：API_KEY=<上面那串>
  cd C:\Users\alan9\OneDrive\Desktop\HeartBox\llm_server
  .\start.bat
  # 另一視窗：
  curl http://127.0.0.1:8765/health
  ```
- **Commit Phase 0b 全部變更**（建議分 commit）：
  1. `feat(llm): provider seam + factory + mock + remote_taide`
  2. `feat(llm): crisis guard with 28 unit tests`
  3. `feat(llm): bge-m3 embeddings adapter + load_knowledge_base for new collection`
  4. `refactor: ai_engine + ai_chat use LLMProvider seam, removed OpenAI`
  5. `feat(llm-server): FastAPI inference server for TAIDE + LLaVA`
  6. `chore: no-openai CI guard + runbook + defense Q&A docs`
  7. `fix(llm): Batch 1 review findings — startup safety + test override`
  8. `fix(crisis): Batch 2 — want-to-die pattern + obfuscation + locale priority`
  9. `fix(llm-server): Batch 3 — auth ordering + body cap + SSRF guard + bomb`
  10. `fix(llm): Batch 4 — image URL absolute + crisis hotline preserved + error wrap`

## 環境提醒

- HF token 已重設、有效 — `whoami` 應該回 alan064
- HF token 不要貼在 chat 裡（之前 session 你撤銷過洩漏的 token），如果新 session 我需要 token，用 `huggingface-cli whoami` 確認你已登入即可
- TAIDE License 已 ACCEPTED
- 3 個下載完成：bge-m3 ✅ LLaVA ✅ Llama-3-Taiwan-8B ✅
- TAIDE 下載中（暫停時 1/11）

## 重要檔案路徑

- Adversarial review 完整結果：`C:\Users\alan9\AppData\Local\Temp\claude\c--Users-alan9-OneDrive-Desktop-HeartBox\fa1b1d96-512d-493d-aada-d494cac3ce3e\tasks\wrpzx3q94.output`（JSON, ~270 KB）
- Phase 0b 設計：`tasks\wt5pb0krw.output`
- 下載 log：`backend\download_models.log`
- 既有 test runs log：`backend\test_run.log`

## 給新視窗 Claude 的 prompt 建議

> 「我正在做 HeartBox 的 Phase 0b LLM 遷移（OpenAI → 自架 TAIDE/LLaVA/bge-m3），6/30 大學專題評審 deadline。讀 `HANDOFF_PHASE0B.md` 然後繼續從 Batch 1 剩餘工作（CI no-openai-check 違規）開始。先跑 143 tests 確認 Batch 1 已 apply 的 fixes 沒造成 regression，再開始 Batch 2 crisis guard 修法。Ultracode 開著。」
