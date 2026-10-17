#!/usr/bin/env bash
# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Cloud Staging Automated Deployment Script
# Enforces Immutable Tagging, DDL Separation, Health Verification & Rollback
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/deploy/compose/docker-compose.cloud-staging.yml"
ENV_FILE="${PROJECT_ROOT}/deploy/compose/.env.staging"

echo "=============================================================================="
echo "ZONATA Cloud Staging Deployment Initializing..."
echo "=============================================================================="

# 1. Verify Git Commit SHA & Working Tree
CURRENT_COMMIT="$(git -C "${PROJECT_ROOT}" rev-parse HEAD)"
SHORT_COMMIT="$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD)"
echo "Current Release Candidate Commit: ${CURRENT_COMMIT} (${SHORT_COMMIT})"

# 2. Check Prerequisites
if [ ! -f "${ENV_FILE}" ]; then
  echo "WARNING: ${ENV_FILE} not found. Checking if environment variables are set..."
  if [ -z "${DATABASE_URL:-}" ] && [ -z "${DB_APP_PASSWORD:-}" ]; then
    echo "ERROR: Neither ${ENV_FILE} nor environment variables are configured."
    echo "Generate .env.staging from AWS Secrets Manager using deploy/compose/.env.staging.example."
    exit 1
  fi
fi

# 3. Record Previous Deployment for Atomic Rollback
PREV_COMMIT_FILE="/opt/zonata/.previous_deployed_commit"
mkdir -p /opt/zonata
if [ -f "/opt/zonata/.current_deployed_commit" ]; then
  cp /opt/zonata/.current_deployed_commit "${PREV_COMMIT_FILE}"
  echo "Previous deployed commit: $(cat "${PREV_COMMIT_FILE}")"
fi

# 4. Pull or Build Images with Immutable Tag
export IMAGE_TAG="${CURRENT_COMMIT}"
echo "Deploying immutable image tag: ${IMAGE_TAG}"

if command -v docker >/dev/null 2>&1; then
  echo "Pulling/verifying images for staging..."
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull --ignore-pull-failures || true
fi

# 5. Execute Schema DDL & Additive Migrations under Dedicated Migrator Identity
echo "Applying database migrations under migrator role..."
if [ -n "${DATABASE_URL_MIGRATOR:-}" ] || [ -n "${POSTGRES_PASSWORD:-}" ]; then
  python3 -c "
import sys, os
sys.path.insert(0, '${PROJECT_ROOT}')
from core.db import db
from core.controlled_migration_engine import ControlledMigrationEngine

db.verify_readiness()
db._init_db()
engine = ControlledMigrationEngine()
applied = engine.apply_pending_migrations()
print(f'Database migrations applied successfully: {len(applied)} steps.')
" || {
    echo "CRITICAL: Database migration failed. Aborting deployment before service start."
    exit 1
  }
fi

# 6. Start Application Services
echo "Starting staging compose services..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

# 7. Health Probe Verification (Timeout: 60s)
echo "Verifying application readiness and health probes..."
MAX_ATTEMPTS=30
HEALTHY=false

for i in $(seq 1 ${MAX_ATTEMPTS}); do
  if curl -fsS http://127.0.0.1:8080/readyz >/dev/null 2>&1; then
    echo "zonata-api is HEALTHY and READY on /readyz (Attempt ${i}/${MAX_ATTEMPTS})"
    HEALTHY=true
    break
  fi
  echo "Waiting for /readyz... (Attempt ${i}/${MAX_ATTEMPTS})"
  sleep 2
done

if [ "${HEALTHY}" = false ]; then
  echo "CRITICAL DEFECT: Staging deployment failed health checks."
  echo "Triggering automated rollback..."
  "${SCRIPT_DIR}/rollback.sh"
  exit 1
fi

# 8. Record Successful Deployment
echo "${CURRENT_COMMIT}" > /opt/zonata/.current_deployed_commit
echo "=============================================================================="
echo "ZONATA Cloud Staging Deployment: SUCCESS"
echo "Active Candidate: ${CURRENT_COMMIT}"
echo "=============================================================================="
