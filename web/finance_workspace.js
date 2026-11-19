/**
 * ZONATA Universal AI Company OS — Finance & Accounting Workspace
 * Comprehensive financial operating layer:
 * Chart of Accounts, General Ledger, AP/AR, Expenses & Reimbursements, Cash & Banking.
 */

(function() {
  'use strict';

  class EnterpriseFinanceWorkspace {
    constructor() {
      this.financeData = null;
      this.activeTab = 'overview'; // 'overview' | 'coa' | 'transactions' | 'expenses'
      this.loading = false;
    }

    async render(containerId = 'view-finance', routePath = '/finance') {
      const container = document.getElementById(containerId);
      if (!container) return;

      if (typeof routePath === 'string') {
        if (routePath.includes('/revenue') || routePath.includes('/transactions')) {
          this.activeTab = 'transactions';
        } else if (routePath.includes('/expenses')) {
          this.activeTab = 'expenses';
        } else if (routePath.includes('/coa') || routePath.includes('/accounts')) {
          this.activeTab = 'coa';
        } else if (routePath === '/finance' || routePath.includes('/overview') || routePath.includes('/profitability')) {
          this.activeTab = 'overview';
        }
      }

      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Loading Financial Operating Layer...</div>
        </div>
      `;

      await this.loadFinanceData();
      this.renderView(container);
    }

    async loadFinanceData() {
      this.loading = true;
      try {
        const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
        const res = await fetch(`/api/finance/summary?company_id=${encodeURIComponent(companyId || 'comp_primary')}`);
        if (res.ok) {
          this.financeData = await res.json();
        }
      } catch (err) {
        console.error('Failed to load finance data:', err);
      } finally {
        this.loading = false;
      }
    }

    renderView(container) {
      if (!this.financeData) {
        container.innerHTML = `
          <div style="padding:60px 24px; text-align:center; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; margin:40px auto; max-width:600px;">
            <div style="font-size:36px; margin-bottom:12px;">💳</div>
            <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">Financial Layer Unavailable</h3>
            <p style="font-size:13px; color:var(--text-secondary); margin-bottom:20px;">Could not connect to the statutory double-entry accounting engine.</p>
            <button class="btn-primary" onclick="window.FinanceWorkspace.render()">Retry Connection</button>
          </div>
        `;
        return;
      }
      const s = this.financeData.summary || {};
      const coa = this.financeData.chart_of_accounts || [];
      const txs = this.financeData.recent_transactions || [];
      const exps = this.financeData.recent_expenses || [];

      container.innerHTML = `
        <div class="finance-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-emerald" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Statutory Accounting</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Double-Entry Ledger Verified
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                Finance & Accounting Center
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                General Ledger, Chart of Accounts, Accounts Payable & Receivable, expense claims, cash runway, and bank feeds.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn-primary" onclick="window.FinanceWorkspace.openSubmitExpenseModal()">
                + Submit Expense Claim
              </button>
            </div>
          </div>

          <!-- Top Executive Metrics -->
          <div class="enterprise-grid-4">
            <div class="metric-stat-card">
              <div class="metric-stat-title">Cash & Treasury Position</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">${s.currency}${(s.cash_position||0).toLocaleString()}</div>
              <div class="metric-stat-sub">Petty Cash + Bank + Escrow</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Accounts Receivable (AR)</div>
              <div class="metric-stat-value" style="color:var(--accent-blue);">${s.currency}${(s.accounts_receivable||0).toLocaleString()}</div>
              <div class="metric-stat-sub">Expected Customer Inflow</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Accounts Payable (AP)</div>
              <div class="metric-stat-value" style="color:var(--accent-amber);">${s.currency}${(s.accounts_payable||0).toLocaleString()}</div>
              <div class="metric-stat-sub">Vendor Obligations Due</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Operating Profit (MTD)</div>
              <div class="metric-stat-value">${s.currency}${(s.operating_profit||0).toLocaleString()}</div>
              <div class="metric-stat-sub">Margin: <strong>${s.operating_margin_pct||0}%</strong></div>
            </div>
          </div>

          <!-- Subnav Tabs -->
          <div style="display:flex; gap:8px; border-bottom:1px solid var(--border-color); padding-bottom:2px;">
            ${[
              { id: 'overview', label: '📊 Financial Overview' },
              { id: 'coa', label: `📑 Chart of Accounts (${coa.length})` },
              { id: 'transactions', label: `💳 General Ledger (${txs.length})` },
              { id: 'expenses', label: `🧾 Expense Claims (${exps.length})` }
            ].map(t => `
              <button 
                class="subnav-tab ${this.activeTab===t.id?'active':''}"
                style="padding:10px 18px; font-size:13.5px; font-weight:600; border:none; background:none; color:${this.activeTab===t.id?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${this.activeTab===t.id?'var(--accent-blue)':'transparent'}; cursor:pointer;"
                onclick="window.FinanceWorkspace.switchTab('${t.id}')">
                ${t.label}
              </button>
            `).join('')}
          </div>

          <!-- Tab Content Area -->
          ${this.renderActiveTab(coa, txs, exps)}
        </div>
      `;
    }

    renderActiveTab(coa, txs, exps) {
      if (this.activeTab === 'coa') {
        return `
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Account Code</th>
                  <th>Account Name</th>
                  <th>Type</th>
                  <th>Category</th>
                  <th>Balance</th>
                  <th>Currency</th>
                </tr>
              </thead>
              <tbody>
                ${coa.length === 0 ? `
                  <tr>
                    <td colspan="6" style="text-align:center; padding:32px; color:var(--text-secondary);">
                      No accounts configured in the Chart of Accounts.
                    </td>
                  </tr>
                ` : coa.map(a => `
                  <tr>
                    <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-blue);">${a.code}</td>
                    <td style="font-weight:600; color:var(--text-primary);">${a.name}</td>
                    <td><span class="badge ${a.account_type==='ASSET'?'badge-emerald':a.account_type==='LIABILITY'?'badge-amber':a.account_type==='REVENUE'?'badge-blue':'badge-neutral'}">${a.account_type}</span></td>
                    <td style="color:var(--text-secondary);">${a.category}</td>
                    <td style="font-weight:700; font-family:var(--font-mono);">${a.currency}${(a.balance||0).toLocaleString()}</td>
                    <td style="color:var(--text-muted);">${a.currency}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } else if (this.activeTab === 'transactions') {
        return `
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Flow</th>
                  <th>Amount</th>
                  <th>Counterparty</th>
                  <th>Reference</th>
                  <th>Status</th>
                  <th>Evidence Seal</th>
                </tr>
              </thead>
              <tbody>
                ${txs.length === 0 ? `
                  <tr>
                    <td colspan="7" style="text-align:center; padding:36px; color:var(--text-secondary);">
                      No transactions recorded yet in the General Ledger. Connect banking feeds or record manual entries.
                    </td>
                  </tr>
                ` : txs.map(t => `
                  <tr>
                    <td style="font-family:var(--font-mono); font-size:11px; color:var(--text-muted);">${t.transaction_id}</td>
                    <td>
                      <span class="badge ${t.tx_type==='CREDIT'?'badge-emerald':'badge-rose'}" style="font-size:10px;">
                        ${t.tx_type}
                      </span>
                    </td>
                    <td style="font-weight:700; font-family:var(--font-mono); color:${t.tx_type==='CREDIT'?'var(--accent-emerald)':'var(--text-primary)'};">
                      ${t.tx_type==='CREDIT'?'+':'-'}₹${(t.amount||0).toLocaleString()}
                    </td>
                    <td style="font-weight:600; color:var(--text-primary);">${t.entity_name}</td>
                    <td style="font-family:var(--font-mono); font-size:11.5px; color:var(--text-secondary);">${t.reference_no}</td>
                    <td><span class="badge badge-emerald">${t.status}</span></td>
                    <td><span style="font-size:11px; font-family:var(--font-mono); color:var(--accent-emerald);">🔒 ${t.evidence_id || 'PENDING'}</span></td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } else if (this.activeTab === 'expenses') {
        return `
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Claimant</th>
                  <th>Department</th>
                  <th>Category</th>
                  <th>Amount</th>
                  <th>Payment Mode</th>
                  <th>Status</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                ${exps.length === 0 ? `
                  <tr>
                    <td colspan="7" style="text-align:center; padding:36px; color:var(--text-secondary);">
                      No expense claims submitted yet. Click "+ Submit Expense Claim" to submit your first claim.
                    </td>
                  </tr>
                ` : exps.map(e => `
                  <tr>
                    <td style="font-weight:600; color:var(--text-primary);">${e.claimant_name}</td>
                    <td><span class="badge" style="background:rgba(255,255,255,0.06);">${e.department}</span></td>
                    <td><span class="badge badge-blue">${e.category}</span></td>
                    <td style="font-weight:700; font-family:var(--font-mono);">₹${(e.amount||0).toLocaleString()}</td>
                    <td style="font-size:11px; color:var(--text-secondary);">${e.payment_mode}</td>
                    <td><span class="badge badge-emerald">${e.status}</span></td>
                    <td style="font-size:12px; color:var(--text-secondary); max-width:300px;">${e.description}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      } else {
        // Overview Tab: Split view of banking pools & cash velocity
        const cashAccounts = coa.filter(a => a.category === 'CASH' || a.category === 'BANK');

        return `
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;" class="enterprise-grid-3">
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
              <h3 style="font-size:15px; font-weight:700; margin-bottom:12px; color:var(--text-primary);">🏦 Connected Treasury & Cash Accounts</h3>
              <div style="display:flex; flex-direction:column; gap:10px;">
                ${cashAccounts.length === 0 ? `
                  <div style="text-align:center; padding:28px 16px; color:var(--text-secondary); font-size:13px; background:rgba(0,0,0,0.15); border-radius:8px; border:1px dashed var(--border-color);">
                    No connected treasury or cash accounts. Configure cash accounts in your Chart of Accounts.
                  </div>
                ` : cashAccounts.map(acc => `
                  <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(0,0,0,0.2); padding:12px 14px; border-radius:8px; border:1px solid var(--border-color);">
                    <div style="display:flex; align-items:center; gap:10px;">
                      <span style="font-size:18px;">${acc.category === 'CASH' ? '💵' : '🏛️'}</span>
                      <div>
                        <div style="font-size:13px; font-weight:600; color:var(--text-primary);">${acc.name}</div>
                        <div style="font-size:11px; color:var(--text-muted);">${acc.code} • ${acc.category}</div>
                      </div>
                    </div>
                    <div style="font-weight:700; font-family:var(--font-mono); color:var(--accent-emerald);">${acc.currency}${(acc.balance||0).toLocaleString()}</div>
                  </div>
                `).join('')}
              </div>
            </div>

            <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
              <h3 style="font-size:15px; font-weight:700; margin-bottom:12px; color:var(--text-primary);">⚡ Recent Autonomous Ledger Reconciliations</h3>
              <div style="display:flex; flex-direction:column; gap:10px;">
                ${txs.length === 0 ? `
                  <div style="text-align:center; padding:28px 16px; color:var(--text-secondary); font-size:13px; background:rgba(0,0,0,0.15); border-radius:8px; border:1px dashed var(--border-color);">
                    No ledger reconciliations yet. New business activities will appear here in real time.
                  </div>
                ` : txs.slice(0, 5).map(t => `
                  <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(0,0,0,0.2); padding:12px 14px; border-radius:8px; border:1px solid var(--border-color);">
                    <div>
                      <div style="font-size:13px; font-weight:600; color:var(--text-primary);">${t.entity_name}</div>
                      <div style="font-size:11px; color:var(--text-muted);">${t.reference_no} • ${t.category}</div>
                    </div>
                    <div style="font-weight:700; font-family:var(--font-mono); color:${t.tx_type==='CREDIT'?'var(--accent-emerald)':'var(--text-primary)'};">
                      ${t.tx_type==='CREDIT'?'+':'-'}₹${(t.amount||0).toLocaleString()}
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        `;
      }
    }

    switchTab(tabId) {
      this.activeTab = tabId;
      const container = document.getElementById('view-finance');
      if (container) this.renderView(container);
    }

    openSubmitExpenseModal() {
      const activeUser = (window.AppState && window.AppState.user && (window.AppState.user.name || window.AppState.user.username)) || '';
      const body = `
        <form onsubmit="window.FinanceWorkspace.submitExpense(event)" style="display:flex; flex-direction:column; gap:12px;">
          <div>
            <label class="form-label">Claimant Name *</label>
            <input type="text" class="form-input" id="expClaimant" value="${activeUser}" placeholder="Enter employee or claimant name" required />
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Department *</label>
              <select class="form-input" id="expDept">
                <option value="Operations">Operations</option>
                <option value="Finance">Finance</option>
                <option value="Sales">Sales</option>
                <option value="Procurement">Procurement</option>
                <option value="HR">HR</option>
              </select>
            </div>
            <div>
              <label class="form-label">Category *</label>
              <select class="form-input" id="expCat">
                <option value="SOFTWARE">SOFTWARE / COMPUTE</option>
                <option value="PROCUREMENT">PROCUREMENT</option>
                <option value="TRAVEL">TRAVEL</option>
                <option value="OFFICE">OFFICE</option>
                <option value="MARKETING">MARKETING</option>
              </select>
            </div>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Amount (₹) *</label>
              <input type="number" class="form-input" id="expAmount" placeholder="0.00" required />
            </div>
            <div>
              <label class="form-label">Payment Mode *</label>
              <select class="form-input" id="expMode">
                <option value="CORPORATE_CARD">Corporate Card</option>
                <option value="BANK_TRANSFER">Bank Transfer</option>
                <option value="REIMBURSEMENT">Reimbursement</option>
              </select>
            </div>
          </div>
          <div>
            <label class="form-label">Business Purpose & Description *</label>
            <textarea class="form-input" id="expDesc" rows="2" placeholder="Explain the business purpose..." required></textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Submit Claim</button>
          </div>
        </form>
      `;

      if (window.openModal) {
        window.openModal('Submit Expense Claim', body);
      }
    }

    async submitExpense(e) {
      e.preventDefault();
      const claimant = document.getElementById('expClaimant').value;
      const dept = document.getElementById('expDept').value;
      const cat = document.getElementById('expCat').value;
      const amount = parseFloat(document.getElementById('expAmount').value || '0');
      const mode = document.getElementById('expMode').value;
      const desc = document.getElementById('expDesc').value;

      try {
        const res = await fetch('/api/finance/expenses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            claimant_name: claimant,
            department: dept,
            category: cat,
            amount,
            payment_mode: mode,
            description: desc
          })
        });

        if (res.ok) {
          if (window.closeModal) window.closeModal();
          if (window.showToast) window.showToast('Expense claim submitted for verification!', 'success');
          await this.loadFinanceData();
          const container = document.getElementById('view-finance');
          if (container) this.renderView(container);
        }
      } catch (err) {
        console.error('Failed to submit expense:', err);
      }
    }
  }

  window.FinanceWorkspace = new EnterpriseFinanceWorkspace();
})();
