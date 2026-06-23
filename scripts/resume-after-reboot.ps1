# Verify the entire HeartBox stack is healthy after a machine reboot.
# Runs through 5 checks: Windows services, local /health, GPU state,
# Cloudflare tunnel, and external reachability.
#
# Usage:   .\scripts\resume-after-reboot.ps1 [-Domain llm.heartbox.tw]
# Exit 0  → stack ready
# Exit 1  → at least one check failed (instructions printed)

param(
    [string]$Domain = "llm.heartbox.tw"
)

$results = @()
function Check {
    param([string]$Name, [scriptblock]$Test, [string]$FixHint)
    $ok = $false
    try {
        $ok = & $Test
    } catch {
        $ok = $false
    }
    $sigil = if ($ok) { "✓" } else { "✗" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host ("{0}  {1}" -f $sigil, $Name) -ForegroundColor $color
    if (-not $ok -and $FixHint) {
        Write-Host ("       fix: {0}" -f $FixHint) -ForegroundColor Yellow
    }
    $script:results += $ok
}

Write-Host ""
Write-Host "═══ HeartBox stack post-reboot health ═══" -ForegroundColor Cyan
Write-Host ""

Check "HeartBoxLLM Windows service running" {
    $svc = Get-Service -Name HeartBoxLLM -ErrorAction SilentlyContinue
    $svc -and ($svc.Status -eq 'Running')
} "nssm start HeartBoxLLM    (or install per checklist §4)"

Check "Cloudflared service running" {
    $svc = Get-Service -Name Cloudflared -ErrorAction SilentlyContinue
    $svc -and ($svc.Status -eq 'Running')
} "sc.exe start Cloudflared    (or install per checklist §1.8)"

Check "GPU detected" {
    $smi = nvidia-smi --query-gpu=name --format=csv,noheader 2>$null
    $smi -and ($smi.Length -gt 0)
} "Check NVIDIA driver is loaded; reboot if Windows Update touched the kernel"

Check "Local llm_server /health" {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $r.StatusCode -eq 200 -and $r.Content -match '"status":\s*"ok"'
    } catch { $false }
} "nssm restart HeartBoxLLM ; wait 60s for TAIDE to reload"

Check "External tunnel reachable ($Domain)" {
    try {
        $r = Invoke-WebRequest -Uri "https://$Domain/health" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        $r.StatusCode -eq 200
    } catch { $false }
} "Check Cloudflared service; verify Cloudflare DNS shows the CNAME; test from phone 4G"

Write-Host ""
$failed = $results | Where-Object { -not $_ }
if ($failed.Count -gt 0) {
    Write-Host ("✗  {0} check(s) failed" -f $failed.Count) -ForegroundColor Red
    Write-Host ""
    Write-Host "See docs/PHASE0B-YOUR-CHECKLIST.md for repair steps." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓  Stack is ready" -ForegroundColor Green
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    exit 0
}
