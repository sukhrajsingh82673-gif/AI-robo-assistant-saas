# ZONATA V3 — Enterprise Capacity & Resource Sizing Model

## 1. Plan Tiers & Resource Allocation
| Subscription Plan Tier | Max Concurrent Agents | Max Concurrent Missions | Max Tokens / Min | Max Tool Calls / Min | Browser Concurrency | OpenHands Concurrency | Daily Spend Cap |
|---|---|---|---|---|---|---|---|
| **DEV** | 10 | 5 | 50,000 | 100 | 2 | 2 | $100 |
| **STARTER** | 25 | 10 | 100,000 | 250 | 5 | 5 | $500 |
| **PROFESSIONAL** | 100 | 25 | 500,000 | 1,000 | 15 | 10 | $2,500 |
| **ENTERPRISE** | 500 | 100 | 2,000,000 | 5,000 | 50 | 25 | $10,000 |
| **HYPERSCALE** | 5,000 | 1,000 | 10,000,000 | 25,000 | 200 | 100 | $50,000 |
| **UNLIMITED** | Scalable Pool | Scalable Pool | Uncapped | Uncapped | Dedicated Cluster | Dedicated Cluster | Custom SLA |

---

## 2. Infrastructure Sizing Guidance
### Small Deployment (Up to 250 Active Agents)
- **API Pods:** 3 replicas (0.5 vCPU, 512 MB RAM each)
- **Worker Pods:** 4 replicas (1 vCPU, 1 GB RAM each)
- **HA Supervisor:** 2 replicas (0.25 vCPU, 256 MB RAM each)
- **Database:** PostgreSQL 2 vCPU, 4 GB RAM, 100 GB SSD (or local SQLite WAL engine)

### Enterprise Deployment (Up to 5,000 Active Agents)
- **API Pods:** 10-20 replicas (2 vCPU, 2 GB RAM each)
- **Worker Pods:** 25-50 replicas (4 vCPU, 4 GB RAM each)
- **HA Supervisor:** 2-3 replicas (1 vCPU, 1 GB RAM each)
- **Database:** Managed PostgreSQL (Aurora / RDS) 8 vCPU, 32 GB RAM with Read Replicas
- **Coordination:** Redis Enterprise Cluster (3 nodes, multi-AZ)
