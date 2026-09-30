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
      try {
        const res = await fetch('/api/companies');
        if (res.ok) {
          const data = await res.json();
          this.companies = Array.isArray(data.companies) ? data.companies : [];

          // Keep in sync with legacy state.companies if present
          if (window.state) {
            window.state.companies = this.companies;
          }

          // If no active company selected, or active company no longer exists, select first
          if (!this.activeCompanyId || !this.companies.some(c => c.id === this.activeCompanyId)) {
            this.activeCompanyId = this.companies.length > 0 ? this.companies[0].id : null;
            if (this.activeCompanyId) {
              localStorage.setItem('zonata_active_company_id', this.activeCompanyId);
            } else {
              localStorage.removeItem('zonata_active_company_id');
            }
          }

          this.activeCompany = this.companies.find(c => c.id === this.activeCompanyId) || null;
          if (window.state) {
            window.state.activeCompanyId = this.activeCompanyId;
          }

          this.updateDropdown();
          this.notify();
        }
      } catch (err) {
        console.warn('[CurrentCompanyContext] Backend offline or fetch error:', err);
      }
    }

    getCompanyId() {
      return this.activeCompanyId;
    }

    getCompany() {
      return this.activeCompany;
    }

    getCompanies() {
      return this.companies;
    }

    hasCompany() {
      return !!(this.activeCompanyId && this.companies.length > 0);
    }

    setCompanyId(id) {
      if (!id || id === this.activeCompanyId) return;
      this.activeCompanyId = id;
      this.activeCompany = this.companies.find(c => c.id === id) || null;
      localStorage.setItem('zonata_active_company_id', id);

      if (window.state) {
        window.state.activeCompanyId = id;
      }

      this.updateDropdown();
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
          this.setCompanyId(e.target.value);
        });
      }
    }

    updateDropdown() {
      const selector = document.getElementById('globalCompanySelector');
      if (!selector) return;

      if (this.companies.length === 0) {
        selector.innerHTML = '<option value="">No Company Connected</option>';
        selector.disabled = true;
        return;
      }

      selector.disabled = false;
      selector.innerHTML = this.companies.map(c => `
        <option value="${c.id}" ${c.id === this.activeCompanyId ? 'selected' : ''}>
          ${c.name} (${c.industry || 'Operations'})
        </option>
      `).join('');
    }

    renderEmptyState(container, title = 'No company connected', subtitle = 'Connect an existing company or create a new company to begin.') {
      if (!container) return;
      container.innerHTML = `
        <div class="empty-company-workspace" style="display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:64px 20px; min-height:480px; max-width:540px; margin:0 auto;">
          <div style="width:68px; height:68px; border-radius:18px; background:rgba(37,99,235,0.12); border:1px solid rgba(37,99,235,0.25); display:flex; align-items:center; justify-content:center; font-size:32px; margin-bottom:20px;">
            🏢
          </div>
          <h2 style="font-size:22px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">
            ${title}
          </h2>
          <p style="font-size:14px; color:var(--text-secondary); line-height:1.5; margin-bottom:28px;">
            ${subtitle}
          </p>
          <div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center;">
            <button class="btn-primary" style="padding:10px 20px; font-size:13.5px;" onclick="if(window.CompanyWorkspace){ window.navigateTo('/company/new'); CompanyWorkspace.startOnboarding('new'); } else { showToast('Add Company clicked', 'info'); }">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
              Add Company
            </button>
            <button class="btn-secondary" style="padding:10px 20px; font-size:13.5px;" onclick="if(window.CompanyWorkspace){ window.navigateTo('/company/new'); CompanyWorkspace.startOnboarding('existing'); } else { showToast('Import Company clicked', 'info'); }">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
              Import Company Data
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
