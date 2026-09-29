PROJECT DIRECTIVES

Universal AI Company Operating System

Architectural Integration & Enterprise SaaS Development Rules

---

1. PRODUCT IDENTITY

The product is a Universal AI Company Operating System and Universal Robotic AI Assistant SaaS.

The system allows a Host/Owner to:

- Manage one or multiple companies
- Onboard existing real-world companies
- Create new companies
- Operate companies through an AI CEO
- Create and manage AI employees/workforce
- Create and execute missions
- Discover and use tools
- Build new tools when required
- Connect external business systems
- Operate web applications and desktop environments
- Perform general digital/robotic tasks
- Monitor operations
- Receive reports
- Configure budgets, permissions, AI models, automation, security and execution policies

The AI CEO is the central management intelligence.

The Universal Robotic Assistant is the underlying execution capability.

The platform must remain industry-agnostic.

It must support companies and workflows across industries without hard-coding the product around hotels, manufacturing, software, finance, retail, healthcare, or any single vertical.

---

2. ARCHITECTURAL REFERENCE

Use the Paperclip open-source project as an architectural reference for applicable patterns involving:

- Agent organization
- Agent orchestration
- Task delegation
- Task lifecycle management
- Inter-agent communication
- Context handoffs
- Workspace organization
- Configuration systems
- Agent status
- Operational dashboards
- Project/task structures
- Settings architecture
- Real-time operational interfaces

Paperclip is a reference architecture only.

Do not make the product dependent on Paperclip's branding, terminology, assumptions, product identity, or limitations.

Do not blindly copy architecture.

For every adopted pattern:

1. Understand the underlying design.
2. Determine whether it is appropriate for this product.
3. Adapt it to the Universal AI Company OS.
4. Integrate it with existing project architecture.
5. Preserve existing verified functionality.
6. Test the resulting implementation.

---

3. ZERO BRAND LEAKAGE

The production application must never expose the Paperclip brand unless explicitly required for legal attribution/documentation.

Never use "paperclip" as:

- Product name
- UI text
- Route
- API endpoint
- Database table
- Database field
- Variable
- Class
- Function
- Component
- Service
- File name
- Folder name
- Configuration key
- Environment variable
- Agent name
- Internal business terminology

Bad:

paperclip-agent.ts
PaperclipConfig
/api/paperclip/tasks
paperclip_tasks

Good:

AgentRuntime
SystemConfig
/api/os/tasks
operation_tasks

Use native product terminology.

Preferred terminology:

CompanyOS
EnterpriseCore
VirtualHQ
AgentRuntime
AgentRegistry
WorkerRegistry
CEOEngine
MissionEngine
TaskGraph
OperationPipeline
JobDispatcher
ToolRegistry
ToolFactory
CapabilityRegistry
ExecutionEngine
VerificationEngine
KnowledgeEngine
CompanyProfile
CompanyWorkspace

---

4. LICENSE AND SOURCE-CODE COMPLIANCE

Before incorporating any source code from an external repository:

- Inspect its license.
- Preserve required attribution where legally necessary.
- Do not remove legally required notices.
- Do not falsely claim original authorship of upstream code.
- Prefer implementing the architectural idea natively rather than copying large portions of source code.
- Keep third-party attribution in the appropriate legal/documentation location rather than exposing upstream branding throughout the product UI.

If the license or provenance of a component is unclear, do not copy it blindly.

---

5. EXISTING PROJECT IS AUTHORITATIVE

Before modifying the codebase:

1. Inspect the existing project.
2. Identify current architecture.
3. Identify existing features.
4. Identify existing APIs.
5. Identify existing database schemas.
6. Identify existing agent/runtime systems.
7. Identify existing security controls.
8. Identify existing tests.
9. Identify existing UI components.
10. Identify existing integrations.

Never assume the repository is empty.

Never replace an existing subsystem merely because a reference architecture contains something similar.

---

6. ADDITIVE DEVELOPMENT

Default development strategy:

«Extend → integrate → refactor safely → test → preserve.»

Do not:

- Delete verified functionality without justification.
- Replace working modules unnecessarily.
- Remove existing APIs.
- Remove existing security controls.
- Remove existing tests.
- Create duplicate implementations of existing core systems.
- Create a second orchestration engine.
- Create a second permission system.
- Create a second governance system.
- Create a second execution engine.

When an equivalent subsystem already exists:

Existing subsystem
       +
Reference architecture improvements
       ↓
Integrated native subsystem

Not:

Existing subsystem
       +
New duplicate subsystem

---

7. CORE PRODUCT HIERARCHY

The primary product hierarchy is:

HOST
  ↓
WORKSPACE
  ↓
COMPANIES
  ↓
AI CEO
  ↓
AI WORKFORCE
  ↓
MISSIONS
  ↓
TOOLS / CAPABILITIES
  ↓
EXECUTION
  ↓
VERIFICATION
  ↓
BUSINESS / TASK OUTCOME
  ↓
REPORT

This hierarchy must remain understandable throughout the product.

---

8. HOST

The Host is the authenticated owner/operator of the SaaS.

The Host controls:

- Account
- Workspace
- Companies
- AI CEO
- AI workforce
- Missions
- Tools
- Integrations
- Budgets
- Models
- Permissions
- Approvals
- Automation
- Security
- Billing
- Data
- Reports
- Execution policies

The Host must have a clear control center.

---

9. PRIMARY APPLICATION NAVIGATION

The main SaaS navigation should remain intentionally simple.

Primary areas:

Overview
Company
AI CEO
Tools
Settings

Do not expose unnecessary internal architecture as top-level navigation.

Complexity should be handled inside these areas.

---

10. OVERVIEW

The Overview is the Host's operational dashboard.

It should summarize:

- Companies
- Company health
- Active missions
- AI workforce activity
- Completed work
- Pending approvals
- Important alerts
- Spending
- AI usage
- Operational trends
- Business metrics
- System health
- Recent reports

The Overview should answer:

«"What is happening right now?"»

without requiring the Host to navigate through multiple screens.

---

11. COMPANY SYSTEM

Company supports:

Existing Company

Onboard Existing Company

New Company

Create New Company

The Company system must support:

- Company profile
- Industry
- Ownership
- Employees
- Financial information
- Operations
- Business goals
- Products/services
- Customers
- Existing systems
- Documents
- Website
- External research
- Connected data

The AI CEO should help understand the company rather than merely storing form fields.

---

12. AI CEO

The AI CEO is the central intelligence layer.

The CEO should:

- Understand company objectives
- Understand company context
- Analyze available information
- Identify required work
- Create missions
- Determine required workforce
- Select appropriate tools
- Coordinate AI employees
- Monitor execution
- Request approvals
- Escalate problems
- Verify outcomes
- Report results
- Learn from verified outcomes

The CEO must not bypass authorization merely because a model recommends an action.

---

13. DYNAMIC AI WORKFORCE

Do not hard-code a permanent universal list of employees.

The AI CEO should be capable of creating specialized workforce roles based on actual requirements.

A workforce member may contain:

Identity
Role
Objective
Capabilities
Model
Knowledge
Tools
Permissions
Budget
Token limit
Time limit
Autonomy
KPIs
Communication channels
Verification requirements

Lifecycle:

Need Identified
→ Role Designed
→ Capabilities Defined
→ Tools Selected
→ Model Selected
→ Knowledge Assigned
→ Policies Assigned
→ Tested
→ Certified
→ Available
→ Active
→ Retired

---

14. MISSION SYSTEM

A mission is a meaningful objective assigned to the AI system.

Example:

"Reduce monthly customer acquisition cost by 15%."

The system may decompose that objective into:

Mission
 ├── Research
 ├── Analysis
 ├── Planning
 ├── Execution
 ├── Monitoring
 └── Verification

Mission lifecycle should support states such as:

DRAFT
QUEUED
PLANNING
AWAITING_APPROVAL
READY
RUNNING
BLOCKED
PAUSED
REVIEW
VERIFYING
COMPLETED
FAILED
CANCELLED
ESCALATED

Do not blindly copy another project's state machine.

Use the state model that best represents this product.

---

15. TASK AND OPERATION MODEL

Use structured task graphs and operation pipelines where useful.

Preferred concepts:

TaskGraph
OperationPipeline
JobDispatcher
ExecutionPlan
ExecutionStep
Dependency
Checkpoint
VerificationStep

Support:

- Dependencies
- Parallel work
- Sequential work
- Retries
- Timeouts
- Cancellation
- Human approval
- Failure recovery
- Verification
- Result reconciliation

---

16. AGENT COMMUNICATION

AI workforce members must communicate through structured internal interfaces.

Use:

AgentMessage
MissionContext
TaskContext
ResultEnvelope
Handoff
Escalation
ApprovalRequest
VerificationResult

Do not depend on uncontrolled free-form agent-to-agent communication.

Every important communication should retain:

- Sender
- Recipient
- Company
- Mission
- Task
- Timestamp
- Context reference
- Message type
- Authorization context

---

17. TOOLS

Tools are capabilities available to the CEO and AI workforce.

Examples:

- Web search
- Web browser
- Web extraction
- File access
- Document processing
- Email
- Messaging
- Voice
- Video
- CRM
- ERP
- PMS
- Accounting
- Payment
- Marketing
- Development
- IDE
- Git
- Database
- Terminal
- Desktop control
- Keyboard
- Mouse
- Screen
- Cloud services

Tools must be registered through a native Tool Registry.

---

18. TOOL FACTORY

The system should be capable of creating new tools when an authorized requirement exists.

Lifecycle:

Capability Gap
→ Tool Specification
→ Design
→ Build
→ Test
→ Security Validation
→ Sandbox Validation
→ Approval
→ Registration
→ Deployment
→ Monitoring

Tool creation must not automatically grant unrestricted authority.

A tool having technical capability does not automatically mean it has permission to use that capability.

---

19. CAPABILITY VS AUTHORITY

Maintain a strict distinction:

Capability ≠ Authority

Example:

A tool may technically support payment.

That does not mean the AI CEO is authorized to make payments.

Similarly:

Model output ≠ authorization
Tool availability ≠ permission
Recommendation ≠ execution
Simulation ≠ execution
API success ≠ business success

These distinctions are mandatory architectural principles.

---

20. COMPUTER / ROBOTIC CONTROL

The Universal Robotic Assistant may interact with:

- Desktop
- Browser
- Applications
- Files
- Keyboard
- Mouse
- Clipboard
- Terminal
- Screen
- Operating-system interfaces

Preferred execution strategy:

API
  ↓
Application interface
  ↓
DOM/UI automation
  ↓
Visual interaction

Use the most deterministic authorized interface available.

Visual automation should not automatically replace a stable API.

---

21. EXECUTION MODES

Support explicit execution modes:

SIMULATION
SANDBOX
READ_ONLY
LOW_RISK_LIVE
APPROVED_LIVE
HIGH_RISK_LIVE

Never represent simulation as real execution.

Never represent API success as verified business success.

The UI must clearly distinguish:

PLANNED
SIMULATED
EXECUTED
VERIFIED
FAILED
UNVERIFIED

---

22. SETTINGS / CONTROL PLANE

Settings must be enterprise-grade.

Major settings domains:

Account
Security
Workspace
Companies
AI CEO
AI Workforce
Missions
AI Models
Tools
Computer Control
Integrations
Knowledge
Communication
Sales
Marketing
Finance
Documents
Notifications
Approvals
Permissions
Privacy
Security Operations
Audit
Usage & Costs
Billing
API
Webhooks
Localization
Appearance
Backup & Recovery
Enterprise Administration
Advanced

Every setting should have:

- Clear description
- Current value
- Scope
- Permission requirement
- Validation
- Safe defaults
- Audit trail where appropriate
- Reset capability where appropriate

---

23. SETTINGS SCOPE

Settings may exist at different scopes:

Platform
Workspace
Company
Department
AI Employee
Mission
Tool
Integration
User

The effective configuration should follow an explicit precedence model.

Example:

Platform Default
      ↓
Workspace Override
      ↓
Company Override
      ↓
Employee Override
      ↓
Mission Override

Do not create ambiguous configuration inheritance.

Always show the Host where a setting came from.

---

24. APPROVAL SYSTEM

Actions can require approval according to policy.

Examples:

External communication
Financial transaction
Data deletion
Account creation
Contract execution
Advertising spend
Production deployment
High-risk computer operation

Approval requests should contain:

- What will happen
- Why
- Target
- Estimated cost
- Relevant data
- Risk level
- Expected result
- Expiration
- Approve
- Reject
- Modify
- Escalate

---

25. PERMISSION SYSTEM

Support granular RBAC and, where required, more detailed policy controls.

Example roles:

Owner
Administrator
Executive
Manager
Operator
Auditor
Developer
Finance
Read Only

Permissions should cover:

- Companies
- AI CEO
- Workforce
- Missions
- Tools
- Integrations
- Data
- Finance
- Settings
- API
- Audit

---

26. SECURITY

Security must be designed into the system rather than added after the UI.

Minimum requirements:

- Secure authentication
- MFA/passkeys
- Session management
- Encryption in transit
- Encryption at rest
- Secret isolation
- Credential rotation
- Least privilege
- Company isolation
- Workspace isolation
- Audit logging
- Rate limiting
- Abuse controls
- Secure file handling
- Prompt-injection defenses
- External-content isolation

Secrets must never be placed into model prompts, ordinary logs, or uncontrolled agent context.

---

27. DATA AND KNOWLEDGE

Knowledge sources may include:

- Company documents
- Websites
- Databases
- CRM
- ERP
- Uploaded files
- Emails
- Business systems
- Knowledge bases

Every knowledge source should have:

Owner
Scope
Permissions
Source
Freshness
Status
Access policy

Company knowledge must not leak across companies.

---

28. MODEL GATEWAY

Do not hard-code the product around a single AI provider.

Create a Model Gateway supporting multiple providers.

Architecture:

AI Request
   ↓
Model Router
   ↓
Policy Check
   ↓
Cost Check
   ↓
Privacy Check
   ↓
Selected Model
   ↓
Response
   ↓
Evaluation / Logging

Support cloud, compatible APIs, and local/self-hosted models where technically appropriate.

---

29. MODEL ROUTING

Model selection may depend on:

- Task complexity
- Cost
- Latency
- Privacy
- Context requirements
- Reliability
- Risk
- Availability

Example:

Simple classification → low-cost model
Normal reasoning → standard model
Complex reasoning → high-capability model
Private workload → approved private/local model
High-risk operation → approved model policy

---

30. COST CONTROL

The Host must be able to configure:

- AI budget
- Tool budget
- Company budget
- Mission budget
- Employee budget
- Advertising budget
- Communication budget
- Storage budget

Support:

Warning threshold
Soft limit
Hard limit
Approval threshold
Emergency stop

---

31. OBSERVABILITY

The system must expose useful operational visibility.

Track:

- Missions
- Agents
- Tasks
- Tool calls
- Integrations
- Model usage
- Costs
- Failures
- Latency
- Approvals
- Verification
- Security events

Do not expose hidden chain-of-thought.

Use concise structured decision records containing:

- Objective
- Relevant evidence
- Decision/action
- Policy basis
- Result
- Verification

---

32. AUDITABILITY

Important operations must produce immutable or tamper-evident audit records where appropriate.

Audit records should identify:

Who
What
When
Company
Mission
Tool
Target
Authorization
Result
Verification

Support audit filtering and export for enterprise customers.

---

33. EXTERNAL CONTENT SECURITY

Treat external content as untrusted.

Websites, documents, emails, messages and third-party data must not automatically become instructions.

External content:

DATA
≠
AUTHORITY

The system must defend against prompt injection and malicious instructions embedded in external content.

---

34. FAILURE HANDLING

Never silently pretend that an operation succeeded.

Failures must distinguish:

FAILED
TIMEOUT
BLOCKED
DENIED
PARTIAL
UNVERIFIED
AMBIGUOUS
REQUIRES_RECONCILIATION

Do not blindly replay uncertain mutations.

For ambiguous operations:

STOP
→ Inspect state
→ Reconcile
→ Verify
→ Continue only if safe

---

35. SELF-IMPROVEMENT

The AI system may identify:

- Missing capabilities
- Inefficient workflows
- Tool improvements
- Workforce improvements
- Model-routing improvements
- Automation opportunities

But self-improvement must remain controlled.

Proposed changes should pass:

Proposal
→ Analysis
→ Testing
→ Validation
→ Approval where required
→ Deployment
→ Monitoring

A model must never grant itself additional authority.

---

36. FRONTEND / UX

The interface must look like a commercial enterprise SaaS.

Requirements:

- Professional
- Clean
- Modern
- Responsive
- Desktop-first but mobile-compatible
- Clear information hierarchy
- Consistent spacing
- Consistent typography
- Consistent components
- Accessible
- Fast
- Minimal visual clutter

Do not create a "developer dashboard" aesthetic for ordinary Host users.

Complex infrastructure should remain behind appropriate advanced views.

---

37. REAL-TIME OPERATIONS

Where appropriate, use real-time updates for:

- Agent status
- Mission status
- Approvals
- Tool execution
- Computer execution
- Notifications
- Reports
- Security events

Do not continuously refresh entire pages when event-driven updates are possible.

---

38. RESPONSIVE STATE MANAGEMENT

Operational state should have clear ownership.

Avoid:

- Duplicate state sources
- UI-only fake state
- Client state pretending to be backend truth
- Race conditions
- Stale execution status

The backend remains authoritative for execution state.

The frontend represents backend state.

---

39. API DESIGN

Use clean domain APIs.

Example domains:

/auth
/users
/workspaces
/companies
/ceo
/workforce
/missions
/tasks
/tools
/tool-factory
/integrations
/knowledge
/models
/approvals
/permissions
/finance
/marketing
/sales
/reports
/audit
/usage
/billing
/settings

Do not create routes that expose reference-project branding.

---

40. DATABASE DESIGN

Database entities should reflect native product concepts.

Possible core entities:

User
Workspace
Company
CompanyMember
CompanyProfile
AIExecutive
AIWorker
Mission
Task
TaskDependency
Tool
ToolVersion
Capability
Integration
CredentialReference
KnowledgeSource
KnowledgeItem
ModelProvider
Model
Approval
Policy
Permission
Budget
UsageRecord
AuditEvent
Report
Notification
Webhook
Subscription
Invoice

Do not create database entities merely because the reference repository has them.

Use the product's actual domain model.

---

41. TESTING REQUIREMENTS

Every major feature must include tests.

At minimum:

Unit tests

Business logic.

Integration tests

Subsystem interaction.

API tests

Endpoints and authorization.

Database tests

Persistence and isolation.

UI tests

Critical workflows.

Security tests

Permission boundaries.

Failure tests

Timeouts, failures, retries and ambiguous outcomes.

Multi-tenant tests

Company/workspace isolation.

Regression tests

Existing verified functionality must continue working.

---

42. ANTI-REGRESSION RULE

Before modifying an existing feature:

Inspect
→ Understand
→ Test current behavior
→ Modify
→ Test again

Never assume an existing feature is disposable.

If a change breaks an existing capability:

1. Identify why.
2. Restore compatibility.
3. Add regression coverage.
4. Then continue.

---

43. NO FAKE FUNCTIONALITY

Do not create UI that falsely implies functionality exists.

Avoid:

"Connected"
when no connection exists.

"Completed"
when execution was not verified.

"AI Employee Active"
when no runtime exists.

"Payment Successful"
when only an API request was sent.

"Tool Ready"
when the tool has not been tested.

Use explicit states.

---

44. PLACEHOLDER POLICY

During development, placeholders may be used only when clearly marked internally.

Never present fake production capabilities as completed features.

For incomplete functionality use states such as:

Coming Soon
Prototype
Sandbox
Not Connected
Configuration Required
Awaiting Approval
Unavailable

---

45. DEVELOPMENT ENVIRONMENT

The system may use development tools such as:

- Git
- VS Code
- IDEs
- Python
- Node.js
- TypeScript
- Java/Kotlin
- Go
- Rust
- Docker
- Databases
- Testing tools
- Browser automation

The development environment is not automatically a production dependency.

Antigravity is the development environment.

The resulting SaaS must have its own production architecture.

---

46. DEVELOPMENT WORKFLOW

For every implementation request:

1. Inspect
2. Understand
3. Identify affected domains
4. Identify existing functionality
5. Design minimal change
6. Implement
7. Run type checks
8. Run tests
9. Run build
10. Inspect runtime behavior
11. Fix regressions
12. Report exactly what changed

Do not generate large amounts of code without verification.

---

47. CHANGE DISCIPLINE

Before making architectural changes, identify:

Affected modules
Affected database entities
Affected APIs
Affected UI
Affected permissions
Affected integrations
Affected tests
Migration requirements
Rollback implications

Avoid unnecessary rewrites.

---

48. PERFORMANCE

The SaaS must be designed for commercial scale.

Consider:

- Async jobs
- Queues
- Caching
- Pagination
- Streaming
- Rate limiting
- Connection pooling
- Background workers
- Efficient database queries
- Large-file handling
- Concurrent missions

Never block the primary web request unnecessarily for long-running AI or robotic operations.

---

49. MULTI-TENANCY

The system must safely support:

Host
 ↓
Workspace
 ↓
Multiple Companies
 ↓
Multiple AI Workforces
 ↓
Multiple Missions

Company data must remain isolated.

Workspace data must remain isolated from other workspaces.

Authorization must be checked server-side.

Never rely solely on frontend hiding.

---

50. COMMERCIAL SAAS REQUIREMENTS

The product must support commercial SaaS fundamentals:

- Registration
- Login
- Subscription
- Billing
- Usage metering
- Plans
- Limits
- Trial
- Upgrade
- Downgrade
- Cancellation
- Invoices
- Notifications
- Support
- Enterprise configuration

Feature availability must be controlled by entitlements rather than hard-coded UI assumptions.

---

51. FEATURE FLAGS

Use feature flags for:

- Experimental features
- Beta tools
- New AI models
- New automation systems
- New integrations
- Enterprise-only features

Feature flags must not become an alternative permission system.

---

52. BACKUP AND RECOVERY

Critical data must have appropriate backup and recovery mechanisms.

Support:

- Database backups
- Configuration backup
- Company backup
- Knowledge backup
- Audit preservation
- Recovery procedures

Recovery operations must be tested.

---

53. DEFINITION OF DONE

A feature is not considered complete merely because:

Code exists

It is complete when:

Implementation
+
Correct integration
+
Authorization
+
Persistence
+
Error handling
+
UI state
+
Tests
+
Build success
+
Runtime verification
+
Documentation where appropriate

---

54. IMPLEMENTATION PRIORITY

Do not attempt to implement the entire product in one generated change.

Build incrementally.

Recommended order:

PHASE 1
Authentication
Workspace
Host profile
Main navigation
Overview

PHASE 2
Company
Company onboarding
New company creation
Company data model

PHASE 3
AI CEO
CEO interaction
Company understanding
CEO dashboard

PHASE 4
AI Workforce
Dynamic employee creation
Workforce management

PHASE 5
Missions
Task graph
Execution lifecycle
Reports

PHASE 6
Tools
Tool Registry
Capability Registry
Tool Factory

PHASE 7
Computer / Robotic Control
Browser
Desktop
Keyboard
Mouse
Files

PHASE 8
Integrations
CRM
ERP
PMS
Accounting
Communication
Payments

PHASE 9
Settings
Permissions
Approvals
Budgets
Models
Security
Audit

PHASE 10
Commercial SaaS
Billing
Plans
Usage
Enterprise administration

PHASE 11
Production hardening
Security
Performance
Recovery
Observability
Multi-tenant testing

---

55. PRIMARY PRODUCT PRINCIPLE

The system must always preserve this relationship:

HOST
  ↓
OBJECTIVE
  ↓
AI CEO
  ↓
UNDERSTAND
  ↓
PLAN
  ↓
CREATE / SELECT WORKFORCE
  ↓
SELECT TOOLS
  ↓
REQUEST AUTHORITY
  ↓
EXECUTE
  ↓
OBSERVE
  ↓
VERIFY
  ↓
REPORT
  ↓
LEARN

The system should not become a collection of disconnected AI agents.

It is a company operating system controlled by an AI CEO.

---

56. FINAL ANTIGRAVITY RULE

When uncertain:

Do not invent architecture.

First inspect:

- Existing source
- Existing schemas
- Existing APIs
- Existing components
- Existing tests
- Existing security
- Existing runtime
- Existing product requirements

Then make the smallest architectural change that achieves the requirement.

Preserve working functionality.

Prefer native implementation.

Prefer reusable abstractions.

Prefer deterministic execution.

Prefer explicit state.

Prefer verification.

Prefer least privilege.

Prefer reversible changes.

Never claim an operation is complete without evidence.

The objective is not to reproduce a reference repository.

The objective is to build a professional, commercially deployable, universal AI Company Operating System using proven architectural patterns while retaining the product's own identity and capabilities.
