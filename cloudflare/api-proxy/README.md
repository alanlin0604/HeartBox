# api.heartbox.tw 反向代理 Worker

`api.heartbox.tw` 在 Cloudflare DNS 上不是 CNAME，而是一條 **Worker route**，綁到名為
`heartbox-api-proxy` 的 Worker。這支 Worker 把請求轉發到 Cloud Run，並改寫 `Host` header
（Cloud Run 依 Host 決定服務，直接 proxy 過去會拿到 404）。

這份原始碼是從線上部署版本還原的 —— 2026-08 之前 repo 裡沒有留檔，換後端網址時只能反編譯。
**改完請務必同步更新這裡。**

## 什麼時候要改

Cloud Run 服務被重新部署到**不同的 GCP 專案**時。`*.run.app` 網址裡含專案編號，
專案一換網址就變，例如：

- 舊：`heartbox-api-598139488748.asia-east1.run.app`（專案 `heartbox-app`，已刪除）
- 新：`heartbox-api-521869298949.asia-east1.run.app`（專案 `heartbox-tw`）

同一專案內重新部署 revision 不會變網址，不用動這支 Worker。

## 部署方式

改 `worker.js` 裡的 `BACKEND_ORIGIN` / `BACKEND_HOST`，然後上傳：

```bash
# 需要有 Workers Scripts:Edit 權限的 CLOUDFLARE_API_TOKEN
ACC=509d006d6e60ee194730252933253a57

curl -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/$ACC/workers/scripts/heartbox-api-proxy" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -F 'metadata={"main_module":"worker.js","compatibility_date":"2025-04-01"};type=application/json' \
  -F 'worker.js=@worker.js;type=application/javascript+module'
```

邊緣節點傳播約需 30 秒，期間會出現新舊版本混雜（部分請求 200、部分 404），屬正常現象。

驗證：

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://api.heartbox.tw/healthz/   # 200
curl -s -X POST https://api.heartbox.tw/api/auth/login/ \
  -H 'Content-Type: application/json' -H 'Origin: https://heartbox.tw' \
  -d '{"username":"test1","password":"test1"}'                              # 200 + JWT
```

## 注意

刻意不用 `wrangler deploy`：本目錄沒有 `wrangler.jsonc`，避免誤把 `api.heartbox.tw`
的 route 設定覆蓋掉。route 是在 Cloudflare Dashboard 上設定的獨立資源。

前端 `heartbox.tw` 是**另一支** Worker（名稱 `heartbox`），由
[`frontend/wrangler.jsonc`](../../frontend/wrangler.jsonc) 以靜態資產方式部署，與這支無關。
