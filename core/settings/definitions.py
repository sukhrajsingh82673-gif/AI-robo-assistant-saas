"""
ZONATA / URA Universal AI Company Operating System
Canonical settings definitions, categories, groups, and scope aliases.

This module contains data only. Importing it must not touch the database,
instantiate the settings service, or seed defaults. The runtime service and
the typed registry both import from here so there is one source of truth.
"""

# Group Constants
GROUP_IDENTITY = "identity"
GROUP_AI_SYSTEM = "ai_system"
GROUP_EXECUTION = "execution"
GROUP_BUSINESS = "business"
GROUP_GOVERNANCE = "governance"
GROUP_PLATFORM = "platform"

GROUPS = [
    {
        "id": GROUP_IDENTITY,
        "name": "GROUP A — IDENTITY",
        "description": "Host sovereignty, company identity, organizational hierarchy, and access control."
    },
    {
        "id": GROUP_AI_SYSTEM,
        "name": "GROUP B — AI EXECUTIVE SYSTEM",
        "description": "Global AI policy, inference providers, AI CEO governance, workforce, and autonomy."
    },
    {
        "id": GROUP_EXECUTION,
        "name": "GROUP C — EXECUTION FABRIC",
        "description": "Workflows, tools registry, MCP, A2A network, desktop, browser, terminal, and sandbox."
    },
    {
        "id": GROUP_BUSINESS,
        "name": "GROUP D — BUSINESS SYSTEMS",
        "description": "Integrations, organizational knowledge, files, records, finance, and notifications."
    },
    {
        "id": GROUP_GOVERNANCE,
        "name": "GROUP E — CONTROL & TRUST",
        "description": "Approvals, constitutional governance, privacy, compliance, audit ledger, and security."
    },
    {
        "id": GROUP_PLATFORM,
        "name": "GROUP F — COST & PLATFORM",
        "description": "Usage & compute costs, billing, developer APIs, webhooks, localization, recovery, and danger zone."
    }
]

# Canonical 32 Primary Domains & Subcategory Aliases
DOMAIN_ALIASES = {
    # Sequential 01 to 32 numeric aliases
    "01": "account", "1": "account",
    "02": "company", "2": "company",
    "03": "users", "3": "users",
    "04": "enterprise", "4": "enterprise",
    "05": "ai_ceo", "5": "ai_ceo",
    "06": "workforce", "6": "workforce",
    "07": "workflows", "7": "workflows",
    "08": "ai_providers", "8": "ai_providers",
    "09": "tools", "9": "tools",
    "10": "desktop",
    "11": "browser",
    "12": "terminal",
    "13": "mcp",
    "14": "a2a",
    "15": "integrations",
    "16": "data",
    "17": "communication",
    "18": "finance",
    "19": "billing",
    "20": "security",
    "21": "governance",
    "22": "privacy",
    "23": "notifications",
    "24": "audit",
    "25": "recovery",
    "26": "monitoring",
    "27": "api",
    "28": "webhooks",
    "29": "localization",
    "30": "appearance",
    "31": "advanced",
    "32": "diagnostics",

    # String identifiers and semantic aliases
    "account": "account",
    "profile": "account",
    "company": "company",
    "organization": "organization",
    "users": "users",
    "access": "users",
    "ai": "ai",
    "ai_ceo": "ai_ceo",
    "ceo": "ai_ceo",
    "workforce": "workforce",
    "agent_factory": "agent_factory",
    "automation": "workflows",
    "missions": "missions",
    "workflows": "workflows",
    "models": "ai_providers",
    "providers": "ai_providers",
    "ai_providers": "ai_providers",
    "tools": "tools",
    "computer": "desktop",
    "desktop": "desktop",
    "coworker": "desktop",
    "browser": "browser",
    "terminal": "terminal",
    "mcp": "mcp",
    "a2a": "a2a",
    "agent_network": "a2a",
    "integrations": "integrations",
    "data": "data",
    "knowledge": "data",
    "files": "files",
    "records": "records",
    "communication": "communication",
    "comms": "communication",
    "email": "communication",
    "dispatch": "communication",
    "notifications": "notifications",
    "notify": "notifications",
    "alerts": "notifications",
    "finance": "finance",
    "billing": "billing",
    "usage": "usage",
    "security": "security",
    "governance": "governance",
    "approvals": "approvals",
    "privacy": "privacy",
    "compliance": "compliance",
    "audit": "audit",
    "evidence": "audit",
    "observability": "monitoring",
    "monitoring": "monitoring",
    "api": "api",
    "developer": "api",
    "webhooks": "webhooks",
    "backup": "recovery",
    "recovery": "recovery",
    "localization": "localization",
    "appearance": "appearance",
    "enterprise": "enterprise",
    "advanced": "advanced",
    "diagnostics": "diagnostics",
    "system": "diagnostics",
    "danger": "danger",
    "features": "features"
}

# Canonical Categories Metadata
CATEGORIES_CATALOG = [
    # Group A - Identity
    {"id": "account", "group_id": GROUP_IDENTITY, "name": "Account", "icon": "👤", "desc": "Administrator profile, notification preferences, sessions, and accessibility.", "status": "Healthy", "scope": "User"},
    {"id": "host", "group_id": GROUP_IDENTITY, "name": "Host & Sovereignty", "icon": "🏛️", "desc": "Sovereign owner boundary, system authority hierarchy, and emergency stops.", "status": "Healthy", "scope": "Host"},
    {"id": "company", "group_id": GROUP_IDENTITY, "name": "Company", "icon": "🏢", "desc": "Legal entity parameters, universal industry, business model, and KPIs.", "status": "Healthy", "scope": "Company"},
    {"id": "organization", "group_id": GROUP_IDENTITY, "name": "Organization", "icon": "🌳", "desc": "Departments, locations, cost centers, profit centers, and delegation tree.", "status": "Healthy", "scope": "Company"},
    {"id": "users", "group_id": GROUP_IDENTITY, "name": "Users & Access", "icon": "👥", "desc": "Granular RBAC roles, permission matrix, active sessions, and trusted devices.", "status": "Healthy", "scope": "Company"},
    
    # Group B - AI Executive System
    {"id": "ai", "group_id": GROUP_AI_SYSTEM, "name": "AI Global Policy", "icon": "🧠", "desc": "Autonomous reasoning depth, quality/cost thresholds, and safety firewalls.", "status": "Healthy", "scope": "Host"},
    {"id": "ai_providers", "group_id": GROUP_AI_SYSTEM, "name": "AI Models & Providers", "icon": "⚡", "desc": "Vertex, Gemini, Claude, OpenAI, local inference endpoints, and credential vault.", "status": "Healthy", "scope": "Host"},
    {"id": "ai_ceo", "group_id": GROUP_AI_SYSTEM, "name": "AI CEO", "icon": "👑", "desc": "Executive operating mode, 0-4 autonomy levels, approval thresholds, and memory.", "status": "Healthy", "scope": "Company"},
    {"id": "workforce", "group_id": GROUP_AI_SYSTEM, "name": "AI Workforce", "icon": "🤖", "desc": "Dynamic agent spawning limits, department budgets, and performance gates.", "status": "Healthy", "scope": "Company"},
    {"id": "agent_factory", "group_id": GROUP_AI_SYSTEM, "name": "Agent Factory", "icon": "🏭", "desc": "Template registry, capability discovery, sandbox simulations, and authority caps.", "status": "Healthy", "scope": "Company"},
    {"id": "missions", "group_id": GROUP_AI_SYSTEM, "name": "Missions & Autonomy", "icon": "🎯", "desc": "Mission creation triggers, risk gates, retries, and outcome verification.", "status": "Healthy", "scope": "Company"},

    # Group C - Execution Fabric
    {"id": "workflows", "group_id": GROUP_EXECUTION, "name": "Automation & Workflows", "icon": "🔄", "desc": "Durable execution, retry backoff, compensating actions, and immutable DAGs.", "status": "Healthy", "scope": "Company"},
    {"id": "tools", "group_id": GROUP_EXECUTION, "name": "Tools & Capabilities", "icon": "🛠️", "desc": "Capability fabric registry, risk classification, sandboxing, and trust gates.", "status": "Healthy", "scope": "Company"},
    {"id": "mcp", "group_id": GROUP_EXECUTION, "name": "MCP Servers", "icon": "🔌", "desc": "Model Context Protocol connections, resource limits, and tool permissions.", "status": "Healthy", "scope": "Company"},
    {"id": "a2a", "group_id": GROUP_EXECUTION, "name": "A2A / Agent Network", "icon": "🌐", "desc": "Agent-to-agent protocol, trust boundaries, message quotas, and broker topology.", "status": "Healthy", "scope": "Company"},
    {"id": "desktop", "group_id": GROUP_EXECUTION, "name": "Desktop / Coworker", "icon": "🖥️", "desc": "Perception rates, mouse/keyboard throttling, application access, and evidence.", "status": "Healthy", "scope": "Host"},
    {"id": "browser", "group_id": GROUP_EXECUTION, "name": "Browser & Web Execution", "icon": "🌐", "desc": "Headless Chromium contexts, domain allowlists, SSRF guard, and DOM audit.", "status": "Healthy", "scope": "Host"},
    {"id": "terminal", "group_id": GROUP_EXECUTION, "name": "Governed Terminal", "icon": "💻", "desc": "Sandboxed shell execution, TTL leases, egress allowlists, and execution ledger.", "status": "Healthy", "scope": "Host"},
    {"id": "openhands", "group_id": GROUP_EXECUTION, "name": "OpenHands / Code Execution", "icon": "📦", "desc": "Sandboxed software workspace, git branch protection, and rollback gates.", "status": "Healthy", "scope": "Company"},

    # Group D - Business Systems
    {"id": "integrations", "group_id": GROUP_BUSINESS, "name": "Integrations", "icon": "🔗", "desc": "Connected business systems (PMS, ERP, CRM, Payments), sync cadence, and least privilege.", "status": "Healthy", "scope": "Company"},
    {"id": "data", "group_id": GROUP_BUSINESS, "name": "Data & Knowledge", "icon": "📚", "desc": "Semantic search index, retention lifecycles, and data classification tags.", "status": "Healthy", "scope": "Company"},
    {"id": "files", "group_id": GROUP_BUSINESS, "name": "Files & Documents", "icon": "📁", "desc": "Storage quotas, MIME restrictions, immutable SHA-256 digests, and encryption.", "status": "Healthy", "scope": "Company"},
    {"id": "records", "group_id": GROUP_BUSINESS, "name": "Records & Business Data", "icon": "📋", "desc": "Structured entity schemas, deduplication rules, and validation pipelines.", "status": "Healthy", "scope": "Company"},
    {"id": "communication", "group_id": GROUP_BUSINESS, "name": "Communication & Dispatch", "icon": "📨", "desc": "Corporate email dispatch, SMTP/SES/SendGrid gateways, dispatch schedules, and sender identity.", "status": "Healthy", "scope": "Company"},
    {"id": "finance", "group_id": GROUP_BUSINESS, "name": "Finance & Ledgers", "icon": "💰", "desc": "Chart of accounts, currencies, fiscal year close, and expenditure approval limits.", "status": "Healthy", "scope": "Company"},
    {"id": "notifications", "group_id": GROUP_BUSINESS, "name": "Notifications & Alerts", "icon": "🔔", "desc": "Immediate SMS alerts, in-app notifications, priority paging, and digest cadence.", "status": "Healthy", "scope": "Company"},

    # Group E - Control & Trust
    {"id": "assistant", "group_id": GROUP_GOVERNANCE, "name": "URA Assistant", "icon": "✨", "desc": "The single assistant: scope, confirmations, memory, background work and web access.", "status": "Healthy", "scope": "Company"},
    {"id": "approvals", "group_id": GROUP_GOVERNANCE, "name": "Approvals & Decision Center", "icon": "⚖️", "desc": "Financial limits, two-person rules, timeout escalations, and owner sign-offs.", "status": "Healthy", "scope": "Company"},
    {"id": "governance", "group_id": GROUP_GOVERNANCE, "name": "Governance & Constitution", "icon": "🛡️", "desc": "Sovereign authority hierarchy, policy IF/THEN builder, and instant kill switches.", "status": "Healthy", "scope": "Host"},
    {"id": "privacy", "group_id": GROUP_GOVERNANCE, "name": "Privacy & Data Protection", "icon": "🔒", "desc": "PII anonymization, AI training zero-retention, and data sovereignty rules.", "status": "Healthy", "scope": "Company"},
    {"id": "compliance", "group_id": GROUP_GOVERNANCE, "name": "Compliance & Regulations", "icon": "📜", "desc": "ISO 37000/31000/37301/42001 profiles, statutory audits, and legal jurisdictions.", "status": "Healthy", "scope": "Company"},
    {"id": "audit", "group_id": GROUP_GOVERNANCE, "name": "Audit & Evidence Ledger", "icon": "⛓️", "desc": "Cryptographic SHA-256 Merkle ledger, immutability mode, and export receipts.", "status": "Healthy", "scope": "Host"},
    {"id": "security", "group_id": GROUP_GOVERNANCE, "name": "Security & Identity Policy", "icon": "🔐", "desc": "MFA enforcement, WebAuthn passkeys, session lifetimes, and brute-force shields.", "status": "Healthy", "scope": "Host"},

    # Group F - Cost & Platform
    {"id": "usage", "group_id": GROUP_PLATFORM, "name": "Usage & AI Costs", "icon": "📊", "desc": "Compute metering, token burn alerts (50/75/90/100%), and hard spend stops.", "status": "Healthy", "scope": "Company"},
    {"id": "billing", "group_id": GROUP_PLATFORM, "name": "Billing & Subscriptions", "icon": "💳", "desc": "Plan tier, payment gateways, licensing tokens, and invoice audit ledger.", "status": "Healthy", "scope": "Company"},
    {"id": "api", "group_id": GROUP_PLATFORM, "name": "API & Developer Platform", "icon": "🔑", "desc": "Bearer token keys, OAuth scopes, rate limiting, and egress IP allowlists.", "status": "Healthy", "scope": "Host"},
    {"id": "webhooks", "group_id": GROUP_PLATFORM, "name": "Webhooks & Events", "icon": "🪝", "desc": "HMAC-SHA256 signature verification, retry backoff, and event dispatch logs.", "status": "Healthy", "scope": "Company"},
    {"id": "localization", "group_id": GROUP_PLATFORM, "name": "Localization & Locale", "icon": "🌍", "desc": "Base reporting timezone, number formatting, currency symbols, and business days.", "status": "Healthy", "scope": "Company"},
    {"id": "appearance", "group_id": GROUP_PLATFORM, "name": "Appearance & UX", "icon": "🎨", "desc": "Theme mode, high contrast, reduced motion, navigation density, and mobile bottom dock.", "status": "Healthy", "scope": "User"},
    {"id": "recovery", "group_id": GROUP_PLATFORM, "name": "Backup & Disaster Recovery", "icon": "💾", "desc": "Automated SQLite snapshots, cold backup sync, RPO/RTO goals, and restore drills.", "status": "Healthy", "scope": "Host"},
    {"id": "monitoring", "group_id": GROUP_PLATFORM, "name": "Monitoring & Reliability", "icon": "📈", "desc": "Subsystem health monitors, circuit breakers, timeout thresholds, and liveness probes.", "status": "Healthy", "scope": "Host"},
    {"id": "enterprise", "group_id": GROUP_PLATFORM, "name": "Enterprise Administration", "icon": "🏢", "desc": "Multi-tenant boundaries, SCIM identity provisioning, SAML 2.0, and data residency.", "status": "Healthy", "scope": "Host"},
    {"id": "features", "group_id": GROUP_PLATFORM, "name": "Feature Flags", "icon": "🚩", "desc": "System capability rollouts, staged enablement, and Canary risk envelopes.", "status": "Healthy", "scope": "Host"},
    {"id": "advanced", "group_id": GROUP_PLATFORM, "name": "Advanced & Diagnostics", "icon": "⚙️", "desc": "Runtime engine tuning, cache invalidation, raw policy viewer, and heap diagnostics.", "status": "Attention", "scope": "Host"},
    {"id": "diagnostics", "group_id": GROUP_PLATFORM, "name": "System Diagnostics", "icon": "💻", "desc": "Live backend status, database WAL check, inference pings, and runtime telemetry.", "status": "Healthy", "scope": "Host"},
    {"id": "danger", "group_id": GROUP_PLATFORM, "name": "Danger Zone", "icon": "🚨", "desc": "High-impact isolated kill switches, session revocation, and data purge guards.", "status": "Warning", "scope": "Host"}
]

# Canonical Domain to Child/Linked Categories Mapping
DOMAIN_CHILD_CATEGORIES = {
    "account": ["account", "host"],
    "company": ["company", "organization"],
    "users": ["users"],
    "enterprise": ["enterprise"],
    "ai_ceo": ["ai_ceo", "ai"],
    "workforce": ["workforce", "agent_factory"],
    "automation": ["workflows", "missions", "automation"],
    "workflows": ["workflows", "missions", "automation"],
    "ai_providers": ["ai_providers"],
    "tools": ["tools"],
    "desktop": ["desktop"],
    "browser": ["browser"],
    "terminal": ["terminal", "openhands"],
    "mcp": ["mcp"],
    "a2a": ["a2a"],
    "integrations": ["integrations"],
    "data": ["data", "files", "records"],
    "communication": ["communication"],
    "finance": ["finance"],
    "billing": ["billing", "usage"],
    "security": ["security"],
    "governance": ["governance", "approvals", "compliance"],
    "privacy": ["privacy"],
    "notifications": ["notifications"],
    "audit": ["audit"],
    "recovery": ["recovery"],
    "monitoring": ["monitoring"],
    "api": ["api"],
    "webhooks": ["webhooks"],
    "localization": ["localization"],
    "appearance": ["appearance"],
    "advanced": ["advanced", "danger", "features"],
    "diagnostics": ["diagnostics"]
}

# Primary Setting Items Schema
SETTINGS_DEFINITIONS = [
    # --- 1. Account ---
    {
        "id": "acc_display_name", "category": "account", "name": "Display Name", "type": "text",
        "default": "Sukhraj Singh", "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Operator or sovereign host full legal name shown across notifications and audit receipts.",
        "doc": {"what": "Full name of the host", "why": "Audit accountability", "recommended": "Official administrator name"}
    },
    {
        "id": "acc_email", "category": "account", "name": "Host Email", "type": "text",
        "default": "host@zonata.internal", "scope": "User", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Primary email for cryptographic security alerts, MFA challenges, and escalation notifications."
    },
    {
        "id": "acc_timezone", "category": "account", "name": "Preferred Timezone", "type": "select",
        "default": "Asia/Kolkata", "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Asia/Kolkata", "UTC", "America/New_York", "Europe/London", "Asia/Dubai", "Asia/Singapore"],
        "desc": "User interface timestamp projection timezone."
    },
    {
        "id": "acc_secondary_timezones", "category": "account", "name": "Additional Monitored Timezones", "type": "multiselect",
        "default": ["UTC", "America/New_York"], "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Asia/Kolkata", "UTC", "America/New_York", "Europe/London", "Asia/Dubai", "Asia/Singapore", "America/Los_Angeles", "Asia/Tokyo"],
        "desc": "Personal secondary timezones projected on world clocks and executive briefings."
    },
    {
        "id": "acc_density", "category": "account", "name": "Interface Density", "type": "radio",
        "default": "comfortable", "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "options": ["compact", "comfortable"]
    },

    # --- 2. Host & Sovereignty ---
    {
        "id": "host_emergency_stop", "category": "host", "name": "Global Emergency Stop", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL", "requires_approval": True,
        "desc": "Immediately halts all AI background missions, terminal commands, and external mutations."
    },
    {
        "id": "host_authority_scope", "category": "host", "name": "Sovereign Authority Level", "type": "status",
        "default": "SOVEREIGN_OWNER", "scope": "Host", "editable_by": "READ_ONLY", "risk": "LOW",
        "desc": "Constitutional authority tier. Only the sovereign owner holds override rights."
    },
    {
        "id": "host_killswitch_finances", "category": "host", "name": "Halt Financial Execution", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Immediately blocks all AI-initiated financial transactions, payments, and payouts."
    },
    {
        "id": "host_killswitch_desktop", "category": "host", "name": "Halt Desktop / OS Control", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Immediately cuts off robotic desktop mouse, keyboard, and OS window interaction."
    },

    # --- 3. Company ---
    {
        "id": "comp_legal_name", "category": "company", "name": "Legal Corporate Name", "type": "text",
        "default": "ZONATA Technologies Private Limited", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Registered statutory entity name for compliance certificates and audit manifests."
    },
    {
        "id": "comp_industry", "category": "company", "name": "Industry Sector", "type": "select",
        "default": "Universal Enterprise", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Universal Enterprise", "Hospitality & Tourism", "SaaS & Software", "Manufacturing & Supply Chain", "Healthcare & Life Sciences", "E-Commerce & Retail", "Financial Services"],
        "desc": "Universal industry profile governing KPI templates and regulatory adapters."
    },
    {
        "id": "comp_business_model", "category": "company", "name": "Business Model", "type": "multiselect",
        "default": ["B2B", "Subscription", "Service"], "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["B2B", "B2C", "B2B2C", "Marketplace", "Subscription", "Transactional", "Project-Based", "Service", "Hybrid"]
    },
    {
        "id": "comp_base_currency", "category": "company", "name": "Base Currency", "type": "select",
        "default": "INR (₹)", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["INR (₹)", "USD ($)", "EUR (€)", "GBP (£)", "AED (د.إ)", "SGD (S$)"]
    },
    {
        "id": "comp_operating_entities", "category": "company", "name": "Subsidiaries & Operating Entities", "type": "multiselect",
        "default": ["ZONATA Technologies Primary", "ZONATA AI Labs"], "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["ZONATA Technologies Primary", "ZONATA AI Labs", "ZONATA Cloud Services", "ZONATA Robotics Private Limited", "ZONATA Global Holdings"],
        "desc": "Operating subsidiary companies covered under this sovereign enterprise license."
    },
    {
        "id": "comp_operating_timezones", "category": "company", "name": "Corporate Operating Time Zones", "type": "multiselect",
        "default": ["Asia/Kolkata", "UTC"], "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Asia/Kolkata", "UTC", "America/New_York", "Europe/London", "Asia/Dubai", "Asia/Singapore", "America/Los_Angeles", "Asia/Tokyo"],
        "desc": "Global operating timezones governing inter-company operations, reporting, and dispatch."
    },

    # --- 4. Organization ---
    {
        "id": "org_hierarchy_enforcement", "category": "organization", "name": "12-Level Hierarchy Enforcement", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Enforces strict L0-L11 reporting chains, span-of-control bounds, and delegation envelopes."
    },
    {
        "id": "org_max_exec_span", "category": "organization", "name": "Executive Span of Control Limit", "type": "number",
        "default": 8, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 1, "max": 32, "unit": "direct reports",
        "desc": "Maximum direct reports permitted for C-Suite nodes before mandatory delegation."
    },

    # --- 5. Users & Access ---
    {
        "id": "rbac_default_role", "category": "users", "name": "Default Invited Role", "type": "select",
        "default": "OPERATOR", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["OBSERVER", "OPERATOR", "MANAGER", "EXECUTIVE"]
    },
    {
        "id": "rbac_two_person_rule", "category": "users", "name": "Enforce Two-Person Rule", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Requires two distinct authenticated operators for high-risk financial or policy operations."
    },

    # --- 6. AI Global Policy ---
    {
        "id": "ai_master_enablement", "category": "ai", "name": "AI System Global Enablement", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Master enable/disable toggle for all AI models, reasoning engines, and background tasks."
    },
    {
        "id": "ai_reasoning_depth", "category": "ai", "name": "Reasoning Depth Policy", "type": "radio",
        "default": "balanced", "scope": "Host", "editable_by": "SHARED", "risk": "LOW",
        "options": ["concise", "balanced", "deep_strategic"]
    },
    {
        "id": "ai_prompt_injection_guard", "category": "ai", "name": "Prompt Injection Firewall", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Scans all inbound inputs and tool outputs for adversarial prompt injection patterns."
    },

    # --- 7. AI Models & Providers ---
    {
        "id": "ai_primary_provider", "category": "ai_providers", "name": "Primary Inference Provider", "type": "select",
        "default": "Embedded Free (zero-config)", "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["Embedded Free (zero-config)", "Local Self-Hosted (Ollama / vLLM)", "Google AI Studio (free tier)", "Groq (free tier)", "OpenRouter (free models)", "Custom OpenAI-compatible endpoint"]
    },
    {
        "id": "llm_provider", "category": "ai_providers", "name": "LLM Runtime Provider", "type": "select",
        "default": "embedded_free", "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["embedded_free", "ollama", "gemini_free", "groq_free", "openrouter_free", "openai_compatible", "deterministic"],
        "desc": "embedded_free = local Ollama if available, otherwise a keyless free inference service. Choose ollama for fully local/private inference."
    },
    {
        "id": "llm_model", "category": "ai_providers", "name": "LLM Model Identifier", "type": "text",
        "default": "", "scope": "Host", "editable_by": "OWNER", "risk": "LOW",
        "desc": "e.g. qwen2.5:1.5b (Ollama), gemini-2.0-flash, llama-3.3-70b-versatile, meta-llama/llama-3.3-70b-instruct:free. Leave blank for provider default."
    },
    {
        "id": "llm_base_url", "category": "ai_providers", "name": "LLM Base URL", "type": "text",
        "default": "", "scope": "Host", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Only for local/self-hosted or custom OpenAI-compatible endpoints (e.g. http://127.0.0.1:11434 or http://127.0.0.1:1234/v1)."
    },
    {
        "id": "llm_api_key", "category": "ai_providers", "name": "LLM API Key", "type": "token",
        "default": "", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "secret": True,
        "desc": "Optional. Required only for keyed free tiers (Google AI Studio, Groq, OpenRouter). Stored encrypted at rest; never logged."
    },
    {
        "id": "llm_temperature", "category": "ai_providers", "name": "LLM Temperature", "type": "number",
        "default": 0.3, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 0.0, "max": 2.0,
        "desc": "Lower = more deterministic executive reasoning; higher = more creative drafting."
    },
    {
        "id": "llm_max_tokens", "category": "ai_providers", "name": "LLM Max Output Tokens", "type": "number",
        "default": 1200, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 64, "max": 8192,
        "desc": "Upper bound on generated tokens per inference turn."
    },
    {
        "id": "llm_timeout_seconds", "category": "ai_providers", "name": "LLM Request Timeout (Seconds)", "type": "number",
        "default": 45, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 5, "max": 300,
        "desc": "Hard socket timeout for inference calls; the runtime degrades gracefully on timeout."
    },
    {
        "id": "ai_gemini_api_token", "category": "ai_providers", "name": "Gemini API Token", "type": "token",
        "default": "AIzaSy••••••••••••••••••••••••••••••••••••", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "secret": True,
        "desc": "Cryptographically masked bearer credential for Gemini API."
    },
    {
        "id": "ai_circuit_breaker_retries", "category": "ai_providers", "name": "Provider Max Retries", "type": "number",
        "default": 3, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 20, "unit": "retries"
    },

    # --- 8. AI CEO ---
    {
        "id": "ceo_autonomy_level", "category": "ai_ceo", "name": "CEO Autonomy Level", "type": "select",
        "default": "Level 3 — Execute Within Policy", "scope": "Company", "editable_by": "OWNER", "risk": "CRITICAL",
        "options": [
            "Level 0 — Observe Only",
            "Level 1 — Recommend Only",
            "Level 2 — Execute With Approval",
            "Level 3 — Execute Within Policy",
            "Level 4 — Strategic Autonomous Operation"
        ],
        "desc": "Strict constitutional ceiling. CEO cannot promote itself to a higher level."
    },
    {
        "id": "ceo_spending_limit", "category": "ai_ceo", "name": "CEO Autonomous Spending Cap", "type": "currency",
        "default": 50000, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH", "min": 1000, "max": 1000000, "unit": "USD",
        "desc": "Maximum single financial allocation the CEO may execute without explicit Host approval."
    },
    {
        "id": "ceo_council_enabled", "category": "ai_ceo", "name": "Executive Council Peer Review", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Mandates multi-perspective peer review by COO, CFO, and CTO personas prior to strategic actions."
    },
    {
        "id": "ceo_continuous_cognition_mins", "category": "ai_ceo", "name": "Continuous Cognition Interval", "type": "number",
        "default": 15, "scope": "Company", "editable_by": "SHARED", "is_ceo_managed": True, "risk": "LOW", "min": 1, "max": 1440, "unit": "minutes",
        "desc": "Scheduled interval for proactive enterprise heartbeat, risk scans, and opportunity evaluation."
    },

    # --- 8b. URA Assistant ---
    {
        "id": "assistant_show_button", "category": "assistant", "name": "Show the assistant button", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Show the one URA Assistant launcher in the corner of every screen.",
        "hint": "On phones the assistant lives in the middle tab, so this only affects desktop.",
        "suggestion": True,
        "reason": "The launcher is the only conversational entry point now that the old bars are gone."
    },
    {
        "id": "assistant_open_as", "category": "assistant", "name": "Open as", "type": "select",
        "default": "window", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["window", "docked"],
        "desc": "How the assistant opens the first time each session.",
        "hint": "Docked keeps it beside your work; window keeps it free-floating.",
        "suggestion": "window",
        "reason": "A floating window stays available on every screen without shrinking the page."
    },
    {
        "id": "assistant_default_scope", "category": "assistant", "name": "Default scope", "type": "select",
        "default": "PERSONAL", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["PERSONAL", "COMPANY"],
        "desc": "Which workspace the assistant starts in when it opens.",
        "hint": "Company data still needs the approved cowork permission, whichever default is set.",
        "suggestion": "PERSONAL",
        "reason": "Personal starts without reading company data, and Company is one click away when you need it."
    },
    {
        "id": "assistant_confirmations", "category": "assistant", "name": "Confirm risky actions", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Ask for an in-window confirmation before the assistant runs a tool that changes something.",
        "hint": "Terminal commands and any high-risk tool always ask, even when this is off.",
        "suggestion": True,
        "reason": "A single confirmation keeps changes visible before they happen."
    },
    {
        "id": "assistant_remember_conversations", "category": "assistant", "name": "Remember conversations", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Keep the assistant's turns so memory and history can refer to them later.",
        "hint": "“Remember this” still saves the item you choose when this is off.",
        "suggestion": True,
        "reason": "History makes follow-up questions work; explicit memory stays opt-in either way."
    },
    {
        "id": "assistant_background_work", "category": "assistant", "name": "Background work", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Allow long research or data work to run as a background job (three active per user).",
        "hint": "With this off, answers stay in the open window and nothing runs after you leave.",
        "suggestion": True,
        "reason": "Background jobs keep research moving without holding the window open."
    },
    {
        "id": "assistant_meetings_enabled", "category": "assistant", "name": "Meetings", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Show the Meetings area: briefs, live notes, summaries and the meeting library.",
        "hint": "Turning this off hides the meeting controls but keeps stored meeting records.",
        "suggestion": True,
        "reason": "Meetings are part of the single assistant, so the controls should be visible by default."
    },
    {
        "id": "assistant_web_access", "category": "assistant", "name": "Web access", "type": "select",
        "default": "off", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["off", "allowlist", "open"],
        "desc": "Off: the assistant never reads the web. Allow list: only listed domains. Open: any public domain except the block list.",
        "hint": "Web search also needs a server-side provider; without one the assistant says it is not configured.",
        "suggestion": "off",
        "reason": "Starting off means no page is read until you name the domains you trust."
    },
    {
        "id": "assistant_web_allowlist", "category": "assistant", "name": "Web allow list", "type": "text",
        "default": "", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Comma-separated domains the assistant may read when web access is set to allow list.",
        "hint": "Subdomains match with a leading wildcard, for example *.example.com.",
        "suggestion": "",
        "reason": "An empty list is honest: nothing is read until a domain is added."
    },
    {
        "id": "assistant_web_blocklist", "category": "assistant", "name": "Web block list", "type": "text",
        "default": "", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Comma-separated domains the assistant must never cite, even when web access is open.",
        "hint": "The block list wins over both the allow list and open access.",
        "suggestion": "",
        "reason": "Nothing needs blocking by default, and the list is checked before any source is cited."
    },
    {
        "id": "assistant_meeting_recording_notice", "category": "assistant", "name": "Announce recording", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Show and record a plain-language recording and transcription announcement when listening starts.",
        "hint": "The announcement is written to the meeting record once, before any transcript line.",
        "suggestion": True,
        "reason": "People in the meeting should hear that it is being recorded before it starts."
    },

    # --- 9. AI Workforce ---
    {
        "id": "wf_max_concurrent_agents", "category": "workforce", "name": "Max Concurrent Active Agents", "type": "number",
        "default": 16, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 0, "max": 128, "unit": "agents",
        "desc": "Upper concurrency boundary on parallel running agent processes."
    },
    {
        "id": "wf_autonomous_spawning", "category": "workforce", "name": "Allow Autonomous Agent Spawning", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Permits AI CEO to dynamically create task-specific agents under constitutional template rules."
    },

    # --- 10. Agent Factory ---
    {
        "id": "af_mandatory_simulation", "category": "agent_factory", "name": "Mandatory Pre-Deployment Simulation", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "New agents must pass 100% of benchmark unit simulations before receiving operational missions."
    },

    # --- 11. Missions & Autonomy ---
    {
        "id": "mission_outcome_verification", "category": "missions", "name": "Mandatory Outcome Verification Gate", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Missions are never marked SUCCESS on task exit codes alone; measurable business outcomes are verified."
    },
    {
        "id": "mission_retry_limit", "category": "missions", "name": "Mission Max Retries", "type": "number",
        "default": 3, "scope": "Company", "editable_by": "SHARED", "is_ceo_managed": True, "risk": "LOW", "min": 1, "max": 10, "unit": "retries"
    },

    # --- 12. Automation & Workflows ---
    {
        "id": "wf_durable_checkpointing", "category": "workflows", "name": "Durable Step Checkpointing", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW"
    },

    # --- 13. Tools & Capabilities ---
    {
        "id": "tools_sandboxed_exec", "category": "tools", "name": "Sandboxed Execution Mandatory", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "All tool invocations run within isolated filesystem and process boundaries."
    },
    {
        "id": "tools_authority_ceiling", "category": "tools", "name": "Default Authority Ceiling", "type": "select",
        "default": "ASK_ME", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["SANDBOXED_READ_ONLY", "AUTOMATIC_IDEMPOTENT", "ASK_ME", "NEVER_ALLOWED"]
    },

    # --- 14. MCP ---
    {
        "id": "mcp_allow_external_servers", "category": "mcp", "name": "Allow External MCP Servers", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM"
    },

    # --- 15. A2A ---
    {
        "id": "a2a_inter_agent_auth", "category": "a2a", "name": "Cryptographic Agent Token Exchange", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH"
    },

    # --- 16. Desktop / Coworker ---
    {
        "id": "desk_enable_control", "category": "desktop", "name": "Enable Desktop Perception & Control", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Enables computer-use perception, OS window management, and pointer interaction."
    },
    {
        "id": "desk_fps_limit", "category": "desktop", "name": "Perception Screen Sampling Rate (FPS)", "type": "slider",
        "default": 2, "scope": "Host", "editable_by": "SHARED", "risk": "LOW", "min": 1, "max": 30, "unit": "fps"
    },

    # --- 17. Browser ---
    {
        "id": "browser_headless_mode", "category": "browser", "name": "Headless Browser Automation", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM"
    },
    {
        "id": "browser_ssrf_protection", "category": "browser", "name": "Strict SSRF & Private Network Egress Filter", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH"
    },

    # --- 18. Governed Terminal ---
    {
        "id": "term_execution_enabled", "category": "terminal", "name": "Terminal Command Execution Enabled", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL"
    },
    {
        "id": "term_max_lease_seconds", "category": "terminal", "name": "Command Execution Lease TTL (Seconds)", "type": "number",
        "default": 60, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 10, "max": 3600, "unit": "sec"
    },

    # --- 19. OpenHands ---
    {
        "id": "openhands_repo_sandbox", "category": "openhands", "name": "Sandboxed Code Execution & Git Branch Isolation", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH"
    },

    # --- 20. Integrations ---
    {
        "id": "integ_least_privilege", "category": "integrations", "name": "Enforce Least Privilege Sync Mappings", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM"
    },

    # --- 21. Data & Knowledge ---
    {
        "id": "data_retention_days", "category": "data", "name": "Operational Context Retention (Days)", "type": "number",
        "default": 365, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 7, "max": 3650, "unit": "days"
    },

    # --- 22. Files ---
    {
        "id": "files_max_upload_mb", "category": "files", "name": "Max Upload Size (MB)", "type": "number",
        "default": 50, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 1024, "unit": "MB"
    },

    # --- 23. Records ---
    {
        "id": "records_deduplication", "category": "records", "name": "Automatic Deterministic Deduplication", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW"
    },

    # --- 24. Finance ---
    {
        "id": "fin_accounting_method", "category": "finance", "name": "Accounting Method", "type": "select",
        "default": "Accrual Basis (GAAP/IFRS)", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["Accrual Basis (GAAP/IFRS)", "Cash Basis"]
    },
    {
        "id": "fin_high_expense_approval", "category": "finance", "name": "Expense Threshold Requiring Owner Approval", "type": "currency",
        "default": 25000, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH", "min": 100, "max": 1000000, "unit": "USD"
    },

    # --- Communication & Dispatch (Domain 17) ---
    {
        "id": "comm_smtp_server", "category": "communication", "name": "Corporate SMTP Server", "type": "text",
        "default": "", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Primary outbound SMTP mail transfer gateway. Empty means no email channel is configured; outbound mail stays disabled until the owner supplies a reachable host."
    },
    {
        "id": "comm_smtp_port", "category": "communication", "name": "SMTP Gateway Port", "type": "number",
        "default": 587, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 65535, "unit": "port",
        "desc": "Standard submission port (587 STARTTLS / 465 SSL)."
    },
    {
        "id": "comm_sender_identity", "category": "communication", "name": "Corporate Sender Identity", "type": "text",
        "default": "dispatch@zonata.internal", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Default From: address for system communications and reports."
    },
    {
        "id": "comm_dispatch_rate_limit", "category": "communication", "name": "Outbound Dispatch Rate Limit (Per Hour)", "type": "number",
        "default": 500, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 1, "max": 50000, "unit": "req/hr",
        "desc": "Maximum automated transactional messages permitted per hour to avoid spam flags."
    },
    {
        "id": "comm_tls_enforced", "category": "communication", "name": "Enforce TLS / STARTTLS Encryption", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Refuse plaintext transmission for outbound messages."
    },

    # --- Notifications & Alert Routing (Domain 23) ---
    {
        "id": "notify_critical_sms", "category": "notifications", "name": "Immediate SMS Alerts on Kill Switch / Breach", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Trigger immediate cellular SMS alert to registered sovereign emergency contact upon kill switch trip."
    },
    {
        "id": "notify_in_app_toast", "category": "notifications", "name": "In-App Real-Time Toast Notifications", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Display real-time visual status updates and task milestones in the administration workspace."
    },
    {
        "id": "notify_severity_threshold", "category": "notifications", "name": "Notification Severity Filter", "type": "select",
        "default": "HIGH", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["ALL", "INFO", "HIGH", "CRITICAL"],
        "desc": "Minimum operational event severity required to emit push notifications."
    },
    {
        "id": "notify_digest_interval", "category": "notifications", "name": "Administrative Digest Interval", "type": "select",
        "default": "Daily Summary", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Real-Time", "Hourly Digest", "Daily Summary"],
        "desc": "Cadence for compiling non-urgent operational events into consolidated briefs."
    },
    {
        "id": "notify_escalation_sms_number", "category": "notifications", "name": "Emergency Escalation SMS Number", "type": "text",
        "default": "+1-555-0199", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Verified sovereign administrator telephone number for incident paging."
    },

    # --- 26. Approvals ---
    {
        "id": "appr_auto_escalation_hours", "category": "approvals", "name": "Escalation Timeout (Hours)", "type": "number",
        "default": 24, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 168, "unit": "hours"
    },

    # --- 27. Governance ---
    {
        "id": "gov_kill_switch_active", "category": "governance", "name": "Emergency Quarantine Isolation Mode", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL", "requires_approval": True,
        "desc": "Isolates company instance and aborts any active or incoming mutation commands."
    },

    # --- 28. Privacy ---
    {
        "id": "priv_pii_masking", "category": "privacy", "name": "Automated PII Sanitization & Masking", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Redacts customer phone numbers, Aadhaar/SSN, emails, and credit cards from model prompts."
    },

    # --- 29. Compliance ---
    {
        "id": "comp_regulatory_profile", "category": "compliance", "name": "Statutory Governance Profile", "type": "select",
        "default": "ISO 37000 / ISO 42001 (Global)", "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["ISO 37000 / ISO 42001 (Global)", "SOC 2 Type II", "EU GDPR & AI Act", "India DPDPA 2023"]
    },

    # --- 30. Audit & Evidence ---
    {
        "id": "audit_ledger_hashing", "category": "audit", "name": "Cryptographic Hash Algorithm", "type": "status",
        "default": "SHA-256 (Merkle Tree)", "scope": "Host", "editable_by": "READ_ONLY", "risk": "LOW",
        "desc": "Immutable ledger cryptographic receipt hashing standard."
    },
    {
        "id": "audit_immutability_mode", "category": "audit", "name": "Immutability Enforcement", "type": "status",
        "default": "STRICT_APPEND_ONLY", "scope": "Host", "editable_by": "READ_ONLY", "risk": "LOW"
    },

    # --- 31. Security ---
    {
        "id": "sec_require_mfa", "category": "security", "name": "Require Multi-Factor Authentication (MFA)", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Forces WebAuthn FIDO2 passkey or TOTP 2FA for all administrative logins."
    },
    {
        "id": "sec_session_duration_hours", "category": "security", "name": "Session Maximum Lifetime (Hours)", "type": "select",
        "default": 12, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": [1, 4, 8, 12, 14, 24, 72]
    },
    {
        "id": "sec_device_trust", "category": "security", "name": "Device Trust Enforced", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH"
    },

    # --- 32. Usage & Costs ---
    {
        "id": "cost_global_budget_monthly", "category": "usage", "name": "Global AI Compute Monthly Spending Cap", "type": "currency",
        "default": 100000, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "min": 1000, "max": 10000000, "unit": "USD",
        "desc": "Hard spending ceiling across all LLM inference, browser scraping, and cloud execution."
    },
    {
        "id": "cost_alert_threshold_pct", "category": "usage", "name": "Budget Warning Alert Threshold", "type": "select",
        "default": "80%", "scope": "Company", "editable_by": "SHARED", "risk": "LOW",
        "options": ["50%", "75%", "80%", "90%", "100%"]
    },

    # --- 33. Billing ---
    {
        "id": "bill_plan_tier", "category": "billing", "name": "Current Subscription Tier", "type": "status",
        "default": "SOVEREIGN ENTERPRISE", "scope": "Company", "editable_by": "READ_ONLY", "risk": "LOW"
    },

    # --- 34. API & Developer ---
    {
        "id": "api_rate_limit_rpm", "category": "api", "name": "API Rate Limit (Requests / Min)", "type": "number",
        "default": 1200, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 10, "max": 60000, "unit": "req/min"
    },

    # --- 35. Webhooks ---
    {
        "id": "webhook_verify_signatures", "category": "webhooks", "name": "HMAC-SHA256 Signature Verification", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH"
    },

    # --- 36. Localization ---
    {
        "id": "loc_date_format", "category": "localization", "name": "Date Presentation Format", "type": "select",
        "default": "YYYY-MM-DD", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"]
    },
    {
        "id": "loc_reporting_timezone", "category": "localization", "name": "Universal Enterprise Reporting Timezone", "type": "select",
        "default": "Asia/Kolkata (IST)", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Asia/Kolkata (IST)", "UTC", "America/New_York (EST)", "Europe/London (GMT)", "Asia/Dubai (GST)", "Asia/Singapore (SGT)", "America/Los_Angeles (PST)", "Asia/Tokyo (JST)"],
        "desc": "Primary enterprise base timezone for statutory reporting, ledger timestamps, and audit manifests."
    },
    {
        "id": "loc_operating_timezones", "category": "localization", "name": "Multi-Region Operating Timezones", "type": "multiselect",
        "default": ["Asia/Kolkata (IST)", "UTC", "America/New_York (EST)"], "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Asia/Kolkata (IST)", "UTC", "America/New_York (EST)", "America/Los_Angeles (PST)", "Europe/London (GMT)", "Europe/Paris (CET)", "Asia/Dubai (GST)", "Asia/Singapore (SGT)", "Asia/Tokyo (JST)", "Australia/Sydney (AEST)"],
        "desc": "Select multiple regional timezones for multi-office scheduling, calendar aggregation, and global shifts."
    },

    # --- 37. Appearance ---
    {
        "id": "app_theme", "category": "appearance", "name": "Color Scheme Theme", "type": "select",
        "default": "dark", "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "options": ["dark", "light", "system"]
    },
    {
        "id": "app_high_contrast", "category": "appearance", "name": "High Contrast Mode", "type": "toggle",
        "default": False, "scope": "User", "editable_by": "OWNER", "risk": "LOW"
    },

    # --- 38. Recovery ---
    {
        "id": "rec_auto_snapshot_frequency", "category": "recovery", "name": "Automated SQLite Snapshot Interval", "type": "select",
        "default": "Every 6 Hours", "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["Hourly", "Every 6 Hours", "Daily", "Weekly"]
    },

    # --- 39. Monitoring ---
    {
        "id": "mon_health_probe_interval_s", "category": "monitoring", "name": "Health Probe Frequency (Seconds)", "type": "number",
        "default": 30, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 5, "max": 3600, "unit": "sec"
    },

    # --- 40. Enterprise Administration ---
    {
        "id": "ent_scim_provisioning", "category": "enterprise", "name": "SCIM Directory Sync", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM"
    },

    # --- 41. Feature Flags ---
    {
        "id": "flag_hal_multimodal", "category": "features", "name": "Enable HAL Multimodal Video Diagnostics", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "LOW"
    },

    # --- 42. Advanced ---
    {
        "id": "adv_debug_logging", "category": "advanced", "name": "Extended Kernel Trace & Debug Logging", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM"
    },

    # --- System Diagnostics (Domain 32) ---
    {
        "id": "diag_wal_auto_checkpoint", "category": "diagnostics", "name": "Auto WAL Checkpoint on Startup", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Forces SQLite write-ahead log checkpoint to preserve transaction journal integrity on boot."
    },
    {
        "id": "diag_verbose_kernel_traces", "category": "diagnostics", "name": "Verbose Kernel Execution Traces", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Emits AST instruction evaluations and latency telemetry to daemon stderr."
    },
    {
        "id": "diag_collect_heap_metrics", "category": "diagnostics", "name": "Continuous Process Heap & Memory Metrics", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Samples Python runtime resident memory and GC cycles for performance telemetry."
    },

    # --- 43. Danger Zone ---
    {
        "id": "danger_revoke_all_sessions", "category": "danger", "name": "Revoke All Active Tokens Immediately", "type": "button_action",
        "default": "REVOKE_ACTION", "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL", "requires_approval": True,
        "desc": "Invalidates every active browser, API, and worker bearer token across the host."
    },
    {
        "id": "danger_purge_telemetry", "category": "danger", "name": "Purge Temporary Sandbox Logs", "type": "button_action",
        "default": "PURGE_ACTION", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "requires_approval": True,
        "desc": "Removes temporary terminal and browser scrape artifacts while preserving cryptographically sealed evidence."
    },

    # --- Extended Canonical Domain Settings (Section 13 Coverage) ---
    # Account
    {
        "id": "acc_session_timeout_min", "category": "account", "name": "Host Session Inactivity Timeout (Minutes)", "type": "number",
        "default": 60, "scope": "User", "editable_by": "OWNER", "risk": "LOW", "min": 15, "max": 480, "unit": "min",
        "desc": "Automatic session lock threshold for administrative console."
    },
    {
        "id": "acc_two_factor_method", "category": "account", "name": "Primary 2FA Verification Method", "type": "select",
        "default": "TOTP Authenticator", "scope": "User", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["TOTP Authenticator", "Hardware Passkey (FIDO2)", "SMS / Email Fallback"],
        "desc": "Cryptographic authentication factor enforced on login."
    },
    {
        "id": "acc_keyboard_shortcuts_enabled", "category": "account", "name": "Global Command Palette Shortcuts (Cmd+K)", "type": "toggle",
        "default": True, "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Enables rapid keyboard navigation across settings, domains, and actions."
    },

    # Company
    {
        "id": "comp_subindustry", "category": "company", "name": "Sub-Industry Vertical Focus", "type": "text",
        "default": "Autonomous Enterprise Operations & Cognitive Governance", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Fine-grained industry vertical governing specialized workflow templates."
    },
    {
        "id": "comp_fiscal_year_start", "category": "company", "name": "Fiscal Year Commencement Month", "type": "select",
        "default": "April", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["January", "April", "July", "October"],
        "desc": "Determines annual accounting periods and budgetary rollover schedules."
    },
    {
        "id": "comp_tax_id_number", "category": "company", "name": "Statutory Tax Registration Number", "type": "text",
        "default": "GSTIN-07AAACZ1234A1Z5", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Official corporate tax identification reflected on billing receipts."
    },
    {
        "id": "comp_business_calendar", "category": "company", "name": "Operating Business Calendar Cadence", "type": "select",
        "default": "Monday - Friday (Standard)", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Monday - Friday (Standard)", "Sunday - Thursday (Middle East)", "Continuous 24/7 Engine"],
        "desc": "Operational working days governing autonomous dispatch and mission cadences."
    },

    # Users
    {
        "id": "usr_session_max_concurrent", "category": "users", "name": "Max Concurrent Operator Sessions", "type": "number",
        "default": 5, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 1, "max": 20, "unit": "sessions",
        "desc": "Maximum simultaneous browser or API sessions allowed per user identity."
    },
    {
        "id": "usr_invitation_expiry_hours", "category": "users", "name": "User Invite Link TTL (Hours)", "type": "number",
        "default": 48, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 168, "unit": "hours",
        "desc": "Time window before pending organization invitation tokens expire."
    },
    {
        "id": "usr_password_min_length", "category": "users", "name": "Minimum Password Length Enforcement", "type": "number",
        "default": 14, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 8, "max": 64, "unit": "chars",
        "desc": "Statutory password complexity boundary for non-SSO credentials."
    },
    {
        "id": "usr_require_hardware_passkey", "category": "users", "name": "Enforce FIDO2 Hardware Security Keys", "type": "toggle",
        "default": False, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Refuse software TOTP; require YubiKey or WebAuthn platform authenticator."
    },

    # Enterprise
    {
        "id": "ent_tenant_domain", "category": "enterprise", "name": "Primary Enterprise Custom Domain", "type": "text",
        "default": "zonata.corp.internal", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Authoritative apex domain routing for enterprise single sign-on."
    },
    {
        "id": "ent_saml_sso_enforced", "category": "enterprise", "name": "Enforce SAML 2.0 / OIDC Single Sign-On", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Mandates authentication through Okta, Entra ID, or Google Workspace."
    },
    {
        "id": "ent_tenant_storage_quota_gb", "category": "enterprise", "name": "Tenant Storage Volume Quota (GB)", "type": "number",
        "default": 500, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 50, "max": 10000, "unit": "GB",
        "desc": "Aggregated disk quota for documents, artifacts, and knowledge vectors."
    },
    {
        "id": "ent_multi_workspace_isolation", "category": "enterprise", "name": "Strict Workspace Boundary Isolation", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Prevents cross-workspace data bleed and enforces strict RBAC segregation."
    },
    {
        "id": "ent_data_residency_zone", "category": "enterprise", "name": "Statutory Data Residency Region", "type": "select",
        "default": "IN-Central (Mumbai)", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["IN-Central (Mumbai)", "EU-West (Frankfurt)", "US-East (Virginia)", "SG-East (Singapore)"],
        "desc": "Geographical compute and database pinning zone for sovereignty compliance."
    },
    {
        "id": "ent_authorized_companies", "category": "enterprise", "name": "Authorized Multi-Company Tenants", "type": "multiselect",
        "default": ["ZONATA Technologies Primary", "ZONATA AI Labs", "ZONATA Cloud Services"], "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["ZONATA Technologies Primary", "ZONATA AI Labs", "ZONATA Cloud Services", "ZONATA Robotics Private Limited", "ZONATA Global Holdings"],
        "desc": "Authorized multi-entity portfolio companies permitted under cross-tenant federation."
    },

    # AI CEO
    {
        "id": "ceo_escalation_protocol", "category": "ai_ceo", "name": "Autonomous Anomaly Escalation Protocol", "type": "select",
        "default": "Notify Host & Await Confirmation", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["Notify Host & Await Confirmation", "Quarantine Task & Alert", "Auto-Rollback to Last Checkpoint"],
        "desc": "Action pipeline triggered when cognitive uncertainty exceeds tolerance thresholds."
    },
    {
        "id": "ceo_evidence_retention_days", "category": "ai_ceo", "name": "Executive Decision Evidence Retention (Days)", "type": "number",
        "default": 365, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 30, "max": 3650, "unit": "days",
        "desc": "Retention lifecycle for rationale graphs and executive decision evidence proofs."
    },

    # Workforce
    {
        "id": "wf_agent_budget_monthly", "category": "workforce", "name": "Per-Worker Monthly Inference Budget Ceiling", "type": "currency",
        "default": 25000, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH", "min": 100, "max": 1000000, "unit": "USD",
        "desc": "Expenditure limit per autonomous agent role before throttling."
    },
    {
        "id": "wf_lifecycle_auto_retire_idle_hours", "category": "workforce", "name": "Auto-Decommission Idle Specialized Workers (Hours)", "type": "number",
        "default": 72, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 720, "unit": "hours",
        "desc": "Reclaims compute resources for dynamic agents with zero active missions."
    },
    {
        "id": "wf_memory_isolation_mode", "category": "workforce", "name": "Cognitive Memory Partitioning Boundary", "type": "select",
        "default": "Tenant Strict Namespace", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["Tenant Strict Namespace", "Department Partitioned", "Global Read-Only Knowledge"],
        "desc": "Prevents unauthorized knowledge cross-pollination between agent squads."
    },

    # Workflows (Automation)
    {
        "id": "wf_retries_max", "category": "workflows", "name": "Maximum Step Retry Attempts on Transient Failure", "type": "number",
        "default": 3, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 0, "max": 10, "unit": "retries",
        "desc": "Exponential backoff retry bounds for distributed DAG tasks."
    },
    {
        "id": "wf_dag_execution_timeout_min", "category": "workflows", "name": "Mission Workflow Hard Timeout (Minutes)", "type": "number",
        "default": 120, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 5, "max": 1440, "unit": "minutes",
        "desc": "Terminates hung tasks and triggers compensating rollback actions."
    },
    {
        "id": "wf_auto_compensate_on_fail", "category": "workflows", "name": "Execute Automatic Compensating Saga Actions", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Rolls back external side-effects when distributed multi-step transactions fail."
    },
    {
        "id": "wf_cron_dispatch_enabled", "category": "workflows", "name": "Enable Autonomous Cron & Heartbeat Schedulers", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Enables recurring background job execution and periodic business scans."
    },

    # AI Providers
    {
        "id": "ai_fallback_provider", "category": "ai_providers", "name": "Failover Backup AI Model Provider", "type": "select",
        "default": "Anthropic Claude 3.5 Sonnet", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["Anthropic Claude 3.5 Sonnet", "OpenAI GPT-4o", "DeepSeek-V3", "Local Ollama 70B"],
        "desc": "Secondary model routed to when primary inference endpoint experiences outages."
    },
    {
        "id": "ai_cost_cap_per_turn_usd", "category": "ai_providers", "name": "Single Inference Turn Maximum Spend ($)", "type": "currency",
        "default": 2.50, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "min": 0.1, "max": 50.0, "unit": "USD",
        "desc": "Prevents catastrophic context-window expansion costs on large documents."
    },
    {
        "id": "ai_request_timeout_seconds", "category": "ai_providers", "name": "LLM Provider HTTP Request Timeout (Seconds)", "type": "number",
        "default": 60, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 5, "max": 300, "unit": "seconds",
        "desc": "Network socket timeout threshold for external cognitive API gateways."
    },

    # Tools
    {
        "id": "tool_allow_network_egress", "category": "tools", "name": "Allow Outbound Internet Egress from Sandbox", "type": "toggle",
        "default": False, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Allows sandboxed tool commands to query public external networks."
    },
    {
        "id": "tool_audit_payloads", "category": "tools", "name": "Capture Complete Tool Invocation Arguments in Evidence", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Records full JSON stdin and stdout in immutable execution receipt."
    },
    {
        "id": "tool_max_execution_duration_sec", "category": "tools", "name": "Tool Execution Time Limit (Seconds)", "type": "number",
        "default": 120, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 5, "max": 600, "unit": "seconds",
        "desc": "Maximum runtime lease granted to sandboxed process executions."
    },

    # Desktop
    {
        "id": "desk_input_cooldown_ms", "category": "desktop", "name": "Hardware Mouse & Keyboard Event Rate Limit (ms)", "type": "number",
        "default": 250, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 50, "max": 2000, "unit": "ms",
        "desc": "Prevents runaway mechanical input loops and OS freeze events."
    },
    {
        "id": "desk_screen_masking_enabled", "category": "desktop", "name": "Mask Sensitive Passwords in Screen Captures", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Blurs password input boxes and financial balances from perceptual vision scans."
    },
    {
        "id": "desk_kill_switch_hotkey", "category": "desktop", "name": "Physical Emergency Halt Hotkey Binding", "type": "text",
        "default": "Ctrl+Alt+Escape", "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Global hardware key combination that immediately kills the OS robot daemon."
    },

    # Browser
    {
        "id": "browser_download_allowed", "category": "browser", "name": "Allow Automatic File Downloads in Browser", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Permits automated file retrieval to sandboxed temporary storage directory."
    },
    {
        "id": "browser_session_isolation", "category": "browser", "name": "Incognito Ephemeral Browser Context Per Task", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Destroys cookies, session storage, and cache immediately upon mission completion."
    },
    {
        "id": "browser_navigation_timeout_sec", "category": "browser", "name": "Page DOM Load & Network Idle Timeout (Seconds)", "type": "number",
        "default": 45, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 10, "max": 180, "unit": "seconds",
        "desc": "Navigation wait threshold before raising an automated page timeout exception."
    },

    # Terminal
    {
        "id": "term_network_isolated", "category": "terminal", "name": "Enforce Network Namespace Isolation (Air-Gapped)", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Disables network interfaces for terminal shell processes to prevent SSRF and exfiltration."
    },
    {
        "id": "term_cgroup_cpu_shares", "category": "terminal", "name": "Linux Cgroup CPU Share Weight Allocation", "type": "number",
        "default": 512, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 128, "max": 2048, "unit": "shares",
        "desc": "Kernel throttling boundary preventing compute starvation by background worker shells."
    },
    {
        "id": "term_allowed_command_prefixes", "category": "terminal", "name": "Authorized Shell Executable Allowlist", "type": "text",
        "default": "git,python3,node,ls,cat,grep,echo,find,tar,gzip", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Comma-delimited binary prefixes permitted inside the governed terminal sandbox."
    },

    # MCP
    {
        "id": "mcp_max_connected_servers", "category": "mcp", "name": "Maximum Active MCP Server Connections", "type": "number",
        "default": 8, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 1, "max": 32, "unit": "servers", "unit": "servers",
        "desc": "Connection pooling threshold for concurrent Model Context Protocol daemons."
    },
    {
        "id": "mcp_json_rpc_timeout_sec", "category": "mcp", "name": "MCP JSON-RPC Handshake Timeout (Seconds)", "type": "number",
        "default": 30, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 5, "max": 120, "unit": "seconds",
        "desc": "Socket latency ceiling for protocol initialization and tool listing queries."
    },
    {
        "id": "mcp_enforce_tls", "category": "mcp", "name": "Mandate TLS Encryption on Remote MCP Transports", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Refuse plaintext SSE / HTTP transport endpoints for remote MCP servers."
    },
    {
        "id": "mcp_auth_token", "category": "mcp", "name": "MCP Gateway Bearer Authentication Secret", "type": "token",
        "default": "mcp_sec_live_9f81a7b3c2e5d1", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH", "secret": True,
        "desc": "Masked credential verifying authorization between agent swarm and MCP hosts."
    },

    # A2A
    {
        "id": "a2a_peer_discovery_mode", "category": "a2a", "name": "Peer Agent Network Discovery Protocol", "type": "select",
        "default": "Gossip Mesh (Scoped)", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["Gossip Mesh (Scoped)", "Central Broker Directory", "Manual Allowlist Only"],
        "desc": "Mechanism by which agents discover specialized coworkers across the trust graph."
    },
    {
        "id": "a2a_rate_limit_per_min", "category": "a2a", "name": "Inter-Agent Message Rate Limit (Msg/Min)", "type": "number",
        "default": 120, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 10, "max": 1000, "unit": "req/min",
        "desc": "Prevents infinite message loops and cognitive feedback storms between agents."
    },
    {
        "id": "a2a_cross_company_allowed", "category": "a2a", "name": "Allow Cross-Company Federation Communications", "type": "toggle",
        "default": False, "scope": "Company", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Strict boundary switch governing whether agents can federate across tenant walls."
    },
    {
        "id": "a2a_message_encryption_cipher", "category": "a2a", "name": "Inter-Agent Transport Encryption Cipher", "type": "select",
        "default": "ChaCha20-Poly1305", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["ChaCha20-Poly1305", "AES-256-GCM"],
        "desc": "Cryptographic authenticated encryption suite securing agent-to-agent envelopes."
    },

    # Integrations
    {
        "id": "integ_oauth_refresh_cadence_hours", "category": "integrations", "name": "OAuth Access Token Preemptive Refresh Cadence", "type": "number",
        "default": 12, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 72, "unit": "hours",
        "desc": "Proactive token refresh interval ensuring continuous uninterrupted SaaS connectivity."
    },
    {
        "id": "integ_sync_cadence_minutes", "category": "integrations", "name": "Universal Data Ingestion Polling Interval (Minutes)", "type": "number",
        "default": 15, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 1, "max": 1440, "unit": "minutes",
        "desc": "Synchronization schedule for pull connectors (CRM, ERP, Accounting)."
    },
    {
        "id": "integ_auto_revoke_on_anomaly", "category": "integrations", "name": "Auto-Revoke Connector on Cryptographic Anomaly", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Immediately invalidates connection credentials if token tampering or unexpected scopes are detected."
    },
    {
        "id": "integ_webhook_signature_secret", "category": "integrations", "name": "Inbound Webhook Verification HMAC Secret", "type": "token",
        "default": "whsec_live_58c2a9341ef8b720", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH", "secret": True,
        "desc": "Secret key verifying authenticity of incoming webhooks from external enterprise SaaS."
    },

    # Data
    {
        "id": "data_semantic_indexing_enabled", "category": "data", "name": "Continuous Semantic Vector Indexing (RAG)", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Indexes uploaded files into dense vector space for fast cognitive retrieval."
    },
    {
        "id": "data_pii_auto_redaction", "category": "data", "name": "Pre-Ingestion PII / Sensitive Data Redaction", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Strips national identifiers, payment cards, and phone numbers before document embedding."
    },
    {
        "id": "data_max_file_upload_mb", "category": "data", "name": "Maximum Ingested Document Size (MB)", "type": "number",
        "default": 50, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 5, "max": 500, "unit": "MB",
        "desc": "Upper file size limit for enterprise PDF, DOCX, CSV, and code bundle ingestion."
    },
    {
        "id": "data_backup_checksum_verify", "category": "data", "name": "Verify SHA-256 Checksum on Every Ingested Asset", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Validates cryptographic file hash before committing document to database storage."
    },

    # Finance
    {
        "id": "fin_strict_dual_signoff_threshold", "category": "finance", "name": "Mandatory Dual Sign-Off Threshold Amount", "type": "currency",
        "default": 100000, "scope": "Company", "editable_by": "OWNER", "risk": "CRITICAL", "min": 1000, "max": 5000000, "unit": "USD",
        "desc": "Transactions exceeding this amount require two distinct executive approval signatures."
    },
    {
        "id": "fin_fiscal_close_lock", "category": "finance", "name": "Lock Historical Fiscal Period Records Against Edits", "type": "toggle",
        "default": False, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Freezes finalized accounting ledger entries to prevent retrospective mutations."
    },
    {
        "id": "fin_auto_receipt_reconciliation", "category": "finance", "name": "Autonomous OCR Receipt Reconciliation Engine", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Matches bank transaction records against vendor invoices and proof slips automatically."
    },

    # Billing
    {
        "id": "cost_hard_stop_at_threshold", "category": "billing", "name": "Enforce Immediate Hard Halt When Spend Exceeds Cap", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Blocks further billable inference calls when consumption reaches 100% of the allocated cap."
    },
    {
        "id": "cost_overage_charge_cap_usd", "category": "billing", "name": "Maximum Authorized Monthly Overage Buffer ($)", "type": "currency",
        "default": 5000, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH", "min": 0, "max": 50000, "unit": "USD",
        "desc": "Emergency headroom allowance for critical production workloads prior to complete shutdown."
    },

    # Security
    {
        "id": "sec_max_login_attempts", "category": "security", "name": "Failed Login Attempts Before Account Lockdown", "type": "number",
        "default": 5, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "min": 3, "max": 10, "unit": "attempts",
        "desc": "Mitigates credential stuffing by locking out identities after repeated failures."
    },
    {
        "id": "sec_enforce_ip_allowlist", "category": "security", "name": "Enforce Administrative IP CIDR Whitelist", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Restricts settings modifications to pre-approved corporate VPN ranges."
    },
    {
        "id": "sec_passkey_enabled", "category": "security", "name": "Enable WebAuthn / FIDO2 Passkey Passwordless Login", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Enables biometric Touch ID / Windows Hello login flows for sovereign operators."
    },

    # Governance
    {
        "id": "gov_two_person_rule", "category": "governance", "name": "Enforce Sovereign Two-Person Rule on System Policies", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Constitutional requirement: critical policy changes require approval from a secondary authority."
    },
    {
        "id": "gov_risk_threshold_matrix", "category": "governance", "name": "Constitutional Boundary Risk Assessment Matrix", "type": "select",
        "default": "Strict Constitutional Boundary", "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "options": ["Strict Constitutional Boundary", "Balanced Enterprise Guardrail", "Autonomous Experimental"],
        "desc": "Determines the threshold at which agent actions must escalate to human oversight."
    },
    {
        "id": "gov_emergency_escalation_tier", "category": "governance", "name": "Emergency Escalation Notification Channel", "type": "select",
        "default": "Tier 1: Sovereign Host Real-Time Alert", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["Tier 1: Sovereign Host Real-Time Alert", "Tier 2: Dual Administrator Consensus", "Tier 3: Automated Fail-Safe Quarantine"],
        "desc": "Routing protocol for statutory and policy violation events."
    },
    {
        "id": "gov_sovereign_override_pin_required", "category": "governance", "name": "Require Hardware PIN for Emergency Overrides", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Prompts operator for cryptographic secondary PIN before overriding governance kill switches."
    },

    # Privacy
    {
        "id": "priv_gdpr_compliance_mode", "category": "privacy", "name": "Enforce GDPR / DPDPA Statutory Privacy Controls", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Activates automatic consent verification and right-to-be-forgotten tracking."
    },
    {
        "id": "priv_ai_training_zero_retention", "category": "privacy", "name": "Zero-Retention Guarantee on External AI Inference", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Enforces enterprise contract flags preventing AI providers from training on corporate prompts."
    },
    {
        "id": "priv_data_subject_request_window_days", "category": "privacy", "name": "Data Subject Access Request SLA (Days)", "type": "number",
        "default": 30, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 7, "max": 60, "unit": "days",
        "desc": "Maximum statutory timeframe permitted to fulfill customer data export and purge requests."
    },
    {
        "id": "priv_anonymize_audit_exports", "category": "privacy", "name": "Anonymize Operator PII in External Audit Exports", "type": "toggle",
        "default": True, "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Replaces real user names with pseudonymized cryptographic identifiers in public compliance filings."
    },

    # Audit
    {
        "id": "audit_retention_days", "category": "audit", "name": "Immutable Cryptographic Audit Retention (Days)", "type": "number",
        "default": 730, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 90, "max": 3650, "unit": "days",
        "desc": "Statutory ledger retention duration before automated archive rotation."
    },
    {
        "id": "audit_tamper_alert_channel", "category": "audit", "name": "Merkle Tree Tamper Detection Alert Destination", "type": "select",
        "default": "Immediate Host Pager + Syslog", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["Immediate Host Pager + Syslog", "Syslog Relay Only", "In-App Notice"],
        "desc": "Notification target triggered if any historical cryptographic hash chain mismatch occurs."
    },
    {
        "id": "audit_merkle_validation_cadence_hours", "category": "audit", "name": "Automated Merkle Root Verification Cadence (Hours)", "type": "number",
        "default": 24, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 168, "unit": "hours",
        "desc": "Interval for full mathematical verification of SHA-256 chain continuity across all records."
    },

    # Recovery
    {
        "id": "recovery_cold_sync_enabled", "category": "recovery", "name": "Replicate Encrypted Snapshots to Cold Storage", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Transfers verified SQLite snapshots to offsite geographically separated storage vault."
    },
    {
        "id": "recovery_rpo_minutes", "category": "recovery", "name": "Recovery Point Objective Target (RPO in Minutes)", "type": "number",
        "default": 15, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "min": 1, "max": 120, "unit": "minutes",
        "desc": "Maximum permissible duration of transactional data loss in catastrophe scenarios."
    },
    {
        "id": "recovery_rto_minutes", "category": "recovery", "name": "Recovery Time Objective Target (RTO in Minutes)", "type": "number",
        "default": 5, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "min": 1, "max": 60, "unit": "minutes",
        "desc": "Target maximum downtime to restore full database and control plane availability."
    },
    {
        "id": "recovery_drill_auto_schedule", "category": "recovery", "name": "Autonomous Disaster Recovery Drill Schedule", "type": "select",
        "default": "Weekly Autonomous Dry-Run", "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "options": ["Weekly Autonomous Dry-Run", "Monthly Drill", "Disabled (Manual Only)"],
        "desc": "Schedules automated sandbox restores to verify database backup integrity."
    },

    # Monitoring
    {
        "id": "mon_circuit_breaker_threshold", "category": "monitoring", "name": "Subsystem Circuit Breaker Consecutive Error Trip Limit", "type": "number",
        "default": 5, "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "min": 1, "max": 20, "unit": "failures",
        "desc": "Trips fail-safe isolation after consecutive failures on an external API or tool endpoint."
    },
    {
        "id": "mon_liveness_probe_interval_sec", "category": "monitoring", "name": "Subsystem Internal Liveness Probe Frequency (Seconds)", "type": "number",
        "default": 10, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 2, "max": 60, "unit": "seconds",
        "desc": "Health monitor check cadence across SQLite, Redis, agent worker bus, and HTTP gateway."
    },
    {
        "id": "mon_drift_check_cadence_min", "category": "monitoring", "name": "Configuration Drift Audit Verification Cadence (Minutes)", "type": "number",
        "default": 5, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 60, "unit": "minutes",
        "desc": "Compares in-memory runtime cache against persisted SQLite state to guarantee zero drift."
    },
    {
        "id": "mon_telemetry_export_format", "category": "monitoring", "name": "Telemetry Metric Protocol Format", "type": "select",
        "default": "OpenTelemetry OTLP", "scope": "Host", "editable_by": "OWNER", "risk": "LOW",
        "options": ["OpenTelemetry OTLP", "Prometheus Metrics", "JSON Structured Syslog"],
        "desc": "Format emitted to observability collectors (Datadog, Grafana, OpenTelemetry)."
    },

    # API
    {
        "id": "api_bearer_auth_enabled", "category": "api", "name": "Mandate Bearer Token Authentication on REST API", "type": "toggle",
        "default": True, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Rejects any unauthenticated API requests with HTTP 401 Unauthorized."
    },
    {
        "id": "api_developer_key_vault", "category": "api", "name": "Primary Developer Bearer Key Token", "type": "token",
        "default": "zapi_live_9b4e872c019df53a", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH", "secret": True,
        "desc": "High-privilege developer bearer secret for programmatic control-plane access."
    },
    {
        "id": "api_cors_allowed_origins", "category": "api", "name": "Permitted CORS Origin Hosts (Comma-Delimited)", "type": "text",
        "default": "https://zonata.internal,http://localhost:8080", "scope": "Host", "editable_by": "OWNER", "risk": "HIGH",
        "desc": "Allowed cross-origin browser endpoints permitted to interact with the API."
    },
    {
        "id": "api_egress_ip_whitelist", "category": "api", "name": "Authorized API Caller Egress CIDR Allowlist", "type": "text",
        "default": "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1/32", "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Restricts API access to verified enterprise subnet CIDRs."
    },

    # Webhooks
    {
        "id": "webhook_retry_max_attempts", "category": "webhooks", "name": "Webhook Dispatch Max Retry Attempts", "type": "number",
        "default": 5, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 0, "max": 10, "unit": "retries",
        "desc": "Maximum automated delivery retries on non-2xx HTTP responses."
    },
    {
        "id": "webhook_backoff_factor_sec", "category": "webhooks", "name": "Exponential Retry Backoff Multiplier (Seconds)", "type": "number",
        "default": 2, "scope": "Company", "editable_by": "OWNER", "risk": "LOW", "min": 1, "max": 10, "unit": "seconds",
        "desc": "Multiplication factor determining backoff delay between subsequent delivery attempts."
    },
    {
        "id": "webhook_signing_algorithm", "category": "webhooks", "name": "Webhook Payload Signing Cryptographic Algorithm", "type": "select",
        "default": "HMAC-SHA256", "scope": "Company", "editable_by": "OWNER", "risk": "HIGH",
        "options": ["HMAC-SHA256", "HMAC-SHA512", "Ed25519"],
        "desc": "Signature standard encoded in X-Zonata-Signature header for receiver verification."
    },
    {
        "id": "webhook_egress_timeout_sec", "category": "webhooks", "name": "Outbound Webhook HTTP Timeout (Seconds)", "type": "number",
        "default": 10, "scope": "Company", "editable_by": "OWNER", "risk": "MEDIUM", "min": 2, "max": 60, "unit": "seconds",
        "desc": "TCP socket timeout for external webhook endpoint responses."
    },

    # Localization
    {
        "id": "loc_base_locale", "category": "localization", "name": "Universal Enterprise Reporting Locale", "type": "select",
        "default": "en-IN", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["en-IN", "en-US", "en-GB", "de-DE", "ja-JP", "ar-AE"],
        "desc": "Base language and regional formatting standard for documents and notifications."
    },
    {
        "id": "loc_number_format", "category": "localization", "name": "Financial Number & Comma Grouping Convention", "type": "select",
        "default": "1,00,000.00 (Indian Lakh/Crore)", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["1,00,000.00 (Indian Lakh/Crore)", "100,000.00 (International Standard)", "100.000,00 (Continental European)"],
        "desc": "Presentation standard for financial ledgers, invoice metrics, and balances."
    },
    {
        "id": "loc_first_day_of_week", "category": "localization", "name": "First Day of the Business Week", "type": "select",
        "default": "Monday", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Monday", "Sunday", "Saturday"],
        "desc": "Defines weekly reporting boundaries and operational sprint schedules."
    },
    {
        "id": "loc_currency_display", "category": "localization", "name": "Monetary Value Display Format", "type": "select",
        "default": "Symbol (₹)", "scope": "Company", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Symbol (₹)", "ISO Code (INR)", "Full Name (Indian Rupee)"],
        "desc": "Controls prefix formatting on all financial values across the console."
    },

    # Appearance
    {
        "id": "app_reduced_motion", "category": "appearance", "name": "Reduced Motion Interface Mode", "type": "toggle",
        "default": False, "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "desc": "Minimizes animations, modal transitions, and drawer sliding effects for accessibility."
    },
    {
        "id": "app_navigation_density", "category": "appearance", "name": "Sidebar Navigation Density Layout", "type": "select",
        "default": "Compact Control Plane", "scope": "User", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Compact Control Plane", "Standard Enterprise", "Spacious Touch"],
        "desc": "Controls vertical padding and icon sizing across the persistent desktop sidebar."
    },
    {
        "id": "app_font_scale_pct", "category": "appearance", "name": "Interface Typography Scale (Percentage)", "type": "slider",
        "default": 100, "scope": "User", "editable_by": "OWNER", "risk": "LOW", "min": 80, "max": 130, "unit": "%",
        "desc": "Scales body, header, and card typography for accessibility preferences."
    },

    # Advanced
    {
        "id": "adv_kernel_cache_ttl_sec", "category": "advanced", "name": "Universal Kernel Cache TTL (Seconds)", "type": "number",
        "default": 300, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM", "min": 30, "max": 3600, "unit": "seconds",
        "desc": "Duration to cache policy evaluation results and permission tokens in memory."
    },
    {
        "id": "adv_isolate_quarantine_mode", "category": "advanced", "name": "Instant Subsystem Isolation Quarantine Mode", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "CRITICAL",
        "desc": "Sever all external network transports and suspend autonomous agent missions immediately."
    },
    {
        "id": "adv_verbose_kernel_traces", "category": "advanced", "name": "Emit Verbose Kernel Execution Traces to Syslog", "type": "toggle",
        "default": False, "scope": "Host", "editable_by": "OWNER", "risk": "MEDIUM",
        "desc": "Prints detailed AST evaluation metrics, memory allocations, and execution timings."
    },

    # Diagnostics
    {
        "id": "diag_inference_ping_interval_sec", "category": "diagnostics", "name": "AI Inference Live Health Ping Interval (Seconds)", "type": "number",
        "default": 30, "scope": "Host", "editable_by": "OWNER", "risk": "LOW", "min": 5, "max": 300, "unit": "seconds",
        "desc": "Cadence for automated probe testing of primary and fallback LLM endpoints."
    },
    {
        "id": "diag_active_subsystem_probe", "category": "diagnostics", "name": "Subsystem Diagnostic Probe Execution Strategy", "type": "select",
        "default": "Continuous Adaptive Ping", "scope": "Host", "editable_by": "OWNER", "risk": "LOW",
        "options": ["Continuous Adaptive Ping", "On-Demand Only", "Passive Monitoring"],
        "desc": "Execution model for probing database, terminal, browser, and network layers."
    }
]
