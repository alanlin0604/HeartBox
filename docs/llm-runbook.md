# HeartBox LLM Operator Runbook

> 場景：你（alan9）一個人營運整套自架 LLM 棧，從家裡 RTX 3060 Ti 8GB 經 Cloudflare Tunnel
> 對外提供推論服務給 GCP Cloud Run 上的 Django 後端。

最後修訂：2026-06-21

---

## 1. 系統拓樸

```
使用者 browser
    │ HTTPS
    ▼
heartbox.tw                       Cloudflare Pages (frontend)
    │ HTTPS
    ▼
heartbox-backend-xxxxx.run.app    GCP Cloud Run (Django + ChromaDB)
    │ HTTPS, X-API-Key
    ▼
llm.heartbox.tw                   Cloudflare Tunnel (公開域名)
    │ tunnel-encrypted
    ▼
127.0.0.1:8765                    家裡 Windows GPU 機 (FastAPI + TAIDE/LLaVA)
```

家裡機器不開 inbound port；Cloudflared daemon outbound-only 連到 Cloudflare edge。

## 2. 模型清單

| Repo                                       | 用途                | 大小   | License        |
| ------------------------------------------ | ------------------- | ------ | -------------- |
| `BAAI/bge-m3`                              | embeddings (Django) | 2.2 GB | MIT            |
| `taide/TAIDE-LX-7B-Chat`                   | chat 預設           | 14 GB  | TAIDE License  |
| `yentinglin/Llama-3-Taiwan-8B-Instruct`    | chat fallback       | 16 GB  | Apache 2.0     |
| `llava-hf/llava-v1.6-mistral-7b-hf`        | vision              | 14 GB  | Apache 2.0     |

下載指令：

```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\backend
.\venv\Scripts\python.exe download_models.py
```

腳本對每個 repo 獨立 try/except，TAIDE GATED 不會阻擋其他三個。

## 3. 啟動順序（demo 日標準操作）

### 3.1 早上 9:00 — 暖機

開兩個 PowerShell 視窗。

**視窗 1（模型 server）**：

```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\llm_server
.\start.bat
```

預期看到：
```
INFO uvicorn.server Started server process [xxxxx]
INFO uvicorn.server Uvicorn running on http://127.0.0.1:8765
INFO llm_server.engine Loading TAIDE chat model ...
INFO llm_server.engine TAIDE loaded in 18.4s
```

**視窗 2（tunnel）**：

```powershell
cloudflared tunnel run heartbox-llm
```

預期看到 `Connection xxx registered with protocol: quic` × 4。

### 3.2 預燒機 smoke test

```powershell
# 健康檢查（無需 key）
curl http://127.0.0.1:8765/health

# 完整 chain 測試（先在自己機器跑，確保都通）
curl -X POST http://127.0.0.1:8765/v1/chat/completions `
     -H "X-API-Key: $env:API_KEY" `
     -H "Content-Type: application/json" `
     -d '{"messages":[{"role":"user","content":"哈囉"}],"max_tokens":50}'
```

應該 5-15 秒內回繁中。延遲 > 30 秒就有問題（看視窗 1 log）。

### 3.3 後端煙霧測試（透過 Cloud Run）

```powershell
# 透過 Cloud Run 呼叫 /api/daily-prompt/ 應該成功
curl https://heartbox-backend-xxxxx.run.app/api/daily-prompt/ `
     -H "Authorization: Bearer <test-token>"
```

## 4. 監控（demo 進行中要看的）

### 4.1 必看儀表板

| 來源                          | 看什麼              | 紅燈值       |
| ----------------------------- | ------------------- | ------------ |
| 視窗 1 stdout                 | 推論延遲、錯誤      | > 30s / 任何 ERROR |
| Cloudflare Zero Trust dashboard| Tunnel 連線數      | < 4          |
| Cloud Run logs (gcloud cli)   | LLM_provider error  | 連續 3 個    |
| GPU temp (HWInfo 或 nvidia-smi) | VRAM / temperature | VRAM > 7.5GB / temp > 80°C |

### 4.2 GPU 即時 check

```powershell
# 每 2 秒刷新 GPU 狀態
nvidia-smi -l 2
```

## 5. 故障排除

### 5.1 「Cloud Run 後端說 LLM 沒回應」

優先順序：

1. **視窗 1 還在嗎？** 看是不是 Python crash 過。重啟 start.bat。
2. **視窗 2 還在嗎？** tunnel 斷會讓所有請求 502。重啟 cloudflared。
3. **GPU 過熱降頻？** nvidia-smi 看 temp。冷卻或暫停 30 秒。
4. **VRAM 滿了？** 視窗 1 log 會看 `CUDA out of memory`。重啟 start.bat，釋放 VRAM。

### 5.2 「TAIDE 回答品質很差 / 亂講話」

兩個選擇：

```powershell
# 切到 Llama-3-Taiwan fallback
notepad %USERPROFILE%\.heartbox-llm.env
# 修改：TAIDE_MODEL_ID=yentinglin/Llama-3-Taiwan-8B-Instruct
# 重啟 start.bat
```

或者 demo 用 mock provider（後端設 `LLM_PROVIDER=mock`），但這違背「真實推論」的論述。

### 5.3 緊急 fallback：切回 OpenAI

**只有所有 local 都失敗才用**。在 Cloud Run console 改 env：

```
LLM_PROVIDER=openai            ← 需要程式碼支援，目前砍掉了
OPENAI_API_KEY=<key>
```

⚠️ **這違背「資料不離境」的核心論述**。如果 demo 時走這條路，必須在現場誠實告知委員。

實務上更建議的緊急 fallback：**讓推論失敗，退到後端的本地關鍵詞層**。後端的 tier-2 fallback 就是為此設計，使用者看到「分析以本地關鍵詞為主」的 banner，至少日記能存、情緒分數能跑、crisis 偵測也照樣工作。

## 6. 定期維護

| 週期    | 動作                                                              |
| ------- | ----------------------------------------------------------------- |
| 每天    | 視窗 1 + 2 還在嗎；GPU temp < 70°C；後端 sentry 沒新 error        |
| 每週    | 看 Cloud Run logs 有沒有 LLM timeout pattern；HF 有沒有新模型版本 |
| 每月    | 重新下載一次 model（拉最新權重 + 確認 HF 還能 auth）              |
| 每季    | Cloudflare tunnel token 輪替；API_KEY 輪替                        |

## 7. 緊急聯絡 & 文件

- llm_server README: `llm_server/README.md`
- 評審 Q&A: `docs/defense-qa.md`
- demo 演練稿: `docs/demo-rehearsal.md`
- 後端 LLM 抽象: `backend/api/services/llm/`
- Crisis guard 規則 + 測試: `backend/api/services/llm/crisis_guard.py` + `backend/api/test_crisis_guard.py`

---

## Appendix A：環境變數總覽

### A.1 家裡 GPU 機（`~/.heartbox-llm.env`）

```
API_KEY=<64 hex chars>
HOST=127.0.0.1
PORT=8765
CORS_ALLOW_ORIGINS=https://heartbox-backend-xxxxx.run.app
HF_HOME=C:\Users\alan9\.cache\huggingface
TAIDE_MODEL_ID=taide/TAIDE-LX-7B-Chat
LLAVA_MODEL_ID=llava-hf/llava-v1.6-mistral-7b-hf
BNB_DISABLE=false
AUTOLOAD_ON_STARTUP=true
LOG_PROMPTS=false
```

### A.2 Cloud Run（Django backend）

```
LLM_PROVIDER=remote_taide
LLM_SERVER_URL=https://llm.heartbox.tw
LLM_SERVER_API_KEY=<same 64 hex chars as家裡的 API_KEY>
LLM_MODEL=taide-lx-7b-chat
LLM_VISION_MODEL=llava-v1.6-mistral-7b
LLM_TIMEOUT_S=30
CHROMA_PERSIST_DIR=/app/chroma_db
CHROMA_COLLECTION_NAME=psychology_kb_bgem3
```

OPENAI_API_KEY 不要設、不要存。Settings.py 已經移除這些變數的讀取。
