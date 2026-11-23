# ADR 0020: Workload Identity and Mutual TLS Architecture

**Status:** ACCEPTED  
**Date:** 2026-11-23  
**Deciders:** Antigravity (Systems Architect), OpenCode (Reviewer & Red Team)  
**Governing Rule:** Rule 42 (Least privilege and default deny), Rule 34 (Ports and sandboxing)

---

## 1. Context and Problem Statement
ZONATA operates distributed autonomous components: API servers, Temporal workers, LangGraph executors, Google ADK squad agents, sandboxed MCP tools, and daemon schedulers. Shared API tokens or static passwords between services violate Rule 42. Every machine workload requires:
- A uniquely named, short-lived, cryptographically verifiable identity.
- Mutual TLS (mTLS) for all inter-service and cross-node communication.
- Automated certificate rotation without application restarts.

## 2. Alternatives Considered

| Approach | Technology & License | Suitability for Target Topologies | Decision |
| :--- | :--- | :--- | :--- |
| **OpenBao PKI Engine (Short-lived X.509)** | OpenBao (MPL-2.0) | Ideal for single-node Docker Compose, VM clusters, and hybrid cloud without Kubernetes dependencies. | **ADOPTED for Baseline / Standalone Deployments:** Lightweight, zero-sidecar requirement, leverages existing OpenBao infrastructure. |
| **SPIFFE / SPIRE** | CNCF Graduated (Apache-2.0) | Gold standard for Kubernetes clusters. SPIFFE Workload API issues X.509 SVIDs via Unix domain socket. | **ADOPTED for Kubernetes Deployments:** Workloads use SPIFFE CSI driver and Workload API. |
| **Service Mesh (Istio / Linkerd)** | CNCF (Apache-2.0) | Sidecar/ambient mTLS proxying. | **OPTIONAL DEFERRAL:** Adds unnecessary network overhead for small to mid-sized tenant installations. |

## 3. Decision
1. **Tiered Workload Identity Strategy:**
   - **Deployment Target A (Docker Compose / Standalone VM):** Use **OpenBao PKI Engine**. Workloads authenticate to OpenBao via short-lived AppRole tokens and receive X.509 mTLS certificates with a 1-hour TTL, renewed every 30 minutes.
   - **Deployment Target B (Kubernetes / Cloud Production):** Use **SPIFFE/SPIRE**. Workload identities follow the SPIFFE ID format:
     `spiffe://zonata.company/ns/{tenant_id}/sa/{service_name}`
2. **Identity Verification at Gateway:** All internal RPCs and agent communication must present a valid client certificate whose Subject Alternative Name (SAN) matches an authorized service identity.
3. **Revocation & Expiry:** Certificates expire in $\le 60$ minutes; immediate revocation achieved through OpenBao CRL distribution or SPIRE trust bundle updates.

## 4. Consequences
- **Positive:** Zero static passwords or long-lived API keys between services; automated cryptographic authentication of every microservice and agent worker.
- **Negative:** Requires background certificate renewal loop in Python workers.
