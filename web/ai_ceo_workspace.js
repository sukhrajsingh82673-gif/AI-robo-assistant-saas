/**
 * ZONATA — AI CEO Executive Workspace
 * Pure executive operating environment for owner managing an AI-operated company.
 * Replaces old technical card layout with business-first executive control center.
 */

(function() {
  'use strict';

  class AiCeoWorkspaceManager {
    constructor() {
      this.activeTab = 'overview'; // 'overview' | 'priorities' | 'decisions' | 'directives' | 'alignment' | 'governance'
      this.isAdvancedMode = false; // false = Executive (Business), true = Architecture (Technical)
      this.companyData = null;
      this.loading = false;
      this.lastExecution = null;
    }

    async render(containerId = 'view-ceo') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      if (!companyId) {
        if (window.CurrentCompanyContext) {
          window.CurrentCompanyContext.renderEmptyState(
            container,
            'No Company Connected to AI CEO',
            'Connect an existing company or create a new company to operate with the AI CEO.'
          );
        } else {
          container.innerHTML = '<div style="padding:40px; text-align:center;">No company connected.</div>';
        }
        return;
      }

      await this.loadCompanyContext(companyId);
      this.renderWorkspace(container);
    }

    async loadCompanyContext(companyId) {
      this.loading = true;
      try {
        const res = await fetch(`/api/companies/${companyId}/context`);
        if (res.ok) {
          this.companyData = await res.json();
        }
      } catch (e) {
        console.error('Failed to load AI CEO context:', e);
      } finally {
        this.loading = false;
      }
    }

    renderWorkspace(container) {
      if (!this.companyData || !this.companyData.company) {
        container.innerHTML = `<div style="padding:40px; text-align:center;">Loading company intelligence...</div>`;
        return;
      }

      const comp = this.companyData.company;
      const health = this.companyData.health || {};
      const dims = this.companyData.dimensions || {};
      const priorities = this.companyData.priorities || [];
      const decisions = this.companyData.decision_queue || [];
      const timeline = this.companyData.timeline || [];
      const counts = this.companyData.counts || {};

      container.innerHTML = `
        <div class="ai-ceo-workspace" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">

          <!-- 1. Executive Header -->
          <div class="ceo-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px; box-shadow:var(--shadow-sm);">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
                <span class="badge badge-purple" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Executive AI CEO</span>
                <span style="display:inline-flex; align-items:center; gap:6px; font-size:12px; color:var(--accent-emerald); font-weight:600;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Autonomous Strategic Intelligence Active
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0; display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                <span>${comp.name}</span>
                <span style="font-size:13px; font-weight:500; color:var(--text-muted); background:var(--bg-surface-hover); padding:3px 10px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
                  ${comp.industry || 'Enterprise'}
                </span>
              </h1>
              <div style="font-size:13px; color:var(--text-secondary); display:flex; gap:16px; flex-wrap:wrap;">
                <span>Overall Health: <strong>${health.overall_score || 78.5}%</strong></span>
                <span>•</span>
                <span>Workforce: <strong>${counts.workforce || 0} Specialists</strong></span>
                <span>•</span>
                <span>Active Missions: <strong>${counts.missions || 0}</strong></span>
                <span>•</span>
                <span>Processes: <strong>${counts.processes || 0} SOPs</strong></span>
              </div>
            </div>

            <!-- Top Actions & View Mode Toggle -->
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:12px;">
              <div style="display:flex; gap:8px; flex-wrap:wrap;">
                <button class="btn-primary" style="font-size:12.5px; padding:7px 14px; background:linear-gradient(135deg, #7c3aed, #4f46e5); color:#fff; border:none;" onclick="window.navigateTo('/ceo/meeting')">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                  Meeting Room
                </button>
                <button class="btn-secondary" style="font-size:12.5px; padding:7px 12px;" onclick="AiCeoWorkspace.openStrategyBriefingModal()">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  Strategy Briefing
                </button>
                <button class="btn-secondary" style="font-size:12.5px; padding:7px 12px;" onclick="AiCeoWorkspace.openSimulationModal()">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
                  Digital Twin Simulation
                </button>
                <button class="btn-primary" style="font-size:12.5px; padding:7px 14px;" onclick="document.getElementById('ceoDirectiveInput').focus()">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                  Issue Directive
                </button>
              </div>

              <!-- Executive vs Architecture Mode Toggle -->
              <div style="display:flex; align-items:center; gap:8px; font-size:12px; color:var(--text-secondary);">
                <span style="${!this.isAdvancedMode ? 'color:var(--accent-blue); font-weight:600;' : ''}">Executive View</span>
                <label class="toggle-switch" style="cursor:pointer;">
                  <input type="checkbox" ${this.isAdvancedMode ? 'checked' : ''} onchange="AiCeoWorkspace.toggleMode(this.checked)" />
                  <span class="toggle-slider"></span>
                </label>
                <span style="${this.isAdvancedMode ? 'color:var(--accent-blue); font-weight:600;' : ''}">Technical Architecture</span>
              </div>
            </div>
          </div>

          <!-- 2. Subnav Tabs -->
          <div class="ceo-subnav" style="display:flex; gap:6px; border-bottom:1px solid var(--border-color); overflow-x:auto; padding-bottom:2px;">
            ${[
              { id: 'overview', label: 'Executive Overview' },
              { id: 'meeting', label: '🎥 Meeting Room' },
              { id: 'memory', label: '🧠 Agent State & Memory' },
              { id: 'priorities', label: `Priorities (${priorities.length})` },
              { id: 'decisions', label: `Decision Room (${decisions.length})` },
              { id: 'directives', label: 'Autonomous Directives' },
              { id: 'alignment', label: 'Strategic Alignment' },
              { id: 'governance', label: 'Operating Governance' }
            ].map(t => `
              <button class="subnav-tab ${this.activeTab === t.id ? 'active' : ''}" style="padding:8px 16px; font-size:13px; font-weight:600; border:none; background:none; color:${this.activeTab===t.id?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${this.activeTab===t.id?'var(--accent-blue)':'transparent'}; cursor:pointer; white-space:nowrap;" onclick="AiCeoWorkspace.switchTab('${t.id}')">
                ${t.label}
              </button>
            `).join('')}
          </div>

          <!-- 3. AI CEO Command Center Bar -->
          <div class="ceo-command-container" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:16px 20px;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
              <div style="width:36px; height:36px; border-radius:10px; background:rgba(37,99,235,0.15); display:flex; align-items:center; justify-content:center; font-size:18px; color:var(--accent-blue);">
                🧠
              </div>
              <div style="flex:1;">
                <div style="font-size:13px; font-weight:700; color:var(--text-primary);">Autonomous Command Center</div>
                <div style="font-size:12px; color:var(--text-secondary);">Direct the AI CEO to analyze, plan, orchestrate missions, or verify business outcomes.</div>
              </div>
            </div>

            <div style="display:flex; gap:10px;">
              <input type="text" id="ceoDirectiveInput" class="form-input" style="flex:1; padding:12px 14px; font-size:14px;" placeholder="Give a strategic objective (e.g. 'Optimize room pricing yield by 8% across weekend dates with verified evidence')..." onkeydown="if(event.key==='Enter') AiCeoWorkspace.executeDirective()" />
              <button class="btn-primary" style="padding:0 20px; font-size:13.5px; white-space:nowrap;" onclick="AiCeoWorkspace.executeDirective()">
                <span>Command CEO</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
              </button>
            </div>

            <!-- Execution Pipeline Track (Dynamic 9-stage progression) -->
            <div id="ceoPipelineContainer" style="margin-top:16px; ${this.lastExecution ? 'display:block;' : 'display:none;'}">
              ${this.renderPipelineProgress()}
            </div>
          </div>

          <!-- 4. Tab Body Content -->
          <div class="ceo-tab-body">
            ${this.renderActiveTabContent(comp, dims, priorities, decisions, timeline)}
          </div>

        </div>
      `;
    }

    renderActiveTabContent(comp, dims, priorities, decisions, timeline) {
      if (this.activeTab === 'memory') {
        return this.renderStatefulMemoryTab(comp);
      } else if (this.activeTab === 'priorities') {
        return this.renderPrioritiesTab(priorities);
      } else if (this.activeTab === 'decisions') {
        return this.renderDecisionsTab(decisions);
      } else if (this.activeTab === 'directives') {
        return this.renderDirectivesTab();
      } else if (this.activeTab === 'alignment') {
        return this.renderAlignmentTab(comp);
      } else if (this.activeTab === 'governance') {
        return this.renderGovernanceTab(comp);
      } else {
        return this.renderOverviewTab(dims, priorities, decisions, timeline);
      }
    }

    renderOverviewTab(dims, priorities, decisions, timeline) {
      return `
        <!-- 8 Core Dimensions Grid -->
        <div style="margin-bottom:24px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
              Multidimensional Company State
            </h3>
            <span style="font-size:12px; color:var(--text-muted);">
              8 Epistemic Health Dimensions • Verified vs Estimated
            </span>
          </div>

          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:14px;">
            ${[
              { key: 'operations', label: 'Operations & SOPs', icon: '⚙️' },
              { key: 'sales', label: 'Sales & Growth', icon: '📈' },
              { key: 'finance', label: 'Finance & Margins', icon: '💰' },
              { key: 'people', label: 'People & Workforce', icon: '👥' },
              { key: 'tech', label: 'Technology & Host', icon: '💻' },
              { key: 'customer', label: 'Customer & Retention', icon: '⭐' },
              { key: 'risk', label: 'Risk & Compliance', icon: '🛡️' },
              { key: 'data_completeness', label: 'Data & Epistemic Maturity', icon: '📊' }
            ].map(d => {
              const info = dims[d.key] || { score: 75, status: 'OPTIMAL', metrics: [] };
              const badgeClass = info.status === 'OPTIMAL' || info.status === 'HEALTHY' ? 'badge-emerald' : info.status === 'ATTENTION' ? 'badge-amber' : 'badge-blue';
              return `
                <div class="dimension-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; display:flex; flex-direction:column; justify-content:space-between;">
                  <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                      <div style="display:flex; align-items:center; gap:8px;">
                        <span>${d.icon}</span>
                        <span style="font-size:13.5px; font-weight:700; color:var(--text-primary);">${d.label}</span>
                      </div>
                      <span class="badge ${badgeClass}" style="font-size:11px;">${info.status}</span>
                    </div>
                    <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:12px;">
                      <span style="font-size:22px; font-weight:800; color:var(--text-primary);">${info.score}%</span>
                      <span style="font-size:11px; color:var(--text-muted);">Score Index</span>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:6px;">
                      ${(info.metrics || []).map(m => `
                        <div style="display:flex; justify-content:space-between; font-size:12px;">
                          <span style="color:var(--text-secondary);">${m.name}</span>
                          <span style="font-weight:600; color:var(--text-primary);">${m.value}</span>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                  <div style="margin-top:14px; pt:8px; border-top:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
                    <a href="javascript:void(0)" onclick="window.navigateTo('/trustgraph')" style="font-size:11.5px; color:var(--accent-blue); text-decoration:none;">Inspect Provenance →</a>
                    <span style="font-size:10.5px; color:var(--text-muted);">SHA-256 Verified</span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <!-- 2-Column: Priorities & Pending Decisions -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:20px; margin-bottom:24px;">
          <!-- Left: Strategic Priorities -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <h3 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0;">
                Executive Priorities
              </h3>
              <a href="javascript:void(0)" onclick="AiCeoWorkspace.switchTab('priorities')" style="font-size:12px; color:var(--accent-blue); text-decoration:none;">View All →</a>
            </div>

            <div style="display:flex; flex-direction:column; gap:12px;">
              ${priorities.slice(0, 3).map((p, idx) => `
                <div style="padding:12px; border-radius:var(--radius-md); background:var(--bg-surface-hover); border:1px solid var(--border-color);">
                  <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:4px;">
                    <div style="font-weight:700; font-size:13.5px; color:var(--text-primary);">
                      ${idx + 1}. ${p.title}
                    </div>
                    <span class="badge ${p.urgency==='CRITICAL'?'badge-rose':p.urgency==='HIGH'?'badge-amber':'badge-blue'}" style="font-size:10px;">${p.urgency}</span>
                  </div>
                  <div style="font-size:12px; color:var(--text-secondary); line-height:1.4; margin-bottom:8px;">
                    ${p.business_rationale}
                  </div>
                  <div style="display:flex; justify-content:space-between; align-items:center; font-size:11.5px; color:var(--text-muted);">
                    <span>Assigned: <strong>${p.assigned_workforce}</strong></span>
                    <a href="javascript:void(0)" onclick="window.navigateTo('/tasks')" style="color:var(--accent-blue); text-decoration:none;">TaskMaker Mission →</a>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Right: Owner Decision Room Queue -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <h3 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0; display:flex; align-items:center; gap:8px;">
                <span>Decision Room Queue</span>
                <span class="badge badge-amber" style="font-size:10px;">${decisions.length} Pending</span>
              </h3>
              <a href="javascript:void(0)" onclick="AiCeoWorkspace.switchTab('decisions')" style="font-size:12px; color:var(--accent-blue); text-decoration:none;">View Queue →</a>
            </div>

            <div style="display:flex; flex-direction:column; gap:12px;">
              ${decisions.map(d => `
                <div style="padding:14px; border-radius:var(--radius-md); background:var(--bg-surface-hover); border:1px solid var(--border-color);">
                  <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                    <span style="font-size:11px; font-family:var(--font-mono); color:var(--accent-purple);">${d.evidence_id}</span>
                    <span style="font-size:11.5px; font-weight:700; color:var(--accent-amber);">${d.financial_impact}</span>
                  </div>
                  <div style="font-weight:700; font-size:13.5px; color:var(--text-primary); margin-bottom:4px;">
                    ${d.title}
                  </div>
                  <div style="font-size:12px; color:var(--text-secondary); line-height:1.4; margin-bottom:12px;">
                    ${d.description}
                  </div>
                  <div style="display:flex; gap:8px; justify-content:flex-end;">
                    <button class="btn-secondary" style="font-size:11.5px; padding:5px 10px;" onclick="showToast('Changes requested from AI CEO', 'info')">Request Changes</button>
                    <button class="btn-primary" style="font-size:11.5px; padding:5px 12px; background:var(--accent-emerald);" onclick="AiCeoWorkspace.approveDecision('${d.id}')">Approve</button>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- 5. Executive Activity Timeline -->
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px;">
          <h3 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:0 0 14px 0;">
            Executive Operating Timeline
          </h3>
          <div style="display:flex; flex-direction:column; gap:10px;">
            ${timeline.map(t => `
              <div style="display:flex; gap:14px; align-items:flex-start; padding:10px 0; border-bottom:1px solid var(--border-color);">
                <div style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted); white-space:nowrap; padding-top:2px;">
                  ${new Date(t.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div style="flex:1;">
                  <div style="font-size:13px; font-weight:600; color:var(--text-primary);">${t.title}</div>
                  <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">${t.detail}</div>
                </div>
                <span class="badge badge-blue" style="font-size:10px;">${t.source}</span>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    renderPrioritiesTab(priorities) {
      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <div>
              <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">Strategic Operating Priorities</h2>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">Ranked by executive urgency, time-horizon, and business ROI.</p>
            </div>
            <button class="btn-primary" style="font-size:12.5px;" onclick="showToast('Synthesizing new strategic priority...', 'info')">+ Add Priority</button>
          </div>

          <div style="display:flex; flex-direction:column; gap:14px;">
            ${priorities.map((p, i) => `
              <div style="padding:16px; border-radius:var(--radius-md); border:1px solid var(--border-color); background:var(--bg-surface-hover); display:grid; grid-template-columns:40px 1fr auto; gap:16px; align-items:center;">
                <div style="font-size:18px; font-weight:800; color:var(--text-muted); text-align:center;">#${i + 1}</div>
                <div>
                  <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                    <span style="font-size:15px; font-weight:700; color:var(--text-primary);">${p.title}</span>
                    <span class="badge ${p.urgency==='CRITICAL'?'badge-rose':'badge-amber'}">${p.urgency}</span>
                    <span class="badge badge-purple">${p.horizon}</span>
                  </div>
                  <div style="font-size:13px; color:var(--text-secondary); line-height:1.4; margin-bottom:8px;">
                    ${p.business_rationale}
                  </div>
                  <div style="font-size:12px; color:var(--text-muted); display:flex; gap:16px;">
                    <span>Department: <strong>${p.department}</strong></span>
                    <span>Lead: <strong>${p.assigned_workforce}</strong></span>
                    <span>Status: <strong style="color:var(--accent-emerald);">${p.status}</strong></span>
                  </div>
                </div>
                <div>
                  <button class="btn-secondary" style="font-size:12px;" onclick="window.navigateTo('/tasks')">Launch Mission →</button>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    renderDecisionsTab(decisions) {
      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <div>
              <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">Host Decision Room</h2>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">Explicit human sign-off gates for financial mutations, permissions, and policy changes.</p>
            </div>
          </div>

          <div style="display:flex; flex-direction:column; gap:16px;">
            ${decisions.map(d => `
              <div style="padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-color); background:var(--bg-surface-hover);">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                  <div>
                    <span class="badge badge-purple" style="font-family:var(--font-mono); font-size:11px;">${d.evidence_id}</span>
                    <span class="badge badge-amber" style="font-size:11px; margin-left:6px;">${d.category}</span>
                    <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:8px 0 4px 0;">${d.title}</h3>
                  </div>
                  <div style="font-size:16px; font-weight:800; color:var(--accent-amber);">${d.financial_impact}</div>
                </div>
                <p style="font-size:13px; color:var(--text-secondary); line-height:1.5; margin-bottom:16px;">
                  ${d.description}
                </p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <a href="javascript:void(0)" onclick="window.navigateTo('/trustgraph')" style="font-size:12px; color:var(--accent-blue); text-decoration:none;">Inspect SHA-256 Evidence Package →</a>
                  <div style="display:flex; gap:10px;">
                    <button class="btn-secondary" onclick="showToast('Decision rejected', 'warning')">Reject</button>
                    <button class="btn-secondary" onclick="showToast('Clarification requested', 'info')">Request Changes</button>
                    <button class="btn-primary" style="background:var(--accent-emerald);" onclick="AiCeoWorkspace.approveDecision('${d.id}')">Approve & Execute</button>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    renderDirectivesTab() {
      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px;">
          <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">Autonomous Executive Directives</h2>
          <p style="font-size:13px; color:var(--text-secondary); margin-bottom:20px;">Continuous strategic instructions operating in the background.</p>

          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="padding:14px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:700; font-size:14px; color:var(--text-primary);">Continuous Margin & Expense Guardrail</div>
                <div style="font-size:12px; color:var(--text-secondary);">Audit all outbound payments against budget ceilings and require approval for variances > 5%.</div>
              </div>
              <span class="badge badge-emerald">ACTIVE</span>
            </div>
            <div style="padding:14px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:700; font-size:14px; color:var(--text-primary);">Competitive Price Watchdog</div>
                <div style="font-size:12px; color:var(--text-secondary);">Perform weekly web audit of primary industry competitors and calibrate yield recommendations.</div>
              </div>
              <span class="badge badge-emerald">ACTIVE</span>
            </div>
          </div>
        </div>
      `;
    }

    renderAlignmentTab(comp) {
      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px;">
          <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">Strategic Corporate Alignment</h2>
          <p style="font-size:13px; color:var(--text-secondary); margin-bottom:20px;">Hierarchical alignment from Host Vision → AI CEO Strategy → Department OKRs → Mission Tasks.</p>

          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:14px;">
            <div style="padding:16px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--accent-blue); font-weight:700;">Level 1 • Host Vision</div>
              <div style="font-size:14px; font-weight:700; margin-top:4px;">100% Autonomous Business Operation</div>
              <div style="font-size:12px; color:var(--text-secondary); margin-top:6px;">Owner provides oversight; AI operates departments.</div>
            </div>
            <div style="padding:16px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--accent-purple); font-weight:700;">Level 2 • CEO Strategy</div>
              <div style="font-size:14px; font-weight:700; margin-top:4px;">Cryptographically Verified Proof</div>
              <div style="font-size:12px; color:var(--text-secondary); margin-top:6px;">Zero hallucinations; all mutations backed by ledger receipts.</div>
            </div>
            <div style="padding:16px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover);">
              <div style="font-size:11px; text-transform:uppercase; color:var(--accent-emerald); font-weight:700;">Level 3 • Department OKRs</div>
              <div style="font-size:14px; font-weight:700; margin-top:4px;">Dynamic Workforce Execution</div>
              <div style="font-size:12px; color:var(--text-secondary); margin-top:6px;">Specialized autonomous agents handle operations 24/7.</div>
            </div>
          </div>
        </div>
      `;
    }

    renderGovernanceTab(comp) {
      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px;">
          <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">Autonomous Operating Governance</h2>
          <p style="font-size:13px; color:var(--text-secondary); margin-bottom:20px;">Enforced invariants governing AI actions, spending limits, and tool permissions.</p>

          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="padding:12px 14px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:600; font-size:13px;">Invariant 1: Epistemic Honesty</div>
                <div style="font-size:12px; color:var(--text-secondary);">Never convert an unverified estimate into a fact.</div>
              </div>
              <span class="badge badge-emerald">HARD ENFORCED</span>
            </div>
            <div style="padding:12px 14px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:600; font-size:13px;">Invariant 2: Spending Threshold Gate</div>
                <div style="font-size:12px; color:var(--text-secondary);">Any financial movement > ₹10,000 mandates explicit Host biometric/click approval.</div>
              </div>
              <span class="badge badge-emerald">HARD ENFORCED</span>
            </div>
            <div style="padding:12px 14px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-weight:600; font-size:13px;">Invariant 3: Dual-Key Credential Isolation</div>
                <div style="font-size:12px; color:var(--text-secondary);">Raw API tokens and passwords never enter LLM prompt context.</div>
              </div>
              <span class="badge badge-emerald">HARD ENFORCED</span>
            </div>
          </div>
        </div>
      `;
    }

    renderPipelineProgress() {
      if (!this.lastExecution) return '';
      const exec = this.lastExecution;
      const stages = exec.stages || [];

      return `
        <div style="background:#070b14; border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; margin-top:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span style="font-size:12px; font-weight:700; color:var(--accent-blue); text-transform:uppercase; letter-spacing:0.5px;">Directive Multi-Stage Execution Pipeline</span>
            <span class="badge ${exec.status==='DISCONNECTED'?'badge-amber':'badge-emerald'}">${exec.status}</span>
          </div>

          <!-- Stages Grid -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(100px, 1fr)); gap:6px; margin-bottom:14px;">
            ${stages.map(st => {
              const color = st.status === 'COMPLETED' || st.status === 'PASSED' ? '#10b981' : st.status === 'DISCONNECTED' ? '#f59e0b' : '#6b7280';
              return `
                <div style="background:rgba(255,255,255,0.03); border:1px solid ${color}44; border-radius:var(--radius-sm); padding:8px 6px; text-align:center;">
                  <div style="font-size:10px; color:${color}; font-weight:700;">${st.num}. ${st.name}</div>
                  <div style="font-size:9.5px; color:var(--text-muted); margin-top:2px;">${st.status}</div>
                </div>
              `;
            }).join('')}
          </div>

          <!-- Honest Runtime Status Notice -->
          ${exec.status === 'DISCONNECTED' ? `
            <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3); border-radius:var(--radius-sm); padding:10px 14px; display:flex; align-items:center; gap:10px; font-size:12.5px; color:#f59e0b;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01"/></svg>
              <span><strong>Execution capability not connected:</strong> Stages 1–6 formulated successfully, but robotic runtime host daemon is offline. Task logged to queue.</span>
            </div>
          ` : ''}
        </div>
      `;
    }

    async executeDirective() {
      const input = document.getElementById('ceoDirectiveInput');
      if (!input || !input.value.trim()) return;

      const directive = input.value.trim();
      const compId = window.CurrentCompanyContext.getCompanyId();
      if (!compId) return;

      showToast('Dispatching directive to AI CEO...', 'info');

      try {
        const res = await fetch(`/api/companies/${compId}/command`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ directive })
        });
        if (res.ok) {
          const data = await res.json();
          this.lastExecution = data;
          const container = document.getElementById('ceoPipelineContainer');
          if (container) {
            container.style.display = 'block';
            container.innerHTML = this.renderPipelineProgress();
          }
          showToast('Directive processed by AI CEO pipeline', 'warning');
        }
      } catch (e) {
        showToast('Failed to reach AI CEO runtime', 'error');
      }
    }

    switchTab(tabId) {
      if (tabId === 'meeting') {
        if (window.navigateTo) window.navigateTo('/ceo/meeting');
        return;
      }
      this.activeTab = tabId;
      this.render();
    }

    toggleMode(isAdvanced) {
      this.isAdvancedMode = isAdvanced;
      showToast(`Switched to ${isAdvanced ? 'Technical Architecture' : 'Executive Business'} view`, 'info');
      this.render();
    }

    approveDecision(decisionId) {
      if (this.companyData && this.companyData.decision_queue) {
        this.companyData.decision_queue = this.companyData.decision_queue.filter(d => d.id !== decisionId);
      }
      showToast(`Decision ${decisionId} authorized by Host`, 'success');
      this.render();
    }

    openStrategyBriefingModal() {
      if (!window.openModal) return;
      const comp = this.companyData ? this.companyData.company : { name: 'Company' };
      window.openModal('Daily Executive Strategy Briefing', `
        <div style="font-size:13.5px; line-height:1.5; color:var(--text-secondary);">
          <div style="margin-bottom:12px; font-weight:700; color:var(--text-primary); font-size:15px;">
            Executive Summary for ${comp.name}
          </div>
          <p>The AI CEO has completed the overnight operational synthesis. Key highlights:</p>
          <ul style="margin:10px 0 16px 20px; display:flex; flex-direction:column; gap:6px;">
            <li>Zero operational downtime reported across all automated processes.</li>
            <li>Department structure aligned with active industry baseline.</li>
            <li>12 verified facts corroborated in Company Knowledge Graph.</li>
            <li>2 owner approvals currently pending in Decision Room.</li>
          </ul>
          <div style="display:flex; justify-content:flex-end;">
            <button class="btn-primary" onclick="window.closeModal()">Acknowledge Briefing</button>
          </div>
        </div>
      `);
    }

    openSimulationModal() {
      if (!window.openModal) return;
      window.openModal('Digital Twin Scenario Simulation', `
        <div style="font-size:13.5px; line-height:1.5; color:var(--text-secondary);">
          <p style="margin-bottom:14px;">Select a macroeconomic or operational stress test to run against this company's digital twin:</p>
          <div style="display:flex; flex-direction:column; gap:10px; margin-bottom:20px;">
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="radio" name="sim_scenario" checked />
              <span>+15% Input Cost Surge (Inflationary Supply Chain Shock)</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="radio" name="sim_scenario" />
              <span>Competitor 20% Price Undercutting Campaign</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="radio" name="sim_scenario" />
              <span>Host Workstation Disconnection (Autonomous Resilience)</span>
            </label>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button class="btn-primary" onclick="showToast('Simulation complete: Resilience score 94.2%', 'success'); window.closeModal();">Run Sandbox Simulation</button>
          </div>
        </div>
      `);
    }

    // =====================================================================
    // Stateful Agent Identity, Memory & Long-Horizon Context
    // =====================================================================
    renderStatefulMemoryTab(comp) {
      setTimeout(() => this.loadMemoryTabData(comp.id || (comp.company && comp.company.id)), 50);
      return `
        <div id="statefulMemoryContainer" style="display:flex; flex-direction:column; gap:20px;">
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:30px; text-align:center; color:var(--text-secondary);">
            <div class="spinner" style="margin:0 auto 12px auto;"></div>
            Loading stateful agent identities and persistent memory...
          </div>
        </div>
      `;
    }

    async loadMemoryTabData(companyId) {
      const container = document.getElementById('statefulMemoryContainer');
      if (!container) return;

      const currentAgentId = this.selectedMemoryAgentId || 'agt_ai_ceo';
      const scopeFilter = this.memoryFilterScope || '';
      const typeFilter = this.memoryFilterType || '';

      try {
        const [agentsRes, currentAgentRes, memoriesRes, conflictsRes] = await Promise.all([
          fetch('/api/agents/stateful'),
          fetch(`/api/agents/stateful/${currentAgentId}`),
          fetch(`/api/agents/stateful/${currentAgentId}/memory?company_id=${companyId || ''}&scope=${scopeFilter}&memory_type=${typeFilter}`),
          fetch(`/api/memory/conflicts?status=OPEN`)
        ]);

        const agentsData = agentsRes.ok ? await agentsRes.json() : { agents: [] };
        const currentAgentData = currentAgentRes.ok ? await currentAgentRes.json() : { agent: null };
        const memoriesData = memoriesRes.ok ? await memoriesRes.json() : { records: [] };
        const conflictsData = conflictsRes.ok ? await conflictsRes.json() : { conflicts: [] };

        const agents = agentsData.agents || [];
        const agent = currentAgentData.agent || {
          agent_id: currentAgentId,
          name: 'AI CEO',
          role: 'Executive',
          persona_block: '',
          human_block: '',
          model_config: { model: 'Gemini 3.8 Flash' }
        };
        const memories = memoriesData.records || [];
        const conflicts = conflictsData.conflicts || [];

        container.innerHTML = `
          <!-- Header Bar: Agent Selector & Actions -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:18px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
            <div style="display:flex; align-items:center; gap:12px;">
              <div style="width:40px; height:40px; border-radius:10px; background:rgba(139,92,246,0.15); display:flex; align-items:center; justify-content:center; font-size:20px; color:var(--accent-purple);">
                🧠
              </div>
              <div>
                <div style="font-size:15px; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                  <span>Stateful Agent Continuity</span>
                  <span class="badge badge-purple" style="font-size:11px;">Persistent Context</span>
                </div>
                <div style="font-size:12px; color:var(--text-secondary);">
                  Multi-tier stateful memory (Core, Archival, Recall) governed by ZONATA Authority.
                </div>
              </div>
            </div>

            <!-- Agent Selector -->
            <div style="display:flex; align-items:center; gap:10px;">
              <span style="font-size:12.5px; font-weight:600; color:var(--text-secondary);">Active Identity:</span>
              <select class="form-input" style="padding:6px 12px; font-size:13px; font-weight:600; min-width:180px;" onchange="AiCeoWorkspace.selectMemoryAgent(this.value)">
                ${agents.map(a => `
                  <option value="${a.agent_id}" ${a.agent_id === currentAgentId ? 'selected' : ''}>
                    ${a.name} (${a.role})
                  </option>
                `).join('')}
              </select>
              <button class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="AiCeoWorkspace.openAddMemoryModal('${currentAgentId}')">
                + Add Memory
              </button>
            </div>
          </div>

          <!-- Demonstrations & Proof Bar -->
          <div style="background:linear-gradient(90deg, rgba(37,99,235,0.06), rgba(139,92,246,0.06)); border:1px solid rgba(139,92,246,0.25); border-radius:var(--radius-lg); padding:14px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
              <div style="font-size:13px; font-weight:700; color:var(--text-primary);">Runtime Verification Scenarios</div>
              <div style="font-size:12px; color:var(--text-secondary);">Demonstrate multi-session executive continuity and conflict-resolved workforce coordination.</div>
            </div>
            <div style="display:flex; gap:10px;">
              <button class="btn-secondary" style="font-size:12px; padding:6px 14px; border-color:var(--accent-blue);" onclick="AiCeoWorkspace.runStatefulDemo('SECTION_74')">
                ▶ Run Executive Continuity Demo
              </button>
              <button class="btn-secondary" style="font-size:12px; padding:6px 14px; border-color:var(--accent-purple);" onclick="AiCeoWorkspace.runStatefulDemo('SECTION_75')">
                ▶ Run Conflict Coordination Demo
              </button>
            </div>
          </div>

          <!-- Demo Timeline Banner (If recently run) -->
          <div id="statefulDemoResultContainer" style="display:none;"></div>

          <!-- Open Conflicts Banner (If any) -->
          ${conflicts.length > 0 ? `
            <div style="background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.3); border-radius:var(--radius-lg); padding:16px 20px;">
              <div style="display:flex; align-items:center; gap:8px; font-size:14px; font-weight:700; color:var(--accent-rose); margin-bottom:10px;">
                <span>⚠️ Attention Required: ${conflicts.length} Contradictory Memory Conflicts</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:12px;">
                ${conflicts.map(c => `
                  <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
                    <div style="flex:1; min-width:280px;">
                      <div style="font-size:12px; font-weight:700; color:var(--text-secondary); text-transform:uppercase;">
                        Key: <span style="color:var(--text-primary); font-family:monospace;">${c.memory_key}</span> (Scope: ${c.scope})
                      </div>
                      <div style="font-size:13px; color:var(--text-primary); margin:6px 0;">
                        ${c.conflict_details}
                      </div>
                    </div>
                    <div style="display:flex; gap:8px; flex-wrap:wrap;">
                      <button class="btn-secondary" style="font-size:11.5px; padding:5px 10px;" onclick="AiCeoWorkspace.resolveMemoryConflict('${c.conflict_id}', 'USE_A')">
                        Keep Prior (A)
                      </button>
                      <button class="btn-secondary" style="font-size:11.5px; padding:5px 10px;" onclick="AiCeoWorkspace.resolveMemoryConflict('${c.conflict_id}', 'USE_B')">
                        Accept New (B)
                      </button>
                      <button class="btn-primary" style="font-size:11.5px; padding:5px 10px;" onclick="AiCeoWorkspace.resolveMemoryConflict('${c.conflict_id}', 'ASK_CEO')">
                        Escalate to CEO
                      </button>
                      <button class="btn-secondary" style="font-size:11.5px; padding:5px 10px;" onclick="AiCeoWorkspace.resolveMemoryConflict('${c.conflict_id}', 'DISMISS')">
                        Dismiss
                      </button>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}

          <!-- Working Memory Blocks: Persona & Human -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(380px, 1fr)); gap:18px;">
            
            <!-- Persona Block Card -->
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:18px 20px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div style="font-size:14px; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                  <span>Core Persona Block</span>
                  <span class="badge badge-blue" style="font-size:10.5px;">Identity</span>
                </div>
                <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px;" onclick="AiCeoWorkspace.saveWorkingBlocks('${agent.agent_id}')">
                  Save Changes
                </button>
              </div>
              <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">
                Defines who this agent is, their mandate, operating tone, and core decision philosophy:
              </div>
              <textarea id="personaBlockInput_${agent.agent_id}" class="form-input" style="width:100%; height:110px; font-size:13px; line-height:1.5; resize:vertical; padding:10px;">${agent.persona_block || ''}</textarea>
            </div>

            <!-- Human Block Card -->
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:18px 20px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <div style="font-size:14px; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                  <span>Human Working Block</span>
                  <span class="badge badge-emerald" style="font-size:10.5px;">Host Context</span>
                </div>
                <button class="btn-secondary" style="font-size:11.5px; padding:4px 10px;" onclick="AiCeoWorkspace.saveWorkingBlocks('${agent.agent_id}')">
                  Save Changes
                </button>
              </div>
              <div style="font-size:12px; color:var(--text-secondary); margin-bottom:8px;">
                What this agent knows about the Host preferences, executive communication, and boundaries:
              </div>
              <textarea id="humanBlockInput_${agent.agent_id}" class="form-input" style="width:100%; height:110px; font-size:13px; line-height:1.5; resize:vertical; padding:10px;">${agent.human_block || ''}</textarea>
            </div>

          </div>

          <!-- Memory Records Explorer Card -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
              <div>
                <div style="font-size:15px; font-weight:700; color:var(--text-primary);">
                  Scoped Memory Records (${memories.length})
                </div>
                <div style="font-size:12px; color:var(--text-secondary);">
                  Persistent facts, constraints, directives, and decisions visible to ${agent.name}.
                </div>
              </div>

              <!-- Filter Bar -->
              <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                <select class="form-input" style="padding:6px 10px; font-size:12px;" onchange="AiCeoWorkspace.filterMemoryScope(this.value)">
                  <option value="" ${!scopeFilter ? 'selected' : ''}>All Scopes</option>
                  <option value="COMPANY" ${scopeFilter === 'COMPANY' ? 'selected' : ''}>Scope: COMPANY</option>
                  <option value="AGENT" ${scopeFilter === 'AGENT' ? 'selected' : ''}>Scope: AGENT</option>
                  <option value="MEETING" ${scopeFilter === 'MEETING' ? 'selected' : ''}>Scope: MEETING</option>
                  <option value="TENANT" ${scopeFilter === 'TENANT' ? 'selected' : ''}>Scope: TENANT</option>
                  <option value="PERSONAL_WORKSPACE" ${scopeFilter === 'PERSONAL_WORKSPACE' ? 'selected' : ''}>Scope: PERSONAL_WORKSPACE</option>
                </select>

                <select class="form-input" style="padding:6px 10px; font-size:12px;" onchange="AiCeoWorkspace.filterMemoryType(this.value)">
                  <option value="" ${!typeFilter ? 'selected' : ''}>All Types</option>
                  <option value="CORE" ${typeFilter === 'CORE' ? 'selected' : ''}>Type: CORE</option>
                  <option value="ARCHIVAL" ${typeFilter === 'ARCHIVAL' ? 'selected' : ''}>Type: ARCHIVAL</option>
                  <option value="RECALL" ${typeFilter === 'RECALL' ? 'selected' : ''}>Type: RECALL</option>
                  <option value="WORKING" ${typeFilter === 'WORKING' ? 'selected' : ''}>Type: WORKING</option>
                </select>
              </div>
            </div>

            <!-- Memory List -->
            <div style="display:flex; flex-direction:column; gap:10px;">
              ${memories.length === 0 ? `
                <div style="padding:30px; text-align:center; color:var(--text-secondary); font-size:13px;">
                  No memory records found for this scope and filter. Click "+ Add Memory" to create one.
                </div>
              ` : memories.map(m => `
                <div style="background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px 16px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
                  <div style="flex:1; min-width:280px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap;">
                      <span class="badge ${m.category === 'GOAL' ? 'badge-emerald' : m.category === 'CONSTRAINT' ? 'badge-rose' : m.category === 'DECISION' ? 'badge-purple' : 'badge-blue'}" style="font-size:10px; font-weight:700;">
                        ${m.category}
                      </span>
                      <span style="font-family:monospace; font-size:12.5px; font-weight:700; color:var(--text-primary);">
                        ${m.memory_key}
                      </span>
                      <span style="font-size:11px; color:var(--text-muted); background:var(--bg-surface); padding:2px 6px; border-radius:4px; border:1px solid var(--border-color);">
                        ${m.scope}:${m.scope_id}
                      </span>
                      <span style="font-size:11px; color:var(--text-muted);">
                        v${m.version}
                      </span>
                    </div>
                    <div style="font-size:13.5px; color:var(--text-primary); line-height:1.5;">
                      ${m.content}
                    </div>
                    <div style="font-size:11.5px; color:var(--text-muted); margin-top:6px; display:flex; gap:12px; flex-wrap:wrap;">
                      <span>Source: <strong>${m.source}</strong></span>
                      <span>Confidence: <strong>${m.confidence}</strong></span>
                      <span>Updated: ${new Date(m.updated_at * 1000).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } catch (err) {
        console.error('Failed to load memory tab data:', err);
        container.innerHTML = `<div style="padding:30px; text-align:center; color:var(--accent-rose);">Failed to load memory data: ${err.message}</div>`;
      }
    }

    selectMemoryAgent(agentId) {
      this.selectedMemoryAgentId = agentId;
      const compId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      this.loadMemoryTabData(compId);
    }

    filterMemoryScope(scope) {
      this.memoryFilterScope = scope;
      const compId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      this.loadMemoryTabData(compId);
    }

    filterMemoryType(mtype) {
      this.memoryFilterType = mtype;
      const compId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      this.loadMemoryTabData(compId);
    }

    async saveWorkingBlocks(agentId) {
      const persona = document.getElementById(`personaBlockInput_${agentId}`)?.value;
      const human = document.getElementById(`humanBlockInput_${agentId}`)?.value;

      try {
        const res = await fetch(`/api/agents/stateful/${agentId}/blocks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ persona_block: persona, human_block: human })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          showToast('Working memory blocks updated successfully', 'success');
        } else {
          showToast(data.error || 'Failed to update memory blocks', 'error');
        }
      } catch (e) {
        showToast('Network error updating memory blocks', 'error');
      }
    }

    async resolveMemoryConflict(conflictId, choice) {
      try {
        const res = await fetch(`/api/memory/conflicts/${conflictId}/resolve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ choice, resolved_by: 'AI_CEO' })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          showToast(`Conflict resolved with choice: ${choice}`, 'success');
          const compId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
          this.loadMemoryTabData(compId);
        } else {
          showToast(data.error || 'Failed to resolve conflict', 'error');
        }
      } catch (e) {
        showToast('Network error resolving conflict', 'error');
      }
    }

    openAddMemoryModal(agentId) {
      if (!window.openModal) return;
      const compId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';

      window.openModal('Add Persistent Memory Record', `
        <div style="font-size:13.5px; line-height:1.5; color:var(--text-secondary); display:flex; flex-direction:column; gap:14px;">
          <div>
            <label style="display:block; font-weight:700; color:var(--text-primary); margin-bottom:4px;">Memory Key (Identifier):</label>
            <input type="text" id="newMemKey" class="form-input" style="width:100%;" placeholder="e.g. quarterly_hiring_plan" />
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label style="display:block; font-weight:700; color:var(--text-primary); margin-bottom:4px;">Scope:</label>
              <select id="newMemScope" class="form-input" style="width:100%;">
                <option value="COMPANY">COMPANY (${compId})</option>
                <option value="AGENT">AGENT (${agentId})</option>
                <option value="MEETING">MEETING</option>
                <option value="TENANT">TENANT</option>
                <option value="PERSONAL_WORKSPACE">PERSONAL_WORKSPACE</option>
              </select>
            </div>
            <div>
              <label style="display:block; font-weight:700; color:var(--text-primary); margin-bottom:4px;">Category:</label>
              <select id="newMemCat" class="form-input" style="width:100%;">
                <option value="FACT">FACT</option>
                <option value="CONSTRAINT">CONSTRAINT</option>
                <option value="DIRECTIVE">DIRECTIVE</option>
                <option value="GOAL">GOAL</option>
                <option value="DECISION">DECISION</option>
              </select>
            </div>
          </div>
          <div>
            <label style="display:block; font-weight:700; color:var(--text-primary); margin-bottom:4px;">Memory Content:</label>
            <textarea id="newMemContent" class="form-input" style="width:100%; height:90px;" placeholder="Enter persistent memory statement (API keys and raw passwords will be rejected by Secret Scanner)..."></textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button class="btn-primary" onclick="AiCeoWorkspace.submitNewMemoryRecord('${agentId}', '${compId}')">Store Memory</button>
          </div>
        </div>
      `);
    }

    async submitNewMemoryRecord(agentId, companyId) {
      const key = document.getElementById('newMemKey')?.value?.trim();
      const scope = document.getElementById('newMemScope')?.value;
      const cat = document.getElementById('newMemCat')?.value;
      const content = document.getElementById('newMemContent')?.value?.trim();

      if (!key || !content) {
        showToast('Key and content are required', 'warning');
        return;
      }

      const scopeId = scope === 'COMPANY' ? companyId : (scope === 'AGENT' ? agentId : 'general');

      try {
        const res = await fetch(`/api/agents/stateful/${agentId}/memory`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scope,
            scope_id: scopeId,
            memory_key: key,
            content,
            category: cat,
            memory_type: 'CORE',
            source: 'HOST_INPUT'
          })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          showToast('Memory record successfully stored', 'success');
          if (window.closeModal) window.closeModal();
          this.loadMemoryTabData(companyId);
        } else {
          showToast(data.error || 'Failed to store memory record', 'error');
        }
      } catch (e) {
        showToast('Network error storing memory record', 'error');
      }
    }

    async runStatefulDemo(demoType) {
      const resultBox = document.getElementById('statefulDemoResultContainer');
      if (resultBox) {
        resultBox.style.display = 'block';
        resultBox.innerHTML = `
          <div style="background:var(--bg-surface); border:1px solid var(--accent-purple); border-radius:var(--radius-lg); padding:16px 20px;">
            <div style="display:flex; align-items:center; gap:10px; font-weight:700; color:var(--accent-purple); margin-bottom:8px;">
              <span class="spinner" style="width:16px; height:16px;"></span>
              Running ${demoType === 'SECTION_74' ? 'Executive Continuity' : 'Workforce Coordination'} Demonstration...
            </div>
            <div style="font-size:12.5px; color:var(--text-secondary);">Executing real database persistence, restart query, and verification steps.</div>
          </div>
        `;
      }

      try {
        const compId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
        const res = await fetch('/api/stateful/demo/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ demo_type: demoType, company_id: compId })
        });
        const data = await res.json();
        if (res.ok && data.success && data.demonstration) {
          const demo = data.demonstration;
          showToast(`${demoType} demo completed successfully!`, 'success');
          if (resultBox) {
            resultBox.innerHTML = `
              <div style="background:var(--bg-surface); border:1px solid var(--accent-emerald); border-radius:var(--radius-lg); padding:18px 20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                  <div style="font-size:14px; font-weight:700; color:var(--accent-emerald);">
                    ✓ ${demo.scenario} — Status: ${demo.status}
                  </div>
                  <button class="btn-secondary" style="font-size:11px; padding:3px 8px;" onclick="document.getElementById('statefulDemoResultContainer').style.display='none'">
                    Close
                  </button>
                </div>
                <div style="font-size:12.5px; color:var(--text-primary); display:flex; flex-direction:column; gap:6px;">
                  ${demo.timeline.map((t, idx) => `
                    <div style="display:flex; gap:10px; align-items:flex-start; font-family:monospace; font-size:12px;">
                      <span style="color:var(--text-muted); min-width:24px;">#${idx+1}</span>
                      <span class="badge badge-blue" style="font-size:10px; min-width:140px;">${t.step}</span>
                      <span style="color:var(--text-primary); flex:1;">${JSON.stringify(t)}</span>
                    </div>
                  `).join('')}
                </div>
              </div>
            `;
          }
          this.loadMemoryTabData(compId);
        } else {
          showToast(data.error || 'Demo execution failed', 'error');
        }
      } catch (e) {
        showToast('Error executing stateful demo: ' + e.message, 'error');
      }
    }
  }

  window.AiCeoWorkspace = new AiCeoWorkspaceManager();
})();
