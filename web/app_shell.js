/**
 * URA / ZONATA — AppShell Controller
 * Manages responsive layout, sidebar rail toggle, and President/Inspector drawer.
 * The assistant lives in ura_assistant.js; this controller no longer owns a
 * fixed Ask URA bar or a second Cmd/Ctrl+K listener.
 */

(function() {
  'use strict';

  class AppShellController {
    constructor() {
      this.sidebarCollapsed = false;
      this.inspectorOpen = false;
      this.init();
    }

    init() {}

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
