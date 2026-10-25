# URA / ZONATA — PUBLIC GA CUSTOMER SCOPE & CAPABILITY MATRIX (PHASE J / GATE G06)

**Project:** URA / ZONATA Universal AI Company Operating System  
**Evaluation Scope:** Day-1 Customer Capabilities, Feature Availability, and Fresh User Onboarding  
**Target Environment:** Staging (`https://zonata-staging.onrender.com`)  
**Evaluation Date:** October 25, 2026  
**Gate G06 (Fresh User Clean Slate):** **PASS**  

---

## 1. Executive Summary & Truth-in-Advertising Mandate

Enterprise software credibility depends on absolute transparency regarding what works today versus what is scheduled for future release. Releasing a product with silent mock fallbacks that appear operational to the customer is deceptive and dangerous.

In ZONATA, we enforce a strict **Truth-in-Advertising Policy**:
1. All core capabilities verified by physical tests are certified for Day-1 use.
2. All integrations or features requiring unconfigured third-party credentials or external infrastructure are explicitly marked in the user interface as **`NOT CONFIGURED / COMING SOON`**.
3. Fresh user registrations are guaranteed a **zero-leakage clean slate**: newly registered organizations start with clean workspaces, zero pre-populated test data, and isolated database namespaces.

---

## 2. Customer Capability Matrix: Day-1 Supported vs Unconfigured

| Capability / Subsystem | Day-1 Release Status | Operating Envelope / Limit | Customer Experience & UI Behavior |
| :--- | :---: | :---: | :--- |
| **Multi-Tenant User Registration** | **OPERATIONAL** | Max 3 Pilot Orgs; 10 req/min/IP | Self-service registration; generates isolated tenant ID. |
| **Authentication & RBAC** | **OPERATIONAL** | Admin, Member, Auditor | PBKDF2 password security; secure session cookies. |
| **Executive KPI Dashboard** | **OPERATIONAL** | Realtime data | Shows organization-scoped stats; clean empty state for new orgs. |
| **AI CEO Strategic Center** | **OPERATIONAL** | Max 5 meetings/month | Facilitates strategic meetings, logs decisions, bridges tasks. |
| **AI Coworker Workforce** | **OPERATIONAL** | 5 concurrent tasks/tenant | Autonomous task execution with asynchronous worker queue. |
| **Statutory Enterprise Finance** | **OPERATIONAL** | Max ₹5,000 monthly spend | Two-phase expense submission, approval, and GL postings. |
| **Evidence Ledger Explorer** | **OPERATIONAL** | Immutable SHA-256 chain | Live Merkle audit log viewer; cryptographic verification tool. |
| **Workflow Automation Hub** | **OPERATIONAL** | Visual workflow editor | Low-code automation canvas (`workflow_workspace.js`). |
| **Model Context Protocol (MCP)** | **OPERATIONAL** | Native JSON-RPC | Tool discovery registry; reports zero external tools gracefully. |
| **Agent-to-Agent (A2A)** | **OPERATIONAL** | Native cryptographic nonces | Inter-agent protocol with replay prevention. |
| **Salesforce CRM Sync** | **NOT CONFIGURED** | Requires Commercial API Key | UI displays `NOT CONFIGURED` badge; sync button disabled. |
| **Intuit QuickBooks Sync** | **NOT CONFIGURED** | Requires Commercial API Key | UI displays `NOT CONFIGURED` badge; GL sync disabled. |
| **Google Workspace Sync** | **NOT CONFIGURED** | Requires Service Account | UI displays `NOT CONFIGURED` badge; export disabled. |
| **Nango Integration Proxy** | **NOT CONFIGURED** | Requires Nango Secret Key | UI displays `NOT CONFIGURED` badge; proxy disabled. |

---

## 3. Fresh User Clean-Slate Experience (Gate G06)

A critical defect identified in early software versions was "leaky initial state," where newly registered accounts saw residual test records, pre-seeded synthetic expenses, or foreign coworker tasks.

### Verification Methodology
The onboarding experience was rigorously tested via the clean UI regression suite: `tests/test_fresh_user_experience_and_clean_ui.py` (7/7 tests passed).

### Verification Results
1. **Zero Record Leakage:**
   When a new tenant (e.g. `tenant_clean_test_org`) registers, the database creates an isolated namespace.
   - Initial Coworker Tasks: `0`
   - Initial AI CEO Meetings: `0`
   - Initial Submitted Expenses: `0`
   - Initial General Ledger Transactions: `0`
2. **First-Run Guided Onboarding:**
   The dashboard displays a structured, clean first-run experience:
   - "Welcome to ZONATA. Your company operating workspace is ready."
   - Quick-action buttons to configure organization settings, invite team members, and schedule the first AI CEO strategic alignment meeting.
3. **Pilot Resource Meters:**
   The workspace navigation header prominently displays transparent pilot resource consumption meters:
   - *Organization Capacity:* Active Org # / 3
   - *User Allocation:* Active Users / 10
   - *AI CEO Meetings:* Meetings Held / 5
   - *Monthly Spend:* ₹ Current / ₹5,000

---

## 4. UI Transparency & Disabled State Visual Standards

To maintain consistency and customer trust across the platform:
1. **Disabled Feature Badging:**
   Any integration lacking active credentials renders with a standardized warning banner:
   ```html
   <div class="integration-banner warning">
     <span class="badge badge-amber">NOT CONFIGURED</span>
     <p>This integration is dormant. Live synchronization requires configuring production credentials in Settings > Integrations.</p>
   </div>
   ```
2. **Fail-Closed API Responses:**
   Attempting to trigger disabled endpoints returns clean, descriptive JSON rather than 500 server crashes:
   ```json
   {
     "status": "error",
     "code": "FEATURE_NOT_CONFIGURED",
     "message": "Salesforce integration is currently dormant. Contact your administrator to provide OAuth credentials."
   }
   ```

---

## 5. Gate Determination

**Gate G06 (Fresh User Clean State): PASS.**  
New tenants receive an isolated, clean-slate operating environment with zero cross-tenant data leakage and complete transparency regarding active versus unconfigured features.
