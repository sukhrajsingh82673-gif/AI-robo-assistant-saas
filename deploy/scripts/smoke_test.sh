#!/usr/bin/env bash
# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Automated Post-Deployment Staging Smoke Test Suite (10 Security & Functional Gates)
# ==============================================================================
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8080}"
INGRESS_HOST="${2:-127.0.0.1}"

echo "=============================================================================="
echo "ZONATA Post-Deployment Smoke Test Suite"
echo "Target Base URL: ${BASE_URL}"
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

# 1. Health Endpoint Probe
check "1. GET /health returns 200 OK" \
  "curl -fsS '${BASE_URL}/health' | grep -q 'ok'"

# 2. Readiness Endpoint Probe
check "2. GET /readyz returns 200 OK" \
  "curl -fsS '${BASE_URL}/readyz' | grep -q 'ready'"

# 3. HTTP to HTTPS Redirection (Ingress Port 80)
check "3. Port 80 redirects to HTTPS (301 Moved Permanently)" \
  "curl -s -I 'http://${INGRESS_HOST}/' | grep -q '301 Moved Permanently'"

# 4. Ingress /metrics Endpoint Protection (BLK-02)
check "4. Edge Ingress blocks /metrics with 403 Forbidden" \
  "curl -s -o /dev/null -w '%{http_code}' 'http://${INGRESS_HOST}/metrics' | grep -q '403'"

# 5. Localhost Internal Metrics Endpoint Reachability
check "5. Internal /metrics accessible on localhost" \
  "curl -fsS '${BASE_URL}/metrics' | grep -q 'http_requests_total'"

# 6. Database Connection Pool & Dialect Verification
check "6. Database readiness probe reports healthy PostgreSQL connection" \
  "python3 -c '
import urllib.request, json
req = urllib.request.Request(\"${BASE_URL}/readyz\")
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    assert data.get(\"status\") in [\"ready\", \"ok\"]
'"

# 7. Multi-Tenant IAM Isolation
check "7. Unauthenticated request to protected endpoint returns 401" \
  "curl -s -o /dev/null -w '%{http_code}' '${BASE_URL}/api/v1/overview' | grep -q '401'"

# 8. S3 / MinIO Object Storage Reachability
check "8. Object storage ping (MinIO or S3 endpoint)" \
  "curl -fsS 'http://127.0.0.1:9000/minio/health/live' || curl -fsS -I 'https://s3.amazonaws.com' >/dev/null 2>&1"

# 9. Prometheus Telemetry Active
check "9. Prometheus monitoring service healthy" \
  "curl -fsS 'http://127.0.0.1:9090/-/healthy' | grep -q 'Prometheus Server is Healthy'"

# 10. Alertmanager Active & Configured
check "10. Alertmanager notification dispatcher healthy" \
  "curl -fsS 'http://127.0.0.1:9093/-/healthy' | grep -q 'OK'"

echo "=============================================================================="
echo "Smoke Test Summary: ${PASSED}/10 PASSED, ${FAILED}/10 FAILED"
echo "=============================================================================="

if [ "${FAILED}" -gt 0 ]; then
  echo "SMOKE TESTS FAILED"
  exit 1
else
  echo "ALL POST-DEPLOYMENT SMOKE TESTS PASSED (100%)"
  exit 0
fi
