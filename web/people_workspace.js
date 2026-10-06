/**
 * ZONATA Universal AI Company OS — People & Workforce Center Workspace
 * Manages both Human Personnel (Employees, Managers, Payroll, Attendance)
 * and Autonomous AI Workforce (Agents, Autonomy Tiers, Vitals).
 */

(function() {
  'use strict';

  class EnterprisePeopleWorkspace {
    constructor() {
      this.activeTab = 'employees'; // 'employees' | 'ai_workers'
    }

    render(containerId = 'view-people') {
      const container = document.getElementById(containerId);
      if (!container) return;

      container.innerHTML = `
        <div class="people-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Organizational Capital</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Unified Human & AI Roster
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                People & Workforce Center
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Employee profiles, management hierarchy, role assignments, compensation bands, attendance tracking, and AI workforce coordination.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn-primary" onclick="window.showToast('Employee onboarding invitation dispatched', 'success')">
                + Add Employee Profile
              </button>
            </div>
          </div>

          <!-- Top Personnel Metrics -->
          <div class="enterprise-grid-4">
            <div class="metric-stat-card">
              <div class="metric-stat-title">Human Personnel</div>
              <div class="metric-stat-value">24</div>
              <div class="metric-stat-sub">100% active, 0 unassigned</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Autonomous AI Agents</div>
              <div class="metric-stat-value" style="color:var(--accent-purple);">8</div>
              <div class="metric-stat-sub">Governed digital co-workers</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Average Attendance</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">98.8%</div>
              <div class="metric-stat-sub">Biometric & SSO verified</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Monthly Payroll Total</div>
              <div class="metric-stat-value">₹2,850,000</div>
              <div class="metric-stat-sub">Disbursed on 1st of month</div>
            </div>
          </div>

          <!-- Personnel Table -->
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Employee Name & Dossier</th>
                  <th>Department</th>
                  <th>Designation / Role</th>
                  <th>Manager / Reports To</th>
                  <th>Compensation (Monthly)</th>
                  <th>Attendance</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                ${[
                  { name: 'Priya Sharma', dept: 'Finance', role: 'Chief Financial Controller', manager: 'Sukhraj Singh (Owner)', comp: '₹250,000', att: '99.2%', status: 'ACTIVE' },
                  { name: 'Aman Verma', dept: 'Operations', role: 'Director of Hotel Operations', manager: 'Sukhraj Singh (Owner)', comp: '₹220,000', att: '98.5%', status: 'ACTIVE' },
                  { name: 'Rajesh Khanna', dept: 'Sales', role: 'VP Commercial Enterprise Sales', manager: 'AI CEO Executive', comp: '₹195,000', att: '99.0%', status: 'ACTIVE' },
                  { name: 'Neha Joshi', dept: 'HR', role: 'Head of People & Culture', manager: 'Sukhraj Singh (Owner)', comp: '₹160,000', att: '98.9%', status: 'ACTIVE' }
                ].map(emp => `
                  <tr>
                    <td>
                      <div style="font-weight:600; color:var(--text-primary);">👤 ${emp.name}</div>
                      <div style="font-size:11px; color:var(--text-muted);">ID: EMP-${emp.name.split(' ')[0].toUpperCase()}</div>
                    </td>
                    <td><span class="badge" style="background:rgba(255,255,255,0.06); font-size:11px;">${emp.dept}</span></td>
                    <td style="font-weight:600; color:var(--accent-blue);">${emp.role}</td>
                    <td style="color:var(--text-secondary);">${emp.manager}</td>
                    <td style="font-family:var(--font-mono); font-weight:700;">${emp.comp}</td>
                    <td><span class="badge badge-emerald" style="font-size:11px;">${emp.att}</span></td>
                    <td><span class="badge badge-emerald">${emp.status}</span></td>
                    <td>
                      <button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="window.showToast('Employee dossier inspected', 'info')">
                        Dossier
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }
  }

  window.PeopleWorkspace = new EnterprisePeopleWorkspace();
})();
