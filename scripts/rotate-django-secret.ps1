# Rotate DJANGO_SECRET_KEY on Cloud Run.
#
# WARNING: this invalidates ALL existing JWT signatures and session
# cookies. Every logged-in user will be kicked out. Use only when:
#   * The current key has leaked, OR
#   * Quarterly rotation per ops policy
#
# Usage:
#   .\scripts\rotate-django-secret.ps1
#
# Exit 0 → key rotated, expect logout wave on next user request
# Exit 1 → details about which step broke

param(
    [string]$Region = "asia-east1",
    [string]$Service = "heartbox-api"
)

$ErrorActionPreference = 'Stop'

function Confirm($message) {
    $resp = Read-Host ("{0} [y/N]" -f $message)
    return $resp -eq 'y' -or $resp -eq 'Y'
}

Write-Host ""
Write-Host "═══ DJANGO_SECRET_KEY rotation ═══" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠  This will:" -ForegroundColor Magenta
Write-Host "    1. Generate a new 50-char URL-safe secret" -ForegroundColor Magenta
Write-Host "    2. Push it to Cloud Run env" -ForegroundColor Magenta
Write-Host "    3. **Invalidate all existing JWTs / session cookies**" -ForegroundColor Magenta
Write-Host "    4. Every logged-in user will see 401 on next request" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Only rotate when:" -ForegroundColor Yellow
Write-Host "    - Key has leaked (commit/log/screenshot exposure)" -ForegroundColor Yellow
Write-Host "    - Quarterly ops policy" -ForegroundColor Yellow
Write-Host "    - Right before a major release (clean slate)" -ForegroundColor Yellow
Write-Host ""

if (-not (Confirm "Acknowledge logout impact and continue?")) {
    Write-Host "Aborted." -ForegroundColor Yellow; exit 0
}

# Generate
$python = "$PSScriptRoot\..\backend\venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$newKey = & $python -c "import secrets; print(secrets.token_urlsafe(50))"

if ($newKey.Length -lt 60) {
    Write-Host "✗ Key gen produced unexpected output" -ForegroundColor Red; exit 1
}
Write-Host "✓ Generated (first 8): $($newKey.Substring(0,8))..." -ForegroundColor Green
Write-Host ""
Write-Host "⚠  SAVE TO PASSWORD MANAGER:" -ForegroundColor Magenta
Write-Host "   $newKey" -ForegroundColor White
Write-Host ""
if (-not (Confirm "Saved?")) { Write-Host "Aborted." -ForegroundColor Yellow; exit 0 }

# Push to Cloud Run
Write-Host "→ Updating Cloud Run env DJANGO_SECRET_KEY..." -ForegroundColor Yellow
gcloud run services update $Service `
  --region=$Region `
  --update-env-vars="DJANGO_SECRET_KEY=$newKey" `
  --quiet 2>&1 | Select-Object -Last 3

# Smoke: confirm service still responds
Write-Host "→ Waiting 30s for new revision to take traffic..." -ForegroundColor Yellow
Start-Sleep 30

try {
    $r = Invoke-WebRequest -Uri "https://heartbox-api-598139488748.asia-east1.run.app/api/" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "✓ Service responding (HTTP $($r.StatusCode))" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host "✓ Service responding (401 = auth gate, healthy)" -ForegroundColor Green
    } else {
        Write-Host "✗ Service not responding: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "  Check logs: gcloud run services logs read $Service --region=$Region --limit=20" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✓ DJANGO_SECRET_KEY rotated" -ForegroundColor Green
Write-Host "  ⚠ All users will be logged out on next request" -ForegroundColor Yellow
Write-Host "════════════════════════════════════════" -ForegroundColor Green
