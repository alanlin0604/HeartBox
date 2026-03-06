# 行動裝置 APP 建置指南

HeartBox 使用 Capacitor 將現有的 React Web App 包裝成原生 iOS 和 Android APP，支援 HealthKit 和 Health Connect 健康數據整合。

---

## 架構概覽

```
同一份 React 程式碼 (frontend/src/)
  ├→ Cloudflare Pages（PWA，照舊運作）
  ├→ Capacitor → Android APP → Google Play
  └→ Capacitor → iOS APP → App Store
```

## 前置需求

### Android（本地建置）
- [Android Studio](https://developer.android.com/studio)（含 Android SDK）
- Java 17+
- Google Play Console 帳號（$25 美元，一次性）

### iOS（雲端建置 via GitHub Actions）
- Apple Developer 帳號（$99 美元/年）
- 不需要 macOS — GitHub Actions 的 macOS runner 會處理建置

---

## 本地開發（Android）

```bash
cd frontend

# 建置 Web 並同步到原生專案
npm run build:mobile

# 在 Android Studio 中開啟
npx cap open android

# 或直接執行到模擬器/手機
npx cap run android
```

### 安裝健康數據插件

```bash
cd frontend
npm install capacitor-health-connect   # Android Health Connect
npm install capacitor-apple-health     # iOS HealthKit（CI 建置用）
npx cap sync
```

---

## GitHub Actions 雲端建置

### 設定步驟

1. 到 GitHub repo → Settings → Secrets and variables → Actions
2. 新增以下 Secrets：

#### Android Secrets

| Secret 名稱 | 說明 |
|-------------|------|
| `ANDROID_KEYSTORE_BASE64` | 簽名用的 keystore，用 `base64 -w 0 heartbox.keystore` 產生 |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore 密碼 |
| `ANDROID_KEY_ALIAS` | Key alias 名稱 |
| `ANDROID_KEY_PASSWORD` | Key 密碼 |

產生 Android Keystore：
```bash
keytool -genkeypair -v \
  -keystore heartbox.keystore \
  -keyalg RSA -keysize 2048 \
  -validity 10000 \
  -alias heartbox \
  -storepass YOUR_PASSWORD \
  -keypass YOUR_PASSWORD \
  -dname "CN=HeartBox, O=HeartBox, L=Taipei, C=TW"
```

#### iOS Secrets

| Secret 名稱 | 說明 |
|-------------|------|
| `IOS_P12_BASE64` | Apple 開發者簽名憑證 (.p12)，用 `base64 -w 0 cert.p12` 產生 |
| `IOS_P12_PASSWORD` | .p12 的密碼 |
| `IOS_PROVISION_PROFILE_BASE64` | Provisioning Profile，用 `base64 -w 0 profile.mobileprovision` 產生 |

### 觸發建置

1. 到 GitHub repo → Actions → Mobile Build
2. 點 "Run workflow"
3. 選擇平台（both / android / ios）和建置類型（debug / release）
4. 建置完成後在 Artifacts 下載 APK 或 IPA

---

## 上架流程

### Google Play Store

1. 建置 release APK（或 AAB）
2. 到 [Google Play Console](https://play.google.com/console) 建立應用程式
3. 上傳 APK/AAB
4. 填寫商店資訊、截圖、隱私政策連結
5. 提交審核（通常 1-3 天）

### Apple App Store

1. 建置 release IPA（via GitHub Actions）
2. 使用 [Transporter](https://apps.apple.com/app/transporter/id1450874784) 或 CI 上傳到 App Store Connect
3. 在 [App Store Connect](https://appstoreconnect.apple.com) 填寫資訊
4. 提交審核（通常 1-3 天）

**健康數據注意事項：**
- Apple 審核時需要說明為什麼需要 HealthKit 數據
- 需要在 App Store Connect 勾選 HealthKit 功能
- 隱私政策頁面需加入健康數據的說明

---

## 健康數據同步流程

```
手機健康 APP (Apple Health / Health Connect)
    ↓ 原生 API 讀取
Capacitor 健康插件 (healthKit.js)
    ↓ 標準化數據格式
React App (useHealthSync hook)
    ↓ POST /api/health/sync/
HeartBox Backend
    ├→ 儲存到 HealthMetric / DailySleep 表
    ├→ Dashboard 顯示趨勢圖
    └→ AI 分析納入生理數據
```

### 支援的數據類型

| 數據類型 | iOS (HealthKit) | Android (Health Connect) |
|---------|:---:|:---:|
| 步數 | HKQuantityTypeIdentifierStepCount | Steps |
| 心率 | HKQuantityTypeIdentifierHeartRate | HeartRate |
| 心率變異性 | HKQuantityTypeIdentifierHeartRateVariabilitySDNN | HeartRateVariabilityRmssd |
| 活動卡路里 | HKQuantityTypeIdentifierActiveEnergyBurned | ActiveCaloriesBurned |
| 運動時長 | HKQuantityTypeIdentifierAppleExerciseTime | ExerciseSession |
| 睡眠 | HKCategoryTypeIdentifierSleepAnalysis | SleepSession |

---

## 常用指令

```bash
# 建置 Web + 同步原生
npm run build:mobile

# 同步（不重新建置 Web）
npx cap sync

# 開啟 Android Studio
npx cap open android

# 直接執行到 Android 裝置
npx cap run android

# 檢查 Capacitor 狀態
npx cap doctor
```
