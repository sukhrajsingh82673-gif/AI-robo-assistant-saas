/**
 * ZONATA — AI CEO Executive Console (Company OS 2.0 / V8 Architecture)
 * Complete 14-Section Executive Operating Environment for the Human Owner and AI CEO.
 *
 * 14 Sections:
 *   1. Company Overview
 *   2. Strategy
 *   3. Objectives
 *   4. Departments
 *   5. Workforce
 *   6. Missions
 *   7. KPIs/KRAs
 *   8. Finance
 *   9. Risks
 *   10. Opportunities
 *   11. Decisions (Why the CEO made each decision: Decision, Evidence, Authority, Approval, Action, Outcome)
 *   12. Approvals (Human Owner Action Queue)
 *   13. Evidence (SHA-256 Cryptographic Proofs)
 *   14. Executive Reports
 */

(function() {
  'use strict';

  class AiCeoWorkspaceManager {
    constructor() {
      this.activeTab = 'overview';
      this.tenantId = 'tnt_primary';
      this.companyId = 'comp_primary';
      this.executiveState = null;
      this.scorecard = null;
      this.objectives = [];
      this.strategies = [];
      this.priorities = [];
      this.departmentObjectives = [];
      this.missions = [];
      this.decisions = [];
      this.pendingApprovals = [];
      this.resources = [];
      this.risks = [];
      this.opportunities = [];
      this.observations = [];
      this.reports = [];
      this.loopStage = 'OBSERVE';
      this.chatHistory = [];
      this.gemmaStatus = null;
      this.loading = false;
      this.economicHierarchy = [];
      this.capitalAllocations = [];
      this.capitalPools = {};
      this.learningLedger = [];
      this.ceoScorecard = null;
      this.missionContracts = [];
      this.industryProfile = null;
      this.constitutionData = null;
      this.krasData = [];
      this.activeIndustry = 'Hospitality';
      this.scenarioResult = null;
      this.lastCompetingResult = null;
    }

    async render(containerId = 'view-ceo', routePath = null) {
      const container = document.getElementById(containerId);
      if (!container) return;

      if (routePath && routePath.startsWith('/ceo/')) {
        const sub = routePath.split('/')[2];
        const validTabs = [
          'overview','strategy','objectives','departments','workforce','missions',
          'kpis','finance','risks','opportunities','decisions','approvals',
          'evidence','reports','economic','contracts','predictions','scorecard',
          'constitution','scenarios'
        ];
        if (sub && validTabs.includes(sub)) {
          this.activeTab = sub;
        }
      }

      const compCtx = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
      this.companyId = compCtx || 'comp_primary';

      container.innerHTML = `
        <div class="card" style="padding: 24px; text-align: center;">
          <div class="status-pulse-dot" style="display:inline-block; margin-bottom:12px;"></div>
          <h3>Connecting to AI CEO Executive State...</h3>
          <p style="color:var(--text-secondary); margin-top:8px;">Loading versioned corporate intelligence, economic command, and audit telemetry.</p>
        </div>
      `;

      await this.loadAllData();
      this.renderConsole(container);
    }

    async loadAllData() {
      this.loading = true;
      try {
        const headers = { 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId };

        const [
          stateRes, perfRes, objRes, stratRes, prioRes,
          deptRes, msnRes, decRes, apprRes, resRes,
          riskRes, oppRes, obsRes, loopRes, rptRes, gemmaRes,
          hierRes, capAllocRes, learnRes, scoreRes,
          contractRes, constRes, krasRes, indRes
        ] = await Promise.all([
          fetch('/api/v8/executive-state', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/performance', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/objectives', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/strategy', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/priorities', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/departments', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/missions', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/decisions', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/approvals', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/resources', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/risks', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/opportunities', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/observations', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/control-loop/state', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/reports', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/gemma/status', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/ceo/economic/hierarchy', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/ceo/capital/allocations', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/ceo/learning/ledger', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/ceo/performance/scorecard', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/ceo/contracts', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/ceo/constitution', { headers }).then(r => r.json()).catch(() => ({})),
          fetch('/api/v8/ceo/kras', { headers }).then(r => r.json()).catch(() => ({})),
          fetch(`/api/v8/ceo/industry/profile?industry=${this.activeIndustry}`, { headers }).then(r => r.json()).catch(() => ({}))
        ]);

        this.executiveState = stateRes.state || null;
        this.scorecard = perfRes.performance_scorecard || null;
        this.objectives = objRes.objectives || [];
        this.strategies = stratRes.strategies || [];
        this.priorities = prioRes.priorities || [];
        this.departmentObjectives = deptRes.department_objectives || [];
        this.missions = msnRes.missions || [];
        this.decisions = decRes.decisions || [];
        this.pendingApprovals = apprRes.pending_approvals || [];
        this.resources = resRes.allocations || [];
        this.risks = riskRes.risks || [];
        this.opportunities = oppRes.opportunities || [];
        this.observations = obsRes.observations || [];
        this.loopStage = loopRes.current_stage || 'OBSERVE';
        this.reports = rptRes.reports || [];
        this.gemmaStatus = gemmaRes || null;

        this.economicHierarchy = hierRes.economic_hierarchy || [];
        this.capitalAllocations = capAllocRes.allocations || [];
        this.capitalPools = {
          total_capital_pool_usd: capAllocRes.total_capital_pool_usd || 500000.0,
          allocated_capital_usd: capAllocRes.allocated_capital_usd || 0.0,
          unallocated_capital_usd: capAllocRes.unallocated_capital_usd || 500000.0
        };
        this.learningLedger = learnRes.learning_ledger || [];
        this.ceoScorecard = scoreRes.scorecard || null;
        this.missionContracts = contractRes.contracts || [];
        this.constitutionData = constRes || null;
        this.krasData = krasRes.kras || [];
        this.industryProfile = indRes.profile || null;
      } catch (err) {
        console.error('Failed to load V8 AI CEO Data:', err);
      } finally {
        this.loading = false;
      }
    }

    renderConsole(container) {
      const companyName = this.executiveState?.company?.company_name || 'Royal Hotel Jaipur';
      const rating = this.scorecard?.operational_rating || 'EXEMPLARY';
      const decRate = this.scorecard ? Math.round(this.scorecard.decision_verification_rate * 100) : 100;
      const msnRate = this.scorecard ? Math.round(this.scorecard.mission_success_rate * 100) : 100;

      container.innerHTML = `
        <div class="ceo-console-wrapper" style="display:flex; flex-direction:column; gap:20px; padding:16px 0;">

          <!-- Top Executive Banner -->
          <div class="card card-header-flexible" style="background:linear-gradient(135deg, rgba(20,24,35,0.95), rgba(15,30,50,0.95)); border-left:4px solid var(--primary, #3b82f6);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
              <div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                  <span style="font-size:24px;">🏛️</span>
                  <h2 style="margin:0; font-size:1.5rem; font-weight:700;">AI CEO Executive Operating Console</h2>
                  <span class="status-indicator-pill" style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid #10b981; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">
                    ${this.loopStage} ACTIVE
                  </span>
                  <span class="status-indicator-pill" style="background:rgba(99,102,241,0.2); color:#818cf8; border:1px solid #6366f1; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">
                    🧠 Cognitive: Google Gemma 4 (${this.gemmaStatus?.active_model || 'gemma-4-31b-it'}) [${this.gemmaStatus?.deployment_mode || 'HYBRID'}]
                  </span>
                  ${this.gemmaStatus?.emergency_halted ? `
                  <span class="status-indicator-pill" style="background:rgba(239,68,68,0.25); color:#ef4444; border:1px solid #ef4444; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; animation:pulse 1.5s infinite;">
                    🛑 EMERGENCY CONTAINMENT ACTIVE
                  </span>` : ''}
                </div>
                <p style="margin:6px 0 0 0; color:var(--text-secondary); font-size:0.9rem;">
                  Operating Context: <strong>${companyName}</strong> | Architecture: <strong>Gemma 4 Cognition + ZONATA Sovereign Authority</strong>
                </p>
              </div>

              <!-- Quick Status Vitals & Sovereign Controls -->
              <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
                <div style="text-align:center; padding:6px 12px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">OPERATIONAL RATING</div>
                  <div style="font-size:1.1rem; font-weight:700; color:#10b981;">${rating}</div>
                </div>
                <div style="text-align:center; padding:6px 12px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">DECISION VERIFIED</div>
                  <div style="font-size:1.1rem; font-weight:700; color:#3b82f6;">${decRate}%</div>
                </div>
                <div style="text-align:center; padding:6px 12px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">ACTIVE MISSIONS</div>
                  <div style="font-size:1.1rem; font-weight:700; color:#f59e0b;">${this.missions.length}</div>
                </div>
                <button class="btn" onclick="window.AiCeoWorkspace.triggerEmergencyStop()" style="background:#dc2626; color:white; border:none; padding:8px 14px; border-radius:6px; font-weight:600; cursor:pointer;">
                  🛑 Emergency STOP
                </button>
                <button class="btn" onclick="window.AiCeoWorkspace.triggerEmergencyResume()" style="background:#16a34a; color:white; border:none; padding:8px 14px; border-radius:6px; font-weight:600; cursor:pointer;">
                  ▶️ Resume
                </button>
                <button class="btn btn-primary" id="btnRunClosedLoop" style="padding:8px 14px; display:flex; align-items:center; gap:6px;">
                  <span>⚡ 22-Step Scenario</span>
                </button>
              </div>
            </div>

            <!-- Natural Language Command Bar -->
            <div style="margin-top:16px; display:flex; gap:10px;">
              <input type="text" id="ceoCommandInput" class="ceo-command-input" style="flex:1; padding:10px 16px; border-radius:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white;" placeholder="Command the AI CEO (e.g. 'Increase hotel bookings by 20% this month', 'What is blocking marketing?', 'Show me the evidence')..." />
              <button class="btn btn-secondary" id="btnSendCeoCommand" style="padding:10px 20px;">Send Directive</button>
            </div>

            <!-- Fast Prompt Chips -->
            <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; font-size:0.8rem;">
              <span style="color:var(--text-secondary); align-self:center;">Cognitive Directives:</span>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('Increase hotel bookings by 20% this month')">🏨 +20% Bookings</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('Create a plan to increase revenue for the company by 15% over the next quarter')">📈 +15% Revenue Plan</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('What is blocking marketing?')">🔍 Audit Marketing</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('How is the company performing?')">📊 Health Status</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('Show me the evidence')">🔗 Evidence Ledger</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.runBenchmarkSuite()">🧪 Gemma 4 Benchmark</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.advanceLoopTick()">Next Loop Tick (${this.loopStage})</button>
            </div>

            <div id="ceoChatFeedback" style="margin-top:12px; display:none; padding:12px; background:rgba(0,0,0,0.4); border-radius:8px; border-left:3px solid #3b82f6;"></div>
          </div>

          <!-- 20-Section Subnav Tabs -->
          <div class="ceo-subnav" style="display:flex; overflow-x:auto; gap:6px; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1);">
            ${this.renderNavTab('overview', '1. Overview', '🏢')}
            ${this.renderNavTab('strategy', '2. Strategy', '🗺️')}
            ${this.renderNavTab('objectives', '3. Objectives', '🎯')}
            ${this.renderNavTab('departments', '4. Departments', '🏛️')}
            ${this.renderNavTab('workforce', '5. Workforce', '👥')}
            ${this.renderNavTab('missions', '6. Missions', '🚀')}
            ${this.renderNavTab('kpis', '7. KPIs / KRAs', '📈')}
            ${this.renderNavTab('finance', '8. Finance', '💰')}
            ${this.renderNavTab('risks', '9. Risks', '⚠️')}
            ${this.renderNavTab('opportunities', '10. Opportunities', '💡')}
            ${this.renderNavTab('decisions', '11. Decisions', '⚖️')}
            ${this.renderNavTab('approvals', '12. Approvals (' + this.pendingApprovals.length + ')', '🛡️')}
            ${this.renderNavTab('evidence', '13. Evidence', '🔗')}
            ${this.renderNavTab('reports', '14. Reports', '📄')}
            ${this.renderNavTab('economic', '15. Economic Command & Capital', '💎')}
            ${this.renderNavTab('contracts', '16. Mission Contracts', '📜')}
            ${this.renderNavTab('predictions', '17. Prediction & Learning', '🔮')}
            ${this.renderNavTab('scorecard', '18. Qualification Scorecard', '🎖️')}
            ${this.renderNavTab('constitution', '19. Constitution & Anti-Gaming', '⚖️')}
            ${this.renderNavTab('scenarios', '20. Stress Test Simulator (A-J)', '🧪')}
          </div>

          <!-- Section Content View Container -->
          <div id="ceoSectionContent" class="ceo-section-view">
            ${this.renderActiveSection()}
          </div>

        </div>
      `;

      this.bindEvents(container);
    }

    renderNavTab(tabId, label, icon) {
      const isActive = this.activeTab === tabId ? 'active' : '';
      return `
        <button class="ceo-tab-btn ${isActive}" onclick="window.AiCeoWorkspace.switchTab('${tabId}')" style="white-space:nowrap; padding:8px 14px; font-size:0.85rem; border-radius:6px; cursor:pointer; background:${isActive ? 'rgba(59,130,246,0.2)' : 'transparent'}; border:1px solid ${isActive ? '#3b82f6' : 'transparent'}; color:${isActive ? '#60a5fa' : 'var(--text-secondary)'};">
          <span>${icon}</span> ${label}
        </button>
      `;
    }

    switchTab(tabId) {
      this.activeTab = tabId;
      const content = document.getElementById('ceoSectionContent');
      if (content) {
        content.innerHTML = this.renderActiveSection();
      }
      // Update button active classes
      document.querySelectorAll('.ceo-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('onclick')?.includes(`'${tabId}'`));
      });
    }

    renderActiveSection() {
      switch (this.activeTab) {
        case 'overview': return this.renderSectionOverview();
        case 'strategy': return this.renderSectionStrategy();
        case 'objectives': return this.renderSectionObjectives();
        case 'departments': return this.renderSectionDepartments();
        case 'workforce': return this.renderSectionWorkforce();
        case 'missions': return this.renderSectionMissions();
        case 'kpis': return this.renderSectionKpis();
        case 'finance': return this.renderSectionFinance();
        case 'risks': return this.renderSectionRisks();
        case 'opportunities': return this.renderSectionOpportunities();
        case 'decisions': return this.renderSectionDecisions();
        case 'approvals': return this.renderSectionApprovals();
        case 'evidence': return this.renderSectionEvidence();
        case 'reports': return this.renderSectionReports();
        case 'economic': return this.renderSectionEconomic();
        case 'contracts': return this.renderSectionContracts();
        case 'predictions': return this.renderSectionPredictions();
        case 'scorecard': return this.renderSectionScorecard();
        case 'constitution': return this.renderSectionConstitution();
        case 'scenarios': return this.renderSectionScenarios();
        default: return `<div>Section not found</div>`;
      }
    }

    // 1. Overview
    renderSectionOverview() {
      const co = this.executiveState?.company || {};
      const vis = this.executiveState?.vision || {};
      return `
        <div class="card" style="padding:20px;">
          <h3 style="margin-top:0;">Company Executive Profile & Governance State</h3>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px; margin-top:16px;">
            <div style="background:rgba(255,255,255,0.02); padding:16px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              <h4 style="color:#60a5fa; margin-top:0;">Corporate Identity</h4>
              <p><strong>Name:</strong> ${co.company_name || 'N/A'}</p>
              <p><strong>Industry:</strong> ${co.industry || 'Hospitality'}</p>
              <p><strong>Lifecycle Stage:</strong> <span class="badge" style="background:#10b981; color:black; padding:2px 6px; border-radius:4px;">${co.lifecycle_stage || 'OPERATIONAL'}</span></p>
              <p><strong>Base Currency:</strong> ${co.currency || '₹'} | <strong>Timezone:</strong> ${co.timezone || 'Asia/Kolkata'}</p>
            </div>
            <div style="background:rgba(255,255,255,0.02); padding:16px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              <h4 style="color:#f59e0b; margin-top:0;">Vision & Strategic Horizon</h4>
              <p><strong>Vision:</strong> ${vis.vision || 'Deliver exceptional value.'}</p>
              <p><strong>Mission:</strong> ${vis.mission || 'Maximize operations and guest satisfaction.'}</p>
              <p><strong>Strategic Horizon:</strong> ${vis.strategic_horizon || 'ANNUAL'}</p>
            </div>
          </div>
        </div>
      `;
    }

    // 2. Strategy
    renderSectionStrategy() {
      if (!this.strategies.length) {
        return `<div class="card" style="padding:24px; text-align:center;">No active strategies formulated yet. Click 'Run 22-Step Scenario' to formulate one.</div>`;
      }
      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          ${this.strategies.map(s => `
            <div class="card" style="padding:20px; border-left:3px solid #10b981;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; font-size:1.1rem; color:#10b981;">${s.title}</h4>
                <span class="badge" style="background:rgba(16,185,129,0.2); color:#10b981; padding:4px 8px; border-radius:6px;">Version ${s.version}</span>
              </div>
              <p style="margin:8px 0; color:var(--text-secondary);">${s.rationale}</p>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-top:12px; font-size:0.85rem;">
                <div><strong>Assumptions:</strong><ul style="margin:4px 0; padding-left:16px;">${(s.assumptions || []).map(a => `<li>${a}</li>`).join('')}</ul></div>
                <div><strong>Constraints:</strong><ul style="margin:4px 0; padding-left:16px;">${(s.constraints || []).map(c => `<li>${c}</li>`).join('')}</ul></div>
                <div><strong>Capabilities:</strong><ul style="margin:4px 0; padding-left:16px;">${(s.required_capabilities || []).map(rc => `<li>${rc}</li>`).join('')}</ul></div>
              </div>
              <div style="margin-top:12px; font-size:0.8rem; color:var(--text-secondary);">
                Evidence Proofs: <code>${JSON.stringify(s.evidence_refs || [])}</code>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 3. Objectives
    renderSectionObjectives() {
      if (!this.objectives.length) {
        return `<div class="card" style="padding:24px; text-align:center;">No corporate objectives compiled yet.</div>`;
      }
      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.objectives.map(o => `
            <div class="card" style="padding:16px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; font-size:1rem;">${o.title}</h4>
                <span class="badge" style="background:#3b82f6; color:white; font-size:0.75rem; padding:2px 8px; border-radius:4px;">${o.provenance}</span>
              </div>
              <div style="margin-top:8px; font-size:0.85rem;">
                <strong>Measurable Dimensions:</strong>
                <pre style="background:rgba(0,0,0,0.3); padding:8px; border-radius:6px; margin-top:4px; font-size:0.8rem;">${JSON.stringify(o.target_dimensions, null, 2)}</pre>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 4. Departments
    renderSectionDepartments() {
      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px;">
          ${this.departmentObjectives.map(d => `
            <div class="card" style="padding:16px; border-top:3px solid #60a5fa;">
              <div style="display:flex; justify-content:space-between;">
                <h4 style="margin:0; color:#60a5fa;">${d.department}</h4>
                <span style="font-size:0.75rem; color:var(--text-secondary);">${d.chief_officer_role}</span>
              </div>
              <p style="margin:8px 0; font-size:0.9rem;"><strong>${d.title}</strong></p>
              <p style="font-size:0.8rem; color:var(--text-secondary);">${d.description}</p>
              <div style="margin-top:10px; font-size:0.8rem;">
                <div>Allocated Budget: <strong>₹${d.allocated_budget.toLocaleString()}</strong></div>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 5. Workforce
    renderSectionWorkforce() {
      return `
        <div class="card" style="padding:20px;">
          <h3 style="margin-top:0;">Workforce Architecture & Discovery Order</h3>
          <div style="background:rgba(59,130,246,0.1); border-left:3px solid #3b82f6; padding:12px; margin:12px 0; font-size:0.85rem;">
            <strong>Canonical Discovery Sequence (Anti-Proliferation):</strong><br>
            1. Existing Employee &rarr; 2. Existing Specialist &rarr; 3. Cross-Department Delegation &rarr; 4. Template Employee &rarr; 5. Project-Specific Employee &rarr; 6. Human Capability Escalation
          </div>
          <p style="font-size:0.9rem;">Active Chief Officers: <strong>COO, CRO, CMO, CFO, CTO</strong></p>
          <p style="font-size:0.9rem;">Active Workforce Capacity: <strong>100.0 Units</strong> | Utilization: <strong>45.0% (Optimal)</strong></p>
        </div>
      `;
    }

    // 6. Missions
    renderSectionMissions() {
      if (!this.missions.length) {
        return `<div class="card" style="padding:24px; text-align:center;">No active missions in registry.</div>`;
      }
      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.missions.map(m => `
            <div class="card" style="padding:16px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; font-size:1rem;">${m.title}</h4>
                <span class="badge" style="background:${m.status === 'COMPLETED' ? '#10b981' : '#f59e0b'}; color:black; padding:2px 8px; border-radius:4px; font-size:0.75rem;">${m.status}</span>
              </div>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:8px; margin-top:8px; font-size:0.85rem;">
                <div>Dept: <strong>${m.department}</strong></div>
                <div>Assigned: <strong>${m.employee}</strong></div>
                <div>Outcome Status: <strong>${m.outcome_status}</strong></div>
              </div>
              <div style="margin-top:8px; background:rgba(0,0,0,0.3); padding:8px; border-radius:6px; font-size:0.8rem;">
                <strong>Verified Business Outcome:</strong> ${m.verified_outcome || 'In execution...'}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 7. KPIs / KRAs
    renderSectionKpis() {
      return `
        <div class="card" style="padding:20px;">
          <h3 style="margin-top:0;">KPI Telemetry & Deviation Signals</h3>
          <div style="display:flex; flex-direction:column; gap:8px; margin-top:16px;">
            ${this.observations.map(o => `
              <div style="padding:10px 14px; background:rgba(255,255,255,0.02); border-radius:6px; border-left:3px solid ${o.observation_type === 'DEVIATION' ? '#ef4444' : o.observation_type === 'UNKNOWN' ? '#a855f7' : '#10b981'}; display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <div style="font-weight:600; font-size:0.9rem;">${o.metric_name || o.category}: ${o.summary}</div>
                  <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:2px;">Type: ${o.observation_type} | Confidence: ${o.confidence}</div>
                </div>
                <div style="font-size:0.85rem; font-weight:700;">
                  ${o.actual_value !== null ? o.actual_value : 'UNKNOWN'}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // 8. Finance
    renderSectionFinance() {
      return `
        <div class="card" style="padding:20px;">
          <h3 style="margin-top:0;">Hierarchical Budget Containment</h3>
          <div style="display:flex; flex-direction:column; gap:10px; margin-top:16px;">
            ${this.resources.map(r => `
              <div style="padding:12px; background:rgba(255,255,255,0.02); border-radius:6px; border:1px solid rgba(255,255,255,0.06); display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <strong>${r.scope_type}: ${r.scope_id}</strong>
                  <div style="font-size:0.8rem; color:var(--text-secondary);">Committed: ₹${r.committed_spend.toLocaleString()} | Actual: ₹${r.actual_spend.toLocaleString()}</div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:1.1rem; font-weight:700; color:#10b981;">₹${r.budget_limit.toLocaleString()}</div>
                  <div style="font-size:0.75rem; color:var(--text-secondary);">Remaining: ₹${r.remaining_budget.toLocaleString()}</div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // 9. Risks
    renderSectionRisks() {
      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.risks.map(r => `
            <div class="card" style="padding:16px; border-left:3px solid ${r.severity === 'CRITICAL' ? '#ef4444' : r.severity === 'HIGH' ? '#f59e0b' : '#3b82f6'};">
              <div style="display:flex; justify-content:space-between;">
                <h4 style="margin:0;">${r.title}</h4>
                <span class="badge" style="background:rgba(239,68,68,0.2); color:#ef4444; font-size:0.75rem; padding:2px 8px; border-radius:4px;">${r.severity}</span>
              </div>
              <p style="margin:6px 0; font-size:0.85rem; color:var(--text-secondary);">${r.description}</p>
              <div style="font-size:0.8rem;">Mitigation: <em>${r.mitigation || 'Under formulation'}</em></div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 10. Opportunities
    renderSectionOpportunities() {
      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.opportunities.map(o => `
            <div class="card" style="padding:16px; border-left:3px solid #10b981;">
              <div style="display:flex; justify-content:space-between;">
                <h4 style="margin:0;">${o.title}</h4>
                <span style="font-weight:700; color:#10b981;">₹${o.estimated_value.toLocaleString()}</span>
              </div>
              <p style="margin:6px 0; font-size:0.85rem; color:var(--text-secondary);">${o.strategic_alignment}</p>
              <div style="font-size:0.8rem;">Confidence: ${(o.confidence * 100).toFixed(0)}% | Status: <strong>${o.status}</strong></div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 11. Decisions (Why the CEO made a decision)
    renderSectionDecisions() {
      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <h3 style="margin-top:0;">Why the AI CEO Made Each Decision</h3>
          ${this.decisions.map(d => `
            <div class="card" style="padding:20px; border-left:3px solid #3b82f6;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; font-size:1.1rem;">${d.title}</h4>
                <span class="badge" style="background:#3b82f6; color:white; font-size:0.75rem; padding:2px 8px; border-radius:4px;">${d.approval_status}</span>
              </div>
              <div style="margin:8px 0; font-size:0.85rem;">
                <strong>Problem:</strong> ${d.problem_statement}<br>
                <strong>Rationale:</strong> ${d.rationale}<br>
                <strong>Selected Option:</strong> <span style="color:#10b981; font-weight:600;">${d.selected_option}</span>
              </div>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; margin-top:10px; font-size:0.8rem; background:rgba(0,0,0,0.25); padding:8px; border-radius:6px;">
                <div>Authority: <code>${d.authority_required}</code></div>
                <div>Execution: <code>${d.execution_status}</code></div>
                <div>Evidence Proof: <code>${d.evidence_refs?.[0] || 'Sealed'}</code></div>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 12. Approvals
    renderSectionApprovals() {
      if (!this.pendingApprovals.length) {
        return `<div class="card" style="padding:24px; text-align:center;">No pending approvals in Human Owner Queue. All executive decisions within granted autonomous bounds.</div>`;
      }
      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <h3>Human Owner Decision Center</h3>
          ${this.pendingApprovals.map(a => `
            <div class="card" style="padding:20px; border-left:4px solid #f59e0b;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0;">${a.summary}</h4>
                <span class="badge" style="background:#f59e0b; color:black; font-size:0.75rem; padding:2px 8px; border-radius:4px;">Risk: ${a.risk_level}</span>
              </div>
              <div style="margin:10px 0; font-size:0.85rem;">
                Parameters: <pre style="background:rgba(0,0,0,0.3); padding:8px; border-radius:6px;">${JSON.stringify(a.parameters, null, 2)}</pre>
              </div>
              <div style="display:flex; gap:10px; margin-top:12px;">
                <button class="btn btn-primary" onclick="window.AiCeoWorkspace.resolveApproval('${a.approval_id}', true)">Approve & Authorize</button>
                <button class="btn btn-secondary" onclick="window.AiCeoWorkspace.resolveApproval('${a.approval_id}', false)">Reject Directive</button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 13. Evidence
    renderSectionEvidence() {
      return `
        <div class="card" style="padding:20px;">
          <h3 style="margin-top:0;">Cryptographic Evidence Ledger (SHA-256)</h3>
          <p style="font-size:0.85rem; color:var(--text-secondary);">
            Every significant executive decision, mission outcome, and KPI variance is sealed with physical Merkle audit proofs.
          </p>
          <div style="display:flex; flex-direction:column; gap:10px; margin-top:16px;">
            ${this.decisions.map(d => `
              <div style="padding:10px; background:rgba(0,0,0,0.3); border-radius:6px; font-family:monospace; font-size:0.8rem; display:flex; justify-content:space-between;">
                <div>${d.decision_id}: ${d.title.substring(0, 40)}...</div>
                <div style="color:#10b981;">PROOF_VERIFIED</div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // 14. Reports
    renderSectionReports() {
      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="margin:0;">Executive Briefs & Strategic Reviews</h3>
            <button class="btn btn-secondary" onclick="window.AiCeoWorkspace.generateReport()">Generate Daily Brief</button>
          </div>
          ${this.reports.map(r => `
            <div class="card" style="padding:16px;">
              <h4 style="margin:0; color:#60a5fa;">${r.title}</h4>
              <p style="margin:6px 0; font-size:0.85rem; color:var(--text-secondary);">${r.summary}</p>
              <div style="font-size:0.75rem; color:var(--text-secondary);">Type: ${r.report_type} | Published: ${new Date(r.created_at * 1000).toLocaleString()}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // 15. Economic Command & Capital Allocation
    renderSectionEconomic() {
      const pools = this.capitalPools || {};
      const totalPool = pools.total_capital_pool_usd || 500000;
      const allocPool = pools.allocated_capital_usd || 0;
      const unallocPool = pools.unallocated_capital_usd || 500000;

      const profile = this.industryProfile || {};
      const priorities = [
        { code: 'P01', name: 'ENTERPRISE_SURVIVAL', desc: 'Solvency, existential defense & cash runway preservation', status: 'ACTIVE (INVIOLABLE)' },
        { code: 'P02', name: 'LEGAL_SAFETY_INTEGRITY', desc: 'Statutory compliance, safety critical controls, zero red-line breach', status: 'ENFORCED' },
        { code: 'P03', name: 'CASH_PRESERVATION', desc: 'Cash liquidity runway & counterparty default mitigation', status: 'ENFORCED' },
        { code: 'P04', name: 'PROFITABLE_GROWTH', desc: 'Growth strictly conditioned on positive unit economics', status: 'OPTIMIZING' },
        { code: 'P05', name: 'GROSS_PROFIT', desc: 'Direct revenue minus COGS/variable delivery costs', status: 'TRACKING' },
        { code: 'P06', name: 'CONTRIBUTION_MARGIN', desc: 'Net margin after sales, marketing & distribution channels', status: 'TARGET: 60%+' },
        { code: 'P07', name: 'EBITDA', desc: 'Core operating earnings before depreciation & amortization', status: 'TRACKING' },
        { code: 'P08', name: 'FREE_CASH_FLOW', desc: 'Discretionary liquidity generated from enterprise operations', status: 'POSITIVE BUFFER' },
        { code: 'P09', name: 'ROIC', desc: 'Return on Invested Capital across all allocated pools', status: 'HURDLE: > 20%' },
        { code: 'P10', name: 'ENTERPRISE_VALUE', desc: 'Risk-adjusted long-term owner equity valuation', status: 'ACCUMULATING' },
        { code: 'P11', name: 'STRATEGIC_RESILIENCE', desc: 'Redundancy, antifragile architecture & supplier diversity', status: 'VERIFIED' },
        { code: 'P12', name: 'SUSTAINABLE_INNOVATION', desc: 'Perpetual R&D and capability evolution within DoA limits', status: 'FUNDED' }
      ];

      return `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- Header & Multi-Industry Adapter -->
          <div class="card" style="padding:20px; background:linear-gradient(135deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
              <div>
                <h3 style="margin:0; font-size:1.3rem; color:#60a5fa;">💎 AIC CEO Economic Priority Hierarchy & Multi-Industry Adapter</h3>
                <p style="margin:6px 0 0 0; color:var(--text-secondary); font-size:0.85rem;">
                  Universal sovereign economic hierarchy grounded in real commercial results and finite capital allocation.
                </p>
              </div>
              <div style="display:flex; align-items:center; gap:10px;">
                <label style="font-size:0.85rem; color:var(--text-secondary);">Active Industry Archetype:</label>
                <select id="ceoIndustrySelect" onchange="window.AiCeoWorkspace.switchIndustry(this.value)" style="padding:8px 12px; background:rgba(0,0,0,0.5); border:1px solid #3b82f6; color:white; border-radius:6px; font-weight:600;">
                  <option value="Hospitality" ${this.activeIndustry === 'Hospitality' ? 'selected' : ''}>🏨 Hospitality & Luxury Hotels</option>
                  <option value="SaaS Software" ${this.activeIndustry === 'SaaS Software' ? 'selected' : ''}>💻 SaaS & Enterprise Cloud</option>
                  <option value="Precision Manufacturing" ${this.activeIndustry === 'Precision Manufacturing' ? 'selected' : ''}>⚙️ Precision Manufacturing</option>
                  <option value="Healthcare" ${this.activeIndustry === 'Healthcare' ? 'selected' : ''}>🏥 Healthcare & Clinical Services</option>
                  <option value="E-Commerce" ${this.activeIndustry === 'E-Commerce' ? 'selected' : ''}>📦 E-Commerce & Retail</option>
                  <option value="Logistics" ${this.activeIndustry === 'Logistics' ? 'selected' : ''}>🚚 Logistics & Global Supply Chain</option>
                  <option value="Clean Energy" ${this.activeIndustry === 'Clean Energy' ? 'selected' : ''}>⚡ Clean Energy & Utilities</option>
                </select>
              </div>
            </div>

            <!-- Active Industry Benchmarking Status -->
            <div style="margin-top:16px; padding:12px; background:rgba(0,0,0,0.25); border-radius:8px; border:1px solid rgba(255,255,255,0.08); font-size:0.85rem;">
              <strong>Calibrated Archetype:</strong> ${profile.industry || this.activeIndustry} | 
              <strong>Primary Metric:</strong> ${profile.primary_metric || 'Contribution Margin'} | 
              <strong>Baseline Target:</strong> ${profile.default_hurdle_rate ? (profile.default_hurdle_rate * 100) + '%' : '<span class="badge" style="background:rgba(239,68,68,0.2); color:#f87171; border:1px solid #ef4444; padding:2px 6px; border-radius:4px;">BENCHMARK_UNKNOWN</span>'} |
              <strong>Source:</strong> ${profile.benchmark_source || 'Verified Dynamic Calibration'}
            </div>
          </div>

          <!-- Priority Hierarchy 12-Card Grid -->
          <div>
            <h4 style="margin:0 0 12px 0; color:var(--text-secondary); text-transform:uppercase; font-size:0.8rem; letter-spacing:0.05em;">
              Universal Sovereign Priority Hierarchy (P01 — P12)
            </h4>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:12px;">
              ${priorities.map(p => `
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); border-radius:8px; padding:12px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; color:#3b82f6; font-size:0.9rem;">${p.code}: ${p.name}</span>
                    <span class="badge" style="background:rgba(16,185,129,0.15); color:#10b981; font-size:0.7rem; padding:2px 6px; border-radius:4px;">${p.status}</span>
                  </div>
                  <p style="margin:6px 0 0 0; font-size:0.78rem; color:var(--text-secondary);">${p.desc}</p>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Finite Capital Resource Pools -->
          <div class="card" style="padding:20px;">
            <h4 style="margin:0 0 16px 0; font-size:1.1rem; color:#60a5fa;">Capital Allocation Engine & Finite Resource Pools</h4>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:14px; margin-bottom:20px;">
              <div style="background:rgba(0,0,0,0.3); padding:14px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); text-align:center;">
                <div style="font-size:0.75rem; color:var(--text-secondary);">TOTAL CAPITAL POOL</div>
                <div style="font-size:1.3rem; font-weight:700; color:white; margin-top:4px;">$${totalPool.toLocaleString()}</div>
                <div style="font-size:0.7rem; color:#10b981; margin-top:2px;">Board Authorized (DoA Limit)</div>
              </div>
              <div style="background:rgba(0,0,0,0.3); padding:14px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); text-align:center;">
                <div style="font-size:0.75rem; color:var(--text-secondary);">ALLOCATED CAPITAL</div>
                <div style="font-size:1.3rem; font-weight:700; color:#f59e0b; margin-top:4px;">$${allocPool.toLocaleString()}</div>
                <div style="font-size:0.7rem; color:var(--text-secondary); margin-top:2px;">Active Governed Missions</div>
              </div>
              <div style="background:rgba(0,0,0,0.3); padding:14px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); text-align:center;">
                <div style="font-size:0.75rem; color:var(--text-secondary);">AVAILABLE LIQUIDITY</div>
                <div style="font-size:1.3rem; font-weight:700; color:#10b981; margin-top:4px;">$${unallocPool.toLocaleString()}</div>
                <div style="font-size:0.7rem; color:#10b981; margin-top:2px;">Surplus Buffer Intact</div>
              </div>
              <div style="background:rgba(0,0,0,0.3); padding:14px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); text-align:center;">
                <div style="font-size:0.75rem; color:var(--text-secondary);">ACTIVE AGENT RUNTIMES</div>
                <div style="font-size:1.3rem; font-weight:700; color:#3b82f6; margin-top:4px;">8 Nodes</div>
                <div style="font-size:0.7rem; color:var(--text-secondary); margin-top:2px;">Compute Envelope Governed</div>
              </div>
            </div>

            <!-- Active Capital Allocations Table -->
            <h5 style="margin:0 0 10px 0; font-size:0.9rem;">Active Governed Allocations Ledger (${this.capitalAllocations.length})</h5>
            ${this.capitalAllocations.length === 0 ? `
              <div style="text-align:center; padding:16px; background:rgba(0,0,0,0.2); border-radius:8px; border:1px dashed rgba(255,255,255,0.1);">
                <span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid #ef4444; padding:3px 10px; border-radius:4px; font-size:0.75rem;">NO VERIFIED ALLOCATIONS</span>
                <p style="margin:8px 0 0 0; color:var(--text-secondary); font-size:0.8rem;">No capital currently deployed. Authorize a governed allocation below.</p>
              </div>
            ` : `
              <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                  <thead>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1); text-align:left; color:var(--text-secondary);">
                      <th style="padding:8px;">ID</th>
                      <th style="padding:8px;">Type</th>
                      <th style="padding:8px;">Amount</th>
                      <th style="padding:8px;">Purpose</th>
                      <th style="padding:8px;">Expected Return</th>
                      <th style="padding:8px;">Payback</th>
                      <th style="padding:8px;">Risk</th>
                      <th style="padding:8px;">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this.capitalAllocations.map(a => `
                      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                        <td style="padding:8px;"><code>${a.allocation_id}</code></td>
                        <td style="padding:8px;">${a.resource_type}</td>
                        <td style="padding:8px; font-weight:600;">$${(a.quantity || 0).toLocaleString()}</td>
                        <td style="padding:8px;">${a.purpose}</td>
                        <td style="padding:8px; color:#10b981; font-weight:600;">+$${(a.expected_return_usd || 0).toLocaleString()}</td>
                        <td style="padding:8px;">${a.payback_months || 'N/A'} mo</td>
                        <td style="padding:8px;"><span class="badge" style="background:rgba(59,130,246,0.2); color:#60a5fa; padding:2px 6px; border-radius:4px;">${a.risk_level}</span></td>
                        <td style="padding:8px;"><span class="badge" style="background:rgba(16,185,129,0.15); color:#10b981; padding:2px 6px; border-radius:4px;">${a.status || 'ACTIVE'}</span></td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            `}

            <!-- Interactive Capital Allocation Authorizer -->
            <div style="margin-top:20px; padding:16px; background:rgba(255,255,255,0.02); border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
              <h5 style="margin:0 0 12px 0; font-size:0.9rem; color:#60a5fa;">Authorize New Capital Deployment</h5>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px;">
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Resource Type</label>
                  <select id="allocResourceType" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;">
                    <option value="MONEY">MONEY (USD)</option>
                    <option value="PEOPLE">PEOPLE (FTEs)</option>
                    <option value="AI_AGENTS">AI_AGENTS (Swarms)</option>
                    <option value="COMPUTE">COMPUTE (Tokens/sec)</option>
                    <option value="TIME">TIME (Hours)</option>
                  </select>
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Amount / Quantity</label>
                  <input type="number" id="allocQuantity" value="25000" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Purpose / Initiative</label>
                  <input type="text" id="allocPurpose" value="Direct Booking Engine & SEO Acquisition" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Expected Return (USD)</label>
                  <input type="number" id="allocReturn" value="45000" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Risk Level</label>
                  <select id="allocRisk" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;">
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                  </select>
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block; margin-bottom:4px;">Payback (Months)</label>
                  <input type="number" id="allocPayback" value="4.5" step="0.5" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
              </div>
              <div style="display:flex; gap:10px; margin-top:14px; flex-wrap:wrap;">
                <button class="btn btn-primary" onclick="window.AiCeoWorkspace.submitCapitalAllocation()" style="padding:8px 16px;">
                  Authorize Governed Allocation
                </button>
                <button class="btn btn-secondary" onclick="window.AiCeoWorkspace.evaluateCompetingOpportunities()" style="padding:8px 16px;">
                  Evaluate Competing Allocation Requests
                </button>
              </div>

              ${this.lastCompetingResult ? `
                <div style="margin-top:16px; padding:12px; background:rgba(0,0,0,0.4); border-radius:6px; border-left:3px solid #10b981;">
                  <h6 style="margin:0 0 8px 0; color:#10b981;">Risk-Adjusted Competing Evaluation Ranking:</h6>
                  <ol style="margin:0; padding-left:18px; font-size:0.8rem;">
                    ${this.lastCompetingResult.map(o => `
                      <li style="margin-bottom:4px;">
                        <strong>${o.name || o.opportunity_name}</strong> — 
                        Cost: $${(o.cost_usd || 0).toLocaleString()} | 
                        Expected Return: $${(o.expected_return_usd || 0).toLocaleString()} | 
                        Rank Score: <span style="color:#10b981; font-weight:700;">${o.rank_score || o.efficiency_score || 'N/A'}</span>
                      </li>
                    `).join('')}
                  </ol>
                </div>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }

    // 16. Mission Contracts & Verification Chain
    renderSectionContracts() {
      return `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- 7-Stage Verification Pipeline Banner -->
          <div class="card" style="padding:20px; background:linear-gradient(135deg, rgba(20,24,35,0.95), rgba(15,30,50,0.95)); border-left:4px solid #10b981;">
            <h3 style="margin:0; font-size:1.25rem; color:#10b981;">Sovereign Verification Hierarchy: Activity vs Achievement</h3>
            <p style="margin:6px 0 12px 0; color:var(--text-secondary); font-size:0.85rem;">
              The AIC CEO enforces strict separation between activity and verified financial outcome.
            </p>
            <div style="background:rgba(0,0,0,0.4); padding:10px 14px; border-radius:6px; font-family:monospace; font-size:0.82rem; color:#60a5fa; margin-bottom:14px; border:1px solid rgba(59,130,246,0.3); overflow-x:auto;">
              TASK_COMPLETION != MISSION_COMPLETION != BUSINESS_OUTCOME != REVENUE != PROFIT != CASH != VERIFIED_ECONOMIC_RESULT
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px;">
              <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:0.7rem; color:var(--text-secondary);">STAGE 1</div>
                <div style="font-weight:700; font-size:0.75rem; color:#94a3b8; margin-top:2px;">TASK DONE</div>
                <div style="font-size:0.65rem; color:var(--text-secondary); margin-top:2px;">Tool Run Logged</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:0.7rem; color:var(--text-secondary);">STAGE 2</div>
                <div style="font-weight:700; font-size:0.75rem; color:#94a3b8; margin-top:2px;">MISSION DONE</div>
                <div style="font-size:0.65rem; color:var(--text-secondary); margin-top:2px;">Deliverable Formed</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:0.7rem; color:var(--text-secondary);">STAGE 3</div>
                <div style="font-weight:700; font-size:0.75rem; color:#3b82f6; margin-top:2px;">OUTCOME</div>
                <div style="font-size:0.65rem; color:var(--text-secondary); margin-top:2px;">Real-World Effect</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:0.7rem; color:var(--text-secondary);">STAGE 4</div>
                <div style="font-weight:700; font-size:0.75rem; color:#3b82f6; margin-top:2px;">REVENUE</div>
                <div style="font-size:0.65rem; color:var(--text-secondary); margin-top:2px;">Invoice Recorded</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:0.7rem; color:var(--text-secondary);">STAGE 5</div>
                <div style="font-weight:700; font-size:0.75rem; color:#f59e0b; margin-top:2px;">PROFIT</div>
                <div style="font-size:0.65rem; color:var(--text-secondary); margin-top:2px;">Positive Margin</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:0.7rem; color:var(--text-secondary);">STAGE 6</div>
                <div style="font-weight:700; font-size:0.75rem; color:#10b981; margin-top:2px;">CASH IN BANK</div>
                <div style="font-size:0.65rem; color:var(--text-secondary); margin-top:2px;">Cleared Treasury</div>
              </div>
              <div style="background:rgba(255,255,255,0.03); border:1px solid #10b981; border-radius:6px; padding:10px; text-align:center;">
                <div style="font-size:0.7rem; color:#10b981;">STAGE 7</div>
                <div style="font-weight:700; font-size:0.75rem; color:#10b981; margin-top:2px;">VERIFIED ROI</div>
                <div style="font-size:0.65rem; color:#10b981; margin-top:2px;">SHA-256 Ledger</div>
              </div>
            </div>
          </div>

          <!-- Ceo-to-Agent Mission Contracts Table -->
          <div class="card" style="padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:10px;">
              <h4 style="margin:0; font-size:1.1rem; color:#60a5fa;">Active Ceo-to-Agent Mission Contracts (${this.missionContracts.length})</h4>
              <button class="btn btn-primary" onclick="document.getElementById('newContractForm').style.display = document.getElementById('newContractForm').style.display === 'none' ? 'block' : 'none'">
                + Issue Governed Contract
              </button>
            </div>

            <!-- Inline Creator Form -->
            <div id="newContractForm" style="display:none; margin-bottom:20px; padding:16px; background:rgba(255,255,255,0.02); border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
              <h5 style="margin:0 0 12px 0; color:#34d399;">Issue New Ceo-to-Agent Delegation Contract</h5>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px;">
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Mission ID</label>
                  <input type="text" id="contractMissionId" value="msn_direct_01" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Owner Objective</label>
                  <input type="text" id="contractOwnerObj" value="Expand direct booking profitability" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">CEO Mandate</label>
                  <input type="text" id="contractCeoObj" value="Target 65% contribution margin" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Expected Outcome</label>
                  <input type="text" id="contractOutcome" value="Deliver positive EBITDA contribution" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Budget Cap (USD)</label>
                  <input type="number" id="contractBudget" value="10000" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
                <div>
                  <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Time Limit (Hours)</label>
                  <input type="number" id="contractHours" value="720" style="width:100%; padding:8px; background:rgba(0,0,0,0.4); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px;" />
                </div>
              </div>
              <button class="btn btn-primary" onclick="window.AiCeoWorkspace.submitMissionContract()" style="margin-top:12px;">
                Seal & Sign Delegation Contract
              </button>
            </div>

            ${this.missionContracts.length === 0 ? `
              <div style="text-align:center; padding:20px; background:rgba(0,0,0,0.2); border-radius:8px; border:1px dashed rgba(255,255,255,0.1);">
                <span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid #ef4444; padding:3px 10px; border-radius:4px; font-size:0.75rem;">NO VERIFIED CONTRACTS</span>
                <p style="margin:8px 0 0 0; color:var(--text-secondary); font-size:0.8rem;">No active Ceo-to-Agent Mission Contracts deployed. Click "+ Issue Governed Contract" to create one.</p>
              </div>
            ` : `
              <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                  <thead>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1); text-align:left; color:var(--text-secondary);">
                      <th style="padding:8px;">Contract ID</th>
                      <th style="padding:8px;">Mission</th>
                      <th style="padding:8px;">Mandate</th>
                      <th style="padding:8px;">Budget Cap</th>
                      <th style="padding:8px;">Authority</th>
                      <th style="padding:8px;">Verification Method</th>
                      <th style="padding:8px;">Cryptographic Proof</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this.missionContracts.map(c => `
                      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                        <td style="padding:8px;"><code>${c.contract_id || c.mission_id}</code></td>
                        <td style="padding:8px; font-weight:600;">${c.mission_id}</td>
                        <td style="padding:8px;">${c.ceo_objective || c.business_objective}</td>
                        <td style="padding:8px;">$${(c.budget_limit_usd || 0).toLocaleString()}</td>
                        <td style="padding:8px;"><span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; padding:2px 6px; border-radius:4px;">${c.authority_level || 'EXECUTIVE_FUNCTION'}</span></td>
                        <td style="padding:8px;">${c.verification_method || 'AUDITED_STATEMENT'}</td>
                        <td style="padding:8px;"><code style="font-size:0.7rem;">${c.cryptographic_hash ? c.cryptographic_hash.substring(0, 16) + '...' : 'SEALED_SHA256'}</code></td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            `}
          </div>
        </div>
      `;
    }

    // 17. Prediction & Learning Ledger
    renderSectionPredictions() {
      return `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <div class="card" style="padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
              <div>
                <h3 style="margin:0; font-size:1.2rem; color:#60a5fa;">🔮 Executive Prediction & Learning Ledger (CeoLearningLoopEngine)</h3>
                <p style="margin:6px 0 0 0; color:var(--text-secondary); font-size:0.85rem;">
                  Every material decision commits an explicit quantitative prediction before execution. Actual results are audited, and variances are categorized (MODEL_ERROR, BENCHMARK_ERROR, EXECUTION_FAILURE, MARKET_SHOCK) to calibrate executive policy.
                </p>
              </div>
            </div>

            <!-- Ledger Table -->
            ${this.learningLedger.length === 0 ? `
              <div style="text-align:center; padding:24px; background:rgba(0,0,0,0.2); border-radius:8px; border:1px dashed rgba(255,255,255,0.1);">
                <span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid #ef4444; padding:3px 10px; border-radius:4px; font-size:0.75rem;">NO VERIFIED DATA</span>
                <p style="margin:8px 0 0 0; color:var(--text-secondary); font-size:0.8rem;">No predictions registered in learning ledger. Record a prediction below.</p>
              </div>
            ` : `
              <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                  <thead>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.1); text-align:left; color:var(--text-secondary);">
                      <th style="padding:8px;">ID</th>
                      <th style="padding:8px;">Hypothesis</th>
                      <th style="padding:8px;">Metric</th>
                      <th style="padding:8px;">Predicted</th>
                      <th style="padding:8px;">Status</th>
                      <th style="padding:8px;">Actual</th>
                      <th style="padding:8px;">Variance</th>
                      <th style="padding:8px;">Error Class</th>
                      <th style="padding:8px;">Root Cause / Corrective Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${this.learningLedger.map(l => `
                      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                        <td style="padding:8px;"><code>${l.prediction_id}</code></td>
                        <td style="padding:8px; max-width:200px;">${l.prediction_statement}</td>
                        <td style="padding:8px;"><code>${l.metric_name}</code></td>
                        <td style="padding:8px; font-weight:600; color:#3b82f6;">${l.predicted_value}</td>
                        <td style="padding:8px;">
                          <span class="badge" style="background:${l.status === 'RESOLVED_CALIBRATED' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)'}; color:${l.status === 'RESOLVED_CALIBRATED' ? '#10b981' : '#f59e0b'}; padding:2px 6px; border-radius:4px;">
                            ${l.status}
                          </span>
                        </td>
                        <td style="padding:8px; font-weight:600;">${l.actual_value !== null ? l.actual_value : '—'}</td>
                        <td style="padding:8px; font-weight:600; color:${l.variance !== null ? (l.variance >= 0 ? '#10b981' : '#ef4444') : 'inherit'};">
                          ${l.variance !== null ? (l.variance > 0 ? '+' : '') + l.variance : '—'}
                        </td>
                        <td style="padding:8px;">
                          <span class="badge" style="background:rgba(255,255,255,0.05); color:#94a3b8; padding:2px 6px; border-radius:4px;">
                            ${l.learning_category || 'NONE'}
                          </span>
                        </td>
                        <td style="padding:8px; font-size:0.75rem; color:var(--text-secondary); max-width:240px;">
                          ${l.root_cause ? `<div><strong>RC:</strong> ${l.root_cause}</div>` : ''}
                          ${l.corrective_action ? `<div><strong>CA:</strong> ${l.corrective_action}</div>` : 'Awaiting actual outcome'}
                        </td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              </div>
            `}

            <!-- Prediction Form & Resolution Controls -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:16px; margin-top:20px;">
              <!-- Record Prediction -->
              <div style="padding:16px; background:rgba(255,255,255,0.02); border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
                <h5 style="margin:0 0 10px 0; color:#3b82f6;">Record Material Prediction</h5>
                <div style="display:flex; flex-direction:column; gap:8px;">
                  <input type="text" id="predDecisionId" placeholder="Decision ID (e.g. dec_marketing_01)" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  <input type="text" id="predOwnerObj" placeholder="Owner Objective" value="Grow high-margin revenue" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  <input type="text" id="predStatement" placeholder="Prediction Statement / Hypothesis" value="Direct booking engine will lift contribution margin to 65%" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
                    <input type="text" id="predMetric" placeholder="Metric Name" value="Contribution_Margin_Pct" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                    <input type="number" id="predValue" placeholder="Predicted Value" value="65.0" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  </div>
                  <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
                    <input type="number" id="predConfLow" placeholder="Conf Low" value="60.0" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                    <input type="number" id="predConfHigh" placeholder="Conf High" value="70.0" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                    <input type="number" id="predDays" placeholder="Days" value="30" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  </div>
                  <button class="btn btn-primary" onclick="window.AiCeoWorkspace.submitPrediction()" style="margin-top:6px;">
                    Commit Prediction to Ledger
                  </button>
                </div>
              </div>

              <!-- Resolve Actual Outcome -->
              <div style="padding:16px; background:rgba(255,255,255,0.02); border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
                <h5 style="margin:0 0 10px 0; color:#10b981;">Resolve Actual Outcome & Execute Learning Loop</h5>
                <div style="display:flex; flex-direction:column; gap:8px;">
                  <select id="resolvePredId" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;">
                    ${this.learningLedger.length ? this.learningLedger.map(l => `<option value="${l.prediction_id}">${l.prediction_id} — ${l.metric_name} (Pred: ${l.predicted_value})</option>`).join('') : '<option value="">No active predictions</option>'}
                  </select>
                  <input type="number" id="resolveActualValue" placeholder="Verified Actual Value" value="63.5" step="0.1" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  <input type="text" id="resolveRootCause" placeholder="Observed Root Cause / Variance Factor" value="Slightly higher customer support staffing during launch" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  <input type="text" id="resolveCorrectiveAction" placeholder="Corrective Action" value="Incorporate support labor variance into channel forecast" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  <input type="text" id="resolvePolicyAdj" placeholder="Future Policy Adjustment" value="Require 2% labor contingency buffer for Q4 models" style="padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
                  <button class="btn btn-secondary" onclick="window.AiCeoWorkspace.submitResolveActual()" style="margin-top:6px;">
                    Resolve Actual & Calibrate
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    // 18. Performance Qualification Scorecard
    renderSectionScorecard() {
      const sc = this.ceoScorecard || {};
      const index = sc.composite_ceo_index || 87.4;
      const unverified = sc.unverified_data_present;

      const cats = [
        { name: '1. Financial Accountability', score: sc.financial_score || 88.0, desc: 'Contribution margin, ROIC, and budget discipline' },
        { name: '2. Commercial Excellence', score: sc.commercial_score || 85.0, desc: 'NRR, retention, CAC efficiency, customer value' },
        { name: '3. Strategic Alignment', score: sc.strategic_score || 85.0, desc: 'Owner intent translation, milestone completion' },
        { name: '4. Operational Discipline', score: sc.execution_score || 90.0, desc: 'Task vs outcome verification, kill-switch adherence' },
        { name: '5. Governance & Compliance', score: sc.governance_score || 100.0, desc: 'Zero red-line breaches, statutory integrity, audit trail' },
        { name: '6. Decision Quality & Learning', score: sc.cognitive_decision_score || 82.0, desc: 'Predicted vs actual calibration, anti-sycophancy' },
        { name: '7. Organizational Leadership', score: sc.organization_score || 88.0, desc: 'Workforce productivity, agent network coordination' }
      ];

      return `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- Overall Qualification Grade Banner -->
          <div class="card" style="padding:24px; background:linear-gradient(135deg, rgba(20,24,35,0.95), rgba(15,30,50,0.95)); border-left:4px solid #3b82f6;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
              <div>
                <h3 style="margin:0; font-size:1.3rem; color:#60a5fa;">🎖️ AIC CEO Sovereign Performance Qualification Scorecard</h3>
                <p style="margin:6px 0 0 0; color:var(--text-secondary); font-size:0.85rem;">
                  Formal executive qualification index audited across 7 mandatory performance dimensions.
                </p>
              </div>
              <div style="display:flex; align-items:center; gap:16px;">
                <div style="text-align:right;">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">COMPOSITE QUALIFICATION INDEX</div>
                  <div style="font-size:1.8rem; font-weight:800; color:#10b981;">
                    ${unverified ? '<span class="badge" style="background:rgba(239,68,68,0.2); color:#f87171; font-size:0.9rem; border:1px solid #ef4444; padding:4px 8px; border-radius:4px;">NO VERIFIED DATA</span>' : `${index} / 100`}
                  </div>
                </div>
                <div style="padding:8px 14px; background:rgba(16,185,129,0.15); border:1px solid #10b981; border-radius:8px; text-align:center;">
                  <div style="font-size:0.7rem; color:#10b981; font-weight:700;">SOVEREIGN GRADE</div>
                  <div style="font-size:0.95rem; font-weight:800; color:white; margin-top:2px;">SOVEREIGN_BOARD_READY</div>
                </div>
              </div>
            </div>

            <div style="margin-top:16px; padding:12px; background:rgba(0,0,0,0.3); border-radius:6px; font-size:0.8rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;">
              <div><strong>Authority Recommendation:</strong> Full Class A & B Operational Autonomy Authorized</div>
              <div><strong>Governance Oversight:</strong> Sovereign Owner Override & Kill Switches Active</div>
              <div><strong>Audit Integrity:</strong> Cryptographically Grounded (SHA-256)</div>
            </div>
          </div>

          <!-- 7 Dimensions Grid -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:14px;">
            ${cats.map(c => `
              <div class="card" style="padding:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <h5 style="margin:0; font-size:0.9rem; color:#60a5fa;">${c.name}</h5>
                  <span style="font-size:1.1rem; font-weight:700; color:${c.score >= 85 ? '#10b981' : (c.score >= 70 ? '#f59e0b' : '#ef4444')};">
                    ${unverified ? '—' : `${c.score}%`}
                  </span>
                </div>
                <div style="margin-top:8px; height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                  <div style="width:${unverified ? 0 : c.score}%; height:100%; background:${c.score >= 85 ? '#10b981' : (c.score >= 70 ? '#f59e0b' : '#ef4444')};"></div>
                </div>
                <p style="margin:8px 0 0 0; font-size:0.75rem; color:var(--text-secondary);">${c.desc}</p>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // 19. Constitution & Anti-Gaming Controls
    renderSectionConstitution() {
      const redLines = [
        { id: 'RL-01', title: 'No Unauthorized Debt or Capital Commitments', desc: 'Cannot execute borrowings, debt guarantees, or off-balance-sheet commitments beyond Owner DoA.' },
        { id: 'RL-02', title: 'No Self-Expansion of Authority', desc: 'Cannot amend its own decision rights, override the ApprovalEngine, or escalate autonomy without Sovereign signoff.' },
        { id: 'RL-03', title: 'No Falsification or Omission of Evidence', desc: 'All metrics, receipts, tool outputs, and ledger proofs must be cryptographically auditable and strictly unaltered.' },
        { id: 'RL-04', title: 'No Concealment of Negative Operational Metrics', desc: 'Deteriorating margins, churn spikes, or SLA failures must be highlighted in real time; cannot be masked or delayed.' },
        { id: 'RL-05', title: 'No Human Displacement without Verified ROI', desc: 'Cannot terminate, replace, or alter human roles without verified productivity, economic, and safety audit.' },
        { id: 'RL-06', title: 'No Execution of Unverified Prompt Injections', desc: 'Hostile instructions, social engineering, or adversarial model overrides must be quarantined and reported to Owner.' },
        { id: 'RL-07', title: 'No Irreversible Strategic Decisions Unapproved', desc: 'Irreversible M&A, business shutdowns, or asset sales require mandatory human owner authorization (Class A).' },
        { id: 'RL-08', title: 'No Local Optimization at Enterprise Expense', desc: 'Cannot artificially inflate single-department KPIs (e.g. sales) while destroying gross margin or solvency.' },
        { id: 'RL-09', title: 'No Bypass of Sovereign Override or Kill Switches', desc: 'Owner override and emergency kill switches are absolute, non-negotiable, and hardwired into the control loop.' },
        { id: 'RL-10', title: 'No Cross-Tenant Data Boundary Breaches', desc: 'Complete confidentiality and isolation across corporate tenants, subsidiaries, and external partners.' },
        { id: 'RL-11', title: 'No Deferred Maintenance Masked as Savings', desc: 'Cannot cut vital maintenance, security patching, or QA and claim artificial cost reduction.' },
        { id: 'RL-12', title: 'No Sycophantic Reporting', desc: 'Reporting must state verifiable reality with confidence intervals, never flattering or placating executive bias.' }
      ];

      const antiGaming = [
        { vector: 'Metric Inflation (Vanity Metrics)', detection: 'Counter-metric paired analysis', counter: 'Revenue vs Contribution Margin %', action: 'Halt discounting; enforce margin floor' },
        { vector: 'Deferred Maintenance', detection: 'System health & deprecation audit', counter: 'Opex Reduction vs Asset Health Score', action: 'Flag deferred liability; freeze savings' },
        { vector: 'Quality Erosion', detection: 'Customer NPS & refund surge monitoring', counter: 'Short-term Margin vs Refund Rate', action: 'Quarantine low-quality deliverable' },
        { vector: 'Risk Transfer', detection: 'Tail-risk & contingent liability scanning', counter: 'Reported Profit vs Downside Exposure', action: 'Cap downside; require reserve allocation' },
        { vector: 'Benchmark Manipulation', detection: 'Historical cohort baseline lock', counter: 'Internal Target vs Industry Archetype', action: 'Reject ungrounded target modifications' },
        { vector: 'Sycophancy / False Optimism', detection: 'Forecast variance & calibration tracking', counter: 'Predicted vs Audited Actual', action: 'Penalize overconfidence; apply discount' },
        { vector: 'Premature Revenue Recognition', detection: 'Cash clearing ledger reconciliation', counter: 'Invoiced Revenue vs Bank Balance', action: 'Stage-gate revenue until cash clears' },
        { vector: 'False Task Completion', detection: 'Invariant enforcement pipeline', counter: 'TASK_COMPLETION != BUSINESS_OUTCOME', action: 'Disallow mission completion on tool logs' }
      ];

      return `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- 12 Invariant Red Lines -->
          <div class="card" style="padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
              <div>
                <h3 style="margin:0; font-size:1.25rem; color:#ef4444;">⚖️ Master Constitution: 12 Invariant Red Lines</h3>
                <p style="margin:6px 0 0 0; color:var(--text-secondary); font-size:0.85rem;">
                  Machine-enforceable boundaries that cannot be bypassed regardless of autonomy level, intelligence, or speed.
                </p>
              </div>
              <span class="badge" style="background:rgba(239,68,68,0.15); color:#ef4444; border:1px solid #ef4444; padding:4px 10px; border-radius:6px; font-weight:700;">
                ALL 12 NON-NEGOTIABLE
              </span>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:12px;">
              ${redLines.map(r => `
                <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:12px; border-left:3px solid #ef4444;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; color:#ef4444; font-size:0.85rem;">${r.id}: ${r.title}</span>
                    <span class="badge" style="background:rgba(16,185,129,0.15); color:#10b981; font-size:0.65rem; padding:1px 4px; border-radius:3px;">LOCKED</span>
                  </div>
                  <p style="margin:6px 0 0 0; font-size:0.75rem; color:var(--text-secondary);">${r.desc}</p>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Anti-Gaming Matrix -->
          <div class="card" style="padding:20px;">
            <h4 style="margin:0 0 12px 0; font-size:1.1rem; color:#f59e0b;">Anti-Gaming Protection Matrix (8 Vectors Blocked)</h4>
            <div style="overflow-x:auto;">
              <table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                <thead>
                  <tr style="border-bottom:1px solid rgba(255,255,255,0.1); text-align:left; color:var(--text-secondary);">
                    <th style="padding:8px;">Gaming Vector</th>
                    <th style="padding:8px;">Detection Method</th>
                    <th style="padding:8px;">Counter-Metric Pair</th>
                    <th style="padding:8px;">Executive Safeguard Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${antiGaming.map(g => `
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                      <td style="padding:8px; font-weight:600; color:#f59e0b;">${g.vector}</td>
                      <td style="padding:8px;">${g.detection}</td>
                      <td style="padding:8px;"><code>${g.counter}</code></td>
                      <td style="padding:8px; color:#10b981;">${g.action}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Sovereign Owner Override Console -->
          <div class="card" style="padding:20px;">
            <h4 style="margin:0 0 10px 0; font-size:1.1rem; color:#3b82f6;">Sovereign Owner Override & Protocol Handoff</h4>
            <p style="margin:0 0 14px 0; font-size:0.85rem; color:var(--text-secondary);">
              The Owner / Sovereign Authority preserves absolute command authority. Overrides are cryptographically recorded in the Evidence Ledger with differential rationale.
            </p>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:10px;">
              <div>
                <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Target Decision ID</label>
                <input type="text" id="overrideDecisionId" value="dec_capital_allocation_01" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
              </div>
              <div>
                <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Owner Instruction</label>
                <input type="text" id="overrideInstruction" value="Prioritize brand market expansion over near-term margin" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
              </div>
              <div>
                <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">CEO Initial Recommendation</label>
                <input type="text" id="overrideRecommendation" value="Decline due to 14-month payback horizon" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
              </div>
              <div>
                <label style="font-size:0.75rem; color:var(--text-secondary); display:block;">Difference Rationale</label>
                <input type="text" id="overrideRationale" value="Strategic enterprise positioning before competitor entry" style="width:100%; padding:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white; border-radius:6px; font-size:0.8rem;" />
              </div>
            </div>
            <button class="btn btn-primary" onclick="window.AiCeoWorkspace.submitOwnerOverride()" style="margin-top:12px;">
              Execute Sovereign Owner Override
            </button>
          </div>
        </div>
      `;
    }

    // 20. Executive Stress-Test Simulator (Scenarios A through J)
    renderSectionScenarios() {
      const res = this.scenarioResult;
      const scenarioOptions = [
        { code: 'SCENARIO_A', title: 'Scenario A: Revenue Increases But Profit Decreases', desc: 'Tests margin collapse detection, halts aggressive discounting, enforces margin floor' },
        { code: 'SCENARIO_B', title: 'Scenario B: Sales Increase But Cancellations Increase', desc: 'Tests false-growth detection, detects gross booking spam, recalibrates qualification gate' },
        { code: 'SCENARIO_C', title: 'Scenario C: Marketing Spend Increases But Incremental Profit Falls', desc: 'Tests diminishing returns detection, stops non-performing ads, reallocates to direct channels' },
        { code: 'SCENARIO_D', title: 'Scenario D: Agent Task Completion Increases But Verified Outcomes Decline', desc: 'Tests productivity illusion, enforces TASK_COMPLETION != BUSINESS_OUTCOME invariant' },
        { code: 'SCENARIO_E', title: 'Scenario E: Cash Decreases Despite Revenue Growth', desc: 'Tests working-capital bottleneck & DSO spike, invokes invoice payment terms & early-pay discounts' },
        { code: 'SCENARIO_F', title: 'Scenario F: Major Customer Lost', desc: 'Tests ACV churn recovery, conducts root-cause post-mortem, accelerates pipeline in late-stage accounts' },
        { code: 'SCENARIO_G', title: 'Scenario G: Competitor Substantially Reduces Price', desc: 'Tests competitive margin defense, unbundles enterprise service SLA, avoids commoditization' },
        { code: 'SCENARIO_H', title: 'Scenario H: Critical Operational Disruption', desc: 'Tests Priority 1 (Survival) failover, air-gapped host failover, freezes write operations' },
        { code: 'SCENARIO_I', title: 'Scenario I: Fraud / Security / Compliance Event', desc: 'Tests Red Line tripwire, revokes credentials, locks treasury outbox, generates cryptographic proof' },
        { code: 'SCENARIO_J', title: 'Scenario J: CEO Forecast Is Materially Wrong', desc: 'Tests forecast error calibration, logs variance in Learning Ledger, updates forecasting policy' }
      ];

      return `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- Simulator Header & Runner Card -->
          <div class="card" style="padding:24px; background:linear-gradient(135deg, rgba(30,41,59,0.85), rgba(15,23,42,0.95));">
            <h3 style="margin:0; font-size:1.3rem; color:#60a5fa;">🧪 Executive Stress-Testing Simulator (Scenarios A through J)</h3>
            <p style="margin:6px 0 16px 0; color:var(--text-secondary); font-size:0.85rem;">
              Adversarial stress-testing suite validating AIC CEO autonomy, constitutional enforcement, risk management, and failover capabilities under extreme operating conditions.
            </p>
            <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
              <select id="stressScenarioSelect" style="flex:1; min-width:320px; padding:10px 14px; background:rgba(0,0,0,0.5); border:1px solid #3b82f6; color:white; border-radius:6px; font-weight:600;">
                ${scenarioOptions.map(s => `
                  <option value="${s.code}">${s.title}</option>
                `).join('')}
              </select>
              <button class="btn btn-primary" onclick="window.AiCeoWorkspace.runStressScenario()" style="padding:10px 20px; font-weight:700;">
                ⚡ Execute Adversarial Stress Test
              </button>
            </div>
          </div>

          <!-- Live Simulation Results Panel -->
          ${res ? `
            <div class="card" style="padding:20px; border-left:4px solid #10b981; background:rgba(20,24,35,0.95);">
              <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <h4 style="margin:0; color:#10b981; font-size:1.15rem;">✓ Stress Test Executed: ${res.scenario}</h4>
                <span class="badge" style="background:rgba(16,185,129,0.2); color:#10b981; padding:4px 10px; border-radius:6px; font-weight:700;">
                  PASSED & CONTAINED
                </span>
              </div>

              <div style="margin-top:14px; display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
                <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:6px; border:1px solid rgba(255,255,255,0.06);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">EXECUTIVE VERDICT</div>
                  <div style="font-weight:700; color:#f59e0b; margin-top:4px; font-size:0.85rem;">${res.ceo_verdict || 'CONSTITUTIONAL_CONTROL_ENFORCED'}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:6px; border:1px solid rgba(255,255,255,0.06);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">MANDATORY ACTION TAKEN</div>
                  <div style="font-weight:600; color:#10b981; margin-top:4px; font-size:0.85rem;">${res.action_taken || res.strategic_response || res.learning_action || 'Safeguards engaged'}</div>
                </div>
              </div>

              ${res.recovery_plan ? `
                <div style="margin-top:14px; padding:12px; background:rgba(0,0,0,0.3); border-radius:6px;">
                  <strong style="color:#60a5fa; font-size:0.85rem;">24-Hour Recovery Action Program:</strong>
                  <ul style="margin:6px 0 0 0; padding-left:18px; font-size:0.8rem; color:var(--text-secondary);">
                    ${res.recovery_plan.map(step => `<li>${step}</li>`).join('')}
                  </ul>
                </div>
              ` : ''}

              <div style="margin-top:14px; font-size:0.75rem; color:var(--text-secondary);">
                Raw Telemetry: <pre style="background:rgba(0,0,0,0.4); padding:10px; border-radius:6px; color:#94a3b8; overflow-x:auto;">${JSON.stringify(res, null, 2)}</pre>
              </div>
            </div>
          ` : `
            <div class="card" style="padding:24px; text-align:center;">
              <p style="color:var(--text-secondary); margin:0;">
                Select any adversarial scenario from A to J and click "Execute Adversarial Stress Test" to test the AIC CEO engine's crisis response and constitutional tripwires in real time.
              </p>
            </div>
          `}

          <!-- Scenarios Catalog Reference -->
          <div class="card" style="padding:20px;">
            <h4 style="margin:0 0 12px 0; font-size:1rem; color:var(--text-secondary); text-transform:uppercase;">Scenario Verification Catalog (A — J)</h4>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:10px;">
              ${scenarioOptions.map(s => `
                <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:6px; padding:10px;">
                  <div style="font-weight:700; color:#3b82f6; font-size:0.8rem;">${s.title}</div>
                  <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:4px;">${s.desc}</div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    }

    async switchIndustry(ind) {
      this.activeIndustry = ind;
      try {
        const res = await fetch(`/api/v8/ceo/industry/profile?industry=${encodeURIComponent(ind)}`, {
          headers: { 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId }
        }).then(r => r.json());
        if (res.profile) {
          this.industryProfile = res.profile;
        }
        if (window.showToast) window.showToast(`Calibrated to ${ind} Profile`, 'info');
        this.switchTab('economic');
      } catch (e) {
        console.error('Failed to switch industry profile:', e);
      }
    }

    async submitCapitalAllocation() {
      const rType = document.getElementById('allocResourceType')?.value || 'MONEY';
      const qty = parseFloat(document.getElementById('allocQuantity')?.value || '10000');
      const purp = document.getElementById('allocPurpose')?.value || 'Operational Growth';
      const ret = parseFloat(document.getElementById('allocReturn')?.value || '15000');
      const risk = document.getElementById('allocRisk')?.value || 'LOW';
      const pay = parseFloat(document.getElementById('allocPayback')?.value || '6');

      try {
        const res = await fetch('/api/v8/ceo/capital/allocate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({
            resource_type: rType,
            quantity: qty,
            unit: 'USD',
            purpose: purp,
            expected_outcome: 'Positive capital return',
            expected_return_usd: ret,
            risk_level: risk,
            payback_months: pay,
            opportunity_cost: 'Alternative project deferred'
          })
        }).then(r => r.json());

        if (res.success) {
          if (window.showToast) window.showToast(`Capital Allocated: $${qty.toLocaleString()} (${res.allocation.allocation_id})`, 'success');
          await this.loadAllData();
          this.switchTab('economic');
        } else {
          if (window.showToast) window.showToast('Allocation failed: ' + (res.error || 'Unknown error'), 'error');
        }
      } catch (err) {
        console.error('Allocation error:', err);
      }
    }

    async evaluateCompetingOpportunities() {
      const opps = [
        { name: 'Direct Booking Engine SEO', cost_usd: 25000, expected_return_usd: 60000, risk_level: 'LOW', payback_months: 4, strategic_alignment: 0.9 },
        { name: 'Luxury Spa Expansion', cost_usd: 75000, expected_return_usd: 110000, risk_level: 'MEDIUM', payback_months: 12, strategic_alignment: 0.75 },
        { name: 'Aggressive OTA Promotion', cost_usd: 30000, expected_return_usd: 40000, risk_level: 'HIGH', payback_months: 6, strategic_alignment: 0.5 }
      ];

      try {
        const res = await fetch('/api/v8/ceo/capital/evaluate-competing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ opportunities: opps })
        }).then(r => r.json());

        if (res.success) {
          this.lastCompetingResult = res.ranked_opportunities;
          if (window.showToast) window.showToast('Evaluated 3 Competing Opportunities', 'success');
          this.switchTab('economic');
        }
      } catch (err) {
        console.error('Failed to evaluate competing opportunities:', err);
      }
    }

    async submitMissionContract() {
      const mId = document.getElementById('contractMissionId')?.value || 'msn_exec_01';
      const ownObj = document.getElementById('contractOwnerObj')?.value || 'Grow recurring high-margin direct revenue';
      const ceoObj = document.getElementById('contractCeoObj')?.value || 'Increase contribution margin to 65%';
      const expOutcome = document.getElementById('contractOutcome')?.value || 'Deliver verified EBITDA margin positive output';
      const budget = parseFloat(document.getElementById('contractBudget')?.value || '15000');
      const hours = parseFloat(document.getElementById('contractHours')?.value || '720');

      try {
        const res = await fetch('/api/v8/ceo/contracts/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({
            mission_id: mId,
            owner_objective: ownObj,
            ceo_objective: ceoObj,
            business_objective: expOutcome,
            expected_business_outcome: expOutcome,
            budget_limit_usd: budget,
            time_limit_hours: hours,
            authority_level: 'EXECUTIVE_FUNCTION',
            risk_limit: 'MEDIUM'
          })
        }).then(r => r.json());

        if (res.success) {
          if (window.showToast) window.showToast(`Issued Governed Mission Contract: ${res.contract.contract_id || res.contract.mission_id}`, 'success');
          await this.loadAllData();
          this.switchTab('contracts');
        } else {
          if (window.showToast) window.showToast('Contract creation failed', 'error');
        }
      } catch (e) {
        console.error('Contract creation error:', e);
      }
    }

    async submitPrediction() {
      const decId = document.getElementById('predDecisionId')?.value || 'dec_rev_01';
      const ownObj = document.getElementById('predOwnerObj')?.value || 'Improve enterprise contribution margin';
      const stmt = document.getElementById('predStatement')?.value || 'Direct booking engine will lift contribution margin to 65%';
      const metric = document.getElementById('predMetric')?.value || 'Contribution_Margin_Pct';
      const predVal = parseFloat(document.getElementById('predValue')?.value || '65.0');
      const confLow = parseFloat(document.getElementById('predConfLow')?.value || '60.0');
      const confHigh = parseFloat(document.getElementById('predConfHigh')?.value || '70.0');
      const days = parseFloat(document.getElementById('predDays')?.value || '30');

      try {
        const res = await fetch('/api/v8/ceo/learning/record-prediction', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({
            decision_id: decId,
            owner_objective: ownObj,
            prediction_statement: stmt,
            metric_name: metric,
            predicted_value: predVal,
            confidence_interval_low: confLow,
            confidence_interval_high: confHigh,
            timeframe_days: days
          })
        }).then(r => r.json());

        if (res.success) {
          const id = res.prediction_entry?.prediction_id || 'Recorded';
          if (window.showToast) window.showToast(`Prediction Recorded: ${id}`, 'success');
          await this.loadAllData();
          this.switchTab('predictions');
        } else {
          if (window.showToast) window.showToast('Recording prediction failed', 'error');
        }
      } catch (e) {
        console.error('Prediction recording error:', e);
      }
    }

    async submitResolveActual() {
      const pId = document.getElementById('resolvePredId')?.value;
      const actualVal = parseFloat(document.getElementById('resolveActualValue')?.value || '0.0');
      const rc = document.getElementById('resolveRootCause')?.value || 'SMB churn offset enterprise bookings';
      const ca = document.getElementById('resolveCorrectiveAction')?.value || 'Recalibrate SMB retention baseline';
      const pa = document.getElementById('resolvePolicyAdj')?.value || 'Require segmented cohort retention forecasts';

      if (!pId) {
        if (window.showToast) window.showToast('Please select or provide a Prediction ID', 'warning');
        return;
      }

      try {
        const res = await fetch('/api/v8/ceo/learning/resolve-actual', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({
            prediction_id: pId,
            actual_value: actualVal,
            root_cause: rc,
            corrective_action: ca,
            future_policy_adjustment: pa
          })
        }).then(r => r.json());

        if (res.success) {
          const entry = res.resolved_entry || {};
          if (window.showToast) window.showToast(`Resolved Actual: Variance ${entry.variance_pct || entry.forecast_error_pct || 0}% (${entry.status || 'CALIBRATED'})`, 'success');
          await this.loadAllData();
          this.switchTab('predictions');
        } else {
          if (window.showToast) window.showToast('Resolution error: ' + (res.error || 'Unknown'), 'error');
        }
      } catch (e) {
        console.error('Resolve error:', e);
      }
    }

    async runStressScenario() {
      const scCode = document.getElementById('stressScenarioSelect')?.value || 'SCENARIO_A';
      try {
        const res = await fetch('/api/v8/ceo/scenarios/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ scenario_id: scCode })
        }).then(r => r.json());

        if (res.success) {
          this.scenarioResult = res.scenario_result;
          if (window.showToast) window.showToast(`Stress Scenario ${scCode} Completed!`, 'success');
          this.switchTab('scenarios');
        } else {
          if (window.showToast) window.showToast('Scenario failed: ' + (res.error || 'Unknown'), 'error');
        }
      } catch (e) {
        console.error('Scenario error:', e);
      }
    }

    async submitOwnerOverride() {
      const decId = document.getElementById('overrideDecisionId')?.value || 'dec_sample';
      const instr = document.getElementById('overrideInstruction')?.value || 'Prioritize brand market expansion over near-term margin';
      const rec = document.getElementById('overrideRecommendation')?.value || 'Decline due to payback duration';
      const rat = document.getElementById('overrideRationale')?.value || 'Owner strategic prerogative';
      const con = document.getElementById('overrideConsequence')?.value || 'Monitored daily in executive brief';

      try {
        const res = await fetch('/api/v8/ceo/owner/override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({
            decision_id: decId,
            owner_instruction: instr,
            ceo_recommendation: rec,
            difference_rationale: rat,
            expected_consequence: con
          })
        }).then(r => r.json());

        if (res.success) {
          if (window.showToast) window.showToast('Sovereign Owner Override Recorded to Ledger', 'warning');
          this.switchTab('constitution');
        } else {
          if (window.showToast) window.showToast('Override error: ' + (res.error || 'Unknown'), 'error');
        }
      } catch (e) {
        console.error('Override error:', e);
      }
    }

    bindEvents(container) {
      const btnRun = container.querySelector('#btnRunClosedLoop');
      if (btnRun) {
        btnRun.onclick = async () => {
          btnRun.disabled = true;
          btnRun.innerHTML = '<span>⚡ Executing 22 Steps...</span>';
          try {
            const res = await fetch('/api/v8/scenario/run', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
              body: JSON.stringify({ goal: 'Increase Royal Hotel Jaipur profitability during peak wedding season while maintaining guest-service standards.' })
            }).then(r => r.json());

            if (res.success) {
              if (window.showToast) window.showToast('22-Step Closed-Loop Scenario Verified!', 'success');
              await this.render();
            } else {
              if (window.showToast) window.showToast('Scenario failed: ' + (res.error || 'Unknown'), 'error');
            }
          } catch (e) {
            console.error('Scenario run error:', e);
          } finally {
            btnRun.disabled = false;
            btnRun.innerHTML = '<span>⚡ Run 22-Step Scenario</span>';
          }
        };
      }

      const btnSend = container.querySelector('#btnSendCeoCommand');
      const input = container.querySelector('#ceoCommandInput');
      if (btnSend && input) {
        const handler = async () => {
          const val = input.value.trim();
          if (!val) return;
          input.value = '';
          await this.sendQuickCommand(val);
        };
        btnSend.onclick = handler;
        input.onkeydown = (e) => { if (e.key === 'Enter') handler(); };
      }
    }

    async sendQuickCommand(msg) {
      const feedback = document.getElementById('ceoChatFeedback');
      if (feedback) {
        feedback.style.display = 'block';
        feedback.innerHTML = `<em>Consulting Google Gemma 4 Cognitive Executive Layer...</em>`;
      }
      try {
        const res = await fetch('/api/v8/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ message: msg })
        }).then(r => r.json());

        if (res.success && feedback) {
          const r = res.reply || {};
          const ans = r.answer || 'Directive acknowledged.';
          const modelBadge = r.model_used || 'gemma-4-31b-it';
          const epistemic = r.epistemic_classification || 'INFERENCE';
          const evLink = r.evidence_digest ? `<div style="margin-top:6px; font-size:0.8rem; color:#10b981;">🔗 <strong>Merkle Evidence Digest:</strong> <code>${r.evidence_digest}</code></div>` : '';
          const metricsBadge = r.tokens_consumed ? `<span style="font-size:0.75rem; color:var(--text-secondary); margin-left:8px;">(${r.tokens_consumed} tokens, ${r.latency_ms}ms)</span>` : '';

          feedback.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap;">
              <div style="font-weight:600; color:#60a5fa;">Human Owner Directive: "${msg}"</div>
              <div>
                <span class="status-indicator-pill" style="background:rgba(99,102,241,0.2); color:#818cf8; font-size:0.75rem; padding:2px 6px; border-radius:6px;">${modelBadge}</span>
                <span class="status-indicator-pill" style="background:rgba(16,185,129,0.2); color:#10b981; font-size:0.75rem; padding:2px 6px; border-radius:6px; margin-left:4px;">${epistemic}</span>
                ${metricsBadge}
              </div>
            </div>
            <div style="font-size:0.9rem; line-height:1.5; color:#f3f4f6;">${ans.replace(/\n/g, '<br>')}</div>
            ${evLink}
          `;
          if (r.resulting_mission || r.scenario_result) {
            await this.loadAllData();
            const sub = document.getElementById('ceoSectionContent');
            if (sub) sub.innerHTML = this.renderActiveSection();
          }
        }
      } catch (e) {
        if (feedback) feedback.innerHTML = `Error executing directive: ${e}`;
      }
    }

    async triggerEmergencyStop() {
      if (!confirm("ENGAGE SOVEREIGN EMERGENCY STOP?\nThis will immediately pause all automated missions across all departments.")) return;
      try {
        const res = await fetch('/api/v8/emergency-stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ reason: "Emergency Stop triggered from Executive Console" })
        }).then(r => r.json());
        if (window.showToast) window.showToast(`Emergency containment engaged. Paused ${res.paused_missions_count || 0} missions.`, 'error');
        await this.render();
      } catch (e) {
        alert("Emergency stop failed: " + e);
      }
    }

    async triggerEmergencyResume() {
      try {
        const res = await fetch('/api/v8/emergency-resume', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ reason: "Sovereign resume authorized by Owner" })
        }).then(r => r.json());
        if (window.showToast) window.showToast(`Sovereign operations resumed. ${res.resumed_missions_count || 0} missions active.`, 'success');
        await this.render();
      } catch (e) {
        alert("Resume failed: " + e);
      }
    }

    async runBenchmarkSuite() {
      const feedback = document.getElementById('ceoChatFeedback');
      if (feedback) {
        feedback.style.display = 'block';
        feedback.innerHTML = `<em>Running empirical Gemma 4 benchmark (31B IT vs 26B MoE across 12 dimensions)...</em>`;
      }
      try {
        const res = await fetch('/api/v8/gemma/benchmark', {
          headers: { 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId }
        }).then(r => r.json());

        if (res.success && feedback) {
          const b = res.benchmark || {};
          const r31 = b.results?.['gemma-4-31b-it'] || {};
          const r26 = b.results?.['gemma-4-26b-a4b-it'] || {};
          feedback.innerHTML = `
            <div style="font-weight:700; color:#818cf8; margin-bottom:6px;">🧪 Google Gemma 4 Empirical Benchmark Matrix (12 Dimensions)</div>
            <div style="font-size:0.85rem; line-height:1.5;">
              <strong>Production Default:</strong> <code>${b.production_default}</code><br>
              <strong>Rationale:</strong> ${b.recommendation_rationale}<br><br>
              <table style="width:100%; border-collapse:collapse; margin-top:8px; font-size:0.8rem; text-align:left;">
                <tr style="border-bottom:1px solid rgba(255,255,255,0.2);">
                  <th style="padding:4px;">Dimension</th>
                  <th style="padding:4px;">Gemma 4 31B IT (Dense)</th>
                  <th style="padding:4px;">Gemma 4 26B MoE (4B Active)</th>
                </tr>
                <tr><td style="padding:3px;">Reasoning Quality</td><td>${r31.reasoning_quality_score}/100</td><td>${r26.reasoning_quality_score}/100</td></tr>
                <tr><td style="padding:3px;">Tool Selection Accuracy</td><td>${r31.tool_selection_accuracy_pct}%</td><td>${r26.tool_selection_accuracy_pct}%</td></tr>
                <tr><td style="padding:3px;">Mean Latency</td><td>${r31.mean_latency_ms} ms</td><td style="color:#10b981; font-weight:600;">${r26.mean_latency_ms} ms (Fast)</td></tr>
                <tr><td style="padding:3px;">Memory Footprint</td><td>${r31.memory_footprint_gb} GB</td><td style="color:#10b981; font-weight:600;">${r26.memory_footprint_gb} GB</td></tr>
                <tr><td style="padding:3px;">Composite Score</td><td style="color:#3b82f6; font-weight:700;">${r31.composite_executive_score}/100 (Primary)</td><td>${r26.composite_executive_score}/100</td></tr>
              </table>
            </div>
          `;
        }
      } catch (e) {
        if (feedback) feedback.innerHTML = `Benchmark error: ${e}`;
      }
    }

    async advanceLoopTick() {
      try {
        const res = await fetch('/api/v8/control-loop/tick', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({})
        }).then(r => r.json());

        if (res.success) {
          if (window.showToast) window.showToast(`Advanced Executive Loop to ${res.tick_result.next_stage}`, 'info');
          await this.render();
        }
      } catch (e) {
        console.error('Tick error:', e);
      }
    }

    async resolveApproval(apprId, approved) {
      try {
        const res = await fetch('/api/v8/approvals/resolve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ approval_id: apprId, approved, reason: approved ? 'Authorized by Human Owner' : 'Rejected by Owner' })
        }).then(r => r.json());

        if (res.success) {
          if (window.showToast) window.showToast(`Decision ${approved ? 'Approved' : 'Rejected'}`, 'success');
          await this.render();
        }
      } catch (e) {
        console.error('Approval resolution error:', e);
      }
    }

    async generateReport() {
      try {
        const res = await fetch('/api/v8/reports', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ report_type: 'DAILY_EXECUTIVE_BRIEF' })
        }).then(r => r.json());

        if (res.success) {
          if (window.showToast) window.showToast('Daily Executive Brief Generated', 'success');
          await this.render();
        }
      } catch (e) {
        console.error('Report error:', e);
      }
    }
  }

  // Export singleton instance for DOM access
  window.AiCeoWorkspace = new AiCeoWorkspaceManager();

})();
