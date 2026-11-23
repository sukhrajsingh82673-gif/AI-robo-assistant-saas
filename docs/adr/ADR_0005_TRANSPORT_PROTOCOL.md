# ADR 0005: Cloud-Host Transport and Framing Protocol

**Status:** Accepted  
**Date:** 2026-11-22  
**Context:** OpenCode Step 3A / 3B / 3D — Hands: Host communication & transport  
**Deciders:** ZONATA Systems Architecture  

---

## 1. Context and Problem Statement

The host agent runs on the user's computer behind corporate firewalls, NATs, and dynamic home IPs. The cloud must securely transmit action requests to the host, and the host must stream telemetry, perception events, and human intervention requests back to the cloud.

Key constraints:
- **Rule 23 (Outbound-Only):** The host must never listen on open inbound ports.
- **Mutual Authentication:** Cloud must verify host identity; host must verify cloud authenticity.
- **Anti-Replay & Integrity:** Every message must be cryptographically signed with monotonic sequence numbers and nonces.

---

## 2. Evaluation of Alternatives

### Option 1: Inbound HTTP/gRPC Server on Host
- **Rejected Reasons:** Requires opening inbound firewall ports, NAT port forwarding, or public IP assignment, exposing user computers to unauthorized port scanning and network intrusion. Completely incompatible with mobile or corporate networks.

### Option 2: Long-Polling HTTP Requests
- **Rejected Reasons:** High latency, HTTP header overhead, and clumsy bidirectional event streaming. Inadequate for real-time human supervisor interruption and emergency kill-switch halts.

### Option 3: Reverse SSH Tunnels
- **Rejected Reasons:** Requires provisioning and managing individual SSH users, port forwarding maps, and key rotation per device. Fails clean multi-tenant SaaS scaling.

### Option 4: Outbound TLS WebSocket with Signed Envelope Framing (Chosen)
- **Licence:** Standard WebSockets (RFC 6455) / TLS 1.3.
- **Architecture:** Host agent establishes outbound secure WebSocket (`wss://<tenant-subdomain>.zonata.internal/host/ws`).
- **Framing Protocol:**
  - Every payload is encapsulated in a signed envelope containing:
    `{ device_id, tenant_id, sequence_no, timestamp_utc, nonce, payload, signature }`.
  - Signature is computed with the host's private Ed25519 key (pairing public key registered during step-up pairing).
  - Out-of-order sequence numbers, expired timestamps (>30s drift), or replayed nonces are rejected immediately.

---

## 3. Decision

We choose **Option 4: Outbound TLS WebSocket with Signed Envelope Framing**.

### Enforcement Invariants:
1. Cloud can only propose actions over the WebSocket; the host agent's local engine independently evaluates the action against active human grants.
2. If connection is dropped or ping heartbeat missed (>15s), host agent automatically halts active autonomous automation and reverts to safe state.
