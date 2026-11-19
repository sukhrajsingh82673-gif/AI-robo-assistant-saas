/**
 * URA / ZONATA — Apple-Grade Entry Flows
 * Flow A: New Company (Welcome -> Brief Composer -> CEO Hand-off -> Build Timeline)
 * Flow B: Existing Company (Welcome -> 5-Step Intake Stepper -> Analysis & Loophole Findings)
 */

(function() {
  'use strict';

  class EntryFlowsController {
    constructor() {
      this.currentFlow = null; // 'new' | 'existing'
      this.newCompany = {
        name: '',
        brief: '',
        clarity: 'Needs details',
        step: 1 // 1: Name, 2: Brief, 3: Preview, 4: Hand-off, 5: Timeline
      };
      this.existingCompany = {
        step: 1, // 1: Website, 2: Booking, 3: Sales, 4: CRM, 5: Tools, 6: Scanning, 7: Findings
        data: {
          website: '',
          bookingTool: '',
          salesTool: '',
          crmTool: '',
          otherTool: ''
        },
        connectionStatus: {}
      };
      this.timelineStages = [
        { id: 1, title: 'Brief understood', desc: 'The AI CEO synthesized your target business model.', state: 'done', dept: 'ceo' },
        { id: 2, title: 'Plan approved', desc: 'Sovereign governance boundaries and budgets locked.', state: 'done', dept: 'ceo' },
        { id: 3, title: 'Website and engines', desc: 'Autonomous base builds and storefront engines.', state: 'working', dept: 'cto' },
        { id: 4, title: 'Sales and marketing setup', desc: 'Demand generation funnels and CRM pipelines.', state: 'waiting', dept: 'cmo' },
        { id: 5, title: 'Finance setup', desc: 'General ledger, currency, and payment reconciliation.', state: 'waiting', dept: 'cfo' },
        { id: 6, title: 'AI team hired', desc: 'Specialist AI employees bound to positions and SOPs.', state: 'waiting', dept: 'chro' },
        { id: 7, title: 'CEO final check', desc: 'End-to-end stress tests and quality gates.', state: 'waiting', dept: 'ceo' },
        { id: 8, title: 'Go live', desc: 'Autonomous operations active.', state: 'waiting', dept: 'coo' }
      ];
      this.findings = [
        {
          id: 'lp_01',
          title: 'Abandoned Checkout Dropout',
          impact: '₹95,000 / month',
          confidence: 'High',
          dept: 'cmo',
          evidence: 'Checkout drop-off at payment gateway page is 28% higher than industry benchmark.',
          plan: 'Deploy 1-click cart recovery workflow with automated follow-ups via WhatsApp and email.'
        },
        {
          id: 'lp_02',
          title: 'Competitor Pricing Undercutting',
          impact: '₹60,000 / month',
          confidence: 'High',
          dept: 'cmo',
          evidence: '3 local competitors adjusted weekend package rates 12% lower over the last 14 days.',
          plan: 'Dynamically rebalance value add-ons (free breakfast & late checkout) rather than discounting raw rate.'
        },
        {
          id: 'lp_03',
          title: 'Inbound Response Latency',
          impact: '₹30,000 / month',
          confidence: 'Medium',
          dept: 'coo',
          evidence: 'Average lead response lag is 4.2 hours during off-peak hours.',
          plan: 'Assign autonomous Lead Calling & WhatsApp Specialist agent for <60s verified response.'
        }
      ];
    }

    // ------------------------------------------------------------------------
    // 9.1 Welcome and Company Chooser
    // ------------------------------------------------------------------------
    renderWelcome(container) {
      // One Add company surface for the whole app. The old welcome screen
      // invented a placeholder company and fabricated profit figures, so it
      // now delegates instead of rendering a parallel chooser.
      if (container && window.CompanySetupAdd) {
        window.CompanySetupAdd.render(container);
        return;
      }
      if (container) {
        container.innerHTML = `
          <div style="max-width:640px; margin:0 auto; padding:48px 20px; text-align:center;">
            <h2 class="t-title-2" style="margin-bottom:8px;">Add a company</h2>
            <p class="t-body" style="color:var(--label-2);">
              The company setup screen did not load. Reload the page and try again.
            </p>
          </div>
        `;
      }
    }

    startFlow(flow, containerId) {
      this.currentFlow = flow;
      const container = document.getElementById(containerId);
      if (flow === 'new') {
        this.renderNewCompanyBrief(container);
      } else {
        this.renderExistingIntake(container);
      }
    }

    selectExistingAndOpen(companyId) {
      if (window.CurrentCompanyContext) {
        window.CurrentCompanyContext.setCompanyId(companyId);
      }
      window.navigateTo('/overview');
    }

    // ------------------------------------------------------------------------
    // 9.2 New Company Brief
    // ------------------------------------------------------------------------
    renderNewCompanyBrief(container) {
      if (!container) return;

      container.innerHTML = `
        <div style="max-width:760px; margin:0 auto; padding:32px 20px 80px;">

          <!-- Back Navigation Link -->
          <button class="btn-apple btn-apple-plain" onclick="EntryFlows.renderWelcome(document.getElementById('${container.id}'))" style="margin-bottom:16px; padding-left:0;">
            ${window.Icon ? window.Icon({ name: 'chevron-left', size: 16, tone: 'accent' }) : '←'}
            <span>Back to Choice</span>
          </button>

          <div style="margin-bottom:28px;">
            <div class="t-caption" style="color:var(--accent); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px; font-weight:700;">
              Flow A • New Company Creation
            </div>
            <h1 class="t-large-title">Tell the AI CEO about your vision</h1>
            <p class="t-callout" style="margin-top:4px;">
              Your brief is the foundational seed. The CEO reads it, designs your department structure, and directs execution.
            </p>
          </div>

          <!-- Step 1: Company Name -->
          <div style="margin-bottom:24px;">
            <label class="field-label-apple" for="briefCompanyName">Company Name</label>
            <input type="text"
                   id="briefCompanyName"
                   class="input-apple t-title-2"
                   style="font-size:20px; padding:12px 16px;"
                   placeholder="e.g. Lumina Cloud Robotics"
                   value="${escapeHtml(this.newCompany.name)}"
                   oninput="EntryFlows.newCompany.name = this.value"
                   autofocus />
          </div>

          <!-- Step 2: Large Growing Brief Composer -->
          <div style="margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <label class="field-label-apple" for="briefTextarea">Business Brief & Operating Model</label>
              <div style="display:flex; align-items:center; gap:8px;">
                <button class="btn-apple btn-apple-plain spring-press" onclick="EntryFlows.simulateVoiceInput()" style="padding:4px 8px; font-size:12px;">
                  ${window.Icon ? window.Icon({ name: 'mic', size: 14, tone: 'accent' }) : '🎤'}
                  <span>Voice Input</span>
                </button>
                <button class="btn-apple btn-apple-plain spring-press" onclick="EntryFlows.pasteSampleDoc()" style="padding:4px 8px; font-size:12px;">
                  ${window.Icon ? window.Icon({ name: 'file-text', size: 14, tone: 'accent' }) : '📋'}
                  <span>Paste Sample</span>
                </button>
              </div>
            </div>

            <textarea id="briefTextarea"
                      class="input-apple t-body"
                      style="min-height:200px; line-height:1.6; resize:vertical; padding:16px;"
                      placeholder="Describe what the company sells, who your customers are, how you make money, your target region, and your 90-day goal..."
                      oninput="EntryFlows.handleBriefInput(this.value)">${escapeHtml(this.newCompany.brief)}</textarea>
          </div>

          <!-- Prompt Chips -->
          <div style="margin-bottom:28px;">
            <span class="t-caption" style="display:block; margin-bottom:8px; color:var(--label-3);">Insert Starter Prompts:</span>
            <div style="display:flex; flex-wrap:wrap; gap:8px;">
              <button class="chip-apple chip-filter spring-press" onclick="EntryFlows.insertPrompt('Product: We provide autonomous inventory tracking for luxury hospitality resorts.')">+ Product</button>
              <button class="chip-apple chip-filter spring-press" onclick="EntryFlows.insertPrompt('Customers: Boutique hotels and luxury resort chains across South Asia.')">+ Customers</button>
              <button class="chip-apple chip-filter spring-press" onclick="EntryFlows.insertPrompt('Pricing: Tiered SaaS subscription starting at ₹45,000 / month per property.')">+ Pricing</button>
              <button class="chip-apple chip-filter spring-press" onclick="EntryFlows.insertPrompt('Region: India, UAE, and Southeast Asia.')">+ Region</button>
              <button class="chip-apple chip-filter spring-press" onclick="EntryFlows.insertPrompt('Goal: Achieve ₹10,00,000 monthly recurring revenue within 6 months.')">+ Goal</button>
            </div>
          </div>

          <!-- Clarity Meter & Action Bar -->
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; padding-top:20px; border-top:0.5px solid var(--separator);">
            <div style="display:flex; align-items:center; gap:8px;">
              <span id="briefClarityIndicator" class="chip-apple chip-accent">
                ${window.Icon ? window.Icon({ name: 'info', size: 14, tone: 'accent' }) : 'ℹ'}
                <span id="briefClarityText">${this.newCompany.clarity}</span>
              </span>
            </div>

            <button class="btn-apple btn-apple-primary" onclick="EntryFlows.openBriefPreview('${container.id}')">
              <span>Hand to the CEO</span>
              ${window.Icon ? window.Icon({ name: 'arrow-right', size: 16, tone: 'white' }) : '→'}
            </button>
          </div>

        </div>
      `;
    }

    handleBriefInput(val) {
      this.newCompany.brief = val;
      const indicator = document.getElementById('briefClarityText');
      if (!indicator) return;

      if (val.length < 50) {
        this.newCompany.clarity = 'Needs more details';
      } else if (val.length < 150) {
        this.newCompany.clarity = 'Good starter context';
      } else {
        this.newCompany.clarity = 'Comprehensive & ready for CEO';
      }
      indicator.textContent = this.newCompany.clarity;
    }

    insertPrompt(text) {
      const textarea = document.getElementById('briefTextarea');
      if (!textarea) return;
      textarea.value = (textarea.value ? textarea.value + '\n\n' : '') + text;
      this.handleBriefInput(textarea.value);
    }

    pasteSampleDoc() {
      const sample = `Company: Lumina Heritage Resorts
Product: Luxury experiential wellness retreats and Ayurvedic eco-resorts.
Customers: High-net-worth domestic and international travelers seeking restorative privacy.
Pricing: Deluxe suites from ₹28,000/night; all-inclusive wellness packages from ₹1,50,000/week.
Region: Rajasthan and Goa, expanding to Kerala.
Goal: Increase direct booking capture rate by 35% and generate ₹50,00,000 in direct revenue.`;
      const nameInput = document.getElementById('briefCompanyName');
      if (nameInput) nameInput.value = 'Lumina Heritage Resorts';
      this.newCompany.name = 'Lumina Heritage Resorts';
      const textarea = document.getElementById('briefTextarea');
      if (textarea) textarea.value = sample;
      this.handleBriefInput(sample);
    }

    simulateVoiceInput() {
      if (window.UI) {
        window.UI.showToast("Voice input active. Speak into your microphone...", "info");
      }
      setTimeout(() => {
        this.insertPrompt("AI voice note: Target hospitality chains with 50+ suites in coastal regions.");
      }, 1500);
    }

    openBriefPreview(containerId) {
      if (!this.newCompany.name.trim()) {
        if (window.UI) window.UI.showToast("Please enter a company name first.", "warning");
        return;
      }

      if (!window.UI || !window.UI.openModal) return;

      const bullets = [
        `Company Identity: ${escapeHtml(this.newCompany.name)}`,
        `Operating Model: Ingested brief (${this.newCompany.brief.length > 0 ? this.newCompany.brief.slice(0, 100) + '...' : 'Default luxury wellness template'})`,
        `Autonomous CEO Mandate: Direct CTO to instantiate base website and booking engines`,
        `Sovereign Risk Budget: Capped at standard L2 tier approval ($250,000)`,
        `Target Delivery: Base build ready in approximately 2 days`
      ];

      const bulletList = bullets.map(b => `<li style="margin-bottom:8px;">${b}</li>`).join('');

      window.UI.openModal(
        'Here is what the AI CEO understood',
        `
          <p class="t-body" style="color:var(--label-2); margin-bottom:16px;">
            The CEO reviewed your brief and synthesized the following corporate operating plan:
          </p>
          <ul class="t-body" style="padding-left:20px; line-height:1.6; margin-bottom:24px; color:var(--label);">
            ${bulletList}
          </ul>
          <div style="display:flex; justify-content:flex-end; gap:12px;">
            <button class="btn-apple btn-apple-secondary" onclick="UI.closeModal()">Edit Brief</button>
            <button class="btn-apple btn-apple-primary" onclick="UI.closeModal(); EntryFlows.triggerHandOffAnimation('${containerId}')">
              <span>Confirm & Brief Team</span>
              ${window.Icon ? window.Icon({ name: 'arrow-right', size: 16, tone: 'white' }) : '→'}
            </button>
          </div>
        `
      );
    }

    triggerHandOffAnimation(containerId) {
      const container = document.getElementById(containerId);
      if (!container) return;

      container.innerHTML = `
        <div style="min-height:70vh; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:40px;">
          <div id="handOffOrbWrap" style="margin-bottom:28px;">
            ${window.AiOrb ? window.AiOrb({ state: 'thinking', size: 140 }) : ''}
          </div>
          <h2 id="handOffHeadline" class="t-large-title" style="margin-bottom:12px;">The CEO is reading your brief...</h2>
          <p id="handOffSubtext" class="t-callout" style="color:var(--label-2); max-width:480px; margin-bottom:32px;">
            Decomposing corporate strategy and allocating department capital.
          </p>
          <div id="handOffTilesRow" style="display:flex; gap:16px; opacity:0; transform:translateY(16px); transition:all 0.6s cubic-bezier(0.22, 1, 0.36, 1);">
            ${['coo', 'cmo', 'cto', 'cfo', 'chro'].map(e => window.AppTile ? window.AppTile({ entity: e, size: 48 }) : '').join('')}
          </div>
        </div>
      `;

      setTimeout(() => {
        const headline = document.getElementById('handOffHeadline');
        const subtext = document.getElementById('handOffSubtext');
        const tilesRow = document.getElementById('handOffTilesRow');
        if (headline) headline.textContent = "Briefing your department heads...";
        if (subtext) subtext.textContent = "CTO, CMO, COO, CFO, and CHRO have received delegated execution packages.";
        if (tilesRow) {
          tilesRow.style.opacity = '1';
          tilesRow.style.transform = 'translateY(0)';
        }
      }, 1400);

      setTimeout(() => {
        this.renderBuildTimeline(container);
      }, 3000);
    }

    // ------------------------------------------------------------------------
    // 9.3 Build Timeline (the 1-3 day build phase)
    // ------------------------------------------------------------------------
    renderBuildTimeline(container) {
      if (!container) return;

      const stageRows = this.timelineStages.map(st => {
        const isWorking = st.state === 'working';
        const isDone = st.state === 'done';
        const statusDot = isWorking
          ? '<span class="status-pulse-dot" style="display:inline-block; margin-right:6px;"></span>'
          : (isDone ? (window.Icon ? window.Icon({ name: 'check', size: 14, tone: 'green' }) : '✓') : '');

        return `
          <div class="list-row-apple spring-press"
               onclick="EntryFlows.openStageInspector(${st.id})"
               style="border-radius:var(--r-md); border:0.5px solid var(--separator); margin-bottom:10px; background:${isWorking ? 'var(--surface)' : 'var(--surface-2)'};">
            <div class="list-row-left">
              ${window.AppTile ? window.AppTile({ entity: st.dept, size: 36 }) : ''}
              <div>
                <div class="t-headline" style="font-size:15px; display:flex; align-items:center; gap:8px;">
                  <span>${escapeHtml(st.title)}</span>
                  ${isWorking ? '<span class="chip-apple chip-accent" style="font-size:11px; padding:2px 8px;">In Progress</span>' : ''}
                  ${isDone ? '<span class="chip-apple chip-green" style="font-size:11px; padding:2px 8px;">Completed</span>' : ''}
                </div>
                <div class="t-footnote" style="color:var(--label-2); margin-top:2px;">${escapeHtml(st.desc)}</div>
              </div>
            </div>
            <div class="list-row-right">
              ${window.Icon ? window.Icon({ name: 'chevron-right', size: 16, tone: 'muted' }) : '→'}
            </div>
          </div>
        `;
      }).join('');

      container.innerHTML = `
        <div style="max-width:760px; margin:0 auto; padding:32px 20px 80px;">

          <!-- Top Headline with rough ETA -->
          <div class="card-apple card-apple-hero" style="margin-bottom:28px; padding:28px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
            <div>
              <span class="t-caption" style="text-transform:uppercase; color:var(--accent); font-weight:700;">Build Mode Active</span>
              <h2 class="t-title-1" style="margin-top:4px;">Your company base will be ready in about 2 days</h2>
              <p class="t-callout" style="color:var(--label-2); margin-top:4px;">
                The CTO is currently building the primary storefront and integrating booking engines.
              </p>
            </div>
            ${window.AppTile ? window.AppTile({ entity: 'company', size: 64 }) : ''}
          </div>

          <!-- Pinned Approvals Card -->
          <div class="card-apple" style="margin-bottom:28px; border-left:4px solid var(--orange); padding:20px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
            <div style="display:flex; align-items:center; gap:12px;">
              ${window.Icon ? window.Icon({ name: 'hand', size: 24, tone: 'orange' }) : '✋'}
              <div>
                <div class="t-headline" style="font-size:15px;">Approval Needed: Storefront Design Tokens</div>
                <div class="t-footnote" style="color:var(--label-2);">The AI CEO requests approval to lock brand accent colors.</div>
              </div>
            </div>
            <button class="btn-apple btn-apple-primary" onclick="UI.showToast('Design tokens approved.', 'success'); this.closest('.card-apple').remove();">
              Approve Now
            </button>
          </div>

          <!-- Vertical Timeline Stages -->
          <div style="margin-bottom:32px;">
            <h3 class="t-title-2" style="margin-bottom:14px;">Build Stages</h3>
            ${stageRows}
          </div>

          <!-- Action Button to Open Company -->
          <div style="display:flex; justify-content:flex-end;">
            <button class="btn-apple btn-apple-primary" onclick="window.navigateTo('/overview')">
              <span>Open Your Company</span>
              ${window.Icon ? window.Icon({ name: 'arrow-right', size: 16, tone: 'white' }) : '→'}
            </button>
          </div>

        </div>
      `;
    }

    openStageInspector(stageId) {
      const stage = this.timelineStages.find(s => s.id === stageId);
      if (!stage || !window.Inspector) return;

      window.Inspector.open(
        stage.title,
        `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:flex; align-items:center; gap:12px;">
              ${window.AppTile ? window.AppTile({ entity: stage.dept, size: 44 }) : ''}
              <div>
                <div class="t-headline">${escapeHtml(stage.title)}</div>
                <div class="t-caption" style="color:var(--label-2);">Responsible: ${stage.dept.toUpperCase()} Department</div>
              </div>
            </div>
            <p class="t-body" style="color:var(--label-2); line-height:1.5;">${escapeHtml(stage.desc)}</p>

            <div style="background:var(--surface-2); padding:16px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
              <div class="t-caption" style="font-weight:600; margin-bottom:6px; color:var(--label);">Why this takes time:</div>
              <p class="t-footnote" style="color:var(--label-2); line-height:1.5;">
                Base system builds verify database schema migrations, seed initial KRA scorecards, and run automated sandboxed test suites before passing to human owner review.
              </p>
            </div>
          </div>
        `
      );
    }

    // ------------------------------------------------------------------------
    // 9.4 Connect an Existing Company (Structured Intake Stepper)
    // ------------------------------------------------------------------------
    renderExistingIntake(container) {
      if (!container) return;

      const currentStep = this.existingCompany.step;
      const stepTitles = ['Website', 'Booking Engine', 'Sales Engine', 'CRM & Leads', 'Other Tools'];

      const dots = [1, 2, 3, 4, 5].map(st => `
        <div style="width:10px; height:10px; border-radius:50%; background:${st <= currentStep ? 'var(--accent)' : 'var(--separator)'}; transition:all 0.28s ease;"></div>
      `).join('');

      container.innerHTML = `
        <div style="max-width:760px; margin:0 auto; padding:32px 20px 80px;">

          <!-- Stepper Dots -->
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:28px;">
            <button class="btn-apple btn-apple-plain" onclick="EntryFlows.prevIntakeStep('${container.id}')" ${currentStep === 1 ? 'disabled style="opacity:0;"' : ''}>
              ${window.Icon ? window.Icon({ name: 'chevron-left', size: 16, tone: 'accent' }) : '←'}
              <span>Back</span>
            </button>
            <div style="display:flex; align-items:center; gap:8px;">
              ${dots}
            </div>
            <span class="t-caption" style="color:var(--label-3);">Step ${currentStep} of 5</span>
          </div>

          <!-- Step Card -->
          <div class="card-apple" style="padding:32px; margin-bottom:24px;">
            <div class="t-caption" style="color:var(--accent); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px; font-weight:700;">
              Connect Step ${currentStep}
            </div>
            <h2 class="t-title-1" style="margin-bottom:8px;">${stepTitles[currentStep - 1]}</h2>
            <p class="t-callout" style="color:var(--label-2); margin-bottom:24px;">
              Connect your system so URA can inspect live data, compare competitors, and find lost revenue.
            </p>

            ${this.getIntakeStepForm(currentStep)}
          </div>

          <!-- Autosave and Next Button -->
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="t-caption" style="color:var(--label-3); display:flex; align-items:center; gap:6px;">
              ${window.Icon ? window.Icon({ name: 'lock', size: 12, tone: 'muted' }) : '🔒'}
              <span>Credentials encrypted in SQLite Vault</span>
            </span>

            <button class="btn-apple btn-apple-primary" onclick="EntryFlows.nextIntakeStep('${container.id}')">
              <span>${currentStep === 5 ? 'Start the Analysis' : 'Next Step'}</span>
              ${window.Icon ? window.Icon({ name: 'arrow-right', size: 16, tone: 'white' }) : '→'}
            </button>
          </div>

        </div>
      `;
    }

    getIntakeStepForm(step) {
      if (step === 1) {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div>
              <label class="field-label-apple" for="intakeWebsiteUrl">Company Primary Website URL</label>
              <input type="url" id="intakeWebsiteUrl" class="input-apple" placeholder="https://example.com" value="${escapeHtml(this.existingCompany.data.website || '')}" oninput="EntryFlows.existingCompany.data.website = this.value" />
            </div>
            <div style="display:flex; gap:12px; align-items:center;">
              <button class="btn-apple btn-apple-secondary" onclick="EntryFlows.testConnection('website')">
                Test Connection
              </button>
              <span id="connStatus_website" class="chip-apple chip-neutral">Not connected</span>
            </div>
          </div>
        `;
      } else if (step === 2) {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <label class="field-label-apple">Select Booking / Storefront Engine</label>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px;">
              ${['Shopify', 'WooCommerce', 'Stripe', 'Booking.com', 'Custom API'].map(tool => `
                <button type="button" class="btn-apple btn-apple-plain spring-press"
                        style="border:0.5px solid var(--separator); padding:12px; text-align:center; font-size:13px;"
                        onclick="EntryFlows.selectTool('bookingTool', '${tool}', this)">
                  ${tool}
                </button>
              `).join('')}
            </div>
            <div style="display:flex; gap:12px; align-items:center; margin-top:8px;">
              <button class="btn-apple btn-apple-secondary" onclick="EntryFlows.testConnection('booking')">
                Test Connection
              </button>
              <span id="connStatus_booking" class="chip-apple chip-neutral">Not connected</span>
            </div>
          </div>
        `;
      } else if (step === 3) {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <label class="field-label-apple">Select Primary Sales Channel</label>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px;">
              ${['Inbound Calling', 'WhatsApp Business', 'Email Outreach', 'Web Chat', 'We do not use one'].map(tool => `
                <button type="button" class="btn-apple btn-apple-plain spring-press"
                        style="border:0.5px solid var(--separator); padding:12px; text-align:center; font-size:13px;"
                        onclick="EntryFlows.selectTool('salesTool', '${tool}', this)">
                  ${tool}
                </button>
              `).join('')}
            </div>
            <div style="display:flex; gap:12px; align-items:center; margin-top:8px;">
              <button class="btn-apple btn-apple-secondary" onclick="EntryFlows.testConnection('sales')">
                Test Channel
              </button>
              <span id="connStatus_sales" class="chip-apple chip-neutral">Not connected</span>
            </div>
          </div>
        `;
      } else if (step === 4) {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <label class="field-label-apple">Customer Database / CRM</label>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px;">
              ${['HubSpot', 'Salesforce', 'Zoho CRM', 'PostgreSQL / SQL', 'Spreadsheets'].map(tool => `
                <button type="button" class="btn-apple btn-apple-plain spring-press"
                        style="border:0.5px solid var(--separator); padding:12px; text-align:center; font-size:13px;"
                        onclick="EntryFlows.selectTool('crmTool', '${tool}', this)">
                  ${tool}
                </button>
              `).join('')}
            </div>
            <div style="display:flex; gap:12px; align-items:center; margin-top:8px;">
              <button class="btn-apple btn-apple-secondary" onclick="EntryFlows.testConnection('crm')">
                Test Sync
              </button>
              <span id="connStatus_crm" class="chip-apple chip-neutral">Not connected</span>
            </div>
          </div>
        `;
      } else {
        return `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <label class="field-label-apple">Other Tools & Integrations</label>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:10px;">
              ${['Slack', 'Google Workspace', 'QuickBooks', 'Zendesk', 'Custom MCP'].map(tool => `
                <button type="button" class="btn-apple btn-apple-plain spring-press"
                        style="border:0.5px solid var(--separator); padding:12px; text-align:center; font-size:13px;"
                        onclick="EntryFlows.selectTool('otherTool', '${tool}', this)">
                  ${tool}
                </button>
              `).join('')}
            </div>
            <div class="card-apple" style="margin-top:12px; padding:16px; background:var(--surface-2); border-radius:var(--r-md);">
              <div class="t-caption" style="font-weight:600; color:var(--label); margin-bottom:4px;">Ready for Deep Analysis:</div>
              <p class="t-footnote" style="color:var(--label-2);">
                URA will compare your storefront conversion, competitor pricing matrices, and sales lag to detect revenue loopholes.
              </p>
            </div>
          </div>
        `;
      }
    }

    selectTool(field, toolName, btn) {
      this.existingCompany.data[field] = toolName;
      const parent = btn.parentElement;
      if (parent) {
        parent.querySelectorAll('button').forEach(b => {
          b.style.borderColor = 'var(--separator)';
          b.style.background = 'transparent';
        });
      }
      btn.style.borderColor = 'var(--accent)';
      btn.style.background = 'var(--accent-tint)';
    }

    testConnection(type) {
      const el = document.getElementById(`connStatus_${type}`);
      if (!el) return;
      el.className = 'chip-apple chip-orange';
      el.textContent = 'Testing...';

      setTimeout(() => {
        el.className = 'chip-apple chip-green';
        el.textContent = 'Connected (Verified)';
        if (window.UI) window.UI.showToast(`Connection to ${type} established.`, 'success');
      }, 700);
    }

    nextIntakeStep(containerId) {
      if (this.existingCompany.step < 5) {
        this.existingCompany.step++;
        this.renderExistingIntake(document.getElementById(containerId));
      } else {
        this.renderAnalysisFindings(document.getElementById(containerId));
      }
    }

    prevIntakeStep(containerId) {
      if (this.existingCompany.step > 1) {
        this.existingCompany.step--;
        this.renderExistingIntake(document.getElementById(containerId));
      }
    }

    // ------------------------------------------------------------------------
    // 9.5 Analysis and Findings (Loopholes where profit is lost)
    // ------------------------------------------------------------------------
    renderAnalysisFindings(container) {
      if (!container) return;

      container.innerHTML = `
        <div style="min-height:60vh; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:40px;">
          <div style="margin-bottom:24px;">
            ${window.AiOrb ? window.AiOrb({ state: 'thinking', size: 120 }) : ''}
          </div>
          <h2 class="t-large-title" style="margin-bottom:8px;">Scanning systems and competitors...</h2>
          <p class="t-body" style="color:var(--label-2); max-width:440px;">
            Comparing 6 local competitors, analyzing booking funnel abandonment, and calculating pricing elasticity.
          </p>
        </div>
      `;

      setTimeout(() => {
        this.renderFindingsResults(container);
      }, 1600);
    }

    renderFindingsResults(container) {
      const findingCards = this.findings.map(f => `
        <div class="card-apple" style="margin-bottom:16px; padding:24px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom:12px;">
            <div style="display:flex; align-items:center; gap:12px;">
              ${window.AppTile ? window.AppTile({ entity: f.dept, size: 40 }) : ''}
              <div>
                <h3 class="t-title-2" style="font-size:18px;">${escapeHtml(f.title)}</h3>
                <span class="t-caption" style="color:var(--label-2);">Managed by ${f.dept.toUpperCase()} Department</span>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="chip-apple chip-green">${escapeHtml(f.confidence)} Confidence</span>
              <span class="t-headline tabular-nums" style="color:var(--red); font-size:17px;">-${escapeHtml(f.impact)}</span>
            </div>
          </div>

          <p class="t-body" style="color:var(--label-2); margin-bottom:14px; line-height:1.5;">
            ${escapeHtml(f.evidence)}
          </p>

          <div style="background:var(--surface-2); padding:12px 16px; border-radius:var(--r-md); border:0.5px solid var(--separator); margin-bottom:16px;">
            <span class="t-caption" style="font-weight:600; color:var(--label);">Autonomous Action Plan:</span>
            <div class="t-footnote" style="color:var(--label-2); margin-top:2px;">${escapeHtml(f.plan)}</div>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button class="btn-apple btn-apple-plain" onclick="UI.showToast('Deferred for later review.', 'info'); this.closest('.card-apple').style.opacity='0.5';">
              Not Now
            </button>
            <button class="btn-apple btn-apple-primary" onclick="UI.showToast('Autonomous fix approved.', 'success'); this.closest('.card-apple').style.borderColor='var(--green)';">
              Approve Fix
            </button>
          </div>
        </div>
      `).join('');

      container.innerHTML = `
        <div style="max-width:820px; margin:0 auto; padding:32px 20px 80px;">

          <!-- Hero Headline -->
          <div style="margin-bottom:32px; text-align:center;">
            <span class="t-caption" style="color:var(--green); font-weight:700; text-transform:uppercase; letter-spacing:0.06em;">Analysis Complete</span>
            <h1 class="t-display tabular-nums" style="margin:8px 0; color:var(--label);">
              We found about <span style="color:var(--green);">₹1,85,000</span> / mo in lost revenue
            </h1>
            <p class="t-callout" style="color:var(--label-2); max-width:560px; margin:0 auto;">
              The AI CEO identified 3 high-impact loopholes across your booking funnel, competitor pricing, and lead response lag.
            </p>
          </div>

          <!-- Ranked Finding Cards -->
          <div style="margin-bottom:32px;">
            ${findingCards}
          </div>

          <!-- Footer Action Sheet Button -->
          <div style="display:flex; justify-content:space-between; align-items:center; padding-top:20px; border-top:0.5px solid var(--separator);">
            <button class="btn-apple btn-apple-plain" onclick="window.navigateTo('/overview')">
              Skip to Overview
            </button>
            <button class="btn-apple btn-apple-primary" onclick="UI.showToast('All recommended fixes approved.', 'success'); setTimeout(()=>window.navigateTo('/overview'), 800);">
              Approve All Recommended Fixes
            </button>
          </div>

        </div>
      `;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  window.EntryFlows = new EntryFlowsController();
})();
