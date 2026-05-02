# 好友系統 API 文件

## 概述

HeartBox 好友系統允許用戶之間建立好友關係、分享日記、互相鼓勵和留言。

## 認證

所有 API 端點都需要 JWT 認證。在請求 Header 中加入：
```
Authorization: Bearer <access_token>
```

---

## 好友管理 APIs

### 1. 取得好友列表

**GET** `/api/friends/`

取得當前用戶的所有好友。

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "user_id": 5,
      "username": "alice",
      "email": "alice@example.com",
      "avatar": "http://example.com/media/avatars/alice.jpg",
      "streak_days": 15,
      "total_entries": 120,
      "friendship_since": "2026-01-15T10:00:00Z"
    }
  ]
}
```

---

### 2. 搜尋用戶

**POST** `/api/friends/search/`

搜尋用戶以發送好友請求。

**Request:**
```json
{
  "query": "alice"
}
```

**Response:**
```json
{
  "users": [
    {
      "id": 5,
      "username": "alice",
      "email": "alice@example.com",
      "avatar": "http://example.com/media/avatars/alice.jpg",
      "bio": "Love journaling!",
      "is_friend": false,
      "has_pending_request": false
    }
  ]
}
```

---

### 3. 發送好友請求

**POST** `/api/friends/requests/`

向另一個用戶發送好友請求。

**Request:**
```json
{
  "to_user_id": 5,
  "message": "想跟你成為好友！"
}
```

**Response:**
```json
{
  "id": 10,
  "from_user_id": 1,
  "from_user_username": "bob",
  "from_user_avatar": null,
  "to_user_id": 5,
  "to_user_username": "alice",
  "status": "pending",
  "message": "想跟你成為好友！",
  "created_at": "2026-04-19T10:00:00Z",
  "updated_at": "2026-04-19T10:00:00Z"
}
```

**Error Responses:**
- `400` - Already friends
- `400` - Request already sent
- `400` - Cannot send to yourself
- `404` - User not found

---

### 4. 收到的好友請求

**GET** `/api/friends/requests/received/`

查看發送給自己的待處理好友請求。

**Response:**
```json
{
  "results": [
    {
      "id": 10,
      "from_user_id": 3,
      "from_user_username": "charlie",
      "from_user_avatar": null,
      "to_user_id": 1,
      "to_user_username": "bob",
      "status": "pending",
      "message": "一起記錄生活吧！",
      "created_at": "2026-04-19T09:00:00Z",
      "updated_at": "2026-04-19T09:00:00Z"
    }
  ]
}
```

---

### 5. 發送的好友請求

**GET** `/api/friends/requests/sent/`

查看自己發送的好友請求。

**Response:** (同上格式)

---

### 6. 接受好友請求

**POST** `/api/friends/requests/{id}/accept/`

接受好友請求並建立雙向好友關係。

**Response:**
```json
{
  "id": 10,
  "from_user_id": 3,
  "from_user_username": "charlie",
  "from_user_avatar": null,
  "to_user_id": 1,
  "to_user_username": "bob",
  "status": "accepted",
  "message": "一起記錄生活吧！",
  "created_at": "2026-04-19T09:00:00Z",
  "updated_at": "2026-04-19T10:05:00Z"
}
```

**Side Effects:**
- 建立雙向 `Friendship` 記錄
- 發送通知給請求發送者

---

### 7. 拒絕好友請求

**POST** `/api/friends/requests/{id}/reject/`

拒絕好友請求。

**Response:** (同上格式，status 為 "rejected")

---

### 8. 解除好友關係

**DELETE** `/api/friends/{friend_id}/`

解除與指定用戶的好友關係。

**Response:**
```json
{
  "message": "Friend removed successfully"
}
```

**Side Effects:**
- 刪除雙向 `Friendship` 記錄
- 刪除所有相關的分享記錄

---

## 日記分享 APIs

### 9. 分享日記給好友

**POST** `/api/friends/share-note/`

將日記分享給一個或多個好友。

**Request:**
```json
{
  "note_id": 10,
  "friend_ids": [5, 7, 9]
}
```

**Response:**
```json
{
  "message": "Note shared with 3 friend(s)",
  "shares_created": 3
}
```

**Validation:**
- 只能分享自己的日記
- 只能分享給已是好友的用戶
- 防止重複分享（使用 unique_together）

---

### 10. 撤銷分享

**DELETE** `/api/friends/share/{share_id}/`

撤銷對特定好友的日記分享。

**Response:**
```json
{
  "message": "Share removed successfully"
}
```

---

### 11. 好友分享給我的日記

**GET** `/api/friends/shared-with-me/`

查看好友分享給我的日記列表。

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "note": 10,
      "shared_by_id": 5,
      "shared_by_username": "alice",
      "shared_by_avatar": "http://example.com/media/avatars/alice.jpg",
      "shared_at": "2026-04-19T10:00:00Z",
      "content_preview": "今天心情很好，完成了很多事...",
      "sentiment_score": 0.8,
      "created_at": "2026-04-19T09:00:00Z",
      "comment_count": 3
    }
  ]
}
```

---

### 12. 我分享的日記

**GET** `/api/friends/shared-by-me/`

查看我分享給好友的日記列表。

**Response:** (同上格式)

---

### 13. 查看分享日記詳情

**GET** `/api/friends/share/{pk}/detail/`

查看分享日記的完整內容（包含完整文字）。

**Response:**
```json
{
  "id": 1,
  "note": 10,
  "shared_by_id": 5,
  "shared_by_username": "alice",
  "shared_by_avatar": "http://example.com/media/avatars/alice.jpg",
  "shared_at": "2026-04-19T10:00:00Z",
  "content_preview": "今天心情很好，完成了很多事...",
  "decrypted_content": "今天心情很好，完成了很多事情。早上去跑步，晚上和朋友聚餐，感覺生活充滿正能量！",
  "sentiment_score": 0.8,
  "created_at": "2026-04-19T09:00:00Z",
  "comment_count": 3,
  "tags": [
    {
      "id": 1,
      "name": "運動",
      "color": "#ff6b6b"
    }
  ]
}
```

**Permission:**
- 只能查看分享給自己的日記或自己分享的日記

---

## 留言 APIs

### 14. 對分享日記留言

**POST** `/api/friends/share/{share_id}/comment/`

對好友分享的日記留言。

**Request:**
```json
{
  "content": "加油！繼續保持！💪"
}
```

**Response:**
```json
{
  "id": 1,
  "commenter_id": 1,
  "commenter_username": "bob",
  "commenter_avatar": null,
  "content": "加油！繼續保持！💪",
  "created_at": "2026-04-19T10:30:00Z"
}
```

**Permission:**
- 只有被分享的好友可以留言

**Side Effects:**
- 發送通知給日記作者

---

### 15. 取得留言列表

**GET** `/api/friends/share/{share_id}/comments/`

取得分享日記的所有留言。

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "commenter_id": 1,
      "commenter_username": "bob",
      "commenter_avatar": null,
      "content": "加油！繼續保持！💪",
      "created_at": "2026-04-19T10:30:00Z"
    }
  ]
}
```

**Permission:**
- 只有分享者和被分享者可以查看留言

---

### 16. 刪除留言

**DELETE** `/api/friends/comment/{comment_id}/`

刪除自己的留言。

**Response:**
```json
{
  "message": "Comment deleted successfully"
}
```

**Permission:**
- 只能刪除自己的留言

---

## 動態 APIs

### 17. 好友動態

**GET** `/api/friends/activity/?hours=24`

取得好友最近的活動（新日記）。

**Query Parameters:**
- `hours` (optional, default: 24): 取得最近 N 小時內的動態

**Response:**
```json
{
  "activities": [
    {
      "friend_id": 5,
      "friend_username": "alice",
      "activity_type": "new_entry",
      "streak_days": 16,
      "timestamp": "2026-04-19T09:00:00Z",
      "note_id": 42
    }
  ]
}
```

---

## 通知類型

好友系統會發送以下類型的通知：

| 類型 | 觸發時機 | 內容 |
|------|---------|------|
| `friend_request` | 收到好友請求 | "{username} 想要加你為好友" |
| `friend_accepted` | 好友請求被接受 | "{username} 接受了你的好友請求" |
| `friend_share` | 好友分享日記 | "{username} 與你分享了一篇日記" |
| `friend_comment` | 好友留言 | "{username} 在你分享的日記上留言了" |

---

## 資料模型關係

```
User
  ├─ friendships (Friendship) → 好友列表
  ├─ sent_requests (FriendRequest) → 發送的請求
  ├─ received_requests (FriendRequest) → 收到的請求
  ├─ notes_shared_with_friends (SharedWithFriend) → 分享的日記
  └─ notes_received_from_friends (SharedWithFriend) → 收到的分享

MoodNote
  └─ friend_shares (SharedWithFriend) → 被分享記錄

SharedWithFriend
  └─ comments (FriendComment) → 留言
```

---

## 最佳實踐

1. **防止重複請求**: `FriendRequest` 的 `unique_together=['from_user', 'to_user']` 確保不會重複發送
2. **雙向關係**: `Friendship` 使用雙向記錄，方便查詢雙方的好友列表
3. **級聯刪除**: 解除好友關係時，自動刪除相關的分享記錄
4. **權限檢查**: 所有操作都會檢查用戶權限（例如：只能分享自己的日記、只能留言在分享給自己的日記上）
5. **通知機制**: 重要操作（請求、接受、分享、留言）都會發送通知

---

## 錯誤處理

所有 API 都遵循統一的錯誤格式：

```json
{
  "error": "錯誤訊息"
}
```

常見 HTTP 狀態碼：
- `200 OK` - 成功
- `201 Created` - 建立成功
- `400 Bad Request` - 請求參數錯誤
- `403 Forbidden` - 無權限
- `404 Not Found` - 資源不存在

---

## 版本

- **API Version**: 1.0
- **Last Updated**: 2026-04-19
