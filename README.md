# HeartBox - AI 心情筆記應用

[![CI](https://github.com/alanlin0604/HeartBox/actions/workflows/ci.yml/badge.svg)](https://github.com/alanlin0604/HeartBox/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-A--級-brightgreen.svg)](docs/安全審查報告.md)

**HeartBox** 是一個 AI 驅動的加密心情日記應用，提供情緒追蹤、健康數據整合、AI 心理諮詢等功能，幫助用戶更好地了解和管理自己的心理健康。

## ✨ 核心功能

### 🎯 情緒追蹤與分析
- 📝 加密心情日記（端到端加密）
- 📊 情緒趨勢分析與可視化
- 📅 年度心情日曆（Year in Pixels）
- 🎨 豐富的情緒表達（12+ 情緒類型）

### 🤖 AI 智能助手
- 💬 AI 心理諮詢對話
- 📈 智能情緒分析
- 💡 個性化建議與洞察
- 🧠 基於 GPT-4 的自然語言理解

### 💪 健康數據整合
- ❤️ 心率、HRV 監測
- 🚶 步數、運動數據
- 😴 睡眠質量追蹤
- 📲 支援 iOS HealthKit / Android Health Connect

### 🧘 心理健康工具
- 🫁 呼吸練習（多種模式）
- 📚 心理健康課程
- 📖 專業心理學文章
- 🎯 自我評估量表

### 👥 專業諮詢
- 🩺 線上諮詢師預約
- 💬 即時訊息諮詢
- 📊 諮詢報告查看
- ⭐ 諮詢師評價系統

## 🛠️ 技術棧

### 前端
- **框架**: React 19 + Vite 7
- **樣式**: Tailwind CSS 4
- **動畫**: Framer Motion 12
- **圖表**: Recharts 3
- **富文本**: TipTap 3
- **狀態管理**: React Context API
- **移動端**: Capacitor 8 (iOS + Android)

### 後端
- **框架**: Django 5.2 + Django REST Framework 3.16
- **數據庫**: PostgreSQL (Neon)
- **緩存**: Redis (Upstash)
- **WebSocket**: Django Channels + Daphne
- **認證**: JWT (SimpleJWT)
- **加密**: Fernet (對稱加密)

### AI & 數據
- **LLM**: OpenAI GPT-4o-mini
- **向量數據庫**: ChromaDB
- **AI 框架**: LangChain
- **數據分析**: Pandas, NumPy, SciPy

### 部署
- **前端**: Cloudflare Pages (自動部署)
- **後端**: Google Cloud Run (容器化)
- **儲存**: Google Cloud Storage
- **監控**: Sentry
- **CI/CD**: GitHub Actions

## 🚀 快速開始

### 環境需求
- Node.js 22+ (CI 用 22)
- Python 3.12+
- PostgreSQL 14+
- Redis 5+ (選用，留空則 Channels 走 InMemory)

### 前端開發

```bash
# 1. 安裝依賴
cd frontend
npm install

# 2. 配置環境變數
cp .env.example .env
# 編輯 .env 填入必要的配置

# 3. 啟動開發伺服器
npm run dev

# 4. 開啟瀏覽器
# http://localhost:5173
```

### 後端開發

```bash
# 1. 創建虛擬環境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安裝依賴
pip install -r ../requirements.txt

# 3. 配置環境變數
cp ../.env.example ../.env
# 編輯 .env 填入必要的配置

# 4. 運行遷移
python manage.py migrate

# 5. 創建超級用戶
python manage.py createsuperuser

# 6. 啟動開發伺服器
python manage.py runserver

# 7. 開啟瀏覽器
# http://localhost:8000/admin
```

### 管理指令

```bash
cd backend
# Play Store 審查者用的 demo 帳號（demo / DemoPass2026），含 14 天日記、健康指標、AI 對話
python manage.py seed_demo_account            # 首次建立或補資料
python manage.py seed_demo_account --reset    # 清掉現有 demo 內容後重建

# 其他
python manage.py reset_users --confirm        # 清掉除 root 之外的所有帳號（CASCADE）
python manage.py load_knowledge_base          # 載入 RAG 用的心理學知識庫
python manage.py generate_weekly_report       # 手動觸發週報產生
```

### 移動端開發

```bash
# 1. 構建前端
cd frontend
npm run build:mobile

# 2. 打開 Xcode (iOS)
npx cap open ios

# 3. 打開 Android Studio (Android)
npx cap open android
```

## 📚 文檔

### 系統架構
- [系統架構圖](docs/system-architecture.md)
- [功能模組說明](docs/feature-modules.md)
- [系統組件](docs/system-components.md)

### 開發指南
- [環境設定指南](docs/setup-guide.md)
- [移動裝置 APP 建置](docs/行動裝置APP建置指南.md)
- [Cloudflare Pages 設定](docs/Cloudflare_Pages_詳細導航指南.md)
- [健康數據整合](docs/健康資訊連動快速指南.md)

### 部署與維護
- [部署報告](docs/部署報告-2026-04-18.md)
- [版本備份與還原](docs/版本備份與還原指南.md)
- [資料庫備份策略](docs/資料庫備份策略指南.md)

### 安全與監控
- [安全審查報告](docs/安全審查報告.md)
- [安全修復報告](docs/安全修復報告.md)
- [Sentry 錯誤監控設定](docs/Sentry錯誤監控設定指南.md)

### UI/UX
- [UI/UX 改善報告](docs/UI-UX-改善報告-完整版.md)
- [UI/UX 進階優化](docs/UI-UX-進階優化報告.md)

### 功能規劃
- [付費方案與金流規劃](docs/付費方案與金流規劃.md)
- [訂閱計劃](docs/subscription-plan.md)

## 🔐 安全性

HeartBox 高度重視用戶隱私和數據安全：

- ✅ **端到端加密**: 所有筆記使用 Fernet 加密
- ✅ **JWT 認證**: 訪問令牌 30 分鐘，刷新令牌 7 天
- ✅ **速率限制**: 防止暴力破解和 DDoS
- ✅ **HTTPS 強制**: 生產環境強制使用 HTTPS
- ✅ **HSTS**: 1 年有效期 + 子域名
- ✅ **CSP**: 內容安全策略防止 XSS
- ✅ **依賴項掃描**: 自動化安全漏洞檢測
- ✅ **Sentry 監控**: 實時錯誤追蹤

**安全等級**: A- ([查看完整報告](docs/安全審查報告.md))

## 📊 專案狀態

### 測試覆蓋率
- **前端**: 進行中（目標 60%+）
- **後端**: 部分覆蓋

### 性能指標
- **首次內容繪製 (FCP)**: ~1.2s
- **首次輸入延遲 (FID)**: <100ms
- **累積佈局偏移 (CLS)**: <0.1

### 代碼品質
- **Security Audit**: 0 個漏洞（npm audit）
- **ESLint**: 79 errors / 123 warnings（多數為 react-hooks 規則，不阻塞 ship — 待 dedicated sprint 清）
- **drf_spectacular schema**: 0 errors / 37 warnings（warnings 為 SerializerMethodField 沒寫 return type hint，cosmetic）
- **Vitest**: 78/78 passing
- **Bundle 大小**: ~1.5MB (未壓縮)

## 🤝 貢獻

歡迎貢獻！請查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解詳情。

### 開發流程
1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

### Commit 規範
遵循 [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` 新功能
- `fix:` 錯誤修復
- `docs:` 文檔更新
- `style:` 代碼格式（不影響邏輯）
- `refactor:` 重構
- `test:` 測試相關
- `chore:` 構建/工具相關

## 📝 許可證

本專案採用 MIT 許可證 - 詳見 [LICENSE](LICENSE) 文件。

## 👨‍💻 作者

**Alan Lin** (alan930604@gmail.com)

- GitHub: [@alanlin0604](https://github.com/alanlin0604)

## 🙏 致謝

- [OpenAI](https://openai.com) - GPT-4 API
- [Django](https://www.djangoproject.com/) - 後端框架
- [React](https://react.dev/) - 前端框架
- [Tailwind CSS](https://tailwindcss.com/) - CSS 框架
- [Framer Motion](https://www.framer.com/motion/) - 動畫庫

## 📞 聯繫方式

- **Email**: support@heartbox.tw
- **網站**: https://heartbox.tw
- **GitHub Issues**: [回報問題](https://github.com/alanlin0604/HeartBox/issues)

---

**Built with ❤️ by Claude Code**
