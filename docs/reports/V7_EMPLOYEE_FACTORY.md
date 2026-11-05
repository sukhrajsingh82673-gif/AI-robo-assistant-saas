# ZONATA V7 — Employee Factory V7 & 24-Stage Provisioning Pipeline
**Document ID:** ZONATA-V7-FACTORY-005  
**Classification:** WORKFORCE PROVISIONING & SECURITY EVALUATION SPECIFICATION  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. 24-Stage Governed Provisioning Pipeline

The `EmployeeFactoryV7` (`core/employee_factory_v7.py`) transforms an approved `EmployeeTemplate` into an operational `AIEmployee` instance. It executes an observable, fail-closed 24-stage pipeline where every stage must pass before activation:

| Stage # | Pipeline Stage | Operational Verification |
| :--- | :--- | :--- |
| **1** | `SPECIFICATION_VALIDATION` | Checks that role, responsibilities, and objectives are well-formed. |
| **2** | `TENANT_VALIDATION` | Confirms tenant existence and isolation boundaries. |
| **3** | `ORGANIZATION_VALIDATION` | Verifies company ID and organizational department assignment. |
| **4** | `ROLE_VALIDATION` | Confirms job family and non-empty duty list. |
| **5** | `SOP_VALIDATION` | Validates compiled SOP references and rule provenance. |
| **6** | `KPI_VALIDATION` | Validates KPI targets, units, thresholds, and data sources. |
| **7** | `KRA_VALIDATION` | Validates core responsibilities, workflows, and tools. |
| **8** | `KNOWLEDGE_VALIDATION` | Verifies allowed data classifications (`INTERNAL`, `CONFIDENTIAL`). |
| **9** | `TOOL_VALIDATION` | Confirms requested tools exist in the system tool fabric. |
| **10** | `AUTHORITY_VALIDATION` | Checks risk ceiling, spending limit, and human approval rules. |
| **11** | `AUTONOMY_VALIDATION` | Enforces Autonomy Level (0 through 5) constraints. |
| **12** | `BUDGET_VALIDATION` | Verifies initial allocated financial budget. |
| **13** | `SECURITY_EVALUATION` | Evaluates prompt injection barriers, container sandbox requirements. |
| **14** | `POLICY_EVALUATION` | Evaluates against ABAC policy engine. |
| **15** | `PROMPT_CONTEXT_COMPILATION` | Compiles discrete identity, role, and constraint context blocks. |
| **16** | `CAPABILITY_BINDING` | Binds capabilities to the dynamic registry. |
| **17** | `MEMORY_BINDING` | Partitions working and long-term memory partitions. |
| **18** | `MANAGER_ASSIGNMENT` | Assigns supervisor (e.g. COO, CTO, CMO, or AI CEO). |
| **19** | `COLLABORATION_CONFIGURATION`| Configures preferred specialist colleagues. |
| **20** | `EVALUATION_GATE` | Executes simulated pre-deployment evaluation test. |
| **21** | `CRYPTOGRAPHIC_SIGNING` | Signs template specification with HMAC-SHA256 signature. |
| **22** | `APPROVAL_GATE` | Validates human owner or CEO authorization signature. |
| **23** | `PROVISIONING` | Inserts record into `ai_employees` registry. |
| **24** | `ACTIVATION` | Advances lifecycle state machine to `ACTIVE` and registers onboarding. |

---

## 2. Onboarding Artifact Generation

Upon successful completion of Stage 24, the factory generates a structured onboarding certificate persisted in `employee_factory_provisions` and commits an immutable event to the Merkle ledger (`AI_EMPLOYEE_PROVISIONED_FROM_TEMPLATE`).
