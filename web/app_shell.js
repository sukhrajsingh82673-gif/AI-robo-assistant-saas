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
      // One switcher for the whole app (web/company_setup_switcher.js).
      if (window.CompanySetupSwitcher && typeof window.CompanySetupSwitcher.open === 'function') {
        window.CompanySetupSwitcher.open();
        return;
      }
      // Fallback: a clear message rather than a fabricated company.
      if (window.UI && window.UI.showToast) {
        window.UI.showToast('The company switcher did not load. Reload the page.', 'error');
      }
    }

    selectCompany(companyId) {
      if (!companyId) return;
      if (window.CompanySetupSwitcher && typeof window.CompanySetupSwitcher.selectCompany === 'function') {
        window.CompanySetupSwitcher.selectCompany(companyId);
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
