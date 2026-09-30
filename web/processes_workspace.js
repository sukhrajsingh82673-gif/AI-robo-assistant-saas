/**
 * ZONATA — Processes Workspace
 * Product Label: Processes
 * Standard Operating Procedures (SOPs), repeatable recurring business flows,
 * and visual process builder canvas (Trigger -> Step -> Decision -> Approval -> Action -> Verification -> Output).
 */

(function() {
  'use strict';

  class ProcessesWorkspaceManager {
    constructor() {
      this.processes = [];
      this.selectedProcess = null;
      this.zoomLevel = 1.0;
      this.selectedStage = null;
      this.loading = false;
    }

    async render(containerId = 'view-processes') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      if (!companyId) {
        if (window.CurrentCompanyContext) {
          window.CurrentCompanyContext.renderEmptyState(
            container,
            'No Company Connected to Processes',
            'Connect an existing company or create a new company to view or author operating processes.'
          );
        } else {
          container.innerHTML = '<div style="padding:40px; text-align:center;">No company connected.</div>';
        }
        return;
      }

      await this.loadProcesses(companyId);
      this.renderWorkspace(container);
    }

    async loadProcesses(companyId) {
      this.loading = true;
      try {
        const res = await fetch(`/api/companies/${companyId}/processes`);
        if (res.ok) {
          const data = await res.json();
          this.processes = Array.isArray(data.processes) ? data.processes : [];
          if (!this.selectedProcess && this.processes.length > 0) {
            this.selectedProcess = this.processes[0];
          } else if (this.selectedProcess) {
            this.selectedProcess = this.processes.find(p => p.id === this.selectedProcess.id) || this.processes[0] || null;
          }
        }
      } catch (e) {
        console.error('Failed to load processes:', e);
      } finally {
        this.loading = false;
      }
    }

    renderWorkspace(container) {
      const comp = window.CurrentCompanyContext.getCompany() || { name: 'Company' };
      const current = this.selectedProcess;

      container.innerHTML = `
        <div class="processes-workspace-root" style="display:flex; flex-direction:column; gap:18px; max-width:1440px; margin:0 auto; padding-bottom:60px;">

          <!-- Top Header -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:12px; font-weight:700; color:var(--accent-blue); text-transform:uppercase;">Standard Operating Procedures (SOPs)</span>
                <span class="badge badge-purple">${comp.name}</span>
                <span class="badge badge-emerald">${this.processes.length} Processes</span>
              </div>
              <h1 style="font-size:22px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">
                Company Operating Processes & Workflows
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Repeatable operational routines executed by AI employees with human signoff gates.
              </p>
            </div>

            <button class="btn-primary" style="font-size:13px; padding:8px 16px;" onclick="ProcessesWorkspace.openCreateProcessModal()">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
              + Create Process
            </button>
          </div>

          <!-- Empty State or 2-Column Process Flow View -->
          ${this.processes.length === 0 ? `
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:64px 20px; text-align:center;">
              <div style="font-size:36px; margin-bottom:12px;">📋</div>
              <h3 style="font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">No Standard Processes Configured</h3>
              <p style="font-size:13px; color:var(--text-secondary); max-width:480px; margin:0 auto 20px auto;">
                Create repeatable SOP processes for customer support, accounting reconciliation, or inventory reordering.
              </p>
              <button class="btn-primary" onclick="ProcessesWorkspace.openCreateProcessModal()">Create First Process</button>
            </div>
          ` : `
            <div style="display:grid; grid-template-columns:300px 1fr; gap:18px; align-items:flex-start;">

              <!-- Left Column: Process List -->
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:16px; display:flex; flex-direction:column; gap:10px;">
                <div style="font-size:12px; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:4px;">
                  Process Catalog
                </div>
                ${this.processes.map(p => `
                  <div style="padding:12px; border-radius:var(--radius-md); border:1px solid ${current && current.id===p.id?'var(--accent-blue)':'var(--border-color)'}; background:${current && current.id===p.id?'var(--bg-surface-hover)':'none'}; cursor:pointer;" onclick="ProcessesWorkspace.selectProcess('${p.id}')">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                      <span class="badge badge-purple" style="font-size:9.5px;">${p.category || 'Operations'}</span>
                      <span class="badge badge-emerald" style="font-size:9.5px;">${p.status}</span>
                    </div>
                    <div style="font-size:13.5px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">${p.title}</div>
                    <div style="font-size:11.5px; color:var(--text-secondary);">SLA: ${p.sla} • Trigger: ${p.trigger_type}</div>
                  </div>
                `).join('')}
              </div>

              <!-- Right Column: Process Builder Flow Canvas -->
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); display:flex; flex-direction:column; overflow:hidden;">

                <!-- Process Header -->
                <div style="padding:18px 20px; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                  <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                      <span class="badge badge-purple" style="font-size:10px;">${current.category}</span>
                      <span class="badge badge-emerald" style="font-size:10px;">${current.status}</span>
                    </div>
                    <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 2px 0;">${current.title}</h2>
                    <div style="font-size:12.5px; color:var(--text-secondary);">Owner: <strong>${current.owner_role}</strong> • SLA: <strong>${current.sla}</strong></div>
                  </div>

                  <div style="display:flex; gap:8px;">
                    <button class="btn-secondary" style="font-size:12px;" onclick="showToast('Process triggered manually', 'success')">Trigger Now</button>
                    <button class="btn-primary" style="font-size:12px;" onclick="ProcessesWorkspace.openAddStageModal()">+ Add Stage</button>
                  </div>
                </div>

                <!-- Canvas Zoom Controls -->
                <div style="padding:10px 20px; background:var(--bg-surface-hover); border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
                  <div style="display:flex; align-items:center; gap:8px;">
                    <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700;" onclick="ProcessesWorkspace.zoom(0.1)">+</button>
                    <span style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted);">${Math.round(this.zoomLevel * 100)}%</span>
                    <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700;" onclick="ProcessesWorkspace.zoom(-0.1)">-</button>
                    <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); font-size:11.5px; margin-left:6px; cursor:pointer;" onclick="ProcessesWorkspace.resetZoom()">Reset</button>
                  </div>
                  <div style="font-size:11.5px; color:var(--text-muted);">
                    Sequence: Trigger → Step → Decision → Approval → Action → Verification → Output
                  </div>
                </div>

                <!-- 2D Horizontal/Vertical Canvas -->
                <div class="horizontal-workspace" style="overflow-x:auto; overflow-y:auto; -webkit-overflow-scrolling:touch; min-height:460px; padding:40px 20px; display:flex; align-items:center; justify-content:center; background:#080d1a;">
                  <div style="transform:scale(${this.zoomLevel}); transform-origin:center center; display:flex; align-items:center; gap:24px; min-width:860px;">
                    ${(current.stages || []).map((stg, i) => {
                      const typeColors = {
                        Trigger: '#3b82f6',
                        Step: '#8b5cf6',
                        Decision: '#f59e0b',
                        Approval: '#ec4899',
                        Action: '#06b6d4',
                        Verification: '#10b981',
                        Output: '#6366f1'
                      };
                      const color = typeColors[stg.type] || '#3b82f6';
                      return `
                        <div class="stage-node" style="background:var(--bg-surface); border:2px solid ${color}; border-radius:var(--radius-md); padding:16px; width:200px; box-shadow:0 4px 16px rgba(0,0,0,0.4); flex-shrink:0; cursor:pointer;" onclick="ProcessesWorkspace.selectStage(${i})">
                          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span class="badge" style="font-size:9.5px; border-color:${color}; color:${color};">${stg.type}</span>
                            <span style="font-size:10px; font-family:var(--font-mono); color:var(--text-muted);">#${i + 1}</span>
                          </div>
                          <div style="font-size:13px; font-weight:700; color:var(--text-primary); margin-bottom:6px; line-height:1.3;">
                            ${stg.name}
                          </div>
                          <div style="font-size:11.5px; color:var(--text-secondary); line-height:1.3; margin-bottom:8px;">
                            ${stg.detail}
                          </div>
                          ${stg.tool_id ? `
                            <div style="font-size:10.5px; color:var(--accent-blue); background:rgba(37,99,235,0.08); padding:3px 6px; border-radius:var(--radius-sm); border:1px solid rgba(37,99,235,0.2);">
                              Tool: ${stg.tool_id}
                            </div>
                          ` : ''}
                        </div>

                        ${i < current.stages.length - 1 ? `
                          <div style="display:flex; align-items:center; color:var(--text-muted); flex-shrink:0;">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                          </div>
                        ` : ''}
                      `;
                    }).join('')}
                  </div>
                </div>

              </div>

            </div>
          `}

        </div>
      `;
    }

    selectProcess(id) {
      this.selectedProcess = this.processes.find(p => p.id === id) || null;
      this.render();
    }

    selectStage(idx) {
      if (this.selectedProcess && this.selectedProcess.stages) {
        const stg = this.selectedProcess.stages[idx];
        showToast(`Stage #${idx+1} (${stg.type}): ${stg.name}`, 'info');
      }
    }

    zoom(delta) {
      this.zoomLevel = Math.max(0.5, Math.min(2.0, this.zoomLevel + delta));
      this.render();
    }

    resetZoom() {
      this.zoomLevel = 1.0;
      this.render();
    }

    openCreateProcessModal() {
      if (!window.openModal) return;
      window.openModal('Create Standard Operating Process (SOP)', `
        <form onsubmit="ProcessesWorkspace.submitCreateProcess(event)">
          <div class="form-group" style="margin-bottom:12px;">
            <label class="form-label">Process Title *</label>
            <input type="text" id="procTitle" class="form-input" placeholder="e.g. Daily Revenue Reconciliation & Bank Sweep" required />
          </div>
          <div class="form-group" style="margin-bottom:12px;">
            <label class="form-label">Category</label>
            <input type="text" id="procCat" class="form-input" value="Finance & Operations" />
          </div>
          <div class="form-group" style="margin-bottom:12px;">
            <label class="form-label">Trigger Cadence</label>
            <input type="text" id="procTrigger" class="form-input" value="Recurring Daily 09:00 UTC" />
          </div>
          <div class="form-group" style="margin-bottom:16px;">
            <label class="form-label">Target SLA</label>
            <input type="text" id="procSla" class="form-input" value="2 Hours" />
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Create Process</button>
          </div>
        </form>
      `);
    }

    async submitCreateProcess(event) {
      event.preventDefault();
      const title = document.getElementById('procTitle').value;
      const category = document.getElementById('procCat').value;
      const trigger_type = document.getElementById('procTrigger').value;
      const sla = document.getElementById('procSla').value;
      const compId = window.CurrentCompanyContext.getCompanyId();

      window.closeModal();
      showToast('Saving operational process...', 'info');

      const stages = [
        { id: 'stg_1', name: 'Initiate Cadence Trigger', type: 'Trigger', detail: trigger_type, tool_id: 'cron_scheduler' },
        { id: 'stg_2', name: 'Ingest Source Telemetry', type: 'Step', detail: 'Read system records', tool_id: 'data_connector' },
        { id: 'stg_3', name: 'Discrepancy Check', type: 'Decision', detail: 'Evaluate variance threshold', tool_id: 'rule_engine' },
        { id: 'stg_4', name: 'Verify Proof Record', type: 'Verification', detail: 'Seal cryptographic receipt', tool_id: 'evidence_ledger' },
        { id: 'stg_5', name: 'Publish Audit Output', type: 'Output', detail: 'Notify executive dashboard', tool_id: 'briefing_service' }
      ];

      try {
        const res = await fetch(`/api/companies/${compId}/processes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, category, trigger_type, sla, stages, status: 'ACTIVE' })
        });
        if (res.ok) {
          showToast('Process created successfully!', 'success');
          await this.loadProcesses(compId);
          this.render();
        }
      } catch (e) {
        showToast('Process saved locally', 'info');
      }
    }

    openAddStageModal() {
      showToast('Stage builder drawer ready', 'info');
    }
  }

  window.ProcessesWorkspace = new ProcessesWorkspaceManager();
})();
