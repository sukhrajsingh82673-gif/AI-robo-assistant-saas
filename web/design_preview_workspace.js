/**
 * URA / ZONATA — Design System Preview & Interactive Test Surface (/design)
 * Complete design token verification, typography scale, motion testbed, and component catalog.
 */

(function() {
  'use strict';

  class DesignPreviewWorkspaceManager {
    constructor() {
      this.activeTheme = document.documentElement.getAttribute('data-theme') || 'light';
      this.orbState = 'idle';
      this.orbSize = 96;
      this.testNumber = 428500;
      this.segmentedActive = 'overview';
      this.toggleState = true;
    }

    render(containerId = 'view-design') {
      const container = document.getElementById(containerId);
      if (!container) return;

      const UI = window.UI || {};

      container.innerHTML = `
        <div style="max-width:1120px; margin:0 auto; padding:32px 24px 80px; display:flex; flex-direction:column; gap:40px;">

          <!-- Header & Live Theme Switcher -->
          <header style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:20px; padding-bottom:24px; border-bottom:0.5px solid var(--separator);">
            <div>
              <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:8px;">
                <span class="t-caption" style="text-transform:uppercase; letter-spacing:0.06em; color:var(--accent); font-weight:700;">Design Foundations & Primitives</span>
                <span style="font-size:12px; color:var(--label-3);">•</span>
                <span class="t-caption" style="color:var(--label-3);">Phase 2 Verification</span>
              </div>
              <h1 class="t-large-title">Apple-Grade Component Library</h1>
              <p class="t-callout" style="max-width:640px; margin-top:6px;">
                Calm, accessible, token-driven component primitives built with spring physics and progressive disclosure.
              </p>
            </div>

            <!-- Theme Toggle Button Group -->
            <div style="display:inline-flex; background:var(--surface-2); padding:3px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
              <button id="themeBtnLight" class="spring-press" style="padding:6px 14px; border-radius:var(--r-sm); border:none; background:${this.activeTheme === 'light' ? 'var(--surface)' : 'transparent'}; color:var(--label); font-weight:${this.activeTheme === 'light' ? '600' : '400'}; font-size:13px; box-shadow:${this.activeTheme === 'light' ? 'var(--shadow-1)' : 'none'}; cursor:pointer;" onclick="DesignPreviewWorkspace.setTheme('light')">
                Light
              </button>
              <button id="themeBtnDark" class="spring-press" style="padding:6px 14px; border-radius:var(--r-sm); border:none; background:${this.activeTheme === 'dark' ? 'var(--surface)' : 'transparent'}; color:var(--label); font-weight:${this.activeTheme === 'dark' ? '600' : '400'}; font-size:13px; box-shadow:${this.activeTheme === 'dark' ? 'var(--shadow-1)' : 'none'}; cursor:pointer;" onclick="DesignPreviewWorkspace.setTheme('dark')">
                Dark
              </button>
            </div>
          </header>

          <!-- 1. Interactive Buttons Showcase -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">1. Buttons & Interactive States</h2>
              <p class="t-footnote" style="margin-top:2px;">One primary action per screen. Instant 80ms press scale (0.97) and visible focus rings.</p>
            </div>

            <div style="display:flex; flex-wrap:wrap; gap:16px; align-items:center;">
              ${UI.Button ? UI.Button({ label: 'Primary Action', variant: 'primary', icon: 'sparkles' }) : ''}
              ${UI.Button ? UI.Button({ label: 'Secondary Action', variant: 'secondary' }) : ''}
              ${UI.Button ? UI.Button({ label: 'Plain Text', variant: 'plain' }) : ''}
              ${UI.Button ? UI.Button({ label: 'Destructive', variant: 'destructive', icon: 'trash' }) : ''}
              ${UI.Button ? UI.Button({ variant: 'icon', icon: 'settings', ariaLabel: 'Settings' }) : ''}
              ${UI.Button ? UI.Button({ label: 'Loading State', variant: 'primary', loading: true }) : ''}
              ${UI.Button ? UI.Button({ label: 'Disabled State', variant: 'secondary', disabled: true }) : ''}
            </div>
          </section>

          <!-- 2. Text Fields & Inputs -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">2. Text Fields & Search Inputs</h2>
              <p class="t-footnote" style="margin-top:2px;">Rounded inputs with accent focus rings, leading icons, error states, and helper messages.</p>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:20px;">
              ${UI.Input ? UI.Input({ label: 'Company Name', placeholder: 'e.g. Acme Corporation', value: 'ZONATA Technologies' }) : ''}
              ${UI.Input ? UI.Input({ label: 'Search Registry', placeholder: 'Search records, agents, files...', icon: 'search' }) : ''}
              ${UI.Input ? UI.Input({ label: 'With Helper Text', placeholder: 'Enter API Key', helperText: 'Stored encrypted in SQLite vault.' }) : ''}
              ${UI.Input ? UI.Input({ label: 'Error State', placeholder: 'Work Email', value: 'invalid-email', errorMessage: 'Please enter a valid business email address.' }) : ''}
            </div>
          </section>

          <!-- 3. Status Chips & Badges -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">3. Status Chips & Filters</h2>
              <p class="t-footnote" style="margin-top:2px;">Semantic 12% tint fills paired with full-strength text and icons.</p>
            </div>

            <div style="display:flex; flex-wrap:wrap; gap:12px; align-items:center;">
              ${UI.Chip ? UI.Chip({ label: 'Healthy / Done', tone: 'green', icon: 'check-circle' }) : ''}
              ${UI.Chip ? UI.Chip({ label: 'Needs You', tone: 'orange', icon: 'hand' }) : ''}
              ${UI.Chip ? UI.Chip({ label: 'Needs Attention', tone: 'red', icon: 'alert-triangle' }) : ''}
              ${UI.Chip ? UI.Chip({ label: 'Working Now', tone: 'accent', icon: 'zap' }) : ''}
              ${UI.Chip ? UI.Chip({ label: 'AI Strategy', tone: 'purple', icon: 'compass' }) : ''}
              ${UI.Chip ? UI.Chip({ label: 'Finance GL', tone: 'teal', icon: 'coins' }) : ''}
              ${UI.Chip ? UI.Chip({ label: 'Removable Filter', tone: 'neutral', removable: true }) : ''}
            </div>
          </section>

          <!-- 4. iOS-Style Toggles & Segmented Controls -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">4. Controls & Navigation Primitives</h2>
              <p class="t-footnote" style="margin-top:2px;">Segmented control with sliding pill selection and iOS-style toggle switches.</p>
            </div>

            <div style="display:flex; flex-direction:column; gap:24px;">
              <div>
                <span class="t-caption" style="display:block; margin-bottom:8px;">Segmented Control:</span>
                ${UI.SegmentedControl ? UI.SegmentedControl({
                  items: [
                    { id: 'overview', label: 'Executive Overview' },
                    { id: 'departments', label: 'Departments' },
                    { id: 'workforce', label: 'Workforce Roster' },
                    { id: 'reports', label: 'Financial Reports' }
                  ],
                  activeId: this.segmentedActive,
                  onChange: 'DesignPreviewWorkspace.handleSegmentChange'
                }) : ''}
              </div>

              <div>
                <span class="t-caption" style="display:block; margin-bottom:8px;">Toggle Switch:</span>
                ${UI.Toggle ? UI.Toggle({ id: 'demoToggle', label: 'Autonomous AI CEO Auto-Execution', checked: true }) : ''}
              </div>
            </div>
          </section>

          <!-- 5. Grouped List Rows -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">5. Grouped List Rows</h2>
              <p class="t-footnote" style="margin-top:2px;">Clean Apple Settings-style list rows with AppTiles, titles, trailing metrics, and chevrons.</p>
            </div>

            <div class="grouped-list-apple">
              ${UI.ListRow ? UI.ListRow({ title: 'AI CEO Strategy Engine', subtitle: 'Quarterly OKRs & corporate governance', tileEntity: 'ceo', trailingValue: 'Active' }) : ''}
              ${UI.ListRow ? UI.ListRow({ title: 'Technology & Cloud Systems', subtitle: 'Base website builds and integrations', tileEntity: 'cto', trailingValue: '99.98% SLA' }) : ''}
              ${UI.ListRow ? UI.ListRow({ title: 'Financial Command Center', subtitle: 'Audited balance sheet and general ledger', tileEntity: 'cfo', trailingValue: '₹4.28L Profit' }) : ''}
            </div>
          </section>

          <!-- 6. Shimmering Loading Skeletons -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">6. Shimmering Skeletons & Progress</h2>
              <p class="t-footnote" style="margin-top:2px;">1.6s smooth shimmers matching content shapes; progress bars with smooth spring easing.</p>
            </div>

            <div style="display:flex; flex-direction:column; gap:20px;">
              <div style="display:flex; align-items:center; gap:16px;">
                ${UI.Skeleton ? UI.Skeleton({ type: 'avatar', width: '48px', height: '48px' }) : ''}
                <div style="flex:1; display:flex; flex-direction:column; gap:8px;">
                  ${UI.Skeleton ? UI.Skeleton({ type: 'text', width: '60%', height: '16px' }) : ''}
                  ${UI.Skeleton ? UI.Skeleton({ type: 'text', width: '40%', height: '12px' }) : ''}
                </div>
              </div>

              <div>
                <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                  <span class="t-caption">Company Build Progress</span>
                  <span class="t-caption tabular-nums">78%</span>
                </div>
                ${UI.ProgressBar ? UI.ProgressBar({ progress: 78 }) : ''}
              </div>
            </div>
          </section>

          <!-- 7. Interactive Modals & Toasts -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">7. Modals, Sheets & Toast Alerts</h2>
              <p class="t-footnote" style="margin-top:2px;">Trigger accessible dialogs with blurred backdrops and floating toast notifications.</p>
            </div>

            <div style="display:flex; flex-wrap:wrap; gap:12px;">
              ${UI.Button ? UI.Button({ label: 'Open Modal Dialog', variant: 'primary', onClick: 'DesignPreviewWorkspace.openDemoModal()' }) : ''}
              ${UI.Button ? UI.Button({ label: 'Show Success Toast', variant: 'secondary', onClick: 'UI.showToast("Report compiled and emailed successfully.", "success")' }) : ''}
              ${UI.Button ? UI.Button({ label: 'Show Warning Toast', variant: 'secondary', onClick: 'UI.showToast("Unusual spike in customer acquisition cost detected.", "warning")' }) : ''}
              ${UI.Button ? UI.Button({ label: 'Show Error Toast', variant: 'secondary', onClick: 'UI.showToast("Unable to reach external payment provider gateway.", "error")' }) : ''}
            </div>
          </section>

          <!-- 8. Empty State View -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">8. Calm Empty State</h2>
              <p class="t-footnote" style="margin-top:2px;">Clear, friendly empty state with 32px icon, one sentence, and one verb action button.</p>
            </div>

            <div style="background:var(--bg); border-radius:var(--r-lg); border:0.5px solid var(--separator);">
              ${UI.EmptyState ? UI.EmptyState({
                icon: 'briefcase',
                title: 'No Active Missions Yet',
                description: 'Your AI CEO will launch strategic company missions once your business brief is confirmed.',
                actionButton: UI.Button ? UI.Button({ label: 'Launch First Mission', variant: 'primary', icon: 'plus' }) : ''
              }) : ''}
            </div>
          </section>

          <!-- 9. Signature AI Presence (<AiOrb />) -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:24px;">
              <div>
                <h2 class="t-title-2">9. Signature AI Presence</h2>
                <p class="t-footnote" style="margin-top:2px;">Physical states: Breathing idle, rotating thinking, pulsing speech, warming needs-you.</p>
              </div>

              <!-- State Buttons -->
              <div style="display:inline-flex; gap:8px; flex-wrap:wrap;">
                ${['idle', 'thinking', 'speaking', 'needs-you'].map(st => `
                  <button class="spring-press"
                          style="padding:6px 12px; border-radius:var(--r-pill); border:0.5px solid var(--separator); background:${this.orbState === st ? 'var(--accent)' : 'var(--surface-2)'}; color:${this.orbState === st ? '#FFFFFF' : 'var(--label)'}; font-size:13px; font-weight:500; cursor:pointer;"
                          onclick="DesignPreviewWorkspace.setOrbState('${st}')">
                    ${st}
                  </button>
                `).join('')}
              </div>
            </div>

            <!-- Live Orb Stage -->
            <div style="min-height:220px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:20px; background:var(--bg); border-radius:var(--r-lg); padding:32px; border:0.5px solid var(--separator);">
              <div id="designOrbContainer">
                ${window.AiOrb ? window.AiOrb({ state: this.orbState, size: this.orbSize }) : ''}
              </div>
              <div style="display:flex; align-items:center; gap:16px;">
                <span class="t-caption">Size: <strong id="orbSizeLabel">${this.orbSize}px</strong></span>
                <input type="range" min="24" max="220" step="4" value="${this.orbSize}"
                       style="accent-color:var(--accent); cursor:pointer;"
                       oninput="DesignPreviewWorkspace.setOrbSize(this.value)" />
              </div>
            </div>
          </section>

          <!-- 10. AppTile Department Squircle Collection -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <h2 class="t-title-2" style="margin-bottom:6px;">10. AppTile Squircles</h2>
            <p class="t-footnote" style="margin-bottom:24px;">Concentric radii (~22%), subtle gradients, and white glyphs across all 9 core entities.</p>

            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(110px, 1fr)); gap:20px; text-align:center;">
              ${['ceo', 'coo', 'cmo', 'cto', 'cfo', 'chro', 'security', 'assistant', 'company'].map(ent => `
                <div class="hover-lift" style="display:flex; flex-direction:column; align-items:center; gap:8px; padding:16px 8px; background:var(--surface-2); border-radius:var(--r-lg); border:0.5px solid var(--separator);">
                  ${window.AppTile ? window.AppTile({ entity: ent, size: 56 }) : ''}
                  <span class="t-caption" style="font-weight:600; text-transform:uppercase;">${ent}</span>
                </div>
              `).join('')}
            </div>
          </section>

          <!-- 11. 5-Part Action Cards & Approvals (Phase 5) -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">11. 5-Part Action & Approval Cards</h2>
              <p class="t-footnote" style="margin-top:2px;">Intent • Reason • Progress • Result • Control + On-demand 'Why?' explainability.</p>
            </div>

            <div style="display:flex; flex-direction:column; gap:16px;">
              ${window.ActionCard ? window.ActionCard({
                intent: 'Scaled search advertising bid to capture surge',
                reason: 'Competitor luxury bookings reached capacity in target region.',
                state: 'done',
                result: 'Captured 14 high-intent bookings. +₹1,45,000 revenue.',
                actorEntity: 'cmo',
                actorName: 'CMO Growth Engine',
                timestamp: '5m ago',
                undoSeconds: 30
              }) : ''}

              ${window.ApprovalCard ? window.ApprovalCard({
                id: 'demo_app_1',
                title: 'Authorize Strategic Inventory Re-allocation',
                actorEntity: 'coo',
                actorName: 'Operations Director',
                riskLevel: 'Medium',
                reason: 'Rebalance fulfillment inventory across North hubs to prevent stockout.',
                worstCase: 'Minor regional shipping delay (approx 12 hrs).',
                alternative: 'Pay expedite courier surcharge (₹18,000).'
              }) : ''}
            </div>
          </section>

          <!-- 12. Department Workspace Previews -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="margin-bottom:20px;">
              <h2 class="t-title-2">12. Executive Department Workspaces</h2>
              <p class="t-footnote" style="margin-top:2px;">Single unified department template with department-specific tints, KPIs, and workforce teams.</p>
            </div>

            <div style="display:flex; flex-wrap:wrap; gap:12px;">
              ${['coo', 'cmo', 'cto', 'cfo', 'chro', 'security'].map(dept => `
                <button class="btn-apple btn-apple-secondary spring-press"
                        onclick="DepartmentWorkspace.open('${dept}')">
                  Open ${dept.toUpperCase()} Workspace →
                </button>
              `).join('')}
            </div>
          </section>

        </div>
      `;
    }

    setTheme(theme) {
      this.activeTheme = theme;
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('zonata_theme', theme);
      this.render();
    }

    setOrbState(state) {
      this.orbState = state;
      const el = document.getElementById('designOrbContainer');
      if (el && window.AiOrb) {
        el.innerHTML = window.AiOrb({ state: this.orbState, size: this.orbSize });
      }
    }

    setOrbSize(size) {
      this.orbSize = parseInt(size, 10);
      const label = document.getElementById('orbSizeLabel');
      if (label) label.textContent = `${this.orbSize}px`;
      const el = document.getElementById('designOrbContainer');
      if (el && window.AiOrb) {
        el.innerHTML = window.AiOrb({ state: this.orbState, size: this.orbSize });
      }
    }

    handleSegmentChange(segmentId) {
      if (window.UI && window.UI.showToast) {
        window.UI.showToast(`Switched segment to: ${segmentId}`, 'info');
      }
    }

    openDemoModal() {
      if (!window.UI || !window.UI.openModal) return;
      window.UI.openModal(
        'Executive Decision Approval',
        `
          <p class="t-body" style="color:var(--label-2); margin-bottom:20px;">
            The AI CMO recommends approving the Q4 DACH demand generation campaign with a budget of ₹2,50,000.
          </p>
          <div style="background:var(--surface-2); padding:16px; border-radius:var(--r-md); border:0.5px solid var(--separator); margin-bottom:24px;">
            <div class="t-caption" style="color:var(--label-3); margin-bottom:4px;">Expected Outcome:</div>
            <div class="t-headline" style="color:var(--green);">+₹12,40,000 Incremental Pipeline</div>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:12px;">
            <button class="btn-apple btn-apple-secondary" onclick="UI.closeModal()">Not Now</button>
            <button class="btn-apple btn-apple-primary" onclick="UI.showToast('Campaign approved successfully.', 'success'); UI.closeModal();">Approve Campaign</button>
          </div>
        `
      );
    }
  }

  window.DesignPreviewWorkspace = new DesignPreviewWorkspaceManager();
})();
