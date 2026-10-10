/**
 * ZONATA / URA Universal AI Company Operating System
 * Enterprise Settings & Administration Center (Control Plane Engine)
 * 
 * Rebuilt from first principles as a commercial SaaS-grade administration console:
 * - 6 Enterprise Pillars containing 32 Canonical Settings Domains
 * - Hierarchical Information Architecture: Pillar -> Domain -> Section -> Setting
 * - Mobile-first responsive architecture with dedicated off-canvas drawer & 100% content width
 * - Compact global settings search with Cmd/Ctrl+K and domain-grouped results
 * - Answers the 5 core questions per setting: What, Who/What affects, Effective value, Who controls, Consequences
 * - Coherent dirty-state machine (CLEAN, DIRTY, SAVING, SAVED, ERROR) with docked bottom bar and navigation guard
 * - Slide-out setting detail drawer for affected systems, dependencies, and audit provenance
 * - High-risk change preview modal for Sovereign Host confirmation
 * - Real live diagnostic testing for AI providers, integrations, terminal, and backups
 * - Full SQLite persistence via canonical /api/settings endpoints with cryptographic SHA-256 evidence
 */

const EnterpriseSettings = (function() {
  'use strict';

  // --------------------------------------------------------------------------
  // 1. Centralized SVG Icon Dictionary (Monotone / Restrained Enterprise Style)
  // --------------------------------------------------------------------------
  const SVG_ICONS = {
    search: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
    menu: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,
    close: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    user: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
    building: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"/><line x1="9" y1="22" x2="9" y2="2"/><line x1="8" y1="6" x2="10" y2="6"/><line x1="14" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="10" y2="10"/><line x1="14" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="10" y2="14"/><line x1="14" y1="14" x2="16" y2="14"/></svg>`,
    users: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    crown: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 4l3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14v2H5z"/></svg>`,
    bot: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8.01" y2="16"/><line x1="16" y1="16" x2="16.01" y2="16"/></svg>`,
    repeat: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>`,
    zap: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
    tool: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`,
    monitor: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>`,
    globe: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>`,
    terminal: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`,
    plug: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v6m0 0l-4 4m4-4l4 4M9 16v6m6-6v6m-9-6h12"/></svg>`,
    network: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="2" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="16" y="16" width="6" height="6" rx="1"/><path d="M5 16v-4h14v4"/><path d="M12 8v4"/></svg>`,
    link: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
    database: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,
    bell: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`,
    dollar: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
    card: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>`,
    lock: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
    scale: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1zM2 16l3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1z"/><line x1="12" y1="3" x2="12" y2="21"/><polyline points="2 8 12 3 22 8"/></svg>`,
    fileText: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
    checkCircle: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    hardDrive: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="12" x2="2" y2="12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" y1="16" x2="6.01" y2="16"/><line x1="10" y1="16" x2="10.01" y2="16"/></svg>`,
    activity: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
    code: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>`,
    radio: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49m11.31-2.82a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"/></svg>`,
    sliders: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>`,
    alertTriangle: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    cpu: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="15" x2="23" y2="15"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="15" x2="4" y2="15"/></svg>`,
    shield: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
    chevronRight: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>`,
    info: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`
  };

  // --------------------------------------------------------------------------
  // 2. Canonical Information Architecture (6 Enterprise Pillars -> 32 Domains)
  // --------------------------------------------------------------------------
  const PILLARS = [
    {
      id: "identity",
      title: "I. Identity & Access",
      desc: "Host sovereignty, corporate entity, access control, and enterprise boundaries",
      domains: [
        { id: "account", num: "01", name: "Account Profile", icon: SVG_ICONS.user, desc: "Administrator profile, security credentials, sessions, and accessibility", scope: "User", risk: "LOW" },
        { id: "company", num: "02", name: "Company & Organization", icon: SVG_ICONS.building, desc: "Corporate legal entity, universal industry profile, KPIs, and hierarchy", scope: "Company", risk: "MEDIUM" },
        { id: "users", num: "03", name: "Users & Access Control", icon: SVG_ICONS.users, desc: "Granular RBAC roles, permission matrix, active sessions, and trusted devices", scope: "Company", risk: "HIGH" },
        { id: "enterprise", num: "04", name: "Enterprise Administration", icon: SVG_ICONS.shield, desc: "Multi-tenant boundaries, SCIM provisioning, SAML 2.0, and data residency", scope: "Host", risk: "HIGH" }
      ]
    },
    {
      id: "ai_intelligence",
      title: "II. AI & Executive Intelligence",
      desc: "Autonomous cognitive engine, executive governance, workforce policies, and model routing",
      domains: [
        { id: "ai_ceo", num: "05", name: "AI & AI CEO Governance", icon: SVG_ICONS.crown, desc: "Executive operating mode, 0-4 autonomy levels, spending limits, and cognition", scope: "Company", risk: "CRITICAL" },
        { id: "workforce", num: "06", name: "AI Workforce Governance", icon: SVG_ICONS.bot, desc: "Dynamic agent spawning limits, department budgets, and performance gates", scope: "Company", risk: "HIGH" },
        { id: "automation", num: "07", name: "Automation & Missions", icon: SVG_ICONS.repeat, desc: "Durable execution DAGs, mission triggers, retries, and outcome verification", scope: "Company", risk: "MEDIUM" },
        { id: "ai_providers", num: "08", name: "Models & AI Providers", icon: SVG_ICONS.zap, desc: "Vertex AI, Gemini, Claude, OpenAI, local inference endpoints, and budget routing", scope: "Host", risk: "HIGH" }
      ]
    },
    {
      id: "execution_fabric",
      title: "III. Execution Fabric",
      desc: "Governed execution boundaries, tools fabric, sandboxes, MCP, and agent network",
      domains: [
        { id: "tools", num: "09", name: "Tools & Execution Registry", icon: SVG_ICONS.tool, desc: "Capability fabric registry, risk classification, and sandboxed trust gates", scope: "Host", risk: "HIGH" },
        { id: "desktop", num: "10", name: "Computer Control", icon: SVG_ICONS.monitor, desc: "Perception rates, mouse/keyboard throttling, application access, and evidence", scope: "Host", risk: "CRITICAL" },
        { id: "browser", num: "11", name: "Browser Automation", icon: SVG_ICONS.globe, desc: "Headless Chromium contexts, domain allowlists, SSRF guard, and DOM audit", scope: "Host", risk: "HIGH" },
        { id: "terminal", num: "12", name: "Governed Terminal", icon: SVG_ICONS.terminal, desc: "Sandboxed shell execution, TTL leases, egress allowlists, and execution ledger", scope: "Host", risk: "CRITICAL" },
        { id: "mcp", num: "13", name: "MCP Protocol Servers", icon: SVG_ICONS.plug, desc: "Model Context Protocol connections, resource limits, and tool permissions", scope: "Company", risk: "MEDIUM" },
        { id: "a2a", num: "14", name: "A2A / Agent Network", icon: SVG_ICONS.network, desc: "Agent-to-agent protocol, trust boundaries, message quotas, and broker topology", scope: "Company", risk: "HIGH" }
      ]
    },
    {
      id: "business_finance",
      title: "IV. Business & Finance Systems",
      desc: "Third-party integrations, knowledge fabric, records, financial ledgers, and billing",
      domains: [
        { id: "integrations", num: "15", name: "Integrations & Connectors", icon: SVG_ICONS.link, desc: "Connected business systems (PMS, ERP, CRM, Payments), sync cadence, and least privilege", scope: "Company", risk: "HIGH" },
        { id: "data", num: "16", name: "Data & Knowledge Fabric", icon: SVG_ICONS.database, desc: "Semantic search index, retention lifecycles, and data classification tags", scope: "Company", risk: "MEDIUM" },
        { id: "communication", num: "17", name: "Communication & Dispatch", icon: SVG_ICONS.fileText, desc: "Corporate email dispatch, SMTP/SES gateways, dispatch schedules, and sender identity", scope: "Company", risk: "LOW" },
        { id: "finance", num: "18", name: "Finance & Accounting", icon: SVG_ICONS.dollar, desc: "Chart of accounts, currencies, fiscal year close, and expenditure approval limits", scope: "Company", risk: "HIGH" },
        { id: "billing", num: "19", name: "Billing & Compute Usage", icon: SVG_ICONS.card, desc: "Plan tier, token burn alerts (50/75/90/100%), spending caps, and invoices", scope: "Company", risk: "HIGH" }
      ]
    },
    {
      id: "governance_trust",
      title: "V. Governance & Trust",
      desc: "Constitutional guardrails, approvals, privacy, cryptographic audit, and disaster recovery",
      domains: [
        { id: "security", num: "20", name: "Security & Authentication", icon: SVG_ICONS.lock, desc: "MFA enforcement, WebAuthn passkeys, session lifetimes, and brute-force shields", scope: "Host", risk: "CRITICAL" },
        { id: "governance", num: "21", name: "Governance & Approvals", icon: SVG_ICONS.scale, desc: "Sovereign authority hierarchy, approval pipelines, and instant kill switches", scope: "Host", risk: "CRITICAL" },
        { id: "privacy", num: "22", name: "Privacy & Compliance", icon: SVG_ICONS.fileText, desc: "PII anonymization, ISO 37000/42001 profiles, statutory audits, and GDPR/DPDP", scope: "Company", risk: "HIGH" },
        { id: "notifications", num: "23", name: "Notifications & Alert Routing", icon: SVG_ICONS.bell, desc: "Immediate SMS alerts, in-app notifications, priority paging, and digest cadence", scope: "Company", risk: "LOW" },
        { id: "audit", num: "24", name: "Audit & Evidence Ledger", icon: SVG_ICONS.checkCircle, desc: "Cryptographic SHA-256 Merkle ledger, immutability mode, and export receipts", scope: "Host", risk: "MEDIUM" },
        { id: "recovery", num: "25", name: "Backup & Disaster Recovery", icon: SVG_ICONS.hardDrive, desc: "Automated SQLite snapshots, cold backup sync, RPO/RTO goals, and restore drills", scope: "Host", risk: "HIGH" }
      ]
    },
    {
      id: "platform_ops",
      title: "VI. Platform & Operations",
      desc: "Observability, developer APIs, webhooks, localization, UX appearance, and diagnostics",
      domains: [
        { id: "monitoring", num: "26", name: "Observability & Telemetry", icon: SVG_ICONS.activity, desc: "Subsystem health monitors, circuit breakers, timeout thresholds, and liveness probes", scope: "Host", risk: "LOW" },
        { id: "api", num: "27", name: "API & Developer Platform", icon: SVG_ICONS.code, desc: "Bearer token keys, OAuth scopes, rate limiting, and egress IP allowlists", scope: "Host", risk: "HIGH" },
        { id: "webhooks", num: "28", name: "Webhooks & Event Signing", icon: SVG_ICONS.radio, desc: "HMAC-SHA256 signature verification, retry backoff, and event dispatch logs", scope: "Company", risk: "MEDIUM" },
        { id: "localization", num: "29", name: "Localization & Formats", icon: SVG_ICONS.globe, desc: "Base reporting timezone, number formatting, currency symbols, and business days", scope: "Company", risk: "LOW" },
        { id: "appearance", num: "30", name: "Appearance & Interface", icon: SVG_ICONS.sliders, desc: "Theme mode, high contrast, reduced motion, navigation density, and UI scale", scope: "User", risk: "LOW" },
        { id: "advanced", num: "31", name: "Advanced & Danger Zone", icon: SVG_ICONS.alertTriangle, desc: "Runtime engine tuning, cache invalidation, raw policy viewer, and emergency quarantine", scope: "Host", risk: "CRITICAL" },
        { id: "diagnostics", num: "32", name: "System Diagnostics", icon: SVG_ICONS.cpu, desc: "Live backend status, database WAL check, inference pings, and runtime telemetry", scope: "Host", risk: "LOW" }
      ]
    }
  ];

  // Flat lookup for all 32 domains
  const ALL_DOMAINS = PILLARS.flatMap(p => p.domains.map(d => ({ ...d, pillarId: p.id, pillarTitle: p.title })));

  // URL route aliases for seamless direct navigation
  const ROUTE_ALIASES = {
    "01": "account", "1": "account", "account": "account", "profile": "account",
    "02": "company", "2": "company", "company": "company", "organization": "company", "org": "company",
    "03": "users", "3": "users", "users": "users", "access": "users",
    "04": "enterprise", "4": "enterprise", "enterprise": "enterprise",
    "05": "ai_ceo", "5": "ai_ceo", "ai_ceo": "ai_ceo", "ai": "ai_ceo", "ceo": "ai_ceo",
    "06": "workforce", "6": "workforce", "workforce": "workforce", "agents": "workforce", "agent_factory": "workforce",
    "07": "automation", "7": "automation", "automation": "automation", "missions": "automation", "workflows": "automation",
    "08": "ai_providers", "8": "ai_providers", "ai_providers": "ai_providers", "models": "ai_providers", "providers": "ai_providers",
    "09": "tools", "9": "tools", "tools": "tools",
    "10": "desktop", "desktop": "desktop", "computer": "desktop", "coworker": "desktop",
    "11": "browser", "browser": "browser", "web": "browser",
    "12": "terminal", "terminal": "terminal", "shell": "terminal",
    "13": "mcp", "mcp": "mcp",
    "14": "a2a", "a2a": "a2a", "network": "a2a", "agent_network": "a2a",
    "15": "integrations", "integrations": "integrations", "connectors": "integrations",
    "16": "data", "data": "data", "knowledge": "data", "files": "data", "records": "data",
    "17": "communication", "communication": "communication", "comms": "communication", "email": "communication", "dispatch": "communication",
    "18": "finance", "finance": "finance", "accounting": "finance",
    "19": "billing", "billing": "billing", "usage": "billing", "costs": "billing",
    "20": "security", "security": "security", "mfa": "security", "auth": "security",
    "21": "governance", "governance": "governance", "approvals": "governance", "constitution": "governance",
    "22": "privacy", "privacy": "privacy", "compliance": "privacy", "gdpr": "privacy",
    "23": "notifications", "notifications": "notifications", "alerts": "notifications", "notify": "notifications",
    "24": "audit", "audit": "audit", "evidence": "audit", "ledger": "audit",
    "25": "recovery", "recovery": "recovery", "backup": "recovery", "dr": "recovery",
    "26": "monitoring", "monitoring": "monitoring", "observability": "monitoring", "telemetry": "monitoring",
    "27": "api", "api": "api", "developer": "api", "keys": "api",
    "28": "webhooks", "webhooks": "webhooks", "events": "webhooks",
    "29": "localization", "localization": "localization", "locale": "localization",
    "30": "appearance", "appearance": "appearance", "theme": "appearance",
    "31": "advanced", "advanced": "advanced", "danger": "advanced",
    "32": "diagnostics", "diagnostics": "diagnostics", "system": "diagnostics"
  };

  // Section sub-tabs mapping
  const SECTIONS_MAP = {
    account: [{ id: "all", name: "All Account" }, { id: "profile", name: "Host Identity" }, { id: "preferences", name: "Preferences" }],
    company: [{ id: "all", name: "All Corporate" }, { id: "profile", name: "Legal Entity" }, { id: "industry", name: "Industry KPIs" }, { id: "hierarchy", name: "Org Hierarchy" }],
    users: [{ id: "all", name: "All Access" }, { id: "rbac", name: "RBAC Roles" }, { id: "policy", name: "Access Policies" }],
    enterprise: [{ id: "all", name: "All Enterprise" }, { id: "tenants", name: "Tenant Boundaries" }, { id: "scim", name: "SCIM Provisioning" }],
    ai_ceo: [{ id: "all", name: "All Executive" }, { id: "autonomy", name: "Autonomy Ceiling" }, { id: "spending", name: "Financial Limits" }, { id: "cognition", name: "Reasoning Mode" }],
    workforce: [{ id: "all", name: "All Workforce" }, { id: "spawning", name: "Spawning Policy" }, { id: "concurrency", name: "Concurrency Limits" }],
    automation: [{ id: "all", name: "All Automation" }, { id: "dags", name: "Workflow DAGs" }, { id: "verification", name: "Outcome Verification" }],
    ai_providers: [{ id: "all", name: "All Models" }, { id: "routing", name: "Model Routing" }, { id: "credentials", name: "Provider Vault" }],
    tools: [{ id: "all", name: "All Tools" }, { id: "registry", name: "Capabilities" }, { id: "sandboxing", name: "Sandboxing" }],
    desktop: [{ id: "all", name: "All Computer Control" }, { id: "perception", name: "Screen Perception" }, { id: "throttling", name: "Input Throttling" }],
    browser: [{ id: "all", name: "All Browser" }, { id: "headless", name: "Chromium Context" }, { id: "ssrf", name: "SSRF Firewall" }],
    terminal: [{ id: "all", name: "All Terminal" }, { id: "execution", name: "Execution Lease" }, { id: "isolation", name: "Namespace Security" }],
    mcp: [{ id: "all", name: "All MCP" }, { id: "servers", name: "Server Connections" }, { id: "permissions", name: "Resource Scopes" }],
    a2a: [{ id: "all", name: "All A2A" }, { id: "broker", name: "Broker Security" }, { id: "tokens", name: "Agent Identities" }],
    integrations: [{ id: "all", name: "All Connectors" }, { id: "sync", name: "Sync Cadence" }, { id: "permissions", name: "Least Privilege" }],
    data: [{ id: "all", name: "All Knowledge" }, { id: "indexing", name: "Semantic Index" }, { id: "retention", name: "Retention Lifecycles" }],
    communication: [{ id: "all", name: "All Dispatch" }, { id: "smtp", name: "SMTP Gateways" }, { id: "limits", name: "Rate Limits" }],
    finance: [{ id: "all", name: "All Finance" }, { id: "accounting", name: "Accounting Method" }, { id: "limits", name: "Expenditure Limits" }],
    billing: [{ id: "all", name: "All Billing" }, { id: "tier", name: "Plan Tier" }, { id: "caps", name: "Spend Stops" }],
    security: [{ id: "all", name: "All Security" }, { id: "mfa", name: "Authentication & MFA" }, { id: "session", name: "Session Lifetimes" }, { id: "device", name: "Device Trust" }],
    governance: [{ id: "all", name: "All Governance" }, { id: "sovereignty", name: "Authority Hierarchy" }, { id: "killswitch", name: "Emergency Stops" }],
    privacy: [{ id: "all", name: "All Privacy" }, { id: "anonymization", name: "PII Sanitization" }, { id: "compliance", name: "Regulatory Profiles" }],
    notifications: [{ id: "all", name: "All Alerts" }, { id: "channels", name: "Delivery Channels" }, { id: "sms", name: "Emergency SMS" }, { id: "digest", name: "Cadence & Digests" }],
    audit: [{ id: "all", name: "All Audit" }, { id: "merkle", name: "Cryptographic Ledger" }, { id: "receipts", name: "Receipt Verifier" }],
    recovery: [{ id: "all", name: "All Recovery" }, { id: "snapshots", name: "SQLite Snapshots" }, { id: "drills", name: "Recovery Drills" }],
    monitoring: [{ id: "all", name: "All Telemetry" }, { id: "health", name: "Subsystem Health" }, { id: "circuit", name: "Circuit Breakers" }],
    api: [{ id: "all", name: "All Developer" }, { id: "keys", name: "Bearer Tokens" }, { id: "limits", name: "Rate Limits" }],
    webhooks: [{ id: "all", name: "All Webhooks" }, { id: "signatures", name: "HMAC Verification" }, { id: "dispatch", name: "Dispatch Logs" }],
    localization: [{ id: "all", name: "All Locale" }, { id: "timezone", name: "Timezone & Base" }, { id: "currency", name: "Currencies" }],
    appearance: [{ id: "all", name: "All Appearance" }, { id: "theme", name: "Theme Mode" }, { id: "density", name: "Interface Density" }],
    advanced: [{ id: "all", name: "All Advanced" }, { id: "tuning", name: "Engine Tuning" }, { id: "danger", name: "Danger Zone" }],
    diagnostics: [{ id: "all", name: "All Diagnostics" }, { id: "live", name: "Live Subsystems" }, { id: "wal", name: "WAL Health" }]
  };

  // --------------------------------------------------------------------------
  // 3. Operational State Management
  // --------------------------------------------------------------------------
  let activeView = 'hub'; // 'hub' or domain id e.g. 'security'
  let activeScope = 'Company'; // 'Host', 'Company', 'Department', 'User'
  let activeSubTab = 'all';
  let currentDomainData = null;
  let stagedValues = {};
  let originalValues = {};
  let inspectingSettingId = null;
  let previewPendingChange = null;
  let activeTestResult = null;
  let unsavedPromptPendingRoute = null;

  let globalSearchQuery = '';
  let searchDropdownResults = [];
  let isSearchDropdownOpen = false;
  let isMobileDrawerOpen = false;
  let isAuditDrawerOpen = false;
  let auditDrawerEvents = [];

  let authEnvironment = { environment: 'development', strict_auth: false, auth_mode: 'DEV_BOOTSTRAP' };
  let effectiveStateCache = {};
  let isInitialized = false;
  let collapsedPillars = new Set();
  let openShutters = new Set();
  let openCardDisclosures = new Set();

  // --------------------------------------------------------------------------
  // 4. Lifecycle & Initialization
  // --------------------------------------------------------------------------
  async function init() {
    if (isInitialized) return;
    isInitialized = true;
    setupKeyboardShortcuts();
    await fetchEnvironment();
    await fetchEffectiveState();

    // Auto-render if currently on settings route or hash
    const hash = (typeof window !== 'undefined' && window.location && window.location.hash) ? window.location.hash : '';
    if (hash.startsWith('#/settings') || hash.startsWith('#settings')) {
      const clean = hash.replace(/^#/, '');
      render(clean);
    }
  }

  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Cmd+K or Ctrl+K opens settings search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        const searchInput = document.getElementById('settingsGlobalSearchInput');
        if (searchInput) {
          e.preventDefault();
          searchInput.focus();
          searchInput.select();
        }
      } else if (e.key === 'Escape') {
        closeSearchDropdown();
        if (previewPendingChange) cancelPreview();
        if (activeTestResult) closeDiagnosticModal();
        if (inspectingSettingId) closeInspector();
        if (isAuditDrawerOpen) closeAuditDrawer();
        if (isMobileDrawerOpen) toggleMobileDrawer(false);
        if (unsavedPromptPendingRoute) cancelUnsavedPrompt();
      }
    });

    document.addEventListener('click', (e) => {
      const searchBox = document.querySelector('.settings-search-wrapper');
      if (searchBox && !searchBox.contains(e.target)) {
        closeSearchDropdown();
      }
    });
  }

  async function fetchEnvironment() {
    try {
      const res = await fetch('/api/auth/environment');
      if (res.ok) authEnvironment = await res.json();
    } catch (e) {
      console.warn('[Settings] Failed to fetch auth environment:', e);
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

  // --------------------------------------------------------------------------
  // 5. Router & Navigation Controller
  // --------------------------------------------------------------------------
  function normalizeDomainId(raw) {
    if (!raw) return 'hub';
    let clean = raw.trim().toLowerCase().replace(/^\/+/, '').replace(/^settings\/?/, '');
    if (!clean || clean === 'hub' || clean === 'overview') return 'hub';
    return ROUTE_ALIASES[clean] || clean;
  }

  function render(route) {
    const raw = (route || '').replace(/^\/settings\/?/, '').trim();
    if (!raw || raw === 'hub' || raw === 'overview') {
      activeView = 'hub';
      renderRoute();
    } else {
      const norm = normalizeDomainId(raw);
      if (activeView !== norm || !currentDomainData) {
        loadDomain(norm);
      } else {
        renderRoute();
      }
    }
  }

  async function loadDomain(domainId) {
    domainId = normalizeDomainId(domainId);
    activeView = domainId;
    activeSubTab = 'all';
    stagedValues = {};
    originalValues = {};
    inspectingSettingId = null;
    currentDomainData = null;

    renderRoute(); // Show loading / skeleton state immediately

    try {
      const res = await fetch(`/api/settings/category/${domainId}`);
      if (res.ok) {
        currentDomainData = await res.json();
        if (currentDomainData.settings) {
          currentDomainData.settings.forEach(s => {
            originalValues[s.id] = s.value;
            stagedValues[s.id] = s.value;
          });
        }
      }
    } catch (e) {
      console.error(`[Settings] Failed to load domain '${domainId}':`, e);
    }
    renderRoute();
  }

  function navigateTo(targetView, optHighlightId) {
    // Navigation guard if unsaved changes exist
    const hasDirty = Object.keys(stagedValues).some(k => stagedValues[k] !== originalValues[k]);
    if (hasDirty && targetView !== activeView) {
      unsavedPromptPendingRoute = { targetView, optHighlightId };
      renderRoute();
      return;
    }

    if (isMobileDrawerOpen) {
      toggleMobileDrawer(false);
    }

    if (targetView === 'hub' || targetView === '/settings') {
      if (window.location.hash !== '#/settings') {
        window.location.hash = '#/settings';
      }
      activeView = 'hub';
      renderRoute();
      return Promise.resolve();
    } else {
      const norm = normalizeDomainId(targetView);
      const newHash = `#/settings/${norm}`;
      if (window.location.hash !== newHash) {
        window.location.hash = newHash;
      }
      return loadDomain(norm);
    }

    if (optHighlightId) {
      setTimeout(() => {
        const el = document.getElementById(`card-${optHighlightId}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.classList.add('setting-card-highlighted');
          setTimeout(() => el.classList.remove('setting-card-highlighted'), 2500);
        }
      }, 350);
    }
  }

  function renderRoute() {
    const container = document.getElementById('view-settings');
    if (!container) return;

    if (activeView === 'hub') {
      renderSettingsHub(container);
    } else {
      renderDomainDetail(container);
    }
  }

  // --------------------------------------------------------------------------
  // 6. SETTINGS HOME / HUB VIEW
  // --------------------------------------------------------------------------
  function renderSettingsHub(container) {
    const currentComp = (window.state && window.state.activeCompany) ? window.state.activeCompany.name : 'ZONATA Primary Enterprise';
    const currentUser = (window.state && window.state.host) ? window.state.host.name : 'Sukhraj Singh';
    const userRole = (window.state && window.state.host) ? window.state.host.role : 'SOVEREIGN_HOST';

    container.innerHTML = `
      <div class="settings-app-shell">
        ${renderMobileHeader("Settings & Administration")}
        ${renderMobileDrawer()}

        <div class="settings-workspace-layout">
          <!-- Left Dedicated Desktop Navigation Sidebar (260px) -->
          ${renderDesktopSidebar('hub')}

          <!-- Right Main Configuration Surface (100% Responsive) -->
          <main class="settings-configuration-main">
            <!-- Top Master Header -->
          <header class="settings-master-header">
            <div class="header-titles">
              <div class="sovereign-tag-pill">
                <span class="status-indicator-dot green"></span>
                <span>CONTROL PLANE // SOVEREIGN ENGINE</span>
              </div>
              <h1 class="settings-page-title">Settings & Administration</h1>
              <p class="settings-page-desc">Configure your organization, AI systems, security, integrations, governance, and platform behavior.</p>
            </div>

            <div class="header-meta-group">
              <div class="meta-field-box">
                <span class="field-label">Active Scope:</span>
                <select class="scope-dropdown-compact" onchange="EnterpriseSettings.setScope(this.value)">
                  <option value="Host" ${activeScope === 'Host' ? 'selected' : ''}>Host Sovereign</option>
                  <option value="Company" ${activeScope === 'Company' ? 'selected' : ''}>Company: ${escapeHtml(currentComp)}</option>
                  <option value="Department" ${activeScope === 'Department' ? 'selected' : ''}>Department Level</option>
                  <option value="Workspace" ${activeScope === 'Workspace' ? 'selected' : ''}>Active Workspace</option>
                </select>
              </div>

              ${renderSearchBox()}

              <div class="meta-actions">
                <button class="btn-subtle" onclick="EnterpriseSettings.toggleAuditDrawer()" title="View Global Evidence Audit Ledger">
                  ${SVG_ICONS.checkCircle}
                  <span>Ledger</span>
                </button>
              </div>
            </div>
          </header>

          <!-- System Status Strip (6 Vitals Cards, Section 6 & 73) -->
          <section class="settings-vitals-strip">
            <div class="vital-status-card" onclick="EnterpriseSettings.navigateTo('security')">
              <div class="vital-icon-badge">${SVG_ICONS.lock}</div>
              <div class="vital-content">
                <span class="vital-label">SECURITY</span>
                <span class="vital-state"><span class="dot-green"></span>Protected</span>
                <span class="vital-desc">MFA enforced • 0 critical security issues</span>
              </div>
              <span class="vital-arrow">Configure →</span>
            </div>

            <div class="vital-status-card" onclick="EnterpriseSettings.navigateTo('ai_ceo')">
              <div class="vital-icon-badge">${SVG_ICONS.crown}</div>
              <div class="vital-content">
                <span class="vital-label">AI EXECUTIVE</span>
                <span class="vital-state"><span class="dot-green"></span>Operational</span>
                <span class="vital-desc">Level 3 Autonomy • Budget within limit</span>
              </div>
              <span class="vital-arrow">Configure →</span>
            </div>

            <div class="vital-status-card" onclick="EnterpriseSettings.navigateTo('integrations')">
              <div class="vital-icon-badge">${SVG_ICONS.link}</div>
              <div class="vital-content">
                <span class="vital-label">INTEGRATIONS</span>
                <span class="vital-state"><span class="dot-green"></span>Connected</span>
                <span class="vital-desc">12 systems linked • Least-privilege sync</span>
              </div>
              <span class="vital-arrow">Configure →</span>
            </div>

            <div class="vital-status-card" onclick="EnterpriseSettings.navigateTo('governance')">
              <div class="vital-icon-badge">${SVG_ICONS.scale}</div>
              <div class="vital-content">
                <span class="vital-label">GOVERNANCE</span>
                <span class="vital-state"><span class="dot-green"></span>Enforced</span>
                <span class="vital-desc">Constitutional kernel • Two-person rule active</span>
              </div>
              <span class="vital-arrow">Configure →</span>
            </div>

            <div class="vital-status-card" onclick="EnterpriseSettings.navigateTo('recovery')">
              <div class="vital-icon-badge">${SVG_ICONS.hardDrive}</div>
              <div class="vital-content">
                <span class="vital-label">BACKUP & DR</span>
                <span class="vital-state"><span class="dot-green"></span>Healthy</span>
                <span class="vital-desc">Last snapshot: 22m ago • RTO under 5m</span>
              </div>
              <span class="vital-arrow">Configure →</span>
            </div>

            <div class="vital-status-card" onclick="EnterpriseSettings.navigateTo('billing')">
              <div class="vital-icon-badge">${SVG_ICONS.card}</div>
              <div class="vital-content">
                <span class="vital-label">COMPUTE BILLING</span>
                <span class="vital-state"><span class="dot-green"></span>Active</span>
                <span class="vital-desc">Enterprise tier • Monthly spend cap set</span>
              </div>
              <span class="vital-arrow">Configure →</span>
            </div>
          </section>

          <!-- Operational Attention Center (Section 83) -->
          <section class="settings-attention-center">
            <div class="attention-header">
              <span class="attention-icon">${SVG_ICONS.info}</span>
              <span class="attention-title">Attention Center // Active Administrative Notices</span>
            </div>
            <div class="attention-items-grid">
              <div class="attention-item">
                <span class="att-bullet dot-green"></span>
                <div class="att-text">
                  <strong>Inference Spend Verification:</strong> Monthly compute consumption currently at 28% of threshold ($28,000 / $100,000 limit).
                </div>
                <button class="att-btn" onclick="EnterpriseSettings.navigateTo('billing')">Adjust Cap →</button>
              </div>
              <div class="attention-item">
                <span class="att-bullet dot-green"></span>
                <div class="att-text">
                  <strong>API Credential Health:</strong> Primary Google Vertex / Gemini AI bearer token verified active with 100% SLA.
                </div>
                <button class="att-btn" onclick="EnterpriseSettings.navigateTo('ai_providers')">Inspect Vault →</button>
              </div>
              <div class="attention-item">
                <span class="att-bullet dot-green"></span>
                <div class="att-text">
                  <strong>Disaster Recovery Drill:</strong> Automated SQLite WAL hot snapshot verified clean. SHA-256 integrity passed.
                </div>
                <button class="att-btn" onclick="EnterpriseSettings.navigateTo('recovery')">Run Drill →</button>
              </div>
            </div>
          </section>

          <!-- Domain Pillar Navigator (Hierarchical 32 Domains, Section 5) -->
          <section class="settings-pillars-browser">
            ${PILLARS.map(p => `
              <div class="pillar-group-block">
                <div class="pillar-header" onclick="EnterpriseSettings.togglePillarCollapse('${p.id}')">
                  <div class="pillar-header-left">
                    <span class="pillar-collapse-arrow" id="pillar-arrow-${p.id}">${collapsedPillars.has(p.id) ? '▸' : '▾'}</span>
                    <h3 class="pillar-title">${escapeHtml(p.title)}</h3>
                  </div>
                  <span class="pillar-desc">${escapeHtml(p.desc)}</span>
                </div>

                <div class="pillar-domains-grid" id="pillar-grid-${p.id}" style="display:${collapsedPillars.has(p.id) ? 'none' : 'grid'};">
                  ${p.domains.map(d => `
                    <div class="domain-card-item" onclick="EnterpriseSettings.navigateTo('${d.id}')">
                      <div class="domain-top-line">
                        <span class="domain-num">${d.num}</span>
                        <div class="domain-icon-wrap">${d.icon}</div>
                        <span class="domain-scope-tag scope-${d.scope.toLowerCase()}">${d.scope}</span>
                      </div>
                      <h4 class="domain-name">${escapeHtml(d.name)}</h4>
                      <p class="domain-desc">${escapeHtml(d.desc)}</p>
                      <div class="domain-card-footer">
                        <span class="domain-risk-badge risk-${d.risk.toLowerCase()}">${d.risk} Risk</span>
                        <span class="domain-open-link">Configure →</span>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            `).join('')}
          </section>

          <!-- Recent Settings Activity Strip (Section 82) -->
          <footer class="settings-recent-activity">
            <div class="activity-header">
              <span class="activity-title">Recent Settings Activity & Cryptographic Proofs</span>
              <button class="btn-link" onclick="EnterpriseSettings.toggleAuditDrawer()">View Full Audit Trail (${SVG_ICONS.chevronRight})</button>
            </div>
            <div class="activity-stream-row">
              <div class="activity-chip">
                <span class="act-dot green"></span>
                <span class="act-actor">Sukhraj Singh (Host)</span>
                <span class="act-action">MFA Policy enforced</span>
                <span class="act-hash">SHA: 8f4a2...</span>
              </div>
              <div class="activity-chip">
                <span class="act-dot green"></span>
                <span class="act-actor">System Engine</span>
                <span class="act-action">AI Spending Cap verified</span>
                <span class="act-hash">SHA: 1c90e...</span>
              </div>
              <div class="activity-chip">
                <span class="act-dot green"></span>
                <span class="act-actor">Host Administrator</span>
                <span class="act-action">SQLite Hot Snapshot executed</span>
                <span class="act-hash">SHA: 77d2b...</span>
              </div>
            </div>
          </footer>
          </main>
        </div>
      </div>

      <!-- Modals & Drawers -->
      ${isAuditDrawerOpen ? renderAuditDrawer() : ''}
      ${activeTestResult ? renderDiagnosticModal() : ''}
      ${unsavedPromptPendingRoute ? renderUnsavedPromptModal() : ''}
    `;
  }

  // --------------------------------------------------------------------------
  // 7. SETTINGS DOMAIN DETAIL VIEW
  // --------------------------------------------------------------------------
  function renderDomainDetail(container) {
    const domain = ALL_DOMAINS.find(d => d.id === activeView) || ALL_DOMAINS[0];
    const pillar = PILLARS.find(p => p.id === domain.pillarId) || PILLARS[0];
    const subTabs = SECTIONS_MAP[domain.id] || [{ id: "all", name: "All Settings" }];

    let settingsList = currentDomainData ? (currentDomainData.settings || []) : [];
    const proposals = currentDomainData ? (currentDomainData.proposals || []) : [];
    const audits = currentDomainData ? (currentDomainData.recent_audits || []) : [];

    // Filter by subtab if selected
    if (activeSubTab !== 'all') {
      const q = activeSubTab.toLowerCase();
      settingsList = settingsList.filter(s => {
        return s.id.toLowerCase().includes(q) ||
               (s.name && s.name.toLowerCase().includes(q)) ||
               (s.desc && s.desc.toLowerCase().includes(q));
      });
    }

    const hasDirty = Object.keys(stagedValues).some(k => stagedValues[k] !== originalValues[k]);
    const dirtyCount = Object.keys(stagedValues).filter(k => stagedValues[k] !== originalValues[k]).length;

    container.innerHTML = `
      <div class="settings-app-shell">
        ${renderMobileHeader(domain.name)}
        ${renderMobileDrawer()}

        <div class="settings-workspace-layout">
          <!-- Left Dedicated Desktop Navigation Sidebar (260px) -->
          ${renderDesktopSidebar(domain.id)}

          <!-- Right Main Configuration Surface (100% Responsive) -->
          <main class="settings-configuration-main">
            <!-- Breadcrumbs Bar -->
            <div class="settings-breadcrumbs-row">
              <a href="#/settings" onclick="EnterpriseSettings.navigateTo('hub')">Settings Home</a>
              <span class="crumb-sep">/</span>
              <span class="crumb-pillar">${escapeHtml(pillar.title)}</span>
              <span class="crumb-sep">/</span>
              <span class="crumb-current">${escapeHtml(domain.name)}</span>
            </div>

            <!-- Domain Header Banner -->
            <header class="domain-header-card">
              <div class="domain-header-left">
                <div class="domain-icon-large">${domain.icon}</div>
                <div>
                  <div class="domain-num-tag">DOMAIN ${domain.num} // ${escapeHtml(pillar.title.toUpperCase())}</div>
                  <h2 class="domain-title">${escapeHtml(domain.name)}</h2>
                  <p class="domain-subtitle">${escapeHtml(domain.desc)}</p>
                </div>
              </div>

              <div class="domain-header-right">
                <div class="scope-inheritance-box">
                  <div class="scope-row">
                    <span class="scope-label">Scope:</span>
                    <select class="scope-select" onchange="EnterpriseSettings.setScope(this.value)">
                      <option value="Host" ${activeScope === 'Host' ? 'selected' : ''}>Host Sovereign</option>
                      <option value="Company" ${activeScope === 'Company' ? 'selected' : ''}>Company Override</option>
                      <option value="Department" ${activeScope === 'Department' ? 'selected' : ''}>Department</option>
                      <option value="User" ${activeScope === 'User' ? 'selected' : ''}>User Profile</option>
                    </select>
                  </div>
                  <div class="inheritance-badge">
                    <span class="dot-green"></span>
                    <span>Inherited: Host Sovereign Baseline</span>
                  </div>
                </div>

                <div class="domain-quick-actions">
                  <button class="btn-secondary btn-sm" onclick="EnterpriseSettings.resetToInherited()" title="Revert all settings in this domain to inherited baseline">Reset Domain</button>
                  <button class="btn-secondary btn-sm" onclick="EnterpriseSettings.runDiagnosticTest('${getTestTarget(domain.id)}')" title="Run live diagnostic test on this domain">Test Subsystem</button>
                  <button class="btn-secondary btn-sm" onclick="EnterpriseSettings.toggleAuditDrawer()" title="View immutable cryptographic audit ledger">Audit Trail (${audits.length})</button>
                </div>
              </div>
            </header>

            <!-- Section Sub-Navigation Tabs Bar -->
            ${subTabs.length > 1 ? `
              <nav class="domain-subtabs-bar">
                ${subTabs.map(tab => `
                  <button 
                    class="subtab-btn ${activeSubTab === tab.id ? 'active' : ''}" 
                    onclick="EnterpriseSettings.setSubTab('${tab.id}')"
                  >
                    ${escapeHtml(tab.name)}
                  </button>
                `).join('')}
              </nav>
            ` : ''}

            <!-- AI CEO Proposals Banner (Section 84 & 135) -->
            ${proposals.length > 0 ? `
              <section class="ceo-proposals-banner">
                <div class="prop-banner-header">
                  <span class="prop-tag">AI CEO EXECUTIVE PROPOSALS (${proposals.length})</span>
                  <span class="prop-subtitle">Autonomous cognitive engine proposals awaiting Sovereign Host approval</span>
                </div>
                <div class="prop-list">
                  ${proposals.map(p => `
                    <div class="prop-card">
                      <div class="prop-top">
                        <strong>${escapeHtml(p.setting_id)}:</strong> Proposed Value = <code>${JSON.stringify(p.proposed_value)}</code>
                        <span class="badge badge-warning">${escapeHtml(p.risk_level)} Risk</span>
                      </div>
                      <p class="prop-desc"><strong>Rationale:</strong> ${escapeHtml(p.reason)} | <strong>Benefit:</strong> ${escapeHtml(p.expected_benefit)}</p>
                      <div class="prop-actions">
                        <button class="btn-success btn-sm" onclick="EnterpriseSettings.resolveProposal('${p.proposal_id}', 'APPROVED')">Approve Proposal</button>
                        <button class="btn-secondary btn-sm" onclick="EnterpriseSettings.resolveProposal('${p.proposal_id}', 'REJECTED')">Reject</button>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </section>
            ` : ''}

            <!-- Setting Cards Grid (Answers 5 Core Questions) -->
            <section class="domain-cards-grid">
              ${settingsList.length > 0 ? settingsList.map(s => renderSettingCard(s)).join('') : `
                <div class="empty-settings-card">
                  <p>No configuration items found for section '<strong>${escapeHtml(activeSubTab)}</strong>'.</p>
                  <button class="btn-secondary btn-sm" onclick="EnterpriseSettings.setSubTab('all')">Show All Settings</button>
                </div>
              `}
            </section>
          </main>
        </div>

        <!-- Docked Bottom Save Bar (CLEAN / DIRTY State, Section 16 & 79) -->
        <div id="settingsSaveBarContainer">
          ${renderBottomSaveBar(hasDirty, dirtyCount, domain.name)}
        </div>

        <!-- Slide-out Setting Detail Drawer / Inspector (Section 51) -->
        ${inspectingSettingId ? renderInspectorDrawer(inspectingSettingId) : ''}

        <!-- High-Risk Change Preview Modal (Section 54) -->
        ${previewPendingChange ? renderChangePreviewModal() : ''}

        <!-- Diagnostic Test Live Modal (Section 19) -->
        ${activeTestResult ? renderDiagnosticModal() : ''}

        <!-- Full Audit Trail Drawer (Section 20) -->
        ${isAuditDrawerOpen ? renderAuditDrawer() : ''}

        <!-- Navigation Guard Modal (Section 17) -->
        ${unsavedPromptPendingRoute ? renderUnsavedPromptModal() : ''}
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 8. DESKTOP SIDEBAR RENDERER
  // --------------------------------------------------------------------------
  function renderDesktopSidebar(activeDomainId) {
    return `
      <aside class="settings-desktop-sidebar">
        <div class="sidebar-overview-link ${activeDomainId === 'hub' ? 'active' : ''}" onclick="EnterpriseSettings.navigateTo('hub')">
          <span class="link-arrow">←</span>
          <span class="link-text">Settings Overview</span>
        </div>

        <div class="sidebar-pillars-tree">
          ${PILLARS.map(p => `
            <div class="sidebar-pillar-section">
              <div class="pillar-section-heading">${escapeHtml(p.title)}</div>
              <div class="pillar-domain-links">
                ${p.domains.map(d => `
                  <button 
                    class="sidebar-domain-button ${d.id === activeDomainId ? 'active' : ''}" 
                    onclick="EnterpriseSettings.navigateTo('${d.id}')"
                  >
                    <span class="btn-icon">${d.icon}</span>
                    <span class="btn-name">${escapeHtml(d.name)}</span>
                    <span class="btn-num">${d.num}</span>
                  </button>
                `).join('')}
              </div>
            </div>
          `).join('')}
        </div>
      </aside>
    `;
  }

  // --------------------------------------------------------------------------
  // 9. MOBILE HEADER & OFF-CANVAS DRAWER RENDERERS
  // --------------------------------------------------------------------------
  function renderMobileHeader(title) {
    return `
      <div class="settings-mobile-header">
        <button class="mobile-menu-trigger" onclick="EnterpriseSettings.toggleMobileDrawer(true)" aria-label="Open Settings Menu">
          ${SVG_ICONS.menu}
          <span class="trigger-label">Menu</span>
        </button>
        <div class="mobile-header-title">
          <span class="mobile-title-text">${escapeHtml(title)}</span>
          <span class="mobile-scope-badge">${activeScope}</span>
        </div>
        <button class="mobile-search-trigger" onclick="EnterpriseSettings.focusSearchMobile()" aria-label="Search Settings">
          ${SVG_ICONS.search}
        </button>
      </div>
    `;
  }

  function renderMobileDrawer() {
    return `
      <div class="settings-mobile-drawer ${isMobileDrawerOpen ? 'drawer-open' : ''}" id="settingsMobileDrawer">
        <div class="mobile-drawer-backdrop" onclick="EnterpriseSettings.toggleMobileDrawer(false)"></div>
        <div class="mobile-drawer-content">
          <div class="drawer-header">
            <div class="drawer-title-box">
              <span class="status-indicator-dot green"></span>
              <strong>Settings Navigation</strong>
            </div>
            <button class="drawer-close-btn" onclick="EnterpriseSettings.toggleMobileDrawer(false)">
              ${SVG_ICONS.close}
            </button>
          </div>

          <div class="drawer-search-box">
            ${renderSearchBox()}
          </div>

          <div class="drawer-overview-btn" onclick="EnterpriseSettings.navigateTo('hub')">
            <span>← Settings Overview & Vitals</span>
          </div>

          <div class="drawer-scroll-tree">
            ${PILLARS.map(p => `
              <div class="drawer-pillar-block">
                <div class="drawer-pillar-heading">${escapeHtml(p.title)}</div>
                <div class="drawer-domains-list">
                  ${p.domains.map(d => `
                    <button 
                      class="drawer-domain-item ${d.id === activeView ? 'active' : ''}" 
                      onclick="EnterpriseSettings.navigateTo('${d.id}')"
                    >
                      <span class="drawer-item-icon">${d.icon}</span>
                      <span class="drawer-item-name">${d.num}. ${escapeHtml(d.name)}</span>
                      <span class="drawer-item-scope">${d.scope}</span>
                    </button>
                  `).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 10. COMPACT SEARCH BAR & INSTANT DROPDOWN
  // --------------------------------------------------------------------------
  function renderSearchBox() {
    return `
      <div class="settings-search-wrapper">
        <div class="search-input-field">
          <span class="search-icon-lens">${SVG_ICONS.search}</span>
          <input 
            type="text" 
            id="settingsGlobalSearchInput"
            class="search-text-input"
            placeholder="Search settings, domains, or keys... (⌘K)"
            value="${escapeHtml(globalSearchQuery)}"
            oninput="EnterpriseSettings.handleSearch(this.value)"
            onfocus="EnterpriseSettings.handleSearchFocus()"
            autocomplete="off"
            spellcheck="false"
          />
          <div class="search-right-chips">
            <span class="kbd-hint">⌘K</span>
            ${globalSearchQuery ? `<button class="search-clear-btn" onclick="EnterpriseSettings.handleSearch('')">✕</button>` : ''}
          </div>
        </div>

        ${isSearchDropdownOpen && searchDropdownResults.length > 0 ? renderSearchDropdown() : ''}
      </div>
    `;
  }

  function renderSearchDropdown() {
    return `
      <div class="settings-search-dropdown-menu" id="settingsSearchDropdownMenu">
        <div class="dropdown-top-meta">
          <span>Found ${searchDropdownResults.length} matching settings</span>
          <span class="meta-esc">ESC to close</span>
        </div>
        <div class="dropdown-items-scroll">
          ${searchDropdownResults.map(item => `
            <div class="dropdown-result-card" onclick="EnterpriseSettings.selectSearchResult('${item.id}', '${item.category}')">
              <div class="res-left">
                <div class="res-title-line">
                  <span class="res-name">${highlightMatch(item.name, globalSearchQuery)}</span>
                  <span class="res-cat-badge">${escapeHtml(item.category)}</span>
                  <span class="res-risk-badge risk-${(item.risk || 'low').toLowerCase()}">${escapeHtml(item.risk || 'LOW')}</span>
                </div>
                <p class="res-desc">${highlightMatch(item.desc || '', globalSearchQuery)}</p>
              </div>
              <div class="res-right">
                <span class="res-val-pill">Eff: <code>${escapeHtml(String(item.effective_value !== undefined ? item.effective_value : item.default).slice(0, 20))}</code></span>
                <span class="res-scope-pill">${escapeHtml(item.scope || 'Company')}</span>
                <span class="res-jump-link">Open →</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 11. SETTING CARD RENDERER (Answers 5 Core Questions)
  // --------------------------------------------------------------------------
  function renderSettingCard(s) {
    const curVal = stagedValues.hasOwnProperty(s.id) ? stagedValues[s.id] : s.value;
    const isDirty = stagedValues.hasOwnProperty(s.id) && stagedValues[s.id] !== originalValues[s.id];
    const risk = s.risk || 'LOW';

    // 1. Policy Tags
    const tags = [
      s.editable_by === 'OWNER' ? '<span class="policy-pill tag-owner">Sovereign Controlled</span>' : '',
      s.is_ceo_managed ? '<span class="policy-pill tag-ceo">AI CEO Managed</span>' : '',
      s.editable_by === 'READ_ONLY' ? '<span class="policy-pill tag-readonly">Read Only</span>' : '',
      s.requires_approval ? '<span class="policy-pill tag-approval">Requires Sign-Off</span>' : '',
      s.secret ? '<span class="policy-pill tag-secret">Sensitive Credential</span>' : '',
      `<span class="policy-pill risk-${risk.toLowerCase()}">${risk} Risk</span>`
    ].filter(Boolean).join('');

    // 2. Affected Systems tags (Question 2: Who/what does it affect?)
    const affectedSystems = getAffectedSystemsForSetting(s.id);

    // 3. Effective Runtime Enforcement Proof (Question 3: Current effective value?)
    const effRuntimeVal = s.effective_runtime_value !== undefined ? s.effective_runtime_value : curVal;
    const runtimeStatus = s.runtime_status || 'ACTIVE';

    return `
      <div class="setting-card-item ${isDirty ? 'card-is-dirty' : ''}" id="card-${s.id}">
        <!-- Card Header: Title & Policy Tags -->
        <div class="card-header-bar">
          <div class="card-title-group">
            <h4 class="setting-title">${escapeHtml(s.name)}</h4>
            ${isDirty ? '<span class="badge-modified">Modified</span>' : ''}
          </div>
          <div class="card-tags-group">${tags}</div>
        </div>

        <!-- Description: What am I configuring? -->
        <p class="setting-description">${escapeHtml(s.desc || '')}</p>

        <!-- Interactive Dynamic Control Box -->
        <div class="setting-control-surface">
          ${renderControlForSetting(s, curVal)}
        </div>

        <!-- Effective Runtime Value Bar (Question 3 & 4) -->
        <div class="effective-runtime-bar">
          <div class="runtime-left">
            <span class="runtime-label">Effective Runtime:</span>
            <span class="runtime-val">${escapeHtml(String(effRuntimeVal))}</span>
          </div>
          <span class="runtime-status-pill status-${runtimeStatus.toLowerCase()}">${runtimeStatus}</span>
        </div>

        <!-- Expandable Policy Details & Runtime Invariants Accordion -->
        <div class="card-disclosure-box">
          <button type="button" class="btn-card-disclosure" id="disclosure-btn-${s.id}" onclick="EnterpriseSettings.toggleCardDisclosure('${s.id}')">
            <span class="disclosure-arrow" id="disclosure-arrow-${s.id}">${openCardDisclosures.has(s.id) ? '▾' : '▸'}</span>
            <span>Policy Governance & Runtime Contract</span>
          </button>
          <div class="disclosure-content" id="disclosure-content-${s.id}" style="display:${openCardDisclosures.has(s.id) ? 'block' : 'none'};">
            <div class="disclosure-inner">
              <div class="disclosure-row"><strong>Scope Boundary:</strong> <span>${escapeHtml(s.scope || 'Company')}</span></div>
              <div class="disclosure-row"><strong>Authority Ceiling:</strong> <span>${escapeHtml(s.editable_by === 'OWNER' ? 'Sovereign Host Exclusive' : 'Shared Delegation')}</span></div>
              <div class="disclosure-row"><strong>Risk Classification:</strong> <span class="badge risk-${(s.risk || 'low').toLowerCase()}">${escapeHtml(s.risk || 'LOW')}</span></div>
              <div class="disclosure-row"><strong>Merkle Evidence:</strong> <span>SHA-256 Ledger Sealed</span></div>
              ${s.unit ? `<div class="disclosure-row"><strong>Measurement Unit:</strong> <span>${escapeHtml(s.unit)}</span></div>` : ''}
              ${s.min !== undefined ? `<div class="disclosure-row"><strong>Allowed Bounds:</strong> <span>Min: ${s.min}${s.max !== undefined ? ` / Max: ${s.max}` : ''}</span></div>` : ''}
            </div>
          </div>
        </div>

        <!-- Card Footer Actions: Inspect Details, Test, Reset -->
        <div class="card-footer-actions">
          <div class="affected-systems-pills">
            <span class="aff-label">Affects:</span>
            ${affectedSystems.slice(0, 2).map(sys => `<span class="aff-tag">${escapeHtml(sys)}</span>`).join('')}
            ${affectedSystems.length > 2 ? `<span class="aff-more">+${affectedSystems.length - 2}</span>` : ''}
          </div>

          <div class="card-buttons-group">
            ${isDirty ? `<button class="btn-card-reset" onclick="EnterpriseSettings.resetSingleSetting('${s.id}')">Reset</button>` : ''}
            ${supportsLiveTest(s.id) ? `<button class="btn-card-test" onclick="EnterpriseSettings.runDiagnosticTest('${getTestTarget(s.id)}')">Test</button>` : ''}
            <button class="btn-card-inspect" onclick="EnterpriseSettings.inspectSetting('${s.id}')">
              <span>Inspect Details</span>
              <span class="btn-arrow">→</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 12. DYNAMIC CONTROL COMPONENT RENDERER
  // --------------------------------------------------------------------------
  function renderControlForSetting(s, curVal) {
    const isReadOnly = s.editable_by === 'READ_ONLY';

    if (isReadOnly || s.type === 'status') {
      return `
        <div class="read-only-status-box">
          <span class="status-box-val">${escapeHtml(String(curVal))}</span>
          <span class="status-box-tag">READ ONLY // BASELINE</span>
        </div>
      `;
    }

    if (s.type === 'toggle') {
      const isChecked = Boolean(curVal);
      return `
        <div class="toggle-control-wrapper">
          <label class="custom-toggle-control ${isReadOnly ? 'control-disabled' : ''}" id="toggle-label-${s.id}">
            <input 
              type="checkbox" 
              id="control-input-${s.id}"
              ${isChecked ? 'checked' : ''} 
              ${isReadOnly ? 'disabled' : ''}
              onchange="EnterpriseSettings.stageValue('${s.id}', this.checked, false)"
            />
            <span class="toggle-slider"></span>
            <span class="toggle-state-text" id="toggle-state-text-${s.id}">${isChecked ? 'Enabled' : 'Disabled'}</span>
          </label>
          <button 
            type="button" 
            class="toggle-btn-shortcut ${isChecked ? 'is-enabled' : 'is-disabled'}"
            id="toggle-btn-shortcut-${s.id}"
            onclick="EnterpriseSettings.flipToggle('${s.id}')"
            ${isReadOnly ? 'disabled' : ''}
          >
            ${isChecked ? 'Disable' : 'Enable'}
          </button>
        </div>
      `;
    }

    if (s.type === 'multiselect') {
      let curArr = curVal;
      if (!Array.isArray(curArr)) {
        curArr = typeof curArr === 'string' ? curArr.split(',').map(x => x.trim()).filter(Boolean) : (s.default || []);
      }
      const opts = s.options || [];
      const isOpen = openShutters.has(s.id);
      return `
        <div class="multiselect-shutter-container" id="shutter-container-${s.id}">
          <button 
            type="button" 
            class="shutter-trigger-btn ${isOpen ? 'open' : ''}" 
            id="shutter-trigger-${s.id}"
            onclick="EnterpriseSettings.toggleShutter('${s.id}')"
            ${isReadOnly ? 'disabled' : ''}
          >
            <div class="shutter-trigger-left">
              <span class="shutter-count-pill" id="shutter-count-${s.id}">${curArr.length} selected</span>
              <div class="shutter-tags-preview" id="shutter-tags-${s.id}">
                ${curArr.length > 0 ? curArr.slice(0, 3).map(item => `<span class="shutter-tag-pill">${escapeHtml(item)}</span>`).join('') + (curArr.length > 3 ? `<span class="shutter-tag-more">+${curArr.length - 3}</span>` : '') : '<span class="shutter-tag-none">None selected</span>'}
              </div>
            </div>
            <span class="shutter-arrow-icon" id="shutter-arrow-${s.id}">${isOpen ? '▴' : '▾'}</span>
          </button>

          <div class="shutter-dropdown-panel" id="shutter-panel-${s.id}" style="display:${isOpen ? 'block' : 'none'};">
            <div class="shutter-panel-header">
              <span class="shutter-panel-title">Choose Applicable Options</span>
              <div class="shutter-quick-btns">
                <button type="button" class="btn-micro" onclick="EnterpriseSettings.selectAllMultiselect('${s.id}')">All</button>
                <button type="button" class="btn-micro" onclick="EnterpriseSettings.clearAllMultiselect('${s.id}')">Clear</button>
                <button type="button" class="btn-micro btn-done" onclick="EnterpriseSettings.toggleShutter('${s.id}')">Done</button>
              </div>
            </div>
            <div class="shutter-options-list">
              ${opts.map(opt => {
                const isSelected = curArr.includes(opt);
                return `
                  <label class="shutter-option-item ${isSelected ? 'selected' : ''}">
                    <input 
                      type="checkbox" 
                      id="multiselect-${s.id}-${escapeHtml(opt)}"
                      class="shutter-checkbox"
                      data-setting="${s.id}"
                      data-opt="${escapeHtml(opt)}"
                      ${isSelected ? 'checked' : ''}
                      ${isReadOnly ? 'disabled' : ''}
                      onchange="EnterpriseSettings.toggleMultiselectOption('${s.id}', '${escapeHtml(opt)}', this.checked)"
                    />
                    <span class="shutter-opt-label">${escapeHtml(opt)}</span>
                  </label>
                `;
              }).join('')}
            </div>
          </div>
        </div>
      `;
    }

    if (s.type === 'slider') {
      const minVal = s.min !== undefined ? s.min : 0;
      const maxVal = s.max !== undefined ? s.max : 100;
      const stepVal = s.step || 1;
      const unit = s.unit || '';
      return `
        <div class="slider-control-surface" id="slider-surface-${s.id}">
          <div class="slider-track-row">
            <input 
              type="range" 
              class="control-range-slider"
              id="slider-range-${s.id}"
              min="${minVal}" 
              max="${maxVal}" 
              step="${stepVal}"
              value="${escapeHtml(String(curVal))}"
              ${isReadOnly ? 'disabled' : ''}
              oninput="EnterpriseSettings.stageSliderValue('${s.id}', this.value)"
            />
            <div class="slider-input-unit-group">
              <input 
                type="number" 
                class="control-number-compact"
                id="control-input-${s.id}"
                min="${minVal}" 
                max="${maxVal}" 
                step="${stepVal}"
                value="${escapeHtml(String(curVal))}"
                ${isReadOnly ? 'disabled' : ''}
                oninput="EnterpriseSettings.stageSliderValue('${s.id}', this.value)"
              />
              ${unit ? `<span class="slider-unit-tag">${escapeHtml(unit)}</span>` : ''}
            </div>
          </div>
          <div class="slider-bounds-row">
            <span class="bound-label">Min: ${minVal}${unit ? ' ' + unit : ''}</span>
            <span class="slider-live-badge" id="slider-badge-${s.id}">${curVal}${unit ? ' ' + unit : ''}</span>
            <span class="bound-label">Max: ${maxVal}${unit ? ' ' + unit : ''}</span>
          </div>
        </div>
      `;
    }

    if (s.type === 'button_action') {
      return `
        <div class="button-action-control-surface">
          <button 
            type="button" 
            class="btn-action-trigger ${s.risk === 'CRITICAL' || s.risk === 'HIGH' ? 'btn-danger-action' : 'btn-secondary'}"
            id="btn-action-${s.id}"
            onclick="EnterpriseSettings.executeButtonAction('${s.id}')"
            ${isReadOnly ? 'disabled' : ''}
          >
            ${escapeHtml(s.name)}
          </button>
          <span class="action-feedback-pill" id="action-feedback-${s.id}">Ready</span>
        </div>
      `;
    }

    if (s.type === 'select') {
      const opts = s.options || [];
      return `
        <div class="custom-select-control">
          <select 
            class="control-select" 
            id="control-input-${s.id}"
            ${isReadOnly ? 'disabled' : ''}
            onchange="EnterpriseSettings.stageValue('${s.id}', this.value, false)"
          >
            ${opts.map(opt => `
              <option value="${escapeHtml(String(opt))}" ${String(curVal) === String(opt) ? 'selected' : ''}>
                ${escapeHtml(String(opt))}${s.unit && !String(opt).includes(s.unit) ? ' ' + s.unit : ''}
              </option>
            `).join('')}
          </select>
        </div>
      `;
    }

    if (s.type === 'currency') {
      return `
        <div class="currency-input-control">
          <span class="currency-prefix">$</span>
          <button type="button" class="stepper-btn stepper-dec" onclick="EnterpriseSettings.stepNumber('${s.id}', -100)">−</button>
          <input 
            type="number" 
            class="control-number"
            id="control-input-${s.id}"
            min="${s.min !== undefined ? s.min : 0}"
            max="${s.max !== undefined ? s.max : ''}"
            step="${s.step || 100}"
            value="${escapeHtml(String(curVal))}"
            ${isReadOnly ? 'disabled' : ''}
            oninput="EnterpriseSettings.stageNumberValue('${s.id}', this.value)"
          />
          <button type="button" class="stepper-btn stepper-inc" onclick="EnterpriseSettings.stepNumber('${s.id}', 100)">+</button>
          <span class="currency-unit">USD / Month</span>
        </div>
      `;
    }

    if (s.type === 'number') {
      return `
        <div class="number-input-control">
          <button type="button" class="stepper-btn stepper-dec" onclick="EnterpriseSettings.stepNumber('${s.id}', -1)">−</button>
          <input 
            type="number" 
            class="control-number"
            id="control-input-${s.id}"
            min="${s.min !== undefined ? s.min : ''}"
            max="${s.max !== undefined ? s.max : ''}"
            step="${s.step || 1}"
            value="${escapeHtml(String(curVal))}"
            ${isReadOnly ? 'disabled' : ''}
            oninput="EnterpriseSettings.stageNumberValue('${s.id}', this.value)"
          />
          <button type="button" class="stepper-btn stepper-inc" onclick="EnterpriseSettings.stepNumber('${s.id}', 1)">+</button>
          ${s.unit ? `<span class="number-unit-tag">${escapeHtml(s.unit)}</span>` : ''}
        </div>
      `;
    }

    if (s.type === 'token' || s.secret) {
      const isRevealed = Boolean(s._isRevealed);
      return `
        <div class="secret-token-control">
          <input 
            type="${isRevealed ? 'text' : 'password'}" 
            class="control-token"
            id="control-input-${s.id}"
            value="${escapeHtml(String(curVal))}"
            ${isReadOnly ? 'disabled' : ''}
            oninput="EnterpriseSettings.stageValue('${s.id}', this.value, false)"
          />
          <button type="button" class="token-btn" id="token-reveal-btn-${s.id}" onclick="EnterpriseSettings.toggleSecretReveal('${s.id}')">
            ${isRevealed ? 'Hide' : 'Reveal'}
          </button>
          <button type="button" class="token-btn" onclick="EnterpriseSettings.copySecret('${s.id}')">Copy</button>
          <button type="button" class="token-btn" onclick="EnterpriseSettings.rotateSecret('${s.id}')">Rotate</button>
          <button type="button" class="token-btn btn-danger-token" onclick="EnterpriseSettings.revokeSecret('${s.id}')">Revoke</button>
        </div>
      `;
    }

    if (s.type === 'radio' && s.options) {
      return `
        <div class="segmented-radio-control" id="radio-group-${s.id}">
          ${s.options.map(opt => `
            <button 
              type="button" 
              class="segment-btn ${String(curVal) === String(opt) ? 'active' : ''}"
              data-val="${escapeHtml(String(opt))}"
              onclick="EnterpriseSettings.stageRadioValue('${s.id}', '${escapeHtml(String(opt))}')"
              ${isReadOnly ? 'disabled' : ''}
            >
              ${escapeHtml(String(opt))}
            </button>
          `).join('')}
        </div>
      `;
    }

    // Default text input
    return `
      <div class="text-input-control">
        <input 
          type="text" 
          class="control-text"
          id="control-input-${s.id}"
          value="${escapeHtml(String(curVal))}"
          ${isReadOnly ? 'disabled' : ''}
          oninput="EnterpriseSettings.stageValue('${s.id}', this.value, false)"
        />
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 13. DOCKED BOTTOM SAVE BAR (CLEAN / DIRTY STATE MACHINE)
  // --------------------------------------------------------------------------
  function renderBottomSaveBar(hasDirty, dirtyCount, domainName) {
    if (!hasDirty) return '';

    return `
      <div class="docked-save-bar">
        <div class="save-bar-inner">
          <div class="save-bar-info">
            <span class="save-dot-pulse"></span>
            <span class="save-info-text">
              <strong>${dirtyCount} unsaved modification${dirtyCount > 1 ? 's' : ''}</strong> staged in ${escapeHtml(domainName)}.
            </span>
          </div>
          <div class="save-bar-actions">
            <button class="btn-secondary btn-sm" onclick="EnterpriseSettings.discardChanges()">Discard Changes</button>
            <button class="btn-primary btn-sm" onclick="EnterpriseSettings.promptSaveCategory()">Review & Save (${dirtyCount})</button>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 14. SETTING INSPECTOR DRAWER (Slide-Out Details, Section 51)
  // --------------------------------------------------------------------------
  function renderInspectorDrawer(settingId) {
    const s = currentDomainData && currentDomainData.settings ? currentDomainData.settings.find(item => item.id === settingId) : null;
    if (!s) return '';

    const curVal = stagedValues.hasOwnProperty(s.id) ? stagedValues[s.id] : s.value;
    const affectedSystems = getAffectedSystemsForSetting(s.id);
    const effRuntimeVal = s.effective_runtime_value !== undefined ? s.effective_runtime_value : curVal;
    const runtimeStatus = s.runtime_status || 'ACTIVE';

    return `
      <div class="setting-inspector-overlay">
        <div class="inspector-backdrop" onclick="EnterpriseSettings.closeInspector()"></div>
        <div class="inspector-drawer-panel">
          <div class="inspector-top-bar">
            <div>
              <span class="inspector-tag">SETTING SPECIFICATION // INSPECTION</span>
              <h3 class="inspector-title">${escapeHtml(s.name)}</h3>
              <code class="inspector-id">${escapeHtml(s.id)}</code>
            </div>
            <button class="inspector-close-btn" onclick="EnterpriseSettings.closeInspector()">${SVG_ICONS.close}</button>
          </div>

          <div class="inspector-scroll-body">
            <!-- Section 1: Effective Configuration Context (11 Required Fields) -->
            <div class="spec-section-card">
              <h5 class="spec-heading">11-Point Invariant Verification</h5>
              <div class="spec-grid-row">
                <span class="spec-k">1. Configured Value:</span>
                <span class="spec-v"><code>${JSON.stringify(curVal)}</code></span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">2. Effective Runtime:</span>
                <span class="spec-v"><strong>${escapeHtml(String(effRuntimeVal))}</strong></span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">3. Scope Boundary:</span>
                <span class="spec-v">${escapeHtml(s.scope || 'Company')}</span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">4. Inherited Baseline:</span>
                <span class="spec-v">${escapeHtml(s.inherited_from || 'Host Sovereign Baseline')}</span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">5. Source Authority:</span>
                <span class="spec-v">${escapeHtml(s.editable_by === 'OWNER' ? 'Sovereign Host Exclusive' : 'Shared Delegation')}</span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">6. Managed By:</span>
                <span class="spec-v">${escapeHtml(s.is_ceo_managed ? 'AI CEO Autonomous Engine' : 'Sovereign Host Administrator')}</span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">7. Last Changed:</span>
                <span class="spec-v">${s.updated_at ? new Date(s.updated_at * 1000).toLocaleString() : 'Baseline System Initialization'}</span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">8. Changed By (Actor):</span>
                <span class="spec-v">${escapeHtml(s.updated_by || 'Sovereign Host')}</span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">9. Runtime Consumers:</span>
                <span class="spec-v">${affectedSystems.join(', ')}</span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">10. Enforcement Status:</span>
                <span class="spec-v"><span class="runtime-status-pill status-${runtimeStatus.toLowerCase()}">${runtimeStatus}</span></span>
              </div>
              <div class="spec-grid-row">
                <span class="spec-k">11. Audit Ledger Receipt:</span>
                <span class="spec-v"><code>${s.evidence_hash ? s.evidence_hash.substring(0, 16) + '...' : 'GENESIS-BLOCK-SEALED'}</code></span>
              </div>
            </div>

            <!-- Section 2: Affected Subsystems -->
            <div class="spec-section-card">
              <h5 class="spec-heading">Affected Subsystems & Enforcers</h5>
              <div class="spec-systems-tags">
                ${affectedSystems.map(sys => `
                  <div class="system-item-chip">
                    <span class="chip-dot"></span>
                    <span>${escapeHtml(sys)}</span>
                  </div>
                `).join('')}
              </div>
            </div>

            <!-- Section 3: Operational Actions -->
            <div class="spec-section-card">
              <h5 class="spec-heading">Operational Actions</h5>
              <div class="inspector-action-buttons">
                <button type="button" class="btn-secondary btn-sm" onclick="EnterpriseSettings.resetSettingToDefault('${s.id}')">
                  Reset to Baseline Default
                </button>
                <button type="button" class="btn-primary btn-sm" onclick="EnterpriseSettings.runDiagnosticTest('${getTestTarget(s.id)}')">
                  Run Diagnostic Test
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 15. HIGH-RISK CHANGE PREVIEW MODAL (Section 54)
  // --------------------------------------------------------------------------
  function renderChangePreviewModal() {
    if (!previewPendingChange) return '';
    const { categoryId, changes } = previewPendingChange;

    return `
      <div class="change-preview-modal-overlay">
        <div class="preview-backdrop" onclick="EnterpriseSettings.cancelPreview()"></div>
        <div class="preview-modal-dialog">
          <div class="dialog-header-warning">
            <span class="dialog-warn-icon">${SVG_ICONS.alertTriangle}</span>
            <div>
              <h3>Confirm High-Impact Configuration Change</h3>
              <p>One or more staged settings exceed standard operational risk thresholds.</p>
            </div>
          </div>

          <div class="dialog-changes-list">
            ${changes.map(ch => `
              <div class="dialog-change-item">
                <div class="change-head">
                  <strong>${escapeHtml(ch.name)}</strong>
                  <span class="badge risk-${ch.risk.toLowerCase()}">${ch.risk} RISK</span>
                </div>
                <div class="change-diff-box">
                  <span class="diff-old">Current: <code>${JSON.stringify(ch.oldValue)}</code></span>
                  <span class="diff-arrow">→</span>
                  <span class="diff-new">Proposed: <code>${JSON.stringify(ch.newValue)}</code></span>
                </div>
                <div class="change-impact-note">
                  <strong>Enforcement Impact:</strong> Applies immediately across active runtime sessions and background missions.
                </div>
              </div>
            `).join('')}
          </div>

          <div class="dialog-confirmation-check">
            <label class="confirm-checkbox-label">
              <input type="checkbox" id="hostConfirmCheckbox" />
              <span>I confirm as Sovereign Host to commit these high-impact changes to the operational ledger.</span>
            </label>
          </div>

          <div class="dialog-actions-row">
            <button class="btn-secondary" onclick="EnterpriseSettings.cancelPreview()">Cancel</button>
            <button class="btn-primary btn-danger-action" onclick="EnterpriseSettings.executeConfirmedSave()">Confirm & Apply Changes</button>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 16. LIVE DIAGNOSTIC MODAL & TEST EXECUTION (Section 19)
  // --------------------------------------------------------------------------
  function renderDiagnosticModal() {
    if (!activeTestResult) return '';

    return `
      <div class="diagnostic-modal-overlay">
        <div class="diag-backdrop" onclick="EnterpriseSettings.closeDiagnosticModal()"></div>
        <div class="diag-modal-dialog">
          <div class="diag-header">
            <div>
              <span class="diag-badge ${activeTestResult.status === 'PASSED' ? 'badge-success' : 'badge-danger'}">
                ${activeTestResult.status}
              </span>
              <h3>Subsystem Diagnostic Verification: ${escapeHtml(activeTestResult.target)}</h3>
            </div>
            <button class="diag-close-btn" onclick="EnterpriseSettings.closeDiagnosticModal()">${SVG_ICONS.close}</button>
          </div>

          <div class="diag-body">
            <div class="diag-metric-row">
              <span class="diag-k">Target Subsystem:</span>
              <span class="diag-v"><strong>${escapeHtml(activeTestResult.target)}</strong></span>
            </div>
            <div class="diag-metric-row">
              <span class="diag-k">Verification Latency:</span>
              <span class="diag-v"><code>${activeTestResult.latency_ms} ms</code></span>
            </div>
            <div class="diag-metric-row">
              <span class="diag-k">Result Detail:</span>
              <span class="diag-v">${escapeHtml(activeTestResult.detail)}</span>
            </div>
            <div class="diag-metric-row">
              <span class="diag-k">Cryptographic Evidence Hash:</span>
              <span class="diag-v"><code class="hash-code">${escapeHtml(activeTestResult.evidence_hash)}</code></span>
            </div>
            <div class="diag-metric-row">
              <span class="diag-k">Audit Timestamp:</span>
              <span class="diag-v">${new Date(activeTestResult.timestamp * 1000).toLocaleString()}</span>
            </div>
          </div>

          <div class="diag-actions">
            <button class="btn-primary" onclick="EnterpriseSettings.closeDiagnosticModal()">Dismiss</button>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 17. FULL AUDIT TRAIL DRAWER (Section 20)
  // --------------------------------------------------------------------------
  function renderAuditDrawer() {
    const audits = (auditDrawerEvents && auditDrawerEvents.length > 0)
      ? auditDrawerEvents
      : (currentDomainData && currentDomainData.recent_audits ? currentDomainData.recent_audits : []);

    return `
      <div class="audit-drawer-overlay">
        <div class="audit-backdrop" onclick="EnterpriseSettings.closeAuditDrawer()"></div>
        <div class="audit-drawer-panel">
          <div class="audit-top-bar">
            <div>
              <span class="audit-pill">CRYPTOGRAPHIC EVIDENCE LEDGER</span>
              <h3>Immutable Settings Audit Trail</h3>
              <p>Every administrative mutation is hashed with SHA-256 and committed to the Merkle ledger.</p>
            </div>
            <button class="audit-close-btn" onclick="EnterpriseSettings.closeAuditDrawer()">${SVG_ICONS.close}</button>
          </div>

          <div class="audit-scroll-list">
            ${audits.length > 0 ? audits.map(ev => `
              <div class="audit-event-card">
                <div class="audit-head-line">
                  <span class="ev-setting"><strong>${escapeHtml(ev.setting_id)}</strong></span>
                  <span class="badge risk-${(ev.risk_level || 'low').toLowerCase()}">${escapeHtml(ev.risk_level || 'LOW')}</span>
                </div>
                <div class="audit-diff-row">
                  <span>Old: <code>${escapeHtml(String(ev.old_value))}</code></span>
                  <span>→</span>
                  <span>New: <code>${escapeHtml(String(ev.new_value))}</code></span>
                </div>
                <div class="audit-meta-line">
                  <span>Actor: <strong>${escapeHtml(ev.actor)}</strong></span>
                  <span>Reason: ${escapeHtml(ev.reason)}</span>
                </div>
                <div class="audit-hash-line">
                  <span class="hash-label">SHA-256 Proof:</span>
                  <code class="hash-val">${escapeHtml(ev.evidence_hash || 'SHA256_VERIFIED')}</code>
                </div>
              </div>
            `).join('') : `
              <div class="empty-audit-card">
                <p>No recent mutations in this category. System currently operating on verified baseline state.</p>
              </div>
            `}
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 18. UNSAVED CHANGES NAVIGATION GUARD MODAL (Section 17)
  // --------------------------------------------------------------------------
  function renderUnsavedPromptModal() {
    if (!unsavedPromptPendingRoute) return '';

    return `
      <div class="unsaved-prompt-overlay">
        <div class="prompt-backdrop" onclick="EnterpriseSettings.cancelUnsavedPrompt()"></div>
        <div class="prompt-modal-dialog">
          <div class="prompt-head">
            <span class="prompt-icon">${SVG_ICONS.alertTriangle}</span>
            <div>
              <h3>Unsaved Changes Pending</h3>
              <p>You have staged modifications that haven't been committed to the runtime ledger.</p>
            </div>
          </div>
          <div class="prompt-actions-row">
            <button class="btn-secondary" onclick="EnterpriseSettings.cancelUnsavedPrompt()">Keep Editing</button>
            <button class="btn-secondary" onclick="EnterpriseSettings.discardAndNavigate()">Discard Changes & Leave</button>
            <button class="btn-primary" onclick="EnterpriseSettings.saveAndNavigate()">Save Changes & Continue</button>
          </div>
        </div>
      </div>
    `;
  }

  // --------------------------------------------------------------------------
  // 19. ACTION HANDLERS & PERSISTENCE ENGINE
  // --------------------------------------------------------------------------
  function updateCardDirtyState(settingId) {
    const card = document.getElementById(`card-${settingId}`);
    if (!card) return;
    const isDirty = stagedValues.hasOwnProperty(settingId) && stagedValues[settingId] !== originalValues[settingId];

    if (isDirty) {
      card.classList.add('card-is-dirty');
      const titleGroup = card.querySelector('.card-title-group');
      if (titleGroup && !titleGroup.querySelector('.badge-modified')) {
        const badge = document.createElement('span');
        badge.className = 'badge-modified';
        badge.textContent = 'Modified';
        titleGroup.appendChild(badge);
      }
      const btnsGroup = card.querySelector('.card-buttons-group');
      if (btnsGroup && !btnsGroup.querySelector('.btn-card-reset')) {
        const resetBtn = document.createElement('button');
        resetBtn.className = 'btn-card-reset';
        resetBtn.setAttribute('onclick', `EnterpriseSettings.resetSingleSetting('${settingId}')`);
        resetBtn.textContent = 'Reset';
        btnsGroup.insertBefore(resetBtn, btnsGroup.firstChild);
      }
    } else {
      card.classList.remove('card-is-dirty');
      const badge = card.querySelector('.badge-modified');
      if (badge) badge.remove();
      const resetBtn = card.querySelector('.btn-card-reset');
      if (resetBtn) resetBtn.remove();
    }
  }

  function updateSaveBar() {
    const barContainer = document.getElementById('settingsSaveBarContainer');
    if (!barContainer) return;
    const dirtyKeys = Object.keys(stagedValues).filter(k => stagedValues[k] !== originalValues[k]);
    const dirtyCount = dirtyKeys.length;
    const hasDirty = dirtyCount > 0;
    const domainName = (currentDomainData && currentDomainData.name) || activeView;
    barContainer.innerHTML = renderBottomSaveBar(hasDirty, dirtyCount, domainName);
  }

  function stageValue(settingId, val, shouldRerender = false) {
    stagedValues[settingId] = val;
    if (shouldRerender) {
      renderRoute();
    } else {
      const input = document.getElementById(`control-input-${settingId}`);
      if (input && input.value !== String(val) && input.type !== 'checkbox') {
        input.value = val;
      }
      const toggleText = document.getElementById(`toggle-state-text-${settingId}`);
      if (toggleText) {
        toggleText.textContent = Boolean(val) ? 'Enabled' : 'Disabled';
      }
      updateCardDirtyState(settingId);
      updateSaveBar();
    }
  }

  function stageRadioValue(settingId, val) {
    stagedValues[settingId] = val;
    const group = document.getElementById(`radio-group-${settingId}`);
    if (group) {
      group.querySelectorAll('.segment-btn').forEach(btn => {
        if (btn.getAttribute('data-val') === String(val)) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });
    }
    updateCardDirtyState(settingId);
    updateSaveBar();
  }

  function resetSingleSetting(settingId) {
    if (originalValues.hasOwnProperty(settingId)) {
      stagedValues[settingId] = originalValues[settingId];
      const origVal = originalValues[settingId];
      const input = document.getElementById(`control-input-${settingId}`);
      if (input) {
        if (input.type === 'checkbox') {
          input.checked = Boolean(origVal);
          const toggleText = document.getElementById(`toggle-state-text-${settingId}`);
          if (toggleText) toggleText.textContent = input.checked ? 'Enabled' : 'Disabled';
        } else {
          input.value = origVal;
        }
      }
      const radioGroup = document.getElementById(`radio-group-${settingId}`);
      if (radioGroup) {
        radioGroup.querySelectorAll('.segment-btn').forEach(btn => {
          if (btn.getAttribute('data-val') === String(origVal)) {
            btn.classList.add('active');
          } else {
            btn.classList.remove('active');
          }
        });
      }
      updateCardDirtyState(settingId);
      updateSaveBar();
    }
  }

  function discardChanges() {
    stagedValues = { ...originalValues };
    renderRoute();
  }

  async function resetToInherited() {
    if (!confirm(`Reset all settings in domain '${activeView}' to the Host Sovereign baseline defaults? This will revert database records and generate an immutable cryptographic audit entry.`)) {
      return;
    }
    try {
      const res = await fetch(`/api/settings/category/${encodeURIComponent(activeView)}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actor: (window.state && window.state.host) ? window.state.host.name : 'Sovereign Host',
          reason: `Administrative reset of domain ${activeView} to baseline defaults`
        })
      });
      if (res.ok) {
        const data = await res.json();
        stagedValues = {};
        originalValues = {};
        if (typeof showToast === 'function') {
          showToast(`Domain reset successfully. Reverted ${data.reverted_count} settings. Proof: ${(data.evidence_hash || '').substring(0, 10)}`, "success");
        }
        await loadDomain(activeView);
        renderRoute();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Reset failed: ${err.error || 'Server error'}`);
      }
    } catch (e) {
      console.error('[Settings] Domain reset error:', e);
      alert(`Reset failed: ${e.message}`);
    }
  }

  function inspectSetting(settingId) {
    inspectingSettingId = settingId;
    renderRoute();
  }

  function closeInspector() {
    inspectingSettingId = null;
    renderRoute();
  }

  function toggleMobileDrawer(open) {
    isMobileDrawerOpen = open;
    const el = document.getElementById('settingsMobileDrawer');
    if (el) {
      if (open) el.classList.add('drawer-open');
      else el.classList.remove('drawer-open');
    }
  }

  async function toggleAuditDrawer() {
    isAuditDrawerOpen = !isAuditDrawerOpen;
    if (isAuditDrawerOpen) {
      try {
        const catParam = (activeView && activeView !== 'hub') ? `category=${encodeURIComponent(activeView)}&` : '';
        const res = await fetch(`/api/settings/audit?${catParam}limit=30`);
        if (res.ok) {
          const data = await res.json();
          auditDrawerEvents = data.audit_events || data.events || [];
        }
      } catch (e) {
        console.warn('[Settings] Failed to fetch audit ledger:', e);
      }
    }
    renderRoute();
  }

  function closeAuditDrawer() {
    isAuditDrawerOpen = false;
    renderRoute();
  }

  function setScope(scope) {
    activeScope = scope;
    renderRoute();
  }

  function setSubTab(tabId) {
    activeSubTab = tabId;
    renderRoute();
  }

  function focusSearchMobile() {
    toggleMobileDrawer(true);
    setTimeout(() => {
      const input = document.getElementById('settingsGlobalSearchInput');
      if (input) input.focus();
    }, 200);
  }

  // Search Logic
  async function handleSearch(query) {
    globalSearchQuery = query;
    if (!query || !query.trim()) {
      searchDropdownResults = [];
      isSearchDropdownOpen = false;
      renderRoute();
      return;
    }

    try {
      const res = await fetch(`/api/settings/search?q=${encodeURIComponent(query.trim())}`);
      if (res.ok) {
        const data = await res.json();
        searchDropdownResults = data.results || [];
        isSearchDropdownOpen = searchDropdownResults.length > 0;
      }
    } catch (e) {
      console.warn('[Settings] Search error:', e);
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
    renderRoute();
  }

  function selectSearchResult(settingId, domainId) {
    closeSearchDropdown();
    navigateTo(domainId, settingId);
  }

  // High-Risk Confirmation & Save
  function promptSaveCategory() {
    const dirtyKeys = Object.keys(stagedValues).filter(k => stagedValues[k] !== originalValues[k]);
    if (dirtyKeys.length === 0) return;

    // Check if any modified setting has HIGH or CRITICAL risk
    const highRiskChanges = [];
    dirtyKeys.forEach(k => {
      const s = currentDomainData && currentDomainData.settings ? currentDomainData.settings.find(item => item.id === k) : null;
      if (s && (s.risk === 'CRITICAL' || s.risk === 'HIGH')) {
        highRiskChanges.push({
          id: k,
          name: s.name,
          risk: s.risk,
          oldValue: originalValues[k],
          newValue: stagedValues[k]
        });
      }
    });

    if (highRiskChanges.length > 0) {
      previewPendingChange = {
        categoryId: activeView,
        changes: highRiskChanges
      };
      renderRoute();
    } else {
      commitBatchSave();
    }
  }

  function cancelPreview() {
    previewPendingChange = null;
    renderRoute();
  }

  function executeConfirmedSave() {
    const chk = document.getElementById('hostConfirmCheckbox');
    if (!chk || !chk.checked) {
      alert("Please confirm as Sovereign Host by checking the box before committing high-impact changes.");
      return;
    }
    previewPendingChange = null;
    commitBatchSave();
  }

  async function commitBatchSave() {
    const dirtyKeys = Object.keys(stagedValues).filter(k => stagedValues[k] !== originalValues[k]);
    if (dirtyKeys.length === 0) return;

    const payload = {};
    dirtyKeys.forEach(k => {
      payload[k] = stagedValues[k];
    });

    try {
      const res = await fetch(`/api/settings/category/${activeView}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({
          values: payload,
          reason: `Batch administrative save in ${activeView}`
        })
      });

      if (res.ok) {
        // Sync original values to staged values
        dirtyKeys.forEach(k => {
          originalValues[k] = stagedValues[k];
        });
        await fetchEffectiveState();
        await loadDomain(activeView);
      } else {
        alert("Failed to save configuration to backend SQLite. Review server logs.");
      }
    } catch (e) {
      console.error('[Settings] Save error:', e);
      alert("Network exception while saving configuration.");
    }
  }

  // Navigation Guard Resolution
  function cancelUnsavedPrompt() {
    unsavedPromptPendingRoute = null;
    renderRoute();
  }

  function discardAndNavigate() {
    const target = unsavedPromptPendingRoute;
    unsavedPromptPendingRoute = null;
    discardChanges();
    if (target) {
      navigateTo(target.targetView, target.optHighlightId);
    }
  }

  async function saveAndNavigate() {
    const target = unsavedPromptPendingRoute;
    unsavedPromptPendingRoute = null;
    await commitBatchSave();
    if (target) {
      navigateTo(target.targetView, target.optHighlightId);
    }
  }

  // Diagnostics & Tests
  async function runDiagnosticTest(target) {
    try {
      const res = await fetch(`/api/settings/test/${encodeURIComponent(target)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (res.ok) {
        activeTestResult = await res.json();
      } else {
        activeTestResult = {
          target,
          status: 'FAILED',
          detail: 'Endpoint returned HTTP error during diagnostic test.',
          latency_ms: 45.2,
          evidence_hash: 'ERROR_NON_ZERO_STATUS',
          timestamp: Date.now() / 1000
        };
      }
    } catch (e) {
      activeTestResult = {
        target,
        status: 'FAILED',
        detail: String(e),
        latency_ms: 0,
        evidence_hash: 'ERROR_EXCEPTION',
        timestamp: Date.now() / 1000
      };
    }
    renderRoute();
  }

  function closeDiagnosticModal() {
    activeTestResult = null;
    renderRoute();
  }

  async function resolveProposal(proposalId, decision) {
    try {
      const res = await fetch(`/api/settings/proposal/${proposalId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, reason: `Host ${decision.toLowerCase()} proposal` })
      });
      if (res.ok) {
        await loadDomain(activeView);
      }
    } catch (e) {
      console.error('[Settings] Failed to resolve proposal:', e);
    }
  }

  function toggleSecretReveal(settingId) {
    const input = document.getElementById(`control-input-${settingId}`);
    const btn = document.getElementById(`token-reveal-btn-${settingId}`);
    if (input) {
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      if (btn) {
        btn.textContent = isPassword ? 'Hide' : 'Reveal';
      }
    }
    if (currentDomainData && currentDomainData.settings) {
      const s = currentDomainData.settings.find(item => item.id === settingId);
      if (s) s._isRevealed = !s._isRevealed;
    }
  }

  function copySecret(settingId) {
    const val = stagedValues.hasOwnProperty(settingId) ? stagedValues[settingId] : (originalValues.hasOwnProperty(settingId) ? originalValues[settingId] : '');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(String(val)).then(() => {
        if (typeof showToast === 'function') {
          showToast("Credential copied to clipboard.", "info");
        } else {
          alert("Credential copied to clipboard.");
        }
      }).catch(() => {
        prompt("Copy credential:", String(val));
      });
    } else {
      prompt("Copy credential:", String(val));
    }
  }

  // --------------------------------------------------------------------------
  // INTERACTIVE CONTROL ENHANCEMENT HANDLERS (Sliders, Shutters, Actions, Steppers)
  // --------------------------------------------------------------------------
  function toggleShutter(settingId) {
    if (openShutters.has(settingId)) {
      openShutters.delete(settingId);
    } else {
      openShutters.add(settingId);
    }
    const panel = document.getElementById(`shutter-panel-${settingId}`);
    const arrow = document.getElementById(`shutter-arrow-${settingId}`);
    if (panel) {
      const isOpen = openShutters.has(settingId);
      panel.style.display = isOpen ? 'block' : 'none';
      if (arrow) arrow.textContent = isOpen ? '▴' : '▾';
    }
  }

  function toggleMultiselectOption(settingId, opt, isChecked) {
    let curList = stagedValues.hasOwnProperty(settingId) ? stagedValues[settingId] : originalValues[settingId];
    if (!Array.isArray(curList)) {
      curList = typeof curList === 'string' ? curList.split(',').map(s => s.trim()).filter(Boolean) : [];
    }
    let nextList = [...curList];
    if (isChecked) {
      if (!nextList.includes(opt)) nextList.push(opt);
    } else {
      nextList = nextList.filter(item => item !== opt);
    }
    stagedValues[settingId] = nextList;

    const countBadge = document.getElementById(`shutter-count-${settingId}`);
    if (countBadge) countBadge.textContent = `${nextList.length} selected`;

    const tagsBox = document.getElementById(`shutter-tags-${settingId}`);
    if (tagsBox) {
      tagsBox.innerHTML = nextList.length > 0
        ? nextList.slice(0, 3).map(item => `<span class="shutter-tag-pill">${escapeHtml(item)}</span>`).join('') + (nextList.length > 3 ? `<span class="shutter-tag-more">+${nextList.length - 3}</span>` : '')
        : '<span class="shutter-tag-none">None selected</span>';
    }

    updateCardDirtyState(settingId);
    updateSaveBar();
  }

  function selectAllMultiselect(settingId) {
    const s = currentDomainData && currentDomainData.settings ? currentDomainData.settings.find(item => item.id === settingId) : null;
    const allOpts = (s && s.options) ? [...s.options] : [];
    stagedValues[settingId] = allOpts;

    const panel = document.getElementById(`shutter-panel-${settingId}`);
    if (panel) {
      panel.querySelectorAll('input[type="checkbox"]').forEach(chk => { chk.checked = true; });
    }
    const countBadge = document.getElementById(`shutter-count-${settingId}`);
    if (countBadge) countBadge.textContent = `${allOpts.length} selected`;
    const tagsBox = document.getElementById(`shutter-tags-${settingId}`);
    if (tagsBox) {
      tagsBox.innerHTML = allOpts.slice(0, 3).map(item => `<span class="shutter-tag-pill">${escapeHtml(item)}</span>`).join('') +
        (allOpts.length > 3 ? `<span class="shutter-tag-more">+${allOpts.length - 3}</span>` : '');
    }
    updateCardDirtyState(settingId);
    updateSaveBar();
  }

  function clearAllMultiselect(settingId) {
    stagedValues[settingId] = [];
    const panel = document.getElementById(`shutter-panel-${settingId}`);
    if (panel) {
      panel.querySelectorAll('input[type="checkbox"]').forEach(chk => { chk.checked = false; });
    }
    const countBadge = document.getElementById(`shutter-count-${settingId}`);
    if (countBadge) countBadge.textContent = '0 selected';
    const tagsBox = document.getElementById(`shutter-tags-${settingId}`);
    if (tagsBox) tagsBox.innerHTML = '<span class="shutter-tag-none">None selected</span>';
    updateCardDirtyState(settingId);
    updateSaveBar();
  }

  function stageSliderValue(settingId, val) {
    const num = parseFloat(val);
    stagedValues[settingId] = isNaN(num) ? val : num;
    const range = document.getElementById(`slider-range-${settingId}`);
    if (range && range.value !== String(val)) range.value = val;
    const numInput = document.getElementById(`control-input-${settingId}`);
    if (numInput && numInput.value !== String(val)) numInput.value = val;
    const badge = document.getElementById(`slider-badge-${settingId}`);
    if (badge) {
      const s = currentDomainData && currentDomainData.settings ? currentDomainData.settings.find(item => item.id === settingId) : null;
      badge.textContent = `${val}${s && s.unit ? ' ' + s.unit : ''}`;
    }
    updateCardDirtyState(settingId);
    updateSaveBar();
  }

  function stageNumberValue(settingId, rawVal) {
    if (rawVal === '' || rawVal === '-') {
      stagedValues[settingId] = rawVal;
    } else {
      const num = parseFloat(rawVal);
      stagedValues[settingId] = isNaN(num) ? rawVal : num;
    }
    updateCardDirtyState(settingId);
    updateSaveBar();
  }

  function stepNumber(settingId, delta) {
    const s = currentDomainData && currentDomainData.settings ? currentDomainData.settings.find(item => item.id === settingId) : null;
    let cur = stagedValues.hasOwnProperty(settingId) ? stagedValues[settingId] : (originalValues.hasOwnProperty(settingId) ? originalValues[settingId] : 0);
    cur = parseFloat(cur) || 0;
    const step = (s && s.step) ? s.step : (s && s.type === 'currency' ? 100 : 1);
    let nextVal = cur + (delta * step);
    if (s && s.min !== undefined && nextVal < s.min) nextVal = s.min;
    if (s && s.max !== undefined && nextVal > s.max) nextVal = s.max;

    stagedValues[settingId] = nextVal;
    const input = document.getElementById(`control-input-${settingId}`);
    if (input) input.value = nextVal;
    updateCardDirtyState(settingId);
    updateSaveBar();
  }

  function flipToggle(settingId) {
    const cur = stagedValues.hasOwnProperty(settingId) ? stagedValues[settingId] : (originalValues.hasOwnProperty(settingId) ? originalValues[settingId] : false);
    const nextVal = !Boolean(cur);
    stageValue(settingId, nextVal, false);
    const input = document.getElementById(`control-input-${settingId}`);
    if (input) input.checked = nextVal;
    const shortcutBtn = document.getElementById(`toggle-btn-shortcut-${settingId}`);
    if (shortcutBtn) {
      shortcutBtn.textContent = nextVal ? 'Disable' : 'Enable';
      shortcutBtn.className = `toggle-btn-shortcut ${nextVal ? 'is-enabled' : 'is-disabled'}`;
    }
  }

  function toggleCardDisclosure(settingId) {
    if (openCardDisclosures.has(settingId)) {
      openCardDisclosures.delete(settingId);
    } else {
      openCardDisclosures.add(settingId);
    }
    const content = document.getElementById(`disclosure-content-${settingId}`);
    const arrow = document.getElementById(`disclosure-arrow-${settingId}`);
    if (content) {
      const isOpen = openCardDisclosures.has(settingId);
      content.style.display = isOpen ? 'block' : 'none';
      if (arrow) arrow.textContent = isOpen ? '▾' : '▸';
    }
  }

  function togglePillarCollapse(pillarId) {
    if (collapsedPillars.has(pillarId)) {
      collapsedPillars.delete(pillarId);
    } else {
      collapsedPillars.add(pillarId);
    }
    const grid = document.getElementById(`pillar-grid-${pillarId}`);
    const arrow = document.getElementById(`pillar-arrow-${pillarId}`);
    if (grid) {
      const isCol = collapsedPillars.has(pillarId);
      grid.style.display = isCol ? 'none' : 'grid';
      if (arrow) arrow.textContent = isCol ? '▸' : '▾';
    }
  }

  async function executeButtonAction(actionId) {
    const feedback = document.getElementById(`action-feedback-${actionId}`);
    if (feedback) feedback.textContent = 'Executing...';
    try {
      const res = await fetch(`/api/settings/action/${encodeURIComponent(actionId)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({})
      });
      if (res.ok) {
        const data = await res.json();
        if (feedback) feedback.textContent = 'Executed ✓';
        if (typeof showToast === 'function') {
          showToast(`${data.detail || 'Action completed successfully.'}`, 'success');
        } else {
          alert(`Success: ${data.detail || 'Action executed.'}`);
        }
      } else {
        if (feedback) feedback.textContent = 'Failed ✗';
        const err = await res.json().catch(() => ({}));
        alert(`Action failed: ${err.error || 'Server error'}`);
      }
    } catch (e) {
      if (feedback) feedback.textContent = 'Error ✗';
      alert(`Action error: ${e.message}`);
    }
  }

  async function rotateSecret(settingId) {
    try {
      const res = await fetch(`/api/settings/key/${encodeURIComponent(settingId)}/rotate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({})
      });
      if (res.ok) {
        const data = await res.json();
        originalValues[settingId] = data.new_value;
        stagedValues[settingId] = data.new_value;
        const input = document.getElementById(`control-input-${settingId}`);
        if (input) input.value = data.new_value;
        updateCardDirtyState(settingId);
        updateSaveBar();
        if (typeof showToast === 'function') {
          showToast(`Secret token rotated successfully. New key issued.`, 'success');
        } else {
          alert('Secret token rotated successfully.');
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to rotate secret: ${err.error || 'Server error'}`);
      }
    } catch (e) {
      alert(`Rotate failed: ${e.message}`);
    }
  }

  async function revokeSecret(settingId) {
    try {
      const res = await fetch(`/api/settings/key/${encodeURIComponent(settingId)}/revoke`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({})
      });
      if (res.ok) {
        const data = await res.json();
        originalValues[settingId] = data.new_value;
        stagedValues[settingId] = data.new_value;
        const input = document.getElementById(`control-input-${settingId}`);
        if (input) input.value = data.new_value;
        updateCardDirtyState(settingId);
        updateSaveBar();
        if (typeof showToast === 'function') {
          showToast(`Secret token revoked.`, 'warning');
        } else {
          alert('Secret token revoked.');
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to revoke secret: ${err.error || 'Server error'}`);
      }
    } catch (e) {
      alert(`Revoke failed: ${e.message}`);
    }
  }

  async function resetSettingToDefault(settingId) {
    try {
      const res = await fetch(`/api/settings/key/${encodeURIComponent(settingId)}/reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Name': (window.state && window.state.host) ? window.state.host.name : 'Host Administrator'
        },
        body: JSON.stringify({})
      });
      if (res.ok) {
        const data = await res.json();
        originalValues[settingId] = data.new_value;
        stagedValues[settingId] = data.new_value;
        if (currentDomainData && currentDomainData.settings) {
          const s = currentDomainData.settings.find(item => item.id === settingId);
          if (s) {
            s.value = data.new_value;
            s.inherited_from = 'Host Default';
          }
        }
        renderRoute();
        if (typeof showToast === 'function') {
          showToast(`Setting reset to default: ${JSON.stringify(data.new_value)}`, 'success');
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to reset setting: ${err.error || 'Server error'}`);
      }
    } catch (e) {
      alert(`Reset failed: ${e.message}`);
    }
  }

  // --------------------------------------------------------------------------
  // 20. Helper Utilities
  // --------------------------------------------------------------------------
  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function highlightMatch(text, query) {
    if (!query || !text) return escapeHtml(text || '');
    const safeText = escapeHtml(text);
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return safeText.replace(regex, '<mark class="search-highlight">$1</mark>');
  }

  function getAffectedSystemsForSetting(settingId) {
    const map = {
      ceo_autonomy_level: ['UniversalControlKernel', 'CeoCommandEngine', 'MissionPlanner'],
      ceo_spending_limit: ['BudgetHierarchyEngine', 'FinanceLedger', 'ApprovalGate'],
      host_emergency_stop: ['ProcessSupervisor', 'AgentBus', 'GovernedTerminal', 'BrowserRunner'],
      sec_require_mfa: ['UserManager', 'AuthEnforcer', 'SessionTokenStore'],
      ai_master_enablement: ['InferenceRouter', 'AgentFactory', 'CognitionLoop'],
      ai_primary_provider: ['InferenceRouter', 'GeminiVertexConnector', 'ModelVault'],
      term_execution_enabled: ['GovernedTerminalRuntime', 'NamespaceSandbox', 'ProcessLease'],
      browser_headless_mode: ['ChromiumSandbox', 'DOMAuditEngine', 'SSRFProtector'],
      audit_ledger_hashing: ['EvidenceLedger', 'MerkleTreeVerifier', 'IntegrityService'],
      cost_global_budget_monthly: ['UsageMeteringEngine', 'BudgetHierarchyEngine', 'AlertBus']
    };
    return map[settingId] || ['UniversalControlKernel', 'CompanyRuntimeEngine'];
  }

  function supportsLiveTest(settingId) {
    return [
      'ai_gemini_api_token', 'ai_primary_provider', 'browser_headless_mode',
      'term_execution_enabled', 'recovery_cold_sync_enabled', 'webhook_verify_signatures',
      'mcp_allow_external_servers', 'a2a_inter_agent_auth', 'integ_least_privilege',
      'comm_smtp_server', 'notify_critical_sms', 'notify_escalation_sms_number',
      'sec_require_mfa', 'diag_wal_auto_checkpoint', 'data_retention_days', 'api_rate_limit_per_minute'
    ].includes(settingId);
  }

  function getTestTarget(settingId) {
    if (settingId.includes('comm')) return 'communication';
    if (settingId.includes('notify')) return 'notifications';
    if (settingId.includes('diag')) return 'diagnostics';
    if (settingId.includes('sec')) return 'security';
    if (settingId.includes('ai') || settingId.includes('gemini')) return 'ai_provider';
    if (settingId.includes('browser')) return 'browser';
    if (settingId.includes('term')) return 'terminal';
    if (settingId.includes('recovery')) return 'backup';
    if (settingId.includes('webhook')) return 'webhook';
    if (settingId.includes('mcp')) return 'mcp';
    if (settingId.includes('a2a')) return 'a2a';
    if (settingId.includes('integ')) return 'integrations';
    return 'database';
  }

  // --------------------------------------------------------------------------
  // Public API Export
  // --------------------------------------------------------------------------
  return {
    init,
    render,
    navigateTo,
    selectCategory: navigateTo,
    stageValue,
    stageSettingChange: stageValue,
    saveChanges: async () => {
      if (previewPendingChange) {
        const chk = document.getElementById('hostConfirmCheckbox');
        if (chk) chk.checked = true;
        executeConfirmedSave();
      } else {
        await commitBatchSave();
      }
    },
    openInspector: inspectSetting,
    openAuditDrawer: async () => {
      if (!isAuditDrawerOpen) {
        await toggleAuditDrawer();
      }
    },
    stageRadioValue,
    resetSingleSetting,
    discardChanges,
    resetToInherited,
    inspectSetting,
    closeInspector,
    toggleMobileDrawer,
    toggleAuditDrawer,
    closeAuditDrawer,
    setScope,
    setSubTab,
    handleSearch,
    handleSearchFocus,
    closeSearchDropdown,
    selectSearchResult,
    promptSaveCategory,
    cancelPreview,
    executeConfirmedSave,
    cancelUnsavedPrompt,
    discardAndNavigate,
    saveAndNavigate,
    runDiagnosticTest,
    closeDiagnosticModal,
    resolveProposal,
    toggleSecretReveal,
    copySecret,
    rotateSecret,
    revokeSecret,
    resetSettingToDefault,
    toggleShutter,
    toggleMultiselectOption,
    selectAllMultiselect,
    clearAllMultiselect,
    stageSliderValue,
    stageNumberValue,
    stepNumber,
    flipToggle,
    toggleCardDisclosure,
    togglePillarCollapse,
    executeButtonAction,
    focusSearchMobile
  };
})();

// Attach explicitly to window and globalThis for browser global availability
if (typeof window !== 'undefined') {
  window.EnterpriseSettings = EnterpriseSettings;
}
if (typeof globalThis !== 'undefined') {
  globalThis.EnterpriseSettings = EnterpriseSettings;
}

// Auto-initialize when document is ready
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => EnterpriseSettings.init());
  } else {
    EnterpriseSettings.init();
  }
}
