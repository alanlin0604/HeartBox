# HeartBox Android 開發與優化清單

## 📋 總覽

本文件包含 HeartBox Android APP 建置的完整待辦清單，分為四大階段：
1. **立即執行** - Android 建置與上架（1-2 週）
2. **中期規劃** - 後端部署與優化（2-4 週）
3. **長期發展** - 功能擴充（1-3 個月）
4. **持續改進** - 品質提升（持續進行）

**總預估時間：** 2-4 個月
**預算：** $25 USD（Google Play 註冊費）

---

## 🚀 第一階段：Android 建置與上架（1-2 週）

### A. 環境準備（1-2 天）

#### 1. 安裝健康資料插件
**預估時間：** 30 分鐘
**優先級：** 🔴 高

```bash
cd frontend
npm install @capgo/capacitor-health
npx cap sync
```

**驗證：**
```bash
grep "capacitor-health" package.json
```

---

#### 2. 配置 AndroidManifest.xml 健康資料權限
**預估時間：** 1 小時
**優先級：** 🔴 高

**檔案位置：** `frontend/android/app/src/main/AndroidManifest.xml`

**需要新增：**
```xml
<!-- Health Connect Permissions -->
<uses-permission android:name="android.permission.health.READ_STEPS" />
<uses-permission android:name="android.permission.health.READ_HEART_RATE" />
<uses-permission android:name="android.permission.health.READ_SLEEP" />
<uses-permission android:name="android.permission.health.READ_ACTIVE_CALORIES_BURNED" />
<uses-permission android:name="android.permission.health.READ_HEART_RATE_VARIABILITY" />

<!-- Health Connect Intent Filter -->
<activity android:name=".MainActivity">
    <intent-filter>
        <action android:name="androidx.health.ACTION_SHOW_PERMISSIONS_RATIONALE" />
    </intent-filter>
</activity>
```

**參考文件：** `docs/健康資訊連動快速指南.md`

---

#### 3. 生成 Android Keystore 簽名檔
**預估時間：** 30 分鐘
**優先級：** 🔴 高

**生成命令：**
```bash
keytool -genkeypair -v \
  -keystore heartbox.keystore \
  -keyalg RSA -keysize 2048 \
  -validity 10000 \
  -alias heartbox \
  -storepass YOUR_SECURE_PASSWORD \
  -keypass YOUR_SECURE_PASSWORD \
  -dname "CN=HeartBox, O=HeartBox, L=Taipei, C=TW"
```

**轉換為 Base64：**
```bash
base64 -w 0 heartbox.keystore > heartbox.keystore.base64
```

**注意：**
- ⚠️ 安全存放 keystore 檔案（不可遺失）
- ⚠️ 記錄密碼（建議使用密碼管理器）
- ⚠️ 備份到安全位置（如加密雲端硬碟）

---

#### 4. 設定 GitHub Actions Secrets
**預估時間：** 20 分鐘
**優先級：** 🔴 高

**前往：** GitHub repo → Settings → Secrets and variables → Actions → New repository secret

**需要新增的 Secrets：**

| Secret 名稱 | 內容 | 取得方式 |
|------------|------|---------|
| `ANDROID_KEYSTORE_BASE64` | Keystore Base64 編碼 | `cat heartbox.keystore.base64` |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore 密碼 | 您設定的密碼 |
| `ANDROID_KEY_ALIAS` | `heartbox` | 固定值 |
| `ANDROID_KEY_PASSWORD` | Key 密碼 | 您設定的密碼 |

---

### B. Google Play 準備（2-3 天）

#### 5. 建立 Google Play Console 帳號並支付 $25 註冊費
**預估時間：** 1 小時
**費用：** $25 USD（一次性）
**優先級：** 🔴 高

**步驟：**
1. 前往 https://play.google.com/console
2. 使用 Google 帳號登入（建議用 alan930604@gmail.com）
3. 支付 $25 USD 註冊費（信用卡或 Google Pay）
4. 完成開發者資料填寫

**所需資訊：**
- 開發者名稱：HeartBox 或您的名字
- 聯絡 Email：alan930604@gmail.com
- 網站（選填）：https://heartbox-frontend.pages.dev
- 地址資訊

---

#### 6. 透過 GitHub Actions 建置 Release APK/AAB
**預估時間：** 2 小時
**優先級：** 🔴 高

**步驟：**
1. 確認 `.github/workflows/mobile-build.yml` 存在
2. 前往 GitHub → Actions → Mobile Build
3. 點擊 "Run workflow"
4. 選擇：
   - Platform: `android`
   - Build type: `release`
5. 等待建置完成（約 10-15 分鐘）
6. 下載 Artifacts：`heartbox-android-release.aab`

**驗證：**
- AAB 檔案大小應該在 10-30 MB
- 可以用 `bundletool` 檢查：
  ```bash
  bundletool validate --bundle=heartbox-android-release.aab
  ```

---

#### 7. 在實體/模擬器測試 Android APP 健康資料功能
**預估時間：** 3-4 小時
**優先級：** 🔴 高

**測試項目：**
- [ ] APP 成功安裝並啟動
- [ ] 健康資料權限請求正常顯示
- [ ] 授權後可讀取步數、心率、睡眠資料
- [ ] 資料成功同步到後端
- [ ] 健康資料頁面正確顯示圖表
- [ ] 離線模式正常運作
- [ ] 推送通知功能正常

**測試環境：**
- Android 模擬器（API 34, Android 14）
- 實體裝置（如果有）

**測試數據：**
- 使用 Health Connect 應用手動輸入測試數據
- 或使用 Google Fit 同步數據

---

#### 8. 準備應用程式圖示、截圖、商店資訊
**預估時間：** 4-6 小時
**優先級：** 🟡 中

**需要準備：**

**1. 應用程式圖示（Icon）**
- 高解析度圖示（512x512 px）
- 圓形圖示變體
- 推薦使用 Figma 或 Canva 設計

**2. 應用程式截圖（每種至少 2 張）**
- 手機截圖（1080x1920 或更高）
- 7 吋平板截圖（選填）
- 10 吋平板截圖（選填）

**建議截圖內容：**
1. 登入/註冊頁面
2. 日記撰寫頁面
3. 情緒統計圖表
4. 健康資料同步頁面
5. AI 對話頁面
6. 個人化儀表板

**3. 商店資訊（繁體中文 + 英文）**

**簡短說明（80 字以內）：**
```
繁中：HeartBox - 您的心理健康日記，結合 AI 對話、情緒追蹤與健康數據分析，守護您的心靈健康。
English: HeartBox - Your mental health journal with AI chat, mood tracking, and health data analysis.
```

**完整說明（4000 字以內）：**
參考 `docs/Google_Play_商店描述.md`（需要建立）

**4. 應用程式分類：**
- 主要分類：健康與健身
- 次要分類：醫療

---

#### 9. 撰寫隱私政策頁面（健康資料使用說明）
**預估時間：** 3-4 小時
**優先級：** 🔴 高

**需要說明：**
- ✅ 收集哪些健康資料（步數、心率、睡眠等）
- ✅ 資料如何使用（情緒分析、健康報告）
- ✅ 資料儲存方式（加密、伺服器位置）
- ✅ 資料分享政策（不會與第三方分享）
- ✅ 用戶權利（刪除帳號、匯出資料）
- ✅ 聯絡方式

**檔案位置：** 建立於 Cloudflare Pages 或 Google Sites
**範例：** https://heartbox-frontend.pages.dev/privacy

**重要：** Google Play 要求有可公開訪問的隱私政策 URL

---

#### 10. 上傳 APK/AAB 到 Google Play Console 內部測試
**預估時間：** 2 小時
**優先級：** 🔴 高

**步驟：**
1. Google Play Console → 建立新應用程式
2. 填寫應用程式詳細資料
3. 前往「測試 → 內部測試」
4. 建立新版本
5. 上傳 AAB 檔案
6. 填寫版本資訊（v1.0.0）
7. 儲存並發布到內部測試

**版本資訊範例：**
```
v1.0.0 - 初始版本

✨ 核心功能
- 情緒日記撰寫與管理
- AI 心理健康對話
- 健康資料整合（步數、心率、睡眠）
- 情緒統計與分析
- 個人化儀表板
- 習慣追蹤器
- 好友系統
- 睡眠分析
```

---

#### 11. 邀請測試者並收集反饋
**預估時間：** 1-2 週
**優先級：** 🟡 中

**測試者數量：** 建議 5-10 位

**測試重點：**
- [ ] 安裝流程順暢
- [ ] 健康資料授權清楚
- [ ] UI/UX 是否友善
- [ ] 有無 bug 或閃退
- [ ] 功能是否符合需求

**收集方式：**
- Google Form 問卷
- 直接訊息回報
- GitHub Issues

---

#### 12. 提交正式審核並上架
**預估時間：** 3-7 天（審核時間）
**優先級：** 🟡 中

**前置檢查：**
- [ ] 內部測試通過，無重大 bug
- [ ] 商店資訊完整
- [ ] 隱私政策已發布
- [ ] 內容分級已完成
- [ ] 目標受眾與內容設定正確

**審核時間：** 通常 1-3 天，最長 7 天

**審核可能被拒原因：**
- 隱私政策不完整
- 健康資料使用未明確說明
- APP 閃退或嚴重 bug
- 內容違反政策

---

## 🔧 第二階段：後端部署與優化（2-4 週）

### C. 解決後端部署問題

#### 13. 解決 Cloud Run "Container import failed" 問題
**預估時間：** 未知（需要 Google Cloud 支援協助）
**優先級：** 🔴 高

**目前狀況：**
- 所有 4月18日後的部署都失敗
- 錯誤訊息：Container import failed
- Docker 映像建置成功，但無法匯入到 Cloud Run

**可能解決方案：**
1. 聯繫 Google Cloud 支援開 ticket
2. 嘗試不同的 Docker base image
3. 檢查是否有配額或權限問題
4. 考慮遷移到其他平台（如 Cloud Run on GKE）

**影響：**
- 前端新功能已部署 ✅
- 後端仍運行舊版本（3月1日），6 個新功能無法使用

---

#### 14. 成功部署包含 6 大新功能的後端版本
**預估時間：** 取決於上一步驟
**優先級：** 🔴 高

**新功能包含：**
1. 習慣追蹤器（8 API + 4 元件）
2. 個人化儀表板（9 API + 6 Widgets）
3. 好友系統（17 API + 9 元件）
4. 睡眠深度分析（4 API + 3 元件）
5. 匿名分享社群（6 API + 1 頁面）
6. 數據匯入（CSV/JSON）

**部署檢查：**
- [ ] Django migrations 成功執行
- [ ] 所有 API 端點正常回應
- [ ] 前端可正常呼叫新 API
- [ ] 資料庫查詢效能正常
- [ ] 錯誤日誌無異常

---

### D. 效能與體驗優化

#### 15. 實作 Android 背景健康資料同步（WorkManager）
**預估時間：** 1 週
**優先級：** 🟡 中

**目標：**
- 每小時自動同步健康資料
- 不消耗過多電量
- 網路連線時才同步

**技術選型：**
```javascript
import { Plugins } from '@capacitor/core';
const { BackgroundTask } = Plugins;
```

**實作步驟：**
1. 設定 Android WorkManager periodic work
2. 實作背景同步邏輯
3. 處理網路連線狀態
4. 優化電量消耗
5. 新增同步狀態通知

---

#### 16. 新增健康資料異常偵測與提醒
**預估時間：** 1-2 週
**優先級：** 🟢 低

**偵測項目：**
- 心率異常（過高/過低）
- 睡眠不足（< 6 小時連續 3 天）
- 活動量不足（步數 < 3000 連續 5 天）
- HRV 顯著下降

**提醒方式：**
- 推送通知
- APP 內橫幅
- 每週健康報告

---

#### 17. 優化前端打包大小
**預估時間：** 3-5 天
**優先級：** 🟢 低

**目前狀況：**
- Lazy loading 已實作 ✅
- Code splitting 已實作 ✅

**進一步優化：**
- Tree-shaking unused code
- 壓縮圖片資源
- 移除未使用的 dependencies
- 優化 Recharts 引入方式

**目標：**
- 初始載入 < 200 KB
- 首次渲染 < 1.5 秒

---

#### 18. 實作離線模式（Service Worker + IndexedDB）
**預估時間：** 2 週
**優先級：** 🟡 中

**功能範圍：**
- 日記離線撰寫（IndexedDB 暫存）
- 網路恢復後自動同步
- 健康資料離線查看
- 快取策略優化

**技術：**
- Workbox
- IndexedDB API
- Background Sync API

---

#### 19. 新增 Sentry 錯誤追蹤和效能監控
**預估時間：** 2-3 天
**優先級：** 🟡 中

**設定項目：**
- 前端錯誤捕捉
- 後端錯誤追蹤
- 效能監控（LCP, FID, CLS）
- Source maps 上傳

**Sentry 專案設定：**
- 免費方案：5K errors/月
- 需要設定 `SENTRY_DSN` 環境變數

---

## 🌟 第三階段：功能擴充（1-3 個月）

### E. iOS 支援

#### 20. 實作 Apple Health 整合（iOS HealthKit）
**預估時間：** 2-3 週
**費用：** $99/年（Apple Developer Program）
**優先級：** 🟢 低

**前置需求：**
- Apple Developer 帳號
- GitHub Actions macOS runner（免費）

**實作內容：**
- HealthKit 權限請求
- 數據讀取與同步
- Info.plist 設定
- 隱私說明文字

**測試：**
- TestFlight 內部測試
- App Store 上架

---

### F. 健康數據擴充

#### 21. 新增運動數據追蹤
**預估時間：** 2 週
**優先級：** 🟢 低

**支援運動類型：**
- 跑步（距離、時間、配速）
- 騎自行車
- 游泳
- 重訓
- 瑜伽

**資料來源：**
- Android: Health Connect workouts API
- iOS: HealthKit workout samples

**UI 設計：**
- 運動記錄列表
- 運動統計圖表
- 個人記錄（PR）

---

#### 22. 實作健康報告匯出（PDF 包含圖表）
**預估時間：** 1-2 週
**優先級：** 🟢 低

**報告內容：**
- 週報/月報/年報
- 情緒趨勢圖表
- 健康數據圖表
- AI 分析建議
- 睡眠品質報告

**技術：**
- 後端：reportlab（已安裝）
- 前端：下載 PDF 功能

---

#### 23. 新增健康數據與情緒的 AI 關聯分析
**預估時間：** 3-4 週
**優先級：** 🟡 中

**分析項目：**
- 睡眠品質對情緒的影響
- 運動量與情緒的相關性
- 心率變異度與壓力指數
- 個人化健康建議

**技術：**
- Python: pandas, scipy（相關性分析）
- OpenAI API（生成建議文字）
- 機器學習模型（預測情緒趨勢）

---

#### 24. 實作健康目標設定與進度追蹤
**預估時間：** 2 週
**優先級：** 🟡 中

**目標類型：**
- 每日步數目標
- 睡眠時數目標
- 運動頻率目標
- 情緒記錄頻率

**功能：**
- 目標設定 UI
- 進度視覺化
- 達成提醒
- 成就徽章系統

---

## 🎨 第四階段：持續改進（持續進行）

### G. 品質提升

#### 25. 優化睡眠分析演算法
**預估時間：** 2-3 週
**優先級：** 🟢 低

**改進項目：**
- 深淺睡、REM 週期分析
- 睡眠效率計算
- 睡眠品質評分
- 失眠風險評估

**參考文獻：**
- Sleep Foundation guidelines
- NIH sleep research data

---

#### 26. 新增更多健康數據視覺化圖表
**預估時間：** 1-2 週
**優先級：** 🟢 低

**圖表類型：**
- 週報表（7 天趨勢）
- 月報表（30 天趨勢）
- 年報表（12 個月對比）
- 相關性散點圖
- 熱力圖（睡眠品質）

**技術：**
- Recharts（已使用）
- 自定義 SVG 圖表

---

#### 27. 實作健康數據隱私控制
**預估時間：** 1 週
**優先級：** 🟡 中

**功能：**
- 選擇性分享健康數據
- 數據匿名化選項
- 數據保留期限設定
- 完整刪除健康記錄

**合規：**
- GDPR
- HIPAA（如果需要）
- 台灣個資法

---

### H. 測試與文檔

#### 28. 建立 Android 健康資料整合的自動化測試
**預估時間：** 1-2 週
**優先級：** 🟢 低

**測試範圍：**
- 權限請求流程
- 數據讀取正確性
- 同步邏輯
- 錯誤處理
- 離線模式

**測試框架：**
- Jest（前端）
- Espresso（Android UI）
- Django Test（後端）

---

#### 29. 撰寫使用者手冊
**預估時間：** 3-5 天
**優先級：** 🟢 低

**內容：**
- 健康資料授權步驟
- 資料解讀說明
- 常見問題 FAQ
- 故障排除指南

**格式：**
- 內建 APP 內說明頁面
- 線上文檔（Notion 或 GitBook）

---

#### 30. 建立開發者文檔
**預估時間：** 1 週
**優先級：** 🟢 低

**內容：**
- 健康 API 使用說明
- 數據模型文檔
- 擴充指南（新增健康指標）
- 部署流程
- 貢獻指南

---

## 📊 優先級與時程規劃

### 立即執行（第 1-2 週）

| 任務 | 預估時間 | 優先級 |
|------|---------|--------|
| 1-4：環境準備 | 2-3 天 | 🔴 高 |
| 5-7：建置與測試 | 2-3 天 | 🔴 高 |
| 8-9：商店資料準備 | 2-3 天 | 🟡 中 |
| 10：內部測試 | 1 天 | 🔴 高 |

**里程碑：** Android APP 可安裝並測試

---

### 短期目標（第 3-4 週）

| 任務 | 預估時間 | 優先級 |
|------|---------|--------|
| 11：測試與反饋 | 1-2 週 | 🟡 中 |
| 12：正式上架 | 3-7 天 | 🟡 中 |
| 13-14：後端部署 | 未知 | 🔴 高 |

**里程碑：** Google Play 正式上架

---

### 中期規劃（第 2-3 個月）

| 任務 | 預估時間 | 優先級 |
|------|---------|--------|
| 15：背景同步 | 1 週 | 🟡 中 |
| 16：異常偵測 | 1-2 週 | 🟢 低 |
| 18：離線模式 | 2 週 | 🟡 中 |
| 23：AI 關聯分析 | 3-4 週 | 🟡 中 |

**里程碑：** 核心優化完成

---

### 長期發展（第 3-6 個月）

| 任務 | 預估時間 | 優先級 |
|------|---------|--------|
| 20：iOS 支援 | 2-3 週 | 🟢 低 |
| 21：運動數據 | 2 週 | 🟢 低 |
| 22：健康報告 | 1-2 週 | 🟢 低 |
| 25-27：品質提升 | 4-6 週 | 🟢 低 |

**里程碑：** 功能完整的健康平台

---

## 💡 建議執行順序

### 階段 1：核心建置（立即開始）
1. ✅ 安裝健康插件
2. ✅ 配置權限
3. ✅ 生成 Keystore
4. ✅ 設定 GitHub Secrets
5. ✅ 建置 APK/AAB
6. ✅ 測試健康功能

### 階段 2：上架準備（第 2 週）
7. ✅ 註冊 Google Play
8. ✅ 準備商店資料
9. ✅ 撰寫隱私政策
10. ✅ 內部測試

### 階段 3：正式發布（第 3-4 週）
11. ✅ 收集測試反饋
12. ✅ 修復 bug
13. ✅ 提交審核
14. ✅ 正式上架

### 階段 4：後端修復（並行進行）
- 聯繫 Google Cloud 支援
- 解決部署問題
- 部署新功能

### 階段 5：優化迭代（持續進行）
- 根據用戶反饋優化
- 新增進階功能
- 效能監控與改進

---

## 📞 需要協助

當您準備好開始時，請告訴我從哪一步開始，我會：

1. **立即執行任務** - 修改程式碼、配置檔案、生成指令
2. **提供詳細指引** - 步驟說明、命令列指令
3. **協助除錯** - 解決建置或測試問題
4. **文檔撰寫** - 隱私政策、使用者手冊

**建議：** 從任務 1 開始，循序漸進完成 Android 建置。

---

**建立日期：** 2026-05-02  
**最後更新：** 2026-05-02  
**版本：** 1.0
