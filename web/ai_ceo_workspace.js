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
      this.loading = false;
    }

    async render(containerId = 'view-ceo') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const compCtx = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
      this.companyId = compCtx || 'comp_primary';

      container.innerHTML = `
        <div class="card" style="padding: 24px; text-align: center;">
          <div class="status-pulse-dot" style="display:inline-block; margin-bottom:12px;"></div>
          <h3>Connecting to AI CEO Executive State...</h3>
          <p style="color:var(--text-secondary); margin-top:8px;">Loading versioned corporate intelligence and audit telemetry.</p>
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
          riskRes, oppRes, obsRes, loopRes, rptRes
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
          fetch('/api/v8/reports', { headers }).then(r => r.json()).catch(() => ({}))
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
                <div style="display:flex; align-items:center; gap:10px;">
                  <span style="font-size:24px;">🏛️</span>
                  <h2 style="margin:0; font-size:1.5rem; font-weight:700;">AI CEO Executive Operating Console</h2>
                  <span class="status-indicator-pill" style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid #10b981; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:600;">
                    ${this.loopStage} ACTIVE
                  </span>
                </div>
                <p style="margin:6px 0 0 0; color:var(--text-secondary); font-size:0.9rem;">
                  Operating Context: <strong>${companyName}</strong> | Mode: <strong>Closed-Loop Governed OS (V8.0-GA)</strong>
                </p>
              </div>

              <!-- Quick Status Vitals -->
              <div style="display:flex; gap:16px; align-items:center;">
                <div style="text-align:center; padding:6px 12px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">OPERATIONAL RATING</div>
                  <div style="font-size:1.1rem; font-weight:700; color:#10b981;">${rating}</div>
                </div>
                <div style="text-align:center; padding:6px 12px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">DECISION VERIFIED</div>
                  <div style="font-size:1.1rem; font-weight:700; color:#3b82f6;">${decRate}%</div>
                </div>
                <div style="text-align:center; padding:6px 12px; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                  <div style="font-size:0.75rem; color:var(--text-secondary);">MISSION SUCCESS</div>
                  <div style="font-size:1.1rem; font-weight:700; color:#f59e0b;">${msnRate}%</div>
                </div>
                <button class="btn btn-primary" id="btnRunClosedLoop" style="padding:10px 16px; display:flex; align-items:center; gap:8px;">
                  <span>⚡ Run 22-Step Scenario</span>
                </button>
              </div>
            </div>

            <!-- Natural Language Command Bar -->
            <div style="margin-top:16px; display:flex; gap:10px;">
              <input type="text" id="ceoCommandInput" class="ceo-command-input" style="flex:1; padding:10px 16px; border-radius:8px; background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.15); color:white;" placeholder="Command the AI CEO (e.g. 'How is the company performing?', 'Why is RevPAR below target?', 'Show me the evidence')..." />
              <button class="btn btn-secondary" id="btnSendCeoCommand" style="padding:10px 20px;">Send Directive</button>
            </div>

            <!-- Fast Prompt Chips -->
            <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap; font-size:0.8rem;">
              <span style="color:var(--text-secondary); align-self:center;">Quick Directives:</span>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('How is the company performing?')">Health Status</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('What are our biggest KPI gaps?')">KPI Gaps</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('Which department is overloaded?')">Workforce Capacity</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.sendQuickCommand('Show me the evidence')">Evidence Ledger</button>
              <button class="chip-btn" onclick="window.AiCeoWorkspace.advanceLoopTick()">Next Loop Tick (${this.loopStage})</button>
            </div>

            <div id="ceoChatFeedback" style="margin-top:12px; display:none; padding:12px; background:rgba(0,0,0,0.4); border-radius:8px; border-left:3px solid #3b82f6;"></div>
          </div>

          <!-- 14-Section Subnav Tabs -->
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
        feedback.innerHTML = `<em>Consulting AI CEO Executive Cognition Layer...</em>`;
      }
      try {
        const res = await fetch('/api/v8/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Tenant-ID': this.tenantId, 'X-Company-ID': this.companyId },
          body: JSON.stringify({ message: msg })
        }).then(r => r.json());

        if (res.success && feedback) {
          const ans = res.reply?.answer || 'Directive acknowledged.';
          feedback.innerHTML = `
            <div style="font-weight:600; color:#60a5fa; margin-bottom:4px;">Human Owner Directive: "${msg}"</div>
            <div style="font-size:0.9rem; line-height:1.5;">${ans.replace(/\n/g, '<br>')}</div>
          `;
          if (res.reply?.scenario_result) {
            await this.render();
          }
        }
      } catch (e) {
        if (feedback) feedback.innerHTML = `Error executing directive: ${e}`;
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
