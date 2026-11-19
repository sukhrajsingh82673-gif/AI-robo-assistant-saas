/**
 * URA / ZONATA — Apple-Grade AI Workforce Directory & Governance Board
 * Quiet • Spacious • Fast • Obvious
 * Enforces Constitutional Invariant: Employees use Agents; Agents NEVER control Employees.
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

  const WORKFORCE_ROSTER = [
    {
      id: 'emp_ceo',
      name: 'AI CEO',
      role: 'Chief Executive Officer',
      dept: 'LEADERSHIP',
      deptLabel: 'Executive Leadership',
      entity: 'ceo',
      status: 'Active',
      sop: 'SOP-EXEC-01: Sovereign Enterprise Governance',
      kra: 'Overall company capital efficiency, strategic execution, and owner alignment',
      agents: ['Perplexity Research Agent', 'Corporate Brief Synthesizer'],
      perfRating: '99.4%',
      tasksCompleted: 428
    },
    {
      id: 'emp_coo',
      name: 'AI COO',
      role: 'Chief Operating Officer',
      dept: 'OPERATIONS',
      deptLabel: 'Operations',
      entity: 'coo',
      status: 'Active',
      sop: 'SOP-OPS-01: End-to-End Operational Execution',
      kra: 'Maintain 99.8% customer order fulfillment SLA and workflow throughput',
      agents: ['Temporal Durable Agent', 'Process Queue Optimizer'],
      perfRating: '99.8%',
      tasksCompleted: 1240
    },
    {
      id: 'emp_cmo',
      name: 'AI CMO',
      role: 'Chief Marketing Officer',
      dept: 'MARKETING',
      deptLabel: 'Marketing & Sales',
      entity: 'cmo',
      status: 'Active',
      sop: 'SOP-MKT-01: Omnichannel Growth & Acquisition Strategy',
      kra: 'Deliver minimum 4.0x ROAS and expand brand citation across AI search',
      agents: ['Google Ads MCP', 'Meta Ads Agent', 'Content Crawler'],
      perfRating: '98.6%',
      tasksCompleted: 890
    },
    {
      id: 'emp_cto',
      name: 'AI CTO',
      role: 'Chief Technology Officer',
      dept: 'TECHNOLOGY',
      deptLabel: 'Technology & Systems',
      entity: 'cto',
      status: 'Active',
      sop: 'SOP-TECH-01: Sandboxed Architecture & Tool Protocols',
      kra: 'Ensure 99.98% platform uptime, zero build regressions, and MCP tool health',
      agents: ['OpenHands Code Engine', 'Docker Sandbox Agent', 'MCP Protocol Inspector'],
      perfRating: '99.9%',
      tasksCompleted: 1540
    },
    {
      id: 'emp_cfo',
      name: 'AI CFO',
      role: 'Chief Financial Officer',
      dept: 'FINANCE',
      deptLabel: 'Finance & Treasury',
      entity: 'cfo',
      status: 'Active',
      sop: 'SOP-FIN-01: Double-Entry Cryptographic General Ledger',
      kra: 'Maintain 100% audited financial accuracy and cash runway > 18 months',
      agents: ['General Ledger Agent', 'Audit Hasher', 'Reconciliation Agent'],
      perfRating: '100%',
      tasksCompleted: 710
    },
    {
      id: 'emp_chro',
      name: 'AI CHRO',
      role: 'Chief Human Resources Officer',
      dept: 'LEADERSHIP',
      deptLabel: 'Workforce Governance',
      entity: 'chro',
      status: 'Active',
      sop: 'SOP-HR-01: AI Workforce Provisioning & Governance',
      kra: 'Enforce SOP certification, employee-agent hierarchy, and role calibration',
      agents: ['Role Provisioner Agent', 'Constitutional Boundary Auditor'],
      perfRating: '99.5%',
      tasksCompleted: 340
    },
    {
      id: 'emp_sec',
      name: 'AI CISO',
      role: 'Chief Information Security Officer',
      dept: 'SECURITY',
      deptLabel: 'Cyber Defense',
      entity: 'security',
      status: 'Active',
      sop: 'SOP-SEC-01: 13-Ring Defense & Data Loss Prevention',
      kra: 'Zero data leakage, continuous DLP scanning, and hourly SHA-256 chain verification',
      agents: ['DLP Regex & Embedding Agent', 'Merkle Tree Hash Agent'],
      perfRating: '100%',
      tasksCompleted: 3100
    },
    {
      id: 'emp_ops_sup',
      name: 'Operations Supervisor',
      role: 'Workflow Orchestration Specialist',
      dept: 'OPERATIONS',
      deptLabel: 'Operations',
      entity: 'coo',
      status: 'In Flight',
      sop: 'SOP-OPS-02: Order Ingestion & Routing',
      kra: 'Route inbound dispatch manifests in under 60 seconds',
      agents: ['OpenHands Executor', 'Temporal Durable Agent'],
      perfRating: '99.1%',
      tasksCompleted: 580
    },
    {
      id: 'emp_ops_log',
      name: 'Logistics Coordinator',
      role: 'Inventory Reconciliation Specialist',
      dept: 'OPERATIONS',
      deptLabel: 'Operations',
      entity: 'coo',
      status: 'Standby',
      sop: 'SOP-OPS-04: Multi-Hub Inventory Sync',
      kra: 'Zero variance between local stock database and supplier feeds',
      agents: ['Database Query Agent'],
      perfRating: '98.9%',
      tasksCompleted: 320
    },
    {
      id: 'emp_mkt_seo',
      name: 'SEO & Answer Specialist',
      role: 'AI Search Optimization Analyst',
      dept: 'MARKETING',
      deptLabel: 'Marketing & Sales',
      entity: 'cmo',
      status: 'In Flight',
      sop: 'SOP-MKT-02: AI Answer Engine Optimization',
      kra: 'Top-3 citation rank in Perplexity, Claude & Google AI Overviews',
      agents: ['Perplexity Research Agent', 'Content Crawler'],
      perfRating: '97.8%',
      tasksCompleted: 450
    },
    {
      id: 'emp_mkt_sales',
      name: 'Inbound Sales Lead Analyst',
      role: 'Lead Qualification Specialist',
      dept: 'MARKETING',
      deptLabel: 'Marketing & Sales',
      entity: 'cmo',
      status: 'Active',
      sop: 'SOP-SALES-01: Real-Time Lead Scoring & Outreach',
      kra: 'Engage high-intent inbound inquiries in under 3 minutes with verified quote',
      agents: ['WhatsApp CRM Agent'],
      perfRating: '98.4%',
      tasksCompleted: 670
    },
    {
      id: 'emp_tech_mcp',
      name: 'API & MCP Protocol Engineer',
      role: 'Tool Integration Specialist',
      dept: 'TECHNOLOGY',
      deptLabel: 'Technology & Systems',
      entity: 'cto',
      status: 'Active',
      sop: 'SOP-TECH-04: Tool Discovery & Auth Gateway',
      kra: 'Validate JSON-RPC tool contracts and maintain zero unauthorized tool access',
      agents: ['Nango Integrations Agent', 'MCP Protocol Inspector'],
      perfRating: '99.7%',
      tasksCompleted: 820
    },
    {
      id: 'emp_fin_ctrl',
      name: 'Financial Controller',
      role: 'Double-Entry Ledger Auditor',
      dept: 'FINANCE',
      deptLabel: 'Finance & Treasury',
      entity: 'cfo',
      status: 'Active',
      sop: 'SOP-FIN-02: Real-Time Transaction Verification',
      kra: 'Reconcile 100% of debit/credit journal entries against bank statements daily',
      agents: ['General Ledger Agent', 'Audit Hasher'],
      perfRating: '100%',
      tasksCompleted: 940
    },
    {
      id: 'emp_sec_dlp',
      name: 'DLP Sentinel Specialist',
      role: 'Data Loss Prevention Sentinel',
      dept: 'SECURITY',
      deptLabel: 'Cyber Defense',
      entity: 'security',
      status: 'In Flight',
      sop: 'SOP-SEC-04: Outbound Egress Screening',
      kra: 'Ensure 0 customer PII, tenant API keys, or proprietary data escape sandbox boundaries',
      agents: ['DLP Regex & Embedding Agent'],
      perfRating: '100%',
      tasksCompleted: 4200
    }
  ];

  class AppleWorkforceBoardController {
    constructor() {
      this.containerId = 'view-workforce';
      this.selectedDept = 'ALL';
      this.searchQuery = '';
      this.roster = WORKFORCE_ROSTER;
    }

    render(containerOrId = this.containerId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;

      if (!container) return;

      const filtered = this.roster.filter(emp => {
        const matchesDept = (this.selectedDept === 'ALL') || (emp.dept === this.selectedDept);
        const q = this.searchQuery.toLowerCase();
        const matchesQuery = !q || (
          emp.name.toLowerCase().includes(q) ||
          emp.role.toLowerCase().includes(q) ||
          emp.sop.toLowerCase().includes(q) ||
          emp.deptLabel.toLowerCase().includes(q)
        );
        return matchesDept && matchesQuery;
      });

      const totalEmployees = this.roster.length;
      const activeCount = this.roster.filter(e => e.status === 'Active' || e.status === 'In Flight').length;
      const totalTools = this.roster.reduce((acc, e) => acc + e.agents.length, 0);

      container.innerHTML = `
        <div style="max-width:1120px; margin:0 auto; display:flex; flex-direction:column; gap:32px;">

          <!-- 1. TOP HEADER & METRICS -->
          <header style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:20px; padding-bottom:8px;">
            <div>
              <div class="t-caption" style="text-transform:uppercase; letter-spacing:0.05em; color:var(--accent); font-weight:700; margin-bottom:4px;">
                Organizational Capital & Workforce
              </div>
              <h1 class="t-large-title" style="margin:0;">AI Team & Employee Directory</h1>
              <p class="t-callout" style="color:var(--label-2); margin-top:6px;">
                Certified AI Employees holding positions, owning SOPs, and operating delegated Agent tools.
              </p>
            </div>

            <button class="btn-apple btn-apple-primary spring-press"
                    onclick="AppleWorkforceBoard.openProvisionModal()"
                    style="font-size:14px; padding:10px 20px;">
              ${window.Icon ? window.Icon({ name: 'plus', size: 16 }) : '+'}
              <span>Provision New Employee</span>
            </button>
          </header>

          <!-- 2. CONSTITUTIONAL INVARIANT BANNER -->
          <div class="card-apple" style="padding:18px 24px; border-left:4px solid var(--accent); background:linear-gradient(135deg, var(--accent-tint) 0%, var(--surface) 100%); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div style="display:flex; align-items:center; gap:14px;">
              ${window.Icon ? window.Icon({ name: 'shield', size: 28, tone: 'accent' }) : '🛡️'}
              <div>
                <div class="t-headline" style="font-size:14.5px; color:var(--label);">Immutable Workforce Governance Invariant</div>
                <div class="t-footnote" style="color:var(--label-2); margin-top:2px;">
                  AI Employees hold corporate identities, responsibilities, and operate AI Agents.
                  <strong>AI Agents are execution tools and can never control or supervise Employees.</strong>
                </div>
              </div>
            </div>
            <span class="chip-apple chip-green" style="font-size:12px;">Enforced by PolicyEngine</span>
          </div>

          <!-- 3. TOP WORKFORCE VITALS -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px;">
            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Certified Employees</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px;">${totalEmployees}</div>
              <div class="t-footnote" style="color:var(--green); margin-top:4px;">100% SOP certified</div>
            </div>

            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Active & In Flight</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px; color:var(--accent);">${activeCount}</div>
              <div class="t-footnote" style="color:var(--label-2); margin-top:4px;">Autonomous task execution</div>
            </div>

            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Authorized Agent Tools</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px;">${totalTools}</div>
              <div class="t-footnote" style="color:var(--label-2); margin-top:4px;">Sandboxed execution agents</div>
            </div>

            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Constitutional Compliance</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px; color:var(--green);">100%</div>
              <div class="t-footnote" style="color:var(--green); margin-top:4px;">0 reverse control attempts</div>
            </div>
          </div>

          <!-- 4. CONTROLS: SEARCH & DEPARTMENT FILTER CHIPS -->
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <!-- Department Chips -->
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
              ${[
                { id: 'ALL', label: 'All Roster' },
                { id: 'LEADERSHIP', label: 'Executive Leadership' },
                { id: 'OPERATIONS', label: 'Operations' },
                { id: 'MARKETING', label: 'Marketing & Sales' },
                { id: 'TECHNOLOGY', label: 'Technology' },
                { id: 'FINANCE', label: 'Finance' },
                { id: 'SECURITY', label: 'Cyber Defense' }
              ].map(d => `
                <button class="chip-apple ${this.selectedDept === d.id ? 'chip-green' : 'chip-neutral'} spring-press"
                        onclick="AppleWorkforceBoard.filterDept('${d.id}')"
                        style="cursor:pointer; font-size:12.5px; padding:6px 14px; font-weight:${this.selectedDept === d.id ? '600' : '400'};">
                  ${escapeHtml(d.label)}
                </button>
              `).join('')}
            </div>

            <!-- Search input -->
            <div style="min-width:260px;">
              <input type="text"
                     class="input-apple"
                     placeholder="Search employees, roles, SOPs..."
                     value="${escapeHtml(this.searchQuery)}"
                     oninput="AppleWorkforceBoard.search(this.value)"
                     style="width:100%; box-sizing:border-box; font-size:13.5px; padding:8px 14px;">
            </div>
          </div>

          <!-- 5. EMPLOYEE CARDS GRID -->
          ${filtered.length === 0 ? `
            <div class="card-apple" style="padding:60px 24px; text-align:center;">
              <div style="font-size:36px; margin-bottom:12px;">👥</div>
              <h3 class="t-title-3">No matching employees found</h3>
              <p class="t-footnote" style="margin-top:4px; color:var(--label-2);">Try adjusting your search query or department filter.</p>
              <button class="btn-apple btn-apple-secondary spring-press"
                      onclick="AppleWorkforceBoard.filterDept('ALL'); AppleWorkforceBoard.search('');"
                      style="margin-top:16px;">
                Reset Filters
              </button>
            </div>
          ` : `
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:18px;">
              ${filtered.map(emp => `
                <div class="card-apple card-apple-interactive hover-lift"
                     onclick="AppleWorkforceBoard.inspectEmployee('${emp.id}')"
                     style="padding:22px; cursor:pointer; display:flex; flex-direction:column; justify-content:space-between; gap:16px;">
                  
                  <div>
                    <!-- Card Top Row -->
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                      <div style="display:flex; align-items:center; gap:12px;">
                        ${window.AppTile ? window.AppTile({ entity: emp.entity, size: 44 }) : ''}
                        <div>
                          <div class="t-headline" style="font-size:15.5px; color:var(--label);">${escapeHtml(emp.name)}</div>
                          <div class="t-caption" style="color:var(--label-2); margin-top:1px;">${escapeHtml(emp.role)}</div>
                        </div>
                      </div>
                      <span class="chip-apple ${emp.status === 'Active' ? 'chip-green' : emp.status === 'In Flight' ? 'chip-accent' : 'chip-neutral'}"
                            style="font-size:11px; padding:3px 8px;">
                        ${escapeHtml(emp.status)}
                      </span>
                    </div>

                    <!-- SOP Badge -->
                    <div style="margin-top:14px; background:var(--surface-2); padding:8px 12px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
                      <div class="t-caption" style="color:var(--label-3); font-weight:600;">Governing SOP</div>
                      <div class="t-footnote" style="color:var(--label); font-weight:500; margin-top:2px; font-family:var(--font-mono); font-size:12px;">
                        ${escapeHtml(emp.sop)}
                      </div>
                    </div>

                    <!-- Authorized Agents List -->
                    <div style="margin-top:12px;">
                      <div class="t-caption" style="color:var(--label-3); font-weight:600; margin-bottom:4px;">
                        Authorized Execution Agents (${emp.agents.length})
                      </div>
                      <div style="display:flex; flex-wrap:wrap; gap:4px;">
                        ${emp.agents.map(ag => `
                          <span class="chip-apple chip-neutral" style="font-size:11px; padding:2px 7px;">
                            ${escapeHtml(ag)}
                          </span>
                        `).join('')}
                      </div>
                    </div>
                  </div>

                  <!-- Card Bottom Footer -->
                  <div style="display:flex; justify-content:space-between; align-items:center; padding-top:12px; border-top:0.5px solid var(--separator); font-size:12px; color:var(--label-2);">
                    <span>${escapeHtml(emp.deptLabel)}</span>
                    <span style="font-weight:600; color:var(--label);">${escapeHtml(emp.perfRating)} rating</span>
                  </div>

                </div>
              `).join('')}
            </div>
          `}

        </div>
      `;
    }

    filterDept(dept) {
      this.selectedDept = dept;
      this.render();
    }

    search(query) {
      this.searchQuery = query;
      this.render();
    }

    inspectEmployee(id) {
      const emp = this.roster.find(e => e.id === id);
      if (!emp) return;

      if (!window.Inspector || !window.Inspector.open) return;

      const content = `
        <div style="display:flex; flex-direction:column; gap:22px;">
          <!-- Header -->
          <div style="display:flex; align-items:center; gap:16px;">
            ${window.AppTile ? window.AppTile({ entity: emp.entity, size: 52 }) : ''}
            <div>
              <h4 class="t-title-3" style="margin:0;">${escapeHtml(emp.name)}</h4>
              <p class="t-caption" style="color:var(--label-2); margin-top:2px;">
                ${escapeHtml(emp.role)} • ${escapeHtml(emp.deptLabel)}
              </p>
            </div>
          </div>

          <!-- Vitals -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div style="background:var(--surface-2); padding:12px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
              <span class="t-caption" style="color:var(--label-3);">Performance Rating</span>
              <div class="t-headline" style="color:var(--green); margin-top:2px;">${escapeHtml(emp.perfRating)}</div>
            </div>
            <div style="background:var(--surface-2); padding:12px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
              <span class="t-caption" style="color:var(--label-3);">Tasks Executed</span>
              <div class="t-headline" style="margin-top:2px;">${emp.tasksCompleted}</div>
            </div>
          </div>

          <!-- SOP Details -->
          <div style="background:var(--surface-2); padding:16px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
            <span class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3);">Standard Operating Procedure</span>
            <div class="t-headline" style="font-size:14.5px; margin-top:4px;">${escapeHtml(emp.sop)}</div>
            <p class="t-footnote" style="color:var(--label-2); margin-top:6px; line-height:1.45;">
              Certified by CHRO governance. Bound by autonomous policy gates and continuous verification loops.
            </p>
          </div>

          <!-- KRA -->
          <div>
            <span class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3);">Key Result Area (KRA)</span>
            <p class="t-body" style="font-size:13.5px; color:var(--label); margin-top:4px; line-height:1.45;">
              ${escapeHtml(emp.kra)}
            </p>
          </div>

          <!-- Authorized Agents -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <span class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3);">Authorized Execution Agents</span>
              <span class="chip-apple chip-green" style="font-size:11px;">Permitted Tools</span>
            </div>
            <div style="display:flex; flex-direction:column; gap:6px;">
              ${emp.agents.map(ag => `
                <div style="display:flex; justify-content:space-between; align-items:center; background:var(--surface-2); padding:10px 14px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
                  <span class="t-footnote" style="font-weight:600;">${escapeHtml(ag)}</span>
                  <span class="t-caption" style="color:var(--label-3);">Subordinate Agent Tool</span>
                </div>
              `).join('')}
            </div>
            <p class="t-caption" style="color:var(--label-3); margin-top:8px;">
              🔒 Constitutional rule: This employee operates these agents. None of these agents can control the employee.
            </p>
          </div>

          <!-- Action Button -->
          <div style="padding-top:14px; border-top:0.5px solid var(--separator); display:flex; justify-content:flex-end;">
            <button class="btn-apple btn-apple-primary spring-press"
                    onclick="UI.showToast('Connecting direct session with ${escapeHtml(emp.name)}...', 'info'); Inspector.close();"
                    style="font-size:13px; padding:8px 18px;">
              Direct Message Employee
            </button>
          </div>
        </div>
      `;

      window.Inspector.open(emp.name, content);
    }

    openProvisionModal() {
      if (!window.UI || !window.UI.openModal) return;

      window.UI.openModal(
        'Provision New AI Employee',
        `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <p class="t-body" style="color:var(--label-2); font-size:13.5px; line-height:1.45;">
              Assign a corporate role, certification SOP, and delegated execution agent tools.
            </p>

            <div>
              <label class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px; display:block;">Employee Position Title</label>
              <input type="text" id="newEmpTitle" class="input-apple" placeholder="e.g. Senior Conversion Rate Optimization Specialist" style="width:100%; box-sizing:border-box;">
            </div>

            <div>
              <label class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px; display:block;">Department</label>
              <select id="newEmpDept" class="input-apple" style="width:100%; box-sizing:border-box;">
                <option value="MARKETING">Marketing & Sales</option>
                <option value="OPERATIONS">Operations</option>
                <option value="TECHNOLOGY">Technology & Systems</option>
                <option value="FINANCE">Finance & Treasury</option>
                <option value="SECURITY">Cyber Defense</option>
              </select>
            </div>

            <div>
              <label class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px; display:block;">Standard Operating Procedure (SOP)</label>
              <input type="text" id="newEmpSop" class="input-apple" placeholder="e.g. SOP-MKT-08: Checkout Funnel Optimization" style="width:100%; box-sizing:border-box;">
            </div>

            <div>
              <label class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px; display:block;">Authorized Agent Tools (Comma separated)</label>
              <input type="text" id="newEmpAgents" class="input-apple" placeholder="e.g. Browser Automation MCP, Content Crawler" style="width:100%; box-sizing:border-box;">
              <span class="t-caption" style="color:var(--label-3); margin-top:4px; display:block;">
                Note: Agents will be provisioned in strictly subordinate execution mode.
              </span>
            </div>

            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
              <button class="btn-apple btn-apple-secondary" onclick="UI.closeModal()">Cancel</button>
              <button class="btn-apple btn-apple-primary" onclick="
                const title = document.getElementById('newEmpTitle').value;
                const dept = document.getElementById('newEmpDept').value;
                const sop = document.getElementById('newEmpSop').value;
                const ag = document.getElementById('newEmpAgents').value;
                if(title && sop) {
                  AppleWorkforceBoard.addEmployee({
                    name: title,
                    role: title,
                    dept: dept,
                    deptLabel: dept,
                    entity: dept === 'MARKETING' ? 'cmo' : dept === 'TECHNOLOGY' ? 'cto' : dept === 'FINANCE' ? 'cfo' : dept === 'SECURITY' ? 'security' : 'coo',
                    status: 'Active',
                    sop: sop,
                    kra: 'Autonomous execution according to certified SOP',
                    agents: ag ? ag.split(',').map(s => s.trim()).filter(Boolean) : ['Standard Execution Tool'],
                    perfRating: '100%',
                    tasksCompleted: 0
                  });
                  UI.showToast('AI Employee provisioned and certified.', 'success');
                  UI.closeModal();
                } else {
                  UI.showToast('Please enter Title and SOP.', 'error');
                }
              ">
                Certify & Provision Employee
              </button>
            </div>
          </div>
        `
      );
    }

    addEmployee(emp) {
      emp.id = 'emp_' + Date.now();
      this.roster.unshift(emp);
      this.render();
    }
  }

  window.AppleWorkforceBoard = new AppleWorkforceBoardController();
})();
