# HeartBox 系統架構

*Last updated: 2026-02-20*

---

## 架構總覽

```
┌─────────────────────────────────────────────────────────┐
│                        用戶端                            │
│                   (瀏覽器 / 手機)                        │
└──────────────┬──────────────────────┬───────────────────┘
               │ HTTPS                │ WebSocket
               ▼                      ▼
┌──────────────────────┐  ┌──────────────────────┐
│   Cloudflare Pages   │  │   Google Cloud Run    │
│   ─────────────────  │  │   ─────────────────   │
│   React 前端 (SPA)   │  │   Django 後端 (ASGI)  │
│   Tailwind CSS       │──▶   DRF REST API       │
│   Recharts 圖表      │  │   Channels WebSocket  │
│   TipTap 編輯器      │  │   Daphne Server       │
└──────────────────────┘  └───┬──────┬──────┬─────┘
                              │      │      │
                    ┌─────────┘      │      └─────────┐
                    ▼                ▼                  ▼
            ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
            │ Neon         │ │ OpenAI API  │ │ ChromaDB     │
            │ PostgreSQL   │ │ ──────────  │ │ ──────────── │
            │ ──────────── │ │ GPT-4o-mini │ │ 向量資料庫    │
            │ 雲端資料庫    │ │ 情緒分析     │ │ RAG 知識庫   │
            │ 加密儲存      │ │ AI 對話     │ │ LangChain    │
            └──────────────┘ └─────────────┘ └──────────────┘
```

---

## 三層架構

1. **前端（展示層）**— React SPA 部署在 Cloudflare CDN，負責 UI 互動與圖表渲染
2. **後端（邏輯層）**— Django API 部署在 Google Cloud Run，處理所有業務邏輯、認證、加密
3. **資料層** — Neon PostgreSQL 存資料、OpenAI 做 AI 分析、ChromaDB 做知識檢索

---

## 資料流

```
用戶寫日記 → 前端送出 → 後端 AES-256 加密存入 DB
                              ↓
                       AI 自動分析情緒 (OpenAI)
                              ↓
                       負面情緒 → RAG 知識庫生成建議 (ChromaDB)
                              ↓
                       結果回傳前端顯示
```

## 即時通訊流

```
用戶 A 發訊息 → WebSocket → Django Channels → WebSocket → 用戶 B 即時收到
```

---

## 關鍵設計決策

| 決策 | 為什麼 |
|------|--------|
| **Fernet 加密日記內容** | 日記是隱私資料，即使 DB 洩露也無法讀取 |
| **AI 三級降級** | OpenAI 掛了 → 本地分析 → 模板回覆，確保永不中斷 |
| **WebSocket + REST 並行** | REST 處理一般 CRUD，WebSocket 處理即時聊天與通知 |
| **Serverless 部署** | Cloud Run 自動擴縮，流量低時不花錢 |
| **JWT Token 版本化** | 改密碼或登出其他裝置時，舊 Token 立刻失效 |

---

## 技術棧

| 層級 | 技術 |
|------|------|
| **前端** | React 19、Tailwind CSS v4、Recharts、TipTap、Axios |
| **後端** | Django 5.2、DRF、SimpleJWT、Channels、Daphne |
| **資料庫** | Neon PostgreSQL（生產）、SQLite（測試） |
| **AI** | OpenAI GPT-4o-mini、LangChain 0.3、ChromaDB 1.0、Jieba |
| **加密** | Fernet（AES-CBC + HMAC-SHA256） |
| **部署** | Cloudflare Pages（前端）、Google Cloud Run（後端） |
| **監控** | Sentry（錯誤追蹤） |
