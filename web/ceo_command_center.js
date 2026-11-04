/**
 * URA / ZONATA — CEO Command Center (Home Cockpit)
 * Quiet • Spacious • Fast • Obvious in under 5 seconds
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

  class CeoCommandCenterController {
    constructor() {
      this.selectedDeptFilter = 'ALL';
    }

    render(container, snapshot) {
      if (!container) return;

      const dateStr = new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric'
      });

      const profitValue = (snapshot && snapshot.financial && snapshot.financial.net_profit)
        ? `₹${Number(snapshot.financial.net_profit).toLocaleString('en-IN')}`
        : '₹4,28,500';

      const approvalsList = [
        {
          id: 'app_01',
          title: 'Q4 DACH Marketing Campaign Budget',
          actorEntity: 'cmo',
          actorName: 'AI CMO',
          riskLevel: 'Medium',
          reason: 'Allocate ₹2,50,000 to capture surging luxury travel search queries in German-speaking territories.',
          worstCase: 'Ad spend underperforms ROAS benchmark by up to ₹40,000 before killswitch triggers.',
          alternative: 'Pilot with ₹75,000 micro-budget on high-intent search only.'
        },
        {
          id: 'app_02',
          title: 'Upgrade Database Connection Pool',
          actorEntity: 'cto',
          actorName: 'AI CTO',
          riskLevel: 'Low',
          reason: 'Expand connection concurrency from 20 to 50 sockets to absorb inbound webhook traffic.',
          worstCase: 'Negligible (zero downtime rolling restart).',
          alternative: 'Maintain existing pool with request queuing.'
        }
      ];

      const departments = [
        { id: 'coo', name: 'COO', label: 'Operations', metric: '12 Running', desc: '0 tasks blocked, SLAs at 99.8%', entity: 'coo' },
        { id: 'cmo', name: 'CMO', label: 'Marketing & Sales', metric: '4 Campaigns', desc: 'Inbound leads up +18% this week', entity: 'cmo' },
        { id: 'cto', name: 'CTO', label: 'Technology', metric: '3 Builds', desc: 'Website engines & MCP integrations verified', entity: 'cto' },
        { id: 'cfo', name: 'CFO', label: 'Finance & GL', metric: '₹4.28L Profit', desc: 'Audited double-entry balance sheet clean', entity: 'cfo' },
        { id: 'chro', name: 'CHRO', label: 'AI Workforce', metric: '14 Employees', desc: 'All employees certified on latest SOPs', entity: 'chro' },
        { id: 'security', name: 'Security', label: 'Cyber Defense', metric: '13 Layers', desc: 'Zero data leakage, continuous DLP active', entity: 'security' }
      ];

      const activityItems = [
        {
          intent: 'Optimized room pricing for peak weekend dates',
          reason: '3 regional competitors raised luxury suite prices by 8%.',
          state: 'done',
          result: 'Average daily rate expanded by 6%. Estimated extra profit: ₹45,000 / mo.',
          actorEntity: 'cmo',
          actorName: 'CMO Pricing Engine',
          timestamp: '12m ago',
          undoSeconds: 30
        },
        {
          intent: 'Synthesized 24 sales inquiries from WhatsApp channel',
          reason: 'New inbound customer leads received through automated verified campaign.',
          state: 'working',
          result: '18 qualified prospects queued for Account Executive follow-up.',
          actorEntity: 'cmo',
          actorName: 'Lead Generation Specialist',
          timestamp: '34m ago'
        },
        {
          intent: 'Verified SHA-256 cryptographic audit ledger',
          reason: 'Scheduled hourly consistency audit across all enterprise records.',
          state: 'done',
          result: '100% of event entries match tamper-evident root hash.',
          actorEntity: 'security',
          actorName: 'Sovereign Integrity Daemon',
          timestamp: '1h ago'
        }
      ];

      container.innerHTML = `
        <div style="max-width:1120px; margin:0 auto; display:flex; flex-direction:column; gap:36px;">

          <!-- 1. HERO COCKPIT GREETING & HEADLINE PROFIT -->
          <section style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:20px; padding-bottom:8px;">
            <div>
              <div class="t-caption" style="color:var(--label-3); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">
                ${dateStr}
              </div>
              <h1 class="t-large-title" style="margin-bottom:6px;">Good day, Owner</h1>
              <p class="t-callout" style="color:var(--label-2);">
                Everything is running smoothly. <strong>2 items</strong> need your review.
              </p>
            </div>

            <!-- Single Hero Metric: Profit this Month -->
            <div class="card-apple card-apple-hero hover-lift"
                 onclick="window.navigateTo('/finance')"
                 style="padding:20px 28px; display:flex; flex-direction:column; align-items:flex-end; min-width:260px; cursor:pointer;"
                 title="Click to view detailed Financial General Ledger">
              <span class="t-caption" style="text-transform:uppercase; letter-spacing:0.04em; color:var(--label-3);">This Month's Profit</span>
              <div style="display:flex; align-items:baseline; gap:10px; margin-top:2px;">
                <span class="t-display tabular-nums" style="color:var(--green);">${profitValue}</span>
                <span class="chip-apple chip-green" style="font-size:12px; padding:2px 8px;">+12%</span>
              </div>
              <div style="margin-top:6px; display:flex; align-items:center; gap:6px;">
                <!-- Subtle Mini Sparkline -->
                <svg width="80" height="18" viewBox="0 0 80 18" fill="none">
                  <path d="M2 14 L18 12 L34 15 L50 9 L66 11 L78 3" stroke="var(--green)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span class="t-footnote" style="color:var(--label-3);">vs last month</span>
              </div>
            </div>
          </section>

          <!-- 2. NEEDS YOU: APPROVALS STRIP -->
          <section>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <h2 class="t-title-2">Needs You</h2>
                <span class="apple-nav-badge" style="background:var(--orange); color:#FFFFFF;">2</span>
              </div>
              <span class="t-caption" style="color:var(--label-3);">Decisions waiting for sovereign owner approval</span>
            </div>

            <div>
              ${approvalsList.map(a => window.ApprovalCard ? window.ApprovalCard(a) : '').join('')}
            </div>
          </section>

          <!-- 3. DEPARTMENTS ROW -->
          <section>
            <div style="margin-bottom:14px;">
              <h2 class="t-title-2">Executive Departments</h2>
              <p class="t-footnote" style="margin-top:2px;">Tap any department to review its team, objectives, and active builds.</p>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:16px;">
              ${departments.map(d => `
                <div class="card-apple card-apple-interactive hover-lift"
                     onclick="DepartmentWorkspace.open('${d.id}')"
                     style="padding:20px; display:flex; flex-direction:column; justify-content:space-between; min-height:160px;">
                  <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                      ${window.AppTile ? window.AppTile({ entity: d.entity, size: 40 }) : ''}
                      <span class="status-dot-active"></span>
                    </div>
                    <div class="t-headline" style="font-size:15px; margin-bottom:2px;">${escapeHtml(d.label)}</div>
                    <div class="t-caption" style="color:var(--label-3);">${escapeHtml(d.name)}</div>
                  </div>
                  <div style="margin-top:14px; pt:8px; border-top:0.5px solid var(--separator);">
                    <div class="t-footnote" style="font-weight:600; color:var(--label);">${escapeHtml(d.metric)}</div>
                    <div class="t-caption" style="color:var(--label-2); font-size:11.5px; margin-top:2px;">${escapeHtml(d.desc)}</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </section>

          <!-- 4. KEY NUMBERS (Max 4 Cards) -->
          <section>
            <div style="margin-bottom:14px;">
              <h2 class="t-title-2">Key Business Performance</h2>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px;">
              <div class="card-apple hover-lift spring-press" onclick="window.navigateTo('/finance')">
                <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Monthly Revenue</span>
                <div class="t-title-1 tabular-nums" style="margin-top:4px;">₹14,80,000</div>
                <div class="t-footnote" style="color:var(--green); margin-top:4px;">+18% from organic search</div>
              </div>

              <div class="card-apple hover-lift spring-press" onclick="window.navigateTo('/finance')">
                <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Operating Margin</span>
                <div class="t-title-1 tabular-nums" style="margin-top:4px;">29.2%</div>
                <div class="t-footnote" style="color:var(--label-2); margin-top:4px;">Target: 28.0%</div>
              </div>

              <div class="card-apple hover-lift spring-press" onclick="window.navigateTo('/customers')">
                <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Active Sales Leads</span>
                <div class="t-title-1 tabular-nums" style="margin-top:4px;">142</div>
                <div class="t-footnote" style="color:var(--accent); margin-top:4px;">18 high-intent deals</div>
              </div>

              <div class="card-apple hover-lift spring-press" onclick="window.navigateTo('/customers')">
                <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Conversion Rate</span>
                <div class="t-title-1 tabular-nums" style="margin-top:4px;">4.6%</div>
                <div class="t-footnote" style="color:var(--green); margin-top:4px;">+0.8% post-checkout fix</div>
              </div>
            </div>
          </section>

          <!-- 5. LIVE ACTIVITY FEED -->
          <section>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
              <div>
                <h2 class="t-title-2">Live Activity</h2>
                <p class="t-footnote" style="margin-top:2px;">Real-time stream of what your AI company is doing right now.</p>
              </div>
              <button class="btn-apple btn-apple-plain" onclick="window.navigateTo('/activity')">
                <span>View Full Feed</span>
                ${window.Icon ? window.Icon({ name: 'arrow-right', size: 14, tone: 'accent' }) : '→'}
              </button>
            </div>

            <div>
              ${activityItems.map(act => window.ActionCard ? window.ActionCard(act) : '').join('')}
            </div>
          </section>

        </div>
      `;
    }
  }

  window.CeoCommandCenter = new CeoCommandCenterController();
})();
