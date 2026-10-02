/**
 * ZONATA — Governed Model Context Protocol (MCP 2026-07-28) Workspace
 * ====================================================================
 * Production Enterprise Tool, Data & System Interoperability Layer:
 * - Governed Server Registry (Streamable HTTP, stdio, Trust States, Health)
 * - Capability & Tool Inspector (Schema, Risk Class, Admin Overrides, Approvals)
 * - Governed Resource Browser (Sanitization, Prompt Injection Firewall)
 * - Execution & Audit Inspector (Policy, Authority, Verifications, Merkle Evidence)
 * - Security Center (SSRF, Injection, Isolation Breaches, Credential Defense)
 * - ZONATA Inbound MCP Server (Published Capabilities for External AI)
 * - Section 73 Canonical Scenario & Verification Suite
 */

(function () {
  'use strict';

  class McpWorkspaceManager {
    constructor() {
      this.containerId = 'view-mcp-network';
      this.activeTab = 'servers'; // 'servers', 'tools', 'resources', 'executions', 'security', 'published', 'demo'
      this.servers = [];
      this.tools = [];
      this.resources = [];
      this.executions = [];
      this.securityEvents = [];
      this.publishedCapabilities = [];
      this.metrics = {
        registered_servers: 0,
        active_connections: 0,
        available_tools: 0,
        tool_invocations: 0,
        successful_executions: 0,
        failed_executions: 0,
        awaiting_approval: 0,
        policy_blocks: 0,
        security_events: 0,
        verification_success: 0,
        unknown_outcomes: 0,
        killswitch_active: false
      };
      this.selectedServer = null;
      this.selectedTool = null;
      this.selectedExecution = null;
      this.killswitchActive = false;
      this.filterTrust = 'ALL';
      this.filterRisk = 'ALL';
      this.searchQuery = '';
      this.isExecutingDemo = false;
      this.demoOutput = null;
    }

    async render(containerId) {
      if (containerId) this.containerId = containerId;
      const el = document.getElementById(this.containerId);
      if (!el) return;

      el.innerHTML = `
        <div style="display:flex; justify-content:center; align-items:center; height:300px; color:var(--text-secondary);">
          <div style="text-align:center;">
            <div style="font-size:28px; margin-bottom:12px; animation:spin 1s linear infinite;">⚡</div>
            <div style="font-weight:600; font-size:15px; color:var(--text-primary);">Loading Governed MCP Layer (2026-07-28)...</div>
            <div style="font-size:12px; margin-top:4px;">Negotiating stateless capability schemas & trust topology</div>
          </div>
        </div>
      `;

      await this.loadData();
      this.renderUI(el);
    }

    async loadData() {
      try {
        const [serversRes, toolsRes, resRes, execsRes, secRes, metricsRes, pubRes, ksRes] = await Promise.all([
          fetch('/api/mcp/servers').then(r => r.json()).catch(() => ({ servers: [] })),
          fetch('/api/mcp/tools').then(r => r.json()).catch(() => ({ tools: [] })),
          fetch('/api/mcp/resources').then(r => r.json()).catch(() => ({ resources: [] })),
          fetch('/api/mcp/executions?limit=50').then(r => r.json()).catch(() => ({ executions: [] })),
          fetch('/api/mcp/security/events?limit=50').then(r => r.json()).catch(() => ({ security_events: [] })),
          fetch('/api/mcp/metrics').then(r => r.json()).catch(() => ({ metrics: {} })),
          fetch('/api/mcp/published').then(r => r.json()).catch(() => ({ published_capabilities: [] })),
          fetch('/api/mcp/killswitch').then(r => r.json()).catch(() => ({ killswitch_active: false }))
        ]);

        this.servers = serversRes.servers || [];
        this.tools = toolsRes.tools || [];
        this.resources = resRes.resources || [];
        this.executions = execsRes.executions || [];
        this.securityEvents = secRes.security_events || [];
        this.metrics = metricsRes.metrics || this.metrics;
        this.publishedCapabilities = pubRes.published_capabilities || [];
        this.killswitchActive = !!ksRes.killswitch_active;
      } catch (err) {
        console.error('Error loading MCP data:', err);
      }
    }

    renderUI(container) {
      container.innerHTML = `
        <!-- Header -->
        <div class="workspace-header" style="margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <h2 style="margin:0; font-size:1.5rem; font-weight:700; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                <span>🔌</span> MCP Network (Model Context Protocol 2026-07-28)
              </h2>
              <span class="badge" style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3); font-size:11px; padding:2px 8px; border-radius:12px;">
                Stateless Protocol Core
              </span>
              <span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); font-size:11px; padding:2px 8px; border-radius:12px;">
                Sovereign Governance Enforced
              </span>
            </div>
            <p style="margin:4px 0 0 0; color:var(--text-secondary); font-size:0.875rem;">
              Governed agent ↔ tool, agent ↔ data, and agent ↔ enterprise system interoperability (CRM, ERP, PMS, Databases, APIs).
            </p>
          </div>

          <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
            <button id="btnMcpKillSwitch" class="btn btn-outline" style="border-color:${this.killswitchActive ? '#ef4444' : 'var(--border)'}; color:${this.killswitchActive ? '#ef4444' : 'var(--text-secondary)'}; font-weight:600;">
              🛑 ${this.killswitchActive ? 'Disengage KillSwitch' : 'MCP KillSwitch'}
            </button>
            <button id="btnAddMcpServer" class="btn btn-primary" style="display:flex; align-items:center; gap:6px;">
              <span>➕</span> Add Server
            </button>
            <button id="btnRunSection73" class="btn" style="background:#8b5cf6; color:#ffffff; font-weight:600; display:flex; align-items:center; gap:6px;">
              <span>🚀</span> Section 73 Test
            </button>
          </div>
        </div>

        <!-- Metric KPI Cards -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:12px; margin-bottom:20px;">
          <div class="overview-card" style="padding:14px;">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">MCP Servers</div>
            <div style="font-size:22px; font-weight:700; color:var(--text-primary); margin-top:4px; font-family:var(--font-mono);">
              ${this.metrics.active_connections || this.metrics.registered_servers} <span style="font-size:12px; color:var(--text-secondary); font-weight:400;">/ ${this.metrics.registered_servers} total</span>
            </div>
          </div>
          <div class="overview-card" style="padding:14px;">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">Governed Capabilities</div>
            <div style="font-size:22px; font-weight:700; color:var(--text-primary); margin-top:4px; font-family:var(--font-mono);">
              ${this.metrics.available_tools || this.tools.length}
            </div>
          </div>
          <div class="overview-card" style="padding:14px;">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">Tool Invocations</div>
            <div style="font-size:22px; font-weight:700; color:#3b82f6; margin-top:4px; font-family:var(--font-mono);">
              ${this.metrics.tool_invocations || this.executions.length}
            </div>
          </div>
          <div class="overview-card" style="padding:14px;">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">Verified Success</div>
            <div style="font-size:22px; font-weight:700; color:#10b981; margin-top:4px; font-family:var(--font-mono);">
              ${this.metrics.verification_success || this.metrics.successful_executions || 0}
            </div>
          </div>
          <div class="overview-card" style="padding:14px;">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">Awaiting Approval</div>
            <div style="font-size:22px; font-weight:700; color:${(this.metrics.awaiting_approval > 0) ? '#f59e0b' : 'var(--text-primary)'}; margin-top:4px; font-family:var(--font-mono);">
              ${this.metrics.awaiting_approval || 0}
            </div>
          </div>
          <div class="overview-card" style="padding:14px;">
            <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">Security Events</div>
            <div style="font-size:22px; font-weight:700; color:${(this.metrics.security_events > 0) ? '#ef4444' : 'var(--text-primary)'}; margin-top:4px; font-family:var(--font-mono);">
              ${this.metrics.security_events || 0}
            </div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div style="display:flex; gap:8px; border-bottom:1px solid var(--border); margin-bottom:20px; overflow-x:auto; padding-bottom:2px;">
          <button class="mcp-tab-btn ${this.activeTab === 'servers' ? 'active' : ''}" data-tab="servers">
            Servers (${this.servers.length})
          </button>
          <button class="mcp-tab-btn ${this.activeTab === 'tools' ? 'active' : ''}" data-tab="tools">
            Tools & Capabilities (${this.tools.length})
          </button>
          <button class="mcp-tab-btn ${this.activeTab === 'resources' ? 'active' : ''}" data-tab="resources">
            Resources (${this.resources.length})
          </button>
          <button class="mcp-tab-btn ${this.activeTab === 'executions' ? 'active' : ''}" data-tab="executions">
            Invocations & Audit (${this.executions.length})
          </button>
          <button class="mcp-tab-btn ${this.activeTab === 'security' ? 'active' : ''}" data-tab="security">
            Security Center (${this.securityEvents.length})
          </button>
          <button class="mcp-tab-btn ${this.activeTab === 'published' ? 'active' : ''}" data-tab="published">
            ZONATA MCP Server (${this.publishedCapabilities.length})
          </button>
          <button class="mcp-tab-btn ${this.activeTab === 'demo' ? 'active' : ''}" data-tab="demo">
            Verification Matrix
          </button>
        </div>

        <!-- Active View Content -->
        <div id="mcpTabContent">
          ${this.renderActiveTabContent()}
        </div>

        <!-- Modals Container -->
        <div id="mcpModalContainer"></div>
      `;

      this.attachEventListeners(container);
    }

    renderActiveTabContent() {
      switch (this.activeTab) {
        case 'servers': return this.renderServersTab();
        case 'tools': return this.renderToolsTab();
        case 'resources': return this.renderResourcesTab();
        case 'executions': return this.renderExecutionsTab();
        case 'security': return this.renderSecurityTab();
        case 'published': return this.renderPublishedTab();
        case 'demo': return this.renderDemoTab();
        default: return this.renderServersTab();
      }
    }

    // -------------------------------------------------------------------------
    // 1. SERVERS TAB
    // -------------------------------------------------------------------------
    renderServersTab() {
      if (this.servers.length === 0) {
        return `
          <div class="overview-card" style="text-align:center; padding:40px 20px;">
            <div style="font-size:36px; margin-bottom:12px;">🔌</div>
            <h3 style="margin:0 0 8px 0; color:var(--text-primary);">No MCP Servers Registered</h3>
            <p style="color:var(--text-secondary); max-width:440px; margin:0 auto 16px auto; font-size:14px;">
              Register an enterprise PMS, ERP, CRM, or database server using Streamable HTTP or stdio to extend ZONATA's governed workforce capabilities.
            </p>
            <button class="btn btn-primary" onclick="window.McpWorkspace.openAddServerModal()">
              <span>➕</span> Register External MCP Server
            </button>
          </div>
        `;
      }

      return `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
          <div style="display:flex; gap:8px; align-items:center;">
            <span style="font-size:12px; color:var(--text-secondary); font-weight:600;">TRUST FILTER:</span>
            <select id="mcpTrustFilter" class="form-control" style="font-size:12px; padding:4px 8px; width:auto;">
              <option value="ALL" ${this.filterTrust === 'ALL' ? 'selected' : ''}>All Trust States</option>
              <option value="TRUSTED" ${this.filterTrust === 'TRUSTED' ? 'selected' : ''}>Trusted</option>
              <option value="VALIDATED" ${this.filterTrust === 'VALIDATED' ? 'selected' : ''}>Validated</option>
              <option value="DISCOVERED" ${this.filterTrust === 'DISCOVERED' ? 'selected' : ''}>Discovered</option>
              <option value="SUSPENDED" ${this.filterTrust === 'SUSPENDED' ? 'selected' : ''}>Suspended</option>
              <option value="BLOCKED" ${this.filterTrust === 'BLOCKED' ? 'selected' : ''}>Blocked</option>
            </select>
          </div>
          <span style="font-size:12px; color:var(--text-secondary);">${this.servers.length} servers configured</span>
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:16px;">
          ${this.servers.map(s => this.renderServerCard(s)).join('')}
        </div>
      `;
    }

    renderServerCard(s) {
      const trustColors = {
        TRUSTED: { bg: 'rgba(16,185,129,0.15)', text: '#34d399', border: 'rgba(16,185,129,0.3)' },
        VALIDATED: { bg: 'rgba(59,130,246,0.15)', text: '#60a5fa', border: 'rgba(59,130,246,0.3)' },
        DISCOVERED: { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24', border: 'rgba(245,158,11,0.3)' },
        SUSPENDED: { bg: 'rgba(239,68,68,0.15)', text: '#f87171', border: 'rgba(239,68,68,0.3)' },
        BLOCKED: { bg: 'rgba(185,28,28,0.2)', text: '#ef4444', border: 'rgba(185,28,28,0.4)' }
      };
      const tstyle = trustColors[s.trust_state] || trustColors.DISCOVERED;
      const isOnline = s.status === 'ONLINE';

      return `
        <div class="overview-card" style="padding:16px; display:flex; flex-direction:column; justify-content:space-between; gap:12px; border-top: 3px solid ${isOnline ? '#10b981' : '#6b7280'};">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
              <div>
                <h4 style="margin:0; font-size:15px; font-weight:700; color:var(--text-primary);">${this.escape(s.display_name)}</h4>
                <div style="font-size:11px; font-family:var(--font-mono); color:var(--text-secondary); margin-top:2px;">
                  ${this.escape(s.server_id)}
                </div>
              </div>
              <span class="badge" style="background:${tstyle.bg}; color:${tstyle.text}; border:1px solid ${tstyle.border}; font-size:10px; padding:2px 6px;">
                ${s.trust_state}
              </span>
            </div>

            <p style="font-size:12px; color:var(--text-secondary); margin:0 0 10px 0; line-height:1.4;">
              ${this.escape(s.description || 'Enterprise MCP connection')}
            </p>

            <div style="background:var(--bg-tertiary, #1f2937); padding:8px 10px; border-radius:6px; font-size:11px; font-family:var(--font-mono); color:var(--text-secondary); margin-bottom:10px; word-break:break-all;">
              <span style="color:var(--text-primary); font-weight:600;">${(s.transport || 'HTTP').toUpperCase()}:</span> ${this.escape(s.endpoint)}
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:11px;">
              <div><span style="color:var(--text-secondary);">Protocol:</span> <strong>${s.protocol_version || '2026-07-28'}</strong></div>
              <div><span style="color:var(--text-secondary);">Health:</span> <strong style="color:${s.health_status === 'HEALTHY' ? '#10b981' : '#f59e0b'};">${s.health_status || 'HEALTHY'}</strong></div>
              <div><span style="color:var(--text-secondary);">Data Class:</span> <strong>${s.data_classification || 'INTERNAL'}</strong></div>
              <div><span style="color:var(--text-secondary);">Rate Limit:</span> <strong>${s.rate_limit || 60}/min</strong></div>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:10px; margin-top:6px; flex-wrap:wrap; gap:6px;">
            <div style="display:flex; gap:6px;">
              <button class="btn btn-outline" style="font-size:11px; padding:4px 8px;" onclick="window.McpWorkspace.testConnection('${s.server_id}')">
                ⚡ Test
              </button>
              <button class="btn btn-outline" style="font-size:11px; padding:4px 8px;" onclick="window.McpWorkspace.refreshCapabilities('${s.server_id}')">
                🔄 Sync
              </button>
            </div>
            <button class="btn btn-primary" style="font-size:11px; padding:4px 10px;" onclick="window.McpWorkspace.openServerDetailModal('${s.server_id}')">
              Inspect Server →
            </button>
          </div>
        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // 2. TOOLS TAB
    // -------------------------------------------------------------------------
    renderToolsTab() {
      if (this.tools.length === 0) {
        return `
          <div class="overview-card" style="text-align:center; padding:40px 20px;">
            <div style="font-size:36px; margin-bottom:12px;">🛠️</div>
            <h3 style="margin:0 0 8px 0; color:var(--text-primary);">No Governed MCP Tools Discovered</h3>
            <p style="color:var(--text-secondary); max-width:440px; margin:0 auto; font-size:14px;">
              Register an MCP server or trigger discovery to map external capabilities into ZONATA's sovereign Capability Registry.
            </p>
          </div>
        `;
      }

      return `
        <div style="margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div style="font-size:12px; color:var(--text-secondary);">
            <strong>${this.tools.length}</strong> governed tools registered in Capability Registry with deterministic risk classification.
          </div>
          <span class="badge" style="background:rgba(59,130,246,0.1); color:#3b82f6; font-size:11px; padding:3px 8px;">
            Authority Gateway Enforced
          </span>
        </div>

        <div style="overflow-x:auto;">
          <table class="table" style="width:100%; border-collapse:collapse; font-size:12px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); text-align:left; color:var(--text-secondary);">
                <th style="padding:10px 8px;">TOOL NAME</th>
                <th style="padding:10px 8px;">SERVER</th>
                <th style="padding:10px 8px;">RISK CLASS</th>
                <th style="padding:10px 8px;">APPROVAL REQUIRED</th>
                <th style="padding:10px 8px;">VERIFICATION</th>
                <th style="padding:10px 8px;">IDEMPOTENCY</th>
                <th style="padding:10px 8px; text-align:right;">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              ${this.tools.map(t => this.renderToolRow(t)).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    renderToolRow(t) {
      const riskColors = {
        READ_ONLY: { bg: 'rgba(16,185,129,0.15)', text: '#34d399' },
        LOW_RISK_MUTATION: { bg: 'rgba(59,130,246,0.15)', text: '#60a5fa' },
        BUSINESS_MUTATION: { bg: 'rgba(168,85,247,0.15)', text: '#c084fc' },
        FINANCIAL: { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24' },
        PRIVILEGED: { bg: 'rgba(239,68,68,0.15)', text: '#f87171' },
        DESTRUCTIVE: { bg: 'rgba(185,28,28,0.25)', text: '#ef4444' }
      };
      const rstyle = riskColors[t.risk_class] || riskColors.READ_ONLY;

      return `
        <tr style="border-bottom:1px solid var(--border); vertical-align:middle;">
          <td style="padding:10px 8px;">
            <div style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${this.escape(t.name)}</div>
            <div style="font-size:11px; color:var(--text-secondary); max-width:240px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
              ${this.escape(t.description || 'No description')}
            </div>
          </td>
          <td style="padding:10px 8px; font-family:var(--font-mono); font-size:11px; color:var(--text-secondary);">
            ${this.escape(t.server_id)}
          </td>
          <td style="padding:10px 8px;">
            <span class="badge" style="background:${rstyle.bg}; color:${rstyle.text}; font-size:10px; padding:2px 6px;">
              ${t.risk_class}
            </span>
          </td>
          <td style="padding:10px 8px;">
            ${t.approval_requirement ? '<span class="badge" style="background:rgba(245,158,11,0.15); color:#f59e0b; font-size:10px;">HUMAN REQUIRED</span>' : '<span style="color:var(--text-secondary); font-size:11px;">Autonomous</span>'}
          </td>
          <td style="padding:10px 8px; font-size:11px; color:var(--text-secondary);">
            ${t.verification_requirement ? 'Physical State Query' : 'Signature Seal'}
          </td>
          <td style="padding:10px 8px; font-size:11px;">
            ${t.idempotency ? '<span style="color:#10b981;">Idempotent</span>' : '<span style="color:#ef4444; font-weight:600;">Non-Idempotent</span>'}
          </td>
          <td style="padding:10px 8px; text-align:right;">
            <button class="btn btn-outline" style="font-size:11px; padding:4px 8px;" onclick="window.McpWorkspace.openToolOverrideModal('${t.tool_id}')">
              ⚙️ Override & Inspect
            </button>
          </td>
        </tr>
      `;
    }

    // -------------------------------------------------------------------------
    // 3. RESOURCES TAB
    // -------------------------------------------------------------------------
    renderResourcesTab() {
      if (this.resources.length === 0) {
        return `
          <div class="overview-card" style="text-align:center; padding:40px 20px;">
            <div style="font-size:36px; margin-bottom:12px;">📄</div>
            <h3 style="margin:0 0 8px 0; color:var(--text-primary);">No Governed MCP Resources Available</h3>
            <p style="color:var(--text-secondary); max-width:440px; margin:0 auto; font-size:14px;">
              MCP Resources expose documents, database schemas, and enterprise reports protected by ZONATA's External Content Firewall.
            </p>
          </div>
        `;
      }

      return `
        <div style="margin-bottom:14px; font-size:12px; color:var(--text-secondary);">
          <strong>${this.resources.length}</strong> enterprise resources attached. External content firewall active to scrub prompt injections.
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); gap:14px;">
          ${this.resources.map(r => `
            <div class="overview-card" style="padding:14px; display:flex; flex-direction:column; justify-content:space-between; gap:10px;">
              <div>
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                  <h4 style="margin:0; font-size:14px; font-weight:700; color:var(--text-primary);">${this.escape(r.name)}</h4>
                  <span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; font-size:10px;">${r.data_classification || 'INTERNAL'}</span>
                </div>
                <div style="background:var(--bg-tertiary, #1f2937); padding:6px 8px; border-radius:4px; font-size:11px; font-family:var(--font-mono); color:var(--text-secondary); margin:8px 0; word-break:break-all;">
                  ${this.escape(r.uri)}
                </div>
                <p style="font-size:12px; color:var(--text-secondary); margin:0; line-height:1.4;">
                  ${this.escape(r.description || 'Enterprise MCP document context')}
                </p>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:8px;">
                <span style="font-size:11px; color:var(--text-secondary); font-family:var(--font-mono);">${this.escape(r.mime_type || 'application/json')}</span>
                <button class="btn btn-outline" style="font-size:11px; padding:4px 10px;" onclick="window.McpWorkspace.readResource('${r.resource_id}')">
                  🔍 Read & Sanitize
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // 4. EXECUTIONS TAB
    // -------------------------------------------------------------------------
    renderExecutionsTab() {
      if (this.executions.length === 0) {
        return `
          <div class="overview-card" style="text-align:center; padding:40px 20px;">
            <div style="font-size:36px; margin-bottom:12px;">📊</div>
            <h3 style="margin:0 0 8px 0; color:var(--text-primary);">No Governed Invocations Recorded</h3>
            <p style="color:var(--text-secondary); max-width:440px; margin:0 auto; font-size:14px;">
              Invocations from AI CEO, Agency Swarm, and LangGraph are sealed with Merkle audit trees and causality proofs here.
            </p>
          </div>
        `;
      }

      return `
        <div style="margin-bottom:14px; font-size:12px; color:var(--text-secondary);">
          Showing recent <strong>${this.executions.length}</strong> governed MCP executions. Complete cryptographic causality lineage preserved.
        </div>

        <div style="overflow-x:auto;">
          <table class="table" style="width:100%; border-collapse:collapse; font-size:12px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); text-align:left; color:var(--text-secondary);">
                <th style="padding:10px 8px;">EXEC ID</th>
                <th style="padding:10px 8px;">TOOL</th>
                <th style="padding:10px 8px;">POLICY / AUTHORITY</th>
                <th style="padding:10px 8px;">STATUS</th>
                <th style="padding:10px 8px;">VERIFICATION</th>
                <th style="padding:10px 8px;">EVIDENCE DIGEST</th>
                <th style="padding:10px 8px; text-align:right;">INSPECT</th>
              </tr>
            </thead>
            <tbody>
              ${this.executions.map(ex => {
                const isVerified = ex.execution_status === 'VERIFIED';
                const isSuspended = ex.execution_status === 'APPROVAL_REQUIRED';
                const statusColor = isVerified ? '#10b981' : (isSuspended ? '#f59e0b' : '#ef4444');

                return `
                  <tr style="border-bottom:1px solid var(--border); vertical-align:middle;">
                    <td style="padding:10px 8px; font-family:var(--font-mono); font-size:11px; font-weight:600;">
                      ${this.escape(ex.execution_id)}
                    </td>
                    <td style="padding:10px 8px;">
                      <div style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${this.escape(ex.tool_name)}</div>
                      <div style="font-size:11px; color:var(--text-secondary); font-family:var(--font-mono);">${this.escape(ex.server_id)}</div>
                    </td>
                    <td style="padding:10px 8px; font-size:11px;">
                      <span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; font-size:10px;">${ex.policy_decision}</span>
                      <span class="badge" style="background:rgba(107,114,128,0.15); color:#9ca3af; font-size:10px; margin-left:4px;">${ex.authority_decision}</span>
                    </td>
                    <td style="padding:10px 8px;">
                      <span class="badge" style="background:${statusColor}22; color:${statusColor}; font-weight:700; font-size:10px;">
                        ${ex.execution_status}
                      </span>
                    </td>
                    <td style="padding:10px 8px; font-size:11px;">
                      ${ex.verification_status === 'VERIFIED' ? '<span style="color:#10b981;">✓ Verified</span>' : '<span style="color:var(--text-secondary);">Unverified</span>'}
                    </td>
                    <td style="padding:10px 8px; font-family:var(--font-mono); font-size:10px; color:var(--text-secondary);">
                      ${ex.sha256_digest ? ex.sha256_digest.substring(0, 16) + '...' : '—'}
                    </td>
                    <td style="padding:10px 8px; text-align:right;">
                      <button class="btn btn-outline" style="font-size:11px; padding:4px 8px;" onclick="window.McpWorkspace.openExecutionModal('${ex.execution_id}')">
                        Inspect
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

    // -------------------------------------------------------------------------
    // 5. SECURITY CENTER TAB
    // -------------------------------------------------------------------------
    renderSecurityTab() {
      if (this.securityEvents.length === 0) {
        return `
          <div class="overview-card" style="text-align:center; padding:40px 20px;">
            <div style="font-size:36px; margin-bottom:12px;">🛡️</div>
            <h3 style="margin:0 0 8px 0; color:var(--text-primary);">Zero MCP Security Violations</h3>
            <p style="color:var(--text-secondary); max-width:440px; margin:0 auto; font-size:14px;">
              SSRF validation, prompt injection firewalls, tenant isolation checks, and credential scrubbing are fully operating with no breaches detected.
            </p>
          </div>
        `;
      }

      return `
        <div style="margin-bottom:14px; font-size:12px; color:var(--text-secondary);">
          <strong>${this.securityEvents.length}</strong> security events intercepted by ZONATA MCP Security Inspector.
        </div>

        <div style="display:flex; flex-direction:column; gap:10px;">
          ${this.securityEvents.map(ev => {
            const isCritical = ev.severity === 'CRITICAL' || ev.severity === 'HIGH';
            const color = isCritical ? '#ef4444' : '#f59e0b';
            const detailsStr = typeof ev.details === 'object' ? JSON.stringify(ev.details, null, 2) : ev.details;

            return `
              <div class="overview-card" style="padding:14px; border-left:4px solid ${color};">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                  <div>
                    <span class="badge" style="background:${color}22; color:${color}; font-weight:700; font-size:10px; margin-right:6px;">
                      ${ev.severity}
                    </span>
                    <strong style="color:var(--text-primary); font-size:13px; font-family:var(--font-mono);">${ev.event_type}</strong>
                  </div>
                  <span style="font-size:11px; color:var(--text-secondary);">
                    ${new Date(ev.timestamp * 1000).toLocaleTimeString()}
                  </span>
                </div>
                <pre style="background:var(--bg-tertiary, #111827); padding:8px 10px; border-radius:6px; font-size:11px; color:var(--text-secondary); margin:6px 0 0 0; overflow-x:auto;">${this.escape(detailsStr)}</pre>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // 6. PUBLISHED CAPABILITIES TAB (ZONATA AS MCP SERVER)
    // -------------------------------------------------------------------------
    renderPublishedTab() {
      return `
        <div class="overview-card" style="padding:16px; margin-bottom:20px; border-left:4px solid #8b5cf6;">
          <h3 style="margin:0 0 6px 0; font-size:15px; color:var(--text-primary);">ZONATA Inbound MCP Server Mode (Section 41-42)</h3>
          <p style="color:var(--text-secondary); font-size:13px; margin:0 0 12px 0; line-height:1.4;">
            Allows external AI clients to securely access authorized ZONATA capabilities via JSON-RPC 2.0. Internal prompts, Letta memories, private credentials, and unrestricted execution authority are permanently protected.
          </p>
          <div style="display:flex; gap:12px; font-size:12px; font-family:var(--font-mono); color:var(--text-secondary); flex-wrap:wrap;">
            <span>Endpoint: <strong>POST /mcp</strong> or <strong>POST /api/mcp/endpoint</strong></span>
            <span>Protocol: <strong>MCP 2026-07-28</strong></span>
            <span>Auth: <strong>Tenant Scoped Bearer Token</strong></span>
          </div>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
          <h4 style="margin:0; font-size:14px; color:var(--text-primary);">Published Inbound Capabilities (${this.publishedCapabilities.length})</h4>
          <button class="btn btn-primary" onclick="window.McpWorkspace.openPublishModal()" style="font-size:12px;">
            <span>➕</span> Publish Capability
          </button>
        </div>

        ${this.publishedCapabilities.length === 0 ? `
          <div class="overview-card" style="text-align:center; padding:30px 20px; color:var(--text-secondary); font-size:13px;">
            No capabilities explicitly published. Default sovereign posture: NOT EXPOSED.
          </div>
        ` : `
          <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr)); gap:14px;">
            ${this.publishedCapabilities.map(p => `
              <div class="overview-card" style="padding:14px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                  <strong style="color:var(--text-primary); font-size:14px;">${this.escape(p.name)}</strong>
                  <span class="badge badge-emerald" style="font-size:10px;">${p.visibility}</span>
                </div>
                <p style="font-size:12px; color:var(--text-secondary); margin:0 0 10px 0;">${this.escape(p.description)}</p>
                <div style="font-size:11px; color:var(--text-secondary); display:flex; justify-content:space-between;">
                  <span>Rate: <strong>${p.rate_limit_per_min}/min</strong></span>
                  <span>Approval: <strong>${p.approval_required ? 'Required' : 'Autonomous'}</strong></span>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      `;
    }

    // -------------------------------------------------------------------------
    // 7. DEMONSTRATION & VERIFICATION MATRIX TAB
    // -------------------------------------------------------------------------
    renderDemoTab() {
      const scenarios = [
        { id: 'SECTION_73', name: 'Section 73 Canonical Acceptance Test', desc: 'AI CEO -> Swarm -> PMS Cancellation Discovery -> Human Approval Interception -> Recovery Booking -> Physical Verification -> Evidence Sealed', color: '#8b5cf6' },
        { id: 'A', name: 'Scenario A: Server Discovery & Trust Hierarchy', desc: 'Discovered state enforcement, schema inspection, and identity transition', color: '#3b82f6' },
        { id: 'B', name: 'Scenario B: Governed Tool Autonomous Execution', desc: 'Read-only tool execution, sanitization, independent verification, and evidence ledger', color: '#10b981' },
        { id: 'C', name: 'Scenario C: Mutation Human Approval Pipeline', desc: 'High-risk business mutation suspended for owner approval and resumed with grant', color: '#f59e0b' },
        { id: 'D', name: 'Scenario D: Financial Threshold Policy Enforcement', desc: '₹10,000 policy threshold intercepts ₹25,000 refund with automatic approval gate', color: '#f59e0b' },
        { id: 'E', name: 'Scenario E: External Prompt Injection Firewall', desc: 'Malicious instructions inside tool results neutralized and stripped from LLM context', color: '#ef4444' },
        { id: 'F', name: 'Scenario F: SSRF & Cloud Metadata Defense', desc: 'Strict IP validation blocks loopback and AWS 169.254.169.254 exfiltration attempts', color: '#ef4444' },
        { id: 'G', name: 'Scenario G: Ambiguous Outcome Timeout Reconciliation', desc: 'Network timeout triggers UNKNOWN state, strictly prohibiting blind replay', color: '#3b82f6' },
        { id: 'H', name: 'Scenario H: Multi-Tenant & Company Isolation', desc: 'Cross-tenant access attempts immediately blocked and audited in Security Center', color: '#ef4444' },
        { id: 'I', name: 'Scenario I: Authoritative KillSwitch Override', desc: 'Emergency KillSwitch engages instant block over all tool calls', color: '#ef4444' },
        { id: 'J', name: 'Scenario J: LangGraph Durable Workflow Integration', desc: 'Stateful workflow node executes MCP capability with durable state checkpointing', color: '#10b981' }
      ];

      return `
        <div style="margin-bottom:16px;">
          <h3 style="margin:0 0 6px 0; font-size:16px; color:var(--text-primary);">MCP Protocol Verification & Canonical Test Scenarios</h3>
          <p style="color:var(--text-secondary); font-size:13px; margin:0;">
            Execute normative end-to-end integration scenarios against live ZONATA governance infrastructure.
          </p>
        </div>

        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:12px; margin-bottom:20px;">
          ${scenarios.map(sc => `
            <div class="overview-card" style="padding:14px; display:flex; flex-direction:column; justify-content:space-between; gap:10px; border-left:4px solid ${sc.color};">
              <div>
                <strong style="color:var(--text-primary); font-size:14px;">${sc.name}</strong>
                <p style="color:var(--text-secondary); font-size:12px; margin:6px 0 0 0; line-height:1.4;">${sc.desc}</p>
              </div>
              <button class="btn btn-primary" style="font-size:11px; padding:6px 12px; align-self:flex-start;" onclick="window.McpWorkspace.runDemoScenario('${sc.id}')">
                ▶ Run Scenario
              </button>
            </div>
          `).join('')}
        </div>

        <div id="mcpDemoResultBox" class="overview-card" style="padding:16px; display:${this.demoOutput ? 'block' : 'none'};">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <strong style="font-size:14px; color:var(--text-primary);">Execution Results</strong>
            <button class="btn btn-outline" style="font-size:11px; padding:2px 8px;" onclick="document.getElementById('mcpDemoResultBox').style.display='none'">Dismiss</button>
          </div>
          <pre id="mcpDemoOutputPre" style="background:var(--bg-tertiary, #111827); padding:12px; border-radius:6px; font-size:12px; color:#34d399; margin:0; max-height:360px; overflow-y:auto; font-family:var(--font-mono);">${this.demoOutput ? this.escape(JSON.stringify(this.demoOutput, null, 2)) : ''}</pre>
        </div>
      `;
    }

    // -------------------------------------------------------------------------
    // Event Listeners & Modals
    // -------------------------------------------------------------------------
    attachEventListeners(container) {
      // Tab navigation
      container.querySelectorAll('.mcp-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.activeTab = e.currentTarget.getAttribute('data-tab');
          container.querySelectorAll('.mcp-tab-btn').forEach(b => b.classList.remove('active'));
          e.currentTarget.classList.add('active');
          const contentEl = document.getElementById('mcpTabContent');
          if (contentEl) contentEl.innerHTML = this.renderActiveTabContent();
        });
      });

      // KillSwitch button
      const ksBtn = document.getElementById('btnMcpKillSwitch');
      if (ksBtn) {
        ksBtn.addEventListener('click', async () => {
          const newActive = !this.killswitchActive;
          const confirmMsg = newActive
            ? 'Activate MCP KillSwitch? This will immediately BLOCK all outbound tool invocations across the tenant.'
            : 'Disengage MCP KillSwitch and restore normal governed operations?';
          if (!confirm(confirmMsg)) return;

          try {
            const res = await fetch('/api/mcp/killswitch', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ active: newActive })
            }).then(r => r.json());

            if (res.success) {
              this.killswitchActive = newActive;
              await this.render();
            }
          } catch (err) {
            alert('Failed to update KillSwitch: ' + err.message);
          }
        });
      }

      // Add Server button
      const addBtn = document.getElementById('btnAddMcpServer');
      if (addBtn) {
        addBtn.addEventListener('click', () => this.openAddServerModal());
      }

      // Run Section 73 button
      const s73Btn = document.getElementById('btnRunSection73');
      if (s73Btn) {
        s73Btn.addEventListener('click', () => this.runDemoScenario('SECTION_73'));
      }
    }

    // -------------------------------------------------------------------------
    // Actions & Handlers
    // -------------------------------------------------------------------------
    async testConnection(serverId) {
      try {
        const res = await fetch(`/api/mcp/servers/${serverId}/test`, { method: 'POST' }).then(r => r.json());
        if (res.success) {
          alert(`✓ MCP Connection Healthy!\nLatency: ${res.latency_ms}ms\nProtocol: ${res.protocol_version}\nTransport: ${res.transport}`);
        } else {
          alert(`✗ Connection test failed: ${res.error || 'Server unreachable'}`);
        }
      } catch (err) {
        alert('Test failed: ' + err.message);
      }
    }

    async refreshCapabilities(serverId) {
      try {
        const res = await fetch(`/api/mcp/servers/${serverId}/refresh`, { method: 'POST' }).then(r => r.json());
        if (res.success) {
          alert(`✓ Refreshed capabilities from server:\n${res.tools_count} tools, ${res.resources_count} resources synchronized.`);
          await this.render();
        }
      } catch (err) {
        alert('Sync failed: ' + err.message);
      }
    }

    async runDemoScenario(scenarioId) {
      const box = document.getElementById('mcpDemoResultBox');
      const pre = document.getElementById('mcpDemoOutputPre');
      if (box) box.style.display = 'block';
      if (pre) pre.textContent = `Running scenario ${scenarioId}... please wait...`;

      try {
        const res = await fetch('/api/mcp/demo/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: scenarioId })
        }).then(r => r.json());

        this.demoOutput = res;
        if (pre) pre.textContent = JSON.stringify(res, null, 2);
        // Refresh metrics and executions
        await this.loadData();
      } catch (err) {
        if (pre) pre.textContent = 'Error executing scenario: ' + err.message;
      }
    }

    openAddServerModal() {
      const modal = document.getElementById('mcpModalContainer');
      if (!modal) return;

      modal.innerHTML = `
        <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:9999; padding:16px;">
          <div class="overview-card" style="width:100%; max-width:520px; padding:24px; max-height:90vh; overflow-y:auto;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <h3 style="margin:0; font-size:16px; color:var(--text-primary);">Register Governed MCP Server</h3>
              <button class="btn btn-outline" style="font-size:12px; padding:2px 8px;" onclick="document.getElementById('mcpModalContainer').innerHTML=''">✕</button>
            </div>
            <form id="addMcpServerForm">
              <div style="margin-bottom:12px;">
                <label style="display:block; font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Display Name</label>
                <input type="text" id="mcpServerName" class="form-control" required placeholder="e.g. Opera PMS Enterprise Gateway" style="width:100%; font-size:13px; padding:8px;" />
              </div>
              <div style="margin-bottom:12px;">
                <label style="display:block; font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Endpoint URL / Command</label>
                <input type="text" id="mcpServerEndpoint" class="form-control" required placeholder="https://pms.hotel-corp.internal/mcp" style="width:100%; font-size:13px; padding:8px; font-family:var(--font-mono);" />
              </div>
              <div style="margin-bottom:12px;">
                <label style="display:block; font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Transport</label>
                <select id="mcpServerTransport" class="form-control" style="width:100%; font-size:13px; padding:8px;">
                  <option value="streamable_http">Streamable HTTP (Stateless 2026-07-28 Spec)</option>
                  <option value="stdio">Local stdio (Sandboxed Subprocess)</option>
                </select>
              </div>
              <div style="margin-bottom:12px;">
                <label style="display:block; font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Description</label>
                <textarea id="mcpServerDesc" class="form-control" placeholder="Capability scope and enterprise system overview" style="width:100%; font-size:13px; padding:8px; height:60px;"></textarea>
              </div>
              <div style="margin-bottom:16px;">
                <label style="display:flex; align-items:center; gap:8px; font-size:12px; color:var(--text-secondary);">
                  <input type="checkbox" id="mcpAllowLoopback" /> Allow test loopback endpoints (testing only)
                </label>
              </div>
              <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button type="button" class="btn btn-outline" onclick="document.getElementById('mcpModalContainer').innerHTML=''">Cancel</button>
                <button type="submit" class="btn btn-primary">Register & Validate Server</button>
              </div>
            </form>
          </div>
        </div>
      `;

      document.getElementById('addMcpServerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          display_name: document.getElementById('mcpServerName').value.trim(),
          endpoint: document.getElementById('mcpServerEndpoint').value.trim(),
          transport: document.getElementById('mcpServerTransport').value,
          description: document.getElementById('mcpServerDesc').value.trim(),
          allow_test_loopback: document.getElementById('mcpAllowLoopback').checked
        };

        try {
          const res = await fetch('/api/mcp/servers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          }).then(r => r.json());

          if (res.success) {
            document.getElementById('mcpModalContainer').innerHTML = '';
            await this.render();
          } else {
            alert('Registration rejected:\n' + (res.errors ? res.errors.join('\n') : res.error));
          }
        } catch (err) {
          alert('Error registering server: ' + err.message);
        }
      });
    }

    async openServerDetailModal(serverId) {
      try {
        const srvRes = await fetch(`/api/mcp/servers/${serverId}`).then(r => r.json());
        if (!srvRes.server) return;
        const s = srvRes.server;

        const modal = document.getElementById('mcpModalContainer');
        modal.innerHTML = `
          <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:9999; padding:16px;">
            <div class="overview-card" style="width:100%; max-width:680px; padding:24px; max-height:90vh; overflow-y:auto;">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
                <div>
                  <h3 style="margin:0; font-size:18px; color:var(--text-primary);">${this.escape(s.display_name)}</h3>
                  <div style="font-size:11px; font-family:var(--font-mono); color:var(--text-secondary);">${s.server_id}</div>
                </div>
                <button class="btn btn-outline" style="font-size:12px; padding:2px 8px;" onclick="document.getElementById('mcpModalContainer').innerHTML=''">✕</button>
              </div>

              <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px; font-size:12px;">
                <div><span style="color:var(--text-secondary);">Trust State:</span> <strong>${s.trust_state}</strong></div>
                <div><span style="color:var(--text-secondary);">Status:</span> <strong>${s.status}</strong></div>
                <div><span style="color:var(--text-secondary);">Transport:</span> <strong>${s.transport}</strong></div>
                <div><span style="color:var(--text-secondary);">Protocol Version:</span> <strong>${s.protocol_version}</strong></div>
                <div><span style="color:var(--text-secondary);">Data Classification:</span> <strong>${s.data_classification}</strong></div>
                <div><span style="color:var(--text-secondary);">Rate Limit:</span> <strong>${s.rate_limit}/min</strong></div>
              </div>

              <div style="margin-bottom:16px;">
                <h4 style="margin:0 0 6px 0; font-size:13px; color:var(--text-primary);">Tools (${(s.tools || []).length})</h4>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                  ${(s.tools || []).map(t => `<span class="badge" style="background:var(--bg-tertiary); font-family:var(--font-mono); font-size:11px;">${t.name}</span>`).join('') || '<span style="color:var(--text-secondary); font-size:12px;">None</span>'}
                </div>
              </div>

              <div style="display:flex; justify-content:space-between; border-top:1px solid var(--border); padding-top:14px; flex-wrap:wrap; gap:8px;">
                <div style="display:flex; gap:6px;">
                  <button class="btn btn-outline" onclick="window.McpWorkspace.changeTrust('${s.server_id}', 'SUSPENDED')">Suspend</button>
                  <button class="btn btn-outline" style="color:#ef4444;" onclick="window.McpWorkspace.changeTrust('${s.server_id}', 'BLOCKED')">Block</button>
                  <button class="btn btn-outline" style="color:#10b981;" onclick="window.McpWorkspace.changeTrust('${s.server_id}', 'TRUSTED')">Trust</button>
                </div>
                <button class="btn btn-outline" style="color:#ef4444;" onclick="window.McpWorkspace.disconnectServer('${s.server_id}')">Disconnect Server</button>
              </div>
            </div>
          </div>
        `;
      } catch (err) {
        alert('Failed to load server details: ' + err.message);
      }
    }

    async changeTrust(serverId, state) {
      try {
        await fetch(`/api/mcp/servers/${serverId}/trust`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ trust_state: state })
        });
        document.getElementById('mcpModalContainer').innerHTML = '';
        await this.render();
      } catch (err) {
        alert('Error updating trust: ' + err.message);
      }
    }

    async disconnectServer(serverId) {
      if (!confirm('Disconnect this MCP server? All mapped capabilities will be un-registered.')) return;
      try {
        await fetch(`/api/mcp/servers/${serverId}/disconnect`, { method: 'POST' });
        document.getElementById('mcpModalContainer').innerHTML = '';
        await this.render();
      } catch (err) {
        alert('Error disconnecting: ' + err.message);
      }
    }

    async openToolOverrideModal(toolId) {
      const tool = this.tools.find(t => t.tool_id === toolId);
      if (!tool) return;

      const modal = document.getElementById('mcpModalContainer');
      modal.innerHTML = `
        <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:9999; padding:16px;">
          <div class="overview-card" style="width:100%; max-width:540px; padding:24px; max-height:90vh; overflow-y:auto;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <div>
                <h3 style="margin:0; font-size:16px; color:var(--text-primary);">Tool Inspector & Admin Override</h3>
                <div style="font-size:11px; font-family:var(--font-mono); color:var(--text-secondary);">${tool.name}</div>
              </div>
              <button class="btn btn-outline" style="font-size:12px; padding:2px 8px;" onclick="document.getElementById('mcpModalContainer').innerHTML=''">✕</button>
            </div>

            <form id="toolOverrideForm">
              <div style="margin-bottom:12px;">
                <label style="display:block; font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Risk Classification</label>
                <select id="toolOverrideRisk" class="form-control" style="width:100%; font-size:13px; padding:8px;">
                  <option value="READ_ONLY" ${tool.risk_class === 'READ_ONLY' ? 'selected' : ''}>READ_ONLY (Autonomous query)</option>
                  <option value="LOW_RISK_MUTATION" ${tool.risk_class === 'LOW_RISK_MUTATION' ? 'selected' : ''}>LOW_RISK_MUTATION</option>
                  <option value="BUSINESS_MUTATION" ${tool.risk_class === 'BUSINESS_MUTATION' ? 'selected' : ''}>BUSINESS_MUTATION (Requires Approval)</option>
                  <option value="FINANCIAL" ${tool.risk_class === 'FINANCIAL' ? 'selected' : ''}>FINANCIAL (Threshold Policy Enforced)</option>
                  <option value="PRIVILEGED" ${tool.risk_class === 'PRIVILEGED' ? 'selected' : ''}>PRIVILEGED (High Audit)</option>
                  <option value="DESTRUCTIVE" ${tool.risk_class === 'DESTRUCTIVE' ? 'selected' : ''}>DESTRUCTIVE (Mandatory Confirmation)</option>
                </select>
              </div>

              <div style="margin-bottom:12px;">
                <label style="display:flex; align-items:center; gap:8px; font-size:13px; color:var(--text-primary);">
                  <input type="checkbox" id="toolOverrideApproval" ${tool.approval_requirement ? 'checked' : ''} />
                  Require Human-in-the-Loop Approval Before Execution
                </label>
              </div>

              <div style="margin-bottom:16px;">
                <label style="display:block; font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Data Classification</label>
                <select id="toolOverrideDataClass" class="form-control" style="width:100%; font-size:13px; padding:8px;">
                  <option value="PUBLIC" ${tool.data_classification === 'PUBLIC' ? 'selected' : ''}>PUBLIC</option>
                  <option value="INTERNAL" ${tool.data_classification === 'INTERNAL' ? 'selected' : ''}>INTERNAL</option>
                  <option value="CONFIDENTIAL" ${tool.data_classification === 'CONFIDENTIAL' ? 'selected' : ''}>CONFIDENTIAL</option>
                  <option value="RESTRICTED" ${tool.data_classification === 'RESTRICTED' ? 'selected' : ''}>RESTRICTED</option>
                </select>
              </div>

              <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button type="button" class="btn btn-outline" onclick="document.getElementById('mcpModalContainer').innerHTML=''">Cancel</button>
                <button type="submit" class="btn btn-primary">Save Overrides & Log Audit</button>
              </div>
            </form>
          </div>
        </div>
      `;

      document.getElementById('toolOverrideForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const updates = {
          risk_class: document.getElementById('toolOverrideRisk').value,
          approval_requirement: document.getElementById('toolOverrideApproval').checked,
          data_classification: document.getElementById('toolOverrideDataClass').value
        };

        try {
          await fetch(`/api/mcp/tools/${toolId}/override`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ updates })
          });
          document.getElementById('mcpModalContainer').innerHTML = '';
          await this.render();
        } catch (err) {
          alert('Failed to update tool: ' + err.message);
        }
      });
    }

    async openExecutionModal(execId) {
      try {
        const res = await fetch(`/api/mcp/executions/${execId}`).then(r => r.json());
        if (!res.execution) return;
        const ex = res.execution;

        const modal = document.getElementById('mcpModalContainer');
        modal.innerHTML = `
          <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:9999; padding:16px;">
            <div class="overview-card" style="width:100%; max-width:680px; padding:24px; max-height:90vh; overflow-y:auto;">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px;">
                <div>
                  <h3 style="margin:0; font-size:16px; color:var(--text-primary);">Governed MCP Execution Trace</h3>
                  <div style="font-size:11px; font-family:var(--font-mono); color:var(--text-secondary);">${ex.execution_id}</div>
                </div>
                <button class="btn btn-outline" style="font-size:12px; padding:2px 8px;" onclick="document.getElementById('mcpModalContainer').innerHTML=''">✕</button>
              </div>

              <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:12px; margin-bottom:14px;">
                <div><span style="color:var(--text-secondary);">Tool:</span> <strong>${this.escape(ex.tool_name)}</strong></div>
                <div><span style="color:var(--text-secondary);">Server:</span> <strong>${this.escape(ex.server_id)}</strong></div>
                <div><span style="color:var(--text-secondary);">Policy:</span> <strong>${ex.policy_decision}</strong></div>
                <div><span style="color:var(--text-secondary);">Authority:</span> <strong>${ex.authority_decision}</strong></div>
                <div><span style="color:var(--text-secondary);">Status:</span> <strong style="color:#10b981;">${ex.execution_status}</strong></div>
                <div><span style="color:var(--text-secondary);">Verification:</span> <strong>${ex.verification_status}</strong></div>
              </div>

              <div style="margin-bottom:12px;">
                <label style="display:block; font-size:11px; color:var(--text-secondary); margin-bottom:4px; text-transform:uppercase;">Sanitized Arguments (Data Minimizer Scrubbed)</label>
                <pre style="background:var(--bg-tertiary); padding:8px 10px; border-radius:6px; font-size:11px; color:var(--text-primary); margin:0;">${this.escape(JSON.stringify(ex.sanitized_arguments || ex.arguments, null, 2))}</pre>
              </div>

              <div style="margin-bottom:12px;">
                <label style="display:block; font-size:11px; color:var(--text-secondary); margin-bottom:4px; text-transform:uppercase;">Sanitized Result (Firewall Inspected)</label>
                <pre style="background:var(--bg-tertiary); padding:8px 10px; border-radius:6px; font-size:11px; color:#34d399; margin:0; max-height:160px; overflow-y:auto;">${this.escape(JSON.stringify(ex.response_sanitized || ex.response_raw, null, 2))}</pre>
              </div>

              <div style="background:var(--bg-tertiary); padding:10px; border-radius:6px; font-size:11px; font-family:var(--font-mono); color:var(--text-secondary); margin-bottom:16px;">
                <div>Evidence ID: <strong style="color:var(--text-primary);">${ex.evidence_id || 'SEALED'}</strong></div>
                <div style="margin-top:2px;">SHA-256 Digest: <strong style="color:var(--text-primary);">${ex.sha256_digest || '—'}</strong></div>
                <div style="margin-top:2px;">Causality Chain: <strong style="color:var(--text-primary);">${ex.causality_chain_id || '—'}</strong></div>
              </div>

              <div style="display:flex; justify-content:flex-end;">
                <button class="btn btn-primary" onclick="window.McpWorkspace.verifyExecution('${ex.execution_id}')">
                  Trigger Independent Physical Verification
                </button>
              </div>
            </div>
          </div>
        `;
      } catch (err) {
        alert('Failed to load trace: ' + err.message);
      }
    }

    async verifyExecution(execId) {
      try {
        const res = await fetch(`/api/mcp/executions/${execId}/verify`, { method: 'POST' }).then(r => r.json());
        alert(res.success ? '✓ Independent physical verification confirmed external state mutation!' : 'Verification failed: State not observed.');
        document.getElementById('mcpModalContainer').innerHTML = '';
        await this.render();
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    async readResource(resId) {
      try {
        const res = await fetch('/api/mcp/resources/read', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ resource_id: resId })
        }).then(r => r.json());

        if (res.success) {
          alert(`✓ Resource Content (Sanitized):\n${JSON.stringify(res.content, null, 2)}`);
        } else {
          alert('Failed to read resource: ' + (res.error || 'Blocked by firewall'));
        }
      } catch (err) {
        alert('Error: ' + err.message);
      }
    }

    openPublishModal() {
      alert('To publish a sovereign ZONATA capability to the MCP Server endpoint, select a certified capability from the Capability Registry in Settings or Org Workspace.');
    }

    escape(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }
  }

  // Register on window
  window.McpWorkspace = new McpWorkspaceManager();
})();
