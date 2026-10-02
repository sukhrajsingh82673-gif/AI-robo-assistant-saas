/**
 * ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
 * Project 10: Nango — Governed External System Connectivity & Integration Center
 *
 * Interactive SPA Cockpit for multi-tenant SaaS & enterprise system connections,
 * OAuth lifecycle, data synchronization, webhooks, capability governance,
 * rate limits, security audit, and canonical scenario validation.
 */

class NangoWorkspaceManager {
  constructor() {
    this.activeTab = 'connections';
    this.metrics = null;
    this.providers = [];
    this.connections = [];
    this.syncJobs = [];
    this.syncRecords = [];
    this.webhooks = [];
    this.capabilities = [];
    this.containerId = null;
    this.selectedConnection = null;
    this.scenarioLogs = {};
    this.isRunningScenario = false;
  }

  async render(containerId) {
    this.containerId = containerId || this.containerId || 'view-nango-integrations';
    const container = document.getElementById(this.containerId);
    if (!container) return;

    container.innerHTML = `
      <div class="nango-loading-shell" style="padding: 3rem; text-align: center; color: var(--text-muted);">
        <div class="spinner" style="margin-bottom: 1rem;"></div>
        <div>Loading Governed External Integrations & SaaS Engine (Nango)...</div>
      </div>
    `;

    await this.fetchData();
    this.renderWorkspace(container);
  }

  async fetchData() {
    try {
      const [metRes, provRes, connRes, syncJobRes, syncRecRes, whRes, capRes] = await Promise.all([
        fetch('/api/nango/metrics').then(r => r.json()).catch(() => ({ metrics: {} })),
        fetch('/api/nango/providers').then(r => r.json()).catch(() => ({ providers: [] })),
        fetch('/api/nango/connections').then(r => r.json()).catch(() => ({ connections: [] })),
        fetch('/api/nango/sync-jobs').then(r => r.json()).catch(() => ({ sync_jobs: [] })),
        fetch('/api/nango/sync-records?limit=20').then(r => r.json()).catch(() => ({ sync_records: [] })),
        fetch('/api/nango/webhooks?limit=20').then(r => r.json()).catch(() => ({ webhooks: [] })),
        fetch('/api/nango/capabilities').then(r => r.json()).catch(() => ({ capabilities: [] }))
      ]);

      this.metrics = metRes.metrics || {};
      this.providers = provRes.providers || [];
      this.connections = connRes.connections || [];
      this.syncJobs = syncJobRes.sync_jobs || [];
      this.syncRecords = syncRecRes.sync_records || [];
      this.webhooks = whRes.webhooks || [];
      this.capabilities = capRes.capabilities || [];
    } catch (e) {
      console.error('Failed to load Nango workspace data:', e);
    }
  }

  renderWorkspace(container) {
    const m = this.metrics || {};

    container.innerHTML = `
      <div class="nango-workspace" style="display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem;">
        
        <!-- Header Banner & Top Metrics -->
        <div class="workspace-header-card" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
            <div>
              <div style="display: flex; align-items: center; gap: 0.75rem;">
                <h2 style="margin: 0; font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">External System Integrations & Connectivity</h2>
                <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                  NANGO ENGINE ${m.nango_version || '0.64.0'} ONLINE
                </span>
                <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid #3b82f6; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                  ELv2 GOVERNED RUNTIME
                </span>
              </div>
              <p style="margin: 0.35rem 0 0 0; color: var(--text-secondary); font-size: 0.875rem;">
                Governed connectivity connecting AI CEO, Agency Swarm, and LangGraph/Temporal to 1,000+ real business systems with secret isolation and Merkle evidence sealing.
              </p>
            </div>
            <div style="display: flex; gap: 0.5rem;">
              <button class="btn btn-secondary btn-sm" onclick="window.nangoWorkspace.render()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;"><path d="M23 4v6h-6"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                Refresh Live State
              </button>
              <button class="btn btn-primary btn-sm" onclick="window.nangoWorkspace.openConnectModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Connect System
              </button>
            </div>
          </div>

          <!-- KPI HUD -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem;">
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Connections</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #3b82f6; margin-top: 0.25rem;">${m.active_connections ?? 0} <span style="font-size: 0.8rem; font-weight: normal; color: var(--text-muted);">/ ${m.total_connections ?? 0}</span></div>
            </div>
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Healthy Systems</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #10b981; margin-top: 0.25rem;">${m.healthy_connections ?? 0}</div>
            </div>
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">API Operations</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #8b5cf6; margin-top: 0.25rem;">${m.total_executions ?? 0}</div>
            </div>
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Success Rate</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #10b981; margin-top: 0.25rem;">${m.success_rate_pct ?? 100}%</div>
            </div>
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Synced Records</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #06b6d4; margin-top: 0.25rem;">${m.total_sync_records ?? 0}</div>
            </div>
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Webhooks Ingested</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #ec4899; margin-top: 0.25rem;">${m.webhook_events ?? 0}</div>
            </div>
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Pending Approvals</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: ${m.pending_approvals > 0 ? '#f59e0b' : '#10b981'}; margin-top: 0.25rem;">${m.pending_approvals ?? 0}</div>
            </div>
            <div class="kpi-mini-card" style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem;">
              <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">Avg Latency</div>
              <div style="font-size: 1.35rem; font-weight: 700; color: #64748b; margin-top: 0.25rem;">${m.average_latency_ms ?? 0}ms</div>
            </div>
          </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="workspace-tabs" style="display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; overflow-x: auto;">
          ${this.renderTabButton('connections', 'Connected Systems', this.connections.length)}
          ${this.renderTabButton('catalog', 'Integration Catalog', this.providers.length)}
          ${this.renderTabButton('sync', 'Data Sync Engine', this.syncJobs.length)}
          ${this.renderTabButton('webhooks', 'Webhooks Gateway', this.webhooks.length)}
          ${this.renderTabButton('capabilities', 'Capability Registry', this.capabilities.length)}
          ${this.renderTabButton('security', 'Security & Rate Limits', m.security_events || 0)}
          ${this.renderTabButton('scenarios', 'Canonical Scenarios (1-10)', '10')}
        </div>

        <!-- Tab Body Content -->
        <div class="workspace-tab-body">
          ${this.renderActiveTabContent()}
        </div>
      </div>
    `;
  }

  renderTabButton(tabKey, label, count) {
    const isActive = this.activeTab === tabKey;
    const activeStyle = isActive
      ? 'background: var(--bg-hover, #2563eb); color: #fff; font-weight: 600;'
      : 'background: transparent; color: var(--text-secondary);';
    return `
      <button class="btn btn-sm" style="${activeStyle} border-radius: 6px; padding: 0.4rem 0.8rem; border: none; cursor: pointer; display: flex; align-items: center; gap: 0.4rem;"
        onclick="window.nangoWorkspace.switchTab('${tabKey}')">
        <span>${label}</span>
        ${count !== undefined ? `<span style="background: rgba(0,0,0,0.25); padding: 0.1rem 0.4rem; border-radius: 10px; font-size: 0.7rem;">${count}</span>` : ''}
      </button>
    `;
  }

  switchTab(tabKey) {
    this.activeTab = tabKey;
    const container = document.getElementById(this.containerId);
    if (container) this.renderWorkspace(container);
  }

  renderActiveTabContent() {
    switch (this.activeTab) {
      case 'connections': return this.renderConnectionsTab();
      case 'catalog': return this.renderCatalogTab();
      case 'sync': return this.renderSyncTab();
      case 'webhooks': return this.renderWebhooksTab();
      case 'capabilities': return this.renderCapabilitiesTab();
      case 'security': return this.renderSecurityTab();
      case 'scenarios': return this.renderScenariosTab();
      default: return this.renderConnectionsTab();
    }
  }

  // --- 1. Connections Tab ---
  renderConnectionsTab() {
    if (this.connections.length === 0) {
      return `
        <div style="background: var(--bg-card); border: 1px dashed var(--border-color); border-radius: 12px; padding: 3rem; text-align: center;">
          <h3 style="margin: 0 0 0.5rem 0; color: var(--text-primary);">No External Systems Connected Yet</h3>
          <p style="color: var(--text-secondary); max-width: 450px; margin: 0 auto 1.5rem auto; font-size: 0.875rem;">
            Connect your company's CRM, ERP, HRIS, or Accounting platform to enable governed AI workforce automation.
          </p>
          <button class="btn btn-primary" onclick="window.nangoWorkspace.switchTab('catalog')">
            Browse Integration Catalog
          </button>
        </div>
      `;
    }

    return `
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem;">
        ${this.connections.map(c => `
          <div class="connection-card" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
                <div>
                  <h4 style="margin: 0; font-size: 1.1rem; color: var(--text-primary); text-transform: capitalize;">${c.provider_name || c.provider_id}</h4>
                  <span style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">${c.provider_category || 'SaaS'}</span>
                </div>
                <div style="display: flex; gap: 0.35rem;">
                  <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 4px;">
                    ${c.health_status}
                  </span>
                  <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 4px;">
                    ${c.auth_type}
                  </span>
                </div>
              </div>

              <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
                <div><strong>Connection ID:</strong> <code style="color: #60a5fa;">${c.connection_id}</code></div>
                <div><strong>Credential Ref:</strong> <code style="color: #f59e0b;">${c.credential_ref}</code></div>
                <div><strong>Company:</strong> ${c.company_id}</div>
                <div><strong>Granted Scopes:</strong> ${(c.granted_scopes || []).join(', ') || 'default'}</div>
              </div>
            </div>

            <div style="border-top: 1px solid var(--border-color); padding-top: 0.75rem; margin-top: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 0.7rem; color: var(--text-muted);">
                Checked: ${new Date((c.last_health_check || c.created_at) * 1000).toLocaleTimeString()}
              </span>
              <div style="display: flex; gap: 0.4rem;">
                <button class="btn btn-secondary btn-sm" onclick="window.nangoWorkspace.testConnection('${c.connection_id}')">Test</button>
                <button class="btn btn-primary btn-sm" onclick="window.nangoWorkspace.triggerSyncModal('${c.connection_id}', '${c.provider_id}')">Sync</button>
                <button class="btn btn-danger btn-sm" onclick="window.nangoWorkspace.disconnectConnection('${c.connection_id}')">Disconnect</button>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  // --- 2. Catalog Tab ---
  renderCatalogTab() {
    return `
      <div>
        <div style="margin-bottom: 1rem; color: var(--text-secondary); font-size: 0.875rem;">
          Supported Enterprise SaaS Providers & Capability Protocols:
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;">
          ${this.providers.map(p => `
            <div class="provider-card" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem; display: flex; flex-direction: column; justify-content: space-between;">
              <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                  <h4 style="margin: 0; font-size: 1.1rem; color: var(--text-primary);">${p.name}</h4>
                  <span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #818cf8; font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 4px;">
                    ${p.category}
                  </span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                  Auth: <code>${p.auth_mode}</code> | Provider: <code>${p.provider_id}</code>
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 1rem;">
                  ${p.docs_url ? `<a href="${p.docs_url}" target="_blank" style="color: #3b82f6; text-decoration: none;">API Documentation &rarr;</a>` : ''}
                </div>
              </div>
              <button class="btn btn-primary btn-sm" style="width: 100%;" onclick="window.nangoWorkspace.connectProvider('${p.provider_id}')">
                Connect ${p.name}
              </button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // --- 3. Sync Tab ---
  renderSyncTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <!-- Sync Jobs -->
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
          <h4 style="margin: 0 0 1rem 0; color: var(--text-primary);">Data Synchronization Jobs</h4>
          <div style="overflow-x: auto;">
            <table class="table" style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-muted); text-align: left;">
                  <th style="padding: 0.5rem;">Job ID</th>
                  <th style="padding: 0.5rem;">Provider</th>
                  <th style="padding: 0.5rem;">Model</th>
                  <th style="padding: 0.5rem;">Type</th>
                  <th style="padding: 0.5rem;">Status</th>
                  <th style="padding: 0.5rem;">Processed</th>
                  <th style="padding: 0.5rem;">Cursor</th>
                  <th style="padding: 0.5rem;">Executed</th>
                </tr>
              </thead>
              <tbody>
                ${this.syncJobs.length === 0 ? `<tr><td colspan="8" style="padding: 1rem; text-align: center; color: var(--text-muted);">No synchronization jobs recorded yet.</td></tr>` : ''}
                ${this.syncJobs.map(j => `
                  <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 0.5rem;"><code>${j.sync_job_id}</code></td>
                    <td style="padding: 0.5rem; text-transform: capitalize;">${j.provider_id}</td>
                    <td style="padding: 0.5rem;"><strong>${j.model_name}</strong></td>
                    <td style="padding: 0.5rem;">${j.sync_type}</td>
                    <td style="padding: 0.5rem;"><span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 0.7rem; padding: 0.1rem 0.35rem; border-radius: 4px;">${j.status}</span></td>
                    <td style="padding: 0.5rem;">${j.records_processed} recs</td>
                    <td style="padding: 0.5rem;"><code>${j.cursor || 'N/A'}</code></td>
                    <td style="padding: 0.5rem;">${new Date((j.last_run_at || j.created_at) * 1000).toLocaleTimeString()}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Synced Records with Provenance -->
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
          <h4 style="margin: 0 0 1rem 0; color: var(--text-primary);">Synchronized Records & Immutable Provenance Ledger</h4>
          <div style="overflow-x: auto;">
            <table class="table" style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
              <thead>
                <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-muted); text-align: left;">
                  <th style="padding: 0.5rem;">Record ID</th>
                  <th style="padding: 0.5rem;">Provider</th>
                  <th style="padding: 0.5rem;">Object Type</th>
                  <th style="padding: 0.5rem;">External ID</th>
                  <th style="padding: 0.5rem;">Payload Snapshot</th>
                  <th style="padding: 0.5rem;">Provenance Metadata</th>
                </tr>
              </thead>
              <tbody>
                ${this.syncRecords.length === 0 ? `<tr><td colspan="6" style="padding: 1rem; text-align: center; color: var(--text-muted);">No records synced yet.</td></tr>` : ''}
                ${this.syncRecords.map(r => `
                  <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 0.5rem;"><code>${r.record_id}</code></td>
                    <td style="padding: 0.5rem; text-transform: capitalize;">${r.provider_id}</td>
                    <td style="padding: 0.5rem;"><strong>${r.object_type}</strong></td>
                    <td style="padding: 0.5rem;"><code>${r.external_id}</code></td>
                    <td style="padding: 0.5rem;"><pre style="margin: 0; font-size: 0.7rem; color: #a78bfa; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${JSON.stringify(r.data_payload)}</pre></td>
                    <td style="padding: 0.5rem;"><pre style="margin: 0; font-size: 0.7rem; color: #34d399; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${JSON.stringify(r.provenance_meta)}</pre></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  // --- 4. Webhooks Tab ---
  renderWebhooksTab() {
    return `
      <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
        <h4 style="margin: 0 0 1rem 0; color: var(--text-primary);">Governed Inbound Webhooks Stream</h4>
        <div style="overflow-x: auto;">
          <table class="table" style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
            <thead>
              <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-muted); text-align: left;">
                <th style="padding: 0.5rem;">Webhook ID</th>
                <th style="padding: 0.5rem;">Provider</th>
                <th style="padding: 0.5rem;">Event Type</th>
                <th style="padding: 0.5rem;">Status</th>
                <th style="padding: 0.5rem;">HMAC Signature Digest</th>
                <th style="padding: 0.5rem;">Payload Snapshot</th>
                <th style="padding: 0.5rem;">Received At</th>
              </tr>
            </thead>
            <tbody>
              ${this.webhooks.length === 0 ? `<tr><td colspan="7" style="padding: 1rem; text-align: center; color: var(--text-muted);">No inbound webhooks received yet.</td></tr>` : ''}
              ${this.webhooks.map(w => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                  <td style="padding: 0.5rem;"><code>${w.webhook_id}</code></td>
                  <td style="padding: 0.5rem; text-transform: capitalize;">${w.provider_id}</td>
                  <td style="padding: 0.5rem;"><strong>${w.event_type}</strong></td>
                  <td style="padding: 0.5rem;">
                    <span class="badge" style="background: ${w.status === 'PROCESSED' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'}; color: ${w.status === 'PROCESSED' ? '#10b981' : '#ef4444'}; font-size: 0.7rem; padding: 0.1rem 0.35rem; border-radius: 4px;">
                      ${w.status}
                    </span>
                  </td>
                  <td style="padding: 0.5rem;"><code>${(w.payload_digest || '').substring(0, 16)}...</code></td>
                  <td style="padding: 0.5rem;"><pre style="margin: 0; font-size: 0.7rem; color: #a78bfa; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${JSON.stringify(w.payload_data)}</pre></td>
                  <td style="padding: 0.5rem;">${new Date(w.created_at * 1000).toLocaleTimeString()}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  // --- 5. Capabilities Tab ---
  renderCapabilitiesTab() {
    return `
      <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
        <h4 style="margin: 0 0 1rem 0; color: var(--text-primary);">Governed Integration Capability Catalog</h4>
        <div style="overflow-x: auto;">
          <table class="table" style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
            <thead>
              <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-muted); text-align: left;">
                <th style="padding: 0.5rem;">Capability ID</th>
                <th style="padding: 0.5rem;">Provider</th>
                <th style="padding: 0.5rem;">Action Name</th>
                <th style="padding: 0.5rem;">Risk Class</th>
                <th style="padding: 0.5rem;">Required Role</th>
                <th style="padding: 0.5rem;">Required Scope</th>
                <th style="padding: 0.5rem;">Description</th>
              </tr>
            </thead>
            <tbody>
              ${this.capabilities.map(c => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                  <td style="padding: 0.5rem;"><code>${c.capability_id}</code></td>
                  <td style="padding: 0.5rem; text-transform: capitalize;">${c.provider_id}</td>
                  <td style="padding: 0.5rem;"><strong>${c.action_name}</strong></td>
                  <td style="padding: 0.5rem;">
                    <span class="badge" style="background: ${this.getRiskColor(c.risk_class)}; font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 4px;">
                      ${c.risk_class}
                    </span>
                  </td>
                  <td style="padding: 0.5rem;"><code>${c.required_role}</code></td>
                  <td style="padding: 0.5rem;"><code>${c.required_scope || 'default'}</code></td>
                  <td style="padding: 0.5rem; color: var(--text-secondary);">${c.description}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  getRiskColor(risk) {
    switch (risk) {
      case 'READ_ONLY': return 'rgba(16, 185, 129, 0.2); color: #10b981;';
      case 'LOW_RISK': return 'rgba(59, 130, 246, 0.2); color: #3b82f6;';
      case 'DATA_ENTRY': return 'rgba(99, 102, 241, 0.2); color: #818cf8;';
      case 'BUSINESS_MUTATION': return 'rgba(245, 158, 11, 0.2); color: #f59e0b;';
      case 'FINANCIAL': return 'rgba(236, 72, 153, 0.2); color: #ec4899;';
      case 'PRIVILEGED': return 'rgba(168, 85, 247, 0.2); color: #a855f7;';
      case 'DESTRUCTIVE':
      case 'IRREVERSIBLE': return 'rgba(239, 68, 68, 0.2); color: #ef4444;';
      default: return 'rgba(100, 116, 139, 0.2); color: #94a3b8;';
    }
  }

  // --- 6. Security Tab ---
  renderSecurityTab() {
    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
          <h4 style="margin: 0 0 1rem 0; color: var(--text-primary);">Integration Multi-Scope KillSwitch Controls</h4>
          <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">
            Emergency halt halts external mutations instantly across Global, Tenant, Company, Mission, Agent, Capability, Provider, or Connection scopes.
          </p>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button class="btn btn-danger btn-sm" onclick="window.nangoWorkspace.triggerKillswitch('PROVIDER', 'salesforce', 'halt')">Halt Salesforce</button>
            <button class="btn btn-danger btn-sm" onclick="window.nangoWorkspace.triggerKillswitch('PROVIDER', 'stripe', 'halt')">Halt Stripe</button>
            <button class="btn btn-danger btn-sm" onclick="window.nangoWorkspace.triggerKillswitch('PROVIDER', 'quickbooks', 'halt')">Halt QuickBooks</button>
            <button class="btn btn-secondary btn-sm" onclick="window.nangoWorkspace.triggerKillswitch('PROVIDER', 'salesforce', 'resume')">Resume Salesforce</button>
            <button class="btn btn-secondary btn-sm" onclick="window.nangoWorkspace.triggerKillswitch('PROVIDER', 'stripe', 'resume')">Resume Stripe</button>
            <button class="btn btn-secondary btn-sm" onclick="window.nangoWorkspace.triggerKillswitch('PROVIDER', 'quickbooks', 'resume')">Resume QuickBooks</button>
          </div>
        </div>

        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
          <h4 style="margin: 0 0 1rem 0; color: var(--text-primary);">Context Firewall & Rate Limits</h4>
          <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
            <div><strong>Sliding Window Quota:</strong> 120 requests/minute per provider endpoint with fairness queueing.</div>
            <div><strong>Credential Isolation:</strong> Secrets vaulted; AI agents only handle opaque handles (e.g. <code>cred_nango_salesforce_...</code>).</div>
            <div><strong>Prompt Injection Defense:</strong> Inbound payloads scanned for instruction overrides before passing to models.</div>
            <div><strong>Non-Idempotent Mutations:</strong> Unknown outcomes trigger <code>UNKNOWN_OUTCOME</code> state reconciliation, prohibiting blind replays.</div>
          </div>
        </div>
      </div>
    `;
  }

  // --- 7. Canonical Scenarios Tab ---
  renderScenariosTab() {
    const scenarios = [
      { id: 'TEST_01', name: 'Scenario 01', desc: 'Standard Connection Lifecycle & Governed Read (Salesforce)' },
      { id: 'TEST_02', name: 'Scenario 02', desc: 'Business Mutation with Idempotency Key (CREATE_LEAD)' },
      { id: 'TEST_03', name: 'Scenario 03', desc: 'Human-in-the-Loop Financial Mutation Escalation (Stripe Invoice)' },
      { id: 'TEST_04', name: 'Scenario 04', desc: 'Multi-Scope KillSwitch Enforcement (Immediate Halt)' },
      { id: 'TEST_05', name: 'Scenario 05', desc: 'Context Firewall & Secret Credential Scrubbing' },
      { id: 'TEST_06', name: 'Scenario 06', desc: 'Inbound Webhook Verification & Replay Attack Defense' },
      { id: 'TEST_07', name: 'Scenario 07', desc: 'Governed Data Synchronization & Provenance Ledger' },
      { id: 'TEST_08', name: 'Scenario 08', desc: 'Unknown Outcome & State Reconciliation Protocol' },
      { id: 'TEST_09', name: 'Scenario 09', desc: 'Cross-Tenant Isolation Attack Defense' },
      { id: 'SECTION_95', name: 'Section 95', desc: 'Grand Acceptance Test (Full Onboarding: CRM, Accounting, Calendar, Email)' }
    ];

    return `
      <div style="display: flex; flex-direction: column; gap: 1.5rem;">
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
              <h4 style="margin: 0; color: var(--text-primary);">Canonical Verification Test Matrix</h4>
              <p style="margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.8rem;">
                Execute automated validation scenarios verifying governance, multi-tenant isolation, idempotency, and Merkle ledger sealing.
              </p>
            </div>
            <button class="btn btn-primary btn-sm" onclick="window.nangoWorkspace.runScenario('SECTION_95')">
              Run Grand Acceptance Test (Section 95)
            </button>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 0.75rem;">
            ${scenarios.map(s => `
              <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: 600; font-size: 0.85rem; color: var(--text-primary);">${s.name}</div>
                  <div style="font-size: 0.75rem; color: var(--text-muted);">${s.desc}</div>
                </div>
                <button class="btn btn-secondary btn-sm" onclick="window.nangoWorkspace.runScenario('${s.id}')">
                  Run
                </button>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Scenario Execution Log Viewer -->
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem;">
          <h4 style="margin: 0 0 0.75rem 0; color: var(--text-primary);">Scenario Execution Output & Evidence Log</h4>
          <pre id="nangoScenarioOutput" style="background: #090d16; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 1rem; color: #10b981; font-family: monospace; font-size: 0.75rem; max-height: 350px; overflow-y: auto; margin: 0;">
// Click any scenario above to execute and stream live cryptographic evidence output...
          </pre>
        </div>
      </div>
    `;
  }

  // --- Action Handlers ---
  async runScenario(scenarioId) {
    const out = document.getElementById('nangoScenarioOutput');
    if (out) out.textContent = `[*] Executing ${scenarioId} against ZONATA External Integration Gateway...\n`;

    try {
      const res = await fetch('/api/nango/demo/scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: scenarioId })
      }).then(r => r.json());

      if (out) {
        out.textContent = `[+] SCENARIO ${scenarioId} RESULT:\n\n` + JSON.stringify(res, null, 2);
      }
      await this.fetchData();
    } catch (e) {
      if (out) out.textContent = `[-] ERROR executing ${scenarioId}: ` + e.toString();
    }
  }

  async testConnection(connId) {
    try {
      const res = await fetch(`/api/nango/connections/${connId}/test`, { method: 'POST' }).then(r => r.json());
      alert(`Connection Test Result: ${res.message || 'OK'}`);
      await this.render();
    } catch (e) {
      alert('Failed to test connection: ' + e.toString());
    }
  }

  async triggerSyncModal(connId, provId) {
    const model = prompt(`Enter model to synchronize for ${provId} (e.g. contacts, invoices, leads):`, 'contacts');
    if (!model) return;
    try {
      const res = await fetch(`/api/nango/connections/${connId}/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: model, limit: 10 })
      }).then(r => r.json());
      alert(`Sync triggered successfully! Records processed: ${res.sync?.records_processed || 0}`);
      await this.render();
    } catch (e) {
      alert('Failed to trigger sync: ' + e.toString());
    }
  }

  async disconnectConnection(connId) {
    if (!confirm(`Are you sure you want to disconnect ${connId}? Scheduled syncs and actions will be suspended.`)) return;
    try {
      await fetch(`/api/nango/connections/${connId}`, { method: 'DELETE' });
      await this.render();
    } catch (e) {
      alert('Failed to disconnect: ' + e.toString());
    }
  }

  async connectProvider(provId) {
    try {
      const res = await fetch('/api/nango/connections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: provId })
      }).then(r => r.json());
      alert(`Successfully connected ${provId}! Connection ID: ${res.connection?.connection_id}`);
      this.activeTab = 'connections';
      await this.render();
    } catch (e) {
      alert('Failed to connect provider: ' + e.toString());
    }
  }

  async triggerKillswitch(scope, targetId, action) {
    try {
      await fetch('/api/nango/killswitch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scope, target_id: targetId, action })
      });
      alert(`KillSwitch ${action.toUpperCase()} updated for ${scope}:${targetId}`);
      await this.render();
    } catch (e) {
      alert('Failed to update killswitch: ' + e.toString());
    }
  }

  openConnectModal() {
    this.switchTab('catalog');
  }
}

// Global initialization
window.NangoWorkspaceManager = NangoWorkspaceManager;
window.nangoWorkspace = new NangoWorkspaceManager();
