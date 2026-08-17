# Start the whole local AI stack: inference server + Cloudflare tunnel, and
# put Cloud Run into the billing mode the AI pipeline needs.
#
# The Cloud Run backend (project heartbox-tw) calls https://llm.heartbox.tw for
# every AI feature that generates new text — note analysis, daily personalised
# suggestion, AI chat. Without this running, llm.heartbox.tw returns 530 and
# those features fall back to static template text. Existing notes are
# unaffected: their AI feedback is already stored in Postgres.
#
# Cloud Run also gets --no-cpu-throttling here. Note analysis runs on a
# threading.Thread spawned after the POST response is sent, so with throttled
# CPU it is starved and the feedback never appears. That setting switches
# Cloud Run to instance-based billing (~$2/hour of instance uptime), which is
# why it is tied to the AI stack being up rather than left on permanently —
# one day of leaving it on cost $18.54. stop-all.ps1 reverts it.
#
# Opens two windows; both must stay open. Ctrl-C in either one stops that half.
#
# Usage:  .\llm_server\start-all.ps1

$ErrorActionPreference = 'Stop'

$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root 'backend\venv\Scripts\python.exe'
$cloudflared = "$env:LOCALAPPDATA\cloudflared\cloudflared.exe"
$envFile = "$env:USERPROFILE\.heartbox-llm.env"

foreach ($p in @($python, $cloudflared, $envFile)) {
    if (-not (Test-Path $p)) { throw "Missing prerequisite: $p" }
}

Write-Host '=== Window 1: inference server (127.0.0.1:8765) ===' -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$root'; `$env:PYTHONIOENCODING='utf-8'; & '$python' -m llm_server"
)

Write-Host '=== Window 2: Cloudflare tunnel (llm.heartbox.tw) ===' -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit', '-Command',
    "& '$cloudflared' tunnel run heartbox-llm"
)

# Model load runs in parallel with this, so the gcloud round-trip is close to free.
Write-Host ''
Write-Host '=== Cloud Run: CPU 常駐（背景分析執行緒需要）===' -ForegroundColor Cyan
# Invoke gcloud.cmd, not the gcloud.ps1 on PATH: gcloud writes progress to
# stderr, and under $ErrorActionPreference='Stop' PowerShell 5.1 turns that
# into a terminating NativeCommandError. The first version of this script
# swallowed the whole update that way and silently left billing throttled.
$ErrorActionPreference = 'Continue'
$gcloud = 'C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
if (-not (Test-Path $gcloud)) { $gcloud = 'gcloud.cmd' }
& $gcloud run services update heartbox-api --region asia-east1 --project heartbox-tw --no-cpu-throttling --quiet | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host '  已切換為 instance-based billing。' -ForegroundColor Green
} else {
    Write-Host '  失敗 — 新日記的 AI 回饋不會出現。手動執行：' -ForegroundColor Yellow
    Write-Host '  gcloud run services update heartbox-api --region asia-east1 --project heartbox-tw --no-cpu-throttling'
}

Write-Host ''
Write-Host 'Model load takes ~40s. Verify with:' -ForegroundColor Yellow
Write-Host '  curl.exe -s http://127.0.0.1:8765/health     # {"status":"ok"}'
Write-Host '  curl.exe -s https://llm.heartbox.tw/health   # same, through the tunnel'
