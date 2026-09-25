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

def cmd_cycle():
    _, _, _, portfolio, _, _ = init_environment()
    from core.ceo_engine import CEOExecutiveEngine
    engine = CEOExecutiveEngine(portfolio)
    companies = portfolio.list_companies()
    cid = companies[0].company_id if companies else "comp_none"
    cycle = engine.execute_executive_cycle(cid)
    print("\n" + "="*65)
    print(" ROBOASSISTANT 2.0 — CONTINUOUS EXECUTIVE CYCLE")
    print("="*65)
    print(f" Company: {cycle.get('company_name')} ({cycle.get('company_id')})")
    print(f" Cycle Stage: {cycle.get('cycle_stage')}")
    print("-" * 65)
    print(" PLANNING HORIZONS:")
    for h, data in cycle.get("planning_horizons", {}).items():
        print(f"  • [{h}]: {data}")
    print("-" * 65)
    print(" EXPLAINABLE OPERATIONAL REASONING:")
    reasoning = cycle.get("operational_reasoning", {})
    for k, v in reasoning.items():
        if k != "timestamp":
            print(f"  - {k.replace('_', ' ').title()}: {v}")
    print("="*65 + "\n")

def cmd_council(proposal: str):
    _, _, _, portfolio, _, _ = init_environment()
    from core.executive_council import ExecutiveCouncil
    companies = portfolio.list_companies()
    cid = companies[0].company_id if companies else "comp_none"
    council = ExecutiveCouncil(company_id=cid)
    review = council.review_proposal(
        topic="Executive Proposal via CLI",
        proposal=proposal,
        proposal_data={"cost": 10000.0, "authority": "AUTOMATIC_IDEMPOTENT"}
    )
    print("\n" + "="*65)
    print(" EXECUTIVE COUNCIL — INDEPENDENT CHALLENGE LOOP")
    print("="*65)
    print(f" Topic: {review['topic']}")
    print(f" Proposal: \"{review['proposal']}\"")
    print(f" Consensus: {review['consensus']}")
    print(f" Recommended Action: {review['recommended_action']}")
    print("-" * 65)
    print(" INDEPENDENT MEMBER ANALYSES:")
    for a in review["member_analyses"]:
        print(f"  [{a['role']}] Stance: {a['stance']} | Risk: {a['domain_risk']}")
        print(f"    Critique: {a['critique']}")
    print("="*65 + "\n")

def cmd_meeting():
    _, _, _, portfolio, _, _ = init_environment()
    from core.interactive_meeting import InteractiveMeetingSystem
    companies = portfolio.list_companies()
    cid = companies[0].company_id if companies else "comp_none"
    system = InteractiveMeetingSystem(portfolio, company_id=cid)
    meeting = system.conduct_executive_operating_meeting()
    print("\n" + "="*65)
    print(" INTERACTIVE EXECUTIVE OPERATING MEETING")
    print("="*65)
    print(f" Company: {meeting['company_name']}")
    print(f" Meeting ID: {meeting['meeting_id']}")
    print("-" * 65)
    print(" DEPARTMENT REPORTS:")
    for dept, rep in meeting["department_reports"].items():
        print(f" • {dept}:")
        print(f"   What Happened: {rep['what_happened']}")
        print(f"   Value Generated: {rep['value_generated']}")
    print("-" * 65)
    print(" CEO INTERROGATIONS & CHALLENGES:")
    for ch in meeting["ceo_challenges"]:
        print(f" • CEO to {ch['target_department']}: \"{ch['challenge']}\"")
        print(f"   Response: \"{ch['department_response']}\"")
    print("="*65 + "\n")

def cmd_telemetry():
    from core.host_fabric import UniversalHostAgent
    agent = UniversalHostAgent()
    t = agent.get_telemetry()
    print("\n" + "="*65)
    print(" UNIVERSAL HOST TELEMETRY & ROBOT STATUS")
    print("="*65)
    print(f" Host ID       : {t['host_id']}")
    print(f" Host Type     : {t['host_type']}")
    print(f" Status        : {t['status']}")
    print(f" OS & Arch     : {t['os']} ({t['architecture']})")
    print(f" CPU Cores     : {t['cpu_cores']}")
    print(f" Load Average  : {t['load_average']}")
    print(f" Quarantined   : {t['quarantined']}")
    print("="*65 + "\n")

def cmd_causality():
    _, _, _, portfolio, _, _ = init_environment()
    from core.business_causality import BusinessCausalityEngine
    companies = portfolio.list_companies()
    cid = companies[0].company_id if companies else "comp_none"
    causality = BusinessCausalityEngine(company_id=cid)
    summary = causality.get_causality_summary()
    print("\n" + "="*65)
    print(" BUSINESS CAUSALITY & OUTCOME ATTRIBUTION")
    print("="*65)
    print(f" Invariant Rule: {summary['invariant_respected']}")
    print(f" Chains Tracked       : {summary['total_chains_tracked']}")
    print(f" Verified Outcomes    : {summary['verified_outcomes_count']}")
    print(f" Pending Evidence     : {summary['pending_evidence_count']}")
    print(f" Verified Revenue     : ₹{summary['verified_attributed_revenue']:,.2f}")
    print(f" Total Incurred Cost  : ₹{summary['total_incurred_cost']:,.2f}")
    print(f" Net Contribution     : ₹{summary['net_verified_contribution']:,.2f}")
    print("="*65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="RoboAssistant 2.0 Unified CLI Cockpit")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("portfolio", help="View corporate portfolio status")
    subparsers.add_parser("briefing", help="View Daily Executive Briefing")
    subparsers.add_parser("cycle", help="Execute CEO continuous operating cycle")
    subparsers.add_parser("meeting", help="Conduct interactive executive operating meeting")
    subparsers.add_parser("telemetry", help="Inspect host and desktop robot status")
    subparsers.add_parser("causality", help="View verified business outcome causality summary")

    council_parser = subparsers.add_parser("council", help="Convene Executive Council challenge loop")
    council_parser.add_argument("proposal", type=str, help="Strategic proposal to review")

    chat_parser = subparsers.add_parser("chat", help="Strategic command chat with AI CEO")
    chat_parser.add_argument("instruction", type=str, help="Strategic instruction for AI CEO")

    args = parser.parse_args()

    if args.command == "portfolio":
        cmd_portfolio()
    elif args.command == "briefing":
        cmd_briefing()
    elif args.command == "cycle":
        cmd_cycle()
    elif args.command == "council":
        cmd_council(args.proposal)
    elif args.command == "meeting":
        cmd_meeting()
    elif args.command == "telemetry":
        cmd_telemetry()
    elif args.command == "causality":
        cmd_causality()
    elif args.command == "chat":
        cmd_chat(args.instruction)
    else:
        cmd_portfolio()

if __name__ == "__main__":
    main()
