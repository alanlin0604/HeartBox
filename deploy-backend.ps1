# Deploy HeartBox backend to Cloud Run.
#
# Why this script exists (vs `gcloud run deploy --source .`):
# Cloud Build's buildkit defaults emit an OCI manifest list with an
# attestation manifest. Cloud Run cannot import this format, surfacing as
# the cryptic "Container import failed" error. Workaround: build locally
# with `docker buildx build --provenance=false` (single Docker manifest v2)
# and deploy by image digest.
#
# Prereqs: Docker Desktop running, gcloud authenticated, docker auth'd to
# the Artifact Registry repo (`gcloud auth configure-docker asia-east1-docker.pkg.dev`).

$ErrorActionPreference = "Stop"

$Project = "heartbox-tw"
$Region = "asia-east1"
$Service = "heartbox-api"
$Image = "asia-east1-docker.pkg.dev/$Project/heartbox/$Service"
$Tag = Get-Date -Format "yyyyMMdd-HHmmss"
$FullTag = "${Image}:$Tag"

Set-Location $PSScriptRoot

Write-Host "=== Build (single manifest, no provenance/attestation) ===" -ForegroundColor Cyan
docker buildx build --platform linux/amd64 --provenance=false `
    --output "type=image,name=$FullTag,push=true" .
if ($LASTEXITCODE -ne 0) { throw "docker build/push failed" }

Write-Host "=== Resolve pushed digest ===" -ForegroundColor Cyan
$Digest = (docker buildx imagetools inspect $FullTag --format '{{json .Manifest.Digest}}').Trim('"')
$ImageByDigest = "$Image@$Digest"
Write-Host "Image: $ImageByDigest" -ForegroundColor Green

Write-Host "=== Deploy revision (no traffic shift yet) ===" -ForegroundColor Cyan
# --min-instances=1 keeps one container warm so the first API call after an
# idle period doesn't pay the ~3 s cold-start tax. At our scale this costs
# about $5/month and removes the most visible UX regression for new users.
# --cpu-boost gives the cold container 2x CPU during startup so Django boots
# faster on the rare second cold start (scale-up beyond 1 instance).
gcloud run deploy $Service `
    --image $ImageByDigest --region $Region --project $Project `
    --no-traffic --memory 4Gi --min-instances 1 --cpu-boost --quiet
if ($LASTEXITCODE -ne 0) { throw "gcloud run deploy failed" }

$NewRevision = (gcloud run services describe $Service --region $Region `
    --format="value(status.latestCreatedRevisionName)" --project $Project).Trim()

# Marker file consumed by verify-prod-readiness.ps1's "deploy stale" check.
# Earlier the check compared against this script's LastWriteTime, which never
# changed when the user ran the script, so the check always flagged the
# deploy as stale. Writing a dedicated marker is unambiguous.
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
"Deploy verified at $Stamp (revision: $NewRevision)" | Out-File -FilePath ".last-backend-deploy" -Encoding ascii

Write-Host ""
Write-Host "New revision: $NewRevision" -ForegroundColor Green
Write-Host ""
Write-Host "Verify health, then run:" -ForegroundColor Yellow
Write-Host "  gcloud run services update-traffic $Service --region $Region --to-revisions=${NewRevision}=100"
