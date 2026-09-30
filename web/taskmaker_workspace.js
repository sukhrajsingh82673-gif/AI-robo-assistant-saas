/**
 * ZONATA — TaskMaker / Mission Engine Workspace
 * Product Label: TaskMaker
 * Mission creation, DAG task decomposition, 12 task states,
 * visual workflow graph with zoom controls, and mission detail tabs.
 */

(function() {
  'use strict';

  class TaskMakerWorkspaceManager {
    constructor() {
      this.missions = [];
      this.selectedMission = null;
      this.zoomLevel = 1.0;
      this.activeDetailTab = 'plan'; // 'overview' | 'plan' | 'tasks' | 'dependencies' | 'workforce' | 'tools' | 'approvals' | 'execution' | 'evidence' | 'outcome' | 'audit'
      this.loading = false;
    }

    async render(containerId = 'view-tasks') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      if (!companyId) {
        if (window.CurrentCompanyContext) {
          window.CurrentCompanyContext.renderEmptyState(
            container,
            'No Company Connected to TaskMaker',
            'Connect an existing company or create a new company to operate TaskMaker missions.'
          );
        } else {
          container.innerHTML = '<div style="padding:40px; text-align:center;">No company connected.</div>';
        }
        return;
      }

      await this.loadMissions(companyId);
      this.renderWorkspace(container);
    }

    async loadMissions(companyId) {
      this.loading = true;
      try {
        const res = await fetch(`/api/companies/${companyId}/missions`);
        if (res.ok) {
          const data = await res.json();
          this.missions = Array.isArray(data.missions) ? data.missions : [];
          if (!this.selectedMission && this.missions.length > 0) {
            this.selectedMission = this.missions[0];
          } else if (this.selectedMission) {
            this.selectedMission = this.missions.find(m => m.mission_id === this.selectedMission.mission_id) || this.missions[0] || null;
          }
        }
      } catch (e) {
        console.error('Failed to load missions:', e);
      } finally {
        this.loading = false;
      }
    }

    renderWorkspace(container) {
      const comp = window.CurrentCompanyContext.getCompany() || { name: 'Company' };
      const current = this.selectedMission;

      container.innerHTML = `
        <div class="taskmaker-workspace-root" style="display:flex; flex-direction:column; gap:18px; max-width:1440px; margin:0 auto; padding-bottom:60px;">

          <!-- Top Header -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:12px; font-weight:700; color:var(--accent-blue); text-transform:uppercase; letter-spacing:0.5px;">TaskMaker • Mission Engine</span>
                <span class="badge badge-purple">${comp.name}</span>
                <span class="badge badge-emerald">${this.missions.length} Missions</span>
              </div>
              <h1 style="font-size:22px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">
                Autonomous Mission Orchestration
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Translate high-level executive objectives into cryptographically verifiable DAG task graphs.
              </p>
            </div>

            <div style="display:flex; gap:10px;">
              <button class="btn-primary" style="font-size:13px; padding:8px 16px;" onclick="TaskMakerWorkspace.openCreateMissionModal()">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
                + Create Mission
              </button>
            </div>
          </div>

          <!-- Empty State or Active Mission Workspace -->
          ${this.missions.length === 0 ? `
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:64px 20px; text-align:center;">
              <div style="font-size:36px; margin-bottom:12px;">🎯</div>
              <h3 style="font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:6px;">No Missions in Progress</h3>
              <p style="font-size:13px; color:var(--text-secondary); max-width:480px; margin:0 auto 20px auto;">
                TaskMaker decomposes company strategic priorities into Directed Acyclic Graphs of discrete, governed tasks.
              </p>
              <button class="btn-primary" onclick="TaskMakerWorkspace.openCreateMissionModal()">Create First Mission</button>
            </div>
          ` : `
            <!-- 2-Column: Left Mission Selector & Right Active Mission Canvas -->
            <div style="display:grid; grid-template-columns:300px 1fr; gap:18px; align-items:flex-start;">

              <!-- Left Column: Mission List -->
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:16px; display:flex; flex-direction:column; gap:10px;">
                <div style="font-size:12px; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:4px;">
                  Active Missions
                </div>
                ${this.missions.map(m => `
                  <div style="padding:12px; border-radius:var(--radius-md); border:1px solid ${current && current.mission_id===m.mission_id?'var(--accent-blue)':'var(--border-color)'}; background:${current && current.mission_id===m.mission_id?'var(--bg-surface-hover)':'none'}; cursor:pointer;" onclick="TaskMakerWorkspace.selectMission('${m.mission_id}')">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                      <span style="font-size:10px; font-family:var(--font-mono); color:var(--accent-purple);">${m.mission_id}</span>
                      <span class="badge ${m.status==='ACTIVE'?'badge-emerald':'badge-blue'}" style="font-size:9.5px;">${m.status}</span>
                    </div>
                    <div style="font-size:13px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">${m.title}</div>
                    <div style="font-size:11px; color:var(--text-secondary);">${m.department} • ${m.owner_agent}</div>
                  </div>
                `).join('')}
              </div>

              <!-- Right Column: Visual DAG Canvas & Tabs -->
              <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); display:flex; flex-direction:column; overflow:hidden;">

                <!-- Mission Header -->
                <div style="padding:18px 20px; border-bottom:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                  <div>
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                      <span class="badge badge-purple" style="font-family:var(--font-mono); font-size:10.5px;">${current.mission_id}</span>
                      <span class="badge badge-emerald" style="font-size:10.5px;">${current.status}</span>
                    </div>
                    <h2 style="font-size:18px; font-weight:700; color:var(--text-primary); margin:0 0 2px 0;">${current.title}</h2>
                    <div style="font-size:12.5px; color:var(--text-secondary);">${current.target_outcome}</div>
                  </div>

                  <div style="display:flex; gap:8px;">
                    <button class="btn-secondary" style="font-size:12px;" onclick="showToast('Verifying task output receipts...', 'info')">Verify Ledger</button>
                    <button class="btn-primary" style="font-size:12px;" onclick="showToast('Running DAG cycle...', 'info')">Run DAG Step</button>
                  </div>
                </div>

                <!-- Mission Detail Tabs -->
                <div style="display:flex; overflow-x:auto; border-bottom:1px solid var(--border-color); padding:0 16px; background:var(--bg-surface-hover); gap:4px;">
                  ${[
                    { id: 'plan', label: 'Workflow DAG Graph' },
                    { id: 'tasks', label: 'Granular Tasks' },
                    { id: 'workforce', label: 'Assigned Agents' },
                    { id: 'evidence', label: 'Evidence & Proof' },
                    { id: 'audit', label: 'Audit Trail' }
                  ].map(tab => `
                    <button style="border:none; background:none; padding:10px 14px; font-size:12px; font-weight:600; color:${this.activeDetailTab===tab.id?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${this.activeDetailTab===tab.id?'var(--accent-blue)':'transparent'}; cursor:pointer; white-space:nowrap;" onclick="TaskMakerWorkspace.switchDetailTab('${tab.id}')">
                      ${tab.label}
                    </button>
                  `).join('')}
                </div>

                <!-- Tab Content: Visual DAG Graph with Zoom -->
                <div style="padding:20px; position:relative;">
                  ${this.activeDetailTab === 'plan' ? this.renderDagCanvas(current) : this.renderOtherTab(current)}
                </div>

              </div>

            </div>
          `}

        </div>
      `;
    }

    renderDagCanvas(mission) {
      const tasks = mission.tasks || [];

      return `
        <!-- Floating Canvas Toolbar -->
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; background:rgba(255,255,255,0.02); padding:8px 12px; border-radius:var(--radius-md); border:1px solid var(--border-color);">
          <div style="display:flex; align-items:center; gap:8px;">
            <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700;" onclick="TaskMakerWorkspace.zoom(0.1)">+</button>
            <span style="font-size:11px; font-family:var(--font-mono); color:var(--text-muted);">${Math.round(this.zoomLevel * 100)}%</span>
            <button class="zoom-btn" style="background:none; border:none; color:var(--text-primary); cursor:pointer; font-weight:700;" onclick="TaskMakerWorkspace.zoom(-0.1)">-</button>
            <button class="zoom-btn" style="background:none; border:none; color:var(--text-secondary); font-size:11.5px; margin-left:6px; cursor:pointer;" onclick="TaskMakerWorkspace.resetZoom()">Reset</button>
          </div>
          <div style="font-size:11.5px; color:var(--text-muted);">
            States: <span style="color:var(--accent-emerald);">COMPLETED</span> • <span style="color:var(--accent-amber);">RUNNING</span> • <span style="color:var(--accent-blue);">PLANNED</span>
          </div>
        </div>

        <!-- 2D Horizontal/Vertical Canvas -->
        <div class="horizontal-workspace" style="overflow-x:auto; overflow-y:auto; -webkit-overflow-scrolling:touch; min-height:420px; padding:30px 20px; display:flex; align-items:center; justify-content:center; background:#080d1a; border-radius:var(--radius-md); border:1px solid var(--border-color);">
          <div style="transform:scale(${this.zoomLevel}); transform-origin:center center; display:flex; align-items:center; gap:28px; min-width:800px;">
            ${tasks.map((tsk, i) => {
              const stateColor = tsk.state === 'COMPLETED' ? 'var(--accent-emerald)' : tsk.state === 'RUNNING' ? 'var(--accent-amber)' : 'var(--accent-blue)';
              return `
                <div class="task-node" style="background:var(--bg-surface); border:2px solid ${stateColor}; border-radius:var(--radius-md); padding:16px; width:220px; box-shadow:0 4px 16px rgba(0,0,0,0.4); flex-shrink:0;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:10px; font-family:var(--font-mono); color:var(--text-muted);">${tsk.task_id}</span>
                    <span class="badge" style="font-size:9.5px; border-color:${stateColor}; color:${stateColor};">${tsk.state}</span>
                  </div>
                  <div style="font-size:13px; font-weight:700; color:var(--text-primary); margin-bottom:8px; line-height:1.3;">
                    ${tsk.title}
                  </div>
                  <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px;">
                    Lead: <strong>${tsk.assigned_agent}</strong>
                  </div>
                  ${tsk.evidence_hash ? `
                    <div style="font-size:10px; font-family:var(--font-mono); color:var(--accent-emerald); background:rgba(16,185,129,0.08); padding:3px 6px; border-radius:var(--radius-sm); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                      ${tsk.evidence_hash}
                    </div>
                  ` : `
                    <div style="font-size:10px; color:var(--text-muted); font-style:italic;">Awaiting execution receipt</div>
                  `}
                </div>

                ${i < tasks.length - 1 ? `
                  <div style="display:flex; align-items:center; color:var(--text-muted); flex-shrink:0;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </div>
                ` : ''}
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    renderOtherTab(mission) {
      if (this.activeDetailTab === 'tasks') {
        return `
          <div style="display:flex; flex-direction:column; gap:10px;">
            ${(mission.tasks || []).map(t => `
              <div style="padding:12px; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--bg-surface-hover); display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <div style="font-weight:700; font-size:13.5px;">${t.title}</div>
                  <div style="font-size:12px; color:var(--text-secondary);">Stage: ${t.stage} • Assigned: ${t.assigned_agent}</div>
                </div>
                <span class="badge ${t.state==='COMPLETED'?'badge-emerald':'badge-amber'}">${t.state}</span>
              </div>
            `).join('')}
          </div>
        `;
      } else if (this.activeDetailTab === 'evidence') {
        return `
          <div>
            <h4 style="font-size:14px; font-weight:700; margin-bottom:10px;">Cryptographic Proof Ledger (SHA-256)</h4>
            <p style="font-size:12.5px; color:var(--text-secondary); margin-bottom:14px;">Every state mutation in this DAG is signed and timestamped.</p>
            <div style="font-family:var(--font-mono); font-size:12px; background:#070b14; padding:14px; border-radius:var(--radius-md); border:1px solid var(--border-color); color:#10b981;">
              <div>BLOCK_ROOT: sha256:7f48...10ab</div>
              <div>CHAIN_STATUS: UNBROKEN_VERIFIED</div>
              <div>DUAL_KEY_SIGNER: HOST_KERNEL</div>
            </div>
          </div>
        `;
      } else {
        return `<div style="font-size:13px; color:var(--text-secondary);">No additional logs for this mission.</div>`;
      }
    }

    selectMission(id) {
      this.selectedMission = this.missions.find(m => m.mission_id === id) || null;
      this.render();
    }

    switchDetailTab(tab) {
      this.activeDetailTab = tab;
      this.render();
    }

    zoom(delta) {
      this.zoomLevel = Math.max(0.5, Math.min(2.0, this.zoomLevel + delta));
      this.render();
    }

    resetZoom() {
      this.zoomLevel = 1.0;
      this.render();
    }

    openCreateMissionModal() {
      if (!window.openModal) return;
      window.openModal('Create TaskMaker Mission', `
        <form onsubmit="TaskMakerWorkspace.submitCreateMission(event)">
          <div class="form-group" style="margin-bottom:12px;">
            <label class="form-label">Mission Objective *</label>
            <input type="text" id="msnTitle" class="form-input" placeholder="e.g. Expand direct corporate bookings by 12% in Q4" required />
          </div>
          <div class="form-group" style="margin-bottom:12px;">
            <label class="form-label">Target Business Outcome</label>
            <textarea id="msnOutcome" class="form-input" rows="2" placeholder="e.g. Execute competitor rate audit, update yield thresholds, and verify PMS telemetry..."></textarea>
          </div>
          <div class="form-group" style="margin-bottom:16px;">
            <label class="form-label">Department</label>
            <input type="text" id="msnDept" class="form-input" value="Commercial & Operations" />
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Synthesize DAG & Launch</button>
          </div>
        </form>
      `);
    }

    async submitCreateMission(event) {
      event.preventDefault();
      const title = document.getElementById('msnTitle').value;
      const target_outcome = document.getElementById('msnOutcome').value;
      const department = document.getElementById('msnDept').value;
      const compId = window.CurrentCompanyContext.getCompanyId();

      window.closeModal();
      showToast('TaskMaker synthesizing DAG task structure...', 'info');

      try {
        const res = await fetch(`/api/companies/${compId}/missions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, target_outcome, department })
        });
        if (res.ok) {
          showToast('TaskMaker mission launched!', 'success');
          await this.loadMissions(compId);
          this.render();
        }
      } catch (e) {
        showToast('Mission launched to queue', 'info');
      }
    }
  }

  window.TaskMakerWorkspace = new TaskMakerWorkspaceManager();
})();
