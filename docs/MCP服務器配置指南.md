# MCP 服務器配置指南

## 配置位置

Claude Desktop 配置文件位置：
```
C:\Users\alan9\AppData\Roaming\Claude\claude_desktop_config.json
```

## 推薦的 MCP 服務器

### 1. PostgreSQL MCP

連接到 Neon PostgreSQL 資料庫

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://user:password@host/database"
      ]
    }
  }
}
```

**設定步驟：**
1. 從 Neon 控制台取得連接字串
2. 替換上面的 `postgresql://...` 為實際連接字串
3. 重啟 Claude Desktop

### 2. GitHub MCP

管理 GitHub Issues、PRs、Repositories

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token_here"
      }
    }
  }
}
```

**設定步驟：**
1. 前往 https://github.com/settings/tokens
2. 建立 Personal Access Token (需要 `repo` 權限)
3. 替換 `your_github_token_here`
4. 重啟 Claude Desktop

### 3. Filesystem MCP (已安裝)

訪問本地文件系統（通常已預設安裝）

### 4. Sequential Thinking MCP (已安裝)

鏈式推理工具（通常已預設安裝）

## 完整配置範例

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://neondb_owner:XXXXX@ep-XXX.us-east-2.aws.neon.tech/neondb?sslmode=require"
      ]
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_XXXXXXXXXXXX"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\alan9\\OneDrive\\Desktop\\HeartBox"
      ]
    }
  }
}
```

## 驗證安裝

1. 重啟 Claude Desktop
2. 在對話中輸入 `/mcp` 查看可用的 MCP 服務器
3. 測試連接：
   - PostgreSQL: 請 Claude 查詢資料庫
   - GitHub: 請 Claude 列出你的 repositories
   - Filesystem: 請 Claude 讀取專案文件

## 常見問題

### Q: MCP 服務器無法連接？
- 檢查配置文件 JSON 格式是否正確
- 確認連接字串和 token 正確
- 查看 Claude Desktop 日誌（Help → View Logs）

### Q: PostgreSQL 連接失敗？
- 確認 Neon 資料庫是否啟動
- 檢查 IP 白名單設定
- 驗證連接字串格式

### Q: GitHub Token 無效？
- 確認 token 有 `repo` 權限
- Token 未過期
- 重新生成 token 並更新配置

## 相關資源

- [MCP 官方文檔](https://modelcontextprotocol.io)
- [PostgreSQL MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
