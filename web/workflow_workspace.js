/**
 * ZONATA — Governed Workflow Runtime (LangGraph Engine) Workspace
 * ===============================================================
 * Production UI for stateful, resumable, human-in-the-loop workflows:
 * - Active & Recent Runs
 * - Certified Workflow Templates (StateGraphs)
 * - Human-in-the-Loop Approval Queue
 * - Visual Graph & Checkpoint Time-Travel Inspector
 * - Verification & Scenarios A-K Demonstration Matrix
 */

(function () {
  'use strict';

  class WorkflowWorkspaceManager {
    constructor() {
      this.containerId = 'view-workflows';
      this.activeTab = 'runs'; // 'runs', 'templates', 'approvals', 'inspector', 'demo'
      this.workflows = [];
      this.runs = [];
      this.approvals = [];
      this.selectedRun = null;
      this.selectedRunState = null;
      this.selectedCheckpoints = [];
      this.killswitchActive = false;
    }

    async render(containerId) {
      if (containerId) this.containerId = containerId;
      const el = document.getElementById(this.containerId);
      if (!el) return;

      el.innerHTML = `
        <div style="display:flex; justify-content:center; align-items:center; height:300px; color:var(--text-secondary);">
          <div style="text-align:center;">
            <div style="font-size:24px; margin-bottom:12px; animation:spin 1s linear infinite;">⚙️</div>
            <div>Loading Governed Workflow Runtime...</div>
          </div>
        </div>
      `;

      await this.loadData();
      this.renderUI(el);
    }

    async loadData() {
      try {
        const [wfRes, runRes, apprRes] = await Promise.all([
          fetch('/api/workflows').then(r => r.json()),
          fetch('/api/workflows/runs').then(r => r.json()),
          fetch('/api/workflows/approvals?status=PENDING').then(r => r.json())
        ]);
        this.workflows = wfRes.workflows || [];
        this.runs = runRes.runs || [];
        this.approvals = apprRes.approvals || [];
      } catch (err) {
        console.error('Error loading workflow data:', err);
      }
    }

    renderUI(el) {
      const activeRunsCount = this.runs.filter(r => r.status === 'RUNNING').length;
      const waitingApprovalsCount = this.approvals.length;
      const completedRunsCount = this.runs.filter(r => r.status === 'COMPLETED').length;

      el.innerHTML = `
        <div class="workspace-page-wrapper" style="padding: 24px; max-width: 1400px; margin: 0 auto;">
          <!-- Top Header -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
            <div>
              <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <h1 style="font-size: 22px; font-weight: 700; color: var(--text-primary); margin: 0;">Governed Workflow Runtime</h1>
                <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600;">
                  LangGraph Core v1.2.12
                </span>
                <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600;">
                  ZONATA Sovereign Governance
                </span>
              </div>
              <p style="color: var(--text-secondary); font-size: 13.5px; margin: 0;">
                Durable, stateful execution graphs with zero-secret SQLite checkpointing, human-in-the-loop approvals, and controlled cycles.
              </p>
            </div>

            <!-- Action Controls -->
            <div style="display: flex; align-items: center; gap: 10px;">
              <button class="btn-secondary" onclick="WorkflowWorkspace.toggleKillSwitch()" style="border-color: ${this.killswitchActive ? '#ef4444' : 'var(--border-color)'}; color: ${this.killswitchActive ? '#ef4444' : 'var(--text-primary)'};">
                ${this.killswitchActive ? '🛑 KillSwitch ENGAGED' : '⚡ KillSwitch (Ready)'}
              </button>
              <button class="btn-primary" onclick="WorkflowWorkspace.openRunModal()">
                ▶ Launch Workflow
              </button>
            </div>
          </div>

          <!-- KPI Metrics Row -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Active Runs</div>
              <div style="font-size: 26px; font-weight: 700; color: #3b82f6; margin-top: 4px;">${activeRunsCount}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Durable StateGraph threads</div>
            </div>

            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Waiting Approvals</div>
              <div style="font-size: 26px; font-weight: 700; color: ${waitingApprovalsCount > 0 ? '#f59e0b' : '#10b981'}; margin-top: 4px;">${waitingApprovalsCount}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Human-in-the-Loop decision gates</div>
            </div>

            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Certified Templates</div>
              <div style="font-size: 26px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${this.workflows.length}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Cryptographically sealed graphs</div>
            </div>

            <div class="card" style="padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color); background: var(--bg-surface);">
              <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Completed Operations</div>
              <div style="font-size: 26px; font-weight: 700; color: #10b981; margin-top: 4px;">${completedRunsCount}</div>
              <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Verified Merkle audit proof</div>
            </div>
          </div>

          <!-- Navigation Tabs -->
          <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border-color); margin-bottom: 20px; overflow-x: auto;">
            ${this.renderTabBtn('runs', '🚀 Execution Runs', this.runs.length)}
            ${this.renderTabBtn('templates', '📜 Workflow Templates', this.workflows.length)}
            ${this.renderTabBtn('approvals', '✋ Approval Queue', this.approvals.length)}
            ${this.renderTabBtn('inspector', '🔍 Graph & Time-Travel', null)}
            ${this.renderTabBtn('demo', '🧪 Demonstration Matrix (A-K)', '11')}
          </div>

          <!-- Tab Content Area -->
          <div id="workflowTabContent">
            ${this.renderTabContent()}
          </div>
        </div>
      `;
    }

    renderTabBtn(tabId, label, badge) {
      const active = this.activeTab === tabId;
      return `
        <button onclick="WorkflowWorkspace.switchTab('${tabId}')" style="
          padding: 10px 16px;
          background: none;
          border: none;
          border-bottom: 2px solid ${active ? 'var(--accent-blue)' : 'transparent'};
          color: ${active ? 'var(--accent-blue)' : 'var(--text-secondary)'};
          font-weight: ${active ? '600' : '500'};
          font-size: 13.5px;
          cursor: pointer;
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 8px;
        ">
          ${label}
          ${badge !== null ? `<span style="font-size: 11px; background: ${active ? 'var(--accent-blue)' : 'var(--border-color)'}; color: ${active ? '#fff' : 'var(--text-secondary)'}; padding: 1px 6px; border-radius: 10px;">${badge}</span>` : ''}
        </button>
      `;
    }

    renderTabContent() {
      if (this.activeTab === 'runs') return this.renderRunsTab();
      if (this.activeTab === 'templates') return this.renderTemplatesTab();
      if (this.activeTab === 'approvals') return this.renderApprovalsTab();
      if (this.activeTab === 'inspector') return this.renderInspectorTab();
      if (this.activeTab === 'demo') return this.renderDemoTab();
      return '';
    }

    renderRunsTab() {
      if (!this.runs.length) {
        return `
          <div class="card" style="padding: 40px; text-align: center; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="font-size: 32px; margin-bottom: 12px;">💤</div>
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">No Active Workflow Runs</h3>
            <p style="font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
              Launch a workflow template or trigger an automated mission from TaskMaker.
            </p>
            <button class="btn-primary" onclick="WorkflowWorkspace.openRunModal()">Launch Workflow</button>
          </div>
        `;
      }

      return `
        <div class="card" style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); overflow: hidden;">
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-color); background: var(--bg-surface-hover); color: var(--text-secondary);">
                  <th style="padding: 12px 16px;">Run ID</th>
                  <th style="padding: 12px 16px;">Workflow</th>
                  <th style="padding: 12px 16px;">Status</th>
                  <th style="padding: 12px 16px;">Current Node</th>
                  <th style="padding: 12px 16px;">Steps</th>
                  <th style="padding: 12px 16px;">Created</th>
                  <th style="padding: 12px 16px; text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${this.runs.map(r => `
                  <tr style="border-bottom: 1px solid var(--border-color); cursor: pointer;" onclick="WorkflowWorkspace.inspectRun('${r.run_id}')">
                    <td style="padding: 12px 16px; font-family: monospace; color: var(--accent-blue); font-weight: 600;">${r.run_id}</td>
                    <td style="padding: 12px 16px; font-weight: 500; color: var(--text-primary);">${r.workflow_id}</td>
                    <td style="padding: 12px 16px;">${this.renderStatusBadge(r.status)}</td>
                    <td style="padding: 12px 16px; font-family: monospace; color: var(--text-secondary);">${r.current_node || '—'}</td>
                    <td style="padding: 12px 16px; color: var(--text-secondary);">${r.step_count || 0}</td>
                    <td style="padding: 12px 16px; color: var(--text-secondary); font-size: 12px;">${new Date(r.created_at * 1000).toLocaleTimeString()}</td>
                    <td style="padding: 12px 16px; text-align: right;" onclick="event.stopPropagation()">
                      ${this.renderRunActions(r)}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    renderStatusBadge(status) {
      let bg = 'rgba(107, 114, 128, 0.15)';
      let col = '#6b7280';
      if (status === 'RUNNING') { bg = 'rgba(59, 130, 246, 0.15)'; col = '#3b82f6'; }
      else if (status === 'COMPLETED') { bg = 'rgba(16, 185, 129, 0.15)'; col = '#10b981'; }
      else if (status === 'WAITING_FOR_APPROVAL' || status === 'WAITING_FOR_INPUT') { bg = 'rgba(245, 158, 11, 0.15)'; col = '#f59e0b'; }
      else if (status === 'FAILED' || status === 'BLOCKED') { bg = 'rgba(239, 68, 68, 0.15)'; col = '#ef4444'; }
      else if (status === 'PAUSED') { bg = 'rgba(139, 92, 246, 0.15)'; col = '#8b5cf6'; }
      else if (status === 'AMBIGUOUS') { bg = 'rgba(236, 72, 153, 0.15)'; col = '#ec4899'; }

      return `
        <span style="background:${bg}; color:${col}; font-size:11px; padding:3px 8px; border-radius:10px; font-weight:600; text-transform:uppercase;">
          ${status}
        </span>
      `;
    }

    renderRunActions(r) {
      if (r.status === 'RUNNING') {
        return `<button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="WorkflowWorkspace.pauseRun('${r.run_id}')">Pause</button>`;
      } else if (r.status === 'PAUSED' || r.status === 'WAITING_FOR_INPUT') {
        return `<button class="btn-primary" style="padding:4px 8px; font-size:11.5px;" onclick="WorkflowWorkspace.resumeRun('${r.run_id}')">Resume</button>`;
      } else if (r.status === 'FAILED' || r.status === 'AMBIGUOUS') {
        return `<button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="WorkflowWorkspace.recoverRun('${r.run_id}')">Recover</button>`;
      }
      return `<button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="WorkflowWorkspace.inspectRun('${r.run_id}')">Inspect</button>`;
    }

    renderTemplatesTab() {
      return `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
          ${this.workflows.map(wf => `
            <div class="card" style="padding: 18px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <h4 style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0;">${wf.name}</h4>
                <span class="badge" style="background: rgba(59, 130, 246, 0.1); color: var(--accent-blue); font-size: 11px; padding: 2px 6px; border-radius: 4px;">
                  v${wf.version}
                </span>
              </div>
              <div style="font-size: 12px; font-family: monospace; color: var(--text-secondary); margin-bottom: 12px;">
                ${wf.workflow_id}
              </div>
              <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
                <span style="font-size: 11px; background: var(--bg-surface-hover); padding: 2px 6px; border-radius: 4px; color: var(--text-secondary);">
                  Risk: ${wf.risk_level}
                </span>
                <span style="font-size: 11px; background: var(--bg-surface-hover); padding: 2px 6px; border-radius: 4px; color: var(--text-secondary);">
                  Runtime: ${wf.runtime_provider}
                </span>
              </div>
              <button class="btn-primary" style="width: 100%; font-size: 12.5px; padding: 6px 12px;" onclick="WorkflowWorkspace.launchTemplate('${wf.workflow_id}')">
                Execute StateGraph
              </button>
            </div>
          `).join('')}
        </div>
      `;
    }

    renderApprovalsTab() {
      if (!this.approvals.length) {
        return `
          <div class="card" style="padding: 40px; text-align: center; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="font-size: 32px; margin-bottom: 12px;">✅</div>
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">All Workflow Actions Authorized</h3>
            <p style="font-size: 13px; max-width: 480px; margin: 0 auto;">
              No pending approval requests. Privileged operations requiring human decision will appear here.
            </p>
          </div>
        `;
      }

      return `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          ${this.approvals.map(appr => `
            <div class="card" style="padding: 18px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div>
                  <span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600;">
                    ${appr.risk_level} RISK
                  </span>
                  <h4 style="font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 6px 0 2px 0;">${appr.proposed_action}</h4>
                  <div style="font-size: 12px; font-family: monospace; color: var(--text-secondary);">
                    Run: ${appr.run_id} • Node: ${appr.node_id}
                  </div>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary);">
                  ${new Date(appr.created_at * 1000).toLocaleTimeString()}
                </div>
              </div>

              <!-- Parameters preview -->
              <div style="background: var(--bg-surface-hover); padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 12px; color: var(--text-primary); margin-bottom: 14px; overflow-x: auto;">
                ${JSON.stringify(appr.parameters, null, 2)}
              </div>

              <div style="display: flex; justify-content: flex-end; gap: 10px;">
                <button class="btn-secondary" style="border-color: #ef4444; color: #ef4444; font-size: 12.5px; padding: 6px 14px;" onclick="WorkflowWorkspace.rejectApproval('${appr.approval_id}')">
                  Reject Action
                </button>
                <button class="btn-secondary" style="font-size: 12.5px; padding: 6px 14px;" onclick="WorkflowWorkspace.openEditModal('${appr.approval_id}', '${encodeURIComponent(JSON.stringify(appr.parameters))}')">
                  ✏️ Edit & Resume
                </button>
                <button class="btn-primary" style="font-size: 12.5px; padding: 6px 14px;" onclick="WorkflowWorkspace.approveApproval('${appr.approval_id}')">
                  ✓ Approve Execution
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    renderInspectorTab() {
      if (!this.selectedRun) {
        return `
          <div class="card" style="padding: 40px; text-align: center; color: var(--text-secondary); background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="font-size: 32px; margin-bottom: 12px;">🔍</div>
            <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px;">Select a Workflow Run to Inspect</h3>
            <p style="font-size: 13px; max-width: 480px; margin: 0 auto 16px auto;">
              Click any execution run from the 'Execution Runs' tab to inspect its StateGraph, step timeline, and zero-secret checkpoints.
            </p>
            ${this.runs.length > 0 ? `
              <button class="btn-primary" onclick="WorkflowWorkspace.inspectRun('${this.runs[0].run_id}')">
                Inspect Latest Run (${this.runs[0].run_id})
              </button>
            ` : ''}
          </div>
        `;
      }

      const stateObj = this.selectedRunState ? this.selectedRunState.run_state : null;
      const latestChk = stateObj ? stateObj.latest_checkpoint : null;

      return `
        <div style="display: grid; grid-template-columns: 1fr 340px; gap: 20px; flex-wrap: wrap;">
          <!-- Left: StateGraph Timeline & Checkpoint Viewer -->
          <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
              <div>
                <h3 style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0;">StateGraph Execution Flow</h3>
                <div style="font-size: 12px; font-family: monospace; color: var(--text-secondary);">Run: ${this.selectedRun}</div>
              </div>
              <div>${stateObj ? this.renderStatusBadge(stateObj.status) : ''}</div>
            </div>

            <!-- Visual Flow (Desktop Graph / Mobile Timeline) -->
            <div style="background: var(--bg-surface-hover); border-radius: var(--radius-md); padding: 20px; margin-bottom: 20px;">
              <div style="display: flex; align-items: center; gap: 12px; overflow-x: auto; padding: 10px 0;">
                <div style="padding: 10px 14px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; font-size: 12px; font-weight: 600; color: var(--text-primary); min-width: 100px; text-align: center;">
                  START
                </div>
                <div style="color: var(--text-secondary);">➔</div>
                <div style="padding: 10px 14px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 8px; font-size: 12px; font-weight: 600; color: var(--accent-blue); min-width: 120px; text-align: center;">
                  ${stateObj && stateObj.current_node ? stateObj.current_node : 'ACTIVE_NODE'}
                </div>
                <div style="color: var(--text-secondary);">➔</div>
                <div style="padding: 10px 14px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 8px; font-size: 12px; font-weight: 600; color: var(--text-primary); min-width: 100px; text-align: center;">
                  END
                </div>
              </div>
            </div>

            <!-- Checkpoint History Timeline -->
            <h4 style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px;">Checkpoint History (${this.selectedCheckpoints.length} snapshots)</h4>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${this.selectedCheckpoints.map(chk => `
                <div style="padding: 10px 14px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-surface); display: flex; justify-content: space-between; align-items: center;">
                  <div>
                    <span style="font-weight: 600; color: var(--accent-blue); font-size: 12px;">Step ${chk.step}</span>
                    <span style="color: var(--text-secondary); font-size: 12px; margin-left: 8px;">Node: <code>${chk.current_node}</code></span>
                  </div>
                  <div style="font-size: 11px; font-family: monospace; color: var(--text-secondary);">
                    SHA: ${chk.state_digest.substring(0, 12)}...
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Right: State Inspector -->
          <div class="card" style="padding: 20px; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
            <h4 style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0 0 12px 0;">Checkpoint State Payload</h4>
            <div style="background: var(--bg-surface-hover); border-radius: 6px; padding: 12px; font-family: monospace; font-size: 11.5px; color: var(--text-primary); max-height: 400px; overflow-y: auto; white-space: pre-wrap;">
              ${latestChk ? JSON.stringify(latestChk.state_payload, null, 2) : 'No state loaded'}
            </div>
          </div>
        </div>
      `;
    }

    renderDemoTab() {
      const scenarios = [
        { key: 'A', name: 'Simple Workflow', desc: 'Host Objective ➔ Tool ➔ Physical Verification ➔ Evidence Merkle Root.' },
        { key: 'B', name: 'Long-Running Workflow', desc: 'Checkpoints state, halts at gate, resumes with Command.' },
        { key: 'C', name: 'Human Approval', desc: 'Sensitive funds action pauses, awaits host approval, and executes.' },
        { key: 'D', name: 'Human Edit', desc: 'Host modifies parameters before approving; runs with edited values.' },
        { key: 'E', name: 'Failure Recovery', desc: 'Recovers crashed process from checkpoint without blind mutation replay.' },
        { key: 'F', name: 'Ambiguous Transaction', desc: 'API timeout caught in AMBIGUOUS state; requires external reconcile.' },
        { key: 'G', name: 'Loop Control', desc: 'Quality refinement loop terminates when threshold met, bounded by max iterations.' },
        { key: 'H', name: 'Agency Swarm', desc: 'AI CEO delegating complex task to Agency Swarm specialist squads.' },
        { key: 'I', name: 'Letta Memory Firewall', desc: 'Separates ephemeral checkpoint state from permanent memory blocks; zero secrets.' },
        { key: 'J', name: 'HAL Multimodal', desc: 'Invokes HAL screen observer and synthesizes spoken audio report.' },
        { key: 'K', name: 'Authoritative KillSwitch', desc: 'Emergency KillSwitch immediately freezes execution thread.' }
      ];

      return `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
          ${scenarios.map(sc => `
            <div class="card" style="padding: 16px; border: 1px solid var(--border-color); border-radius: var(--radius-md); background: var(--bg-surface);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); font-weight: 700; padding: 2px 8px; border-radius: 8px; font-size: 11px;">
                  TEST ${sc.key}
                </span>
                <span style="font-size: 12px; font-weight: 600; color: var(--text-primary);">${sc.name}</span>
              </div>
              <p style="font-size: 12.5px; color: var(--text-secondary); margin: 0 0 14px 0; min-height: 38px;">
                ${sc.desc}
              </p>
              <button class="btn-primary" style="width: 100%; font-size: 12px; padding: 6px 12px;" onclick="WorkflowWorkspace.runDemoScenario('${sc.key}')">
                ▶ Verify Scenario ${sc.key}
              </button>
              <div id="demoResult_${sc.key}" style="margin-top: 10px; display: none; font-size: 11.5px; padding: 8px 12px; border-radius: 6px; font-family: monospace;"></div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // =========================================================================
    // USER ACTIONS & API CALLS
    // =========================================================================

    switchTab(tabId) {
      this.activeTab = tabId;
      const contentEl = document.getElementById('workflowTabContent');
      if (contentEl) contentEl.innerHTML = this.renderTabContent();
    }

    async inspectRun(runId) {
      this.selectedRun = runId;
      try {
        const [stateRes, chkRes] = await Promise.all([
          fetch(`/api/workflows/runs/${runId}/state`).then(r => r.json()),
          fetch(`/api/workflows/runs/${runId}/checkpoints`).then(r => r.json())
        ]);
        this.selectedRunState = stateRes;
        this.selectedCheckpoints = chkRes.checkpoints || [];
        this.activeTab = 'inspector';
        this.render();
      } catch (err) {
        showToast('Error inspecting run: ' + err.message, 'error');
      }
    }

    async pauseRun(runId) {
      try {
        await fetch(`/api/workflows/runs/${runId}/pause`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason: 'Host request' })
        });
        showToast(`Paused run ${runId}`, 'info');
        this.render();
      } catch (err) {
        showToast('Error pausing run: ' + err.message, 'error');
      }
    }

    async resumeRun(runId) {
      try {
        await fetch(`/api/workflows/runs/${runId}/resume`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        showToast(`Resumed run ${runId}`, 'success');
        this.render();
      } catch (err) {
        showToast('Error resuming run: ' + err.message, 'error');
      }
    }

    async recoverRun(runId) {
      try {
        await fetch(`/api/workflows/runs/${runId}/recover`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        showToast(`Recovered run ${runId} from checkpoint`, 'success');
        this.render();
      } catch (err) {
        showToast('Error recovering run: ' + err.message, 'error');
      }
    }

    async approveApproval(apprId) {
      try {
        await fetch(`/api/workflows/approvals/${apprId}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ actor: 'Host' })
        });
        showToast(`Approved execution ${apprId}`, 'success');
        this.render();
      } catch (err) {
        showToast('Approval error: ' + err.message, 'error');
      }
    }

    async rejectApproval(apprId) {
      try {
        await fetch(`/api/workflows/approvals/${apprId}/reject`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ actor: 'Host', reason: 'Host rejected' })
        });
        showToast(`Rejected execution ${apprId}`, 'warning');
        this.render();
      } catch (err) {
        showToast('Rejection error: ' + err.message, 'error');
      }
    }

    openEditModal(apprId, paramsEncoded) {
      const params = JSON.parse(decodeURIComponent(paramsEncoded));
      window.openModal('Edit Proposed Workflow Parameters', `
        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
          Modify parameter payload before execution. Modifications will be cryptographically audited.
        </div>
        <textarea id="editParamsInput" style="width: 100%; height: 180px; font-family: monospace; font-size: 12px; padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: var(--text-primary); margin-bottom: 16px;">${JSON.stringify(params, null, 2)}</textarea>
        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button class="btn-secondary" onclick="closeModal()">Cancel</button>
          <button class="btn-primary" onclick="WorkflowWorkspace.submitEdit('${apprId}')">Submit & Resume</button>
        </div>
      `);
    }

    async submitEdit(apprId) {
      try {
        const txt = document.getElementById('editParamsInput').value;
        const modified = JSON.parse(txt);
        closeModal();
        await fetch(`/api/workflows/approvals/${apprId}/edit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ parameters: modified, actor: 'Host' })
        });
        showToast('Workflow resumed with modified parameters', 'success');
        this.render();
      } catch (err) {
        showToast('Error editing parameters: ' + err.message, 'error');
      }
    }

    async toggleKillSwitch() {
      this.killswitchActive = !this.killswitchActive;
      try {
        await fetch('/api/workflows/killswitch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ active: this.killswitchActive })
        });
        showToast(this.killswitchActive ? '🛑 ZONATA KillSwitch ENGAGED' : '⚡ KillSwitch DISENGAGED', this.killswitchActive ? 'error' : 'info');
        this.render();
      } catch (err) {
        showToast('KillSwitch error: ' + err.message, 'error');
      }
    }

    async launchTemplate(wfId) {
      try {
        const res = await fetch(`/api/workflows/${wfId}/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ inputs: { objective: 'Launched from Workflow Templates' } })
        }).then(r => r.json());
        showToast(`Workflow ${wfId} launched (Run: ${res.run_id})`, 'success');
        this.activeTab = 'runs';
        this.render();
      } catch (err) {
        showToast('Launch error: ' + err.message, 'error');
      }
    }

    async runDemoScenario(scenarioKey) {
      const resEl = document.getElementById(`demoResult_${scenarioKey}`);
      if (resEl) {
        resEl.style.display = 'block';
        resEl.style.background = 'var(--bg-surface-hover)';
        resEl.style.color = 'var(--text-secondary)';
        resEl.innerText = 'Executing scenario against live runtime...';
      }

      try {
        const data = await fetch('/api/workflows/demo/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: scenarioKey })
        }).then(r => r.json());

        const resObj = data.result || {};
        if (resEl) {
          if (resObj.verified) {
            resEl.style.background = 'rgba(16, 185, 129, 0.15)';
            resEl.style.color = '#10b981';
            resEl.innerText = `✓ Verified: Status=${resObj.status || 'COMPLETED'}`;
          } else {
            resEl.style.background = 'rgba(239, 68, 68, 0.15)';
            resEl.style.color = '#ef4444';
            resEl.innerText = `✕ Error: ${resObj.error || 'Failed'}`;
          }
        }
        showToast(`Scenario ${scenarioKey} verified successfully!`, 'success');
      } catch (err) {
        if (resEl) {
          resEl.style.background = 'rgba(239, 68, 68, 0.15)';
          resEl.style.color = '#ef4444';
          resEl.innerText = `✕ Error: ${err.message}`;
        }
      }
    }

    openRunModal() {
      const options = this.workflows.map(w => `<option value="${w.workflow_id}">${w.name} (${w.workflow_id})</option>`).join('');
      window.openModal('Launch Governed Workflow', `
        <form onsubmit="WorkflowWorkspace.submitLaunch(event)">
          <div style="margin-bottom: 14px;">
            <label style="display:block; font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Select Workflow Template</label>
            <select id="modalWfId" style="width:100%; padding:8px 12px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-surface); color:var(--text-primary); font-size:13px;">
              ${options}
            </select>
          </div>
          <div style="margin-bottom: 16px;">
            <label style="display:block; font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Task Objective / Inputs (JSON)</label>
            <textarea id="modalWfInputs" style="width:100%; height:100px; padding:8px 12px; border-radius:6px; border:1px solid var(--border-color); background:var(--bg-surface); color:var(--text-primary); font-family:monospace; font-size:12px;">{"objective": "Comprehensive Financial Margin Audit"}</textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Launch Execution</button>
          </div>
        </form>
      `);
    }

    async submitLaunch(e) {
      e.preventDefault();
      const wfId = document.getElementById('modalWfId').value;
      const rawInputs = document.getElementById('modalWfInputs').value;
      try {
        const inputs = JSON.parse(rawInputs);
        closeModal();
        await this.launchTemplate(wfId);
      } catch (err) {
        showToast('Invalid JSON inputs: ' + err.message, 'error');
      }
    }
  }

  window.WorkflowWorkspace = new WorkflowWorkspaceManager();
})();
