# Stop the local AI stack started by start-all.ps1, freeing GPU memory, and
# put Cloud Run back on request-based billing.
#
# Matches on command line, not just process name, so unrelated python.exe or
# cloudflared.exe processes (other projects, other tunnels) are left alone.
#
# The Cloud Run half matters as much as the GPU half: start-all.ps1 sets
# --no-cpu-throttling, which bills the whole instance lifetime rather than just
# request time (~$2/hour of uptime). Leaving it on for a day cost $18.54, so it
# is reverted whenever the AI stack goes down. The site keeps working — only
# AI feedback on *newly written* notes stops appearing.
#
# Usage:  .\llm_server\stop-all.ps1

$stopped = 0

$targets = @(
    @{ Name = 'python.exe';      Match = '*llm_server*';   Label = '推論 server' },
    @{ Name = 'cloudflared.exe'; Match = '*heartbox-llm*'; Label = 'tunnel' }
)

foreach ($t in $targets) {
    Get-CimInstance Win32_Process -Filter "Name='$($t.Name)'" |
        Where-Object { $_.CommandLine -like $t.Match } |
        ForEach-Object {
            Write-Host "  停止 $($t.Label) (PID $($_.ProcessId))"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $stopped++
        }
}

if ($stopped -eq 0) {
    Write-Host '  沒有找到執行中的 HeartBox AI 服務。'
} else {
    Start-Sleep -Seconds 2
    Write-Host ''
    Write-Host "  已停止 $stopped 個處理程序。"
}

# Report GPU state so it is obvious whether VRAM actually came back.
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) {
    $vram = (& nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader) -join ''
    Write-Host "  GPU 記憶體: $vram"
}

Write-Host ''
Write-Host '  Cloud Run 切回 request-based billing（省錢）...'
# gcloud.cmd rather than the gcloud.ps1 on PATH — see the note in start-all.ps1
# about stderr progress output becoming a terminating error.
$gcloud = 'C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'
if (-not (Test-Path $gcloud)) { $gcloud = 'gcloud.cmd' }
& $gcloud run services update heartbox-api --region asia-east1 --project heartbox-tw --cpu-throttling --quiet | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host '  已切回。閒置時不再計費。' -ForegroundColor Green
} else {
    Write-Host '  失敗 — 仍在計費中！手動執行：' -ForegroundColor Red
    Write-Host '  gcloud run services update heartbox-api --region asia-east1 --project heartbox-tw --cpu-throttling'
}
