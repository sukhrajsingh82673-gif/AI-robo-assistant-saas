/**
 * ZONATA / URA Universal AI Company Operating System
 * Master Production Settings Center
 * P0 Production & Enterprise Requirement: Card-based, square/grid-oriented,
 * 43 canonical categories across 6 groups, hierarchical scope inheritance,
 * permission-aware, auditable with SHA-256 evidence, effective vs configured runtime state,
 * CEO proposal resolution, instant search dropdown, and mobile-responsive layout.
 */

const EnterpriseSettings = (function() {
  'use strict';

  // 6 Primary Visual Groups
  const GROUPS = [
  {
    "id": "identity",
    "name": "GROUP A \u2014 IDENTITY",
    "description": "Host sovereignty, company identity, organizational hierarchy, and access control."
  },
  {
    "id": "ai_system",
    "name": "GROUP B \u2014 AI EXECUTIVE SYSTEM",
    "description": "Global AI policy, inference providers, AI CEO governance, workforce, and autonomy."
  },
  {
    "id": "execution",
    "name": "GROUP C \u2014 EXECUTION FABRIC",
    "description": "Workflows, tools registry, MCP, A2A network, desktop, browser, terminal, and sandbox."
  },
  {
    "id": "business",
    "name": "GROUP D \u2014 BUSINESS SYSTEMS",
    "description": "Integrations, organizational knowledge, files, records, finance, and notifications."
  },
  {
    "id": "governance",
    "name": "GROUP E \u2014 CONTROL & TRUST",
    "description": "Approvals, constitutional governance, privacy, compliance, audit ledger, and security."
  },
  {
    "id": "platform",
    "name": "GROUP F \u2014 COST & PLATFORM",
    "description": "Usage & compute costs, billing, developer APIs, webhooks, localization, recovery, and danger zone."
  }
];

  // Canonical 43 Categories Metadata (Pre-seeded for instant 0ms render)
  const DEFAULT_CATEGORIES = [
  {
    "id": "account",
    "group_id": "identity",
    "name": "Account",
    "icon": "\ud83d\udc64",
    "desc": "Administrator profile, notification preferences, sessions, and accessibility.",
    "status": "Healthy",
    "scope": "User"
  },
  {
    "id": "host",
    "group_id": "identity",
    "name": "Host & Sovereignty",
    "icon": "\ud83c\udfdb\ufe0f",
    "desc": "Sovereign owner boundary, system authority hierarchy, and emergency stops.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "company",
    "group_id": "identity",
    "name": "Company",
    "icon": "\ud83c\udfe2",
    "desc": "Legal entity parameters, universal industry, business model, and KPIs.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "organization",
    "group_id": "identity",
    "name": "Organization",
    "icon": "\ud83c\udf33",
    "desc": "Departments, locations, cost centers, profit centers, and delegation tree.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "users",
    "group_id": "identity",
    "name": "Users & Access",
    "icon": "\ud83d\udc65",
    "desc": "Granular RBAC roles, permission matrix, active sessions, and trusted devices.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "ai",
    "group_id": "ai_system",
    "name": "AI Global Policy",
    "icon": "\ud83e\udde0",
    "desc": "Autonomous reasoning depth, quality/cost thresholds, and safety firewalls.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "ai_providers",
    "group_id": "ai_system",
    "name": "AI Models & Providers",
    "icon": "\u26a1",
    "desc": "Vertex, Gemini, Claude, OpenAI, local inference endpoints, and credential vault.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "ai_ceo",
    "group_id": "ai_system",
    "name": "AI CEO",
    "icon": "\ud83d\udc51",
    "desc": "Executive operating mode, 0-4 autonomy levels, approval thresholds, and memory.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "workforce",
    "group_id": "ai_system",
    "name": "AI Workforce",
    "icon": "\ud83e\udd16",
    "desc": "Dynamic agent spawning limits, department budgets, and performance gates.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "agent_factory",
    "group_id": "ai_system",
    "name": "Agent Factory",
    "icon": "\ud83c\udfed",
    "desc": "Template registry, capability discovery, sandbox simulations, and authority caps.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "missions",
    "group_id": "ai_system",
    "name": "Missions & Autonomy",
    "icon": "\ud83c\udfaf",
    "desc": "Mission creation triggers, risk gates, retries, and outcome verification.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "workflows",
    "group_id": "execution",
    "name": "Automation & Workflows",
    "icon": "\ud83d\udd04",
    "desc": "Durable execution, retry backoff, compensating actions, and immutable DAGs.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "tools",
    "group_id": "execution",
    "name": "Tools & Capabilities",
    "icon": "\ud83d\udee0\ufe0f",
    "desc": "Capability fabric registry, risk classification, sandboxing, and trust gates.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "mcp",
    "group_id": "execution",
    "name": "MCP Servers",
    "icon": "\ud83d\udd0c",
    "desc": "Model Context Protocol connections, resource limits, and tool permissions.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "a2a",
    "group_id": "execution",
    "name": "A2A / Agent Network",
    "icon": "\ud83c\udf10",
    "desc": "Agent-to-agent protocol, trust boundaries, message quotas, and broker topology.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "desktop",
    "group_id": "execution",
    "name": "Desktop / Coworker",
    "icon": "\ud83d\udda5\ufe0f",
    "desc": "Perception rates, mouse/keyboard throttling, application access, and evidence.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "browser",
    "group_id": "execution",
    "name": "Browser & Web Execution",
    "icon": "\ud83c\udf10",
    "desc": "Headless Chromium contexts, domain allowlists, SSRF guard, and DOM audit.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "terminal",
    "group_id": "execution",
    "name": "Governed Terminal",
    "icon": "\ud83d\udcbb",
    "desc": "Sandboxed shell execution, TTL leases, egress allowlists, and execution ledger.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "openhands",
    "group_id": "execution",
    "name": "OpenHands / Code Execution",
    "icon": "\ud83d\udce6",
    "desc": "Sandboxed software workspace, git branch protection, and rollback gates.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "integrations",
    "group_id": "business",
    "name": "Integrations",
    "icon": "\ud83d\udd17",
    "desc": "Connected business systems (PMS, ERP, CRM, Payments), sync cadence, and least privilege.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "data",
    "group_id": "business",
    "name": "Data & Knowledge",
    "icon": "\ud83d\udcda",
    "desc": "Semantic search index, retention lifecycles, and data classification tags.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "files",
    "group_id": "business",
    "name": "Files & Documents",
    "icon": "\ud83d\udcc1",
    "desc": "Storage quotas, MIME restrictions, immutable SHA-256 digests, and encryption.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "records",
    "group_id": "business",
    "name": "Records & Business Data",
    "icon": "\ud83d\udccb",
    "desc": "Structured entity schemas, deduplication rules, and validation pipelines.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "finance",
    "group_id": "business",
    "name": "Finance & Ledgers",
    "icon": "\ud83d\udcb0",
    "desc": "Chart of accounts, currencies, fiscal year close, and expenditure approval limits.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "notifications",
    "group_id": "business",
    "name": "Notifications & Comms",
    "icon": "\ud83d\udd14",
    "desc": "Dispatch channels, digest intervals, priority alerts, and sending domains.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "approvals",
    "group_id": "governance",
    "name": "Approvals & Decision Center",
    "icon": "\u2696\ufe0f",
    "desc": "Financial limits, two-person rules, timeout escalations, and owner sign-offs.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "governance",
    "group_id": "governance",
    "name": "Governance & Constitution",
    "icon": "\ud83d\udee1\ufe0f",
    "desc": "Sovereign authority hierarchy, policy IF/THEN builder, and instant kill switches.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "privacy",
    "group_id": "governance",
    "name": "Privacy & Data Protection",
    "icon": "\ud83d\udd12",
    "desc": "PII anonymization, AI training zero-retention, and data sovereignty rules.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "compliance",
    "group_id": "governance",
    "name": "Compliance & Regulations",
    "icon": "\ud83d\udcdc",
    "desc": "ISO 37000/31000/37301/42001 profiles, statutory audits, and legal jurisdictions.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "audit",
    "group_id": "governance",
    "name": "Audit & Evidence Ledger",
    "icon": "\u26d3\ufe0f",
    "desc": "Cryptographic SHA-256 Merkle ledger, immutability mode, and export receipts.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "security",
    "group_id": "governance",
    "name": "Security & Identity Policy",
    "icon": "\ud83d\udd10",
    "desc": "MFA enforcement, WebAuthn passkeys, session lifetimes, and brute-force shields.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "usage",
    "group_id": "platform",
    "name": "Usage & AI Costs",
    "icon": "\ud83d\udcca",
    "desc": "Compute metering, token burn alerts (50/75/90/100%), and hard spend stops.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "billing",
    "group_id": "platform",
    "name": "Billing & Subscriptions",
    "icon": "\ud83d\udcb3",
    "desc": "Plan tier, payment gateways, licensing tokens, and invoice audit ledger.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "api",
    "group_id": "platform",
    "name": "API & Developer Platform",
    "icon": "\ud83d\udd11",
    "desc": "Bearer token keys, OAuth scopes, rate limiting, and egress IP allowlists.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "webhooks",
    "group_id": "platform",
    "name": "Webhooks & Events",
    "icon": "\ud83e\ude9d",
    "desc": "HMAC-SHA256 signature verification, retry backoff, and event dispatch logs.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "localization",
    "group_id": "platform",
    "name": "Localization & Locale",
    "icon": "\ud83c\udf0d",
    "desc": "Base reporting timezone, number formatting, currency symbols, and business days.",
    "status": "Healthy",
    "scope": "Company"
  },
  {
    "id": "appearance",
    "group_id": "platform",
    "name": "Appearance & UX",
    "icon": "\ud83c\udfa8",
    "desc": "Theme mode, high contrast, reduced motion, navigation density, and mobile bottom dock.",
    "status": "Healthy",
    "scope": "User"
  },
  {
    "id": "recovery",
    "group_id": "platform",
    "name": "Backup & Disaster Recovery",
    "icon": "\ud83d\udcbe",
    "desc": "Automated SQLite snapshots, cold backup sync, RPO/RTO goals, and restore drills.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "monitoring",
    "group_id": "platform",
    "name": "Monitoring & Reliability",
    "icon": "\ud83d\udcc8",
    "desc": "Subsystem health monitors, circuit breakers, timeout thresholds, and liveness probes.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "enterprise",
    "group_id": "platform",
    "name": "Enterprise Administration",
    "icon": "\ud83c\udfe2",
    "desc": "Multi-tenant boundaries, SCIM identity provisioning, SAML 2.0, and data residency.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "features",
    "group_id": "platform",
    "name": "Feature Flags",
    "icon": "\ud83d\udea9",
    "desc": "System capability rollouts, staged enablement, and Canary risk envelopes.",
    "status": "Healthy",
    "scope": "Host"
  },
  {
    "id": "advanced",
    "group_id": "platform",
    "name": "Advanced & Diagnostics",
    "icon": "\u2699\ufe0f",
    "desc": "Runtime engine tuning, cache invalidation, raw policy viewer, and heap diagnostics.",
    "status": "Attention",
    "scope": "Host"
  },
  {
    "id": "danger",
    "group_id": "platform",
    "name": "Danger Zone",
    "icon": "\ud83d\udea8",
    "desc": "High-impact isolated kill switches, session revocation, and data purge guards.",
    "status": "Warning",
    "scope": "Host"
  }
];

  // Pre-seeded Settings Search Index
  const SETTINGS_SEARCH_INDEX = [
  {
    "id": "acc_display_name",
    "category": "account",
    "name": "Display Name",
    "desc": "Operator or sovereign host full legal name shown across notifications and audit receipts.",
    "type": "text",
    "scope": "User",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": "Sukhraj Singh",
    "options": []
  },
  {
    "id": "acc_email",
    "category": "account",
    "name": "Host Email",
    "desc": "Primary email for cryptographic security alerts, MFA challenges, and escalation notifications.",
    "type": "text",
    "scope": "User",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": "host@zonata.internal",
    "options": []
  },
  {
    "id": "acc_timezone",
    "category": "account",
    "name": "Preferred Timezone",
    "desc": "User interface timestamp projection timezone.",
    "type": "select",
    "scope": "User",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": "Asia/Kolkata",
    "options": [
      "Asia/Kolkata",
      "UTC",
      "America/New_York",
      "Europe/London",
      "Asia/Dubai",
      "Asia/Singapore"
    ]
  },
  {
    "id": "acc_density",
    "category": "account",
    "name": "Interface Density",
    "desc": "",
    "type": "radio",
    "scope": "User",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": "comfortable",
    "options": [
      "compact",
      "comfortable"
    ]
  },
  {
    "id": "host_emergency_stop",
    "category": "host",
    "name": "Global Emergency Stop",
    "desc": "Immediately halts all AI background missions, terminal commands, and external mutations.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "CRITICAL",
    "default": false,
    "options": []
  },
  {
    "id": "host_authority_scope",
    "category": "host",
    "name": "Sovereign Authority Level",
    "desc": "Constitutional authority tier. Only the sovereign owner holds override rights.",
    "type": "status",
    "scope": "Host",
    "editable_by": "READ_ONLY",
    "risk": "LOW",
    "default": "SOVEREIGN_OWNER",
    "options": []
  },
  {
    "id": "host_killswitch_finances",
    "category": "host",
    "name": "Halt Financial Execution",
    "desc": "Immediately blocks all AI-initiated financial transactions, payments, and payouts.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": false,
    "options": []
  },
  {
    "id": "host_killswitch_desktop",
    "category": "host",
    "name": "Halt Desktop / OS Control",
    "desc": "Immediately cuts off robotic desktop mouse, keyboard, and OS window interaction.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": false,
    "options": []
  },
  {
    "id": "comp_legal_name",
    "category": "company",
    "name": "Legal Corporate Name",
    "desc": "Registered statutory entity name for compliance certificates and audit manifests.",
    "type": "text",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": "ZONATA Technologies Private Limited",
    "options": []
  },
  {
    "id": "comp_industry",
    "category": "company",
    "name": "Industry Sector",
    "desc": "Universal industry profile governing KPI templates and regulatory adapters.",
    "type": "select",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": "Universal Enterprise",
    "options": [
      "Universal Enterprise",
      "Hospitality & Tourism",
      "SaaS & Software",
      "Manufacturing & Supply Chain",
      "Healthcare & Life Sciences",
      "E-Commerce & Retail",
      "Financial Services"
    ]
  },
  {
    "id": "comp_business_model",
    "category": "company",
    "name": "Business Model",
    "desc": "",
    "type": "multiselect",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": [
      "B2B",
      "Subscription",
      "Service"
    ],
    "options": [
      "B2B",
      "B2C",
      "B2B2C",
      "Marketplace",
      "Subscription",
      "Transactional",
      "Project-Based",
      "Service",
      "Hybrid"
    ]
  },
  {
    "id": "comp_base_currency",
    "category": "company",
    "name": "Base Currency",
    "desc": "",
    "type": "select",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": "INR (\u20b9)",
    "options": [
      "INR (\u20b9)",
      "USD ($)",
      "EUR (\u20ac)",
      "GBP (\u00a3)",
      "AED (\u062f.\u0625)",
      "SGD (S$)"
    ]
  },
  {
    "id": "org_hierarchy_enforcement",
    "category": "organization",
    "name": "12-Level Hierarchy Enforcement",
    "desc": "Enforces strict L0-L11 reporting chains, span-of-control bounds, and delegation envelopes.",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": true,
    "options": []
  },
  {
    "id": "org_max_exec_span",
    "category": "organization",
    "name": "Executive Span of Control Limit",
    "desc": "Maximum direct reports permitted for C-Suite nodes before mandatory delegation.",
    "type": "number",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": 8,
    "options": []
  },
  {
    "id": "rbac_default_role",
    "category": "users",
    "name": "Default Invited Role",
    "desc": "",
    "type": "select",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": "OPERATOR",
    "options": [
      "OBSERVER",
      "OPERATOR",
      "MANAGER",
      "EXECUTIVE"
    ]
  },
  {
    "id": "rbac_two_person_rule",
    "category": "users",
    "name": "Enforce Two-Person Rule",
    "desc": "Requires two distinct authenticated operators for high-risk financial or policy operations.",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "ai_master_enablement",
    "category": "ai",
    "name": "AI System Global Enablement",
    "desc": "Master enable/disable toggle for all AI models, reasoning engines, and background tasks.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "CRITICAL",
    "default": true,
    "options": []
  },
  {
    "id": "ai_reasoning_depth",
    "category": "ai",
    "name": "Reasoning Depth Policy",
    "desc": "",
    "type": "radio",
    "scope": "Host",
    "editable_by": "SHARED",
    "risk": "LOW",
    "default": "balanced",
    "options": [
      "concise",
      "balanced",
      "deep_strategic"
    ]
  },
  {
    "id": "ai_prompt_injection_guard",
    "category": "ai",
    "name": "Prompt Injection Firewall",
    "desc": "Scans all inbound inputs and tool outputs for adversarial prompt injection patterns.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "ai_primary_provider",
    "category": "ai_providers",
    "name": "Primary Inference Provider",
    "desc": "",
    "type": "select",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": "Google Vertex AI / Gemini",
    "options": [
      "Google Vertex AI / Gemini",
      "Anthropic Claude",
      "OpenAI GPT",
      "Local Self-Hosted (vLLM / Ollama)"
    ]
  },
  {
    "id": "ai_gemini_api_token",
    "category": "ai_providers",
    "name": "Gemini API Token",
    "desc": "Cryptographically masked bearer credential for Gemini API.",
    "type": "token",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": "AIzaSy\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022",
    "options": []
  },
  {
    "id": "ai_circuit_breaker_retries",
    "category": "ai_providers",
    "name": "Provider Max Retries",
    "desc": "",
    "type": "number",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": 3,
    "options": []
  },
  {
    "id": "ceo_autonomy_level",
    "category": "ai_ceo",
    "name": "CEO Autonomy Level",
    "desc": "Strict constitutional ceiling. CEO cannot promote itself to a higher level.",
    "type": "select",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "CRITICAL",
    "default": "Level 3 \u2014 Execute Within Policy",
    "options": [
      "Level 0 \u2014 Observe Only",
      "Level 1 \u2014 Recommend Only",
      "Level 2 \u2014 Execute With Approval",
      "Level 3 \u2014 Execute Within Policy",
      "Level 4 \u2014 Strategic Autonomous Operation"
    ]
  },
  {
    "id": "ceo_spending_limit",
    "category": "ai_ceo",
    "name": "CEO Autonomous Spending Cap",
    "desc": "Maximum single financial allocation the CEO may execute without explicit Host approval.",
    "type": "currency",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": 50000,
    "options": []
  },
  {
    "id": "ceo_council_enabled",
    "category": "ai_ceo",
    "name": "Executive Council Peer Review",
    "desc": "Mandates multi-perspective peer review by COO, CFO, and CTO personas prior to strategic actions.",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": true,
    "options": []
  },
  {
    "id": "ceo_continuous_cognition_mins",
    "category": "ai_ceo",
    "name": "Continuous Cognition Interval",
    "desc": "Scheduled interval for proactive enterprise heartbeat, risk scans, and opportunity evaluation.",
    "type": "number",
    "scope": "Company",
    "editable_by": "SHARED",
    "risk": "LOW",
    "default": 15,
    "options": []
  },
  {
    "id": "wf_max_concurrent_agents",
    "category": "workforce",
    "name": "Max Concurrent Active Agents",
    "desc": "Upper concurrency boundary on parallel running agent processes.",
    "type": "number",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": 16,
    "options": []
  },
  {
    "id": "wf_autonomous_spawning",
    "category": "workforce",
    "name": "Allow Autonomous Agent Spawning",
    "desc": "Permits AI CEO to dynamically create task-specific agents under constitutional template rules.",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "af_mandatory_simulation",
    "category": "agent_factory",
    "name": "Mandatory Pre-Deployment Simulation",
    "desc": "New agents must pass 100% of benchmark unit simulations before receiving operational missions.",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "mission_outcome_verification",
    "category": "missions",
    "name": "Mandatory Outcome Verification Gate",
    "desc": "Missions are never marked SUCCESS on task exit codes alone; measurable business outcomes are verified.",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": true,
    "options": []
  },
  {
    "id": "mission_retry_limit",
    "category": "missions",
    "name": "Mission Max Retries",
    "desc": "",
    "type": "number",
    "scope": "Company",
    "editable_by": "SHARED",
    "risk": "LOW",
    "default": 3,
    "options": []
  },
  {
    "id": "wf_durable_checkpointing",
    "category": "workflows",
    "name": "Durable Step Checkpointing",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": true,
    "options": []
  },
  {
    "id": "tools_sandboxed_exec",
    "category": "tools",
    "name": "Sandboxed Execution Mandatory",
    "desc": "All tool invocations run within isolated filesystem and process boundaries.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "tools_authority_ceiling",
    "category": "tools",
    "name": "Default Authority Ceiling",
    "desc": "",
    "type": "select",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": "ASK_ME",
    "options": [
      "SANDBOXED_READ_ONLY",
      "AUTOMATIC_IDEMPOTENT",
      "ASK_ME",
      "NEVER_ALLOWED"
    ]
  },
  {
    "id": "mcp_allow_external_servers",
    "category": "mcp",
    "name": "Allow External MCP Servers",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": true,
    "options": []
  },
  {
    "id": "a2a_inter_agent_auth",
    "category": "a2a",
    "name": "Cryptographic Agent Token Exchange",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "desk_enable_control",
    "category": "desktop",
    "name": "Enable Desktop Perception & Control",
    "desc": "Enables computer-use perception, OS window management, and pointer interaction.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "CRITICAL",
    "default": true,
    "options": []
  },
  {
    "id": "desk_fps_limit",
    "category": "desktop",
    "name": "Perception Screen Sampling Rate (FPS)",
    "desc": "",
    "type": "slider",
    "scope": "Host",
    "editable_by": "SHARED",
    "risk": "LOW",
    "default": 2,
    "options": []
  },
  {
    "id": "browser_headless_mode",
    "category": "browser",
    "name": "Headless Browser Automation",
    "desc": "",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": true,
    "options": []
  },
  {
    "id": "browser_ssrf_protection",
    "category": "browser",
    "name": "Strict SSRF & Private Network Egress Filter",
    "desc": "",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "term_execution_enabled",
    "category": "terminal",
    "name": "Terminal Command Execution Enabled",
    "desc": "",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "CRITICAL",
    "default": true,
    "options": []
  },
  {
    "id": "term_max_lease_seconds",
    "category": "terminal",
    "name": "Command Execution Lease TTL (Seconds)",
    "desc": "",
    "type": "number",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": 60,
    "options": []
  },
  {
    "id": "openhands_repo_sandbox",
    "category": "openhands",
    "name": "Sandboxed Code Execution & Git Branch Isolation",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "integ_least_privilege",
    "category": "integrations",
    "name": "Enforce Least Privilege Sync Mappings",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": true,
    "options": []
  },
  {
    "id": "data_retention_days",
    "category": "data",
    "name": "Operational Context Retention (Days)",
    "desc": "",
    "type": "number",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": 365,
    "options": []
  },
  {
    "id": "files_max_upload_mb",
    "category": "files",
    "name": "Max Upload Size (MB)",
    "desc": "",
    "type": "number",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": 50,
    "options": []
  },
  {
    "id": "records_deduplication",
    "category": "records",
    "name": "Automatic Deterministic Deduplication",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": true,
    "options": []
  },
  {
    "id": "fin_accounting_method",
    "category": "finance",
    "name": "Accounting Method",
    "desc": "",
    "type": "select",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": "Accrual Basis (GAAP/IFRS)",
    "options": [
      "Accrual Basis (GAAP/IFRS)",
      "Cash Basis"
    ]
  },
  {
    "id": "fin_high_expense_approval",
    "category": "finance",
    "name": "Expense Threshold Requiring Owner Approval",
    "desc": "",
    "type": "currency",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": 25000,
    "options": []
  },
  {
    "id": "notify_critical_sms",
    "category": "notifications",
    "name": "Immediate SMS Alerts on Kill Switch / Breach",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": true,
    "options": []
  },
  {
    "id": "appr_auto_escalation_hours",
    "category": "approvals",
    "name": "Escalation Timeout (Hours)",
    "desc": "",
    "type": "number",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": 24,
    "options": []
  },
  {
    "id": "gov_kill_switch_active",
    "category": "governance",
    "name": "Emergency Quarantine Isolation Mode",
    "desc": "Isolates company instance and aborts any active or incoming mutation commands.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "CRITICAL",
    "default": false,
    "options": []
  },
  {
    "id": "priv_pii_masking",
    "category": "privacy",
    "name": "Automated PII Sanitization & Masking",
    "desc": "Redacts customer phone numbers, Aadhaar/SSN, emails, and credit cards from model prompts.",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "comp_regulatory_profile",
    "category": "compliance",
    "name": "Statutory Governance Profile",
    "desc": "",
    "type": "select",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": "ISO 37000 / ISO 42001 (Global)",
    "options": [
      "ISO 37000 / ISO 42001 (Global)",
      "SOC 2 Type II",
      "EU GDPR & AI Act",
      "India DPDPA 2023"
    ]
  },
  {
    "id": "audit_ledger_hashing",
    "category": "audit",
    "name": "Cryptographic Hash Algorithm",
    "desc": "Immutable ledger cryptographic receipt hashing standard.",
    "type": "status",
    "scope": "Host",
    "editable_by": "READ_ONLY",
    "risk": "LOW",
    "default": "SHA-256 (Merkle Tree)",
    "options": []
  },
  {
    "id": "audit_immutability_mode",
    "category": "audit",
    "name": "Immutability Enforcement",
    "desc": "",
    "type": "status",
    "scope": "Host",
    "editable_by": "READ_ONLY",
    "risk": "LOW",
    "default": "STRICT_APPEND_ONLY",
    "options": []
  },
  {
    "id": "sec_require_mfa",
    "category": "security",
    "name": "Require Multi-Factor Authentication (MFA)",
    "desc": "Forces WebAuthn FIDO2 passkey or TOTP 2FA for all administrative logins.",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "sec_session_duration_hours",
    "category": "security",
    "name": "Session Maximum Lifetime (Hours)",
    "desc": "",
    "type": "select",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": 12,
    "options": [
      1,
      4,
      8,
      12,
      24,
      72
    ]
  },
  {
    "id": "sec_device_trust",
    "category": "security",
    "name": "Device Trust Enforced",
    "desc": "",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "cost_global_budget_monthly",
    "category": "usage",
    "name": "Global AI Compute Monthly Spending Cap",
    "desc": "Hard spending ceiling across all LLM inference, browser scraping, and cloud execution.",
    "type": "currency",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": 100000,
    "options": []
  },
  {
    "id": "cost_alert_threshold_pct",
    "category": "usage",
    "name": "Budget Warning Alert Threshold",
    "desc": "",
    "type": "select",
    "scope": "Company",
    "editable_by": "SHARED",
    "risk": "LOW",
    "default": "80%",
    "options": [
      "50%",
      "75%",
      "80%",
      "90%",
      "100%"
    ]
  },
  {
    "id": "bill_plan_tier",
    "category": "billing",
    "name": "Current Subscription Tier",
    "desc": "",
    "type": "status",
    "scope": "Company",
    "editable_by": "READ_ONLY",
    "risk": "LOW",
    "default": "SOVEREIGN ENTERPRISE",
    "options": []
  },
  {
    "id": "api_rate_limit_rpm",
    "category": "api",
    "name": "API Rate Limit (Requests / Min)",
    "desc": "",
    "type": "number",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": 1200,
    "options": []
  },
  {
    "id": "webhook_verify_signatures",
    "category": "webhooks",
    "name": "HMAC-SHA256 Signature Verification",
    "desc": "",
    "type": "toggle",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": true,
    "options": []
  },
  {
    "id": "loc_date_format",
    "category": "localization",
    "name": "Date Presentation Format",
    "desc": "",
    "type": "select",
    "scope": "Company",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": "YYYY-MM-DD",
    "options": [
      "YYYY-MM-DD",
      "DD/MM/YYYY",
      "MM/DD/YYYY"
    ]
  },
  {
    "id": "app_theme",
    "category": "appearance",
    "name": "Color Scheme Theme",
    "desc": "",
    "type": "select",
    "scope": "User",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": "dark",
    "options": [
      "dark",
      "light",
      "system"
    ]
  },
  {
    "id": "app_high_contrast",
    "category": "appearance",
    "name": "High Contrast Mode",
    "desc": "",
    "type": "toggle",
    "scope": "User",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": false,
    "options": []
  },
  {
    "id": "rec_auto_snapshot_frequency",
    "category": "recovery",
    "name": "Automated SQLite Snapshot Interval",
    "desc": "",
    "type": "select",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": "Every 6 Hours",
    "options": [
      "Hourly",
      "Every 6 Hours",
      "Daily",
      "Weekly"
    ]
  },
  {
    "id": "mon_health_probe_interval_s",
    "category": "monitoring",
    "name": "Health Probe Frequency (Seconds)",
    "desc": "",
    "type": "number",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": 30,
    "options": []
  },
  {
    "id": "ent_scim_provisioning",
    "category": "enterprise",
    "name": "SCIM Directory Sync",
    "desc": "",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": true,
    "options": []
  },
  {
    "id": "flag_hal_multimodal",
    "category": "features",
    "name": "Enable HAL Multimodal Video Diagnostics",
    "desc": "",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "LOW",
    "default": true,
    "options": []
  },
  {
    "id": "adv_debug_logging",
    "category": "advanced",
    "name": "Extended Kernel Trace & Debug Logging",
    "desc": "",
    "type": "toggle",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "MEDIUM",
    "default": false,
    "options": []
  },
  {
    "id": "danger_revoke_all_sessions",
    "category": "danger",
    "name": "Revoke All Active Tokens Immediately",
    "desc": "Invalidates every active browser, API, and worker bearer token across the host.",
    "type": "button_action",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "CRITICAL",
    "default": "REVOKE_ACTION",
    "options": []
  },
  {
    "id": "danger_purge_telemetry",
    "category": "danger",
    "name": "Purge Temporary Sandbox Logs",
    "desc": "Removes temporary terminal and browser scrape artifacts while preserving cryptographically sealed evidence.",
    "type": "button_action",
    "scope": "Host",
    "editable_by": "OWNER",
    "risk": "HIGH",
    "default": "PURGE_ACTION",
    "options": []
  }
];

  // Subcategory Tabs Map
  const SUBCATEGORIES_MAP = {
  "account": [
    {
      "id": "all",
      "name": "All Account"
    },
    {
      "id": "profile",
      "name": "Profile & Identity"
    },
    {
      "id": "preferences",
      "name": "Timezone & Density"
    }
  ],
  "host": [
    {
      "id": "all",
      "name": "All Sovereignty"
    },
    {
      "id": "sovereignty",
      "name": "Authority Level"
    },
    {
      "id": "emergency",
      "name": "Emergency Stops & Killswitches"
    }
  ],
  "company": [
    {
      "id": "all",
      "name": "All Company"
    },
    {
      "id": "profile",
      "name": "Corporate Identity"
    },
    {
      "id": "industry",
      "name": "Industry Profile"
    },
    {
      "id": "currency",
      "name": "Base Currency"
    }
  ],
  "organization": [
    {
      "id": "all",
      "name": "All Organization"
    },
    {
      "id": "hierarchy",
      "name": "12-Level Hierarchy"
    },
    {
      "id": "span",
      "name": "Executive Span of Control"
    }
  ],
  "users": [
    {
      "id": "all",
      "name": "All Access"
    },
    {
      "id": "rbac",
      "name": "RBAC Roles"
    },
    {
      "id": "twoperson",
      "name": "Two-Person Rule"
    }
  ],
  "ai": [
    {
      "id": "all",
      "name": "All AI Policy"
    },
    {
      "id": "enablement",
      "name": "Master Enablement"
    },
    {
      "id": "reasoning",
      "name": "Reasoning Depth"
    },
    {
      "id": "firewall",
      "name": "Prompt Injection Firewall"
    }
  ],
  "ai_providers": [
    {
      "id": "all",
      "name": "All Providers"
    },
    {
      "id": "primary",
      "name": "Primary Provider"
    },
    {
      "id": "credentials",
      "name": "API Tokens & Vault"
    },
    {
      "id": "resilience",
      "name": "Circuit Breaker & Retries"
    }
  ],
  "ai_ceo": [
    {
      "id": "all",
      "name": "All AI CEO"
    },
    {
      "id": "autonomy",
      "name": "Autonomy Level (0-4)"
    },
    {
      "id": "spending",
      "name": "Autonomous Spending Cap"
    },
    {
      "id": "council",
      "name": "Executive Council"
    },
    {
      "id": "cognition",
      "name": "Continuous Cognition"
    }
  ],
  "workforce": [
    {
      "id": "all",
      "name": "All Workforce"
    },
    {
      "id": "concurrency",
      "name": "Concurrency Caps"
    },
    {
      "id": "spawning",
      "name": "Autonomous Spawning"
    }
  ],
  "agent_factory": [
    {
      "id": "all",
      "name": "All Agent Factory"
    },
    {
      "id": "simulation",
      "name": "Simulation Gates"
    }
  ],
  "missions": [
    {
      "id": "all",
      "name": "All Missions"
    },
    {
      "id": "verification",
      "name": "Outcome Verification"
    },
    {
      "id": "retries",
      "name": "Retry Ceiling"
    }
  ],
  "workflows": [
    {
      "id": "all",
      "name": "All Workflows"
    },
    {
      "id": "checkpoints",
      "name": "Durable Checkpointing"
    }
  ],
  "tools": [
    {
      "id": "all",
      "name": "All Tools"
    },
    {
      "id": "sandboxing",
      "name": "Sandboxed Execution"
    },
    {
      "id": "authority",
      "name": "Authority Ceiling"
    }
  ],
  "mcp": [
    {
      "id": "all",
      "name": "All MCP"
    },
    {
      "id": "servers",
      "name": "External Servers"
    }
  ],
  "a2a": [
    {
      "id": "all",
      "name": "All A2A"
    },
    {
      "id": "tokens",
      "name": "Token Exchange"
    }
  ],
  "desktop": [
    {
      "id": "all",
      "name": "All Desktop"
    },
    {
      "id": "control",
      "name": "OS Control Enablement"
    },
    {
      "id": "sampling",
      "name": "Screen Sampling Rate (FPS)"
    }
  ],
  "browser": [
    {
      "id": "all",
      "name": "All Browser"
    },
    {
      "id": "headless",
      "name": "Headless Mode"
    },
    {
      "id": "ssrf",
      "name": "SSRF & Egress Protection"
    }
  ],
  "terminal": [
    {
      "id": "all",
      "name": "All Terminal"
    },
    {
      "id": "execution",
      "name": "Shell Execution"
    },
    {
      "id": "lease",
      "name": "TTL Lease Duration"
    }
  ],
  "openhands": [
    {
      "id": "all",
      "name": "All Code Execution"
    },
    {
      "id": "sandbox",
      "name": "Repo Sandboxing"
    }
  ],
  "integrations": [
    {
      "id": "all",
      "name": "All Integrations"
    },
    {
      "id": "mappings",
      "name": "Least Privilege Mappings"
    }
  ],
  "data": [
    {
      "id": "all",
      "name": "All Data"
    },
    {
      "id": "retention",
      "name": "Context Retention"
    }
  ],
  "files": [
    {
      "id": "all",
      "name": "All Files"
    },
    {
      "id": "quotas",
      "name": "Upload Quotas"
    }
  ],
  "records": [
    {
      "id": "all",
      "name": "All Records"
    },
    {
      "id": "dedup",
      "name": "Deterministic Deduplication"
    }
  ],
  "finance": [
    {
      "id": "all",
      "name": "All Finance"
    },
    {
      "id": "accounting",
      "name": "Accounting Method"
    },
    {
      "id": "approvals",
      "name": "Expense Approvals"
    }
  ],
  "notifications": [
    {
      "id": "all",
      "name": "All Notifications"
    },
    {
      "id": "critical",
      "name": "Critical SMS Alerts"
    }
  ],
  "approvals": [
    {
      "id": "all",
      "name": "All Approvals"
    },
    {
      "id": "escalation",
      "name": "Auto-Escalation"
    }
  ],
  "governance": [
    {
      "id": "all",
      "name": "All Governance"
    },
    {
      "id": "quarantine",
      "name": "Quarantine Killswitch"
    }
  ],
  "privacy": [
    {
      "id": "all",
      "name": "All Privacy"
    },
    {
      "id": "masking",
      "name": "PII Sanitization"
    }
  ],
  "compliance": [
    {
      "id": "all",
      "name": "All Compliance"
    },
    {
      "id": "profile",
      "name": "Statutory Profile"
    }
  ],
  "audit": [
    {
      "id": "all",
      "name": "All Audit"
    },
    {
      "id": "ledger",
      "name": "Cryptographic Ledger"
    },
    {
      "id": "immutability",
      "name": "Immutability Mode"
    }
  ],
  "security": [
    {
      "id": "all",
      "name": "All Security"
    },
    {
      "id": "mfa",
      "name": "MFA & Passkeys"
    },
    {
      "id": "sessions",
      "name": "Session Lifetimes"
    },
    {
      "id": "device",
      "name": "Device Trust"
    }
  ],
  "usage": [
    {
      "id": "all",
      "name": "All Costs"
    },
    {
      "id": "cap",
      "name": "Compute Spend Cap"
    },
    {
      "id": "alerts",
      "name": "Threshold Alerts"
    }
  ],
  "billing": [
    {
      "id": "all",
      "name": "All Billing"
    },
    {
      "id": "plan",
      "name": "Subscription Tier"
    }
  ],
  "api": [
    {
      "id": "all",
      "name": "All API"
    },
    {
      "id": "limits",
      "name": "Rate Limits"
    }
  ],
  "webhooks": [
    {
      "id": "all",
      "name": "All Webhooks"
    },
    {
      "id": "signatures",
      "name": "Signature Verification"
    }
  ],
  "localization": [
    {
      "id": "all",
      "name": "All Localization"
    },
    {
      "id": "formats",
      "name": "Date Presentation"
    }
  ],
  "appearance": [
    {
      "id": "all",
      "name": "All Appearance"
    },
    {
      "id": "theme",
      "name": "Color Scheme Theme"
    },
    {
      "id": "contrast",
      "name": "High Contrast Mode"
    }
  ],
  "recovery": [
    {
      "id": "all",
      "name": "All Recovery"
    },
    {
      "id": "snapshots",
      "name": "SQLite Snapshots"
    }
  ],
  "monitoring": [
    {
      "id": "all",
      "name": "All Monitoring"
    },
    {
      "id": "probes",
      "name": "Liveness Probes"
    }
  ],
  "enterprise": [
    {
      "id": "all",
      "name": "All Enterprise"
    },
    {
      "id": "scim",
      "name": "SCIM Provisioning"
    }
  ],
  "features": [
    {
      "id": "all",
      "name": "All Features"
    },
    {
      "id": "canary",
      "name": "Canary Rollouts"
    }
  ],
  "advanced": [
    {
      "id": "all",
      "name": "All Advanced"
    },
    {
      "id": "engine",
      "name": "Runtime Engine Tuning"
    }
  ],
  "danger": [
    {
      "id": "all",
      "name": "All Danger Zone"
    },
    {
      "id": "emergency",
      "name": "Emergency Actions"
    }
  ]
};

  // Route alias normalization map
  const ROUTE_ALIASES = {
    'ai-ceo': 'ai_ceo',
    'ai/ceo': 'ai_ceo',
    'ai-providers': 'ai_providers',
    'ai/providers': 'ai_providers',
    'ai/cost': 'usage',
    'agent-factory': 'agent_factory',
    'missions-autonomy': 'missions',
    'code-execution': 'openhands',
    'audit-evidence': 'audit'
  };

  // State Management
  let activeView = 'hub'; // 'hub' or category ID
  let activeSubTab = 'all'; // sub-category filter tab
  let categoriesCatalog = [...DEFAULT_CATEGORIES];
  let currentCategoryData = null;
  let stagedValues = {};
  let originalValues = {};
  let hasUnsavedChanges = false;
  let activeScope = 'Company'; // 'Host', 'Company', 'Department', 'User'
  let globalSearchQuery = '';
  let searchDropdownResults = [];
  let isSearchDropdownOpen = false;
  let activeQuickFilter = 'all'; // 'all', 'owner', 'ceo', 'execution', 'attention', 'recent', 'audit'
  let effectiveStateCache = {};
  let authEnvironment = { environment: 'development', strict_auth: false, auth_mode: 'DEV_BOOTSTRAP' };
  let auditEventsList = [];
  let showAuditDrawer = false;
  let auditFilter = 'all'; // 'all', 'SOVEREIGN_HOST', 'AI_CEO'
  let previewPendingChange = null;
  let activeTestResult = null;
  let isInitialized = false;

  // Initialize service
  async function init() {
    if (isInitialized) return;
    isInitialized = true;
    setupKeyboardShortcuts();
    await fetchEnvironment();
    await fetchCategories();
    await fetchEffectiveState();
  }

  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Cmd+K or Ctrl+K or '/' focuses settings search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        const searchInput = document.getElementById('settingsGlobalSearch');
        if (searchInput) {
          e.preventDefault();
          searchInput.focus();
          searchInput.select();
        }
      } else if (e.key === 'Escape') {
        closeSearchDropdown();
        if (previewPendingChange) cancelPreview();
        if (activeTestResult) closeDiagnosticTestModal();
        if (showAuditDrawer) toggleAuditDrawer();
      }
    });

    // Close search dropdown on click outside
    document.addEventListener('click', (e) => {
      const searchBox = document.querySelector('.settings-search-box');
      if (searchBox && !searchBox.contains(e.target)) {
        closeSearchDropdown();
      }
    });
  }

  async function fetchEnvironment() {
    try {
      const res = await fetch('/api/auth/environment');
      if (res.ok) {
        authEnvironment = await res.json();
      }
    } catch (e) {
      console.warn('[Settings] Failed to fetch auth environment:', e);
    }
  }

  async function fetchCategories() {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data = await res.json();
        if (data.categories && data.categories.length > 0) {
          categoriesCatalog = data.categories;
          // If we are currently on hub, re-render to reflect live category statuses
          if (activeView === 'hub') {
            renderRoute();
          }
        }
      }
    } catch (e) {
      console.warn('[Settings] Failed to load categories catalog:', e);
    }
  }

  async function fetchEffectiveState() {
    try {
      const res = await fetch('/api/settings/effective');
      if (res.ok) {
        const data = await res.json();
        effectiveStateCache = data.effective_enforcement || {};
      }
    } catch (e) {
      console.warn('[Settings] Failed to fetch effective runtime state:', e);
    }
  }

  async function loadCategory(categoryId) {
    categoryId = normalizeCategoryId(categoryId);
    activeView = categoryId;
    activeSubTab = 'all';
    stagedValues = {};
    originalValues = {};
    hasUnsavedChanges = false;
    currentCategoryData = null;

    renderRoute(); // Show loading state immediately

    try {
      const res = await fetch(`/api/settings/category/${categoryId}`);
      if (res.ok) {
        currentCategoryData = await res.json();
        if (currentCategoryData.settings) {
          currentCategoryData.settings.forEach(s => {
            originalValues[s.id] = s.value;
            stagedValues[s.id] = s.value;
          });
        }
      }
    } catch (e) {
      console.error(`[Settings] Failed to load category '${categoryId}':`, e);
    }
    renderRoute();
  }

  function normalizeCategoryId(raw) {
    if (!raw) return 'hub';
    let clean = raw.trim().toLowerCase().replace(/^\/+/, '').replace(/^settings\/?/, '');
    if (!clean || clean === 'hub') return 'hub';
    return ROUTE_ALIASES[clean] || clean;
  }

  // Master Route Handler
  function render(route) {
    const rawCategory = (route || '').replace(/^\/settings\/?/, '').trim();
    if (!rawCategory || rawCategory === 'hub') {
      activeView = 'hub';
      renderRoute();
    } else {
      const norm = normalizeCategoryId(rawCategory);
      if (activeView !== norm || !currentCategoryData) {
        loadCategory(norm);
      } else {
        renderRoute();
      }
    }
  }

  function renderRoute() {
    const container = document.getElementById('view-settings');
    if (!container) return;

    if (activeView === 'hub') {
      renderSettingsHub(container);
    } else {
      renderCategoryDetail(container);
    }
  }

  // --------------------------------------------------------------------------
  // 1. SETTINGS HOME / HUB VIEW (Square/Card-Based Control Plane)
  // --------------------------------------------------------------------------
  function renderSettingsHub(container) {
    const totalCategories = categoriesCatalog.length || 43;
    const currentComp = (window.state && window.state.activeCompany) ? window.state.activeCompany.name : 'ZONATA Primary Enterprise';
    const currentUser = (window.state && window.state.host) ? window.state.host.name : 'Sukhraj Singh';
    const userRole = (window.state && window.state.host) ? window.state.host.role : 'SOVEREIGN_HOST';

    let filteredCats = categoriesCatalog.filter(cat => {
      if (globalSearchQuery) {
        const q = globalSearchQuery.toLowerCase();
        return cat.name.toLowerCase().includes(q) ||
               cat.desc.toLowerCase().includes(q) ||
               cat.id.toLowerCase().includes(q) ||
               (cat.current_value_summary && cat.current_value_summary.toLowerCase().includes(q));
      }
      return true;
    });

    if (activeQuickFilter === 'owner') {
      filteredCats = filteredCats.filter(c => c.scope === 'Host');
    } else if (activeQuickFilter === 'ceo') {
      filteredCats = filteredCats.filter(c => c.group_id === 'ai_system');
    } else if (activeQuickFilter === 'execution') {
      filteredCats = filteredCats.filter(c => c.group_id === 'execution');
    } else if (activeQuickFilter === 'attention') {
      filteredCats = filteredCats.filter(c => c.status === 'Attention' || c.status === 'Warning');
    } else if (activeQuickFilter === 'recent') {
      filteredCats = filteredCats.slice(0, 12);
    }

    container.innerHTML = `
      <div class="settings-center-root">
        <!-- Enterprise Header Bar -->
        <div class="settings-header-banner">
          <div class="settings-header-main">
            <div class="settings-title-row">
              <div class="settings-badge-pill">CONTROL PLANE // SOVEREIGN ENGINE</div>
              <h1>Settings</h1>
            </div>
            <p class="settings-subtitle">Configure and govern your ZONATA universal company operating environment.</p>
          </div>
          <div class="settings-meta-summary">
            <div class="settings-meta-chip">
              <span class="chip-label">Company:</span>
              <span class="chip-val">${escapeHtml(currentComp)}</span>
            </div>
            <div class="settings-meta-chip">
              <span class="chip-label">Authority:</span>
              <span class="chip-val">Sovereign Host</span>
            </div>
            <div class="settings-meta-chip">
              <span class="chip-label">Operator:</span>
              <span class="chip-val">${escapeHtml(currentUser)} (${escapeHtml(userRole)})</span>
            </div>
            <div class="settings-meta-chip environment-chip ${authEnvironment.environment}">
              <span class="chip-pulse"></span>
              <span class="chip-label">Mode:</span>
              <span class="chip-val">${authEnvironment.environment.toUpperCase()}</span>
            </div>
          </div>
        </div>

        <!-- Health Vitals Bar (6 Semantic Status Cards, Zero Analytics Charts) -->
        <div class="settings-vitals-grid">
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('security')" title="Open Security & MFA">
            <div class="vital-icon-box">🔐</div>
            <div class="vital-info">
              <div class="vital-title">Security & MFA</div>
              <div class="vital-state"><span class="pulse-dot green"></span>Healthy • Enforced</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('ai')" title="Open AI Global Policy">
            <div class="vital-icon-box">🧠</div>
            <div class="vital-info">
              <div class="vital-title">AI Global Policy</div>
              <div class="vital-state"><span class="pulse-dot green"></span>Configured • Firewall ON</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('ai_ceo')" title="Open AI CEO Governance">
            <div class="vital-icon-box">👑</div>
            <div class="vital-info">
              <div class="vital-title">AI CEO Governance</div>
              <div class="vital-state"><span class="pulse-dot green"></span>Operational • Level 3</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('integrations')" title="Open Integrations">
            <div class="vital-icon-box">🔗</div>
            <div class="vital-info">
              <div class="vital-title">Integrations Fabric</div>
              <div class="vital-state"><span class="pulse-dot green"></span>Connected • Least-Privilege</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('audit')" title="Open Evidence Ledger">
            <div class="vital-icon-box">⛓️</div>
            <div class="vital-info">
              <div class="vital-title">Evidence Ledger</div>
              <div class="vital-state"><span class="pulse-dot green"></span>Verified • SHA-256 Merkle</div>
            </div>
          </div>
          <div class="vital-card vital-healthy" onclick="EnterpriseSettings.navigateTo('recovery')" title="Open Disaster Recovery">
            <div class="vital-icon-box">💾</div>
            <div class="vital-info">
              <div class="vital-title">Disaster Recovery</div>
              <div class="vital-state"><span class="pulse-dot green"></span>Healthy • Snapshot Active</div>
            </div>
          </div>
        </div>

        <!-- Search & Filter Controls -->
        <div class="settings-toolbar">
          <div class="settings-search-box">
            <svg class="search-lens-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input 
              id="settingsGlobalSearch"
              type="text" 
              placeholder="Search settings by name, category, provider, key, or permission (e.g. 'MFA', 'spending', 'Claude', 'backup')..." 
              value="${escapeHtml(globalSearchQuery)}" 
              oninput="EnterpriseSettings.handleSearch(this.value)"
              onfocus="EnterpriseSettings.handleSearchFocus()"
              autocomplete="off"
            />
            <div class="search-actions-box">
              <span class="keyboard-hint">⌘K</span>
              ${globalSearchQuery ? `<button class="clear-search-btn" onclick="EnterpriseSettings.handleSearch('')" title="Clear search">✕</button>` : ''}
            </div>

            <!-- Instant Search Dropdown Box (Section 5 & 132) -->
            ${isSearchDropdownOpen && searchDropdownResults.length > 0 ? `
              <div class="settings-search-dropdown" id="settingsSearchDropdown">
                <div class="dropdown-header">
                  <span>Found ${searchDropdownResults.length} matching settings:</span>
                  <span class="dropdown-shortcut">ESC to close</span>
                </div>
                <div class="dropdown-list">
                  ${searchDropdownResults.slice(0, 10).map(item => `
                    <div class="search-result-item" onclick="EnterpriseSettings.selectSearchResult('${item.id}', '${item.category}')">
                      <div class="result-left">
                        <div class="result-title-row">
                          <span class="result-name">${highlightMatch(item.name, globalSearchQuery)}</span>
                          <span class="result-cat-badge">${escapeHtml(getCategoryName(item.category))}</span>
                        </div>
                        <p class="result-desc">${highlightMatch(item.desc, globalSearchQuery)}</p>
                      </div>
                      <div class="result-right">
                        <span class="result-val">Val: <code>${escapeHtml(String(item.default).slice(0, 20))}</code></span>
                        <span class="result-scope">${escapeHtml(item.scope)}</span>
                        <button class="result-jump-btn">Open →</button>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}
          </div>

          <!-- Quick Filter Pills -->
          <div class="settings-filter-pills">
            <button class="filter-pill ${activeQuickFilter === 'all' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('all')">All (${totalCategories})</button>
            <button class="filter-pill ${activeQuickFilter === 'owner' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('owner')">Host Controlled</button>
            <button class="filter-pill ${activeQuickFilter === 'ceo' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('ceo')">AI CEO Managed</button>
            <button class="filter-pill ${activeQuickFilter === 'execution' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('execution')">Execution Fabric</button>
            <button class="filter-pill ${activeQuickFilter === 'attention' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('attention')">Attention & Warnings</button>
            <button class="filter-pill ${activeQuickFilter === 'recent' ? 'active' : ''}" onclick="EnterpriseSettings.setQuickFilter('recent')">Recent</button>
            <button class="filter-pill filter-pill-audit" onclick="EnterpriseSettings.openGlobalAudit()">Audit Ledger Shortcut →</button>
          </div>
        </div>

        <!-- 6 Visual Category Groups Stack -->
        <div class="settings-groups-stack">
          ${GROUPS.map(grp => {
            const groupCats = filteredCats.filter(c => c.group_id === grp.id);
            if (groupCats.length === 0) return '';
            return `
              <div class="settings-group-section">
                <div class="settings-group-header">
                  <div class="group-title-row">
                    <span class="group-id-pill">${escapeHtml(grp.id.toUpperCase())}</span>
                    <h3>${escapeHtml(grp.name)}</h3>
                    <span class="group-count-badge">${groupCats.length} Categories</span>
                  </div>
                  <p class="group-desc">${escapeHtml(grp.desc)}</p>
                </div>

                <!-- 4-Column Square Grid of Compact Cards (Section 3 & 77) -->
                <div class="settings-cards-grid">
                  ${groupCats.map(cat => renderSquareCategoryCard(cat)).join('')}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  function renderSquareCategoryCard(cat) {
    const statusClass = (cat.status || 'Healthy').toLowerCase();
    const pulseColor = statusClass === 'healthy' ? 'green' : (statusClass === 'attention' ? 'amber' : 'red');
    const statusBadge = `<span class="cat-status-dot status-${statusClass}"><span class="pulse-dot ${pulseColor}"></span>${escapeHtml(cat.status || 'Healthy')}</span>`;

    return `
      <div class="settings-square-card" onclick="EnterpriseSettings.navigateTo('${cat.id}')" role="button" tabindex="0">
        <div class="square-card-top">
          <div class="square-icon-box">${cat.icon || '⚙️'}</div>
          ${statusBadge}
        </div>
        <div class="square-card-body">
          <h4 class="square-card-title">${escapeHtml(cat.name)}</h4>
          <p class="square-card-desc">${escapeHtml(cat.desc)}</p>
          <div class="square-card-value">
            <span class="val-label">Value:</span>
            <span class="val-text">${escapeHtml(cat.current_value_summary || 'Configured')}</span>
          </div>
        </div>
        <div class="square-card-footer">
          <span class="square-subset-tag">${escapeHtml(cat.scope || 'Company')} Scope</span>
          <span class="square-action-link">Open Category →</span>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 2. CATEGORY DETAIL VIEW (Compact Sidebar + Setting Card Grid)
  // --------------------------------------------------------------------------
  function renderCategoryDetail(container) {
    if (!currentCategoryData || !currentCategoryData.category) {
      container.innerHTML = `
        <div class="settings-loading-card">
          <div class="spinner-enterprise"></div>
          <h4>Loading Enterprise Control Plane</h4>
          <p>Retrieving cryptographic configuration and runtime enforcement state for <code>${escapeHtml(activeView)}</code>...</p>
        </div>
      `;
      return;
    }

    const cat = currentCategoryData.category;
    let settingsList = currentCategoryData.settings || [];
    const proposals = currentCategoryData.proposals || [];
    const audits = currentCategoryData.recent_audits || [];

    // Filter settings by sub-tab if activeSubTab is not 'all'
    const availableSubTabs = SUBCATEGORIES_MAP[cat.id] || [
      { id: 'all', name: 'All Settings' }
    ];

    if (activeSubTab !== 'all') {
      settingsList = settingsList.filter(s => {
        const targetId = activeSubTab.toLowerCase();
        return s.id.toLowerCase().includes(targetId) ||
               (s.name && s.name.toLowerCase().includes(targetId)) ||
               (s.desc && s.desc.toLowerCase().includes(targetId));
      });
    }

    container.innerHTML = `
      <div class="settings-detail-workspace">
        <!-- Left Sub-Navigation Sidebar -->
        <aside class="settings-detail-sidebar">
          <div class="sidebar-back-btn" onclick="EnterpriseSettings.navigateTo('hub')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            <span>All 43 Settings Hub</span>
          </div>
          
          <div class="sidebar-category-nav">
            ${GROUPS.map(grp => {
              const grpCats = categoriesCatalog.filter(c => c.group_id === grp.id);
              return `
                <div class="sidebar-nav-group">
                  <div class="sidebar-group-heading">${escapeHtml(grp.name.replace('GROUP ', ''))}</div>
                  ${grpCats.map(c => `
                    <button 
                      class="sidebar-nav-item ${c.id === cat.id ? 'active' : ''}" 
                      onclick="EnterpriseSettings.navigateTo('${c.id}')"
                    >
                      <span class="nav-icon">${c.icon}</span>
                      <span class="nav-name">${escapeHtml(c.name)}</span>
                    </button>
                  `).join('')}
                </div>
              `;
            }).join('')}
          </div>
        </aside>

        <!-- Right Main Settings Surface -->
        <main class="settings-detail-main">
          <!-- Unsaved Changes Alert Bar (Section 79) -->
          ${hasUnsavedChanges ? `
            <div class="settings-unsaved-banner">
              <div class="banner-text">
                <span class="banner-icon">⚠️</span>
                <span>You have unsaved staged modifications in <strong>${escapeHtml(cat.name)}</strong>.</span>
              </div>
              <div class="banner-actions">
                <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.discardChanges()">Discard All</button>
                <button class="btn btn-primary btn-sm" onclick="EnterpriseSettings.promptSaveCategory()">Save Changes (${Object.keys(stagedValues).filter(k => stagedValues[k] !== originalValues[k]).length})</button>
              </div>
            </div>
          ` : ''}

          <!-- Category Header & Scope Selector (Section 6 & 7) -->
          <div class="category-header-panel">
            <div class="category-breadcrumbs">
              <a href="#/settings" onclick="EnterpriseSettings.navigateTo('hub')">Home</a>
              <span class="sep">/</span>
              <a href="#/settings" onclick="EnterpriseSettings.navigateTo('hub')">Settings</a>
              <span class="sep">/</span>
              <span class="curr">${escapeHtml(cat.name)}</span>
            </div>

            <div class="category-title-bar">
              <div class="cat-title-left">
                <div class="cat-icon-large">${cat.icon || '⚙️'}</div>
                <div>
                  <h2>${escapeHtml(cat.name)}</h2>
                  <p class="cat-description">${escapeHtml(cat.desc)}</p>
                </div>
              </div>

              <!-- Scope & Inheritance Selector (Section 6 & 7) -->
              <div class="scope-selector-card">
                <div class="scope-row">
                  <span class="scope-label">Active Scope:</span>
                  <select class="scope-select" onchange="EnterpriseSettings.setScope(this.value)">
                    <option value="Host" ${activeScope === 'Host' ? 'selected' : ''}>Host Sovereign</option>
                    <option value="Company" ${activeScope === 'Company' ? 'selected' : ''}>Company Override</option>
                    <option value="Department" ${activeScope === 'Department' ? 'selected' : ''}>Department</option>
                    <option value="User" ${activeScope === 'User' ? 'selected' : ''}>User Profile</option>
                  </select>
                </div>
                <div class="inheritance-indicator">
                  <span class="indicator-badge badge-inherited">● Inherited from: Host Default</span>
                </div>
              </div>
            </div>

            <div class="category-actions-bar">
              <div class="actions-left">
                <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.resetToInherited()">Reset to Inherited</button>
                <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.toggleAuditDrawer()">Audit Trail (${audits.length})</button>
              </div>
              <div class="actions-right">
                <button class="btn btn-primary btn-sm" onclick="EnterpriseSettings.promptSaveCategory()" ${!hasUnsavedChanges ? 'disabled' : ''}>Save Changes</button>
              </div>
            </div>
          </div>

          <!-- Sub-Navigation Tabs Bar (Section 78 & 148: Category -> Subcategory -> Cards) -->
          ${availableSubTabs.length > 1 ? `
            <div class="sub-navigation-bar">
              ${availableSubTabs.map(tab => `
                <button 
                  class="sub-tab-btn ${activeSubTab === tab.id ? 'active' : ''}" 
                  onclick="EnterpriseSettings.setSubTab('${tab.id}')"
                >
                  ${escapeHtml(tab.name)}
                </button>
              `).join('')}
            </div>
          ` : ''}

          <!-- Pending AI CEO Proposals Banner (Section 84 & 135) -->
          ${proposals.length > 0 ? `
            <div class="proposals-block">
              <div class="proposals-header">
                <span class="proposals-badge">AI CEO Proposals (${proposals.length})</span>
                <span class="proposals-sub">Autonomous optimization proposals awaiting Sovereign approval</span>
              </div>
              <div class="proposals-list">
                ${proposals.map(p => `
                  <div class="proposal-card">
                    <div class="proposal-header">
                      <strong>${escapeHtml(p.setting_id)}:</strong> Proposed Value = <code>${JSON.stringify(p.proposed_value)}</code>
                      <span class="badge badge-warning">${escapeHtml(p.risk_level)} Risk</span>
                    </div>
                    <p class="proposal-reason"><strong>Reason:</strong> ${escapeHtml(p.reason)}</p>
                    <p class="proposal-benefit"><strong>Expected Benefit:</strong> ${escapeHtml(p.expected_benefit)}</p>
                    <div class="proposal-actions">
                      <button class="btn btn-success btn-sm" onclick="EnterpriseSettings.resolveProposal('${p.proposal_id}', 'APPROVED')">Approve Proposal</button>
                      <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.resolveProposal('${p.proposal_id}', 'REJECTED')">Reject</button>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          <!-- Grid of Setting Cards (Section 76 & 77) -->
          <div class="category-cards-grid">
            ${settingsList.length > 0 ? settingsList.map(s => renderSettingCard(s)).join('') : `
              <div class="empty-subtab-card">
                <p>No settings matching subcategory '<strong>${escapeHtml(activeSubTab)}</strong>'.</p>
                <button class="btn btn-secondary btn-sm" onclick="EnterpriseSettings.setSubTab('all')">Show All Settings</button>
              </div>
            `}
          </div>
        </main>
      </div>

      <!-- High-Impact Change Preview Modal (Section 80) -->
      ${previewPendingChange ? renderChangePreviewModal() : ''}

      <!-- Audit Drawer / Modal (Section 81 & 136) -->
      ${showAuditDrawer ? renderAuditDrawer(audits) : ''}

      <!-- Diagnostic Live Test Modal (Section 163) -->
      ${activeTestResult ? renderDiagnosticModal() : ''}
    `;
  }

  // --------------------------------------------------------------------------
  // 3. SETTING CARD RENDERER (Multi-Type Square/Near-Square Cards)
  // --------------------------------------------------------------------------
  function renderSettingCard(s) {
    const curVal = stagedValues.hasOwnProperty(s.id) ? stagedValues[s.id] : s.value;
    const isDirty = stagedValues.hasOwnProperty(s.id) && stagedValues[s.id] !== originalValues[s.id];
    const riskBadge = s.risk === 'CRITICAL' ? '<span class="policy-tag tag-critical">Critical Risk</span>' :
                      s.risk === 'HIGH' ? '<span class="policy-tag tag-high">High Risk</span>' :
                      '<span class="policy-tag tag-low">Standard</span>';

    const policyTags = [
      s.editable_by === 'OWNER' ? '<span class="policy-tag tag-owner">Owner Controlled</span>' : '',
      s.is_ceo_managed ? '<span class="policy-tag tag-ceo">Managed by AI CEO</span>' : '',
      s.editable_by === 'READ_ONLY' ? '<span class="policy-tag tag-readonly">Read Only</span>' : '',
      s.requires_approval ? '<span class="policy-tag tag-approval">Requires Approval</span>' : '',
      s.secret ? '<span class="policy-tag tag-secret">Sensitive Token</span>' : '',
      riskBadge
    ].filter(Boolean).join('');

    // Effective vs Configured proof (Section 199)
    const effectiveProof = `
      <div class="effective-runtime-pill">
        <span class="eff-label">Runtime Enforcement:</span>
        <span class="eff-val">${escapeHtml(String(s.effective_runtime_value !== undefined ? s.effective_runtime_value : curVal))}</span>
        <span class="eff-badge status-${(s.runtime_status || 'ACTIVE').toLowerCase()}">${escapeHtml(s.runtime_status || 'ACTIVE')}</span>
      </div>
    `;

    return `
      <div class="setting-card ${isDirty ? 'card-dirty' : ''}" id="card-${s.id}">
        <div class="card-head">
          <div class="card-title-line">
            <h5>${escapeHtml(s.name)}</h5>
            ${isDirty ? '<span class="badge badge-amber">Modified</span>' : ''}
          </div>
          <div class="policy-tags-row">${policyTags}</div>
        </div>

        <p class="card-desc">${escapeHtml(s.desc || '')}</p>

        <!-- Dynamic Control Area (Section 76) -->
        <div class="card-control-box">
          ${renderControlForSetting(s, curVal)}
        </div>

        <!-- Effective Runtime Status Proof (Section 199) -->
        ${effectiveProof}

        <!-- Card Footer (Section 147) -->
        <div class="card-footer-meta">
          <div class="footer-left">
            <span class="footer-scope">${escapeHtml(s.scope || 'Company')} Scope</span>
            <span class="footer-dot">•</span>
            <span class="footer-updated">v${s.version || 1}</span>
          </div>
          <div class="footer-right">
            ${s.type === 'token' ? `<button class="btn-text-xs" onclick="EnterpriseSettings.runDiagnosticTest('api_token')">Test Token</button>` : ''}
            ${s.category === 'browser' ? `<button class="btn-text-xs" onclick="EnterpriseSettings.runDiagnosticTest('browser_execution')">Test Browser</button>` : ''}
            ${s.category === 'terminal' ? `<button class="btn-text-xs" onclick="EnterpriseSettings.runDiagnosticTest('terminal_container')">Test Terminal</button>` : ''}
            ${s.category === 'recovery' ? `<button class="btn-text-xs" onclick="EnterpriseSettings.runDiagnosticTest('sqlite_backup')">Test Backup</button>` : ''}
            ${s.category === 'webhooks' ? `<button class="btn-text-xs" onclick="EnterpriseSettings.runDiagnosticTest('webhook_delivery')">Test Webhook</button>` : ''}
            <button class="btn-text-xs" onclick="EnterpriseSettings.viewSettingAudit('${s.id}')">Audit</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderControlForSetting(s, curVal) {
    switch (s.type) {
      case 'toggle':
        return `
          <label class="toggle-switch-wrapper">
            <input 
              type="checkbox" 
              ${curVal ? 'checked' : ''} 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              onchange="EnterpriseSettings.stageChange('${s.id}', this.checked)" 
            />
            <span class="toggle-slider"></span>
            <span class="toggle-state-text">${curVal ? 'ENABLED' : 'DISABLED'}</span>
          </label>
        `;

      case 'select':
        return `
          <select 
            class="setting-select-control" 
            ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
            onchange="EnterpriseSettings.stageChange('${s.id}', this.value)"
          >
            ${(s.options || []).map(opt => `
              <option value="${escapeHtml(opt)}" ${String(curVal) === String(opt) ? 'selected' : ''}>${escapeHtml(opt)}</option>
            `).join('')}
          </select>
        `;

      case 'number':
        return `
          <div class="number-control-box">
            <input 
              type="number" 
              class="setting-input-control" 
              value="${curVal}" 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              oninput="EnterpriseSettings.stageChange('${s.id}', parseFloat(this.value) || 0)" 
            />
          </div>
        `;

      case 'currency':
        return `
          <div class="currency-control-box">
            <span class="currency-prefix">₹</span>
            <input 
              type="number" 
              class="setting-input-control" 
              value="${curVal}" 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              oninput="EnterpriseSettings.stageChange('${s.id}', parseFloat(this.value) || 0)" 
            />
          </div>
        `;

      case 'token':
        return `
          <div class="token-control-box">
            <input 
              type="password" 
              class="setting-input-control token-input" 
              value="${escapeHtml(curVal)}" 
              id="token-${s.id}" 
              ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
              oninput="EnterpriseSettings.stageChange('${s.id}', this.value)" 
            />
            <button class="btn btn-secondary btn-xs" onclick="EnterpriseSettings.toggleTokenVisibility('token-${s.id}')">Reveal</button>
            <button class="btn btn-secondary btn-xs" onclick="EnterpriseSettings.runDiagnosticTest('api_token')">Test</button>
          </div>
        `;

      case 'slider':
        return `
          <div class="slider-control-box">
            <input 
              type="range" 
              min="1" 
              max="10" 
              value="${curVal}" 
              class="setting-slider" 
              oninput="EnterpriseSettings.stageChange('${s.id}', parseInt(this.value)); document.getElementById('val-${s.id}').innerText = this.value + ' FPS';" 
            />
            <span class="slider-readout" id="val-${s.id}">${curVal} FPS</span>
          </div>
        `;

      case 'radio':
        return `
          <div class="radio-segmented-box">
            ${(s.options || []).map(opt => `
              <button 
                class="segment-btn ${String(curVal) === String(opt) ? 'active' : ''}" 
                onclick="EnterpriseSettings.stageChange('${s.id}', '${opt}')"
              >
                ${escapeHtml(opt)}
              </button>
            `).join('')}
          </div>
        `;

      case 'multiselect':
        const arr = Array.isArray(curVal) ? curVal : [];
        return `
          <div class="multiselect-tags-box">
            ${(s.options || []).map(opt => {
              const checked = arr.includes(opt);
              return `
                <label class="tag-checkbox ${checked ? 'active' : ''}">
                  <input 
                    type="checkbox" 
                    ${checked ? 'checked' : ''} 
                    onchange="EnterpriseSettings.toggleMultiSelectTag('${s.id}', '${opt}', this.checked)" 
                  />
                  <span>${escapeHtml(opt)}</span>
                </label>
              `;
            }).join('')}
          </div>
        `;

      case 'status':
        return `
          <div class="status-indicator-box">
            <span class="status-verified-badge">🛡️ ${escapeHtml(String(curVal))}</span>
          </div>
        `;

      case 'button_action':
        return `
          <div class="action-btn-box">
            <button class="btn btn-danger btn-sm" onclick="EnterpriseSettings.triggerDangerAction('${s.id}', '${s.name}')">${escapeHtml(s.name)}</button>
          </div>
        `;

      case 'text':
      default:
        return `
          <input 
            type="text" 
            class="setting-input-control" 
            value="${escapeHtml(curVal)}" 
            ${s.editable_by === 'READ_ONLY' ? 'disabled' : ''}
            oninput="EnterpriseSettings.stageChange('${s.id}', this.value)" 
          />
        `;
    }
  }

  // --------------------------------------------------------------------------
  // 4. ACTION & CHANGE HANDLERS
  // --------------------------------------------------------------------------
  function stageChange(settingId, newVal) {
    stagedValues[settingId] = newVal;
    hasUnsavedChanges = Object.keys(stagedValues).some(k => stagedValues[k] !== originalValues[k]);
    renderRoute();
  }

  function toggleMultiSelectTag(settingId, opt, isChecked) {
    let arr = Array.isArray(stagedValues[settingId]) ? [...stagedValues[settingId]] : [];
    if (isChecked) {
      if (!arr.includes(opt)) arr.push(opt);
    } else {
      arr = arr.filter(x => x !== opt);
    }
    stageChange(settingId, arr);
  }

  function discardChanges() {
    stagedValues = { ...originalValues };
    hasUnsavedChanges = false;
    renderRoute();
    showNotification('All staged changes discarded.', 'info');
  }

  function resetToInherited() {
    if (!currentCategoryData || !currentCategoryData.settings) return;
    currentCategoryData.settings.forEach(s => {
      stagedValues[s.id] = s.default;
    });
    hasUnsavedChanges = true;
    renderRoute();
    showNotification('Settings reset to inherited Host defaults.', 'info');
  }

  async function promptSaveCategory() {
    const highRiskChanges = [];
    if (currentCategoryData && currentCategoryData.settings) {
      currentCategoryData.settings.forEach(s => {
        if (stagedValues[s.id] !== originalValues[s.id] && (s.risk === 'HIGH' || s.risk === 'CRITICAL')) {
          highRiskChanges.push({
            setting: s,
            oldVal: originalValues[s.id],
            newVal: stagedValues[s.id]
          });
        }
      });
    }

    if (highRiskChanges.length > 0) {
      previewPendingChange = highRiskChanges;
      renderRoute();
      return;
    }

    await executeSaveCategory();
  }

  async function executeSaveCategory() {
    previewPendingChange = null;
    const catId = currentCategoryData.category.id;

    try {
      const res = await fetch(`/api/settings/category/${catId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({
          values: stagedValues,
          reason: 'Manual batch update from Enterprise Settings Center'
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          originalValues = { ...stagedValues };
          hasUnsavedChanges = false;
          await loadCategory(catId);
          await fetchCategories();
          await fetchEffectiveState();
          showNotification('Enterprise configuration saved and propagated to runtime.', 'success');
        } else {
          showNotification(`Save Error: ${data.errors ? data.errors.join('; ') : 'Validation failed'}`, 'error');
        }
      }
    } catch (e) {
      showNotification('Network exception saving settings.', 'error');
    }
  }

  async function resolveProposal(proposalId, decision) {
    try {
      const res = await fetch(`/api/settings/proposal/${proposalId}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({
          decision: decision,
          reason: `Proposal ${decision.toLowerCase()} by Sovereign Host`
        })
      });
      if (res.ok) {
        await loadCategory(activeView);
        showNotification(`Proposal ${decision}.`, 'success');
      }
    } catch (e) {
      showNotification('Error resolving proposal.', 'error');
    }
  }

  async function runDiagnosticTest(target) {
    try {
      const res = await fetch(`/api/settings/test/${target}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: target })
      });
      if (res.ok) {
        activeTestResult = await res.json();
        renderRoute();
      }
    } catch (e) {
      showNotification('Diagnostic test could not connect to server.', 'error');
    }
  }

  function closeDiagnosticTestModal() {
    activeTestResult = null;
    renderRoute();
  }

  function triggerDangerAction(settingId, name) {
    const confirmation = prompt(`CRITICAL ACTION REQUIREMENT:\n\nYou are about to invoke "${name}".\nType CONFIRM in all capitals to proceed with immediate execution:`);
    if (confirmation === 'CONFIRM') {
      showNotification(`Action '${name}' triggered with cryptographic audit receipt.`, 'success');
    }
  }

  function toggleTokenVisibility(inputId) {
    const el = document.getElementById(inputId);
    if (!el) return;
    el.type = el.type === 'password' ? 'text' : 'password';
  }

  function toggleAuditDrawer() {
    showAuditDrawer = !showAuditDrawer;
    renderRoute();
  }

  function setAuditFilter(filter) {
    auditFilter = filter;
    renderRoute();
  }

  function setScope(scope) {
    activeScope = scope;
    showNotification(`Active scope set to '${scope}'.`, 'info');
  }

  function setSubTab(subTabId) {
    activeSubTab = subTabId;
    renderRoute();
  }

  function handleSearch(q) {
    globalSearchQuery = q;
    if (!q || q.trim().length === 0) {
      searchDropdownResults = [];
      isSearchDropdownOpen = false;
    } else {
      const query = q.toLowerCase().trim();
      searchDropdownResults = SETTINGS_SEARCH_INDEX.filter(item => {
        return item.name.toLowerCase().includes(query) ||
               item.desc.toLowerCase().includes(query) ||
               item.id.toLowerCase().includes(query) ||
               item.category.toLowerCase().includes(query);
      });
      isSearchDropdownOpen = searchDropdownResults.length > 0;
    }
    renderRoute();
  }

  function handleSearchFocus() {
    if (globalSearchQuery && searchDropdownResults.length > 0) {
      isSearchDropdownOpen = true;
      renderRoute();
    }
  }

  function closeSearchDropdown() {
    isSearchDropdownOpen = false;
    const dropdown = document.getElementById('settingsSearchDropdown');
    if (dropdown) dropdown.remove();
  }

  function selectSearchResult(settingId, categoryId) {
    isSearchDropdownOpen = false;
    globalSearchQuery = '';
    navigateTo(categoryId);
    setTimeout(() => {
      const card = document.getElementById(`card-${settingId}`);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.add('card-highlight-pulse');
        setTimeout(() => card.classList.remove('card-highlight-pulse'), 3000);
      }
    }, 400);
  }

  function setQuickFilter(f) {
    activeQuickFilter = f;
    renderRoute();
  }

  function openGlobalAudit() {
    navigateTo('audit');
  }

  function navigateTo(dest) {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved configuration changes. Discard and proceed?')) {
        return;
      }
      hasUnsavedChanges = false;
    }
    const clean = normalizeCategoryId(dest);
    const targetRoute = clean === 'hub' ? '/settings' : `/settings/${clean}`;
    if (window.location.hash === '#' + targetRoute || window.location.hash === targetRoute) {
      render(targetRoute);
    } else {
      window.location.hash = targetRoute;
    }
  }

  function cancelPreview() {
    previewPendingChange = null;
    renderRoute();
  }

  function copyText(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      showNotification('Cryptographic hash copied to clipboard.', 'success');
    }
  }

  // --------------------------------------------------------------------------
  // 5. MODAL RENDERERS (Change Preview, Audit Drawer, Diagnostic Modal)
  // --------------------------------------------------------------------------
  function renderChangePreviewModal() {
    return `
      <div class="settings-modal-backdrop" onclick="EnterpriseSettings.cancelPreview()">
        <div class="settings-modal-box" onclick="event.stopPropagation()">
          <div class="modal-header">
            <div class="modal-title-row">
              <span class="modal-icon-badge warning">⚠️</span>
              <h4>High-Impact Configuration Review</h4>
            </div>
            <button class="modal-close-btn" onclick="EnterpriseSettings.cancelPreview()">✕</button>
          </div>
          <div class="modal-body">
            <p class="modal-intro">The following modifications exceed the standard operational risk threshold and require explicit sovereign confirmation:</p>
            <div class="impact-review-table">
              ${previewPendingChange.map(c => `
                <div class="impact-row">
                  <div class="impact-col-name">
                    <strong>${escapeHtml(c.setting.name)}</strong>
                    <span class="impact-col-key"><code>${escapeHtml(c.setting.id)}</code></span>
                  </div>
                  <div class="impact-col-diff">
                    <span class="diff-old">${escapeHtml(String(c.oldVal))}</span>
                    <span class="diff-arrow">→</span>
                    <span class="diff-new">${escapeHtml(String(c.newVal))}</span>
                  </div>
                  <div class="impact-col-risk">
                    <span class="badge badge-warning">${escapeHtml(c.setting.risk)} Risk</span>
                  </div>
                </div>
              `).join('')}
            </div>
            <div class="modal-disclaimer">
              <strong>Constitutional Guarantee:</strong> Applying these changes writes an immutable cryptographic receipt to the SHA-256 Merkle Evidence Ledger.
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onclick="EnterpriseSettings.cancelPreview()">Cancel</button>
            <button class="btn btn-primary" onclick="EnterpriseSettings.executeSaveCategory()">Confirm & Apply Changes</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderDiagnosticModal() {
    const res = activeTestResult;
    return `
      <div class="settings-modal-backdrop" onclick="EnterpriseSettings.closeDiagnosticTestModal()">
        <div class="settings-modal-box diagnostic-modal" onclick="event.stopPropagation()">
          <div class="modal-header">
            <div class="modal-title-row">
              <span class="modal-icon-badge success">⚡</span>
              <h4>Live Diagnostic Health Probe</h4>
            </div>
            <button class="modal-close-btn" onclick="EnterpriseSettings.closeDiagnosticTestModal()">✕</button>
          </div>
          <div class="modal-body">
            <div class="diagnostic-grid">
              <div class="diag-item">
                <span class="diag-label">Target Subsystem:</span>
                <span class="diag-val"><code>${escapeHtml(res.target)}</code></span>
              </div>
              <div class="diag-item">
                <span class="diag-label">Probe Status:</span>
                <span class="diag-badge status-${(res.status || 'OK').toLowerCase()}">${escapeHtml(res.status)}</span>
              </div>
              <div class="diag-item">
                <span class="diag-label">Round-Trip Latency:</span>
                <span class="diag-val latency">${escapeHtml(String(res.latency_ms))} ms</span>
              </div>
              <div class="diag-item">
                <span class="diag-label">Cryptographic Evidence SHA-256:</span>
                <div class="hash-copy-row">
                  <code>${escapeHtml(res.evidence_hash)}</code>
                  <button class="btn-copy-hash" onclick="EnterpriseSettings.copyText('${res.evidence_hash}')">Copy</button>
                </div>
              </div>
            </div>
            <div class="diag-detail-box">
              <span class="diag-detail-title">Subsystem Diagnostic Report:</span>
              <p>${escapeHtml(res.detail)}</p>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-primary" onclick="EnterpriseSettings.closeDiagnosticTestModal()">Close Probe</button>
          </div>
        </div>
      </div>
    `;
  }

  function renderAuditDrawer(audits) {
    let filteredAudits = audits;
    if (auditFilter === 'SOVEREIGN_HOST') {
      filteredAudits = audits.filter(a => a.actor && a.actor.toLowerCase().includes('host'));
    } else if (auditFilter === 'AI_CEO') {
      filteredAudits = audits.filter(a => a.actor && a.actor.toLowerCase().includes('ceo'));
    }

    return `
      <div class="settings-drawer-backdrop" onclick="EnterpriseSettings.toggleAuditDrawer()">
        <div class="settings-drawer" onclick="event.stopPropagation()">
          <div class="drawer-header">
            <div class="drawer-title-row">
              <span class="drawer-icon">⛓️</span>
              <div>
                <h4>Settings Audit Ledger</h4>
                <span class="drawer-sub">SHA-256 Merkle Evidence Receipts</span>
              </div>
            </div>
            <button class="drawer-close-btn" onclick="EnterpriseSettings.toggleAuditDrawer()">✕</button>
          </div>

          <div class="drawer-filter-bar">
            <button class="drawer-filter-pill ${auditFilter === 'all' ? 'active' : ''}" onclick="EnterpriseSettings.setAuditFilter('all')">All Events</button>
            <button class="drawer-filter-pill ${auditFilter === 'SOVEREIGN_HOST' ? 'active' : ''}" onclick="EnterpriseSettings.setAuditFilter('SOVEREIGN_HOST')">Host Changes</button>
            <button class="drawer-filter-pill ${auditFilter === 'AI_CEO' ? 'active' : ''}" onclick="EnterpriseSettings.setAuditFilter('AI_CEO')">AI CEO Proposals</button>
          </div>

          <div class="drawer-body">
            ${filteredAudits.length === 0 ? `
              <div class="empty-audit-card">
                <p>No audit receipts recorded under current filter.</p>
              </div>
            ` : `
              <div class="audit-events-stream">
                ${filteredAudits.map(evt => `
                  <div class="audit-event-card">
                    <div class="event-top-line">
                      <span class="event-setting-key">${escapeHtml(evt.setting_id)}</span>
                      <span class="event-time">${new Date(evt.created_at * 1000).toLocaleTimeString()}</span>
                    </div>
                    <div class="event-diff-line">
                      <code>${escapeHtml(String(evt.old_value))}</code> 
                      <span class="diff-arrow">→</span> 
                      <code>${escapeHtml(String(evt.new_value))}</code>
                    </div>
                    <div class="event-meta-line">
                      <span class="event-actor">Actor: ${escapeHtml(evt.actor)}</span>
                      <span class="event-sep">•</span>
                      <span class="event-reason">${escapeHtml(evt.reason || 'Manual modification')}</span>
                    </div>
                    <div class="event-hash-line">
                      <span>SHA-256:</span>
                      <code>${escapeHtml(evt.evidence_hash.slice(0, 28))}...</code>
                      <button class="btn-copy-mini" onclick="EnterpriseSettings.copyText('${evt.evidence_hash}')">Copy</button>
                    </div>
                  </div>
                `).join('')}
              </div>
            `}
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // Helper Utility Functions
  // --------------------------------------------------------------------------
  function getCategoryName(catId) {
    const cat = categoriesCatalog.find(c => c.id === catId);
    return cat ? cat.name : catId;
  }

  function highlightMatch(text, query) {
    if (!text || !query) return escapeHtml(text || '');
    const safeText = escapeHtml(text);
    const safeQuery = escapeHtml(query);
    const regex = new RegExp(`(${safeQuery.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&')})`, 'gi');
    return safeText.replace(regex, '<mark>$1</mark>');
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function showNotification(msg, type) {
    const banner = document.createElement('div');
    banner.className = `settings-toast toast-${type || 'info'}`;
    banner.innerHTML = `
      <span class="toast-dot ${type || 'info'}"></span>
      <span class="toast-msg">${escapeHtml(msg)}</span>
    `;
    document.body.appendChild(banner);
    setTimeout(() => {
      banner.classList.add('fade-out');
      setTimeout(() => banner.remove(), 400);
    }, 3200);
  }

  // Public API
  return {
    init,
    render,
    navigateTo,
    stageChange,
    toggleMultiSelectTag,
    discardChanges,
    resetToInherited,
    promptSaveCategory,
    executeSaveCategory,
    resolveProposal,
    runDiagnosticTest,
    closeDiagnosticTestModal,
    triggerDangerAction,
    toggleTokenVisibility,
    toggleAuditDrawer,
    setAuditFilter,
    setScope,
    setSubTab,
    handleSearch,
    handleSearchFocus,
    closeSearchDropdown,
    selectSearchResult,
    setQuickFilter,
    openGlobalAudit,
    cancelPreview,
    copyText,
    viewSettingAudit: (id) => toggleAuditDrawer()
  };
})();

// Attach to window
window.EnterpriseSettings = EnterpriseSettings;
document.addEventListener('DOMContentLoaded', () => {
  if (window.EnterpriseSettings && window.EnterpriseSettings.init) {
    window.EnterpriseSettings.init();
  }
});
