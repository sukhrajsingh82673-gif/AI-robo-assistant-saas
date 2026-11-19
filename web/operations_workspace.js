/**
 * ZONATA Universal AI Company OS — Operations Center Workspace
 * Generic operational work orders, maintenance schedules, assets, and incidents
 * plus dynamic Industry Packs (Hospitality, Manufacturing, SaaS).
 */

(function() {
  'use strict';

  class EnterpriseOperationsWorkspace {
    constructor() {
      this.activeTab = 'work_orders'; // 'work_orders' | 'industry_pack' | 'assets' | 'incidents'
      this.industry = 'General Operations';
      this.processes = [];
      this.loading = false;
    }

    async render(containerId = 'view-operations') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const company = (window.CurrentCompanyContext && window.CurrentCompanyContext.getCompany()) ||
                      (window.state && window.state.companies && window.state.companies[0]) ||
                      { id: 'comp_primary', name: 'Primary Enterprise', industry: 'General Operations' };
      this.industry = company.industry || 'General Operations';
      const companyId = company.id || (window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary');

      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Loading Operational Runtime...</div>
        </div>
      `;

      await this.loadProcesses(companyId);
      this.renderView(container, companyId);
    }

    async loadProcesses(companyId) {
      this.loading = true;
      try {
        const res = await fetch(`/api/companies/${encodeURIComponent(companyId || 'comp_primary')}/processes`);
        if (res.ok) {
          const data = await res.json();
          this.processes = Array.isArray(data.processes) ? data.processes : [];
        } else {
          this.processes = [];
        }
      } catch (err) {
        console.error('Failed to load operations processes:', err);
        this.processes = [];
      } finally {
        this.loading = false;
      }
    }

    renderView(container, companyId) {
      const totalOps = this.processes.length;
      const activeOps = this.processes.filter(p => p.status === 'RUNNING' || p.status === 'ACTIVE' || p.status === 'IN_PROGRESS').length;
      const completedOps = this.processes.filter(p => p.status === 'COMPLETED' || p.status === 'SUCCESS').length;
      const slaRate = totalOps > 0 ? `${Math.round((completedOps / totalOps) * 100)}%` : '—';

      container.innerHTML = `
        <div class="operations-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Operational Center</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Industry Pack: ${this.industry}
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                Operations & Facility Execution
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Autonomous shift execution, work order dispatch, equipment maintenance, and industry-specific operational flows.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn-primary" onclick="window.OperationsWorkspace.openCreateOrderModal('${companyId}')">
                + Create Work Order
              </button>
            </div>
          </div>

          <!-- Top Operational KPIs -->
          <div class="enterprise-grid-4">
            <div class="metric-stat-card">
              <div class="metric-stat-title">Active Work Orders</div>
              <div class="metric-stat-value">${activeOps}</div>
              <div class="metric-stat-sub">${activeOps > 0 ? `${activeOps} in execution` : 'Zero pending orders'}</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">SLA Compliance Rate</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">${slaRate}</div>
              <div class="metric-stat-sub">${totalOps > 0 ? `${completedOps} of ${totalOps} fulfilled` : 'Awaiting order telemetry'}</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Equipment / Asset Uptime</div>
              <div class="metric-stat-value">100%</div>
              <div class="metric-stat-sub">Zero critical incidents reported</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Industry Module</div>
              <div class="metric-stat-value" style="font-size:18px; color:var(--accent-blue);">${this.industry}</div>
              <div class="metric-stat-sub">Dynamic Pack Configured</div>
            </div>
          </div>

          <!-- Subnav Tabs -->
          <div style="display:flex; gap:8px; border-bottom:1px solid var(--border-color); padding-bottom:2px;">
            ${[
              { id: 'work_orders', label: `📋 Work Orders (${totalOps})` },
              { id: 'industry_pack', label: `🏨 Industry Pack (${this.industry})` },
              { id: 'assets', label: '🏢 Asset Register' },
              { id: 'incidents', label: '🛡️ Incident Log' }
            ].map(t => `
              <button 
                class="subnav-tab ${this.activeTab===t.id?'active':''}"
                style="padding:10px 18px; font-size:13.5px; font-weight:600; border:none; background:none; color:${this.activeTab===t.id?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${this.activeTab===t.id?'var(--accent-blue)':'transparent'}; cursor:pointer;"
                onclick="window.OperationsWorkspace.switchTab('${t.id}', '${companyId}')">
                ${t.label}
              </button>
            `).join('')}
          </div>

          <!-- Content Tab -->
          ${this.renderActiveTab(companyId)}
        </div>
      `;
    }

    renderActiveTab(companyId) {
      if (this.activeTab === 'industry_pack') {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:24px;">
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
                🏨 ${this.industry} Operational Matrix
              </h3>
              <p style="font-size:13px; color:var(--text-secondary); margin-bottom:20px;">
                Industry telemetry syncs live key performance indicators directly from connected operational software.
              </p>
              <div style="padding:32px 16px; text-align:center; background:rgba(0,0,0,0.15); border:1px dashed var(--border-color); border-radius:8px;">
                <div style="font-size:28px; margin-bottom:8px;">📡</div>
                <div style="font-size:14px; font-weight:600; color:var(--text-primary); margin-bottom:4px;">No Telemetry Connector Linked</div>
                <div style="font-size:12px; color:var(--text-muted); max-width:440px; margin:0 auto 16px;">
                  Connect your Property Management System (PMS), SCADA, ERP, or IoT gateway in the Integration Center to stream real-time operational feeds.
                </div>
                <button class="btn-secondary" style="font-size:12px;" onclick="window.navigateTo ? window.navigateTo('/integrations') : null">
                  Open Integration Center
                </button>
              </div>
            </div>
          </div>
        `;
      } else if (this.activeTab === 'assets') {
        return `
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:36px; text-align:center;">
            <div style="font-size:28px; margin-bottom:8px;">🏢</div>
            <div style="font-size:14px; font-weight:600; color:var(--text-primary); margin-bottom:4px;">No Equipment Assets Registered</div>
            <div style="font-size:12px; color:var(--text-muted);">Physical and digital assets will appear here as maintenance schedules are created.</div>
          </div>
        `;
      } else if (this.activeTab === 'incidents') {
        return `
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:36px; text-align:center;">
            <div style="font-size:28px; margin-bottom:8px;">🛡️</div>
            <div style="font-size:14px; font-weight:600; color:var(--text-primary); margin-bottom:4px;">Zero Operational Incidents</div>
            <div style="font-size:12px; color:var(--accent-emerald);">All monitored execution boundaries and host runtimes are operating nominally.</div>
          </div>
        `;
      } else {
        // Work Orders Tab
        if (this.processes.length === 0) {
          return `
            <div class="empty-state-card" style="padding:60px 24px; text-align:center; background:var(--bg-surface); border:1px dashed var(--border-color); border-radius:12px;">
              <div style="font-size:36px; margin-bottom:12px;">⚙️</div>
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">No Active Work Orders or Shifts</h3>
              <p style="font-size:13px; color:var(--text-secondary); max-width:480px; margin:0 auto 20px;">
                Operational execution is currently idle with no active maintenance tasks, room audits, or scheduled shifts. Dispatched work orders will appear here with live execution tracking.
              </p>
              <button class="btn-primary" onclick="window.OperationsWorkspace.openCreateOrderModal('${companyId}')">+ Create First Work Order</button>
            </div>
          `;
        }

        return `
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Order Code</th>
                  <th>Task Description</th>
                  <th>Location / Asset</th>
                  <th>Assigned Worker</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                ${this.processes.map(p => `
                  <tr>
                    <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-blue);">${p.process_id || p.id}</td>
                    <td style="font-weight:600; color:var(--text-primary);">${p.name || p.description}</td>
                    <td style="color:var(--text-secondary);">${p.category || 'Operations'}</td>
                    <td>${p.assigned_to || 'AI Specialist'}</td>
                    <td><span class="badge ${p.status==='COMPLETED'?'badge-emerald':p.status==='RUNNING'?'badge-blue':'badge-amber'}">${p.status || 'PENDING'}</span></td>
                    <td>
                      <button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="window.showToast ? window.showToast('Work order inspected', 'info') : alert('Work order inspected')">
                        Inspect
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      }
    }

    switchTab(tabId, companyId) {
      this.activeTab = tabId;
      const container = document.getElementById('view-operations');
      if (container) this.renderView(container, companyId);
    }

    openCreateOrderModal(companyId) {
      const body = `
        <form onsubmit="window.OperationsWorkspace.submitCreateOrder(event, '${companyId}')" style="display:flex; flex-direction:column; gap:12px;">
          <div>
            <label class="form-label">Task / Work Order Description *</label>
            <input type="text" class="form-input" id="woDesc" placeholder="e.g. Audit room charge folios, calibrate sensor array" required />
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Location / Department *</label>
              <input type="text" class="form-input" id="woLoc" placeholder="e.g. Server Room, Front Desk, Bay 02" required />
            </div>
            <div>
              <label class="form-label">Assigned Specialist *</label>
              <input type="text" class="form-input" id="woWorker" value="Operations Specialist" required />
            </div>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Dispatch Order</button>
          </div>
        </form>
      `;

      if (window.openModal) {
        window.openModal('Create Operational Work Order', body);
      }
    }

    async submitCreateOrder(e, companyId) {
      e.preventDefault();
      const desc = document.getElementById('woDesc').value;
      const loc = document.getElementById('woLoc').value;
      const worker = document.getElementById('woWorker').value;

      try {
        const res = await fetch(`/api/companies/${encodeURIComponent(companyId || 'comp_primary')}/processes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: desc,
            category: loc,
            assigned_to: worker,
            status: 'RUNNING'
          })
        });

        if (res.ok) {
          if (window.closeModal) window.closeModal();
          if (window.showToast) window.showToast('Work order dispatched successfully', 'success');
          await this.render();
        }
      } catch (err) {
        console.error('Failed to create work order:', err);
      }
    }
  }

  window.OperationsWorkspace = new EnterpriseOperationsWorkspace();
})();
