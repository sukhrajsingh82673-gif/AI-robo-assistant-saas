/**
 * ZONATA — Plugins, Connections & Connectors Workspace
 * Comprehensive integration center strictly distinguishing:
 * - Plugins (installable capabilities)
 * - Connections (authenticated external systems like PMS, ERP, CRM)
 * - Connectors (data translation and schema mapping layer)
 */

(function() {
  'use strict';

  class PluginsWorkspaceManager {
    constructor() {
      this.activeTab = 'connections'; // 'connections' | 'plugins' | 'connectors'
      this.plugins = [];
      this.connections = [];
      this.loading = false;
      this.selectedConnection = null;
    }

    async render(containerId = 'view-plugins') {
      const container = document.getElementById(containerId);
      if (!container) return;

      this.loading = true;
      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Loading Plugins, Connections & Connectors Hub...</div>
        </div>
      `;

      try {
        await Promise.all([
          this.loadPlugins(),
          this.loadConnections()
        ]);
        this.renderWorkspace(container);
      } catch (err) {
        console.error('Failed to load plugins workspace:', err);
        container.innerHTML = `
          <div style="padding:40px; text-align:center;">
            <h3>Unable to load Integration Hub</h3>
            <p style="color:var(--text-muted);">${err.message}</p>
            <button class="btn-primary" onclick="window.PluginsWorkspace.render()">Retry</button>
          </div>
        `;
      } finally {
        this.loading = false;
      }
    }

    async loadPlugins() {
      const res = await fetch('/api/plugins');
      if (res.ok) {
        const data = await res.json();
        this.plugins = data.plugins || [];
      }
    }

    async loadConnections() {
      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : null;
      const url = companyId ? `/api/connections?company_id=${encodeURIComponent(companyId)}` : '/api/connections';
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        this.connections = data.connections || [];
      }
    }

    renderWorkspace(container) {
      container.innerHTML = `
        <div class="plugins-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- 1. Integration Hub Header -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Platform Integration</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Cryptographic Isolation Enforced
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                Plugins, Connections & Connectors
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Connect external enterprise systems (PMS, ERP, CRM), install platform plugins, and govern schema translation pipelines.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn-primary" onclick="window.PluginsWorkspace.openAddConnectionModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                + Connect External Service
              </button>
            </div>
          </div>

          <!-- 2. Subnav Tabs (Conceptual Separation: Connections, Plugins, Connectors) -->
          <div class="plugins-subnav" style="display:flex; gap:8px; border-bottom:1px solid var(--border-color); padding-bottom:2px;">
            ${[
              { id: 'connections', label: `🔗 External Connections (${this.connections.length})` },
              { id: 'plugins', label: `📦 System Plugins (${this.plugins.length})` },
              { id: 'connectors', label: '🔄 Connectors & Field Mappings' }
            ].map(t => `
              <button 
                class="subnav-tab ${this.activeTab === t.id ? 'active' : ''}" 
                style="padding:10px 18px; font-size:13.5px; font-weight:600; border:none; background:none; color:${this.activeTab===t.id?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${this.activeTab===t.id?'var(--accent-blue)':'transparent'}; cursor:pointer;" 
                onclick="window.PluginsWorkspace.switchTab('${t.id}')">
                ${t.label}
              </button>
            `).join('')}
          </div>

          <!-- 3. Active Tab View Content -->
          <div class="plugins-tab-content-area">
            ${this.renderActiveTabContent()}
          </div>

        </div>
      `;
    }

    switchTab(tabId) {
      this.activeTab = tabId;
      const container = document.getElementById('view-plugins');
      if (container) this.renderWorkspace(container);
    }

    renderActiveTabContent() {
      switch (this.activeTab) {
        case 'plugins':
          return this.renderPluginsTab();
        case 'connectors':
          return this.renderConnectorsTab();
        case 'connections':
        default:
          return this.renderConnectionsTab();
      }
    }

    // =========================================================================
    // Tab 1: External Connections
    // =========================================================================
    renderConnectionsTab() {
      if (this.connections.length === 0) {
        return `
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:40px; text-align:center;">
            <div style="font-size:32px; margin-bottom:10px;">🔌</div>
            <h3>No External Connections Configured</h3>
            <p style="color:var(--text-muted); max-width:480px; margin:0 auto 16px;">
              Connect your Hospitality PMS, Accounting ERP, or Commercial CRM to ingest real operational data into ZONATA.
            </p>
            <button class="btn-primary" onclick="window.PluginsWorkspace.openAddConnectionModal()">+ Connect First Service</button>
          </div>
        `;
      }

      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(360px, 1fr)); gap:18px;">
          ${this.connections.map(c => {
            const healthColor = c.health_score > 90 ? '#10b981' : c.health_score > 70 ? '#f59e0b' : '#ef4444';
            const permLevel = c.permission_scope?.level || 'READ_ONLY_VISIBILITY';

            return `
              <div class="connection-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:var(--shadow-sm);">
                <div>
                  <!-- Header row -->
                  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                    <div>
                      <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:18px;">${this.getServiceIcon(c.service_type)}</span>
                        <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
                          ${this.escape(c.name)}
                        </h3>
                      </div>
                      <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">
                        ${c.service_type} • Adapter: <code>${c.connector_adapter}</code>
                      </div>
                    </div>
                    <span class="badge ${c.auth_status==='CONNECTED'?'badge-emerald':'badge-amber'}">
                      ${c.auth_status}
                    </span>
                  </div>

                  <!-- Telemetry Meters -->
                  <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; background:var(--bg-surface-hover); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:10px 14px; margin:14px 0; font-size:12.5px;">
                    <div>
                      <span style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Health Score</span>
                      <div style="font-weight:700; color:${healthColor}; margin-top:2px;">
                        ${c.health_score}%
                      </div>
                    </div>
                    <div>
                      <span style="color:var(--text-muted); font-size:11px; text-transform:uppercase;">Latency</span>
                      <div style="font-weight:700; color:var(--text-primary); margin-top:2px;">
                        ${c.latency_ms} ms
                      </div>
                    </div>
                  </div>

                  <!-- Permission and Security Ceiling -->
                  <div style="font-size:12px; color:var(--text-secondary); margin-bottom:14px;">
                    <div>Permission Level: <strong style="color:var(--accent-blue);">${permLevel}</strong></div>
                    <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">
                      Endpoint: <code style="font-size:10.5px;">${this.escape(c.endpoint_url || 'https://api.internal/v1')}</code>
                    </div>
                  </div>
                </div>

                <!-- Action Toolbar -->
                <div style="display:flex; justify-content:space-between; align-items:center; pt:12px; border-top:1px solid var(--border-color); padding-top:12px;">
                  <button class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="window.PluginsWorkspace.testConnection('${c.connection_id}')">
                    ⚡ Test Ping
                  </button>
                  <button class="btn-primary" style="font-size:12px; padding:6px 14px;" onclick="window.PluginsWorkspace.syncConnection('${c.connection_id}')">
                    🔄 Sync Now
                  </button>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    // =========================================================================
    // Tab 2: System Plugins Catalog
    // =========================================================================
    renderPluginsTab() {
      return `
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(360px, 1fr)); gap:18px;">
          ${this.plugins.map(p => {
            return `
              <div class="plugin-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                    <div>
                      <span class="badge badge-subtle" style="font-size:10.5px; text-transform:uppercase;">${p.category}</span>
                      <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:6px 0 2px 0;">
                        ${this.escape(p.name)}
                      </h3>
                      <div style="font-size:11.5px; color:var(--text-muted);">v${p.version} • Author: ${p.author}</div>
                    </div>
                    <span class="badge ${p.enabled ? 'badge-emerald' : p.installed ? 'badge-blue' : 'badge-subtle'}">
                      ${p.enabled ? 'Active' : p.installed ? 'Installed' : 'Available'}
                    </span>
                  </div>

                  <p style="font-size:12.5px; color:var(--text-secondary); margin:10px 0 14px 0; line-height:1.45;">
                    ${this.escape(p.description)}
                  </p>

                  <!-- Capabilities Tags -->
                  <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:16px;">
                    ${(p.capabilities || []).map(cap => `
                      <span style="font-size:11px; background:var(--bg-surface-hover); border:1px solid var(--border-color); padding:2px 8px; border-radius:4px; font-family:var(--font-mono);">
                        ${cap}
                      </span>
                    `).join('')}
                  </div>
                </div>

                <!-- Install / Enable Actions -->
                <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-color); padding-top:12px;">
                  ${p.installed ? `
                    <div style="display:flex; align-items:center; gap:8px;">
                      <label class="toggle-switch" style="cursor:pointer;">
                        <input type="checkbox" ${p.enabled ? 'checked' : ''} onchange="window.PluginsWorkspace.toggleEnable('${p.plugin_id}', this.checked)" />
                        <span class="toggle-slider"></span>
                      </label>
                      <span style="font-size:12px; color:var(--text-secondary);">${p.enabled ? 'Enabled' : 'Disabled'}</span>
                    </div>
                    <button class="btn-secondary" style="font-size:11.5px; color:#ef4444;" onclick="window.PluginsWorkspace.toggleInstall('${p.plugin_id}', false)">
                      Uninstall
                    </button>
                  ` : `
                    <div></div>
                    <button class="btn-primary" style="font-size:12px; padding:6px 14px;" onclick="window.PluginsWorkspace.toggleInstall('${p.plugin_id}', true)">
                      Install Plugin
                    </button>
                  `}
                </div>
              </div>
            `;
          }).join('')}
        </div>
      `;
    }

    // =========================================================================
    // Tab 3: Connectors & Field Mapping Layer
    // =========================================================================
    renderConnectorsTab() {
      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:24px; display:flex; flex-direction:column; gap:20px;">
          <div>
            <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0 0 4px 0;">
              Canonical Entity Transformation & Schema Mapping
            </h3>
            <p style="font-size:13px; color:var(--text-secondary); margin:0;">
              Connectors normalize external vendor schemas into ZONATA's verified epistemic knowledge graph and accounting ledger.
            </p>
          </div>

          <div class="horizontal-scroll-container">
            <div style="min-width:680px; display:flex; flex-direction:column; gap:14px;">
              ${this.connections.map(c => {
                const mappings = c.field_mappings || {};

                return `
                  <div style="border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; background:var(--bg-surface-hover);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                      <div>
                        <span style="font-size:14px; font-weight:700; color:var(--text-primary);">${this.escape(c.name)}</span>
                        <span class="badge badge-subtle" style="margin-left:8px;">${c.service_type}</span>
                      </div>
                      <span style="font-size:11.5px; color:var(--accent-blue); font-weight:600;">Adapter: ${c.connector_adapter}</span>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr auto 1fr; gap:12px; align-items:center; font-size:12px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:8px;">
                      <div>External Vendor Field</div>
                      <div>Transform</div>
                      <div>ZONATA Canonical Entity Field</div>
                    </div>

                    <div style="display:flex; flex-direction:column; gap:6px;">
                      ${Object.entries(mappings).map(([ext, zon]) => `
                        <div style="display:grid; grid-template-columns:1fr auto 1fr; gap:12px; align-items:center; background:var(--bg-surface); padding:8px 12px; border-radius:var(--radius-sm); border:1px solid var(--border-color); font-size:12.5px;">
                          <div><code>${ext}</code></div>
                          <div style="color:var(--text-muted);">➔</div>
                          <div><strong style="color:var(--accent-emerald);">${zon}</strong></div>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        </div>
      `;
    }

    getServiceIcon(serviceType) {
      switch (serviceType) {
        case 'PMS': return '🏨';
        case 'ERP': return '📊';
        case 'CRM': return '👥';
        case 'SLACK': return '💬';
        case 'BANKING': return '🏦';
        default: return '🔌';
      }
    }

    async toggleInstall(pluginId, install) {
      try {
        const res = await fetch(`/api/plugins/${pluginId}/toggle-install`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ install })
        });
        if (res.ok) {
          await this.loadPlugins();
          const container = document.getElementById('view-plugins');
          if (container) this.renderWorkspace(container);
        }
      } catch (e) {
        console.error('Failed to toggle install:', e);
      }
    }

    async toggleEnable(pluginId, enable) {
      try {
        const res = await fetch(`/api/plugins/${pluginId}/toggle-enable`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enable })
        });
        if (res.ok) {
          await this.loadPlugins();
          const container = document.getElementById('view-plugins');
          if (container) this.renderWorkspace(container);
        }
      } catch (e) {
        console.error('Failed to toggle enable:', e);
      }
    }

    async testConnection(connectionId) {
      try {
        const res = await fetch(`/api/connections/${connectionId}/test`, { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          alert(`Connection verified: Latency ${data.latency_ms}ms, Health ${data.health_score}%, Handshake Passed.`);
          await this.loadConnections();
          const container = document.getElementById('view-plugins');
          if (container) this.renderWorkspace(container);
        }
      } catch (e) {
        alert('Test connection ping failed.');
      }
    }

    async syncConnection(connectionId) {
      try {
        const res = await fetch(`/api/connections/${connectionId}/sync`, { method: 'POST' });
        if (res.ok) {
          const data = await res.json();
          alert(`Synchronized clean: ${data.records_synced} records translated and normalized into ZONATA.`);
          await this.loadConnections();
          const container = document.getElementById('view-plugins');
          if (container) this.renderWorkspace(container);
        }
      } catch (e) {
        alert('Sync failed.');
      }
    }

    openAddConnectionModal() {
      const modalBody = document.getElementById('modalBody');
      const modalTitle = document.getElementById('modalTitle');
      const overlay = document.getElementById('modalOverlay');

      if (!modalBody || !overlay) return;

      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';

      modalTitle.textContent = 'Connect External Enterprise Service';
      modalBody.innerHTML = `
        <form id="addConnectionForm" onsubmit="event.preventDefault(); window.PluginsWorkspace.submitAddConnection();" style="display:flex; flex-direction:column; gap:14px;">
          <div class="form-group">
            <label class="form-label">Connection Name</label>
            <input type="text" id="connFormName" class="form-input" placeholder="e.g. Oracle Opera PMS Production" required />
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Service Type</label>
              <select id="connFormType" class="form-input">
                <option value="PMS">Hospitality PMS</option>
                <option value="ERP">Accounting / ERP</option>
                <option value="CRM">Sales & Marketing CRM</option>
                <option value="SLACK">Messaging & Slack</option>
                <option value="BANKING">Banking & Payments</option>
                <option value="CUSTOM_API">Custom Enterprise REST API</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Permission Enforcement</label>
              <select id="connFormPerm" class="form-input">
                <option value="READ_ONLY_VISIBILITY">READ_ONLY_VISIBILITY (Safest)</option>
                <option value="SCOPED_MUTATION">SCOPED_MUTATION (Audited Write)</option>
                <option value="FULL_ADMIN">FULL_ADMIN</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">API Endpoint URL</label>
            <input type="url" id="connFormUrl" class="form-input" placeholder="https://api.service.enterprise.com/v1" required />
          </div>

          <div class="form-group">
            <label class="form-label">Authentication Token / Client Secret (Vault Encrypted)</label>
            <input type="password" id="connFormSecret" class="form-input" placeholder="••••••••••••••••••••••••" required />
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
            <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Establish Connection</button>
          </div>
        </form>
      `;

      overlay.style.display = 'flex';
    }

    async submitAddConnection() {
      const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
      const name = document.getElementById('connFormName').value.trim();
      const service_type = document.getElementById('connFormType').value;
      const permission_level = document.getElementById('connFormPerm').value;
      const endpoint_url = document.getElementById('connFormUrl').value.trim();

      try {
        const res = await fetch('/api/connections', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_id: companyId,
            name,
            service_type,
            permission_level,
            endpoint_url
          })
        });

        if (res.ok) {
          closeModal();
          await this.loadConnections();
          const container = document.getElementById('view-plugins');
          if (container) this.renderWorkspace(container);
        } else {
          alert('Failed to establish connection.');
        }
      } catch (err) {
        console.error('Add connection failed:', err);
      }
    }

    escape(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }
  }

  window.PluginsWorkspace = new PluginsWorkspaceManager();
})();
