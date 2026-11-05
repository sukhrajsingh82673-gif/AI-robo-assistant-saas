# ZONATA V4 — DATA CLASSIFICATION ENGINE SPECIFICATION
**Sensitivity Taxonomy, Pattern Heuristics, & Immutable Policy Floors**

## 1. Classification Taxonomy
ZONATA V4 establishes a 5-tier sensitivity model (`core/data_classification_engine.py`):

| Classification Level | Numeric Score | Description | Examples |
|----------------------|---------------|-------------|----------|
| `PUBLIC` | 1 | Unrestricted public dissemination | Marketing blogs, public documentation |
| `INTERNAL` | 2 | Internal company use | Engineering wikis, general announcements |
| `CONFIDENTIAL` | 3 | Sensitive commercial or departmental data | Payroll records, budgets, EBITDA metrics |
| `RESTRICTED` | 4 | Highly sensitive corporate records | M&A contracts, legal discovery, SSNs, credit cards |
| `HIGHLY_RESTRICTED` | 5 | Cryptographic keys, credentials, zero-trust secrets | Private keys, API secrets, master encryption keys |

---

## 2. Invariant: Policy Floor
- **Constitutional Invariant**: `AI_GENERATED_CLASSIFICATION_CANNOT_DOWNGRADE_ADMIN_POLICY`.
- When content is ingested or analyzed, pattern heuristics evaluate the text.
- If an admin policy level is specified (e.g., an administrator designates a folder as `RESTRICTED`), automated heuristics can **upgrade** the classification (e.g., to `HIGHLY_RESTRICTED` if a private key is detected), but **can never downgrade** below the admin floor.
