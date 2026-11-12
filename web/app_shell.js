/**
 * URA / ZONATA — AppShell Controller
 * Manages responsive layout, sidebar rail toggle, Ask URA bar, ⌘K command palette, and Inspector drawer.
 */

(function() {
  'use strict';

  class AppShellController {
    constructor() {
      this.sidebarCollapsed = false;
      this.inspectorOpen = false;
      this.init();
    }

    init() {
      // The URA shell owns the command palette. Keep this shortcut working even
      // if this legacy controller is still mounted.
      document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          if (window.URAShell && window.URAShell.openPalette) {
            window.URAShell.openPalette();
            return;
          }
          this.openAskUra();
        }
      });
    }

    openAskUra() {
      // The new UI chats with the CEO on a real screen. The old modal is kept
      // only as a fallback when the URA layer has not loaded.
      if (window.URAShell) {
        window.navigateTo('/ask-ceo');
        return;
      }
      this.openAskUraModal();
    }

    toggleSidebarCollapse() {
      const sidebar = document.getElementById('appSidebar');
      if (!sidebar) return;
      this.sidebarCollapsed = !this.sidebarCollapsed;
      sidebar.classList.toggle('collapsed', this.sidebarCollapsed);
      const wrap = document.getElementById('askUraBarWrap');
      if (wrap) {
        wrap.style.left = this.sidebarCollapsed ? 'calc(50% + 36px)' : 'calc(50% + 132px)';
      }
    }

    openCompanySwitcher() {
      if (!window.UI || !window.UI.openModal) return;
      const companies = (window.state && window.state.companies) || [
        { company_id: 'comp_primary', name: 'ZONATA Technologies', industry: 'SaaS / AI Systems', status: 'ACTIVE' }
      ];

      const rows = companies.map(c => `
        <div class="list-row-apple spring-press" onclick="AppShell.selectCompany('${c.company_id}')" style="margin-bottom:8px; border-radius:var(--r-md); border:0.5px solid var(--separator);">
          <div class="list-row-left">
            ${window.AppTile ? window.AppTile({ entity: 'company', size: 36 }) : ''}
            <div>
              <div class="t-headline" style="font-size:14px;">${escapeHtml(c.name)}</div>
              <div class="t-caption" style="color:var(--label-2);">${escapeHtml(c.industry || 'Active Operating Company')}</div>
            </div>
          </div>
          <div class="list-row-right">
            <span class="chip-apple chip-green">Active</span>
          </div>
        </div>
      `).join('');

      window.UI.openModal(
        'Switch Company Operating Context',
        `
          <p class="t-body" style="color:var(--label-2); margin-bottom:16px;">
            Select an operating company or onboard a new business entity:
          </p>
          <div style="margin-bottom:20px;">
            ${rows}
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; pt:12px; border-top:0.5px solid var(--separator);">
            <button class="btn-apple btn-apple-secondary" onclick="window.navigateTo('/company/new'); UI.closeModal();">
              ${window.Icon ? window.Icon({ name: 'plus', size: 16, tone: 'accent' }) : '+'}
              <span>Add New Company</span>
            </button>
            <button class="btn-apple btn-apple-plain" onclick="UI.closeModal()">Cancel</button>
          </div>
        `
      );
    }

    selectCompany(companyId) {
      if (window.CurrentCompanyContext && window.CurrentCompanyContext.setCompanyId) {
        window.CurrentCompanyContext.setCompanyId(companyId);
      }
      if (window.UI) {
        window.UI.showToast(`Switched context to: ${companyId}`, 'info');
        window.UI.closeModal();
      }
    }

    openAskUraModal() {
      if (!window.UI || !window.UI.openModal) return;

      const starterQuestions = [
        "How is my company doing today?",
        "What items need my approval?",
        "Show me where we are losing money",
        "What are our active sales leads?",
        "Audit employee SOP compliance"
      ];

      const chips = starterQuestions.map(q => `
        <button class="chip-apple chip-filter spring-press"
                onclick="AppShell.submitAskUra('${escapeHtml(q)}')">
          ${escapeHtml(q)}
        </button>
      `).join('');

      window.UI.openModal(
        'Ask URA AI Assistant',
        `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:flex; align-items:center; gap:12px; background:var(--surface-2); padding:10px 14px; border-radius:var(--r-xl); border:0.5px solid var(--separator);">
              ${window.AiOrb ? window.AiOrb({ state: 'idle', size: 32 }) : ''}
              <input type="text"
                     id="askUraModalInput"
                     class="input-apple"
                     style="background:transparent; border:none; box-shadow:none; padding:4px 0; font-size:16px;"
                     placeholder="Type a question, command, or jump to workspace..."
                     autofocus
                     onkeydown="if(event.key==='Enter') AppShell.submitAskUra(this.value)" />
            </div>

            <div>
              <span class="t-caption" style="display:block; margin-bottom:8px; color:var(--label-3); text-transform:uppercase; letter-spacing:0.04em;">Suggested Starter Inquiries:</span>
              <div style="display:flex; flex-wrap:wrap; gap:8px;">
                ${chips}
              </div>
            </div>

            <div id="askUraReplyArea" style="display:none; padding:16px; background:var(--surface-2); border-radius:var(--r-lg); border:0.5px solid var(--separator);">
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                ${window.AiOrb ? window.AiOrb({ state: 'speaking', size: 24 }) : ''}
                <span class="t-headline" style="font-size:14px;">URA Autonomous Insight</span>
              </div>
              <div id="askUraStreamedText" class="t-body" style="line-height:1.6; color:var(--label);"></div>
            </div>
          </div>
        `
      );

      setTimeout(() => {
        const input = document.getElementById('askUraModalInput');
        if (input) input.focus();
      }, 100);
    }

    async submitAskUra(query) {
      if (!query || !query.trim()) return;
      const input = document.getElementById('askUraModalInput');
      if (input) input.value = query;

      const replyArea = document.getElementById('askUraReplyArea');
      const streamEl = document.getElementById('askUraStreamedText');
      if (!replyArea || !streamEl) return;

      replyArea.style.display = 'block';
      streamEl.innerHTML = '<span class="status-pulse-dot"></span> Asking the CEO service...';

      // The old build scripted an answer here. This now calls the real CEO
      // endpoint and reports an honest connection error instead of inventing
      // profit figures or approval counts.
      try {
        const res = await fetch('/api/v8/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query.trim() })
        }).then(r => r.json());

        const reply = res.reply || {};
        const answer = reply.answer || res.answer;
        if (!res.success || !answer) {
          throw new Error(res.error || res.detail || 'The CEO service returned no answer.');
        }

        streamEl.innerHTML = '';
        const meta = [
          reply.model_used,
          reply.epistemic_classification,
          reply.evidence_digest ? 'Evidence ' + String(reply.evidence_digest).slice(0, 18) : ''
        ].filter(Boolean).join(' · ');

        // Keep the short reveal, but reveal the real answer rather than a script.
        const words = String(answer).split(' ');
        let idx = 0;
        const interval = setInterval(() => {
          if (idx < words.length) {
            streamEl.textContent += (idx === 0 ? '' : ' ') + words[idx];
            idx++;
          } else {
            clearInterval(interval);
            if (meta) {
              streamEl.innerHTML += `<div style="margin-top:8px;font-size:11px;color:var(--label-3);">${escapeHtml(meta)}</div>`;
            }
            streamEl.innerHTML += `
              <div style="margin-top:12px; display:flex; gap:8px;">
                <span class="chip-apple chip-accent" style="cursor:pointer;" onclick="window.navigateTo('/ask-ceo'); UI.closeModal();">Open Ask CEO →</span>
              </div>
            `;
          }
        }, 20);
      } catch (err) {
        streamEl.innerHTML = `<div style="color:var(--red);font-size:13px;line-height:1.55;">
          <b>Could not reach the CEO service.</b><br>${escapeHtml(err.message || 'Unknown error')}<br>
          <span style="color:var(--label-2);">Nothing is being simulated. Check the connection and try again.</span>
        </div>
        <div style="margin-top:10px;"><button class="btn-apple btn-apple-secondary" onclick="AppShell.submitAskUra(${JSON.stringify(query).replace(/"/g, '&quot;')})">Retry</button></div>`;
      }
    }

    openInspector(title, contentHtml) {
      let panel = document.getElementById('appleInspectorPanel');
      if (!panel) {
        panel = document.createElement('aside');
        panel.id = 'appleInspectorPanel';
        panel.className = 'apple-inspector-panel';
        panel.innerHTML = `
          <div class="inspector-header">
            <h3 class="t-headline" id="inspectorTitle">Inspector</h3>
            <button class="btn-apple-icon spring-press" onclick="AppShell.closeInspector()" aria-label="Close Inspector">
              ${window.Icon ? window.Icon({ name: 'x', size: 18, tone: 'default' }) : '✕'}
            </button>
          </div>
          <div class="inspector-body" id="inspectorBody"></div>
        `;
        document.body.appendChild(panel);
      }

      document.getElementById('inspectorTitle').textContent = title;
      document.getElementById('inspectorBody').innerHTML = contentHtml;
      panel.classList.add('open');
      this.inspectorOpen = true;
    }

    closeInspector() {
      const panel = document.getElementById('appleInspectorPanel');
      if (panel) {
        panel.classList.remove('open');
        this.inspectorOpen = false;
      }
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  window.AppShell = new AppShellController();
  window.Inspector = {
    open: (t, c) => window.AppShell.openInspector(t, c),
    close: () => window.AppShell.closeInspector()
  };
})();
