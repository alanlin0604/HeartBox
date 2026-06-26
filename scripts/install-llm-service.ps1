# Install llm_server as a Windows service via NSSM so it auto-starts on boot,
# auto-restarts on crash, and stays alive across Windows Update reboots.
#
# WHY:
#   llm_server is started manually with `python -m llm_server`. If the
#   machine reboots (Windows Update, power blip, manual restart), the
#   process is gone and llm.heartbox.tw returns 502 until the operator
#   notices and re-runs start.bat. With NSSM the service comes up at
#   boot in ~50-60s (TAIDE model load) without any human action.
#
# WHAT THIS SCRIPT DOES:
#   1. Verifies admin (NSSM service install requires it).
#   2. Verifies prereqs (~/.heartbox-llm.env exists, venv exists, nssm.exe
#      available — auto-installs via choco if not).
#   3. Stops + removes any existing HeartBoxLLM service (idempotent).
#   4. Registers HeartBoxLLM with the venv python and -m llm_server.
#   5. Sets HF_HOME so the TAIDE / LLaVA model cache is found.
#   6. Configures auto-restart: 5s delay, infinite retries.
#   7. Configures rotating log files at %LOCALAPPDATA%\HeartBoxLLM\logs\.
#   8. Sets Start=SERVICE_AUTO_START (boots at system start, before login).
#   9. Starts the service.
#  10. Polls /health for up to 120s and reports status.
#
# USAGE:
#   .\scripts\install-llm-service.ps1                 # default install
#   .\scripts\install-llm-service.ps1 -Uninstall      # remove the service
#   .\scripts\install-llm-service.ps1 -Force          # skip prompts
#
# AFTER INSTALL:
#   nssm start  HeartBoxLLM
#   nssm stop   HeartBoxLLM
#   nssm restart HeartBoxLLM
#   nssm status HeartBoxLLM
#   Get-Content $env:LOCALAPPDATA\HeartBoxLLM\logs\stdout.log -Tail 50
#   .\scripts\rotate-llm-key.ps1   # rotation also triggers nssm restart
#
# EXIT CODES:
#   0  → service installed (or uninstalled) + /health responding
#   1  → prereq missing (env file, venv, etc.)
#   2  → admin required
#   3  → service started but /health timed out (model load issue)

param(
    [switch]$Uninstall,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$SERVICE_NAME = 'HeartBoxLLM'
$LOG_DIR = "$env:LOCALAPPDATA\HeartBoxLLM\logs"
$ENV_FILE = "$env:USERPROFILE\.heartbox-llm.env"
$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$VENV_PY = Join-Path $REPO_ROOT 'backend\venv\Scripts\python.exe'
$HEALTH_URL = 'http://127.0.0.1:8765/health'

function Confirm($msg) {
    if ($Force) { return $true }
    $r = Read-Host ("{0} [y/N]" -f $msg)
    return $r -eq 'y' -or $r -eq 'Y'
}

function Require-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $admin = [System.Security.Principal.WindowsPrincipal]::new($id).IsInRole(
        [System.Security.Principal.WindowsBuiltinRole]::Administrator
    )
    if (-not $admin) {
        Write-Host "✗ This script must be run from an elevated PowerShell (Run as Administrator)." -ForegroundColor Red
        Write-Host "  Right-click PowerShell → Run as administrator, then re-run the script." -ForegroundColor Yellow
        exit 2
    }
}

function Find-Nssm {
    # Prefer PATH lookup; fall back to chocolatey + common install paths.
    foreach ($candidate in @(
        'nssm.exe',
        'C:\ProgramData\chocolatey\bin\nssm.exe',
        'C:\Tools\nssm\win64\nssm.exe',
        "${env:ProgramFiles}\nssm\win64\nssm.exe"
    )) {
        $found = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($found) { return $found.Source }
    }
    return $null
}

function Install-Nssm {
    Write-Host "→ nssm.exe not found on PATH." -ForegroundColor Yellow
    # Try chocolatey if installed
    $choco = Get-Command choco.exe -ErrorAction SilentlyContinue
    if ($choco) {
        if (Confirm "Install NSSM via Chocolatey (choco install nssm -y)?") {
            & choco install nssm -y --no-progress | Out-Host
            $found = Find-Nssm
            if ($found) { return $found }
        }
    }
    # Manual download fallback
    if (Confirm "Download NSSM 2.24 directly to C:\Tools\nssm\?") {
        $tmp = "$env:TEMP\nssm-2.24.zip"
        Write-Host "  downloading nssm-2.24.zip ..." -ForegroundColor DarkGray
        Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $tmp -UseBasicParsing
        Expand-Archive -Path $tmp -DestinationPath 'C:\Tools\' -Force
        Remove-Item $tmp
        $exe = 'C:\Tools\nssm-2.24\win64\nssm.exe'
        if (Test-Path $exe) {
            # Mirror to C:\Tools\nssm\ for stable path
            New-Item -ItemType Directory -Force -Path 'C:\Tools\nssm\win64' | Out-Null
            Copy-Item $exe 'C:\Tools\nssm\win64\nssm.exe' -Force
            Write-Host "  ✓ Installed to C:\Tools\nssm\win64\nssm.exe" -ForegroundColor Green
            Write-Host "    Add C:\Tools\nssm\win64\ to PATH for future convenience." -ForegroundColor Yellow
            return 'C:\Tools\nssm\win64\nssm.exe'
        }
    }
    Write-Host "✗ NSSM install aborted. Install manually from https://nssm.cc/ and re-run." -ForegroundColor Red
    exit 1
}

function Service-Exists($name) {
    return $null -ne (Get-Service -Name $name -ErrorAction SilentlyContinue)
}

# ----------------------------------------------------------------------
# UNINSTALL path
# ----------------------------------------------------------------------
if ($Uninstall) {
    Require-Admin
    $nssm = Find-Nssm
    if (-not $nssm) {
        Write-Host "✗ nssm.exe not found — cannot uninstall via NSSM. If the service exists, remove it manually:" -ForegroundColor Red
        Write-Host "    sc.exe stop $SERVICE_NAME"
        Write-Host "    sc.exe delete $SERVICE_NAME"
        exit 1
    }
    if (-not (Service-Exists $SERVICE_NAME)) {
        Write-Host "→ Service $SERVICE_NAME not installed; nothing to do." -ForegroundColor Yellow
        exit 0
    }
    Write-Host "→ Stopping $SERVICE_NAME ..." -ForegroundColor Yellow
    & $nssm stop $SERVICE_NAME confirm 2>&1 | Out-Null
    Start-Sleep 2
    & $nssm remove $SERVICE_NAME confirm 2>&1 | Out-Null
    Write-Host "✓ Service uninstalled." -ForegroundColor Green
    exit 0
}

# ----------------------------------------------------------------------
# INSTALL path
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "═══ HeartBoxLLM Windows service installer ═══" -ForegroundColor Cyan
Write-Host ""

Require-Admin

# Prereq 1: env file
if (-not (Test-Path $ENV_FILE)) {
    Write-Host "✗ $ENV_FILE not found." -ForegroundColor Red
    Write-Host "  Create it first per docs/PHASE0B-YOUR-CHECKLIST.md §2:" -ForegroundColor Yellow
    Write-Host "    API_KEY=<64 hex chars from secrets.token_hex(32)>" -ForegroundColor Yellow
    Write-Host "    HF_HOME=$env:USERPROFILE\.cache\huggingface" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Found $ENV_FILE" -ForegroundColor Green

# Prereq 2: venv python
if (-not (Test-Path $VENV_PY)) {
    Write-Host "✗ Backend venv not found at $VENV_PY" -ForegroundColor Red
    Write-Host "  Run: cd backend; python -m venv venv; venv\Scripts\pip install -r ..\requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Found venv python" -ForegroundColor Green

# Prereq 3: nssm
$nssm = Find-Nssm
if (-not $nssm) {
    $nssm = Install-Nssm
}
Write-Host "✓ NSSM at $nssm" -ForegroundColor Green

# Resolve HF_HOME from env file (operator may have overridden the default).
$hfHome = "$env:USERPROFILE\.cache\huggingface"
foreach ($line in Get-Content $ENV_FILE) {
    if ($line -match '^\s*HF_HOME\s*=\s*(.+?)\s*$') { $hfHome = $matches[1] }
}
Write-Host "  HF_HOME → $hfHome" -ForegroundColor DarkGray

# Idempotent: remove existing service if present.
if (Service-Exists $SERVICE_NAME) {
    Write-Host ""
    Write-Host "→ Service $SERVICE_NAME already exists." -ForegroundColor Yellow
    if (-not (Confirm "  Stop + remove and reinstall fresh?")) {
        Write-Host "  Aborted (existing service untouched)." -ForegroundColor Yellow
        exit 0
    }
    & $nssm stop $SERVICE_NAME confirm 2>&1 | Out-Null
    Start-Sleep 2
    & $nssm remove $SERVICE_NAME confirm 2>&1 | Out-Null
}

# Create log directory before NSSM tries to write into it.
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

Write-Host ""
Write-Host "→ Installing service..." -ForegroundColor Yellow

# Core install: python.exe -m llm_server
& $nssm install $SERVICE_NAME $VENV_PY '-m' 'llm_server' | Out-Host

# Working directory — must be the repo root so ``llm_server.config`` resolves
# the env file via $env:USERPROFILE (NSSM clears most env unless we set it).
& $nssm set $SERVICE_NAME AppDirectory $REPO_ROOT | Out-Null

# Display name + description so it shows up sensibly in services.msc.
& $nssm set $SERVICE_NAME DisplayName 'HeartBox LLM Server (TAIDE + LLaVA)' | Out-Null
& $nssm set $SERVICE_NAME Description 'FastAPI inference server backing llm.heartbox.tw via Cloudflare Tunnel. Auto-installed by scripts/install-llm-service.ps1.' | Out-Null

# Environment: NSSM needs explicit env vars (it does NOT inherit interactive
# shell vars). HF_HOME is critical — without it the model load times out.
# USERPROFILE is also needed so llm_server/config.py can find ~/.heartbox-llm.env.
$envExtra = @(
    "HF_HOME=$hfHome",
    "USERPROFILE=$env:USERPROFILE",
    "PYTHONIOENCODING=utf-8",
    "PYTHONUNBUFFERED=1"
) -join "`0"
& $nssm set $SERVICE_NAME AppEnvironmentExtra $envExtra | Out-Null

# Auto-restart on crash: wait 5s, then retry forever. Throttle so we don't
# burn the disk if Python is segfaulting in a hot loop.
& $nssm set $SERVICE_NAME AppExit Default Restart | Out-Null
& $nssm set $SERVICE_NAME AppRestartDelay 5000 | Out-Null
& $nssm set $SERVICE_NAME AppThrottle 30000 | Out-Null

# Graceful shutdown sequence: SIGINT (Ctrl-C) → wait → WM_CLOSE → wait → kill.
# TAIDE model unload can take a few seconds; give it room.
& $nssm set $SERVICE_NAME AppStopMethodSkip 0 | Out-Null
& $nssm set $SERVICE_NAME AppStopMethodConsole 10000 | Out-Null
& $nssm set $SERVICE_NAME AppStopMethodWindow 10000 | Out-Null
& $nssm set $SERVICE_NAME AppStopMethodThreads 10000 | Out-Null

# Log file rotation: rotate when stdout > 10 MB OR > 24h old, keep 5 files.
& $nssm set $SERVICE_NAME AppStdout "$LOG_DIR\stdout.log" | Out-Null
& $nssm set $SERVICE_NAME AppStderr "$LOG_DIR\stderr.log" | Out-Null
& $nssm set $SERVICE_NAME AppStdoutCreationDisposition 4 | Out-Null   # OPEN_ALWAYS
& $nssm set $SERVICE_NAME AppStderrCreationDisposition 4 | Out-Null
& $nssm set $SERVICE_NAME AppRotateFiles 1 | Out-Null
& $nssm set $SERVICE_NAME AppRotateOnline 1 | Out-Null
& $nssm set $SERVICE_NAME AppRotateBytes 10485760 | Out-Null          # 10 MB
& $nssm set $SERVICE_NAME AppRotateSeconds 86400 | Out-Null           # 24h

# Boot-time start (runs before any user login).
& $nssm set $SERVICE_NAME Start SERVICE_AUTO_START | Out-Null

Write-Host "✓ Service configured." -ForegroundColor Green

# ----------------------------------------------------------------------
# Start + smoke
# ----------------------------------------------------------------------
Write-Host ""
Write-Host "→ Starting service ..." -ForegroundColor Yellow
& $nssm start $SERVICE_NAME | Out-Host

Write-Host "  (TAIDE 4-bit load typically takes 30-60 s on first start)" -ForegroundColor DarkGray
$ok = $false
$elapsed = 0
while ($elapsed -lt 120) {
    Start-Sleep 5
    $elapsed += 5
    try {
        $r = Invoke-WebRequest -Uri $HEALTH_URL -TimeoutSec 3 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {
        Write-Host -NoNewline "."
    }
}
Write-Host ""

if ($ok) {
    Write-Host "✓ /health responding at $HEALTH_URL after $elapsed s" -ForegroundColor Green
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓ HeartBoxLLM service installed + running" -ForegroundColor Green
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "Operator cheat-sheet:" -ForegroundColor Cyan
    Write-Host "  nssm status  HeartBoxLLM"
    Write-Host "  nssm restart HeartBoxLLM     # picks up sanitize.py / engine.py edits"
    Write-Host "  nssm stop    HeartBoxLLM"
    Write-Host "  Get-Content $LOG_DIR\stdout.log -Tail 50 -Wait"
    Write-Host ""
    Write-Host "  scripts\install-llm-service.ps1 -Uninstall   # remove the service"
    Write-Host ""
    exit 0
} else {
    Write-Host "✗ /health did not respond within 120 s." -ForegroundColor Red
    Write-Host "  The service is registered but Python may have errored on startup." -ForegroundColor Yellow
    Write-Host "  Check the error log:" -ForegroundColor Yellow
    Write-Host "    Get-Content $LOG_DIR\stderr.log -Tail 50" -ForegroundColor Yellow
    Write-Host "  Common causes:" -ForegroundColor Yellow
    Write-Host "    - HF cache missing → run backend\download_models.py first" -ForegroundColor Yellow
    Write-Host "    - GPU OOM           → free VRAM (nvidia-smi) and try nssm restart HeartBoxLLM" -ForegroundColor Yellow
    Write-Host "    - API_KEY too short → see scripts\rotate-llm-key.ps1" -ForegroundColor Yellow
    exit 3
}
