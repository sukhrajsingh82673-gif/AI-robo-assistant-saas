# ZONATA V3 — Kubernetes Manifests & Deployment Validation

## 1. Cluster Manifest Inventory
The production Kubernetes infrastructure for ZONATA is located in the `k8s/` directory:
- `k8s/00-namespace.yaml`: Restricted PodSecurity namespace `zonata-system`
- `k8s/01-configmap.yaml`: Distributed configuration settings & defaults
- `k8s/02-secrets.yaml`: Template for encrypted vault credentials
- `k8s/03-api-deployment.yaml`: Control Plane API deployment (3 replicas, RollingUpdate)
- `k8s/04-worker-deployment.yaml`: Command execution worker deployment (4 replicas)
- `k8s/05-supervisor-deployment.yaml`: High-Availability Supervisor deployment (2 replicas)
- `k8s/06-services.yaml`: Internal ClusterIP service definitions
- `k8s/07-ingress.yaml`: NGINX ingress with TLS termination and rate limits
- `k8s/08-hpa.yaml`: HorizontalPodAutoscaler definitions for API and Workers
- `k8s/09-pdb.yaml`: PodDisruptionBudgets guaranteeing high availability during cluster drains
- `k8s/10-networkpolicy.yaml`: Zero-trust network segmentation and egress controls
- `k8s/11-migration-job.yaml`: Pre-deployment database migration and validation job

---

## 2. Hardening & Compliance Verification
| Control Dimension | Specification | Compliance Status |
|---|---|---|
| **Non-Root Execution** | `runAsNonRoot: true`, `runAsUser: 10001` | PASS |
| **Capability Dropping** | `capabilities.drop: ["ALL"]` | PASS |
| **Privilege Escalation** | `allowPrivilegeEscalation: false` | PASS |
| **Seccomp Profile** | `seccompProfile.type: RuntimeDefault` | PASS |
| **Zero Downtime Upgrade** | `maxSurge: 1`, `maxUnavailable: 0` | PASS |
| **Pod Disruption Budget** | `minAvailable: 2` (API), `minAvailable: 1` (Supervisor) | PASS |
| **Network Isolation** | Ingress restricted to Ingress Controller; Egress restricted to essential ports | PASS |

---

## 3. Operational Classification
- **Manifest Syntax & Schema Compliance:** `REAL_LOCAL_INFRASTRUCTURE`
- **Live Cloud Kubernetes Cluster (EKS / GKE):** `BLOCKED — CLUSTER ACCESS REQUIRED`
