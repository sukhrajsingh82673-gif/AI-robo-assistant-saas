#!/usr/bin/env bash
# =============================================================================
# ZONATA / RoboAssistant — Embedded Local LLM Installer
# =============================================================================
# Installs a fully local, zero-cost, zero-egress language model so the platform
# is intelligent out of the box without any API key.
#
# What it does:
#   1. Installs Ollama (Linux, no root required if using the user install).
#   2. Starts the Ollama service on 127.0.0.1:11434.
#   3. Pulls a small instruction-tuned model (default: qwen2.5:1.5b, ~1 GB).
#   4. Verifies the model responds.
#
# Usage:
#   ./scripts/install_embedded_llm.sh              # install everything
#   ./scripts/install_embedded_llm.sh --check      # verify only
#   ZONATA_EMBEDDED_MODEL=qwen2.5:3b ./scripts/install_embedded_llm.sh
#
# After installation the platform automatically prefers this local model when
# Settings → AI Models & Providers is set to "Embedded Free (zero-config)" or
# "Local Self-Hosted (Ollama / vLLM)".
# =============================================================================
set -euo pipefail

MODEL="${ZONATA_EMBEDDED_MODEL:-qwen2.5:1.5b}"
BASE_URL="${OLLAMA_HOST:-http://127.0.0.1:11434}"
BASE_URL="${BASE_URL%/}"

log()  { printf '\033[1;34m[embedded-llm]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[embedded-llm]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[embedded-llm]\033[0m %s\n' "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

check_ollama() {
  have ollama || return 1
  curl -sf -m 3 "${BASE_URL}/api/tags" >/dev/null 2>&1
}

check_model() {
  curl -sf -m 3 "${BASE_URL}/api/tags" 2>/dev/null \
    | grep -q "\"${MODEL%%:*}" || return 1
}

probe() {
  log "Probing ${MODEL} ..."
  local out
  out="$(curl -sf -m 120 -X POST "${BASE_URL}/api/chat" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${MODEL}\",\"stream\":false,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly: READY\"}],\"options\":{\"num_predict\":12}}" \
    2>/dev/null || true)"
  if printf '%s' "$out" | grep -qi 'READY'; then
    log "Model responded correctly."
    return 0
  fi
  warn "Model probe did not return READY. Response: ${out:0:200}"
  return 1
}

install_ollama() {
  log "Installing Ollama (user-local, no sudo)..."
  if have curl; then
    curl -fsSL https://ollama.com/install.sh | sh
  elif have wget; then
    wget -qO- https://ollama.com/install.sh | sh
  else
    fail "Neither curl nor wget is available; install Ollama manually from https://ollama.com/download"
  fi
}

start_service() {
  if curl -sf -m 2 "${BASE_URL}/api/tags" >/dev/null 2>&1; then
    return 0
  fi
  log "Starting Ollama service..."
  if have systemctl && systemctl --user list-unit-files 2>/dev/null | grep -q '^ollama'; then
    systemctl --user start ollama 2>/dev/null || true
  fi
  if ! curl -sf -m 2 "${BASE_URL}/api/tags" >/dev/null 2>&1; then
    # Background fallback (works in containers without systemd).
    nohup ollama serve >"${TMPDIR:-/tmp}/ollama-serve.log" 2>&1 &
    for _ in $(seq 1 30); do
      sleep 1
      curl -sf -m 2 "${BASE_URL}/api/tags" >/dev/null 2>&1 && break
    done
  fi
  curl -sf -m 2 "${BASE_URL}/api/tags" >/dev/null 2>&1 \
    || fail "Ollama did not start. See ${TMPDIR:-/tmp}/ollama-serve.log"
}

main() {
  if [[ "${1:-}" == "--check" ]]; then
    check_ollama || fail "Ollama is not reachable at ${BASE_URL}"
    check_model  || fail "Model ${MODEL} is not pulled"
    probe || exit 1
    log "Embedded LLM is ready."
    exit 0
  fi

  have curl || fail "curl is required."

  if ! have ollama; then
    install_ollama
  else
    log "Ollama already installed."
  fi

  start_service

  if check_model; then
    log "Model ${MODEL} already present."
  else
    log "Pulling ${MODEL} (this downloads roughly 1 GB)..."
    ollama pull "${MODEL}"
  fi

  probe || fail "Installation finished but the model probe failed."

  cat <<EOF

Embedded LLM is ready.

  Endpoint : ${BASE_URL}
  Model    : ${MODEL}

No API key is required and no prompt leaves this machine.
Set these in Settings → AI Models & Providers if you want to pin it:

  Provider : Local Self-Hosted (Ollama / vLLM)
  Base URL : ${BASE_URL}
  Model    : ${MODEL}

EOF
}

main "$@"
