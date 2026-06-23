# Rotate ENCRYPTION_KEY (Fernet) on Cloud Run using MultiFernet
# (comma-separated keys: new first, old second so existing data can
# still decrypt).
#
# backend/api/services/encryption.py supports comma-separated keys
# via MultiFernet — old data decrypts with the second key, new data
# encrypts with the first. After all existing rows have been re-encrypted
# (`manage.py reencrypt_notes` if such command exists), the old key
# can be dropped.
#
# Usage:
#   .\scripts\rotate-encryption-key.ps1
#
# Exit 0 → new key is first in ENCRYPTION_KEY env (MultiFernet active)
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
Write-Host "═══ ENCRYPTION_KEY (Fernet) rotation ═══" -ForegroundColor Cyan
Write-Host ""
Write-Host "This wizard will:" -ForegroundColor Yellow
Write-Host "  1. Generate a new Fernet key"
Write-Host "  2. Read current ENCRYPTION_KEY from Cloud Run"
Write-Host "  3. Build new value: '<new>,<old>' (MultiFernet)"
Write-Host "  4. Push to Cloud Run via --update-env-vars"
Write-Host "  5. Print follow-up steps for re-encryption pass"
Write-Host ""
Write-Host "⚠  After this rotation, encrypted notes can be DECRYPTED with EITHER key" -ForegroundColor Magenta
Write-Host "   but NEW encryption uses ONLY the new key. Eventually you should run" -ForegroundColor Magenta
Write-Host "   a re-encryption pass + drop the old key from ENCRYPTION_KEY env." -ForegroundColor Magenta
Write-Host ""

if (-not (Confirm "Continue?")) { exit 0 }

# 1. Generate new Fernet
$python = "$PSScriptRoot\..\backend\venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
$newKey = & $python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Write-Host "✓ New key (first 8): $($newKey.Substring(0,8))..." -ForegroundColor Green
Write-Host ""
Write-Host "⚠  SAVE TO PASSWORD MANAGER:" -ForegroundColor Magenta
Write-Host "   $newKey" -ForegroundColor White
Write-Host ""
if (-not (Confirm "Saved?")) { Write-Host "Aborted." -ForegroundColor Yellow; exit 0 }

# 2. Read current value
Write-Host "→ Reading current ENCRYPTION_KEY from Cloud Run..." -ForegroundColor Yellow
$svcDesc = gcloud run services describe $Service --region=$Region --format=json 2>$null
$current = $svcDesc | & $python -c @"
import json, sys
d = json.load(sys.stdin)
for e in d.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [{}])[0].get('env', []):
    if e.get('name') == 'ENCRYPTION_KEY':
        print(e.get('value', ''))
        break
"@

if (-not $current) {
    Write-Host "✗ Could not read current ENCRYPTION_KEY from Cloud Run service" -ForegroundColor Red
    exit 1
}
Write-Host "  current keys count: $($current.Split(',').Count)"

# 3. Build new comma-separated value
$combined = "$newKey,$current"

# 4. Push
Write-Host "→ Pushing combined key to Cloud Run..." -ForegroundColor Yellow
gcloud run services update $Service `
  --region=$Region `
  --update-env-vars="ENCRYPTION_KEY=$combined" `
  --quiet 2>&1 | Select-Object -Last 3

Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✓ Rotation phase 1 complete." -ForegroundColor Green
Write-Host "    Old data: decrypts with either key" -ForegroundColor Green
Write-Host "    New data: encrypts with new key" -ForegroundColor Green
Write-Host "════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "FOLLOW-UP (do within a week):" -ForegroundColor Yellow
Write-Host "  1. Run a re-encryption job to migrate old-key data:" -ForegroundColor Yellow
Write-Host "       gcloud run jobs deploy reencrypt-notes \``"
Write-Host "         --image=<current-image> \``"
Write-Host "         --command=python --args=manage.py,reencrypt_notes \``"
Write-Host "         --region=$Region"
Write-Host "     (write the manage.py command if it does not exist yet)" -ForegroundColor Yellow
Write-Host "  2. After all rows re-encrypted, drop the old key from env:" -ForegroundColor Yellow
Write-Host "       gcloud run services update $Service --region=$Region \``"
Write-Host "         --update-env-vars=`"ENCRYPTION_KEY=$newKey`""
