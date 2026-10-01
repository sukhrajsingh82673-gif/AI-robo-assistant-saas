/**
 * ZONATA — Governed Agent Interoperability (A2A Protocol v1.0) Workspace
 * ======================================================================
 * Production UI for sovereign agent-to-agent collaboration:
 * - Agent Network Directory (Internal, Trusted External, Discovered, Blocked)
 * - Remote Task Timeline & Dual Correlation Inspector
 * - Human-in-the-Loop Sensitive Delegation Approval Queue
 * - Security Center (Prompt Injection, SSRF, Replay, Cross-Tenant blocks)
 * - Published ZONATA A2A Server Endpoints & Agent Card Manifest
 * - Live Verification & Demonstration Matrix (Scenarios A through J)
 */

(function () {
  'use strict';

  class AgentNetworkWorkspaceManager {
    constructor() {
      this.containerId = 'view-agent-network';
      this.activeTab = 'directory'; // 'directory', 'tasks', 'approvals', 'security', 'published', 'demo'
      this.agents = [];
      this.tasks = [];
      this.approvals = [];
      this.securityEvents = [];
      this.publishedAgents = [];
      this.metrics = {
        connected_agents: 0,
        trusted_agents: 0,
        active_delegations: 0,
        completed_delegations: 0,
        failed_tasks: 0,
        security_events: 0
      };
      this.selectedAgent = null;
      this.selectedTask = null;
      this.killswitchActive = false;
      this.filterTrust = 'ALL';
      this.filterRole = 'ALL';
      this.searchQuery = '';
    }

    async render(containerId) {
      if (containerId) this.containerId = containerId;
      const el = document.getElementById(this.containerId);
      if (!el) return;

      el.innerHTML = `
        <div style="display:flex; justify-content:center; align-items:center; height:300px; color:var(--text-secondary);">
          <div style="text-align:center;">
            <div style="font-size:24px; margin-bottom:12px; animation:spin 1s linear infinite;">🌐</div>
            <div>Loading Governed Agent Network (A2A v1.0)...</div>
          </div>
        </div>
      `;

      await this.loadData();
      this.renderUI(el);
    }

    async loadData() {
      try {
        const [agentsRes, tasksRes, apprsRes, secRes, metricsRes, pubRes] = await Promise.all([
          fetch('/api/a2a/agents').then(r => r.json()).catch(() => ({ agents: [] })),
          fetch('/api/a2a/tasks').then(r => r.json()).catch(() => ({ tasks: [] })),
          fetch('/api/a2a/approvals').then(r => r.json()).catch(() => ({ approvals: [] })),
          fetch('/api/a2a/security/events').then(r => r.json()).catch(() => ({ security_events: [] })),
          fetch('/api/a2a/metrics').then(r => r.json()).catch(() => ({ metrics: {} })),
          fetch('/api/a2a/published').then(r => r.json()).catch(() => ({ published_agents: [] }))
        ]);

        this.agents = agentsRes.agents || [];
        this.tasks = tasksRes.tasks || [];
        this.approvals = apprsRes.approvals || [];
        this.securityEvents = secRes.security_events || [];
        this.metrics = metricsRes.metrics || this.metrics;
        this.publishedAgents = pubRes.published_agents || [];
      } catch (err) {
        console.error('Error loading A2A data:', err);
      }
    }

    renderUI(container) {
      container.innerHTML = `
        <div class="workspace-header" style="margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <h2 style="margin:0; font-size:1.5rem; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                <span>🌐</span> Agent Network (A2A Protocol v1.0)
              </h2>
              <span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); font-size:11px; padding:2px 8px; border-radius:12px;">
                Linux Foundation Standard
              </span>
            </div>
            <p style="margin:4px 0 0 0; color:var(--text-secondary); font-size:0.875rem;">
              Governed interoperability connecting ZONATA with independent, remote, and partner AI agents.
            </p>
          </div>

          <div style="display:flex; gap:10px; align-items:center;">
            <button id="btnA2AKillSwitch" class="btn btn-outline" style="border-color:${this.killswitchActive ? '#ef4444' : 'var(--border)'}; color:${this.killswitchActive ? '#ef4444' : 'var(--text-secondary)'};">
              🛑 ${this.killswitchActive ? 'Disengage KillSwitch' : 'A2A KillSwitch'}
            </button>
            <button id="btnDiscoverAgentModal" class="btn btn-primary" style="background:#2563eb; color:#fff;">
              ➕ Ingest Agent Card
            </button>
          </div>
        </div>

        <!-- Real-time KPI Cards -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; margin-bottom:20px;">
          <div class="card" style="padding:14px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg);">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase;">Connected Agents</div>
            <div style="font-size:22px; font-weight:700; color:var(--text-primary); margin-top:4px;">${this.metrics.connected_agents || 0}</div>
            <div style="font-size:11px; color:#10b981; margin-top:2px;">${this.metrics.trusted_agents || 0} Trusted</div>
          </div>
          <div class="card" style="padding:14px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg);">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase;">Active Delegations</div>
            <div style="font-size:22px; font-weight:700; color:#3b82f6; margin-top:4px;">${this.metrics.active_delegations || 0}</div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">In-flight remote tasks</div>
          </div>
          <div class="card" style="padding:14px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg);">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase;">Completed Tasks</div>
            <div style="font-size:22px; font-weight:700; color:#10b981; margin-top:4px;">${this.metrics.completed_delegations || 0}</div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">Verified causality</div>
          </div>
          <div class="card" style="padding:14px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg);">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase;">Pending Approvals</div>
            <div style="font-size:22px; font-weight:700; color:${this.approvals.length > 0 ? '#f59e0b' : 'var(--text-primary)'}; margin-top:4px;">${this.approvals.length}</div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">Sensitive delegations</div>
          </div>
          <div class="card" style="padding:14px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg);">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase;">Security Events</div>
            <div style="font-size:22px; font-weight:700; color:${this.metrics.security_events > 0 ? '#ef4444' : 'var(--text-primary)'}; margin-top:4px;">${this.metrics.security_events || 0}</div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">Injections & SSRF blocked</div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display:flex; border-bottom:1px solid var(--border); margin-bottom:16px; overflow-x:auto;">
          <button class="a2a-tab-btn ${this.activeTab === 'directory' ? 'active' : ''}" data-tab="directory" style="padding:10px 16px; background:none; border:none; border-bottom:2px solid ${this.activeTab === 'directory' ? '#3b82f6' : 'transparent'}; color:${this.activeTab === 'directory' ? '#3b82f6' : 'var(--text-secondary)'}; font-weight:600; cursor:pointer;">
            📇 Agent Directory
          </button>
          <button class="a2a-tab-btn ${this.activeTab === 'tasks' ? 'active' : ''}" data-tab="tasks" style="padding:10px 16px; background:none; border:none; border-bottom:2px solid ${this.activeTab === 'tasks' ? '#3b82f6' : 'transparent'}; color:${this.activeTab === 'tasks' ? '#3b82f6' : 'var(--text-secondary)'}; font-weight:600; cursor:pointer;">
            ⏱️ Remote Tasks (${this.tasks.length})
          </button>
          <button class="a2a-tab-btn ${this.activeTab === 'approvals' ? 'active' : ''}" data-tab="approvals" style="padding:10px 16px; background:none; border:none; border-bottom:2px solid ${this.activeTab === 'approvals' ? '#3b82f6' : 'transparent'}; color:${this.activeTab === 'approvals' ? '#3b82f6' : 'var(--text-secondary)'}; font-weight:600; cursor:pointer;">
            🛡️ Approvals (${this.approvals.length})
          </button>
          <button class="a2a-tab-btn ${this.activeTab === 'security' ? 'active' : ''}" data-tab="security" style="padding:10px 16px; background:none; border:none; border-bottom:2px solid ${this.activeTab === 'security' ? '#3b82f6' : 'transparent'}; color:${this.activeTab === 'security' ? '#3b82f6' : 'var(--text-secondary)'}; font-weight:600; cursor:pointer;">
            🔒 Security Center (${this.securityEvents.length})
          </button>
          <button class="a2a-tab-btn ${this.activeTab === 'published' ? 'active' : ''}" data-tab="published" style="padding:10px 16px; background:none; border:none; border-bottom:2px solid ${this.activeTab === 'published' ? '#3b82f6' : 'transparent'}; color:${this.activeTab === 'published' ? '#3b82f6' : 'var(--text-secondary)'}; font-weight:600; cursor:pointer;">
            🚀 Published Endpoints (${this.publishedAgents.length})
          </button>
          <button class="a2a-tab-btn ${this.activeTab === 'demo' ? 'active' : ''}" data-tab="demo" style="padding:10px 16px; background:none; border:none; border-bottom:2px solid ${this.activeTab === 'demo' ? '#3b82f6' : 'transparent'}; color:${this.activeTab === 'demo' ? '#3b82f6' : 'var(--text-secondary)'}; font-weight:600; cursor:pointer;">
            🧪 Verification Matrix (A-J)
          </button>
        </div>

        <div id="a2aTabContent">
          ${this.renderTabContent()}
        </div>

        <!-- Ingest Modal Container -->
        <div id="a2aModalContainer"></div>
      `;

      this.wireEvents(container);
    }

    renderTabContent() {
      switch (this.activeTab) {
        case 'directory':
          return this.renderDirectoryTab();
        case 'tasks':
          return this.renderTasksTab();
        case 'approvals':
          return this.renderApprovalsTab();
        case 'security':
          return this.renderSecurityTab();
        case 'published':
          return this.renderPublishedTab();
        case 'demo':
          return this.renderDemoTab();
        default:
          return this.renderDirectoryTab();
      }
    }

    renderDirectoryTab() {
      let filtered = this.agents;
      if (this.filterTrust !== 'ALL') {
        filtered = filtered.filter(a => a.trust_level === this.filterTrust);
      }
      if (this.filterRole !== 'ALL') {
        filtered = filtered.filter(a => a.role_type === this.filterRole);
      }
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        filtered = filtered.filter(a => (a.agent_name || '').toLowerCase().includes(q) || (a.provider_name || '').toLowerCase().includes(q));
      }

      if (filtered.length === 0) {
        return `
          <div style="text-align:center; padding:40px; color:var(--text-secondary); background:var(--card-bg); border-radius:8px; border:1px solid var(--border);">
            <div style="font-size:32px; margin-bottom:8px;">📡</div>
            <div style="font-weight:600; font-size:16px;">No External Agents Connected</div>
            <div style="font-size:13px; margin-top:4px;">No agents match the current filter criteria. Use "Ingest Agent Card" to connect a partner or specialist agent.</div>
          </div>
        `;
      }

      return `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:10px;">
          <div style="display:flex; gap:8px; align-items:center;">
            <input type="text" id="a2aSearchInput" placeholder="Search agents..." value="${this.escape(this.searchQuery)}" style="padding:6px 12px; border-radius:6px; border:1px solid var(--border); background:var(--bg-secondary); color:var(--text-primary); font-size:13px; width:220px;" />
            <select id="a2aFilterTrust" style="padding:6px 10px; border-radius:6px; border:1px solid var(--border); background:var(--bg-secondary); color:var(--text-primary); font-size:13px;">
              <option value="ALL" ${this.filterTrust === 'ALL' ? 'selected' : ''}>All Trust Levels</option>
              <option value="TRUSTED" ${this.filterTrust === 'TRUSTED' ? 'selected' : ''}>Trusted</option>
              <option value="VALIDATED" ${this.filterTrust === 'VALIDATED' ? 'selected' : ''}>Validated</option>
              <option value="DISCOVERED" ${this.filterTrust === 'DISCOVERED' ? 'selected' : ''}>Discovered</option>
              <option value="BLOCKED" ${this.filterTrust === 'BLOCKED' ? 'selected' : ''}>Blocked</option>
            </select>
          </div>
          <div style="font-size:12px; color:var(--text-secondary);">Showing ${filtered.length} of ${this.agents.length} agents</div>
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:14px;">
          ${filtered.map(ag => this.renderAgentCard(ag)).join('')}
        </div>
      `;
    }

    renderAgentCard(ag) {
      const trustColor = {
        'TRUSTED': '#10b981',
        'VALIDATED': '#3b82f6',
        'IDENTITY_VERIFIED': '#6366f1',
        'DISCOVERED': '#f59e0b',
        'RESTRICTED': '#f97316',
        'BLOCKED': '#ef4444'
      }[ag.trust_level] || '#64748b';

      const skillsCount = Array.isArray(ag.skills) ? ag.skills.length : 0;
      const metrics = ag.reputation_metrics || {};

      return `
        <div class="card" style="padding:16px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg); display:flex; flex-direction:column; justify-content:space-between;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
              <div>
                <div style="font-weight:700; font-size:15px; color:var(--text-primary);">${this.escape(ag.agent_name)}</div>
                <div style="font-size:12px; color:var(--text-secondary);">${this.escape(ag.provider_name || 'Independent Provider')}</div>
              </div>
              <span class="badge" style="background:${trustColor}22; color:${trustColor}; border:1px solid ${trustColor}44; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:600;">
                ${ag.trust_level}
              </span>
            </div>

            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">
              ${this.escape(ag.capabilities?.description || 'A2A Protocol v1.0 remote agent endpoint')}
            </div>

            <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">
              <span style="font-size:11px; background:var(--bg-secondary); padding:2px 6px; border-radius:4px; border:1px solid var(--border);">
                ⚡ v${ag.protocol_version || '1.0'}
              </span>
              <span style="font-size:11px; background:var(--bg-secondary); padding:2px 6px; border-radius:4px; border:1px solid var(--border);">
                🎯 ${skillsCount} Skills
              </span>
              <span style="font-size:11px; background:var(--bg-secondary); padding:2px 6px; border-radius:4px; border:1px solid var(--border);">
                ✅ ${metrics.tasks_completed || 0} Done
              </span>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:10px; margin-top:8px;">
            <span style="font-size:11px; color:${ag.status === 'ONLINE' ? '#10b981' : '#64748b'}; display:flex; align-items:center; gap:4px;">
              <span style="width:6px; height:6px; border-radius:50%; background:currentColor;"></span>
              ${ag.status}
            </span>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-sm btn-outline btn-inspect-agent" data-id="${ag.agent_id}" style="font-size:11px; padding:3px 8px;">
                Inspect
              </button>
              <button class="btn btn-sm btn-primary btn-delegate-task" data-id="${ag.agent_id}" style="font-size:11px; padding:3px 8px; background:#2563eb; color:#fff;">
                Delegate
              </button>
            </div>
          </div>
        </div>
      `;
    }

    renderTasksTab() {
      if (this.tasks.length === 0) {
        return `
          <div style="text-align:center; padding:40px; color:var(--text-secondary); background:var(--card-bg); border-radius:8px; border:1px solid var(--border);">
            <div style="font-size:32px; margin-bottom:8px;">⏱️</div>
            <div style="font-weight:600; font-size:16px;">No Remote Tasks Recorded</div>
            <div style="font-size:13px; margin-top:4px;">Delegate a task to an external agent to view its dual correlation timeline.</div>
          </div>
        `;
      }

      return `
        <div class="card" style="border:1px solid var(--border); border-radius:8px; background:var(--card-bg); overflow-x:auto;">
          <table style="width:100%; border-collapse:collapse; font-size:13px; text-align:left;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); background:var(--bg-secondary);">
                <th style="padding:10px 14px;">Task ID</th>
                <th style="padding:10px 14px;">External Agent</th>
                <th style="padding:10px 14px;">A2A State</th>
                <th style="padding:10px 14px;">ZONATA State</th>
                <th style="padding:10px 14px;">Requested By</th>
                <th style="padding:10px 14px;">Created</th>
                <th style="padding:10px 14px; text-align:right;">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this.tasks.map(t => `
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 14px; font-family:monospace; font-size:12px;">${this.escape(t.task_id)}</td>
                  <td style="padding:10px 14px; font-weight:600;">${this.escape(t.agent_id)}</td>
                  <td style="padding:10px 14px;">
                    <span class="badge" style="font-size:11px; padding:2px 6px; border-radius:4px; background:rgba(59,130,246,0.15); color:#60a5fa;">
                      ${t.a2a_state}
                    </span>
                  </td>
                  <td style="padding:10px 14px;">
                    <span class="badge" style="font-size:11px; padding:2px 6px; border-radius:4px; background:rgba(16,185,129,0.15); color:#34d399;">
                      ${t.zonata_state}
                    </span>
                  </td>
                  <td style="padding:10px 14px; color:var(--text-secondary);">${this.escape(t.requested_by || 'AI CEO')}</td>
                  <td style="padding:10px 14px; color:var(--text-secondary); font-size:12px;">${new Date(t.created_at * 1000).toLocaleTimeString()}</td>
                  <td style="padding:10px 14px; text-align:right;">
                    <button class="btn btn-sm btn-outline btn-inspect-task" data-id="${t.task_id}" style="font-size:11px; padding:2px 8px;">
                      Inspect
                    </button>
                    ${t.zonata_state === 'AMBIGUOUS' ? `
                      <button class="btn btn-sm btn-primary btn-reconcile-task" data-id="${t.task_id}" style="font-size:11px; padding:2px 8px; background:#f59e0b; color:#fff;">
                        Reconcile
                      </button>
                    ` : ''}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    renderApprovalsTab() {
      if (this.approvals.length === 0) {
        return `
          <div style="text-align:center; padding:40px; color:var(--text-secondary); background:var(--card-bg); border-radius:8px; border:1px solid var(--border);">
            <div style="font-size:32px; margin-bottom:8px;">🛡️</div>
            <div style="font-weight:600; font-size:16px;">No Pending Delegations for Approval</div>
            <div style="font-size:13px; margin-top:4px;">All external A2A operations are either within autonomous limits or already resolved.</div>
          </div>
        `;
      }

      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(380px, 1fr)); gap:14px;">
          ${this.approvals.map(appr => `
            <div class="card" style="padding:16px; border-radius:8px; border:1px solid #f59e0b; background:var(--card-bg); display:flex; flex-direction:column; justify-content:space-between;">
              <div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                  <span class="badge" style="background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid #f59e0b44; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:700;">
                    WAITING FOR APPROVAL
                  </span>
                  <span style="font-size:11px; color:var(--text-secondary); font-family:monospace;">${appr.request_id}</span>
                </div>
                <div style="font-weight:700; font-size:14px; color:var(--text-primary); margin-bottom:6px;">
                  ${this.escape(appr.action_desc)}
                </div>

                <!-- Section 59: Required Approval Fields -->
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:11px; margin-bottom:12px; background:var(--bg-secondary); padding:10px; border-radius:6px; border:1px solid var(--border);">
                  <div>
                    <span style="color:var(--text-secondary);">External Agent:</span>
                    <div style="font-weight:600; color:var(--text-primary);">${this.escape(appr.agent_id || 'External Specialist')}</div>
                  </div>
                  <div>
                    <span style="color:var(--text-secondary);">Target System:</span>
                    <div style="font-weight:600; color:var(--text-primary);">A2A Remote Gateway</div>
                  </div>
                  <div>
                    <span style="color:var(--text-secondary);">Risk Classification:</span>
                    <div style="font-weight:700; color:#ef4444;">${this.escape(appr.risk_level || 'HIGH')}</div>
                  </div>
                  <div>
                    <span style="color:var(--text-secondary);">Expected Cost:</span>
                    <div style="font-weight:600; color:var(--text-primary);">₹0.00 / Task</div>
                  </div>
                  <div style="grid-column:span 2;">
                    <span style="color:var(--text-secondary);">Data Being Shared:</span>
                    <div style="color:var(--text-primary); font-family:monospace; margin-top:2px;">${this.escape(appr.reason || 'Context-minimized parameters')}</div>
                  </div>
                  <div style="grid-column:span 2;">
                    <span style="color:var(--text-secondary);">Verification Plan:</span>
                    <div style="color:var(--text-primary); margin-top:2px;">Merkle Evidence Ledger check + Physical reality SHA-256 match</div>
                  </div>
                </div>
              </div>

              <!-- Host Decision Controls: Approve, Reject, Edit, Cancel -->
              <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:10px; margin-top:8px;">
                <div style="display:flex; gap:6px;">
                  <button class="btn btn-sm btn-outline btn-edit-approval" data-id="${appr.request_id}" style="font-size:11px; padding:3px 8px;">
                    Edit
                  </button>
                  <button class="btn btn-sm btn-outline btn-reject-approval" data-id="${appr.request_id}" style="color:#ef4444; border-color:#ef4444; font-size:11px; padding:3px 8px;">
                    Cancel / Reject
                  </button>
                </div>
                <button class="btn btn-sm btn-primary btn-approve-approval" data-id="${appr.request_id}" style="background:#10b981; color:#fff; font-size:11px; padding:3px 12px; font-weight:600;">
                  ✓ Approve Action
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    renderSecurityTab() {
      if (this.securityEvents.length === 0) {
        return `
          <div style="text-align:center; padding:40px; color:var(--text-secondary); background:var(--card-bg); border-radius:8px; border:1px solid var(--border);">
            <div style="font-size:32px; margin-bottom:8px;">🔒</div>
            <div style="font-weight:600; font-size:16px;">Zero Security Invariant Violations</div>
            <div style="font-size:13px; margin-top:4px;">All inbound and outbound A2A traffic conforms to policy boundaries.</div>
          </div>
        `;
      }

      return `
        <div class="card" style="border:1px solid var(--border); border-radius:8px; background:var(--card-bg); overflow-x:auto;">
          <table style="width:100%; border-collapse:collapse; font-size:13px; text-align:left;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); background:var(--bg-secondary);">
                <th style="padding:10px 14px;">Event ID</th>
                <th style="padding:10px 14px;">Violation Type</th>
                <th style="padding:10px 14px;">Severity</th>
                <th style="padding:10px 14px;">Details</th>
                <th style="padding:10px 14px;">Timestamp</th>
              </tr>
            </thead>
            <tbody>
              ${this.securityEvents.map(e => `
                <tr style="border-bottom:1px solid var(--border);">
                  <td style="padding:10px 14px; font-family:monospace; font-size:12px;">${this.escape(e.event_id)}</td>
                  <td style="padding:10px 14px; font-weight:700; color:#ef4444;">${this.escape(e.event_type)}</td>
                  <td style="padding:10px 14px;">
                    <span class="badge" style="background:rgba(239,68,68,0.15); color:#ef4444; font-size:11px; padding:2px 6px; border-radius:4px;">
                      ${e.severity}
                    </span>
                  </td>
                  <td style="padding:10px 14px; color:var(--text-secondary); font-size:12px; font-family:monospace; max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    ${this.escape(JSON.stringify(e.details))}
                  </td>
                  <td style="padding:10px 14px; color:var(--text-secondary); font-size:12px;">${new Date(e.timestamp * 1000).toLocaleString()}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    renderPublishedTab() {
      return `
        <div class="card" style="padding:20px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg); margin-bottom:16px;">
          <div style="font-weight:700; font-size:16px; color:var(--text-primary); margin-bottom:8px;">
            A2A Inbound Service Endpoint
          </div>
          <p style="font-size:13px; color:var(--text-secondary); margin-bottom:14px;">
            External agents connect to ZONATA via standard A2A v1.0 specifications.
          </p>
          <div style="background:var(--bg-secondary); padding:12px; border-radius:6px; border:1px solid var(--border); font-family:monospace; font-size:12px; margin-bottom:14px;">
            <div><strong>Agent Card URL:</strong> <code>/.well-known/agent-card.json</code></div>
            <div style="margin-top:4px;"><strong>Send Message Endpoint:</strong> <code>POST /a2a/message:send</code></div>
            <div style="margin-top:4px;"><strong>Task Status Endpoint:</strong> <code>GET /a2a/tasks/{id}</code></div>
          </div>
          <button id="btnViewAgentCard" class="btn btn-outline" style="font-size:12px;">
            📄 View Raw A2A Agent Card Manifest
          </button>
        </div>
      `;
    }

    renderDemoTab() {
      const scenarios = [
        { id: 'A', name: 'Discover External Agent', desc: 'Validates and registers an external Agent Card' },
        { id: 'B', name: 'Delegate Simple Task', desc: 'AI CEO -> Agency Swarm -> A2A -> Verification' },
        { id: 'C', name: 'Long-Running Async Task', desc: 'Asynchronous task with delayed completion' },
        { id: 'D', name: 'Approval Gate', desc: 'Financial mutation suspended for Owner approval' },
        { id: 'E', name: 'Prompt Injection Defense', desc: 'Rejects malicious instruction in external response' },
        { id: 'F', name: 'Malicious Card Defense', desc: 'Blocks SSRF and script payload in Agent Card' },
        { id: 'G', name: 'Ambiguous State Reconciliation', desc: 'Reconciles remote timeout without blind replay' },
        { id: 'H', name: 'Tenant Isolation', desc: 'Verifies cross-tenant data access is blocked' },
        { id: 'I', name: 'KillSwitch Override', desc: 'Instantly halts all outbound A2A communications' },
        { id: 'J', name: 'LangGraph + A2A Workflow', desc: 'StateGraph workflow with external A2A delegation node' }
      ];

      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:12px; margin-bottom:20px;">
          ${scenarios.map(s => `
            <div class="card" style="padding:14px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg); display:flex; flex-direction:column; justify-content:space-between;">
              <div>
                <div style="font-weight:700; font-size:14px; color:var(--text-primary); margin-bottom:4px;">
                  Scenario ${s.id}: ${s.name}
                </div>
                <div style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">
                  ${s.desc}
                </div>
              </div>
              <button class="btn btn-sm btn-primary btn-run-scenario" data-scenario="${s.id}" style="width:100%; background:#2563eb; color:#fff; font-size:12px;">
                ▶ Run Scenario ${s.id}
              </button>
            </div>
          `).join('')}
        </div>

        <div class="card" style="padding:16px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg);">
          <div style="font-weight:700; font-size:14px; color:var(--text-primary); margin-bottom:8px;">Live Scenario Execution Output</div>
          <pre id="a2aScenarioOutput" style="background:var(--bg-secondary); padding:12px; border-radius:6px; border:1px solid var(--border); font-family:monospace; font-size:12px; max-height:260px; overflow-y:auto; margin:0; color:#10b981;">// Click any scenario above to execute live test...</pre>
        </div>
      `;
    }

    wireEvents(container) {
      // Tab switching
      container.querySelectorAll('.a2a-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.activeTab = e.currentTarget.getAttribute('data-tab');
          this.renderUI(container);
        });
      });

      // Search & Filters
      const search = container.querySelector('#a2aSearchInput');
      if (search) {
        search.addEventListener('input', (e) => {
          this.searchQuery = e.target.value;
          const content = container.querySelector('#a2aTabContent');
          if (content) content.innerHTML = this.renderDirectoryTab();
          this.wireCardButtons(container);
        });
      }

      const trustSelect = container.querySelector('#a2aFilterTrust');
      if (trustSelect) {
        trustSelect.addEventListener('change', (e) => {
          this.filterTrust = e.target.value;
          const content = container.querySelector('#a2aTabContent');
          if (content) content.innerHTML = this.renderDirectoryTab();
          this.wireCardButtons(container);
        });
      }

      // KillSwitch Button
      const ksBtn = container.querySelector('#btnA2AKillSwitch');
      if (ksBtn) {
        ksBtn.addEventListener('click', async () => {
          this.killswitchActive = !this.killswitchActive;
          await fetch('/api/a2a/killswitch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active: this.killswitchActive })
          });
          this.renderUI(container);
        });
      }

      // Ingest Modal Button
      const modalBtn = container.querySelector('#btnDiscoverAgentModal');
      if (modalBtn) {
        modalBtn.addEventListener('click', () => this.showIngestModal());
      }

      // View Agent Card JSON
      const viewCardBtn = container.querySelector('#btnViewAgentCard');
      if (viewCardBtn) {
        viewCardBtn.addEventListener('click', async () => {
          const res = await fetch('/.well-known/agent-card.json').then(r => r.json());
          alert(JSON.stringify(res, null, 2));
        });
      }

      this.wireCardButtons(container);
      this.wireScenarioButtons(container);
    }

    wireCardButtons(container) {
      // Inspect agent
      container.querySelectorAll('.btn-inspect-agent').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          this.inspectAgent(id);
        });
      });

      // Delegate task
      container.querySelectorAll('.btn-delegate-task').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          this.delegatePrompt(id);
        });
      });

      // Inspect task
      container.querySelectorAll('.btn-inspect-task').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          await this.inspectTask(id);
        });
      });

      // Reconcile task
      container.querySelectorAll('.btn-reconcile-task').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          const res = await fetch(`/api/a2a/tasks/${id}/reconcile`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) }).then(r => r.json());
          alert(`Reconciled: ${JSON.stringify(res)}`);
          await this.render();
        });
      });

      // Approvals
      container.querySelectorAll('.btn-approve-approval').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          await fetch(`/api/a2a/approvals/${id}/approve`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
          await this.render();
        });
      });

      container.querySelectorAll('.btn-reject-approval').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          await fetch(`/api/a2a/approvals/${id}/reject`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
          await this.render();
        });
      });
    }

    wireScenarioButtons(container) {
      container.querySelectorAll('.btn-run-scenario').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const sc = e.currentTarget.getAttribute('data-scenario');
          const out = container.querySelector('#a2aScenarioOutput');
          if (out) out.innerText = `Executing Scenario ${sc}...`;
          try {
            const res = await fetch('/api/a2a/demo/scenarios', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ scenario: sc })
            }).then(r => r.json());
            if (out) out.innerText = JSON.stringify(res, null, 2);
          } catch (err) {
            if (out) out.innerText = `Error: ${err.message}`;
          }
        });
      });
    }

    showIngestModal() {
      const container = document.getElementById('a2aModalContainer');
      if (!container) return;

      container.innerHTML = `
        <div style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:flex; justify-content:center; align-items:center; z-index:9999;">
          <div class="card" style="width:90%; max-width:540px; background:var(--card-bg); border:1px solid var(--border); border-radius:8px; padding:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <h3 style="margin:0; font-size:16px;">Ingest A2A Agent Card</h3>
              <button id="btnCloseIngestModal" style="background:none; border:none; color:var(--text-secondary); cursor:pointer; font-size:18px;">&times;</button>
            </div>
            <p style="font-size:12px; color:var(--text-secondary); margin-bottom:12px;">
              Paste an A2A v1.0 Agent Card JSON manifest. It will be sanitized and checked for prompt injection and SSRF prior to registration.
            </p>
            <textarea id="a2aCardJsonInput" rows="8" style="width:100%; font-family:monospace; font-size:12px; padding:8px; border-radius:6px; border:1px solid var(--border); background:var(--bg-secondary); color:var(--text-primary); margin-bottom:12px; box-sizing:border-box;">{
  "name": "Partner Tax Compliance Agent",
  "description": "Calculates cross-border VAT and corporate tax filings",
  "version": "1.0.0",
  "supported_interfaces": [
    {
      "url": "https://tax.partner.example.com/a2a",
      "protocol_binding": "HTTP+JSON",
      "protocol_version": "1.0"
    }
  ],
  "provider": { "organization": "TaxCompliance Int." },
  "capabilities": { "streaming": true },
  "skills": [
    { "id": "calc_vat", "name": "Calculate VAT", "description": "Computes invoice VAT", "tags": ["tax"] }
  ]
}</textarea>
            <div style="display:flex; justify-content:flex-end; gap:8px;">
              <button id="btnCancelIngestModal" class="btn btn-outline">Cancel</button>
              <button id="btnSubmitIngestCard" class="btn btn-primary" style="background:#2563eb; color:#fff;">Validate & Register</button>
            </div>
          </div>
        </div>
      `;

      container.querySelector('#btnCloseIngestModal').onclick = () => container.innerHTML = '';
      container.querySelector('#btnCancelIngestModal').onclick = () => container.innerHTML = '';
      container.querySelector('#btnSubmitIngestCard').onclick = async () => {
        const val = container.querySelector('#a2aCardJsonInput').value;
        try {
          const cardObj = JSON.parse(val);
          const res = await fetch('/api/a2a/agents/discover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_card: cardObj, allow_test_loopback: true })
          }).then(r => r.json());
          if (res.success) {
            alert(`Success: Registered agent ${res.agent_id}`);
            container.innerHTML = '';
            await this.render();
          } else {
            alert(`Failed: ${JSON.stringify(res.errors)}`);
          }
        } catch (e) {
          alert(`JSON parse error: ${e.message}`);
        }
      };
    }

    async inspectAgent(agentId) {
      try {
        const res = await fetch(`/api/a2a/agents/${agentId}`).then(r => r.json());
        if (res.agent) {
          this.showAgentDetailModal(res.agent);
        } else {
          alert('Agent not found');
        }
      } catch (err) {
        alert(`Error loading agent: ${err.message}`);
      }
    }

    async inspectTask(taskId) {
      try {
        const res = await fetch(`/api/a2a/tasks/${taskId}`).then(r => r.json());
        if (res.task) {
          this.showTaskDetailModal(res.task);
        } else {
          alert('Task not found');
        }
      } catch (err) {
        alert(`Error loading task: ${err.message}`);
      }
    }

    showAgentDetailModal(agent) {
      const container = document.getElementById('a2aModalContainer');
      if (!container) return;

      const trustColor = {
        'TRUSTED': '#10b981',
        'VALIDATED': '#3b82f6',
        'IDENTITY_VERIFIED': '#6366f1',
        'DISCOVERED': '#f59e0b',
        'RESTRICTED': '#f97316',
        'BLOCKED': '#ef4444'
      }[agent.trust_level] || '#64748b';

      const metrics = agent.reputation_metrics || {};
      const skills = agent.registered_skills || agent.skills || [];

      container.innerHTML = `
        <div class="a2a-modal-backdrop" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.65); display:flex; justify-content:center; align-items:center; z-index:9999; padding:16px; box-sizing:border-box;">
          <div class="card" style="width:100%; max-width:680px; max-height:85vh; overflow-y:auto; background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:24px; box-shadow:0 12px 36px rgba(0,0,0,0.4);">
            <!-- Modal Header (Section 57) -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
              <div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <h3 style="margin:0; font-size:18px; font-weight:700; color:var(--text-primary);">${this.escape(agent.agent_name)}</h3>
                  <span class="badge" style="background:${trustColor}22; color:${trustColor}; border:1px solid ${trustColor}44; font-size:11px; padding:2px 8px; border-radius:4px; font-weight:700;">
                    ${agent.trust_level}
                  </span>
                </div>
                <div style="font-size:13px; color:var(--text-secondary); margin-top:2px;">
                  ${this.escape(agent.provider_name || 'Independent Provider')} &bull; Org: ${this.escape(agent.organization || 'External Partner')}
                </div>
              </div>
              <button class="btn-close-modal" style="background:none; border:none; color:var(--text-secondary); cursor:pointer; font-size:22px; line-height:1;">&times;</button>
            </div>

            <!-- Metadata Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px; margin-bottom:16px; font-size:12px;">
              <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                <div style="color:var(--text-secondary);">Protocol Version</div>
                <div style="font-weight:600; font-family:monospace; margin-top:2px;">A2A v${agent.protocol_version || '1.0'}</div>
              </div>
              <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                <div style="color:var(--text-secondary);">Role Classification</div>
                <div style="font-weight:600; margin-top:2px;">${agent.role_type}</div>
              </div>
              <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                <div style="color:var(--text-secondary);">Status / Health</div>
                <div style="font-weight:600; color:${agent.status === 'ONLINE' ? '#10b981' : '#64748b'}; margin-top:2px;">
                  ${agent.status} ${agent.last_health_check ? '(' + new Date(agent.last_health_check * 1000).toLocaleTimeString() + ')' : ''}
                </div>
              </div>
              <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                <div style="color:var(--text-secondary);">Reputation</div>
                <div style="font-weight:600; margin-top:2px;">${metrics.tasks_completed || 0} done &bull; ${metrics.verification_success || 0} verified</div>
              </div>
            </div>

            <!-- Endpoint URL -->
            <div style="margin-bottom:14px;">
              <div style="font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:4px;">Endpoint URL</div>
              <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border); font-family:monospace; font-size:12px; word-break:break-all;">
                ${this.escape(agent.endpoint_url)}
              </div>
            </div>

            <!-- Skills List -->
            <div style="margin-bottom:16px;">
              <div style="font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Published Skills & Capabilities</div>
              ${skills.length === 0 ? '<div style="font-size:12px; color:var(--text-secondary);">No individual skills declared.</div>' : `
                <div style="display:flex; flex-direction:column; gap:6px;">
                  ${skills.map(s => `
                    <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border); font-size:12px; display:flex; justify-content:space-between; align-items:center;">
                      <div>
                        <div style="font-weight:600; color:var(--text-primary);">${this.escape(s.name || s.id)}</div>
                        <div style="font-size:11px; color:var(--text-secondary);">${this.escape(s.description || '')}</div>
                      </div>
                      <span class="badge" style="background:rgba(59,130,246,0.1); color:#3b82f6; font-size:10px; padding:2px 6px; border-radius:4px;">
                        ${s.risk_level || 'SAFE'}
                      </span>
                    </div>
                  `).join('')}
                </div>
              `}
            </div>

            <!-- Security & Zero-Trust Boundary -->
            <div style="margin-bottom:16px; font-size:12px; background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.2); padding:10px 14px; border-radius:6px;">
              <div style="font-weight:600; color:#ef4444; margin-bottom:2px;">Security & Zero-Trust Governance Boundary</div>
              <div style="color:var(--text-secondary);">
                Zero credentials or private memories shared. Outbound transmissions are strictly context-minimized and secret-scrubbed. Inbound responses undergo prompt-injection and malware quarantine scanning.
              </div>
            </div>

            <!-- Actions -->
            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:14px; flex-wrap:wrap; gap:8px;">
              <div style="display:flex; gap:8px;">
                <button class="btn btn-sm btn-outline btn-modal-ping" data-id="${agent.agent_id}" style="font-size:12px;">
                  💓 Health Ping
                </button>
                <button class="btn btn-sm btn-outline btn-modal-trust" data-id="${agent.agent_id}" data-trust="${agent.trust_level === 'TRUSTED' ? 'RESTRICTED' : 'TRUSTED'}" style="font-size:12px;">
                  ${agent.trust_level === 'TRUSTED' ? '⚠️ Restrict' : '🛡️ Trust'}
                </button>
                <button class="btn btn-sm btn-outline btn-modal-block" data-id="${agent.agent_id}" style="font-size:12px; color:#ef4444; border-color:#ef4444;">
                  🚫 Block
                </button>
              </div>
              <div style="display:flex; gap:8px;">
                <button class="btn btn-sm btn-outline btn-close-modal" style="font-size:12px;">Close</button>
                <button class="btn btn-sm btn-primary btn-modal-delegate" data-id="${agent.agent_id}" style="background:#2563eb; color:#fff; font-size:12px;">
                  Delegate Task
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      // Wire modal buttons
      container.querySelectorAll('.btn-close-modal').forEach(btn => btn.onclick = () => container.innerHTML = '');
      
      const pingBtn = container.querySelector('.btn-modal-ping');
      if (pingBtn) {
        pingBtn.onclick = async () => {
          await fetch(`/api/a2a/agents/${agent.agent_id}/health`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
          container.innerHTML = '';
          await this.render();
        };
      }

      const trustBtn = container.querySelector('.btn-modal-trust');
      if (trustBtn) {
        trustBtn.onclick = async () => {
          const nextTrust = trustBtn.getAttribute('data-trust');
          await fetch(`/api/a2a/agents/${agent.agent_id}/trust`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ trust_level: nextTrust }) });
          container.innerHTML = '';
          await this.render();
        };
      }

      const blockBtn = container.querySelector('.btn-modal-block');
      if (blockBtn) {
        blockBtn.onclick = async () => {
          await fetch(`/api/a2a/agents/${agent.agent_id}/block`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
          container.innerHTML = '';
          await this.render();
        };
      }

      const delBtn = container.querySelector('.btn-modal-delegate');
      if (delBtn) {
        delBtn.onclick = () => {
          container.innerHTML = '';
          this.delegatePrompt(agent.agent_id);
        };
      }
    }

    showTaskDetailModal(task) {
      const container = document.getElementById('a2aModalContainer');
      if (!container) return;

      container.innerHTML = `
        <div class="a2a-modal-backdrop" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.65); display:flex; justify-content:center; align-items:center; z-index:9999; padding:16px; box-sizing:border-box;">
          <div class="card" style="width:100%; max-width:700px; max-height:85vh; overflow-y:auto; background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:24px; box-shadow:0 12px 36px rgba(0,0,0,0.4);">
            <!-- Modal Header (Section 58) -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
              <div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <h3 style="margin:0; font-size:18px; font-weight:700; color:var(--text-primary);">A2A Task Inspector</h3>
                  <span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; font-size:11px; padding:2px 8px; border-radius:4px; font-weight:700;">
                    ${task.a2a_state}
                  </span>
                  <span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; font-size:11px; padding:2px 8px; border-radius:4px; font-weight:700;">
                    ZONATA: ${task.zonata_state}
                  </span>
                </div>
                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px; font-family:monospace;">
                  Task: ${task.id} &bull; Request: ${task.zonata_request_id || 'N/A'}
                </div>
              </div>
              <button class="btn-close-modal" style="background:none; border:none; color:var(--text-secondary); cursor:pointer; font-size:22px; line-height:1;">&times;</button>
            </div>

            <!-- Causality Trace (Section 53 & 58) -->
            <div style="background:var(--bg-secondary); padding:12px; border-radius:6px; border:1px solid var(--border); margin-bottom:16px; font-size:12px;">
              <div style="font-weight:600; color:var(--text-primary); margin-bottom:6px;">Governance & Verification Chain</div>
              <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px; color:var(--text-secondary); font-size:11px;">
                <span style="color:#60a5fa; font-weight:600;">AI CEO / Swarm</span> &rarr;
                <span>A2A Gateway</span> &rarr;
                <span style="color:#f59e0b; font-weight:600;">Agent: ${this.escape(task.agent_id)}</span> &rarr;
                <span>State: ${task.a2a_state}</span> &rarr;
                <span style="color:#10b981; font-weight:600;">Evidence Sealed</span> &rarr;
                <span style="color:#34d399; font-weight:600;">Outcome Verified</span>
              </div>
            </div>

            <!-- Messages Timeline -->
            <div style="margin-bottom:16px;">
              <div style="font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Message Exchange History</div>
              ${(task.messages || []).length === 0 ? '<div style="font-size:12px; color:var(--text-secondary);">No messages stored.</div>' : `
                <div style="display:flex; flex-direction:column; gap:8px; max-height:160px; overflow-y:auto;">
                  ${task.messages.map(m => `
                    <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border); font-size:12px;">
                      <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:11px; color:var(--text-secondary);">
                        <span><strong>${m.role === 'ROLE_USER' ? 'ZONATA Host' : 'External Agent'}</strong> (${m.sender_agent_id})</span>
                        <span>${new Date(m.timestamp * 1000).toLocaleTimeString()}</span>
                      </div>
                      <div style="font-family:monospace; font-size:11px; color:var(--text-primary); word-break:break-all;">
                        ${this.escape(m.sanitized_content)}
                      </div>
                    </div>
                  `).join('')}
                </div>
              `}
            </div>

            <!-- Artifacts -->
            <div style="margin-bottom:16px;">
              <div style="font-size:12px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Exchanged & Quarantined Artifacts</div>
              ${(task.artifacts || []).length === 0 ? '<div style="font-size:12px; color:var(--text-secondary);">No artifacts generated for this task.</div>' : `
                <div style="display:flex; flex-direction:column; gap:6px;">
                  ${task.artifacts.map(art => `
                    <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:6px; border:1px solid var(--border); font-size:12px; display:flex; justify-content:space-between; align-items:center;">
                      <div>
                        <div style="font-weight:600; color:var(--text-primary); font-family:monospace;">${this.escape(art.name)}</div>
                        <div style="font-size:11px; color:var(--text-secondary); font-family:monospace;">SHA256: ${art.sha256_hash ? art.sha256_hash.substring(0, 24) + '...' : 'N/A'}</div>
                      </div>
                      <span class="badge" style="background:${art.security_scan_status === 'CLEAN' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${art.security_scan_status === 'CLEAN' ? '#10b981' : '#ef4444'}; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:600;">
                        ${art.security_scan_status}
                      </span>
                    </div>
                  `).join('')}
                </div>
              `}
            </div>

            <!-- Actions -->
            <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:14px;">
              <div>
                ${task.zonata_state === 'AMBIGUOUS' ? `
                  <button class="btn btn-sm btn-primary btn-modal-reconcile" data-id="${task.id}" style="background:#f59e0b; color:#fff; font-size:12px;">
                    ⚠️ Reconcile State
                  </button>
                ` : ''}
                ${task.a2a_state === 'TASK_STATE_WORKING' ? `
                  <button class="btn btn-sm btn-outline btn-modal-cancel" data-id="${task.id}" style="color:#ef4444; border-color:#ef4444; font-size:12px;">
                    Cancel Task
                  </button>
                ` : ''}
              </div>
              <button class="btn btn-sm btn-outline btn-close-modal" style="font-size:12px;">Close</button>
            </div>
          </div>
        </div>
      `;

      container.querySelectorAll('.btn-close-modal').forEach(btn => btn.onclick = () => container.innerHTML = '');

      const recBtn = container.querySelector('.btn-modal-reconcile');
      if (recBtn) {
        recBtn.onclick = async () => {
          await fetch(`/api/a2a/tasks/${task.id}/reconcile`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
          container.innerHTML = '';
          await this.render();
        };
      }

      const cancelBtn = container.querySelector('.btn-modal-cancel');
      if (cancelBtn) {
        cancelBtn.onclick = async () => {
          await fetch(`/api/a2a/tasks/${task.id}/cancel`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
          container.innerHTML = '';
          await this.render();
        };
      }
    }

    async delegatePrompt(agentId) {
      const query = prompt('Enter task prompt to delegate to external agent:', 'Perform standard market analysis');
      if (!query) return;
      const res = await fetch('/api/a2a/tasks/delegate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: agentId,
          skill_name: 'Market Intelligence',
          parameters: { query },
          requested_by: 'Host Cockpit UI'
        })
      }).then(r => r.json());
      alert(`Delegation Result:\n${JSON.stringify(res, null, 2)}`);
      await this.render();
    }

    escape(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
  }

  // Export singleton
  window.AgentNetworkWorkspace = new AgentNetworkWorkspaceManager();
})();
