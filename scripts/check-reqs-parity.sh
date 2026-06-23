#!/usr/bin/env bash
# Verify root requirements.txt is identical to backend/requirements.txt.
#
# Both files exist for historical reasons:
#   * root  → used by render.yaml build.sh (`pip install -r ../requirements.txt`)
#   * backend/ → used by Cloud Run Python buildpack (looks at --source root)
#
# They MUST stay in sync. A drift will show up as either:
#   * Render running fine, Cloud Run pulling 10 GB nvidia-cublas (or vice versa)
#   * "It works on my deploy target but not the other one"
#
# Run locally with: bash scripts/check-reqs-parity.sh
# Or in CI:         scripts/check-reqs-parity.sh

set -euo pipefail

ROOT_FILE="requirements.txt"
BACKEND_FILE="backend/requirements.txt"

if [ ! -f "$ROOT_FILE" ]; then
    echo "✗ Missing $ROOT_FILE" >&2
    exit 1
fi
if [ ! -f "$BACKEND_FILE" ]; then
    echo "✗ Missing $BACKEND_FILE" >&2
    exit 1
fi

if diff -q "$ROOT_FILE" "$BACKEND_FILE" > /dev/null; then
    echo "✓ $ROOT_FILE and $BACKEND_FILE are identical"
    exit 0
fi

echo "✗ Drift detected between $ROOT_FILE and $BACKEND_FILE:" >&2
echo "" >&2
diff "$ROOT_FILE" "$BACKEND_FILE" >&2
echo "" >&2
echo "FIX: cp $BACKEND_FILE $ROOT_FILE  (or the other direction)" >&2
echo "     then commit." >&2
exit 1
