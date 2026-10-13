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
      this.industry = 'Hospitality'; // dynamically adapts to active company
    }

    render(containerId = 'view-operations') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const company = (window.state && window.state.companies && window.state.companies[0]) || { name: 'Primary Enterprise', industry: 'Operations & SaaS' };
      this.industry = company.industry || 'General Operations';

      container.innerHTML = `
        <div class="operations-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Operational Center</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Industry Pack: ${this.industry} Active
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
              <button class="btn-primary" onclick="window.showToast('New Work Order dispatched to AI Operations Specialist', 'success')">
                + Create Work Order
              </button>
            </div>
          </div>

          <!-- Top Operational KPIs -->
          <div class="enterprise-grid-4">
            <div class="metric-stat-card">
              <div class="metric-stat-title">Active Work Orders</div>
              <div class="metric-stat-value">18</div>
              <div class="metric-stat-sub"><span style="color:var(--accent-emerald);">●</span> 14 on schedule, 4 pending sign-off</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">SLA Compliance Rate</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">99.4%</div>
              <div class="metric-stat-sub">Average completion: 34 minutes</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Equipment / Asset Uptime</div>
              <div class="metric-stat-value">99.8%</div>
              <div class="metric-stat-sub">Zero critical incidents this week</div>
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
              { id: 'work_orders', label: '📋 Work Orders & Schedules' },
              { id: 'industry_pack', label: `🏨 Industry Pack (${this.industry})` },
              { id: 'assets', label: '🏢 Asset & Maintenance Register' },
              { id: 'incidents', label: '🛡️ Incident Log' }
            ].map(t => `
              <button 
                class="subnav-tab ${this.activeTab===t.id?'active':''}"
                style="padding:10px 18px; font-size:13.5px; font-weight:600; border:none; background:none; color:${this.activeTab===t.id?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${this.activeTab===t.id?'var(--accent-blue)':'transparent'}; cursor:pointer;"
                onclick="window.OperationsWorkspace.switchTab('${t.id}')">
                ${t.label}
              </button>
            `).join('')}
          </div>

          <!-- Content Tab -->
          ${this.renderActiveTab()}
        </div>
      `;
    }

    renderActiveTab() {
      if (this.activeTab === 'industry_pack') {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:12px;">
                🏨 Hospitality & Resort Operational Matrix
              </h3>
              <div class="enterprise-grid-3">
                <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:8px; padding:16px;">
                  <div style="font-size:12px; color:var(--text-muted); font-weight:600;">OCCUPANCY RATE</div>
                  <div style="font-size:24px; font-weight:700; color:var(--accent-emerald); margin:4px 0;">86.4%</div>
                  <div style="font-size:11px; color:var(--text-secondary);">128 of 148 Rooms Occupied</div>
                </div>
                <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:8px; padding:16px;">
                  <div style="font-size:12px; color:var(--text-muted); font-weight:600;">AVERAGE DAILY RATE (ADR)</div>
                  <div style="font-size:24px; font-weight:700; color:var(--accent-blue); margin:4px 0;">₹8,450</div>
                  <div style="font-size:11px; color:var(--text-secondary);">RevPAR: ₹7,301</div>
                </div>
                <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:8px; padding:16px;">
                  <div style="font-size:12px; color:var(--text-muted); font-weight:600;">NIGHT AUDIT STATUS</div>
                  <div style="font-size:24px; font-weight:700; color:var(--accent-emerald); margin:4px 0;">BALANCED</div>
                  <div style="font-size:11px; color:var(--text-secondary);">Zero folio billing discrepancies</div>
                </div>
              </div>
            </div>
          </div>
        `;
      } else {
        return `
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Order Code</th>
                  <th>Task Description</th>
                  <th>Location / Asset</th>
                  <th>Assigned Worker</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                ${[
                  { code: 'WO-8821', desc: 'Overnight Room Charge Folio Balancing & PMS Audit', loc: 'Front Desk / Server 01', worker: 'Night Auditor Agent', prio: 'CRITICAL', status: 'IN_PROGRESS' },
                  { code: 'WO-8822', desc: 'Raw Material Batch Quality Verification (#RM-442)', loc: 'Warehouse Bay 02', worker: 'Quality QA Agent', prio: 'HIGH', status: 'COMPLETED' },
                  { code: 'WO-8823', desc: 'HVAC Air Purification Filter Calibration', loc: 'Tower A Plant Room', worker: 'Facilities Technician', prio: 'NORMAL', status: 'COMPLETED' }
                ].map(o => `
                  <tr>
                    <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-blue);">${o.code}</td>
                    <td style="font-weight:600; color:var(--text-primary);">${o.desc}</td>
                    <td style="color:var(--text-secondary);">${o.loc}</td>
                    <td>${o.worker}</td>
                    <td><span class="badge ${o.prio==='CRITICAL'?'badge-rose':o.prio==='HIGH'?'badge-amber':'badge-blue'}">${o.prio}</span></td>
                    <td><span class="badge ${o.status==='COMPLETED'?'badge-emerald':'badge-amber'}">${o.status}</span></td>
                    <td>
                      <button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="window.showToast('Work order inspected', 'info')">
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

    switchTab(tabId) {
      this.activeTab = tabId;
      const container = document.getElementById('view-operations');
      if (container) this.render('view-operations');
    }
  }

  window.OperationsWorkspace = new EnterpriseOperationsWorkspace();
})();
