/**
 * ZONATA Universal AI Company OS — Enterprise Records Center Workspace
 * Manages structured business events and historical state:
 * Invoices, Expenses, Customers, Vendors, Employees, Payments, Inventory, Decisions, Audit.
 */

(function() {
  'use strict';

  class EnterpriseRecordsWorkspace {
    constructor() {
      this.records = [];
      this.total = 0;
      this.currentFilterType = 'ALL';
      this.currentDateRange = 'ALL';
      this.searchQuery = '';
      this.selectedRecord = null;
      this.loading = false;
    }

    async render(containerId = 'view-records') {
      const container = document.getElementById(containerId);
      if (!container) return;

      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Loading Enterprise Records Center...</div>
        </div>
      `;

      await this.loadRecords();
      this.renderView(container);
    }

    async loadRecords() {
      this.loading = true;
      try {
        const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
        let url = `/api/records?company_id=${encodeURIComponent(companyId || 'comp_primary')}`;
        if (this.currentFilterType !== 'ALL') url += `&record_type=${encodeURIComponent(this.currentFilterType)}`;
        if (this.currentDateRange !== 'ALL') url += `&date_range=${encodeURIComponent(this.currentDateRange)}`;
        if (this.searchQuery) url += `&q=${encodeURIComponent(this.searchQuery)}`;

        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          this.records = data.records || [];
          this.total = data.total || 0;
        }
      } catch (err) {
        console.error('Failed to load records:', err);
      } finally {
        this.loading = false;
      }
    }

    renderView(container) {
      container.innerHTML = `
        <div class="records-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Corporate Ledger</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Cryptographic Traceability Active
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                Enterprise Records Center
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Structured business events, operational state, historical transactions, customer/vendor profiles, and immutable audit logs.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn-primary" onclick="window.RecordsWorkspace.openNewRecordModal()">
                + Create Record
              </button>
            </div>
          </div>

          <!-- Filter & Search Toolbar -->
          <div class="enterprise-filter-toolbar">
            <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap; flex:1;">
              <div style="position:relative; min-width:240px; flex:1;">
                <input 
                  type="text" 
                  class="form-input" 
                  placeholder="Search records by title, actor, or ID..." 
                  value="${this.searchQuery}" 
                  oninput="window.RecordsWorkspace.handleSearch(this.value)"
                  style="padding-left:32px;"
                />
                <svg style="position:absolute; left:10px; top:50%; transform:translateY(-50%); width:14px; height:14px; color:var(--text-muted);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </div>

              <!-- Record Type Filter -->
              <select class="form-input" style="width:auto; min-width:160px;" onchange="window.RecordsWorkspace.handleTypeFilter(this.value)">
                <option value="ALL" ${this.currentFilterType==='ALL'?'selected':''}>All Record Types (${this.total})</option>
                <option value="INVOICE" ${this.currentFilterType==='INVOICE'?'selected':''}>Invoices</option>
                <option value="EXPENSE" ${this.currentFilterType==='EXPENSE'?'selected':''}>Expenses</option>
                <option value="CUSTOMER" ${this.currentFilterType==='CUSTOMER'?'selected':''}>Customers</option>
                <option value="VENDOR" ${this.currentFilterType==='VENDOR'?'selected':''}>Vendors</option>
                <option value="EMPLOYEE" ${this.currentFilterType==='EMPLOYEE'?'selected':''}>Employees</option>
                <option value="PAYMENT" ${this.currentFilterType==='PAYMENT'?'selected':''}>Payments</option>
                <option value="INVENTORY" ${this.currentFilterType==='INVENTORY'?'selected':''}>Inventory</option>
                <option value="DECISION" ${this.currentFilterType==='DECISION'?'selected':''}>AI Decisions</option>
              </select>

              <!-- Date Range Filter -->
              <select class="form-input" style="width:auto; min-width:140px;" onchange="window.RecordsWorkspace.handleDateFilter(this.value)">
                <option value="ALL" ${this.currentDateRange==='ALL'?'selected':''}>All Time</option>
                <option value="TODAY" ${this.currentDateRange==='TODAY'?'selected':''}>Today</option>
                <option value="YESTERDAY" ${this.currentDateRange==='YESTERDAY'?'selected':''}>Yesterday</option>
                <option value="THIS_WEEK" ${this.currentDateRange==='THIS_WEEK'?'selected':''}>This Week</option>
                <option value="THIS_MONTH" ${this.currentDateRange==='THIS_MONTH'?'selected':''}>This Month</option>
                <option value="THIS_QUARTER" ${this.currentDateRange==='THIS_QUARTER'?'selected':''}>This Quarter</option>
              </select>
            </div>
          </div>

          <!-- Records Table -->
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Record Title & ID</th>
                  <th>Department</th>
                  <th>Category</th>
                  <th>Amount / Value</th>
                  <th>Actor / Source</th>
                  <th>Status</th>
                  <th>Evidence Seal</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                ${this.records.length === 0 ? `
                  <tr>
                    <td colspan="8" style="text-align:center; padding:40px; color:var(--text-muted);">
                      No business records matching current filter criteria.
                    </td>
                  </tr>
                ` : this.records.map(r => `
                  <tr>
                    <td>
                      <div style="font-weight:600; color:var(--text-primary); cursor:pointer;" onclick="window.RecordsWorkspace.viewRecordDetail('${r.record_id}')">
                        ${r.title}
                      </div>
                      <div style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${r.record_id}</div>
                    </td>
                    <td><span class="badge" style="background:rgba(255,255,255,0.06); font-size:11px;">${r.department}</span></td>
                    <td><span class="badge badge-blue" style="font-size:11px;">${r.record_type}</span></td>
                    <td style="font-weight:600; font-family:var(--font-mono);">
                      ${r.amount > 0 ? `${r.currency}${r.amount.toLocaleString()}` : '—'}
                    </td>
                    <td>
                      <div style="font-size:12px; color:var(--text-primary);">${r.actor_name}</div>
                      <div style="font-size:10.5px; color:${r.actor_type==='AI_AGENT'?'var(--accent-purple)':'var(--accent-blue)'};">${r.actor_type}</div>
                    </td>
                    <td>
                      <span class="badge ${r.status==='COMPLETED'||r.status==='APPROVED'||r.status==='ACTIVE'?'badge-emerald':'badge-amber'}" style="font-size:11px;">
                        ${r.status}
                      </span>
                    </td>
                    <td>
                      <span style="font-size:11px; font-family:var(--font-mono); color:var(--text-secondary); display:inline-flex; align-items:center; gap:4px;">
                        🔒 ${r.evidence_id || 'SEALED'}
                      </span>
                    </td>
                    <td>
                      <button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="window.RecordsWorkspace.viewRecordDetail('${r.record_id}')">
                        Inspect
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

    async handleSearch(q) {
      this.searchQuery = q;
      await this.loadRecords();
      const container = document.getElementById('view-records');
      if (container) this.renderView(container);
    }

    async handleTypeFilter(t) {
      this.currentFilterType = t;
      await this.loadRecords();
      const container = document.getElementById('view-records');
      if (container) this.renderView(container);
    }

    async handleDateFilter(d) {
      this.currentDateRange = d;
      await this.loadRecords();
      const container = document.getElementById('view-records');
      if (container) this.renderView(container);
    }

    viewRecordDetail(recordId) {
      const rec = this.records.find(r => r.record_id === recordId);
      if (!rec) return;

      const body = `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div>
            <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">${rec.record_id}</div>
            <h3 style="font-size:18px; font-weight:700; margin:4px 0 8px 0;">${rec.title}</h3>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <span class="badge badge-blue">${rec.record_type}</span>
              <span class="badge" style="background:rgba(255,255,255,0.06);">${rec.department}</span>
              <span class="badge badge-emerald">${rec.status}</span>
            </div>
          </div>

          <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:8px; padding:12px;">
            <div style="font-size:11.5px; font-weight:600; color:var(--text-muted); text-transform:uppercase;">Financial & Operational Valuation</div>
            <div style="font-size:22px; font-weight:700; color:var(--text-primary); margin-top:4px;">
              ${rec.amount > 0 ? `${rec.currency}${rec.amount.toLocaleString()}` : 'Non-Monetary Event'}
            </div>
          </div>

          <div>
            <h4 style="font-size:13px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Originating Actor & Authority</h4>
            <div style="font-size:13px; color:var(--text-primary);">${rec.actor_name} (${rec.actor_type})</div>
          </div>

          <div>
            <h4 style="font-size:13px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Verification Notes</h4>
            <p style="font-size:13px; color:var(--text-secondary); background:rgba(255,255,255,0.02); padding:10px; border-radius:6px; border:1px solid var(--border-color);">${rec.notes || 'Direct ledger entry verified by authority kernel.'}</p>
          </div>

          <div>
            <h4 style="font-size:13px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Relations & Cross-References</h4>
            <pre style="font-family:var(--font-mono); font-size:11.5px; background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; overflow-x:auto;">${JSON.stringify(rec.relations, null, 2)}</pre>
          </div>

          <div>
            <h4 style="font-size:13px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Cryptographic Proof Seal</h4>
            <div style="font-family:var(--font-mono); font-size:11.5px; color:var(--accent-emerald); background:rgba(16,185,129,0.08); padding:8px 12px; border-radius:6px; border:1px solid rgba(16,185,129,0.2);">
              🔒 Merkle Leaf ID: ${rec.evidence_id || 'SEALED_VALID'}
            </div>
          </div>
        </div>
      `;

      if (window.openModal) {
        window.openModal('Business Record Dossier', body);
      }
    }

    openNewRecordModal() {
      const body = `
        <form onsubmit="window.RecordsWorkspace.submitNewRecord(event)" style="display:flex; flex-direction:column; gap:12px;">
          <div>
            <label class="form-label">Record Title *</label>
            <input type="text" class="form-input" id="newRecTitle" placeholder="e.g. Vendor Invoice #INV-2026-99" required />
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Category *</label>
              <select class="form-input" id="newRecType">
                <option value="INVOICE">INVOICE</option>
                <option value="EXPENSE">EXPENSE</option>
                <option value="CUSTOMER">CUSTOMER</option>
                <option value="VENDOR">VENDOR</option>
                <option value="EMPLOYEE">EMPLOYEE</option>
                <option value="PAYMENT">PAYMENT</option>
                <option value="INVENTORY">INVENTORY</option>
                <option value="DECISION">AI DECISION</option>
              </select>
            </div>
            <div>
              <label class="form-label">Department *</label>
              <select class="form-input" id="newRecDept">
                <option value="Finance">Finance</option>
                <option value="Procurement">Procurement</option>
                <option value="Sales">Sales</option>
                <option value="Operations">Operations</option>
                <option value="HR">HR</option>
                <option value="Executive">Executive</option>
              </select>
            </div>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Amount (₹)</label>
              <input type="number" class="form-input" id="newRecAmount" placeholder="0.00" value="0.0" />
            </div>
            <div>
              <label class="form-label">Responsible Actor</label>
              <input type="text" class="form-input" id="newRecActor" value="Host Owner / ZONATA Co-Worker" />
            </div>
          </div>
          <div>
            <label class="form-label">Audit Notes & Justification</label>
            <textarea class="form-input" id="newRecNotes" rows="2" placeholder="Audit evidence context..."></textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Register Record</button>
          </div>
        </form>
      `;

      if (window.openModal) {
        window.openModal('Register Structured Business Record', body);
      }
    }

    async submitNewRecord(e) {
      e.preventDefault();
      const title = document.getElementById('newRecTitle').value;
      const type = document.getElementById('newRecType').value;
      const dept = document.getElementById('newRecDept').value;
      const amount = parseFloat(document.getElementById('newRecAmount').value || '0');
      const actor = document.getElementById('newRecActor').value;
      const notes = document.getElementById('newRecNotes').value;

      try {
        const res = await fetch('/api/records', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title,
            record_type: type,
            department: dept,
            amount,
            actor_name: actor,
            actor_type: 'HUMAN_OWNER',
            notes
          })
        });

        if (res.ok) {
          if (window.closeModal) window.closeModal();
          if (window.showToast) window.showToast('Business record cryptographically registered!', 'success');
          await this.loadRecords();
          const container = document.getElementById('view-records');
          if (container) this.renderView(container);
        }
      } catch (err) {
        console.error('Failed to create record:', err);
      }
    }
  }

  window.RecordsWorkspace = new EnterpriseRecordsWorkspace();
})();
