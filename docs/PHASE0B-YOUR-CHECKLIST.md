# Phase 0b 剩下你要做的事（純專案部署）

**最後修訂**：2026-06-23  
**範圍**：只談 code / infra / 部署。報告、demo 演練、錄影那些**不在這份**。

## 先確認 Claude 已做完什麼（不用再碰）

- ✅ 17 commits 已 push 到 origin/main
- ✅ GitHub Actions 雙綠（CI + no-openai-check）
- ✅ `~/.heartbox-llm.env` 已建（API key 在裡面）
- ✅ TAIDE / LLaVA / bge-m3 / Llama-3-Taiwan 4 個模型已下載
- ✅ 本機 `llm_server` 已驗 boot / chat / SSRF / auth 全通過
- ✅ 本機 ChromaDB `psychology_kb_bgem3` 已灌 104 chunks
- ✅ 全套 164 個 Django tests + 21 個 llm_server tests 全綠
- ✅ booking date-bomb 已修，CI 不再紅

---

## 你剩下要做的（7 件事）

| # | 項目 | 必要性 | 預估時間 | 為什麼非做不可 |
|---|---|---|---|---|
| 1 | **Cloudflare Tunnel** | 🔴 必做 | 30-45 分 | Cloud Run 打不到家裡 GPU，沒這個 production AI 全部走 fallback |
| 2 | **Production env 變數** | 🔴 必做 | 10 分 | `render.yaml` 只宣告 key，dashboard 要實際填值 |
| 3 | **Production 灌 knowledge base** | 🔴 必做 | 5 分 | 新 collection `psychology_kb_bgem3` 是 1024-dim，prod 要重灌 |
| 4 | **NSSM 包 llm_server 成 service** | 🟡 強烈建議 | 15 分 | 沒 auto-restart 一掛就掛 |
| 5 | **GPU monitor 視窗** | 🟡 建議 | 5 分 | 沒監控不知道溫度多高、VRAM 多滿 |
| 6 | **Mock fallback Cloud Run revision** | 🟢 進階 | 20 分 | GPU 死的時候一鍵切罐頭 |
| 7 | **API key rotation 演練** | 🟢 進階 | 10 分 | 每季要做一次，先走過一遍流程 |

**1-3 是必做**，跑完這 3 條 production AI 就活了。**4-5 是強烈建議**，沒做的話 demo 期間 process 死了沒人拉得回來。**6-7 是長期維運**，demo 後做也行。

---

# §1. Cloudflare Tunnel

## 為什麼

Cloud Run backend（asia-east1）要打到家裡 RTX 3060 Ti 跑 TAIDE。家裡路由器不開 inbound port → Cloudflare Tunnel 反向打洞是唯一方式。

## 前置：確認 Cloudflare 有你的 zone

開 https://dash.cloudflare.com → 看 Websites 列表有 `heartbox.tw`（或你打算用的 domain）。沒有的話兩條路：

- **(a) 把 heartbox.tw 加進 Cloudflare**：要去 godaddy / 你的 registrar 改 nameserver 指向 Cloudflare 給的兩個 NS。生效要 1-24 小時。
- **(b) 暫時用 `*.trycloudflare.com`**：cloudflared 給的 throwaway URL，不用設 DNS，但每次 tunnel 重啟 URL 會變 — 不適合 production，但可以先驗 tunnel 機制能用。

底下假設你選 (a) 用自己的 domain。

## 1.1 安裝

```powershell
# 系統管理員 PowerShell
winget install --id Cloudflare.cloudflared
# 重開 PowerShell（PATH 才生效）
cloudflared --version
```

**預期**：印出 `cloudflared version 2024.x.x`

**失敗**：winget 沒裝 → 從 Microsoft Store 裝 App Installer；或直接下載 https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe 丟 `C:\Windows\System32\`

## 1.2 認證

```powershell
cloudflared tunnel login
```

會開瀏覽器 → 登入 Cloudflare → 選 `heartbox.tw` zone → Authorize。回到 PowerShell 看到「You have successfully logged in. ... cert.pem」就 OK。

**驗證**：`Test-Path "$env:USERPROFILE\.cloudflared\cert.pem"` → True

## 1.3 建 tunnel

```powershell
cloudflared tunnel create heartbox-llm
```

**會印**：
```
Tunnel credentials written to C:\Users\alan9\.cloudflared\<UUID>.json
Created tunnel heartbox-llm with id <UUID>
```

## 1.4 設定檔

```powershell
$tunnelId = (cloudflared tunnel list 2>&1 | Select-String "heartbox-llm" | ForEach-Object { ($_.Line -split '\s+')[0] })
Write-Host "Tunnel UUID: $tunnelId"

$config = @"
tunnel: $tunnelId
credentials-file: $env:USERPROFILE\.cloudflared\$tunnelId.json

ingress:
  - hostname: llm.heartbox.tw
    service: http://127.0.0.1:8765
    originRequest:
      connectTimeout: 10s
      tlsTimeout: 10s
  - service: http_status:404
"@
$config | Out-File -FilePath "$env:USERPROFILE\.cloudflared\config.yml" -Encoding utf8 -NoNewline
Get-Content "$env:USERPROFILE\.cloudflared\config.yml"
```

## 1.5 DNS 路由

```powershell
cloudflared tunnel route dns heartbox-llm llm.heartbox.tw
```

**會印**：`Added CNAME llm.heartbox.tw which will route to this tunnel <UUID>.cfargotunnel.com`

**驗證**：開 Cloudflare dashboard → heartbox.tw → DNS → 看到一筆 CNAME `llm` → `<UUID>.cfargotunnel.com`，狀態 Proxied（橘雲）。

## 1.6 測試 — 用 foreground 跑一次

先確認 `llm_server` 在 `127.0.0.1:8765`：
```powershell
curl http://127.0.0.1:8765/health
# 應該 {"status":"ok"}
```

如果沒在跑，先起：
```powershell
# 視窗 A
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\llm_server
.\start.bat
# 等 30-60 秒看到 "Application startup complete"
```

開**另一個** PowerShell 跑 tunnel：
```powershell
# 視窗 B
cloudflared tunnel run heartbox-llm
# 等看到「Registered tunnel connection」× 4 條（4 個 PoP）
```

從外網驗證（**手機 4G** 或從別人電腦）：
```
curl https://llm.heartbox.tw/health
# 應該回 {"status":"ok"}
```

**從家裡 wifi 測會誤判**（會繞回 LAN）。一定要外網。

## 1.7 失敗排除

| 看到 | 原因 | 動作 |
|---|---|---|
| `error="Unable to reach the origin service"` | llm_server 沒跑 | 視窗 A 開沒？`curl http://127.0.0.1:8765/health` 通嗎？ |
| `SSL_ERROR` from external | DNS 還沒生效 | 等 1-2 分鐘 + 重試；或檢查 DNS 那筆 CNAME 是不是 Proxied |
| 外網 timeout | tunnel 視窗沒 4 條 connection | 視窗 B 看 log，可能是防火牆擋 outbound 7844 port |
| `502 Bad Gateway` | tunnel 通但 origin 502 | 看 llm_server 視窗 stderr |

## 1.8（建議）變 Windows service

每次重開機都要手動 `cloudflared tunnel run` 很煩 → 包成 service：

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

# §2. Production env 變數

## 為什麼

`render.yaml` 用 `sync: false` 宣告了 env key name，但**沒填值** — 那是 secrets 不該進 repo。要在 platform dashboard 實際填。

沒填的話 backend 跑起來 `remote_provider.is_configured()` 回 False → 所有 AI 端點 silently 走 tier-2 fallback（本地關鍵字）→ 看起來像 AI 沒在用。

## 2A. Render 路徑

1. 開 https://dashboard.render.com/
2. 進你的 web service（叫 `heartbox-api` 之類）
3. 左 menu 點 **Environment**
4. 點 **Add Environment Variable**，加 4 筆：

| Key | Value |
|---|---|
| `LLM_PROVIDER` | `remote_taide` |
| `LLM_SERVER_URL` | `https://llm.heartbox.tw` |
| `LLM_SERVER_API_KEY` | （`~/.heartbox-llm.env` 裡 `API_KEY=` 那串 64 hex）|
| `CRON_SECRET` | （另外產，見下）|

產 CRON_SECRET：
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

抓 LLM_SERVER_API_KEY：
```powershell
(Get-Content "$env:USERPROFILE\.heartbox-llm.env" | Select-String "^API_KEY=" | ForEach-Object { $_.Line.Split("=")[1] })
```

5. 按 **Save Changes** → Render 自動 redeploy（2-3 分鐘）
6. 進 **Logs** tab 看 deploy 完成

## 2B. Cloud Run 路徑

```powershell
# gcloud auth login（開瀏覽器）
gcloud auth login
gcloud config set project heartbox-app   # 或你的 project id

# 確認 service name
gcloud run services list --region=asia-east1

# 一次更新
$apiKey = (Get-Content "$env:USERPROFILE\.heartbox-llm.env" | Select-String "^API_KEY=" | ForEach-Object { $_.Line.Split("=")[1] })
$cronKey = python -c "import secrets; print(secrets.token_hex(32))"

gcloud run services update heartbox-api `
  --region=asia-east1 `
  --update-env-vars="LLM_PROVIDER=remote_taide,LLM_SERVER_URL=https://llm.heartbox.tw,LLM_SERVER_API_KEY=$apiKey,CRON_SECRET=$cronKey"
```

## 2.1 驗證

從前端送一筆日記（或直接 curl backend），開 logs tab 觀察。

**期待看到**：
```
INFO api.services.llm.factory LLM provider initialised: remote_taide
INFO api.services.llm.remote_provider llm_call provider=remote_taide op=chat ... latency_ms=NNNN status=ok
```

**不該看到**：
```
WARNING LLM provider not configured, returning fallback response
```

**Render**：dashboard 右上角 Logs 直接看 live。  
**Cloud Run**：
```powershell
gcloud run services logs read heartbox-api --region=asia-east1 --limit 30
```

---

# §3. Production 灌 knowledge_base

## 為什麼

本機 `psychology_kb_bgem3` 已灌好但**那是你電腦的 ChromaDB**，跟 production 是兩份。Cloud Run 的容器啟動會空著（或裝舊的 1536-dim OpenAI 向量），RAG retriever 永遠回零結果。

## 3A. Render shell（如果有 Standard+ plan）

1. Dashboard → service → **Shell** tab
2. 跑：
```bash
python manage.py load_knowledge_base --reset
```
3. 等 1-2 分鐘看到 `Successfully loaded 104 chunks into ChromaDB collection psychology_kb_bgem3`

Render Free / Starter plan 沒 shell → 走 3B 或 3C。

## 3B. Cloud Run Jobs（一次性 job）

```powershell
# 撈現在 service 用的 image
$img = (gcloud run services describe heartbox-api --region=asia-east1 --format="value(spec.template.spec.containers[0].image)")
Write-Host "Image: $img"

# 建一次性 job
gcloud run jobs create load-kb-once `
  --image=$img `
  --region=asia-east1 `
  --command="python" `
  --args="manage.py,load_knowledge_base,--reset"

# 把 service 的 env vars 複製過來
# （Cloud Run jobs 跟 service 不共享 env，要自己設）
gcloud run jobs update load-kb-once `
  --region=asia-east1 `
  --update-env-vars="DJANGO_SECRET_KEY=...,DATABASE_URL=...,ENCRYPTION_KEY=..."

# 跑
gcloud run jobs execute load-kb-once --region=asia-east1 --wait
```

## 3C. 包進 build.sh（每次 deploy 自動跑）

如果 production 沒持久 storage（Cloud Run / Render Free），容器重啟會丟 ChromaDB → 改成每次啟動自動灌：

編輯 `backend/build.sh`，最後加：
```bash
python manage.py load_knowledge_base 2>/dev/null || echo "kb load skipped"
```

**注意**：這會把 build time 加 1-2 分。離峰時段 deploy 影響小，但每次推 main 都付這個成本。

## 3.1 驗證

從前端寫一筆**負面**日記（sentiment < -0.4 會觸發 RAG），看 backend log：

```
INFO api.services.ai_engine RAG retrieved 3 docs from psychology_kb_bgem3
```

如果看到 `RAG retriever is None` 或 `0 docs retrieved` → KB 沒灌成功。

---

# §4. NSSM 把 llm_server 包成 Windows service

## 為什麼

`start.bat` 是手動腳本，process 死掉沒人拉。NSSM 包成 service 後：
- 開機自動啟動
- Process die 5 秒內自動重啟
- stdout/stderr 寫檔自動 rotation

沒做這個的話，半夜 Windows Update 重開機 → 隔天 demo 你的 GPU 沒人在跑。

## 4.1 裝 NSSM

```powershell
# 系統管理員 PowerShell
winget install --id NSSM.NSSM
# 重開 PowerShell
nssm --help
```

## 4.2 包成 service

```powershell
# 系統管理員 PowerShell
nssm install HeartBoxLLM
```

會跳 GUI，按以下填：

**Application 分頁**：
- **Path**: `C:\Users\alan9\OneDrive\Desktop\HeartBox\backend\venv\Scripts\python.exe`
- **Startup directory**: `C:\Users\alan9\OneDrive\Desktop\HeartBox`
- **Arguments**: `-m llm_server --host 127.0.0.1 --port 8765`

**Details 分頁**：
- **Display name**: HeartBox LLM Server
- **Description**: TAIDE + LLaVA inference for HeartBox (Phase 0b)
- **Startup type**: Automatic

**I/O 分頁**：
- **Output (stdout)**: `C:\Users\alan9\heartbox-llm-stdout.log`
- **Error (stderr)**: `C:\Users\alan9\heartbox-llm-stderr.log`

**File Rotation 分頁**：
- ✓ Replace existing Output/Error files
- ✓ Rotate files
- ✓ Rotate while service is running
- **Restrict rotation to files bigger than**: `10485760` (10 MB)

按 **Install service**。

## 4.3 啟動 + 設 auto-start

```powershell
nssm start HeartBoxLLM
nssm status HeartBoxLLM
# 應該回 SERVICE_RUNNING

# 確認 auto-start
sc.exe config HeartBoxLLM start=auto
```

等 30-60 秒讓 TAIDE 載入：
```powershell
curl http://127.0.0.1:8765/health
# {"status":"ok"}
```

## 4.4 驗證 auto-restart

```powershell
# 找 service 拉起的 python pid
$pid = (Get-WmiObject Win32_Service -Filter "Name='HeartBoxLLM'").ProcessId
Write-Host "Current PID: $pid"

# 殺掉
Stop-Process -Id $pid -Force

# 等 5 秒
Start-Sleep 5

# 看狀態
nssm status HeartBoxLLM
# 應該還是 SERVICE_RUNNING（NSSM 已重新拉起）

# 新 PID 跟舊的不一樣
$newPid = (Get-WmiObject Win32_Service -Filter "Name='HeartBoxLLM'").ProcessId
Write-Host "New PID: $newPid (was $pid)"
```

## 4.5 看 log

```powershell
Get-Content "$env:USERPROFILE\heartbox-llm-stderr.log" -Tail 40
# 看 TAIDE 載入時間、推論延遲、有沒有 error
```

## 4.6 之前手動跑的要殺掉

如果你按 §1.6 手動起過 `start.bat`，那個 process 還在跑會跟 service 搶 port：

```powershell
# 找所有 python process
Get-Process python -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, StartTime, CPU

# 殺掉 service 之外的（小心別殺到 service 那個）
$svcPid = (Get-WmiObject Win32_Service -Filter "Name='HeartBoxLLM'").ProcessId
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $svcPid } | Stop-Process -Force
```

---

# §5. GPU monitor 視窗

## 為什麼

`nvidia-smi` 印出來的數字看不出趨勢。包成 colored loop 一眼看出溫度 / VRAM 異常。GPU 是單點故障，沒監控 = 沒事故反應時間。

## 5.1 寫成腳本

存成 `$env:USERPROFILE\heartbox-gpu-monitor.ps1`：

```powershell
$script = @'
while ($true) {
    $smi = nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
    $vals = $smi -split ','
    $temp = [int]$vals[0]
    $used = [int]$vals[1]
    $total = [int]$vals[2]
    $util = [int]$vals[3]
    $pct = [math]::Round(($used / $total) * 100, 0)

    Clear-Host
    Write-Host "═══ HeartBox GPU monitor ($(Get-Date -Format 'HH:mm:ss')) ═══" -ForegroundColor Cyan
    Write-Host ""

    if ($temp -gt 85) {
        Write-Host "🔥 溫度 $temp °C — 危險區，考慮暫停推論" -ForegroundColor Red
    } elseif ($temp -gt 75) {
        Write-Host "⚠ 溫度 $temp °C — 偏高" -ForegroundColor Yellow
    } else {
        Write-Host "✓ 溫度 $temp °C" -ForegroundColor Green
    }

    if ($pct -gt 90) {
        Write-Host "⚠ VRAM $used/$total MB ($pct%) — 接近爆掉" -ForegroundColor Red
    } elseif ($pct -gt 70) {
        Write-Host "  VRAM $used/$total MB ($pct%)" -ForegroundColor Yellow
    } else {
        Write-Host "✓ VRAM $used/$total MB ($pct%)" -ForegroundColor Green
    }

    Write-Host "  GPU 使用率 $util%"
    Write-Host ""
    Write-Host "(Ctrl+C 結束)" -ForegroundColor Gray
    Start-Sleep 3
}
'@
$script | Out-File -FilePath "$env:USERPROFILE\heartbox-gpu-monitor.ps1" -Encoding utf8
```

## 5.2 跑

```powershell
& "$env:USERPROFILE\heartbox-gpu-monitor.ps1"
```

或建捷徑放桌面：
```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$([Environment]::GetFolderPath('Desktop'))\GPU Monitor.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -File `"$env:USERPROFILE\heartbox-gpu-monitor.ps1`""
$Shortcut.Save()
```

桌面就有一個 GPU Monitor 捷徑，雙擊跑。

## 5.3 警戒線

- **溫度 > 85 °C**：危險，遊戲常溫頂多到 80。持續超過考慮停止推論或加風扇。
- **VRAM > 90%**：可能 OOM 邊緣。TAIDE warm + 一次推論大約用 5-6 GB；如果常駐 7+ GB 表示有 leak 或同時跑多個 model（不該發生）。

---

# §6. Mock fallback Cloud Run revision

## 為什麼

GPU 突然死 / Cloudflare regional outage / TAIDE OOM → 全部 AI 端點 500。預先 deploy 一個 `LLM_PROVIDER=mock` revision 待命（流量 0），緊急時一鍵切流量。

切過去後 AI 端點還能回（罐頭回應），至少 frontend 不會看到 500。

## 6.1 預先 deploy

```powershell
# 先 gcloud auth login 完
$currentImage = (gcloud run services describe heartbox-api --region=asia-east1 --format="value(spec.template.spec.containers[0].image)")
Write-Host "Current image: $currentImage"

# Deploy 一個 mock revision，no-traffic
gcloud run deploy heartbox-api `
  --image=$currentImage `
  --region=asia-east1 `
  --set-env-vars="LLM_PROVIDER=mock" `
  --no-traffic `
  --tag=mock-fallback

# 確認
gcloud run revisions list --service=heartbox-api --region=asia-east1 --limit 5
# 應該看到 ... heartbox-api-mock-fallback-xxxxx ... traffic=0%
```

Render 沒這種 revision-tag + traffic-split 機制 → 改用 git branch（`mock-fallback` branch，要切時 push 到該 branch 觸發 deploy）。

## 6.2 緊急切過去

```powershell
# 100% 流量切到 mock
gcloud run services update-traffic heartbox-api `
  --region=asia-east1 `
  --to-revisions=heartbox-api-mock-fallback=100

# 驗證
curl https://heartbox-api.onrender.com/api/health    # 還是 200
# 寫一筆日記，AI 回的會是固定罐頭字
```

## 6.3 危機解除後切回

```powershell
gcloud run services update-traffic heartbox-api `
  --region=asia-east1 `
  --to-latest
```

---

# §7. API key rotation

## 為什麼

季度輪替是基本資安。萬一 key 洩漏（誤 commit、log file 漏記）也要立刻能換。

## 7.1 步驟

```powershell
# 1. 產新 key
$newKey = python -c "import secrets; print(secrets.token_hex(32))"
Write-Host "New key: $newKey"
# 立刻記到密碼管理器（1Password / Bitwarden / KeePass / 紙）

# 2. 更新 llm_server 的 env
$envFile = "$env:USERPROFILE\.heartbox-llm.env"
$content = Get-Content $envFile
$updated = $content -replace "^API_KEY=.*", "API_KEY=$newKey"
[System.IO.File]::WriteAllText($envFile, ($updated -join "`n"), [System.Text.UTF8Encoding]::new($false))

# 3. 重啟 service
nssm restart HeartBoxLLM
# 等 60 秒讓 TAIDE 重新載入
Start-Sleep 60
curl http://127.0.0.1:8765/health

# 4. 更新 backend 的 LLM_SERVER_API_KEY（Render dashboard 或 gcloud）
# Render: dashboard → Environment → 找 LLM_SERVER_API_KEY → 換值 → Save
# Cloud Run:
gcloud run services update heartbox-api `
  --region=asia-east1 `
  --update-env-vars="LLM_SERVER_API_KEY=$newKey"

# 5. 驗
# 從 production 前端寫一筆日記，看 backend log 有沒有 "status=ok"
```

## 7.2 注意

⚠️ **rotation 期間有 30-60 秒 production AI 會回 401**（backend 拿舊 key 打新 server 之間的時間差）。Tier-2 fallback 會接住，但 RAG 回饋會降級。建議**離峰時段做**。

## 7.3 更安全的做法（未來）

把 key 放 Google Secret Manager / AWS Secrets Manager / Vault：
- Cloud Run 用 `--set-secrets` 注入而不是 `--set-env-vars`
- llm_server 啟動時從 secret store 拉
- rotation 變成「換 secret store 那一條 + 兩邊重啟」

現在 MVP 階段直接環境變數可以接受。

---

## 完成度自評

```
🔴 必做：
[ ] §1 Cloudflare Tunnel 跑得起來 + DNS 接通 + 外網 curl 通
[ ] §1.8 cloudflared 變 Windows service
[ ] §2 Production env 變數 4 個都填好
[ ] §2.1 backend log 看到 llm_call provider=remote_taide status=ok
[ ] §3 Production load_knowledge_base 灌完 104 chunks
[ ] §3.1 寫負面日記能看到 RAG 引用

🟡 強烈建議：
[ ] §4 NSSM 包 llm_server，nssm status SERVICE_RUNNING
[ ] §4.4 kill -9 後 5 秒內自動拉起
[ ] §5 GPU monitor 桌面捷徑會跑

🟢 進階：
[ ] §6 Mock fallback revision deployed（traffic=0）
[ ] §6.2 演練過一次切流量 + 切回
[ ] §7 API key rotation 演練過一次
```

---

## 卡住怎麼辦

1. `docs/llm-runbook.md` — 日常維運細節（這份的姊妹篇）
2. `docs/PHASE0B-OPERATIONAL-RUNBOOK.md` — 更深、含 demo 端
3. Google 錯誤訊息 → Stack Overflow
4. 把 stderr.log 完整貼回來問我

---

## 一行總結

**做完 §1 + §2 + §3 → production AI 就活了**。§4-§7 是讓系統穩定 + 安全的加值，6/30 前能多做就多做。
