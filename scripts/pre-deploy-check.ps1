# Run the same checks GitHub Actions does, locally, before pushing.
# Catches: secret leaks, banned OpenAI references, failing tests.
#
# Usage:   .\scripts\pre-deploy-check.ps1
# Exit 0  → safe to push
# Exit 1  → fix the issues before pushing

$ErrorActionPreference = 'Continue'
$failed = $false
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host ("─── {0} ───" -f $Name) -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        Write-Host ("✗ {0} FAILED" -f $Name) -ForegroundColor Red
        $script:failed = $true
    } else {
        Write-Host ("✓ {0} OK" -f $Name) -ForegroundColor Green
    }
    Write-Host ""
}

# 1. Check for plaintext secrets in tracked files
Step "1/4  Secret scan (OPENAI_API_KEY / sk-* / AKIA*)" {
    $patterns = @(
        'OPENAI_API_KEY\s*=\s*sk-',
        '\bsk-[a-zA-Z0-9]{20,}',
        '\bAKIA[A-Z0-9]{16}'
    )
    $hits = @()
    foreach ($p in $patterns) {
        $found = git grep -nE $p 2>$null
        if ($found) {
            $hits += $found
        }
    }
    if ($hits.Count -gt 0) {
        Write-Host "  Found potential secrets in tracked files:" -ForegroundColor Red
        $hits | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        $global:LASTEXITCODE = 1
    } else {
        Write-Host "  No plaintext secrets found." -ForegroundColor Green
        $global:LASTEXITCODE = 0
    }
}

# 2. CI guard: simulate no-openai-check.yml
Step "2/4  no-openai-check guard" {
    $pattern = '((import|from)\s+(openai|langchain_openai)\b|OPENAI_[A-Z_]+|(?i:gpt-[0-9][0-9.o-]*|\bo[1-9]-(preview|mini|pro)\b|text-(davinci|babbage|curie|ada)-[0-9]+|gpt-oss(-[0-9]+[a-z]?)?|text-embedding-(ada|3)|api\.openai\.com))'
    $excludes = @(
        '--glob', '!llm_server/**',
        '--glob', '!.github/workflows/no-openai-check.yml',
        '--glob', '!docs/**',
        '--glob', '!research/**',
        '--glob', '!**/CHANGELOG*',
        '--glob', '!**/.env*.example',
        '--glob', '!**/migrations/**',
        '--glob', '!**/*.lock',
        '--glob', '!HANDOFF_*.md',
        '--glob', '!.claude/**',
        '--glob', '!frontend/dist/**',
        '--glob', '!frontend/build/**',
        '--glob', '!**/__pycache__/**',
        '--glob', '!scripts/pre-deploy-check.ps1'
    )
    & rg -n -e $pattern @excludes .
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Banned OpenAI reference found (output above)." -ForegroundColor Red
        $global:LASTEXITCODE = 1
    } else {
        Write-Host "  No banned references." -ForegroundColor Green
        $global:LASTEXITCODE = 0
    }
}

# 3. Crisis-guard unit tests (fast, no DB)
Step "3/4  Crisis-guard tests (no DB)" {
    Push-Location backend
    & .\venv\Scripts\python.exe manage.py test api.test_crisis_guard --noinput 2>&1 | Select-Object -Last 6
    $tc = $LASTEXITCODE
    Pop-Location
    $global:LASTEXITCODE = $tc
}

# 4. llm_server integration tests
Step "4/4  llm_server tests" {
    & .\backend\venv\Scripts\python.exe -m unittest discover -s llm_server.tests 2>&1 | Select-Object -Last 6
}

Write-Host ""
if ($failed) {
    Write-Host "════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  ✗ DO NOT PUSH — fix the failures above" -ForegroundColor Red
    Write-Host "════════════════════════════════════════" -ForegroundColor Red
    exit 1
} else {
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓ All checks green — safe to push" -ForegroundColor Green
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    exit 0
}
