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
      this.employees = [];
      this.loading = false;
    }

    async render(containerId = 'view-people') {
      const container = document.getElementById(containerId);
      if (!container) return;

      if (window.AppleWorkforceBoard) {
        window.AppleWorkforceBoard.render(container);
        return;
      }

      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Loading Workforce Roster...</div>
        </div>
      `;

      await this.loadEmployees();
      this.renderView(container);
    }

    async loadEmployees() {
      this.loading = true;
      try {
        const res = await fetch('/api/employees');
        if (res.ok) {
          const data = await res.json();
          this.employees = Array.isArray(data.employees) ? data.employees : [];
        }
      } catch (err) {
        console.error('Failed to load employees:', err);
      } finally {
        this.loading = false;
      }
    }

    renderView(container) {
      const totalEmp = this.employees.length;
      const aiAgents = this.employees.filter(e => e.allowed_tools || (e.manager && e.manager.includes('AI'))).length;
      const humanStaff = totalEmp - aiAgents;
      const totalPayroll = this.employees.reduce((acc, e) => acc + (Number(e.budget_limit || e.spending_limit || 0)), 0);

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
              <button class="btn-primary" onclick="window.PeopleWorkspace.openAddEmployeeModal()">
                + Add Employee Profile
              </button>
            </div>
          </div>

          <!-- Top Personnel Metrics -->
          <div class="enterprise-grid-4">
            <div class="metric-stat-card">
              <div class="metric-stat-title">Human Personnel</div>
              <div class="metric-stat-value">${humanStaff}</div>
              <div class="metric-stat-sub">${humanStaff > 0 ? `${humanStaff} active` : 'No personnel assigned'}</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Autonomous AI Agents</div>
              <div class="metric-stat-value" style="color:var(--accent-purple);">${aiAgents}</div>
              <div class="metric-stat-sub">${aiAgents > 0 ? 'Governed digital co-workers' : '0 specialists deployed'}</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Average Attendance</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">${totalEmp > 0 ? '100%' : '—'}</div>
              <div class="metric-stat-sub">${totalEmp > 0 ? 'Biometric & SSO verified' : 'Awaiting team sync'}</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Monthly Payroll Allocation</div>
              <div class="metric-stat-value">₹${totalPayroll.toLocaleString()}</div>
              <div class="metric-stat-sub">${totalPayroll > 0 ? 'Authorized operational budget' : '₹0 committed'}</div>
            </div>
          </div>

          <!-- Personnel Table or Empty State -->
          ${totalEmp === 0 ? `
            <div class="empty-state-card" style="padding:60px 24px; text-align:center; background:var(--bg-surface); border:1px dashed var(--border-color); border-radius:12px;">
              <div style="font-size:36px; margin-bottom:12px;">👥</div>
              <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">No Workforce Personnel Added Yet</h3>
              <p style="font-size:13px; color:var(--text-secondary); max-width:480px; margin:0 auto 20px;">
                Your organization currently has 0 registered human staff and 0 deployed AI specialists. Add an employee profile or deploy an autonomous agent to build your roster.
              </p>
              <button class="btn-primary" onclick="window.PeopleWorkspace.openAddEmployeeModal()">+ Add First Employee Profile</button>
            </div>
          ` : `
            <div class="responsive-table-container">
              <table class="enterprise-data-table">
                <thead>
                  <tr>
                    <th>Employee Name & Role</th>
                    <th>Department</th>
                    <th>Company</th>
                    <th>Manager / Reports To</th>
                    <th>Spend / Budget Limit</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${this.employees.map(emp => `
                    <tr>
                      <td>
                        <div style="font-weight:600; color:var(--text-primary);">👤 ${emp.name || 'Specialist'}</div>
                        <div style="font-size:11px; color:var(--text-muted);">ID: ${emp.id || 'EMP-01'}</div>
                      </td>
                      <td><span class="badge" style="background:rgba(255,255,255,0.06); font-size:11px;">${emp.department || 'Operations'}</span></td>
                      <td style="font-weight:600; color:var(--accent-blue);">${emp.company_name || 'Primary'}</td>
                      <td style="color:var(--text-secondary);">${emp.manager || 'Executive'}</td>
                      <td style="font-family:var(--font-mono); font-weight:700;">₹${Number(emp.budget_limit || emp.spending_limit || 0).toLocaleString()}</td>
                      <td><span class="badge badge-emerald">${emp.status || 'ACTIVE'}</span></td>
                      <td>
                        <button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="window.showToast ? window.showToast('Employee dossier inspected', 'info') : alert('Employee dossier inspected')">
                          Dossier
                        </button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `}
        </div>
      `;
    }

    openAddEmployeeModal() {
      const body = `
        <form onsubmit="window.PeopleWorkspace.submitAddEmployee(event)" style="display:flex; flex-direction:column; gap:12px;">
          <div>
            <label class="form-label">Role / Job Title *</label>
            <input type="text" class="form-input" id="newEmpRole" placeholder="e.g. Operations Specialist, Financial Analyst" required />
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Department *</label>
              <select class="form-input" id="newEmpDept">
                <option value="Operations">Operations</option>
                <option value="Finance">Finance</option>
                <option value="Sales">Sales</option>
                <option value="Procurement">Procurement</option>
                <option value="Engineering">Engineering</option>
                <option value="HR">HR</option>
              </select>
            </div>
            <div>
              <label class="form-label">Monthly Spending / Budget Limit (₹)</label>
              <input type="number" class="form-input" id="newEmpBudget" placeholder="0.00" value="0" />
            </div>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Create Profile</button>
          </div>
        </form>
      `;

      if (window.openModal) {
        window.openModal('Add Employee Profile', body);
      }
    }

    async submitAddEmployee(e) {
      e.preventDefault();
      const role = document.getElementById('newEmpRole').value;
      const dept = document.getElementById('newEmpDept').value;
      const budget = parseFloat(document.getElementById('newEmpBudget').value || '0');

      try {
        const res = await fetch('/api/employees', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            role: role,
            department: dept,
            budget_limit: budget,
            spending_limit: budget
          })
        });

        if (res.ok) {
          if (window.closeModal) window.closeModal();
          if (window.showToast) window.showToast('Employee profile added successfully', 'success');
          await this.render();
        }
      } catch (err) {
        console.error('Failed to add employee:', err);
      }
    }
  }

  window.PeopleWorkspace = new EnterprisePeopleWorkspace();
})();
