# Tail the HeartBoxLLM Windows service log files.
#
# Usage:
#   .\scripts\llm-logs.ps1                  # last 50 lines of stderr
#   .\scripts\llm-logs.ps1 -Follow          # live tail
#   .\scripts\llm-logs.ps1 -Stdout          # switch to stdout log
#   .\scripts\llm-logs.ps1 -Lines 200       # custom tail length

param(
    [int]$Lines = 50,
    [switch]$Follow,
    [switch]$Stdout
)

$file = if ($Stdout) {
    "$env:USERPROFILE\heartbox-llm-stdout.log"
} else {
    "$env:USERPROFILE\heartbox-llm-stderr.log"
}

if (-not (Test-Path $file)) {
    Write-Host "Log file not found: $file" -ForegroundColor Red
    Write-Host "  - Is the HeartBoxLLM service installed? Run: nssm status HeartBoxLLM" -ForegroundColor Yellow
    Write-Host "  - Log path may differ if you configured NSSM with different paths." -ForegroundColor Yellow
    exit 1
}

if ($Follow) {
    Write-Host "Following $file (Ctrl-C to stop)..." -ForegroundColor Cyan
    Get-Content $file -Wait -Tail $Lines
} else {
    Get-Content $file -Tail $Lines
}
