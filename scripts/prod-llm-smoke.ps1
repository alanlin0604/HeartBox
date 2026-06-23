# Real end-to-end LLM probe against production.
# Logs in as the demo user, writes a negative-sentiment mood note,
# polls until AI feedback is populated, and asserts a real TAIDE
# response (not the template fallback).
#
# The audit found that the Cloud Run → Cloudflare Tunnel → TAIDE
# wire has NEVER been verified with a real authenticated user request.
# All previous probes hit /api/internal/cron/* which can short-circuit
# without calling provider.chat() (e.g. weekly-summaries returns
# {"created": 0} when no users qualify).
#
# Usage:
#   $env:DEMO_EMAIL = 'demo@heartbox.tw'
#   $env:DEMO_PASS  = 'DemoPass2026'
#   .\scripts\prod-llm-smoke.ps1
#
# Exit 0 → full pipeline works (Cloud Run → tunnel → TAIDE → ai_feedback)
# Exit 1 → details about which step broke + correlation hints

param(
    [string]$ApiBase = "https://heartbox-api-598139488748.asia-east1.run.app",
    [string]$Email = $env:DEMO_EMAIL,
    [string]$Pass = $env:DEMO_PASS,
    [int]$PollTimeoutSec = 60
)

$ErrorActionPreference = 'Stop'
$timer = [System.Diagnostics.Stopwatch]::StartNew()

if (-not $Email -or -not $Pass) {
    Write-Host "✗ Set DEMO_EMAIL + DEMO_PASS env vars, or pass -Email / -Pass" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "═══ Production LLM smoke test ═══" -ForegroundColor Cyan
Write-Host "API:    $ApiBase"
Write-Host "User:   $Email"
Write-Host ""

# 1. Login
Write-Host "1/4  Logging in..." -ForegroundColor Yellow
try {
    $loginBody = @{ email = $Email; password = $Pass } | ConvertTo-Json
    $login = Invoke-RestMethod -Uri "$ApiBase/api/auth/login/" `
        -Method POST -ContentType 'application/json' -Body $loginBody `
        -TimeoutSec 10
    $jwt = $login.access
    Write-Host "  ✓ access token (first 12): $($jwt.Substring(0,12))..."
} catch {
    Write-Host "  ✗ Login failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Write negative-sentiment mood note
$payload = @{
    content = '今天壓力很大很焦慮，工作做不完，整個人很疲憊。明天還有報告要交，腦袋一片混亂。'
    mood_score = 2
    activities = @('work')
} | ConvertTo-Json

Write-Host "2/4  Writing mood note..." -ForegroundColor Yellow
try {
    $note = Invoke-RestMethod -Uri "$ApiBase/api/notes/" `
        -Method POST -ContentType 'application/json' -Body $payload `
        -Headers @{ 'Authorization' = "Bearer $jwt" } -TimeoutSec 15
    $noteId = $note.id
    Write-Host "  ✓ note id $noteId saved"
} catch {
    Write-Host "  ✗ Note save failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 3. Poll for AI feedback (background worker writes ai_feedback)
Write-Host "3/4  Polling for AI feedback (max ${PollTimeoutSec}s)..." -ForegroundColor Yellow
$feedback = ''
$score = $null
$pollStart = [System.Diagnostics.Stopwatch]::StartNew()
while ($pollStart.Elapsed.TotalSeconds -lt $PollTimeoutSec) {
    Start-Sleep 3
    try {
        $r = Invoke-RestMethod -Uri "$ApiBase/api/notes/$noteId/" `
            -Headers @{ 'Authorization' = "Bearer $jwt" } -TimeoutSec 10
        if ($r.ai_feedback -and $r.ai_feedback.Length -gt 0) {
            $feedback = $r.ai_feedback
            $score = $r.sentiment_score
            Write-Host "  ✓ feedback populated after $([int]$pollStart.Elapsed.TotalSeconds)s"
            break
        }
    } catch {
        # transient
    }
}

if (-not $feedback) {
    Write-Host "  ✗ Timeout — ai_feedback never populated" -ForegroundColor Red
    exit 1
}

# 4. Assert NOT template fallback (template is the 暫時無法 line)
Write-Host "4/4  Verifying TAIDE response (not template fallback)..." -ForegroundColor Yellow
Write-Host "  sentiment_score: $score"
Write-Host "  feedback (first 80): $($feedback.Substring(0,[Math]::Min(80, $feedback.Length)))..."
Write-Host ""

if ($feedback -match '暫時無法' -or $feedback -match 'temporarily' -or $feedback.Length -lt 30) {
    Write-Host "✗ Got template fallback — TAIDE call FAILED, tier-2 absorbed it" -ForegroundColor Red
    Write-Host "  Check: gcloud run services logs read heartbox-api --region=asia-east1 --limit=50 | grep llm_call" -ForegroundColor Yellow
    exit 1
}

# Bonus: tail Cloud Run logs to confirm llm_call status=ok
Write-Host "Verifying in Cloud Run logs..." -ForegroundColor Yellow
$logs = gcloud run services logs read heartbox-api --region=asia-east1 --limit=30 2>&1
$llmCallLine = $logs | Select-String "llm_call.*status=ok" | Select-Object -First 1
if ($llmCallLine) {
    Write-Host "  ✓ found: $($llmCallLine.Line.Substring(0, [Math]::Min(180, $llmCallLine.Line.Length)))..."
} else {
    Write-Host "  ⚠ no recent llm_call status=ok in last 30 logs (may have rolled off)" -ForegroundColor Yellow
}

$timer.Stop()
Write-Host ""
Write-Host "════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✓ Full pipeline verified in $([int]$timer.Elapsed.TotalSeconds)s" -ForegroundColor Green
Write-Host "  Cloud Run → Cloudflare Tunnel → TAIDE → ai_feedback" -ForegroundColor Green
Write-Host "════════════════════════════════════════" -ForegroundColor Green
