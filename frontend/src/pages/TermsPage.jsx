import { Link } from 'react-router-dom'

export default function TermsPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          服務條款 Terms of Service
        </h1>
        <p className="text-sm opacity-60">最後更新：2025 年 6 月</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">1. 服務說明</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            HeartBox（心事盒）是一款個人心情日記應用程式，提供情緒記錄、AI 情緒分析、
            數據視覺化及諮商師媒合等功能。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">2. AI 免責聲明</h2>
          <p className="text-sm opacity-80 leading-relaxed font-medium text-yellow-500/90">
            本應用程式中的 AI 分析功能僅供參考，不構成任何形式的醫療診斷、心理治療或專業諮詢建議。
            如果您正在經歷嚴重的情緒困擾或心理健康問題，請尋求專業醫療人員的協助。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">3. 使用者義務</h2>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>不得利用本服務進行任何違法活動</li>
            <li>不得嘗試破解、反編譯或干擾本服務的運作</li>
            <li>妥善保管您的帳號密碼</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">4. 資料所有權</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            您保留您所撰寫的所有日記內容的完整所有權。
            我們不會將您的內容用於任何商業用途，也不會與第三方分享（AI 分析除外，詳見隱私政策）。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">5. 帳號終止</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            您可以隨時刪除您的帳號。刪除後，所有相關資料將被永久移除且無法恢復。
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">6. 服務變更</h2>
          <p className="text-sm opacity-80 leading-relaxed">
            我們保留隨時修改本服務或這些條款的權利。重大變更將透過應用程式內通知告知您。
          </p>
        </section>

        <div className="pt-4 flex gap-4 text-sm">
          <Link to="/privacy" className="text-purple-500 hover:text-purple-400">
            隱私政策
          </Link>
          <Link to="/login" className="text-purple-500 hover:text-purple-400">
            返回登入
          </Link>
        </div>
      </div>
    </div>
  )
}
