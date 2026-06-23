# HeartBox GPU live monitor.
#
# Polls nvidia-smi every 3 seconds and prints a coloured dashboard:
#   - GREEN if temp/VRAM healthy
#   - YELLOW if warm/half-full
#   - RED if temp >85 C or VRAM >90 %
#
# Usage:   .\scripts\gpu-monitor.ps1
# Stop:    Ctrl-C
#
# Demo-day use: open this in a separate PowerShell window so you can
# glance at it during inference. If the panel turns red, switch to the
# Cloud Run mock-fallback revision before the next request.

while ($true) {
    $smi = nvidia-smi --query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
    if (-not $smi) {
        Write-Host "nvidia-smi not available — is the NVIDIA driver installed?" -ForegroundColor Red
        Start-Sleep 5
        continue
    }
    $vals = $smi -split ','
    $temp = [int]$vals[0]
    $used = [int]$vals[1]
    $total = [int]$vals[2]
    $util = [int]$vals[3]
    $pct = [math]::Round(($used / $total) * 100, 0)

    Clear-Host
    Write-Host ("═══ HeartBox GPU monitor  ({0}) ═══" -f (Get-Date -Format 'HH:mm:ss')) -ForegroundColor Cyan
    Write-Host ""

    if ($temp -gt 85) {
        Write-Host ("🔥 Temp {0} °C  — DANGER zone, consider pausing inference" -f $temp) -ForegroundColor Red
    } elseif ($temp -gt 75) {
        Write-Host ("⚠  Temp {0} °C  — warm" -f $temp) -ForegroundColor Yellow
    } else {
        Write-Host ("✓  Temp {0} °C" -f $temp) -ForegroundColor Green
    }

    if ($pct -gt 90) {
        Write-Host ("⚠  VRAM {0}/{1} MB ({2}%) — near OOM" -f $used, $total, $pct) -ForegroundColor Red
    } elseif ($pct -gt 70) {
        Write-Host ("   VRAM {0}/{1} MB ({2}%)" -f $used, $total, $pct) -ForegroundColor Yellow
    } else {
        Write-Host ("✓  VRAM {0}/{1} MB ({2}%)" -f $used, $total, $pct) -ForegroundColor Green
    }

    Write-Host ("   GPU util  {0}%" -f $util)
    Write-Host ""
    Write-Host "(Ctrl+C to quit)" -ForegroundColor DarkGray
    Start-Sleep 3
}
