# ZONATA V4 — CORPORATE DATA PLANE ARCHITECTURE
**Multi-Tenant Isolation, Row-Level ACLs, Residency Controls, & Retention Management**

## 1. Overview
The Corporate Data Plane (`core/corporate_data_plane.py`) is the centralized repository and governance barrier for all enterprise knowledge, business documents, ERP records, and transaction logs. No AI Employee or tool may access enterprise data directly; all reads, writes, searches, and purges are mediated through the `CorporateDataGateway`.

---

## 2. Data Model & Metadata
Every corporate data object maintains immutable governance attributes:
- `object_id`: Unique identifier (e.g., `doc_xxxxxxxxxxxx`).
- `tenant_id`: Mandatory tenant isolation key.
- `company_id`: Operating subsidiary.
- `classification_level`: Sensitivity tier (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, `HIGHLY_RESTRICTED`).
- `sensitivity_categories`: Granular tags (`FINANCIAL`, `CUSTOMER_PII`, `EMPLOYEE_HR`, `SECURITY_AUTH`, `LEGAL`).
- `owner_identity_id`: Creator or designated custodian.
- `acl`: Multi-dimensional access control list (`allowed_departments`, `allowed_roles`, `allowed_identities`).
- `content_hash`: SHA-256 content integrity digest.
- `residency_region`: Geographic residency compliance (`US-EAST`, `EU-CENTRAL`, `APAC-SOUTHEAST`).
- `retention_days`: Policy-mandated retention duration.
- `legal_hold`: Boolean flag blocking destruction.
- `deletion_state`: `ACTIVE`, `MARKED_FOR_DELETION`, or `PURGED`.

---

## 3. Row-Level Security & Multi-Tenant Isolation
- Database queries mandate `tenant_id` and `company_id` filters in the `WHERE` clause.
- Access requests are validated against:
  1. Multi-tenant boundary: `TENANT_A_DATA != TENANT_B_DATA`.
  2. Deletion state: `DELETED_DATA != RETRIEVABLE_DATA`.
  3. Security clearance: Requester clearance score must be `>=` document sensitivity score.
  4. Department and Role ACL matching.
