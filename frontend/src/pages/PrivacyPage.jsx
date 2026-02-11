import { Link } from 'react-router-dom'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          隱私政策 Privacy Policy
        </h1>
        <p className="text-sm opacity-60">最後更新：2025 年 6 月</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">1. 資料收集</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            HeartBox（心事盒）會收集您的帳號資訊（使用者名稱、電子郵件）以及您主動輸入的日記內容。
            我們不會收集您的裝置位置、通訊錄或其他個人資料。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">2. 資料加密</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            所有日記內容均使用 AES-CBC + HMAC-SHA256（Fernet）加密後儲存。
            即使資料庫外洩，第三方也無法讀取您的日記原文。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">3. AI 分析</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            您的日記內容會傳送至 OpenAI API 進行情緒分析與回饋建議。
            OpenAI 不會使用通過 API 提交的資料來訓練其模型。
            AI 分析結果僅供參考，不構成專業醫療或心理諮詢建議。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">4. 第三方服務</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            我們使用以下第三方服務：
          </p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>OpenAI — AI 情緒分析</li>
            <li>Neon PostgreSQL — 資料庫託管</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">5. 用戶權利</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            您有權隨時匯出您的所有資料（JSON 格式），也可以永久刪除您的帳號及所有相關資料。
            這些功能可在「設定」頁面中找到。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">6. Cookie 與本地儲存</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            我們使用 localStorage 儲存驗證令牌（JWT）和用戶偏好設定（主題、語言）。
            不使用第三方追蹤 Cookie。
          </p>
        </section>

        <div className="pt-4 flex gap-4 text-sm">
          <Link to="/terms" className="text-purple-500 hover:text-purple-400">
            服務條款
          </Link>
          <Link to="/login" className="text-purple-500 hover:text-purple-400">
            返回登入
          </Link>
        </div>
      </div>
    </div>
  )
}
