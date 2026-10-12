#!/usr/bin/env bash
# ==============================================================================
# ZONATA SaaS / Universal Robotic Assistant (URA)
# Localhost Runner Script
# Launches the integrated API server and web interface on localhost:8080
# ==============================================================================
set -e

PORT="${1:-8080}"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# Ensure runtime database exists to preserve baseline invariant reference
if [ ! -f "$BASE_DIR/storage/runtime.db" ]; then
    echo "[*] Initializing active runtime database from baseline..."
    cp "$BASE_DIR/storage/roboassistant.db" "$BASE_DIR/storage/runtime.db"
fi

export ZONATA_DB_PATH="$BASE_DIR/storage/runtime.db"
export APP_ENV="${APP_ENV:-development}"
export PORT="$PORT"

echo "[*] Starting ZONATA Company OS 1.0 on http://localhost:${PORT}"
echo "[*] Serving Web Application Shell from $BASE_DIR/web/"
echo "[*] Active Database: $ZONATA_DB_PATH"
echo "[*] Press Ctrl+C to stop."

exec python3 api_server.py "$PORT"
