# Quarterly API key rotation wizard for the HeartBox LLM stack.
# Walks through all 5 manual steps with confirmations + verification.
#
# This script DOES write to ~/.heartbox-llm.env and DOES call
# `gcloud run services update`, so back up the existing env file
# first if you want a paper trail.
#
# Usage:
#   .\scripts\rotate-llm-key.ps1                    # interactive wizard
#   .\scripts\rotate-llm-key.ps1 -Region asia-east1 -Service heartbox-api
#
# Steps performed:
#   1. Generate new 64-hex API key (cryptographically random)
#   2. Back up ~/.heartbox-llm.env to ~/.heartbox-llm.env.bak-YYYYMMDD-HHMMSS
#   3. Write new key to ~/.heartbox-llm.env (preserve all other lines)
#   4. Restart HeartBoxLLM Windows service (if installed) or warn the user
#      to restart manually
#   5. Update Cloud Run env var LLM_SERVER_API_KEY → new key (creates new
#      revision)
#   6. Smoke-test the rotation: curl /health on the tunnel, verify 200

param(
    [string]$Region = "asia-east1",
    [string]$Service = "heartbox-api"
)

$ErrorActionPreference = 'Stop'

function Confirm($message) {
    $resp = Read-Host ("{0} [y/N]" -f $message)
    return $resp -eq 'y' -or $resp -eq 'Y'
}

$envFile = "$env:USERPROFILE\.heartbox-llm.env"
if (-not (Test-Path $envFile)) {
    Write-Host "✗ $envFile not found — set up the env file first per docs/PHASE0B-YOUR-CHECKLIST.md §2" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "═══ HeartBox LLM API key rotation ═══" -ForegroundColor Cyan
Write-Host ""
Write-Host "This wizard will:" -ForegroundColor Yellow
Write-Host "  1. Generate a new 64-hex API key"
Write-Host "  2. Back up your current ~/.heartbox-llm.env"
Write-Host "  3. Write new key locally"
Write-Host "  4. Restart HeartBoxLLM Windows service (if present)"
Write-Host "  5. Update Cloud Run env var LLM_SERVER_API_KEY"
Write-Host "  6. Smoke-test https://llm.heartbox.tw/health"
Write-Host ""
Write-Host "⚠  Production AI will return 401 for ~30-60 s during rotation" -ForegroundColor Magenta
Write-Host "   (Tier-2 fallback covers HIGH-crisis hotline; RAG temporarily downgrades)" -ForegroundColor Magenta
Write-Host ""

if (-not (Confirm "Continue?")) {
    Write-Host "Aborted." -ForegroundColor Yellow
    exit 0
}

# 1. Generate
$python = "$PSScriptRoot\..\backend\venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$newKey = & $python -c "import secrets; print(secrets.token_hex(32))"
if ($newKey.Length -ne 64) {
    Write-Host "✗ Key generation produced unexpected output: $newKey" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "✓ Generated new key (first 8): $($newKey.Substring(0,8))..." -ForegroundColor Green
Write-Host ""
Write-Host "⚠  SAVE THIS KEY TO YOUR PASSWORD MANAGER NOW:" -ForegroundColor Magenta
Write-Host "   $newKey" -ForegroundColor White
Write-Host ""
if (-not (Confirm "Have you saved the new key?")) {
    Write-Host "Aborted — nothing changed." -ForegroundColor Yellow
    exit 0
}

# 2. Backup
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$envFile.bak-$ts"
Copy-Item $envFile $backup
Write-Host "✓ Backed up to $backup" -ForegroundColor Green

# 3. Write new key (preserve all other lines)
$content = Get-Content $envFile
$updated = $content | ForEach-Object {
    if ($_ -match '^API_KEY=') { "API_KEY=$newKey" } else { $_ }
}
[System.IO.File]::WriteAllText($envFile, ($updated -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))
Write-Host "✓ Wrote new key to $envFile" -ForegroundColor Green

# 4. Restart service
$svc = Get-Service -Name HeartBoxLLM -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "→ Restarting HeartBoxLLM service..." -ForegroundColor Yellow
    nssm restart HeartBoxLLM 2>&1 | Out-Null
    Write-Host "  waiting 60s for TAIDE to reload..." -ForegroundColor DarkGray
    Start-Sleep 60
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -TimeoutSec 5 -UseBasicParsing
        if ($r.StatusCode -eq 200) {
            Write-Host "✓ Local server back up with new key" -ForegroundColor Green
        }
    } catch {
        Write-Host "✗ Local server didn't respond — investigate before continuing" -ForegroundColor Red
        Write-Host "  rollback: copy $backup over $envFile and nssm restart HeartBoxLLM" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "⚠  HeartBoxLLM service not installed — you need to restart llm_server manually" -ForegroundColor Yellow
    Write-Host "   (the manually-started python process; kill it and re-run start.bat)" -ForegroundColor Yellow
    Read-Host "Press Enter once the local server is back up"
}

# 5. Cloud Run
Write-Host "→ Updating Cloud Run env LLM_SERVER_API_KEY..." -ForegroundColor Yellow
gcloud run services update $Service `
  --region=$Region `
  --update-env-vars="LLM_SERVER_API_KEY=$newKey" `
  --quiet 2>&1 | Select-Object -Last 3

# 6. Smoke test
Write-Host ""
Write-Host "→ Smoke-testing https://llm.heartbox.tw/health..." -ForegroundColor Yellow
$ok = $false
for ($i = 1; $i -le 6; $i++) {
    Start-Sleep 5
    try {
        $r = Invoke-WebRequest -Uri "https://llm.heartbox.tw/health" -TimeoutSec 5 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
}
if ($ok) {
    Write-Host "✓ Tunnel /health responding" -ForegroundColor Green
} else {
    Write-Host "✗ Tunnel /health timing out — verify llm_server + cloudflared services" -ForegroundColor Red
}

Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Rotation complete." -ForegroundColor Green
Write-Host "  Old key in: $backup" -ForegroundColor Green
Write-Host "  Verify by writing a journal note that triggers AI feedback." -ForegroundColor Green
Write-Host "════════════════════════════════════════" -ForegroundColor Green
