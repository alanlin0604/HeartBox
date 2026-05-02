# HeartBox 自動環境建置腳本
# 執行方式：PowerShell -ExecutionPolicy Bypass -File setup.ps1

Write-Host "🚀 HeartBox 環境建置開始..." -ForegroundColor Green
Write-Host ""

# 檢查工具版本
function Check-Tool {
    param($Name, $Command, $MinVersion)
    Write-Host "檢查 $Name..." -NoNewline
    try {
        $version = & $Command --version 2>&1 | Select-Object -First 1
        Write-Host " ✅ $version" -ForegroundColor Green
        return $true
    } catch {
        Write-Host " ❌ 未安裝" -ForegroundColor Red
        return $false
    }
}

# 1. 檢查必要工具
Write-Host "=== 1️⃣ 檢查必要工具 ===" -ForegroundColor Cyan
$gitOk = Check-Tool "Git" "git" "2.0"
$nodeOk = Check-Tool "Node.js" "node" "20.0"
$pythonOk = Check-Tool "Python" "python" "3.12"
$ghOk = Check-Tool "GitHub CLI" "gh" "2.0"

if (-not ($gitOk -and $nodeOk -and $pythonOk)) {
    Write-Host ""
    Write-Host "❌ 缺少必要工具！請先執行以下命令安裝：" -ForegroundColor Red
    if (-not $gitOk) { Write-Host "  winget install Git.Git" }
    if (-not $nodeOk) { Write-Host "  winget install OpenJS.NodeJS.LTS" }
    if (-not $pythonOk) { Write-Host "  winget install Python.Python.3.12" }
    if (-not $ghOk) { Write-Host "  winget install GitHub.cli" }
    exit 1
}

Write-Host ""

# 2. 設定 Git
Write-Host "=== 2️⃣ 設定 Git ===" -ForegroundColor Cyan
git config --global user.name "alanlin0604"
git config --global user.email "alan930604@gmail.com"
Write-Host "✅ Git 設定完成" -ForegroundColor Green
Write-Host ""

# 3. 安裝前端依賴
Write-Host "=== 3️⃣ 安裝前端依賴 ===" -ForegroundColor Cyan
if (Test-Path "frontend/package.json") {
    Set-Location frontend
    Write-Host "執行 npm install..."
    npm install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 前端依賴安裝完成" -ForegroundColor Green
    } else {
        Write-Host "❌ 前端依賴安裝失敗" -ForegroundColor Red
        Set-Location ..
        exit 1
    }
    Set-Location ..
} else {
    Write-Host "❌ 找不到 frontend/package.json" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 4. 設定後端環境
Write-Host "=== 4️⃣ 設定後端環境 ===" -ForegroundColor Cyan
if (Test-Path "requirements.txt") {
    # venv 放在 backend/，但 requirements.txt 在專案根目錄
    if (-not (Test-Path "backend/venv")) {
        Write-Host "建立 Python 虛擬環境 (backend/venv)..."
        python -m venv backend/venv
    }

    Write-Host "安裝 Python 依賴 (從根目錄 requirements.txt)..."
    & "backend\venv\Scripts\python.exe" -m pip install --upgrade pip
    & "backend\venv\Scripts\python.exe" -m pip install -r requirements.txt

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 後端依賴安裝完成" -ForegroundColor Green
    } else {
        Write-Host "❌ 後端依賴安裝失敗" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ 找不到 requirements.txt（應位於專案根目錄）" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 5. 檢查環境變數檔案
Write-Host "=== 5️⃣ 檢查環境變數 ===" -ForegroundColor Cyan
$envNeeded = $false

# Django 從專案根目錄載入 .env（settings.py: load_dotenv(BASE_DIR.parent / '.env')）
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  需要建立根目錄 .env（後端）" -ForegroundColor Yellow
    $envNeeded = $true
} else {
    Write-Host "✅ 根目錄 .env 已存在" -ForegroundColor Green
}

if (-not (Test-Path "frontend/.env.production")) {
    Write-Host "⚠️  需要建立 frontend/.env.production" -ForegroundColor Yellow
    $envNeeded = $true
} else {
    Write-Host "✅ frontend/.env.production 已存在" -ForegroundColor Green
}

if ($envNeeded) {
    Write-Host ""
    Write-Host "📝 請告訴 Claude：'幫我建立環境變數檔案'" -ForegroundColor Yellow
}
Write-Host ""

# 6. 完成
Write-Host "=== ✅ 環境建置完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  1. 建立環境變數檔案（告訴 Claude：'幫我建立環境變數檔案'）"
Write-Host "  2. 啟動開發環境："
Write-Host "     終端機 1： cd backend; venv\Scripts\activate; python manage.py runserver"
Write-Host "     終端機 2： cd frontend; npm run dev"
Write-Host ""
Write-Host "🎉 準備就緒！" -ForegroundColor Green
