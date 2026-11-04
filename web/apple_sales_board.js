/**
 * URA / ZONATA — Apple-Grade Sales Pipeline Board
 * Calm • Spacious • Fast • Obvious
 * 5-Stage Commercial Pipeline Kanban with deal cards, assigned AI specialists, and probability scoring.
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

  const STAGES = [
    { id: 'inbound', title: '1. Inbound & Discovery', color: 'var(--accent)' },
    { id: 'qualified', title: '2. Qualified & Scored', color: 'var(--purple)' },
    { id: 'proposal', title: '3. Proposal Sent', color: 'var(--orange)' },
    { id: 'negotiation', title: '4. Negotiation', color: 'var(--teal)' },
    { id: 'won', title: '5. Won & Booked', color: 'var(--green)' }
  ];

  const DEALS_DATA = [
    {
      id: 'deal_01',
      title: 'Alpine Luxury Chalet Retreat',
      company: 'Vanderbilt Family Office',
      amount: 450000,
      stage: 'proposal',
      specialist: 'Inbound Sales Lead Analyst',
      specialistEntity: 'cmo',
      probability: 78,
      nextAction: 'AI proposal follow-up tomorrow at 10:00 AM',
      channel: 'High-Net-Worth Search Campaign',
      notes: '7-night stay for 14 guests. Requested private chef and bespoke transfers.'
    },
    {
      id: 'deal_02',
      title: 'Q4 Annual Leadership Summit',
      company: 'Fintech Nexus Europe',
      amount: 720000,
      stage: 'negotiation',
      specialist: 'CMO Pricing Engine',
      specialistEntity: 'cmo',
      probability: 88,
      nextAction: 'Contract review scheduled with Legal Analyst',
      channel: 'Direct Referral',
      notes: 'Corporate group booking. Seeking full venue exclusivity and customized AV setup.'
    },
    {
      id: 'deal_03',
      title: 'Private Estate Wedding & Banquet',
      company: 'Somerset & Co. Estates',
      amount: 600000,
      stage: 'qualified',
      specialist: 'Inbound Sales Lead Analyst',
      specialistEntity: 'cmo',
      probability: 65,
      nextAction: 'Drafting custom itemized banquet proposal',
      channel: 'Instagram Verified Ad',
      notes: 'Inquiry qualified with verified budget. 80 guests expected.'
    },
    {
      id: 'deal_04',
      title: 'Executive Winter Holiday Package',
      company: 'Dr. Florian Becker',
      amount: 280000,
      stage: 'won',
      specialist: 'Growth Campaign Manager',
      specialistEntity: 'cmo',
      probability: 100,
      nextAction: 'Payment confirmed. Digital keys dispatched',
      channel: 'Perplexity AI Answer Citation',
      notes: 'Discovered through AI citation on top luxury suites in Switzerland.'
    },
    {
      id: 'deal_05',
      title: 'Architectural Design Offsite',
      company: 'Studio Kroma Zürich',
      amount: 320000,
      stage: 'inbound',
      specialist: 'Inbound Sales Lead Analyst',
      specialistEntity: 'cmo',
      probability: 45,
      nextAction: 'Autonomous WhatsApp response sent in 42s',
      channel: 'Google Luxury Search',
      notes: 'New inquiry received 24 minutes ago. Preferred weekend in late November.'
    },
    {
      id: 'deal_06',
      title: 'Holiday Family Gala',
      company: 'Harrison Group',
      amount: 410000,
      stage: 'won',
      specialist: 'Growth Campaign Manager',
      specialistEntity: 'cmo',
      probability: 100,
      nextAction: 'Concierge briefing complete',
      channel: 'Repeat Customer',
      notes: 'Annual recurring booking. Full deposit logged in cryptographic general ledger.'
    }
  ];

  class AppleSalesBoardController {
    constructor() {
      this.containerId = 'view-customers';
      this.deals = DEALS_DATA;
      this.activeFilter = 'ALL';
    }

    render(containerOrId = this.containerId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;

      if (!container) return;

      container.innerHTML = this.renderHtml();
    }

    renderHtml() {
      const totalPipeline = this.deals.reduce((sum, d) => sum + d.amount, 0);
      const weightedValue = this.deals.reduce((sum, d) => sum + Math.round(d.amount * (d.probability / 100)), 0);
      const wonDeals = this.deals.filter(d => d.stage === 'won');
      const wonValue = wonDeals.reduce((sum, d) => sum + d.amount, 0);
      const winRate = Math.round((wonDeals.length / this.deals.length) * 100) || 0;
      const avgDeal = Math.round(totalPipeline / this.deals.length) || 0;

      return `
        <div style="max-width:1320px; margin:0 auto; display:flex; flex-direction:column; gap:32px;">

          <!-- 1. HEADER & ACTIONS -->
          <header style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:20px; padding-bottom:8px;">
            <div>
              <div class="t-caption" style="text-transform:uppercase; letter-spacing:0.05em; color:var(--accent); font-weight:700; margin-bottom:4px;">
                Commercial Revenue Engine
              </div>
              <h1 class="t-large-title" style="margin:0;">Sales Pipeline & Deals Board</h1>
              <p class="t-callout" style="color:var(--label-2); margin-top:6px;">
                Visual deal progression managed by AI Sales Specialists with automated follow-ups.
              </p>
            </div>

            <button class="btn-apple btn-apple-primary spring-press"
                    onclick="AppleSalesBoard.openNewDealModal()"
                    style="font-size:14px; padding:10px 20px;">
              ${window.Icon ? window.Icon({ name: 'plus', size: 16 }) : '+'}
              <span>Create New Deal</span>
            </button>
          </header>

          <!-- 2. TOP PERFORMANCE CARDS -->
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px;">
            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Total Active Pipeline</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px;">₹${totalPipeline.toLocaleString('en-IN')}</div>
              <div class="t-footnote" style="color:var(--label-2); margin-top:4px;">${this.deals.length} tracked opportunities</div>
            </div>

            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Weighted Expected Value</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px; color:var(--accent);">₹${weightedValue.toLocaleString('en-IN')}</div>
              <div class="t-footnote" style="color:var(--green); margin-top:4px;">Empirical probability weighting</div>
            </div>

            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Closed & Won Revenue</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px; color:var(--green);">₹${wonValue.toLocaleString('en-IN')}</div>
              <div class="t-footnote" style="color:var(--green); margin-top:4px;">${wonDeals.length} bookings confirmed</div>
            </div>

            <div class="card-apple" style="padding:20px;">
              <span class="t-caption" style="text-transform:uppercase; color:var(--label-3);">Win Rate & Avg Deal</span>
              <div class="t-display tabular-nums" style="margin-top:4px; font-size:28px;">${winRate}%</div>
              <div class="t-footnote" style="color:var(--label-2); margin-top:4px;">Avg deal: ₹${avgDeal.toLocaleString('en-IN')}</div>
            </div>
          </div>

          <!-- 3. KANBAN PIPELINE BOARD -->
          <div class="apple-kanban-board">
            ${STAGES.map(stage => {
              const stageDeals = this.deals.filter(d => d.stage === stage.id);
              const stageVal = stageDeals.reduce((sum, d) => sum + d.amount, 0);

              return `
                <div class="apple-kanban-column" id="col-${stage.id}">
                  <!-- Column Header -->
                  <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom:8px; border-bottom:0.5px solid var(--separator);">
                    <div>
                      <div class="t-headline" style="font-size:14px; color:var(--label);">${escapeHtml(stage.title)}</div>
                      <div class="t-footnote tabular-nums" style="color:var(--green); font-weight:600; margin-top:2px;">
                        ₹${stageVal.toLocaleString('en-IN')}
                      </div>
                    </div>
                    <span class="chip-apple chip-neutral" style="font-size:11px; padding:2px 8px;">
                      ${stageDeals.length}
                    </span>
                  </div>

                  <!-- Deal Cards -->
                  <div style="display:flex; flex-direction:column; gap:12px; flex:1;">
                    ${stageDeals.length === 0 ? `
                      <div style="padding:32px 16px; text-align:center; color:var(--label-3); font-size:13px; border:1px dashed var(--separator); border-radius:var(--r-md);">
                        No deals in this stage
                      </div>
                    ` : stageDeals.map(d => `
                      <div class="apple-deal-card hover-lift"
                           onclick="AppleSalesBoard.inspectDeal('${d.id}')">
                        
                        <!-- Deal Top -->
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                          <div>
                            <div class="t-headline" style="font-size:14.5px; color:var(--label); line-height:1.35;">${escapeHtml(d.title)}</div>
                            <div class="t-caption" style="color:var(--label-2); margin-top:2px;">${escapeHtml(d.company)}</div>
                          </div>
                          <span class="chip-apple ${d.probability >= 75 ? 'chip-green' : d.probability >= 50 ? 'chip-orange' : 'chip-neutral'}"
                                style="font-size:11px; padding:2px 6px;">
                            ${d.probability}%
                          </span>
                        </div>

                        <!-- Amount -->
                        <div class="t-title-3 tabular-nums" style="color:var(--green); font-size:17px; margin-top:4px;">
                          ₹${d.amount.toLocaleString('en-IN')}
                        </div>

                        <!-- Assigned Specialist -->
                        <div style="display:flex; align-items:center; gap:8px; margin-top:4px; padding-top:8px; border-top:0.5px solid var(--separator);">
                          ${window.AppTile ? window.AppTile({ entity: d.specialistEntity, size: 24 }) : ''}
                          <span class="t-caption" style="color:var(--label-2); font-size:11.5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                            ${escapeHtml(d.specialist)}
                          </span>
                        </div>

                        <!-- Next Action -->
                        <div class="t-caption" style="color:var(--accent); font-size:11.5px; margin-top:2px; display:flex; align-items:center; gap:4px;">
                          <span class="status-dot-active" style="width:6px; height:6px;"></span>
                          <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(d.nextAction)}</span>
                        </div>

                        <!-- Advance Stage Quick Button -->
                        ${stage.id !== 'won' ? `
                          <div style="display:flex; justify-content:flex-end; margin-top:6px;" onclick="event.stopPropagation();">
                            <button class="btn-apple btn-apple-plain spring-press"
                                    onclick="AppleSalesBoard.advanceStage('${d.id}')"
                                    style="padding:3px 8px; font-size:11px; color:var(--accent);">
                              Advance Stage →
                            </button>
                          </div>
                        ` : ''}

                      </div>
                    `).join('')}
                  </div>
                </div>
              `;
            }).join('')}
          </div>

        </div>
      `;
    }

    advanceStage(dealId) {
      const deal = this.deals.find(d => d.id === dealId);
      if (!deal) return;

      const stageOrder = ['inbound', 'qualified', 'proposal', 'negotiation', 'won'];
      const currentIndex = stageOrder.indexOf(deal.stage);
      if (currentIndex >= 0 && currentIndex < stageOrder.length - 1) {
        deal.stage = stageOrder[currentIndex + 1];
        if (deal.stage === 'won') deal.probability = 100;
        else deal.probability = Math.min(95, deal.probability + 15);

        if (window.UI && window.UI.showToast) {
          window.UI.showToast(`Deal advanced to ${deal.stage.toUpperCase()}`, 'success');
        }
        this.render();
      }
    }

    inspectDeal(dealId) {
      const deal = this.deals.find(d => d.id === dealId);
      if (!deal) return;

      if (!window.Inspector || !window.Inspector.open) return;

      const content = `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <div>
            <span class="chip-apple ${deal.stage === 'won' ? 'chip-green' : 'chip-accent'}" style="font-size:12px; margin-bottom:8px;">
              ${deal.stage.toUpperCase()}
            </span>
            <h4 class="t-title-2" style="margin:4px 0 2px 0;">${escapeHtml(deal.title)}</h4>
            <p class="t-caption" style="color:var(--label-2);">${escapeHtml(deal.company)}</p>
          </div>

          <div style="background:var(--surface-2); padding:16px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
            <span class="t-caption" style="color:var(--label-3);">Deal Value</span>
            <div class="t-display tabular-nums" style="color:var(--green); font-size:28px; margin-top:2px;">
              ₹${deal.amount.toLocaleString('en-IN')}
            </div>
            <div class="t-caption" style="color:var(--label-2); margin-top:4px;">
              Lead Source: <strong>${escapeHtml(deal.channel)}</strong>
            </div>
          </div>

          <div style="display:flex; align-items:center; gap:12px; background:var(--surface-2); padding:12px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
            ${window.AppTile ? window.AppTile({ entity: deal.specialistEntity, size: 36 }) : ''}
            <div>
              <div class="t-headline" style="font-size:14px;">${escapeHtml(deal.specialist)}</div>
              <div class="t-caption" style="color:var(--label-2);">Autonomous Deal Owner</div>
            </div>
          </div>

          <div>
            <span class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3);">Deal Notes & Brief</span>
            <p class="t-body" style="font-size:13.5px; color:var(--label); margin-top:4px; line-height:1.45;">
              ${escapeHtml(deal.notes)}
            </p>
          </div>

          <div>
            <span class="t-caption" style="font-weight:600; text-transform:uppercase; color:var(--label-3);">Next Scheduled Step</span>
            <div style="display:flex; align-items:center; gap:8px; margin-top:4px; background:var(--accent-tint); padding:10px 12px; border-radius:var(--r-md); color:var(--accent); font-size:13px; font-weight:500;">
              <span class="status-dot-active"></span>
              <span>${escapeHtml(deal.nextAction)}</span>
            </div>
          </div>

          <div style="padding-top:14px; border-top:0.5px solid var(--separator); display:flex; justify-content:space-between; align-items:center;">
            ${deal.stage !== 'won' ? `
              <button class="btn-apple btn-apple-primary spring-press"
                      onclick="AppleSalesBoard.advanceStage('${deal.id}'); Inspector.close();"
                      style="font-size:13px; padding:8px 16px;">
                Advance to Next Stage
              </button>
            ` : `
              <span class="chip-apple chip-green">Deal Closed & Paid</span>
            `}
            <button class="btn-apple btn-apple-secondary spring-press"
                    onclick="UI.showToast('Generating draft proposal quote...', 'info'); Inspector.close();"
                    style="font-size:13px; padding:8px 14px;">
              Draft Quote
            </button>
          </div>
        </div>
      `;

      window.Inspector.open(deal.title, content);
    }

    openNewDealModal() {
      if (!window.UI || !window.UI.openModal) return;

      window.UI.openModal(
        'Create New Deal Opportunity',
        `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div>
              <label class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px; display:block;">Deal Title</label>
              <input type="text" id="newDealTitle" class="input-apple" placeholder="e.g. Winter Luxury Villa Package" style="width:100%; box-sizing:border-box;">
            </div>

            <div>
              <label class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px; display:block;">Company / Customer Name</label>
              <input type="text" id="newDealCompany" class="input-apple" placeholder="e.g. Geneva Family Office" style="width:100%; box-sizing:border-box;">
            </div>

            <div>
              <label class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px; display:block;">Deal Value (₹)</label>
              <input type="number" id="newDealAmount" class="input-apple" placeholder="500000" style="width:100%; box-sizing:border-box;">
            </div>

            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
              <button class="btn-apple btn-apple-secondary" onclick="UI.closeModal()">Cancel</button>
              <button class="btn-apple btn-apple-primary" onclick="
                const title = document.getElementById('newDealTitle').value;
                const company = document.getElementById('newDealCompany').value;
                const amount = Number(document.getElementById('newDealAmount').value) || 250000;
                if(title && company) {
                  AppleSalesBoard.addDeal({
                    title,
                    company,
                    amount,
                    stage: 'inbound',
                    specialist: 'Inbound Sales Lead Analyst',
                    specialistEntity: 'cmo',
                    probability: 40,
                    nextAction: 'Automated initial intake follow-up',
                    channel: 'Direct Intake Entry',
                    notes: 'Newly created sales opportunity.'
                  });
                  UI.showToast('Deal created successfully.', 'success');
                  UI.closeModal();
                } else {
                  UI.showToast('Please enter title and company.', 'error');
                }
              ">
                Create Deal
              </button>
            </div>
          </div>
        `
      );
    }

    addDeal(deal) {
      deal.id = 'deal_' + Date.now();
      this.deals.unshift(deal);
      this.render();
    }
  }

  window.AppleSalesBoard = new AppleSalesBoardController();
})();
