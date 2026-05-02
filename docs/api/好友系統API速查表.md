# 好友系統 API 速查表

## 基礎 URL
```
http://localhost:8000/api/friends/
```

所有請求需要 JWT 認證：
```
Authorization: Bearer <access_token>
```

---

## 好友管理

| 方法 | 端點 | 說明 | 參數 |
|------|------|------|------|
| `GET` | `/api/friends/` | 取得好友列表 | - |
| `POST` | `/api/friends/search/` | 搜尋用戶 | `query` |
| `POST` | `/api/friends/requests/` | 發送好友請求 | `to_user_id`, `message` |
| `GET` | `/api/friends/requests/received/` | 收到的請求 | - |
| `GET` | `/api/friends/requests/sent/` | 發送的請求 | - |
| `POST` | `/api/friends/requests/{id}/accept/` | 接受請求 | - |
| `POST` | `/api/friends/requests/{id}/reject/` | 拒絕請求 | - |
| `DELETE` | `/api/friends/{friend_id}/` | 解除好友 | - |

---

## 日記分享

| 方法 | 端點 | 說明 | 參數 |
|------|------|------|------|
| `POST` | `/api/friends/share-note/` | 分享日記 | `note_id`, `friend_ids[]` |
| `DELETE` | `/api/friends/share/{share_id}/` | 撤銷分享 | - |
| `GET` | `/api/friends/shared-with-me/` | 收到的分享 | - |
| `GET` | `/api/friends/shared-by-me/` | 我的分享 | - |
| `GET` | `/api/friends/share/{pk}/detail/` | 分享詳情 | - |

---

## 留言功能

| 方法 | 端點 | 說明 | 參數 |
|------|------|------|------|
| `POST` | `/api/friends/share/{share_id}/comment/` | 新增留言 | `content` |
| `GET` | `/api/friends/share/{share_id}/comments/` | 取得留言 | - |
| `DELETE` | `/api/friends/comment/{comment_id}/` | 刪除留言 | - |

---

## 動態功能

| 方法 | 端點 | 說明 | 參數 |
|------|------|------|------|
| `GET` | `/api/friends/activity/` | 好友動態 | `hours` (optional) |

---

## 快速範例

### 1. 搜尋用戶
```bash
curl -X POST http://localhost:8000/api/friends/search/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "alice"}'
```

### 2. 發送好友請求
```bash
curl -X POST http://localhost:8000/api/friends/requests/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_user_id": 5, "message": "一起記錄生活吧！"}'
```

### 3. 接受好友請求
```bash
curl -X POST http://localhost:8000/api/friends/requests/10/accept/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 分享日記給多個好友
```bash
curl -X POST http://localhost:8000/api/friends/share-note/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"note_id": 42, "friend_ids": [5, 7, 9]}'
```

### 5. 新增留言
```bash
curl -X POST http://localhost:8000/api/friends/share/1/comment/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "加油！繼續保持！"}'
```

---

## 回應格式

### 成功回應
```json
{
  "id": 1,
  "username": "alice",
  "streak_days": 15,
  ...
}
```

### 列表回應
```json
{
  "results": [
    { "id": 1, ... },
    { "id": 2, ... }
  ]
}
```

### 錯誤回應
```json
{
  "error": "錯誤訊息"
}
```

---

## HTTP 狀態碼

| 狀態碼 | 說明 |
|--------|------|
| `200 OK` | 成功 |
| `201 Created` | 建立成功 |
| `400 Bad Request` | 請求參數錯誤 |
| `403 Forbidden` | 無權限 |
| `404 Not Found` | 資源不存在 |

---

## 通知類型

| 類型 | 說明 |
|------|------|
| `friend_request` | 收到好友請求 |
| `friend_accepted` | 請求被接受 |
| `friend_share` | 好友分享日記 |
| `friend_comment` | 好友留言 |

---

## 重要欄位

### FriendRequest
- `status`: `pending` / `accepted` / `rejected`
- `from_user_id`: 發送者 ID
- `to_user_id`: 接收者 ID

### SharedWithFriend
- `note`: 日記 ID
- `shared_by_id`: 分享者 ID
- `shared_with_id`: 接收者 ID
- `comment_count`: 留言數

### FriendComment
- `share`: 分享記錄 ID
- `commenter_id`: 留言者 ID
- `content`: 留言內容

---

## Django Admin 管理

訪問 `http://localhost:8000/admin/` 可管理：

- `api.Friendship` - 好友關係
- `api.FriendRequest` - 好友請求
- `api.SharedWithFriend` - 分享記錄
- `api.FriendComment` - 留言

---

## 測試指令

```bash
# 檢查系統
python manage.py check

# 建立 Migration
python manage.py makemigrations

# 執行 Migration
python manage.py migrate

# 測試 Models
python manage.py shell < test_friends_en.py
```

---

**完成日期**: 2026-04-19  
**版本**: 1.0
