# Stop the local AI stack started by start-all.ps1, freeing GPU memory.
#
# Matches on command line, not just process name, so unrelated python.exe or
# cloudflared.exe processes (other projects, other tunnels) are left alone.
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
