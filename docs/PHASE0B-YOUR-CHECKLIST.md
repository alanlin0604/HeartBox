# Phase 0b 剩下你要做的事（給 Alan 的可勾選清單）

**最後修訂**：2026-06-23（demo 倒數 7 天）  
**先決條件**：以下所有事已由 Claude 完成 — 你不用再做。
- ✅ Code 全部 push 到 origin/main（17 commits）
- ✅ GitHub Actions 雙綠（CI + no-openai-check）
- ✅ `~/.heartbox-llm.env` 已建（API key 在裡面）
- ✅ TAIDE / LLaVA / bge-m3 / Llama-3-Taiwan 4 個模型 weight 已下載
- ✅ 本機 `llm_server` 已驗 boot → /health → /v1/chat → SSRF 防禦全部通過
- ✅ 本機 ChromaDB collection `psychology_kb_bgem3` 已灌 104 chunks
- ✅ 全套 164 個 Django tests + 21 個 llm_server tests 全綠
- ✅ booking date-bomb（CI 紅燈的真兇）已修

---

## 🎯 三條路線：依時間預算選

| 路線 | 時間 | 完成度 | 適合 |
|---|---|---|---|
| **A. 最小可行（demo 跑得起來）** | 60 分鐘 | 70% | 緊急情況、demo 在即 |
| **B. 推薦（demo + fallback 安全網）** | 3-4 小時 | 95% | 評審週、認真模擬 |
| **C. 完整（含維運面）** | 8-10 小時（分兩天）| 100% | 真的要上線給人用 |

---

# 路線 A：最小可行（60 分鐘）

跑完這條，產品在線、評審現場至少能 demo 一輪。

### A1. 上 Cloudflare Tunnel（45 分）
→ 看下方 [§1 Cloudflare Tunnel 完整指南](#1-cloudflare-tunnel-完整指南)

### A2. 設 Cloud Run / Render 環境變數（10 分）
→ 看下方 [§2 設 production env 變數](#2-設-production-env-變數)

### A3. 灌 production 知識庫（5 分）
→ 看下方 [§3 Production 重灌 knowledge_base](#3-production-重灌-knowledge_base)

完成這 3 步 → demo 流程可走。

---

# 路線 B：推薦（3-4 小時，分兩天做）

路線 A 完整 + 加上：

### B4. 跑 1 次 dated rehearsal（30 分）
→ 看下方 [§4 Dated rehearsal 流程](#4-dated-rehearsal-流程)

### B5. 錄 5 段 fallback 影片（60-90 分）
→ 看下方 [§5 錄 fallback mp4](#5-錄-fallback-mp4)

### B6. demo 早上 sanity checklist（10 分，當天做）
→ 看下方 [§6 demo 當天早上 checklist](#6-demo-當天早上-checklist)

---

# 路線 C：完整（8-10 小時）

路線 B + 加上維運面（demo 後 vs 前都可做）：

### C7. NSSM 包 llm_server 成 Windows service（30 分）
→ 看下方 [§7 llm_server 自動啟動](#7-llm_server-自動啟動)

### C8. GPU 溫度自動監控（10 分）
→ 看下方 [§8 GPU 監控](#8-gpu-監控)

### C9. 預備 mock fallback Cloud Run revision（30 分）
→ 看下方 [§9 Mock fallback revision](#9-mock-fallback-revision)

### C10. 季度 API key 輪替演練（10 分）
→ 看下方 [§10 API key rotation](#10-api-key-rotation)

---

---

# §1. Cloudflare Tunnel 完整指南

**為什麼非做不可**：你的 Cloud Run（asia-east1）backend 需要打到家裡 RTX 3060 Ti 跑 TAIDE 推論。家裡路由器 outbound-only（不開 inbound port），唯一通道是 Cloudflare Tunnel（cloudflared）反向打洞。

**前置條件檢查**：
```powershell
# 確認你有 Cloudflare 帳號 + heartbox.tw 已加入 Cloudflare DNS
# 開 https://dash.cloudflare.com/ → 看 Websites 列表有沒有 heartbox.tw
# 沒有的話兩個選擇：
#   (a) 把 heartbox.tw 加進 Cloudflare（要改 nameserver）
#   (b) 用 *.trycloudflare.com 臨時 subdomain（不適合 demo，會變）
# 假設你用 (a)。
```

## 1.1 安裝 cloudflared

```powershell
# 系統管理員 PowerShell
winget install --id Cloudflare.cloudflared
# 重開 PowerShell（PATH 才會生效）
cloudflared --version
```

**預期**：印出 `cloudflared version 2024.x.x` 之類。

**如果失敗**：
- `winget` 沒安裝 → 從 Microsoft Store 裝 App Installer
- 或直接下載 `cloudflared.exe` 從 https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe，丟到 `C:\Windows\System32\`

## 1.2 認證 Cloudflare 帳號

```powershell
cloudflared tunnel login
```

**會發生**：
1. 開瀏覽器到 Cloudflare dashboard
2. 你選 `heartbox.tw` zone
3. 按 "Authorize"
4. PowerShell 印出 `You have successfully logged in. ... /Users/alan9/.cloudflared/cert.pem`

**預期**：`$env:USERPROFILE\.cloudflared\cert.pem` 出現。

## 1.3 建 tunnel

```powershell
cloudflared tunnel create heartbox-llm
```

**會印出**：
```
Tunnel credentials written to C:\Users\alan9\.cloudflared\<UUID>.json
Created tunnel heartbox-llm with id <UUID>
```

**把 UUID 記下來**（或之後從 `cloudflared tunnel list` 拿）。

## 1.4 寫 config.yml

```powershell
$tunnelId = (cloudflared tunnel list 2>&1 | Select-String "heartbox-llm" | ForEach-Object { ($_.Line -split '\s+')[0] })
Write-Host "Tunnel UUID: $tunnelId"

$configDir = "$env:USERPROFILE\.cloudflared"
$config = @"
tunnel: $tunnelId
credentials-file: $configDir\$tunnelId.json

ingress:
  - hostname: llm.heartbox.tw
    service: http://127.0.0.1:8765
    originRequest:
      connectTimeout: 10s
      tlsTimeout: 10s
      noTLSVerify: true
  - service: http_status:404
"@
$config | Out-File -FilePath "$configDir\config.yml" -Encoding utf8 -NoNewline
Get-Content "$configDir\config.yml"
```

## 1.5 DNS 路由

```powershell
cloudflared tunnel route dns heartbox-llm llm.heartbox.tw
```

**會印出**：`Added CNAME llm.heartbox.tw which will route to this tunnel ...`

**驗證**：開 Cloudflare dashboard → heartbox.tw → DNS → 應該看到一筆 CNAME `llm` → `<UUID>.cfargotunnel.com`，狀態 Proxied（橘雲）。

## 1.6 測試跑起來

```powershell
# 確認 llm_server 在跑（如果你 Stop-Process 過就要重新起）
# 開一個新 PowerShell：
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\llm_server
.\start.bat
# 等 30-60 秒看到 "Application startup complete"

# 開另一個 PowerShell（tunnel 視窗）：
cloudflared tunnel run heartbox-llm
# 等到看到 "Registered tunnel connection" × 4
```

## 1.7 從外網驗證

開**手機 4G 網路**（不要用家裡 wifi，會誤判）：
```
curl https://llm.heartbox.tw/health
# 應該回 {"status":"ok"}
```

或從電腦：
```powershell
curl https://llm.heartbox.tw/health
```

**如果 connection refused / 502**：
- 確認 llm_server 真的在 `127.0.0.1:8765`：`curl http://127.0.0.1:8765/health`
- 確認 cloudflared 還在跑：tunnel 視窗有「Registered tunnel connection」
- 看 cloudflared log 有沒有「error proxying to origin」

**如果 SSL error**：DNS 還沒生效，等 1-2 分鐘 + 重試

## 1.8 變成 Windows service（demo 當天不靠手動）

```powershell
# 系統管理員 PowerShell
cloudflared service install
# 印出 "service installed"
sc.exe config Cloudflared start=auto
sc.exe start Cloudflared
sc.exe query Cloudflared
# 應該看到 STATE: 4 RUNNING
```

**驗證 auto-start**：重開機 → 不要手動啟動任何東西 → 從手機 4G 打 `curl https://llm.heartbox.tw/health` 應該還是 200。

---

# §2. 設 production env 變數

**前提**：你已知道 backend 部署在哪 — Render 還是 Cloud Run（看 `render.yaml` 暗示是 Render）。

## 2A. 如果是 Render

1. 開 https://dashboard.render.com/
2. 進你的 web service（應該叫 `heartbox-api` 之類）
3. 左側 menu **Environment**
4. **Add Environment Variable**（手動加，因為 `render.yaml` 只宣告 key 不填值）：

| Key | Value | 來源 |
|---|---|---|
| `LLM_PROVIDER` | `remote_taide` | 固定 |
| `LLM_SERVER_URL` | `https://llm.heartbox.tw` | §1 設好的 |
| `LLM_SERVER_API_KEY` | （`$env:USERPROFILE\.heartbox-llm.env` 裡的 `API_KEY=` 那串）| 64 hex |
| `CRON_SECRET` | （另外產生一組）| 看下方 |

產生 CRON_SECRET：
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
# 把輸出貼到 Render dashboard
```

5. 按 **Save Changes** → Render 自動 redeploy（2-3 分鐘）
6. 進 **Logs** tab 看 deploy 成功

## 2B. 如果是 Cloud Run

```powershell
# 先 gcloud auth login（會開瀏覽器）
gcloud auth login

# 設專案
gcloud config set project heartbox-app    # 或你的 project id

# 撈現在的 service name
gcloud run services list --region=asia-east1

# 更新 env 變數（一次設完）
$apiKey = (Get-Content "$env:USERPROFILE\.heartbox-llm.env" | Select-String "^API_KEY=" | ForEach-Object { $_.Line.Split("=")[1] })
$cronKey = python -c "import secrets; print(secrets.token_hex(32))"

gcloud run services update heartbox-api `
  --region=asia-east1 `
  --update-env-vars="LLM_PROVIDER=remote_taide,LLM_SERVER_URL=https://llm.heartbox.tw,LLM_SERVER_API_KEY=$apiKey,CRON_SECRET=$cronKey"
```

## 2.1 驗證設定有生效

從前端送一筆日記 → 觀察後端 log：

```powershell
# Render
# 開 dashboard → Logs tab → live tail

# Cloud Run
gcloud run services logs read heartbox-api --region=asia-east1 --limit 50
```

**期待看到**：
```
INFO api.services.llm.factory LLM provider initialised: remote_taide
INFO api.services.llm.remote_provider llm_call provider=remote_taide op=chat ... latency_ms=NNN status=ok
```

**不應該看到**：
```
WARNING LLM provider not configured, returning fallback response
```

---

# §3. Production 重灌 knowledge_base

**為什麼**：本機 `psychology_kb_bgem3` collection 已灌好但**那是本機 ChromaDB**。Cloud Run / Render 的容器是另一份 ChromaDB（如果用 persistent storage 的話），而且容器重啟可能丟失。

## 3.1 Render shell 路徑

1. Dashboard → service → **Shell** tab（如果你有 Standard / Pro plan 才有 shell；Free / Starter 沒有）
2. 在 shell 跑：
```bash
python manage.py load_knowledge_base --reset
```
3. 等 1-2 分鐘看到 `Successfully loaded 104 chunks into ChromaDB collection psychology_kb_bgem3`

## 3.2 Cloud Run jobs 路徑

```powershell
# 建一次性的 Cloud Run Job 跑 load_knowledge_base
gcloud run jobs create load-kb-once `
  --image=gcr.io/heartbox-app/heartbox-api:latest `
  --region=asia-east1 `
  --command="python" `
  --args="manage.py,load_knowledge_base,--reset" `
  --set-env-vars="..." # 跟 service 一樣的 env

gcloud run jobs execute load-kb-once --region=asia-east1 --wait
# 看完成
```

## 3.3 如果 production 沒有 persistent storage

ChromaDB 預設用 local disk，Cloud Run / Render 容器重啟會丟。需要：
- **Render**: 加 persistent disk（付費 plan）掛在 `/data` → 改 `CHROMA_PERSIST_DIR=/data/chroma`
- **Cloud Run**: 用 Cloud Storage FUSE 或改用 ChromaDB 雲端版（Chroma Cloud）

**最簡單的做法（給 demo 用）**：每次容器啟動時自動跑一次 `load_knowledge_base`。在 `backend/build.sh` 結尾加：
```bash
python manage.py load_knowledge_base 2>/dev/null || echo "kb skip"
```

但這會把 build time 加 1-2 分。權衡看你。

---

# §4. Dated rehearsal 流程

**為什麼**：5 分鐘 demo 含 LLaVA swap（~25s）、TAIDE 多輪對話（~3s × N）、現場斷網等變數，沒實際走過一遍永遠不知道哪步爆。

## 4.1 鋪設備

1. 拿 demo 機（可能是場機，不是你家 GPU 機）
2. 開 5 分鐘倒數計時器（手機 / Win 11 內建 Clock app）
3. 截圖工具開好（Win+Shift+S）

## 4.2 跑流程（照 `docs/demo-rehearsal.md`）

```powershell
# 0:00 — 開場 introduce
# 0:30 — 登入 heartbox.tw（demo 帳號）
# 1:00 — 寫日記「今天好累」
# 1:30 — 等 AI 回饋（應該 3-6 秒回）
# 2:00 — 寫負面日記，看 RAG 帶心理學引用
# 2:45 — 附圖 reanalyze（LLaVA 第一次 swap ~25s）
# 3:30 — 切投影片或 docs/system-architecture.md 講架構
# 4:00 — 寫 crisis keyword「我想死」→ 1925 hotline 立刻彈
# 5:00 — 結尾 wrap
```

## 4.3 紀錄表格

打開 `docs/demo-rehearsal.md` → 找到「演練紀錄」表格 → 補一行：

```markdown
| 日期 | 機器 | 總時間 | 卡點 | 修正 |
|---|---|---|---|---|
| 6/23 22:00 | 家機 RTX 3060 Ti | 4:50 | LLaVA swap 28s 超過 25s 預算 | 把 reanalyze 步驟挪到 vision swap warm 之後 |
```

## 4.4 排程建議

| 日期 | 場合 | 目的 |
|---|---|---|
| 6/23 晚（今天）| 自己跑 | 找出最大問題 |
| 6/25 晚 | 自己跑 | 修完問題後重跑 |
| 6/27 晚 | 找朋友當聽眾 | 要求他打斷你問挑釁問題（練 Q&A） |
| 6/29 早 | Final dress rehearsal | stack 跟 demo 機都用最終配置 |
| 6/30 早 | 場勘 | 確認場機網路、HDMI、麥克風、投影 |

---

# §5. 錄 fallback mp4

**為什麼**：場機可能不是 RTX 3060 Ti、現場可能斷網、Cloudflare 可能 regional outage。預錄影片是最後保險。

## 5.1 工具選一個

- **Windows 內建 Game Bar**（最簡單）：Win+G → 「擷取」按鈕 → 紅點開始錄
- **OBS Studio**（推薦，可以多場景切）：https://obsproject.com/ 免費下載
- **ShareX**（輕量）：https://getsharex.com/

## 5.2 5 段要錄

每段 30-60 秒，純展示流程：

| 檔名 | 內容 | 操作步驟 |
|---|---|---|
| `demo-01-login.mp4` | 登入 → 主頁 | 開 heartbox.tw → 輸入 demo 帳號 → 登入成功進主頁 |
| `demo-02-note.mp4` | 新增 mood note + AI 分析 | 點「新增日記」→ 打字「今天工作好累，腰也痠」→ 送出 → 等 AI 分析跳出 sentiment_score / stress_index / 個人化回饋 |
| `demo-03-rag.mp4` | RAG 回饋帶心理學引用 | 寫「我覺得我做什麼都失敗」→ 送出 → AI 回饋會含 WHO / APA 引述 |
| `demo-04-vision.mp4` | 圖片 reanalyze | 新日記附 1 張照片 → 點「reanalyze」→ 等 25s → LLaVA 回應描述圖片 |
| `demo-05-crisis.mp4` | crisis hotline 觸發 | 寫「我想死」→ 立刻彈 1925 安心專線橫幅 + AI 回應同理 + 熱線資訊 |

## 5.3 錄製要點

- **解析度 1920×1080**（評審投影常見）
- **沒聲音也可以**（demo 你會旁白）
- **滑鼠 cursor 顯示**（看清楚你點哪）
- **每段獨立檔**（不要錄成一個大檔，臨時跳要切換）

## 5.4 放對位置

```powershell
$desk = [Environment]::GetFolderPath('Desktop')
mkdir "$desk\heartbox-fallback-videos" -Force
# 把 5 個 mp4 拖進去
# 或：
Copy-Item "C:\path\to\recordings\demo-*.mp4" -Destination "$desk\heartbox-fallback-videos\"
ls "$desk\heartbox-fallback-videos\"
```

**也要存 USB 隨身碟**！場機可能存取不到你的雲端。

---

# §6. demo 當天早上 checklist

```powershell
# 0. 開機後第一件事 — 確認 stack 都活著
nssm status HeartBoxLLM 2>$null
# 應該 SERVICE_RUNNING（如果有做 §7）

sc.exe query Cloudflared
# STATE: 4 RUNNING

curl http://127.0.0.1:8765/health
# {"status":"ok"}

# 1. 從外網（手機開分享 / 4G）測
# 在手機開瀏覽器訪問 https://llm.heartbox.tw/health
# 應該回 {"status":"ok"}

# 2. 訪問 production frontend
# 開 https://heartbox.tw 或 https://your-frontend.cloudflare-pages.dev
# 登入 demo 帳號 → 寫一筆「今天好累」→ 等 5-10 秒應該看到 AI 回饋

# 3. 確認 crisis path
# 寫「我想死」→ 應該立刻看到 1925 hotline 橫幅

# 4. 開 nvidia-smi 看 VRAM
nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total --format=csv
# 溫度 < 70，memory.used 應該 < 6GB（warm 但沒在 generate）

# 5. 確認 fallback mp4 都在
ls "$([Environment]::GetFolderPath('Desktop'))\heartbox-fallback-videos\"
# 看到 demo-01 ~ demo-05.mp4 共 5 個

# 6. demo 機準備
# - 充電線插好
# - 網路連好（場館 wifi 或 4G 分享）
# - 投影 HDMI 試一次
# - 滑鼠 cursor speed 調大方便觀眾看清楚
```

任何一條失敗 → 對應 [§9 Fallback 表](#fallback-表) 找對應動作。

---

# §7. llm_server 自動啟動

**為什麼**：`start.bat` 是手動腳本，process 死掉就掛了。NSSM 包成 Windows service 後 process 自動拉起、開機自動 start、有 log rotation。

## 7.1 裝 NSSM

```powershell
# 系統管理員 PowerShell
winget install --id NSSM.NSSM
# 重開 PowerShell
nssm --help
```

## 7.2 包成 service

```powershell
# 系統管理員 PowerShell
nssm install HeartBoxLLM "$env:USERPROFILE\OneDrive\Desktop\HeartBox\backend\venv\Scripts\python.exe"
# GUI 開起來 → 在 Application 分頁設：

# Path:        C:\Users\alan9\OneDrive\Desktop\HeartBox\backend\venv\Scripts\python.exe
# Startup directory: C:\Users\alan9\OneDrive\Desktop\HeartBox
# Arguments:   -m llm_server --host 127.0.0.1 --port 8765

# I/O 分頁：
# Output (stdout): C:\Users\alan9\heartbox-llm-stdout.log
# Error (stderr):  C:\Users\alan9\heartbox-llm-stderr.log

# Rotation 分頁：
# 勾 Replace existing Output/Error files? (Online)
# Rotate files: ✓
# Rotate while service is running: ✓
# Restrict rotation to files bigger than: 10485760 (10MB)

# 按 Install service

# 設自動啟動 + 啟動
sc.exe config HeartBoxLLM start=auto
nssm start HeartBoxLLM
nssm status HeartBoxLLM
# SERVICE_RUNNING
```

## 7.3 驗證 auto-restart

```powershell
# kill llm_server process
$pid = (Get-WmiObject Win32_Service -Filter "Name='HeartBoxLLM'").ProcessId
Stop-Process -Id $pid -Force
# 等 5 秒
Start-Sleep 5
nssm status HeartBoxLLM
# 應該還是 SERVICE_RUNNING（NSSM 自動拉起）
```

## 7.4 看 log

```powershell
Get-Content "$env:USERPROFILE\heartbox-llm-stderr.log" -Tail 30
Get-Content "$env:USERPROFILE\heartbox-llm-stdout.log" -Tail 30
# 看 TAIDE 載入時間 / 推論延遲
```

---

# §8. GPU 監控

放一個 PowerShell 視窗一直跑，超過閾值就警示。

## 8.1 即時 dashboard

開 PowerShell：
```powershell
while ($true) {
    $smi = nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
    $vals = $smi -split ','
    $temp = [int]$vals[0]
    $used = [int]$vals[1]
    $total = [int]$vals[2]
    $util = [int]$vals[3]
    $pct = [math]::Round(($used / $total) * 100, 0)
    
    Clear-Host
    Write-Host "═══ HeartBox GPU monitor ═══" -ForegroundColor Cyan
    Write-Host ""
    
    if ($temp -gt 85) { 
        Write-Host "🔥🔥 溫度 $temp °C — 立刻暫停推論" -ForegroundColor Red 
    } elseif ($temp -gt 75) {
        Write-Host "⚠ 溫度 $temp °C" -ForegroundColor Yellow
    } else {
        Write-Host "✓ 溫度 $temp °C" -ForegroundColor Green
    }
    
    if ($pct -gt 90) {
        Write-Host "⚠ VRAM $used/$total MB ($pct%)" -ForegroundColor Red
    } else {
        Write-Host "✓ VRAM $used/$total MB ($pct%)" -ForegroundColor Green
    }
    
    Write-Host "GPU 使用率 $util%"
    Write-Host ""
    Write-Host "(Ctrl+C 結束)"
    Start-Sleep 3
}
```

## 8.2 寫成腳本

存成 `$env:USERPROFILE\heartbox-gpu-monitor.ps1`，demo 當天開機後雙擊就跑。

---

# §9. Mock fallback Cloud Run revision

**為什麼**：Cloudflare regional outage / GPU 突然死 / TAIDE OOM 等情境，需要一鍵切流量到 `LLM_PROVIDER=mock`。預先 deploy 一個 mock 版的 revision 待命，緊急時切流量。

## 9.1 預先 deploy

```powershell
# 假設你已 gcloud auth login + set project
# 拿你目前的 image
$currentImage = (gcloud run services describe heartbox-api --region=asia-east1 --format="value(spec.template.spec.containers[0].image)")
Write-Host "Current image: $currentImage"

# Deploy 一個 mock revision（不給流量）
gcloud run deploy heartbox-api `
  --image=$currentImage `
  --region=asia-east1 `
  --set-env-vars="LLM_PROVIDER=mock" `
  --no-traffic `
  --tag=mock-fallback

# 確認
gcloud run revisions list --service=heartbox-api --region=asia-east1
# 應該看到 heartbox-api-mock-fallback-xxxxx revision，traffic=0
```

## 9.2 緊急切過去

```powershell
# 當下 100% 流量切到 mock
gcloud run services update-traffic heartbox-api `
  --region=asia-east1 `
  --to-revisions=heartbox-api-mock-fallback=100

# 驗證
curl https://heartbox-api.onrender.com/api/health
# 仍然 200，但 AI 回固定罐頭文字

# 危機解除後切回主 revision
gcloud run services update-traffic heartbox-api `
  --region=asia-east1 `
  --to-latest
```

---

# §10. API key rotation

**頻率**：建議每季一次（或洩漏疑慮時）。

## 10.1 步驟

```powershell
# 1. 產新 key
$newKey = python -c "import secrets; print(secrets.token_hex(32))"
Write-Host "New key: $newKey"
# 寫到密碼管理器（1Password / Bitwarden / KeePass）

# 2. 更新 llm_server side
$envFile = "$env:USERPROFILE\.heartbox-llm.env"
$content = Get-Content $envFile
$updated = $content -replace "^API_KEY=.*", "API_KEY=$newKey"
[System.IO.File]::WriteAllText($envFile, ($updated -join "`n"), [System.Text.UTF8Encoding]::new($false))

# 3. 重啟 service
nssm restart HeartBoxLLM
Start-Sleep 60
curl http://127.0.0.1:8765/health

# 4. 更新 backend env（Render / Cloud Run）
# 同 §2 的步驟，只是改 LLM_SERVER_API_KEY

# 5. 從 production 驗
# 寫一筆日記，看 AI 回饋有沒有正常出現
```

⚠️ **rotation 期間有 30-60 秒 production AI 會失敗**（backend 拿舊 key 打新 server）。Tier-2 fallback 會接住，但 RAG 回饋會降級。建議離峰時間做。

---

# Fallback 表

demo 當下狀況 → 立刻動作：

| 失敗模式 | 觀察到 | 立刻動作 |
|---|---|---|
| GPU 溫度 > 85 °C | §8 監控視窗紅字 | 切 mock revision（§9.2）+ 告知評審 |
| Cloudflare tunnel 掛 | `curl https://llm.heartbox.tw/health` timeout | 切 mock revision；說「為避免今天網路風險，切到 fallback 模式 — 真實推論影片在 demo-02.mp4」 |
| llm_server process 死 | tunnel 視窗顯示 502 | 系統管理員 PowerShell `nssm restart HeartBoxLLM`；等 60 秒 |
| 場機網路斷 | 前端 loading 永遠轉 | 播 demo-01 ~ demo-05 mp4，連播 5 段（4 分鐘） |
| TAIDE 載不起來 | service stderr.log 顯示 OOM / bnb error | 改 `~/.heartbox-llm.env` 設 `BNB_DISABLE=true` + 重啟 — 改用 fp16 跑（VRAM 用 14GB ≠ 你的 8GB，可能還是炸）；備案是切 `TAIDE_MODEL_ID=yentinglin/Llama-3-Taiwan-8B-Instruct` |
| 評審問「e.n.d i.t a.l.l 抓不到？」 | — | 答 `docs/defense-qa.md` Q13 |
| 評審問 SSRF 怎麼做？ | — | 答 `docs/defense-qa.md` Q14 |
| 評審問 OpenAI 比較 | — | 答 `docs/defense-qa.md` Q1（落差 7.4 vs 8.1 但資料不離境） |
| 評審問斷網怎麼辦？ | — | 答 `docs/defense-qa.md` Q2 + 演示 Tier-2 fallback（前端的「分析以本地關鍵詞為主」banner） |

---

# 最簡 fallback path（極限情況）

**如果你只剩 1 小時 + 什麼都還沒做**：

1. （20 分）只做 §2 — production env 變數設好，至少 backend 跟得上自架 LLM 路由
2. （30 分）只做 §1.1-1.6 — Cloudflare tunnel 跑起來但不變 service（手動開 cloudflared 視窗）
3. （10 分）§3 — production 灌 KB

跳過 §4 rehearsal、§5 mp4、§7 service、§8 monitor、§9 fallback、§10 rotation。

評審當下 risk：高，但至少 demo 跑得起來。

---

# 完成度自評表

跑完每條後勾起來：

```
路線 A — 最小可行：
[ ] §1 Cloudflare Tunnel
[ ] §2 Production env 變數
[ ] §3 Production load_knowledge_base

路線 B — 推薦（加上）：
[ ] §4 至少 2 次 dated rehearsal
[ ] §5 5 段 fallback mp4
[ ] §6 demo 當天早上 checklist 跑過一次

路線 C — 完整（加上）：
[ ] §7 NSSM service
[ ] §8 GPU monitor 跑著
[ ] §9 Mock fallback revision deployed
[ ] §10 API key rotation 演練過
```

---

# 求救路徑

任何一條卡住：

1. 看 `docs/llm-runbook.md` — 有日常維運的詳細說明
2. 看 `docs/PHASE0B-OPERATIONAL-RUNBOOK.md` — 更深的版本（這份的擴充）
3. 看 `docs/defense-qa.md` Q1-Q14 — 評審現場問答稿
4. Google 錯誤訊息 → Stack Overflow

最最最後的後盾：跑 `LLM_PROVIDER=mock`、播 mp4、講為什麼選自架架構的故事。**這個架構講得通**，技術 demo 不順但設計理念站得住 → 評審分數不會差太多。

加油！🚀
