# Generate the Android signing keystore for HeartBox releases.
#
# Why this script exists: the mobile-build.yml workflow needs four GitHub
# Secrets to sign release APKs/AABs. This generates the keystore using
# Docker (no local JDK required) and prints the four values you need to paste
# into GitHub.
#
# CRITICAL:
#   - Run this ONCE and back up heartbox.keystore to a secure location (1Password,
#     encrypted USB, OneDrive Personal Vault). Losing it means you can never
#     publish app updates — Google Play locks the signing key per app.
#   - Never commit the keystore to git. The .gitignore in this repo excludes
#     *.keystore, but always sanity-check `git status` before pushing.
#
# Usage:
#   .\scripts\generate-android-keystore.ps1
#   (you'll be prompted for a password — use a password manager to store it)

$ErrorActionPreference = "Stop"

# Output directory: outside the repo to make it harder to accidentally commit.
$OutDir = "$HOME\.heartbox-android"
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$KeystorePath = Join-Path $OutDir "heartbox.keystore"
$Base64Path   = Join-Path $OutDir "heartbox.keystore.base64"

if (Test-Path $KeystorePath) {
    Write-Host "WARNING: $KeystorePath already exists." -ForegroundColor Yellow
    $reply = Read-Host "Overwrite? Existing app signatures will become invalid. (y/N)"
    if ($reply -ne 'y') { Write-Host "Aborted."; exit 1 }
    Remove-Item $KeystorePath -Force
    if (Test-Path $Base64Path) { Remove-Item $Base64Path -Force }
}

# Prompt for password (typed twice, hidden). 12+ chars recommended.
Write-Host ""
Write-Host "=== Pick a strong password (12+ chars). You will need it again ===" -ForegroundColor Cyan
$pw1 = Read-Host -AsSecureString "Keystore password"
$pw2 = Read-Host -AsSecureString "Confirm password"
$plain1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw1))
$plain2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw2))
if ($plain1 -ne $plain2) { Write-Host "Passwords don't match." -ForegroundColor Red; exit 1 }
if ($plain1.Length -lt 12) { Write-Host "Password too short (<12 chars)." -ForegroundColor Red; exit 1 }

# Use Docker (already installed for the backend deploy fix) to run keytool
# without requiring a local JDK.
Write-Host ""
Write-Host "=== Generating keystore via Docker (eclipse-temurin:17-jre) ===" -ForegroundColor Cyan
$dockerOut = ($OutDir -replace '\\', '/')
docker run --rm -v "${dockerOut}:/out" -w /out eclipse-temurin:17-jre `
    keytool -genkeypair -v `
        -keystore heartbox.keystore `
        -keyalg RSA -keysize 2048 `
        -validity 10000 `
        -alias heartbox `
        -storepass $plain1 `
        -keypass $plain1 `
        -dname "CN=HeartBox, O=HeartBox, L=Taipei, C=TW"
if ($LASTEXITCODE -ne 0) { throw "keytool failed" }

# Base64 for the GitHub secret. -w 0 prevents line wrapping which would corrupt
# the secret on paste.
Write-Host ""
Write-Host "=== Encoding keystore as base64 ===" -ForegroundColor Cyan
[Convert]::ToBase64String([IO.File]::ReadAllBytes($KeystorePath)) | Out-File -Encoding ascii $Base64Path
$base64 = Get-Content $Base64Path -Raw

Write-Host ""
Write-Host "=== Done. Files saved to: $OutDir ===" -ForegroundColor Green
Write-Host "  heartbox.keystore         (binary, BACK UP SECURELY)"
Write-Host "  heartbox.keystore.base64  (text, paste into GitHub secret)"
Write-Host ""
Write-Host "=== Next: add 4 GitHub repository secrets ===" -ForegroundColor Cyan
Write-Host "Go to https://github.com/alanlin0604/HeartBox/settings/secrets/actions"
Write-Host "and add the following:"
Write-Host ""
Write-Host "  ANDROID_KEYSTORE_BASE64    -> contents of $Base64Path"
Write-Host "  ANDROID_KEYSTORE_PASSWORD  -> the password you just entered"
Write-Host "  ANDROID_KEY_ALIAS          -> heartbox"
Write-Host "  ANDROID_KEY_PASSWORD       -> the password you just entered (same)"
Write-Host ""
Write-Host "Then: GitHub Actions -> Mobile Build -> Run workflow ->"
Write-Host "      platform=android, build_type=release"
