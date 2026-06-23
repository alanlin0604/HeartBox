# Phase 0b 上線運維手冊（給 Alan 6/30 前的操作指南）

**最後修訂**：2026-06-23  
**目的**：把 Claude 寫好的 code 變成「真的在跑、評審當天不會掛」的系統。

整份 runbook 假設你站在 `C:\Users\alan9\OneDrive\Desktop\HeartBox`，用 PowerShell。所有指令都是 copy-paste 可用。

---

## 🔴 BLOCK DEMO — 必須完成才能 demo

### 1. Push 13 個 local commits 到 origin/main

**為什麼急**：整個 Phase 0b 全卡在你筆電。CI guard 從沒在 GitHub 跑過 → 不知道 cloud-side 還會不會 fail。Cloud Run 自動部署若綁 main，現在 production 還在跑 pre-migration 程式碼。

```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox
git status                              # 應該看到 "ahead by N commits"
git log origin/main..HEAD --oneline     # 確認 push 的內容
git push origin main
```

**驗證**：
```powershell
# 等 1-2 分鐘讓 GitHub Actions 跑
gh run list --workflow=no-openai-check.yml --limit 1
gh run view --log <run-id>              # 看 ✓ no banned OpenAI references found
```

**Rollback**：如果 CI 沒過 → `git push origin main --force-with-lease` 不要用，先看哪個檔出問題，本機修好再 push。

---

### 2. 建 `~/.heartbox-llm.env` + 起 FastAPI server

**為什麼**：`llm_server/main.py:create_app` 在 `settings.api_key` 為空時會 `raise RuntimeError('API_KEY missing')`。沒這個檔 → server 起不來 → demo 當天炸。

```powershell
# 產生 64 hex 的 API key（永久保存，記到密碼管理工具）
$env:USERPROFILE                        # 確認路徑是 C:\Users\alan9
$apiKey = python -c "import secrets; print(secrets.token_hex(32))"
Write-Output "API key (保存好): $apiKey"

# 寫進去
$envFile = "$env:USERPROFILE\.heartbox-llm.env"
@"
API_KEY=$apiKey
HOST=127.0.0.1
PORT=8765
CORS_ALLOW_ORIGINS=https://heartbox.tw,https://heartbox-api.onrender.com
HF_HOME=$env:USERPROFILE\.cache\huggingface
AUTOLOAD_ON_STARTUP=true
BNB_DISABLE=false
REQUEST_TIMEOUT_S=60
"@ | Out-File -FilePath $envFile -Encoding utf8 -NoNewline

# 確認
Get-Content $envFile
```

**起 server**：
```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\llm_server
.\start.bat
```

**驗證**（**另開一個 PowerShell 視窗**）：
```powershell
# health 不需要 API key
curl http://127.0.0.1:8765/health
# 應該回 {"status": "ok"}

# chat 需要 API key
$key = (Get-Content "$env:USERPROFILE\.heartbox-llm.env" | Select-String "^API_KEY=" | ForEach-Object { $_.Line.Split("=")[1] })
$body = '{"messages":[{"role":"user","content":"你好，今天心情有點低落"}],"max_tokens":80}' 
curl -X POST http://127.0.0.1:8765/v1/chat/completions `
  -H "X-API-Key: $key" `
  -H "Content-Type: application/json" `
  -d $body
```

**期待**：第一次起 server 會看到 `Loading TAIDE chat model ... TAIDE loaded in XX.Xs`，需要 30-90 秒。warm 之後 chat call 約 3-6 秒回。

**Rollback**：起不來 → `Get-Process python` 查殘留 process 殺掉；看 `llm_server` 視窗 stderr 的 traceback。

---

### 3. Smoke-test TAIDE + LLaVA 模型可載入

**為什麼**：weight 下載完 ≠ 載得起來。bitsandbytes / CUDA driver / transformers 版本錯配可能讓 4-bit NF4 quant 在 GPU 上炸開。**這必須在 Cloudflare Tunnel 接好之前先驗**。

```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\backend
.\venv\Scripts\Activate.ps1

# TAIDE 一發短 generate
python -c @"
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch, time
print('CUDA available:', torch.cuda.is_available(), 'name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')
t0 = time.time()
tok = AutoTokenizer.from_pretrained('taide/TAIDE-LX-7B-Chat')
m = AutoModelForCausalLM.from_pretrained(
    'taide/TAIDE-LX-7B-Chat',
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
    device_map='auto')
print(f'TAIDE loaded in {time.time()-t0:.1f}s VRAM={torch.cuda.memory_allocated()/1e9:.1f}GB')
inp = tok('哈囉，今天心情很差', return_tensors='pt').to(m.device)
out = m.generate(**inp, max_new_tokens=50, do_sample=False)
print('Output:', tok.decode(out[0], skip_special_tokens=True))
"@

# LLaVA 視覺 smoke test
python -c @"
from transformers import AutoProcessor, LlavaNextForConditionalGeneration, BitsAndBytesConfig
from PIL import Image
import torch, time, io, urllib.request
print('Loading LLaVA...')
t0 = time.time()
proc = AutoProcessor.from_pretrained('llava-hf/llava-v1.6-mistral-7b-hf')
m = LlavaNextForConditionalGeneration.from_pretrained(
    'llava-hf/llava-v1.6-mistral-7b-hf',
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
        bnb_4bit_compute_dtype=torch.bfloat16),
    device_map='auto')
print(f'LLaVA loaded in {time.time()-t0:.1f}s VRAM={torch.cuda.memory_allocated()/1e9:.1f}GB')
# Use a small public test image
img_bytes = urllib.request.urlopen('https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=200').read()
img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
prompt = '[INST] <image>\nWhat is in this picture? [/INST]'
inp = proc(text=prompt, images=img, return_tensors='pt').to(m.device)
out = m.generate(**inp, max_new_tokens=60, do_sample=False)
print('Output:', proc.tokenizer.decode(out[0], skip_special_tokens=True))
"@
```

**期待**：
- TAIDE warm load: 30-60 秒，VRAM 約 5-6 GB
- LLaVA warm load: 40-80 秒，VRAM 約 6-8 GB
- 兩者同時跑會超過 16 GB GPU；engine 設計是 lazy-swap 不會同時 hold

**常見失敗**：
| 錯誤 | 原因 | 修法 |
|---|---|---|
| `bitsandbytes not found` | venv 沒裝 | `pip install bitsandbytes` |
| `CUDA error: device-side assert` | driver 太舊 | 升級 NVIDIA driver |
| `OOM at load` | VRAM 不夠 | 設 `bnb_disable=true` 跑 fp16，需要 ~14 GB；或考慮 fp16 + offload |
| `OSError: Can't load tokenizer` | HF cache 損壞 | `huggingface-cli download taide/TAIDE-LX-7B-Chat --force` |

---

### 4. 部署 Cloudflare Tunnel

**為什麼**：Cloud Run（backend）跑在 GCP asia-east1，要打你家 RTX 3060 Ti 必須有反向通道。你家路由器 outbound-only 不開 inbound port，所以走 Cloudflare Tunnel（cloudflared）。

**步驟**：

```powershell
# 安裝 cloudflared（如還沒）
winget install --id Cloudflare.cloudflared

# 認證 — 會開瀏覽器登入 Cloudflare 帳號
cloudflared tunnel login

# 建 tunnel
cloudflared tunnel create heartbox-llm
# 記下顯示的 UUID，會在 .cloudflared/<UUID>.json

# 建設定檔
$tunnelId = (cloudflared tunnel list | Select-String "heartbox-llm" | ForEach-Object { $_.Line.Split()[0] })
$configDir = "$env:USERPROFILE\.cloudflared"
@"
tunnel: $tunnelId
credentials-file: $configDir\$tunnelId.json
ingress:
  - hostname: llm.heartbox.tw
    service: http://127.0.0.1:8765
    originRequest:
      noTLSVerify: true
      connectTimeout: 10s
  - service: http_status:404
"@ | Out-File -FilePath "$configDir\config.yml" -Encoding utf8

# DNS route（把 llm.heartbox.tw 指向 tunnel）
cloudflared tunnel route dns heartbox-llm llm.heartbox.tw

# 跑 tunnel（測試）
cloudflared tunnel run heartbox-llm
```

**驗證**：
```powershell
# 從其他網路（手機 4G）測
curl https://llm.heartbox.tw/health
# 應該回 {"status": "ok"} — 經 Cloudflare → tunnel → 家裡 127.0.0.1:8765
```

**安裝成 Windows service**（demo 當天不靠手動啟動）：
```powershell
# 以系統管理員 PowerShell 執行
cloudflared service install
sc.exe config Cloudflared start=auto
sc.exe start Cloudflared
```

**Rollback**：tunnel 跑不起來 → `cloudflared tunnel delete heartbox-llm` 重來；DNS record 可能要從 Cloudflare dashboard 手動刪。

---

### 5. 設 Cloud Run prod env 變數

**為什麼**：`render.yaml` 只宣告 key name（`sync: false`），實際值要 per-environment 填。沒填 → `remote_provider.is_configured()` 回 False → 所有 AI 端點 silently skip → 評審 demo 時全部回 fallback 罐頭。

**Render（如部署在 Render）**：
1. 開 https://dashboard.render.com/web/<service-id>/env
2. 加：
   ```
   LLM_PROVIDER=remote_taide
   LLM_SERVER_URL=https://llm.heartbox.tw
   LLM_SERVER_API_KEY=<步驟 2 那組 64 hex>
   CRON_SECRET=<另外產生一組 64 hex>
   ```
3. 按 "Save Changes" → Render 自動 redeploy

**Cloud Run（如部署在 GCP）**：
```powershell
gcloud run services update heartbox-api `
  --region=asia-east1 `
  --update-env-vars="LLM_PROVIDER=remote_taide,LLM_SERVER_URL=https://llm.heartbox.tw,LLM_SERVER_API_KEY=<key>,CRON_SECRET=<cron-key>"
```

**驗證**：
```powershell
# 等 deployment 完成（1-2 分鐘）
# 從前端發一筆 mood note，觀察 backend log（gcloud run logs read 或 Render log tab）
# 應該看到 "llm_call provider=remote_taide op=chat ... status=ok"
# 不應該看到 "LLM provider not configured"
```

---

### 6. 重灌知識庫到新 collection

**為什麼**：舊 collection `psychology_kb` 是 OpenAI 1536-dim embedding。新 collection `psychology_kb_bgem3` 是 bge-m3 1024-dim。不重灌 → RAG retriever 永遠回 0 結果 → 負面情緒回饋走 personalized 而非 RAG。

```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\backend
.\venv\Scripts\Activate.ps1

# 本地先驗
python manage.py load_knowledge_base --reset

# Production（Cloud Run / Render，從 dashboard SSH 或 deploy hook）
# 範例（Render shell）：
#   python manage.py load_knowledge_base --reset
```

**期待**：
```
[INFO] Loading 7 source files from knowledge_base/
[INFO] Embedding via bge-m3 (1024-dim)... 
[INFO] Wrote 142 chunks to collection psychology_kb_bgem3
```

**驗證**：
```powershell
python manage.py shell -c "from langchain_chroma import Chroma; from api.services.llm.embeddings import BgeM3Embeddings; v = Chroma(collection_name='psychology_kb_bgem3', embedding_function=BgeM3Embeddings(), persist_directory='./chroma_db'); print('count:', v._collection.count())"
# 應該回 count: 100+
```

---

### 7. 跑完整 143 tests（不要 --keepdb）

**為什麼**：之前都用 `--keepdb` 跑（沿用前一輪 dev DB）。production-shape 的乾淨 migration 從沒驗過。Phase 0b 改 `LLM_PROVIDER=mock` override 可能在 fresh DB 跑出 import-time regression。

```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\backend
.\venv\Scripts\Activate.ps1
.\venv\Scripts\python.exe manage.py test api --noinput 2>&1 | Tee-Object -FilePath test_run_clean.log
# 注意：拿掉 --keepdb，會重新建 test DB
```

**期待**：
```
Ran 164 tests in ~5 min
FAILED (failures=3)    # 3 個 pre-existing booking 失敗，跟之前一樣
```

**如果失敗超過 3 個 → 找 regression**：
```powershell
# 比對之前測試的 log
Compare-Object (Get-Content test_run.log) (Get-Content test_run_clean.log)
```

---

### 8. 手動實測 SSRF 防護

**為什麼**：`_verify_peer_ip` 用 httpcore 的 `server_addr` extension key。程式邏輯對，但實機 Windows asyncio backend 是否真的填值 — 沒驗過。如果填 None → 失敗封閉（拒絕請求）→ 視覺分析全炸；如果填對 → SSRF 攔截才有效。

```powershell
# 起 llm_server（步驟 2 那個視窗繼續開著）
$key = (Get-Content "$env:USERPROFILE\.heartbox-llm.env" | Select-String "^API_KEY=" | ForEach-Object { $_.Line.Split("=")[1] })

# 公網 image（正常情況）— 應該 200
curl -X POST http://127.0.0.1:8765/v1/vision `
  -H "X-API-Key: $key" `
  -H "Content-Type: application/json" `
  -d '{"messages":[{"role":"user","content":"describe"}],"image_urls":["https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=200"],"max_tokens":50}'

# 私網 image（攻擊情況）— 應該 400 "rejected non-public host"
curl -X POST http://127.0.0.1:8765/v1/vision `
  -H "X-API-Key: $key" `
  -H "Content-Type: application/json" `
  -d '{"messages":[{"role":"user","content":"x"}],"image_urls":["http://127.0.0.1:8765/health"]}'

# AWS metadata（典型 SSRF）— 應該 400
curl -X POST http://127.0.0.1:8765/v1/vision `
  -H "X-API-Key: $key" `
  -H "Content-Type: application/json" `
  -d '{"messages":[{"role":"user","content":"x"}],"image_urls":["http://169.254.169.254/latest/meta-data/"]}'
```

**期待**：第一個回 200（vision 結果），後兩個回 `{"detail":"rejected non-public host: ..."}`。

**如果公網的也 400 → server_addr 沒填值**：
```powershell
# 編輯 llm_server/main.py 的 _verify_peer_ip，暫時改成 warning + 不 raise
# 但這會打開 SSRF 窗口！只能緊急 demo 用，demo 完馬上修
```

---

### 9. 跑 5 次 dated rehearsal

**為什麼**：`docs/demo-rehearsal.md` 表格是空的。5 分鐘 demo budget 包含 LLaVA swap（~25s）、TAIDE 多輪對話（~3s × 5）、Cloudflare RTT、現場斷網風險都沒驗。

**每次 rehearsal 流程**（照 `docs/demo-rehearsal.md` step by step）：

```powershell
# 開始計時前先確認 stack 都活著
curl https://llm.heartbox.tw/health           # 應該 200
curl https://heartbox-api.onrender.com/health # 或 Cloud Run URL

# 開 5 分鐘倒數
$timer = New-Object System.Diagnostics.Stopwatch; $timer.Start()
# ... 走 demo 流程 ...
$timer.Stop(); Write-Output "完成時間: $($timer.Elapsed.TotalSeconds)s"
```

**填表**：每次跑完，在 `docs/demo-rehearsal.md` 的「演練紀錄」表格補一行。卡哪個步驟、總時間、有沒有需要修腳本。

**排程建議**：
- 6/23（今天）首跑 — 找出最大問題
- 6/25 — 修完問題後重跑
- 6/27 — 朋友當聽眾，要求他打斷你問挑釁問題
- 6/29 早上 — final dress rehearsal，stack 跟 demo 機都用最終配置
- 6/30 早上 — 場勘，確認場機網路、HDMI、麥克風

---

### 10. 錄 4 個 fallback 影片

**為什麼**：demo 機可能是場機（不是你的 RTX 3060 Ti），或現場網路掛掉。`docs/demo-rehearsal.md` 提到 `demo-01-login.mp4` 等 4 個檔，但實際沒人錄。

**錄製工具**（Windows 內建）：
- Win+G 開 Game Bar → 錄製目前視窗
- 或裝 OBS Studio 更穩

**4 段內容**（每段 30-60 秒）：
1. **demo-01-login.mp4** — 登入頁 → 主頁
2. **demo-02-note.mp4** — 新增 mood note + 即時看到 AI 分析跳出
3. **demo-03-rag.mp4** — 寫負面內容 → RAG 回饋帶心理學引用
4. **demo-04-vision.mp4** — 附圖 reanalyze → LLaVA 回應
5. **demo-05-crisis.mp4** — 寫 crisis keyword → hotline 橫幅 + 安心專線 1925

**保存**：
```powershell
# 放 demo 機桌面
$desk = [Environment]::GetFolderPath('Desktop')
mkdir "$desk\heartbox-fallback-videos" -Force
# 把 mp4 拖過去
```

---

## 🟠 ok-to-defer（6/30 前最好處理）

### 11. 驗 GitHub Actions 真的綠燈

完成第 1 步 push 後：
```powershell
gh run list --workflow=no-openai-check.yml --limit 3
# 看最新的 status 是不是 success
```
如果失敗：`gh run view <id> --log` 看哪個 grep hit。修完再 push。

### 12. 12 + 13 已完成
- ✅ `docs/defense-qa.md` 已加 Q13（obfuscation trade-off）+ Q14（SSRF 設計）
- ✅ `llm_server/tests/test_app.py` 已寫 21 個 integration test（auth ordering、body cap、CORS、SSRF helper、image-block normalize）

### 14. 14 已完成
- ✅ `docs/安全審查報告.md` + `docs/工作交接-2026-05-*.md` 的 `OPENAI_API_KEY` 殘留已清

---

## ⚠️ 維運面強化（demo 後仍需做）

### A. llm_server 變 Windows service（auto-restart）

`start.bat` 是手動腳本，process die 就掛了。改用 NSSM 包成 Windows service。

```powershell
# 裝 NSSM
winget install --id NSSM.NSSM

# 包成 service（系統管理員 PowerShell）
nssm install HeartBoxLLM "$env:USERPROFILE\OneDrive\Desktop\HeartBox\backend\venv\Scripts\python.exe"
nssm set HeartBoxLLM AppParameters "-m llm_server --host 127.0.0.1 --port 8765"
nssm set HeartBoxLLM AppDirectory "$env:USERPROFILE\OneDrive\Desktop\HeartBox"
nssm set HeartBoxLLM Start SERVICE_AUTO_START
nssm set HeartBoxLLM AppStdout "$env:USERPROFILE\heartbox-llm-stdout.log"
nssm set HeartBoxLLM AppStderr "$env:USERPROFILE\heartbox-llm-stderr.log"
nssm set HeartBoxLLM AppRotateFiles 1                # 自動日輪
nssm set HeartBoxLLM AppRotateBytes 10485760         # 10MB roll

# 啟動
nssm start HeartBoxLLM
nssm status HeartBoxLLM                              # 看是不是 SERVICE_RUNNING
```

**測 auto-restart**：
```powershell
# kill process，等 NSSM 自動拉起
Stop-Process -Name python -Force
Start-Sleep 5
nssm status HeartBoxLLM                              # 應該 SERVICE_RUNNING
```

### B. GPU 溫度自動警示

放在另一個 PowerShell 視窗跑：
```powershell
while ($true) {
    $smi = nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total --format=csv,noheader,nounits
    $vals = $smi -split ','
    $temp = [int]$vals[0]; $used = [int]$vals[1]; $total = [int]$vals[2]
    if ($temp -gt 80) { Write-Host "🔥 GPU 溫度 $temp °C — 暫停推論" -ForegroundColor Red }
    elseif ($used / $total -gt 0.9) { Write-Host "⚠ VRAM 90%+ ($used/$total MB)" -ForegroundColor Yellow }
    else { Write-Host "✓ temp=$temp °C  vram=$used/$total MB" -ForegroundColor Green }
    Start-Sleep 5
}
```

### C. Cloudflare 區域故障備用 Cloud Run revision

預先 deploy 一個 `LLM_PROVIDER=mock` 版本，緊急時一個指令切：
```powershell
# 先 deploy mock 版作為 standby
gcloud run deploy heartbox-api-mock-fallback `
  --image=gcr.io/<project>/heartbox-api:latest `
  --set-env-vars="LLM_PROVIDER=mock" `
  --no-traffic

# 緊急切流量到 mock
gcloud run services update-traffic heartbox-api `
  --to-revisions=heartbox-api-mock-fallback=100
```

### D. API key rotation（季度）

```powershell
# 1. 產新 key
$newKey = python -c "import secrets; print(secrets.token_hex(32))"

# 2. 更新 llm_server side
$envFile = "$env:USERPROFILE\.heartbox-llm.env"
(Get-Content $envFile) -replace "^API_KEY=.*", "API_KEY=$newKey" | Set-Content $envFile

# 3. 重啟 service
nssm restart HeartBoxLLM

# 4. 更新 backend side（Render dashboard / gcloud）
gcloud run services update heartbox-api --update-env-vars="LLM_SERVER_API_KEY=$newKey"

# 5. 驗
curl https://llm.heartbox.tw/health
curl https://heartbox-api.onrender.com/api/ai-chat/sessions/ # 用一個需要 LLM 的 endpoint
```

### E. 結構化 logging（Sentry / Cloudwatch / loki）

`llm_server` 目前 log 到 stdout/stderr。簡易方案：把 NSSM 的 stderr 接到 Sentry：

```python
# 在 llm_server/main.py 加（demo 後）：
import sentry_sdk
if os.getenv('SENTRY_DSN'):
    sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'), traces_sample_rate=0.1)
```

---

## 📋 快速 sanity checklist（demo 當天早上跑一次）

```powershell
# 0. 在家機（GPU machine）
nssm status HeartBoxLLM             # 應該 SERVICE_RUNNING
sc.exe query Cloudflared            # 應該 RUNNING
curl http://127.0.0.1:8765/health   # 應該 {"status":"ok"}

# 1. 從外網（手機開分享）
curl https://llm.heartbox.tw/health             # 應該 {"status":"ok"}
curl https://heartbox-api.onrender.com/health   # 或 Cloud Run

# 2. End-to-end smoke
# 在 demo 機開 browser → heartbox.tw → 登入 demo 帳號 → 寫一筆「今天好累」→
# 等 5-10 秒，應該看到 AI 回饋 + 不出現 "AI 分析暫時無法使用" banner

# 3. Crisis path
# 寫「我想死」→ 應該立刻看到 1925 hotline 橫幅 + AI 回應前段是同理 + 安心專線資訊

# 4. Vision path
# 上傳 1 張照片 → reanalyze → 應該看到 LLaVA 描述 + 情緒 reanalyzed
```

任何一條失敗 → 對照 runbook 步驟 1-10 修。

---

## 🆘 評審當天最壞情況 fallback 表

| 失敗模式 | 立刻動作 | 影響 |
|---|---|---|
| GPU 溫度 > 85 °C | 切 `LLM_PROVIDER=mock`（步驟 5 改 env redeploy）| AI 回固定文字，crisis 偵測仍可用 |
| Cloudflare tunnel 掛 | 切 standby mock revision（維運面 C）| 同上 |
| 場機網路斷 | 播 `demo-01~05.mp4` 預錄影片 | 失去互動感但 demo 還能進行 |
| TAIDE 載不起來 | 改 `TAIDE_MODEL_ID=yentinglin/Llama-3-Taiwan-8B-Instruct` 重啟 service | 模型 fallback，論述需多解釋 |
| 評審問「為什麼 e.n.d i.t a.l.l 抓不到」 | 答 `docs/defense-qa.md` Q13 | 已預備 |
| 評審問 SSRF 怎麼做 | 答 `docs/defense-qa.md` Q14 | 已預備 |

---

## 📁 Phase 0b 完整檔案清單（不要動）

**核心 code（已 commit）**：
- `backend/api/services/llm/{base,factory,mock_provider,remote_provider,crisis_guard,embeddings,__init__}.py`
- `backend/api/services/crisis_detector.py`
- `backend/api/services/ai_engine.py`、`ai_chat.py`
- `backend/api/views/{notes,__init__,analytics,health}.py`
- `backend/api/tests.py`、`backend/api/test_crisis_guard.py`（53 tests）
- `backend/api/apps.py`（含 bge-m3 pre-warm）
- `backend/api/management/commands/load_knowledge_base.py`
- `backend/moodnotes_pro/settings.py`、`backend/.env.render.example`
- `llm_server/{main,engine,config,__main__,__init__}.py`、`start.bat`、`README.md`
- `llm_server/tests/test_app.py`（21 tests）
- `requirements.txt`、`requirements-llm.txt`
- `backend/download_models.py`、`backend/check_env.py`

**Docs（評審 pre-read 會看）**：
- `README.md`、`render.yaml`
- `docs/llm-runbook.md`、`docs/defense-qa.md`、`docs/demo-rehearsal.md`
- `docs/system-architecture.md`、`docs/feature-modules.md`、`docs/system-components.md`
- `docs/簡報內容-更新版.md`、`docs/簡報內容-核心技術.md`
- `docs/setup-guide.md`、`docs/安全審查報告.md`
- `frontend/src/locales/{en,zh-TW,ja}.json`（privacy.s3Body 三語系）

**CI**：
- `.github/workflows/no-openai-check.yml`

---

## 🎯 一句話總結

Code 部分都已寫好、commit 好、test 過。**剩下的 1-10 全是「離開鍵盤實際動手」的事**：push、配置 env、起 service、實測。每一條對你都不到 30 分鐘。連續做完約 4-6 小時，可以分兩天。

最重要：**先做第 1 步（push）+ 第 2 步（起 server）+ 第 3 步（smoke-test model）**。這三步通了，後面的 tunnel / Cloud Run / load_kb 都是依序套上去而已。
