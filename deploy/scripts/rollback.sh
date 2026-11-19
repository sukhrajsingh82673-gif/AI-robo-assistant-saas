#!/usr/bin/env bash
# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Automated Rollback Script
# Restores previous immutable image tag and verifies service restoration
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/deploy/compose/docker-compose.cloud-staging.yml"
ENV_FILE="${PROJECT_ROOT}/deploy/compose/.env.staging"
PREV_COMMIT_FILE="/opt/zonata/.previous_deployed_commit"

echo "=============================================================================="
echo "EMERGENCY ROLLBACK INITIATED"
echo "=============================================================================="

if [ ! -f "${PREV_COMMIT_FILE}" ]; then
  echo "ERROR: Previous deployed commit file (${PREV_COMMIT_FILE}) not found."
  echo "Manual operator intervention required."
  exit 1
fi

PREV_COMMIT="$(cat "${PREV_COMMIT_FILE}")"
echo "Target Rollback Commit SHA: ${PREV_COMMIT}"

# Export Rollback Image Tag
export IMAGE_TAG="${PREV_COMMIT}"

# Stop potentially degraded services
echo "Stopping currently failing services..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" down --remove-orphans || true

# Relaunch with previous immutable image tag
echo "Restarting services with previous known-good tag: ${PREV_COMMIT}..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

# Verify health probes
echo "Probing rollback health on /readyz..."
MAX_ATTEMPTS=20
ROLLBACK_OK=false

for i in $(seq 1 ${MAX_ATTEMPTS}); do
  if curl -fsS http://127.0.0.1:8080/readyz >/dev/null 2>&1; then
    echo "Rollback instance is HEALTHY on /readyz (Attempt ${i}/${MAX_ATTEMPTS})"
    ROLLBACK_OK=true
    break
  fi
  sleep 2
done

if [ "${ROLLBACK_OK}" = true ]; then
  echo "${PREV_COMMIT}" > /opt/zonata/.current_deployed_commit
  echo "Rollback completed successfully. Active version: ${PREV_COMMIT}"
  exit 0
else
  echo "CRITICAL: Rollback failed health verification. Operator escalation required."
  exit 2
fi
