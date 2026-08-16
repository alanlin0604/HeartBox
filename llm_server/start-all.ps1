# Start the whole local AI stack: inference server + Cloudflare tunnel.
#
# The Cloud Run backend (project heartbox-tw) calls https://llm.heartbox.tw for
# every AI feature that generates new text — note analysis, daily personalised
# suggestion, AI chat. Without this running, llm.heartbox.tw returns 530 and
# those features fall back to static template text. Existing notes are
# unaffected: their AI feedback is already stored in Postgres.
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

Write-Host ''
Write-Host 'Model load takes ~20s. Verify with:' -ForegroundColor Yellow
Write-Host '  curl.exe -s http://127.0.0.1:8765/health     # {"status":"ok"}'
Write-Host '  curl.exe -s https://llm.heartbox.tw/health   # same, through the tunnel'
