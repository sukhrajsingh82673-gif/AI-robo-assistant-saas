/**
 * ZONATA — Company switcher
 *
 * One switcher for the whole app:
 *   - the current company is always first, the rest keep their server order;
 *   - when there are no companies it shows a real empty state, never a fake one;
 *   - "Add company" is always the last control in the sheet;
 *   - a phone gets a bottom sheet, a desktop gets a centred dialog;
 *   - it is keyboard operable (arrow keys, Tab trap, Escape) and screen-reader
 *     labelled (role=dialog, role=option, aria-current).
 *
 * Selection goes through CurrentCompanyContext so every screen, the assistant
 * and the topbar dropdown stay in sync.
 */

(function() {
  'use strict';

  const ROOT_ID = 'zcSwitcherRoot';

  const STATUS_META = {
    DRAFT: { key: 'status.draft', tone: 'neutral' },
    CREATING: { key: 'status.creating', tone: 'accent' },
    ONBOARDING: { key: 'status.onboarding', tone: 'accent' },
    OPERATIONAL: { key: 'status.operational', tone: 'green' },
    NEEDS_ATTENTION: { key: 'status.needs_attention', tone: 'orange' },
    PENDING_EXPORT: { key: 'status.pending_export', tone: 'orange' },
    PENDING_DELETION: { key: 'status.pending_deletion', tone: 'red' },
    DELETED: { key: 'status.deleted', tone: 'red' },
    SUSPENDED: { key: 'status.suspended', tone: 'orange' }
  };

  function t(key, vars) {
    if (window.I18n && typeof window.I18n.t === 'function') return window.I18n.t(key, vars);
    return String(key || '');
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  function normaliseStatus(value) {
    const status = String(value || '').toUpperCase();
    if (status === 'ATTENTION') return 'NEEDS_ATTENTION';
    return status || 'UNKNOWN';
  }

  function statusMeta(value) {
    const status = normaliseStatus(value);
    return STATUS_META[status] || { key: 'status.unknown', tone: 'neutral' };
  }

  function statusLabel(value) {
    return t(statusMeta(value).key);
  }

  function isPhone() {
    try {
      return !!(window.matchMedia && window.matchMedia('(max-width: 640px)').matches);
    } catch (err) {
      return false;
    }
  }

  function normaliseCompany(raw) {
    if (!raw || typeof raw !== 'object') return null;
    const id = raw.id || raw.company_id;
    const name = raw.name;
    if (!id || !name) return null;
    const revenue = raw.revenue && typeof raw.revenue === 'object' ? raw.revenue : null;
    return {
      id: String(id),
      name: String(name),
      industry: raw.industry || '',
      status: normaliseStatus(raw.status),
      type: raw.type || raw.company_type || '',
      raw: raw,
      revenue: revenue ? revenue.amount : raw.revenue
    };
  }

  function cachedCompanies() {
    const ctx = window.CurrentCompanyContext;
    let list = [];
    if (ctx && typeof ctx.getCompanies === 'function') {
      const fromContext = ctx.getCompanies();
      if (Array.isArray(fromContext)) list = fromContext;
    }
    if (!list.length && window.state && Array.isArray(window.state.companies)) {
      list = window.state.companies;
    }
    return (list || []).map(normaliseCompany).filter(Boolean);
  }

  function activeCompanyId(companies) {
    const ctx = window.CurrentCompanyContext;
    let id = ctx && typeof ctx.getCompanyId === 'function' ? ctx.getCompanyId() : null;
    if (!id && window.state) id = window.state.activeCompanyId || null;
    if (!id && companies.length) id = companies[0].id;
    return id ? String(id) : null;
  }

  function currentCompany() {
    const companies = cachedCompanies();
    if (!companies.length) return null;
    const id = activeCompanyId(companies);
    return companies.find((company) => company.id === id) || companies[0];
  }

  function orderedCompanies() {
    const companies = cachedCompanies();
    if (companies.length < 2) return companies;
    const id = activeCompanyId(companies);
    const active = companies.find((company) => company.id === id);
    if (!active) return companies;
    return [active].concat(companies.filter((company) => company.id !== active.id));
  }

  function currentFocusable(root) {
    if (!root) return [];
    return Array.prototype.slice.call(
      root.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
    ).filter((el) => !el.disabled && el.getAttribute('aria-hidden') !== 'true');
  }

  class CompanySwitcher {
    constructor() {
      this._refreshing = false;
      this._error = false;
      this._returnFocus = null;
      this._keydown = this._onKeydown.bind(this);
    }

    isOpen() {
      return !!document.getElementById(ROOT_ID);
    }

    open(options) {
      const opts = options || {};
      if (this.isOpen()) return;
      this._returnFocus = document.activeElement;
      this._refreshing = false;
      this._error = false;
      this._ensureRoot();
      this.render();
      if (opts.refresh !== false) this.refresh();
    }

    close() {
      const root = document.getElementById(ROOT_ID);
      if (root && root.parentNode) root.parentNode.removeChild(root);
      document.removeEventListener('keydown', this._keydown);
      document.body.classList.remove('zc-sheet-open');
      if (this._returnFocus && typeof this._returnFocus.focus === 'function') {
        try { this._returnFocus.focus(); } catch (err) { /* detached */ }
      }
      this._returnFocus = null;
    }

    _ensureRoot() {
      let root = document.getElementById(ROOT_ID);
      if (!root) {
        root = document.createElement('div');
        root.id = ROOT_ID;
        document.body.appendChild(root);
      }
      document.body.classList.add('zc-sheet-open');
      document.addEventListener('keydown', this._keydown);
    }

    _companiesForRender() {
      return orderedCompanies();
    }

    render() {
      const root = document.getElementById(ROOT_ID);
      if (!root) return;
      const companies = this._companiesForRender();
      const activeId = activeCompanyId(companies);
      const phone = isPhone();

      const rows = companies.map((company) => {
        const active = company.id === activeId;
        const meta = statusMeta(company.status);
        return `
          <button type="button"
                  class="zc-company-row${active ? ' is-current' : ''}"
                  role="option"
                  aria-selected="${active ? 'true' : 'false'}"
                  ${active ? 'aria-current="true"' : ''}
                  data-company-id="${escapeAttr(company.id)}">
            <span class="zc-company-tile" aria-hidden="true">
              ${window.AppTile ? window.AppTile({ entity: 'company', size: 36 }) : '<span class="zc-company-tile-fallback">Z</span>'}
            </span>
            <span class="zc-company-main">
              <span class="zc-company-name">${escapeHtml(company.name)}</span>
              <span class="zc-company-meta">
                <span class="zc-status-dot" data-tone="${escapeAttr(meta.tone)}" aria-hidden="true"></span>
                <span>${escapeHtml(company.industry || t('company.switcher.unknown_industry'))}</span>
                <span aria-hidden="true">·</span>
                <span>${escapeHtml(statusLabel(company.status))}</span>
              </span>
            </span>
            ${active ? `<span class="zc-chip zc-chip-current">${escapeHtml(t('company.switcher.current'))}</span>` : '<span class="zc-company-enter" aria-hidden="true">›</span>'}
          </button>
        `;
      }).join('');

      const body = companies.length
        ? `<div class="zc-company-list" role="listbox" aria-label="${escapeAttr(t('company.switcher.title'))}">${rows}</div>`
        : `
          <div class="zc-switcher-empty">
            <div class="zc-switcher-empty-icon" aria-hidden="true">${window.Icon ? window.Icon({ name: 'building', size: 28, tone: 'muted' }) : '🏢'}</div>
            <h3 class="zc-switcher-empty-title">${escapeHtml(t('company.switcher.empty.title'))}</h3>
            <p class="zc-switcher-empty-body">${escapeHtml(t('company.switcher.empty.body'))}</p>
          </div>
        `;

      const errorBanner = this._error
        ? `<div class="zc-inline-notice zc-inline-notice-warning" role="status">${escapeHtml(t('company.switcher.refresh_failed'))}</div>`
        : '';
      const refreshing = this._refreshing
        ? `<div class="zc-inline-notice zc-inline-notice-muted" role="status">${escapeHtml(t('company.switcher.refreshing'))}</div>`
        : '';

      root.innerHTML = `
        <div class="zc-sheet-overlay" data-layout="${phone ? 'sheet' : 'dialog'}">
          <section class="zc-sheet" role="dialog" aria-modal="true" aria-labelledby="zcSwitcherTitle">
            <div class="zc-sheet-grabber" aria-hidden="true"></div>
            <header class="zc-sheet-header">
              <div>
                <h2 class="zc-sheet-title" id="zcSwitcherTitle">${escapeHtml(t('company.switcher.title'))}</h2>
                <p class="zc-sheet-subtitle">${escapeHtml(t('company.switcher.subtitle'))}</p>
              </div>
              <button type="button" class="zc-icon-button" id="zcSwitcherClose" aria-label="${escapeAttr(t('common.close'))}">
                ${window.Icon ? window.Icon({ name: 'x', size: 18, tone: 'default' }) : '✕'}
              </button>
            </header>
            <div class="zc-sheet-body">
              ${errorBanner}
              ${refreshing}
              ${body}
            </div>
            <footer class="zc-sheet-footer">
              <button type="button" class="zc-add-button" id="zcSwitcherAdd">
                <span class="zc-add-plus" aria-hidden="true">${window.Icon ? window.Icon({ name: 'plus', size: 16, tone: 'white' }) : '+'}</span>
                <span>${escapeHtml(t('company.switcher.add'))}</span>
              </button>
            </footer>
          </section>
        </div>
      `;

      root.querySelector('#zcSwitcherClose').addEventListener('click', () => this.close());
      root.querySelector('#zcSwitcherAdd').addEventListener('click', () => this.addCompany());
      root.querySelectorAll('[data-company-id]').forEach((button) => {
        button.addEventListener('click', () => this.selectCompany(button.getAttribute('data-company-id')));
      });
      const overlay = root.querySelector('.zc-sheet-overlay');
      overlay.addEventListener('click', (event) => {
        if (event.target === overlay) this.close();
      });

      this._focusInitial();
    }

    _focusInitial() {
      const root = document.getElementById(ROOT_ID);
      if (!root) return;
      const target = root.querySelector('[aria-current="true"]')
        || root.querySelector('[data-company-id]')
        || root.querySelector('#zcSwitcherAdd');
      if (target) {
        try { target.focus(); } catch (err) { /* ignore */ }
      }
    }

    _onKeydown(event) {
      const root = document.getElementById(ROOT_ID);
      if (!root) return;

      if (event.key === 'Escape') {
        event.preventDefault();
        this.close();
        return;
      }

      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        const focusables = currentFocusable(root);
        if (!focusables.length) return;
        event.preventDefault();
        const index = focusables.indexOf(document.activeElement);
        const next = event.key === 'ArrowDown'
          ? (index + 1 + focusables.length) % focusables.length
          : (index - 1 + focusables.length) % focusables.length;
        focusables[next].focus();
        return;
      }

      if (event.key === 'Tab') {
        const focusables = currentFocusable(root);
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }

    selectCompany(companyId) {
      if (!companyId) return;
      const companies = cachedCompanies();
      const company = companies.find((item) => item.id === companyId);
      if (!company) {
        // A stale row (deleted elsewhere): refresh instead of pretending.
        this._error = true;
        this.refresh();
        return;
      }

      const ctx = window.CurrentCompanyContext;
      if (ctx && typeof ctx.setCompanyId === 'function') {
        ctx.setCompanyId(companyId);
      } else if (window.state) {
        window.state.activeCompanyId = companyId;
      }

      if (window.state) window.state.activeCompanyId = companyId;
      if (typeof window.populateGlobalCompanySelector === 'function') window.populateGlobalCompanySelector();
      if (typeof window.updateBreadcrumbs === 'function') window.updateBreadcrumbs();
      if (window.URAAssistant && typeof window.URAAssistant.refreshContext === 'function') {
        window.URAAssistant.refreshContext();
      }
      this.syncSidebar();

      if (window.UI && typeof window.UI.showToast === 'function') {
        window.UI.showToast(t('company.switcher.switched', { name: company.name }), 'info');
      }
      this.close();
      if (typeof window.renderActiveNavView === 'function') window.renderActiveNavView();
    }

    addCompany() {
      this.close();
      if (typeof window.navigateTo === 'function') {
        window.navigateTo('/company/add');
      } else {
        window.location.hash = '#/company/add';
      }
    }

    refresh() {
      let token = null;
      try {
        token = localStorage.getItem('zonata_auth_token');
      } catch (err) {
        token = null;
      }
      if (!token) {
        this._refreshing = false;
        this.render();
        return;
      }

      this._refreshing = true;
      this._error = false;
      this.render();

      fetch('/api/companies', { headers: { Accept: 'application/json' } })
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        })
        .then((data) => {
          const list = Array.isArray(data && data.companies) ? data.companies : [];
          this._applyServerList(list);
          this._error = false;
        })
        .catch(() => {
          // Keep the last known list, but say so. No silent fake success.
          this._error = true;
        })
        .then(() => {
          this._refreshing = false;
          this.render();
        });
    }

    _applyServerList(list) {
      const normalised = list.map(normaliseCompany).filter(Boolean);
      const rawList = normalised.map((company) => company.raw);
      const ctx = window.CurrentCompanyContext;

      if (ctx) {
        ctx.companies = rawList;
        let active = ctx.activeCompanyId;
        if (active && !normalised.some((company) => company.id === active)) active = null;
        if (!active && normalised.length) active = normalised[0].id;
        ctx.activeCompanyId = active || null;
        ctx.activeCompany = normalised.find((company) => company.id === active) || null;
        try {
          if (active) localStorage.setItem('zonata_active_company_id', active);
          else localStorage.removeItem('zonata_active_company_id');
        } catch (err) { /* storage blocked */ }
        if (typeof ctx.notify === 'function') ctx.notify();
      }

      if (window.state) {
        window.state.companies = rawList;
        window.state.activeCompanyId = (ctx && ctx.activeCompanyId) || (normalised[0] ? normalised[0].id : null);
      }

      if (typeof window.populateGlobalCompanySelector === 'function') window.populateGlobalCompanySelector();
      if (typeof window.updateBreadcrumbs === 'function') window.updateBreadcrumbs();
      this.syncSidebar();
    }

    syncSidebar() {
      const nameEl = document.getElementById('sidebarCompanyName');
      const statusEl = document.getElementById('sidebarCompanyStatus');
      const company = currentCompany();
      if (nameEl) {
        nameEl.textContent = company ? company.name : t('company.switcher.empty.sidebar');
      }
      if (statusEl) {
        statusEl.textContent = company ? statusLabel(company.status) : t('company.switcher.empty.status');
        const row = statusEl.closest ? statusEl.closest('.company-status-row') : null;
        const dot = row ? row.querySelector('.status-dot-active') : null;
        if (dot) {
          dot.setAttribute('data-tone', company ? statusMeta(company.status).tone : 'neutral');
        }
      }
    }

    /**
     * Client-side intent shortcut for the assistant. The server still owns the
     * real rules; this only opens a page or the switcher.
     */
    matchIntent(text) {
      const prompt = String(text || '').trim().toLowerCase();
      if (!prompt) return null;
      if (/أضف\s+شركة|إضافة\s+شركة|انشئ\s+شركة|إنشاء\s+شركة|اربط\s+شركة|ربط\s+شركة/.test(prompt)) return 'ADD';
      if (/تبديل\s+الشركة|تغيير\s+الشركة|بدّل\s+الشركة/.test(prompt)) return 'SWITCH';
      if (/\b(add|create|connect|onboard)\b[^.!?]{0,40}\b(company|business|entity|organisation|organization)\b/.test(prompt)) return 'ADD';
      if (/\b(switch|change)\b[^.!?]{0,30}\b(company|business|entity|context)\b/.test(prompt)) return 'SWITCH';
      return null;
    }

    statusLabel(value) {
      return statusLabel(value);
    }

    statusTone(value) {
      return statusMeta(value).tone;
    }
  }

  window.CompanySetupSwitcher = new CompanySwitcher();
  window.CompanySetupStatus = { label: statusLabel, tone: (value) => statusMeta(value).tone };
})();
