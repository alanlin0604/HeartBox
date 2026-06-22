# HeartBox LLM Server

Single-process FastAPI inference server. Hosts **TAIDE-LX-7B-Chat** (繁中
chat) and **LLaVA-1.6-Mistral-7B** (vision) on one consumer GPU (RTX 3060 Ti
8GB) via bitsandbytes 4-bit NF4 quantisation. Talks OpenAI-compatible JSON to
the GCP Cloud Run Django backend over a Cloudflare Tunnel.

```
User browser
   │   HTTPS
   ▼
heartbox.tw  (Cloudflare Pages → Cloud Run)
   │   HTTPS, X-API-Key
   ▼
llm.heartbox.tw  (Cloudflare Tunnel)
   │   localhost:8765
   ▼
This server  (Windows, RTX 3060 Ti)
```

Journal data crosses no commercial AI API. Defense talking point: 「使用者
資料不會離開台灣境內基礎設施」.

---

## 1. Prerequisites

* Windows 10/11 with NVIDIA GPU (RTX 3060 Ti tested) and recent driver.
* Python 3.12 in `backend/venv/` with `requirements-llm.txt` installed:
  ```powershell
  cd C:\Users\alan9\OneDrive\Desktop\HeartBox\backend
  .\venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
  .\venv\Scripts\pip install -r requirements-llm.txt
  .\venv\Scripts\pip install pydantic-settings==2.6.1 httpx==0.28.1 pillow==11.0.0
  ```
* HF models cached. Run `python backend/download_models.py` once. Total
  ~46 GB across:
  * `BAAI/bge-m3` (~2 GB, for Django backend not this server)
  * `taide/TAIDE-LX-7B-Chat` (~14 GB) — needs HF License approval
  * `llava-hf/llava-v1.6-mistral-7b-hf` (~14 GB)
  * `yentinglin/Llama-3-Taiwan-8B-Instruct` (~16 GB) — fallback
* `cloudflared` installed and authenticated to your Cloudflare account.

## 2. Configuration

Create `%USERPROFILE%\.heartbox-llm.env`:

```
API_KEY=<64-char random hex; share with Cloud Run env LLM_SERVER_API_KEY>
HOST=127.0.0.1
PORT=8765
CORS_ALLOW_ORIGINS=https://heartbox-backend-xxxxx.run.app
HF_HOME=%USERPROFILE%\.cache\huggingface
AUTOLOAD_ON_STARTUP=true
LOG_PROMPTS=false
```

Generate the API key with `python -c "import secrets; print(secrets.token_hex(32))"`.

## 3. Start

Two windows, both stay open during operation:

**Window 1 — model server**:
```powershell
cd C:\Users\alan9\OneDrive\Desktop\HeartBox\llm_server
.\start.bat
```
First boot loads TAIDE (~15-30s). When you see `Uvicorn running on 127.0.0.1:8765` and `TAIDE loaded`, it's ready.

**Window 2 — Cloudflare tunnel**:
```powershell
cloudflared tunnel run heartbox-llm
```
(One-time tunnel setup: `cloudflared tunnel create heartbox-llm` → `cloudflared tunnel route dns heartbox-llm llm.heartbox.tw` → write the `config.yml` mapping `llm.heartbox.tw` to `http://127.0.0.1:8765`.)

## 4. Smoke test

```powershell
# Health (no auth)
curl http://127.0.0.1:8765/health

# Chat (auth required)
curl -X POST http://127.0.0.1:8765/v1/chat/completions `
     -H "X-API-Key: $env:API_KEY" `
     -H "Content-Type: application/json" `
     -d '{
       "messages": [
         {"role": "system", "content": "你是一位溫暖的心理健康陪伴助手。"},
         {"role": "user", "content": "今天有點累。"}
       ],
       "max_tokens": 200,
       "temperature": 0.7
     }'
```

Expected: a 繁中 supportive reply, latency 5-15s on cold start, ~3-6s warm.

## 5. Endpoints

| Method | Path                       | Auth | Purpose                                         |
| ------ | -------------------------- | ---- | ----------------------------------------------- |
| GET    | `/health`                  | no   | uptime + currently-loaded model                 |
| POST   | `/v1/chat/completions`     | yes  | OpenAI-shaped chat                              |
| POST   | `/v1/chat_json`            | yes  | chat with tolerant JSON parsing of the reply    |
| POST   | `/v1/vision`               | yes  | LLaVA multimodal — text + up to 3 image URLs    |
| POST   | `/v1/switch_model`         | yes  | force-swap to `taide` or `llava`                |

## 6. Known limitations

* **Per-request timeout doesn't cancel HF generate()**. On 504 the orphaned
  worker keeps running until the model finishes the current decode. v2 will
  use `TextIteratorStreamer` with a custom `StoppingCriteria`.
* **Vision swap cost**. First /v1/vision call after server boot pays ~10-20s
  for LLaVA load. Backend HTTP client timeout MUST be ≥120s for vision.
* **Single GPU, no batching.** One request at a time per model. Concurrent
  POSTs serialize through `_swap_lock`.
* **No streaming.** ``stream: true`` is accepted by the schema but ignored.

## 7. Rollback

If TAIDE is hallucinating badly under demo pressure:

1. Edit `~/.heartbox-llm.env`:
   ```
   TAIDE_MODEL_ID=yentinglin/Llama-3-Taiwan-8B-Instruct
   ```
2. Restart `start.bat`.

If the entire local stack is broken on demo day, the safest fallback is
`LLM_PROVIDER=mock` — every endpoint returns deterministic canned text
without sending user data anywhere. The OpenAI escape hatch was removed
in Phase 0b (no `openai` value is accepted by the factory, and the
no-openai CI guard would block any attempt to re-add it). If a cloud
LLM is genuinely required for the demo, add a new provider class behind
its own opt-in env var and disclose the data-residency trade-off to the
committee before flipping it.
