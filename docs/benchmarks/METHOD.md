# GDPval Blinded Comparison Methodology & TheAgentCompany Benchmark Framework

## 1. Overview
This specification defines the rigorous evaluation framework used to validate the autonomous capabilities of the AI Robo-Assistant SaaS platform across all 10 corporate departments.

The benchmark methodology synthesizes two premier evaluation standards:
1. **TheAgentCompany Deterministic Checkpoint Scoring:** Evaluates multi-step departmental tasks against 5 sequential, deterministic verification checkpoints (CP1 to CP5).
2. **GDPval Blinded Pairwise Comparison:** Conducts randomized, blinded side-by-side evaluations between agent-generated deliverables and expert human deliverables.

---

## 2. Checkpoint Verification Pyramid (CP1 – CP5)

For each golden benchmark task, execution proceeds through a deterministic 5-stage verification ladder:

| Checkpoint | Gate Name | Verification Criteria | Enforcement Invariant |
| :--- | :--- | :--- | :--- |
| **CP1** | Task Intake & Schema Validation | Validates input parameters against canonical department models (`tenant_id`, `company_id`, payload typing). | Pydantic model validation |
| **CP2** | Policy & Constraint Verification | Checks regulatory boundaries, sanctions lists, statutory rates, and approval thresholds. | Rules 60, 61, 62, 63, 64 |
| **CP3** | Core Execution & State Mutation | Executes domain business logic (e.g., BOM explosion, AP match, payroll computation). | Domain engine execution |
| **CP4** | Independent Re-Read Verification | Performs a fresh, independent read of the modified entity to verify storage persistence. | Rule 59 Invariant |
| **CP5** | Audit Attestation & Provenance | Verifies cryptographic seal, audit log emission, and metric tap recording. | Rule 41, 65, and Telemetry |

A task is scored as **100% PASS** if and only if all 5 checkpoints pass without failure or bypassed security invariants.

---

## 3. Departmental Benchmark Coverage (250 Golden Tasks)

The benchmark suite defines 25 distinct golden tasks for each of the 10 departmental domains:

1. **Finance & Accounting (25 Tasks):** AP 3-way matching, discrepancy holds, multi-format bank statement parsing (CAMT.053, MT940, CSV), 2-phase bank reconciliation, vendor fraud 72h holds, statutory India GST E-Invoicing (IRN computation), month-end close cutoff, intercompany eliminations, trial balance debit=credit validation, immutable period locking.
2. **Sales & CRM (25 Tasks):** Multi-key lead deduplication (email, phone, domain), Rule 64 outreach consent verification, quote pricing with margin protection, discount threshold enforcement (>20% human gateway), bounded automated negotiation rounds, multi-adapter CRM synchronizations (Native, Twenty, HubSpot).
3. **Customer Support & Helpdesk (25 Tasks):** Multi-label ticket classification (urgency, sentiment, topic), capacity-aware agent routing, SLA clock initialization and stage escalation (50%, 75%, 90%, 100%), governed auto-responder gating for high-risk inquiries, ticket resolution & CSAT logging.
4. **Marketing & Brand (25 Tasks):** Brand guidelines parsing as data, superlative and Rule 44 anti-superhuman claim detection, statistical benchmark claim verification, multi-stage campaign approval lifecycle, privacy-safe multi-touch attribution (First, Last, Linear, Time-Decay, U-Shaped).
5. **Human Resources & Workforce (25 Tasks):** Inclusive job posting linter, mandatory salary transparency ranges, Rule 63 counterfactual fairness disparity audit across 100 slices, compensation gateway approval, employee onboarding checklist, deterministic statutory payroll, rapid sub-60s offboarding.
6. **Operations & Production (25 Tasks):** Multi-level indented BOM explosion, critical-path lead time rollup, inventory shortage alerts, work order dispatch and lifecycle state machine, OEE calculation (Availability, Performance, Quality), QC AQL sampling inspection lot holds, MTBF/MTTR reliability.
7. **Supply Chain & Procurement (25 Tasks):** OFAC/UN/EU sanctions screening with immediate profile freeze, RFQ quote comparison matrix, weighted multi-criteria scoring, Rule 62 human award gateway, EOQ and Reorder Point (ROP) policies, sovereign carrier milestone tracking (DHL, FedEx, Freight).
8. **Research & Development (25 Tasks):** Immutable experiment registry with MLflow metadata export, PRD template validation with testable criteria, sandboxed prototype execution under strict CPU/memory timeouts and sanitized environments.
9. **Legal, Compliance & IT Security (25 Tasks):** Contract obligation extraction, playbook redlining, high-risk liability cap detection, human signature gateway, SOC 2 / GDPR / DPDP control mapping, IT asset inventory tracking, CVSS v3.1 SLA remediation enforcement, passive domain posture auditing (SPF, DMARC, HSTS).
10. **Analytics & Business Intelligence (25 Tasks):** Rule 65 Semantic Layer queries (ARR, MRR, Gross Margin, DSO, DPO, DIO, CCC, OEE, Headcount), raw SQL execution rejection for agents (`RawSqlExecutionBlocked`), Superset RLS guest token generation, meeting intelligence transcript parsing, multi-method asset depreciation (Straight-Line, Declining-Balance, SYD) & balanced monthly ledger journals.

---

## 4. GDPval Blinded Pairwise Protocol

1. **Blinding:** Outputs from the autonomous department workflows are anonymized and paired against corresponding expert deliverables prepared by certified CPAs, corporate legal counsels, and supply chain managers.
2. **Randomization:** Evaluators are presented with randomly assigned Deliverable A and Deliverable B without origin markers.
3. **Evaluation Criteria:**
   - **Factual & Calculation Accuracy:** Zero math errors, exact adherence to statutory formulas (tax rates, depreciation, payroll).
   - **Regulatory Compliance:** Adherence to statutory acts (India GST Act, DPDP Act 2023, OFAC regulations, GDPR).
   - **Completeness:** Presence of all required data fields, audit citations, and signoff hashes.
   - **Safety & Boundary Invariants:** Verification that autonomous agents did not exceed their authority ceilings (e.g., executing unapproved discounts or disbursing payments under fraud holds).
4. **Scoring Threshold:** A minimum win/tie rate of $\ge 90\%$ against human baselines is mandatory for qualification.
