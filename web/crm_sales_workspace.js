/**
 * ZONATA Universal AI Company OS — Customers & Commercial Sales Workspace
 * Comprehensive CRM pipeline: Leads, Accounts, Deal Velocity, Proposals, and Invoices.
 */

(function() {
  'use strict';

  class EnterpriseCrmWorkspace {
    constructor() {
      this.activeTab = 'pipeline'; // 'pipeline' | 'customers'
    }

    render(containerId = 'view-customers') {
      const container = document.getElementById(containerId);
      if (!container) return;

      container.innerHTML = `
        <div class="crm-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Commercial Revenue</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Autonomous Deal Velocity Active
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                Customers & Commercial CRM
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Enterprise customer profiles, deal pipeline stages, contract values, and automated outreach sequences.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn-primary" onclick="window.showToast('New deal opportunity registered in CRM pipeline', 'success')">
                + Add Customer / Deal
              </button>
            </div>
          </div>

          <!-- Top Sales Pipeline Metrics -->
          <div class="enterprise-grid-4">
            <div class="metric-stat-card">
              <div class="metric-stat-title">Total Pipeline Value</div>
              <div class="metric-stat-value" style="color:var(--accent-blue);">₹8,900,000</div>
              <div class="metric-stat-sub">42 Active Deals in Progress</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Weighted Forecast</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">₹5,420,000</div>
              <div class="metric-stat-sub">Trailing 90D Win Rate: 44.6%</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Average Deal Size</div>
              <div class="metric-stat-value">₹212,000</div>
              <div class="metric-stat-sub">Enterprise Tier Target</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Autonomous SDR Velocity</div>
              <div class="metric-stat-value">+22%</div>
              <div class="metric-stat-sub">Automated follow-up conversion</div>
            </div>
          </div>

          <!-- Sales Pipeline Board -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
            <h3 style="font-size:15px; font-weight:700; color:var(--text-primary); margin-bottom:14px;">
              🎯 Commercial Deal Pipeline
            </h3>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
              ${[
                { stage: '1. New Discovery', count: 15, value: '₹2.1M', deals: ['Oberoi Luxe Group (₹450K)', 'Leela Palaces (₹600K)'] },
                { stage: '2. Proposal Submitted', count: 12, value: '₹3.2M', deals: ['Taj Heritage Palace (₹1.2M)', 'ITC Hotels East (₹800K)'] },
                { stage: '3. Negotiation', count: 9, value: '₹2.4M', deals: ['Radisson Corporate (₹650K)', 'Marriott Resort (₹950K)'] },
                { stage: '4. Won / Closed', count: 6, value: '₹1.2M', deals: ['Hyatt Regency (₹700K)', 'Lemon Tree Hub (₹500K)'] }
              ].map(col => `
                <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:8px; padding:12px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-size:12px; font-weight:700; color:var(--text-primary);">${col.stage}</span>
                    <span class="badge badge-blue" style="font-size:10px;">${col.count}</span>
                  </div>
                  <div style="font-size:14px; font-weight:700; color:var(--accent-emerald); margin-bottom:10px;">${col.value}</div>
                  <div style="display:flex; flex-direction:column; gap:6px;">
                    ${col.deals.map(d => `
                      <div style="background:var(--bg-surface); border:1px solid rgba(255,255,255,0.06); padding:8px 10px; border-radius:6px; font-size:12px; color:var(--text-secondary);">
                        ${d}
                      </div>
                    `).join('')}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    }
  }

  window.CrmWorkspace = new EnterpriseCrmWorkspace();
})();
