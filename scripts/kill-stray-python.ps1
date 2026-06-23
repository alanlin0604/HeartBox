# List or kill Python processes that are NOT the HeartBoxLLM service.
# Useful when you've manually run start.bat earlier and now want to
# install the NSSM service without port conflicts on 8765.
#
# Usage:
#   .\scripts\kill-stray-python.ps1            # dry-run, list orphans
#   .\scripts\kill-stray-python.ps1 -Force     # actually kill them

param([switch]$Force)

$svcPid = $null
try {
    $svcPid = (Get-WmiObject Win32_Service -Filter "Name='HeartBoxLLM'" -ErrorAction Stop).ProcessId
} catch {
    Write-Host "HeartBoxLLM service not installed — all python processes are 'stray' by definition." -ForegroundColor Yellow
}

$pythons = Get-Process python -ErrorAction SilentlyContinue
if (-not $pythons) {
    Write-Host "No python processes running." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "All python processes:" -ForegroundColor Cyan
Write-Host ""
$strays = @()
foreach ($p in $pythons) {
    $isService = ($svcPid -and ($p.Id -eq $svcPid))
    $tag = if ($isService) { "[SERVICE]" } else { "[stray]" }
    $color = if ($isService) { "Green" } else { "Yellow" }
    Write-Host ("  {0} PID {1,-7} started {2}" -f $tag, $p.Id, $p.StartTime) -ForegroundColor $color
    if (-not $isService) {
        $strays += $p
    }
}

Write-Host ""
if ($strays.Count -eq 0) {
    Write-Host "No strays — only the service is running." -ForegroundColor Green
    exit 0
}

if ($Force) {
    Write-Host ("Killing {0} stray process(es)..." -f $strays.Count) -ForegroundColor Red
    foreach ($s in $strays) {
        Stop-Process -Id $s.Id -Force
        Write-Host ("  killed PID {0}" -f $s.Id) -ForegroundColor Red
    }
} else {
    Write-Host ("Found {0} stray python process(es). Re-run with -Force to kill them." -f $strays.Count) -ForegroundColor Yellow
}
