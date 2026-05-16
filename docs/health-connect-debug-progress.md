# Health Connect 連結 — 進行中的 crash 調查

> **更新（2026-05-16）：** 採用「不依賴診斷的直接修復」策略。
> Patch 已永久化（[patches/@capgo+capacitor-health+8.4.5.patch](../frontend/patches/@capgo+capacitor-health+8.4.5.patch)）
> 透過 `patch-package` + `postinstall` hook 自動套用，不再被 `npm install` 覆蓋。
> JS 端加 60s timeout 保險。下次 build Android 即生效。
>
> 狀態：暫停（2026-05-09）。卡在 `Health.requestAuthorization()` native crash，已備好 v7 APK 帶診斷 patch、等使用者執行測試讀取 CATCH alert 訊息確診 root cause。

## 症狀

Galaxy A52 (SM-A5260) 上跑 HeartBox debug build，按設定 → 健康 → 「連結」，app 立刻閃退（process SIGKILL）。

## 已驗證 / 可排除

- ✅ 手機端 Health Connect APK 已安裝（從 Play Store 裝的）
- ✅ AndroidManifest.xml 已加 `<queries>` 宣告 `com.google.android.apps.healthdata`（Android 11+ package visibility 必要）
- ✅ Plugin 在 init 階段 `Health.isAvailable()` 正常回傳 `available: true`
- ❌ Plugin 在 `Health.requestAuthorization()` native call 直接 crash，沒有 stack trace 留下
- ❌ localStorage breadcrumb 在 native crash 前沒 flush 到磁碟（Android WebView storage 是非同步寫入，process 死前資料丟失）
- ❌ adb 在這台 Windows 機器卡死，無法抓 logcat：port 5037 上累積 17 條 TimeWait 殭屍 socket，新連線打不通；Gradle `installDebug` 也卡同一個 adb

## 已做的修改（uncommitted）

| 檔案 | 修改 | 是否要保留 |
|---|---|---|
| `frontend/android/app/src/main/AndroidManifest.xml` | 加 `<queries>` block（Health Connect 可見性宣告） | **保留** — 真實必要修復，跟 crash 無關但對 Android 11+ HC 必要 |
| `frontend/src/services/healthKit.js` | 加 breadcrumb 機制 + `alert()` 探針 | breadcrumb 機制可保留當未來 debug 工具，alert 探針要拿掉 |
| `frontend/src/hooks/useHealthSync.js` | 加 alert 探針到 connect callback | 拿掉 |
| `frontend/src/pages/SettingsPage.jsx` | 加紅色 debug 診斷面板 + 測試按鈕 + alert 探針 | 拿掉，但思考是否做成「正式的診斷頁」隱藏在 debug build |
| `frontend/node_modules/@capgo/capacitor-health/android/.../HealthPlugin.kt` | 把 `requestAuthorization` 的 coroutine body 整段 try/catch，每個 stage 失敗時 reject 帶 `STAGE_xxx:` 訊息 | **node_modules 不入 git**，下次 `npm install` 會被覆蓋。需要 patch-package 或 fork 來持久化 |

## 下一步：使用者要做的測試

1. 拷桌面 `heartbox-debug-v7.apk` 到手機 Download，覆蓋安裝
2. 開 app → 設定 → 健康 → 紅框寫 `DEBUG BUILD v7 — patched plugin try/catch`
3. 按紅色「🧪 TEST connect」
4. alert 序列：A → B → C → PRE-NATIVE → 之前到這裡會閃退，**v7 不會閃退**，會跳一個 CATCH alert
5. CATCH alert 文字像：`CATCH: STAGE_xxx: ExceptionClassName: error message`
6. 把那段文字回報

## 可能的 STAGE 含義

| stage | 意義 | 可能 root cause |
|---|---|---|
| `STAGE_permissionsFor` | 權限對應失敗 | 不太可能 — 純 Kotlin 邏輯 |
| `STAGE_getGrantedPermissions` | 跟 HC IPC 失敗 | HC service 沒就緒 / 版本不相容 / Samsung S Health 衝突 |
| `STAGE_createIntent` | 權限 intent 建立失敗 | 權限字串格式問題 |
| `STAGE_startActivityForResult` | 啟動權限畫面失敗 | Activity context 問題、HC permission UI 缺失 |
| `STAGE_outer` | 其他 | 未知 |

## adb 在這台 Windows 卡死的解法（之後再修）

- 嘗試過：kill adb 處理程序、換 port、phone 端關開 USB 偵錯、撤銷授權重新允許
- 沒試過：重開 phone、重開 Windows、重灌 USB 驅動
- 暫時繞道：MTP 拷 APK 到 Download 手動安裝（雖然慢但 work）

## APK 檔案

| 檔 | 內容 |
|---|---|
| 桌面 `heartbox-debug-v2.apk` | 加 `<queries>` block 的版本（已驗證裝得上） |
| 桌面 `heartbox-debug-v7.apk` | v2 + breadcrumb + alert 探針 + plugin try/catch patch — **接著測這個** |

中間版本（v3-v6）已過時可刪。

## 收尾要做的（等找到 root cause 後）

- [x] **2026-05-09** 把 alert 探針從 healthKit.js / useHealthSync.js / SettingsPage.jsx 拿掉
- [x] **2026-05-09** breadcrumb 機制保留在 hot path（可由 `localStorage.heartbox_health_debug='1'` 重啟診斷面板）
- [x] **2026-05-16** plugin patch 用 [patch-package](https://www.npmjs.com/package/patch-package) 持久化
      → [patches/@capgo+capacitor-health+8.4.5.patch](../frontend/patches/@capgo+capacitor-health+8.4.5.patch)，
      `postinstall` script 自動套用，npm install 不再覆蓋
- [x] **2026-05-16** JS 端 60s timeout 包覆 `requestAuthorization`，避免 bridge 永不 resolve 時 UI hang
- [ ] 寫個測試覆蓋 graceful HC-not-installed UX（之前說要加但沒做）

## 為什麼這算「修復」而非「diagnostic 持久化」

Plugin patch 對每個 stage 加 `var stage = "STAGE_xxx"` 標記後再用外層 `try { ... } catch (t: Throwable) { call.reject("${stage}: ...", ...) }` 接住——這把
**uncaught native exception → silent coroutine death → SIGKILL** 的鏈條打斷
成 **catchable JS rejection**。所以即使我們不知道 root cause stage 是哪個，
app 也不會再閃退；最壞情況是使用者看到「Health Connect 連結失敗」+ 一段
stage tag，按取消後 app 還在。

未來真的要找 root cause，breadcrumb 機制 + Sentry 已能直接讀到
`reqPerms:requestAuthorization-error` 的 STAGE_xxx 訊息，不需要 v7 debug APK 流程。
