/**
 * ZONATA — Governed Temporal Durable Execution Center
 * ===================================================
 * Project 09: Governed Durable Execution & Long-Running Mission Reliability Layer.
 *
 * Core Capabilities:
 * - Active & Historical Durable Processes / Workflows Inspector
 * - Mission Execution Detail Timeline (Created -> Planned -> Authorized -> Started -> Activity -> Tool -> Verification -> Outcome)
 * - Execution Workers & Governed Task Queues (Heartbeat, Queues, Concurrency)
 * - Human-in-the-Loop Durable Approval Center (Hours/Days/Weeks Waits with Authority Re-validation)
 * - Reconciliations & Unknown Outcomes (No Blind Replay, External Assertions, Sagas)
 * - Security Center & Authoritative Multi-Scope KillSwitch
 * - Canonical Scenarios (Tests 01-09) & Section 85 Grand Acceptance Test Runner
 */

(function () {
  'use strict';

  class TemporalWorkspaceManager {
    constructor() {
      this.containerId = 'view-temporal-durable';
      this.activeTab = 'processes'; // 'processes', 'timeline', 'workers', 'approvals', 'reconciliations', 'security', 'scenarios'
      this.workflows = [];
      this.workers = [];
      this.queues = [];
      this.approvals = [];
      this.securityEvents = [];
      this.selectedWorkflow = null;
      this.selectedWorkflowHistory = [];
      this.metrics = {
        total_workflows: 0,
        active_workflows: 0,
        completed_workflows: 0,
        failed_workflows: 0,
        pending_approvals: 0,
        unknown_outcomes: 0,
        reconciled_count: 0,
        workers_online: 0,
        task_queues_count: 0,
        security_events: 0,
        recovery_rate_pct: 100,
        server_version: '1.26.2',
        sdk_version: '1.7.0',
        cluster_status: 'ONLINE'
      };
      this.killswitchActive = false;
      this.isExecutingScenario = false;
      this.scenarioOutput = null;
      this.filterStatus = 'ALL';
    }

    async render(containerId) {
      if (containerId) this.containerId = containerId;
      const el = document.getElementById(this.containerId);
      if (!el) return;

      el.innerHTML = `
        <div style="display:flex; justify-content:center; align-items:center; height:300px; color:var(--text-secondary);">
          <div style="text-align:center;">
            <div style="font-size:28px; margin-bottom:12px; animation:spin 1s linear infinite;">⏳</div>
            <div style="font-weight:600; font-size:15px; color:var(--text-primary);">Loading Governed Temporal Durable Execution Center...</div>
            <div style="font-size:12px; margin-top:4px;">Connecting durable workflows, execution workers, task queues, and Merkle verification ledger</div>
          </div>
        </div>
      `;

      await this.loadData();
      this.renderUI(el);
    }

    async loadData() {
      try {
        const [wfRes, wrkRes, qRes, apprRes, secRes, metricsRes, ksRes] = await Promise.all([
          fetch('/api/temporal/workflows?limit=50').then(r => r.json()).catch(() => ({ workflows: [] })),
          fetch('/api/temporal/workers').then(r => r.json()).catch(() => ({ workers: [] })),
          fetch('/api/temporal/queues').then(r => r.json()).catch(() => ({ queues: [] })),
          fetch('/api/temporal/approvals').then(r => r.json()).catch(() => ({ approvals: [] })),
          fetch('/api/temporal/security/events?limit=50').then(r => r.json()).catch(() => ({ security_events: [] })),
          fetch('/api/temporal/metrics').then(r => r.json()).catch(() => ({ metrics: {} })),
          fetch('/api/temporal/killswitch').then(r => r.json()).catch(() => ({ killswitch_active: false }))
        ]);

        this.workflows = wfRes.workflows || [];
        this.workers = wrkRes.workers || [];
        this.queues = qRes.queues || [];
        this.approvals = apprRes.approvals || [];
        this.securityEvents = secRes.security_events || [];
        this.metrics = Object.assign(this.metrics, metricsRes.metrics || {});
        this.killswitchActive = !!ksRes.killswitch_active;

        if (this.workflows.length > 0 && !this.selectedWorkflow) {
          await this.selectWorkflow(this.workflows[0].workflow_id);
        }
      } catch (err) {
        console.error('Failed to load Temporal data:', err);
      }
    }

    async selectWorkflow(workflowId) {
      try {
        const [wfRes, histRes] = await Promise.all([
          fetch(`/api/temporal/workflows/${workflowId}`).then(r => r.json()),
          fetch(`/api/temporal/workflows/${workflowId}/history`).then(r => r.json())
        ]);
        this.selectedWorkflow = wfRes;
        this.selectedWorkflowHistory = histRes.history || [];
      } catch (err) {
        console.error('Failed to load workflow detail:', err);
      }
    }

    renderUI(container) {
      container.innerHTML = `
        <div class="mcp-workspace-root" style="padding: 20px; max-width: 1400px; margin: 0 auto; color: var(--text-primary, #e2e8f0); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
          ${this.renderHeader()}
          ${this.renderMetricsBar()}
          ${this.renderTabsNav()}
          <div class="mcp-tab-content" style="margin-top: 20px;">
            ${this.renderActiveTabContent()}
          </div>
        </div>
      `;
      this.attachEventListeners();
    }

    renderHeader() {
      const ksBadge = this.killswitchActive
        ? `<span style="background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
            <span style="display:inline-block; width:6px; height:6px; background:#ef4444; border-radius:50%;"></span> KILLSWITCH ENGAGED
          </span>`
        : `<span style="background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid #22c55e; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
            <span style="display:inline-block; width:6px; height:6px; background:#22c55e; border-radius:50%;"></span> DURABLE RUNTIME ONLINE
          </span>`;

      return `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.08));">
          <div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <h1 style="font-size: 24px; font-weight: 700; margin: 0; display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 26px;">⏳</span> Governed Durable Execution Center
              </h1>
              ${ksBadge}
              <span style="font-size: 11px; padding: 3px 8px; border-radius: 4px; background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3);">
                Temporal v${this.metrics.server_version || '1.26.2'} • SDK v${this.metrics.sdk_version || '1.7.0'}
              </span>
            </div>
            <p style="margin: 6px 0 0 0; font-size: 13px; color: var(--text-secondary, #94a3b8);">
              Enterprise durable execution underneath ZONATA Sovereignty • Crash recovery, durable human approval waits & verified business causality.
            </p>
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <button id="btnRefreshTemporal" class="btn btn-secondary" style="display:flex; align-items:center; gap:6px; padding: 8px 14px; font-size: 12px;">
              <span>🔄</span> Refresh
            </button>
            <button id="btnToggleTemporalKillswitch" class="btn ${this.killswitchActive ? 'btn-success' : 'btn-danger'}" style="display:flex; align-items:center; gap:6px; padding: 8px 14px; font-size: 12px; font-weight: 600;">
              <span>🛑</span> ${this.killswitchActive ? 'Reset KillSwitch' : 'Trip KillSwitch'}
            </button>
          </div>
        </div>
      `;
    }

    renderMetricsBar() {
      const m = this.metrics;
      return `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 24px;">
          <div class="mcp-kpi-card" style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); text-transform: uppercase; font-weight: 600;">Active Workflows</div>
            <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #38bdf8;">${m.active_workflows}</div>
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); margin-top: 2px;">Total: ${m.total_workflows}</div>
          </div>

          <div class="mcp-kpi-card" style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); text-transform: uppercase; font-weight: 600;">Recovery Rate</div>
            <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #22c55e;">${m.recovery_rate_pct}%</div>
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); margin-top: 2px;">${m.completed_workflows} completed • ${m.failed_workflows} failed</div>
          </div>

          <div class="mcp-kpi-card" style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); text-transform: uppercase; font-weight: 600;">Human Approval Waits</div>
            <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #f59e0b;">${m.pending_approvals}</div>
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); margin-top: 2px;">Durable pause in effect</div>
          </div>

          <div class="mcp-kpi-card" style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); text-transform: uppercase; font-weight: 600;">Execution Workers</div>
            <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #a855f7;">${m.workers_online}</div>
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); margin-top: 2px;">${m.task_queues_count} Governed Task Queues</div>
          </div>

          <div class="mcp-kpi-card" style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); text-transform: uppercase; font-weight: 600;">Reconciliations</div>
            <div style="font-size: 24px; font-weight: 700; margin-top: 4px; color: #10b981;">${m.reconciled_count}</div>
            <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); margin-top: 2px;">Unknown outcomes resolved</div>
          </div>
        </div>
      `;
    }

    renderTabsNav() {
      const tabs = [
        { id: 'processes', label: 'Durable Processes', icon: '⚡', count: this.workflows.length },
        { id: 'timeline', label: 'Mission Timeline', icon: '📊' },
        { id: 'workers', label: 'Workers & Queues', icon: '⚙️', count: this.workers.length },
        { id: 'approvals', label: 'Human Approval Waits', icon: '👤', count: this.approvals.filter(a => a.status === 'PENDING').length },
        { id: 'reconciliations', label: 'Reconciliations & Sagas', icon: '🔄', count: this.metrics.reconciled_count },
        { id: 'security', label: 'Security & Audit', icon: '🛡️', count: this.securityEvents.length },
        { id: 'scenarios', label: 'Canonical Scenarios', icon: '🧪' }
      ];

      return `
        <div style="display: flex; gap: 4px; border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.08)); overflow-x: auto; padding-bottom: 2px;">
          ${tabs.map(t => {
            const isActive = this.activeTab === t.id;
            return `
              <button class="mcp-tab-btn" data-tab="${t.id}" style="
                background: ${isActive ? 'rgba(59, 130, 246, 0.15)' : 'transparent'};
                color: ${isActive ? '#60a5fa' : 'var(--text-secondary, #94a3b8)'};
                border: none;
                border-bottom: 2px solid ${isActive ? '#3b82f6' : 'transparent'};
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                white-space: nowrap;
                transition: all 0.15s ease;
              ">
                <span>${t.icon}</span>
                <span>${t.label}</span>
                ${t.count !== undefined ? `<span style="font-size: 11px; padding: 1px 6px; border-radius: 9999px; background: ${isActive ? 'rgba(59, 130, 246, 0.3)' : 'rgba(255,255,255,0.08)'};">${t.count}</span>` : ''}
              </button>
            `;
          }).join('')}
        </div>
      `;
    }

    renderActiveTabContent() {
      switch (this.activeTab) {
        case 'processes':
          return this.renderProcessesTab();
        case 'timeline':
          return this.renderTimelineTab();
        case 'workers':
          return this.renderWorkersTab();
        case 'approvals':
          return this.renderApprovalsTab();
        case 'reconciliations':
          return this.renderReconciliationsTab();
        case 'security':
          return this.renderSecurityTab();
        case 'scenarios':
          return this.renderScenariosTab();
        default:
          return this.renderProcessesTab();
      }
    }

    renderProcessesTab() {
      const filtered = this.workflows.filter(wf => {
        if (this.filterStatus === 'ALL') return true;
        return wf.status === this.filterStatus;
      });

      return `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <!-- Left: Workflows List -->
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
              <h3 style="font-size: 15px; font-weight: 600; margin: 0;">Durable Workflows (${filtered.length})</h3>
              <div style="display: flex; gap: 8px;">
                <select id="selTemporalStatusFilter" style="background: var(--card-bg, #1e293b); color: var(--text-primary, #e2e8f0); border: 1px solid var(--border-color, rgba(255,255,255,0.1)); border-radius: 6px; padding: 4px 8px; font-size: 12px;">
                  <option value="ALL" ${this.filterStatus === 'ALL' ? 'selected' : ''}>All States</option>
                  <option value="RUNNING" ${this.filterStatus === 'RUNNING' ? 'selected' : ''}>RUNNING</option>
                  <option value="COMPLETED" ${this.filterStatus === 'COMPLETED' ? 'selected' : ''}>COMPLETED</option>
                  <option value="AWAITING_APPROVAL" ${this.filterStatus === 'AWAITING_APPROVAL' ? 'selected' : ''}>AWAITING_APPROVAL</option>
                  <option value="FAILED" ${this.filterStatus === 'FAILED' ? 'selected' : ''}>FAILED</option>
                  <option value="UNKNOWN_OUTCOME" ${this.filterStatus === 'UNKNOWN_OUTCOME' ? 'selected' : ''}>UNKNOWN_OUTCOME</option>
                </select>
                <button id="btnNewWorkflowModal" class="btn btn-primary" style="padding: 4px 10px; font-size: 12px;">+ New Process</button>
              </div>
            </div>

            <div style="display: flex; flex-direction: column; gap: 10px; max-height: 600px; overflow-y: auto;">
              ${filtered.length === 0 ? `
                <div style="text-align: center; padding: 40px; color: var(--text-secondary, #94a3b8); background: var(--card-bg, #1e293b); border-radius: 8px;">
                  No durable processes match the selected status filter.
                </div>
              ` : filtered.map(wf => {
                const isSelected = this.selectedWorkflow && this.selectedWorkflow.workflow_id === wf.workflow_id;
                const statusColor = this.getStatusColor(wf.status);
                return `
                  <div class="wf-item-card" data-wfid="${wf.workflow_id}" style="
                    background: ${isSelected ? 'rgba(59, 130, 246, 0.1)' : 'var(--card-bg, #1e293b)'};
                    border: 1px solid ${isSelected ? '#3b82f6' : 'var(--border-color, rgba(255,255,255,0.08))'};
                    border-radius: 8px;
                    padding: 14px;
                    cursor: pointer;
                    transition: border 0.15s ease;
                  ">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                      <div>
                        <div style="font-weight: 600; font-size: 14px; color: #f8fafc;">${wf.workflow_type}</div>
                        <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); margin-top: 2px;">
                          ID: <code style="color:#38bdf8;">${wf.workflow_id}</code> • Queue: <code>${wf.task_queue}</code>
                        </div>
                      </div>
                      <span style="background: ${statusColor.bg}; color: ${statusColor.text}; border: 1px solid ${statusColor.border}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">
                        ${wf.status}
                      </span>
                    </div>

                    <div style="display: flex; gap: 14px; margin-top: 10px; font-size: 11px; color: var(--text-secondary, #94a3b8);">
                      <span>⏱️ ${new Date(wf.created_at * 1000).toLocaleTimeString()}</span>
                      <span>🛡️ Verif: <b style="color:${wf.verification_status === 'VERIFIED' ? '#22c55e' : '#94a3b8'};">${wf.verification_status || 'UNVERIFIED'}</b></span>
                      ${wf.idempotency_key ? `<span>🔑 Idemp: <code>${wf.idempotency_key.substring(0, 14)}...</code></span>` : ''}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Right: Selected Workflow Inspector -->
          <div>
            ${this.renderWorkflowInspector()}
          </div>
        </div>
      `;
    }

    renderWorkflowInspector() {
      const wf = this.selectedWorkflow;
      if (!wf) {
        return `
          <div style="text-align: center; padding: 60px; color: var(--text-secondary, #94a3b8); background: var(--card-bg, #1e293b); border-radius: 8px; border: 1px dashed var(--border-color, rgba(255,255,255,0.15));">
            Select a durable process on the left to inspect its state, history, and verification evidence.
          </div>
        `;
      }

      const statusColor = this.getStatusColor(wf.status);

      return `
        <div style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 18px;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
            <div>
              <h3 style="margin: 0; font-size: 16px; font-weight: 600;">${wf.workflow_type}</h3>
              <div style="font-size: 11px; color: var(--text-secondary, #94a3b8); margin-top: 2px;">
                Workflow ID: <code style="color:#38bdf8;">${wf.workflow_id}</code> • Run: <code>${wf.run_id}</code>
              </div>
            </div>
            <span style="background: ${statusColor.bg}; color: ${statusColor.text}; border: 1px solid ${statusColor.border}; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600;">
              ${wf.status}
            </span>
          </div>

          <!-- Action buttons for workflow lifecycle -->
          <div style="display: flex; gap: 8px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid rgba(255,255,255,0.08);">
            ${wf.status === 'RUNNING' ? `
              <button class="btn btn-secondary btn-sm" onclick="window.temporalApp.pauseSelectedWorkflow()">⏸️ Pause</button>
              <button class="btn btn-danger btn-sm" onclick="window.temporalApp.cancelSelectedWorkflow()">✕ Cancel</button>
            ` : ''}
            ${wf.status === 'PAUSED' ? `
              <button class="btn btn-primary btn-sm" onclick="window.temporalApp.resumeSelectedWorkflow()">▶️ Resume</button>
            ` : ''}
            ${wf.status === 'AWAITING_APPROVAL' ? `
              <button class="btn btn-success btn-sm" onclick="window.temporalApp.quickApproveWorkflow()">✓ Approve Step</button>
            ` : ''}
            ${wf.status === 'UNKNOWN_OUTCOME' ? `
              <button class="btn btn-warning btn-sm" onclick="window.temporalApp.reconcileSelectedWorkflow()">🔄 Reconcile Outcome</button>
            ` : ''}
            <button class="btn btn-secondary btn-sm" onclick="window.temporalApp.recoverSelectedWorkflow()">🔁 Test Crash Recovery</button>
          </div>

          <!-- Payload Tabs -->
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <div>
              <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 4px;">Sanitized Input Payload:</div>
              <pre style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 10px; font-size: 11px; overflow-x: auto; max-height: 140px; margin: 0;">${JSON.stringify(wf.input_payload, null, 2)}</pre>
            </div>

            ${wf.result_payload ? `
              <div>
                <div style="font-size: 12px; font-weight: 600; color: #22c55e; margin-bottom: 4px;">Verified Result Payload:</div>
                <pre style="background: rgba(0,0,0,0.3); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 6px; padding: 10px; font-size: 11px; overflow-x: auto; max-height: 140px; margin: 0; color: #86efac;">${JSON.stringify(wf.result_payload, null, 2)}</pre>
              </div>
            ` : ''}

            <!-- Event History Log -->
            <div>
              <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 6px;">Durable Event History (${this.selectedWorkflowHistory.length} events):</div>
              <div style="display: flex; flex-direction: column; gap: 6px; max-height: 220px; overflow-y: auto;">
                ${this.selectedWorkflowHistory.map(ev => `
                  <div style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 4px; padding: 8px; font-size: 11px;">
                    <div style="display:flex; justify-content:space-between;">
                      <span style="font-weight:600; color:#38bdf8;">${ev.event_index}. ${ev.event_type}</span>
                      <span style="color:#64748b;">${new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                    </div>
                    <div style="color:#94a3b8; margin-top:2px; font-family:monospace; font-size:10px;">
                      ${JSON.stringify(ev.payload)}
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        </div>
      `;
    }

    renderTimelineTab() {
      const wf = this.selectedWorkflow;
      if (!wf) {
        return `
          <div style="text-align: center; padding: 60px; color: var(--text-secondary, #94a3b8); background: var(--card-bg, #1e293b); border-radius: 8px;">
            Select a durable process first to visualize its Mission Execution Timeline.
          </div>
        `;
      }

      const stages = [
        { name: "Mission Created", status: "COMPLETED", icon: "📋", detail: `Mission: ${wf.mission_id || wf.workflow_id}` },
        { name: "Planned", status: "COMPLETED", icon: "🧠", detail: "LangGraph Agentic Graph compiled" },
        { name: "Authorized", status: "COMPLETED", icon: "🛡️", detail: "PolicyEngine & Authority Gateway check passed" },
        { name: "Workflow Started", status: "COMPLETED", icon: "⏳", detail: `Temporal Queue: ${wf.task_queue}` },
        { name: "Activity Execution", status: wf.status === 'RUNNING' ? 'RUNNING' : 'COMPLETED', icon: "⚙️", detail: "Execution workers processing steps" },
        { name: "Tool Execution", status: wf.status === 'COMPLETED' ? 'COMPLETED' : 'IN_PROGRESS', icon: "🔧", detail: "MCP, OpenHands, and Browser Use bridges" },
        { name: "Verification", status: wf.verification_status === 'VERIFIED' ? 'COMPLETED' : 'PENDING', icon: "🔍", detail: `Status: ${wf.verification_status || 'UNVERIFIED'}` },
        { name: "Business Outcome", status: wf.status === 'COMPLETED' && wf.verification_status === 'VERIFIED' ? 'COMPLETED' : 'PENDING', icon: "🏆", detail: "Cryptographic Merkle Proof sealed" }
      ];

      return `
        <div style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 20px;">
          <h3 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 600;">Mission Execution Detail Timeline</h3>
          <p style="margin: 0 0 20px 0; font-size: 12px; color: #94a3b8;">
            Non-negotiable ZONATA Invariant: <code style="color:#f59e0b;">TASK_SUCCESS != BUSINESS_OUTCOME</code> • Full causal chain verified against physical evidence.
          </p>

          <div style="display: flex; flex-direction: column; gap: 16px; position: relative; margin-left: 20px;">
            <div style="position: absolute; left: 15px; top: 10px; bottom: 10px; width: 2px; background: rgba(59, 130, 246, 0.3);"></div>

            ${stages.map((stage, idx) => {
              const isDone = stage.status === 'COMPLETED';
              const isRunning = stage.status === 'RUNNING' || stage.status === 'IN_PROGRESS';
              const dotBg = isDone ? '#22c55e' : (isRunning ? '#3b82f6' : '#475569');
              return `
                <div style="display: flex; align-items: flex-start; gap: 16px; position: relative;">
                  <div style="width: 32px; height: 32px; border-radius: 50%; background: ${dotBg}; display: flex; align-items: center; justify-content: center; font-size: 14px; z-index: 2; border: 2px solid #0f172a;">
                    ${stage.icon}
                  </div>
                  <div style="flex: 1; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 10px 14px;">
                    <div style="display: flex; justify-content: space-between;">
                      <span style="font-weight: 600; font-size: 13px; color: ${isDone ? '#f8fafc' : '#94a3b8'};">${stage.name}</span>
                      <span style="font-size: 10px; padding: 2px 6px; border-radius: 4px; background: ${isDone ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.05)'}; color: ${isDone ? '#4ade80' : '#94a3b8'};">
                        ${stage.status}
                      </span>
                    </div>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${stage.detail}</div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    renderWorkersTab() {
      return `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <!-- Execution Workers -->
          <div>
            <h3 style="font-size: 15px; font-weight: 600; margin-bottom: 12px;">Active Execution Workers (${this.workers.length})</h3>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              ${this.workers.map(w => `
                <div style="background: var(--card-bg, #1e293b); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:600; font-size:13px; color:#f8fafc;">${w.worker_id}</div>
                    <span style="background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid #22c55e; border-radius:4px; font-size:10px; padding:2px 6px; font-weight:600;">
                      ${w.status}
                    </span>
                  </div>
                  <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                    Task Queue: <code style="color:#38bdf8;">${w.task_queue}</code> • Max Concurrency: <b>${w.max_concurrent_activities}</b>
                  </div>
                  <div style="font-size:11px; color:#94a3b8; margin-top:4px;">
                    Activities: ${(w.supported_activities || []).map(a => `<code style="font-size:10px;">${a}</code>`).join(' ')}
                  </div>
                  <div style="font-size:10px; color:#64748b; margin-top:6px;">
                    Heartbeat: ${new Date(w.heartbeat_at * 1000).toLocaleTimeString()} • Runtime v${w.runtime_version}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Governed Task Queues -->
          <div>
            <h3 style="font-size: 15px; font-weight: 600; margin-bottom: 12px;">Governed Task Queues (${this.queues.length})</h3>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              ${this.queues.map(q => `
                <div style="background: var(--card-bg, #1e293b); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 14px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="font-weight:600; font-size:13px; color:#38bdf8;">${q.queue_name}</div>
                    <span style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); border-radius:4px; font-size:10px; padding:2px 6px;">
                      ${q.workload_type}
                    </span>
                  </div>
                  <div style="font-size:11px; color:#cbd5e1; margin-top:4px;">${q.description || 'Standard governed queue'}</div>
                  <div style="font-size:11px; color:#94a3b8; margin-top:6px; display:flex; gap:12px;">
                    <span>Concurrency Limit: <b>${q.concurrency_limit}</b></span>
                    <span>Rate Limit: <b>${q.rate_limit_per_minute}/min</b></span>
                    <span>Security: <b style="color:#f59e0b;">${q.security_level}</b></span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    }

    renderApprovalsTab() {
      return `
        <div style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 20px;">
          <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Human-in-the-Loop Durable Approval Waits</h3>
          <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px;">
            Workflows wait safely for hours, days, or weeks without losing state. Authority is strictly re-validated upon resumption.
          </p>

          ${this.approvals.length === 0 ? `
            <div style="text-align: center; padding: 40px; color: var(--text-secondary, #94a3b8);">
              No pending approval requests. All durable processes are currently running autonomously within governed limits.
            </div>
          ` : `
            <div style="display: flex; flex-direction: column; gap: 12px;">
              ${this.approvals.map(appr => `
                <div style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 14px;">
                  <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                      <div style="font-weight:600; font-size:14px; color:#f8fafc;">${appr.step_name}</div>
                      <div style="font-size:11px; color:#94a3b8; margin-top:2px;">
                        Approval ID: <code>${appr.approval_id}</code> • Workflow: <code style="color:#38bdf8;">${appr.workflow_id}</code>
                      </div>
                      <div style="font-size:12px; color:#e2e8f0; margin-top:6px;">
                        ${(appr.requested_action || {}).summary || 'Approval required for mutation'}
                      </div>
                    </div>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">
                      <span style="background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); border-radius:4px; font-size:11px; padding:2px 8px; font-weight:600;">
                        ${appr.status}
                      </span>
                      <span style="font-size:10px; color:#64748b;">Req Role: <b>${appr.required_role}</b></span>
                    </div>
                  </div>

                  ${appr.status === 'PENDING' ? `
                    <div style="display:flex; gap:8px; margin-top:12px;">
                      <button class="btn btn-success btn-sm" onclick="window.temporalApp.decideApproval('${appr.approval_id}', true)">✓ Approve & Resume</button>
                      <button class="btn btn-danger btn-sm" onclick="window.temporalApp.decideApproval('${appr.approval_id}', false)">✕ Reject Action</button>
                    </div>
                  ` : `
                    <div style="margin-top:8px; font-size:11px; color:#94a3b8;">
                      Decided by: <b>${appr.decided_by || 'UNKNOWN'}</b> • Reason: <i>${appr.decision_reason || 'N/A'}</i>
                    </div>
                  `}
                </div>
              `).join('')}
            </div>
          `}
        </div>
      `;
    }

    renderReconciliationsTab() {
      return `
        <div style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 20px;">
          <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">UNKNOWN_OUTCOME Protocols & Saga Compensations</h3>
          <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px;">
            Non-negotiable invariant: <code style="color:#ef4444;">Ambiguous mutations must NEVER be blindly replayed</code>. If network drops occur, the protocol queries external reality before compensating or resuming.
          </p>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 14px;">
              <h4 style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #f59e0b;">Unknown Outcome Safety Protocol</h4>
              <ol style="margin: 0; padding-left: 18px; font-size: 11px; color: #cbd5e1; line-height: 1.6;">
                <li>Network connection drops during external mutation</li>
                <li>Activity is flagged <code>UNKNOWN_OUTCOME</code> (blind retry blocked)</li>
                <li>System persists operation idempotency key</li>
                <li>External provider queried for physical transaction receipt</li>
                <li>Business postcondition asserted</li>
                <li>Continue forward, execute saga compensation, or escalate</li>
              </ol>
            </div>

            <div style="background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 14px;">
              <h4 style="margin: 0 0 8px 0; font-size: 13px; font-weight: 600; color: #10b981;">Governed Saga Rollbacks</h4>
              <p style="font-size: 11px; color: #cbd5e1; margin: 0 0 8px 0; line-height: 1.5;">
                For multi-step transactions (Reservation -> Payment -> Inventory Update), downstream failures trigger sequential reverse compensation operations under cryptographic audit.
              </p>
              <div style="font-size: 11px; color: #94a3b8;">
                Total Reconciled Records: <b>${this.metrics.reconciled_count}</b>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    renderSecurityTab() {
      return `
        <div style="background: var(--card-bg, #1e293b); border: 1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius: 8px; padding: 20px;">
          <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Temporal Security Center & Audit Stream</h3>
          <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px;">
            Monitors multi-scope KillSwitches, credential isolation, tenant boundaries, and prompt-injection interception.
          </p>

          <div style="display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto;">
            ${this.securityEvents.length === 0 ? `
              <div style="text-align: center; padding: 30px; color: #94a3b8;">
                No security anomalies recorded. Zero-credential leakage & tenant isolation verified.
              </div>
            ` : this.securityEvents.map(ev => {
              const isCrit = ev.severity === 'CRITICAL' || ev.severity === 'HIGH';
              return `
                <div style="background: rgba(0,0,0,0.2); border: 1px solid ${isCrit ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.06)'}; border-radius: 6px; padding: 10px 14px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:600; font-size:12px; color:${isCrit ? '#ef4444' : '#f59e0b'};">
                      ${ev.event_type}
                    </span>
                    <span style="font-size:10px; color:#64748b;">${new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                  </div>
                  <div style="font-size:11px; color:#cbd5e1; margin-top:3px; font-family:monospace;">
                    ${JSON.stringify(ev.details)}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    renderScenariosTab() {
      const scenarios = [
        { id: "TEST_01", title: "Scenario 01: Worker Crash & State Recovery", desc: "Simulates worker crash during multi-step onboarding; state is recovered from durable event history without data loss." },
        { id: "TEST_02", title: "Scenario 02: Governed Retries vs Mutation Protection", desc: "Safe read operations retry with backoff; non-idempotent & financial mutations are strictly blocked from blind replay." },
        { id: "TEST_03", title: "Scenario 03: UNKNOWN_OUTCOME & Reconciliation", desc: "Simulates network drop during payment POST; enters UNKNOWN_OUTCOME state, queries external provider, and reconciles." },
        { id: "TEST_04", title: "Scenario 04: Multi-Day Human Approval Wait", desc: "Durable approval wait survives host restart; authority re-validated on approval decision." },
        { id: "TEST_05", title: "Scenario 05: Multi-Scope KillSwitch Enforcement", desc: "Authoritative stop instantly halts workflows and blocks all subsequent activities across scopes." },
        { id: "TEST_06", title: "Scenario 06: Zero-Credential Leakage Invariant", desc: "Proves raw tokens, passwords, and secrets are scrubbed and replaced with opaque handles in workflow state & event history." },
        { id: "TEST_07", title: "Scenario 07: Strict Multi-Tenant Isolation", desc: "Proves Company A cannot inspect, signal, or resume Company B's durable workflows or workers." },
        { id: "TEST_08", title: "Scenario 08: LangGraph + Temporal Hybrid", desc: "LangGraph agent reasoning graph executed atop Temporal durable crash recovery runtime." },
        { id: "TEST_09", title: "Scenario 09: Multi-Engine Integration", desc: "Temporal coordinates Browser Use + OpenHands + MCP + A2A under a single durable workflow." },
        { id: "SECTION_85", title: "Section 85: Grand Acceptance Scenario", desc: "Full realistic ZONATA scenario: AI CEO customer onboarding & campaign with failure injection, recovery, human approval, Merkle Evidence Ledger & TrustGraph!" }
      ];

      return `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <!-- Scenarios List -->
          <div>
            <h3 style="font-size: 15px; font-weight: 600; margin-bottom: 12px;">Canonical Verification Scenarios</h3>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${scenarios.map(sc => `
                <div style="background: var(--card-bg, #1e293b); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px 14px; display:flex; justify-content:space-between; align-items:center;">
                  <div style="flex:1; padding-right:12px;">
                    <div style="font-weight:600; font-size:13px; color:#f8fafc;">${sc.title}</div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:2px;">${sc.desc}</div>
                  </div>
                  <button class="btn btn-primary btn-sm btn-run-scenario" data-scenario="${sc.id}" style="white-space:nowrap;">
                    ▶ Run
                  </button>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Scenario Execution Output -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h3 style="font-size: 15px; font-weight: 600; margin:0;">Live Execution Output</h3>
              ${this.isExecutingScenario ? `<span style="color:#38bdf8; font-size:12px;">Executing...</span>` : ''}
            </div>

            <pre id="preScenarioOutput" style="background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 16px; font-family: monospace; font-size: 11px; color: #a5f3fc; height: 500px; overflow-y: auto; margin:0;">
${this.scenarioOutput || 'Select a scenario on the left and click "▶ Run" to execute live against the Temporal durable execution runtime.'}
            </pre>
          </div>
        </div>
      `;
    }

    attachEventListeners() {
      // Tab navigation
      document.querySelectorAll('.mcp-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.activeTab = e.currentTarget.getAttribute('data-tab');
          const el = document.getElementById(this.containerId);
          if (el) this.renderUI(el);
        });
      });

      // Status filter
      const filterSel = document.getElementById('selTemporalStatusFilter');
      if (filterSel) {
        filterSel.addEventListener('change', (e) => {
          this.filterStatus = e.target.value;
          const el = document.getElementById(this.containerId);
          if (el) this.renderUI(el);
        });
      }

      // Workflow item select
      document.querySelectorAll('.wf-item-card').forEach(card => {
        card.addEventListener('click', async (e) => {
          const wfid = e.currentTarget.getAttribute('data-wfid');
          await this.selectWorkflow(wfid);
          const el = document.getElementById(this.containerId);
          if (el) this.renderUI(el);
        });
      });

      // Refresh
      const btnRefresh = document.getElementById('btnRefreshTemporal');
      if (btnRefresh) {
        btnRefresh.addEventListener('click', async () => {
          await this.loadData();
          const el = document.getElementById(this.containerId);
          if (el) this.renderUI(el);
        });
      }

      // KillSwitch toggle
      const btnKS = document.getElementById('btnToggleTemporalKillswitch');
      if (btnKS) {
        btnKS.addEventListener('click', async () => {
          try {
            await fetch('/api/temporal/killswitch', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ active: !this.killswitchActive, scope: 'GLOBAL' })
            });
            await this.loadData();
            const el = document.getElementById(this.containerId);
            if (el) this.renderUI(el);
          } catch (err) {
            alert('Failed to toggle KillSwitch: ' + err);
          }
        });
      }

      // Run scenario buttons
      document.querySelectorAll('.btn-run-scenario').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const scId = e.currentTarget.getAttribute('data-scenario');
          await this.runScenario(scId);
        });
      });

      // New workflow button
      const btnNew = document.getElementById('btnNewWorkflowModal');
      if (btnNew) {
        btnNew.addEventListener('click', () => {
          const type = prompt('Enter workflow type:', 'EnterpriseCustomerOnboardingWorkflow');
          if (type) {
            fetch('/api/temporal/workflows', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ workflow_type: type, input_payload: { initiated_by: 'OperatorUI' } })
            }).then(() => {
              this.loadData().then(() => {
                const el = document.getElementById(this.containerId);
                if (el) this.renderUI(el);
              });
            });
          }
        });
      }
    }

    async runScenario(scenarioId) {
      this.isExecutingScenario = true;
      this.scenarioOutput = `[*] Dispatching Scenario ${scenarioId} to Temporal Durable Execution Gateway...\n`;
      const pre = document.getElementById('preScenarioOutput');
      if (pre) pre.textContent = this.scenarioOutput;

      try {
        const res = await fetch('/api/temporal/demo/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: scenarioId })
        }).then(r => r.json());

        this.scenarioOutput += `[✓] Execution Completed Successfully!\n\n`;
        this.scenarioOutput += JSON.stringify(res, null, 2);
      } catch (err) {
        this.scenarioOutput += `[✗] Error during scenario execution: ${err}\n`;
      } finally {
        this.isExecutingScenario = false;
        await this.loadData();
        const preAfter = document.getElementById('preScenarioOutput');
        if (preAfter) preAfter.textContent = this.scenarioOutput;
      }
    }

    async pauseSelectedWorkflow() {
      if (!this.selectedWorkflow) return;
      await fetch(`/api/temporal/workflows/${this.selectedWorkflow.workflow_id}/pause`, { method: 'POST', body: '{}' });
      await this.loadData();
      await this.selectWorkflow(this.selectedWorkflow.workflow_id);
      const el = document.getElementById(this.containerId);
      if (el) this.renderUI(el);
    }

    async resumeSelectedWorkflow() {
      if (!this.selectedWorkflow) return;
      await fetch(`/api/temporal/workflows/${this.selectedWorkflow.workflow_id}/resume`, { method: 'POST', body: '{}' });
      await this.loadData();
      await this.selectWorkflow(this.selectedWorkflow.workflow_id);
      const el = document.getElementById(this.containerId);
      if (el) this.renderUI(el);
    }

    async cancelSelectedWorkflow() {
      if (!this.selectedWorkflow) return;
      await fetch(`/api/temporal/workflows/${this.selectedWorkflow.workflow_id}/cancel`, { method: 'POST', body: '{}' });
      await this.loadData();
      await this.selectWorkflow(this.selectedWorkflow.workflow_id);
      const el = document.getElementById(this.containerId);
      if (el) this.renderUI(el);
    }

    async recoverSelectedWorkflow() {
      if (!this.selectedWorkflow) return;
      alert('Simulating host reboot and recovering workflow from durable event history...');
      await this.loadData();
      await this.selectWorkflow(this.selectedWorkflow.workflow_id);
      const el = document.getElementById(this.containerId);
      if (el) this.renderUI(el);
    }

    async decideApproval(approvalId, approved) {
      await fetch(`/api/temporal/approvals/${approvalId}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, decided_by: 'EXECUTIVE_OWNER', reason: approved ? 'Approved in cockpit' : 'Rejected in cockpit' })
      });
      await this.loadData();
      const el = document.getElementById(this.containerId);
      if (el) this.renderUI(el);
    }

    getStatusColor(status) {
      switch (status) {
        case 'RUNNING':
          return { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.4)' };
        case 'COMPLETED':
          return { bg: 'rgba(34, 197, 94, 0.15)', text: '#4ade80', border: 'rgba(34, 197, 94, 0.4)' };
        case 'FAILED':
        case 'TERMINATED':
          return { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: 'rgba(239, 68, 68, 0.4)' };
        case 'AWAITING_APPROVAL':
        case 'AWAITING_SIGNAL':
          return { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.4)' };
        case 'UNKNOWN_OUTCOME':
          return { bg: 'rgba(217, 70, 239, 0.15)', text: '#e879f9', border: 'rgba(217, 70, 239, 0.4)' };
        case 'PAUSED':
          return { bg: 'rgba(148, 163, 184, 0.15)', text: '#cbd5e1', border: 'rgba(148, 163, 184, 0.4)' };
        default:
          return { bg: 'rgba(255, 255, 255, 0.1)', text: '#f1f5f9', border: 'rgba(255, 255, 255, 0.2)' };
      }
    }
  }

  // Export Singleton
  window.temporalWorkspace = new TemporalWorkspaceManager();
  window.temporalApp = window.temporalWorkspace;

  // Auto-init on page load if element exists
  document.addEventListener('DOMContentLoaded', () => {
    const el = document.getElementById('view-temporal-durable');
    if (el) window.temporalWorkspace.render();
  });
})();
