"""Canonical top-level Settings information architecture.

The product prompt defines 16 sections.  The legacy registry has 45 categories.
This module maps the stable category IDs onto the new navigation without
renaming any key or category, so deep links and existing tests keep working.
"""

from __future__ import annotations

from typing import Dict, List

SECTIONS: List[Dict[str, object]] = [
    {
        "id": "general_organization",
        "num": "01",
        "name": "General & Organization",
        "description": "Organization profile, branding, locale, fiscal settings, and defaults for new companies.",
    },
    {
        "id": "companies",
        "num": "02",
        "name": "Companies",
        "description": "Company list and switcher, profiles, lifecycle, residency, clone/export, and ownership.",
    },
    {
        "id": "team_access",
        "num": "03",
        "name": "Team & Access",
        "description": "Members, invites, roles, permission matrix, SSO/SCIM, MFA, sessions, and approvals.",
    },
    {
        "id": "ai_agents_employees",
        "num": "04",
        "name": "AI Agents & Employees",
        "description": "Autonomy, speed presets, model routing, behavior, permissions, SOPs, memory, and emergency controls.",
    },
    {
        "id": "spending_budgets",
        "num": "05",
        "name": "Spending & Budgets",
        "description": "Scoped budgets, soft/hard caps, alerts, approvals, cost breakdown, and forecasting.",
    },
    {
        "id": "integrations",
        "num": "06",
        "name": "Integrations",
        "description": "Connectors, provider keys, public API tokens, webhooks, MCP servers, and the tool catalogue.",
    },
    {
        "id": "browser_automation",
        "num": "07",
        "name": "Browser & Automation",
        "description": "Browsing style, domain policy, politeness, sessions, downloads, desktop permissions, and evidence.",
    },
    {
        "id": "security_compliance",
        "num": "08",
        "name": "Security & Compliance",
        "description": "Encryption, keys, IP policy, sandboxing, DLP, residency, compliance packs, and incident response.",
    },
    {
        "id": "reports_documents",
        "num": "09",
        "name": "Reports & Documents",
        "description": "Scheduled reports, templates, document output, email delivery, sharing, and retention.",
    },
    {
        "id": "notifications",
        "num": "10",
        "name": "Notifications",
        "description": "Channels, per-event matrix, quiet hours, digests, escalation chains, and owner assistant channel.",
    },
    {
        "id": "data_storage_backups",
        "num": "11",
        "name": "Data, Storage & Backups",
        "description": "Storage quotas, retention, object storage, backups, restore drills, RPO/RTO, and erasure workflows.",
    },
    {
        "id": "infrastructure_stack",
        "num": "12",
        "name": "Infrastructure & Stack",
        "description": "Environments, deployment, workers, providers, release channel, feature flags, and observability.",
    },
    {
        "id": "billing_plan",
        "num": "13",
        "name": "Billing & Plan",
        "description": "Plan, seats, usage, invoices, payment methods, tax IDs, add-ons, and chargeback.",
    },
    {
        "id": "appearance_accessibility",
        "num": "14",
        "name": "Appearance & Accessibility",
        "description": "Theme, accent, density, motion, text size, contrast, and keyboard shortcuts.",
    },
    {
        "id": "audit_activity",
        "num": "15",
        "name": "Audit & Activity",
        "description": "Immutable searchable settings history, filters, exports, SIEM webhook, and retention.",
    },
    {
        "id": "advanced_danger",
        "num": "16",
        "name": "Advanced & Danger Zone",
        "description": "Experimental flags, event bus, ownership transfer, and destructive company actions.",
    },
]

SECTION_IDS = tuple(str(section["id"]) for section in SECTIONS)
SECTION_BY_ID = {str(section["id"]): section for section in SECTIONS}

# One category belongs to exactly one top-level section.  Category and setting
# IDs are deliberately unchanged from the legacy registry.
CATEGORY_TO_SECTION: Dict[str, str] = {
    # 01 General & Organization
    "account": "general_organization",
    "organization": "general_organization",
    "localization": "general_organization",
    # 02 Companies
    "company": "companies",
    # 03 Team & Access
    "users": "team_access",
    "approvals": "team_access",
    "enterprise": "team_access",
    # 04 AI Agents & Employees
    "ai": "ai_agents_employees",
    "ai_providers": "ai_agents_employees",
    "ai_ceo": "ai_agents_employees",
    "assistant": "ai_agents_employees",
    "workforce": "ai_agents_employees",
    "agent_factory": "ai_agents_employees",
    "missions": "ai_agents_employees",
    "workflows": "ai_agents_employees",
    "tools": "ai_agents_employees",
    "a2a": "ai_agents_employees",
    # 05 Spending & Budgets
    "finance": "spending_budgets",
    "usage": "spending_budgets",
    # 06 Integrations
    "integrations": "integrations",
    "api": "integrations",
    "webhooks": "integrations",
    "mcp": "integrations",
    # 07 Browser & Automation
    "desktop": "browser_automation",
    "browser": "browser_automation",
    "terminal": "browser_automation",
    "openhands": "browser_automation",
    # 08 Security & Compliance
    "host": "security_compliance",
    "governance": "security_compliance",
    "privacy": "security_compliance",
    "compliance": "security_compliance",
    "security": "security_compliance",
    # 09 Reports & Documents
    # No legacy category yet.  New definitions will target this section.
    # 10 Notifications
    "communication": "notifications",
    "notifications": "notifications",
    # 11 Data, Storage & Backups
    "data": "data_storage_backups",
    "files": "data_storage_backups",
    "records": "data_storage_backups",
    "recovery": "data_storage_backups",
    # 12 Infrastructure & Stack
    "monitoring": "infrastructure_stack",
    "features": "infrastructure_stack",
    "diagnostics": "infrastructure_stack",
    # 13 Billing & Plan
    "billing": "billing_plan",
    # 14 Appearance & Accessibility
    "appearance": "appearance_accessibility",
    # 15 Audit & Activity
    "audit": "audit_activity",
    # 16 Advanced & Danger Zone
    "advanced": "advanced_danger",
    "danger": "advanced_danger",
}


def section_for_category(category: str) -> str:
    """Return the top-level section ID for a legacy category.

    Unknown categories are attached to Advanced rather than silently dropped;
    the registry validator then reports them for review.
    """
    return CATEGORY_TO_SECTION.get(category, "advanced_danger")


def categories_for_section(section_id: str) -> List[str]:
    return [category for category, section in CATEGORY_TO_SECTION.items() if section == section_id]
