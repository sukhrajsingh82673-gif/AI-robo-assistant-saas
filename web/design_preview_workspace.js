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
    }

    render(containerId = 'view-design') {
      const container = document.getElementById(containerId);
      if (!container) return;

      container.innerHTML = `
        <div style="max-width:1120px; margin:0 auto; padding:32px 24px 80px; display:flex; flex-direction:column; gap:40px;">

          <!-- Header & Live Theme Switcher -->
          <header style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:20px; padding-bottom:24px; border-bottom:0.5px solid var(--separator);">
            <div>
              <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:8px;">
                <span class="t-caption" style="text-transform:uppercase; letter-spacing:0.06em; color:var(--accent); font-weight:700;">Design Foundations</span>
                <span style="font-size:12px; color:var(--label-3);">•</span>
                <span class="t-caption" style="color:var(--label-3);">Phase 1 Verification</span>
              </div>
              <h1 class="t-large-title">Apple-Grade Design System</h1>
              <p class="t-callout" style="max-width:640px; margin-top:6px;">
                Single source of truth for design tokens, typography, materials, motion springs, and signature presence.
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

          <!-- 1. Signature AI Presence (<AiOrb />) -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:24px;">
              <div>
                <h2 class="t-title-2">Signature AI Presence</h2>
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
            <div style="min-height:260px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:24px; background:var(--bg); border-radius:var(--r-lg); padding:40px; border:0.5px solid var(--separator);">
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

          <!-- 2. Typography Scale -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <h2 class="t-title-2" style="margin-bottom:6px;">Typography Scale</h2>
            <p class="t-footnote" style="margin-bottom:24px;">Inter font stack with tabular numbers for data alignment.</p>

            <div style="display:flex; flex-direction:column; gap:24px;">
              <div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:0.5px solid var(--separator); padding-bottom:12px;">
                <span class="t-caption" style="min-width:140px; color:var(--label-3);">--t-display (48/52)</span>
                <span class="t-display tabular-nums">₹4,28,500</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:0.5px solid var(--separator); padding-bottom:12px;">
                <span class="t-caption" style="min-width:140px; color:var(--label-3);">--t-large-title (34/41)</span>
                <span class="t-large-title">Autonomous Company</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:0.5px solid var(--separator); padding-bottom:12px;">
                <span class="t-caption" style="min-width:140px; color:var(--label-3);">--t-title-1 (28/34)</span>
                <span class="t-title-1">Executive Department Strategy</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:0.5px solid var(--separator); padding-bottom:12px;">
                <span class="t-caption" style="min-width:140px; color:var(--label-3);">--t-title-2 (22/28)</span>
                <span class="t-title-2">Sales Pipeline & Commercial Operations</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:0.5px solid var(--separator); padding-bottom:12px;">
                <span class="t-caption" style="min-width:140px; color:var(--label-3);">--t-headline (17/22)</span>
                <span class="t-headline">Q4 Revenue Target Achieved</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:baseline; border-bottom:0.5px solid var(--separator); padding-bottom:12px;">
                <span class="t-caption" style="min-width:140px; color:var(--label-3);">--t-body (15/22)</span>
                <span class="t-body">Every employee owns assigned Key Result Areas and Standard Operating Procedures.</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:baseline; padding-bottom:6px;">
                <span class="t-caption" style="min-width:140px; color:var(--label-3);">--t-caption (12/16)</span>
                <span class="t-caption">VERIFIED PROVENANCE • SHA-256 HASH CHAIN</span>
              </div>
            </div>
          </section>

          <!-- 3. Dynamic Number Count-Up & Springs -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
              <div>
                <h2 class="t-title-2">Spring Motion & Number Animation</h2>
                <p class="t-footnote" style="margin-top:2px;">600ms tabular count-up without layout jumps.</p>
              </div>
              <button class="spring-press"
                      style="padding:8px 18px; border-radius:var(--r-pill); border:none; background:var(--accent); color:#FFFFFF; font-size:14px; font-weight:600; cursor:pointer;"
                      onclick="DesignPreviewWorkspace.triggerCountUp()">
                Trigger Count-Up
              </button>
            </div>

            <div style="background:var(--bg); padding:32px; border-radius:var(--r-lg); border:0.5px solid var(--separator); display:flex; flex-direction:column; align-items:center; gap:8px;">
              <span class="t-caption" style="text-transform:uppercase; letter-spacing:0.04em;">Today's Verified Profit</span>
              <div id="testCountUpDisplay" class="t-display tabular-nums" style="color:var(--green);">
                ₹4,28,500
              </div>
            </div>
          </section>

          <!-- 4. AppTile Department Squircle Collection -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <h2 class="t-title-2" style="margin-bottom:6px;">AppTile Squircles</h2>
            <p class="t-footnote" style="margin-bottom:24px;">Concentric radii (~22%), subtle gradients, and white glyphs across all 9 core entities.</p>

            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(110px, 1fr)); gap:20px; text-align:center;">
              ${['ceo', 'coo', 'cmo', 'cto', 'cfo', 'chro', 'security', 'assistant', 'company'].map(ent => `
                <div class="hover-lift" style="display:flex; flex-direction:column; align-items:center; gap:8px; padding:16px 8px; background:var(--surface-2); border-radius:var(--r-lg); border:0.5px solid var(--separator);">
                  ${window.AppTile ? window.AppTile({ entity: ent, size: 56 }) : ''}
                  <span class="t-caption" style="font-weight:600; text-transform:uppercase;">${ent}</span>
                </div>
              `).join('')}
            </div>

            <!-- Size Comparison -->
            <div style="margin-top:28px; padding-top:20px; border-top:0.5px solid var(--separator); display:flex; align-items:center; justify-content:center; gap:28px; flex-wrap:wrap;">
              <div style="display:flex; align-items:center; gap:8px;">
                ${window.AppTile ? window.AppTile({ entity: 'ceo', size: 28 }) : ''}
                <span class="t-caption">28px (Sidebar)</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                ${window.AppTile ? window.AppTile({ entity: 'ceo', size: 40 }) : ''}
                <span class="t-caption">40px (List rows)</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                ${window.AppTile ? window.AppTile({ entity: 'ceo', size: 64 }) : ''}
                <span class="t-caption">64px (Cards)</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                ${window.AppTile ? window.AppTile({ entity: 'ceo', size: 96 }) : ''}
                <span class="t-caption">96px (Hero headers)</span>
              </div>
            </div>
          </section>

          <!-- 5. Material & Glass Chrome -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <h2 class="t-title-2" style="margin-bottom:6px;">Materials & Elevation</h2>
            <p class="t-footnote" style="margin-bottom:24px;">Translucent glass used for chrome that floats above content; solid cards below.</p>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:20px;">
              <div style="padding:24px; border-radius:var(--r-lg); background:var(--surface); border:0.5px solid var(--separator); box-shadow:var(--shadow-1);">
                <div class="t-headline">Shadow 1</div>
                <div class="t-caption" style="margin-top:4px;">Resting card baseline</div>
              </div>
              <div style="padding:24px; border-radius:var(--r-lg); background:var(--surface); border:0.5px solid var(--separator); box-shadow:var(--shadow-2);">
                <div class="t-headline">Shadow 2</div>
                <div class="t-caption" style="margin-top:4px;">Elevated panel / popover</div>
              </div>
              <div style="padding:24px; border-radius:var(--r-lg); background:var(--surface); border:0.5px solid var(--separator); box-shadow:var(--shadow-3);">
                <div class="t-headline">Shadow 3</div>
                <div class="t-caption" style="margin-top:4px;">Hover lift / sheet</div>
              </div>
              <div class="glass" style="padding:24px; border-radius:var(--r-lg); box-shadow:var(--shadow-4);">
                <div class="t-headline">Glass Material</div>
                <div class="t-caption" style="margin-top:4px;">Translucent floating chrome</div>
              </div>
            </div>
          </section>

          <!-- 6. Color Tokens & Semantic Indicators -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <h2 class="t-title-2" style="margin-bottom:6px;">Semantic Palette & Contrast</h2>
            <p class="t-footnote" style="margin-bottom:24px;">Pairing color with symbols and words for WCAG 2.2 AA conformance.</p>

            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:16px;">
              ${[
                { name: 'Accent', token: 'var(--accent)', tint: 'var(--accent-tint)' },
                { name: 'Green (Success)', token: 'var(--green)', tint: 'var(--green-tint)' },
                { name: 'Orange (Attention)', token: 'var(--orange)', tint: 'var(--orange-tint)' },
                { name: 'Red (Critical)', token: 'var(--red)', tint: 'var(--red-tint)' },
                { name: 'Purple (Strategy)', token: 'var(--purple)', tint: 'var(--purple-tint)' },
                { name: 'Teal (Finance)', token: 'var(--teal)', tint: 'var(--teal-tint)' }
              ].map(c => `
                <div style="padding:16px; border-radius:var(--r-lg); background:${c.tint}; border:0.5px solid var(--separator); display:flex; flex-direction:column; gap:8px;">
                  <div style="width:24px; height:24px; border-radius:50%; background:${c.token}; box-shadow:var(--shadow-1);"></div>
                  <div class="t-headline" style="color:${c.token}; font-size:14px;">${c.name}</div>
                  <div class="t-caption" style="color:var(--label-2);">12% Tint BG</div>
                </div>
              `).join('')}
            </div>
          </section>

          <!-- 7. Icon Library Sample -->
          <section style="background:var(--surface); border:0.5px solid var(--separator); border-radius:var(--r-xl); padding:32px; box-shadow:var(--shadow-1);">
            <h2 class="t-title-2" style="margin-bottom:6px;">Icon System Sample (1.75px Stroke)</h2>
            <p class="t-footnote" style="margin-bottom:24px;">Precision glyphs vertically aligned to cap height.</p>

            <div style="display:flex; flex-wrap:wrap; gap:16px; align-items:center;">
              ${['home', 'compass', 'trend', 'chip', 'coins', 'people', 'shield', 'sparkles', 'bell', 'search', 'settings', 'lock', 'play', 'check', 'x', 'arrow-right'].map(ic => `
                <div style="padding:12px; background:var(--surface-2); border-radius:var(--r-md); border:0.5px solid var(--separator); display:flex; align-items:center; gap:8px;">
                  ${window.Icon ? window.Icon({ name: ic, size: 20, tone: 'default' }) : ''}
                  <span class="t-caption">${ic}</span>
                </div>
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

    triggerCountUp() {
      const el = document.getElementById('testCountUpDisplay');
      if (!el || !window.Motion) return;
      this.testNumber += Math.floor(Math.random() * 25000) + 5000;
      window.Motion.animateCountUp(el, this.testNumber, {
        duration: 600,
        formatter: (val) => `₹${Math.round(val).toLocaleString('en-IN')}`
      });
    }
  }

  window.DesignPreviewWorkspace = new DesignPreviewWorkspaceManager();
})();
