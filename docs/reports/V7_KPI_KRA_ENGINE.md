# ZONATA V7 — KPI & KRA Operational Engine
**Document ID:** ZONATA-V7-KPI-004  
**Classification:** BUSINESS OUTCOME MEASUREMENT & GOVERNANCE  
**Status:** IMPLEMENTED & VALIDATED  

---

## 1. Operational Invariant: Task Completion != Business Outcome

A critical flaw in autonomous agent systems is conflating task completion with business success. An agent may execute 50 tool calls, write 10 emails, and return HTTP 200 without moving enterprise business metrics.

ZONATA's `KPIKRAEngine` (`core/kpi_kra_engine.py`) binds AI Employees directly to real-world verified metrics:

```
[Tool Action Executed (HTTP 200 OK)]
                 |
                 v
   [Data Source Physical Probe]
   - Queries settled ERP/PMS/Billing ledger
   - Collects cryptographic audit proof
                 |
                 v
      [KPI Measurement Engine]
   - Computes: Variance = Measured - Target
   - Assigns: TARGET_MET | WARNING | BREACHED
                 |
                 v
   [Cryptographic Evidence Ledger]
   - Event: KPI_MEASUREMENT_RECORDED
```

---

## 2. Structured KPI Definition Schema

Every employee KPI must define its mathematical parameters, measurement frequency, and verification source:

```python
@dataclass
class StructuredKPI:
    kpi_id: str
    tenant_id: str
    company_id: str
    employee_id: str
    name: str                            # e.g., "Monthly Direct Booking Revenue"
    definition: str                      # Clear operational explanation
    unit: str                            # USD, INR, PERCENTAGE, COUNT, SECONDS
    target_value: float                  # e.g., 1000000.0
    threshold_value: float               # Minimum target for full compliance
    measurement_frequency: str           # DAILY, WEEKLY, MONTHLY, PER_MISSION
    data_source: str                     # e.g., PMS_SETTLED_LEDGER
    owner: str                           # Employee ID or Title
    calculation_method: str              # SUM, AVERAGE, RATIO, LATEST
    minimum_acceptable_value: float      # Hard failure boundary
    warning_threshold: float             # Degradation alert threshold
    escalation_threshold: float          # Automatic supervisor alert threshold
    verification_method: str             # LEDGER_RECONCILIATION, THIRD_PARTY_API
```

---

## 3. Aggregate Performance Health Evaluation

The engine continuously evaluates employee performance over a sliding window of measurements:

- **PERFORMING:** Score $\ge 85\%$, zero critical breaches. Full operational authority retained.
- **DEGRADED:** Score between $75\%$ and $84\%$. Minor warnings detected; self-healing backoff engaged.
- **REVIEW_REQUIRED:** Score between $50\%$ and $74\%$, or $\ge 2$ warnings. Read-only mode recommended; supervisor alerted.
- **UNDERPERFORMING:** Score $< 50\%$ or $\ge 3$ KPI breaches. Triggers automatic proposal for retraining, reconfiguration, or succession.
