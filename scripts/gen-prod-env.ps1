# Generate the four production env-var values for the Phase 0b LLM stack
# and print them in copy-paste-ready blocks for:
#   (a) Render dashboard's "Add Environment Variable" form
#   (b) a gcloud one-liner for Cloud Run
#
# Reads LLM_SERVER_API_KEY from %USERPROFILE%\.heartbox-llm.env so the
# server-side and backend-side use the same key. Generates a fresh
# CRON_SECRET each run.
#
# Usage:   .\scripts\gen-prod-env.ps1 [-Domain llm.heartbox.tw] [-Service heartbox-api] [-Region asia-east1]
#
# DO NOT commit the output. Paste it directly into the Render dashboard
# or the gcloud command, then close the terminal.

param(
    [string]$Domain = "llm.heartbox.tw",
    [string]$Service = "heartbox-api",
    [string]$Region = "asia-east1"
)

$envFile = "$env:USERPROFILE\.heartbox-llm.env"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: $envFile not found." -ForegroundColor Red
    Write-Host "       Create it first per docs/PHASE0B-YOUR-CHECKLIST.md §2." -ForegroundColor Red
    exit 1
}

$apiKeyLine = Get-Content $envFile | Select-String "^API_KEY=" | Select-Object -First 1
if (-not $apiKeyLine) {
    Write-Host "ERROR: API_KEY= not found in $envFile" -ForegroundColor Red
    exit 1
}
$apiKey = $apiKeyLine.Line.Split("=", 2)[1].Trim()
if ($apiKey.Length -lt 32) {
    Write-Host "WARNING: API_KEY looks short ($($apiKey.Length) chars). Should be 64 hex." -ForegroundColor Yellow
}

# Find python — prefer the project venv, fall back to PATH.
$python = "$PSScriptRoot\..\backend\venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}
$cronSecret = & $python -c "import secrets; print(secrets.token_hex(32))"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Production env-var block (Render / Cloud Run)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Copy-paste into Render dashboard → Environment → Add Variable:" -ForegroundColor Yellow
Write-Host ""
Write-Host "LLM_PROVIDER=remote_taide" -ForegroundColor White
Write-Host "LLM_SERVER_URL=https://$Domain" -ForegroundColor White
Write-Host "LLM_SERVER_API_KEY=$apiKey" -ForegroundColor White
Write-Host "CRON_SECRET=$cronSecret" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 OR gcloud one-liner for Cloud Run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "gcloud run services update $Service \`" -ForegroundColor White
Write-Host "  --region=$Region \`" -ForegroundColor White
Write-Host "  --update-env-vars=`"LLM_PROVIDER=remote_taide,LLM_SERVER_URL=https://$Domain,LLM_SERVER_API_KEY=$apiKey,CRON_SECRET=$cronSecret`"" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠  IMPORTANT:" -ForegroundColor Magenta
Write-Host "  - Save CRON_SECRET to your password manager NOW" -ForegroundColor Magenta
Write-Host "    (it's not recoverable from anywhere else)" -ForegroundColor Magenta
Write-Host "  - DO NOT commit this output" -ForegroundColor Magenta
Write-Host "  - Close this terminal after pasting" -ForegroundColor Magenta
Write-Host ""
