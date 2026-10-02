# ZONATA V4 — ENTERPRISE WORKFORCE & ORGANIZATION GRAPH MODEL
**Multi-Tenant Corporate Structure, Hierarchy Containment, & Supervision Trees**

## 1. Enterprise Hierarchy Graph
ZONATA V4 establishes a formal organizational hierarchy (`core/organization_graph.py`) that organizes people, departments, and AI Employees into a structured tree:

```
Tenant (Customer Enterprise)
  └── Company (Legal Entity)
        └── Business Unit (e.g., Global Commercial)
              └── Department (e.g., Engineering, Finance, Operations)
                    └── Team (e.g., Core Infrastructure, Accounts Payable)
                          ├── Human Supervisor / Manager
                          └── AI Employee Workforce (Specialists & Workers)
```

### Node Types
- `TENANT`: Root boundary of data, identity, and billing isolation.
- `COMPANY`: Subsidiary or legal operating company under the tenant.
- `BUSINESS_UNIT`: Operational business division.
- `DEPARTMENT`: Functional unit (e.g., FINANCE, LEGAL, HR, ENGINEERING).
- `TEAM`: Specific working group.
- `EMPLOYEE_NODE`: Either a human supervisor or an AI employee.

---

## 2. Delegation Containment & Supervision
- Every AI Employee is placed within an organization node and assigned a designated `supervisor_id` (either human or higher-tier AI Executive).
- Actions requiring human-in-the-loop elevation escalate upward along the organizational tree until reaching an authorized human role (e.g., Department Manager, CFO).
- An AI employee cannot access data, invoke tools, or delegate missions outside its parent department or team without explicit cross-functional ABAC policy grants.
