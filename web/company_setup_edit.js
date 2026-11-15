/**
 * ZONATA — Edit a company
 *
 * The same facts that were captured during setup, editable in one column:
 * identity, the accountable owner, money, operations, and the optional
 * details. The company type is fixed and shown as such, because changing NEW
 * to EXISTING would silently rewrite the build history behind it.
 *
 * Validation runs here for speed and again on the server, which is the real
 * gate. Saving is a PATCH to the existing company route; the server writes the
 * audit event. If a build is running the page says so plainly: changes are
 * saved now and the build is not silently restarted.
 *
 * Connections can be added or removed here as well. Every scope stays
 * read-only.
 *
 * Route: /company/<company_id>/edit
 */

(function() {
  'use strict';

  const CURRENCIES = ['INR', 'USD', 'AED', 'GBP', 'EUR', 'SGD', 'AUD', 'CAD', 'SAR', 'QAR', 'KWD', 'OMR', 'BHD'];
  const PERIODS = ['ANNUAL', 'MONTHLY', 'QUARTERLY', 'WEEKLY', 'DAILY', 'ONE_TIME'];

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

  function language() {
    return (window.I18n && window.I18n.getLanguage && window.I18n.getLanguage()) || 'en';
  }

  function statusLabel(value) {
    const status = String(value || '').toUpperCase();
    const key = `status.${status.toLowerCase()}`;
    const label = t(key);
    return label === key ? status : label;
  }

  function emailLooksValid(value) {
    const text = String(value || '').trim();
    if (!text) return true;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text);
  }

  function urlLooksValid(value) {
    const text = String(value || '').trim();
    if (!text) return true;
    return /^https?:\/\/\S+$/i.test(text);
  }

  function numberOrNull(value) {
    const text = String(value == null ? '' : value).trim();
    if (!text) return null;
    const number = Number(text);
    return Number.isFinite(number) ? number : null;
  }

  class CompanySetupEdit {
    constructor() {
      this.containerId = null;
      this.companyId = null;
      this.company = null;
      this.connections = [];
      this.catalogue = [];
      this.loading = true;
      this.saving = false;
      this.error = null;
      this.notice = null;
      this.errors = {};
      this.data = {};
      this.connectionError = null;
      this.connectionBusy = false;
      this._onLanguageChange = this._onLanguageChange.bind(this);
      if (document && document.addEventListener) {
        document.addEventListener('zonata:languagechange', this._onLanguageChange);
      }
    }

    render(containerOrId, companyId) {
      const container = typeof containerOrId === 'string'
        ? document.getElementById(containerOrId)
        : containerOrId;
      if (!container) return;
      this.containerId = container.id || this.containerId;
      if (companyId) this.companyId = String(companyId);
      if (!this.companyId) this.companyId = this._companyIdFromHash();
      if (!this.companyId) {
        this.loading = false;
        this.error = { code: 'NO_COMPANY', message: t('company.overview.error.no_company') };
        this._render();
        return;
      }
      this.loading = true;
      this.error = null;
      this._render();
      this._load();
    }

    destroy() {
      this.notice = null;
    }

    _companyIdFromHash() {
      const hash = String(window.location.hash || '').replace(/^#/, '');
      const match = hash.match(/^\/company\/([^/]+)\/edit\/?$/);
      return match ? decodeURIComponent(match[1]) : null;
    }

    _onLanguageChange() {
      if (!this.containerId) return;
      const container = document.getElementById(this.containerId);
      if (container && container.querySelector('[data-company-edit]')) this._render();
    }

    async _get(path) {
      try {
        const response = await fetch(path);
        let data = {};
        try { data = await response.json(); } catch (err) { data = {}; }
        return { ok: response.ok, status: response.status, data };
      } catch (err) {
        return { ok: false, status: 0, data: {}, offline: true };
      }
    }

    async _send(method, path, body) {
      try {
        const response = await fetch(path, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: body === undefined ? undefined : JSON.stringify(body)
        });
        let data = {};
        try { data = await response.json(); } catch (err) { data = {}; }
        return { ok: response.ok, status: response.status, data };
      } catch (err) {
        return { ok: false, status: 0, data: {}, offline: true };
      }
    }

    async _load() {
      const base = `/api/v1/companies/${encodeURIComponent(this.companyId)}`;
      const [company, connections, catalogue] = await Promise.all([
        this._get(base),
        this._get(`${base}/connections`),
        this._get('/api/v1/companies/sources/catalogue')
      ]);

      if (!company.ok) {
        this.loading = false;
        this.error = {
          code: company.status === 404 ? 'NOT_FOUND' : (company.offline ? 'OFFLINE' : 'LOAD_FAILED'),
          message: company.status === 404
            ? t('company.overview.error.not_found')
            : (company.offline ? t('company.overview.error.offline') : t('company.overview.error.load'))
        };
        this._render();
        return;
      }

      this.company = company.data;
      this.connections = connections.ok && Array.isArray(connections.data.connections)
        ? connections.data.connections
        : [];
      this.catalogue = catalogue.ok && Array.isArray(catalogue.data.sources)
        ? catalogue.data.sources
        : [];
      this.data = this._formData(company.data);
      this.loading = false;
      this._render();
    }

    _formData(company) {
      const owner = company.owner || {};
      const revenue = company.revenue || {};
      const budget = company.budget || {};
      return {
        name: company.name || '',
        title: company.title || '',
        description: company.description || '',
        owner_name: owner.name || '',
        owner_email: owner.email || '',
        owner_role: owner.role || '',
        country: company.country || '',
        industry: company.industry || '',
        website: company.website || '',
        business_model: company.business_model || '',
        target_customers: company.target_customers || '',
        revenue_amount: revenue.amount == null ? '' : String(revenue.amount),
        revenue_currency: revenue.currency || company.currency || 'INR',
        revenue_period: revenue.period || 'ANNUAL',
        budget_amount: budget.amount == null ? '' : String(budget.amount),
        budget_currency: budget.currency || company.currency || 'INR',
        timeline: company.timeline || '',
        setup_notes: company.setup_notes || '',
        assets: Array.isArray(company.assets) ? company.assets.join('\n') : ''
      };
    }

    // ------------------------------------------------------------- rendering
    _render() {
      const container = document.getElementById(this.containerId);
      if (!container) return;
      if (this.loading) {
        container.innerHTML = this._shell(this._loadingHtml());
        this._bind(container);
        return;
      }
      if (this.error) {
        container.innerHTML = this._shell(this._errorHtml());
        this._bind(container);
        return;
      }
      if (!this.company || !this.company.permissions || !this.company.permissions.edit) {
        container.innerHTML = this._shell(this._readOnlyHtml());
        this._bind(container);
        return;
      }
      container.innerHTML = this._shell(this._formHtml());
      this._bind(container);
    }

    _shell(inner) {
      return `
        <div class="zc-flow-page zc-edit-page" data-company-edit>
          <div class="zc-flow-top">
            <button type="button" class="zc-back-link" id="zcEditBack">
              <span class="zc-back-arrow" aria-hidden="true">←</span>
              <span>${escapeHtml(t('company.edit.back'))}</span>
            </button>
            <div class="zc-language-toggle" role="group" aria-label="${escapeHtml(t('common.language'))}">
              <button type="button" data-language="en" aria-pressed="${language() === 'en' ? 'true' : 'false'}">${escapeHtml(t('common.english'))}</button>
              <button type="button" data-language="ar" aria-pressed="${language() === 'ar' ? 'true' : 'false'}">${escapeHtml(t('common.arabic'))}</button>
            </div>
          </div>
          ${inner}
        </div>
      `;
    }

    _loadingHtml() {
      return `
        <header class="zc-flow-header">
          <h1 class="zc-flow-title">${escapeHtml(t('company.edit.title'))}</h1>
          <p class="zc-flow-subtitle" role="status">${escapeHtml(t('common.loading'))}</p>
        </header>
        <div class="zc-skeleton-stack" aria-hidden="true">
          <span class="zc-skeleton zc-skeleton-lg"></span>
          <span class="zc-skeleton"></span>
          <span class="zc-skeleton"></span>
        </div>
      `;
    }

    _errorHtml() {
      return `
        <div class="zc-inline-notice zc-inline-notice-error" role="alert">
          <strong>${escapeHtml(t('company.edit.error.title'))}</strong>
          <span>${escapeHtml(this.error && this.error.message ? this.error.message : t('company.overview.error.load'))}</span>
        </div>
        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-quiet" id="zcEditErrorBack">${escapeHtml(t('company.edit.back'))}</button>
          <button type="button" class="zc-button zc-button-primary" id="zcEditReload">${escapeHtml(t('common.retry'))}</button>
        </div>
      `;
    }

    _readOnlyHtml() {
      return `
        <header class="zc-flow-header">
          <p class="zc-eyebrow">${escapeHtml(t('company.edit.eyebrow'))}</p>
          <h1 class="zc-flow-title">${escapeHtml(this.company.name || t('company.edit.title'))}</h1>
          <p class="zc-flow-subtitle">${escapeHtml(t('company.edit.readonly'))}</p>
        </header>
        <div class="zc-inline-notice zc-inline-notice-muted" role="status">
          ${escapeHtml(t('company.edit.readonly_note'))}
        </div>
        <div class="zc-form-actions">
          <button type="button" class="zc-button zc-button-primary" id="zcEditReadOnlyBack">${escapeHtml(t('company.overview.back'))}</button>
        </div>
      `;
    }

    _formHtml() {
      const company = this.company || {};
      const canManageConnections = !!(company.permissions && company.permissions.manage_connections);
      const buildRunning = !!(company.build && String(company.build.phase_state || '').toUpperCase() === 'RUNNING');
      return `
        <header class="zc-flow-header">
          <p class="zc-eyebrow">${escapeHtml(t('company.edit.eyebrow'))}</p>
          <h1 class="zc-flow-title">${escapeHtml(t('company.edit.title'))}</h1>
          <p class="zc-flow-subtitle">${escapeHtml(t('company.edit.subtitle'))}</p>
          <div class="zc-edit-type">
            <span class="zc-pill zc-pill-neutral">${escapeHtml(company.type === 'EXISTING' ? t('company.overview.type.existing') : t('company.overview.type.new'))}</span>
            <span class="zc-section-note">${escapeHtml(t('company.edit.type_fixed'))}</span>
          </div>
        </header>

        ${buildRunning ? `
          <div class="zc-inline-notice zc-inline-notice-warning" role="status">
            ${escapeHtml(t('company.edit.build_running'))}
          </div>
        ` : ''}

        ${this.notice ? `<div class="zc-inline-notice zc-inline-notice-success" role="status">${escapeHtml(this.notice)}</div>` : ''}
        ${this._errorSummaryHtml()}

        <form id="zcEditForm" class="zc-form" novalidate>
          <section class="zc-form-section" aria-labelledby="zcEditIdentity">
            <h2 class="zc-section-title" id="zcEditIdentity">${escapeHtml(t('company.edit.section.identity'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.edit.section.identity_note'))}</p>
            ${this._field('name', t('company.create.name.label'), { hint: t('company.create.name.hint'), required: true, autocomplete: 'organization' })}
            ${this._field('title', t('company.create.tagline.label'), { hint: t('company.create.tagline.hint') })}
            ${this._field('description', t('company.create.description.label'), { hint: t('company.create.description.hint'), multiline: true, rows: 6 })}
          </section>

          <section class="zc-form-section" aria-labelledby="zcEditOwner">
            <h2 class="zc-section-title" id="zcEditOwner">${escapeHtml(t('company.edit.section.owner'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.edit.section.owner_note'))}</p>
            ${this._field('owner_name', t('company.create.owner.label'), { hint: t('company.create.owner.hint'), autocomplete: 'name' })}
            ${this._field('owner_email', t('company.create.email.label'), { hint: t('company.create.email.hint'), type: 'email', autocomplete: 'email' })}
            ${this._field('owner_role', t('company.create.role.label'), { hint: t('company.create.role.hint') })}
          </section>

          <section class="zc-form-section" aria-labelledby="zcEditWhere">
            <h2 class="zc-section-title" id="zcEditWhere">${escapeHtml(t('company.create.where.title'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.create.where.note'))}</p>
            <div class="zc-field-row">
              ${this._field('country', t('company.create.country.label'), { hint: t('company.create.country.hint'), autocomplete: 'country' })}
              ${this._field('industry', t('company.create.industry.label'), { hint: t('company.create.industry.hint') })}
            </div>
            ${this._field('website', t('company.create.website.label'), { hint: t('company.create.website.hint'), type: 'url' })}
            ${this._field('business_model', t('company.existing.model.label'), { hint: t('company.existing.model.hint'), multiline: true, rows: 4 })}
            ${this._field('target_customers', t('company.create.customers.label'), { hint: t('company.create.customers.hint') })}
          </section>

          <section class="zc-form-section" aria-labelledby="zcEditNumbers">
            <h2 class="zc-section-title" id="zcEditNumbers">${escapeHtml(t('company.edit.section.numbers'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.edit.section.numbers_note'))}</p>
            <div class="zc-field-row zc-field-row-three">
              ${this._field('revenue_amount', t('company.existing.revenue.label'), { hint: t('company.existing.revenue.hint'), inputmode: 'decimal' })}
              <div class="zc-field">
                <label class="zc-label" for="zcField-revenue_currency">${escapeHtml(t('company.existing.revenue.currency'))}</label>
                <select class="zc-input zc-select" id="zcField-revenue_currency" data-field="revenue_currency">
                  ${CURRENCIES.map((code) => `<option value="${code}"${this.data.revenue_currency === code ? ' selected' : ''}>${code}</option>`).join('')}
                </select>
              </div>
              <div class="zc-field">
                <label class="zc-label" for="zcField-revenue_period">${escapeHtml(t('company.existing.revenue.period'))}</label>
                <select class="zc-input zc-select" id="zcField-revenue_period" data-field="revenue_period">
                  ${PERIODS.map((code) => `<option value="${code}"${this.data.revenue_period === code ? ' selected' : ''}>${escapeHtml(t(`company.revenue.period.${code.toLowerCase()}`, { period: code }))}</option>`).join('')}
                </select>
              </div>
            </div>
            <div class="zc-field-row">
              ${this._field('budget_amount', t('company.create.budget.label'), { hint: t('company.create.budget.hint'), inputmode: 'decimal' })}
              <div class="zc-field">
                <label class="zc-label" for="zcField-budget_currency">${escapeHtml(t('company.create.budget.currency'))}</label>
                <select class="zc-input zc-select" id="zcField-budget_currency" data-field="budget_currency">
                  ${CURRENCIES.map((code) => `<option value="${code}"${this.data.budget_currency === code ? ' selected' : ''}>${code}</option>`).join('')}
                </select>
              </div>
            </div>
          </section>

          <section class="zc-form-section" aria-labelledby="zcEditOptional">
            <h2 class="zc-section-title" id="zcEditOptional">${escapeHtml(t('company.create.optional.title'))}</h2>
            <p class="zc-section-note">${escapeHtml(t('company.create.optional.note'))}</p>
            ${this._field('timeline', t('company.create.timeline.label'), { hint: t('company.create.timeline.hint') })}
            ${this._field('setup_notes', t('company.create.notes.label'), { hint: t('company.create.notes.hint'), multiline: true, rows: 4 })}
            ${this._field('assets', t('company.create.assets.label'), { hint: t('company.create.assets.hint'), multiline: true, rows: 3 })}
          </section>

          <div class="zc-form-actions">
            <button type="button" class="zc-button zc-button-quiet" id="zcEditCancel">${escapeHtml(t('common.cancel'))}</button>
            <button type="button" class="zc-button zc-button-primary" id="zcEditSave"${this.saving ? ' disabled' : ''}>
              ${escapeHtml(this.saving ? t('company.edit.saving') : t('company.edit.save'))}
            </button>
          </div>
        </form>

        ${canManageConnections ? this._connectionsHtml() : ''}

        <p class="zc-form-footnote">${escapeHtml(t('company.edit.footnote'))}</p>
      `;
    }

    _errorSummaryHtml() {
      const fields = Object.keys(this.errors || {});
      if (!fields.length) return '';
      return `
        <div class="zc-inline-notice zc-inline-notice-error" role="alert">
          <strong>${escapeHtml(t('company.create.errors.title'))}</strong>
          <ul class="zc-error-list">
            ${fields.map((field) => `<li>${escapeHtml(this.errors[field])}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    _field(name, label, opts) {
      const options = opts || {};
      const value = this.data[name] == null ? '' : this.data[name];
      const error = this.errors[name];
      const describedBy = [];
      if (options.hint) describedBy.push(`zcEditHint-${name}`);
      if (error) describedBy.push(`zcEditErr-${name}`);
      const hintHtml = options.hint
        ? `<p class="zc-field-hint" id="zcEditHint-${name}">${escapeHtml(options.hint)}</p>`
        : '';
      const errorHtml = `<p class="zc-field-error" id="zcEditErr-${name}" role="alert"${error ? '' : ' hidden'}>${escapeHtml(error || '')}</p>`;
      const shared = `id="zcField-${name}" name="${name}" data-field="${name}"`;
      const aria = `aria-describedby="${describedBy.join(' ')}" aria-invalid="${error ? 'true' : 'false'}"${options.required ? ' aria-required="true"' : ''}`;
      const control = options.multiline
        ? `<textarea class="zc-input zc-textarea" ${shared} rows="${options.rows || 4}" ${aria}>${escapeHtml(value)}</textarea>`
        : `<input class="zc-input" ${shared} type="${options.type || 'text'}" value="${escapeHtml(value)}" ${aria}${options.autocomplete ? ` autocomplete="${options.autocomplete}"` : ''}${options.inputmode ? ` inputmode="${options.inputmode}"` : ''} />`;
      return `
        <div class="zc-field${error ? ' has-error' : ''}" data-field-wrap="${name}">
          <label class="zc-label" for="zcField-${name}">${escapeHtml(label)}${options.required ? ' <span class="zc-required" aria-hidden="true">*</span>' : ''}${options.required ? '' : `<span class="zc-optional">${escapeHtml(t('company.create.optional'))}</span>`}</label>
          ${control}
          ${hintHtml}
          ${errorHtml}
        </div>
      `;
    }

    _connectionsHtml() {
      const connected = Array.isArray(this.connections) ? this.connections : [];
      const connectedIds = new Set(connected.map((item) => item.source_id || item.provider_id));
      const available = (this.catalogue || []).filter((source) => !connectedIds.has(source.id));
      return `
        <section class="zc-form-section zc-edit-connections" aria-labelledby="zcEditConnections">
          <h2 class="zc-section-title" id="zcEditConnections">${escapeHtml(t('company.edit.connections.title'))}</h2>
          <p class="zc-section-note">${escapeHtml(t('company.edit.connections.note'))}</p>
          ${this.connectionError ? `<div class="zc-inline-notice zc-inline-notice-error" role="alert">${escapeHtml(this.connectionError)}</div>` : ''}
          ${connected.length ? `
            <ul class="zc-edit-connection-list">
              ${connected.map((item) => `
                <li>
                  <span class="zc-edit-connection-name">${escapeHtml(item.name || item.provider_id || item.connection_id)}</span>
                  <span class="zc-pill zc-pill-neutral">${escapeHtml(item.status || 'NEEDS_CHECK')}</span>
                  <button type="button" class="zc-link-button zc-link-danger" data-remove-connection="${escapeHtml(item.connection_id)}"${this.connectionBusy ? ' disabled' : ''}>
                    ${escapeHtml(t('company.edit.connections.remove'))}
                  </button>
                </li>
              `).join('')}
            </ul>
          ` : `<p class="zc-section-note">${escapeHtml(t('company.edit.connections.empty'))}</p>`}
          ${available.length ? `
            <div class="zc-connection-add">
              <label class="zc-label" for="zcConnectionSource">${escapeHtml(t('company.edit.connections.add_label'))}</label>
              <div class="zc-connection-add-row">
                <select class="zc-input zc-select" id="zcConnectionSource">
                  ${available.map((source) => `<option value="${escapeHtml(source.id)}">${escapeHtml(source.name)}</option>`).join('')}
                </select>
                <button type="button" class="zc-button zc-button-quiet" id="zcConnectionAdd"${this.connectionBusy ? ' disabled' : ''}>${escapeHtml(t('company.edit.connections.add'))}</button>
              </div>
            </div>
          ` : ''}
          <p class="zc-form-footnote">${escapeHtml(t('company.edit.connections.scope_note'))}</p>
        </section>
      `;
    }

    // --------------------------------------------------------------- binding
    _bind(container) {
      const back = container.querySelector('#zcEditBack');
      if (back) back.addEventListener('click', () => this._goOverview());
      const errorBack = container.querySelector('#zcEditErrorBack');
      if (errorBack) errorBack.addEventListener('click', () => this._go('/company'));
      const readOnlyBack = container.querySelector('#zcEditReadOnlyBack');
      if (readOnlyBack) readOnlyBack.addEventListener('click', () => this._goOverview());
      const cancel = container.querySelector('#zcEditCancel');
      if (cancel) cancel.addEventListener('click', () => this._goOverview());
      const reload = container.querySelector('#zcEditReload');
      if (reload) reload.addEventListener('click', () => {
        this.loading = true;
        this.error = null;
        this._render();
        this._load();
      });

      container.querySelectorAll('[data-language]').forEach((button) => {
        button.addEventListener('click', () => {
          if (window.I18n && window.I18n.setLanguage) window.I18n.setLanguage(button.getAttribute('data-language'));
        });
      });

      const form = container.querySelector('#zcEditForm');
      if (form) {
        form.addEventListener('submit', (event) => {
          event.preventDefault();
          this.save();
        });
        form.addEventListener('input', (event) => this._onInput(event));
        form.addEventListener('change', (event) => this._onInput(event));
        form.addEventListener('focusout', (event) => {
          const field = event.target && event.target.getAttribute && event.target.getAttribute('data-field');
          if (field) this._validateField(field, true);
        });
      }

      const save = container.querySelector('#zcEditSave');
      if (save) save.addEventListener('click', () => this.save());

      container.querySelectorAll('[data-remove-connection]').forEach((button) => {
        button.addEventListener('click', () => this.removeConnection(button.getAttribute('data-remove-connection')));
      });
      const add = container.querySelector('#zcConnectionAdd');
      if (add) add.addEventListener('click', () => this.addConnection());
    }

    _onInput(event) {
      const target = event.target;
      if (!target || !target.getAttribute) return;
      const field = target.getAttribute('data-field');
      if (!field) return;
      this.data[field] = target.value;
      if (this.errors[field]) {
        delete this.errors[field];
        this._clearFieldError(field);
      }
    }

    _clearFieldError(field) {
      const wrap = document.querySelector(`[data-field-wrap="${field}"]`);
      const error = document.getElementById(`zcEditErr-${field}`);
      const input = document.getElementById(`zcField-${field}`);
      if (error) {
        error.textContent = '';
        error.hidden = true;
      }
      if (wrap) wrap.classList.remove('has-error');
      if (input) input.setAttribute('aria-invalid', 'false');
      const summary = document.querySelector('[data-company-edit] .zc-inline-notice-error');
      if (!Object.keys(this.errors).length && summary) summary.remove();
    }

    _validateField(field, quiet) {
      const message = this._fieldError(field);
      if (message) {
        this.errors[field] = message;
        if (!quiet) this._render();
      } else if (this.errors[field]) {
        delete this.errors[field];
        this._clearFieldError(field);
      }
      return !message;
    }

    _fieldError(field) {
      const value = this.data[field];
      if (field === 'name') {
        if (!String(value || '').trim()) return t('company.create.error.name_required');
        if (String(value).trim().length < 2) return t('company.create.error.name_short');
      }
      if (field === 'owner_email' && !emailLooksValid(value)) return t('company.create.error.email');
      if (field === 'website' && !urlLooksValid(value)) return t('company.create.error.url');
      if (field === 'revenue_amount') {
        if (String(value || '').trim() && numberOrNull(value) == null) return t('company.existing.error.revenue_amount');
        if (numberOrNull(value) != null && numberOrNull(value) < 0) return t('company.edit.error.negative');
      }
      if (field === 'budget_amount') {
        if (String(value || '').trim() && numberOrNull(value) == null) return t('company.create.error.budget');
        if (numberOrNull(value) != null && numberOrNull(value) < 0) return t('company.edit.error.negative');
      }
      if (field === 'assets') {
        const bad = String(value || '').split('\n').map((line) => line.trim()).filter(Boolean).filter((line) => !urlLooksValid(line));
        if (bad.length) return t('company.create.error.assets');
      }
      return '';
    }

    validate() {
      this.errors = {};
      ['name', 'owner_email', 'website', 'revenue_amount', 'budget_amount', 'assets'].forEach((field) => {
        const message = this._fieldError(field);
        if (message) this.errors[field] = message;
      });
      return Object.keys(this.errors).length === 0;
    }

    _payload() {
      const assets = String(this.data.assets || '')
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);
      return {
        name: String(this.data.name || '').trim(),
        title: String(this.data.title || '').trim(),
        description: String(this.data.description || '').trim(),
        owner: {
          name: String(this.data.owner_name || '').trim(),
          email: String(this.data.owner_email || '').trim(),
          role: String(this.data.owner_role || '').trim()
        },
        country: String(this.data.country || '').trim(),
        industry: String(this.data.industry || '').trim(),
        website: String(this.data.website || '').trim(),
        business_model: String(this.data.business_model || '').trim(),
        target_customers: String(this.data.target_customers || '').trim(),
        revenue: {
          amount: numberOrNull(this.data.revenue_amount),
          currency: String(this.data.revenue_currency || '').trim().toUpperCase(),
          period: String(this.data.revenue_period || '').trim().toUpperCase()
        },
        budget: {
          amount: numberOrNull(this.data.budget_amount),
          currency: String(this.data.budget_currency || '').trim().toUpperCase()
        },
        timeline: String(this.data.timeline || '').trim(),
        setup_notes: String(this.data.setup_notes || '').trim(),
        assets
      };
    }

    async save() {
      if (this.saving) return;
      this.notice = null;
      if (!this.validate()) {
        this._render();
        const first = Object.keys(this.errors)[0];
        const input = first ? document.getElementById(`zcField-${first}`) : null;
        if (input && input.focus) input.focus();
        return;
      }
      this.saving = true;
      this._render();
      const result = await this._send(
        'PATCH',
        `/api/v1/companies/${encodeURIComponent(this.companyId)}`,
        this._payload()
      );
      this.saving = false;
      if (!result.ok) {
        this._handleSaveError(result);
        this._render();
        return;
      }
      this.company = result.data;
      this.data = this._formData(result.data);
      if (window.showToast) {
        window.showToast(t('company.edit.saved'), 'success');
      }
      this._goOverview();
    }

    _handleSaveError(result) {
      const data = result.data || {};
      const code = String(data.code || '');
      this.errors = {};
      if (code === 'DUPLICATE_COMPANY_NAME') {
        this.errors.name = t('company.create.error.duplicate');
      } else if (code === 'VALIDATION_FAILED' && Array.isArray(data.detail)) {
        data.detail.forEach((item) => {
          const field = String(item.field || 'name')
            .replace(/^owner\./, 'owner_')
            .replace(/^revenue\./, 'revenue_')
            .replace(/^budget\./, 'budget_')
            .replace(/\./g, '_');
          if (item.message) this.errors[field || 'name'] = item.message;
        });
      } else if (code === 'FORBIDDEN') {
        this.error = { code, message: t('company.edit.error.forbidden') };
        return;
      } else if (result.offline) {
        this.error = { code: 'OFFLINE', message: t('company.edit.error.offline') };
        return;
      } else {
        this.error = { code: code || 'SAVE_FAILED', message: data.error || t('company.edit.error.save') };
        return;
      }
      this.error = null;
    }

    async addConnection() {
      if (this.connectionBusy) return;
      const select = document.getElementById('zcConnectionSource');
      const sourceId = select ? select.value : '';
      if (!sourceId) return;
      this.connectionBusy = true;
      this.connectionError = null;
      this._render();
      const result = await this._send(
        'POST',
        `/api/v1/companies/${encodeURIComponent(this.companyId)}/connections`,
        { source_id: sourceId }
      );
      this.connectionBusy = false;
      if (!result.ok) {
        this.connectionError = result.data && result.data.error
          ? result.data.error
          : t('company.edit.connections.add_failed');
        this._render();
        return;
      }
      await this._reloadConnections();
    }

    async removeConnection(connectionId) {
      if (this.connectionBusy || !connectionId) return;
      const confirmed = typeof window.confirm === 'function'
        ? window.confirm(t('company.edit.connections.remove_confirm'))
        : true;
      if (!confirmed) return;
      this.connectionBusy = true;
      this.connectionError = null;
      this._render();
      const result = await this._send(
        'DELETE',
        `/api/v1/companies/${encodeURIComponent(this.companyId)}/connections/${encodeURIComponent(connectionId)}`
      );
      this.connectionBusy = false;
      if (!result.ok) {
        this.connectionError = result.data && result.data.error
          ? result.data.error
          : t('company.edit.connections.remove_failed');
        this._render();
        return;
      }
      await this._reloadConnections();
    }

    async _reloadConnections() {
      const result = await this._get(
        `/api/v1/companies/${encodeURIComponent(this.companyId)}/connections`
      );
      if (result.ok && Array.isArray(result.data.connections)) {
        this.connections = result.data.connections;
      }
      this._render();
    }

    _goOverview() {
      this._go(`/company/${encodeURIComponent(this.companyId)}/overview`);
    }

    _go(path) {
      if (typeof window.navigateTo === 'function') {
        window.navigateTo(path);
      } else {
        window.location.hash = `#${path}`;
      }
    }
  }

  window.CompanySetupEdit = new CompanySetupEdit();
})();
