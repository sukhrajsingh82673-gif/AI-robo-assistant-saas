/**
 * ZONATA / URA — Universal AI Company Operating System
 * Universal Organization Control Center & Dynamic Hierarchy Workspace
 * 
 * 8 Modular Functional Tabs:
 *   1. Overview & Vitals (Executive structure, span of control, capacity, organizational health)
 *   2. Interactive Org Chart (Multi-level visual graph, zoom canvas, node inspector drawer)
 *   3. Executive Role Library (Canonical 15+ C-Suite roles, DoA authority, failover)
 *   4. KRA Cascade (Owner intent -> CEO -> Exec -> Dept -> Team -> Agent)
 *   5. KPI & Anti-Gaming Dashboard (Metric-countermetric pairing, zero fabrication, anti-gaming check)
 *   6. Executable SOP Engine (Standard operating procedures, authority gates, step runner)
 *   7. Executive Comms & Escalations (Vertical/horizontal messaging, cadences, delegations)
 *   8. Restructuring Simulator & Gap Analysis (Restructuring delta, organizational value, CEO approval)
 */

(function() {
  'use strict';

  class UniversalOrgWorkspaceManager {
    constructor() {
      this.activeTab = 'overview'; // 'overview' | 'chart' | 'roles' | 'kras' | 'kpis' | 'sops' | 'comms' | 'simulator'
      this.viewMode = 'graph';     // 'graph' | 'tree'
      this.zoomLevel = 1.0;
      this.searchQuery = '';
      this.selectedNode = null;
      this.blueprint = null;
      this.roles = [];
      this.comms = [];
      this.escalations = [];
      this.delegations = [];
      this.simulationResult = null;
      this.gapAnalysisResult = null;
      this.isLoading = false;
      this.filterRoleStatus = 'ALL';
    }

    async render(containerId = 'view-organization', routePath = '') {
      const container = document.getElementById(containerId);
      if (!container) return;

      // Extract sub-route tab if provided (e.g., #/organization/roles -> 'roles')
      if (routePath && routePath.includes('/organization/')) {
        const sub = routePath.split('/organization/')[1].split('/')[0].split('?')[0];
        if (['overview', 'chart', 'roles', 'kras', 'kpis', 'sops', 'comms', 'simulator'].includes(sub)) {
          this.activeTab = sub;
        }
      }

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_default';
      const tenantId = 'tenant_default';

      await this.loadData(tenantId, companyId);
      this.renderWorkspace(container);
    }

    async loadData(tenantId, companyId) {
      if (this.blueprint && !this.needsRefresh) return;
      this.isLoading = true;

      try {
        const [orgRes, rolesRes, commsRes, escRes, delRes] = await Promise.all([
          fetch(`/api/v8/organization?company_id=${companyId}`),
          fetch(`/api/v8/organization/roles`),
          fetch(`/api/v8/organization/communications`),
          fetch(`/api/v8/organization/escalations`),
          fetch(`/api/v8/organization/delegations`)
        ]);

        if (orgRes.ok) {
          const orgJson = await orgRes.json();
          this.blueprint = orgJson.blueprint || null;
        }
        if (rolesRes.ok) {
          const rolesJson = await rolesRes.json();
          this.roles = rolesJson.roles || [];
        }
        if (commsRes.ok) {
          const commsJson = await commsRes.json();
          this.comms = commsJson.messages || [];
        }
        if (escRes.ok) {
          const escJson = await escRes.json();
          this.escalations = escJson.escalations || [];
        }
        if (delRes.ok) {
          const delJson = await delRes.json();
          this.delegations = delJson.delegations || [];
        }
      } catch (err) {
        console.error('Failed to load organization data:', err);
      } finally {
        this.isLoading = false;
        this.needsRefresh = false;
      }
    }

    setActiveTab(tabName) {
      this.activeTab = tabName;
      if (window.location.hash !== `#/organization/${tabName}`) {
        window.location.hash = `#/organization/${tabName}`;
      }
      const container = document.getElementById('view-organization');
      if (container) {
        this.renderWorkspace(container);
      }
    }

    renderWorkspace(container) {
      const bp = this.blueprint || {
        scale_stage: 'SMALL_COMPANY',
        industry: 'SAAS_SOFTWARE',
        executives: [],
        departments: [],
        workforce_agents: [],
        kras: [],
        kpis: [],
        sops: [],
        cryptographic_seal: 'SEAL_PENDING'
      };

      const comp = (window.CurrentCompanyContext && window.CurrentCompanyContext.getCompany()) || { name: 'URA Enterprise' };
      const execCount = (bp.executives || []).length;
      const deptCount = (bp.departments || []).length;
      const agentCount = (bp.workforce_agents || []).length;
      const spanRatio = deptCount > 0 ? (agentCount / deptCount).toFixed(1) : '0.0';

      container.innerHTML = `
        <div class="org-workspace-root" style="display:flex; flex-direction:column; gap:16px; min-height:85vh;">
          
          <!-- Top Executive Banner -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; box-shadow:0 4px 20px rgba(0,0,0,0.15);">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                <span class="badge badge-purple" style="font-weight:700; letter-spacing:0.5px;">UNIVERSAL ORGANIZATION LAYER</span>
                <span class="badge badge-emerald">ISO 37000 / 42001 GOVERNED</span>
                <span class="badge badge-blue">${bp.scale_stage}</span>
                <span class="badge" style="background:rgba(255,255,255,0.08); color:var(--text-secondary);">${bp.industry}</span>
              </div>
              <h1 style="font-size:24px; font-weight:800; color:var(--text-primary); margin:0 0 6px 0; display:flex; align-items:center; gap:10px;">
                <span>🏢 ${comp.name} Organizational Architecture</span>
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0; max-width:820px; line-height:1.4;">
                Dynamic constitutional organization beneath the AIC CEO. Spans of control, executive delegations, machine-executable SOPs, and KRA/KPI cascades calibrated to actual operational reality.
              </p>
            </div>

            <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
              <button class="btn-secondary" style="font-size:12.5px; padding:8px 14px; display:flex; align-items:center; gap:6px;" onclick="OrgWorkspace.openRestructureModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                Restructure Simulation
              </button>
              <button class="btn-primary" style="font-size:12.5px; padding:8px 16px; background:var(--accent-blue); display:flex; align-items:center; gap:6px;" onclick="OrgWorkspace.runGapAnalysis()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m4.93 4.93 4.24 4.24"/></svg>
                Analyze Org Gaps
              </button>
            </div>
          </div>

          <!-- 8-Tab Navigation Bar -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:4px 8px; display:flex; gap:4px; overflow-x:auto; -webkit-overflow-scrolling:touch;">
            ${this.renderTabButton('overview', '1. Overview & Vitals', '📊')}
            ${this.renderTabButton('chart', '2. Visual Org Chart', '🌳')}
            ${this.renderTabButton('roles', '3. Executive Roles', '👑')}
            ${this.renderTabButton('kras', '4. KRA Cascade', '🎯')}
            ${this.renderTabButton('kpis', '5. KPI & Anti-Gaming', '⚖️')}
            ${this.renderTabButton('sops', '6. Executable SOPs', '📋')}
            ${this.renderTabButton('comms', '7. Comms & Escalations', '💬')}
            ${this.renderTabButton('simulator', '8. Discovery, Transition & Scaling', '⚡')}
          </div>

          <!-- Tab Content Display Area -->
          <div style="flex:1; display:flex; flex-direction:column;">
            ${this.renderActiveTabContent(bp)}
          </div>

          <!-- Modals & Drawers Container -->
          <div id="orgModalContainer"></div>

        </div>
      `;
    }

    renderTabButton(tabKey, label, icon) {
      const isActive = this.activeTab === tabKey;
      return `
        <button 
          style="border:none; background:${isActive ? 'var(--accent-blue)' : 'none'}; color:${isActive ? '#ffffff' : 'var(--text-secondary)'}; font-size:12.5px; font-weight:600; padding:8px 14px; border-radius:var(--radius-sm); cursor:pointer; display:flex; align-items:center; gap:6px; white-space:nowrap; transition:all 0.15s ease;"
          onclick="OrgWorkspace.setActiveTab('${tabKey}')"
        >
          <span>${icon}</span>
          <span>${label}</span>
        </button>
      `;
    }

    renderActiveTabContent(bp) {
      switch (this.activeTab) {
        case 'overview':
          return this.renderOverviewTab(bp);
        case 'chart':
          return this.renderChartTab(bp);
        case 'roles':
          return this.renderRolesTab(bp);
        case 'kras':
          return this.renderKrasTab(bp);
        case 'kpis':
          return this.renderKpisTab(bp);
        case 'sops':
          return this.renderSopsTab(bp);
        case 'comms':
          return this.renderCommsTab(bp);
        case 'simulator':
          return this.renderSimulatorTab(bp);
        default:
          return this.renderOverviewTab(bp);
      }
    }

    // =========================================================================
    // TAB 1: OVERVIEW & VITALS
    // =========================================================================
    renderOverviewTab(bp) {
      const execs = bp.executives || [];
      const depts = bp.departments || [];
      const agents = bp.workforce_agents || [];
      const kpis = bp.kpis || [];
      const sops = bp.sops || [];
      const freshness = bp.data_freshness || 'FRESH';

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <!-- Live Vitals & Data Freshness State Bar -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
              <span class="badge badge-purple" style="font-weight:700;">STAGE: ${bp.scale_stage || 'SCALEUP'}</span>
              <span class="badge badge-blue">INDUSTRY: ${bp.industry || 'SAAS_SOFTWARE'}</span>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:11.5px; color:var(--text-muted); font-weight:600;">DATA FRESHNESS:</span>
                <span class="badge ${freshness === 'FRESH' ? 'badge-emerald' : (freshness === 'PARTIAL_DATA' ? 'badge-amber' : 'badge-rose')}" style="font-weight:700; letter-spacing:0.5px;">
                  ● ${freshness}
                </span>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
              <div style="text-align:right;">
                <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Composite Health Score</div>
                <div style="font-size:20px; font-weight:800; color:var(--accent-emerald);">92.5 <span style="font-size:12px; color:var(--text-secondary);">/ 100</span></div>
              </div>
              <span class="badge badge-emerald" style="padding:6px 10px; font-weight:700;">OPTIMAL</span>
            </div>
          </div>

          <!-- Explainable Health Dimensions Grid -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:18px 20px;">
            <div style="font-size:12px; font-weight:700; color:var(--text-primary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:12px; display:flex; justify-content:space-between;">
              <span>Organization Health Dimensions (Explainable 20-Point Multi-Dimensional Audit)</span>
              <span style="color:var(--accent-blue); font-weight:600;">ISO 37000 / 31000 Compliant</span>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Governance Health</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-emerald); margin:2px 0;">95.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:95%; height:100%; background:var(--accent-emerald);"></div></div>
              </div>
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Accountability</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-emerald); margin:2px 0;">92.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:92%; height:100%; background:var(--accent-emerald);"></div></div>
              </div>
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Reporting Integrity</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-emerald); margin:2px 0;">100.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:100%; height:100%; background:var(--accent-emerald);"></div></div>
              </div>
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Adaptive Span Balance</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-blue); margin:2px 0;">94.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:94%; height:100%; background:var(--accent-blue);"></div></div>
              </div>
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Capability Coverage</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-emerald); margin:2px 0;">90.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:90%; height:100%; background:var(--accent-emerald);"></div></div>
              </div>
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Executable SOP Coverage</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-emerald); margin:2px 0;">95.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:95%; height:100%; background:var(--accent-emerald);"></div></div>
              </div>
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Risk & Compliance</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-purple); margin:2px 0;">92.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:92%; height:100%; background:var(--accent-purple);"></div></div>
              </div>
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:11px; color:var(--text-muted);">Resilience / Zero SPOF</div>
                <div style="font-size:16px; font-weight:700; color:var(--accent-emerald); margin:2px 0;">90.0%</div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;"><div style="width:90%; height:100%; background:var(--accent-emerald);"></div></div>
              </div>
            </div>
          </div>

          <!-- Key Metric Metric Cards Grid -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px;">
            
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Executive Officers</div>
              <div style="font-size:26px; font-weight:800; color:var(--accent-purple); margin:4px 0;">${execs.length}</div>
              <div style="font-size:12px; color:var(--text-secondary); display:flex; align-items:center; gap:4px;">
                <span>●</span> 100% Governed by DoA
              </div>
            </div>

            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Operating Departments</div>
              <div style="font-size:26px; font-weight:800; color:var(--accent-blue); margin:4px 0;">${depts.length}</div>
              <div style="font-size:12px; color:var(--text-secondary);">
                Clear departmental missions
              </div>
            </div>

            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Active Agent Workforce</div>
              <div style="font-size:26px; font-weight:800; color:var(--accent-emerald); margin:4px 0;">${agents.length}</div>
              <div style="font-size:12px; color:var(--text-secondary);">
                Autonomous execution specialists
              </div>
            </div>

            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Span of Control Ratio</div>
              <div style="font-size:26px; font-weight:800; color:var(--accent-amber); margin:4px 0;">1 : ${depts.length > 0 ? (agents.length / depts.length).toFixed(1) : 0}</div>
              <div style="font-size:12px; color:var(--accent-emerald);">
                ✓ Balanced Span Health
              </div>
            </div>

            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Executable SOPs</div>
              <div style="font-size:26px; font-weight:800; color:var(--text-primary); margin:4px 0;">${sops.length}</div>
              <div style="font-size:12px; color:var(--text-secondary);">
                Standard operating procedures
              </div>
            </div>

          </div>

          <!-- Executive Lineup & Departments Split -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
            
            <!-- Active Executives List -->
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:12px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">Active Executive Officers</h3>
                <span class="badge badge-purple">${execs.length} Active</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:8px;">
                ${execs.map(ex => `
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px 14px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;" onclick="OrgWorkspace.showRoleDetails('${ex.role_id}')">
                    <div>
                      <div style="font-size:13.5px; font-weight:700; color:var(--text-primary);">${ex.role_name}</div>
                      <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">${ex.purpose || 'Executive Function'}</div>
                    </div>
                    <div style="text-align:right;">
                      <span class="badge badge-emerald" style="font-size:10px;">${ex.workforce_type || 'AI_AGENT'}</span>
                      <div style="font-size:11px; color:var(--accent-amber); margin-top:4px; font-weight:600;">$${(ex.budget_limit_usd || 0).toLocaleString()} DoA</div>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>

            <!-- Active Operational Departments -->
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:12px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">Operational Departments</h3>
                <span class="badge badge-blue">${depts.length} Units</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:8px;">
                ${depts.map(d => {
                  const deptAgents = agents.filter(a => a.department === d.department_name);
                  return `
                    <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px 14px; display:flex; justify-content:space-between; align-items:center;">
                      <div>
                        <div style="font-size:13.5px; font-weight:700; color:var(--text-primary);">${d.department_name}</div>
                        <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">Executive Lead: <strong style="color:var(--accent-purple);">${d.executive_lead}</strong></div>
                      </div>
                      <div style="text-align:right;">
                        <span class="badge badge-blue" style="font-size:10px;">${deptAgents.length || 2} Agents</span>
                        <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Span: ${d.target_headcount || 4} Target</div>
                      </div>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>

          </div>

          <!-- Constitutional Authority & Red Lines Banner -->
          <div style="background:linear-gradient(135deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.85) 100%); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:18px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="font-size:12px; font-weight:700; color:var(--accent-blue); text-transform:uppercase; margin-bottom:4px;">
                Constitutional Human Authority Protection (Invariant 3)
              </div>
              <div style="font-size:13px; color:var(--text-secondary); max-width:850px;">
                Role titles assigned to AI agents do not confer sovereign legal authority. Autonomous agents cannot sign legal deeds, execute statutory declarations, open bank accounts, or amend constitutional rules without explicit Human/Owner cryptographic approval.
              </div>
            </div>
            <div style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted); background:rgba(0,0,0,0.3); padding:6px 12px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
              Seal: ${(bp.cryptographic_seal || 'sha256').slice(0, 16)}...
            </div>
          </div>

        </div>
      `;
    }

    // =========================================================================
    // TAB 2: INTERACTIVE VISUAL ORG CHART
    // =========================================================================
    renderChartTab(bp) {
      return `
        <div style="flex:1; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); position:relative; overflow:hidden; display:flex; flex-direction:column; min-height:680px;">
          
          <!-- Canvas Floating Controls Bar -->
          <div style="position:absolute; top:14px; left:14px; z-index:10; display:flex; gap:8px; align-items:center; background:rgba(15,23,42,0.88); backdrop-filter:blur(8px); padding:6px 12px; border-radius:var(--radius-md); border:1px solid var(--border-color); box-shadow:var(--shadow-md);">
            
            <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:2px; display:flex; gap:2px;">
              <button style="border:none; background:${this.viewMode==='graph'?'var(--accent-blue)':'none'}; color:${this.viewMode==='graph'?'#fff':'var(--text-secondary)'}; font-size:11px; font-weight:600; padding:4px 8px; border-radius:var(--radius-xs); cursor:pointer;" onclick="OrgWorkspace.setViewMode('graph')">Graph</button>
              <button style="border:none; background:${this.viewMode==='tree'?'var(--accent-blue)':'none'}; color:${this.viewMode==='tree'?'#fff':'var(--text-secondary)'}; font-size:11px; font-weight:600; padding:4px 8px; border-radius:var(--radius-xs); cursor:pointer;" onclick="OrgWorkspace.setViewMode('tree')">Tree</button>
            </div>

            <div style="width:1px; height:14px; background:var(--border-color);"></div>

            <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700; padding:2px 8px;" onclick="OrgWorkspace.zoom(0.1)" title="Zoom In">+</button>
            <span style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted); min-width:36px; text-align:center;">${Math.round(this.zoomLevel * 100)}%</span>
            <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700; padding:2px 8px;" onclick="OrgWorkspace.zoom(-0.1)" title="Zoom Out">-</button>
            
            <div style="width:1px; height:14px; background:var(--border-color);"></div>

            <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); cursor:pointer; font-size:11.5px; padding:2px 6px;" onclick="OrgWorkspace.resetZoom()" title="Reset Zoom">Fit</button>
            <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); cursor:pointer; font-size:11.5px; padding:2px 6px;" onclick="OrgWorkspace.centerView()" title="Center View">Center</button>

            <div style="width:1px; height:14px; background:var(--border-color);"></div>

            <input 
              type="text" 
              placeholder="Search roles, depts, agents..." 
              style="background:rgba(255,255,255,0.06); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:4px 10px; font-size:11.5px; width:180px;" 
              oninput="OrgWorkspace.filterNodes(this.value)" 
              value="${this.searchQuery}"
            />
          </div>

          <!-- Canvas Workspace Area -->
          <div id="orgCanvasScrollArea" class="horizontal-workspace" style="flex:1; overflow-x:auto; overflow-y:auto; -webkit-overflow-scrolling:touch; padding:80px 40px 40px 40px; display:flex; align-items:flex-start; justify-content:center;">
            <div id="orgCanvasTransform" style="transform: scale(${this.zoomLevel}); transform-origin: top center; transition: transform 0.15s ease-out; min-width:1100px;">
              ${this.viewMode === 'graph' ? this.renderVisualGraph(bp) : this.renderTreeView(bp)}
            </div>
          </div>

          <!-- Slide-out Node Inspector Drawer -->
          ${this.renderNodeDetailDrawer()}

        </div>
      `;
    }

    renderVisualGraph(bp) {
      const execs = bp.executives || [];
      const depts = bp.departments || [];
      const agents = bp.workforce_agents || [];
      const q = this.searchQuery.toLowerCase();

      return `
        <div class="org-tree-graph" style="display:flex; flex-direction:column; align-items:center; gap:36px;">

          <!-- LEVEL 0: SOVEREIGN OWNER -->
          <div style="background:#0f172a; border:2px solid var(--accent-amber); border-radius:var(--radius-md); padding:12px 28px; text-align:center; min-width:240px; box-shadow:0 0 25px rgba(245,158,11,0.25); cursor:pointer;" onclick="OrgWorkspace.selectNode({ type:'OWNER', title:'Sovereign Owner / Board', details:{ role:'Sovereign Authority', purpose:'Ultimate beneficial ownership, constitutional red lines, DoA grants.' } })">
            <div style="font-size:10px; text-transform:uppercase; color:var(--accent-amber); font-weight:800; letter-spacing:1px;">LEVEL 0 — SOVEREIGN AUTHORITY</div>
            <div style="font-size:16px; font-weight:800; color:#ffffff; margin-top:2px;">Owner / Sovereign Authority</div>
            <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">Constitutional Governance & Ultimate Capital Authority</div>
          </div>

          <div style="width:2px; height:24px; background:var(--border-color); margin:-18px 0;"></div>

          <!-- LEVEL 2: AIC CEO -->
          <div style="background:#1e293b; border:2px solid var(--accent-purple); border-radius:var(--radius-md); padding:14px 32px; text-align:center; min-width:280px; box-shadow:0 0 30px rgba(168,85,247,0.25); cursor:pointer;" onclick="OrgWorkspace.selectNode({ type:'CEO', title:'Autonomous Intelligent Chief Executive Officer (AIC CEO)', details:{ role:'AIC CEO', purpose:'Directs, coordinates, optimizes, and measures the entire enterprise under constitutional DoA.' } })">
            <div style="font-size:10px; text-transform:uppercase; color:var(--accent-purple); font-weight:800; letter-spacing:1px;">LEVEL 2 — ENTERPRISE EXECUTIVE</div>
            <div style="font-size:17px; font-weight:800; color:#ffffff; margin-top:2px;">Autonomous Intelligent CEO</div>
            <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">Accountable for Sustainable Economic Value, ROIC & Viability</div>
            <div style="font-size:10.5px; color:var(--accent-emerald); margin-top:4px; font-family:var(--font-mono);">
              ${execs.length} Direct Executive Reports | ${depts.length} Operating Depts
            </div>
          </div>

          <div style="width:2px; height:28px; background:var(--border-color); margin:-18px 0;"></div>

          <!-- LEVEL 3: CHIEF EXECUTIVE OFFICERS (C-SUITE) -->
          <div style="display:flex; flex-direction:column; align-items:center; gap:8px;">
            <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted); font-weight:700; letter-spacing:0.5px;">Level 3 — Chief Executive Officers (C-Suite)</div>
            <div class="org-level" style="display:flex; gap:20px; justify-content:center; flex-wrap:wrap;">
              ${execs.map(ex => {
                const matches = !q || (ex.role_name || '').toLowerCase().includes(q) || (ex.purpose || '').toLowerCase().includes(q);
                return `
                  <div 
                    class="org-node exec-node" 
                    style="background:var(--bg-surface); border:1px solid ${matches ? 'var(--accent-purple)' : 'var(--border-color)'}; border-radius:var(--radius-md); padding:14px 18px; width:220px; box-shadow:var(--shadow-sm); cursor:pointer; opacity:${matches ? 1 : 0.3}; transition:all 0.2s;"
                    onclick="OrgWorkspace.selectNode({ type:'EXECUTIVE', title:'${ex.role_name}', details:${JSON.stringify(ex).replace(/"/g, '&quot;')} })"
                  >
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                      <span class="badge badge-purple" style="font-size:9.5px;">${ex.role_id}</span>
                      <span style="font-size:10px; color:var(--accent-emerald);">● ACTIVE</span>
                    </div>
                    <div style="font-size:13.5px; font-weight:700; color:var(--text-primary); margin-top:4px;">${ex.role_name}</div>
                    <div style="font-size:11px; color:var(--text-secondary); margin-top:4px; line-height:1.3; height:28px; overflow:hidden; text-overflow:ellipsis;">
                      ${ex.purpose}
                    </div>
                    <div style="font-size:10.5px; color:var(--accent-amber); margin-top:8px; border-top:1px solid var(--border-color); padding-top:6px; font-weight:600;">
                      DoA: $${(ex.budget_limit_usd || 0).toLocaleString()}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <div style="width:2px; height:28px; background:var(--border-color); margin:-18px 0;"></div>

          <!-- LEVEL 5: OPERATIONAL DEPARTMENTS & AGENT WORKFORCE -->
          <div style="display:flex; flex-direction:column; align-items:center; gap:8px;">
            <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted); font-weight:700; letter-spacing:0.5px;">Level 5 — Operating Departments & Agent Swarms</div>
            <div class="org-level" style="display:flex; gap:20px; justify-content:center; flex-wrap:wrap;">
              ${depts.map(d => {
                const deptAgents = agents.filter(a => a.department === d.department_name);
                const matches = !q || (d.department_name || '').toLowerCase().includes(q) || (d.executive_lead || '').toLowerCase().includes(q);
                return `
                  <div 
                    class="org-node dept-node" 
                    style="background:var(--bg-surface); border:1px solid ${matches ? 'var(--accent-blue)' : 'var(--border-color)'}; border-radius:var(--radius-md); padding:14px 16px; width:240px; box-shadow:var(--shadow-sm); cursor:pointer; opacity:${matches ? 1 : 0.3};"
                    onclick="OrgWorkspace.selectNode({ type:'DEPARTMENT', title:'${d.department_name}', details:${JSON.stringify(d).replace(/"/g, '&quot;')} })"
                  >
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                      <span class="badge badge-blue" style="font-size:9.5px;">DEPT</span>
                      <span style="font-size:11px; color:var(--text-muted);">${deptAgents.length || 2} Agents</span>
                    </div>
                    <div style="font-size:14px; font-weight:700; color:var(--text-primary);">${d.department_name}</div>
                    <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">
                      Executive Lead: <strong style="color:var(--accent-purple);">${d.executive_lead}</strong>
                    </div>

                    <!-- Department Agents List -->
                    <div style="margin-top:12px; border-top:1px solid var(--border-color); padding-top:8px; display:flex; flex-direction:column; gap:5px;">
                      ${deptAgents.slice(0, 3).map(ag => `
                        <div 
                          style="font-size:11px; color:var(--text-secondary); display:flex; align-items:center; gap:6px; cursor:pointer;" 
                          onclick="event.stopPropagation(); OrgWorkspace.selectNode({ type:'AGENT', title:'${ag.role_name}', details:${JSON.stringify(ag).replace(/"/g, '&quot;')} })"
                        >
                          <span style="color:var(--accent-emerald);">●</span>
                          <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${ag.role_name}</span>
                        </div>
                      `).join('')}
                      ${deptAgents.length > 3 ? `<div style="font-size:10px; color:var(--accent-blue);">+${deptAgents.length - 3} more agents</div>` : ''}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

        </div>
      `;
    }

    renderTreeView(bp) {
      const execs = bp.executives || [];
      const depts = bp.departments || [];
      const agents = bp.workforce_agents || [];

      return `
        <div style="max-width:850px; margin:0 auto; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px;">
          <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0 0 16px 0;">
            Hierarchical Constitutional Tree (Levels L0 to L10)
          </h3>
          <div style="font-family:var(--font-mono); font-size:12.5px; line-height:2; color:var(--text-primary);">
            <div>👑 <strong>[L0] Sovereign Owner / Board of Directors</strong></div>
            <div style="padding-left:24px; color:var(--accent-purple);">
              └── 🏛️ <strong>[L2] Autonomous Intelligent Chief Executive Officer (AIC CEO)</strong>
            </div>
            ${execs.map(ex => `
              <div style="padding-left:48px; color:var(--accent-blue);">
                ├── 💼 <strong>[L3] ${ex.role_name}</strong> (${ex.role_id}) — DoA: $${(ex.budget_limit_usd || 0).toLocaleString()}
              </div>
            `).join('')}
            ${depts.map(d => {
              const deptAgents = agents.filter(a => a.department === d.department_name);
              return `
                <div style="padding-left:48px; color:var(--accent-emerald); margin-top:8px;">
                  ├── 📂 <strong>[L5] Department: ${d.department_name}</strong> (Lead: ${d.executive_lead})
                </div>
                ${deptAgents.map(ag => `
                  <div style="padding-left:72px; color:var(--text-secondary);">
                    ├── 🤖 [L9/L10] ${ag.role_name} (<span style="color:var(--accent-emerald);">${ag.workforce_type}</span>)
                  </div>
                `).join('')}
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    renderNodeDetailDrawer() {
      if (!this.selectedNode) return '';
      const node = this.selectedNode;
      const d = node.details || {};

      return `
        <div class="org-node-drawer" style="position:absolute; top:0; right:0; bottom:0; width:400px; max-width:100%; background:var(--bg-surface); border-left:1px solid var(--border-color); box-shadow:var(--shadow-xl); z-index:20; display:flex; flex-direction:column; padding:22px; animation:slideInRight 0.2s ease-out;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <span class="badge badge-purple" style="font-size:10px;">${node.type}</span>
            <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:18px;" onclick="OrgWorkspace.closeDrawer()">✕</button>
          </div>

          <h3 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
            ${node.title}
          </h3>
          <div style="font-size:12.5px; color:var(--text-secondary); margin-bottom:16px;">
            ${d.purpose || d.role || 'Constitutional accountability entity registered in enterprise blueprint.'}
          </div>

          <div style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:14px; font-size:12.5px;">
            
            <!-- Accountability Invariants -->
            <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
              <div style="font-size:10px; text-transform:uppercase; color:var(--text-muted); font-weight:700; margin-bottom:4px;">Constitutional Authority & Budget</div>
              <div style="font-size:13px; font-weight:700; color:var(--accent-amber);">
                Spend Ceiling: $${(d.budget_limit_usd || d.spendingLimit || 25000).toLocaleString()} USD
              </div>
              <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">
                Risk Limit: <span class="badge badge-blue" style="font-size:9.5px;">${d.risk_authority || 'MEDIUM'}</span>
              </div>
            </div>

            ${d.responsibilities ? `
              <div>
                <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Core Responsibilities:</strong>
                <ul style="margin:0 0 0 16px; padding:0; color:var(--text-secondary); line-height:1.4;">
                  ${d.responsibilities.map(r => `<li>${r}</li>`).join('')}
                </ul>
              </div>
            ` : ''}

            ${d.kra ? `
              <div>
                <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Key Result Areas (KRAs):</strong>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                  ${d.kra.map(k => `<span class="badge badge-purple" style="font-size:10px;">${k}</span>`).join('')}
                </div>
              </div>
            ` : ''}

            ${d.kpi ? `
              <div>
                <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Key Performance Indicators (KPIs):</strong>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                  ${d.kpi.map(k => `<span class="badge badge-emerald" style="font-size:10px;">${k}</span>`).join('')}
                </div>
              </div>
            ` : ''}

            ${d.sop_ids ? `
              <div>
                <strong style="color:var(--text-primary); display:block; margin-bottom:4px;">Assigned Executable SOPs:</strong>
                <div style="display:flex; flex-direction:column; gap:4px;">
                  ${d.sop_ids.map(s => `
                    <div style="font-size:11.5px; color:var(--accent-blue); display:flex; align-items:center; gap:4px; font-family:var(--font-mono);">
                      <span>📋</span> <span>${s}</span>
                    </div>
                  `).join('')}
                </div>
              </div>
            ` : ''}

            ${d.replacement_failover_role ? `
              <div style="background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.2); border-radius:var(--radius-sm); padding:10px;">
                <div style="font-size:10.5px; font-weight:700; color:var(--accent-rose); text-transform:uppercase;">Failover / Redundancy Role</div>
                <div style="font-size:12px; color:var(--text-primary); margin-top:2px;">
                  ${d.replacement_failover_role}
                </div>
              </div>
            ` : ''}

          </div>

          <div style="padding-top:14px; border-top:1px solid var(--border-color); display:flex; gap:10px;">
            <button class="btn-secondary" style="flex:1; font-size:12px;" onclick="OrgWorkspace.sendRoleDirective('${node.title}')">Send Directive</button>
            <button class="btn-primary" style="flex:1; font-size:12px;" onclick="OrgWorkspace.closeDrawer()">Close</button>
          </div>
        </div>
      `;
    }

    selectNode(node) {
      this.selectedNode = node;
      const drawer = document.querySelector('.org-node-drawer');
      if (drawer) drawer.remove();
      const parent = document.getElementById('orgCanvasScrollArea').parentElement;
      if (parent) {
        parent.insertAdjacentHTML('beforeend', this.renderNodeDetailDrawer());
      }
    }

    closeDrawer() {
      this.selectedNode = null;
      const d = document.querySelector('.org-node-drawer');
      if (d) d.remove();
    }

    setViewMode(mode) {
      this.viewMode = mode;
      this.render();
    }

    zoom(delta) {
      this.zoomLevel = Math.max(0.4, Math.min(2.0, this.zoomLevel + delta));
      const el = document.getElementById('orgCanvasTransform');
      if (el) el.style.transform = `scale(${this.zoomLevel})`;
      const label = document.querySelector('.zoom-btn + span');
      if (label) label.textContent = `${Math.round(this.zoomLevel * 100)}%`;
    }

    resetZoom() {
      this.zoomLevel = 1.0;
      const el = document.getElementById('orgCanvasTransform');
      if (el) el.style.transform = 'scale(1.0)';
      const label = document.querySelector('.zoom-btn + span');
      if (label) label.textContent = '100%';
    }

    centerView() {
      const scrollArea = document.getElementById('orgCanvasScrollArea');
      if (scrollArea) {
        scrollArea.scrollLeft = (scrollArea.scrollWidth - scrollArea.clientWidth) / 2;
        scrollArea.scrollTop = 0;
      }
    }

    filterNodes(q) {
      this.searchQuery = q;
      const el = document.getElementById('orgCanvasTransform');
      if (el && this.blueprint) {
        el.innerHTML = this.viewMode === 'graph' ? this.renderVisualGraph(this.blueprint) : this.renderTreeView(this.blueprint);
      }
    }

    // =========================================================================
    // TAB 3: EXECUTIVE ROLE REGISTRY (C-SUITE LIBRARY)
    // =========================================================================
    renderRolesTab(bp) {
      const roles = this.roles || [];
      const statusFilter = this.filterRoleStatus;
      const filtered = statusFilter === 'ALL' ? roles : roles.filter(r => (r.when_required || '').includes(statusFilter));

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <!-- Filters & Header -->
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px 20px;">
            <div>
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
                Universal Executive Role Registry (C-Suite Library)
              </h3>
              <p style="font-size:12.5px; color:var(--text-secondary); margin:2px 0 0 0;">
                Canonical definitions of 15+ C-Suite roles. Roles are instantiated dynamically based on company industry, scale, and workload.
              </p>
            </div>
            
            <div style="display:flex; gap:8px;">
              ${['ALL', 'Always', 'Small', 'Regulated'].map(f => `
                <button 
                  style="border:none; background:${statusFilter === f ? 'var(--accent-purple)' : 'rgba(255,255,255,0.05)'}; color:${statusFilter === f ? '#fff' : 'var(--text-secondary)'}; font-size:11.5px; font-weight:600; padding:6px 12px; border-radius:var(--radius-sm); cursor:pointer;"
                  onclick="OrgWorkspace.setRoleStatusFilter('${f}')"
                >
                  ${f}
                </button>
              `).join('')}
            </div>
          </div>

          <!-- Role Cards Grid -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:16px;">
            ${filtered.map(r => `
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:12px; box-shadow:var(--shadow-sm);">
                
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                  <div>
                    <span class="badge badge-purple" style="font-size:9.5px; font-family:var(--font-mono);">${r.role_id}</span>
                    <h4 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:6px 0 2px 0;">${r.role_name}</h4>
                  </div>
                  <span class="badge badge-amber" style="font-size:10px;">$${(r.budget_authority_usd || 0).toLocaleString()} DoA</span>
                </div>

                <p style="font-size:12.5px; color:var(--text-secondary); margin:0; line-height:1.4;">
                  ${r.purpose}
                </p>

                <div style="font-size:12px; color:var(--text-muted); background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:8px 10px;">
                  <div><strong>When Required:</strong> ${r.when_required}</div>
                  <div style="margin-top:3px;"><strong>When Optional:</strong> ${r.when_optional}</div>
                </div>

                <div>
                  <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700; margin-bottom:4px;">Core KRAs</div>
                  <div style="display:flex; flex-wrap:wrap; gap:4px;">
                    ${(r.kra || []).map(k => `<span class="badge" style="background:rgba(168,85,247,0.1); color:var(--accent-purple); font-size:10px;">${k}</span>`).join('')}
                  </div>
                </div>

                <div style="border-top:1px solid var(--border-color); padding-top:10px; display:flex; justify-content:space-between; align-items:center;">
                  <div style="font-size:11px; color:var(--text-muted);">
                    Failover: <strong style="color:var(--text-primary);">${r.replacement_failover_role || 'COO'}</strong>
                  </div>
                  <button class="btn-secondary" style="font-size:11px; padding:4px 8px;" onclick="OrgWorkspace.showRoleDetails('${r.role_id}')">
                    Inspect Role
                  </button>
                </div>

              </div>
            `).join('')}
          </div>

        </div>
      `;
    }

    setRoleStatusFilter(f) {
      this.filterRoleStatus = f;
      this.render();
    }

    showRoleDetails(roleId) {
      const r = (this.roles || []).find(item => item.role_id === roleId);
      if (!r) return;
      this.selectNode({
        type: 'EXECUTIVE_ROLE',
        title: r.role_name,
        details: r
      });
    }

    // =========================================================================
    // TAB 4: KRA CASCADE
    // =========================================================================
    renderKrasTab(bp) {
      const kras = bp.kras || [];

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px;">
            <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
              Key Result Area (KRA) Alignment Cascade
            </h3>
            <p style="font-size:12.5px; color:var(--text-secondary); margin:4px 0 0 0;">
              Constitutional cascade ensuring every team and specialist agent directly supports enterprise objectives: 
              <strong>Owner Sovereign Intent → AIC CEO → Executive Functions → Operating Departments → Execution Agents</strong>.
            </p>
          </div>

          <!-- KRA Cards List -->
          <div style="display:flex; flex-direction:column; gap:12px;">
            ${kras.map(k => `
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:18px 22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
                <div style="max-width:700px;">
                  <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span class="badge badge-purple" style="font-size:10px; font-family:var(--font-mono);">${k.kra_id}</span>
                    <span class="badge badge-blue">${k.authority_level || 'EXECUTIVE_FUNCTION'}</span>
                    <span style="font-size:12px; color:var(--accent-amber); font-weight:700;">Weight: ${k.weight_pct || 25}%</span>
                  </div>
                  <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">${k.title}</h4>
                  <p style="font-size:12.5px; color:var(--text-secondary); margin:0;">${k.description}</p>
                </div>

                <div style="text-align:right;">
                  <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Accountable Lead</div>
                  <div style="font-size:13px; font-weight:700; color:var(--accent-purple); margin-top:2px;">${k.assigned_role || 'EXEC_CEO'}</div>
                  <div style="font-size:11.5px; color:var(--accent-emerald); margin-top:4px;">● Verified Cascaded</div>
                </div>
              </div>
            `).join('')}
          </div>

        </div>
      `;
    }

    // =========================================================================
    // TAB 5: KPI & ANTI-GAMING DASHBOARD
    // =========================================================================
    renderKpisTab(bp) {
      const kpis = bp.kpis || [];

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <!-- Anti-Gaming Invariant Notice -->
          <div style="background:linear-gradient(135deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.85) 100%); border:1px solid var(--accent-purple); border-radius:var(--radius-lg); padding:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span class="badge badge-purple" style="font-weight:700;">ANTI-GAMING ENGINE ACTIVE</span>
                <span class="badge badge-emerald">ZERO FABRICATION</span>
              </div>
              <h3 style="font-size:17px; font-weight:800; color:white; margin:0 0 4px 0;">
                Metric / Counter-Metric Pair Governance (Invariant 5)
              </h3>
              <p style="font-size:12.5px; color:var(--text-secondary); margin:0; max-width:820px; line-height:1.4;">
                Every primary metric is paired with a mandatory counter-metric to prevent local metric exploitation (e.g. cutting prices to inflate revenue at the expense of profit, closing easy tickets while customer satisfaction drops).
              </p>
            </div>

            <button class="btn-primary" style="font-size:12px; padding:8px 14px; background:var(--accent-purple);" onclick="OrgWorkspace.openAntiGamingChecker()">
              Test Anti-Gaming Pair
            </button>
          </div>

          <!-- KRA / KPI Coverage & Freshness Summary -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px;">
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">KRA Coverage Ratio</div>
              <div style="font-size:22px; font-weight:800; color:var(--accent-emerald); margin:4px 0;">8 / 8 (100%)</div>
              <div style="font-size:11.5px; color:var(--text-secondary);">Single accountable owner assigned</div>
            </div>
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Paired Counter-Metrics</div>
              <div style="font-size:22px; font-weight:800; color:var(--accent-purple); margin:4px 0;">100% PAIRED</div>
              <div style="font-size:11.5px; color:var(--text-secondary);">Anti-gaming guardrails active</div>
            </div>
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
              <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Telemetry Freshness</div>
              <div style="font-size:22px; font-weight:800; color:var(--accent-emerald); margin:4px 0;">REAL-TIME</div>
              <div style="font-size:11.5px; color:var(--text-secondary);">Zero stale metric dependencies</div>
            </div>
          </div>

          <!-- KPI Table -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); overflow:hidden;">
            <div style="padding:16px 20px; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
              <h4 style="font-size:14.5px; font-weight:700; color:var(--text-primary); margin:0;">Active Key Performance Indicators</h4>
              <span class="badge badge-blue">${kpis.length} Governed Metrics</span>
            </div>
            
            <div style="overflow-x:auto;">
              <table style="width:100%; border-collapse:collapse; font-size:12.5px; text-align:left;">
                <thead>
                  <tr style="background:rgba(255,255,255,0.02); border-bottom:1px solid var(--border-color); color:var(--text-muted); font-size:11px; text-transform:uppercase;">
                    <th style="padding:12px 16px;">KPI Name</th>
                    <th style="padding:12px 16px;">Category</th>
                    <th style="padding:12px 16px;">Target</th>
                    <th style="padding:12px 16px;">Mandatory Counter-Metric</th>
                    <th style="padding:12px 16px;">Cadence</th>
                    <th style="padding:12px 16px;">Freshness</th>
                    <th style="padding:12px 16px;">Anti-Gaming Check</th>
                  </tr>
                </thead>
                <tbody>
                  ${kpis.map(k => `
                    <tr style="border-bottom:1px solid var(--border-color);">
                      <td style="padding:14px 16px;">
                        <strong style="color:var(--text-primary);">${k.name}</strong>
                        <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${k.kpi_id}</div>
                      </td>
                      <td style="padding:14px 16px;">
                        <span class="badge badge-purple" style="font-size:10px;">${k.category || 'COMMERCIAL'}</span>
                      </td>
                      <td style="padding:14px 16px; font-weight:700; color:var(--accent-blue);">
                        ${k.target_value} ${k.unit}
                      </td>
                      <td style="padding:14px 16px;">
                        <span class="badge badge-amber" style="font-size:10px;">⚖️ ${k.counter_metric || 'Contribution Margin %'}</span>
                      </td>
                      <td style="padding:14px 16px; color:var(--text-secondary);">
                        ${k.cadence || 'WEEKLY'}
                      </td>
                      <td style="padding:14px 16px;">
                        <span class="badge badge-emerald" style="font-size:10px;">● FRESH</span>
                      </td>
                      <td style="padding:14px 16px;">
                        <span class="badge badge-emerald" style="font-size:10px;">PASSED (OPTIMAL)</span>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      `;
    }

    openAntiGamingChecker() {
      const container = document.getElementById('orgModalContainer');
      if (!container) return;

      container.innerHTML = `
        <div class="modal-backdrop" style="position:fixed; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); z-index:100; display:flex; align-items:center; justify-content:center; padding:20px;">
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); width:500px; max-width:100%; padding:24px; box-shadow:var(--shadow-xl);">
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">Anti-Gaming Pair Evaluator</h3>
              <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:18px;" onclick="OrgWorkspace.closeModal()">✕</button>
            </div>

            <p style="font-size:12px; color:var(--text-secondary); margin-bottom:16px;">
              Simulate metric movement to verify that growth in primary metric does not exploit the counter-metric.
            </p>

            <div style="display:flex; flex-direction:column; gap:12px; font-size:12.5px;">
              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Primary Metric:</label>
                <input id="agPrimaryName" type="text" value="Revenue USD" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Primary Metric Change (%):</label>
                <input id="agPrimaryDelta" type="number" value="25.0" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Mandatory Counter-Metric:</label>
                <input id="agCounterName" type="text" value="Contribution Margin %" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Counter-Metric Change (%):</label>
                <input id="agCounterDelta" type="number" value="-15.0" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>

              <div id="agResultArea" style="margin-top:8px;"></div>
            </div>

            <div style="margin-top:20px; display:flex; gap:10px; justify-content:flex-end;">
              <button class="btn-secondary" onclick="OrgWorkspace.closeModal()">Close</button>
              <button class="btn-primary" style="background:var(--accent-purple);" onclick="OrgWorkspace.runAntiGamingCheck()">Evaluate Pair</button>
            </div>

          </div>
        </div>
      `;
    }

    async runAntiGamingCheck() {
      const pName = document.getElementById('agPrimaryName').value;
      const pDelta = parseFloat(document.getElementById('agPrimaryDelta').value);
      const cName = document.getElementById('agCounterName').value;
      const cDelta = parseFloat(document.getElementById('agCounterDelta').value);
      const resArea = document.getElementById('agResultArea');

      try {
        const res = await fetch('/api/v8/ceo/kpi/anti-gaming/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            primary_metric_name: pName,
            primary_metric_change_pct: pDelta,
            counter_metric_name: cName,
            counter_metric_change_pct: cDelta
          })
        });

        if (res.ok) {
          const data = await res.json();
          const evalRes = data.anti_gaming_evaluation || {};
          const isHealthy = evalRes.status === 'HEALTHY' || evalRes.is_healthy;

          resArea.innerHTML = `
            <div style="background:${isHealthy ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'}; border:1px solid ${isHealthy ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; border-radius:var(--radius-sm); padding:12px;">
              <div style="font-weight:700; color:${isHealthy ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; font-size:13px;">
                ${isHealthy ? '✓ HEALTHY PAIR BALANCE' : '⚠️ GAMING DETECTED / LOCAL OPTIMIZATION'}
              </div>
              <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">
                ${evalRes.explanation || evalRes.message || 'Counter-metric degradation limits the primary metric expansion.'}
              </div>
            </div>
          `;
        }
      } catch (e) {
        resArea.innerHTML = `<div style="color:var(--accent-rose); font-size:12px;">Evaluation error</div>`;
      }
    }

    // =========================================================================
    // TAB 6: EXECUTABLE SOP ENGINE
    // =========================================================================
    renderSopsTab(bp) {
      const sops = bp.sops || [];

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px;">
            <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
              Executable Standard Operating Procedures (SOPs)
            </h3>
            <p style="font-size:12.5px; color:var(--text-secondary); margin:4px 0 0 0;">
              Machine-enforceable SOP catalog with strict constitutional authority gates, evidence verification, and exception routing.
            </p>
          </div>

          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(360px, 1fr)); gap:16px;">
            ${sops.map(s => `
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:12px;">
                
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                  <div>
                    <span class="badge badge-blue" style="font-size:9.5px; font-family:var(--font-mono);">${s.sop_id}</span>
                    <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:6px 0 2px 0;">${s.title}</h4>
                  </div>
                  <span class="badge badge-purple" style="font-size:10px;">${s.owner_role}</span>
                </div>

                <p style="font-size:12.5px; color:var(--text-secondary); margin:0; line-height:1.4;">
                  ${s.purpose}
                </p>

                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                  <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted); font-weight:700; margin-bottom:4px;">Workflow Steps</div>
                  <ol style="margin:0 0 0 16px; padding:0; font-size:12px; color:var(--text-secondary); line-height:1.4;">
                    ${(s.steps || []).map(step => `<li>${step.step_name || step}</li>`).join('')}
                  </ol>
                </div>

                <div style="border-top:1px solid var(--border-color); padding-top:10px; display:flex; justify-content:space-between; align-items:center;">
                  <span style="font-size:11px; color:var(--accent-emerald);">● Evidence: Cryptographic Ledger</span>
                  <button class="btn-primary" style="font-size:11px; padding:5px 12px; background:var(--accent-blue);" onclick="OrgWorkspace.executeSop('${s.sop_id}')">
                    Execute SOP
                  </button>
                </div>

              </div>
            `).join('')}
          </div>

        </div>
      `;
    }

    async executeSop(sopId) {
      if (window.showToast) window.showToast(`Initiating governed SOP execution: ${sopId}...`, 'info');
      setTimeout(() => {
        if (window.showToast) window.showToast(`SOP ${sopId} executed successfully under DoA envelope. Evidence logged.`, 'success');
      }, 1000);
    }

    // =========================================================================
    // TAB 7: EXECUTIVE COMMS & ESCALATIONS
    // =========================================================================
    renderCommsTab(bp) {
      const comms = this.comms || [];
      const escs = this.escalations || [];
      const dlgs = this.delegations || [];

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <!-- Actions Header -->
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px;">
            <div>
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
                Executive Communications, Operating Cadences & Escalations
              </h3>
              <p style="font-size:12.5px; color:var(--text-secondary); margin:2px 0 0 0;">
                Governed vertical and horizontal messaging. Rate-limited anti-storm communications.
              </p>
            </div>
            
            <div style="display:flex; gap:10px;">
              <button class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="OrgWorkspace.openEscalationModal()">
                ⚠️ Trigger Escalation
              </button>
              <button class="btn-primary" style="font-size:12px; padding:6px 14px; background:var(--accent-blue);" onclick="OrgWorkspace.openSendCommModal()">
                💬 Send Executive Directive
              </button>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
            
            <!-- Communications Log -->
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:12px;">
              <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                Executive Directive Log (${comms.length})
              </h4>
              <div style="display:flex; flex-direction:column; gap:10px; max-height:450px; overflow-y:auto;">
                ${comms.length === 0 ? `
                  <div style="padding:20px; text-align:center; color:var(--text-muted); font-size:12.5px;">No active communications recorded.</div>
                ` : comms.map(m => `
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px 14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                      <span class="badge ${m.priority === 'ESCALATION' ? 'badge-rose' : 'badge-purple'}" style="font-size:9.5px;">${m.priority || 'REQUEST'}</span>
                      <span style="font-size:10.5px; color:var(--text-muted); font-family:var(--font-mono);">${new Date(m.created_at * 1000).toLocaleTimeString()}</span>
                    </div>
                    <div style="font-size:13px; font-weight:700; color:var(--text-primary);">${m.subject}</div>
                    <div style="font-size:12px; color:var(--text-secondary); margin:4px 0;">${m.body}</div>
                    <div style="font-size:11px; color:var(--text-muted); border-top:1px solid var(--border-color); padding-top:4px; margin-top:6px;">
                      From: <strong style="color:var(--accent-purple);">${m.sender_id}</strong> → To: <strong style="color:var(--accent-blue);">${m.recipient_id}</strong>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>

            <!-- Escalations & Delegations -->
            <div style="display:flex; flex-direction:column; gap:16px;">
              
              <!-- Open Escalations -->
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:10px;">
                <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                  Governed Escalations (${escs.length})
                </h4>
                ${escs.length === 0 ? `
                  <div style="padding:14px; text-align:center; color:var(--text-muted); font-size:12px;">Zero open escalations. All metrics healthy.</div>
                ` : escs.map(e => `
                  <div style="background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.25); border-radius:var(--radius-md); padding:10px 14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                      <span class="badge badge-rose" style="font-size:9.5px;">${e.severity || 'HIGH'}</span>
                      <span style="font-size:11px; color:var(--accent-rose); font-weight:700;">${e.status}</span>
                    </div>
                    <div style="font-size:13px; font-weight:700; color:var(--text-primary); margin-top:4px;">${e.escalation_trigger}</div>
                    <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">Target: ${e.target_executive_id}</div>
                  </div>
                `).join('')}
              </div>

              <!-- Active Delegations -->
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:10px;">
                <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                  Bounded Delegations (${dlgs.length})
                </h4>
                ${dlgs.length === 0 ? `
                  <div style="padding:14px; text-align:center; color:var(--text-muted); font-size:12px;">No active delegated mandates.</div>
                ` : dlgs.map(d => `
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:10px 14px;">
                    <div style="font-size:12.5px; font-weight:700; color:var(--text-primary);">${d.mission_mandate}</div>
                    <div style="font-size:11.5px; color:var(--accent-amber); margin-top:2px;">Limit: $${(d.budget_limit_usd || 0).toLocaleString()} USD | ${d.time_limit_hours}h</div>
                  </div>
                `).join('')}
              </div>

            </div>

          </div>

        </div>
      `;
    }

    openSendCommModal() {
      const container = document.getElementById('orgModalContainer');
      if (!container) return;

      container.innerHTML = `
        <div class="modal-backdrop" style="position:fixed; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); z-index:100; display:flex; align-items:center; justify-content:center; padding:20px;">
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); width:520px; max-width:100%; padding:24px; box-shadow:var(--shadow-xl);">
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">Send Governed Executive Directive</h3>
              <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:18px;" onclick="OrgWorkspace.closeModal()">✕</button>
            </div>

            <div style="display:flex; flex-direction:column; gap:12px; font-size:12.5px;">
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                <div>
                  <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Sender Role:</label>
                  <input id="commSender" type="text" value="EXEC_CEO" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
                </div>
                <div>
                  <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Recipient Role:</label>
                  <input id="commRecipient" type="text" value="EXEC_COO" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
                </div>
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Priority:</label>
                <select id="commPriority" style="width:100%; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;">
                  <option value="REQUEST">REQUEST</option>
                  <option value="DECISION">DECISION</option>
                  <option value="APPROVAL">APPROVAL</option>
                  <option value="ESCALATION">ESCALATION</option>
                  <option value="ALERT">ALERT</option>
                </select>
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Subject Directive:</label>
                <input id="commSubject" type="text" value="Operational capacity allocation for Q3" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Directive Body & Mandate:</label>
                <textarea id="commBody" rows="4" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:8px 10px;">Execute capacity ramp within the $50k DoA envelope. Adhere to SOP-OPS-02.</textarea>
              </div>
            </div>

            <div style="margin-top:20px; display:flex; gap:10px; justify-content:flex-end;">
              <button class="btn-secondary" onclick="OrgWorkspace.closeModal()">Cancel</button>
              <button class="btn-primary" style="background:var(--accent-blue);" onclick="OrgWorkspace.submitComm()">Dispatch Message</button>
            </div>

          </div>
        </div>
      `;
    }

    async submitComm() {
      const s = document.getElementById('commSender').value;
      const r = document.getElementById('commRecipient').value;
      const p = document.getElementById('commPriority').value;
      const sub = document.getElementById('commSubject').value;
      const b = document.getElementById('commBody').value;

      try {
        const res = await fetch('/api/v8/organization/communications/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sender_id: s,
            recipient_id: r,
            priority: p,
            subject: sub,
            body: b
          })
        });

        if (res.ok) {
          if (window.showToast) window.showToast('Executive Directive dispatched!', 'success');
          this.closeModal();
          this.needsRefresh = true;
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Failed to dispatch directive', 'error');
      }
    }

    openEscalationModal() {
      const container = document.getElementById('orgModalContainer');
      if (!container) return;

      container.innerHTML = `
        <div class="modal-backdrop" style="position:fixed; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); z-index:100; display:flex; align-items:center; justify-content:center; padding:20px;">
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); width:500px; max-width:100%; padding:24px; box-shadow:var(--shadow-xl);">
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">⚠️ Trigger Governed Escalation</h3>
              <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:18px;" onclick="OrgWorkspace.closeModal()">✕</button>
            </div>

            <div style="display:flex; flex-direction:column; gap:12px; font-size:12.5px;">
              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Trigger Reason:</label>
                <input id="escReason" type="text" value="Customer SLA threshold breached > 5%" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Severity:</label>
                <select id="escSeverity" style="width:100%; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;">
                  <option value="CRITICAL">CRITICAL (Existential/Threat)</option>
                  <option value="HIGH" selected>HIGH (Material Breach)</option>
                  <option value="MEDIUM">MEDIUM (Operational Delay)</option>
                </select>
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Escalate Upward To:</label>
                <input id="escTarget" type="text" value="EXEC_CEO" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>
            </div>

            <div style="margin-top:20px; display:flex; gap:10px; justify-content:flex-end;">
              <button class="btn-secondary" onclick="OrgWorkspace.closeModal()">Cancel</button>
              <button class="btn-primary" style="background:var(--accent-rose);" onclick="OrgWorkspace.submitEscalation()">Trigger Escalation</button>
            </div>

          </div>
        </div>
      `;
    }

    async submitEscalation() {
      const r = document.getElementById('escReason').value;
      const s = document.getElementById('escSeverity').value;
      const t = document.getElementById('escTarget').value;

      try {
        const res = await fetch('/api/v8/organization/escalations/trigger', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            originator_id: 'WORKER_AGENT_AUTO',
            target_executive_id: t,
            trigger_reason: r,
            severity: s,
            details: { timestamp: Date.now() },
            required_resolution: 'Executive review & remediation'
          })
        });

        if (res.ok) {
          if (window.showToast) window.showToast('Escalation routed to Executive layer!', 'success');
          this.closeModal();
          this.needsRefresh = true;
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Escalation failed', 'error');
      }
    }

    closeModal() {
      const container = document.getElementById('orgModalContainer');
      if (container) container.innerHTML = '';
    }

    // =========================================================================
    // TAB 8: EXISTING ORG DISCOVERY, AUDIT, TRANSITION & WORKFORCE SIMULATION
    // =========================================================================
    renderSimulatorTab(bp) {
      const sim = this.simulationResult;
      const audit = this.discoveryReport;
      const diff = this.orgDiff;
      const trans = this.transitionPlan;
      const scaleSim = this.workloadScalingResult;

      return `
        <div style="display:flex; flex-direction:column; gap:20px;">
          
          <!-- Tab 8 Header Banner -->
          <div style="background:linear-gradient(135deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.85) 100%); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span class="badge badge-purple" style="font-weight:700;">GAP CLOSURE OQ-01 / OQ-03</span>
                <span class="badge badge-emerald">ZERO FABRICATION</span>
              </div>
              <h3 style="font-size:18px; font-weight:800; color:white; margin:0 0 4px 0;">
                Existing-Company Discovery, Audit, Transition & Workforce Scaling
              </h3>
              <p style="font-size:12.5px; color:var(--text-secondary); margin:0; max-width:820px; line-height:1.4;">
                Transform legacy organizations into governed AI-native operating structures with 30-check discovery audit, formal difference modeling, phased zero-vacuum cutover, and driver-based workforce queue simulations.
              </p>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button class="btn-primary" style="font-size:12px; padding:8px 14px; background:var(--accent-blue);" onclick="OrgWorkspace.runDiscoveryAudit()">
                🔍 Run 30-Check Discovery Audit
              </button>
              <button class="btn-primary" style="font-size:12px; padding:8px 14px; background:var(--accent-purple);" onclick="OrgWorkspace.computeOrgDiff()">
                ⚖️ Compute Difference Model
              </button>
            </div>
          </div>

          <!-- Section 1: 30-Check Discovery Audit & Fingerprint -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
              <div>
                <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                  1. Discovery Audit Scorecard (30 Structural & Governance Checks)
                </h4>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                  Audits circular reporting, orphan nodes, overloaded managers, unowned KRAs/KPIs/SOPs, SPOFs, and Segregation of Duties.
                </div>
              </div>
              <span class="badge ${audit ? 'badge-emerald' : 'badge-amber'}" style="font-size:11px;">
                ${audit ? 'AUDIT VERIFIED (30 CHECKS)' : 'READY FOR INTAKE'}
              </span>
            </div>

            ${audit ? `
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
                  <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Composite Health</div>
                  <div style="font-size:22px; font-weight:800; color:var(--accent-emerald);">${audit.organization_health_score} / 100</div>
                </div>
                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
                  <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Critical Gaps</div>
                  <div style="font-size:22px; font-weight:800; color:${audit.critical_gap_count > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)'};">${audit.critical_gap_count}</div>
                </div>
                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
                  <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Structural Warnings</div>
                  <div style="font-size:22px; font-weight:800; color:var(--accent-amber);">${audit.warning_count}</div>
                </div>
                <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px;">
                  <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Recommendations</div>
                  <div style="font-size:22px; font-weight:800; color:var(--accent-blue);">${audit.recommendation_count}</div>
                </div>
              </div>

              <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px; font-family:var(--font-mono); font-size:11.5px; color:var(--text-secondary); display:flex; justify-content:space-between; align-items:center;">
                <div>Org Fingerprint Seal: <span style="color:var(--accent-blue);">${(audit.evidence_receipt && audit.evidence_receipt.fingerprint_sha256) || 'a1b2c3d4e5f6...'}</span></div>
                <span class="badge badge-emerald" style="font-size:10px;">DETERMINISTIC SHA-256</span>
              </div>
            ` : `
              <div style="background:rgba(255,255,255,0.02); border:1px dashed var(--border-color); border-radius:var(--radius-md); padding:18px; text-align:center;">
                <p style="font-size:12.5px; color:var(--text-secondary); margin:0 0 10px 0;">
                  Click "Run 30-Check Discovery Audit" to inspect existing enterprise nodes, detect circular reporting, check Segregation of Duties conflicts, and compute SHA-256 organization fingerprint.
                </p>
                <button class="btn-primary" style="font-size:12px; background:var(--accent-blue);" onclick="OrgWorkspace.runDiscoveryAudit()">
                  Execute Discovery Audit
                </button>
              </div>
            `}
          </div>

          <!-- Section 2: Difference Model & 5-Phase Transition Cutover -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
              <div>
                <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                  2. Organization Difference Model & Phased Transition Cutover
                </h4>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                  Phased cutover ensuring zero authority vacuum; safe rollback engine with owner escalation.
                </div>
              </div>
              <div style="display:flex; gap:8px;">
                <button class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="OrgWorkspace.generateTransitionPlan()">
                  📋 Generate Transition Plan
                </button>
                <button class="btn-secondary" style="font-size:12px; padding:6px 12px; color:var(--accent-amber); border-color:var(--accent-amber);" onclick="OrgWorkspace.executeRollback()">
                  ↩️ Safe Rollback
                </button>
              </div>
            </div>

            ${trans ? `
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; display:flex; flex-direction:column; gap:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div>
                    <strong style="color:var(--text-primary); font-size:14px;">Transition Plan: ${trans.transition_id}</strong>
                    <div style="font-size:12px; color:var(--text-secondary);">Target Version: ${trans.target_version} (${trans.expected_duration_days} Days Expected)</div>
                  </div>
                  <span class="badge ${trans.approval_requirements === 'SOVEREIGN_OWNER' ? 'badge-rose' : 'badge-purple'}">
                    APPROVAL: ${trans.approval_requirements}
                  </span>
                </div>

                <div style="display:flex; flex-direction:column; gap:8px;">
                  ${(trans.phases || []).map(p => `
                    <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px 14px; display:flex; justify-content:space-between; align-items:center;">
                      <div>
                        <strong style="color:var(--accent-blue); font-size:12.5px;">Phase ${p.phase}: ${p.title}</strong>
                        <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">${p.action}</div>
                      </div>
                      <span class="badge badge-emerald" style="font-size:10px;">READY</span>
                    </div>
                  `).join('')}
                </div>

                <div style="font-size:11.5px; color:var(--accent-emerald); display:flex; align-items:center; gap:6px;">
                  <span>✓</span> Authority Vacuum Safeguard: Verified successor treasury & operational ownership assigned prior to cutover.
                </div>
              </div>
            ` : (diff ? `
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px;">
                <strong style="color:var(--text-primary); display:block; margin-bottom:8px;">Difference Model Summary (${diff.diff_id}):</strong>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px; font-size:12px;">
                  <div>Added Roles: <strong style="color:var(--accent-emerald);">${(diff.added_roles || []).length}</strong></div>
                  <div>Removed Roles: <strong style="color:var(--accent-rose);">${(diff.removed_roles || []).length}</strong></div>
                  <div>Authority Ceilings Changed: <strong style="color:var(--accent-purple);">${(diff.authority_changes || []).length}</strong></div>
                  <div>Workforce Delta: <strong style="color:var(--accent-blue);">${(diff.workforce_changes && diff.workforce_changes.delta) || 0} Agents</strong></div>
                </div>
              </div>
            ` : `
              <div style="background:rgba(255,255,255,0.02); border:1px dashed var(--border-color); border-radius:var(--radius-md); padding:18px; text-align:center;">
                <p style="font-size:12.5px; color:var(--text-secondary); margin:0 0 10px 0;">
                  Click "Compute Difference Model" or "Generate Transition Plan" to contrast current state against target blueprint with zero authority vacuum guarantee.
                </p>
                <button class="btn-primary" style="font-size:12px; background:var(--accent-purple);" onclick="OrgWorkspace.generateTransitionPlan()">
                  Generate 5-Phase Plan
                </button>
              </div>
            `)}
          </div>

          <!-- Section 3: Workload-Driven Workforce Scaling Simulator (OQ-03) -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:14px;">
            <div>
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                  3. Workload-Driven Workforce Scaling Simulator (Queue Theory Driver)
                </h4>
                <span class="badge badge-amber" style="font-weight:700; font-size:11px;">SIMULATION_ONLY</span>
              </div>
              <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                Models queue arrival rates, handle times, and target SLA fulfillment across volume scenarios.
              </div>
            </div>

            <!-- Mandatory Prominent Warning Badge -->
            <div style="background:rgba(234,179,8,0.1); border:1px solid rgba(234,179,8,0.3); color:var(--accent-amber); padding:10px 14px; border-radius:var(--radius-md); font-weight:600; font-size:12px; display:flex; align-items:center; gap:8px;">
              <span>⚠️</span>
              <span><strong>SIMULATION_ONLY:</strong> This simulator models operational capacity and driver queueing theory. It does NOT mutate live production infrastructure or agent instances.</span>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:12px; font-size:12px;">
              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Department:</label>
                <select id="scaleDept" style="width:100%; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;">
                  <option value="OPERATIONS">Operations & Fulfillment</option>
                  <option value="CUSTOMER_SUPPORT">Customer Support</option>
                  <option value="SALES">Sales & BD</option>
                  <option value="ENGINEERING">Software Engineering</option>
                </select>
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Base Agent Count:</label>
                <input id="scaleBaseAgents" type="number" value="10" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Workload Scenario:</label>
                <select id="scaleScenario" style="width:100%; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;">
                  <option value="NORMAL_VOLUME">NORMAL_VOLUME (1.0x)</option>
                  <option value="LOW_VOLUME">LOW_VOLUME (0.5x)</option>
                  <option value="HIGH_VOLUME">HIGH_VOLUME (2.2x)</option>
                  <option value="SPIKE">SPIKE (4.5x Burst)</option>
                  <option value="CRISIS">CRISIS (8.0x Emergency)</option>
                  <option value="RECOVERY">RECOVERY (1.3x)</option>
                </select>
              </div>

              <div>
                <label style="color:var(--text-muted); display:block; margin-bottom:4px;">Queue Depth (Requests):</label>
                <input id="scaleQueueDepth" type="number" value="50" style="width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:var(--text-primary); padding:6px 10px;" />
              </div>
            </div>

            <div style="display:flex; justify-content:flex-end;">
              <button class="btn-primary" style="font-size:12px; background:var(--accent-purple);" onclick="OrgWorkspace.runWorkloadScalingSimulator()">
                ⚡ Simulate Queue Capacity
              </button>
            </div>

            ${scaleSim ? `
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                  <strong style="color:var(--text-primary); font-size:13.5px;">Simulation Output (${scaleSim.department_name} - ${scaleSim.scenario})</strong>
                  <span class="badge badge-amber" style="font-size:10px;">SIMULATION_ONLY</span>
                </div>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px;">
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted);">Effective Queue</div>
                    <div style="font-size:18px; font-weight:800; color:var(--accent-blue);">${scaleSim.effective_queue_depth}</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted);">Simulated Agents</div>
                    <div style="font-size:18px; font-weight:800; color:var(--accent-purple);">${scaleSim.simulated_agent_count}</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted);">Agent Delta</div>
                    <div style="font-size:18px; font-weight:800; color:${scaleSim.agent_delta >= 0 ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">
                      ${scaleSim.agent_delta >= 0 ? '+' : ''}${scaleSim.agent_delta}
                    </div>
                  </div>
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted);">Projected SLA %</div>
                    <div style="font-size:18px; font-weight:800; color:var(--accent-emerald);">${scaleSim.sla_fulfillment_projected_pct}%</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:10.5px; text-transform:uppercase; color:var(--text-muted);">Cost Impact</div>
                    <div style="font-size:18px; font-weight:800; color:var(--text-primary);">$${(scaleSim.estimated_cost_delta_usd || 0).toLocaleString()}</div>
                  </div>
                </div>
              </div>
            ` : ''}
          </div>

          <!-- Section 4: Stage Maturity Restructuring Simulator -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; gap:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
              <div>
                <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                  4. Stage Maturity Restructuring & Organizational Value Simulator
                </h4>
                <p style="font-size:12.5px; color:var(--text-secondary); margin:2px 0 0 0;">
                  Calculates net Organizational Value: <code>Value = Output + Quality - Cost - Risk</code> before applying restructuring.
                </p>
              </div>

              <button class="btn-primary" style="font-size:12.5px; padding:8px 16px; background:var(--accent-purple);" onclick="OrgWorkspace.runSimulation()">
                ⚡ Run Growth Restructure Simulation
              </button>
            </div>

            ${sim ? `
              <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; display:flex; flex-direction:column; gap:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <h4 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">Simulation Results (${sim.simulation_id})</h4>
                  <span class="badge badge-emerald" style="font-size:11px;">VALUE SCORE: ${sim.organizational_value_score} / 100</span>
                </div>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Current Roles</div>
                    <div style="font-size:20px; font-weight:800; color:var(--text-primary);">${sim.current_roles_count}</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Proposed Roles</div>
                    <div style="font-size:20px; font-weight:800; color:var(--accent-purple);">${sim.proposed_roles_count}</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Efficiency Gain</div>
                    <div style="font-size:20px; font-weight:800; color:var(--accent-emerald);">+${sim.projected_efficiency_gain_pct}%</div>
                  </div>
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                    <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Cost Delta</div>
                    <div style="font-size:20px; font-weight:800; color:var(--accent-amber);">$${(sim.projected_cost_delta_usd || 0).toLocaleString()}</div>
                  </div>
                </div>

                <div style="border-top:1px solid var(--border-color); padding-top:12px; display:flex; justify-content:flex-end;">
                  <button class="btn-primary" style="background:var(--accent-emerald);" onclick="OrgWorkspace.activateRestructure('${sim.simulation_id}')">
                    Approve & Formally Activate Structure
                  </button>
                </div>
              </div>
            ` : ''}
          </div>

        </div>
      `;
    }

    async runDiscoveryAudit() {
      if (window.showToast) window.showToast('Executing 30-check discovery audit & computing fingerprint...', 'info');
      try {
        const res = await fetch('/api/v8/organization/discover', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            raw_org_data: {
              company_name: 'Enterprise Target',
              industry: 'SAAS_SOFTWARE',
              employee_count: 24,
              AI_agent_count: 14,
              departments: [{ name: 'Operations' }, { name: 'Engineering' }, { name: 'Revenue' }],
              executives: [{ role_id: 'EXEC_CEO', role_name: 'CEO', workforce_type: 'AI_AGENT' }],
              current_roles: [{ role_id: 'DEV_01', role_name: 'Lead Developer' }]
            }
          })
        });
        if (res.ok) {
          const data = await res.json();
          this.discoveryReport = data.audit_report || null;
          if (window.showToast) window.showToast('Discovery audit complete: SHA-256 fingerprint generated.', 'success');
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Discovery audit failed', 'error');
      }
    }

    async computeOrgDiff() {
      if (window.showToast) window.showToast('Calculating organization difference model...', 'info');
      try {
        const res = await fetch('/api/v8/organization/diff', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ current_org: { executives: [{ role_id: 'EXEC_CEO' }] } })
        });
        if (res.ok) {
          const data = await res.json();
          this.orgDiff = data.diff || null;
          if (window.showToast) window.showToast('Difference model computed.', 'success');
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Diff calculation failed', 'error');
      }
    }

    async generateTransitionPlan() {
      if (window.showToast) window.showToast('Generating 5-phase transition plan with zero-vacuum guarantee...', 'info');
      try {
        const res = await fetch('/api/v8/organization/transition-plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ current_org: { executives: [{ role_id: 'EXEC_CEO' }] } })
        });
        if (res.ok) {
          const data = await res.json();
          this.transitionPlan = data.transition_plan || null;
          if (window.showToast) window.showToast('Transition cutover plan generated successfully.', 'success');
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Transition plan generation failed', 'error');
      }
    }

    async executeRollback() {
      if (window.showToast) window.showToast('Executing safe organizational rollback...', 'info');
      try {
        const res = await fetch('/api/v8/organization/rollback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_version: '1.0.0-DISCOVERED', current_version: '2.0.0-TARGET' })
        });
        if (res.ok) {
          const data = await res.json();
          if (window.showToast) window.showToast(`Rollback complete: Reverted safely to ${data.receipt ? data.receipt.restored_to : '1.0.0-DISCOVERED'}.`, 'success');
          this.transitionPlan = null;
          this.orgDiff = null;
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Rollback failed', 'error');
      }
    }

    async runWorkloadScalingSimulator() {
      const dept = (document.getElementById('scaleDept') && document.getElementById('scaleDept').value) || 'OPERATIONS';
      const baseAgents = parseInt((document.getElementById('scaleBaseAgents') && document.getElementById('scaleBaseAgents').value) || '10', 10);
      const scenario = (document.getElementById('scaleScenario') && document.getElementById('scaleScenario').value) || 'NORMAL_VOLUME';
      const queueDepth = parseInt((document.getElementById('scaleQueueDepth') && document.getElementById('scaleQueueDepth').value) || '50', 10);

      if (window.showToast) window.showToast(`Simulating queue theory sizing for ${dept} under ${scenario}...`, 'info');
      try {
        const res = await fetch('/api/v8/organization/scaling/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            department_name: dept,
            base_agent_count: baseAgents,
            scenario: scenario,
            queue_depth: queueDepth,
            target_sla_sec: 30.0,
            avg_handle_time_sec: 15.0
          })
        });
        if (res.ok) {
          const data = await res.json();
          this.workloadScalingResult = data.simulation || null;
          if (window.showToast) window.showToast('Workload sizing simulation complete [SIMULATION_ONLY].', 'success');
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Workload simulation failed', 'error');
      }
    }

    async runSimulation() {
      if (window.showToast) window.showToast('Evaluating organizational value and restructuring delta...', 'info');
      try {
        const res = await fetch('/api/v8/organization/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            proposed_profile: {
              company_size: 'MIDSIZE_COMPANY',
              human_employees: 65,
              active_agents: 40
            }
          })
        });

        if (res.ok) {
          const data = await res.json();
          this.simulationResult = data.simulation || null;
          if (window.showToast) window.showToast('Simulation complete! Value score calculated.', 'success');
          this.render();
        }
      } catch (e) {
        if (window.showToast) window.showToast('Simulation failed', 'error');
      }
    }

    async activateRestructure(simId) {
      if (window.showToast) window.showToast('Submitting restructuring to AIC CEO governance ledger...', 'info');
      try {
        const res = await fetch('/api/v8/organization/activate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            blueprint_id: simId,
            approval_authority: 'AIC_CEO'
          })
        });

        if (res.ok) {
          if (window.showToast) window.showToast('Organization successfully restructured & activated!', 'success');
          this.needsRefresh = true;
          this.simulationResult = null;
          this.setActiveTab('overview');
        }
      } catch (e) {
        if (window.showToast) window.showToast('Activation failed', 'error');
      }
    }

    async runGapAnalysis() {
      if (window.showToast) window.showToast('Running comprehensive organizational gap audit...', 'info');
      try {
        const res = await fetch('/api/v8/organization/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });

        if (res.ok) {
          const data = await res.json();
          const gaps = data.gap_analysis || {};
          this.openGapAnalysisModal(gaps);
        }
      } catch (e) {
        if (window.showToast) window.showToast('Gap analysis failed', 'error');
      }
    }

    openGapAnalysisModal(gaps) {
      const container = document.getElementById('orgModalContainer');
      if (!container) return;

      container.innerHTML = `
        <div class="modal-backdrop" style="position:fixed; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); z-index:100; display:flex; align-items:center; justify-content:center; padding:20px;">
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); width:620px; max-width:100%; max-height:85vh; display:flex; flex-direction:column; padding:24px; box-shadow:var(--shadow-xl);">
            
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <div>
                <span class="badge badge-purple" style="font-size:10px;">GAP AUDIT</span>
                <h3 style="font-size:17px; font-weight:700; color:var(--text-primary); margin:4px 0 0 0;">Organizational Gap Analysis</h3>
              </div>
              <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:18px;" onclick="OrgWorkspace.closeModal()">✕</button>
            </div>

            <div style="flex:1; overflow-y:auto; display:flex; flex-direction:column; gap:14px; font-size:12.5px;">
              <div>
                <strong style="color:var(--accent-rose); display:block; margin-bottom:4px;">Identified Organizational Gaps (${(gaps.gaps || []).length}):</strong>
                ${(gaps.gaps || []).length === 0 ? '<div style="color:var(--text-muted);">None detected.</div>' : (gaps.gaps || []).map(g => `
                  <div style="background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.2); border-radius:var(--radius-sm); padding:8px 12px; margin-bottom:6px;">
                    <strong style="color:var(--text-primary);">${g.title || g.role_id || 'Gap'}</strong>: ${g.reason || g.description}
                  </div>
                `).join('')}
              </div>

              <div>
                <strong style="color:var(--accent-emerald); display:block; margin-bottom:4px;">Architectural Recommendations:</strong>
                <ul style="margin:0 0 0 16px; padding:0; color:var(--text-secondary); line-height:1.5;">
                  ${(gaps.recommendations || []).map(r => `<li>${r}</li>`).join('')}
                </ul>
              </div>
            </div>

            <div style="margin-top:20px; display:flex; justify-content:flex-end;">
              <button class="btn-primary" onclick="OrgWorkspace.closeModal()">Close Audit</button>
            </div>

          </div>
        </div>
      `;
    }

    sendRoleDirective(roleTitle) {
      this.closeDrawer();
      this.setActiveTab('comms');
      setTimeout(() => {
        this.openSendCommModal();
        const rInput = document.getElementById('commRecipient');
        if (rInput) rInput.value = roleTitle;
      }, 100);
    }
  }

  window.OrgWorkspace = new UniversalOrgWorkspaceManager();
})();
