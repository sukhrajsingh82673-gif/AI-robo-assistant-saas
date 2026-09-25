"""
RoboAssistant 1.0.0-GA Unified CLI & Interactive Executive Cockpit
Zero Mock Data: Operates against true runtime state.
"""

import sys
import os
import argparse
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from core.models import MissionStatus
from core.portfolio import CompanyPortfolioManager, CompanyOnboardingEngine
from core.ceo import CeoCommandEngine, ExecutiveReportEngine
from core.evidence_ledger import EvidenceLedger
from core.control_kernel import UniversalControlKernel
from core.tool_fabric import CapabilityRegistry
from workloads.hospitality import run_hospitality_night_audit
from workloads.manufacturing import run_manufacturing_bottleneck_analysis
from workloads.saas import run_saas_churn_analysis
from workloads.personal import run_personal_file_hygiene
from workloads.universal_computer import run_universal_capability_discovery_task

def init_environment():
    ledger = EvidenceLedger(os.path.join(BASE_DIR, "storage/evidence/audit_ledger.jsonl"))
    kernel = UniversalControlKernel(ledger)
    registry = CapabilityRegistry()
    portfolio = CompanyPortfolioManager(tenant_id="tnt_primary", load_from_db=True)
    ceo_command = CeoCommandEngine(portfolio)
    ceo_reports = ExecutiveReportEngine(portfolio)
    return ledger, kernel, registry, portfolio, ceo_command, ceo_reports

def cmd_portfolio():
    _, _, _, portfolio, _, _ = init_environment()
    summary = portfolio.get_portfolio_summary()

    print("\n" + "="*65)
    print(" ROBOASSISTANT 1.0.0-GA — CORPORATE PORTFOLIO COCKPIT")
    print("="*65)
    print(f" Companies in Portfolio : {summary['total_companies']}")
    print(f" Operational Entities   : {summary['operational_companies']}")
    print(f" Requiring Attention    : {summary['attention_required_count']}")
    print(f" Active AI Missions     : {summary['total_active_missions']}")
    print(f" Active AI Employees    : {summary['total_ai_employees']}")
    print("-" * 65)
    print(" PORTFOLIO FINANCIAL OVERVIEW")
    print(f" Total Revenue          : ₹{summary['total_revenue']:,.2f}")
    print(f" Total Operating Cost   : ₹{summary['total_cost']:,.2f}")
    print(f" Net Contribution       : ₹{summary['total_contribution']:,.2f}")
    print("="*65)

    if not portfolio.list_companies():
        print("\n[!] Zero entities onboarded. Use 'onboard' or API to register an operating company.\n")
    else:
        print("\nOPERATING CONTEXTS:")
        for c in portfolio.list_companies():
            print(f" • [{c.status}] {c.name} ({c.industry})")
            print(f"   Revenue: ₹{c.revenue:,.2f} | Cost: ₹{c.cost:,.2f} | Contribution: ₹{c.contribution:,.2f}")
            print(f"   AI Workforce: {len(c.workforce)} agents | Operating Rules: {len(c.operating_rules)}")
        print("")

def cmd_briefing():
    _, _, _, portfolio, _, ceo_reports = init_environment()
    briefing = ceo_reports.generate_daily_executive_briefing()

    print("\n" + "="*65)
    print(" EXECUTIVE REPORTING ROOM — DAILY EXECUTIVE BRIEFING")
    print("="*65)
    print(f" Scope: {briefing['scope']} | Timestamp: {briefing['timestamp']}")
    print("-" * 65)
    print(" FINANCIAL SUMMARY:")
    for k, v in briefing["financial_summary"].items():
        print(f"  - {k.replace('_', ' ').title()}: {v}")
    print("-" * 65)
    print(" EXECUTIVE INTELLIGENCE:")
    answers = briefing["executive_answers"]
    print(f" [What happened] : {answers['what_happened']}")
    print(f" [Completed]     : {answers['what_was_completed']}")
    print(f" [Blocked/Issues]: {answers['what_failed_or_blocked']}")
    print(f" [Attention]     : {answers['what_needs_attention']}")
    print("="*65 + "\n")

def cmd_chat(instruction: str):
    _, _, _, portfolio, ceo_command, _ = init_environment()
    companies = portfolio.list_companies()
    if not companies:
        print("\n[!] No active company onboarded. Please onboard an entity first.\n")
        return

    comp = companies[0]
    print("\n" + "="*65)
    print(f" CHAT WITH CEO — STRATEGIC COMMAND ({comp.name})")
    print("="*65)
    print(f"Owner: \"{instruction}\"")
    print("-" * 65)
    res = ceo_command.execute_directive(comp.company_id, instruction)
    print(f"AI CEO ({res.get('command_type', 'RESPONSE')}):")
    print(f"\"{res['ceo_response']}\"")
    print("="*65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="RoboAssistant 1.0.0-GA CLI (Zero Mock Data)")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("portfolio", help="View corporate portfolio status")
    subparsers.add_parser("briefing", help="View Daily Executive Briefing")
    chat_parser = subparsers.add_parser("chat", help="Strategic command chat with AI CEO")
    chat_parser.add_argument("instruction", type=str, help="Strategic instruction for AI CEO")

    args = parser.parse_args()

    if args.command == "portfolio":
        cmd_portfolio()
    elif args.command == "briefing":
        cmd_briefing()
    elif args.command == "chat":
        cmd_chat(args.instruction)
    else:
        cmd_portfolio()

if __name__ == "__main__":
    main()
