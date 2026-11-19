/**
 * URA / ZONATA — Apple-Grade Department Workspace
 * Single unified template for COO, CMO, CTO, CFO, CHRO, and Security.
 * Quiet • Spacious • Fast • Obvious
 */

(function() {
  'use strict';

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  const DEPARTMENT_DATA = {
    coo: {
      id: 'coo',
      name: 'COO',
      entity: 'coo',
      title: 'Chief Operating Officer',
      label: 'Operations & Execution',
      tint: 'rgba(0, 113, 227, 0.08)',
      borderColor: 'var(--accent)',
      status: 'All operations running smoothly. 14 processes in flight, 0 SLA breaches.',
      objective: 'Maintain 99.8% customer fulfillment SLA with under 15-minute turnaround',
      progress: 88,
      targetStr: 'Target: 99.8% SLA • 88% completed this month',
      kpis: [
        { label: 'SLA Adherence', value: '99.8%', note: 'Target: 99.5%', tone: 'green' },
        { label: 'Avg Turnaround', value: '14.2m', note: 'Down 2.4m vs last week', tone: 'green' },
        { label: 'Active Queue', value: '28 items', note: '4 priority tasks', tone: 'accent' },
        { label: 'Error Rate', value: '0.02%', note: 'Within tolerance', tone: 'neutral' }
      ],
      employees: [
        {
          id: 'emp_coo_1',
          name: 'Operations Supervisor',
          role: 'Workflow Orchestration',
          entity: 'coo',
          status: 'Working',
          sop: 'SOP-OPS-01: Order Ingestion & Routing',
          kra: 'Ensure 100% of incoming operational orders are routed without latency',
          agents: ['OpenHands Executor', 'Temporal Durable Agent']
        },
        {
          id: 'emp_coo_2',
          name: 'Logistics Coordinator',
          role: 'Fulfillment Tracking',
          entity: 'coo',
          status: 'Standby',
          sop: 'SOP-OPS-04: Inventory Reconciliation',
          kra: 'Maintain zero discrepancy between supplier feeds and local records',
          agents: ['Database Query Agent']
        },
        {
          id: 'emp_coo_3',
          name: 'Quality Analyst',
          role: 'Audit & Compliance',
          entity: 'coo',
          status: 'Working',
          sop: 'SOP-OPS-09: Post-Fulfillment Verification',
          kra: 'Verify complete delivery satisfaction and verify tamper-proof audit trails',
          agents: ['Ledger Audit Agent']
        }
      ],
      tasks: [
        {
          intent: 'Dispatched 42 delivery manifests',
          reason: 'Automated 11:00 AM dispatch batch processing.',
          state: 'done',
          result: '100% route optimization confirmed.',
          actorEntity: 'coo',
          actorName: 'Logistics Coordinator',
          timestamp: '18m ago',
          undoSeconds: 30
        },
        {
          intent: 'Synchronizing warehouse stock records',
          reason: 'High-frequency inventory delta received from suppliers.',
          state: 'working',
          result: 'Reconciled 1,240 SKUs across 2 fulfillment hubs.',
          actorEntity: 'coo',
          actorName: 'Operations Supervisor',
          timestamp: '3m ago'
        }
      ],
      approvals: [
        {
          id: 'app_coo_1',
          title: 'Authorize Overtime Shift Dispatch for Weekend Influx',
          actorEntity: 'coo',
          actorName: 'Operations Supervisor',
          riskLevel: 'Low',
          reason: 'Demand spikes expected Saturday morning. Routing auxiliary automated capacity.',
          worstCase: 'Minor compute credit consumption ($4.50).',
          alternative: 'Allow requests to queue with estimated 8-minute latency increase.'
        }
      ]
    },

    cmo: {
      id: 'cmo',
      name: 'CMO',
      entity: 'cmo',
      title: 'Chief Marketing Officer',
      label: 'Marketing, Growth & Revenue',
      tint: 'rgba(175, 82, 222, 0.08)',
      borderColor: 'var(--purple)',
      status: 'Active campaigns generating 4.2x ROAS across high-intent search.',
      objective: 'Acquire 600 verified customer bookings at sub-₹1,200 CAC',
      progress: 74,
      targetStr: 'Target: 600 Bookings • 74% completed this month',
      kpis: [
        { label: 'Monthly Leads', value: '480', note: '80% of monthly target', tone: 'accent' },
        { label: 'Blended CAC', value: '₹980', note: '₹220 below max budget', tone: 'green' },
        { label: 'ROAS', value: '4.2x', note: 'Top campaign: 5.8x', tone: 'green' },
        { label: 'Organic Traffic', value: '+34%', note: 'AI Search & SEO', tone: 'accent' }
      ],
      employees: [
        {
          id: 'emp_cmo_1',
          name: 'SEO & Visibility Specialist',
          role: 'Search & LLM Optimization',
          entity: 'cmo',
          status: 'Working',
          sop: 'SOP-MKT-02: AI Answer Engine Optimization',
          kra: 'Attain #1 citation rank in Perplexity & Google AI Overviews for primary keywords',
          agents: ['Perplexity Search Agent', 'Content Crawler']
        },
        {
          id: 'emp_cmo_2',
          name: 'Growth Campaign Manager',
          role: 'Ad Optimization & Bidding',
          entity: 'cmo',
          status: 'Working',
          sop: 'SOP-MKT-05: Real-Time Bid Scaling',
          kra: 'Maintain ROAS > 4.0x while pacing target ad spend dynamically',
          agents: ['Google Ads MCP', 'Meta Ads Agent']
        },
        {
          id: 'emp_cmo_3',
          name: 'Inbound Sales Lead Analyst',
          role: 'Lead Qualification',
          entity: 'cmo',
          status: 'Standby',
          sop: 'SOP-SALES-01: Inbound Lead Triage',
          kra: 'Contact high-intent leads within 60 seconds with hyper-personalized quotes',
          agents: ['WhatsApp CRM Agent']
        }
      ],
      tasks: [
        {
          intent: 'Optimized Q4 luxury search keywords',
          reason: 'Surging demand in European luxury feeder markets.',
          state: 'done',
          result: 'Expanded daily inquiries by +24%.',
          actorEntity: 'cmo',
          actorName: 'SEO Specialist',
          timestamp: '45m ago',
          undoSeconds: 60
        },
        {
          intent: 'Generated 18 custom sales email drafts',
          reason: 'Incoming inquiries from enterprise group booking form.',
          state: 'working',
          result: 'Drafts ready for account executive review.',
          actorEntity: 'cmo',
          actorName: 'Inbound Sales Lead Analyst',
          timestamp: '10m ago'
        }
      ],
      approvals: [
        {
          id: 'app_cmo_1',
          title: 'Q4 DACH Marketing Campaign Budget',
          actorEntity: 'cmo',
          actorName: 'AI CMO',
          riskLevel: 'Medium',
          reason: 'Allocate ₹2,50,000 to capture surging luxury travel search queries in German-speaking territories.',
          worstCase: 'Ad spend underperforms ROAS benchmark by up to ₹40,000 before killswitch triggers.',
          alternative: 'Pilot with ₹75,000 micro-budget on high-intent search only.'
        }
      ]
    },

    cto: {
      id: 'cto',
      name: 'CTO',
      entity: 'cto',
      title: 'Chief Technology Officer',
      label: 'Technology, Systems & MCP',
      tint: 'rgba(255, 149, 0, 0.08)',
      borderColor: 'var(--orange)',
      status: 'Core engines healthy. 6 MCP servers connected, 0 failed builds.',
      objective: 'Zero-downtime deployment of autonomous booking engine v2.4',
      progress: 92,
      targetStr: 'Target: v2.4 Production Rollout • 92% completed',
      kpis: [
        { label: 'Platform Uptime', value: '99.98%', note: 'Last incident: 42d ago', tone: 'green' },
        { label: 'P95 Latency', value: '46ms', note: 'Edge cached', tone: 'green' },
        { label: 'Active MCPs', value: '8 Connected', note: 'Database, Search, Sandbox', tone: 'accent' },
        { label: 'Build Success', value: '100%', note: '14 consecutive passes', tone: 'green' }
      ],
      employees: [
        {
          id: 'emp_cto_1',
          name: 'Systems Architect',
          role: 'Infrastructure & Sandboxing',
          entity: 'cto',
          status: 'Working',
          sop: 'SOP-TECH-01: Sandboxed Execution Governance',
          kra: 'Ensure 100% container isolation and strict network egress policies',
          agents: ['OpenHands Code Engine', 'Docker Sandbox Agent']
        },
        {
          id: 'emp_cto_2',
          name: 'API & MCP Engineer',
          role: 'Protocol & Tool Integration',
          entity: 'cto',
          status: 'Standby',
          sop: 'SOP-TECH-04: Tool Discovery & Auth Gateway',
          kra: 'Enforce schema verification and token encryption across MCP tools',
          agents: ['Nango Integrations Agent', 'MCP Protocol Inspector']
        },
        {
          id: 'emp_cto_3',
          name: 'Site Reliability Specialist',
          role: 'Observability & Healing',
          entity: 'cto',
          status: 'Working',
          sop: 'SOP-TECH-08: Autonomous Health Remediation',
          kra: 'Detect and heal microservice degradation before latency exceeds 100ms',
          agents: ['Telemetry Monitor', 'Log Watchdog Agent']
        }
      ],
      tasks: [
        {
          intent: 'Verified database connection pool elasticity',
          reason: 'High traffic peak forecast during promotional launch.',
          state: 'done',
          result: 'Connection limit scaled safely to 50 active sockets.',
          actorEntity: 'cto',
          actorName: 'Systems Architect',
          timestamp: '1h ago'
        },
        {
          intent: 'Compiled edge worker cache invalidation bundle',
          reason: 'New pricing algorithm activated by CMO.',
          state: 'done',
          result: 'Cache purged across 24 edge points in 120ms.',
          actorEntity: 'cto',
          actorName: 'API & MCP Engineer',
          timestamp: '2h ago'
        }
      ],
      approvals: [
        {
          id: 'app_cto_1',
          title: 'Upgrade Database Connection Pool',
          actorEntity: 'cto',
          actorName: 'AI CTO',
          riskLevel: 'Low',
          reason: 'Expand connection concurrency from 20 to 50 sockets to absorb inbound webhook traffic.',
          worstCase: 'Negligible (zero downtime rolling restart).',
          alternative: 'Maintain existing pool with request queuing.'
        }
      ]
    },

    cfo: {
      id: 'cfo',
      name: 'CFO',
      entity: 'cfo',
      title: 'Chief Financial Officer',
      label: 'Finance, Treasury & Audit',
      tint: 'rgba(52, 199, 89, 0.08)',
      borderColor: 'var(--green)',
      status: 'Double-entry ledger balanced. Cryptographic audit trail 100% verified.',
      objective: 'Achieve ₹5,00,000 net monthly profit with >28% operating margin',
      progress: 85,
      targetStr: 'Target: ₹5.00L Net Profit • 85% completed this month',
      kpis: [
        { label: 'Net Profit', value: '₹4,28,500', note: 'Target: ₹5,00,000', tone: 'green' },
        { label: 'Gross Revenue', value: '₹14,80,000', note: '+18% MoM', tone: 'green' },
        { label: 'Operating Margin', value: '29.2%', note: 'Target: 28.0%', tone: 'green' },
        { label: 'Cash Runway', value: '18.4 Mo', note: 'Treasury reserve safe', tone: 'accent' }
      ],
      employees: [
        {
          id: 'emp_cfo_1',
          name: 'Financial Controller',
          role: 'Audit & Compliance',
          entity: 'cfo',
          status: 'Working',
          sop: 'SOP-FIN-01: Double-Entry Cryptographic Verification',
          kra: 'Ensure every rupee has an immutable cryptographic hash in the general ledger',
          agents: ['General Ledger Agent', 'Audit Hasher']
        },
        {
          id: 'emp_cfo_2',
          name: 'Treasury Specialist',
          role: 'Cash Flow & Accounts',
          entity: 'cfo',
          status: 'Standby',
          sop: 'SOP-FIN-03: Real-Time Cash Rebalancing',
          kra: 'Optimize overnight sweep accounts and manage operational disbursements',
          agents: ['Bank Reconciliation Agent']
        },
        {
          id: 'emp_cfo_3',
          name: 'Tax & Regulatory Analyst',
          role: 'GST & Compliance Filings',
          entity: 'cfo',
          status: 'Standby',
          sop: 'SOP-FIN-07: Tax Calculation & Accrual',
          kra: 'Automate tax withholding and quarterly compliance calculations',
          agents: ['Statutory Engine Agent']
        }
      ],
      tasks: [
        {
          intent: 'Reconciled 142 bank transactions',
          reason: 'Daily closing reconciliation schedule.',
          state: 'done',
          result: '0 discrepancy detected across 4 merchant accounts.',
          actorEntity: 'cfo',
          actorName: 'Treasury Specialist',
          timestamp: '30m ago',
          undoSeconds: 60
        },
        {
          intent: 'Generated real-time profit & loss statement',
          reason: 'Executive end-of-week reporting cycle.',
          state: 'done',
          result: 'Ledger root hash recorded to cryptographic proof store.',
          actorEntity: 'cfo',
          actorName: 'Financial Controller',
          timestamp: '1h ago'
        }
      ],
      approvals: [
        {
          id: 'app_cfo_1',
          title: 'Approve Vendor Payout Batch #1042',
          actorEntity: 'cfo',
          actorName: 'Financial Controller',
          riskLevel: 'Medium',
          reason: 'Disburse ₹1,12,000 across verified SaaS providers and infrastructure vendors.',
          worstCase: 'Immediate cash debit from operating checking account.',
          alternative: 'Stagger payouts across 2 weeks to preserve liquidity.'
        }
      ]
    },

    chro: {
      id: 'chro',
      name: 'CHRO',
      entity: 'chro',
      title: 'Chief Human Resources Officer',
      label: 'AI Workforce, SOPs & Governance',
      tint: 'rgba(88, 86, 214, 0.08)',
      borderColor: 'var(--indigo)',
      status: '14 AI employees fully certified on latest Standard Operating Procedures.',
      objective: 'Enforce 100% SOP compliance and expand agent tool library safely',
      progress: 95,
      targetStr: 'Target: 100% Certification • 95% completed',
      kpis: [
        { label: 'Certified Employees', value: '14 / 14', note: 'All roles staffed', tone: 'green' },
        { label: 'Active Agent Tools', value: '26 Tools', note: 'Delegated execution tools', tone: 'accent' },
        { label: 'SOP Compliance', value: '100%', note: '0 policy deviations', tone: 'green' },
        { label: 'Workforce Efficiency', value: '94.2%', note: 'High autonomous completion', tone: 'green' }
      ],
      employees: [
        {
          id: 'emp_chro_1',
          name: 'Talent Acquisition Director',
          role: 'Role Architect & Prompt Engineer',
          entity: 'chro',
          status: 'Working',
          sop: 'SOP-HR-01: Employee Role Provisioning',
          kra: 'Synthesize optimal prompts and boundary safeguards for new positions',
          agents: ['Persona Calibration Agent']
        },
        {
          id: 'emp_chro_2',
          name: 'Performance & SOP Evaluator',
          role: 'KRA/KPI Continuous Review',
          entity: 'chro',
          status: 'Working',
          sop: 'SOP-HR-03: Autonomous Employee Review',
          kra: 'Evaluate weekly employee action logs against stated KPIs',
          agents: ['Performance Analysis Agent']
        },
        {
          id: 'emp_chro_3',
          name: 'Agent Safety Coordinator',
          role: 'Tool Isolation & Permission Enforcer',
          entity: 'chro',
          status: 'Standby',
          sop: 'SOP-HR-08: Invariant Rule Enforcement',
          kra: 'Strictly enforce: Employees use agents; agents never use employees',
          agents: ['Constitutional Boundary Agent']
        }
      ],
      tasks: [
        {
          intent: 'Audited AI employee authority boundaries',
          reason: 'Ensured no agent tool has reverse execution authority over an employee.',
          state: 'done',
          result: '100% compliance: Employees operate agents; agents never operate employees.',
          actorEntity: 'chro',
          actorName: 'Agent Safety Coordinator',
          timestamp: '2h ago'
        },
        {
          intent: 'Refreshed SOP-MKT-02 with latest AI Answer Engine protocols',
          reason: 'Updated search algorithm standards published.',
          state: 'done',
          result: 'SEO Specialist auto-certified on new SOP version 2.1.',
          actorEntity: 'chro',
          actorName: 'Performance & SOP Evaluator',
          timestamp: '3h ago'
        }
      ],
      approvals: [
        {
          id: 'app_chro_1',
          title: 'Provision Autonomous Research Analyst for DACH Market',
          actorEntity: 'chro',
          actorName: 'Talent Acquisition Director',
          riskLevel: 'Low',
          reason: 'Hire specialist AI employee with SOP-RES-04 to accelerate German competitor mapping.',
          worstCase: 'Minor token consumption overhead ($12/mo).',
          alternative: 'Assign research tasks as ad-hoc jobs to existing SEO specialist.'
        }
      ]
    },

    security: {
      id: 'security',
      name: 'Security',
      entity: 'security',
      title: 'Chief Information Security Officer',
      label: 'Cyber Defense, DLP & Cryptography',
      tint: 'rgba(255, 59, 48, 0.08)',
      borderColor: 'var(--red)',
      status: '13 defense rings active. 0 data leaks, 100% constitutional compliance.',
      objective: 'Maintain flawless sovereign data privacy & tamper-proof audit trail',
      progress: 99,
      targetStr: 'Target: Zero Breach Guarantee • 99.4% active score',
      kpis: [
        { label: 'Security Score', value: '99.4%', note: 'Enterprise Fortress Level', tone: 'green' },
        { label: 'Active Defense Rings', value: '13 / 13', note: 'DLP, Sandbox, Hashes', tone: 'green' },
        { label: 'Data Leakage', value: '0 bytes', note: 'Strict egress isolation', tone: 'green' },
        { label: 'Ledger Audit', value: 'Verified', note: 'SHA-256 root valid', tone: 'green' }
      ],
      employees: [
        {
          id: 'emp_sec_1',
          name: 'Constitutional Policy Enforcer',
          role: 'Rule Adherence & Gateway',
          entity: 'security',
          status: 'Working',
          sop: 'SOP-SEC-01: Constitutional Boundary Check',
          kra: 'Intercept all external API dispatches for constitutional compliance',
          agents: ['Policy Evaluator Agent']
        },
        {
          id: 'emp_sec_2',
          name: 'Data Loss Prevention Sentinel',
          role: 'Prompt & Output Sanitization',
          entity: 'security',
          status: 'Working',
          sop: 'SOP-SEC-04: Outbound Egress Screening',
          kra: 'Ensure 0 customer PII or API credentials escape isolated environment',
          agents: ['DLP Regex & Embedding Agent']
        },
        {
          id: 'emp_sec_3',
          name: 'Cryptographic Ledger Custodian',
          role: 'Merkle Hash Consistency',
          entity: 'security',
          status: 'Standby',
          sop: 'SOP-SEC-09: Tamper-Evident Ledger Audit',
          kra: 'Recalculate SHA-256 state hash hourly and log to immutable ledger',
          agents: ['Merkle Tree Hash Agent']
        }
      ],
      tasks: [
        {
          intent: 'Verified SHA-256 cryptographic audit chain',
          reason: 'Hourly sovereign data integrity sweep.',
          state: 'done',
          result: '12,480 ledger events cryptographically verified.',
          actorEntity: 'security',
          actorName: 'Ledger Custodian',
          timestamp: '15m ago'
        },
        {
          intent: 'Screened outbound API payload for PII',
          reason: 'Nango integration webhook sync.',
          state: 'done',
          result: 'Clean: 0 PII or sensitive tenant credentials in payload.',
          actorEntity: 'security',
          actorName: 'DLP Sentinel',
          timestamp: '40m ago'
        }
      ],
      approvals: [
        {
          id: 'app_sec_1',
          title: 'Rotate Master Cryptographic Key Ring',
          actorEntity: 'security',
          actorName: 'Ledger Custodian',
          riskLevel: 'High',
          reason: 'Periodic 90-day sovereign key rotation for tenant encryption keys.',
          worstCase: 'Brief re-encryption lock (1.5 seconds) on historical cold archives.',
          alternative: 'Postpone rotation by 30 days.'
        }
      ]
    }
  };

  class DepartmentWorkspaceController {
    constructor() {
      this.currentDeptId = 'cmo';
      this.containerId = 'view-overview';
      this.previousHtml = null;
    }

    render(containerOrId, deptId = 'cmo') {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;

      if (!container) return;

      const dept = DEPARTMENT_DATA[deptId.toLowerCase()] || DEPARTMENT_DATA['cmo'];
      this.currentDeptId = dept.id;

      container.innerHTML = `
        <div class="department-workspace-view" style="max-width:1120px; margin:0 auto; display:flex; flex-direction:column; gap:32px;">

          <!-- TOP BAR: BACK & BREADCRUMB -->
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <button class="btn-apple btn-apple-plain spring-press"
                    onclick="DepartmentWorkspace.close()"
                    style="padding:6px 10px; font-size:14px; color:var(--label-2);">
              ${window.Icon ? window.Icon({ name: 'arrow-left', size: 16 }) : '←'}
              <span>All Departments</span>
            </button>

            <div style="display:flex; align-items:center; gap:8px;">
              <span class="chip-apple chip-green" style="font-size:12px;">Active & Healthy</span>
              <button class="btn-apple btn-apple-secondary spring-press"
                      onclick="DepartmentWorkspace.askExecutive('${dept.id}')"
                      style="font-size:13px; padding:6px 14px;">
                Ask ${escapeHtml(dept.name)}
              </button>
            </div>
          </div>

          <!-- 1. HEADER HERO WITH TINT -->
          <div class="card-apple"
               style="padding:28px 32px; background:linear-gradient(135deg, ${dept.tint} 0%, var(--surface) 100%); border-color:${dept.borderColor}33;">
            <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
              ${window.AppTile ? window.AppTile({ entity: dept.entity, size: 64 }) : ''}
              <div style="flex:1; min-width:240px;">
                <div style="display:flex; align-items:center; gap:10px;">
                  <h1 class="t-large-title" style="margin:0;">${escapeHtml(dept.label)}</h1>
                  <span class="chip-apple chip-neutral" style="font-size:12px; font-weight:600;">${escapeHtml(dept.name)}</span>
                </div>
                <p class="t-callout" style="color:var(--label-2); margin-top:6px; line-height:1.4;">
                  ${escapeHtml(dept.status)}
                </p>
              </div>
            </div>

            <!-- Objective Progress Bar -->
            <div style="margin-top:24px; padding-top:18px; border-top:0.5px solid var(--separator);">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3);">Monthly Objective</span>
                <span class="t-footnote" style="color:var(--label); font-weight:600;">${escapeHtml(dept.targetStr)}</span>
              </div>
              ${window.UI && window.UI.ProgressBar ? window.UI.ProgressBar({ value: dept.progress, max: 100, tone: 'accent' }) : `
                <div style="height:6px; background:var(--surface-3); border-radius:3px; overflow:hidden;">
                  <div style="height:100%; width:${dept.progress}%; background:var(--accent);"></div>
                </div>
              `}
              <div class="t-body" style="font-size:13.5px; color:var(--label-2); margin-top:8px;">
                <strong>Key Result:</strong> ${escapeHtml(dept.objective)}
              </div>
            </div>
          </div>

          <!-- 2. DEPARTMENT OBJECTIVES & KPIS -->
          <section>
            <div style="margin-bottom:12px;">
              <h2 class="t-title-2">Department KPIs</h2>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px;">
              ${dept.kpis.map(kpi => `
                <div class="card-apple" style="padding:18px;">
                  <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">${escapeHtml(kpi.label)}</span>
                  <div class="t-title-1 tabular-nums" style="margin-top:4px;">${escapeHtml(kpi.value)}</div>
                  <div class="t-footnote" style="color:var(--${kpi.tone === 'neutral' ? 'label-2' : kpi.tone}); margin-top:4px;">
                    ${escapeHtml(kpi.note)}
                  </div>
                </div>
              `).join('')}
            </div>
          </section>

          <!-- 3. WORK IN PROGRESS (Running • Needs You • Done) -->
          <section>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <div>
                <h2 class="t-title-2">Work in Progress</h2>
                <p class="t-footnote" style="margin-top:2px;">Tasks executing right now under constitutional supervision.</p>
              </div>
              <span class="t-caption" style="color:var(--label-3);">${dept.tasks.length + dept.approvals.length} active items</span>
            </div>

            <!-- Approvals if any -->
            ${dept.approvals && dept.approvals.length > 0 ? `
              <div style="margin-bottom:18px;">
                <div class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--orange); margin-bottom:8px;">
                  Pending Approvals (${dept.approvals.length})
                </div>
                ${dept.approvals.map(a => window.ApprovalCard ? window.ApprovalCard(a) : '').join('')}
              </div>
            ` : ''}

            <!-- Active / Completed Tasks -->
            <div>
              <div class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3); margin-bottom:8px;">
                Autonomous Action Log
              </div>
              ${dept.tasks.map(t => window.ActionCard ? window.ActionCard(t) : '').join('')}
            </div>
          </section>

          <!-- 4. DEPARTMENT AI EMPLOYEES (TEAM) -->
          <section>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <div>
                <h2 class="t-title-2">Department AI Workforce</h2>
                <p class="t-footnote" style="margin-top:2px;">
                  AI Employees hold positions and own SOPs. They operate specialized Agent tools.
                </p>
              </div>
              <span class="chip-apple chip-neutral">${dept.employees.length} Certified Employees</span>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:16px;">
              ${dept.employees.map(emp => `
                <div class="card-apple card-apple-interactive hover-lift"
                     onclick="DepartmentWorkspace.inspectEmployee('${dept.id}', '${emp.id}')"
                     style="padding:18px; cursor:pointer;">
                  <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div style="display:flex; align-items:center; gap:12px;">
                      ${window.AppTile ? window.AppTile({ entity: emp.entity, size: 40 }) : ''}
                      <div>
                        <div class="t-headline" style="font-size:15px;">${escapeHtml(emp.name)}</div>
                        <div class="t-caption" style="color:var(--label-2);">${escapeHtml(emp.role)}</div>
                      </div>
                    </div>
                    <span class="chip-apple chip-green" style="font-size:11px; padding:2px 8px;">${escapeHtml(emp.status)}</span>
                  </div>

                  <div style="margin-top:12px; padding-top:10px; border-top:0.5px solid var(--separator);">
                    <div class="t-caption" style="color:var(--label-3); font-weight:600;">Assigned SOP</div>
                    <div class="t-footnote" style="color:var(--label); margin-top:2px; font-family:var(--font-mono); font-size:12px;">
                      ${escapeHtml(emp.sop)}
                    </div>
                  </div>

                  <div style="margin-top:10px;">
                    <div class="t-caption" style="color:var(--label-3); font-weight:600; margin-bottom:4px;">Authorized Agent Tools</div>
                    <div style="display:flex; flex-wrap:wrap; gap:4px;">
                      ${emp.agents.map(ag => `<span class="chip-apple chip-neutral" style="font-size:11px; padding:2px 6px;">${escapeHtml(ag)}</span>`).join('')}
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
          </section>

          <!-- 5. DEPARTMENT SPECIFIC EXTRA VISUALIZATION -->
          ${this.renderDepartmentExtra(dept)}

        </div>
      `;
    }

    renderDepartmentExtra(dept) {
      if (dept.id === 'cmo') {
        return `
          <section class="card-apple" style="padding:24px;">
            <h3 class="t-title-3" style="margin-bottom:4px;">Lead & Revenue Conversion Funnel</h3>
            <p class="t-footnote" style="margin-bottom:16px;">Live customer journey tracking from search discovery to booked revenue.</p>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:12px; text-align:center;">
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">1. Web & AI Visits</div>
                <div class="t-title-2" style="margin-top:4px;">24,500</div>
                <span class="t-footnote" style="color:var(--green);">+14% Organic</span>
              </div>
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">2. Inquiries</div>
                <div class="t-title-2" style="margin-top:4px;">1,840</div>
                <span class="t-footnote" style="color:var(--accent);">7.5% Opt-in</span>
              </div>
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">3. Qualified Leads</div>
                <div class="t-title-2" style="margin-top:4px;">480</div>
                <span class="t-footnote" style="color:var(--green);">High Intent</span>
              </div>
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">4. Bookings</div>
                <div class="t-title-2" style="margin-top:4px;">142</div>
                <span class="t-footnote" style="color:var(--accent);">4.6% Conversion</span>
              </div>
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">5. Booked Value</div>
                <div class="t-title-2" style="margin-top:4px; color:var(--green);">₹14.8L</div>
                <span class="t-footnote" style="color:var(--label-2);">₹1.04L ADR</span>
              </div>
            </div>
          </section>
        `;
      }

      if (dept.id === 'cto') {
        return `
          <section class="card-apple" style="padding:24px;">
            <h3 class="t-title-3" style="margin-bottom:4px;">Connected MCP Tools & Sandboxes</h3>
            <p class="t-footnote" style="margin-bottom:16px;">Model Context Protocol servers providing safe execution boundaries.</p>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
              <div style="padding:14px; background:var(--surface-2); border-radius:var(--r-md); border:0.5px solid var(--separator);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span class="t-headline" style="font-size:14px;">Postgres MCP</span>
                  <span class="status-dot-active"></span>
                </div>
                <div class="t-caption" style="color:var(--label-2); margin-top:4px;">Direct query isolation, 0 pool errors</div>
              </div>
              <div style="padding:14px; background:var(--surface-2); border-radius:var(--r-md); border:0.5px solid var(--separator);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span class="t-headline" style="font-size:14px;">OpenHands Engine</span>
                  <span class="status-dot-active"></span>
                </div>
                <div class="t-caption" style="color:var(--label-2); margin-top:4px;">Docker sandbox active, 0 egress violations</div>
              </div>
              <div style="padding:14px; background:var(--surface-2); border-radius:var(--r-md); border:0.5px solid var(--separator);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span class="t-headline" style="font-size:14px;">Browser Automation MCP</span>
                  <span class="status-dot-active"></span>
                </div>
                <div class="t-caption" style="color:var(--label-2); margin-top:4px;">Headless Chromium cluster, DOM sandbox</div>
              </div>
            </div>
          </section>
        `;
      }

      if (dept.id === 'cfo') {
        return `
          <section class="card-apple" style="padding:24px;">
            <h3 class="t-title-3" style="margin-bottom:4px;">Double-Entry Ledger Integrity</h3>
            <p class="t-footnote" style="margin-bottom:16px;">Real-time balance sheet backed by immutable cryptographic proofs.</p>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px;">
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">Gross Inflow</div>
                <div class="t-title-2 tabular-nums" style="margin-top:4px; color:var(--green);">₹14,80,000</div>
              </div>
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">Operating Expenses</div>
                <div class="t-title-2 tabular-nums" style="margin-top:4px; color:var(--red);">₹10,51,500</div>
              </div>
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">Net Operating Profit</div>
                <div class="t-title-2 tabular-nums" style="margin-top:4px; color:var(--green);">₹4,28,500</div>
              </div>
              <div style="background:var(--surface-2); padding:14px; border-radius:var(--r-md);">
                <div class="t-caption" style="color:var(--label-3);">SHA-256 Ledger State</div>
                <div class="t-caption" style="font-family:var(--font-mono); margin-top:6px; color:var(--label-2);">sha256:4a88...c91e</div>
              </div>
            </div>
          </section>
        `;
      }

      if (dept.id === 'chro') {
        return `
          <section class="card-apple" style="padding:24px; border-left:4px solid var(--accent);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <h3 class="t-title-3">Workforce Architecture Invariant</h3>
              <span class="chip-apple chip-green">Enforced by Constitution</span>
            </div>
            <p class="t-body" style="color:var(--label); font-weight:500; line-height:1.5;">
              <strong>Immutable Rule:</strong> AI Employees hold corporate roles, own SOPs, and operate AI Agents.
              AI Agents are specialized tools and can <em>never</em> control or supervise AI Employees.
            </p>
          </section>
        `;
      }

      return '';
    }

    open(deptId = 'cmo') {
      const container = document.getElementById(this.containerId);
      if (!container) return;

      if (!this.previousHtml) {
        this.previousHtml = container.innerHTML;
      }

      this.render(container, deptId);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    close() {
      const container = document.getElementById(this.containerId);
      if (!container) return;

      if (this.previousHtml) {
        container.innerHTML = this.previousHtml;
        this.previousHtml = null;
      } else if (window.OverviewWorkspace) {
        window.OverviewWorkspace.render();
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    inspectEmployee(deptId, empId) {
      const dept = DEPARTMENT_DATA[deptId.toLowerCase()];
      if (!dept) return;
      const emp = dept.employees.find(e => e.id === empId);
      if (!emp) return;

      if (!window.Inspector || !window.Inspector.open) return;

      const content = `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <div style="display:flex; align-items:center; gap:14px;">
            ${window.AppTile ? window.AppTile({ entity: emp.entity, size: 48 }) : ''}
            <div>
              <h4 class="t-title-3" style="margin:0;">${escapeHtml(emp.name)}</h4>
              <p class="t-caption" style="color:var(--label-2); margin-top:2px;">${escapeHtml(emp.role)} • ${escapeHtml(dept.name)}</p>
            </div>
          </div>

          <div style="background:var(--surface-2); padding:16px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
            <div class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3);">Standard Operating Procedure</div>
            <div class="t-headline" style="font-size:14px; margin-top:4px;">${escapeHtml(emp.sop)}</div>
            <p class="t-footnote" style="color:var(--label-2); margin-top:6px; line-height:1.4;">
              Certified by CHRO. Governed by company constitutional boundaries and automated Ralph loop quality gating.
            </p>
          </div>

          <div>
            <div class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3); margin-bottom:6px;">Key Result Area (KRA)</div>
            <p class="t-body" style="font-size:13.5px; line-height:1.5; color:var(--label);">
              ${escapeHtml(emp.kra)}
            </p>
          </div>

          <div>
            <div class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3); margin-bottom:8px;">Authorized Execution Agents</div>
            <div style="display:flex; flex-direction:column; gap:6px;">
              ${emp.agents.map(ag => `
                <div style="display:flex; justify-content:space-between; align-items:center; background:var(--surface); padding:8px 12px; border-radius:var(--r-sm); border:0.5px solid var(--separator);">
                  <span class="t-footnote" style="font-weight:500;">${escapeHtml(ag)}</span>
                  <span class="chip-apple chip-green" style="font-size:11px; padding:2px 6px;">Permitted</span>
                </div>
              `).join('')}
            </div>
          </div>

          <div style="padding-top:12px; border-top:0.5px solid var(--separator); display:flex; justify-content:flex-end;">
            <button class="btn-apple btn-apple-primary spring-press"
                    onclick="UI.showToast('Connecting direct session with ${escapeHtml(emp.name)}...', 'info'); Inspector.close();"
                    style="font-size:13px; padding:8px 16px;">
              Direct Message Employee
            </button>
          </div>
        </div>
      `;

      window.Inspector.open(emp.name, content);
    }

    askExecutive(deptId) {
      const dept = DEPARTMENT_DATA[deptId.toLowerCase()] || DEPARTMENT_DATA['cmo'];
      if (!window.UI || !window.UI.openModal) return;

      window.UI.openModal(
        `Consult ${escapeHtml(dept.title)}`,
        `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:flex; align-items:center; gap:12px;">
              ${window.AppTile ? window.AppTile({ entity: dept.entity, size: 40 }) : ''}
              <div>
                <div class="t-headline" style="font-size:15px;">Executive Consultation</div>
                <div class="t-caption" style="color:var(--label-2);">${escapeHtml(dept.name)} Department Strategy</div>
              </div>
            </div>

            <p class="t-body" style="font-size:13.5px; color:var(--label-2); line-height:1.45;">
              Send a high-priority strategic directive or query to the ${escapeHtml(dept.name)} AI executive.
            </p>

            <textarea id="execDirectiveInput" class="input-apple" rows="4"
                      placeholder="e.g. Focus ad spend on luxury suites with minimum 5-night stay..."
                      style="width:100%; box-sizing:border-box; font-size:14px; padding:12px;"></textarea>

            <div style="display:flex; justify-content:flex-end; gap:10px;">
              <button class="btn-apple btn-apple-secondary" onclick="UI.closeModal()">Cancel</button>
              <button class="btn-apple btn-apple-primary" onclick="
                const val = document.getElementById('execDirectiveInput').value;
                if(val) {
                  UI.showToast('Directive dispatched to ${escapeHtml(dept.name)} executive.', 'success');
                  UI.closeModal();
                } else {
                  UI.showToast('Please type a directive.', 'error');
                }
              ">
                Send Directive
              </button>
            </div>
          </div>
        `
      );
    }
  }

  window.DepartmentWorkspace = new DepartmentWorkspaceController();
})();
