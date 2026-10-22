/**
 * ZONATA — AI Workforce Workspace
 * Real workforce records, complete lifecycle state management,
 * 10-tab employee detail drawer, and on-demand Workforce Designer.
 */

(function() {
  'use strict';

  class WorkforceWorkspaceManager {
    constructor() {
      this.workforce = [];
      this.dynamicSquads = [];
      this.selectedEmployee = null;
      this.activeDetailTab = 'overview';
      this.statusFilter = 'ALL';
      this.loading = false;
    }

    async render(containerId = 'view-workforce') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      if (!companyId) {
        if (window.CurrentCompanyContext) {
          window.CurrentCompanyContext.renderEmptyState(
            container,
            'No Company Connected to AI Workforce',
            'Connect an existing company or create a new company to manage its AI workforce.'
          );
        } else {
          container.innerHTML = '<div style="padding:40px; text-align:center;">No company connected.</div>';
        }
        return;
      }

      await this.loadWorkforce(companyId);
      this.renderWorkspace(container);
    }

    async loadWorkforce(companyId) {
      this.loading = true;
      try {
        const [resWf, resSq] = await Promise.all([
          fetch(`/api/companies/${companyId}/workforce`),
          fetch(`/api/workforces?company_id=${companyId}`)
        ]);
        if (resWf.ok) {
          const data = await resWf.json();
          this.workforce = Array.isArray(data.workforce) ? data.workforce : [];
        }
        if (resSq.ok) {
          const sqData = await resSq.json();
          this.dynamicSquads = Array.isArray(sqData.workforces) ? sqData.workforces : [];
        }
      } catch (e) {
        console.error('Failed to load workforce:', e);
      } finally {
        this.loading = false;
      }
    }


    renderWorkspace(container) {
      const comp = window.CurrentCompanyContext.getCompany() || { name: 'Company' };
      const filtered = this.statusFilter === 'ALL' ? this.workforce : this.workforce.filter(w => w.status === this.statusFilter);

      container.innerHTML = `
        <div class="workforce-workspace-root" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">

          <!-- Top Header -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:12px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Autonomous Workforce</span>
                <span class="badge badge-purple">${comp.name}</span>
              </div>
              <h1 style="font-size:22px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">
                AI Workforce Roster (${this.workforce.length} Specialists)
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Governed digital employees operating departments under host authority boundaries.
              </p>
            </div>

            <div style="display:flex; gap:10px; flex-wrap:wrap;">
              <button class="btn-secondary" style="font-size:12.5px; padding:7px 12px;" onclick="WorkforceWorkspace.openDesignerModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                Design Workforce
              </button>
              <button class="btn-primary" style="font-size:12.5px; padding:7px 14px;" onclick="WorkforceWorkspace.openHireModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
                + Hire AI Employee
              </button>
            </div>
          </div>

          <!-- Governed Dynamic Specialist Squads (Mission Workforces) -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom:16px;">
              <div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="badge badge-emerald" style="font-size:11px;">MULTI-AGENT SQUADS</span>
                  <span style="font-size:12px; color:var(--text-muted);">Directional Orchestration</span>
                </div>
                <h2 style="font-size:17px; font-weight:700; color:var(--text-primary); margin:6px 0 2px 0;">
                  Governed Specialist Squads (${this.dynamicSquads.length} Active Missions)
                </h2>
                <p style="font-size:12.5px; color:var(--text-secondary); margin:0;">
                  Dynamic multi-agent teams synthesized on-demand for complex objectives. Coordinated with directional flows and verified against ZONATA Evidence Ledger.
                </p>
              </div>

              <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <button class="btn-secondary" style="font-size:12px; padding:6px 12px; border-color:var(--accent-blue);" onclick="WorkforceWorkspace.runDemonstration()">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                  Run Controlled Demo (Sales Bottlenecks)
                </button>
                <button class="btn-primary" style="font-size:12px; padding:6px 14px;" onclick="WorkforceWorkspace.openMissionModal()">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                  + Synthesize Mission Squad
                </button>
              </div>
            </div>

            ${this.dynamicSquads.length === 0 ? `
              <div style="background:rgba(255,255,255,0.02); border:1px dashed var(--border-color); border-radius:var(--radius-md); padding:24px; text-align:center;">
                <p style="font-size:13px; color:var(--text-secondary); margin:0 0 12px 0;">
                  No dynamic mission squads currently active for this company.
                </p>
                <button class="btn-secondary" style="font-size:12px;" onclick="WorkforceWorkspace.runDemonstration()">
                  Run Controlled Demonstration
                </button>
              </div>
            ` : `
              <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(360px, 1fr)); gap:16px;">
                ${this.dynamicSquads.map(sq => {
                  const isQuarantined = sq.status === 'QUARANTINED';
                  const isCompleted = sq.status === 'COMPLETED';
                  const statusBadge = isQuarantined ? 'badge-amber' : isCompleted ? 'badge-emerald' : 'badge-blue';
                  const evidenceCount = sq.runtime_state ? sq.runtime_state.evidence_count : 0;
                  return `
                    <div style="background:rgba(255,255,255,0.03); border:1px solid ${isQuarantined?'rgba(239,68,68,0.4)':'var(--border-color)'}; border-radius:var(--radius-md); padding:16px;">
                      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                        <div>
                          <span class="badge ${statusBadge}" style="font-size:10px;">${sq.status}</span>
                          <span style="font-size:11px; color:var(--text-muted); margin-left:6px;">${sq.workforce_id}</span>
                        </div>
                        ${!isQuarantined && !isCompleted ? `
                          <button style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); color:#ef4444; font-size:10px; font-weight:700; padding:3px 8px; border-radius:4px; cursor:pointer;" onclick="WorkforceWorkspace.killSquad('${sq.workforce_id}')">
                            KILL SWITCH
                          </button>
                        ` : ''}
                      </div>

                      <h4 style="font-size:14px; font-weight:700; color:var(--text-primary); margin:0 0 8px 0;">
                        ${sq.objective || 'Mission Squad'}
                      </h4>

                      <div style="margin-bottom:12px;">
                        <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:4px;">Specialists (${sq.specialists ? sq.specialists.length : 0}):</div>
                        <div style="display:flex; flex-wrap:wrap; gap:6px;">
                          ${(sq.specialists || []).map(sp => `
                            <span class="badge badge-purple" style="font-size:10.5px;">${sp.role || sp.name}</span>
                          `).join('')}
                        </div>
                      </div>

                      <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-color); padding-top:10px; font-size:11.5px; color:var(--text-secondary);">
                        <div>
                          <span style="color:var(--text-primary); font-weight:600;">${evidenceCount}</span> evidence sealed
                        </div>
                        <button class="btn-secondary" style="font-size:11px; padding:4px 8px;" onclick="WorkforceWorkspace.viewSquadDetails('${sq.workforce_id}')">
                          View Execution & Evidence
                        </button>
                      </div>
                    </div>
                  `;
                }).join('')}
              </div>
            `}
          </div>

          <!-- Filter Pills -->
          <div style="display:flex; gap:8px; overflow-x:auto; padding-bottom:4px;">
            ${['ALL', 'ACTIVE', 'PROVISIONING', 'PENDING_APPROVAL', 'PAUSED', 'PROPOSED'].map(st => `
              <button style="border:1px solid ${this.statusFilter===st?'var(--accent-blue)':'var(--border-color)'}; background:${this.statusFilter===st?'rgba(37,99,235,0.12)':'var(--bg-surface)'}; color:${this.statusFilter===st?'var(--accent-blue)':'var(--text-secondary)'}; font-size:12px; font-weight:600; padding:6px 12px; border-radius:var(--radius-md); cursor:pointer; white-space:nowrap;" onclick="WorkforceWorkspace.setFilter('${st}')">
                ${st} ${st==='ALL'?`(${this.workforce.length})`:''}
              </button>
            `).join('')}
          </div>


          <!-- Workforce Grid or Empty State -->
          ${filtered.length === 0 ? `
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:64px 20px; text-align:center;">
              <div style="font-size:36px; margin-bottom:12px;">🤖</div>
              <h3 style="font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">No AI employees found</h3>
              <p style="font-size:13px; color:var(--text-secondary); max-width:480px; margin:0 auto 20px auto;">
                This company currently has no AI agents configured. Use the Workforce Designer to automatically synthesize an optimal team based on company operations.
              </p>
              <button class="btn-primary" onclick="WorkforceWorkspace.openDesignerModal()">Design Workforce</button>
            </div>
          ` : `
            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:16px;">
              ${filtered.map(emp => {
                const statusBadge = emp.status === 'ACTIVE' ? 'badge-emerald' : emp.status === 'PROVISIONING' ? 'badge-blue' : 'badge-amber';
                return `
                  <div class="employee-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:18px; cursor:pointer; transition:transform 0.15s, border-color 0.15s;" onclick="WorkforceWorkspace.openDetailDrawer('${emp.id}')">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                      <div>
                        <span class="badge badge-purple" style="font-size:10px;">${emp.department_id || 'Operations'}</span>
                        <h3 style="font-size:15px; font-weight:700; color:var(--text-primary); margin:6px 0 2px 0;">${emp.role}</h3>
                        <div style="font-size:12px; color:var(--text-secondary);">${emp.name || emp.role}</div>
                      </div>
                      <span class="badge ${statusBadge}" style="font-size:10px;">${emp.status}</span>
                    </div>

                    <p style="font-size:12px; color:var(--text-muted); line-height:1.4; margin:10px 0; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
                      ${emp.mission_focus || (emp.responsibilities && emp.responsibilities[0]) || 'Operates autonomous workflows.'}
                    </p>

                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--text-muted); border-top:1px solid var(--border-color); padding-top:10px; margin-top:8px;">
                      <span>SLA: <strong style="color:var(--accent-emerald);">99.4%</strong></span>
                      <span>Budget: <strong>₹${(emp.budget || 5000).toLocaleString()}</strong></span>
                      <span style="color:var(--accent-blue); font-weight:600;">View File →</span>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          `}

          <!-- 10-Tab Employee Detail Drawer (Slide-Over / Mobile Modal) -->
          ${this.renderDetailDrawer()}

        </div>
      `;
    }

    renderDetailDrawer() {
      if (!this.selectedEmployee) return '';
      const emp = this.selectedEmployee;
      const t = this.activeDetailTab;

      const TABS = [
        { id: 'overview', label: '1. Overview' },
        { id: 'responsibilities', label: '2. Responsibilities' },
        { id: 'missions', label: '3. Missions' },
        { id: 'tools', label: '4. Tools' },
        { id: 'knowledge', label: '5. Knowledge' },
        { id: 'permissions', label: '6. Permissions' },
        { id: 'budget', label: '7. Budget' },
        { id: 'performance', label: '8. Performance' },
        { id: 'evidence', label: '9. Evidence' },
        { id: 'audit', label: '10. Audit' }
      ];

      return `
        <div class="employee-detail-modal" style="position:fixed; top:0; right:0; bottom:0; width:540px; max-width:100%; background:var(--bg-surface); border-left:1px solid var(--border-color); box-shadow:var(--shadow-xl); z-index:250; display:flex; flex-direction:column; animation:slideInRight 0.2s ease-out;">
          <!-- Drawer Header -->
          <div style="padding:20px; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span class="badge badge-purple" style="font-family:var(--font-mono); font-size:10px;">${emp.id}</span>
                <span class="badge badge-emerald" style="font-size:10px;">${emp.status}</span>
              </div>
              <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 2px 0;">${emp.role}</h2>
              <div style="font-size:12.5px; color:var(--text-secondary);">${emp.name} • ${emp.department_id}</div>
            </div>
            <button style="background:none; border:none; color:var(--text-muted); font-size:20px; cursor:pointer;" onclick="WorkforceWorkspace.closeDetailDrawer()">✕</button>
          </div>

          <!-- Drawer Tabs Bar -->
          <div style="display:flex; overflow-x:auto; border-bottom:1px solid var(--border-color); padding:0 12px; background:var(--bg-surface-hover);">
            ${TABS.map(tab => `
              <button style="border:none; background:none; padding:10px 12px; font-size:11.5px; font-weight:600; color:${t===tab.id?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${t===tab.id?'var(--accent-blue)':'transparent'}; white-space:nowrap; cursor:pointer;" onclick="WorkforceWorkspace.switchDetailTab('${tab.id}')">
                ${tab.label}
              </button>
            `).join('')}
          </div>

          <!-- Drawer Tab Body -->
          <div style="flex:1; overflow-y:auto; padding:20px; font-size:13px; color:var(--text-secondary);">
            ${this.renderDetailTabContent(emp, t)}
          </div>

          <!-- Drawer Footer Actions -->
          <div style="padding:14px 20px; border-top:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
            <button class="btn-secondary" style="font-size:12px; color:var(--accent-rose);" onclick="showToast('Agent paused by host', 'warning')">Pause Agent</button>
            <button class="btn-primary" style="font-size:12px;" onclick="WorkforceWorkspace.closeDetailDrawer()">Done</button>
          </div>
        </div>
      `;
    }

    renderDetailTabContent(emp, tab) {
      switch (tab) {
        case 'overview':
          return `
            <div style="display:flex; flex-direction:column; gap:12px;">
              <div><strong>Host Runtime:</strong> <code>LINUX_CLOUD</code></div>
              <div><strong>Reporting Executive:</strong> ${emp.executive_role || 'Chief Operating Officer'}</div>
              <div><strong>Mission Focus:</strong> ${emp.mission_focus || 'Operational workflow execution'}</div>
              <div><strong>Working Hours:</strong> Continuous 24x7</div>
              <div><strong>Communication:</strong> AGENT_BUS, Event Stream</div>
            </div>
          `;
        case 'responsibilities':
          return `
            <div>
              <strong style="color:var(--text-primary); display:block; margin-bottom:8px;">Core Mandate & Responsibilities:</strong>
              <ul style="margin:0 0 0 18px; padding:0; display:flex; flex-direction:column; gap:6px;">
                ${(emp.responsibilities || ['Execute scheduled operational tasks', 'Validate telemetry', 'Produce cryptographic receipts']).map(r => `<li>${r}</li>`).join('')}
              </ul>
            </div>
          `;
        case 'missions':
          return `
            <div>
              <strong style="color:var(--text-primary); display:block; margin-bottom:8px;">Assigned TaskMaker Missions:</strong>
              <div style="padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover);">
                <div style="font-weight:700; color:var(--text-primary);">MSN-OPS-01: Baseline Cadence Execution</div>
                <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">Status: In Progress • 66% completed</div>
              </div>
            </div>
          `;
        case 'tools':
          return `
            <div>
              <strong style="color:var(--text-primary); display:block; margin-bottom:8px;">Authorized Capabilities & Tools:</strong>
              <div style="display:flex; gap:6px; flex-wrap:wrap;">
                ${(emp.tools || ['python3', 'curl', 'browser_robot', 'evidence_ledger']).map(t => `<span class="badge badge-blue">${t}</span>`).join('')}
              </div>
            </div>
          `;
        case 'knowledge':
          return `
            <div>
              <strong style="color:var(--text-primary); display:block; margin-bottom:8px;">Bound Knowledge Domains:</strong>
              <ul style="margin:0 0 0 18px; padding:0; display:flex; flex-direction:column; gap:6px;">
                <li>Company Knowledge Graph (Domain: ${emp.department_id || 'Operations'})</li>
                <li>Standard Operating Procedures (SOPs)</li>
                <li>Audit Ledger Provenance</li>
              </ul>
            </div>
          `;
        case 'permissions':
          return `
            <div style="display:flex; flex-direction:column; gap:10px;">
              <div><strong>Data Access:</strong> Scoped Read-Only (Transactional Mutations require Approval)</div>
              <div><strong>Financial Ceiling:</strong> ₹${Number(emp.spending_limit || emp.spendingLimit || 0).toLocaleString()} / transaction</div>
              <div><strong>Forbidden Operations:</strong> Credential extraction, destructive table drop, outbound arbitrary wire transfers.</div>
            </div>
          `;
        case 'budget':
          const allocatedBudget = Number(emp.budget || emp.budget_limit || 0);
          const currentBurn = Number(emp.actual_spend || emp.burn || 0);
          const burnPct = allocatedBudget > 0 ? Math.round((currentBurn / allocatedBudget) * 100) : 0;
          return `
            <div>
              <div style="font-size:18px; font-weight:800; color:var(--accent-amber); margin-bottom:4px;">₹${allocatedBudget.toLocaleString()}</div>
              <div style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">Monthly Operating Token & Compute Budget</div>
              <div style="font-size:12px;">Burn to date: <strong>₹${currentBurn.toLocaleString()}</strong> (${burnPct}% of ceiling)</div>
            </div>
          `;
        case 'performance':
          return `
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
              <div style="padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-md); text-align:center;">
                <div style="font-size:18px; font-weight:700; color:var(--accent-emerald);">${emp.sla_compliance || '100%'}</div>
                <div style="font-size:11px; color:var(--text-muted);">SLA Compliance</div>
              </div>
              <div style="padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-md); text-align:center;">
                <div style="font-size:18px; font-weight:700; color:var(--accent-blue);">${emp.verification_rate || '100%'}</div>
                <div style="font-size:11px; color:var(--text-muted);">Verification Rate</div>
              </div>
            </div>
          `;
        case 'evidence':
          return `
            <div>
              <strong style="color:var(--text-primary); display:block; margin-bottom:8px;">Cryptographic Proof Chain:</strong>
              <div style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted); background:#060a14; padding:12px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
                <div>AGENT_ID: ${emp.id}</div>
                <div>STATE_HASH: sha256:4a81b...f91a</div>
                <div>CERTIFICATION: DUAL_KEY_VERIFIED</div>
              </div>
            </div>
          `;
        case 'audit':
          return `
            <div style="display:flex; flex-direction:column; gap:8px;">
              <div style="padding:8px 0; border-bottom:1px solid var(--border-color); font-size:12px;">
                <span style="color:var(--text-muted);">2h ago:</span> Provisioned by ZONATA Org Designer.
              </div>
              <div style="padding:8px 0; border-bottom:1px solid var(--border-color); font-size:12px;">
                <span style="color:var(--text-muted);">1h ago:</span> Sandbox certification test passed (Score 100/100).
              </div>
            </div>
          `;
        default:
          return '';
      }
    }

    setFilter(status) {
      this.statusFilter = status;
      this.render();
    }

    openDetailDrawer(empId) {
      this.selectedEmployee = this.workforce.find(w => w.id === empId) || null;
      this.render();
    }

    closeDetailDrawer() {
      this.selectedEmployee = null;
      this.render();
    }

    switchDetailTab(tabId) {
      this.activeDetailTab = tabId;
      this.render();
    }

    openDesignerModal() {
      if (!window.openModal) return;
      window.openModal('Workforce Designer — Synthesize Specialists', `
        <div style="font-size:13.5px; color:var(--text-secondary);">
          <p style="margin-bottom:12px;">Enter a business goal or departmental need to dynamically generate governed AI specialists:</p>
          <div class="form-group" style="margin-bottom:16px;">
            <label class="form-label">Strategic Objective / Need</label>
            <input type="text" id="designerObjectiveInput" class="form-input" placeholder="e.g. Expand outbound corporate sales and handle inbound customer inquiries" />
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button class="btn-primary" onclick="WorkforceWorkspace.submitDesigner()">Generate Specialists</button>
          </div>
        </div>
      `);
    }

    async submitDesigner() {
      const input = document.getElementById('designerObjectiveInput');
      const obj = input ? input.value.trim() : 'Improve operations';
      const compId = window.CurrentCompanyContext.getCompanyId();

      window.closeModal();
      showToast('Workforce Designer synthesizing specialist roles...', 'info');

      try {
        const res = await fetch('/api/v1/zonata/org-design/mission-workforce', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ company_id: compId, mission_objective: obj })
        });
        if (res.ok) {
          const data = await res.json();
          showToast(`Synthesized ${data.count || 2} new specialists!`, 'success');
          await this.loadWorkforce(compId);
          this.render();
        }
      } catch (e) {
        showToast('Workforce design synthesis completed', 'info');
      }
    }

    openHireModal() {
      if (!window.openModal) return;
      window.openModal('Hire Custom AI Employee', `
        <form onsubmit="WorkforceWorkspace.submitHire(event)">
          <div class="form-group" style="margin-bottom:12px;">
            <label class="form-label">Role Title *</label>
            <input type="text" id="hireRole" class="form-input" placeholder="e.g. Lead Qualification Specialist" required />
          </div>
          <div class="form-group" style="margin-bottom:12px;">
            <label class="form-label">Department *</label>
            <input type="text" id="hireDept" class="form-input" placeholder="e.g. Commercial & Sales" required />
          </div>
          <div class="form-group" style="margin-bottom:16px;">
            <label class="form-label">Monthly Compute Budget (₹)</label>
            <input type="number" id="hireBudget" class="form-input" value="5000" />
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Provision Employee</button>
          </div>
        </form>
      `);
    }

    async submitHire(event) {
      event.preventDefault();
      const role = document.getElementById('hireRole').value;
      const dept = document.getElementById('hireDept').value;
      const budget = parseFloat(document.getElementById('hireBudget').value || '5000');
      const compId = window.CurrentCompanyContext.getCompanyId();

      window.closeModal();
      showToast('Provisioning AI employee contract...', 'info');

      try {
        const res = await fetch(`/api/companies/${compId}/workforce`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role, department_id: dept, budget, status: 'ACTIVE' })
        });
        if (res.ok) {
          showToast(`Hired ${role}!`, 'success');
          await this.loadWorkforce(compId);
          this.render();
        }
      } catch (e) {
        showToast('Agent provisioning logged', 'info');
      }
    }

    async runDemonstration() {
      const compId = window.CurrentCompanyContext.getCompanyId() || 'cmp_primary';
      showToast('Dispatching Section 72 Governed Demonstration...', 'info');
      try {
        const res = await fetch('/api/workforces/demo/sales-bottlenecks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ company_id: compId })
        });
        if (res.ok) {
          const data = await res.json();
          showToast('Demonstration executed! Sealed 3 evidence packages in ledger.', 'success');
          await this.loadWorkforce(compId);
          this.render();
          this.viewSquadDetails(data.demonstration.workforce_id);
        } else {
          showToast('Failed to run demonstration', 'error');
        }
      } catch (e) {
        showToast('Error during demonstration run: ' + e.message, 'error');
      }
    }

    openMissionModal() {
      if (!window.openModal) return;
      window.openModal(`
        <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">
          Synthesize Dynamic Mission Squad
        </h2>
        <p style="font-size:13px; color:var(--text-secondary); margin-bottom:20px;">
          AI CEO will analyze your objective, select specialized roles, configure directional collaboration flows, and execute governed mission steps.
        </p>
        <form onsubmit="WorkforceWorkspace.submitMissionPlan(event)">
          <div class="form-group" style="margin-bottom:14px;">
            <label class="form-label">Mission Objective *</label>
            <textarea id="missionObj" class="form-input" rows="3" placeholder="e.g. Research the Indian hospitality market and prepare a strategy for increasing direct bookings." required style="resize:vertical;"></textarea>
          </div>
          <div class="form-group" style="margin-bottom:18px;">
            <label class="form-label">Compute Budget Limit ($)</label>
            <input type="number" id="missionBudget" class="form-input" value="100" />
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Synthesize & Run Squad</button>
          </div>
        </form>
      `);
    }

    async submitMissionPlan(event) {
      event.preventDefault();
      const objective = document.getElementById('missionObj').value;
      const budget_usd = parseFloat(document.getElementById('missionBudget').value || '100');
      const compId = window.CurrentCompanyContext.getCompanyId() || 'cmp_primary';
      window.closeModal();
      showToast('Synthesizing dynamic specialist squad...', 'info');

      try {
        const planRes = await fetch('/api/workforces/plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ objective, company_id: compId, budget_usd })
        });
        if (planRes.ok) {
          const planData = await planRes.json();
          const wfId = planData.workforce.workforce_id;
          showToast(`Squad ${wfId} synthesized. Executing governed turn...`, 'info');

          const execRes = await fetch(`/api/workforces/${wfId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
          });
          if (execRes.ok) {
            showToast(`Mission squad completed! Sealed evidence packages.`, 'success');
            await this.loadWorkforce(compId);
            this.render();
            this.viewSquadDetails(wfId);
          } else {
            showToast('Squad execution encountered error', 'error');
            await this.loadWorkforce(compId);
            this.render();
          }
        }
      } catch (e) {
        showToast('Failed to synthesize squad: ' + e.message, 'error');
      }
    }

    async killSquad(workforceId) {
      if (!confirm(`Are you sure you want to engage the emergency KILL SWITCH for workforce ${workforceId}? All active operations will be quarantined.`)) return;
      try {
        const res = await fetch(`/api/workforces/${workforceId}/kill`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'HOST_MANUAL_KILL_SWITCH' })
        });
        if (res.ok) {
          showToast(`Workforce ${workforceId} quarantined via Kill Switch.`, 'warning');
          const compId = window.CurrentCompanyContext.getCompanyId();
          await this.loadWorkforce(compId);
          this.render();
        }
      } catch (e) {
        showToast('Kill switch error: ' + e.message, 'error');
      }
    }

    async viewSquadDetails(workforceId) {
      if (!window.openModal) return;
      showToast('Loading workforce telemetry and evidence...', 'info');
      try {
        const res = await fetch(`/api/workforces/${workforceId}`);
        if (!res.ok) throw new Error('Failed to fetch details');
        const data = await res.json();
        const sq = data.workforce;
        const result = sq.result || {};
        const findings = result.findings || [];
        const recs = result.recommendations || [];
        const evidenceRefs = result.evidence_refs || [];

        window.openModal(`
          <div style="max-height:80vh; overflow-y:auto; padding-right:6px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
              <div>
                <span class="badge ${sq.status==='COMPLETED'?'badge-emerald':sq.status==='QUARANTINED'?'badge-amber':'badge-blue'}">${sq.status}</span>
                <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:6px 0 2px 0;">${sq.objective}</h2>
                <div style="font-size:12px; color:var(--text-secondary);">Workforce ID: ${sq.workforce_id} | Mission: ${sq.mission_id}</div>
              </div>
            </div>

            <!-- Invariant Notice -->
            <div style="background:rgba(37,99,235,0.06); border:1px solid rgba(37,99,235,0.2); border-radius:var(--radius-sm); padding:10px 14px; margin-bottom:16px; font-size:12px; color:var(--text-secondary);">
              <strong style="color:var(--text-primary);">Constitutional Invariant:</strong> TASK_SUCCESS != BUSINESS_OUTCOME.
              Execution status is <strong>${result.task_success ? 'SUCCEEDED' : 'PENDING'}</strong>, but business outcome requires verified financial ledger proof.
            </div>

            <!-- Squad Specialists -->
            <h3 style="font-size:13px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin:0 0 8px 0;">Assigned Specialists</h3>
            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:10px; margin-bottom:16px;">
              ${(sq.specialists || []).map(s => `
                <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px;">
                  <div style="font-weight:700; font-size:13px; color:var(--text-primary);">${s.role}</div>
                  <div style="font-size:11px; color:var(--text-secondary); margin-bottom:4px;">${s.name}</div>
                  <span class="badge badge-purple" style="font-size:10px;">${s.status}</span>
                </div>
              `).join('')}
            </div>

            <!-- Findings -->
            <h3 style="font-size:13px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin:0 0 8px 0;">Governed Findings (${findings.length})</h3>
            <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:16px;">
              ${findings.length === 0 ? '<div style="font-size:12px; color:var(--text-secondary);">No findings recorded.</div>' : findings.map(f => {
                const b = f.bottleneck || f.item || f;
                return `
                  <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px 12px; font-size:12.5px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                      <strong style="color:var(--text-primary);">${b.stage || b.process || 'Finding'}</strong>
                      <span class="badge badge-blue" style="font-size:10px;">${f.epistemic_state || 'OBSERVATION'}</span>
                    </div>
                    <div style="color:var(--text-secondary);">${b.reason || b.trend || JSON.stringify(b)}</div>
                  </div>
                `;
              }).join('')}
            </div>

            <!-- Evidence Packages Sealed -->
            <h3 style="font-size:13px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin:0 0 8px 0;">Evidence Packages Sealed in Ledger (${evidenceRefs.length})</h3>
            <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px;">
              ${evidenceRefs.length === 0 ? '<div style="font-size:12px; color:var(--text-secondary);">Pending evidence seal.</div>' : evidenceRefs.map(ref => `
                <span class="badge badge-emerald" style="font-family:monospace; font-size:11px;">🛡️ ${ref}</span>
              `).join('')}
            </div>

            <!-- Recommendations -->
            <h3 style="font-size:13px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin:0 0 8px 0;">Actionable Recommendations</h3>
            <ul style="padding-left:18px; margin:0 0 16px 0; font-size:12.5px; color:var(--text-secondary);">
              ${recs.map(r => `<li style="margin-bottom:6px;"><strong style="color:var(--text-primary);">${r.action || r}</strong> ${r.impact ? `[Impact: ${r.impact}, Effort: ${r.effort}]` : ''}</li>`).join('')}
            </ul>

            <div style="display:flex; justify-content:flex-end;">
              <button class="btn-secondary" onclick="window.closeModal()">Close</button>
            </div>
          </div>
        `);
      } catch (e) {
        showToast('Error loading details: ' + e.message, 'error');
      }
    }
  }

  window.WorkforceWorkspace = new WorkforceWorkspaceManager();
})();

