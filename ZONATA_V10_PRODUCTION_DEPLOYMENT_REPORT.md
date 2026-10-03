# ZONATA V10 PRODUCTION DEPLOYMENT REPORT
## Enterprise Deployment Topology, Preflight Validation & Operational Topology

**Document Version**: 1.0.0  
**Target Environment**: Enterprise Production Operating Unit  
**Classification**: INFRASTRUCTURE & ARCHITECTURE SPECIFICATION  

---

## 1. Enterprise Deployment Topology

```mermaid
flowchart TD
    Client["Enterprise User / Human Owner"] -->|TLS 1.3 / HTTPS| WAF["Enterprise Ingress / TLS Termination / WAF"]
    WAF -->|Strict CORS / RBAC| Gateway["ZONATA API Gateway (Port 8080)"]
    Gateway --> Preflight["core/production_config.py<br/>(Startup Preflight Validator)"]
    Preflight --> Kernel["ZONATA Universal Control Kernel"]
    
    subgraph Core_Control_Plane["Sovereign Control Plane"]
        Kernel --> Policy["PolicyEngine & CEO Policy Matrix"]
        Policy --> Auth["AuthorityGateway & Approval Revocation"]
        Auth --> Outbox["Transactional Outbox Manager"]
    end
    
    subgraph Data_Storage_Plane["Authoritative Data Plane"]
        Outbox -->|Atomic Commit| DB[("PostgreSQL / SQLite WAL<br/>(176 Normalized Tables)")]
        DB -->|Hot Backup API| DR["Disaster Recovery Manager"]
        Kernel --> Vault["SecretVault & SovereignKeyManager"]
    end
    
    subgraph Execution_Plane["Governed Execution Plane"]
        Outbox -->|Worker Dispatch| Workers["Action Execution Workers"]
        Workers --> Firewall["AI Data Firewall<br/>(PII Redaction & Scope Filter)"]
        Firewall --> Router["ModelRouter<br/>(Approved Enterprise LLMs)"]
        Workers --> Connectors["Hospitality Production Connector"]
        Connectors --> Reconcil["External Action Reconciliation Engine"]
    end
    
    subgraph Observability_Plane["SRE & Governance Plane"]
        Kernel --> Prometheus["Prometheus Metrics (/metrics)"]
        Kernel --> Incidents["Executive Incident Engine"]
        Kernel --> Matrix["9-Level KillSwitch Matrix"]
    end
```

---

## 2. Startup Preflight & Fail-Closed Validation

The startup preflight validator (`core/production_config.py`) enforces strict gates prior to accepting HTTP ingress:

1. **DEBUG Mode Rejection**: If `ZONATA_ENV == "production"`, `DEBUG=true` halts process startup.
2. **Weak Secret Rejection**: `SECRET_VAULT_KEY` and `APPLICATION_SIGNING_KEY` must be at least 32 characters and cannot match known defaults (`changeme`, `admin`, `password`).
3. **Sovereign Root Key Requirement**: `SOVEREIGN_ROOT_KEY_ID` must be configured.
4. **Ingress CORS Restriction**: Wildcard `*` in `ALLOWED_ORIGINS` is rejected in production.
5. **Database Connectivity & Table Verification**: Actively executes ping and table discovery.

---

## 3. Deployment Artifacts
- **Configuration Schema**: [`production_config_schema.json`](file:///root/roboassistant/production_config_schema.json)
- **Environment Template**: [`production.env.example`](file:///root/roboassistant/production.env.example)
- **Preflight Engine**: [`core/production_config.py`](file:///root/roboassistant/core/production_config.py)
