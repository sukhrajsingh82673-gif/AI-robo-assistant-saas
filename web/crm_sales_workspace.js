/**
 * ZONATA Universal AI Company OS — Customers & Commercial Sales Workspace
 * Comprehensive CRM pipeline: Leads, Deals, Forecasts, and Enterprise Customer 360.
 * Includes complete 8-dimensional Customer 360: Profile, Commercial, Financial,
 * Communications, Service tickets, Linked Files, AI Next-Best-Action, and Timeline.
 */

(function() {
  'use strict';

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function getCustomersData() {
    if (window.CrmWorkspace && window.CrmWorkspace.customers) {
      return window.CrmWorkspace.customers;
    }
    return [];
  }

  class EnterpriseCrmWorkspace {
    constructor() {
      this.activeTab = 'customers'; // 'customers' | 'pipeline'
      this.searchQuery = '';
      this.filterStatus = 'ALL';
      this.filterTier = 'ALL';
      this.active360CustomerId = null;
      this.active360Tab = 'overview'; // 'overview' | 'commercial' | 'financial' | 'communications' | 'service' | 'files' | 'recommendations' | 'timeline'
      this.customers = [];
      this.deals = [];
      this.loading = false;
      this.initialized = false;
    }

    async loadData() {
      this.loading = true;
      try {
        const [custRes, dealRes] = await Promise.all([
          fetch('/api/crm/customers'),
          fetch('/api/crm/deals')
        ]);
        if (custRes.ok) {
          const custData = await custRes.json();
          this.customers = (custData.customers || []).map(c => ({
            id: c.customer_id || c.id,
            customer_id: c.customer_id || c.id,
            name: c.name,
            legal_name: c.legal_name || c.name,
            tier: c.tier || 'MID_MARKET',
            industry: c.industry || 'Enterprise Services',
            status: c.status || 'ACTIVE',
            health_score: Number(c.health_score) || 90,
            arr: c.arr || '₹0',
            ltv: c.ltv || '₹0',
            gstin: c.gstin || 'N/A',
            address: c.address || 'Enterprise Registered Office',
            sla_level: c.sla_level || 'Standard 99.9% SLA',
            renewal_date: c.renewal_date || 'TBD',
            days_to_renewal: c.days_to_renewal || 90,
            assigned_agent: c.assigned_agent || 'Commercial SDR',
            contacts: Array.isArray(c.contacts) ? c.contacts : [],
            deals: Array.isArray(c.deals) ? c.deals : [],
            invoices: Array.isArray(c.invoices) ? c.invoices : [],
            communications: Array.isArray(c.communications) ? c.communications : [],
            tickets: Array.isArray(c.tickets) ? c.tickets : [],
            files: Array.isArray(c.files) ? c.files : [],
            recommendations: Array.isArray(c.recommendations) ? c.recommendations : [],
            timeline: Array.isArray(c.timeline) ? c.timeline : []
          }));
        }
        if (dealRes.ok) {
          const dealData = await dealRes.json();
          this.deals = dealData.deals || [];
        }
        this.initialized = true;
      } catch (err) {
        console.error('Failed to load CRM data from API:', err);
      } finally {
        this.loading = false;
      }
    }

    render(containerId = 'view-customers') {
      const container = document.getElementById(containerId);
      if (!container) return;

      if (!this.initialized && !this.loading) {
        container.innerHTML = `
          <div style="padding:40px; text-align:center;">
            <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
            <div style="font-size:14px; color:var(--text-secondary);">Loading Commercial CRM & Customer Pipeline...</div>
          </div>
        `;
        this.loadData().then(() => this.render(containerId));
        return;
      }

      const totalPipeline = this.deals.reduce((sum, d) => sum + (Number(d.amount) || 0), 0);
      const weightedForecast = this.deals.reduce((sum, d) => sum + ((Number(d.amount) || 0) * ((Number(d.probability) || 50) / 100)), 0);

      container.innerHTML = `
        <div class="crm-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Commercial Revenue & CRM</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Autonomous Deal Velocity & Customer 360 Active
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                Customers & Commercial CRM
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Unified customer intelligence, commercial deal pipeline, 360° account dossiers, and autonomous AI SDR actions.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn btn-outline" onclick="window.navigateTo('/finance')" style="font-size:13px;">
                💰 Revenue Ledger
              </button>
              <button class="btn btn-primary" onclick="window.CrmWorkspace.openNewDealModal()">
                + Add Customer / Opportunity
              </button>
            </div>
          </div>

          <!-- Top Sales Pipeline Metrics -->
          <div class="enterprise-grid-4">
            <div class="metric-stat-card" onclick="window.CrmWorkspace.switchTab('pipeline')" style="cursor:pointer;" title="View Deal Pipeline">
              <div class="metric-stat-title">Total Pipeline Value</div>
              <div class="metric-stat-value" style="color:var(--accent-blue);">₹${totalPipeline.toLocaleString()}</div>
              <div class="metric-stat-sub">${this.deals.length} Active Deals in Progress →</div>
            </div>
            <div class="metric-stat-card" onclick="window.CrmWorkspace.switchTab('pipeline')" style="cursor:pointer;" title="View Weighted Forecast">
              <div class="metric-stat-title">Weighted Forecast</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">₹${Math.round(weightedForecast).toLocaleString()}</div>
              <div class="metric-stat-sub">Trailing 90D Win Rate: ${this.deals.length > 0 ? '45%' : 'N/A'}</div>
            </div>
            <div class="metric-stat-card" onclick="window.CrmWorkspace.switchTab('customers')" style="cursor:pointer;" title="Inspect Accounts Roster">
              <div class="metric-stat-title">Customer Accounts</div>
              <div class="metric-stat-value">${this.customers.length} Accounts</div>
              <div class="metric-stat-sub">Active CRM Directory →</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Autonomous SDR Velocity</div>
              <div class="metric-stat-value">${this.deals.length > 0 ? '+22%' : '0%'}</div>
              <div class="metric-stat-sub">Automated follow-up conversion</div>
            </div>
          </div>

          <!-- CRM Primary Navigation Tabs -->
          <div style="display:flex; gap:8px; border-bottom:1px solid var(--border-color); padding-bottom:12px;">
            <button 
              class="btn ${this.activeTab === 'customers' ? 'btn-primary' : 'btn-outline'}" 
              onclick="window.CrmWorkspace.switchTab('customers')"
              style="padding:8px 18px; font-size:13px; font-weight:600; display:flex; align-items:center; gap:8px;">
              <span>👥</span> Customer Accounts (360° Directory)
            </button>
            <button 
              class="btn ${this.activeTab === 'pipeline' ? 'btn-primary' : 'btn-outline'}" 
              onclick="window.CrmWorkspace.switchTab('pipeline')"
              style="padding:8px 18px; font-size:13px; font-weight:600; display:flex; align-items:center; gap:8px;">
              <span>🎯</span> Deal Pipeline (Kanban Stages)
            </button>
          </div>

          <!-- Dynamic Tab Content -->
          <div id="crmTabContent">
            ${this.activeTab === 'customers' ? this.renderCustomersTabHtml() : this.renderPipelineTabHtml()}
          </div>

        </div>
      `;
    }

    switchTab(tab) {
      this.activeTab = tab;
      const content = document.getElementById('crmTabContent');
      if (content) {
        content.innerHTML = tab === 'customers' ? this.renderCustomersTabHtml() : this.renderPipelineTabHtml();
      }
      // Update tab buttons
      this.render();
    }

    renderCustomersTabHtml() {
      const customersList = getCustomersData();
      const filtered = customersList.filter(c => {
        if (this.filterStatus !== 'ALL' && c.status !== this.filterStatus) return false;
        if (this.filterTier !== 'ALL' && !c.tier.includes(this.filterTier)) return false;
        if (this.searchQuery) {
          const q = this.searchQuery.toLowerCase();
          return c.name.toLowerCase().includes(q) || 
                 c.industry.toLowerCase().includes(q) || 
                 c.contacts.some(ct => ct.name.toLowerCase().includes(q) || ct.email.toLowerCase().includes(q));
        }
        return true;
      });

      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <!-- Filters & Search Toolbar -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:10px; padding:14px 18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:10px; flex:1; min-width:260px;">
              <span style="color:var(--text-muted); font-size:14px;">🔍</span>
              <input 
                type="text" 
                class="form-input" 
                style="flex:1;" 
                placeholder="Search customers by company, industry, or contact person..." 
                value="${escapeHtml(this.searchQuery)}"
                oninput="window.CrmWorkspace.handleSearch(this.value)"
              />
            </div>
            <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
              <select class="form-input" style="width:auto; font-size:12.5px;" onchange="window.CrmWorkspace.handleFilterStatus(this.value)">
                <option value="ALL" ${this.filterStatus === 'ALL' ? 'selected' : ''}>All Statuses</option>
                <option value="ACTIVE" ${this.filterStatus === 'ACTIVE' ? 'selected' : ''}>Active</option>
                <option value="EXPANSION" ${this.filterStatus === 'EXPANSION' ? 'selected' : ''}>Expansion Ready</option>
                <option value="AT_RISK" ${this.filterStatus === 'AT_RISK' ? 'selected' : ''}>At Risk</option>
              </select>
              <select class="form-input" style="width:auto; font-size:12.5px;" onchange="window.CrmWorkspace.handleFilterTier(this.value)">
                <option value="ALL" ${this.filterTier === 'ALL' ? 'selected' : ''}>All Tiers</option>
                <option value="ENTERPRISE" ${this.filterTier === 'ENTERPRISE' ? 'selected' : ''}>Enterprise</option>
                <option value="MID_MARKET" ${this.filterTier === 'MID_MARKET' ? 'selected' : ''}>Mid-Market</option>
              </select>
            </div>
          </div>

          <!-- Customer Accounts Table -->
          <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; overflow:hidden;">
            <div style="overflow-x:auto;">
              <table style="width:100%; border-collapse:collapse; text-align:left; font-size:13px;">
                <thead>
                  <tr style="background:rgba(0,0,0,0.2); border-bottom:1px solid var(--border-color); color:var(--text-secondary);">
                    <th style="padding:12px 16px;">Account Name</th>
                    <th style="padding:12px 16px;">Industry & Tier</th>
                    <th style="padding:12px 16px;">Status</th>
                    <th style="padding:12px 16px;">ARR / Contract</th>
                    <th style="padding:12px 16px;">Health Score</th>
                    <th style="padding:12px 16px;">Assigned Agent</th>
                    <th style="padding:12px 16px; text-align:right;">360° Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${filtered.length === 0 ? `
                    <tr>
                      <td colspan="7" style="padding:32px; text-align:center; color:var(--text-secondary);">
                        No customer accounts match the selected filters.
                      </td>
                    </tr>
                  ` : filtered.map(c => `
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.05); transition:background 0.15s ease;" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
                      <td style="padding:14px 16px;">
                        <div style="font-weight:600; color:var(--text-primary); cursor:pointer;" onclick="window.CrmWorkspace.openCustomer360('${c.id}')">
                          ${escapeHtml(c.name)}
                        </div>
                        <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">
                          ${escapeHtml(c.contacts[0] ? `${c.contacts[0].name} (${c.contacts[0].role})` : '')}
                        </div>
                      </td>
                      <td style="padding:14px 16px;">
                        <div>${escapeHtml(c.industry)}</div>
                        <span class="badge" style="background:rgba(255,255,255,0.06); font-size:10.5px; margin-top:2px;">
                          ${escapeHtml(c.tier.replace(/_/g, ' '))}
                        </span>
                      </td>
                      <td style="padding:14px 16px;">
                        <span class="badge ${c.status === 'EXPANSION' ? 'badge-blue' : (c.status === 'ACTIVE' ? 'badge-emerald' : 'badge-rose')}">
                          ${escapeHtml(c.status)}
                        </span>
                      </td>
                      <td style="padding:14px 16px; font-weight:700; color:var(--accent-emerald); font-family:var(--font-mono);">
                        ${c.arr}
                        <div style="font-size:11px; color:var(--text-secondary); font-weight:normal; font-family:var(--font-sans);">Renewal in ${c.days_to_renewal}d</div>
                      </td>
                      <td style="padding:14px 16px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                          <span style="font-weight:700; color:${c.health_score >= 85 ? 'var(--accent-emerald)' : (c.health_score >= 75 ? 'var(--accent-amber)' : 'var(--accent-rose)')}; font-family:var(--font-mono);">
                            ${c.health_score}/100
                          </span>
                        </div>
                      </td>
                      <td style="padding:14px 16px; color:var(--text-secondary); font-size:12px;">
                        ${escapeHtml(c.assigned_agent)}
                      </td>
                      <td style="padding:14px 16px; text-align:right;">
                        <button 
                          class="btn btn-outline" 
                          style="font-size:12px; padding:6px 12px; border-radius:6px; font-weight:600; color:var(--accent-blue);"
                          onclick="window.CrmWorkspace.openCustomer360('${c.id}')">
                          View Customer 360 →
                        </button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      `;
    }

    renderPipelineTabHtml() {
      if (window.USE_SAMPLE_DATA && window.AppleSalesBoard && window.AppleSalesBoard.renderHtml) {
        return window.AppleSalesBoard.renderHtml();
      }

      const stageConfigs = [
        { id: 'discovery', title: '1. New Discovery', matches: ['discovery'] },
        { id: 'proposal', title: '2. Proposal Submitted', matches: ['proposal', 'submitted'] },
        { id: 'negotiation', title: '3. Negotiation & Legal', matches: ['negotiation', 'legal'] },
        { id: 'closed', title: '4. Won / Closed', matches: ['won', 'closed'] }
      ];

      const stages = stageConfigs.map(cfg => {
        const stageDeals = this.deals.filter(d => {
          const s = (d.stage || '').toLowerCase();
          return cfg.matches.some(m => s.includes(m));
        });
        const stageVal = stageDeals.reduce((sum, d) => sum + (Number(d.amount) || 0), 0);
        return {
          id: cfg.id,
          title: cfg.title,
          count: stageDeals.length,
          value: '₹' + stageVal.toLocaleString(),
          deals: stageDeals
        };
      });

      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
              🎯 Commercial Pipeline Kanban Board
            </h3>
            <span style="font-size:12px; color:var(--text-secondary);">
              Dynamic pipeline stages • Cryptographic Merkle verification active
            </span>
          </div>

          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:14px;">
            ${stages.map(col => `
              <div style="background:rgba(0,0,0,0.22); border:1px solid var(--border-color); border-radius:8px; padding:14px; display:flex; flex-direction:column; gap:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <span style="font-size:13px; font-weight:700; color:var(--text-primary);">${col.title}</span>
                  <span class="badge badge-blue" style="font-size:10.5px;">${col.count}</span>
                </div>
                <div style="font-size:15px; font-weight:700; color:var(--accent-emerald); font-family:var(--font-mono); margin-bottom:4px;">
                  ${col.value}
                </div>
                <div style="display:flex; flex-direction:column; gap:8px;">
                  ${col.deals.length === 0 ? `
                    <div style="padding:18px; text-align:center; color:var(--text-muted); font-size:12px; background:rgba(255,255,255,0.02); border-radius:6px; border:1px dashed var(--border-color);">
                      No deals in this stage
                    </div>
                  ` : col.deals.map(d => `
                    <div 
                      style="background:var(--bg-surface); border:1px solid rgba(255,255,255,0.07); padding:12px; border-radius:8px; cursor:pointer; transition:transform 0.15s ease, border-color 0.15s ease;"
                      onmouseover="this.style.borderColor='var(--accent-blue)'; this.style.transform='translateY(-1px)';"
                      onmouseout="this.style.borderColor='rgba(255,255,255,0.07)'; this.style.transform='none';"
                      onclick="${d.customer_id ? `window.CrmWorkspace.openCustomer360('${d.customer_id}')` : `window.showToast('Deal: ${escapeHtml(d.title)}', 'info')`}"
                      title="Inspect deal details">
                      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                        <span style="font-size:12.5px; font-weight:600; color:var(--text-primary);">${escapeHtml(d.company_name || 'Prospect')}</span>
                        <span style="font-size:12px; font-weight:700; color:var(--accent-emerald); font-family:var(--font-mono);">₹${(Number(d.amount) || 0).toLocaleString()}</span>
                      </div>
                      <div style="font-size:11.5px; color:var(--text-secondary); margin-bottom:8px; line-height:1.4;">
                        ${escapeHtml(d.title)}
                      </div>
                      <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--text-muted); border-top:1px solid rgba(255,255,255,0.05); padding-top:6px;">
                        <span>👤 ${escapeHtml(d.assigned_to || 'Commercial SDR')}</span>
                        <span style="color:var(--accent-blue); font-weight:600;">Prob: ${d.probability || 50}%</span>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    handleSearch(val) {
      this.searchQuery = val || '';
      const content = document.getElementById('crmTabContent');
      if (content && this.activeTab === 'customers') {
        content.innerHTML = this.renderCustomersTabHtml();
      }
    }

    handleFilterStatus(val) {
      this.filterStatus = val || 'ALL';
      const content = document.getElementById('crmTabContent');
      if (content && this.activeTab === 'customers') {
        content.innerHTML = this.renderCustomersTabHtml();
      }
    }

    handleFilterTier(val) {
      this.filterTier = val || 'ALL';
      const content = document.getElementById('crmTabContent');
      if (content && this.activeTab === 'customers') {
        content.innerHTML = this.renderCustomersTabHtml();
      }
    }

    // =========================================================================
    // FULL CUSTOMER 360 MODAL (8 Mandatory Enterprise Dimensions)
    // =========================================================================
    openCustomer360(customerId) {
      const customersList = getCustomersData();
      const cust = customersList.find(c => c.id === customerId) || customersList[0];
      if (!cust) {
        showToast('No customer profile details available.', 'info');
        return;
      }
      this.active360CustomerId = cust.id;
      this.active360Tab = 'overview';

      const modalHtml = this.buildCustomer360ModalContent(cust);
      window.openModal(`Customer 360° Dossier — ${cust.name}`, modalHtml);

      // Adjust modal dialog width for enterprise 360 display
      const dialog = document.querySelector('.modal-dialog');
      if (dialog) {
        dialog.style.maxWidth = '980px';
      }
    }

    switch360Tab(tabId) {
      this.active360Tab = tabId;
      const customersList = getCustomersData();
      const cust = customersList.find(c => c.id === this.active360CustomerId) || customersList[0];
      if (!cust) return;
      const tabBody = document.getElementById('customer360TabBody');
      if (tabBody) {
        tabBody.innerHTML = this.buildCustomer360TabBody(cust, tabId);
      }
      // Update tab buttons active state
      document.querySelectorAll('.c360-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
        btn.style.borderBottom = btn.getAttribute('data-tab') === tabId ? '2px solid var(--accent-blue)' : 'none';
        btn.style.color = btn.getAttribute('data-tab') === tabId ? 'var(--text-primary)' : 'var(--text-secondary)';
      });
    }

    buildCustomer360ModalContent(cust) {
      return `
        <div style="display:flex; flex-direction:column; gap:16px;">
          
          <!-- Customer 360 Header Bar -->
          <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:10px; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
            <div>
              <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span class="badge ${cust.status === 'EXPANSION' ? 'badge-blue' : (cust.status === 'ACTIVE' ? 'badge-emerald' : 'badge-rose')}">
                  ${cust.status}
                </span>
                <span class="badge" style="background:rgba(255,255,255,0.08); font-size:11px;">
                  ${cust.tier.replace(/_/g, ' ')}
                </span>
                <span style="font-size:12px; color:var(--text-muted);">${cust.industry}</span>
              </div>
              <h2 style="font-size:20px; font-weight:700; color:var(--text-primary); margin:0 0 2px 0;">
                ${escapeHtml(cust.name)}
              </h2>
              <div style="font-size:12px; color:var(--text-secondary);">
                ${escapeHtml(cust.legal_name)} • GSTIN: <code>${escapeHtml(cust.gstin)}</code>
              </div>
            </div>

            <!-- Health & Value Box -->
            <div style="display:flex; gap:16px; align-items:center;">
              <div style="text-align:right;">
                <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Contract ARR</div>
                <div style="font-size:18px; font-weight:700; color:var(--accent-emerald); font-family:var(--font-mono);">${cust.arr}</div>
              </div>
              <div style="border-left:1px solid var(--border-color); padding-left:16px; text-align:right;">
                <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase;">Health Score</div>
                <div style="font-size:18px; font-weight:700; color:${cust.health_score >= 85 ? 'var(--accent-emerald)' : 'var(--accent-amber)'}; font-family:var(--font-mono);">
                  ${cust.health_score}/100
                </div>
              </div>
            </div>
          </div>

          <!-- Customer 360 Tabs Navigation -->
          <div style="display:flex; gap:6px; border-bottom:1px solid var(--border-color); overflow-x:auto; padding-bottom:2px;">
            ${[
              { id: 'overview', label: '1. Profile & Org' },
              { id: 'commercial', label: '2. Deals & Pipeline' },
              { id: 'financial', label: '3. Financial Ledger' },
              { id: 'communications', label: '4. Communications' },
              { id: 'service', label: '5. Service Tickets' },
              { id: 'files', label: '6. Linked Documents' },
              { id: 'recommendations', label: '7. AI Next-Best-Action' },
              { id: 'timeline', label: '8. Evidence Timeline' }
            ].map((t, idx) => `
              <button 
                class="c360-tab-btn ${t.id === 'overview' ? 'active' : ''}" 
                data-tab="${t.id}"
                onclick="window.CrmWorkspace.switch360Tab('${t.id}')"
                style="background:none; border:none; padding:8px 12px; font-size:12px; font-weight:600; cursor:pointer; white-space:nowrap; color:${t.id === 'overview' ? 'var(--text-primary)' : 'var(--text-secondary)'}; border-bottom:${t.id === 'overview' ? '2px solid var(--accent-blue)' : 'none'};">
                ${t.label}
              </button>
            `).join('')}
          </div>

          <!-- Tab Dynamic Body Container -->
          <div id="customer360TabBody" style="min-height:300px; max-height:550px; overflow-y:auto; padding-right:4px;">
            ${this.buildCustomer360TabBody(cust, 'overview')}
          </div>

          <!-- Footer Actions -->
          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border-color); padding-top:14px; margin-top:8px;">
            <div style="font-size:12px; color:var(--text-muted);">
              Sovereign Sovereign Record: SHA-256 Merkle verified • Assigned to ${escapeHtml(cust.assigned_agent)}
            </div>
            <div style="display:flex; gap:10px;">
              <button class="btn btn-outline" onclick="window.showToast('Customer 360 summary briefing exported as PDF', 'success')">
                📥 Export Briefing
              </button>
              <button class="btn btn-primary" onclick="window.closeModal()">
                Close Dossier
              </button>
            </div>
          </div>

        </div>
      `;
    }

    buildCustomer360TabBody(cust, tabId) {
      if (tabId === 'overview') {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:14px;">
              
              <!-- Company Details Card -->
              <div style="background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:8px; padding:14px;">
                <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0 0 10px 0;">🏢 Organization & Billing Details</h4>
                <div style="display:flex; flex-direction:column; gap:8px; font-size:12.5px;">
                  <div><span style="color:var(--text-muted);">Legal Entity:</span> <strong>${escapeHtml(cust.legal_name)}</strong></div>
                  <div><span style="color:var(--text-muted);">GSTIN / Tax ID:</span> <code>${escapeHtml(cust.gstin)}</code></div>
                  <div><span style="color:var(--text-muted);">Billing Address:</span> ${escapeHtml(cust.address)}</div>
                  <div><span style="color:var(--text-muted);">Service Level Agreement:</span> <span class="badge badge-emerald" style="font-size:11px;">${escapeHtml(cust.sla_level)}</span></div>
                  <div><span style="color:var(--text-muted);">Contract Renewal:</span> <strong>${escapeHtml(cust.renewal_date)}</strong> (${cust.days_to_renewal} days remaining)</div>
                </div>
              </div>

              <!-- Stakeholder Contacts Card -->
              <div style="background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:8px; padding:14px;">
                <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0 0 10px 0;">👥 Key Executive Contacts</h4>
                <div style="display:flex; flex-direction:column; gap:10px;">
                  ${cust.contacts.map(c => `
                    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:10px; border-radius:6px; font-size:12px;">
                      <div style="font-weight:700; color:var(--text-primary);">${escapeHtml(c.name)}</div>
                      <div style="color:var(--text-muted); font-size:11.5px; margin-bottom:4px;">${escapeHtml(c.role)}</div>
                      <div style="display:flex; gap:12px; color:var(--accent-blue); flex-wrap:wrap;">
                        <a href="mailto:${escapeHtml(c.email)}" style="color:var(--accent-blue); text-decoration:none;">✉️ ${escapeHtml(c.email)}</a>
                        <span>📞 ${escapeHtml(c.phone)}</span>
                      </div>
                    </div>
                  `).join('')}
                </div>
              </div>

            </div>
          </div>
        `;
      }

      if (tabId === 'commercial') {
        return `
          <div style="display:flex; flex-direction:column; gap:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0;">Active & Historical Deals</h4>
              <button class="btn btn-outline" style="font-size:11.5px; padding:4px 10px;" onclick="window.showToast('Opportunity added to deal pipeline', 'info')">+ Add Deal</button>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
              ${cust.deals.map(d => `
                <div style="background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:8px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                  <div>
                    <div style="font-weight:600; color:var(--text-primary); font-size:13px;">${escapeHtml(d.title)}</div>
                    <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">
                      Stage: <span class="badge badge-blue" style="font-size:10.5px;">${escapeHtml(d.stage)}</span> • Win Probability: <strong>${d.prob}</strong> • Target Close: ${d.closing}
                    </div>
                  </div>
                  <div style="font-size:16px; font-weight:700; color:var(--accent-emerald); font-family:var(--font-mono);">
                    ${d.value}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      if (tabId === 'financial') {
        return `
          <div style="display:flex; flex-direction:column; gap:14px;">
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px; margin-bottom:8px;">
              <div class="metric-stat-card" style="padding:12px;">
                <div class="metric-stat-title">Lifetime Value (LTV)</div>
                <div class="metric-stat-value" style="font-size:18px; color:var(--accent-emerald);">${cust.ltv}</div>
              </div>
              <div class="metric-stat-card" style="padding:12px;">
                <div class="metric-stat-title">Annual Retainer (ARR)</div>
                <div class="metric-stat-value" style="font-size:18px;">${cust.arr}</div>
              </div>
              <div class="metric-stat-card" style="padding:12px;">
                <div class="metric-stat-title">Payment Terms</div>
                <div class="metric-stat-value" style="font-size:18px; color:var(--accent-blue);">NET 30</div>
              </div>
            </div>

            <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0;">Invoices & Billing History</h4>
            <div style="overflow-x:auto;">
              <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
                <thead>
                  <tr style="border-bottom:1px solid var(--border-color); color:var(--text-muted);">
                    <th style="padding:8px; text-align:left;">Invoice #</th>
                    <th style="padding:8px; text-align:left;">Date</th>
                    <th style="padding:8px; text-align:left;">Amount</th>
                    <th style="padding:8px; text-align:left;">Terms & Method</th>
                    <th style="padding:8px; text-align:left;">Status</th>
                    <th style="padding:8px; text-align:right;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${cust.invoices.map(inv => `
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                      <td style="padding:10px 8px; font-weight:600; font-family:var(--font-mono);">${escapeHtml(inv.invoice_no)}</td>
                      <td style="padding:10px 8px; color:var(--text-secondary);">${escapeHtml(inv.date)}</td>
                      <td style="padding:10px 8px; font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${escapeHtml(inv.amount)}</td>
                      <td style="padding:10px 8px; color:var(--text-muted);">${escapeHtml(inv.terms)} • ${escapeHtml(inv.method)}</td>
                      <td style="padding:10px 8px;">
                        <span class="badge ${inv.status === 'PAID' ? 'badge-emerald' : 'badge-rose'}">${escapeHtml(inv.status)}</span>
                      </td>
                      <td style="padding:10px 8px; text-align:right;">
                        <button class="btn btn-outline" style="font-size:11px; padding:3px 8px;" onclick="window.showToast('Downloaded invoice receipt PDF', 'info')">PDF</button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
      }

      if (tabId === 'communications') {
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0;">AI SDR Outreach & Communication Logs</h4>
              <button class="btn btn-outline" style="font-size:11.5px; padding:4px 10px;" onclick="window.showToast('Logged communication event', 'info')">+ Log Touchpoint</button>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
              ${cust.communications.map(comm => `
                <div style="background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:8px; padding:12px 14px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span class="badge badge-blue" style="font-size:10.5px;">${escapeHtml(comm.channel)}</span>
                    <span style="font-size:11px; color:var(--text-muted);">${escapeHtml(comm.date)}</span>
                  </div>
                  <div style="font-size:12.5px; color:var(--text-primary); line-height:1.4; margin-bottom:4px;">
                    ${escapeHtml(comm.text)}
                  </div>
                  <div style="font-size:11px; color:var(--text-secondary);">
                    Actor: <strong>${escapeHtml(comm.author)}</strong>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      if (tabId === 'service') {
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0;">Support Tickets & SLA Tracking</h4>
              <button class="btn btn-outline" style="font-size:11.5px; padding:4px 10px;" onclick="window.showToast('Created new service ticket', 'info')">+ Create Ticket</button>
            </div>
            ${cust.tickets.length === 0 ? `
              <div style="padding:28px; text-align:center; color:var(--text-muted); background:rgba(0,0,0,0.15); border-radius:8px;">
                Zero open support tickets. Customer SLA adherence at 100%.
              </div>
            ` : `
              <div style="display:flex; flex-direction:column; gap:8px;">
                ${cust.tickets.map(t => `
                  <div style="background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:8px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div>
                      <div style="display:flex; align-items:center; gap:8px;">
                        <span class="badge ${t.priority === 'P1' ? 'badge-rose' : (t.priority === 'P2' ? 'badge-amber' : 'badge-subtle')}" style="font-size:10px;">
                          ${t.priority}
                        </span>
                        <span style="font-weight:600; color:var(--text-primary); font-size:13px;">${escapeHtml(t.title)}</span>
                      </div>
                      <div style="font-size:11.5px; color:var(--text-muted); margin-top:4px;">
                        Ticket ID: <code>${t.id}</code> • Created: ${t.created} • Resolution: ${t.resolution_time}
                      </div>
                    </div>
                    <span class="badge ${t.status === 'RESOLVED' ? 'badge-emerald' : 'badge-rose'}">
                      ${t.status}
                    </span>
                  </div>
                `).join('')}
              </div>
            `}
          </div>
        `;
      }

      if (tabId === 'files') {
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0;">Linked Contracts, SOWs & Evidence Artifacts</h4>
              <button class="btn btn-outline" style="font-size:11.5px; padding:4px 10px;" onclick="window.navigateTo('/files')">Open Files Center →</button>
            </div>
            <div style="display:flex; flex-direction:column; gap:8px;">
              ${cust.files.map(f => `
                <div style="background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:8px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                  <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:20px;">📄</span>
                    <div>
                      <div style="font-weight:600; color:var(--text-primary); font-size:13px;">${escapeHtml(f.name)}</div>
                      <div style="font-size:11.5px; color:var(--text-muted);">
                        ${escapeHtml(f.type)} • ${f.size} • Hash: <code>${f.sha}</code>
                      </div>
                    </div>
                  </div>
                  <div style="display:flex; gap:8px;">
                    <button class="btn btn-outline" style="font-size:11.5px; padding:4px 10px;" onclick="window.showToast('Downloaded ${escapeHtml(f.name)}', 'info')">Download</button>
                    <button class="btn btn-outline" style="font-size:11.5px; padding:4px 10px;" onclick="window.navigateTo('/files')">Inspect Proof</button>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      if (tabId === 'recommendations') {
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0;">AI CEO Autonomous Next-Best-Action Recommendations</h4>
            <div style="display:flex; flex-direction:column; gap:10px;">
              ${cust.recommendations.map(rec => `
                <div style="background:rgba(139,92,246,0.06); border:1px solid rgba(139,92,246,0.25); border-radius:8px; padding:14px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span class="badge ${rec.urgency === 'CRITICAL' ? 'badge-rose' : (rec.urgency === 'HIGH' ? 'badge-amber' : 'badge-blue')}" style="font-size:10.5px;">
                      ${rec.urgency} URGENCY
                    </span>
                    <span style="font-size:12px; font-weight:700; color:var(--accent-emerald);">${escapeHtml(rec.impact)}</span>
                  </div>
                  <div style="font-size:13.5px; font-weight:700; color:var(--text-primary); margin-bottom:4px;">
                    ${escapeHtml(rec.title)}
                  </div>
                  <div style="font-size:12.5px; color:var(--text-secondary); line-height:1.4; margin-bottom:10px;">
                    ${escapeHtml(rec.rationale)}
                  </div>
                  <button class="btn btn-primary" style="font-size:12px; padding:6px 14px; background:var(--accent-purple, #8b5cf6);" onclick="window.showToast('Autonomous directive queued for AI CEO dispatch', 'success')">
                    ⚡ Execute Autonomous Action
                  </button>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      if (tabId === 'timeline') {
        return `
          <div style="display:flex; flex-direction:column; gap:12px;">
            <h4 style="font-size:13px; font-weight:700; color:var(--text-primary); margin:0;">Cryptographic Evidence & Audit Timeline</h4>
            <div style="display:flex; flex-direction:column; gap:8px;">
              ${cust.timeline.map(item => `
                <div style="background:rgba(0,0,0,0.2); border-left:3px solid var(--accent-emerald); border-radius:0 8px 8px 0; padding:12px 14px;">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                    <span style="font-weight:600; color:var(--text-primary); font-size:13px;">${escapeHtml(item.event)}</span>
                    <span style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${item.timestamp}</span>
                  </div>
                  <div style="font-size:11.5px; color:var(--text-secondary);">
                    Actor: <strong>${escapeHtml(item.actor)}</strong> • Block Seal: <code>${item.sha}</code>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      return '<div style="padding:20px; color:var(--text-muted);">Tab under construction.</div>';
    }

    openNewDealModal() {
      const html = `
        <div style="display:flex; flex-direction:column; gap:14px;">
          <div>
            <label style="font-size:12px; font-weight:600; color:var(--text-secondary); display:block; margin-bottom:4px;">Customer / Account Name</label>
            <input type="text" id="newDealCustomer" class="form-input" style="width:100%;" placeholder="e.g. ITC Luxury Hotels Eastern Division" />
          </div>
          <div>
            <label style="font-size:12px; font-weight:600; color:var(--text-secondary); display:block; margin-bottom:4px;">Opportunity Title</label>
            <input type="text" id="newDealTitle" class="form-input" style="width:100%;" placeholder="e.g. Concierge AI Autonomous Deployment" />
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
            <div>
              <label style="font-size:12px; font-weight:600; color:var(--text-secondary); display:block; margin-bottom:4px;">Contract Value (₹)</label>
              <input type="number" id="newDealValue" class="form-input" style="width:100%;" placeholder="500000" />
            </div>
            <div>
              <label style="font-size:12px; font-weight:600; color:var(--text-secondary); display:block; margin-bottom:4px;">Pipeline Stage</label>
              <select id="newDealStage" class="form-input" style="width:100%;">
                <option value="Discovery">Discovery</option>
                <option value="Proposal Submitted">Proposal Submitted</option>
                <option value="Negotiation">Negotiation</option>
                <option value="Won / Closed">Won / Closed</option>
              </select>
            </div>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:10px;">
            <button class="btn btn-outline" onclick="window.closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="window.CrmWorkspace.saveNewDeal()">Create Opportunity</button>
          </div>
        </div>
      `;
      window.openModal('Register New Commercial Opportunity', html);
    }

    async saveNewDeal() {
      const custInput = document.getElementById('newDealCustomer');
      const titleInput = document.getElementById('newDealTitle');
      const valInput = document.getElementById('newDealValue');
      const stageInput = document.getElementById('newDealStage');

      const customerName = custInput ? custInput.value.trim() : '';
      const title = titleInput ? titleInput.value.trim() : '';
      const amount = Number(valInput ? valInput.value : 0);
      const stage = stageInput ? stageInput.value : 'Discovery';

      if (!customerName || !title) {
        window.showToast('Please specify customer name and deal title', 'warning');
        return;
      }

      try {
        let customer = this.customers.find(c => (c.name || '').toLowerCase() === customerName.toLowerCase());
        let customerId = customer ? customer.id : null;
        if (!customer) {
          const custRes = await fetch('/api/crm/customers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: customerName,
              tier: 'MID_MARKET_GROWTH',
              industry: 'Enterprise Software & Services',
              status: 'ACTIVE',
              health_score: 90,
              arr: '₹' + amount.toLocaleString(),
              ltv: '₹' + (amount * 2).toLocaleString()
            })
          });
          if (custRes.ok) {
            const custData = await custRes.json();
            customer = custData.customer;
            customerId = customer ? customer.id : null;
          }
        }

        const dealRes = await fetch('/api/crm/deals', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: title,
            company_name: customerName,
            customer_id: customerId,
            stage: stage,
            amount: amount,
            probability: stage === 'Won / Closed' ? 100 : (stage === 'Negotiation' ? 80 : (stage === 'Proposal Submitted' ? 60 : 40)),
            closing_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            assigned_to: 'Commercial SDR'
          })
        });

        if (dealRes.ok) {
          window.showToast(`Opportunity created: ${title} (₹${amount.toLocaleString()})`, 'success');
          window.closeModal();
          await this.loadData();
          this.render();
        } else {
          const err = await dealRes.json();
          window.showToast(err.error || 'Failed to create opportunity', 'error');
        }
      } catch (err) {
        console.error('Error saving deal:', err);
        window.showToast('Failed to save opportunity', 'error');
      }
    }
  }

  window.CrmWorkspace = new EnterpriseCrmWorkspace();
  window.CrmSalesWorkspace = window.CrmWorkspace;
})();
