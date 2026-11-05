# ZONATA V3 — Real Infrastructure Deployment Report

## 1. Executive Summary
- **Target Topology:** Multi-tenant, distributed, containerized Linux/Kubernetes runtime.
- **Classification:** `REAL_LOCAL_INFRASTRUCTURE`
- **Cluster Components:**
  - Control Plane API Server (`Dockerfile.api`, 3 replicas)
  - Asynchronous Execution Workers (`Dockerfile.worker`, 4-50 autoscaling replicas)
  - HA Supervisor Coordinator (`Dockerfile.supervisor`, 2 active-passive replicas)
  - Database Migration Job (`Dockerfile.migration`, pre-deployment schema gate)
- **Status:** **PROVEN ON LOCAL & K8S TOPOLOGY (CONDITIONAL ON LIVE SAAS CREDENTIALS)**

---

## 2. Process Architecture & Topology
```
                     +---------------------------------------+
                     |           NGINX Ingress               |
                     |  TLS Termination + Rate Limit + CORS  |
                     +-------------------+-------------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
             +-------------------+               +-------------------+
             |  zonata-api-1     |               |  zonata-api-2     |
             |  (Port 8080)      |               |  (Port 8080)      |
             +---------+---------+               +---------+---------+
                       |                                   |
                       +-----------------+-----------------+
                                         |
                +------------------------+------------------------+
                |                        |                        |
                v                        v                        v
      +------------------+     +------------------+     +------------------+
      |  Database Engine |     | Distributed Redis|     | Supervisor HA    |
      |  (Postgres/WAL)  |     | Coordination Bus |     | (Leader/Standby) |
      +--------+---------+     +--------+---------+     +------------------+
               |                        |
               +-----------+------------+
                           |
             +-------------+-------------+
             |                           |
             v                           v
   +-------------------+       +-------------------+
   |  zonata-worker-1  |       |  zonata-worker-2  |
   |  (Action Bus)     |       |  (Action Bus)     |
   +-------------------+       +-------------------+
```

---

## 3. Container Specification & Hardening
- **Base OS:** Linux Debian 12 (Bookworm) `python:3.12-slim`
- **User Execution:** Non-root, dedicated `zonata:zonata` user (`UID 10001, GID 10001`).
- **Filesystem Permissions:** Read-only root filesystem compatible with dedicated `/app/storage` writable volumes for WAL journals and evidence hashes.
- **Health Probing:** Liveness (`/livez`) and readiness (`/readyz`) probes configured on all HTTP ingress points.

---

## 4. Startup & Bootstrap Sequence
1. **Config Validation:** `core.production_config.ProductionConfig` runs fail-closed environment validation.
2. **Schema Gate:** One-shot Kubernetes Job executes database migration checks against `DatabaseEngine`.
3. **Control Plane Ingress:** API instances bind non-privileged ports and begin serving stateless token-authenticated routes.
4. **Worker Initialization:** Workers connect to `AsynchronousCommandBus` and begin atomic claim loops.
5. **Supervisor Election:** Active-passive leader lease acquired via distributed lock with automated heartbeats.

---

## 5. Verification Classification
- **Container Build & Manifests:** `REAL_LOCAL_INFRASTRUCTURE`
- **Process Spawning & Dual-Node Binding:** `REAL_LOCAL_INFRASTRUCTURE`
- **External SaaS Endpoints:** `BLOCKED — CREDENTIALS REQUIRED`
