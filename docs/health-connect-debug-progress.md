# Health Connect 連結 — RESOLVED (2026-05-17, commit 695e010)

> **狀態：✅ 已修復、Galaxy A52 上實機驗證通過**。HC 整合完整 work：
> 連結成功、6 種資料類型同步到 backend、`/api/health/sync/` 收到正確 payload、
> SettingsPage 顯示「上次同步」時間戳更新。

## Root cause（最終確定）

Android APK 內的 `kotlin-stdlib` runtime 版本與 plugin/app bytecode 期待的不
對齊：

- Capacitor 8.0 預設用 **Kotlin 2.2.20** 編譯
- 編出的 bytecode 內呼叫 `kotlin.coroutines.jvm.internal.SpillingKt`
- 但這個 class 是 **Kotlin 2.1.0** 才加入的 internal coroutine state machine 優化
- HeartBox 之前的 build 內 `kotlin-stdlib` 被 transitive 解析到 **1.7.10**
  （由 `androidx.health.connect:connect-client:1.1.0` 帶入），class 不存在
- Plugin coroutine 第一個 `await` 觸發 state machine → call SpillingKt →
  `NoClassDefFoundError` → 部分 Samsung 韌體升級成 SIGKILL

最終 fix：[android/build.gradle](../frontend/android/build.gradle) `allprojects`
區塊內加 `resolutionStrategy.eachDependency` hook，把每個 `kotlin-stdlib*` 強制
override 成 `rootProject.ext.kotlinVersion`（2.2.20）。

## 為什麼花 7 輪修

每一輪揭露下一輪要解的問題：

1. **v1** (515f84a) — 包覆 `requestAuthorization` coroutine。**結果**：不再
   SIGKILL，但點允許後仍崩。揭露：`handlePermissionResult` 同樣未 guard。
2. **v2** (de8d061) — 包覆 `handlePermissionResult` + `checkAuthorization`。
   **結果**：不再崩潰，但顯示「連結失敗」誤報。揭露：plugin 認為 readAuthorized=[]。
3. **v3** (3fe1e76) — 加 500ms retry。**結果**：仍空。揭露：不是 IPC race。
4. **v4** (b5cdcb4) — 5 次 exponential retry + JS data-probe + 自動展開診斷面板
   + 一鍵複製 + CI patch verification。**結果**：仍空，但**診斷面板讓 user 貼出
   `STAGE_callback_getClient: NoClassDefFoundError: SpillingKt`**。揭露：是
   Kotlin runtime class missing，不是 HC 邏輯問題。
5. **v5** (d8bbfcb) — Force kotlin-stdlib **降**到 1.9.25。**完全錯反**：以為
   SpillingKt 是 1.9 加入的。揭露：用 Web research（aws-sdk-kotlin#1654）發現
   SpillingKt 是 2.1+。
6. **v6** (580eee4) — Force **升**到 2.2.20 + 加 CI guard 檢查 final resolved
   stdlib 版本。**結果**：CI 紅燈，guard 報「resolved to 1.7.10」。揭露：force
   宣告**沒生效**。
7. **v7** (695e010) — 改用 `resolutionStrategy.eachDependency` hook +
   explicit `rootProject.ext.kotlinVersion`。**根本原因**：v6 的 force 字串
   `"...:$kotlinVersion"` 在 allprojects scope 內 subproject evaluation
   找不到 binding，Groovy GString interpolation 變成 `"...:" `（空版本）→ Gradle
   silently 忽略無效宣告。eachDependency 每個 dep 解析時都 call hook，無視
   source declaration 強制 override。**結果**：✅ stdlib 正確 resolve 2.2.20、
   SpillingKt 在 APK 內、HC 連結成功、資料同步動起來。

## 留在 codebase 內的「副產品」

每輪做的東西都不是白工：

| Layer | 檔案 | 為何留著 |
|---|---|---|
| Plugin try/catch | [patches/@capgo+capacitor-health+8.4.5.patch](../frontend/patches/@capgo+capacitor-health+8.4.5.patch) | 未來任何新 native exception 都會轉 JS rejection 而不是 SIGKILL |
| 5 次 retry + data-probe | [healthKit.js](../frontend/src/services/healthKit.js) | 真實 IPC race（不同機型）的保險 |
| 自動展開診斷面板 + 一鍵複製 | [SettingsPage.jsx](../frontend/src/pages/SettingsPage.jsx) | 沒這個 user 貼不出 STAGE_，我們現在還在猜 |
| CI dependency-version guard | [.github/workflows/mobile-build.yml](../.github/workflows/mobile-build.yml) | build 階段抓 stdlib < 2.1，不再讓壞 APK 進 user 手機 |

## 給後人的 lessons

1. **看到 `NoClassDefFoundError` 時先 verify class 屬於哪個 artifact、哪個版本
   開始有**，再決定 force up 還是 down。Web search class FQN +「added in」。
2. **Gradle `force` 與 GString interpolation 是地雷**：在 `allprojects {}` 內
   subproject evaluation 看不到 root ext。Always 用 `rootProject.ext.X` 顯式
   reference。最安全直接用 `eachDependency`。
3. **CI verification step > 反覆 build APK 手測**：一個 `:app:dependencies`
   grep 比 5 次 phone 安裝測試節省半天。投資 CI guard 永遠值得。
4. **診斷面板的 ROI 不是 debug 工具，是 user 反饋頻寬**：把「STAGE_」標記轉成
   user 一鍵複製貼回的訊息，把猜謎變成靠證據對話。

## 真相揭曉（從 user 提供的 STAGE_ 診斷）

User 在第 5 輪測試時用我加的「自動展開診斷面板」 + 「複製診斷」按鈕，貼上：

```
03:47:07.078 reqPerms:before-requestAuthorization
03:47:11.537 reqPerms:requestAuthorization-error
   "STAGE_callback_getClient: NoClassDefFoundError:
    Failed resolution of: Lkotlin/coroutines/jvm/internal/SpillingKt;"
```

短短一行 stack 解釋了所有前面 4 輪 patch 為何徒勞 — plugin
`requestAuthorization` 跳出 HC 權限頁是因為 HC 系統 Intent 啟動不需要 coroutine
spilling，但 `handlePermissionResult` 回呼路徑的 `getClientOrReject(call) ?:
return@launch` 就會 trigger coroutine state machine spill 程式碼，class 找不到，
SIGKILL→ JS 看到 reject。 patch v2 用外層 try/catch 把 SIGKILL 變成 catchable
reject 完全 OK，但 actual root cause 是 runtime missing class。

## 為什麼這個 Bug 這麼難找

- `getGrantedPermissions()` 從未真正執行 — error 發生在更早的 `getClientOrReject`
  內。Plugin 永遠回 0 個 granted permission 不是因為 HC 沒授權，而是 plugin coroutine 死了
- HC App 的「應用程式存取權」UI 顯示 5 個 toggle ON 是正確的 — HC service 真的授了
- 我們的 stage tag 一開始放在 `STAGE_callback_authorizationStatus`，沒看到
  `STAGE_callback_getClient` 才是死亡點。Patch v2 增加更細粒度 stage tag 才讓
  user 拿到 actual class name

## 收尾要做的

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
