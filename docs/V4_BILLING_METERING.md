# ZONATA V4 — ENTERPRISE USAGE METERING & BILLING LEDGER
**Immutable Usage Events, Multi-Tier Spend Ceilings, & Cost Allocation**

## 1. Metering Architecture
The `UsageMeter` (`core/usage_meter.py`) and `SpendGovernor` (`core/spend_governor.py`) track all resource consumption in real time:
- **Tracked Meters**: LLM prompt tokens, LLM completion tokens, tool execution duration (ms), storage consumed (bytes), active AI employee hours.
- **Event Immutability**: Metering records are appended to `usage_meter_events` as an immutable financial ledger with tenant, company, and department attribution.

---

## 2. Multi-Tier Spend Ceilings
- **Soft Limit (80%)**: Emits automated notifications to tenant billing administrators.
- **Hard Limit (100%)**: Blocks mutating and fee-incurring actions until budget is increased or renewed.
- **Emergency Freeze**: Global or per-tenant budget freeze tripped by anomalous spend velocity.
