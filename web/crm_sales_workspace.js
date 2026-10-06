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

  // Canonical Enterprise Customer Directory
  const CUSTOMERS_DATA = [
    {
      id: 'comp_cust_taj',
      name: 'Taj Hospitality & Leisure Corporate Account',
      legal_name: 'Taj Luxury Hospitality Ventures Ltd',
      tier: 'ENTERPRISE_PLATINUM',
      industry: 'Luxury Hospitality & Leisure',
      status: 'EXPANSION',
      health_score: 96,
      arr: '₹1,450,000',
      ltv: '₹3,820,000',
      gstin: '27AABCT8921K1ZD',
      address: 'Taj Palace Complex, Chanakyapuri, New Delhi 110021, India',
      sla_level: 'Mission-Critical 24/7 (99.98% SLA)',
      renewal_date: 'Nov 15, 2026',
      days_to_renewal: 40,
      assigned_agent: 'Priya Sharma (AI Key Accounts & SDR)',
      contacts: [
        { name: 'Aman Verma', role: 'VP Operations', email: 'aman.verma@tajhotels.example.com', phone: '+91 98201 44521' },
        { name: 'Radhika Nair', role: 'Director of Procurement', email: 'radhika.n@tajhotels.example.com', phone: '+91 98110 99234' }
      ],
      deals: [
        { id: 'deal_101', title: 'Pan-India Concierge AI Automation', stage: 'Negotiation', value: '₹650,000', prob: '85%', closing: 'Oct 20, 2026' },
        { id: 'deal_102', title: 'Room Service Voice AI Multi-Lingual Integration', stage: 'Proposal Submitted', value: '₹420,000', prob: '60%', closing: 'Nov 05, 2026' },
        { id: 'deal_103', title: 'Property Management Night Audit Reconciler', stage: 'Won / Closed', value: '₹380,000', prob: '100%', closing: 'Aug 14, 2026' }
      ],
      invoices: [
        { invoice_no: 'INV-2026-089', date: '2026-09-01', amount: '₹145,000', status: 'PAID', terms: 'NET_30', method: 'Stripe ACH' },
        { invoice_no: 'INV-2026-074', date: '2026-08-01', amount: '₹145,000', status: 'PAID', terms: 'NET_30', method: 'Stripe ACH' },
        { invoice_no: 'INV-2026-058', date: '2026-07-01', amount: '₹145,000', status: 'PAID', terms: 'NET_30', method: 'Stripe ACH' }
      ],
      communications: [
        { date: 'Yesterday, 16:42', channel: 'AI SDR Outreach', author: 'Commercial SDR Agent', text: 'Dispatched automated follow-up proposal with property-level ROI breakdown for Concierge pilot across 4 properties.' },
        { date: 'Oct 02, 11:30', channel: 'Executive Video Sync', author: 'Sukhraj Singh (Owner)', text: 'Quarterly strategy sync with VP Operations Aman Verma. Client confirmed budget authorization for pan-India expansion.' },
        { date: 'Sep 25, 09:15', channel: 'System Notification', author: 'Payment Gateway', text: 'Automatic recurring retainer settled for invoice #INV-2026-089 via Stripe.' }
      ],
      tickets: [
        { id: 'TICK-902', title: 'PMS Webhook Latency Calibration', priority: 'P2', status: 'RESOLVED', resolution_time: '1.4 hours', created: 'Sep 28, 2026' },
        { id: 'TICK-914', title: 'Custom Folio PDF Export Mapping', priority: 'P3', status: 'IN_PROGRESS', resolution_time: 'Pending Review', created: 'Oct 04, 2026' }
      ],
      files: [
        { name: 'Master_Service_Agreement_Taj_2026.pdf', size: '2.4 MB', type: 'PDF Contract', sha: 'sha256:7b21...9a0b' },
        { name: 'Concierge_Automation_SOW_v2.pdf', size: '1.1 MB', type: 'Statement of Work', sha: 'sha256:3c88...1f4e' },
        { name: 'SOC2_Type_II_Compliance_Certificate.pdf', size: '840 KB', type: 'Security Audit', sha: 'sha256:e92a...66d1' }
      ],
      recommendations: [
        { title: 'Schedule Executive QBR Before Q4 Renewal', urgency: 'HIGH', impact: 'Multi-year lock-in (+₹2.8M)', rationale: 'Contract renewal window opens in 40 days. Platform utilization spike (+34%) indicates high expansion readiness.' },
        { title: 'Propose Voice AI Add-on License', urgency: 'MEDIUM', impact: 'Upsell +₹420,000 ARR', rationale: 'Taj guest interaction volume exceeded standard tier allowance by 22% during September festival season.' }
      ],
      timeline: [
        { timestamp: '2026-10-04 14:20', event: 'Q4 Renewal Opportunity Created', actor: 'AI CEO Strategy Engine', sha: 'a89f...32d0' },
        { timestamp: '2026-09-28 15:40', event: 'Support Case TICK-902 Resolved', actor: 'Autonomous Support Agent', sha: '5c21...88ee' },
        { timestamp: '2026-09-01 09:30', event: 'Invoice #INV-2026-089 Verified & Dispatched', actor: 'Billing Agent', sha: 'f71e...88bc' }
      ]
    },
    {
      id: 'comp_cust_oberoi',
      name: 'Oberoi Luxe Group',
      legal_name: 'Oberoi Luxury Hospitality Services Pvt Ltd',
      tier: 'ENTERPRISE_GOLD',
      industry: 'Luxury Hospitality',
      status: 'ACTIVE',
      health_score: 88,
      arr: '₹980,000',
      ltv: '₹2,100,000',
      gstin: '07AAAC09281M1ZT',
      address: '7 Sham Nath Marg, Civil Lines, Delhi 110054, India',
      sla_level: 'Enterprise 99.9% SLA',
      renewal_date: 'Jan 20, 2027',
      days_to_renewal: 106,
      assigned_agent: 'AI Commercial SDR',
      contacts: [
        { name: 'Meera Sen', role: 'Head of Digital Innovation', email: 'meera.sen@oberoigroup.example.com', phone: '+91 98450 11209' }
      ],
      deals: [
        { id: 'deal_201', title: 'Dynamic Pricing & Folio Balancer', stage: 'Discovery', value: '₹450,000', prob: '50%', closing: 'Nov 12, 2026' }
      ],
      invoices: [
        { invoice_no: 'INV-2026-085', date: '2026-09-05', amount: '₹98,000', status: 'PAID', terms: 'NET_30', method: 'Wire Transfer' }
      ],
      communications: [
        { date: 'Oct 03, 15:10', channel: 'AI SDR Outreach', author: 'AI Commercial SDR', text: 'Shared benchmarking report illustrating 4.2x faster night audit reconciliation across luxury hotels.' }
      ],
      tickets: [
        { id: 'TICK-884', title: 'API Authentication Token Rotation', priority: 'P3', status: 'RESOLVED', resolution_time: '45 mins', created: 'Sep 18, 2026' }
      ],
      files: [
        { name: 'Oberoi_MSA_2026.pdf', size: '1.9 MB', type: 'PDF Contract', sha: 'sha256:d81a...001c' }
      ],
      recommendations: [
        { title: 'Confirm Technical Discovery Call', urgency: 'HIGH', impact: 'Accelerate Deal Close', rationale: 'Digital Innovation team viewed proposal deck 4 times in the past 48 hours.' }
      ],
      timeline: [
        { timestamp: '2026-10-03 15:10', event: 'Proposal Deck Viewed', actor: 'Client (Meera Sen)', sha: 'bc12...99aa' },
        { timestamp: '2026-09-05 10:12', event: 'Invoice #INV-2026-085 Settled', actor: 'Banking Gateway', sha: '1100...ff42' }
      ]
    },
    {
      id: 'comp_cust_apex',
      name: 'Apex Industrial Supplies Ltd',
      legal_name: 'Apex Industrial Solutions & Manufacturing Ltd',
      tier: 'ENTERPRISE_MFG',
      industry: 'Industrial Spares & Manufacturing',
      status: 'EXPANSION',
      health_score: 93,
      arr: '₹1,200,000',
      ltv: '₹2,900,000',
      gstin: '24AABCA5512J1ZY',
      address: 'GIDC Industrial Estate, Vatva, Ahmedabad 382445, Gujarat',
      sla_level: 'Enterprise 99.95% SLA',
      renewal_date: 'Mar 10, 2027',
      days_to_renewal: 155,
      assigned_agent: 'Supply Chain Operations Agent',
      contacts: [
        { name: 'Rajesh Goel', role: 'Chief Operating Officer', email: 'rajesh@apexindustrial.example.com', phone: '+91 97129 33011' }
      ],
      deals: [
        { id: 'deal_301', title: 'Autonomous Warehouse Robot Synchronization', stage: 'Proposal Submitted', value: '₹800,000', prob: '75%', closing: 'Dec 01, 2026' }
      ],
      invoices: [
        { invoice_no: 'INV-2026-091', date: '2026-09-12', amount: '₹120,000', status: 'PAID', terms: 'NET_15', method: 'NEFT / RTGS' }
      ],
      communications: [
        { date: 'Oct 01, 10:00', channel: 'On-site Inspection', author: 'Operations Team', text: 'Factory floor audit completed. IoT sensors ready for robotic telemetry streaming.' }
      ],
      tickets: [],
      files: [
        { name: 'Apex_Enterprise_Agreement.pdf', size: '3.1 MB', type: 'PDF Agreement', sha: 'sha256:11bb...cc21' }
      ],
      recommendations: [
        { title: 'Finalize Warehouse Hardware Specification', urgency: 'MEDIUM', impact: 'Ensure Deployment Schedule', rationale: 'Procurement committee approval scheduled for next Tuesday.' }
      ],
      timeline: [
        { timestamp: '2026-09-28 11:00', event: 'Sensor API Bridge Validated', actor: 'IoT Bridge Node', sha: '99aa...22f1' }
      ]
    },
    {
      id: 'comp_cust_leela',
      name: 'Leela Palaces Hotels & Resorts',
      legal_name: 'The Leela Palaces Hospitality Ltd',
      tier: 'MID_MARKET_GROWTH',
      industry: 'Hospitality',
      status: 'AT_RISK',
      health_score: 74,
      arr: '₹720,000',
      ltv: '₹1,100,000',
      gstin: '29AABCL4419P1ZE',
      address: '23 Airport Road, Bengaluru 560008, Karnataka, India',
      sla_level: 'Standard Business Hours SLA',
      renewal_date: 'Oct 28, 2026',
      days_to_renewal: 22,
      assigned_agent: 'AI Commercial SDR',
      contacts: [
        { name: 'Sanjay Gupta', role: 'General Manager Systems', email: 's.gupta@theleela.example.com', phone: '+91 98860 77123' }
      ],
      deals: [
        { id: 'deal_401', title: 'Service Desk AI Agent Renewal & Expansion', stage: 'Negotiation', value: '₹600,000', prob: '40%', closing: 'Oct 28, 2026' }
      ],
      invoices: [
        { invoice_no: 'INV-2026-081', date: '2026-08-15', amount: '₹60,000', status: 'OVERDUE', terms: 'NET_30', method: 'Invoice Awaiting Payment' }
      ],
      communications: [
        { date: 'Oct 04, 09:30', channel: 'AI Finance Email', author: 'Treasury & Billing Agent', text: 'Gentle overdue notice dispatched with direct payment portal link.' }
      ],
      tickets: [
        { id: 'TICK-908', title: 'Intermittent WiFi Robot Roaming Disconnect', priority: 'P1', status: 'OPEN', resolution_time: 'In Progress (Active)', created: 'Oct 03, 2026' }
      ],
      files: [
        { name: 'Leela_Contract_2025.pdf', size: '1.2 MB', type: 'PDF Contract', sha: 'sha256:88ee...99ac' }
      ],
      recommendations: [
        { title: 'Escalate Open P1 Ticket To Engineering Lead', urgency: 'CRITICAL', impact: 'Retain ₹720K ARR Account', rationale: 'Account health fell to 74 due to open P1 ticket during renewal window. Requires priority engineering dispatch.' },
        { title: 'Waive Late Fee on Invoice #INV-2026-081 as Goodwill', urgency: 'HIGH', impact: 'Smooth Renewal Closing', rationale: 'Acknowledge connectivity inconvenience with goodwill credit to unlock contract extension.' }
      ],
      timeline: [
        { timestamp: '2026-10-04 09:30', event: 'Risk Flag: P1 Ticket in Active Renewal Window', actor: 'AI CEO Risk Engine', sha: 'ee33...77a1' },
        { timestamp: '2026-10-03 14:15', event: 'Ticket TICK-908 Opened (Severity P1)', actor: 'Customer Contact', sha: '41ab...00de' }
      ]
    }
  ];

  class EnterpriseCrmWorkspace {
    constructor() {
      this.activeTab = 'customers'; // 'customers' | 'pipeline'
      this.searchQuery = '';
      this.filterStatus = 'ALL';
      this.filterTier = 'ALL';
      this.active360CustomerId = null;
      this.active360Tab = 'overview'; // 'overview' | 'commercial' | 'financial' | 'communications' | 'service' | 'files' | 'recommendations' | 'timeline'
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
              <div class="metric-stat-value" style="color:var(--accent-blue);">₹8,900,000</div>
              <div class="metric-stat-sub">42 Active Deals in Progress →</div>
            </div>
            <div class="metric-stat-card" onclick="window.CrmWorkspace.switchTab('pipeline')" style="cursor:pointer;" title="View Weighted Forecast">
              <div class="metric-stat-title">Weighted Forecast</div>
              <div class="metric-stat-value" style="color:var(--accent-emerald);">₹5,420,000</div>
              <div class="metric-stat-sub">Trailing 90D Win Rate: 44.6%</div>
            </div>
            <div class="metric-stat-card" onclick="window.CrmWorkspace.switchTab('customers')" style="cursor:pointer;" title="Inspect Accounts Roster">
              <div class="metric-stat-title">Customer Accounts</div>
              <div class="metric-stat-value">${CUSTOMERS_DATA.length} Key Accounts</div>
              <div class="metric-stat-sub">Avg Health Score: 87.8/100 →</div>
            </div>
            <div class="metric-stat-card">
              <div class="metric-stat-title">Autonomous SDR Velocity</div>
              <div class="metric-stat-value">+22%</div>
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
      const filtered = CUSTOMERS_DATA.filter(c => {
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
      const stages = [
        { 
          id: 'discovery', 
          title: '1. New Discovery', 
          count: 15, 
          value: '₹2.1M', 
          deals: [
            { id: 'd1', name: 'Oberoi Luxe Group', deal: 'Dynamic Pricing AI Folio Balancer', value: '₹450,000', owner: 'Commercial SDR', cid: 'comp_cust_oberoi' },
            { id: 'd2', name: 'Leela Palaces Hospitality', deal: 'Front Desk Multilingual Voice Bot', value: '₹600,000', owner: 'Sales Agent', cid: 'comp_cust_leela' }
          ] 
        },
        { 
          id: 'proposal', 
          title: '2. Proposal Submitted', 
          count: 12, 
          value: '₹3.2M', 
          deals: [
            { id: 'd3', name: 'Taj Hospitality Ventures', deal: 'Pan-India Concierge AI Automation', value: '₹650,000', owner: 'Priya Sharma', cid: 'comp_cust_taj' },
            { id: 'd4', name: 'Apex Industrial Supplies', deal: 'Autonomous Warehouse Robot Sync', value: '₹800,000', owner: 'Operations Agent', cid: 'comp_cust_apex' }
          ] 
        },
        { 
          id: 'negotiation', 
          title: '3. Negotiation & Legal', 
          count: 9, 
          value: '₹2.4M', 
          deals: [
            { id: 'd5', name: 'Taj Luxury Group', deal: 'Multi-Lingual Room Service Integration', value: '₹420,000', owner: 'Priya Sharma', cid: 'comp_cust_taj' },
            { id: 'd6', name: 'Radisson Corporate East', deal: 'Autonomous Energy & HVAC Optimization', value: '₹950,000', owner: 'Enterprise Exec', cid: 'comp_cust_taj' }
          ] 
        },
        { 
          id: 'closed', 
          title: '4. Won / Closed', 
          count: 6, 
          value: '₹1.2M', 
          deals: [
            { id: 'd7', name: 'Taj Heritage Palace', deal: 'Night Audit Ledger Automation (Annual)', value: '₹380,000', owner: 'Billing Agent', cid: 'comp_cust_taj' },
            { id: 'd8', name: 'Hyatt Regency Mumbai', deal: 'Guest Checkout Concierge Pilot', value: '₹700,000', owner: 'Sales Agent', cid: 'comp_cust_oberoi' }
          ] 
        }
      ];

      return `
        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; padding:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <h3 style="font-size:16px; font-weight:700; color:var(--text-primary); margin:0;">
              🎯 Commercial Pipeline Kanban Board
            </h3>
            <span style="font-size:12px; color:var(--text-secondary);">
              Drag & drop pipeline stages • Automated Merkle contract sealing
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
                  ${col.deals.map(d => `
                    <div 
                      style="background:var(--bg-surface); border:1px solid rgba(255,255,255,0.07); padding:12px; border-radius:8px; cursor:pointer; transition:transform 0.15s ease, border-color 0.15s ease;"
                      onmouseover="this.style.borderColor='var(--accent-blue)'; this.style.transform='translateY(-1px)';"
                      onmouseout="this.style.borderColor='rgba(255,255,255,0.07)'; this.style.transform='none';"
                      onclick="window.CrmWorkspace.openCustomer360('${d.cid}')"
                      title="Click to open Customer 360 for ${escapeHtml(d.name)}">
                      <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                        <span style="font-size:12.5px; font-weight:600; color:var(--text-primary);">${escapeHtml(d.name)}</span>
                        <span style="font-size:12px; font-weight:700; color:var(--accent-emerald); font-family:var(--font-mono);">${d.value}</span>
                      </div>
                      <div style="font-size:11.5px; color:var(--text-secondary); margin-bottom:8px; line-height:1.4;">
                        ${escapeHtml(d.deal)}
                      </div>
                      <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--text-muted); border-top:1px solid rgba(255,255,255,0.05); padding-top:6px;">
                        <span>👤 ${escapeHtml(d.owner)}</span>
                        <span style="color:var(--accent-blue); font-weight:600;">View 360° →</span>
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
      const cust = CUSTOMERS_DATA.find(c => c.id === customerId) || CUSTOMERS_DATA[0];
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
      const cust = CUSTOMERS_DATA.find(c => c.id === this.active360CustomerId) || CUSTOMERS_DATA[0];
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

    saveNewDeal() {
      const cust = document.getElementById('newDealCustomer');
      const title = document.getElementById('newDealTitle');
      const val = document.getElementById('newDealValue');
      const stage = document.getElementById('newDealStage');

      if (!cust || !cust.value.trim() || !title || !title.value.trim()) {
        window.showToast('Please specify customer name and deal title', 'warning');
        return;
      }

      window.showToast(`Opportunity created for ${cust.value.trim()} (₹${Number(val ? val.value : 0).toLocaleString()})`, 'success');
      window.closeModal();
      this.render();
    }
  }

  window.CrmWorkspace = new EnterpriseCrmWorkspace();
  window.CrmSalesWorkspace = window.CrmWorkspace;
})();
