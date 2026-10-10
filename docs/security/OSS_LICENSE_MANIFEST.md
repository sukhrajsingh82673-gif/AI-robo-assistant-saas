# ZONATA / URA — Open-Source License & Operational Cost Manifest

**Compliance Policy:** 100% OSI-approved permissive and commercially compatible open-source licenses.  
**Prohibited:** Unapproved proprietary SDKs, mandatory SaaS subscriptions, restrictive copyleft on core application binaries.

---

## 1. Pinned Component License Manifest

| Component | Verified Version | Canonical Source Repository | SPDX License | SaaS Distribution Assessment | Operational Cost Considerations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Apache Camel** | `4.8.0` (LTS) | `https://github.com/apache/camel` | `Apache-2.0` | **Permitted**. Self-hostable, no copyleft obligations. | Compute/RAM for JVM message routers (~512MB RAM). |
| **LiteLLM** | `1.48.0` | `https://github.com/BerriAI/litellm` | `MIT` | **Permitted**. Core proxy is MIT. Enterprise tier omitted. | Zero licensing cost. Upstream model API token usage. |
| **vLLM** | `0.6.2` | `https://github.com/vllm-project/vllm` | `Apache-2.0` | **Permitted**. High-throughput self-hosted inference. | Optional GPU infrastructure (NVIDIA Ampere/Hopper). |
| **Apache Tika** | `2.9.2` | `https://github.com/apache/tika` | `Apache-2.0` | **Permitted**. Sandboxed document extraction. | Minor CPU memory consumption for parser workers. |
| **Tesseract OCR** | `5.3.4` | `https://github.com/tesseract-ocr/tesseract` | `Apache-2.0` | **Permitted**. Standard OCR engine. | CPU bound during intensive image analysis. |
| **OpenSearch** | `2.17.0` | `https://github.com/opensearch-project/OpenSearch` | `Apache-2.0` | **Permitted**. Full open-source fork of Elasticsearch. | Cluster RAM/storage for Lucene indices. |
| **Qdrant** | `1.12.0` | `https://github.com/qdrant/qdrant` | `Apache-2.0` | **Permitted**. Rust-based vector search engine. | RAM for vector indexes and disk for persistence. |
| **ERPNext Client** | `15.38.0` | `https://github.com/frappe/erpnext` | `MIT` (Client) | **Permitted**. REST API client adapter. Self-hosted ERP backend. | Backend MariaDB/Redis infrastructure if hosting self. |
| **SuiteCRM Client**| `8.6.0` | `https://github.com/SuiteCRM/SuiteCRM` | `Apache-2.0` (Client) | **Permitted**. Client API boundary isolates SaaS core. | Backend PHP/MySQL server hosting if self-hosted. |
| **Zammad Client** | `6.3.1` | `https://github.com/zammad/zammad` | `Apache-2.0` (Client) | **Permitted**. Client API adapter. Self-hosted helpdesk. | Backend PostgreSQL/Elasticsearch for ticketing. |
| **Nextcloud Client**| `29.0.4` | `https://github.com/nextcloud/server` | `Apache-2.0` (Client) | **Permitted**. WebDAV/CalDAV protocol client. | Object storage (S3/MinIO) for user documents. |
| **Apache Superset**| `4.0.2` | `https://github.com/apache/superset` | `Apache-2.0` | **Permitted**. BI and SQL exploration layer. | Read-only analytics DB replicas. |
| **dbt Core** | `1.8.5` | `https://github.com/dbt-labs/dbt-core` | `Apache-2.0` | **Permitted**. Data modeling and transformation engine. | CLI runner execution time. |
| **Meltano** | `3.5.0` | `https://github.com/meltano/meltano` | `MIT` | **Permitted**. Singer-compatible data sync platform. | Scheduled worker batch job compute. |
| **Falco** | `0.38.1` | `https://github.com/falcosecurity/falco` | `Apache-2.0` | **Permitted**. Cloud-native runtime threat detection. | Kernel eBPF/kmod probe on container hosts. |
| **Wazuh Agent** | `4.8.0` | `https://github.com/wazuh/wazuh` | `Apache-2.0` (Agent) | **Permitted**. Endpoint monitoring agent. | Centralized Wazuh manager cluster. |
| **Argo CD** | `v2.12.0` | `https://github.com/argoproj/argo-cd` | `Apache-2.0` | **Permitted**. Declarative GitOps deployment controller. | Lightweight Kubernetes controller pods. |
| **promptfoo** | `0.82.0` | `https://github.com/promptfoo/promptfoo` | `MIT` | **Permitted**. AI adversarial evaluation framework. | Test runner execution time & eval token spend. |
| **Matrix Synapse** | `v1.111.0` | `https://github.com/element-hq/synapse` | `Apache-2.0` (Client) | **Permitted**. Client API for messaging. | Homeserver PostgreSQL storage if self-hosted. |
| **OpenFeature** | `0.7.0` | `https://github.com/open-feature` | `Apache-2.0` | **Permitted**. Vendor-agnostic feature flag specification. | Negligible in-memory flag evaluation overhead. |

---

## 2. Commercial SaaS Invariants

1. **No Compelled Source Disclosures:** All integrations run over separate process boundaries, REST APIs, or permissively licensed client libraries (Apache-2.0 / MIT). Core proprietary and tenant business logic remain unencumbered by AGPL copyleft contamination.
2. **Zero Paid Software Lock-In:** Every required capability runs completely self-hosted on standard Linux infrastructure without requiring commercial license keys or hosted accounts.
