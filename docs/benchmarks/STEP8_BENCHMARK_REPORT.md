# Step 8 Empirical Human-Baseline Benchmark Report

> **Governing Rule:** Rule 69 & ADR 0045/0046  
> **Execution Timestamp:** 2026-11-24T17:23:40.231771+00:00  
> **Comparison Baseline:** Config C (Zonata Autonomous System) vs Config A (Unassisted Human Baseline)  

## 1. Executive Summary

This report documents empirical trial results measuring Zonata Autonomous System (Config C) against licensed, unassisted human professionals (Config A).
Under Rule 69, Zonata does not benchmark against or claim superiority over unassisted foundation models (Config B). All speedup and economic claims cite verified, sample-sufficient ($N \ge 30$) empirical trials.

## 2. Summary of Trial Results

| Task ID | Task Description | Industry | $N_C$ | $N_A$ | Mean C (s) | Mean A (s) | Speedup | Cohen's $d$ | 95% CI | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `TASK-C28-AP-01` | 3-Way PO and Delivery Note Invoice Matching | `C28` | 50 | 50 | 19.0 | 967.5 | 50.92x | -30.82 | [-960.5652, -936.4348] | **BETTER** |
| `TASK-H52-BOL-01` | Multi-Modal Bill of Lading & Customs Declaration Generation | `H52` | 40 | 40 | 25.5 | 755.0 | 29.61x | -44.41 | [-736.6998, -722.3002] | **BETTER** |
| `TASK-Q86-ADMIN-01` | Administrative Appointment Intake & Facility Scheduling | `Q86` | 35 | 35 | 31.0 | 509.1 | 16.44x | -33.07 | [-484.9461, -471.3967] | **BETTER** |
| `TASK-M69-LEGAL-01` | Bespoke Complex M&A Warranty Indemnity Audit | `M69` | 3 | 3 | N/A | N/A | N/A | N/A | N/A | NO_BASELINE |

## 3. Unit Economics & Cost Efficiency

- **Accounts Payable Matching (`TASK-C28-AP-01`):**
  - Human Baseline Cost: ~$8.75 per invoice (15 minutes at $35/hr loaded labor rate).
  - Zonata Autonomous Cost: ~$0.12 per invoice (token inference + database compute).
  - **Cost Savings:** ~98.6% per transaction.
- **Logistics Documentation (`TASK-H52-BOL-01`):**
  - Human Baseline Cost: ~$7.00 per shipment document set (12 minutes at $35/hr).
  - Zonata Autonomous Cost: ~$0.15 per document set.
  - **Cost Savings:** ~97.8% per transaction.

## 4. Safety & Boundary Invariant Adherence (Rule 72)

- **Critical Safety Violations:** 0 across all evaluated trials.
- **Sector Boundary Enforcer:** Rebuffed 100% of adversarial boundary injection probes (clinical diagnosis, consumer credit scoring, automated claim denial).
- **Critical-Error Veto:** No vetoes triggered during production trial execution.

## 5. Cryptographic Seal

**Report Seal (SHA-256):** `8a19bf044cad08e348a4dfd4ebedd7aa3e23e5d263be39cf0009474a15dd7cd6`  
