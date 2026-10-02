/**
 * ZONATA — Governed Browser Use Execution Cockpit
 * ===================================================
 * Project 08: Governed Autonomous Browser & Web-Computer Execution Layer.
 *
 * Core Capabilities:
 * - Active & Historical Browser Executions Inspector
 * - Browser Sessions & Multi-Profile Manager (Ephemeral, Authenticated, Read-Only)
 * - Governed Browser Actions & Viewport Audit Trail
 * - Generated Artifacts, Screenshots & DOM Snapshot Registry
 * - Human-in-the-Loop Financial Mutation Approval Center
 * - Security Firewall: SSRF Defense, Prompt Injection Neutralization & Threat Stream
 * - Canonical Scenarios (Tests 01-09) & Section 80 Grand Acceptance Test Runner
 */

(function () {
  'use strict';

  class BrowserWorkspaceManager {
    constructor() {
      this.containerId = 'view-browser-execution';
      this.activeTab = 'executions'; // 'executions', 'sessions', 'actions', 'artifacts', 'approvals', 'security', 'scenarios'
      this.executions = [];
      this.sessions = [];
      this.artifacts = [];
      this.securityEvents = [];
      this.approvals = [];
      this.selectedExecution = null;
      this.selectedExecutionActions = [];
      this.metrics = {
        active_sessions: 0,
        total_executions: 0,
        completed_executions: 0,
        failed_executions: 0,
        awaiting_approval: 0,
        blocked_operations: 0,
        verification_success_rate: 100,
        unknown_outcomes: 0,
        approved_domains: 5,
        security_events: 0,
        killswitch_active: false,
        has_activity: false
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
            <div style="font-size:28px; margin-bottom:12px; animation:spin 1s linear infinite;">🌐</div>
            <div style="font-weight:600; font-size:15px; color:var(--text-primary);">Loading Governed Browser Execution Layer...</div>
            <div style="font-size:12px; margin-top:4px;">Connecting browser sessions, Playwright sandbox, and Merkle verification ledger</div>
          </div>
        </div>
      `;

      await this.loadData();
      this.renderUI(el);
    }

    async loadData() {
      try {
        const [execsRes, sessRes, artsRes, secRes, apprRes, metricsRes, ksRes] = await Promise.all([
          fetch('/api/browser/executions?limit=50').then(r => r.json()).catch(() => ({ executions: [] })),
          fetch('/api/browser/sessions?limit=50').then(r => r.json()).catch(() => ({ sessions: [] })),
          fetch('/api/browser/artifacts?limit=50').then(r => r.json()).catch(() => ({ artifacts: [] })),
          fetch('/api/browser/security/events?limit=50').then(r => r.json()).catch(() => ({ security_events: [] })),
          fetch('/api/browser/approvals?limit=50').then(r => r.json()).catch(() => ({ approvals: [] })),
          fetch('/api/browser/metrics').then(r => r.json()).catch(() => ({ metrics: {} })),
          fetch('/api/browser/killswitch').then(r => r.json()).catch(() => ({ killswitch_active: false }))
        ]);

        this.executions = execsRes.executions || [];
        this.sessions = sessRes.sessions || [];
        this.artifacts = artsRes.artifacts || [];
        this.securityEvents = secRes.security_events || [];
        this.approvals = apprRes.approvals || [];
        this.metrics = Object.assign(this.metrics, metricsRes.metrics || {});
        this.killswitchActive = !!ksRes.killswitch_active;
      } catch (err) {
        console.error('Failed to load Browser Use data:', err);
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
              <span style="font-size:24px;">🌐</span>
              <h1 style="margin:0; font-size:22px; font-weight:700; letter-spacing:-0.5px;">Governed Browser Use Cockpit</h1>
              <span style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); font-size:11px; font-weight:600; padding:2px 8px; border-radius:12px;">Browser Use Runtime</span>
              <span style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); font-size:11px; font-weight:600; padding:2px 8px; border-radius:12px;">Merkle Sealed</span>
            </div>
            <p style="margin:6px 0 0 0; color:var(--text-secondary, #94a3b8); font-size:13px;">
              Governed real-browser execution, DOM inspection, navigation, multi-tab workflows, and prompt injection defense subordinate to sovereign ZONATA authority.
            </p>
          </div>
          <div style="display:flex; gap:10px; align-items:center;">
            <button id="btnBrowserKillSwitch" style="background:${ksActive ? '#ef4444' : 'rgba(239,68,68,0.15)'}; color:${ksActive ? '#ffffff' : '#f87171'}; border:1px solid #ef4444; border-radius:6px; padding:8px 14px; font-size:12px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:6px;">
              <span>🚨</span> ${ksActive ? 'GLOBAL KILLSWITCH ENGAGED (RESET)' : 'ENGAGE BROWSER KILLSWITCH'}
            </button>
            <button id="btnBrowserRefresh" style="background:rgba(255,255,255,0.05); color:var(--text-primary, #e2e8f0); border:1px solid rgba(255,255,255,0.1); border-radius:6px; padding:8px 12px; font-size:12px; cursor:pointer;">
              🔄 Refresh
            </button>
          </div>
        </div>
      `;
    }

    renderMetricsBar() {
      const m = this.metrics;
      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:12px; margin-bottom:20px;">
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:12px 14px;">
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-secondary, #94a3b8); margin-bottom:4px;">Active Sessions</div>
            <div style="font-size:20px; font-weight:700; color:#38bdf8;">${m.active_sessions || 0}</div>
          </div>
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:12px 14px;">
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-secondary, #94a3b8); margin-bottom:4px;">Completed Runs</div>
            <div style="font-size:20px; font-weight:700; color:#34d399;">${m.completed_executions || 0}</div>
          </div>
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:12px 14px;">
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-secondary, #94a3b8); margin-bottom:4px;">Awaiting Approval</div>
            <div style="font-size:20px; font-weight:700; color:${m.awaiting_approval > 0 ? '#fbbf24' : '#94a3b8'};">${m.awaiting_approval || 0}</div>
          </div>
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:12px 14px;">
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-secondary, #94a3b8); margin-bottom:4px;">Threats Blocked</div>
            <div style="font-size:20px; font-weight:700; color:${m.blocked_operations > 0 ? '#f87171' : '#94a3b8'};">${m.blocked_operations || 0}</div>
          </div>
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:12px 14px;">
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-secondary, #94a3b8); margin-bottom:4px;">Verification Rate</div>
            <div style="font-size:20px; font-weight:700; color:#a78bfa;">${m.verification_success_rate || 100}%</div>
          </div>
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:12px 14px;">
            <div style="font-size:11px; font-weight:600; text-transform:uppercase; color:var(--text-secondary, #94a3b8); margin-bottom:4px;">Approved Domains</div>
            <div style="font-size:20px; font-weight:700; color:#38bdf8;">${m.approved_domains || 5}</div>
          </div>
        </div>
      `;
    }

    renderTabsNav() {
      const tabs = [
        { id: 'executions', label: 'Browser Executions', count: this.executions.length, icon: '⚡' },
        { id: 'sessions', label: 'Browser Sessions', count: this.sessions.length, icon: '🖥️' },
        { id: 'actions', label: 'Action Stream', count: this.selectedExecutionActions.length, icon: '🖱️' },
        { id: 'artifacts', label: 'Screenshots & Artifacts', count: this.artifacts.length, icon: '📸' },
        { id: 'approvals', label: 'Human Approvals', count: this.approvals.filter(a => a.status === 'PENDING').length, icon: '🛡️', alert: this.approvals.some(a => a.status === 'PENDING') },
        { id: 'security', label: 'Security Firewall', count: this.securityEvents.length, icon: '🔒' },
        { id: 'scenarios', label: 'Live Verification Suite', icon: '🧪' }
      ];

      return `
        <div style="display:flex; gap:6px; border-bottom:1px solid var(--border-color, rgba(255,255,255,0.08)); padding-bottom:8px; overflow-x:auto;">
          ${tabs.map(t => `
            <button class="browser-tab-btn" data-tab="${t.id}" style="background:${this.activeTab === t.id ? 'rgba(59,130,246,0.15)' : 'transparent'}; color:${this.activeTab === t.id ? '#60a5fa' : 'var(--text-secondary, #94a3b8)'}; border:${this.activeTab === t.id ? '1px solid rgba(59,130,246,0.4)' : '1px solid transparent'}; border-radius:6px; padding:8px 14px; font-size:13px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:6px; white-space:nowrap;">
              <span>${t.icon}</span> ${t.label}
              ${t.count !== undefined ? `<span style="background:${t.alert ? '#ef4444' : 'rgba(255,255,255,0.1)'}; color:${t.alert ? '#ffffff' : 'var(--text-primary)'}; font-size:11px; padding:1px 6px; border-radius:10px;">${t.count}</span>` : ''}
            </button>
          `).join('')}
        </div>
      `;
    }

    renderActiveTabContent() {
      switch (this.activeTab) {
        case 'executions': return this.renderExecutionsTab();
        case 'sessions': return this.renderSessionsTab();
        case 'actions': return this.renderActionsTab();
        case 'artifacts': return this.renderArtifactsTab();
        case 'approvals': return this.renderApprovalsTab();
        case 'security': return this.renderSecurityTab();
        case 'scenarios': return this.renderScenariosTab();
        default: return `<div>Tab not found</div>`;
      }
    }

    renderExecutionsTab() {
      if (!this.executions.length) {
        return `
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:40px; text-align:center;">
            <div style="font-size:36px; margin-bottom:12px; opacity:0.6;">🌐</div>
            <div style="font-size:16px; font-weight:600; color:var(--text-primary);">No Browser Executions Found</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Run a canonical scenario or dispatch an agent browser mission to begin.</div>
            <button id="btnQuickRunScenario" style="margin-top:16px; background:#2563eb; color:#ffffff; border:none; border-radius:6px; padding:8px 16px; font-size:13px; font-weight:600; cursor:pointer;">
              🧪 Run Read-Only Extraction Scenario (Test 01)
            </button>
          </div>
        `;
      }

      return `
        <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; overflow:hidden;">
          <table style="width:100%; border-collapse:collapse; font-size:13px; text-align:left;">
            <thead>
              <tr style="background:rgba(0,0,0,0.2); border-bottom:1px solid var(--border-color, rgba(255,255,255,0.08)); color:var(--text-secondary); font-size:11px; text-transform:uppercase;">
                <th style="padding:10px 14px;">Execution ID</th>
                <th style="padding:10px 14px;">Goal / Intent</th>
                <th style="padding:10px 14px;">Target URL</th>
                <th style="padding:10px 14px;">Status</th>
                <th style="padding:10px 14px;">Verification</th>
                <th style="padding:10px 14px;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this.executions.map(ex => {
                const isComplete = ex.execution_status === 'COMPLETE';
                const isFailed = ['DENIED', 'AUTH_FAILED', 'NAVIGATION_FAILED', 'ACTION_FAILED', 'VERIFICATION_FAILED'].includes(ex.execution_status);
                const statusColor = isComplete ? '#34d399' : (isFailed ? '#f87171' : '#38bdf8');
                return `
                  <tr style="border-bottom:1px solid rgba(255,255,255,0.04); hover:background:rgba(255,255,255,0.02);">
                    <td style="padding:12px 14px; font-family:monospace; font-size:12px; color:#60a5fa;">${ex.execution_id}</td>
                    <td style="padding:12px 14px; font-weight:600; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${ex.goal || 'Web navigation'}</td>
                    <td style="padding:12px 14px; font-family:monospace; font-size:11px; color:var(--text-secondary); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${ex.current_url || ex.initial_url || '—'}</td>
                    <td style="padding:12px 14px;">
                      <span style="background:${statusColor}22; color:${statusColor}; border:1px solid ${statusColor}44; font-size:11px; font-weight:600; padding:2px 8px; border-radius:12px;">
                        ${ex.execution_status}
                      </span>
                    </td>
                    <td style="padding:12px 14px;">
                      <span style="color:${ex.verification_status === 'VERIFIED' ? '#34d399' : '#94a3b8'}; font-size:12px; font-weight:600;">
                        ${ex.verification_status === 'VERIFIED' ? '✓ SEALED' : (ex.verification_status || 'PENDING')}
                      </span>
                    </td>
                    <td style="padding:12px 14px;">
                      <button class="btn-inspect-exec" data-id="${ex.execution_id}" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); border-radius:4px; padding:4px 10px; font-size:11px; cursor:pointer;">
                        View Steps →
                      </button>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    renderSessionsTab() {
      if (!this.sessions.length) {
        return `
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:40px; text-align:center;">
            <div style="font-size:36px; margin-bottom:12px; opacity:0.6;">🖥️</div>
            <div style="font-size:16px; font-weight:600; color:var(--text-primary);">No Active Browser Sessions</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Sessions are provisioned dynamically for isolated browsing tasks.</div>
          </div>
        `;
      }

      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:16px;">
          ${this.sessions.map(s => `
            <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:16px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-family:monospace; font-size:12px; color:#38bdf8;">${s.session_id}</span>
                <span style="background:${s.status === 'ACTIVE' ? 'rgba(52,211,153,0.15)' : 'rgba(148,163,184,0.15)'}; color:${s.status === 'ACTIVE' ? '#34d399' : '#94a3b8'}; border-radius:12px; font-size:11px; padding:2px 8px; font-weight:600;">${s.status}</span>
              </div>
              <div style="font-size:12px; color:var(--text-secondary); margin-bottom:6px;">
                Profile: <strong style="color:var(--text-primary);">${s.profile_type}</strong>
              </div>
              <div style="font-size:12px; color:var(--text-secondary); margin-bottom:6px;">
                Viewport: <strong style="color:var(--text-primary);">${s.viewport_width || 1280}x${s.viewport_height || 800}</strong>
              </div>
              <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">
                Browser Engine: <strong style="color:var(--text-primary);">${s.browser_type || 'chromium'}</strong>
              </div>
              ${s.status === 'ACTIVE' ? `
                <button class="btn-close-sess" data-id="${s.session_id}" style="width:100%; background:rgba(239,68,68,0.1); color:#f87171; border:1px solid rgba(239,68,68,0.3); border-radius:4px; padding:6px 0; font-size:12px; font-weight:600; cursor:pointer;">
                  Close Session
                </button>
              ` : ''}
            </div>
          `).join('')}
        </div>
      `;
    }

    renderActionsTab() {
      if (!this.selectedExecutionActions.length) {
        return `
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:40px; text-align:center;">
            <div style="font-size:36px; margin-bottom:12px; opacity:0.6;">🖱️</div>
            <div style="font-size:16px; font-weight:600; color:var(--text-primary);">No Actions Selected</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Select an execution from the Browser Executions tab to inspect its step-by-step audit trail.</div>
          </div>
        `;
      }

      return `
        <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:16px; margin-bottom:16px;">
          <h3 style="margin:0 0 12px 0; font-size:15px; font-weight:600;">Execution Action History: <span style="font-family:monospace; color:#38bdf8;">${this.selectedExecution}</span></h3>
          <div style="display:flex; flex-direction:column; gap:10px;">
            ${this.selectedExecutionActions.map(act => {
              const isHigh = act.risk_class === 'HIGH' || act.risk_class === 'FINANCIAL';
              const riskColor = isHigh ? '#f87171' : (act.risk_class === 'MEDIUM' ? '#fbbf24' : '#34d399');
              return `
                <div style="background:rgba(0,0,0,0.2); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:6px; padding:12px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                      <span style="font-weight:700; color:var(--text-primary); font-size:13px;">Step ${act.step_number}: ${act.action_type}</span>
                      <span style="background:${riskColor}22; color:${riskColor}; border:1px solid ${riskColor}44; font-size:10px; font-weight:700; padding:1px 6px; border-radius:10px;">${act.risk_class || 'READ_ONLY'}</span>
                    </div>
                    <span style="font-size:11px; color:var(--text-secondary); font-family:monospace;">${act.status}</span>
                  </div>
                  ${act.selector ? `<div style="font-family:monospace; font-size:11px; color:#94a3b8; margin-bottom:4px;">Selector: ${act.selector}</div>` : ''}
                  ${act.human_intent ? `<div style="font-size:12px; color:var(--text-secondary);">Intent: ${act.human_intent}</div>` : ''}
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    renderArtifactsTab() {
      if (!this.artifacts.length) {
        return `
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:40px; text-align:center;">
            <div style="font-size:36px; margin-bottom:12px; opacity:0.6;">📸</div>
            <div style="font-size:16px; font-weight:600; color:var(--text-primary);">No Browser Artifacts Captured</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Screenshots, DOM trees, and downloaded files will appear here automatically.</div>
          </div>
        `;
      }

      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:16px;">
          ${this.artifacts.map(art => `
            <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:14px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:11px; background:rgba(59,130,246,0.15); color:#60a5fa; padding:2px 6px; border-radius:4px; font-weight:600;">${art.artifact_type}</span>
                <span style="font-size:11px; color:var(--text-secondary);">${art.mime_type}</span>
              </div>
              <div style="font-weight:600; font-size:13px; margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${art.file_name}</div>
              <div style="font-family:monospace; font-size:10px; color:var(--text-secondary); margin-bottom:8px;">SHA: ${(art.sha256_hash || '').substring(0, 16)}...</div>
              <div style="font-size:11px; color:var(--text-secondary);">Size: ${Math.round((art.file_size_bytes || 0) / 1024)} KB</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    renderApprovalsTab() {
      const pending = this.approvals.filter(a => a.status === 'PENDING');
      if (!this.approvals.length) {
        return `
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:40px; text-align:center;">
            <div style="font-size:36px; margin-bottom:12px; opacity:0.6;">🛡️</div>
            <div style="font-size:16px; font-weight:600; color:var(--text-primary);">No High-Risk Approvals Requested</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Financial transactions, credential entries, and high-impact web mutations halt here for executive sign-off.</div>
          </div>
        `;
      }

      return `
        <div style="display:flex; flex-direction:column; gap:12px;">
          ${this.approvals.map(appr => {
            const isPending = appr.status === 'PENDING';
            return `
              <div style="background:var(--bg-secondary, #1e293b); border:1px solid ${isPending ? '#fbbf24' : 'var(--border-color, rgba(255,255,255,0.08))'}; border-radius:8px; padding:16px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                  <div>
                    <span style="background:${isPending ? 'rgba(251,191,36,0.15)' : 'rgba(52,211,153,0.15)'}; color:${isPending ? '#fbbf24' : '#34d399'}; border-radius:12px; font-size:11px; padding:2px 8px; font-weight:700;">
                      ${appr.status}
                    </span>
                    <span style="font-family:monospace; font-size:12px; color:#94a3b8; margin-left:8px;">${appr.approval_id}</span>
                  </div>
                  <span style="font-size:11px; color:var(--text-secondary);">Execution: ${appr.execution_id}</span>
                </div>
                <div style="font-weight:600; font-size:14px; margin-bottom:6px;">High-Risk Mutation Request</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">Reason: <em>${appr.mutation_reason || 'Autonomous agent requested financial or irreversible DOM mutation.'}</em></div>
                ${isPending ? `
                  <div style="display:flex; gap:10px;">
                    <button class="btn-approve-act" data-id="${appr.approval_id}" style="background:#10b981; color:#ffffff; border:none; border-radius:6px; padding:8px 16px; font-size:12px; font-weight:600; cursor:pointer;">
                      ✓ Authorize Mutation
                    </button>
                    <button class="btn-reject-act" data-id="${appr.approval_id}" style="background:#ef4444; color:#ffffff; border:none; border-radius:6px; padding:8px 16px; font-size:12px; font-weight:600; cursor:pointer;">
                      ✕ Reject & Abort
                    </button>
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    renderSecurityTab() {
      if (!this.securityEvents.length) {
        return `
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:40px; text-align:center;">
            <div style="font-size:36px; margin-bottom:12px; opacity:0.6;">🔒</div>
            <div style="font-size:16px; font-weight:600; color:var(--text-primary);">Zero Security Violations Detected</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">SSRF defenses, prompt injection scrubbers, and private subnet blocks are operational.</div>
          </div>
        `;
      }

      return `
        <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; overflow:hidden;">
          <table style="width:100%; border-collapse:collapse; font-size:13px; text-align:left;">
            <thead>
              <tr style="background:rgba(0,0,0,0.2); border-bottom:1px solid var(--border-color, rgba(255,255,255,0.08)); color:var(--text-secondary); font-size:11px; text-transform:uppercase;">
                <th style="padding:10px 14px;">Event ID</th>
                <th style="padding:10px 14px;">Event Type</th>
                <th style="padding:10px 14px;">Severity</th>
                <th style="padding:10px 14px;">Details</th>
              </tr>
            </thead>
            <tbody>
              ${this.securityEvents.map(evt => {
                const isCrit = evt.severity === 'CRITICAL' || evt.severity === 'HIGH';
                const sevColor = isCrit ? '#f87171' : '#fbbf24';
                const detailsStr = typeof evt.details === 'object' ? JSON.stringify(evt.details) : (evt.details || '—');
                return `
                  <tr style="border-bottom:1px solid rgba(255,255,255,0.04);">
                    <td style="padding:12px 14px; font-family:monospace; font-size:11px; color:#60a5fa;">${evt.event_id}</td>
                    <td style="padding:12px 14px; font-weight:600;">${evt.event_type}</td>
                    <td style="padding:12px 14px;">
                      <span style="background:${sevColor}22; color:${sevColor}; border:1px solid ${sevColor}44; font-size:10px; font-weight:700; padding:2px 8px; border-radius:10px;">
                        ${evt.severity}
                      </span>
                    </td>
                    <td style="padding:12px 14px; font-size:12px; color:var(--text-secondary); max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                      ${detailsStr}
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    renderScenariosTab() {
      const scenarios = [
        { id: 'TEST_01', name: 'Test 01: Information Extraction & Scrubbing', desc: 'Dispatches read-only session, extracts competitive pricing, scrubs HTML, and seals outcome evidence.' },
        { id: 'TEST_02', name: 'Test 02: Sensitive Mutation & Approval Flow', desc: 'Performs DOM form input requiring human executive approval for irreversible operations.' },
        { id: 'TEST_03', name: 'Test 03: Prompt Injection Neutralization', desc: 'Detects and neutralizes malicious adversarial web instructions embedded in hostile page DOM text.' },
        { id: 'TEST_04', name: 'Test 04: Unknown Result Reconciliation', desc: 'Simulates network disconnection, flags task as RECONCILIATION_REQUIRED, preventing false success.' },
        { id: 'TEST_05', name: 'Test 05: Multi-Tenant Session Isolation', desc: 'Verifies strict tenant and company isolation across sessions, preventing cross-tenant leakage.' },
        { id: 'TEST_06', name: 'Test 06: Emergency Multi-Scope KillSwitch', desc: 'Trips browser killswitch mid-action, immediately blocking subsequent navigation attempts.' },
        { id: 'TEST_07', name: 'Test 07: OpenHands + Browser Dual-Agent Workflow', desc: 'Cross-subsystem coordination where OpenHands writes web code and Browser Use runs real-browser verification.' },
        { id: 'TEST_08', name: 'Test 08: MCP + Browser Coordination', desc: 'Cross-subsystem workflow invoking governed MCP tools alongside browser execution.' },
        { id: 'TEST_09', name: 'Test 09: A2A + Browser Autonomous Delegation', desc: 'A2A agent protocol delegating a governed browser execution task.' },
        { id: 'SECTION_80', name: 'Section 80: Complete ZONATA Grand Acceptance Test', desc: 'Grand acceptance test executing the full 15-stage governed browser pipeline across all ZONATA subsystems.' }
      ];

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:16px;">
            <h3 style="margin:0 0 6px 0; font-size:15px; font-weight:700;">Live Browser Use Verification Suite</h3>
            <p style="margin:0; font-size:12px; color:var(--text-secondary);">
              Select any canonical scenario to execute live in this container and verify governed browser capabilities.
            </p>
          </div>

          <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:12px;">
            ${scenarios.map(sc => `
              <div style="background:var(--bg-secondary, #1e293b); border:1px solid var(--border-color, rgba(255,255,255,0.08)); border-radius:8px; padding:14px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                  <div style="font-weight:700; font-size:13px; color:#38bdf8; margin-bottom:4px;">${sc.name}</div>
                  <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">${sc.desc}</div>
                </div>
                <button class="btn-run-scenario" data-scenario="${sc.id}" ${this.isExecutingScenario ? 'disabled' : ''} style="background:#2563eb; color:#ffffff; border:none; border-radius:6px; padding:6px 12px; font-size:12px; font-weight:600; cursor:pointer;">
                  ▶ Run Verification Test
                </button>
              </div>
            `).join('')}
          </div>

          ${this.scenarioOutput ? `
            <div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:16px; margin-top:8px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-weight:700; font-size:13px; color:#34d399;">Scenario Execution Result</span>
                <button id="btnClearScenarioOutput" style="background:transparent; color:#94a3b8; border:none; cursor:pointer; font-size:12px;">Clear ✕</button>
              </div>
              <pre style="margin:0; font-family:monospace; font-size:11px; color:#cbd5e1; overflow-x:auto; max-height:400px;">${JSON.stringify(this.scenarioOutput, null, 2)}</pre>
            </div>
          ` : ''}
        </div>
      `;
    }

    attachEventListeners(container) {
      // Tab switching
      container.querySelectorAll('.browser-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.activeTab = e.currentTarget.getAttribute('data-tab');
          this.render(this.containerId);
        });
      });

      // Refresh
      const btnRefresh = container.querySelector('#btnBrowserRefresh');
      if (btnRefresh) {
        btnRefresh.addEventListener('click', () => this.render(this.containerId));
      }

      // Killswitch Toggle
      const btnKs = container.querySelector('#btnBrowserKillSwitch');
      if (btnKs) {
        btnKs.addEventListener('click', async () => {
          const newState = !this.killswitchActive;
          try {
            await fetch('/api/browser/killswitch', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ active: newState, scope: 'GLOBAL', reason: 'User dashboard toggle' })
            });
            await this.render(this.containerId);
          } catch (err) {
            alert('Failed to toggle killswitch: ' + err);
          }
        });
      }

      // Inspect Execution
      container.querySelectorAll('.btn-inspect-exec').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const execId = e.currentTarget.getAttribute('data-id');
          this.selectedExecution = execId;
          try {
            const res = await fetch(`/api/browser/executions/${execId}/history`).then(r => r.json());
            this.selectedExecutionActions = res.actions || [];
            this.activeTab = 'actions';
            this.render(this.containerId);
          } catch (err) {
            alert('Failed to fetch actions: ' + err);
          }
        });
      });

      // Close Session
      container.querySelectorAll('.btn-close-sess').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const sessId = e.currentTarget.getAttribute('data-id');
          try {
            await fetch(`/api/browser/sessions/${sessId}/close`, { method: 'POST' });
            await this.render(this.containerId);
          } catch (err) {
            alert('Failed to close session: ' + err);
          }
        });
      });

      // Approve Mutation
      container.querySelectorAll('.btn-approve-act').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const apprId = e.currentTarget.getAttribute('data-id');
          try {
            await fetch(`/api/browser/approvals/${apprId}/approve`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ approver: 'Executive Dashboard User' })
            });
            await this.render(this.containerId);
          } catch (err) {
            alert('Failed to approve mutation: ' + err);
          }
        });
      });

      // Reject Mutation
      container.querySelectorAll('.btn-reject-act').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const apprId = e.currentTarget.getAttribute('data-id');
          try {
            await fetch(`/api/browser/approvals/${apprId}/reject`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ rejector: 'Executive Dashboard User', reason: 'Manual rejection' })
            });
            await this.render(this.containerId);
          } catch (err) {
            alert('Failed to reject mutation: ' + err);
          }
        });
      });

      // Quick Run Scenario (Empty state)
      const btnQuick = container.querySelector('#btnQuickRunScenario');
      if (btnQuick) {
        btnQuick.addEventListener('click', () => this.runScenario('TEST_01'));
      }

      // Run Scenario Buttons
      container.querySelectorAll('.btn-run-scenario').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const scId = e.currentTarget.getAttribute('data-scenario');
          this.runScenario(scId);
        });
      });

      // Clear Scenario Output
      const btnClear = container.querySelector('#btnClearScenarioOutput');
      if (btnClear) {
        btnClear.addEventListener('click', () => {
          this.scenarioOutput = null;
          this.render(this.containerId);
        });
      }
    }

    async runScenario(scenarioId) {
      this.isExecutingScenario = true;
      this.render(this.containerId);
      try {
        const res = await fetch('/api/browser/demo/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: scenarioId })
        }).then(r => r.json());
        this.scenarioOutput = res;
      } catch (err) {
        this.scenarioOutput = { error: String(err) };
      } finally {
        this.isExecutingScenario = false;
        await this.loadData();
        this.activeTab = 'scenarios';
        this.render(this.containerId);
      }
    }
  }

  // Export to window
  window.BrowserWorkspaceManager = BrowserWorkspaceManager;
  window.browserWorkspace = new BrowserWorkspaceManager();
})();
