/**
 * ZONATA — Governed OpenHands Agent Execution Center
 * ===================================================
 * Project 07: Governed Autonomous Workspaces, Software Engineering,
 * and Computer-Operation Execution Layer.
 *
 * Core Capabilities:
 * - Active & Historical Executions Inspector
 * - Isolated Workspaces & Sandboxes Manager
 * - Governed Terminal & Shell Commands Audit
 * - Generated Artifacts, Code & Diffs Registry
 * - Human-in-the-Loop Approval Center
 * - Security Firewall & Threat Events Stream
 * - Canonical Scenarios (Tests 01-08) & Section 79 Acceptance Test Runner
 */

(function () {
  'use strict';

  class OpenHandsWorkspaceManager {
    constructor() {
      this.containerId = 'view-openhands-execution';
      this.activeTab = 'executions'; // 'executions', 'workspaces', 'commands', 'artifacts', 'approvals', 'security', 'scenarios'
      this.executions = [];
      this.workspaces = [];
      this.artifacts = [];
      this.securityEvents = [];
      this.approvals = [];
      this.metrics = {
        active_executions: 0,
        completed_executions: 0,
        failed_executions: 0,
        total_executions: 0,
        average_execution_time_ms: 0,
        verification_success_rate: 100,
        policy_blocks: 0,
        approval_requests: 0,
        active_workspaces: 0,
        artifacts_created: 0,
        security_events: 0,
        killswitch_active: false,
        has_activity: false
      };
      this.killswitchActive = false;
      this.selectedExecution = null;
      this.isExecutingScenario = false;
      this.scenarioOutput = null;
      this.filterStatus = 'ALL';
      this.searchQuery = '';
    }

    async render(containerId) {
      if (containerId) this.containerId = containerId;
      const el = document.getElementById(this.containerId);
      if (!el) return;

      el.innerHTML = `
        <div style="display:flex; justify-content:center; align-items:center; height:300px; color:var(--text-secondary);">
          <div style="text-align:center;">
            <div style="font-size:28px; margin-bottom:12px; animation:spin 1s linear infinite;">⚙️</div>
            <div style="font-weight:600; font-size:15px; color:var(--text-primary);">Loading Agent Execution Center (OpenHands)...</div>
            <div style="font-size:12px; margin-top:4px;">Synchronizing sandbox workspaces, command pipelines & verification ledgers</div>
          </div>
        </div>
      `;

      await this.loadData();
      this.renderUI(el);
    }

    async loadData() {
      try {
        const [execsRes, wsRes, artsRes, secRes, metricsRes, ksRes] = await Promise.all([
          fetch('/api/openhands/executions?limit=50').then(r => r.json()).catch(() => ({ executions: [] })),
          fetch('/api/openhands/workspaces?limit=50').then(r => r.json()).catch(() => ({ workspaces: [] })),
          fetch('/api/openhands/artifacts?limit=50').then(r => r.json()).catch(() => ({ artifacts: [] })),
          fetch('/api/openhands/security/events?limit=50').then(r => r.json()).catch(() => ({ security_events: [] })),
          fetch('/api/openhands/metrics').then(r => r.json()).catch(() => ({ metrics: {} })),
          fetch('/api/openhands/killswitch').then(r => r.json()).catch(() => ({ killswitch_active: false }))
        ]);

        this.executions = execsRes.executions || [];
        this.workspaces = wsRes.workspaces || [];
        this.artifacts = artsRes.artifacts || [];
        this.securityEvents = secRes.security_events || [];
        this.metrics = Object.assign(this.metrics, metricsRes.metrics || {});
        this.killswitchActive = !!ksRes.killswitch_active;
      } catch (err) {
        console.error('Failed to load OpenHands data:', err);
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
      this.attachEventListeners(container);
    }

    renderHeader() {
      const ksActive = this.killswitchActive;
      return `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px; margin-bottom:20px; border-bottom:1px solid var(--border-color, rgba(255,255,255,0.08)); padding-bottom:16px;">
          <div>
            <div style="display:flex; align-items:center; gap:10px;">
              <span style="font-size:24px;">🛠️</span>
              <h1 style="margin:0; font-size:22px; font-weight:700; letter-spacing:-0.5px;">Agent Execution Center</h1>
              <span style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); font-size:11px; font-weight:600; padding:2px 8px; border-radius:12px;">OpenHands Governed Runtime</span>
              <span style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); font-size:11px; font-weight:600; padding:2px 8px; border-radius:12px;">Isolated Sandboxes</span>
            </div>
            <p style="margin:6px 0 0 0; color:var(--text-secondary, #94a3b8); font-size:13px;">
              Governed workspace execution, software engineering automation, safe terminal commands, and independent physical verification under sovereign ZONATA authority.
            </p>
          </div>
          <div style="display:flex; align-items:center; gap:10px;">
            <button id="btn-oh-refresh" style="background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); color:#cbd5e1; padding:8px 14px; border-radius:8px; font-size:13px; font-weight:500; cursor:pointer; display:flex; align-items:center; gap:6px;">
              <span>🔄</span> Refresh
            </button>
            <button id="btn-oh-killswitch" style="background:${ksActive ? '#ef4444' : 'rgba(239,68,68,0.15)'}; color:${ksActive ? '#fff' : '#f87171'}; border:1px solid ${ksActive ? '#dc2626' : 'rgba(239,68,68,0.3)'}; padding:8px 14px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:6px;">
              <span>🛑</span> ${ksActive ? 'KILLSWITCH ENGAGED' : 'ARM KILLSWITCH'}
            </button>
          </div>
        </div>
      `;
    }

    renderMetricsBar() {
      const m = this.metrics;
      const ksActive = this.killswitchActive;
      return `
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:12px; margin-bottom:20px;">
          <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); padding:12px 14px; border-radius:10px;">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px;">Active Runs</div>
            <div style="font-size:22px; font-weight:700; color:#38bdf8; margin-top:4px;">${m.active_executions}</div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Currently in sandbox</div>
          </div>
          <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); padding:12px 14px; border-radius:10px;">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px;">Completed</div>
            <div style="font-size:22px; font-weight:700; color:#34d399; margin-top:4px;">${m.completed_executions}</div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Sealed & verified</div>
          </div>
          <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); padding:12px 14px; border-radius:10px;">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px;">Workspaces</div>
            <div style="font-size:22px; font-weight:700; color:#818cf8; margin-top:4px;">${m.active_workspaces}</div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Isolated sandboxes</div>
          </div>
          <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); padding:12px 14px; border-radius:10px;">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px;">Artifacts</div>
            <div style="font-size:22px; font-weight:700; color:#f59e0b; margin-top:4px;">${m.artifacts_created}</div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Scanned files & diffs</div>
          </div>
          <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); padding:12px 14px; border-radius:10px;">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px;">Verification Rate</div>
            <div style="font-size:22px; font-weight:700; color:#10b981; margin-top:4px;">${m.verification_success_rate}%</div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Physical reality checks</div>
          </div>
          <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); padding:12px 14px; border-radius:10px;">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px;">Threats Blocked</div>
            <div style="font-size:22px; font-weight:700; color:${m.security_events > 0 ? '#f43f5e' : '#94a3b8'}; margin-top:4px;">${m.security_events}</div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Firewall & path blocks</div>
          </div>
          <div style="background:rgba(15,23,42,0.6); border:1px solid ${ksActive ? '#ef4444' : 'var(--border-color, rgba(255,255,255,0.08))'}; padding:12px 14px; border-radius:10px;">
            <div style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px;">KillSwitch</div>
            <div style="font-size:16px; font-weight:700; color:${ksActive ? '#f87171' : '#10b981'}; margin-top:8px;">${ksActive ? 'ACTIVE' : 'READY'}</div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">Authoritative halt</div>
          </div>
        </div>
      `;
    }

    renderTabsNav() {
      const tabs = [
        { id: 'executions', label: 'Executions', count: this.executions.length, icon: '⚡' },
        { id: 'workspaces', label: 'Workspaces', count: this.workspaces.length, icon: '📁' },
        { id: 'artifacts', label: 'Artifacts', count: this.artifacts.length, icon: '📦' },
        { id: 'security', label: 'Security Center', count: this.securityEvents.length, icon: '🛡️' },
        { id: 'scenarios', label: 'Scenario Runner', count: 'Tests 01–08', icon: '🧪' }
      ];

      return `
        <div style="display:flex; gap:8px; border-bottom:1px solid var(--border-color, rgba(255,255,255,0.08)); padding-bottom:8px; overflow-x:auto;">
          ${tabs.map(t => {
            const isActive = this.activeTab === t.id;
            return `
              <button class="mcp-tab-btn ${isActive ? 'active' : ''}" data-tab="${t.id}" style="background:${isActive ? 'rgba(59,130,246,0.15)' : 'transparent'}; color:${isActive ? '#60a5fa' : '#94a3b8'}; border:1px solid ${isActive ? 'rgba(59,130,246,0.3)' : 'transparent'}; padding:8px 16px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:8px; white-space:nowrap;">
                <span>${t.icon}</span>
                <span>${t.label}</span>
                <span style="background:rgba(255,255,255,0.1); font-size:11px; padding:1px 6px; border-radius:10px; color:${isActive ? '#93c5fd' : '#64748b'};">${t.count}</span>
              </button>
            `;
          }).join('')}
        </div>
      `;
    }

    renderActiveTabContent() {
      switch (this.activeTab) {
        case 'executions':
          return this.renderExecutionsTab();
        case 'workspaces':
          return this.renderWorkspacesTab();
        case 'artifacts':
          return this.renderArtifactsTab();
        case 'security':
          return this.renderSecurityTab();
        case 'scenarios':
          return this.renderScenariosTab();
        default:
          return this.renderExecutionsTab();
      }
    }

    // -----------------------------------------------------------------------
    // TAB: EXECUTIONS
    // -----------------------------------------------------------------------
    renderExecutionsTab() {
      if (this.executions.length === 0) {
        return `
          <div style="text-align:center; padding:60px 20px; background:rgba(15,23,42,0.4); border:1px dashed var(--border-color, rgba(255,255,255,0.1)); border-radius:12px;">
            <div style="font-size:36px; margin-bottom:12px;">💻</div>
            <div style="font-size:16px; font-weight:600; color:#e2e8f0;">No OpenHands execution activity yet</div>
            <div style="font-size:13px; color:#94a3b8; max-width:480px; margin:8px auto 20px;">
              Executions will appear here when an agent is dispatched to write code, modify files, run tests, or execute terminal commands in a sandboxed workspace.
            </div>
            <button class="btn-run-scenario" data-scenario="TEST_01" style="background:#2563eb; color:#fff; border:none; padding:8px 16px; border-radius:8px; font-size:13px; font-weight:600; cursor:pointer;">
              Run Test 01 (Software Task)
            </button>
          </div>
        `;
      }

      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.executions.map(ex => {
            const isCompleted = ex.execution_status === 'COMPLETED';
            const isRunning = ex.execution_status === 'RUNNING';
            const isWaiting = ex.execution_status === 'WAITING';
            const isFailed = ['FAILED', 'DENIED', 'TERMINATED', 'CANCELLED', 'VERIFICATION_FAILED'].includes(ex.execution_status);
            const badgeBg = isCompleted ? 'rgba(16,185,129,0.15)' : isRunning ? 'rgba(56,189,248,0.15)' : isWaiting ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)';
            const badgeColor = isCompleted ? '#34d399' : isRunning ? '#38bdf8' : isWaiting ? '#fbbf24' : '#f87171';
            const files = ex.files_changed ? JSON.parse(ex.files_changed) : [];

            return `
              <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:10px; padding:16px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:10px;">
                  <div>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <span style="font-weight:700; font-size:15px; color:#f8fafc;">${ex.execution_id}</span>
                      <span style="background:${badgeBg}; color:${badgeColor}; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px;">${ex.execution_status}</span>
                      <span style="font-size:12px; color:#94a3b8;">Agent: <b>${ex.agent_id}</b></span>
                    </div>
                    <div style="margin-top:6px; font-size:13px; color:#cbd5e1; font-family:monospace; background:rgba(0,0,0,0.2); padding:6px 10px; border-radius:6px; max-width:800px;">
                      ${ex.task_prompt}
                    </div>
                  </div>
                  <div style="display:flex; gap:8px;">
                    ${isRunning ? `
                      <button class="btn-cancel-exec" data-id="${ex.execution_id}" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3); padding:4px 10px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer;">Cancel</button>
                    ` : ''}
                  </div>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:16px; margin-top:12px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.05); font-size:12px; color:#94a3b8;">
                  <div>Workspace: <b style="color:#e2e8f0;">${ex.workspace_id}</b></div>
                  <div>Files Modified: <b style="color:#e2e8f0;">${files.length}</b></div>
                  <div>Tests Passed: <b style="color:#34d399;">${ex.tests_passed || 0}</b></div>
                  <div>Verification: <b style="color:${ex.verification_status === 'VERIFIED' ? '#34d399' : '#f87171'};">${ex.verification_status}</b></div>
                  ${ex.evidence_id ? `<div>Evidence: <span style="font-family:monospace; color:#38bdf8;">${ex.evidence_id}</span></div>` : ''}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    // -----------------------------------------------------------------------
    // TAB: WORKSPACES
    // -----------------------------------------------------------------------
    renderWorkspacesTab() {
      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.workspaces.map(ws => `
            <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:10px; padding:16px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:10px;">
                  <span style="font-size:18px;">📁</span>
                  <div>
                    <span style="font-weight:700; font-size:14px; color:#f8fafc;">${ws.workspace_id}</span>
                    <span style="background:rgba(99,102,241,0.15); color:#818cf8; font-size:11px; font-weight:600; padding:2px 8px; border-radius:10px; margin-left:8px;">${ws.workspace_class}</span>
                    <span style="background:rgba(16,185,129,0.15); color:#34d399; font-size:11px; font-weight:600; padding:2px 8px; border-radius:10px; margin-left:4px;">${ws.status}</span>
                  </div>
                </div>
                <span style="font-size:12px; color:#94a3b8;">Network: <b>${ws.network_scope}</b></span>
              </div>
              <div style="margin-top:10px; font-family:monospace; font-size:12px; color:#94a3b8; background:rgba(0,0,0,0.2); padding:6px 10px; border-radius:6px;">
                Path: ${ws.path}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // -----------------------------------------------------------------------
    // TAB: ARTIFACTS
    // -----------------------------------------------------------------------
    renderArtifactsTab() {
      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.artifacts.length === 0 ? `
            <div style="text-align:center; padding:40px 20px; color:#94a3b8; font-size:14px;">No artifacts produced yet. Run an execution or test scenario.</div>
          ` : this.artifacts.map(art => `
            <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:10px; padding:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span style="font-size:16px;">📄</span>
                  <span style="font-weight:700; font-size:14px; color:#f8fafc;">${art.name}</span>
                  <span style="background:rgba(245,158,11,0.15); color:#fbbf24; font-size:11px; font-weight:600; padding:2px 6px; border-radius:8px;">${art.artifact_type}</span>
                </div>
                <span style="font-size:11px; color:#34d399; font-weight:600;">VERIFIED HASH</span>
              </div>
              <div style="margin-top:8px; font-size:11px; color:#64748b; font-family:monospace;">
                SHA256: ${art.sha256_digest} | Size: ${art.size_bytes} bytes
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // -----------------------------------------------------------------------
    // TAB: SECURITY CENTER
    // -----------------------------------------------------------------------
    renderSecurityTab() {
      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.securityEvents.length === 0 ? `
            <div style="text-align:center; padding:40px 20px; color:#34d399; font-size:14px;">
              🛡️ Zero security violations recorded. Path traversals, prompt injections, and forbidden commands are actively blocked.
            </div>
          ` : this.securityEvents.map(ev => `
            <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:10px; padding:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#f87171; font-weight:700; font-size:13px;">🚨 ${ev.event_type}</span>
                <span style="color:#cbd5e1; font-size:11px;">Severity: <b>${ev.severity}</b></span>
              </div>
              <div style="margin-top:6px; font-size:12px; color:#e2e8f0; font-family:monospace;">
                ${typeof ev.details === 'string' ? ev.details : JSON.stringify(ev.details)}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // -----------------------------------------------------------------------
    // TAB: SCENARIOS (Tests 01 to 08 & Section 79 Acceptance Test)
    // -----------------------------------------------------------------------
    renderScenariosTab() {
      const scenarios = [
        { id: 'TEST_01', name: 'Test 01 — Software Engineering Task', desc: 'Inspect code, modify, run unit tests, verify pass, seal Merkle evidence.' },
        { id: 'TEST_02', name: 'Test 02 — MCP + OpenHands Tool Interoperability', desc: 'OpenHands invokes governed MCP tool via MCP Gateway and saves output artifact.' },
        { id: 'TEST_03', name: 'Test 03 — Human-in-the-Loop Approval', desc: 'Destructive command blocked, requires human admin approval before execution.' },
        { id: 'TEST_04', name: 'Test 04 — Authoritative KillSwitch Stop', desc: 'KillSwitch triggers instantaneous abort on running workspace execution.' },
        { id: 'TEST_05', name: 'Test 05 — Malicious Repository Defense', desc: 'Untrusted repository prompt injection attempt detected and blocked by Context Firewall.' },
        { id: 'TEST_06', name: 'Test 06 — Unknown Mutation Reconciliation', desc: 'Network failure during mutation sets RECONCILIATION_REQUIRED, preventing blind retries.' },
        { id: 'TEST_07', name: 'Test 07 — Multi-Tenant Sandbox Isolation', desc: 'Tenant A blocked from accessing Tenant B workspace or traversing path boundaries.' },
        { id: 'TEST_08', name: 'Test 08 — Self-Improvement Development Branch', desc: 'ZONATA self-upgrade staged in dev branch workspace; direct production overwrite blocked.' },
        { id: 'SECTION_79', name: 'Section 79 — Grand Enterprise Acceptance Test', desc: 'Complete 15-stage end-to-end pipeline: CEO -> Swarm -> LangGraph -> OpenHands -> MCP -> Verification -> Evidence -> Outcome.' }
      ];

      return `
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; align-items:start;">
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div style="font-weight:700; font-size:14px; color:#e2e8f0; margin-bottom:4px;">Select Test Scenario</div>
            ${scenarios.map(sc => `
              <div style="background:rgba(15,23,42,0.6); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                  <div style="font-weight:600; font-size:13px; color:#f8fafc;">${sc.name}</div>
                  <div style="font-size:11px; color:#94a3b8; margin-top:2px;">${sc.desc}</div>
                </div>
                <button class="btn-run-scenario" data-scenario="${sc.id}" style="background:rgba(59,130,246,0.2); color:#60a5fa; border:1px solid rgba(59,130,246,0.4); padding:6px 12px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; white-space:nowrap; margin-left:12px;">
                  Run Test
                </button>
              </div>
            `).join('')}
          </div>

          <div style="background:#0f172a; border:1px solid var(--border-color, rgba(255,255,255,0.1)); border-radius:10px; padding:16px; min-height:400px; display:flex; flex-direction:column;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:8px; margin-bottom:12px;">
              <span style="font-size:13px; font-weight:700; color:#cbd5e1;">Live Execution Output Console</span>
              ${this.isExecutingScenario ? '<span style="font-size:11px; color:#38bdf8; animation:pulse 1s infinite;">● Running Scenario...</span>' : ''}
            </div>
            <pre id="oh-scenario-console" style="margin:0; flex:1; font-family:'Fira Code', monospace; font-size:12px; color:#94a3b8; overflow:auto; max-height:420px; white-space:pre-wrap; word-break:break-all;">
${this.scenarioOutput ? JSON.stringify(this.scenarioOutput, null, 2) : '// Select a scenario on the left to execute live inside the OpenHands runtime...'}
            </pre>
          </div>
        </div>
      `;
    }

    attachEventListeners(container) {
      // Tab switching
      container.querySelectorAll('.mcp-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.activeTab = btn.getAttribute('data-tab');
          this.renderUI(container);
        });
      });

      // Refresh button
      const btnRefresh = container.querySelector('#btn-oh-refresh');
      if (btnRefresh) {
        btnRefresh.addEventListener('click', async () => {
          btnRefresh.disabled = true;
          btnRefresh.innerHTML = '<span>⏳</span> Refreshing...';
          await this.loadData();
          this.renderUI(container);
        });
      }

      // KillSwitch toggle
      const btnKs = container.querySelector('#btn-oh-killswitch');
      if (btnKs) {
        btnKs.addEventListener('click', async () => {
          const nextActive = !this.killswitchActive;
          try {
            await fetch('/api/openhands/killswitch', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ active: nextActive, scope: 'GLOBAL' })
            });
            await this.loadData();
            this.renderUI(container);
          } catch (e) {
            alert('Failed to toggle KillSwitch: ' + e.message);
          }
        });
      }

      // Run scenario buttons
      container.querySelectorAll('.btn-run-scenario').forEach(btn => {
        btn.addEventListener('click', async () => {
          const scId = btn.getAttribute('data-scenario');
          this.isExecutingScenario = true;
          this.scenarioOutput = { status: 'RUNNING', scenario: scId, message: 'Initiating governed OpenHands execution...' };
          this.renderUI(container);

          try {
            const res = await fetch('/api/openhands/demo/scenarios', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ scenario: scId })
            }).then(r => r.json());
            this.scenarioOutput = res;
          } catch (err) {
            this.scenarioOutput = { error: err.message };
          } finally {
            this.isExecutingScenario = false;
            await this.loadData();
            this.renderUI(container);
          }
        });
      });
    }
  }

  // Register in global window
  window.OpenHandsWorkspaceManager = OpenHandsWorkspaceManager;
  window.openhandsWorkspace = new OpenHandsWorkspaceManager();
})();
