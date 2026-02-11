#!/bin/bash
# HeartBox Smoke Test - Full Flow
# Usage: bash smoke_test.sh [BASE_URL]

BASE_URL="${1:-http://localhost:8000/api}"
PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  [PASS] $name"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $name (expected=$expected, got=$actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== HeartBox Smoke Test ==="
echo "Base URL: $BASE_URL"
echo ""

# 1. Register
echo "1. Register"
REG=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{"username":"smoketest_'$$'","email":"smoke'$$'@test.com","password":"SmokePass123!"}')
check "Register user" "201" "$REG"

# 2. Login
echo "2. Login"
LOGIN_RESP=$(curl -s -X POST "$BASE_URL/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"smoketest_'$$'","password":"SmokePass123!"}')
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access',''))" 2>/dev/null)
if [ -n "$TOKEN" ]; then
  echo "  [PASS] Login (got token)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] Login (no token)"
  FAIL=$((FAIL + 1))
fi

AUTH="Authorization: Bearer $TOKEN"

# 3. Create note
echo "3. Create note"
NOTE_RESP=$(curl -s -X POST "$BASE_URL/notes/" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"content":"Smoke test note","metadata":{"tags":["test"]}}')
NOTE_ID=$(echo "$NOTE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$NOTE_ID" ]; then
  echo "  [PASS] Create note (id=$NOTE_ID)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] Create note"
  FAIL=$((FAIL + 1))
fi

# 4. Search notes
echo "4. Search notes"
SEARCH=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$BASE_URL/notes/?search=smoke")
check "Search notes" "200" "$SEARCH"

# 5. Export data
echo "5. Export data"
EXPORT=$(curl -s -o /dev/null -w "%{http_code}" -H "$AUTH" "$BASE_URL/auth/export/")
check "Export data" "200" "$EXPORT"

# 6. Delete account
echo "6. Delete account"
DEL=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/auth/delete-account/" \
  -H "Content-Type: application/json" -H "$AUTH" \
  -d '{"password":"SmokePass123!"}')
check "Delete account" "200" "$DEL"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
exit $FAIL
