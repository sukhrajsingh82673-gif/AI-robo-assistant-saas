#!/usr/bin/env bash
# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Free-Tier Live Staging Smoke Test Suite (Render / Cloud Run)
# Validates public HTTPS endpoint, database connectivity, auth, and edge security
# ==============================================================================
set -euo pipefail

TARGET_URL="${1:-}"
METRICS_TOKEN="${2:-}"

if [ -z "${TARGET_URL}" ]; then
  echo "Usage: $0 <https://your-app.onrender.com> [METRICS_AUTH_TOKEN]"
  echo "Example: $0 https://zonata-staging.onrender.com my_secret_token"
  exit 1
fi

TARGET_URL="${TARGET_URL%/}" # Strip trailing slash

echo "=============================================================================="
echo "ZONATA Free-Tier Staging Smoke Test"
echo "Target Endpoint: ${TARGET_URL}"
echo "=============================================================================="

PASSED=0
FAILED=0

check() {
  local desc="$1"
  local cmd="$2"
  echo -n "Gate: ${desc} ... "
  if eval "${cmd}" >/dev/null 2>&1; then
    echo "PASS"
    PASSED=$((PASSED + 1))
  else
    echo "FAIL"
    FAILED=$((FAILED + 1))
  fi
}

# 1. Health Probe
check "1. GET /health returns 200 OK" \
  "curl -fsS '${TARGET_URL}/health' | grep -qiE 'ok|healthy'"

# 2. Database Readiness Probe
check "2. GET /readyz confirms PostgreSQL database readiness" \
  "curl -fsS '${TARGET_URL}/readyz' | grep -qiE 'ready|healthy'"

# 3. Public Edge Metrics Restriction (BLK-02)
check "3. Unauthenticated GET /metrics is blocked (403 Forbidden)" \
  "[ \$(curl -s -o /dev/null -w '%{http_code}' '${TARGET_URL}/metrics') -eq 403 ]"

# 4. Authenticated Metrics Access (if token provided)
if [ -n "${METRICS_TOKEN}" ]; then
  check "4. Authenticated GET /metrics returns Prometheus format" \
    "curl -fsS -H 'Authorization: Bearer ${METRICS_TOKEN}' '${TARGET_URL}/metrics' | grep -q 'http_requests_total'"
else
  echo "Gate: 4. Authenticated /metrics access ... SKIPPED (No token provided)"
fi

# 5. Multi-Tenant IAM Isolation
check "5. Unauthenticated request to /api/v1/overview returns 401" \
  "[ \$(curl -s -o /dev/null -w '%{http_code}' '${TARGET_URL}/api/v1/overview') -eq 401 ]"

# 6. CSRF Token Endpoint Active
check "6. GET /api/auth/csrf returns valid token" \
  "curl -fsS '${TARGET_URL}/api/auth/csrf' | grep -q 'csrf_token'"

# 7. TLS Transport Security (HTTPS Enforcement)
check "7. Scheme is HTTPS" \
  "[[ '${TARGET_URL}' == https://* ]]"

# 8. Neon Cloud Services Integration
check "8. GET /api/v1/neon/services confirms Neon integration" \
  "curl -fsS '${TARGET_URL}/api/v1/neon/services' | grep -q 'postgres'"

# 9. Neon Serverless Function Invocation
check "9. GET /api/v1/neon/functions/hello confirms function proxy" \
  "curl -fsS '${TARGET_URL}/api/v1/neon/functions/hello' | grep -q 'Hello from Neon Functions'"

echo "=============================================================================="
echo "Smoke Test Summary: ${PASSED} PASSED, ${FAILED} FAILED"
echo "=============================================================================="

if [ "${FAILED}" -gt 0 ]; then
  echo "STAGING VERIFICATION: FAILED"
  exit 1
else
  echo "ALL FREE-TIER STAGING GATES PASSED (100%)"
  exit 0
fi
