/**
 * ZONATA — Canonical Company Operating Context
 * Single source of truth for company context consumed identically across:
 * Overview, Company, AI CEO, Organization, Workforce, Missions/TaskMaker,
 * Processes, TrustGraph, Tools, Reports, and Settings.
 */

(function() {
  'use strict';

  class CanonicalCompanyContextManager {
    constructor() {
      this.activeCompanyId = null;
      this.activeCompany = null;
      this.companies = [];
      this.subscribers = new Set();
      this.initialized = false;
    }

    async init() {
      if (this.initialized) return;
      this.initialized = true;

      // Load stored preference
      const storedId = localStorage.getItem('zonata_active_company_id');
      if (storedId) {
        this.activeCompanyId = storedId;
      }

      await this.refresh();
      this.bindSelector();
    }

    async refresh() {
      // Unauthenticated visitors do not need to poll /api/companies
      const token = localStorage.getItem('zonata_auth_token');
      if (!token) {
        this.updateDropdown();
        this.syncSidebar();
        return;
      }

      try {
        const res = await fetch('/api/companies');
        if (res.ok) {
          const data = await res.json();
          this.companies = Array.isArray(data.companies) ? data.companies : [];

          // Keep in sync with legacy state.companies if present
          if (window.state) {
            window.state.companies = this.companies;
          }

          // If active company ID is set but does not exist in loaded companies, reset
          if (this.activeCompanyId && !this.companies.some(c => c.id === this.activeCompanyId)) {
            this.activeCompanyId = null;
            try { localStorage.removeItem('zonata_active_company_id'); } catch (err) { /* blocked */ }
          }

          if (!this.activeCompanyId && this.companies.length > 0) {
            this.activeCompanyId = this.companies[0].id;
            try { localStorage.setItem('zonata_active_company_id', this.activeCompanyId); } catch (err) { /* blocked */ }
          }

          this.activeCompany = this.companies.find(c => c.id === this.activeCompanyId) || (this.companies[0] || null);
          if (window.state) {
            window.state.activeCompanyId = this.activeCompanyId;
          }

          this.updateDropdown();
          this.syncSidebar();
          this.notify();
        }
      } catch (err) {
        console.warn('[CurrentCompanyContext] Backend offline or fetch error:', err);
      }
    }

    getCompanyId() {
      if (this.activeCompanyId) return this.activeCompanyId;
      if (this.companies && this.companies.length > 0) return this.companies[0].id;
      if (window.state && window.state.companies && window.state.companies.length > 0) {
        return window.state.companies[0].id;
      }
      return null;
    }

    getCompany() {
      if (this.activeCompany) return this.activeCompany;
      if (this.companies && this.companies.length > 0) return this.companies[0];
      return null;
    }

    getCompanies() {
      return this.companies;
    }

    hasCompany() {
      return (this.companies && this.companies.length > 0);
    }

    setCompanyId(id) {
      const normalizedId = (id && id !== 'ALL') ? id : null;
      if (normalizedId === this.activeCompanyId) {
        this.syncSidebar();
        return;
      }
      this.activeCompanyId = normalizedId;
      if (normalizedId) {
        try { localStorage.setItem('zonata_active_company_id', normalizedId); } catch (err) { /* blocked */ }
      } else {
        try { localStorage.removeItem('zonata_active_company_id'); } catch (err) { /* blocked */ }
      }
      this.activeCompany = this.companies.find(c => c.id === normalizedId) || null;

      if (window.state) {
        window.state.activeCompanyId = normalizedId;
      }

      this.updateDropdown();
      this.syncSidebar();
      this.notify();

      // Trigger re-render of active screen
      if (window.renderActiveNavView) {
        window.renderActiveNavView();
      }
    }

    subscribe(callback) {
      if (typeof callback === 'function') {
        this.subscribers.add(callback);
        // Invoke immediately with current context
        callback(this.activeCompany, this.activeCompanyId, this.companies);
        return () => this.subscribers.delete(callback);
      }
      return () => {};
    }

    notify() {
      for (const cb of this.subscribers) {
        try {
          cb(this.activeCompany, this.activeCompanyId, this.companies);
        } catch (e) {
          console.error('[CurrentCompanyContext] Error in subscriber callback:', e);
        }
      }
    }

    bindSelector() {
      const selector = document.getElementById('globalCompanySelector');
      if (selector) {
        selector.addEventListener('change', (e) => {
          if (!this.companies.length) {
            // No company to switch to: take the user to the Add page.
            if (window.navigateTo) window.navigateTo('/company/add');
            return;
          }
          this.setCompanyId(e.target.value);
        });
      }
    }

    updateDropdown() {
      const selector = document.getElementById('globalCompanySelector');
      if (!selector) return;

      if (this.companies.length === 0) {
        selector.innerHTML = '<option value="">No company yet — add one</option>';
        selector.disabled = false;
        return;
      }

      selector.disabled = false;
      const active = this.companies.find(c => c.id === this.activeCompanyId);
      const ordered = active
        ? [active].concat(this.companies.filter(c => c.id !== active.id))
        : this.companies;

      let opts = `<option value="" ${!this.activeCompanyId ? 'selected' : ''}>All Companies (Group Portfolio)</option>`;
      opts += ordered.map(c => {
        const selected = c.id === this.activeCompanyId ? 'selected' : '';
        const label = active && c.id === active.id ? `${c.name} (current)` : c.name;
        return `<option value="${c.id}" ${selected}>${label}</option>`;
      }).join('');
      selector.innerHTML = opts;
    }

    /**
     * Keep the sidebar identity block truthful. The switcher module owns the
     * status vocabulary; this only reads it.
     */
    syncSidebar() {
      const company = this.activeCompany
        || this.companies.find(c => c.id === this.activeCompanyId)
        || (this.companies[0] || null);
      if (window.CompanySetupSwitcher && typeof window.CompanySetupSwitcher.syncSidebar === 'function') {
        window.CompanySetupSwitcher.syncSidebar();
        return;
      }
      const nameEl = document.getElementById('sidebarCompanyName');
      if (nameEl) nameEl.textContent = company ? company.name : 'No company yet';
    }

    renderEmptyState(container, title = 'No company connected', subtitle = 'Add your first company to start operating.') {
      if (!container) return;
      const goAdd = "if(window.navigateTo){window.navigateTo('/company/add');}else{window.location.hash='#/company/add';}";
      container.innerHTML = `
        <div class="empty-company-workspace" style="display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:64px 20px; min-height:480px; max-width:540px; margin:0 auto;">
          <div style="width:68px; height:68px; border-radius:18px; background:var(--accent-tint); border:1px solid rgba(0,113,227,0.25); display:flex; align-items:center; justify-content:center; font-size:32px; margin-bottom:20px;">
            🏢
          </div>
          <h2 style="font-size:22px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
            ${title}
          </h2>
          <p style="font-size:14px; color:var(--text-secondary); line-height:1.5; margin-bottom:28px;">
            ${subtitle}
          </p>
          <div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center;">
            <button class="btn-primary" style="padding:10px 20px; font-size:13.5px;" onclick="${goAdd}">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
              Add Company
            </button>
          </div>
        </div>
      `;
    }
  }

  window.CurrentCompanyContext = new CanonicalCompanyContextManager();
  document.addEventListener('DOMContentLoaded', () => {
    window.CurrentCompanyContext.init();
  });
})();
